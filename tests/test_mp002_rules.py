"""WP-011 MP-002 B1-B7 / §12 collision fixtures, invariance and direct restore (pure). Hand-expected outcomes from
the fixture construction (see ``adviser3_fixtures``); dispatch-level fixtures that alter state between two dispatches
are explicitly white-box and say so. Synthetic engineering inputs only."""

from __future__ import annotations

import dataclasses
import json
from datetime import timedelta
from decimal import Decimal

import adviser3_fixtures as fx
import pytest
from adviser3_fixtures import DAY1, DAY2, T
from adviser_fixtures import box_fixture

from algotrader.adviser import methods
from algotrader.adviser.core import AdviserError, Quote
from algotrader.adviser.core3 import CallV3, Scen
from algotrader.adviser.harness import build_events, make_runtime, run_pure, temporal_for
from algotrader.adviser.identity import live_profile
from algotrader.adviser.runtime3 import AdviserRuntimeV3
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

D = Decimal
V03 = methods.get("v0.3")


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def params(k):
    return dataclasses.replace(V03.params(), hist_k_bps=D(k))


def run(minutes, **kw):
    return run_pure(DAY1, minutes, eval_start=DAY2, method="v0.3", **kw)


def normalized(journal, kinds=("scenario", "market_view", "landmark")):
    """Structural content without the economic envelope (method/profile hashes, sequences, cursors)."""
    out = []
    for e in journal:
        if e["kind"] in kinds:
            r = {k: v for k, v in e["record"].items() if k != "env"}
            out.append((e["kind"], e["record"]["env"]["clock_time"], json.dumps(r, sort_keys=True)))
    return out


# -- B1 / cost invariance -------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def three_costs():
    mins = fx.a3_return_long()
    return {k: run(mins, params=params(k)) for k in (2, 14, 40)}


def test_cost_change_alone_keeps_normalized_structural_lineage_identical(three_costs):
    """K 2 bps -> IMMEDIATE issue at confirmation; 14 -> WAIT then RETURN; 40 -> no economic return region. Scenario,
    landmark and MarketView content (envelope excluded) is identical; only entry/call/evaluator outputs differ."""
    lo, mid, hi = three_costs[2], three_costs[14], three_costs[40]
    assert normalized(lo.journal) == normalized(mid.journal) == normalized(hi.journal)
    assert [c["entry_mode"] for c in lo.calls()] == ["IMMEDIATE"]
    assert lo.calls()[0]["issued_at"] == iso(T(4, 1))
    assert [c["entry_mode"] for c in mid.calls()] == ["RETURN"]
    assert hi.calls() == [] and hi.entries("AL")[-1]["reason"] == "NO_ECONOMIC_RETURN_REGION"
    # the confirmation reference, hard deadline and progress check are cost-independent
    confs = [[s for s in r.scenarios("AL") if s["transition"] == "CONFIRM"][0] for r in (lo, mid, hi)]
    assert len({(c["confirmed_at"], c["confirmed_deadline"], c["progress_check_at"], c["confirmation_close"])
                for c in confs}) == 1
    # B1: no cost profile births a second A owner before the common structural release; same latch states
    for r in (lo, mid, hi):
        assert [s["transition"] for s in r.scenarios("AL")].count("BIRTH") == 1
        assert r.runtime.core.latch == mid.runtime.core.latch
    # immediate geometry is the exact v0.2 width around the confirmation close (never widened)
    assert lo.calls()[0]["structural_area"] == ["99700.1", "100550.0"]


def test_evaluator_disabled_leaves_every_professional_record_identical():
    mins = fx.a3_return_long()
    on, off = run(mins), run(mins, evaluator=False)
    assert [e["digest"] for e in on.journal] == [e["digest"] for e in off.journal]
    assert off.records == []


