"""Public live-recorder session contracts (``algotrader.recorder.v1``, PROVISIONAL).

Operational/provenance records for prospective public recording. Separate from
``algotrader.semantic.v1``, ``algotrader.marketdata.v1`` and the causal
``algotrader.feed.v1`` (a pure bridge turns recorded sessions into feed.v1
RECORDED events). No trading, sizing, account or order semantics.

Timing vocabulary (never collapsed):

* source market/event time - timestamps inside the source payload (bar open,
  fundingTime, ...);
* source data-return time - a source-supplied response/push timestamp such as
  the funding channel ``ts`` or the REST server-time ``ts``;
* local receipt time - ``recv_utc_ns``: host UTC wall clock read immediately
  after the recorder's read of the message returns. It is the *client-observed*
  receipt instant, never the exchange publication instant;
* local monotonic time - ``recv_mono_ns`` plus the in-session ``seq`` keep local
  receipt order even if the wall clock steps.

PROVISIONAL during M3: a contract change must bump RECORDER_SCHEMA_REVISION,
add a RECORDER_CHANGELOG entry and be Director-approved.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RECORDER_SCHEMA_VERSION = "algotrader.recorder.v1"
RECORDER_CONTRACT_STATUS = "PROVISIONAL"
RECORDER_SCHEMA_REVISION = 1
RECORDER_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-09-30", "Initial provisional baseline (WP-005): session config/manifest, journal and lifecycle "
                      "records, clock observations, measured-availability report."),
)
CLOCK_SOURCE = (
    "host UTC wall clock (time.time_ns) for recv_utc_ns; process monotonic clock (time.monotonic_ns) for "
    "recv_mono_ns; neither is corrected. Offset versus the OKX public server-time endpoint is observed "
    "separately (ClockObservation)."
)
RECEIPT_POINT = (
    "recv_utc_ns is taken immediately after the recorder's read of a message from the WebSocket client "
    "(or of a complete REST response) returns, before parsing. It includes network, TLS/WebSocket-library "
    "buffering and scheduling delay; it is not the exchange publication time."
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Connection(StrEnum):
    PUBLIC = "public"  # OKX public WS endpoint (e.g. funding-rate)
    BUSINESS = "business"  # OKX business WS endpoint (candle channels)
    REST = "rest"  # public REST (server time, instrument, polling fallback)


class ChannelFamily(StrEnum):
    TRADE_BAR_1M = "trade_bar_1m"
    MARK_BAR_1M = "mark_bar_1m"
    INDEX_BAR_1M = "index_bar_1m"
    FUNDING_LIVE = "funding_live"  # evolving pre-settlement funding information (NOT settlements)


class ChannelSpec(Record):
    family: ChannelFamily
    channel: str  # OKX channel name, e.g. "candle1m"
    inst_id: str  # OKX instId in the subscription (index id for index candles)
    connection: Connection

    @property
    def key(self) -> str:
        return f"{self.channel}:{self.inst_id}"


class Endpoints(Record):
    ws_public_url: str
    ws_business_url: str
    rest_base_url: str


class SessionConfig(Record):
    session_id: str
    source: Literal["okx"] = "okx"
    inst_id: str
    index_id: str
    endpoints: Endpoints
    channels: tuple[ChannelSpec, ...]
    max_duration: timedelta = Field(gt=timedelta(0))
    ping_interval: timedelta  # OKX closes idle connections after 30 s; a text "ping" is sent before that
    clock_probe_interval: timedelta
    fsync_interval: timedelta  # upper bound on data a power loss/OS crash can drop
    reconnect_initial: timedelta
    reconnect_max: timedelta
    funding_poll_interval: timedelta  # REST fallback cadence if the WS funding channel is unavailable
    completion_grace: timedelta  # report: how long after bar end a completion is expected while healthy
    segment_max_bytes: int = Field(gt=0)


class ParseStatus(StrEnum):
    DATA = "data"
    EVENT = "event"  # subscribe/unsubscribe/notice acknowledgements
    ERROR = "error"  # source error event
    PONG = "pong"
    UNPARSED = "unparsed"  # retained raw, not understood


class JournalRecord(Record):
    """One raw source message/response, exactly as received, with local receipt timing."""

    seq: int  # contiguous from 1 within the session
    kind: Literal["ws_message", "rest_response"]
    connection: Connection
    generation: int  # connection generation (increments on every (re)connect); 0 for REST
    endpoint: str
    recv_utc_ns: int
    recv_mono_ns: int
    raw: str  # exact message text
    raw_sha256: str
    parse_status: ParseStatus
    channel: str | None = None
    inst_id: str | None = None
    # REST only: request timing and polling policy (poll-observed availability bounds)
    request_sent_utc_ns: int | None = None
    request_sent_mono_ns: int | None = None
    purpose: str | None = None  # e.g. "server_time", "instrument", "funding_poll_fallback"
    poll_interval_s: float | None = None
    previous_observation_utc_ns: int | None = None


class LifecycleEvent(Record):
    seq: int
    at_utc_ns: int
    at_mono_ns: int
    event: str  # session_start, connecting, connected, subscribe_sent, subscribed, subscribe_error,
    #             disconnected, reconnect_scheduled, fallback_enabled, stop_requested, session_end, recovered...
    connection: Connection | None = None
    generation: int | None = None
    channel: str | None = None
    detail: str = ""


class ClockObservation(Record):
    at_utc_ns: int  # local receipt of the server-time response
    request_sent_utc_ns: int
    request_sent_mono_ns: int
    response_mono_ns: int
    server_ts_ms: int | None  # OKX public server time (ms), None if unavailable
    rtt_ns: int  # monotonic round trip
    offset_estimate_ns: int | None  # server_time - local midpoint (positive: local clock behind source)
    offset_bound_ns: int | None  # +/- rtt/2 + 1 ms server timestamp resolution
    status: Literal["ok", "unavailable"]
    detail: str = ""


class SessionStatus(StrEnum):
    CLEAN = "clean"  # all requested channels subscribed; no disconnects or errors
    PARTIAL = "partial"  # usable evidence with outages/errors/missing channels, or recovered after a crash
    FAILED = "failed"  # no usable market data recorded


class FileRef(Record):
    name: str
    sha256: str
    bytes: int
    lines: int | None


class ChannelReceipt(Record):
    channel_key: str
    family: ChannelFamily
    subscribed: bool
    records: int
    first_recv_utc: datetime | None
    last_recv_utc: datetime | None


class DelaySummary(Record):
    """Bar end -> first completed receipt, in seconds, on the raw local clock."""

    count: int
    min_s: float | None
    p50_s: float | None
    p90_s: float | None
    max_s: float | None
    mean_s: float | None
    negative_count: int  # completion received before bar end on the local clock (clock issue / impossible)


class Interval(Record):
    start: datetime
    end: datetime | None
    connection: Connection | None
    detail: str


class BarChannelReport(Record):
    channel_key: str
    family: ChannelFamily
    updates: int  # all data rows received (forming + completed + repeats)
    forming_updates: int
    completed_bars: int  # distinct bars with a completed receipt
    duplicate_completed: int  # identical completed rows received again after first completion
    post_completion_changes: int  # completed rows with different values after first completion (kept raw)
    out_of_order_updates: int  # rows for a bar older than the newest bar already seen
    delay_raw: DelaySummary
    delay_offset_adjusted: DelaySummary | None  # raw + median observed clock offset (estimate)
    missing_completions_while_healthy: tuple[datetime, ...]  # bar open times


class FundingReport(Record):
    snapshots_ws: int
    snapshots_poll: int  # REST fallback, POLL_OBSERVED
    distinct_funding_times: tuple[datetime, ...]
    funding_time_transitions: tuple[str, ...]  # settlement-boundary observations (descriptive only)
    fields_seen: tuple[str, ...]


class ClockReport(Record):
    observations: int
    ok_observations: int
    offset_estimate_ms_min: float | None
    offset_estimate_ms_median: float | None
    offset_estimate_ms_max: float | None
    rtt_ms_median: float | None
    clock_quality: Literal["observed", "unknown"]


class SessionReport(Record):
    schema_version: str
    session_id: str
    status: SessionStatus
    duration_s: float
    receipt_point: str
    note: str
    channels: tuple[ChannelReceipt, ...]
    bars: tuple[BarChannelReport, ...]
    funding: FundingReport
    clock: ClockReport
    outages: tuple[Interval, ...]  # disconnect -> resubscribe intervals (recorder coverage loss, not market gaps)
    unusable_timing_periods: tuple[Interval, ...]
    errors: tuple[str, ...]


class SessionManifest(Record):
    schema_version: str
    contract_status: str
    schema_revision: int
    session_id: str
    status: SessionStatus
    labels: tuple[str, ...]
    source: str
    inst_id: str
    index_id: str
    endpoints: Endpoints
    config: SessionConfig
    started_at: datetime
    stopped_at: datetime
    stop_reason: str
    recovered_after_crash: bool
    code_version: str | None
    host: str
    pid: int
    clock_source: str
    receipt_point: str
    channels_requested: tuple[str, ...]
    channels_subscribed: tuple[str, ...]
    connections: int  # successful connections (all generations)
    reconnects: int
    errors: int
    record_count: int
    lifecycle_count: int
    clock_observation_count: int
    fsync_policy: str
    files: tuple[FileRef, ...]


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (
    SessionConfig,
    JournalRecord,
    LifecycleEvent,
    ClockObservation,
    SessionReport,
    SessionManifest,
)
