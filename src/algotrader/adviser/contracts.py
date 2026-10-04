"""Advisory semantic contracts ``algotrader.semantic.v2`` (revision 1, PROVISIONAL) — MP-001 §10.

Separate from the frozen synthetic DEMO ``algotrader.semantic.v1`` (unchanged) and from the factual
``feed.v1``/``temporal.v1`` contracts (reused, never extended). Every record carries a shared envelope:
record id/revision, method identity (model, rules version + rules-document hash, register hash, capability
profile hash, implementation, build), instrument/price role, origin (HISTORICAL_MODELED / RECONSTRUCTED / LIVE),
the professional input frontier (professional sequence + admitted factual cursor + clock time), event interval,
known_at / published_at, dependency references with readiness, limitations and revision lineage.

Decimals are serialized as exact decimal strings; instants are explicit UTC. Observed context is not expected
direction; a scenario is a conditional antecedent with an alternative, never a calibrated probability. A call's
original direction/V/T/structural area/scale/trigger reference/issue time/hard horizon never change; revisions alter
current entry/guidance/status only, with reasons. RETIRED is terminal guidance withdrawal, not a statement about any
human or synthetic position. No account, quantity, leverage, order or P&L field exists in this namespace (hypothetical
outcomes live in ``algotrader.adviser-evaluation.v1``).

PROVISIONAL: any change bumps ``SEMANTIC_V2_REVISION`` with a changelog entry (Director approval); the checked-in
baseline ``schemas/algotrader.semantic.v2.json`` is never rewritten silently.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

SEMANTIC_V2_VERSION = "algotrader.semantic.v2"
SEMANTIC_V2_STATUS = "PROVISIONAL"
SEMANTIC_V2_REVISION = 1
SEMANTIC_V2_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-10-04", "Initial provisional advisory baseline (WP-009): Observation, Landmark, PhaseState, "
                      "EventContext/EventResponse, MarketView, Scenario, CandidatePlan, Actionability, AdviserCall, "
                      "CallRevision, MaterialChange with the shared provenance envelope."),
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Origin(StrEnum):
    HISTORICAL_MODELED = "HISTORICAL_MODELED"  # receipt-pinned historical pack, modeled availability
    RECONSTRUCTED = "RECONSTRUCTED"  # live-session catch-up from fetched history (never measured receipt)
    LIVE = "LIVE"  # live session after activation: recorded local receipts


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class Family(StrEnum):
    A = "A"  # continuation after reaction
    B = "B"  # compression exit with retest
    C = "C"  # failed exit of a compression-qualified box


class MethodRef(Record):
    model: str
    rules_version: str
    rules_sha256: str
    register_sha256: str
    profile_sha256: str
    implementation: str
    build: str | None


class DependencyRef(Record):
    name: str  # e.g. trade.15m, trade.1h, trade.1m, quotes
    status: str  # READY / WARMING_UP / GAP / STALE / UNAVAILABLE / NOT_COVERED
    latest_ref: str | None  # newest record/bar id used
    event_end: datetime | None
    known_at: datetime | None
    digest: str | None = None


class Envelope(Record):
    record_id: str
    revision: int = 0
    kind: str
    schema_version: str = SEMANTIC_V2_VERSION
    method: MethodRef
    instrument: str
    price_role: str  # TRADE (setups/targets/predicates); MARK/INDEX only as named references
    origin: Origin
    clock_policy: str
    professional_seq: int
    factual_cursor: int
    clock_time: datetime  # the professional dispatch barrier that produced this record
    event_start: datetime | None
    event_end: datetime | None
    known_at: datetime
    published_at: datetime
    dependencies: tuple[DependencyRef, ...] = ()
    limitations: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()  # previous revision id / owner (episode, box, attempt, call) ids


class Observation(Record):
    env: Envelope
    lens: str  # structure / momentum / volatility / participation / timing / events / derivatives / execution
    name: str
    values: dict[str, str | None]  # raw values as exact strings with units in the key names
    category: str  # descriptive category (e.g. UP / BALANCED / COMPRESSION / FRESH / UNAVAILABLE)
    decision_role: str  # e.g. FAMILY_CONTEXT_GATE, BOX_BIRTH_GATE, DESCRIPTIVE_ONLY, EXECUTION_ADEQUACY
    meaning: str  # plain-language human meaning


class Landmark(Record):
    env: Envelope
    landmark_id: str
    landmark_type: str  # PIVOT_HIGH_15M ... PREV_DAY_HIGH ... IMPULSE_B ... BOX_UPPER/BOX_LOWER
    side: str  # HIGH (opposes LONG) / LOW (opposes SHORT) — locational type, not order flow
    price: Decimal
    zone_low: Decimal
    zone_high: Decimal
    zone_halfwidth: Decimal
    frozen_scale: Decimal
    horizon: str
    source_ids: tuple[str, ...]
    extremum_time: datetime | None
    status: str  # ACTIVE / BROKEN / RETIRED
    status_reason: str | None
    owner: str | None


class PhaseState(Record):
    env: Envelope
    phase: str  # EXPANSION / COMPRESSION / REACTION / ROTATION / TRANSITION / UNAVAILABLE
    direction: str | None  # displacement sign for EXPANSION
    compression_ratio: Decimal | None
    er6: Decimal | None
    displacement6_scale: Decimal | None
    since: datetime | None  # observed age (descriptive only)
    previous: str | None
    authority: str = "BOX_BIRTH_AND_ADVERSE_EXPANSION_GATES_ONLY; AGE_DESCRIPTIVE"


class EventContext(Record):
    env: Envelope
    event_id: str
    event_revision: int
    event_type: str  # FOMC_DECISION / FOMC_PRESS_CONFERENCE / US_CPI / US_EMPLOYMENT_SITUATION / incident types
    scope: str
    schedule_time: datetime | None  # None: exact official time unknown (never guessed)
    schedule_known_at: datetime | None
    content_known_at: datetime | None
    provenance_sha256: str
    coverage_start: datetime | None
    coverage_end: datetime | None
    cancelled: bool = False
    restriction_start: datetime | None
    restriction_end: datetime | None  # None while the first wholly post-event 15m bar is not complete
    status: str  # SCHEDULED / RESTRICTING / RESPONSE_PENDING / CLOSED / UNKNOWN_TIME / CANCELLED / RESOLVED


class EventResponse(Record):
    env: Envelope
    event_id: str
    label: str = "OBSERVED_PRICE_RESPONSE"  # never causal news interpretation or surprise
    pre_event_reference: Decimal | None
    pre_event_reference_time: datetime | None
    pre_event_scale: Decimal | None
    response_bar_start: datetime | None
    displacement_scale: Decimal | None
    true_range_scale: Decimal | None
    reclaim_flags: dict[str, bool]
    unavailable_fields: tuple[str, ...]


class Scenario(Record):
    scenario_id: str  # the attempt/episode id it is conditional on
    family: Family
    direction: Direction
    antecedent: str  # e.g. "a later eligible complete 1m close >= K+tick with low > V"
    trigger_level: Decimal | None  # K
    invalidation_level: Decimal | None  # V
    conditional_target: str
    alternative: str
    expires_at: datetime | None
    candidate_domain: str


class MarketView(Record):
    env: Envelope
    observed_context: str  # 1h measured path label: UP / DOWN / BALANCED / UNAVAILABLE (not a forecast)
    phase: str
    expected_direction: str  # UP / DOWN / BALANCED / UNCERTAIN / UNAVAILABLE
    conditional: bool  # True when the direction depends on a scenario antecedent
    table_row: str  # which row of the MP-001 §5 total priority table matched
    principal: Scenario | None
    alternatives: tuple[Scenario, ...]
    ongoing_call_id: str | None
    horizon_minutes: tuple[int, int] | None  # family expected durations bounded by remaining lifetime
    levels: dict[str, str | None]
    reasons: tuple[str, ...]
    counterevidence: tuple[str, ...]
    blockers: tuple[str, ...]
    uncertainty: str = "QUALITATIVE_ONLY_NOT_CALIBRATED"


class CandidatePlan(Record):
    env: Envelope
    attempt_id: str
    owner_id: str | None  # episode / box owner
    family: Family
    direction: Direction
    status: str  # WATCH / ARMED / TRIGGERED / ISSUED / REJECTED / WITHDRAWN / EXPIRED
    transition: str  # BIRTH / ARM / REVISE / TRIGGER / WITHDRAW / EXPIRE / REJECT / ISSUE / CLEARED
    reason: str | None
    trigger_level: Decimal | None
    invalidation_level: Decimal | None
    setup: dict[str, str | None]  # frozen setup facts (A/B/L/U/M, scale, zone, source bars, renewal latch)
    arm_published_at: datetime | None
    expires_at: datetime | None


class Actionability(Record):
    env: Envelope
    subject_id: str  # attempt id (trigger evaluation) or call id (reassessment)
    actionable: bool
    blockers: tuple[str, ...]  # every applicable blocking reason, not a score
    execution_mode: str  # HISTORICAL_BASE (MODELED trade close) / LIVE_QUOTED (measured side quote)
    side_price: Decimal | None
    side_price_source: str | None
    cost_envelope_bps: Decimal | None
    gain_bps: Decimal | None  # G
    risk_bps: Decimal | None  # Q
    reward_risk_margin: Decimal | None  # G - 1.2Q - 2.2K
    structural_area: tuple[Decimal, Decimal] | None
    admissible_bounds: tuple[Decimal, Decimal] | None
    remaining_minutes: Decimal | None
    limiting_landmark: dict[str, str | None] | None


class AdviserCall(Record):
    env: Envelope
    call_id: str
    attempt_id: str
    family: Family
    direction: Direction
    thesis: str
    trigger_minute_start: datetime
    issue_reference: Decimal  # trigger complete 1m close
    issued_at: datetime
    invalidation: Decimal  # V (stop guidance), frozen
    target: Decimal  # T, frozen
    target_type: str  # LANDMARK / PROJECTED_BOX_WIDTH / MIDPOINT
    limiting_landmark: dict[str, str | None] | None
    frozen_scale: Decimal
    structural_area: tuple[Decimal, Decimal]
    expected_minutes: tuple[int, int]
    minimum_residual_minutes: int
    hard_deadline: datetime
    progress_check_at: datetime
    premise: str
    entry_status: str  # AVAILABLE / CLOSED / UNVERIFIED
    thesis_status: str  # ONGOING / TARGET_REACHED / INVALIDATED / TIME_EXPIRED / UNASSESSABLE / RETIRED
    actionability: Actionability
    cost_assumptions: str
    uncertainties: tuple[str, ...]


class CallRevision(Record):
    env: Envelope
    call_id: str
    revision: int
    entry_status: str
    entry_reasons: tuple[str, ...]
    entry_conditions_enabled: bool  # all non-price entry conditions hold (data, time, events, quotes); price separate
    thesis_status: str
    terminal_reason: str | None  # THESIS_FAILED / STALLED for RETIRED; contact/gap reasons otherwise
    current_admissible_bounds: tuple[Decimal, Decimal] | None
    remaining_minutes: Decimal | None
    duration_window_minutes: tuple[Decimal, Decimal] | None
    guidance: str
    changed: tuple[str, ...]
    progress_max_favorable_scale: Decimal | None


class MaterialChange(Record):
    env: Envelope
    change_id: str
    subject_id: str
    change_type: str  # NEW_CALL / ENTRY_WITHDRAWN / ENTRY_REOPENED / ENTRY_UNVERIFIED / TERMINAL / VIEW_CHANGED
    summary: str
    alertable: bool  # only LIVE committed publications of call changes are alert candidates


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (
    MethodRef, DependencyRef, Envelope, Observation, Landmark, PhaseState, EventContext, EventResponse, Scenario,
    MarketView, CandidatePlan, Actionability, AdviserCall, CallRevision, MaterialChange,
)
KIND_CONTRACTS: dict[str, type[Record]] = {
    "observation": Observation, "landmark": Landmark, "phase": PhaseState, "event_context": EventContext,
    "event_response": EventResponse, "market_view": MarketView, "candidate": CandidatePlan,
    "actionability": Actionability, "call": AdviserCall, "call_revision": CallRevision,
    "material_change": MaterialChange,
}

__all__ = ["SEMANTIC_V2_VERSION", "SEMANTIC_V2_REVISION", "PUBLIC_CONTRACTS", "KIND_CONTRACTS", "Origin", "Direction",
           "Family"]
_ = Decimal  # exact decimal strings in JSON mode
