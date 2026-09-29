"""Semantic contracts shared by the engine, worker, API and artifacts.

These are minimal typed versions of the Foundation contracts. They keep
observation, interpretation (MarketView/Scenario), conditional plan
(TradePlan), decision, independent risk approval, order, fill and account
records distinct. Nothing here depends on the UI or the database.

Monetary and quantity values use Decimal so accounting is exact and the
semantic trace is byte-identical across runs and platforms.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "wp001.v1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Instrument and observations
# ---------------------------------------------------------------------------


class InstrumentIdentity(Contract):
    instrument_id: str
    venue: str
    kind: Literal["perpetual_future"] = "perpetual_future"
    base_asset: str
    quote_asset: str
    settlement_asset: str
    contract_multiplier: Decimal
    quantity_step: Decimal
    price_tick: Decimal
    synthetic: bool


class DataQuality(StrEnum):
    OK = "OK"
    MISSING = "MISSING"
    STALE = "STALE"


class MarketObservation(Contract):
    """One bar as it becomes available. Missing bars carry no prices."""

    observation_id: str
    instrument_id: str
    bar_index: int
    event_time: datetime  # bar open time
    available_time: datetime  # when the bar is known (bar close)
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: Decimal | None
    quality: DataQuality
    source: str


class DataQualityState(Contract):
    status: DataQuality
    as_of: datetime
    last_valid_observation_id: str | None
    last_valid_available_time: datetime | None
    bars_since_valid: int
    reasons: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Interpretation: MarketView and scenarios
# ---------------------------------------------------------------------------


class Bias(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    BALANCED = "BALANCED"
    UNCERTAIN = "UNCERTAIN"


class QualitativeConfidence(StrEnum):
    """Explicitly qualitative. This is not a probability."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ViewValidity(StrEnum):
    VALID = "VALID"
    STALE = "STALE"  # last valid view retained; inputs missing
    WARMUP = "WARMUP"


class ScenarioKind(StrEnum):
    CONTINUATION = "CONTINUATION"
    BALANCE = "BALANCE"
    TRANSITION = "TRANSITION"


class Scenario(Contract):
    scenario_id: str
    kind: ScenarioKind
    label: str
    rank: int
    supporting: tuple[str, ...]
    opposing: tuple[str, ...]
    applicability: str
    expected_behavior: str
    expires_at: datetime
    invalidation: str


class HorizonState(Contract):
    horizon: str
    bias: Bias
    freshness: str
    note: str


class Level(Contract):
    label: str
    price: Decimal


class MarketView(Contract):
    view_id: str
    instrument_id: str
    as_of: datetime
    information_cutoff: datetime
    input_refs: tuple[str, ...]
    engine_id: str
    engine_version: str
    config_version: str
    validity: ViewValidity
    data_quality: DataQualityState
    horizons: tuple[HorizonState, ...]
    scenarios: tuple[Scenario, ...]
    confidence: QualitativeConfidence
    relevant_levels: tuple[Level, ...] = ()
    expected_response: str
    change_triggers: tuple[str, ...]
    summary: str
    demo: bool


# ---------------------------------------------------------------------------
# Plans, decisions and risk
# ---------------------------------------------------------------------------


