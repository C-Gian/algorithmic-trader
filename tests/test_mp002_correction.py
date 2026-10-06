"""WP-011 correction (Director review F1/F2) on reachable pure orchestration, not helper calls alone.

F1: a structural B episode alive at dispatch entry owns that dispatch's opposite far-edge box retirement even when the
simultaneous protective / V contact terminates it earlier in the same dispatch (contact precedence kept).
F2: an hourly view sample whose principal is already CONFIRMED at the sample cutoff records that activation; an ARMED
principal is credited only by its own causally later CONFIRM.

Synthetic engineering inputs only (``adviser_fixtures.box_fixture`` / ``adviser3_fixtures``); no market evidence."""

from __future__ import annotations

import dataclasses
import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import adviser3_fixtures as fx
import pytest
from adviser3_fixtures import DAY1, DAY2, T
from adviser_fixtures import box_fixture

from algotrader.adviser import compare, methods
from algotrader.adviser.core3 import Scen
from algotrader.adviser.harness import build_events, make_runtime, run_pure, temporal_for
from algotrader.adviser.measures import Bar
from algotrader.adviser.runtime3 import AdviserRuntimeV3
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

D = Decimal
V03 = methods.get("v0.3")
HIGH_COST = dataclasses.replace(V03.params(), hist_k_bps=D(500))  # B child economically rejected at confirmation


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def run(minutes, **kw):
    return run_pure(DAY1, minutes, eval_start=DAY2, method="v0.3", **kw)


def restored_run(minutes, window, params=None):
    """The pure fold with a direct encode -> decode restore before EVERY event available inside ``window``."""
    events, cov = build_events(DAY1, minutes)
    lo, hi = window
    cuts = {i for i, e in enumerate(events) if lo <= e.available_time <= hi}
    assert len(cuts) >= 3
    rt = make_runtime(eval_start=DAY2, method="v0.3", params=params)
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
            rt = AdviserRuntimeV3.decode(json.loads(raw), rt.core.cfg,
                                         make_runtime(eval_start=DAY2, method="v0.3", params=params).ev)
            assert canonical(rt.encode()) == raw
            rt.attach(temporal)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    end = DAY1 + len(minutes) * timedelta(minutes=1)
    temporal.finish(end)
    rt.finish(end)
    j, r = rt.take()
    return journal + j, records + r


# -- F1 fixtures ------------------------------------------------------------------------------------------------------
# box [100000, 101800], z 60 (L - z 99940); B LONG born 04:30, armed 04:45, confirmed 04:46 (V 101720). Prices hold
# 101860 until the last minute of the 15m bar [04:45, 05:00).


def collision(last=(101860, 101860, 99930, 99930), wick_at=None, mirror=False):
    """``last``: the [04:59, 05:00) minute; the default contacts V AND closes the 15m bar at 99930 < L - z.
    ``wick_at``: an earlier minute that only wicks to 99930 (closes back at 101860)."""
    m = box_fixture("B")
    first, end = fx.index_of(T(4, 46)), fx.index_of(T(5)) - 1
    for i in range(first, end):
        m[i] = fx.minute(101860, 101860, 101860, 101860)
    if wick_at is not None:
        m[fx.index_of(wick_at)] = fx.minute(101860, 101860, 99930, 101860)
    m[end] = fx.minute(*last)
    return fx.mirror(m) if mirror else m


def at(st_or_journal, t):
    j = st_or_journal.journal if hasattr(st_or_journal, "journal") else st_or_journal
    return [e for e in j if e["clock_time"] == iso(t)]