def test_appended_future_never_changes_earlier_records():
    mins = fx.a3_return_long()
    full = run(mins)
    cut = fx.index_of(T(4, 20))
    short = run(mins[:cut])
    limit = iso(T(4, 19))
    a = [e["digest"] for e in full.journal if e["clock_time"] <= limit]
    b = [e["digest"] for e in short.journal if e["clock_time"] <= limit]
    assert a == b and len(a) > 20


@pytest.mark.parametrize("cuts", [{1, 7, 1680 * 3 + 1, 1681 * 3}, {5000, 5001, 5002, 5003}])
def test_direct_restore_at_arbitrary_cursors_reproduces_every_v03_output(cuts):
    mins = fx.a3_return_long()
    base = run(mins)
    events, cov = build_events(DAY1, mins)
    rt = make_runtime(eval_start=DAY2, method="v0.3")
    temporal = temporal_for(cov)
    rt.attach(temporal)
    journal, records = [], []
    for i, e in enumerate(events):
        if i in cuts:
            j, r = rt.take()
            journal += j
            records += r
            temporal = te.unpack(*te.pack(temporal))
            raw = canonical(rt.encode())
            assert json.loads(raw)["format"] == "algotrader.adviser-runtime.v3"
            assert json.loads(raw)["core"]["format"] == "algotrader.adviser-state.v3"
            rt = AdviserRuntimeV3.decode(json.loads(raw), rt.core.cfg, make_runtime(eval_start=DAY2, method="v0.3").ev)
            assert canonical(rt.encode()) == raw
            rt.attach(temporal)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    end = DAY1 + len(mins) * timedelta(minutes=1)
    temporal.finish(end)
    rt.finish(end)
    j, r = rt.take()
    journal += j
    records += r
    assert [e["digest"] for e in journal] == [e["digest"] for e in base.journal]
    assert [x["digest"] for x in records] == [x["digest"] for x in base.records]


def test_v02_state_never_decodes_as_v03_and_vice_versa():
    a = make_runtime(eval_start=DAY2, method="v0.2")
    b = make_runtime(eval_start=DAY2, method="v0.3")
    with pytest.raises(ValueError):
        AdviserRuntimeV3.decode(json.loads(canonical(a.encode())), b.core.cfg, None if b.ev is None else b.ev)
    from algotrader.adviser.runtime import AdviserRuntime

    with pytest.raises(ValueError):
        AdviserRuntime.decode(json.loads(canonical(b.encode())), a.core.cfg, a.ev)


# -- B2: simultaneous blockers at confirmation ---------------------------------------------------------------------


def test_nonselection_veto_with_economic_failure_is_terminal_never_return():
    """Dislocation (trade vs mark 30 bps > 25) at the otherwise RETURN-routable confirmation: terminal nonselection,
    every blocker recorded; the structural scenario survives."""
    mins = fx.a3_return_long()
    i = fx.index_of(T(4))
    m = mins[i]
    mins[i] = fx.Minute(m.o, m.h, m.lo, m.c, mark=m.c * D("0.997"))
    res = run(mins)
    [e] = res.entries("AL")
    assert e["transition"] == "TERMINAL" and e["reason"] == "NONSELECTION_GATE:DISLOCATION_TRADE_MARK"
    assert "REWARD_RISK_BELOW_MINIMUM" in e["blockers"] and "DISLOCATION_TRADE_MARK" in e["blockers"]
    assert not res.calls()
    assert [s["transition"] for s in res.scenarios("AL")][-2:] == ["CONFIRM", "TERMINAL"]
    assert res.scenarios("AL")[-1]["terminal_state"] == "DESTINATION_REACHED"


