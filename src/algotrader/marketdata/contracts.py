"""Market-data contracts (``algotrader.marketdata.v1``).

Versioned separately from the frozen trader contracts (``algotrader.semantic.v1``).
These records describe *source evidence*: what a public market-data source
returned, when it was retrieved, and how it was normalized. They carry no
trading interpretation.

Time semantics are kept in distinct, explicitly named fields:

* ``open_time`` / ``close_time`` / ``funding_time`` - market event time
  reported by (or computed from) the source;
* ``available_time`` - *modeled* earliest availability under a named
  ``availability_policy``. OKX does not publish a historical publication
  timestamp per bar, so this is a modeling convention, never a measurement;
* ``retrieved_at`` - when this application fetched the source page
  (provenance only).

Prices, rates and volumes are ``Decimal`` parsed from the source strings,
never binary floats. Normalized Parquet stores them as the exact source
decimal strings.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MARKETDATA_SCHEMA_VERSION = "algotrader.marketdata.v1"

# Completed 1m bars are modeled as available at their bar close. This is a
# modeling policy (OKX gives no historical publication timestamp per bar).
AVAILABILITY_POLICY_ID = "okx.completed_1m_bar_available_at_close.v1"
AVAILABILITY_POLICY_TEXT = (
    "MODELING POLICY, not a measured publication fact: a confirmed (confirm=1) 1m candle is "
    "treated as available no earlier than its bar close (open_time + 60s). A funding-rate "
    "event is treated as available no earlier than its source funding_time. Unconfirmed "
    "candles (confirm=0) are never normalized as completed bars."
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Family(StrEnum):
    """In-scope source data families."""

    INSTRUMENT = "instrument"
    TRADE_CANDLES = "trade_candles_1m"
    MARK_CANDLES = "mark_candles_1m"
    INDEX_CANDLES = "index_candles_1m"
    FUNDING = "funding_rates"


HISTORICAL_FAMILIES = (Family.TRADE_CANDLES, Family.MARK_CANDLES, Family.INDEX_CANDLES, Family.FUNDING)
CANDLE_FAMILIES = (Family.TRADE_CANDLES, Family.MARK_CANDLES, Family.INDEX_CANDLES)


class RowQuality(StrEnum):
    OK = "OK"
    INVALID = "INVALID"  # kept for evidence; see quality_flags; unusable downstream


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class RawPageRef(Record):
    """One source HTTP response, stored byte-for-byte."""

    page_id: str  # e.g. "trade_candles_1m/0003"
    family: Family
    method: Literal["GET"] = "GET"
    base_url: str
    path: str
    params: dict[str, str]
    retrieved_at: datetime
    http_status: int
    source_code: str | None  # OKX "code" field
    rows: int
    sha256: str
    bytes: int
    file: str  # path inside the dataset directory


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


class InstrumentSnapshot(Record):
    """Normalized source definition of the perpetual contract at retrieval time."""

    source: Literal["okx"] = "okx"
    inst_id: str
    inst_type: Literal["SWAP"]
    ct_type: Literal["linear"]
    underlying: str  # uly
    inst_family: str
    index_id: str  # index series used for index candles (from the source, not hard-coded)
    base_ccy: str  # derived from the instrument family; equals ct_val_ccy
    quote_ccy: str  # derived from the instrument family
    ct_val: Decimal  # contract value ...
    ct_val_ccy: str  # ... in this currency (BTC per contract)
    ct_mult: Decimal
    settle_ccy: str
    tick_sz: Decimal
    lot_sz: Decimal
    min_sz: Decimal
    state: str
    list_time: datetime | None
    # Venue metadata only. Never alters the project's hard 1x exposure rule.
    advertised_max_leverage: str | None
    retrieved_at: datetime
    raw_page_ref: str
    raw_sha256: str


# ---------------------------------------------------------------------------
# Normalized market records
# ---------------------------------------------------------------------------


class _Candle(Record):
    instrument_id: str
    bar: Literal["1m"] = "1m"
    open_time: datetime  # source timestamp (bar open)
    close_time: datetime  # open_time + 60 s (computed)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    confirm: bool  # always True in a completed-bar dataset
    available_time: datetime  # modeled; see availability_policy
    availability_policy: str
    retrieved_at: datetime  # provenance only
    raw_page_ref: str
    quality: RowQuality
    quality_flags: tuple[str, ...] = ()


class TradeCandle1m(_Candle):
    """Traded-price candle. Volume units are preserved separately."""

    volume_contracts: Decimal  # OKX "vol": number of contracts
    volume_base: Decimal  # OKX "volCcy": base currency amount (see volume_base_ccy)
    volume_base_ccy: str
    volume_quote: Decimal  # OKX "volCcyQuote": quote currency amount
    volume_quote_ccy: str


class MarkCandle1m(_Candle):
    """Mark-price candle (no volume in the source)."""


class IndexCandle1m(_Candle):
    """Index-price candle (no volume in the source)."""

    index_id: str


class FundingRateEvent(Record):
    """A source funding event. Not applied to any account in this version."""

    instrument_id: str
    inst_type: str
    funding_time: datetime  # source event time
    funding_rate: Decimal
    realized_rate: Decimal | None
    method: str | None
    formula_type: str | None
    available_time: datetime  # modeled: never before funding_time
    availability_policy: str
    retrieved_at: datetime
    raw_page_ref: str


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    INFO = "info"  # no effect on usability
    WARNING = "warning"  # noted; data remains usable
    DEGRADED = "degraded"  # usable only with explicit handling (e.g. gaps)
    INVALID = "invalid"  # affected records must not be used


class QualityStatus(StrEnum):
    CLEAN = "clean"
    WARNING = "warning"
    DEGRADED = "degraded"
    INVALID = "invalid"


class QualityFinding(Record):
    family: Family
    check: str
    severity: Severity
    count: int
    detail: str
    examples: tuple[str, ...] = ()


class Gap(Record):
    first_missing_open_time: datetime
    last_missing_open_time: datetime
    missing_bars: int


class FamilyQuality(Record):
    family: Family
    status: QualityStatus
    rows: int
    expected_rows: int | None  # for 1m candles: minutes in the requested interval
    missing_rows: int | None
    first_time: datetime | None
    last_time: datetime | None
    gaps: tuple[Gap, ...] = ()


class QualityReport(Record):
    schema_version: str
    dataset_id: str
    status: QualityStatus
    scope_note: str
    families: tuple[FamilyQuality, ...]
    findings: tuple[QualityFinding, ...]


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class DatasetRequest(Record):
    """The logical request. Its hash identifies 'the same request' across fetches."""

    source: Literal["okx"] = "okx"
    base_url: str
    inst_id: str
    bar: Literal["1m"] = "1m"
    start: datetime  # inclusive, UTC, minute-aligned
    end: datetime  # exclusive, UTC, minute-aligned
    families: tuple[Family, ...]
    page_limit: int = Field(ge=1, le=100)


class FileRef(Record):
    name: str  # path inside the dataset directory
    sha256: str
    bytes: int
    rows: int | None
    media_type: str


class FamilySummary(Record):
    family: Family
    endpoint: str
    rows: int
    pages: int
    first_time: datetime | None
    last_time: datetime | None
    rejected_incomplete: int
    outside_interval: int


class DatasetManifest(Record):
    schema_version: str
    dataset_id: str
    logical_request_key: str
    labels: tuple[str, ...]
    request: DatasetRequest
    instrument: InstrumentSnapshot
    availability_policy: str
    availability_policy_text: str
    retrieval_started_at: datetime
    retrieval_finished_at: datetime
    code_version: str | None
    families: tuple[FamilySummary, ...]
    quality_status: QualityStatus
    raw_page_count: int
    identity_basis: str
    prior_versions: tuple[str, ...]  # earlier datasets for the same logical request with different content
    files: tuple[FileRef, ...]


RECORD_CONTRACTS: tuple[type[Record], ...] = (
    InstrumentSnapshot,
    TradeCandle1m,
    MarkCandle1m,
    IndexCandle1m,
    FundingRateEvent,
    RawPageRef,
    QualityReport,
    DatasetManifest,
)