class Action(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


FLAT_ACTIONS = frozenset({Action.LONG, Action.SHORT, Action.NO_TRADE})
EXPOSED_ACTIONS = frozenset({Action.HOLD, Action.REDUCE, Action.EXIT})


class CostAssumptions(Contract):
    fee_bps: Decimal
    slippage_bps: Decimal
    funding: Literal["NOT_MODELED"] = "NOT_MODELED"
    label: Literal["DEMO_PLACEHOLDER"] = "DEMO_PLACEHOLDER"


class PlanStatus(StrEnum):
    ARMED = "ARMED"  # conditions stated, waiting for trigger
    TRIGGERED = "TRIGGERED"  # trigger met, action proposed to risk
    CLOSED = "CLOSED"  # position from this plan exited
    EXPIRED = "EXPIRED"  # never acted on / rejected


class TradePlan(Contract):
    """A conditional plan. A plan is not an order."""

    plan_id: str
    status: PlanStatus
    scenario_ref: str
    direction: Literal["LONG", "SHORT"]
    eligible: bool
    eligibility_notes: tuple[str, ...]
    trigger: str
    invalidation: str
    exit_logic: str
    expires_at: datetime
    target_exposure_fraction: Decimal
    max_exposure_fraction: Decimal
    cost_assumptions: CostAssumptions


class ActionProposal(Contract):
    """What the trader would like to do, before independent risk checks."""

    action: Action
    plan_ref: str | None
    target_exposure_fraction: Decimal  # of equity, unsigned; 0 means flat
    reason: str


class RiskCheck(Contract):
    name: str
    passed: bool
    detail: str


class RiskDecision(Contract):
    risk_decision_id: str
    as_of: datetime
    proposed_action: Action
    requested_target_quantity: Decimal  # signed BTC
    approved: bool
    approved_target_quantity: Decimal  # signed BTC
    approved_exposure_fraction: Decimal
    checks: tuple[RiskCheck, ...]
    blocking_reasons: tuple[str, ...]


class ExposureSummary(Contract):
    side: Literal["LONG", "SHORT", "FLAT"]
    quantity: Decimal  # signed BTC
    notional: Decimal
    exposure_fraction: Decimal


class Decision(Contract):
    decision_id: str
    as_of: datetime
    view_ref: str
    plan_ref: str | None
    risk_decision_ref: str
    proposed_action: Action
    permitted_action: Action
    blocking_reasons: tuple[str, ...]
    reason: str
    current_exposure: ExposureSummary
    target_quantity: Decimal  # signed BTC after risk approval


# ---------------------------------------------------------------------------
# Orders, fills and account
# ---------------------------------------------------------------------------


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderIntent(Contract):
    """Desired exposure change approved by risk, before it becomes an order."""

    intent_id: str
    decision_ref: str
    current_quantity: Decimal
    desired_quantity: Decimal
    approved_quantity: Decimal  # unsigned size of the change


class Order(Contract):
    order_id: str
    intent_ref: str
    instrument_id: str
    side: Side
    quantity: Decimal
    filled_quantity: Decimal
    order_type: Literal["MARKET"] = "MARKET"
    reduce_only: bool
    submitted_at: datetime
    status: OrderStatus
    status_detail: str = ""


class Fill(Contract):
    fill_id: str
    order_ref: str
    instrument_id: str
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal
    fill_time: datetime
    liquidity: Literal["TAKER"] = "TAKER"
    model: str


class Position(Contract):
    instrument_id: str
    side: Literal["LONG", "SHORT", "FLAT"]
    quantity: Decimal  # signed BTC
    average_entry_price: Decimal | None


class AccountSnapshot(Contract):
    as_of: datetime
    collateral_balance: Decimal  # initial + realized - fees
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees_paid: Decimal
    equity: Decimal
    mark_price: Decimal | None
    position: Position
    exposure_notional: Decimal
    exposure_fraction: Decimal
    funding: Literal["NOT_MODELED"] = "NOT_MODELED"


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.CANCELLED, RunStatus.FAILED})


class FaultMode(StrEnum):
    """Controlled worker interruption used to demonstrate recovery/failure."""

    NONE = "none"
    CRASH_ONCE = "crash_once"  # worker dies mid-step on attempt 1 only
    CRASH_ALWAYS = "crash_always"  # worker dies on every attempt -> failed


class RunConfig(Contract):
    fixture_id: str = "synthetic-btc-perp-v1"
    seed: int = 20260929
    # Replay speed in bars per second; 0 means as fast as possible.
    # Speed only affects pacing, never decisions.
    speed: float = Field(default=4.0, ge=0, le=1000)
    fault: FaultMode = FaultMode.NONE
    fault_at_step: int = Field(default=45, ge=0)


class RunProgress(Contract):
    steps_done: int
    total_steps: int
    sim_time: datetime | None
    heartbeat_at: datetime | None
    elapsed_seconds: float | None


class Run(Contract):
    run_id: str
    status: RunStatus
    config: RunConfig
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancel_requested: bool
    attempt: int
    max_attempts: int
    recovery_log: tuple[dict, ...]
    error: str | None
    progress: RunProgress


class ArtifactRef(Contract):
    name: str
    path: str
    sha256: str
    rows: int | None
    media_type: str


class RunManifest(Contract):
    schema_version: str
    run_id: str
    labels: tuple[str, ...]
    status: RunStatus
    engine_id: str
    engine_version: str
    code_version: str | None
    config: RunConfig
    config_hash: str
    fixture: dict
    instrument: InstrumentIdentity
    assumptions: dict
    risk_policy: dict
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    steps_processed: int
    total_steps: int
    attempts: int
    recovery_log: tuple[dict, ...]
    error: str | None
    semantic_trace_hash: str
    event_count: int
    validation: dict
    artifacts: tuple[ArtifactRef, ...]