def test_return_selection_with_an_occupied_slot_consumes_the_attempt_without_retry():
    """White-box dispatch-level fixture: an unrelated ongoing call occupies the slot from 04:01:30; the first fully
    actionable return at 04:02 is rejected SLOT_OCCUPIED and later better prices never retry it."""
    st = fx.Stepper(fx.a3_return_long())
    st.run_until(T(4, 1))
    assert st.core.waits
    st.core.call = CallV3(cid="call-occupier", aid="x#entry", family="B", d=1, origin="HISTORICAL_MODELED",
                          issued_at=T(4, 1), issue_seq=0, trigger_start=T(4), ref=D(100000), v=D(90000),
                          t=D(110000), target_type="LANDMARK", limiting=None, s15=D(2000),
                          area=(D(99000), D(101000)), expected=(30, 240), min_residual=30,
                          hard_deadline=T(10), progress_at=T(7), premise_kind="X", premise_level=D(1),
                          scenario_id="x", confirmed_at=T(4, 1), t_confirm=D(110000))
    st.finish()
    ent = [e for e in st.kinds("entry_attempt") if e["scenario_id"].startswith("AL")]
    assert [(e["transition"], e["reason"]) for e in ent][-2:] == [
        ("RETURN_USABLE", ent[-2]["reason"]), ("REJECT", "SLOT_OCCUPIED")]
    assert not [c for c in st.kinds("call") if c["attempt_id"].startswith("AL")]


# -- straddling intervals (delayed receipts) --------------------------------------------------------------------------


def test_contact_in_an_interval_straddling_the_confirmation_publication_is_unassessable():
    """The confirming minute [04:00,04:01) is received at 04:01:30 (confirmation published then); [04:01,04:02)
    straddles that publication and its high reaches T_confirm 100700: PRE_ENTRY_CONTACT_TIME_AMBIGUOUS."""
    mins = fx.a3([fx.minute(100050, 100700, 100000, 100000)])
    evs = fx.delayed_events(mins, {fx.index_of(T(4)): 30})
    st = fx.Stepper(mins, events=evs)
    st.finish()
    conf = [s for s in st.kinds("scenario") if s["transition"] == "CONFIRM"][0]
    assert conf["confirmed_at"] == "2025-09-01T04:01:30Z"
    ent = [e for e in st.kinds("entry_attempt") if e["scenario_id"].startswith("AL")]
    assert ent[-1]["transition"] == "TERMINAL" and ent[-1]["reason"] == "PRE_ENTRY_CONTACT_TIME_AMBIGUOUS"
    assert not st.kinds("call")


def test_contact_in_an_interval_straddling_a_level_publication_is_unassessable():
    """Dispatch-level unit (white-box): with recorded receipts a pre-confirmation V revision can be published inside
    a minute (e.g. 04:00:30). A minute [04:00,04:01) admitted later that touches the revised V straddles that
    publication: UNASSESSABLE, never a certified invalidation; an untouched straddling minute cannot confirm either."""
    from algotrader.adviser.measures import Bar

    st = fx.Stepper(fx.a3_return_long())
    st.run_until(T(3, 59))
    core = st.core
    [s] = [x for x in core.scen.values() if x.family == "A"]
    assert s.status == "ARMED"
    s.v_hist.append(["2025-09-01T04:00:30+00:00", str(D(99700))])
    s.v_t, s.arm_at = D(99700), T(4) + timedelta(seconds=30)
    m = Bar(T(4), T(4, 1), D(99950), D(100050), D(99700), D(100050), D(1), T(4, 1), "m")
    core._scen_intervals([m], T(4, 1))
    assert s.sid not in core.scen
    term = [e["record"] for e in core.journal if e["kind"] == "scenario"][-1]
    assert term["terminal_state"] == "UNASSESSABLE" and term["reason"] == "LEVEL_REVISION_CONTACT_TIME_AMBIGUOUS"
    assert core._confirmations([m], T(4, 1)) == []


# -- B3: live temporary cost emptiness -------------------------------------------------------------------------------


def _q(st, at, bid, ask):
    st.rt.quote(Quote(D(bid), D(ask), at, at, "BTC-USDT-SWAP", "q" * 64), at)


