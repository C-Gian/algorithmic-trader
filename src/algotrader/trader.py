"""Trader interface and the scripted DEMO dummy trader.

The ``Trader`` protocol is the interface the future real trader will
implement. ``DummyTrader`` follows a fixed script keyed by bar index; it
reads no indicators and contains no professional trading rule. Its purpose
is to exercise the contracts (views, scenarios, plans, LONG/SHORT/NO_TRADE,
HOLD/REDUCE/EXIT, risk rejection, stale data) deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from .contracts import (
    AccountSnapshot,
    Action,
    ActionProposal,
    Bias,
    CostAssumptions,
    DataQuality,
    DataQualityState,
    HorizonState,
    MarketObservation,
    MarketView,
    PlanStatus,
    QualitativeConfidence,
    Scenario,
    ScenarioKind,
    TradePlan,
    ViewValidity,
)


class TraderContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step: int
    observation: MarketObservation
    data_quality: DataQualityState
    account: AccountSnapshot
    order_pending: bool
    costs: CostAssumptions


class TraderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: dict
    view: MarketView
    plan_updates: tuple[TradePlan, ...]
    proposal: ActionProposal


class Trader(Protocol):
    engine_id: str
    engine_version: str
    config_version: str

    def initial_state(self) -> dict: ...

    def on_observation(self, state: dict, ctx: TraderContext) -> TraderOutput: ...


# ---------------------------------------------------------------------------
# Scripted dummy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScriptEntry:
    first: int
    last: int
    bias: Bias
    action: Action
    target: Decimal = Decimal("0")
    note: str = ""


D = Decimal
# DEMO script. Bar indices are arbitrary scaffolding, not signals.
SCRIPT: tuple[ScriptEntry, ...] = (
    ScriptEntry(0, 9, Bias.BALANCED, Action.NO_TRADE, note="warm-up / balanced"),
    ScriptEntry(10, 10, Bias.BULLISH, Action.LONG, D("0.5"), "scripted LONG entry"),
    ScriptEntry(11, 19, Bias.BULLISH, Action.HOLD, note="scripted hold"),
    ScriptEntry(20, 20, Bias.BULLISH, Action.REDUCE, D("0.25"), "scripted partial reduce"),
    ScriptEntry(21, 27, Bias.BULLISH, Action.HOLD, note="scripted hold"),
    ScriptEntry(28, 28, Bias.BALANCED, Action.EXIT, note="scripted exit"),
    ScriptEntry(29, 39, Bias.BALANCED, Action.NO_TRADE, note="balanced; no trade"),
    ScriptEntry(40, 40, Bias.BEARISH, Action.SHORT, D("0.5"), "scripted SHORT entry"),
    ScriptEntry(41, 49, Bias.BEARISH, Action.HOLD, note="scripted hold"),
    ScriptEntry(50, 50, Bias.BALANCED, Action.EXIT, note="scripted exit"),
    ScriptEntry(51, 60, Bias.BALANCED, Action.NO_TRADE, note="balanced; no trade"),
    ScriptEntry(61, 61, Bias.BULLISH, Action.LONG, D("0.5"), "scripted LONG during data gap (tests risk block)"),
    ScriptEntry(62, 69, Bias.UNCERTAIN, Action.NO_TRADE, note="uncertain; no trade"),
    ScriptEntry(70, 70, Bias.BULLISH, Action.LONG, D("1.5"), "scripted oversized LONG (tests 1x cap)"),
    ScriptEntry(71, 79, Bias.BALANCED, Action.NO_TRADE, note="balanced; no trade"),
    ScriptEntry(80, 80, Bias.BEARISH, Action.SHORT, D("0.4"), "scripted SHORT entry"),
    ScriptEntry(81, 89, Bias.BEARISH, Action.HOLD, note="scripted hold"),
    ScriptEntry(90, 90, Bias.BEARISH, Action.REDUCE, D("0.2"), "scripted partial reduce"),
    ScriptEntry(91, 99, Bias.BEARISH, Action.HOLD, note="scripted hold"),
    ScriptEntry(100, 100, Bias.BALANCED, Action.EXIT, note="scripted exit"),
    ScriptEntry(101, 10**9, Bias.BALANCED, Action.NO_TRADE, note="balanced; no trade"),
)
ARM_LEAD_BARS = 2
WARMUP_BARS = 5


def script_at(step: int) -> ScriptEntry:
    for entry in SCRIPT:
        if entry.first <= step <= entry.last:
            return entry
    raise LookupError(step)


def entry_steps() -> dict[int, ScriptEntry]:
    return {e.first: e for e in SCRIPT if e.action in (Action.LONG, Action.SHORT)}


class DummyState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_plan: TradePlan | None = None
    plan_filled: bool = False
    last_valid_bias: Bias | None = None
    last_valid_view_id: str | None = None


class DummyTrader:
    """Scripted, deterministic, visibly DEMO. Not a trading strategy."""

    engine_id = "dummy-scripted"
    engine_version = "1.0.0"
    config_version = "dummy-script-v1"

    def initial_state(self) -> dict:
        return DummyState().model_dump(mode="json")

    # -- helpers ---------------------------------------------------------

    def _scenarios(self, bias: Bias, as_of: datetime, step: int) -> tuple[Scenario, ...]:
        expires = as_of + timedelta(minutes=5)
        order = {
            Bias.BULLISH: (ScenarioKind.CONTINUATION, ScenarioKind.BALANCE, ScenarioKind.TRANSITION),
            Bias.BEARISH: (ScenarioKind.CONTINUATION, ScenarioKind.TRANSITION, ScenarioKind.BALANCE),
            Bias.BALANCED: (ScenarioKind.BALANCE, ScenarioKind.TRANSITION, ScenarioKind.CONTINUATION),
            Bias.UNCERTAIN: (ScenarioKind.TRANSITION, ScenarioKind.BALANCE, ScenarioKind.CONTINUATION),
        }[bias]
        direction = {Bias.BULLISH: "up", Bias.BEARISH: "down"}.get(bias, "sideways")
        out = []
        for rank, kind in enumerate(order, start=1):
            out.append(
                Scenario(
                    scenario_id=f"S{step:04d}-{kind.value}",
                    kind=kind,
                    label=f"DEMO {kind.value.lower()} ({direction})",
                    rank=rank,
                    supporting=(f"DEMO script entry for bar {step}",),
                    opposing=("DEMO: no real evidence evaluated",),
                    applicability="DEMO scripted scenario; not derived from market data",
                    expected_behavior=f"DEMO: price drifts {direction}",
                    expires_at=expires,
                    invalidation="DEMO: next script change",
                )
            )
        return tuple(out)

    def _plan(
        self, entry: ScriptEntry, status: PlanStatus, plan_id: str, as_of: datetime, ctx: TraderContext
    ) -> TradePlan:
        return TradePlan(
            plan_id=plan_id,
            status=status,
            scenario_ref=f"S{entry.first:04d}-{ScenarioKind.CONTINUATION.value}",
            direction="LONG" if entry.action == Action.LONG else "SHORT",
            eligible=True,
            eligibility_notes=("DEMO scripted plan",),
            trigger=f"DEMO: script reaches bar {entry.first}",
            invalidation="DEMO: scripted exit only (no real invalidation rule)",
            exit_logic="DEMO: scripted HOLD/REDUCE/EXIT",
            expires_at=as_of + timedelta(minutes=10),
            target_exposure_fraction=entry.target,
            max_exposure_fraction=Decimal("1"),
            cost_assumptions=ctx.costs,
        )

    # -- interface -------------------------------------------------------

    def on_observation(self, state: dict, ctx: TraderContext) -> TraderOutput:
        st = DummyState.model_validate(state)
        step = ctx.step
        obs = ctx.observation
        as_of = obs.available_time
        entry = script_at(step)
        exposed = ctx.account.position.quantity != 0
        plan_updates: list[TradePlan] = []
        view_id = f"V{step:04d}"

        # --- plan lifecycle -------------------------------------------------
        plan = st.active_plan
        if plan is not None and plan.status == PlanStatus.TRIGGERED:
            if exposed:
                st.plan_filled = True
            elif not ctx.order_pending:
                final = PlanStatus.CLOSED if st.plan_filled else PlanStatus.EXPIRED
                plan_updates.append(plan.model_copy(update={"status": final}))
                st.active_plan, st.plan_filled, plan = None, False, None

        upcoming = entry_steps().get(step + ARM_LEAD_BARS)
        if upcoming is not None and plan is None:
            plan = self._plan(upcoming, PlanStatus.ARMED, f"P{upcoming.first:04d}", as_of, ctx)
            plan_updates.append(plan)
            st.active_plan = plan

        # --- proposal ---------------------------------------------------------
        action, target, note = entry.action, entry.target, entry.note
        if action in (Action.LONG, Action.SHORT) and exposed:
            action, target, note = Action.HOLD, Decimal("0"), "script entry while exposed -> HOLD"
        elif action in (Action.HOLD, Action.REDUCE, Action.EXIT) and not exposed:
            action, target, note = Action.NO_TRADE, Decimal("0"), f"script {entry.action} while flat -> NO_TRADE"

        plan_ref = st.active_plan.plan_id if st.active_plan else None
        if action in (Action.LONG, Action.SHORT) and st.active_plan is not None:
            if st.active_plan.status == PlanStatus.ARMED:
                plan = st.active_plan.model_copy(update={"status": PlanStatus.TRIGGERED})
                plan_updates.append(plan)
                st.active_plan = plan
        if action == Action.NO_TRADE:
            plan_ref = None

        proposal = ActionProposal(
            action=action,
            plan_ref=plan_ref,
            target_exposure_fraction=target,
            reason=f"DEMO script: {note}",
        )

        # --- view ------------------------------------------------------------
        quality = ctx.data_quality
        if quality.status != DataQuality.OK:
            validity = ViewValidity.STALE
            bias = st.last_valid_bias or Bias.UNCERTAIN
            summary = (
                f"DEMO view STALE: input {quality.status}; retaining last valid view "
                f"{st.last_valid_view_id} ({bias})"
            )
            freshness = f"stale {quality.bars_since_valid} bar(s)"
        else:
            validity = ViewValidity.WARMUP if step < WARMUP_BARS else ViewValidity.VALID
            bias = entry.bias
            summary = f"DEMO scripted view: {bias}"
            freshness = "fresh"
            st.last_valid_bias = bias
            st.last_valid_view_id = view_id

        confidence = (
            QualitativeConfidence.LOW
            if validity != ViewValidity.VALID or bias in (Bias.BALANCED, Bias.UNCERTAIN)
            else QualitativeConfidence.MEDIUM
        )
        view = MarketView(
            view_id=view_id,
            instrument_id=obs.instrument_id,
            as_of=as_of,
            information_cutoff=as_of,
            input_refs=(obs.observation_id,),
            engine_id=self.engine_id,
            engine_version=self.engine_version,
            config_version=self.config_version,
            validity=validity,
            data_quality=quality,
            horizons=(
                HorizonState(
                    horizon="DEMO-scripted (1m bars)",
                    bias=bias,
                    freshness=freshness,
                    note="DEMO: scripted bias, not inferred from data",
                ),
            ),
            scenarios=self._scenarios(bias, as_of, step),
            confidence=confidence,
            expected_response="DEMO: scripted; no expectation is claimed",
            change_triggers=("DEMO: next script entry", "data quality change"),
            summary=summary,
            demo=True,
        )
        return TraderOutput(
            state=st.model_dump(mode="json"),
            view=view,
            plan_updates=tuple(plan_updates),
            proposal=proposal,
        )
