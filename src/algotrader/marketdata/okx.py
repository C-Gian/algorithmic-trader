"""Read-only OKX public REST adapter (no credentials, no account/trade endpoints).

The adapter is split into a tiny transport (injectable; the live one uses
``urllib``) and a client that paces requests, retries safe GETs with bounded
backoff, validates the OKX envelope and keeps the exact response bytes for
provenance. Parsers turn the envelope ``data`` into market-data records; the
same parsers serve live access and offline tests.

OKX paging semantics (verified against the live API 2026-09-30):
``after=<ts>`` returns records strictly older than ``ts``, ``before=<ts>``
strictly newer, newest first, at most ``limit`` rows.
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from .. import __version__
from .contracts import (
    AVAILABILITY_POLICY_ID,
    Family,
    FundingRateEvent,
    IndexCandle1m,
    InstrumentSnapshot,
    MarkCandle1m,
    RowQuality,
    TradeCandle1m,
)

DEFAULT_BASE_URL = "https://www.okx.com"
# Regional domains documented by OKX (e.g. EEA users). Configure, never assume.
KNOWN_BASE_URLS = ("https://www.okx.com", "https://my.okx.com", "https://eea.okx.com")
USER_AGENT = f"algotrader-research/{__version__} (read-only public market data; paper research)"

ENDPOINTS: dict[Family, str] = {
    Family.INSTRUMENT: "/api/v5/public/instruments",
    Family.TRADE_CANDLES: "/api/v5/market/history-candles",
    Family.MARK_CANDLES: "/api/v5/market/history-mark-price-candles",
    Family.INDEX_CANDLES: "/api/v5/market/history-index-candles",
    Family.FUNDING: "/api/v5/public/funding-rate-history",
}
# Anything outside this allow-list is refused by the client (no account/trade access).
ALLOWED_PATHS = frozenset(ENDPOINTS.values())

RETRYABLE_HTTP = frozenset({429, 500, 502, 503, 504})
RETRYABLE_OKX_CODES = frozenset({"50011", "50013", "50026"})  # rate limit / busy / system error
BAR_MS = 60_000


class SourceError(Exception):
    """The source could not provide a valid response."""


class OkxApiError(SourceError):
    def __init__(self, code: str, msg: str, url: str) -> None:
        super().__init__(f"OKX error code {code}: {msg or '(no message)'} [{url}]")
        self.code, self.msg, self.url = code, msg, url


class MalformedResponse(SourceError):
    pass


class InstrumentIncompatible(SourceError):
    pass


class Transport(Protocol):
    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]: ...


def urllib_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:  # non-2xx still carries a body worth keeping
        return exc.code, exc.read()


@dataclass(frozen=True)
class RawResponse:
    base_url: str
    path: str
    params: dict[str, str]
    url: str
    http_status: int
    body: bytes
    retrieved_at: datetime
    code: str | None
    data: list[Any]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


class OkxPublicClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        transport: Transport = urllib_transport,
        timeout: float = 10.0,
        max_attempts: int = 4,
        backoff: float = 0.5,
        min_interval: float = 0.25,  # <= 4 requests/s, well under OKX public limits
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
            raise ValueError(f"base URL must be https://host, got {base_url!r}")
        self.base_url = f"https://{parsed.netloc}"
        self.transport = transport
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff = backoff
        self.min_interval = min_interval
        self.sleep = sleep
        self.monotonic = monotonic
        self.clock = clock
        self._last_request: float | None = None
        self.requests = 0

    def _pace(self) -> None:
        if self._last_request is not None:
            wait = self.min_interval - (self.monotonic() - self._last_request)
            if wait > 0:
                self.sleep(wait)
        self._last_request = self.monotonic()

    def get(self, path: str, params: dict[str, str]) -> RawResponse:
        """Safe GET with pacing and bounded retry. Raises SourceError subclasses."""
        if path not in ALLOWED_PATHS:
            raise ValueError(f"path {path} is not an allowed public market-data endpoint")
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}{path}?{query}"
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            if attempt > 1:
                self.sleep(self.backoff * 2 ** (attempt - 2))
            self._pace()
            self.requests += 1
            try:
                status, body = self.transport(url, headers, self.timeout)
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
                last_error = SourceError(f"network error for {url}: {exc}")
                continue
            retrieved_at = self.clock()
            if status in RETRYABLE_HTTP:
                last_error = SourceError(f"HTTP {status} for {url}")
                continue
            try:
                doc = json.loads(body)
            except ValueError:
                raise MalformedResponse(f"HTTP {status}: response is not JSON [{url}]") from None
            if not isinstance(doc, dict) or "code" not in doc:
                raise MalformedResponse(f"HTTP {status}: missing OKX envelope [{url}]")
            code = str(doc["code"])
            if code != "0":
                err = OkxApiError(code, str(doc.get("msg", "")), url)
                if code in RETRYABLE_OKX_CODES:
                    last_error = err
                    continue
                raise err
            if status != 200:
                raise MalformedResponse(f"HTTP {status} with OKX code 0 [{url}]")
            data = doc.get("data")
            if not isinstance(data, list):
                raise MalformedResponse(f"'data' is not a list [{url}]")
            return RawResponse(self.base_url, path, dict(params), url, status, body, retrieved_at, code, data)
        raise SourceError(f"giving up after {self.max_attempts} attempts: {last_error}")

    # -- endpoint helpers ---------------------------------------------------

    def instrument(self, inst_id: str) -> RawResponse:
        return self.get(ENDPOINTS[Family.INSTRUMENT], {"instType": "SWAP", "instId": inst_id})

    def history_page(
        self, family: Family, source_id: str, after_ms: int, before_ms: int, limit: int
    ) -> RawResponse:
        """One page of records with before_ms < t < after_ms, newest first."""
        params = {"instId": source_id}
        if family != Family.FUNDING:
            params["bar"] = "1m"
        params.update(after=str(after_ms), before=str(before_ms), limit=str(limit))
        return self.get(ENDPOINTS[family], params)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def ms_to_dt(value: Any) -> datetime:
    """Exact integer conversion of an OKX millisecond timestamp to UTC."""
    text = str(value)
    if not text.isdigit():
        raise MalformedResponse(f"bad millisecond timestamp {value!r}")
    return EPOCH + timedelta(milliseconds=int(text))


def dt_to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        raise ValueError("naive datetime; UTC required")
    return (dt - EPOCH) // timedelta(milliseconds=1)


def dec(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or value == "":
        raise MalformedResponse(f"{field}: expected a decimal string, got {value!r}")
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise MalformedResponse(f"{field}: not a decimal {value!r}") from None
    if not d.is_finite():
        raise MalformedResponse(f"{field}: not finite {value!r}")
    return d


def opt_dec(value: Any, field: str) -> Decimal | None:
    return None if value in (None, "") else dec(value, field)


def parse_instrument(resp: RawResponse, inst_id: str, page_ref: str) -> InstrumentSnapshot:
    """Validate that the source describes the requested linear perpetual; fail explicitly otherwise."""
    rows = [r for r in resp.data if isinstance(r, dict) and r.get("instId") == inst_id]
    if len(rows) != 1:
        raise InstrumentIncompatible(f"expected exactly one {inst_id} definition, got {len(rows)}")
    r = rows[0]
    problems = []
    if r.get("instType") != "SWAP":
        problems.append(f"instType={r.get('instType')!r} (expected SWAP)")
    if r.get("ctType") != "linear":
        problems.append(f"ctType={r.get('ctType')!r} (expected linear)")
    if r.get("expTime") not in (None, ""):
        problems.append(f"expTime={r.get('expTime')!r} (a perpetual has no expiry)")
    uly = r.get("uly") or ""
    family = r.get("instFamily") or uly
    parts = family.split("-")
    if len(parts) != 2 or not all(parts):
        problems.append(f"instFamily/uly={family!r} is not BASE-QUOTE")
        parts = ["", ""]
    if r.get("ctValCcy") != parts[0]:
        problems.append(f"ctValCcy={r.get('ctValCcy')!r} differs from base currency {parts[0]!r}")
    for field in ("ctVal", "tickSz", "lotSz", "minSz"):
        try:
            if dec(r.get(field), field) <= 0:
                problems.append(f"{field} must be positive")
        except MalformedResponse as exc:
            problems.append(str(exc))
    if not r.get("settleCcy"):
        problems.append("settleCcy missing")
    if problems:
        raise InstrumentIncompatible(f"{inst_id}: incompatible instrument definition: " + "; ".join(problems))
    return InstrumentSnapshot(
        inst_id=inst_id,
        inst_type="SWAP",
        ct_type="linear",
        underlying=uly,
        inst_family=family,
        index_id=uly or family,
        base_ccy=parts[0],
        quote_ccy=parts[1],
        ct_val=dec(r["ctVal"], "ctVal"),
        ct_val_ccy=r["ctValCcy"],
        ct_mult=opt_dec(r.get("ctMult"), "ctMult") or Decimal(1),
        settle_ccy=r["settleCcy"],
        tick_sz=dec(r["tickSz"], "tickSz"),
        lot_sz=dec(r["lotSz"], "lotSz"),
        min_sz=dec(r["minSz"], "minSz"),
        state=str(r.get("state", "")),
        list_time=ms_to_dt(r["listTime"]) if r.get("listTime") else None,
        advertised_max_leverage=r.get("lever") or None,
        retrieved_at=resp.retrieved_at,
        raw_page_ref=page_ref,
        raw_sha256=resp.sha256,
    )


@dataclass(frozen=True)
class ParsedRow:
    """A candle/funding record plus what the source said, before interval filtering."""

    key_ms: int
    confirmed: bool
    record: Any  # TradeCandle1m | MarkCandle1m | IndexCandle1m | FundingRateEvent | None
    raw: Any


def _row_flags(o: Decimal, h: Decimal, low: Decimal, c: Decimal, key_ms: int, volumes: dict[str, Decimal]) -> list[str]:
    flags = []
    if min(o, h, low, c) <= 0:
        flags.append("nonpositive_price")
    if h < max(o, c, low) or low > min(o, c, h):
        flags.append("ohlc_inconsistent")
    if key_ms % BAR_MS:
        flags.append("misaligned_open_time")
    flags += [f"negative_{k}" for k, v in volumes.items() if v < 0]
    return flags


def parse_candle(
    family: Family, row: Any, inst: InstrumentSnapshot, retrieved_at: datetime, page_ref: str
) -> ParsedRow:
    """Parse one candle row. Unconfirmed candles are returned with record=None."""
    width = 9 if family == Family.TRADE_CANDLES else 6
    if not isinstance(row, list) or len(row) < width:
        raise MalformedResponse(f"{family}: expected a list of >= {width} fields, got {row!r}")
    open_time = ms_to_dt(row[0])
    key_ms = int(str(row[0]))
    confirm = str(row[width - 1])
    if confirm not in ("0", "1"):
        raise MalformedResponse(f"{family}: bad confirm flag {confirm!r}")
    if confirm == "0":  # still forming: never a completed historical bar
        return ParsedRow(key_ms, False, None, row)
    close_time = open_time + timedelta(milliseconds=BAR_MS)
    o, h, low, c = (dec(row[i], f"{family}[{i}]") for i in range(1, 5))
    volumes: dict[str, Decimal] = {}
    if family == Family.TRADE_CANDLES:
        volumes = {
            "volume_contracts": dec(row[5], "vol"),
            "volume_base": dec(row[6], "volCcy"),
            "volume_quote": dec(row[7], "volCcyQuote"),
        }
    flags = tuple(_row_flags(o, h, low, c, key_ms, volumes))
    common = dict(
        instrument_id=inst.inst_id,
        open_time=open_time,
        close_time=close_time,
        open=o,
        high=h,
        low=low,
        close=c,
        confirm=True,
        available_time=close_time,  # modeling policy: never before the bar closes
        availability_policy=AVAILABILITY_POLICY_ID,
        retrieved_at=retrieved_at,
        raw_page_ref=page_ref,
        quality=RowQuality.INVALID if flags else RowQuality.OK,
        quality_flags=flags,
    )
    if family == Family.TRADE_CANDLES:
        rec: Any = TradeCandle1m(
            **common, **volumes, volume_base_ccy=inst.base_ccy, volume_quote_ccy=inst.quote_ccy
        )
    elif family == Family.MARK_CANDLES:
        rec = MarkCandle1m(**common)
    else:
        rec = IndexCandle1m(**common, index_id=inst.index_id)
    return ParsedRow(key_ms, True, rec, row)


def parse_funding(row: Any, inst: InstrumentSnapshot, retrieved_at: datetime, page_ref: str) -> ParsedRow:
    if not isinstance(row, dict) or "fundingTime" not in row or "fundingRate" not in row:
        raise MalformedResponse(f"funding: unexpected row {row!r}")
    if row.get("instId") != inst.inst_id:
        raise MalformedResponse(f"funding: row for {row.get('instId')!r}, expected {inst.inst_id}")
    t = ms_to_dt(row["fundingTime"])
    rec = FundingRateEvent(
        instrument_id=inst.inst_id,
        inst_type=str(row.get("instType", "")),
        funding_time=t,
        funding_rate=dec(row["fundingRate"], "fundingRate"),
        realized_rate=opt_dec(row.get("realizedRate"), "realizedRate"),
        method=row.get("method") or None,
        formula_type=row.get("formulaType") or None,
        available_time=t,  # never smeared before the source event time
        availability_policy=AVAILABILITY_POLICY_ID,
        retrieved_at=retrieved_at,
        raw_page_ref=page_ref,
    )
    return ParsedRow(dt_to_ms(t), True, rec, row)


def source_id_for(family: Family, inst: InstrumentSnapshot) -> str:
    return inst.index_id if family == Family.INDEX_CANDLES else inst.inst_id
