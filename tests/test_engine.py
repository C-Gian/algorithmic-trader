"""Engine determinism, causality and DEMO fixture coverage (no database)."""

from __future__ import annotations

import json
from decimal import Decimal

from algotrader.engine import Engine, EngineState, trace_hash
from algotrader.synthetic import MISSING_BARS, build_fixture
from algotrader.validation import validate_run

# Pinned semantic trace of fixture synthetic-btc-perp-v1 / seed 20260929 /
# dummy-scripted-1.0.0. Update only deliberately when semantics change.
PINNED_TRACE_SHA256 = "3265f6041fe0d420dfcf5ae208cb19c5d99e072b302a1bd9d2b0c12ba385f226"


def semantic(events):
    return [e.semantic() for e in events]


def by_step(events, kind):
    return {e.step: e.payload for e in events if e.kind == kind}


def test_fixture_is_deterministic_and_seed_sensitive():
    assert build_fixture().content_hash() == build_fixture().content_hash()
    assert build_fixture(seed=1).content_hash() != build_fixture().content_hash()


def test_identical_runs_produce_identical_trace():
    _, a = Engine(build_fixture()).run_all()
    _, b = Engine(build_fixture()).run_all()
    assert trace_hash(semantic(a)) == trace_hash(semantic(b))


def test_trace_matches_pinned_hash():
    _, events = Engine(build_fixture()).run_all()
    assert trace_hash(semantic(events)) == PINNED_TRACE_SHA256


def test_resume_from_serialized_checkpoint_gives_identical_trace():
    engine = Engine(build_fixture())
    _, reference = engine.run_all()
    state = engine.initial_state()
    events = []
    for obs in engine.fixture.bars:
        # round-trip through JSON exactly as the worker checkpoint does
        state = EngineState.model_validate(json.loads(json.dumps(state.model_dump(mode="json"))))
        state, evs = engine.step(state, obs)
        events.extend(evs)
    assert trace_hash(semantic(events)) == trace_hash(semantic(reference))


def test_demo_fixture_exercises_required_behaviours():
    engine = Engine(build_fixture())
    _, events = engine.run_all()
    result = validate_run(
        semantic(events), len(engine.fixture.bars), Decimal("10000"), engine.fixture.instrument.instrument_id, True
    )
    assert result["passed"], result
    assert all(result["demo_coverage"].values()), result["demo_coverage"]


def test_fills_happen_only_at_next_available_bar_open():
    engine = Engine(build_fixture())
    _, events = engine.run_all()
    bars = engine.fixture.bars
    orders = {e.payload["order_id"]: e for e in events if e.kind == "order" and e.payload["status"] == "SUBMITTED"}
    fills = [e for e in events if e.kind == "fill"]
    assert fills
    for f in fills:
        order = orders[f.payload["order_ref"]]
        assert f.step == order.step + 1
        open_price = bars[f.step].open
        assert abs(Decimal(f.payload["price"]) - open_price) <= open_price * Decimal("0.0002") + Decimal("0.01")


def test_missing_data_yields_stale_view_and_blocked_entry():
    _, events = Engine(build_fixture()).run_all()
    views = by_step(events, "market_view")
    decisions = by_step(events, "decision")
    for step in MISSING_BARS:
        assert views[step]["validity"] == "STALE"
        assert views[step]["data_quality"]["status"] == "STALE"
    assert views[60]["horizons"][0]["bias"] == views[59]["horizons"][0]["bias"]  # last valid view retained
    blocked = decisions[61]
    assert blocked["proposed_action"] == "LONG" and blocked["permitted_action"] == "NO_TRADE"
    assert "data_quality_for_new_exposure" in blocked["blocking_reasons"]


def test_oversized_proposal_is_rejected_by_risk():
    _, events = Engine(build_fixture()).run_all()
    d = by_step(events, "decision")[70]
    assert d["proposed_action"] == "LONG" and d["permitted_action"] == "NO_TRADE"
    assert "exposure_cap_1x" in d["blocking_reasons"]


def test_position_management_transitions():
    _, events = Engine(build_fixture()).run_all()
    permitted = [p["permitted_action"] for p in by_step(events, "decision").values()]
    for action in ("LONG", "SHORT", "NO_TRADE", "HOLD", "REDUCE", "EXIT"):
        assert action in permitted
    plans = [(e.step, e.payload["plan_id"], e.payload["status"]) for e in events if e.kind == "trade_plan"]
    assert (8, "P0010", "ARMED") in plans and (10, "P0010", "TRIGGERED") in plans and (29, "P0010", "CLOSED") in plans
    assert (71, "P0070", "EXPIRED") in plans