@pytest.mark.parametrize("mirror", [False, True], ids=["B_LONG", "B_SHORT"])
@pytest.mark.parametrize("params", [None, HIGH_COST], ids=["child_issued", "child_rejected"])
def test_simultaneous_v_contact_and_opposite_edge_close_retires_the_box_once(mirror, params):
    d, opp = ("LONG", "SHORT") if not mirror else ("SHORT", "LONG")
    st = fx.Stepper(collision(mirror=mirror), params=params)
    st.run_until(T(4, 59))
    old = st.core.box.bid
    [b] = [s for s in st.core.scen.values() if s.family == "B"]
    assert (b.status, b.owner, b.entry) == ("CONFIRMED", old, "ISSUED" if params is None else "TERMINAL")
    st.run_until(T(5))
    ev = at(st, T(5))
    kinds = [(e["kind"], e["record"].get("transition") or e["record"].get("thesis_status")
              or e["record"].get("category")) for e in ev]
    # protective call/scenario contact keeps precedence; the retirement follows in the same dispatch
    term = next(i for i, e in enumerate(ev) if e["kind"] == "scenario" and e["record"]["scenario_id"] == b.sid)
    assert ev[term]["record"]["terminal_state"] == "INVALIDATED"
    assert ev[term]["record"]["reason"].startswith("V_CONTACT:")
    if params is None:
        inv = next(i for i, e in enumerate(ev) if e["kind"] == "call_revision")
        assert ev[inv]["record"]["thesis_status"] == "INVALIDATED" and inv < term
        assert ev[inv]["record"]["terminal_reason"].startswith("CERTIFIED_INVALIDATION_CONTACT:")
    else:
        assert not st.kinds("call")
    retired = [i for i, e in enumerate(ev) if e["kind"] == "observation"
               and e["record"].get("category") == "BOX_RETIRED"]
    assert len(retired) == 1 and retired[0] > term, kinds
    r = ev[retired[0]]["record"]
    assert r["values"]["box_id"] == old and r["env"]["lineage"] == [old]
    assert r["values"]["reason"].startswith(f"OPPOSITE_FAR_EDGE_CLOSE_DURING_B_{d}:")
    assert "15m/2025-09-01T04:45:00" in r["values"]["reason"]
    # no episode is born from the retired box (neither the opposite B nor any C), now or later
    assert not [e for e in st.kinds("scenario") if e["owner_id"] == old and e["transition"] == "BIRTH"
                and e["env"]["clock_time"] >= iso(T(5))]
    # retirement sets NEED_FALSE; the unchanged box-birth rule then sees this close's non-compression phase -> READY
    assert st.core.box is None and st.core.box_token == "READY"
    st.finish()
    assert not [e for e in st.kinds("scenario") if e["owner_id"] == old and e["family"] == "B"
                and e["direction"] == opp]
    assert len([e for e in st.kinds("observation") if e.get("category") == "BOX_RETIRED"
                and e["values"]["box_id"] == old]) == 1


@pytest.mark.parametrize("mirror", [False, True], ids=["B_LONG", "B_SHORT"])
def test_returned_inside_close_above_the_far_edge_never_retires(mirror):
    """The same V-contact minute with the 15m close back inside the box (100500 > L - z): B ends on V contact, the
    box is kept, no retirement."""
    st = fx.Stepper(collision(last=(101860, 101860, 99930, 100500), mirror=mirror))
    st.run_until(T(4, 59))
    old = st.core.box.bid
    st.run_until(T(5))
    assert [e["record"]["reason"].split(":")[0] for e in at(st, T(5)) if e["kind"] == "scenario"
            and e["record"]["transition"] == "TERMINAL"] == ["V_CONTACT"]
    assert not [e for e in at(st, T(5)) if e["record"].get("category") == "BOX_RETIRED"]
    assert st.core.box is not None and st.core.box.bid == old


@pytest.mark.parametrize("mirror", [False, True], ids=["B_LONG", "B_SHORT"])
def test_earlier_wick_alone_never_retires(mirror):
    """An earlier minute only wicks below L - z (V contact ends B at 04:51); the 15m bar closes at 101860: the wick is
    not a 15m opposite-edge close and the box is kept."""
    st = fx.Stepper(collision(last=(101860, 101860, 101860, 101860), wick_at=T(4, 50), mirror=mirror))
    st.run_until(T(4, 49))
    old = st.core.box.bid
    st.finish()
    b_end = [e for e in st.kinds("scenario") if e["family"] == "B" and e["transition"] == "TERMINAL"][0]
    assert b_end["env"]["clock_time"] == iso(T(4, 51)) and b_end["reason"].startswith("V_CONTACT:")
    assert not [e for e in st.kinds("observation") if e.get("category") == "BOX_RETIRED"
                and e["values"]["box_id"] == old and e["env"]["clock_time"] <= iso(T(5))]


