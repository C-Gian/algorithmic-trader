"""WP-011 hand-expected MP-002 v0.3 paths (pure). Every number below is derived by hand from the fixture
construction in ``adviser3_fixtures`` (S15 2000, z 200 at confirmation; tick 0.1; historical K_cost 14 bps; r 1.2)
and, for the economics, from the independent rational reference ``mp002_reference`` - never read back from the
implementation. Synthetic engineering inputs only, not market evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction

import adviser3_fixtures as fx
import mp002_reference as ref
import pytest
from adviser3_fixtures import DAY1, DAY2, T

from algotrader.adviser.harness import run_pure

D = Decimal


def run(minutes, **kw):
    return run_pure(DAY1, minutes, eval_start=DAY2, method="v0.3", **kw)


def iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def dec(x) -> Decimal:
    return D(str(x))


def scen_steps(res, prefix="AL"):
    return [(s["env"]["clock_time"], s["transition"], s["terminal_state"]) for s in res.scenarios(prefix)]


def entry_steps(res, prefix="AL"):
    return [(e["env"]["clock_time"], e["state"], e["mode"], e["transition"], (e["reason"] or "").split(":")[0])
            for e in res.entries(prefix)]


@pytest.fixture(scope="module")
def ret_long():
    return run(fx.a3_return_long())


@pytest.fixture(scope="module")
def ret_short():
    return run(fx.mirror(fx.a3_return_long()))


# -- independent arithmetic --------------------------------------------------------------------------------------


def test_reference_bounds_exact_inward_ticks_and_separate_short_economics():
    lb = ref.bound_long(100700, 99700, 14)
    assert lb == Fraction(220340 * 100000, 22 * 10014) and str(float(lb))[:12] == "100014.52511"
    assert ref.floor_tick(lb) == Fraction(1000145, 10)
    assert ref.passes(1, D("100014.5"), 99700, 100700, 14) and not ref.passes(1, D("100014.6"), 99700, 100700, 14)
    assert ref.floor_tick(ref.bound_long(100700, 99700, 20)) == Fraction(999546, 10)  # 99954.636... -> 99954.6
    sb = ref.bound_short(99300, 100300, 14)
    assert str(float(sb))[:11] == "99985.43415" and ref.ceil_tick(sb) == Fraction(999855, 10)
    assert ref.passes(-1, D("99985.5"), 100300, 99300, 14) and not ref.passes(-1, D("99985.4"), 100300, 99300, 14)
    assert 200000 - lb != sb  # the price denominator breaks affine symmetry of the bound
    # corridor examples (MP-002 §12): R > K is empty, never reordered; exactly one valid tick
    assert ref.corridor_long(100060, D("100049.9"), 99700, 100700) is None
    assert ref.corridor_long(D("100049.9"), D("100049.9"), 99700, 100700) == (Fraction(1000499, 10),) * 2
    assert ref.corridor_long(99900, D("100049.9"), 99700, 100700) == (Fraction(99900), Fraction(1000499, 10))
    assert ref.economic_long((Fraction(99900), Fraction(1000499, 10)), 99700, 100700, 14) == \
        (Fraction(99900), Fraction(1000145, 10))
    # T = 100200 with V = 100000: no compatible price with positive risk at 14 bps / 1.2
    assert ref.economic_long(ref.corridor_long(100050, 100150, 100000, 100200), 100000, 100200, 14) is None
    # live K 14 -> 20 -> 14 on an accepted wait with R 99980: bound 100014.5 -> 99954.6 -> 100014.5
    cor = ref.corridor_long(99980, D("100049.9"), 99700, 100700)
    assert ref.economic_long(cor, 99700, 100700, 14) == (Fraction(99980), Fraction(1000145, 10))
    assert ref.economic_long(cor, 99700, 100700, 20) is None
    assert ref.economic_long(cor, 99700, 100700, 14) == (Fraction(99980), Fraction(1000145, 10))


def test_reference_clocks_mp002_example():
    c = ref.a_clocks(datetime(2025, 9, 1, 10, tzinfo=UTC), datetime(2025, 9, 1, 11, 30, tzinfo=UTC),
                     datetime(2025, 9, 1, 12, tzinfo=UTC))
    assert c["hard"].hour == 14 and c["scenario_progress"].hour == 12
    assert (c["call_progress"].hour, c["call_progress"].minute) == (12, 45)
    assert c["duration_window"] == (30, 150) and c["horizon_only_request"].hour == 14 and c["issue_allowed"]
    from algotrader.adviser.core3 import half_point

    ti, h = datetime(2025, 9, 1, 11, 30, tzinfo=UTC), datetime(2025, 9, 1, 14, tzinfo=UTC)
    assert half_point(ti, h) == c["call_progress"]
    assert half_point(ti, ti + timedelta(microseconds=3)) == ti + timedelta(microseconds=2)  # odd span rounds up


def test_reference_routing_table_rows():
    base = dict(structural=None, target_contact=False, prerequisites_ok=True, nonselection=[], immediate=[],
                corridor_nonempty=True, economic_nonempty=True)
    assert ref.route(**base) == "IMMEDIATE"
    assert ref.route(**{**base, "immediate": ["REWARD_RISK_BELOW_MINIMUM"]}) == "WAIT_PRICE"
    assert ref.route(**{**base, "immediate": ["REWARD_RISK_BELOW_MINIMUM"], "nonselection": ["EVENT"]}) \
        == "TERMINAL:NONSELECTION_GATE"  # B2: calendar/quote veto with economic failure is terminal, no RETURN
    assert ref.route(**{**base, "target_contact": True, "immediate": ["NO_ROOM_AFTER_COSTS"]}) \
        == "TERMINAL:PRE_ENTRY_TARGET_CONTACT"
    assert ref.route(**{**base, "immediate": ["NO_ROOM_AFTER_COSTS"], "corridor_nonempty": False}) \
        == "TERMINAL:EMPTY_RETURN_CORRIDOR"
    assert ref.route(**{**base, "immediate": ["NO_ROOM_AFTER_COSTS"], "economic_nonempty": False}) \
        == "TERMINAL:NO_ECONOMIC_RETURN_REGION"
    assert ref.route(**{**base, "immediate": ["AT_OR_BEYOND_INVALIDATION"]}) == "TERMINAL:IMMEDIATE_INCOMPATIBLE"
    assert ref.route(**{**base, "structural": "NO_TARGET"}) == "TERMINAL:NO_TARGET"


# -- A RETURN, LONG (MP-002 §9 rows 1-2) ---------------------------------------------------------------------------


def test_a_long_return_full_path_is_hand_expected(ret_long):
    assert scen_steps(ret_long) == [
        (iso(T(3, 30)), "BIRTH", None), (iso(T(3, 45)), "ARM", None), (iso(T(4)), "REVISE", None),
        (iso(T(4, 1)), "CONFIRM", None), (iso(T(4, 47)), "TERMINAL", "DESTINATION_REACHED")]
    birth, arm, rev, conf, term = ret_long.scenarios("AL")
    assert birth["reason"] == "FALSE_AT_OR_AFTER_RELEASE_TO_TRUE" and birth["discovery_owner"] == "OCCUPIED"
    assert dec(birth["setup"]["impulse_A"]) == 97000 and dec(birth["setup"]["impulse_B"]) == 100900
    assert dec(birth["setup"]["s15"]) == 2000 and dec(birth["setup"]["zone_halfwidth"]) == 200
    assert dec(birth["destination"]) == 100900 and birth["destination_type"] == "IMPULSE_B"
    assert birth["original_expiry"] == iso(T(5, 30))
    assert (dec(arm["trigger_level"]), dec(arm["invalidation_level"]), dec(arm["reaction_level"])) == \
        (100700, 99800, 100000)
    assert (dec(rev["trigger_level"]), dec(rev["invalidation_level"]), dec(rev["reaction_level"])) == \
        (D("100049.9"), 99700, 99900)
    assert rev["activated_at"] == iso(T(4))
    assert conf["confirmed_at"] == iso(T(4, 1)) and dec(conf["confirmation_close"]) == 100050
    assert dec(conf["confirmation_scale"]) == 2000
    assert conf["confirmed_deadline"] == iso(T(8, 1)) and conf["progress_check_at"] == iso(T(6, 1))
    # the narrative survives the call's conservative target (100700 at 04:38) until B 100900 is reached (04:47)
    assert term["reason"].startswith("DESTINATION_CONTACT") and term["discovery_owner"] == "RELEASED"
    assert entry_steps(ret_long) == [
        (iso(T(4, 1)), "WAIT_PRICE", "RETURN", "WAIT_OPEN", "IMMEDIATE_ECONOMIC_FAILURE_RETURN_CORRIDOR_USABLE"),
        (iso(T(4, 2)), "WAIT_PRICE", "RETURN", "RETURN_USABLE", "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04"),
        (iso(T(4, 2)), "ISSUED", "RETURN", "ISSUE", "call-AL-2025-09-01T04")]
    w = ret_long.entries("AL")[0]
    g = w["geometry"]
    assert w["blockers"] == ["REWARD_RISK_BELOW_MINIMUM"]
    gi, qi = ref.g_q(1, 100050, 99700, 100700)
    assert abs(Fraction(D(g["G"])) - gi) < Fraction(1, 10 ** 30) and abs(Fraction(D(g["Q"])) - qi) < Fraction(1, 10 ** 30)
    assert (gi - 14) / (qi + 14) < ref.R_MIN  # immediate economics fail at the confirmation close
    assert g["I0"] == "99700.1..100550.0" and g["corridor"] == "99900..100049.9"
    assert g["economic_fixed_k"] == "99900..100014.5" == g["economic_current"]
    assert (dec(g["R"]), dec(g["K_trigger"]), dec(g["V"]), dec(g["T_confirm"])) == \
        (99900, D("100049.9"), 99700, 100700)
    assert w["diagnostic"] == {"in_D": "true", "exclusion": None, "corridor_geometric_empty": "false",
                               "corridor_fixed_k_economic_empty": "false", "in_N": "false"}
    assert w["selected_zone"] is None and w["containing_zones"] == []
    assert w["limiting_landmark"]["type"] == "IMPULSE_B"  # the attempt's own impulse-B zone near edge 100700
    [call] = ret_long.calls()
    assert call["entry_mode"] == "RETURN" and call["issued_at"] == iso(T(4, 2))
    assert call["confirmed_at"] == iso(T(4, 1)) and call["hard_deadline_origin"] == "STRUCTURAL_CONFIRMATION_PUBLICATION"
    assert call["hard_deadline"] == iso(T(8, 1))  # confirmation + 4h, not return issue + 4h
    assert call["progress_check_at"] == "2025-09-01T06:01:30Z"  # ti + (H - ti)/2
    assert (dec(call["target"]), dec(call["target_at_confirmation"]), dec(call["invalidation"])) == \
        (100700, 100700, 99700)
    assert [dec(x) for x in call["structural_area"]] == [99900, D("100049.9")]  # return container, never unioned
    assert dec(call["issue_reference"]) == 100000 and call["trigger_minute_start"] == iso(T(4, 1))
    assert dec(call["issue_scale"]) == 2000 and call["scenario_id"] == conf["scenario_id"]
    assert call["attempt_id"] == conf["entry_attempt_id"]
    revs = ret_long.revisions(call["call_id"])
    assert revs[-1]["thesis_status"] == "TARGET_REACHED" and revs[-1]["env"]["clock_time"] == iso(T(4, 38))
    paths = {p["variant"]: p for p in ret_long.paths()}
    assert paths["PRIMARY"]["entry"]["time_start"] == iso(T(4, 3)) and dec(paths["PRIMARY"]["entry"]["price"]) == 100010
    assert paths["PRIMARY"]["exit_class"] == "TARGET" and dec(paths["PRIMARY"]["exit"]["price"]) == 100700
    assert dec(paths["ENTRY_DELAY_0"]["entry"]["price"]) == 100000  # the issue minute's own open at 04:02
    # HORIZON_ONLY: the A request is the frozen H = 08:01 plus the 60 s exit delay -> 08:02 opening boundary
    assert paths["HORIZON_ONLY"]["exit"]["time_start"] == iso(T(8, 2))
    assert paths["HORIZON_ONLY"]["profile"]["profile_id"] == "mp002.evaluation.horizon_only.v1"


def test_wait_price_is_not_a_call_view_is_structural(ret_long):
    views = [(e["env"]["clock_time"], e["table_row"], e["expected_direction"], (e["principal"] or {}).get("status"))
             for e in [x["record"] for x in ret_long.journal if x["kind"] == "market_view"]
             if T(3, 30) <= datetime.fromisoformat(e["env"]["clock_time"].replace("Z", "+00:00")) <= T(4, 50)]
    assert (iso(T(3, 30)), "WATCH_ONLY", "UNCERTAIN", None) in views
    assert (iso(T(3, 45)), "CONDITIONAL_SCENARIO", "UP", "ARMED") in views
    assert (iso(T(4, 1)), "CONDITIONAL_SCENARIO", "UP", "CONFIRMED") in views
    assert all(v["record"]["ongoing_call_id"] is None for v in ret_long.journal if v["kind"] == "market_view")
    # no call, path or NO_ENTRY exists for the WAIT period itself
    assert len(ret_long.calls()) == 1 and all(p["call_id"] == ret_long.calls()[0]["call_id"] for p in ret_long.paths())


def test_a_short_return_is_the_reflected_structure_with_separately_computed_economics(ret_short):
    assert [(t, s) for t, s, _ in scen_steps(ret_short, "AS")] == [
        (iso(T(3, 30)), "BIRTH"), (iso(T(3, 45)), "ARM"), (iso(T(4)), "REVISE"), (iso(T(4, 1)), "CONFIRM"),
        (iso(T(4, 47)), "TERMINAL")]
    w = ret_short.entries("AS")[0]
    g = w["geometry"]
    assert (dec(g["R"]), dec(g["K_trigger"]), dec(g["V"]), dec(g["T_confirm"])) == \
        (100100, D("99950.1"), 100300, 99300)
    assert g["corridor"] == "99950.1..100100"
    want = ref.economic_short(ref.corridor_short(100100, D("99950.1"), 100300, 99300), 100300, 99300, 14)
    assert want == (Fraction(999855, 10), Fraction(100100))
    assert g["economic_fixed_k"] == "99985.5..100100"
    [call] = ret_short.calls()
    assert call["direction"] == "SHORT" and call["entry_mode"] == "RETURN" and call["issued_at"] == iso(T(4, 2))
    assert (dec(call["target"]), dec(call["invalidation"])) == (99300, 100300)
    assert [dec(x) for x in call["structural_area"]] == [D("99950.1"), 100100]
    p = {x["variant"]: x for x in ret_short.paths()}["PRIMARY"]
    assert dec(p["entry"]["price"]) == 99990 and p["exit_class"] == "TARGET"


# -- MP-002 §9 rows 3-5 and the econ-empty / expiry / stall fixtures -------------------------------------------------


def test_wick_to_the_corridor_with_a_close_outside_is_no_issue():
    res = run(fx.a3_outside_then())
    assert not res.calls()
    steps = entry_steps(res)
    assert steps[1][3] == "BLOCKERS" and steps[-1][3:] == ("TERMINAL", "ORIGINAL_SETUP_DEADLINE")
    assert "CLOSE_OUTSIDE_RETURN_CORRIDOR" in res.entries("AL")[1]["blockers"]


def test_v_contact_during_wait_invalidates_the_scenario_and_ends_entry_no_path():
    res = run(fx.a3([fx.minute(100050, 100050, 99700, 100000)]))
    assert scen_steps(res)[-1] == (iso(T(4, 2)), "TERMINAL", "INVALIDATED")
    assert entry_steps(res)[-1][3:] == ("TERMINAL", "SCENARIO_TERMINAL")
    assert not res.calls() and not res.paths()


def test_cap_contact_during_wait_is_pre_entry_target_contact_not_a_profitable_path():
    res = run(fx.a3([fx.minute(100050, 100700, 100000, 100000)]))
    assert entry_steps(res)[-1] == (iso(T(4, 2)), "TERMINAL", "RETURN", "TERMINAL", "PRE_ENTRY_TARGET_CONTACT")
    assert not res.calls() and not res.paths()
    assert scen_steps(res)[-1][2] == "STALLED"  # the scenario keeps its own lifecycle


def test_initially_empty_fixed_k_economics_is_terminal_and_counted_in_n():
    res = run(fx.a3_spike_base() + fx.flat(420, 100050))
    [e] = res.entries("AL")
    assert e["reason"] == "NO_ECONOMIC_RETURN_REGION" and e["geometry"]["T_confirm"] == "100400.0"
    assert ref.economic_long(ref.corridor_long(99900, D("100049.9"), 99700, 100400), 99700, 100400, 14) is None
    assert e["diagnostic"]["in_D"] == "true" and e["diagnostic"]["in_N"] == "true"
    assert e["geometry"]["economic_fixed_k"] is None and e["geometry"]["corridor"] == "99900..100049.9"
    assert {z["type"] for z in [e["limiting_landmark"]]} <= {"PIVOT_HIGH_15M", "PIVOT_HIGH_1H", "PREV_1D_HIGH"}
    assert res.runtime.core.counters["v3"]["a_denominators"] == {"confirmations": 1, "D": 1, "N": 1, "excluded": {}}
    assert not res.calls()


def test_wait_reaching_the_original_setup_deadline_exactly_at_return_expires_before_issue():
    res = run(fx.a3_expiry_at_return())
    assert entry_steps(res)[-1] == (iso(T(5, 30)), "TERMINAL", "RETURN", "TERMINAL", "ORIGINAL_SETUP_DEADLINE")
    assert not res.calls() and not res.paths()


def test_scenario_stalled_retires_a_young_return_call_before_its_own_progress_check():
    res = run(fx.a3_stall_after_return())
    [call] = res.calls()
    assert call["issued_at"] == iso(T(5, 1)) and call["hard_deadline"] == iso(T(8, 1))
    assert call["progress_check_at"] == iso(T(6, 31))  # 05:01 + (08:01 - 05:01)/2
    assert scen_steps(res)[-1] == (iso(T(6, 1)), "TERMINAL", "STALLED")
    term = res.revisions(call["call_id"])[-1]
    assert term["thesis_status"] == "RETIRED" and term["env"]["clock_time"] == iso(T(6, 1))
    assert term["terminal_reason"].startswith("SCENARIO_TERMINAL:STALLED")
    assert term["scenario_terminal"].startswith("STALLED") and term["coverage_loss_from"] is None
    p = {x["variant"]: x for x in res.paths()}["PRIMARY"]
    assert p["exit_class"] == "GUIDANCE_RETIRED" and p["exit"]["time_start"] == iso(T(6, 2))  # 06:01 + 60 s


# -- causal caps (B4) -----------------------------------------------------------------------------------------------


def test_new_obstacle_lowers_the_cap_at_its_publication_then_return_uses_the_capped_target():
    res = run(fx.a3_cap_then_return())
    cap = [e for e in res.entries("AL") if e["transition"] == "CAP_REVISION"]
    assert len(cap) == 1 and cap[0]["env"]["clock_time"] == iso(T(5))
    hist = cap[0]["cap_history"]
    assert [(h["cap"], h["since"]) for h in hist] == [("100700.0", "2025-09-01T04:01:00+00:00"),
                                                       ("100495.0", "2025-09-01T05:00:00+00:00")]
    assert hist[1]["zone_id"].startswith("lm-pv15m-H") and dec(hist[1]["near_edge"]) == D("100495.0")
    [call] = res.calls()
    assert call["issued_at"] == iso(T(5, 1)) and dec(call["target"]) == D("100495.0")
    assert dec(call["target_at_confirmation"]) == 100700 and len(call["cap_history"]) == 2
    assert ref.passes(1, 99910, 99700, 100495, 14)  # G 58.55, Q 21.02 -> ratio 1.272


def test_cap_activation_bar_contact_is_ambiguous_never_a_target_hit():
    res = run(fx.a3_cap_activation_contact())
    assert entry_steps(res)[-1] == (iso(T(5)), "TERMINAL", "RETURN", "TERMINAL", "CAP_ACTIVATION_CONTACT_AMBIGUOUS")
    assert not res.calls() and scen_steps(res)[-1][2] == "STALLED"


def test_new_cap_not_ahead_of_the_current_price_ends_entry():
    res = run(fx.a3_cap_not_ahead())
    assert entry_steps(res)[-1] == (iso(T(5)), "TERMINAL", "RETURN", "TERMINAL", "CAP_NOT_AHEAD_NOW")
    assert not res.calls()


def test_reported_collision_anchor_at_impulse_b_reaches_the_destination_before_confirmation():
    """Smallest reported example (the WP-009 A fixture): K = anchor high = impulse B = 100240, so the confirming
    close >= K+tick needs a contact with the frozen narrative destination B first; MP-002 §3 ends the scenario before
    confirmation (implemented literally, reported for Director decision). v0.2 issues its call on the same tape."""
    from adviser_fixtures import DAY1 as D1, DAY2 as D2, a_fixture

    res = run_pure(D1, a_fixture(), eval_start=D2, method="v0.3")
    sc = res.scenarios("AL")
    assert [s["transition"] for s in sc] == ["BIRTH", "ARM", "TERMINAL"]
    assert dec(sc[1]["trigger_level"]) == dec(sc[1]["destination"]) == 100240
    assert sc[-1]["terminal_state"] == "DESTINATION_REACHED" and sc[-1]["env"]["clock_time"] == "2025-09-01T05:20:00Z"
    assert not res.calls() and len(run_pure(D1, a_fixture(), eval_start=D2).calls()) == 1
