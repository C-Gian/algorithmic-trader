"""Offline stand-ins for OKX public WebSocket/REST used by recorder tests.

Messages are delivered in global receipt-time order across connections and
set a fake wall/monotonic clock, so the recorder's receipt timestamps are
deterministic. Real captured messages live in tests/fixtures/okx_ws.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from algotrader.recorder.contracts import Endpoints
from algotrader.recorder.okx_live import Recorder, make_config
from algotrader.recorder.journal import SessionWriter

FIX = Path(__file__).parent / "fixtures"
PUBLIC = "wss://ws.test.invalid:8443/ws/v5/public"
BUSINESS = "wss://ws.test.invalid:8443/ws/v5/business"
REST = "https://rest.test.invalid"
ENDPOINTS = Endpoints(ws_public_url=PUBLIC, ws_business_url=BUSINESS, rest_base_url=REST)


def captured() -> list[dict]:
    return [json.loads(line) for line in (FIX / "okx_ws" / "session_messages.jsonl").read_text().splitlines()]


def captured_script(connection: str, drop_errors: bool = True) -> list[tuple]:
    out = []
    for r in captured():
        if r["connection"] != connection:
            continue
        if drop_errors and '"event":"error"' in r["raw"]:
            continue  # the capture also subscribed candle1m on /public; our recorder does not
        out.append(("msg", r["recv_utc_ns"], r["raw"]))
    return out


class FakeClock:
    def __init__(self, t_ns: int) -> None:
        self.t = t_ns
        self.m = 5_000_000_000

    def time_ns(self) -> int:
        return self.t

    def monotonic_ns(self) -> int:
        return self.m

    def advance_to(self, t_ns: int) -> None:
        self.m += max(0, t_ns - self.t)  # monotonic never goes back
        self.t = t_ns


@dataclass
class FakeNetwork:
    """scripts[url] = list of connection attempts; each attempt is a list of items or "refuse".

    Items: ("msg", recv_ns, text) | ("close", at_ns). An exhausted attempt stays open silently.
    """

    clock: FakeClock
    scripts: dict[str, list]
    expected: int = 2
    rest: dict[str, tuple[int, bytes]] = field(default_factory=dict)
    server_offset_ms: int = 0
    sent: list[tuple[str, str]] = field(default_factory=list)
    rest_calls: list[tuple[str, dict]] = field(default_factory=list)
    registered: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.cond = asyncio.Condition()
        self.live: dict[str, list] = {}

    @property
    def done(self) -> bool:
        return all(not a for a in self.scripts.values()) and all(not q for q in self.live.values())

    def _is_min(self, url: str, t: int) -> bool:
        if len(self.registered) < self.expected:
            return False
        for other, q in self.live.items():
            if other != url and q and (q[0][1], other) < (t, url):
                return False
        return True

    async def connect(self, url: str):
        attempts = self.scripts.get(url, [])
        if not attempts:
            await asyncio.Event().wait()  # no more attempts: hang (cancelled at stop)
        attempt = attempts.pop(0)
        if attempt == "refuse":
            raise ConnectionRefusedError(f"fake refuse {url}")
        self.registered.add(url)
        self.live[url] = list(attempt)
        net = self

        class Conn:
            async def send(self, text: str) -> None:
                net.sent.append((url, text))

            async def recv(self) -> str:
                async with net.cond:
                    while True:
                        q = net.live.get(url)
                        if q and net._is_min(url, q[0][1]):
                            break
                        await net.cond.wait()
                    item = q.pop(0)
                    net.cond.notify_all()
                net.clock.advance_to(item[1])
                if item[0] == "close":
                    raise ConnectionResetError("fake connection closed")
                return item[2]

            async def close(self) -> None:
                async with net.cond:
                    net.live[url] = []
                    net.cond.notify_all()

        return Conn()

    async def rest_get(self, url: str, headers: dict) -> tuple[int, bytes]:
        self.rest_calls.append((url, headers))
        for key, resp in self.rest.items():
            if key in url:
                return resp
        if "/api/v5/public/time" in url:
            return 200, json.dumps({"code": "0", "data": [{"ts": str(self.clock.t // 1_000_000 + self.server_offset_ms)}],
                                    "msg": ""}).encode()
        if "/api/v5/public/instruments" in url:
            return 200, (FIX / "okx" / "instrument.json").read_bytes()
        return 404, b'{"code":"50000","msg":"not found","data":[]}'


def record_session(tmp_path, scripts: dict, start_ns: int | None = None, rest: dict | None = None,
                   server_offset_ms: int = 0, session_id: str = "rec-test", expected: int = 2, **cfg):
    """Run a recorder over scripted connections until every script is consumed; returns (dir, net, stop_reason)."""
    first = min((i[1] for attempts in scripts.values() for a in attempts if a != "refuse" for i in a), default=0)
    clock = FakeClock(start_ns or first - 1_000_000)
    net = FakeNetwork(clock, {k: list(v) for k, v in scripts.items()}, expected=expected, rest=rest or {},
                      server_offset_ms=server_offset_ms)
    cfg.setdefault("reconnect_initial", timedelta(milliseconds=1))
    cfg.setdefault("reconnect_max", timedelta(milliseconds=2))
    cfg.setdefault("ping_interval", timedelta(seconds=20))
    config = make_config(session_id, endpoints=ENDPOINTS, max_duration=timedelta(hours=1), **cfg)
    writer = SessionWriter(tmp_path, config, clock)

    async def control(stats) -> bool:
        return net.done

    async def go():
        rec = Recorder(config, writer, clock, ws_connect=net.connect, rest_get=net.rest_get, control=control,
                       control_interval=0.001)
        return await rec.run()

    reason = asyncio.run(go())
    writer.close()
    return writer.dir, net, reason, clock
