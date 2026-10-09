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
SEMANTIC_V2_REVISION = 5
SEMANTIC_V2_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-10-04", "Initial provisional advisory baseline (WP-009): Observation, Landmark, PhaseState, "
                      "EventContext/EventResponse, MarketView, Scenario, CandidatePlan, Actionability, AdviserCall, "
                      "CallRevision, MaterialChange with the shared provenance envelope."),
    (2, "2026-10-05", "WP-011 MP-002 btc.context-action.v0.3 (additive): new discriminated kinds ScenarioState "
                      "('scenario': structural scenario lifecycle independent of entry/call/evaluator) and "
                      "EntryAttempt ('entry_attempt': the child entry attempt - confirmation routing, IMMEDIATE/RETURN "
                      "mode, WAIT_PRICE, caps, blockers, zone provenance, registered diagnostic geometry); v0.3 "
                      "variants ScenarioV3/MarketViewV3/AdviserCallV3/CallRevisionV3 extend the revision-1 records "
                      "with fields. Revision-1 records, their bytes and readers are unchanged; v0.2 runs never emit "
                      "the new kinds, variants or fields (per-method emitted revision: v0.2 -> 1, v0.3 -> 2)."),
    (3, "2026-10-06", "WP-012 MP-003 btc.context-action.v0.4 (additive): variant ScenarioStateV4 of the 'scenario' kind "
                      "adds the pre-confirmation A local anchor provenance - anchor epoch/status/source bar, actual "
                      "anchor publication time and admitted cursor, the lost or superseded anchor (geometry, reason, "
                      "contact interval and its end), ever_armed and the immutable first-arm destination-monitoring "
                      "origin (time and cursor) - and the transitions ANCHOR_LOST and REARM (prospective replacement). "
                      "Every other v0.4 kind uses the revision-2 contracts unchanged. Revision-1/2 records, their bytes "
                      "and readers are unchanged; v0.2/v0.3 runs never emit the variant (per-method emitted revision: "
                      "v0.2 -> 1, v0.3 -> 2, v0.4 -> 3)."),
    (4, "2026-10-08", "WP-014 MP-004 btc.context-action.v0.5 (additive): variant EntryAttemptV5 of the 'entry_attempt' "
                      "kind adds 'response' - the A RETURN local reference (bar, H0/L0, close, interval, actual "
                      "publication p0 and admitted cursor c0), the phase WAIT_RETURN/WAIT_RESPONSE, the complete bars "
                      "checked in the local domain and, on the closing record, the decisive bar and outcome "
                      "(ISSUED / NOT_ISSUABLE with every blocker and one primary reason / CONTRADICTED / UNASSESSABLE "
                      "/ ENDED_BY_PRIORITY_CAUSE / CLEARED); null for IMMEDIATE, B/C and children without a "
                      "reference. New values only: entry state WAIT_RESPONSE, transition RESPONSE_REFERENCE, reasons "
                      "LOCAL_RESPONSE_CONTRADICTED, LOCAL_CONTACT_TIME_AMBIGUOUS and RESPONSE_NOT_ISSUABLE. Every other "
                      "v0.5 kind uses the revision-3 contracts unchanged. Revision-1/2/3 records, their bytes and "
                      "readers are unchanged; v0.2/v0.3/v0.4 runs never emit the variant (per-method emitted "
                      "revision: v0.2 -> 1, v0.3 -> 2, v0.4 -> 3, v0.5 -> 4)."),
    (5, "2026-10-09", "WP-015 MP-005 btc.context-action.v0.6 (values only; no kind, field, type or shape change): v0.6 "
                      "emits the revision-4 contracts unchanged (KIND_CONTRACTS_V6 = KIND_CONTRACTS_V5). New values "
                      "only: entry-attempt reason INITIAL_RESPONSE_INCOMPATIBLE:<CORRIDOR|HISTORICAL_ECONOMICS> on a "
                      "TERMINAL record published in the same dispatch as its RESPONSE_REFERENCE, whose 'response' "
                      "outcome is INITIAL_RESPONSE_INCOMPATIBLE with the string keys incompatibility_base, "
                      "incompatibility_annotations, execution_profile, F, C0, A0, F_cap_C0, J0 and economic_basis "
                      "(diagnostic bases; exact decimal strings or null). Revision-1..4 records, their bytes and "
                      "readers are unchanged; v0.2-v0.5 runs never emit the new values (per-method emitted revision: "
                      "v0.2 -> 1, v0.3 -> 2, v0.4 -> 3, v0.5 -> 4, v0.6 -> 5)."),
)
SEMANTIC_V2_EMITTED_REVISION = {"btc.context-action.v0.2": 1, "btc.context-action.v0.3": 2,
                                "btc.context-action.v0.4": 3, "btc.context-action.v0.5": 4,
                                "btc.context-action.v0.6": 5}


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