def test_live_wait_recovers_from_temporary_cost_emptiness_and_never_issues_while_blocked():
    """LIVE_QUOTED: confirmation with a zero-spread quote (K 14) -> WAIT; at 04:02 a 240-wide quote makes K 26 bps and
    the economic intersection empty (TEMPORARY_COST_BLOCKED, wait kept); at 04:03 K returns to 14 and the fresh
    return issues. The corridor, V and T never change."""
    mins = fx.a3([fx.minute(100050, 100050, 99990, 100000), fx.minute(100000, 100005, 99995, 100000)])
    st = fx.Stepper(mins, profile=live_profile())
    for k in range(-90, 0):
        at = T(4) + timedelta(minutes=k)
        _q(st, at, "99950", "99950")
    _q(st, T(4, 1), "100050", "100050")
    _q(st, T(4, 2), "99880", "100120")
    _q(st, T(4, 3), "100000", "100000")
    st.finish()
    ent = [e for e in st.kinds("entry_attempt") if e["scenario_id"].startswith("AL")]
    steps = [(e["env"]["clock_time"], e["transition"]) for e in ent]
    assert steps[0] == (iso(T(4, 1)), "WAIT_OPEN")
    blocked = [e for e in ent if e["transition"] == "BLOCKERS" and e["env"]["clock_time"] == iso(T(4, 2))]
    assert blocked and "TEMPORARY_COST_BLOCKED" in blocked[0]["blockers"]
    assert blocked[0]["geometry"]["economic_current"] is None and blocked[0]["geometry"]["T_current"] == "100700.0"
    [call] = [c for c in st.kinds("call") if c["attempt_id"].startswith("AL")]
    assert call["issued_at"] == iso(T(4, 3)) and call["entry_mode"] == "RETURN"
    assert call["actionability"]["side_price_source"] == "MEASURED_ASK"


# -- post-issue collisions (B5 / B6) ----------------------------------------------------------------------------------


def test_certified_call_protective_contact_keeps_precedence_over_the_same_dispatch_scenario_terminal():
    post = [fx.minute(100050, 100050, 99990, 100000), fx.minute(100000, 100010, 100000, 100010),
            fx.minute(100010, 100010, 99650, 99700)]
    res = run(fx.a3(post))
    [call] = res.calls()
    term = res.revisions(call["call_id"])[-1]
    assert term["thesis_status"] == "INVALIDATED" and term["terminal_reason"].startswith("CERTIFIED_INVALIDATION")
    assert term["scenario_terminal"] is None
    assert res.scenarios("AL")[-1]["terminal_state"] == "INVALIDATED"
    p = {x["variant"]: x for x in res.paths()}["PRIMARY"]
    assert p["exit_class"] == "STOP"


def test_monitoring_gap_after_issue_censors_from_the_first_missing_interval():
    post = [fx.minute(100050, 100050, 99990, 100000), fx.minute(100000, 100010, 100000, 100010)]
    post += fx.flat(5, 100010)
    mins = fx.a3(post)
    gap_i = fx.index_of(T(4, 6))
    mins[gap_i] = fx.Minute(mins[gap_i].o, mins[gap_i].h, mins[gap_i].lo, mins[gap_i].c, gap=True)
    res = run(mins)
    [call] = res.calls()
    term = res.revisions(call["call_id"])[-1]
    assert term["thesis_status"] == "UNASSESSABLE" and "GAP" in term["terminal_reason"]
    p = {x["variant"]: x for x in res.paths()}["PRIMARY"]
    assert p["status"] == "CENSORED" and p["censored_from"] == iso(T(4, 6))
    assert res.scenarios("AL")[-1]["terminal_state"] == "UNASSESSABLE"