@pytest.mark.parametrize("mirror", [False, True], ids=["B_LONG", "B_SHORT"])
def test_episode_dead_before_the_dispatch_is_not_resurrected(mirror):
    """B ends on an earlier wick (04:51); the later opposite-edge 15m close at 05:00 happens without a live B episode:
    no retirement is attributed to the dead episode (the unchanged structural rules then treat the close as a fresh
    opposite B break of the kept box)."""
    opp = "SHORT" if not mirror else "LONG"
    st = fx.Stepper(collision(wick_at=T(4, 50), mirror=mirror))
    st.run_until(T(4, 52))
    old = st.core.box.bid
    assert not [s for s in st.core.scen.values() if s.family == "B"]
    st.run_until(T(5))
    assert not [e for e in at(st, T(5)) if e["record"].get("category") == "BOX_RETIRED"]
    assert st.core.box is not None and st.core.box.bid == old
    assert [(e["record"]["family"], e["record"]["direction"]) for e in at(st, T(5)) if e["kind"] == "scenario"
            and e["record"]["transition"] == "BIRTH"] == [("B", opp)]


@pytest.mark.parametrize("mirror", [False, True], ids=["B_LONG", "B_SHORT"])
@pytest.mark.parametrize("params", [None, HIGH_COST], ids=["child_issued", "child_rejected"])
def test_direct_restore_around_the_collision_boundary_keeps_box_token_and_lineage(mirror, params):
    mins = collision(mirror=mirror)
    base = run(mins, params=params)
    journal, records = restored_run(mins, (T(4, 58), T(5, 2)), params=params)
    assert [e["digest"] for e in journal] == [e["digest"] for e in base.journal]
    assert [x["digest"] for x in records] == [x["digest"] for x in base.records]
    assert [e for e in journal if e["record"].get("category") == "BOX_RETIRED"] == \
        [e for e in base.journal if e["record"].get("category") == "BOX_RETIRED"]
    assert base.runtime.core.box_token == AdviserRuntimeV3.decode(
        json.loads(canonical(base.runtime.encode())), base.runtime.core.cfg, base.runtime.ev).core.box_token


def test_white_box_snapshot_episode_terminated_earlier_in_the_dispatch_still_retires():
    """White-box: the dispatch-entry snapshot, not the mutated scenario map, owns the retirement predicate (called
    without a snapshot, the helper keeps snapshotting the current episodes as the earlier white-box test does)."""
    from algotrader.adviser.core import Box

    res = run(box_fixture("B"), params=HIGH_COST, stop_after=None)
    core = res.runtime.core
    t = T(10)
    core.box = Box("box-x", D(100000), D(101800), D(100900), D(600), D(60), T(9), 1, T(13), ["s"])
    core.scen["BL-x"] = Scen(sid="BL-x", family="B", d=1, owner="box-x", born_at=T(9), born_seq=1, sources=["s"],
                             setup_deadline=T(10), s15=D(600), z=D(60), status="CONFIRMED", entry="TERMINAL",
                             k_t=D(101860), v_t=D(101720), conf_at=T(9, 30), conf_deadline=T(15, 30),
                             progress_at=T(12, 30), premise_t=D(101740), dest_t=D(103600))
    # an episode listed in the dispatch-entry snapshot but already terminated in this dispatch still retires the box
    pre = [("BL-x", 1, "box-x")]
    del core.scen["BL-x"]
    core._box_close_flags(Bar(T(9, 45), t, D(100000), D(100000), D(99900), D(99930), D(1), t, "b"), t, pre)
    assert core.box is None


# -- F2 -----------------------------------------------------------------------------------------------------------------


def samples(res_or_records, sid=None):
    recs = res_or_records.records if hasattr(res_or_records, "records") else res_or_records
    return {r["record"]["sample_time"]: r["record"] for r in recs if r["kind"] == "view_sample"
            and (sid is None or r["record"]["scenario_id"] == sid)}