# -- revision 2: MP-002 v0.3 records (never emitted by v0.2 runs) -------------------------------------------------


class ScenarioV3(Scenario):
    status: str  # WATCH / ARMED / CONFIRMED
    destination: Decimal | None  # frozen narrative destination (A: B, B: box projection, C: midpoint M)
    destination_type: str
    confirmed_at: datetime | None


class MarketViewV3(MarketView):
    """v0.3 total table (MP-002 §4): structural scenarios only; call existence never creates a direction, so
    ``ongoing_call_id`` is always None here (guidance is in call records)."""

    principal: ScenarioV3 | None
    alternatives: tuple[ScenarioV3, ...]
    watch: tuple[ScenarioV3, ...]  # conditional WATCH hypotheses (never a forecast hit or a call)


class AdviserCallV3(AdviserCall):
    scenario_id: str
    entry_mode: str  # IMMEDIATE / RETURN (A); IMMEDIATE (B/C one-shot)
    confirmed_at: datetime  # structural confirmation publication (A hard-deadline origin)
    target_at_confirmation: Decimal  # T_confirm; ``target`` is the current monotone cap frozen at issue
    hard_deadline_origin: str  # STRUCTURAL_CONFIRMATION_PUBLICATION (A) / ISSUE (B/C: confirmation = issue)
    issue_scale: Decimal  # S15 at issue (call progress scale)
    cap_history: tuple[dict[str, str | None], ...]


class CallRevisionV3(CallRevision):
    coverage_loss_from: datetime | None  # first missing interval when guidance ended for coverage loss
    scenario_terminal: str | None  # underlying scenario terminal reason when retired as SCENARIO_TERMINAL


class ScenarioState(Record):
    """One structural scenario transition. Structural only: no cost, admissible interval, call or evaluator field,
    so identical structural input under different execution-cost assumptions yields identical normalized scenario
    records (MP-002 §3/§4)."""

    env: Envelope
    scenario_id: str
    owner_id: str | None  # A: its own discovery owner (= scenario id); B/C: the box
    entry_attempt_id: str  # deterministic child id (scenario id + '#entry'); its records are separate
    family: Family
    direction: Direction
    status: str  # WATCH / ARMED / CONFIRMED / TERMINAL
    transition: str  # BIRTH / ARM / REVISE / CONFIRM / OWNER_RELEASE / TERMINAL
    reason: str | None
    terminal_state: str | None  # INVALIDATED / DESTINATION_REACHED / EXPIRED / WITHDRAWN / STALLED / ...
    antecedent: str
    trigger_level: Decimal | None  # K_trigger
    invalidation_level: Decimal | None  # V
    reaction_level: Decimal | None  # A: R
    destination: Decimal | None  # frozen narrative destination
    destination_type: str
    premise: str | None
    setup: dict[str, str | None]
    activated_at: datetime | None  # actual arm (or latest pre-confirmation revision) publication
    original_expiry: datetime | None  # original setup deadline (A: also the discovery-owner and WAIT bound)
    confirmed_at: datetime | None
    confirmation_close: Decimal | None
    confirmation_scale: Decimal | None
    confirmed_deadline: datetime | None  # confirmation + family hard horizon
    progress_check_at: datetime | None  # confirmation + half the family hard horizon
    discovery_owner: str | None  # A: OCCUPIED / RELEASED
    warmup_origin: bool


class EntryAttempt(Record):
    """The child entry attempt of one structural scenario (economic: may differ under other cost assumptions)."""

    env: Envelope
    entry_attempt_id: str
    scenario_id: str
    family: Family
    direction: Direction
    state: str  # WAIT_PRICE / ISSUED / TERMINAL
    mode: str | None  # IMMEDIATE / RETURN
    transition: str  # ROUTED / WAIT_OPEN / CAP_REVISION / BLOCKERS / RETURN_USABLE / ISSUE / REJECT / TERMINAL
    reason: str | None
    blockers: tuple[str, ...]  # every applicable reason, not a score
    call_id: str | None
    geometry: dict[str, str | None]  # R, K_trigger, V, T_confirm, T_current, S15, corridor, I0, economics, K_cost
    containing_zones: tuple[dict[str, str | None], ...]  # every eligible opposing zone containing the price
    selected_zone: dict[str, str | None] | None  # deterministic resolver attribution among them
    limiting_landmark: dict[str, str | None] | None
    cap_history: tuple[dict[str, str | None], ...]  # each cap with its effective publication/cursor
    clocks: dict[str, str | None]
    diagnostic: dict[str, str | None]  # registered D/N denominators (computed for every evaluable confirmation)


