"""Hypothetical evaluation contracts ``algotrader.adviser-evaluation.v1`` (revision 2, PROVISIONAL).

A separate namespace from ``semantic.v2``: immutable call-linked hypothetical entry/exit paths, their declared
profiles, censored/ambiguous bounds, hourly MarketView/persistence samples and report aggregates (MP-001 §11).
Reasoning never reads these records; evaluator profiles/identity are separate from model/capability identity.

N0 = 1 USDT is an abstract reporting unit with a constant synthetic quantity q = 1/E; results are normalized
fractions of that unit. There is no wallet, account, balance, quantity decision, margin, leverage or currency
result here and none of this is a fill a person achieved.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

EVALUATION_VERSION = "algotrader.adviser-evaluation.v1"
EVALUATION_STATUS = "PROVISIONAL"
EVALUATION_REVISION = 2
EVALUATION_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-10-04", "Initial provisional baseline (WP-009): evaluator profile, hypothetical path (primary, "
                      "entry-delay sensitivities, horizon-only baseline), normalized one-unit accounting, view "
                      "samples and report aggregates."),
    (2, "2026-10-05", "WP-009 correction (additive, optional): HypotheticalPath.resolved_at - the professional clock "
                      "time of the dispatch (or clock-end finish) at which the evaluator determined the path, so "
                      "cutoff-safe inspection never shows an outcome before it was knowable. Revision-1 records "
                      "remain readable (resolved_at absent = unknown; withheld under a cutoff)."),
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluatorProfile(Record):
    profile_id: str = "mp001.evaluation.primary.v1"
    entry_delay_seconds: int
    exit_delay_seconds: int
    boundary_alignment: str = "UTC_CEIL_MINUTE"
    opening_condition: str = "PREOPEN_EVIDENCE_PLUS_OWN_OPEN_GEOMETRY_NO_FUTURE_HLC"
    fee_per_leg: Decimal
    allowance_per_leg: Decimal
    adequacy_envelope_bps: Decimal
    funding: str  # AUTHORITATIVE_IF_COVERED / PRICE_NET_ONLY
    exit_mode: str  # GUIDANCE (stop/target/guidance) / HORIZON_ONLY (no stop/target)
    notional_unit: str = "N0=1 abstract USDT reporting unit; q=N0/E constant; not a human size"


class Fill(Record):
    price: Decimal
    reason: str  # OPEN / STOP_TOUCH / TARGET_TOUCH / STOP_GAP_ADVERSE_OPEN / TARGET_GAP_CONSERVATIVE / DISCRETIONARY_OPEN
    time_start: datetime  # exact boundary for open fills; minute interval start for intrabar touches
    time_end: datetime  # == time_start for open fills; minute end for intrabar touches (fill time unknown inside)


class HypotheticalPath(Record):
    path_id: str
    call_id: str
    profile: EvaluatorProfile
    variant: str  # PRIMARY / ENTRY_DELAY_0 / ENTRY_DELAY_120 / HORIZON_ONLY
    family: str
    direction: str
    status: str  # NO_ENTRY / CLOSED / AMBIGUOUS / CENSORED / UNRESOLVED
    exit_class: str | None  # TARGET / STOP / STOP_GAP / TARGET_GAP / GUIDANCE_RETIRED / GUIDANCE_TIME / ...
    entry: Fill | None
    exit: Fill | None
    entry_attempts: int  # opening boundaries checked
    rejected_opens: int  # boundaries whose own open failed the primary predicate
    gross: Decimal | None
    fees: Decimal | None
    allowances: Decimal | None
    price_net: Decimal | None
    stress_price_net: Decimal | None  # same path, stress allowance per leg (outcome sensitivity only)
    funding: Decimal | None
    total_net: Decimal | None  # None = TOTAL_NET_UNAVAILABLE (never zero by assumption)
    funding_status: str
    bounds: dict[str, Decimal | None]  # ambiguity/censoring bounds (favorable/adverse)
    mfe: Decimal | None  # max favorable excursion fraction over the complete observed post-entry path
    mae: Decimal | None
    held_minutes: Decimal | None
    censored_from: datetime | None
    notes: tuple[str, ...]
    resolved_at: datetime | None = None  # r2: dispatch/finish time at which this path was determined


class ViewSample(Record):
    sample_time: datetime
    anchor_price: Decimal | None  # latest complete 1m trade close known at sampling
    view: str  # UP / DOWN / BALANCED / UNCERTAIN / UNAVAILABLE
    conditional: bool
    scenario_id: str | None
    persistence: str | None  # UP / DOWN / FLAT / None(unassessable)
    outcome_1h: str | None  # UP / DOWN / FLAT / None (endpoint unavailable)
    outcome_4h: str | None
    return_1h: Decimal | None
    return_4h: Decimal | None
    antecedent_activated_1h: bool | None
    antecedent_activated_4h: bool | None


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (EvaluatorProfile, Fill, HypotheticalPath, ViewSample)