def test_same_call_entry_closes_and_reopens_under_one_id_and_one_path():
    post = [fx.minute(100050, 100050, 99990, 100000), fx.minute(100000, 100030, 100000, 100030),
            fx.minute(100030, 100030, 100000, 100000)] + fx.flat(3, 100000)
    res = run(fx.a3(post, tail_price=100000))
    [call] = res.calls()
    st = [r["entry_status"] for r in res.revisions(call["call_id"])]
    assert "CLOSED" in st and "AVAILABLE" in st[st.index("CLOSED"):]
    assert len([p for p in res.paths() if p["variant"] == "PRIMARY"]) == 1


# -- B/C one-shot entry with a persistent structural scenario --------------------------------------------------------


def test_bc_economic_rejection_consumes_entry_and_the_scenario_persists():
    res = run(box_fixture("B"), params=params(500))
    ent = res.entries("BL")
    assert [e["transition"] for e in ent] == ["TERMINAL"] and "NO_ROOM_AFTER_COSTS" in ent[0]["blockers"]
    sc = res.scenarios("BL")
    assert [s["transition"] for s in sc][:4] == ["BIRTH", "ARM", "CONFIRM", "TERMINAL"]
    assert sc[2]["env"]["clock_time"] == ent[0]["env"]["clock_time"]  # the child is evaluated at confirmation
    assert sc[3]["env"]["clock_time"] > sc[2]["env"]["clock_time"]  # the confirmed narrative outlives the child
    assert not res.calls()


def test_box_retirement_uses_the_structural_b_episode_even_after_a_rejected_child():
    """White-box: a confirmed B scenario whose child was consumed still owns the opposite far-edge close rule."""
    from algotrader.adviser.core3 import AdviserCoreV3
    from algotrader.adviser.measures import Bar

    res = run(box_fixture("B"), params=params(500), stop_after=None)
    core: AdviserCoreV3 = res.runtime.core
    from algotrader.adviser.core import Box

    t = T(10)
    core.box = Box("box-x", D(100000), D(101800), D(100900), D(600), D(60), T(9), 1, T(13), ["s"])
    core.scen["BL-x"] = Scen(sid="BL-x", family="B", d=1, owner="box-x", born_at=T(9), born_seq=1, sources=["s"],
                             setup_deadline=T(10), s15=D(600), z=D(60), status="CONFIRMED", entry="TERMINAL",
                             k_t=D(101860), v_t=D(101720),
                             conf_at=T(9, 30), conf_deadline=T(15, 30), progress_at=T(12, 30),
                             premise_t=D(101740), dest_t=D(103600))
    core._box_close_flags(Bar(T(9, 45), t, D(100000), D(100000), D(99900), D(99930), D(1), t, "b"), t)
    assert core.box is None and "BL-x" not in core.scen


# -- view table and capacity (white-box tables) ------------------------------------------------------------------


def _core_with(scens, monkeypatch):
    from algotrader.adviser.core3 import AdviserCoreV3

    core: AdviserCoreV3 = make_runtime(eval_start=DAY2, method="v0.3").core
    monkeypatch.setattr(core, "ready_15m", lambda t: True)
    monkeypatch.setattr(core, "ready_1h", lambda t: True)
    for s in scens:
        core.scen[s.sid] = s
    return core


def _scen(sid, d, status, fam="A"):
    return Scen(sid=sid, family=fam, d=d, owner=sid, born_at=T(3), born_seq=1, sources=["s"], setup_deadline=T(5),
                s15=D(10), z=D(1), status=status, k_t=D(100) * d, v_t=D(90) * d, dest_t=D(120) * d,
                conf_at=T(4) if status == "CONFIRMED" else None,
                conf_deadline=T(8) if status == "CONFIRMED" else None)


