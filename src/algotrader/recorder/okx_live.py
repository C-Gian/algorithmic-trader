"""OKX public/read-only live recorder (no credentials, no private channels, no orders).

Verified against the live service on 2026-09-30:

* candle channels (``candle1m``, ``mark-price-candle1m``, ``index-candle1m``) are
  served on the *business* WebSocket endpoint; subscribing to them on the public
  endpoint fails with code 60018;
* ``funding-rate`` is served on the *public* endpoint and pushes the evolving
  pre-settlement funding information about every 30 s;
* candle pushes carry ``confirm`` = "0" while forming and "1" once complete;
* the connection is kept alive with a text ``ping`` (answered by ``pong``).

The recorder writes every received message raw, together with the local
receipt time taken immediately after the read returns (see RECEIPT_POINT), and
logs connection lifecycle and clock observations. It never fabricates messages
for a disconnection; reconnects are logged with a new connection generation.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Protocol

from ..marketdata.okx import USER_AGENT, urllib_transport
from ..marketdata.okx_authority import validate_okx_rest_base_url, validate_okx_ws_url
from .contracts import (
    ChannelFamily,
    ChannelSpec,
    ClockObservation,
    Connection,
    Endpoints,
    ParseStatus,
    SessionConfig,
)
from .journal import Clock, SessionWriter

DEFAULT_ENDPOINTS = Endpoints(
    ws_public_url="wss://ws.okx.com:8443/ws/v5/public",
    ws_business_url="wss://ws.okx.com:8443/ws/v5/business",
    rest_base_url="https://www.okx.com",
)
# Regional domains documented by OKX differ (e.g. EEA); configure, never assume one hostname.
REST_ALLOWED_PATHS = frozenset({"/api/v5/public/time", "/api/v5/public/instruments", "/api/v5/public/funding-rate"})
WS_PUBLIC_PATH = "/ws/v5/public"
WS_BUSINESS_PATH = "/ws/v5/business"
FORBIDDEN_HEADERS = frozenset({"ok-access-key", "ok-access-sign", "ok-access-passphrase", "ok-access-timestamp",
                               "authorization"})


class SystemClock:
    def time_ns(self) -> int:
        return time.time_ns()

    def monotonic_ns(self) -> int:
        return time.monotonic_ns()


def default_channels(inst_id: str = "BTC-USDT-SWAP", index_id: str = "BTC-USDT") -> tuple[ChannelSpec, ...]:
    return (
        ChannelSpec(family=ChannelFamily.TRADE_BAR_1M, channel="candle1m", inst_id=inst_id,
                    connection=Connection.BUSINESS),
        ChannelSpec(family=ChannelFamily.MARK_BAR_1M, channel="mark-price-candle1m", inst_id=inst_id,
                    connection=Connection.BUSINESS),
        ChannelSpec(family=ChannelFamily.INDEX_BAR_1M, channel="index-candle1m", inst_id=index_id,
                    connection=Connection.BUSINESS),
        ChannelSpec(family=ChannelFamily.FUNDING_LIVE, channel="funding-rate", inst_id=inst_id,
                    connection=Connection.PUBLIC),
    )


def make_config(session_id: str, endpoints: Endpoints = DEFAULT_ENDPOINTS, max_duration=timedelta(hours=6),
                inst_id: str = "BTC-USDT-SWAP", index_id: str = "BTC-USDT", **overrides: Any) -> SessionConfig:
    values = dict(
        session_id=session_id, inst_id=inst_id, index_id=index_id, endpoints=endpoints,
        channels=default_channels(inst_id, index_id), max_duration=max_duration,
        ping_interval=timedelta(seconds=20), clock_probe_interval=timedelta(minutes=5),
        fsync_interval=timedelta(seconds=1), reconnect_initial=timedelta(seconds=1),
        reconnect_max=timedelta(seconds=60), funding_poll_interval=timedelta(seconds=30),
        completion_grace=timedelta(seconds=15), segment_max_bytes=16 * 1024 * 1024,
    )
    values.update(overrides)
    return SessionConfig(**values)


def validate_endpoints(ep: Endpoints) -> None:
    """Reject any endpoint that is not an official secure OKX public/business form (see okx_authority)."""
    validate_okx_ws_url(ep.ws_public_url, (WS_PUBLIC_PATH,))
    validate_okx_ws_url(ep.ws_business_url, (WS_BUSINESS_PATH,))
    validate_okx_rest_base_url(ep.rest_base_url)


# ---------------------------------------------------------------------------
# Transports (injectable for offline tests)
# ---------------------------------------------------------------------------


class WsConn(Protocol):
    async def send(self, text: str) -> None: ...
    async def recv(self) -> str: ...
    async def close(self) -> None: ...


WsConnect = Callable[[str], Awaitable[WsConn]]
RestGet = Callable[[str, dict[str, str]], Awaitable[tuple[int, bytes]]]


async def websockets_connect(url: str) -> WsConn:
    import websockets

    ws = await websockets.connect(url, ping_interval=None, open_timeout=15, close_timeout=3, max_size=2**22,
                                  user_agent_header=USER_AGENT)

    class _Conn:
        async def send(self, text: str) -> None:
            await ws.send(text)

        async def recv(self) -> str:
            msg = await ws.recv()
            return msg if isinstance(msg, str) else msg.decode("utf-8")

        async def close(self) -> None:
            await ws.close()

    return _Conn()


async def urllib_rest_get(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
    return await asyncio.to_thread(urllib_transport, url, headers, 10.0)


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------


@dataclass
class RecorderStats:
    records: int = 0
    per_channel: dict[str, int] = field(default_factory=dict)
    last_recv_utc_ns: int | None = None
    connection_state: dict[str, str] = field(default_factory=dict)
    generation: dict[str, int] = field(default_factory=dict)
    subscribed: set[str] = field(default_factory=set)
    reconnects: int = 0
    errors: int = 0
    funding_fallback: bool = False

    def as_dict(self) -> dict:
        return {"records": self.records, "per_channel": dict(sorted(self.per_channel.items())),
                "last_recv_utc_ns": self.last_recv_utc_ns, "connection_state": dict(self.connection_state),
                "generation": dict(self.generation), "subscribed": sorted(self.subscribed),
                "reconnects": self.reconnects, "errors": self.errors, "funding_fallback": self.funding_fallback}


class Recorder:
    def __init__(
        self,
        config: SessionConfig,
        writer: SessionWriter,
        clock: Clock | None = None,
        ws_connect: WsConnect = websockets_connect,
        rest_get: RestGet = urllib_rest_get,
        control: Callable[[RecorderStats], Awaitable[bool]] | None = None,  # returns True to stop
        control_interval: float = 2.0,
    ) -> None:
        validate_endpoints(config.endpoints)
        self.config = config
        self.writer = writer
        self.clock = clock or SystemClock()
        self.ws_connect = ws_connect
        self.rest_get = rest_get
        self.control = control
        self.control_interval = control_interval
        self.stats = RecorderStats()
        self._stop = asyncio.Event()
        self.stop_reason = "running"
        self._fallback_started = False
        self._tasks: list[asyncio.Task] = []
        self._by_key = {c.key: c for c in config.channels}

    def request_stop(self, reason: str) -> None:
        if not self._stop.is_set():
            self.stop_reason = reason
            self.writer.lifecycle("stop_requested", detail=reason)
            self._stop.set()

    # -- REST ------------------------------------------------------------------

    async def _rest(self, path: str, params: dict[str, str], purpose: str, **extra: Any):
        if path not in REST_ALLOWED_PATHS:
            raise ValueError(f"REST path {path} is not an allowed public endpoint")
        url = f"{self.config.endpoints.rest_base_url.rstrip('/')}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        assert not {h.lower() for h in headers} & FORBIDDEN_HEADERS
        sent_utc, sent_mono = self.clock.time_ns(), self.clock.monotonic_ns()
        try:
            status, body = await self.rest_get(url, headers)
        except Exception as exc:  # network failure: logged, never fabricated
            self.writer.lifecycle("rest_error", connection=Connection.REST, detail=f"{purpose}: {exc}")
            self.stats.errors += 1
            return None, sent_utc, sent_mono, None, None
        recv_utc, recv_mono = self.clock.time_ns(), self.clock.monotonic_ns()
        text = body.decode("utf-8", errors="replace")
        try:
            doc = json.loads(text)
            ok = isinstance(doc, dict) and str(doc.get("code")) == "0"
        except ValueError:
            doc, ok = None, False
        rec = self.writer.record(
            kind="rest_response", connection=Connection.REST, generation=0, endpoint=url,
            recv_utc_ns=recv_utc, recv_mono_ns=recv_mono, raw=text,
            parse_status=ParseStatus.DATA if ok else ParseStatus.ERROR,
            channel=extra.pop("channel", None), inst_id=extra.pop("inst_id", None),
            request_sent_utc_ns=sent_utc, request_sent_mono_ns=sent_mono, purpose=purpose, **extra,
        )
        self._count(rec)
        return (doc if ok else None), sent_utc, sent_mono, recv_utc, recv_mono

    async def probe_clock(self) -> None:
        doc, sent_utc, sent_mono, recv_utc, recv_mono = await self._rest("/api/v5/public/time", {}, "server_time")
        if doc is None or recv_mono is None:
            self.writer.clock_observation(ClockObservation(
                at_utc_ns=recv_utc or self.clock.time_ns(), request_sent_utc_ns=sent_utc,
                request_sent_mono_ns=sent_mono, response_mono_ns=recv_mono or self.clock.monotonic_ns(),
                server_ts_ms=None, rtt_ns=(recv_mono or sent_mono) - sent_mono, offset_estimate_ns=None,
                offset_bound_ns=None, status="unavailable", detail="server time not obtained"))
            return
        server_ms = int(doc["data"][0]["ts"])
        rtt = recv_mono - sent_mono
        midpoint = sent_utc + rtt // 2  # wall clock at the request midpoint (monotonic-derived spacing)
        self.writer.clock_observation(ClockObservation(
            at_utc_ns=recv_utc, request_sent_utc_ns=sent_utc, request_sent_mono_ns=sent_mono,
            response_mono_ns=recv_mono, server_ts_ms=server_ms, rtt_ns=rtt,
            offset_estimate_ns=server_ms * 1_000_000 - midpoint, offset_bound_ns=rtt // 2 + 1_000_000,
            status="ok", detail="offset = OKX server time - local midpoint; raw receipt times are not corrected"))

    async def _clock_loop(self) -> None:
        while not self._stop.is_set():
            await self.probe_clock()
            await self._sleep(self.config.clock_probe_interval.total_seconds())

    async def _funding_poll_loop(self, spec: ChannelSpec) -> None:
        previous = None
        interval = self.config.funding_poll_interval.total_seconds()
        while not self._stop.is_set():
            _, _, _, recv_utc, _ = await self._rest(
                "/api/v5/public/funding-rate", {"instId": spec.inst_id}, "funding_poll_fallback",
                channel=spec.channel, inst_id=spec.inst_id, poll_interval_s=interval,
                previous_observation_utc_ns=previous)
            previous = recv_utc or previous
            await self._sleep(interval)

    # -- WebSocket -------------------------------------------------------------

    def _classify(self, text: str) -> tuple[ParseStatus, str | None, str | None, dict | None]:
        if text == "pong":
            return ParseStatus.PONG, None, None, None
        try:
            doc = json.loads(text)
        except ValueError:
            return ParseStatus.UNPARSED, None, None, None
        if not isinstance(doc, dict):
            return ParseStatus.UNPARSED, None, None, None
        arg = doc.get("arg") or {}
        channel, inst = arg.get("channel"), arg.get("instId")
        if "event" in doc:
            return (ParseStatus.ERROR if doc["event"] == "error" else ParseStatus.EVENT), channel, inst, doc
        if "data" in doc:
            return ParseStatus.DATA, channel, inst, doc
        return ParseStatus.UNPARSED, channel, inst, doc

    def _count(self, rec) -> None:
        self.stats.records += 1
        self.stats.last_recv_utc_ns = rec.recv_utc_ns
        if rec.channel and rec.inst_id:
            key = f"{rec.channel}:{rec.inst_id}"
            self.stats.per_channel[key] = self.stats.per_channel.get(key, 0) + 1

    def _error_channel(self, doc: dict) -> str | None:
        """Best-effort mapping of an OKX subscribe error back to a requested channel."""
        msg = str(doc.get("msg", ""))
        for spec in self.config.channels:
            if f"channel:{spec.channel}," in msg and spec.inst_id in msg:
                return spec.key
        return None

    async def _connection_loop(self, connection: Connection, specs: list[ChannelSpec]) -> None:
        url = self.config.endpoints.ws_public_url if connection == Connection.PUBLIC else self.config.endpoints.ws_business_url
        backoff = self.config.reconnect_initial.total_seconds()
        ping_after = self.config.ping_interval.total_seconds()
        name = connection.value
        while not self._stop.is_set():
            self.stats.connection_state[name] = "connecting"
            self.writer.lifecycle("connecting", connection=connection, detail=url)
            try:
                conn = await asyncio.wait_for(self.ws_connect(url), 20)
            except Exception as exc:
                self.stats.connection_state[name] = "disconnected"
                self.stats.errors += 1
                self.writer.lifecycle("connect_failed", connection=connection, detail=f"{type(exc).__name__}: {exc}")
                self.writer.lifecycle("reconnect_scheduled", connection=connection, detail=f"in {backoff} s")
                await self._sleep(backoff)
                backoff = min(backoff * 2, self.config.reconnect_max.total_seconds())
                continue
            gen = self.stats.generation.get(name, 0) + 1
            self.stats.generation[name] = gen
            if gen > 1:
                self.stats.reconnects += 1
            self.stats.connection_state[name] = "connected"
            self.writer.lifecycle("connected", connection=connection, generation=gen, detail=url)
            args = [{"channel": s.channel, "instId": s.inst_id} for s in specs]
            reason = "stopped"
            try:
                await conn.send(json.dumps({"op": "subscribe", "args": args}))
                self.writer.lifecycle("subscribe_sent", connection=connection, generation=gen,
                                      detail=json.dumps(args))
                while not self._stop.is_set():
                    try:
                        text = await asyncio.wait_for(conn.recv(), ping_after)
                    except TimeoutError:
                        await conn.send("ping")
                        continue
                    # receipt time captured immediately after the read returns, before any parsing
                    recv_utc, recv_mono = self.clock.time_ns(), self.clock.monotonic_ns()
                    status, channel, inst, doc = self._classify(text)
                    rec = self.writer.record(kind="ws_message", connection=connection, generation=gen, endpoint=url,
                                             recv_utc_ns=recv_utc, recv_mono_ns=recv_mono, raw=text,
                                             parse_status=status, channel=channel, inst_id=inst)
                    self._count(rec)
                    if status == ParseStatus.EVENT and doc.get("event") == "subscribe" and channel:
                        key = f"{channel}:{inst}"
                        self.stats.subscribed.add(key)
                        self.writer.lifecycle("subscribed", connection=connection, generation=gen, channel=key)
                        backoff = self.config.reconnect_initial.total_seconds()
                    elif status == ParseStatus.ERROR:
                        self.stats.errors += 1
                        key = self._error_channel(doc)
                        self.writer.lifecycle("subscribe_error", connection=connection, generation=gen,
                                              channel=key, detail=text[:500])
                        spec = self._by_key.get(key or "")
                        if spec is not None and spec.family == ChannelFamily.FUNDING_LIVE:
                            self._start_funding_fallback(spec)
            except asyncio.CancelledError:
                reason = "cancelled"
                raise
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
            finally:
                self.stats.connection_state[name] = "closed" if self._stop.is_set() else "disconnected"
                self.stats.subscribed -= {s.key for s in specs}
                # a requested stop is a clean close, not a coverage outage
                self.writer.lifecycle("closed" if self._stop.is_set() else "disconnected", connection=connection,
                                      generation=gen, detail=reason)
                try:
                    await asyncio.wait_for(conn.close(), 3)
                except Exception:  # noqa: BLE001 - closing a broken socket must not mask the disconnect
                    pass
            if self._stop.is_set():
                break
            self.writer.lifecycle("reconnect_scheduled", connection=connection, generation=gen,
                                  detail=f"in {backoff} s; no messages are fabricated for the gap")
            await self._sleep(backoff)
            backoff = min(backoff * 2, self.config.reconnect_max.total_seconds())

    def _start_funding_fallback(self, spec: ChannelSpec) -> None:
        if self._fallback_started:
            return
        self._fallback_started = True
        self.stats.funding_fallback = True
        self.writer.lifecycle("fallback_enabled", connection=Connection.REST, channel=spec.key,
                              detail="WS funding channel unavailable; REST polling (POLL_OBSERVED availability)")
        self._tasks.append(asyncio.create_task(self._funding_poll_loop(spec)))

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), seconds)
        except TimeoutError:
            pass

    async def _control_loop(self) -> None:
        started = self.clock.monotonic_ns()
        limit = self.config.max_duration.total_seconds() * 1e9
        while not self._stop.is_set():
            if self.clock.monotonic_ns() - started >= limit:
                self.request_stop("max_duration reached")
                break
            if self.control is not None and await self.control(self.stats):
                self.request_stop("stop requested")
                break
            await self._sleep(self.control_interval)

    async def run(self) -> str:
        """Record until stopped (control hook, max duration or request_stop). Returns the stop reason."""
        self.writer.lifecycle("session_start", detail=json.dumps(
            {"endpoints": self.config.endpoints.model_dump(), "channels": [c.key for c in self.config.channels]}))
        await self._rest("/api/v5/public/instruments", {"instType": "SWAP", "instId": self.config.inst_id},
                         "instrument")
        by_conn: dict[Connection, list[ChannelSpec]] = {}
        for spec in self.config.channels:
            by_conn.setdefault(spec.connection, []).append(spec)
        self._tasks = [asyncio.create_task(self._connection_loop(c, s)) for c, s in by_conn.items()]
        self._tasks += [asyncio.create_task(self._clock_loop()), asyncio.create_task(self._control_loop())]
        await self._stop.wait()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self.writer.lifecycle("session_end", detail=self.stop_reason)
        self.writer.sync()
        return self.stop_reason
