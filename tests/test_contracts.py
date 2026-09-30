"""Contract/schema tests: every journaled payload conforms to its contract."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from algotrader import contracts as c
from algotrader.engine import Engine
from algotrader.risk import RiskPolicy
from algotrader.synthetic import build_fixture

KIND_TO_CONTRACT = c.EVENT_KIND_CONTRACTS

ALL_CONTRACTS = [
    c.InstrumentIdentity,
    c.MarketObservation,
    c.DataQualityState,
    c.MarketView,
    c.Scenario,
    c.TradePlan,
    c.Decision,
    c.RiskDecision,
    c.OrderIntent,
    c.Order,
    c.Fill,
    c.Position,
    c.AccountSnapshot,
    c.Run,
    c.RunProgress,
    c.RunConfig,
    c.ReplayControl,
    c.RunManifest,
]


@pytest.mark.parametrize("model", ALL_CONTRACTS, ids=lambda m: m.__name__)
def test_contract_has_json_schema_and_forbids_unknown_fields(model):
    schema = model.model_json_schema()
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False


def test_every_engine_event_roundtrips_through_its_contract():
    _, events = Engine(build_fixture()).run_all()
    kinds = set()
    for ev in events:
        model = KIND_TO_CONTRACT[ev.kind]
        parsed = model.model_validate(ev.payload)
        assert parsed.model_dump(mode="json") == ev.payload
        kinds.add(ev.kind)
    assert kinds == set(KIND_TO_CONTRACT)


def test_market_view_is_distinct_from_decision_and_marked_demo():
    _, events = Engine(build_fixture()).run_all()
    views = [e.payload for e in events if e.kind == "market_view"]
    decisions = [e.payload for e in events if e.kind == "decision"]
    assert all(v["demo"] for v in views)
    # a view carries no action; a decision references a view and a risk decision
    assert all("permitted_action" not in v for v in views)
    assert all(d["view_ref"].startswith("V") and d["risk_decision_ref"].startswith("R") for d in decisions)
    # confidence is qualitative, never numeric
    assert {v["confidence"] for v in views} <= {"LOW", "MEDIUM", "HIGH"}


def test_action_sets_distinguish_flat_and_exposed_states():
    assert c.FLAT_ACTIONS == {c.Action.LONG, c.Action.SHORT, c.Action.NO_TRADE}
    assert c.EXPOSED_ACTIONS == {c.Action.HOLD, c.Action.REDUCE, c.Action.EXIT}
    assert not (c.FLAT_ACTIONS & c.EXPOSED_ACTIONS)


def test_contracts_are_immutable_and_reject_extra_fields():
    pos = c.Position(instrument_id="X", side="FLAT", quantity=Decimal(0), average_entry_price=None)
    with pytest.raises(ValidationError):
        pos.quantity = Decimal(1)  # type: ignore[misc]
    with pytest.raises(ValidationError):
        c.Position(instrument_id="X", side="FLAT", quantity=Decimal(0), average_entry_price=None, leverage=5)


def test_cost_assumptions_record_funding_not_modeled():
    costs = c.CostAssumptions(fee_bps=Decimal(5), slippage_bps=Decimal(2))
    assert costs.funding == "NOT_MODELED"
    assert costs.label == "DEMO_PLACEHOLDER"


def test_risk_policy_cannot_exceed_1x_exposure():
    with pytest.raises(ValidationError):
        RiskPolicy(max_exposure_fraction=Decimal("1.5"))


def test_run_config_validates_fault_and_excludes_pacing():
    assert c.RunConfig().fault == c.FaultMode.NONE
    with pytest.raises(ValidationError):
        c.RunConfig(fault="explode")
    with pytest.raises(ValidationError):  # speed is operational control, not a pinned input
        c.RunConfig(speed=4)


def test_replay_control_validates_speed_and_step_budget():
    assert c.ReplayControl(paused=True, step_budget=1, speed=0).paused
    with pytest.raises(ValidationError):
        c.ReplayControl(paused=False, step_budget=0, speed=-1)
    with pytest.raises(ValidationError):
        c.ReplayControl(paused=False, step_budget=-1, speed=1)


def test_observation_times_are_explicit():
    obs = build_fixture().bars[0]
    assert obs.available_time > obs.event_time
    assert obs.available_time.tzinfo is not None
    assert obs.available_time == datetime(2026, 1, 1, 0, 1, tzinfo=UTC)
