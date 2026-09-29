"""Deterministic replay engine: one step per available observation.

The engine is pure: ``step(state, observation) -> (state', events)``. It has
no clock, UI or database dependency, so real-time paper and historical
replay can share it; only the event source/clock/execution adapter differ.
Speed and persistence live in the worker and cannot influence decisions.

Per-step ordering (documented tie order):
  1. observation becomes available (bar close)
  2. data-quality state update
  3. a working order from the previous step fills at this bar's open
     (only if this bar has data; otherwise it keeps working)
  4. account marked at this bar's close (last valid close if missing)
  5. trader updates view / plans / proposal
  6. independent risk decision
  7. decision record
  8. order intent + order submission (fills no earlier than next bar open)
  9. account snapshot
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from . import __version__
from .account import AccountState, simulate_market_fill
from .contracts import (
    SCHEMA_VERSION,
    CostAssumptions,
    DataQuality,
    DataQualityState,
    Decision,
    MarketObservation,
    Order,
    OrderIntent,
    OrderStatus,
    Side,
)
from .risk import RiskPolicy, evaluate, permitted_action
from .synthetic import Fixture
from .trader import DummyTrader, Trader, TraderContext

INITIAL_COLLATERAL = Decimal("10000")
DEFAULT_COSTS = CostAssumptions(fee_bps=Decimal("5"), slippage_bps=Decimal("2"))


class EngineState(BaseModel):
    """Everything needed to resume a run exactly (persisted as checkpoint)."""

    model_config = ConfigDict(extra="forbid")

    next_step: int = 0
    next_seq: int = 0
    account: AccountState
    trader_state: dict
    pending_order: Order | None = None
    last_valid_observation_id: str | None = None
    last_valid_available_time: str | None = None
    last_valid_close: Decimal | None = None
    bars_since_valid: int = 0


@dataclass(frozen=True)
class Event:
    seq: int
    step: int
    kind: str
    sim_time: str
    payload: dict[str, Any]

    def semantic(self) -> dict[str, Any]:
        return {"seq": self.seq, "step": self.step, "kind": self.kind, "sim_time": self.sim_time, "payload": self.payload}


class Engine:
    def __init__(
        self,
        fixture: Fixture,
        trader: Trader | None = None,
        policy: RiskPolicy | None = None,
        costs: CostAssumptions = DEFAULT_COSTS,
    ) -> None:
        self.fixture = fixture
        self.trader = trader or DummyTrader()
        self.policy = policy or RiskPolicy()
        self.costs = costs

    @property
    def engine_version(self) -> str:
        return f"algotrader-{__version__}/{self.trader.engine_id}-{self.trader.engine_version}"

    def describe(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "engine_id": self.trader.engine_id,
            "engine_version": self.engine_version,
            "trader_config_version": self.trader.config_version,
            "initial_collateral": str(INITIAL_COLLATERAL),
        }

    def initial_state(self) -> EngineState:
        return EngineState(
            account=AccountState(
                instrument_id=self.fixture.instrument.instrument_id,
                initial_collateral=INITIAL_COLLATERAL,
            ),
            trader_state=self.trader.initial_state(),
        )

    def step(self, state: EngineState, obs: MarketObservation) -> tuple[EngineState, list[Event]]:
        st = state.model_copy(deep=True)
        step = st.next_step
        assert obs.bar_index == step, f"out-of-order observation {obs.bar_index} at step {step}"
        events: list[Event] = []
        t = obs.available_time.isoformat()

        def emit(kind: str, model: BaseModel, sim_time: str = t) -> None:
            events.append(
                Event(seq=st.next_seq, step=step, kind=kind, sim_time=sim_time, payload=model.model_dump(mode="json"))
            )
            st.next_seq += 1

        # 1. observation
        emit("observation", obs)

        # 2. data quality
        if obs.quality == DataQuality.OK:
            st.last_valid_observation_id = obs.observation_id
            st.last_valid_available_time = t
            st.last_valid_close = obs.close
            st.bars_since_valid = 0
            reasons: tuple[str, ...] = ()
        else:
            st.bars_since_valid += 1
            reasons = (f"observation {obs.observation_id} is {obs.quality}",)
        quality = DataQualityState(
            status=DataQuality.OK if obs.quality == DataQuality.OK else DataQuality.STALE,
            as_of=obs.available_time,
            last_valid_observation_id=st.last_valid_observation_id,
            last_valid_available_time=st.last_valid_available_time,
            bars_since_valid=st.bars_since_valid,
            reasons=reasons,
        )

        # 3. working order fills at this bar's open (information after submission)
        if st.pending_order is not None and obs.quality == DataQuality.OK:
            order = st.pending_order
            fill = simulate_market_fill(
                order, obs.open, obs.event_time, self.costs, fill_id=f"F-{order.order_id}"
            )
            emit("fill", fill, sim_time=obs.event_time.isoformat())
            st.account = st.account.apply_fill(fill)
            filled = order.model_copy(update={"status": OrderStatus.FILLED, "filled_quantity": fill.quantity})
            emit("order", filled, sim_time=obs.event_time.isoformat())
            st.pending_order = None

        # 4. mark to market
        if st.last_valid_close is not None:
            st.account = st.account.mark(st.last_valid_close)
        snapshot_before = st.account.snapshot(obs.available_time)

        # 5. trader
        out = self.trader.on_observation(
            st.trader_state,
            TraderContext(
                step=step,
                observation=obs,
                data_quality=quality,
                account=snapshot_before,
                order_pending=st.pending_order is not None,
                costs=self.costs,
            ),
        )
        st.trader_state = out.state
        emit("market_view", out.view)
        for plan in out.plan_updates:
            emit("trade_plan", plan)

        # 6. independent risk
        risk = evaluate(
            self.policy,
            out.proposal,
            st.account,
            quality,
            st.last_valid_close,
            self.fixture.instrument.quantity_step,
            st.pending_order is not None,
            obs.available_time,
            risk_decision_id=f"R{step:04d}",
        )
        emit("risk_decision", risk)

        # 7. decision
        exposed = st.account.quantity != 0
        permitted = permitted_action(out.proposal, risk, exposed)
        blocking = risk.blocking_reasons
        reason = out.proposal.reason
        if blocking:
            reason = f"{reason} | BLOCKED by risk: {', '.join(blocking)}"
        decision = Decision(
            decision_id=f"D{step:04d}",
            as_of=obs.available_time,
            view_ref=out.view.view_id,
            plan_ref=out.proposal.plan_ref,
            risk_decision_ref=risk.risk_decision_id,
            proposed_action=out.proposal.action,
            permitted_action=permitted,
            blocking_reasons=blocking,
            reason=reason,
            current_exposure=st.account.exposure(),
            target_quantity=risk.approved_target_quantity,
        )
        emit("decision", decision)

        # 8. order intent / submission
        delta = risk.approved_target_quantity - st.account.quantity
        if risk.approved and delta != 0:
            intent = OrderIntent(
                intent_id=f"I{step:04d}",
                decision_ref=decision.decision_id,
                current_quantity=st.account.quantity,
                desired_quantity=risk.approved_target_quantity,
                approved_quantity=abs(delta),
            )
            emit("order_intent", intent)
            order = Order(
                order_id=f"O{step:04d}",
                intent_ref=intent.intent_id,
                instrument_id=self.fixture.instrument.instrument_id,
                side=Side.BUY if delta > 0 else Side.SELL,
                quantity=abs(delta),
                filled_quantity=Decimal("0"),
                reduce_only=abs(risk.approved_target_quantity) < abs(st.account.quantity),
                submitted_at=obs.available_time,
                status=OrderStatus.SUBMITTED,
                status_detail="market order; fills at next available bar open",
            )
            emit("order", order)
            st.pending_order = order

        # 9. account snapshot
        emit("account", st.account.snapshot(obs.available_time))
        st.next_step = step + 1
        return st, events

    def run_all(self) -> tuple[EngineState, list[Event]]:
        state = self.initial_state()
        events: list[Event] = []
        for obs in self.fixture.bars:
            state, evs = self.step(state, obs)
            events.extend(evs)
        return state, events


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def trace_hash(events: list[dict[str, Any]]) -> str:
    """Hash of the semantic event trace (no wall-clock fields)."""
    h = hashlib.sha256()
    for ev in events:
        h.update(canonical_json(ev))
        h.update(b"\n")
    return h.hexdigest()