@pytest.mark.parametrize("mirror", [False, True], ids=["A_LONG", "A_SHORT"])
def test_already_confirmed_principal_samples_record_activation(mirror):
    """CONFIRM at 04:01; the same scenario is principal at 05:00 and 06:00 (terminal STALLED at 06:01)."""
    mins = fx.a3_stall_after_return()
    res = run(fx.mirror(mins) if mirror else mins)
    fam = "AS" if mirror else "AL"
    conf = next(s for s in res.scenarios(fam) if s["transition"] == "CONFIRM")
    assert conf["env"]["clock_time"] == iso(T(4, 1))
    sid = conf["scenario_id"]
    sm = samples(res)
    # pre-confirmation sample (principal ARMED at 04:00) credited by the causally later CONFIRM
    assert sm[iso(T(4))]["scenario_id"] == sid
    # already-confirmed samples
    for h in (T(4), T(5), T(6)):
        s = sm[iso(h)]
        assert s["scenario_id"] == sid and s["view"] == ("DOWN" if mirror else "UP")
        assert (s["antecedent_activated_1h"], s["antecedent_activated_4h"]) == (True, True), h
    # terminal control: after the 06:01 STALLED terminal the scenario is no longer principal; nothing is attributed
    for h in (T(7), T(8)):
        s = sm[iso(h)]
        assert s["scenario_id"] is None and s["antecedent_activated_1h"] is None
    # 1h/4h endpoint availability stays separate from activation
    assert sm[iso(T(5))]["outcome_1h"] is not None and sm[iso(T(5))]["outcome_4h"] is not None


def test_never_confirmed_principal_samples_stay_unactivated():
    """The confirmation minute never reaches K + tick (close 100000 < 100050): the A scenario stays ARMED (principal)
    and is never confirmed; its samples report False, never borrowed."""
    mins = fx.a3_base()[:-1] + fx.flat(120, 100000)
    res = run(mins)
    assert not [s for s in res.scenarios("AL") if s["transition"] == "CONFIRM"]
    armed = [s for s in samples(res).values() if s["scenario_id"]]
    assert armed and all(s["antecedent_activated_1h"] is False and s["antecedent_activated_4h"] is False
                         for s in armed)


def _fake_core(h, view_sid, scen):
    lb = Bar(h - timedelta(minutes=1), h, D(1), D(1), D(1), D(1), D(1), h, "m")
    return SimpleNamespace(last_1m=lb, ready_1m=lambda t: True, ready_1h=lambda t: False, h1=[], scen=scen,
                           view={"expected_direction": "UP", "conditional": True,
                                 "principal": {"scenario_id": view_sid}})


def _confirm_entry(sid, t):
    return {"kind": "scenario", "record": {"scenario_id": sid, "transition": "CONFIRM",
                                          "env": {"published_at": iso(t)}}}


def test_white_box_wrong_scenario_and_later_confirmation_are_causal():
    """White-box evaluator: principal X ARMED at 05:00 while another scenario Y is CONFIRMED; Y's activation is never
    borrowed; X is credited only by its own later CONFIRM (06:10, inside 4h but not 1h)."""
    ev = make_runtime(eval_start=DAY2, method="v0.3").ev
    x = SimpleNamespace(status="ARMED", conf_at=None)
    y = SimpleNamespace(status="CONFIRMED", conf_at=T(4, 1))
    ev._sample(T(5), _fake_core(T(5), "X", {"X": x, "Y": y}))
    ev.on_journal([_confirm_entry("Y", T(5, 30))])
    assert ev.samples[-1]["scenario_id"] == "X" and ev.samples[-1]["activated_at"] is None
    ev.on_journal([_confirm_entry("X", T(6, 10))])
    assert ev.samples[-1]["activated_at"] == iso(T(6, 10))
    ev._emit_sample(ev.samples[-1] | {"outcome_1h": None, "outcome_4h": None, "return_1h": None, "return_4h": None})
    rec = ev.records[-1]["record"]
    assert (rec["antecedent_activated_1h"], rec["antecedent_activated_4h"]) == (False, True)
    # a confirmation in the core state that is later than the cutoff never counts at that cutoff
    z = SimpleNamespace(status="CONFIRMED", conf_at=T(7, 1))
    ev._sample(T(7), _fake_core(T(7), "Z", {"Z": z}))
    assert ev.samples[-1]["activated_at"] is None


@pytest.mark.parametrize("window", [(T(3, 59), T(4, 2)), (T(4, 59), T(5, 2)), (T(5, 59), T(6, 2))],
                         ids=["around_confirmation", "around_05", "around_06"])
def test_pause_restore_before_and_after_the_hourly_sample(window):
    mins = fx.a3_stall_after_return()
    base = run(mins)
    journal, records = restored_run(mins, window)
    assert [e["digest"] for e in journal] == [e["digest"] for e in base.journal]
    assert [x["digest"] for x in records] == [x["digest"] for x in base.records]
    assert samples(records)[iso(T(5))]["antecedent_activated_1h"] is True


