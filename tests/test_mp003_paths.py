"""WP-012 / MP-003 §6 fixtures for btc.context-action.v0.4 (pure, database-free).

Each tape is a complete reachable state machine on the MP-002 base A path (``adviser4_fixtures``): A 97000, B 100900,
birth S15 2000, z 200 (A+z 97200, B+z 101100), birth 03:30, original deadline 05:30, first ARM 03:45 (R 100000,
K 100700, V 99800). Expected transitions are written by hand for LONG; the SHORT run is the positive-price reflection
x -> 200000 - x with every structural level reflected and identical times/transitions/reasons. Assertions are on
scenario states, anchor epochs, reasons, publication domains and the absence of retroactive confirmation or calls —
not on aggregate counts. Economics are never asserted by reflection.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import timedelta
from decimal import Decimal

import adviser4_fixtures as fx
import pytest
from adviser3_fixtures import Stepper
from adviser4_fixtures import D, T, bar15, minute, walk

from algotrader.adviser import methods
from algotrader.adviser.harness import run_pure

V04 = methods.get("v0.4")
PIVOT = D(200000)
N = None


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def run(ms, method="v0.4", **kw):
    return run_pure(fx.DAY1, ms, eval_start=fx.DAY2, method=method, **kw)


def main_records(journal: list[dict], kind="scenario") -> list[dict]:
    """Records of the A scenario born on the 03:30 boundary (published 03:30, or later under a closure allowance)."""
    recs = [e["record"] for e in journal if e["kind"] == kind and e["record"]["scenario_id"][:2] in ("AL", "AS")]
    sid = next(r["scenario_id"] for r in recs if r.get("transition") == "BIRTH"
               and r["env"]["clock_time"][:15] == "2025-09-01T03:3")
    return [r for r in recs if r["scenario_id"] == sid]


def flip(x, side):
    if x is None:
        return None
    return D(x) if side == "L" else PIVOT - D(x)


def table(recs: list[dict]) -> list[tuple]:
    out = []
    for r in recs:
        out.append((r["env"]["clock_time"][11:19], r["transition"], (r["reason"] or "").split(":")[0] or None,
                    None if r["reaction_level"] is None else D(r["reaction_level"]),
                    None if r["trigger_level"] is None else D(r["trigger_level"]),
                    None if r["invalidation_level"] is None else D(r["invalidation_level"]),
                    r["anchor_epoch"], r["anchor_status"]))
    return out


def expect(rows: list[tuple], side: str) -> list[tuple]:
    return [(t, tr, rs, flip(r, side), flip(k, side), flip(v, side), ep, st) for t, tr, rs, r, k, v, ep, st in rows]


def both(fixture):
    return [("L", fixture()), ("S", fx.mirror(fixture()))]


BIRTH = ("03:30:00", "BIRTH", "FALSE_AT_OR_AFTER_RELEASE_TO_TRUE", N, N, N, N, "NONE")
ARM1 = ("03:45:00", "ARM", N, 100000, 100700, 99800, 1, "ACTIVE")


# -- rows 4-5: local contact -> same owner WATCH -> prospective replacement -> fresh confirmation ---------------------

@pytest.mark.parametrize("side,ms", both(fx.contact_then_rearm), ids=["LONG", "SHORT"])
def test_local_contact_invalidates_only_the_anchor_and_a_deeper_reaction_rearms_prospectively(side, ms):
    res = run(ms)
    recs = main_records(res.journal)
    assert table(recs) == expect([
        BIRTH, ARM1,
        ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("04:00:00", "REARM", "NEW_COMPLETE_STRICTLY_DEEPER_CLEAN_REACTION", 99790, 100300, 99590, 2, "ACTIVE"),
        ("04:09:00", "CONFIRM", "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04", 99790, 100300, 99590, 2,
         "FROZEN_AT_CONFIRMATION"),
        ("05:30:00", "OWNER_RELEASE", "ORIGINAL_SETUP_EXPIRY", 99790, 100300, 99590, 2, "FROZEN_AT_CONFIRMATION"),
        ("06:09:00", "TERMINAL", "SCENARIO_PROGRESS_BELOW_HALF_SCALE", 99790, 100300, 99590, 2,
         "FROZEN_AT_CONFIRMATION"),
    ], side)
    lost, rearm, conf = recs[2], recs[3], recs[4]
    # the lost anchor is journalled with its geometry, publication and the contact interval (cutoff) it died on
    prev = lost["previous_anchor"]
    assert (prev["epoch"], prev["status"], D(prev["R"]), D(prev["K"]), D(prev["V"])) == (
        "1", "INVALIDATED", flip(100000, side), flip(100700, side), flip(99800, side))
    assert prev["published_at"] == "2025-09-01T03:45:00+00:00" and prev["published_cursor"] is not None
    assert prev["interval"].endswith("@2025-09-01T03:50:00Z") and prev["interval_end"] == "2025-09-01T03:51:00+00:00"
    # same owner, same birth geometry / deadline / child budget; WATCH is a conditional observation, not an entry
    assert lost["status"] == "WATCH" and lost["discovery_owner"] == "OCCUPIED"
    assert {(r["original_expiry"], r["setup"]["impulse_A"], r["setup"]["impulse_B"], r["setup"]["s15"],
             r["setup"]["zone_halfwidth"]) for r in recs} == {(recs[0]["original_expiry"], recs[0]["setup"]["impulse_A"],
                                                               recs[0]["setup"]["impulse_B"], recs[0]["setup"]["s15"],
                                                               recs[0]["setup"]["zone_halfwidth"])}
    assert "waiting for a new completed reaction" in lost["antecedent"] and "not an entry" in lost["antecedent"]
    # replacement: actual dispatch publication (never the source bar's market close backdated), its own source bar
    assert rearm["anchor_published_at"] == rearm["env"]["clock_time"] == "2025-09-01T04:00:00Z"
    assert rearm["anchor_source"].endswith("/15m/2025-09-01T03:45:00+00:00")
    assert rearm["anchor_published_cursor"] > lost["anchor_published_cursor"]
    # destination monitoring origin is the FIRST arm, immutable through loss and replacement
    assert {r["destination_monitoring_from"] for r in recs[1:]} == {"2025-09-01T03:45:00Z"}
    assert all(r["ever_armed"] for r in recs[1:])
    # confirmation by a later fresh minute starting at/after the replacement publication
    assert conf["reason"].endswith("@2025-09-01T04:08:00Z") and conf["confirmed_at"] == "2025-09-01T04:09:00Z"
    assert not [e for e in res.entries() if e["env"]["clock_time"] < "2025-09-01T04:09"]
    # v0.3 on the same tape terminates the scenario at the contact (the MP-003 delta)
    v3 = main_records(run(ms, method="v0.3").journal)
    assert [(r["transition"], r["terminal_state"], (r["reason"] or "").split(":")[0]) for r in v3][-1] == (
        "TERMINAL", "INVALIDATED", "V_CONTACT")


@pytest.mark.parametrize("side,ms", both(fx.contact_at_equality), ids=["LONG", "SHORT"])
def test_contact_equality_is_inclusive(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs)[:4] == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("04:00:00", "REARM", "NEW_COMPLETE_STRICTLY_DEEPER_CLEAN_REACTION", 99800, D("100049.9"), 99600, 2, "ACTIVE"),
    ], side)


@pytest.mark.parametrize("side,ms", both(fx.replacement_tie), ids=["LONG", "SHORT"])
def test_replacement_requires_a_strictly_deeper_reaction_tie_does_not_rearm(side, ms):
    """The bar [04:00,04:15) with low exactly the lost R is NOT a replacement; [04:15,04:30) one tick deeper is."""
    assert table(main_records(run(ms).journal)) == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("04:30:00", "REARM", "NEW_COMPLETE_STRICTLY_DEEPER_CLEAN_REACTION", D("99999.9"), 100400, D("99799.9"), 2,
         "ACTIVE"),
        ("05:30:00", "OWNER_RELEASE", "ORIGINAL_SETUP_EXPIRY", D("99999.9"), 100400, D("99799.9"), 2, "ACTIVE"),
        ("05:30:00", "TERMINAL", "ORIGINAL_SETUP_DEADLINE", D("99999.9"), 100400, D("99799.9"), 2, "ACTIVE"),
    ], side)


@pytest.mark.parametrize("side,ms", both(fx.supersede_tie), ids=["LONG", "SHORT"])
def test_supersession_without_contact_keeps_the_inherited_inclusive_tie(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs)[:3] == expect([
        BIRTH, ARM1, ("04:00:00", "REVISE", "LOWER_CLEAN_REACTION_REANCHOR", 100000, 100500, 99800, 2, "ACTIVE")], side)
    assert recs[2]["previous_anchor"]["status"] == "SUPERSEDED" and recs[2]["previous_anchor"]["interval"] is None


# -- rows 7 and 11: complete-15m close predicate versus a 1m wick; no eligible reaction -------------------------------

@pytest.mark.parametrize("side,ms", both(fx.wick_through_a_plus_z_then_rebound), ids=["LONG", "SHORT"])
def test_wick_through_a_plus_z_is_not_the_close_predicate_and_without_a_clean_reaction_the_owner_waits(side, ms):
    res = run(ms)
    assert table(main_records(res.journal)) == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("05:30:00", "OWNER_RELEASE", "ORIGINAL_SETUP_EXPIRY", N, N, N, 1, "INVALIDATED"),
        ("05:30:00", "TERMINAL", "ORIGINAL_SETUP_DEADLINE", N, N, N, 1, "INVALIDATED"),
    ], side)
    assert res.calls() == [] and not [e for e in res.entries() if e["env"]["clock_time"] < "2025-09-01T05:30"]


@pytest.mark.parametrize("side,ms", both(fx.close_at_a_plus_z), ids=["LONG", "SHORT"])
def test_complete_15m_close_at_a_plus_z_withdraws_without_replacement(side, ms):
    res = run(ms)
    assert table(main_records(res.journal)) == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("04:00:00", "TERMINAL", "CLOSE_AT_OR_BEYOND_A_PLUS_ZONE", N, N, N, 1, "INVALIDATED"),
    ], side)
    assert res.calls() == []


# -- rows 1-3: destination monitoring origin -----------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.never_armed), ids=["LONG", "SHORT"])
def test_never_armed_b_contact_is_no_terminal_and_spend_needs_strictly_beyond_b_plus_z(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs) == [BIRTH, ("04:15:00", "TERMINAL", "SPENT_HIGH_BEYOND_B_BEFORE_REACTION", N, N, N, N, "NONE")]
    assert recs[-1]["ever_armed"] is False and recs[-1]["destination_monitoring_from"] is None


@pytest.mark.parametrize("side,ms", both(fx.arm_source_touches_b), ids=["LONG", "SHORT"])
def test_first_arm_source_bar_touching_b_is_never_a_retroactive_destination(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs) == expect([
        BIRTH, ("03:45:00", "ARM", N, 100000, 100950, 99800, 1, "ACTIVE"),
        ("03:51:00", "TERMINAL", "DESTINATION_CONTACT", 100000, 100950, 99800, 1, "ACTIVE")], side)
    assert recs[-1]["terminal_state"] == "DESTINATION_REACHED" and recs[-1]["reason"].endswith("@2025-09-01T03:50:00Z")


@pytest.mark.parametrize("side,ms", both(fx.arm_then_lost_then_b), ids=["LONG", "SHORT"])
def test_destination_monitoring_stays_active_in_watch_after_anchor_loss(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs) == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("04:21:00", "TERMINAL", "DESTINATION_CONTACT", N, N, N, 1, "INVALIDATED")], side)
    assert recs[-1]["terminal_state"] == "DESTINATION_REACHED" and recs[-1]["destination_monitoring_from"] == \
        "2025-09-01T03:45:00Z"


@pytest.mark.parametrize("side,ms", both(fx.local_and_destination_same_minute), ids=["LONG", "SHORT"])
def test_simultaneous_local_and_destination_contact_is_unassessable_without_replacement(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs) == expect([
        BIRTH, ARM1, ("03:51:00", "TERMINAL", "DESTINATION_AND_LOCAL_ANCHOR_CONTACT_SAME_INTERVAL", 100000, 100700,
                      99800, 1, "ACTIVE")], side)
    assert recs[-1]["terminal_state"] == "UNASSESSABLE"


@pytest.mark.parametrize("side,ms", both(fx.monitoring_gap_after_loss), ids=["LONG", "SHORT"])
def test_required_monitoring_gap_after_anchor_loss_is_a_structural_terminal(side, ms):
    recs = main_records(run(ms).journal)
    assert table(recs) == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("03:56:00", "TERMINAL", "REQUIRED_MONITORING_GAP", N, N, N, 1, "INVALIDATED")], side)
    assert recs[-1]["terminal_state"] == "UNASSESSABLE"


# -- row 8: original deadline first --------------------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.deadline_with_candidate_replacement), ids=["LONG", "SHORT"])
def test_original_deadline_precedes_a_candidate_replacement(side, ms):
    assert table(main_records(run(ms).journal)) == expect([
        BIRTH, ARM1, ("03:51:00", "ANCHOR_LOST", "V_CONTACT", N, N, N, 1, "INVALIDATED"),
        ("05:30:00", "OWNER_RELEASE", "ORIGINAL_SETUP_EXPIRY", N, N, N, 1, "INVALIDATED"),
        ("05:30:00", "TERMINAL", "ORIGINAL_SETUP_DEADLINE", N, N, N, 1, "INVALIDATED")], side)


def test_the_deadline_control_bar_would_otherwise_rearm():
    """Control for row 8: the same deeper bar completing one bar earlier ([05:00,05:15)) is a valid REARM at 05:15."""
    ms = fx.deadline_with_candidate_replacement()
    i = fx.index_of(T(5))
    ms = ms[:i] + walk(100600, 99500, 10) + walk(99500, 99800, 5) + fx.flat(400, 99800)
    recs = main_records(run(ms).journal)
    assert ("05:15:00", "REARM") in [(r[0], r[1]) for r in table(recs)]


# -- rows 9-10: no post-confirmation re-anchor ---------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.a3_wait_v_contact_then_rebound), ids=["LONG", "SHORT"])
def test_confirmed_wait_v_contact_is_terminal_with_no_reanchor(side, ms):
    res = run(ms)
    recs = main_records(res.journal)
    assert [r[:3] for r in table(recs)][-2:] == [("04:01:00", "CONFIRM", "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04"),
                                                 ("04:02:00", "TERMINAL", "V_CONTACT")]
    assert recs[-1]["terminal_state"] == "INVALIDATED" and recs[-1]["anchor_status"] == "FROZEN_AT_CONFIRMATION"
    assert not [r for r in recs if r["transition"] in ("ANCHOR_LOST", "REARM")]
    ent = [e for e in res.entries() if e["scenario_id"] == recs[0]["scenario_id"]]
    assert [e["transition"] for e in ent] == ["WAIT_OPEN", "TERMINAL"] and res.calls() == []


@pytest.mark.parametrize("side,ms", both(fx.a3_issued_then_v_contact), ids=["LONG", "SHORT"])
def test_issued_call_v_contact_keeps_the_existing_protection_identical_to_v03(side, ms):
    r4, r3 = run(ms), run(ms, method="v0.3")
    assert len(r4.calls()) == 1
    strip = lambda rows: [{k: v for k, v in x.items() if k not in ("env", "call_id", "attempt_id", "scenario_id")}  # noqa: E731
                          for x in rows]
    assert strip(r4.revisions()) == strip(r3.revisions())
    assert r4.revisions()[-1]["thesis_status"] == "INVALIDATED"
    assert [p["exit_class"] for p in r4.paths()] == [p["exit_class"] for p in r3.paths()]
    assert not [r for r in main_records(r4.journal) if r["transition"] in ("ANCHOR_LOST", "REARM")]


# -- delayed publication, backlog and straddling (row 2, 6, 12) -----------------------------------------------------

def _stepper(ms, delays=None, allowance=timedelta(0)):
    evs = fx.delayed_events(ms, {fx.index_of(t): s for t, s in (delays or {}).items()})
    st = Stepper(ms, events=evs, method="v0.4", allowance=allowance)
    st.finish()
    return st


def _pre_touch_b():
    return fx.birth_base() + bar15(D(100700), D(100950), D(100000), D("100049.9"), order="HL")


@pytest.mark.parametrize("side", ["L", "S"])
def test_delayed_first_arm_publication_ignores_already_admitted_b_contacts(side):
    """5-minute closure allowance: the reaction bar [03:30,03:45) is published at 03:50 (actual dispatch). The minute
    [03:45,03:46) reached 100950 >= B but was admitted at 03:46, before the first arm: no retroactive destination; the
    first newly admitted minute after the origin that reaches B ([03:50,03:51) high 100900) terminates at 03:51."""
    ms = fx.tail(_pre_touch_b() + [minute("100049.9", 100950, 100040, 100100)] + walk(100100, 100800, 4)
                 + [minute(100800, 100900, 100800, 100850)] + walk(100850, 100600, 9))
    st = _stepper(ms if side == "L" else fx.mirror(ms), allowance=timedelta(minutes=5))
    recs = main_records(st.journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"], (r["reason"] or "").split(":")[0] or None) for r in recs] \
        == [("03:35:00", "BIRTH", "FALSE_AT_OR_AFTER_RELEASE_TO_TRUE"), ("03:50:00", "ARM", None),
            ("03:51:00", "TERMINAL", "DESTINATION_CONTACT")]
    assert recs[1]["destination_monitoring_from"] == recs[1]["anchor_published_at"] == "2025-09-01T03:50:00Z"
    assert recs[2]["reason"].endswith("@2025-09-01T03:50:00Z")


@pytest.mark.parametrize("side", ["L", "S"])
def test_straddling_first_arm_origin_with_b_contact_is_unassessable(side):
    ms = fx.tail(_pre_touch_b() + [minute("100049.9", 100950, 100040, 100100)] + walk(100100, 100600, 13))
    st = _stepper(ms if side == "L" else fx.mirror(ms), {T(3, 44): 30}, allowance=timedelta(seconds=30))
    recs = main_records(st.journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"]) for r in recs] == [
        ("03:30:30", "BIRTH"), ("03:45:30", "ARM"), ("03:46:00", "TERMINAL")]
    assert recs[-1]["terminal_state"] == "UNASSESSABLE"
    assert recs[-1]["reason"].startswith("FIRST_ARM_DESTINATION_CONTACT_TIME_AMBIGUOUS")


@pytest.mark.parametrize("side", ["L", "S"])
def test_straddling_local_contact_makes_only_the_anchor_unassessable(side):
    ms = fx.tail(fx.arm_base() + [minute("100049.9", "100049.9", 99790, 99900)] + walk(99900, 100300, 6)
                 + walk(100300, 99950, 7) + walk(99950, 100350, 10))
    st = _stepper(ms if side == "L" else fx.mirror(ms), {T(3, 44): 30}, allowance=timedelta(seconds=30))
    recs = main_records(st.journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"], r["anchor_status"]) for r in recs][:5] == [
        ("03:30:30", "BIRTH", "NONE"), ("03:45:30", "ARM", "ACTIVE"), ("03:46:00", "ANCHOR_LOST", "UNASSESSABLE"),
        ("04:00:30", "REARM", "ACTIVE"), ("04:08:00", "CONFIRM", "FROZEN_AT_CONFIRMATION")]
    assert recs[2]["reason"].startswith("ANCHOR_CONTACT_TIME_AMBIGUOUS") and recs[2]["status"] == "WATCH"
    assert recs[3]["anchor_published_at"] == "2025-09-01T04:00:30Z"


@pytest.mark.parametrize("side", ["L", "S"])
def test_contact_and_replacement_in_one_dispatch_are_ordered_and_prospective(side):
    """Row 6: the contact minute [03:58,03:59) is received at 04:00 together with [03:59,04:00) and the seal of
    [03:45,04:00): ANCHOR_LOST is journalled first, then REARM at the same dispatch/cursor; no admitted minute confirms
    it - the first confirmation is the later fresh minute [04:00,04:01)."""
    ms = fx.contact_same_bar_backlog()
    st = _stepper(ms if side == "L" else fx.mirror(ms), {T(3, 58): 60})
    recs = main_records(st.journal)
    seq = [(r["env"]["clock_time"][11:19], r["transition"]) for r in recs][:5]
    assert seq == [("03:30:00", "BIRTH"), ("03:45:00", "ARM"), ("04:00:00", "ANCHOR_LOST"), ("04:00:00", "REARM"),
                   ("04:01:00", "CONFIRM")]
    lost, rearm, conf = recs[2], recs[3], recs[4]
    assert lost["previous_anchor"]["interval"].endswith("@2025-09-01T03:58:00Z")
    ent = {e["record"]["env"]["record_id"]: e for e in st.journal if e["kind"] == "scenario"}
    lost_e, rearm_e = ent[lost["env"]["record_id"]], ent[rearm["env"]["record_id"]]
    assert lost_e["factual_cursor"] == rearm_e["factual_cursor"] == rearm["anchor_published_cursor"]
    assert lost_e["seq"] < rearm_e["seq"]
    assert flip(rearm["trigger_level"], side) == D(100600) and conf["reason"].endswith("@2025-09-01T04:00:00Z")


@pytest.mark.parametrize("side", ["L", "S"])
def test_recoveries_admitted_before_a_delayed_replacement_never_confirm_it(side):
    """5-minute closure allowance: REARM is published at 04:05 (actual dispatch) for the bar ending 04:00. The minutes
    [04:00,04:05) close at/above the new K+tick but were admitted before that publication: no confirmation from them;
    the first confirmation is [04:05,04:06)."""
    ms = fx.contact_same_bar_backlog()
    st = _stepper(ms if side == "L" else fx.mirror(ms), allowance=timedelta(minutes=5))
    recs = main_records(st.journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"]) for r in recs][2:5] == [
        ("03:59:00", "ANCHOR_LOST"), ("04:05:00", "REARM"), ("04:06:00", "CONFIRM")]
    long_ms = fx.contact_same_bar_backlog()
    assert all(m.c >= D("100600.1") for m in long_ms[fx.index_of(T(4)):fx.index_of(T(4, 5))])  # K+tick (LONG)
    assert recs[4]["reason"].endswith("@2025-09-01T04:05:00Z")


# -- row 13: cost invariance, evaluator on/off, appended future ------------------------------------------------------

def _structural(journal):
    out = []
    for e in journal:
        if e["kind"] in ("scenario", "landmark", "market_view"):
            r = {k: v for k, v in e["record"].items() if k != "env"}
            out.append((e["kind"], e["record"]["env"]["clock_time"], json.dumps(r, sort_keys=True)))
    return out


def test_cost_profiles_give_identical_normalized_structural_lineage_and_anchor_sequence():
    ms = fx.contact_then_rearm()
    runs = {k: run(ms, params=dataclasses.replace(V04.params(), hist_k_bps=D(k))) for k in (2, 14, 500)}
    assert _structural(runs[2].journal) == _structural(runs[14].journal) == _structural(runs[500].journal)
    assert [e["transition"] for e in runs[2].entries("AL")] != [e["transition"] for e in runs[500].entries("AL")]


def test_evaluator_on_off_and_appended_future_do_not_change_professional_records():
    ms = fx.contact_then_rearm()
    on, off = run(ms), run(ms, evaluator=False)
    assert [e["digest"] for e in on.journal] == [e["digest"] for e in off.journal]
    longer = run(ms + fx.flat(120, ms[-1].c))
    n = len(on.journal)
    assert [e["digest"] for e in longer.journal[:n - 5]] == [e["digest"] for e in on.journal[:n - 5]]


def test_anchor_loss_never_creates_a_call_alert_or_an_entry_record():
    res = run(fx.wick_through_a_plus_z_then_rebound())
    assert res.calls() == [] and not [e for e in res.journal if e["kind"] == "material_change"
                                      and e["record"]["subject_id"].startswith("A")]
    _ = Decimal


def _late_tape(contact_low):
    post = walk("100049.9", 99850, 7) + walk(99850, 100100, 8) + walk(100100, 100000, 4)
    post += [minute(100000, 100000, contact_low, 99900)] + walk(99900, 100200, 12)
    return fx.tail(fx.arm_base() + post)


@pytest.mark.parametrize("side", ["L", "S"])
def test_an_older_retained_bar_never_republishes_a_replacement(side):
    """5-minute allowance: ARM published 03:50; the contact minute [04:02,04:03) (low 99700) loses the anchor at 04:03.
    The bar [03:45,04:00) - low 99850, deeper than the lost R - is sealed only at 04:05 but ENDED before the contact
    interval end: no REARM from it. The bar [04:00,04:15) (low 99700) is the prospective replacement at 04:20."""
    post = walk("100049.9", 99850, 7) + walk(99850, 100100, 8) + walk(100100, 100000, 2)
    post += [minute(100000, 100000, 99700, 99900)] + walk(99900, 100200, 12)
    ms = fx.tail(fx.arm_base() + post)
    st = _stepper(ms if side == "L" else fx.mirror(ms), allowance=timedelta(minutes=5))
    recs = main_records(st.journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"], r["anchor_epoch"]) for r in recs][:5] == [
        ("03:35:00", "BIRTH", None), ("03:50:00", "ARM", 1), ("04:03:00", "ANCHOR_LOST", 1), ("04:20:00", "REARM", 2),
        ("04:22:00", "CONFIRM", 2)]
    assert flip(recs[3]["reaction_level"], side) == D(99700)
    assert recs[3]["anchor_source"].endswith("/15m/2025-09-01T04:00:00+00:00")


@pytest.mark.parametrize("side", ["L", "S"])
def test_late_interval_in_an_earlier_epoch_domain_makes_the_newer_anchor_unassessable(side):
    """5-minute allowance: the bar [03:45,04:00) (low 99850, no contact) supersedes epoch 1 at 04:05 (epoch 2, V 99650).
    The minute [04:04,04:05) - wholly inside epoch 1's domain - is received at 04:05:30 with low 99750 <= V1 99800:
    epoch 2 was published without that evidence -> ANCHOR_LOST UNASSESSABLE (LATE_CONTACT_WITH_EARLIER_ANCHOR_EPOCH_1).
    Received on time, the same minute is an ordinary contact of epoch 1 at 04:05 processed BEFORE that bar's
    revision, and the bar (ended before the contact) cannot re-anchor."""
    ms = _late_tape(99750)
    st = _stepper(ms if side == "L" else fx.mirror(ms), {T(4, 4): 30}, allowance=timedelta(minutes=5))
    recs = main_records(st.journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"], r["anchor_epoch"], r["anchor_status"]) for r in recs][1:4] \
        == [("03:50:00", "ARM", 1, "ACTIVE"), ("04:05:00", "REVISE", 2, "ACTIVE"),
            ("04:05:30", "ANCHOR_LOST", 2, "UNASSESSABLE")]
    assert recs[3]["reason"].startswith("LATE_CONTACT_WITH_EARLIER_ANCHOR_EPOCH_1")
    on_time = main_records(_stepper(ms if side == "L" else fx.mirror(ms), allowance=timedelta(minutes=5)).journal)
    assert [(r["env"]["clock_time"][11:19], r["transition"]) for r in on_time][1:4] == [
        ("03:50:00", "ARM"), ("04:05:00", "ANCHOR_LOST"), ("04:20:00", "REARM")]
