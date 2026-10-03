"""Causal temporal substrate contracts (``algotrader.temporal.v1``, revision 1, PROVISIONAL).

Separate from the frozen ``semantic.v1`` / ``marketdata.v1`` and from ``feed.v1`` (reused, never extended). These
records describe FACTUAL multi-horizon aggregates of the admitted 1m evidence, the explicit logical clock and the
reasoning-dispatch boundaries at which a future adviser may read them, plus dependency readiness. They carry no
interpretation, prediction, recommendation, sizing or P&L; horizon roles are design labels, not votes or gates.

Time fields stay distinct: ``interval_start/end`` (market time), ``known_at`` (when the record could be known from
its admitted prerequisites), ``sealed_at`` / ``Dispatch.clock_time`` (logical clock barrier) and the admitted
cursor (position in the canonical feed). Wall-clock pacing, checkpoint cadence and UI refresh never enter here.

PROVISIONAL: any change bumps ``TEMPORAL_SCHEMA_REVISION`` with a ``TEMPORAL_CHANGELOG`` entry and needs Director
approval; the checked-in baseline ``schemas/algotrader.temporal.v1.json`` cannot be rewritten silently.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ..feed.contracts import AvailabilityBasis, ChannelRef, Family

TEMPORAL_SCHEMA_VERSION = "algotrader.temporal.v1"
TEMPORAL_CONTRACT_STATUS = "PROVISIONAL"
TEMPORAL_SCHEMA_REVISION = 1
TEMPORAL_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-10-03", "Initial provisional baseline (WP-008-R2): UTC multi-horizon factual aggregates, seal-no-revision "
                      "late policy, logical clock/dispatch records, clock commands and dependency readiness."),
)

PROFILE_ID = "temporal.utc-horizons.v1"
SEAL_POLICY_ID = "temporal.seal-no-revision.v1"
SEAL_POLICY_TEXT = (
    "Each interval is frozen at its scheduled closure barrier (interval end, clipped to coverage end, plus the declared "
    "closure allowance) or earlier, once every in-coverage minute has admitted evidence. If any prerequisite minute was "
    "not admitted valid by then, the interval is sealed INCOMPLETE (or OUTSIDE_COVERAGE) and is never reopened or "
    "repaired: evidence for a sealed interval is counted as late-excluded here and stays accepted factual evidence in "
    "the feed reducer. Consequence: late data can leave a horizon unavailable even though it was received later. A "
    "revision policy would need an explicit new version.")


class ClockPolicy(StrEnum):
    MODELED_COMPLETE_PREFIX = "temporal.clock.modeled-complete-prefix.v1"
    RECORDED_SYNTHETIC_BARRIER = "temporal.clock.recorded-replay-synthetic-barrier.v1"
    RECORDED_DISPATCH_TAPE = "temporal.clock.recorded-dispatch-tape.v1"


CLOCK_POLICY_TEXT: dict[ClockPolicy, str] = {
    ClockPolicy.MODELED_COMPLETE_PREFIX: (
        "Modeled historical execution: at every barrier time t the whole canonical prefix with available_time <= t "
        "(the entire tie group, any family order) is admitted first; then due intervals close, readiness is "
        "assessed, due expiry callbacks run, then scheduled reasoning, then publication. No event available after t "
        "contributes. The clock jumps from barrier to barrier; empty minutes are never iterated."),
    ClockPolicy.RECORDED_SYNTHETIC_BARRIER: (
        "Recorded replay WITHOUT a dispatch tape: a synthetic barrier follows every admitted receipt (its local "
        "receipt time and cursor); equal-timestamp receipts produce separate barriers in receipt order and never "
        "wait for a supposedly complete tie group. This is a named replay convention, NOT a reproduction of the "
        "decisions an unrecorded live adviser would have made."),
    ClockPolicy.RECORDED_DISPATCH_TAPE: (
        "Recorded/live-style execution from an explicit admission/clock command tape: only the logged prefix is "
        "admitted at each clock barrier; a later receipt at the same time causes a later dispatch with a different "
        "admitted cursor. Replaying the same tape reproduces the same dispatches exactly."),
}


class Horizon(StrEnum):
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MO1 = "1mo"


HORIZON_ROLE: dict[Horizon, str] = {
    Horizon.M15: "setup", Horizon.H1: "tactical", Horizon.H4: "broad", Horizon.D1: "broad",
    Horizon.W1: "context", Horizon.MO1: "context",
}
HORIZON_ORDER = (Horizon.M15, Horizon.H1, Horizon.H4, Horizon.D1, Horizon.W1, Horizon.MO1)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AggregateStatus(StrEnum):
    FORMING = "FORMING"  # open interval (inspection only; never a sealed record)
    COMPLETE = "COMPLETE"  # every expected minute admitted valid before the closure barrier
    INCOMPLETE = "INCOMPLETE"  # sealed with missing / rejected / absent prerequisites
    OUTSIDE_COVERAGE = "OUTSIDE_COVERAGE"  # the interval is cut by the evidence package's coverage


class ConstituentCounts(Record):
    expected: int  # calendar minutes of the interval (actual length, e.g. 28/29/30/31-day months)
    valid: int
    missing: int  # explicit MISSING + absent at seal + outside coverage
    rejected: int  # INVALID_ROW / CONFLICTING_DUPLICATE / INCOMPLETE_REJECTED / EXCLUDED_UNCLASSIFIED
    reasons: dict[str, int]  # reason -> minutes; sums to missing + rejected


class AggregateValues(Record):
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    # trade family only (typed, exact sums; currencies preserved). Mark/index carry no volume.
    volume_contracts: Decimal | None = None
    volume_base: Decimal | None = None
    volume_base_ccy: str | None = None
    volume_quote: Decimal | None = None
    volume_quote_ccy: str | None = None
    index_id: str | None = None


class TemporalAggregate(Record):
    record_id: str
    profile_id: str
    channel: ChannelRef
    channel_id: str
    horizon: Horizon
    role: str
    interval_start: datetime
    interval_end: datetime
    status: AggregateStatus
    counts: ConstituentCounts
    values: AggregateValues | None  # only when COMPLETE
    partial_diagnostic: AggregateValues | None  # explicitly PARTIAL values of valid constituents; never a bar
    known_at: datetime  # COMPLETE: max(end, prerequisite available times); otherwise the sealing barrier
    sealed_at: datetime  # logical clock barrier that froze the interval
    admitted_cursor: int  # canonical prefix length admitted at the sealing barrier
    closure_dispatch_id: str
    availability_basis: AvailabilityBasis
    availability_policy_id: str
    feed_content_identity: str
    seal_policy_id: str
    content_digest: str  # over market content + status/counts/times (not provenance)


class ReadinessStatus(StrEnum):
    READY = "READY"
    WARMING_UP = "WARMING_UP"
    GAP = "GAP"
    STALE = "STALE"
    OUTSIDE_COVERAGE = "OUTSIDE_COVERAGE"
    UNAVAILABLE = "UNAVAILABLE"


# Deterministic precedence (most severe first); every applicable blocker is reported, not only the winner.
READINESS_PRECEDENCE = (ReadinessStatus.UNAVAILABLE, ReadinessStatus.OUTSIDE_COVERAGE, ReadinessStatus.GAP,
                        ReadinessStatus.STALE, ReadinessStatus.WARMING_UP, ReadinessStatus.READY)


class Dependency(Record):
    """One declared observation dependency. R2 demonstrates the query; MP-001 chooses production values."""

    name: str
    family: Family
    horizon: Horizon | None  # None only for sparse funding settlement context
    required_complete: int = Field(ge=1)  # consecutive COMPLETE sealed records
    freshness_allowance: timedelta = Field(gt=timedelta(0))  # vs known_at of the newest complete record
    optional: bool = True  # an unavailable optional dependency never invalidates the others


class Readiness(Record):
    dependency: str
    status: ReadinessStatus
    blockers: tuple[str, ...]
    complete_consecutive: int
    required: int
    latest_record_id: str | None
    age_since_end: timedelta | None
    age_since_known: timedelta | None


class DeadlineKind(StrEnum):
    EXPIRY = "expiry"  # e.g. a future call's expiry check (runs before publication)
    REASONING = "reasoning"  # scheduled reasoning callback
    PUBLICATION = "publication"  # potential publication callback


DEADLINE_KIND_RANK = {DeadlineKind.EXPIRY: 0, DeadlineKind.REASONING: 1, DeadlineKind.PUBLICATION: 2}


class Deadline(Record):
    deadline_id: str
    due: datetime
    priority: int = 0
    kind: DeadlineKind = DeadlineKind.REASONING


class Dispatch(Record):
    dispatch_id: str
    seq: int
    clock_time: datetime
    barrier: str  # scheduled | receipt | tape | finish
    admitted_cursor: int
    last_order: str | None
    clock_policy_id: str
    profile_fingerprint: str
    reasons: tuple[str, ...]  # sorted, unique; closures, readiness transitions, due deadlines (in callback order)
    callbacks: tuple[str, ...]  # due deadline ids in execution order (expiry < reasoning < publication)
    closed_record_ids: tuple[str, ...]
    readiness: tuple[Readiness, ...]


# Clock commands (live-style tape / fixtures). R2 subscribers are engineering fakes only.
class Admit(Record):
    command: str = "admit"
    cursor: int  # canonical position of the event being admitted (== admitted count before it)
    event_id: str


class AdvanceTo(Record):
    command: str = "advance"
    time: datetime
    barrier_id: str


class RegisterDeadline(Record):
    command: str = "register"
    deadline: Deadline


class CancelDeadline(Record):
    command: str = "cancel"
    deadline_id: str


class TemporalProfile(Record):
    """Versioned profile + execution configuration (fingerprinted; part of every restore point)."""

    profile_id: str = PROFILE_ID
    horizons: tuple[Horizon, ...] = HORIZON_ORDER
    retention: dict[Horizon, int]  # sealed records kept per channel/horizon (finite; hard max enforced)
    closure_allowance: timedelta = Field(ge=timedelta(0))
    max_open_intervals: int = Field(ge=1, le=8)
    clock_policy: ClockPolicy
    seal_policy_id: str = SEAL_POLICY_ID
    dependencies: tuple[Dependency, ...] = ()
    deadlines: tuple[Deadline, ...] = ()
    clock_end: datetime | None = None  # finite replay end (default: coverage end + closure allowance)
    labels: tuple[str, ...] = ("TEMPORAL_SUBSTRATE_ONLY", "NO_ADVISER", "NO_INTERPRETATION")


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (
    ConstituentCounts, AggregateValues, TemporalAggregate, Dependency, Readiness, Deadline, Dispatch,
    Admit, AdvanceTo, RegisterDeadline, CancelDeadline, TemporalProfile,
)