# -- reporting -----------------------------------------------------------------------------------------------------------


def _facts(method):
    return {"evaluation_id": f"e-{method}", "replay_id": "r", "status": "completed", "method": method,
            "model": "m", "rules_version": "r", "rules_sha256": "s", "register_sha256": "g", "implementation": "i",
            "identity_sha256": "x", "capability_profile_sha256": "c", "pins": {k: "p" for k in compare.PIN_FIELDS},
            "pack_manifest_sha256": "pm", "evaluator_terms": {}, "evaluator_sha256": "e", "assurance": "PASSED",
            "validation_outcome": "passed", "adviser": {"report_version": "v", "funnel": {}}}


def test_comparison_discloses_the_dislocation_correction_in_json_and_markdown():
    c = compare.build(_facts("v0.2"), _facts("v0.3"))
    assert [x["id"] for x in c["limitations"]] == ["V02_DISLOCATION_BASELINE_DEFECT_CORRECTED_IN_V03"]
    assert "RETURN alone" in c["limitations"][0]["text"] and "dislocation" in c["scope"]
    md = compare.render_markdown(c)
    assert "## Comparison limitations" in md and "V02_DISLOCATION_BASELINE_DEFECT_CORRECTED_IN_V03" in md
    same = compare.build(_facts("v0.3"), _facts("v0.3"))
    assert same["limitations"] == []


def _report3(res, eval_end):
    """report3.build over a pure fold with a minimal engine document (same keys as ``adviser.engine.engine_config``)."""
    from algotrader.adviser import report3
    from algotrader.adviser.harness import historical_profile

    rel = methods.get("v0.3")
    profile = historical_profile()
    adv = {"identity": rel.composite_identity(profile, {"pack_id": "synthetic"}, None),
           "profile": profile.model_dump(mode="json"), "evaluator": res.runtime.ev.identity(), "tick": "0.1",
           "eval_start": iso(DAY2), "eval_end": iso(eval_end), "warmup_start": iso(DAY1), "tail_end": iso(eval_end),
           "clock_end": iso(eval_end)}
    rep = report3.build(engine={"adviser": adv}, journal=res.journal, records=res.records, view=None,
                        status="completed", clock_end_reached=True)
    return rep, report3.render_markdown(rep)


def test_a_destination_before_confirmation_is_reported_with_an_example():
    """The reviewed K >= frozen B case (WP-009 A fixture): literal after-arm destination precedence is kept and the
    report counts it with an example; an ordinary confirmed A run reports zero."""
    from adviser_fixtures import a_fixture

    res = run(a_fixture())
    rep, md = _report3(res, DAY2 + timedelta(hours=12))
    x = rep["funnel"]["a_destination_before_confirmation"]
    assert x["count"] == 1 and x["by_direction"] == {"LONG": 1}
    [e] = x["examples"]
    assert e["at"] == "2025-09-01T05:20:00Z" and e["reason"].startswith("DESTINATION_CONTACT:")
    assert D(e["trigger_level"]) == D(e["destination"]) == 100240
    assert any(d.startswith("A_DESTINATION_BEFORE_CONFIRMATION: 1") for d in rep["diagnosis"])
    assert any("A destination contacted before confirmation (no call, rules unchanged): 1" in ln for ln in md)
    ok, _ = _report3(run(fx.a3_stall_after_return()), DAY2 + timedelta(hours=12))
    assert ok["funnel"]["a_destination_before_confirmation"]["count"] == 0


def test_earlier_v3_state_without_the_dependency_snapshot_still_decodes():
    """The dependency snapshot added to the v3 state is optional on decode (earlier v3 restore points keep their old
    behavior: an empty snapshot until the next dispatch recomputes it)."""
    res = run(fx.a3_stall_after_return(), stop_after=None)
    doc = json.loads(canonical(res.runtime.encode()))
    assert doc["core"]["v3"]["deps"]
    del doc["core"]["v3"]["deps"]
    rt = AdviserRuntimeV3.decode(doc, res.runtime.core.cfg, make_runtime(eval_start=DAY2, method="v0.3").ev)
    assert rt.core._deps == ()