def test_view_total_table_is_structural_and_never_erased_by_economics(monkeypatch):
    core = _core_with([_scen("AL-1", 1, "CONFIRMED"), _scen("AS-1", -1, "ARMED")], monkeypatch)
    assert core.compute_view(T(4))["expected_direction"] == "UNCERTAIN"  # opposing supported scenarios
    core = _core_with([_scen("AL-1", 1, "CONFIRMED"), _scen("AS-2", -1, "WATCH")], monkeypatch)
    v = core.compute_view(T(4))
    assert (v["table_row"], v["expected_direction"], v["conditional"]) == ("CONDITIONAL_SCENARIO", "UP", True)
    assert [a["scenario_id"] for a in v["alternatives"]] == ["AS-2"]  # an opposing WATCH is an alternative
    core = _core_with([_scen("AL-3", 1, "WATCH")], monkeypatch)
    assert core.compute_view(T(4))["table_row"] == "WATCH_ONLY"
    assert core.compute_view(T(4))["ongoing_call_id"] is None


def test_scenario_capacity_breach_is_an_invariant_error_never_an_economic_eviction(monkeypatch):
    core = _core_with([_scen(f"AL-{i}", 1, "CONFIRMED") for i in range(18)], monkeypatch)
    core._capacity_check()
    core.scen["AL-x"] = _scen("AL-x", 1, "CONFIRMED")
    with pytest.raises(AdviserError, match="SCENARIO_CAPACITY_INVARIANT"):
        core._capacity_check()


# -- zones: crossing V and monotone caps (white-box dispatch-level) --------------------------------------------------


def _inject_high(core, lid, price, z, t):
    from algotrader.adviser.core import Landmark

    core.landmarks[lid] = Landmark(lid, "PIVOT_HIGH_15M", "HIGH", D(price), D(z), D(650), "15m", ["src"], t, t,
                                   core.seq, t + timedelta(hours=24))


def test_new_zone_across_v_blocks_containing_ticks_without_a_fabricated_cap_and_retired_caps_never_widen():
    st = fx.Stepper(fx.a3(fx.flat(3, 100070) + [fx.minute(100070, 100070, 99950, 99950)] + fx.flat(5, 99950)))
    st.run_until(T(4, 2))
    # (a) a zone crossing V (near 99650 <= V 99700 < far 99960) leaves the cap unchanged and blocks the containing
    # corridor ticks (a later close at 99950 inside it is BLOCKED_BY_ZONE)
    _inject_high(st.core, "lm-test-across-v", 99805, 155, T(4, 2))
    st.core._touch()
    st.run_until(T(4, 3))
    w = next(iter(st.core.waits.values()))
    assert w.cap == D("100700.0") and "lm-test-across-v" in w.seen
    # (b) a nearer obstacle (near edge 100500) caps T and its later retirement never restores the farther cap; the
    # fixed-K economics stay nonempty (bound (100500 + 1.2*99700)/(2.2*1.0014) = 99923.6...)
    _inject_high(st.core, "lm-test-cap", 100600, 100, T(4, 3))
    st.run_until(T(4, 4))
    assert w.cap == D("100500.0")
    del st.core.landmarks["lm-test-cap"]
    st.run_until(T(4, 6))
    assert w.cap == D("100500.0") and st.core.waits
    st.finish()
    ent = [e for e in st.kinds("entry_attempt") if e["scenario_id"].startswith("AL")]
    assert any("BLOCKED_BY_ZONE" in e["blockers"] for e in ent if e["transition"] == "BLOCKERS")
    assert not [c for c in st.kinds("call") if c["attempt_id"].startswith("AL")]


def test_spent_high_before_reaction_keeps_v02_precedence():
    mins = fx.a3_base()
    i = fx.index_of(T(3, 30))
    mins[i:i + 15] = fx.bar15(D(100700), D(101200), D(100000), D("100049.9"))
    res = run(mins + fx.flat(400, D("100049.9")))
    sc = res.scenarios("AL")
    assert [s["transition"] for s in sc] == ["BIRTH", "TERMINAL"]
    assert sc[-1]["reason"] == "SPENT_HIGH_BEYOND_B_BEFORE_REACTION" and sc[-1]["discovery_owner"] == "RELEASED"
