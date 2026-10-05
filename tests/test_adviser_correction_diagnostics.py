"""WP-009 correction, finding 9 (pure, tiny fixtures; no parameter search, no market run): durable bounded diagnosis
accumulators with defined denominators — overlapping named-condition durations (separate from attempt counts),
SLOT_OCCUPIED/PRIORITY exposure time, staged room erosion (A impulse -> reaction -> trigger -> primary open; B/C impulse
and reaction explicitly NOT_APPLICABLE) — in the JSON section and the Markdown copy, identical after restore."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from adviser_fixtures import DAY1, DAY2, a_fixture, box_fixture
from adviser_rig import Rig
from test_adviser_rules import T

from algotrader.adviser import report as ar
from algotrader.adviser.harness import build_events, make_runtime, run_pure, temporal_for
from algotrader.adviser.identity import composite_identity, historical_profile
from algotrader.adviser.runtime import AdviserRuntime
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

D = Decimal
US_MIN = 60_000_000


def _engine(eval_start, eval_end, minutes):
    prof = historical_profile()
    ev = make_runtime(eval_start=eval_start, eval_end=eval_end).ev
    return {"adviser": {"identity": composite_identity(prof, {"fixture": True}, "test"),
                        "profile": prof.model_dump(mode="json"), "evaluator": ev.identity(), "tick": "0.1",
                        "eval_start": eval_start.isoformat(), "eval_end": eval_end.isoformat(),
                        "warmup_start": DAY1.isoformat(), "tail_end": (DAY1 + len(minutes) * timedelta(minutes=1))
                        .isoformat(), "clock_end": (DAY1 + len(minutes) * timedelta(minutes=1)).isoformat()}}


def _report(res, eval_start, eval_end, minutes):
    view = {"diagnostics": res.runtime.core.diag, "boundary": res.runtime.core.boundary}
    return ar.build(engine=_engine(eval_start, eval_end, minutes), journal=res.journal, records=res.records,
                    view=view, status="completed", clock_end_reached=True)


def test_overlapping_named_blockers_are_timed_separately_from_attempt_counts():
    r = Rig(eval_start=T)
    r.t = T
    for i in range(30):  # 30 complete minutes without any 15m/1h context: two blockers overlap the whole time
        r.minute(100, 100, 100, 100)
    d = r.core.diag
    assert d["covered_us"] == 29 * US_MIN  # credited between dispatches inside the window
    for k in ("TRADE_15M_NOT_READY", "TRADE_1H_NOT_READY", "ANY_COMMON_BLOCKER", "NO_ARMED_SCENARIO"):
        assert d["us"][k] == d["covered_us"], k
        assert d["onsets"][k] == 1, k  # one episode, not one per minute
    assert "ISSUABLE_IF_TRIGGERED" not in d["us"]
    out = ar.condition_durations(d)
    assert out["conditions"]["TRADE_15M_NOT_READY"]["fraction_of_covered"] == "1.0000"
    assert out["covered_minutes"] == "29.00"


def test_zero_call_report_carries_durations_diagnosis_and_markdown():
    mins = a_fixture()[: 24 * 60 + 120]  # warmup + two evaluation hours, before the fixture's call
    res = run_pure(DAY1, mins, eval_start=DAY2, eval_end=DAY2 + timedelta(hours=2))
    assert res.calls() == []
    a = _report(res, DAY2, DAY2 + timedelta(hours=2), mins)
    cd = a["condition_durations"]
    assert cd["available"] and D(cd["covered_minutes"]) > 0
    covered = D(cd["covered_minutes"])
    assert all(D(v["minutes"]) <= covered for v in cd["conditions"].values())
    assert any(x.startswith("CONDITION_TIME:") for x in a["diagnosis"])
    assert a["funnel"]["slot_priority_minutes"] is not None
    md = "\n".join(ar.render_markdown(a))
    assert "Condition time (overlapping" in md and "Slot/priority exposure" in md
    json.dumps(a, default=str)  # JSON-serializable section


def test_slot_occupied_time_and_staged_room_erosion_for_an_issued_a_call():
    mins = a_fixture()
    res = run_pure(DAY1, mins, eval_start=DAY2)
    end = DAY1 + len(mins) * timedelta(minutes=1)
    a = _report(res, DAY2, end, mins)
    [call] = res.calls()
    cs = a["condition_durations"]["conditions"]
    assert D(cs["SLOT_OCCUPIED"]["minutes"]) > 0 and cs["SLOT_OCCUPIED"]["onsets"] == 1
    st = a["room_erosion_staged"]
    row = next(x for x in st["list"] if x["issued_call"] == call["call_id"])
    assert row["family"] == "A"
    for k in ("impulse", "reaction", "trigger", "primary_open"):
        assert row[f"room_{k}_bps"] not in (None, "NOT_APPLICABLE"), k
    # reaction pulls price back from the impulse end: more room there than at the impulse end or the trigger
    assert D(row["room_reaction_bps"]) > D(row["room_trigger_bps"])
    assert D(row["room_reaction_bps"]) > D(row["room_impulse_bps"])
    fam = st["by_family"]["A"]
    assert "erosion_trigger_to_primary_open" in fam and "erosion_reaction_to_trigger" in fam
    md = "\n".join(ar.render_markdown(a))
    assert "Room by stage A" in md


def test_b_and_c_impulse_and_reaction_stages_are_explicitly_not_applicable():
    mins = box_fixture("B")
    res = run_pure(DAY1, mins, eval_start=DAY2)
    end = DAY1 + len(mins) * timedelta(minutes=1)
    a = _report(res, DAY2, end, mins)
    rows = [x for x in a["room_erosion_staged"]["list"] if x["family"] == "B"]
    assert rows
    for x in rows:
        assert x["room_impulse_bps"] == "NOT_APPLICABLE" and x["room_reaction_bps"] == "NOT_APPLICABLE"
        assert x["room_trigger_bps"] not in (None, "NOT_APPLICABLE")


def test_accumulator_is_identical_after_an_interrupted_restore():
    mins = a_fixture()
    base = run_pure(DAY1, mins, eval_start=DAY2)
    events, cov = build_events(DAY1, mins)
    rt = make_runtime(eval_start=DAY2)
    temporal = temporal_for(cov)
    rt.attach(temporal)
    cut = len(events) // 2 + 7
    for i, e in enumerate(events):
        if i == cut:
            rt.take()
            temporal = te.unpack(*te.pack(temporal))
            rt = AdviserRuntime.decode(json.loads(canonical(rt.encode())), rt.core.cfg, make_runtime(eval_start=DAY2).ev)
            rt.attach(temporal)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    end = DAY1 + len(mins) * timedelta(minutes=1)
    temporal.finish(end)
    rt.finish(end)
    assert rt.core.diag == base.runtime.core.diag and base.runtime.core.diag["covered_us"] > 0


def test_legacy_view_without_accumulator_is_labelled_not_invented():
    assert ar.condition_durations(None) == {"available": False, "note": "no committed diagnosis accumulator (run "
                                                                        "started before it existed)"}