class ScenarioStateV4(ScenarioState):
    """Revision 3 (MP-003 v0.4): the structural scenario record plus the pre-confirmation A LOCAL anchor provenance.

    Transitions add ANCHOR_LOST (the active anchor's V was contacted in an eligible complete interval, or its contact
    time is ambiguous: the same unconfirmed scenario returns to WATCH, owner/latch/zones/deadline unchanged) and REARM
    (a prospective replacement anchor from a newly published, strictly deeper complete 15m reaction). REVISE is a
    supersession without contact. Every field is structural (cost-invariant). B/C and confirmed scenarios carry the
    anchor fields as null / their last values."""

    anchor_epoch: int | None  # local epoch of the current (or last) anchor under this scenario; None before first arm
    anchor_status: str | None  # NONE / ACTIVE / INVALIDATED / UNASSESSABLE / SUPERSEDED / FROZEN_AT_CONFIRMATION
    anchor_source: str | None  # the complete 15m reaction bar defining R/K of the current anchor
    anchor_published_at: datetime | None  # actual dispatch publication (never backdated to the source bar close)
    anchor_published_cursor: int | None  # admitted factual cursor at publication
    previous_anchor: dict[str, str | None] | None  # lost/superseded epoch: R/K/V, status, reason, interval and its end
    ever_armed: bool | None  # A: destination monitoring is active from the first published arm onward
    destination_monitoring_from: datetime | None  # immutable first actual arm publication (A); None before
    destination_monitoring_cursor: int | None


class EntryAttemptV5(EntryAttempt):
    """Revision 4 (MP-004 v0.5): the child entry attempt plus the A RETURN local response provenance.

    ``response`` is null until the first usable return prepares the single immutable reference; afterwards it carries
    the reference bar/interval, H0/L0 and close, the actual publication (p0) and admitted cursor (c0) - never the
    nominal bar end - the phase, the complete bars examined in the local domain and, on the closing record, the
    decisive bar and outcome. A first recovery is a transient event: it is never stored as a confirmation; the
    dispatch ends with ISSUE or a terminal record carrying the observation. Exact decimal strings."""

    response: dict[str, str | None] | None


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (
    MethodRef, DependencyRef, Envelope, Observation, Landmark, PhaseState, EventContext, EventResponse, Scenario,
    MarketView, CandidatePlan, Actionability, AdviserCall, CallRevision, MaterialChange, ScenarioV3, MarketViewV3,
    AdviserCallV3, CallRevisionV3, ScenarioState, EntryAttempt, ScenarioStateV4, EntryAttemptV5,
)
KIND_CONTRACTS: dict[str, type[Record]] = {  # revision-1 kinds emitted by v0.2 (unchanged)
    "observation": Observation, "landmark": Landmark, "phase": PhaseState, "event_context": EventContext,
    "event_response": EventResponse, "market_view": MarketView, "candidate": CandidatePlan,
    "actionability": Actionability, "call": AdviserCall, "call_revision": CallRevision,
    "material_change": MaterialChange,
}
KIND_CONTRACTS_V3: dict[str, type[Record]] = {  # kinds emitted by v0.3 (no 'candidate': scenarios + entry attempts)
    "observation": Observation, "landmark": Landmark, "phase": PhaseState, "event_context": EventContext,
    "event_response": EventResponse, "market_view": MarketViewV3, "actionability": Actionability,
    "call": AdviserCallV3, "call_revision": CallRevisionV3, "material_change": MaterialChange,
    "scenario": ScenarioState, "entry_attempt": EntryAttempt,
}
KIND_CONTRACTS_V4: dict[str, type[Record]] = {**KIND_CONTRACTS_V3, "scenario": ScenarioStateV4}  # v0.4 (revision 3)
KIND_CONTRACTS_V5: dict[str, type[Record]] = {**KIND_CONTRACTS_V4, "entry_attempt": EntryAttemptV5}  # v0.5 (revision 4)
KIND_CONTRACTS_V6: dict[str, type[Record]] = dict(KIND_CONTRACTS_V5)  # v0.6 (revision 5: new values only)

__all__ = ["SEMANTIC_V2_VERSION", "SEMANTIC_V2_REVISION", "PUBLIC_CONTRACTS", "KIND_CONTRACTS", "Origin", "Direction",
           "Family", "KIND_CONTRACTS_V3", "KIND_CONTRACTS_V4", "KIND_CONTRACTS_V5", "KIND_CONTRACTS_V6"]
_ = Decimal  # exact decimal strings in JSON mode
