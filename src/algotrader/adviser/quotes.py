"""Narrow read-only public quote client (WP-009 live current practicability).

Exactly one public GET: ``/api/v5/market/ticker?instId=BTC-USDT-SWAP`` on a validated official OKX REST host (same
source-authority rule as the historical client and the recorder). No credentials, no account/trade path, no other
endpoint. Per the official v5 documentation consulted by the Director on 2026-10-03 the ticker returns ``bidPx`` /
``askPx`` and a generation timestamp ``ts`` and may be served from independent caches that return older snapshots;
this client therefore validates every snapshot and never lets a repeated/older snapshot refresh its age.

Polling is an engineering transport convention: at most one request per second, bounded retry/backoff, never
overlapping requests (single sequential poller). A failure yields NO quote (disconnected/UNVERIFIED downstream),
never a manufactured one, and never a candle/midpoint substitute.
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from ..marketdata.okx import USER_AGENT, urllib_transport
from ..marketdata.okx_authority import validate_okx_rest_base_url
from .core import Quote

TICKER_PATH = "/api/v5/market/ticker"
ALLOWED_PATHS = frozenset({TICKER_PATH})
MIN_INTERVAL = 1.0  # <= 1 request/second
FUTURE_TOLERANCE = timedelta(seconds=1)  # source generation time may not be after local receipt by more than this
STALE_AFTER = timedelta(seconds=5)


class QuoteRejected(Exception):
    """A response or snapshot that must not become a quote (reason in the message)."""


@dataclass
class QuoteStats:
    requests: int = 0
    accepted: int = 0
    rejected: int = 0
    not_newer: int = 0
    errors: int = 0
    last_error: str | None = None
    last_reject: str | None = None

    def doc(self) -> dict:
        return dict(self.__dict__)


def parse_ticker(body: bytes, inst_id: str, received_at: datetime, last_ts: datetime | None) -> Quote:
    """Validate one ticker response into a Quote (raises QuoteRejected)."""
    try:
        doc = json.loads(body)
    except ValueError:
        raise QuoteRejected("response is not JSON") from None
    if not isinstance(doc, dict) or str(doc.get("code")) != "0":
        raise QuoteRejected(f"OKX error envelope code {doc.get('code') if isinstance(doc, dict) else '?'}")
    data = doc.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise QuoteRejected("ticker data must be exactly one object")
    d = data[0]
    if d.get("instId") != inst_id:
        raise QuoteRejected(f"instrument {d.get('instId')!r} is not {inst_id}")
    try:
        bid, ask = Decimal(str(d["bidPx"])), Decimal(str(d["askPx"]))
        ts = datetime.fromtimestamp(int(d["ts"]) / 1000, tz=UTC)
    except (KeyError, InvalidOperation, ValueError, TypeError):
        raise QuoteRejected("missing or malformed bidPx/askPx/ts") from None
    if bid <= 0 or ask <= 0:
        raise QuoteRejected("nonpositive bid/ask")
    if bid > ask:
        raise QuoteRejected("crossed quote (bid > ask)")
    if ts > received_at + FUTURE_TOLERANCE:
        raise QuoteRejected("source generation time is in the future relative to local receipt (clock uncertain)")
    if last_ts is not None and ts < last_ts:
        raise QuoteRejected("older snapshot than the last accepted one (independent cache)")
    if last_ts is not None and ts == last_ts:
        raise QuoteRejected("NOT_NEWER: same snapshot repeated; its age is not refreshed")
    return Quote(bid=bid, ask=ask, source_ts=ts, received_at=received_at, inst_id=inst_id,
                 raw_sha256=hashlib.sha256(body).hexdigest())


class QuoteClient:
    def __init__(self, base_url: str = "https://www.okx.com", inst_id: str = "BTC-USDT-SWAP", *,
                 transport=urllib_transport, timeout: float = 4.0, max_attempts: int = 2, backoff: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep, monotonic: Callable[[], float] = time.monotonic,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        parsed = validate_okx_rest_base_url(base_url)  # official OKX host only; never rewritten
        self.base_url = f"https://{parsed.netloc}"
        self.inst_id = inst_id
        self.transport, self.timeout, self.max_attempts, self.backoff = transport, timeout, max_attempts, backoff
        self.sleep, self.monotonic, self.clock = sleep, monotonic, clock
        self._last_request: float | None = None
        self.last_ts: datetime | None = None
        self.stats = QuoteStats()

    def url(self) -> str:
        return f"{self.base_url}{TICKER_PATH}?{urllib.parse.urlencode({'instId': self.inst_id})}"

    def _pace(self) -> None:
        if self._last_request is not None:
            wait = MIN_INTERVAL - (self.monotonic() - self._last_request)
            if wait > 0:
                self.sleep(wait)
        self._last_request = self.monotonic()

    def poll(self) -> Quote | None:
        """One sequential poll (paced, bounded retry). Returns an accepted Quote or None (never a fabricated one)."""
        url = self.url()
        assert urllib.parse.urlsplit(url).path in ALLOWED_PATHS
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        for attempt in range(1, self.max_attempts + 1):
            if attempt > 1:
                self.sleep(self.backoff * 2 ** (attempt - 2))
            self._pace()
            self.stats.requests += 1
            try:
                status, body = self.transport(url, headers, self.timeout)
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
                self.stats.errors += 1
                self.stats.last_error = f"network: {exc}"
                continue
            received = self.clock()
            if status != 200:
                self.stats.errors += 1
                self.stats.last_error = f"HTTP {status}"
                if status in (429, 500, 502, 503, 504):
                    continue
                return None
            try:
                q = parse_ticker(body, self.inst_id, received, self.last_ts)
            except QuoteRejected as exc:
                if str(exc).startswith("NOT_NEWER"):
                    self.stats.not_newer += 1
                else:
                    self.stats.rejected += 1
                self.stats.last_reject = str(exc)
                return None
            self.last_ts = q.source_ts
            self.stats.accepted += 1
            return q
        return None
