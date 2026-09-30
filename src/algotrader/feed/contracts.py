"""Causal feed and observable-state contracts (``algotrader.feed.v1``, PROVISIONAL).

Separate from the frozen ``algotrader.semantic.v1`` (synthetic shell) and
``algotrader.marketdata.v1`` (source evidence). This namespace describes how
source evidence becomes *known* to the system (availability events) and the
point-in-time observable market state built from those events. It carries no
professional interpretation, prediction, recommendation, sizing or P&L.

PROVISIONAL during M3: controlled breaking changes remain possible until M3
acceptance. Any change to these contracts must bump ``FEED_SCHEMA_REVISION``,
add an entry to ``FEED_CHANGELOG`` and be approved by the Director in a task.
The checked-in baseline ``schemas/algotrader.feed.v1.json`` records the
revision; the schema tool refuses to rewrite it without a revision bump.

Time fields are kept distinct everywhere:

* ``event_time`` / ``event_end_time`` - market/economic time of the evidence
  (for a 1m bar: its open and close; for funding: the settlement time);
* ``available_time`` - when the system may know the event, under a named
  availability policy with an explicit ``availability_basis``;
* ``SourceRef.retrieved_at`` - provenance (when the evidence was fetched).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

FEED_SCHEMA_VERSION = "algotrader.feed.v1"
FEED_CONTRACT_STATUS = "PROVISIONAL"
FEED_SCHEMA_REVISION = 1
FEED_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-09-30", "Initial provisional baseline (WP-004): availability events, ordering key, "
                      "channel snapshots, observable snapshot and delta."),
)

ORDERING_POLICY_ID = "feed.order.availability-family-series-time-kind.v1"
ORDERING_POLICY_TEXT = (
    "Deterministic replay convention, not a claim about true exchange micro-order: events are "
    "totally ordered by (available_time, family rank [trade, mark, index, funding], series id, "
    "event_time, kind rank [observation, quality], event_id). Input file, page or database order "
    "never affects the result. At most one event may exist per (channel, slot)."
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


class Family(StrEnum):
    """Role-specific source families. No generic 'price' channel exists."""

    TRADE_BAR_1M = "trade_bar_1m"  # what traded (OHLC + typed volumes)
    MARK_BAR_1M = "mark_bar_1m"  # venue mark price (valuation/reference), not an execution price
    INDEX_BAR_1M = "index_bar_1m"  # external index/reference, not an execution price
    FUNDING_SETTLEMENT = "funding_settlement"  # sparse settled funding events (carry evidence)


FAMILY_RANK: dict[Family, int] = {
    Family.TRADE_BAR_1M: 0,
    Family.MARK_BAR_1M: 1,
    Family.INDEX_BAR_1M: 2,
    Family.FUNDING_SETTLEMENT: 3,
}
BAR_FAMILIES = frozenset({Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M})


class ChannelRef(Record):
    source: str  # e.g. "okx"
    family: Family
    series_id: str  # instrument id, or index id for the index family

    @property
    def channel_id(self) -> str:
        return f"{self.source}/{self.series_id}/{self.family.value}"


class ChannelCoverage(Record):
    """Event-time window for which the evidence package can speak about this channel."""

    channel: ChannelRef
    covered_from: datetime  # inclusive event time
    covered_until: datetime  # exclusive event time
    expected_cadence: timedelta | None  # 1m for bars; None for sparse funding (schedule not assumed)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventKind(StrEnum):
    BAR_OBSERVATION = "bar_observation"  # a valid completed bar
    FUNDING_OBSERVATION = "funding_observation"  # a sparse settled funding event
    SLOT_QUALITY = "slot_quality"  # missing / invalid / rejected evidence for a bar slot


KIND_RANK: dict[EventKind, int] = {
    EventKind.BAR_OBSERVATION: 0,
    EventKind.FUNDING_OBSERVATION: 0,
    EventKind.SLOT_QUALITY: 1,
}


class AvailabilityBasis(StrEnum):
    MODELED = "MODELED"  # historical evidence with unknown publication latency
    RECORDED = "RECORDED"  # actual recorded receipt time (live recorder; not produced in WP-004)


class QualityReason(StrEnum):
    MISSING = "MISSING"  # no source record for the slot
    INVALID_ROW = "INVALID_ROW"  # record exists but failed validity checks
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"  # source returned different values for the slot
    INCOMPLETE_REJECTED = "INCOMPLETE_REJECTED"  # only an unconfirmed (confirm=0) record existed
    EXCLUDED_UNCLASSIFIED = "EXCLUDED_UNCLASSIFIED"  # absent from normalized data for an unknown reason


REJECTED_REASONS = frozenset(
    {QualityReason.INVALID_ROW, QualityReason.CONFLICTING_DUPLICATE, QualityReason.INCOMPLETE_REJECTED,
     QualityReason.EXCLUDED_UNCLASSIFIED}
)


class SourceRef(Record):
    """Provenance of the evidence behind an event. Excluded from market-content digests."""

    dataset_id: str  # acquisition/evidence package identity (WP-003)
    artifact: str  # normalized artifact or raw page inside the package
    row_index: int | None
    raw_page_ref: str | None
    retrieved_at: datetime | None
    source_availability_policy: str  # the marketdata.v1 modeling policy the feed started from


class TradeBarPayload(Record):
    payload_type: Literal["trade_bar_1m"] = "trade_bar_1m"
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume_contracts: Decimal
    volume_base: Decimal
    volume_base_ccy: str
    volume_quote: Decimal
    volume_quote_ccy: str


class MarkBarPayload(Record):
    payload_type: Literal["mark_bar_1m"] = "mark_bar_1m"
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


class IndexBarPayload(Record):
    payload_type: Literal["index_bar_1m"] = "index_bar_1m"
    index_id: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


class FundingPayload(Record):
    payload_type: Literal["funding_settlement"] = "funding_settlement"
    funding_rate: Decimal
    realized_rate: Decimal | None
    method: str | None
    formula_type: str | None


class SlotQualityPayload(Record):
    payload_type: Literal["slot_quality"] = "slot_quality"
    reason: QualityReason
    detail: str
    flags: tuple[str, ...] = ()


Payload = Annotated[
    TradeBarPayload | MarkBarPayload | IndexBarPayload | FundingPayload | SlotQualityPayload,
    Field(discriminator="payload_type"),
]


class OrderKey(Record):
    """Explicit, deterministic total-order fields (see ORDERING_POLICY_TEXT)."""

    available_time: datetime
    family_rank: int
    series_id: str
    event_time: datetime
    kind_rank: int
    event_id: str


class FeedEvent(Record):
    event_id: str  # stable: independent of dataset package and availability policy
    channel: ChannelRef
    kind: EventKind
    event_time: datetime
    event_end_time: datetime | None  # bar close; None for instantaneous events
    available_time: datetime
    availability_basis: AvailabilityBasis
    availability_policy_id: str
    source: SourceRef
    order: OrderKey
    payload: Payload


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


class AvailabilityPolicy(Record):
    """Feed-layer availability transformation. Never changes event time."""

    policy_id: str
    basis: AvailabilityBasis
    base_policy_id: str  # marketdata.v1 policy the source availability came from
    bar_delay: timedelta = Field(ge=timedelta(0))
    funding_delay: timedelta = Field(ge=timedelta(0))
    measured: bool  # False: modeled convention, not a measured publication latency
    note: str


class FreshnessPolicy(Record):
    """Per-family freshness thresholds. Configuration, not universal constants."""

    policy_id: str
    bar_max_age: timedelta  # max age since availability for a valid bar to count as FRESH
    funding_max_age: timedelta | None  # None: sparse channel, freshness NOT_APPLICABLE
    history_limit: int = Field(ge=1)  # valid observations retained per channel in state/snapshots
    note: str


# ---------------------------------------------------------------------------
# Feed manifest
# ---------------------------------------------------------------------------


class FeedManifest(Record):
    schema_version: str
    contract_status: str
    schema_revision: int
    dataset_ids: tuple[str, ...]  # evidence-package identities (kept, never replaced)
    content_identity: str  # normalized feed-content identity (packaging-independent)
    inst_id: str
    index_id: str
    ordering_policy_id: str
    availability_policy: AvailabilityPolicy
    coverage: tuple[ChannelCoverage, ...]
    event_count: int
    event_counts: dict[str, int]  # by "family/kind"
    ordered_event_hash: str


# ---------------------------------------------------------------------------
# Observable state snapshot and delta
# ---------------------------------------------------------------------------


class ChannelCondition(StrEnum):
    """What the latest slot evidence says (independent of timing)."""

    NEVER_SEEN = "NEVER_SEEN"  # no event yet (warm-up)
    VALID = "VALID"  # latest slot has a valid observation
    GAP = "GAP"  # latest slot is missing
    REJECTED = "REJECTED"  # latest slot had evidence that was rejected
    INVALID_ONLY = "INVALID_ONLY"  # only rejected evidence has ever been seen


class Freshness(StrEnum):
    UNKNOWN = "UNKNOWN"  # no valid observation yet
    FRESH = "FRESH"
    STALE = "STALE"  # last valid value is carried with its original times, not refreshed
    NOT_APPLICABLE = "NOT_APPLICABLE"  # sparse channel without an expected schedule


class FeedCursor(Record):
    applied_events: int  # number of feed events applied
    last_event_id: str | None
    last_order: OrderKey | None


class ChannelCounts(Record):
    valid: int = 0
    missing: int = 0
    invalid_row: int = 0
    conflicting_duplicate: int = 0
    incomplete_rejected: int = 0
    excluded_unclassified: int = 0


class ChannelSnapshot(Record):
    channel: ChannelRef
    channel_id: str
    condition: ChannelCondition
    freshness: Freshness
    latest_valid: FeedEvent | None  # newest valid observation by event time (carried if stale)
    age_since_available: timedelta | None  # as_of - latest_valid.available_time
    age_since_event_end: timedelta | None  # as_of - latest_valid event end (or event time)
    latest_slot_time: datetime | None  # event time of the newest slot evidence of any kind
    last_quality: FeedEvent | None
    quality_slots_since_valid: int  # slot-quality events newer than the latest valid observation
    counts: ChannelCounts
    beyond_coverage: bool  # as_of is past the last moment the evidence could speak for
    history: tuple[FeedEvent, ...]  # valid observations, oldest -> newest, bounded


class ObservableSnapshot(Record):
    """Point-in-time observable market state. No interpretation."""

    schema_version: str
    snapshot_id: str  # content digest + provenance
    content_digest: str  # causal market content only (no dataset/package references)
    as_of: datetime
    information_cutoff: datetime  # == as_of: nothing available later influenced this snapshot
    cursor: FeedCursor
    ordering_policy_id: str
    availability_policy_id: str
    freshness_policy_id: str
    feed_content_identity: str
    dataset_ids: tuple[str, ...]
    channels: tuple[ChannelSnapshot, ...]
    labels: tuple[str, ...]


class ChannelChange(Record):
    channel_id: str
    new_events: int
    condition_before: ChannelCondition
    condition_after: ChannelCondition
    freshness_before: Freshness
    freshness_after: Freshness
    latest_valid_before: str | None  # event id
    latest_valid_after: str | None


class SnapshotDelta(Record):
    """What changed between two snapshots of the same feed, in causal order."""

    schema_version: str
    delta_id: str
    from_snapshot_id: str
    to_snapshot_id: str
    from_as_of: datetime
    to_as_of: datetime
    from_cursor: FeedCursor
    to_cursor: FeedCursor
    events: tuple[FeedEvent, ...]  # events applied between the cursors, in feed order
    channel_changes: tuple[ChannelChange, ...]


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (
    ChannelRef,
    ChannelCoverage,
    SourceRef,
    FeedEvent,
    AvailabilityPolicy,
    FreshnessPolicy,
    FeedManifest,
    FeedCursor,
    ChannelSnapshot,
    ObservableSnapshot,
    SnapshotDelta,
)
