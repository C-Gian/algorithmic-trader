"""WP-014 / MP-004 §6 fixtures for btc.context-action.v0.5 (pure, database-free).

Every tape is a complete reachable state machine on the MP-002 base A path (``adviser5_fixtures``): confirmation
published 04:01, WAIT_PRICE corridor [99900, 100049.9], V 99700, T_confirm 100700, original deadline 05:30. The first
usable return [04:01,04:02) prepares the reference H0 100008 / L0 99990 at 04:02. Expected transitions are written by
hand for LONG; the SHORT run is the positive-price reflection x -> 200000 - x with identical times/transitions/reasons
(H0 100010 / L0 99992, V 100300, T 99300). Economics are checked separately for each side with the independent
rational reference ``mp002_reference`` (never by reflection). Assertions are on entry-attempt records, the response
provenance and the absence of retroactive or repeated evaluations - not on aggregate counts.

The MP-004 §6 table itself uses its own illustrative prices (R 1000, K 1020, ...); its predicates and economic ratios
are checked literally in the first tests.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta
from decimal import Decimal

import adviser5_fixtures as fx
import mp002_reference as ref
import pytest
from adviser3_fixtures import Stepper
from adviser5_fixtures import D, T

from algotrader.adviser import geometry as geo
from algotrader.adviser.core3 import CallV3
from algotrader.adviser.core5 import local_verdict, primary_reason, reason_class
from algotrader.adviser.harness import run_pure

N = None
PIVOT = D(200000)


def iso(t) -> str:
    return t.isoformat().replace("+00:00", "Z")


def run(ms, method="v0.5", **kw):
    kw.setdefault("eval_start", fx.DAY2)
    return run_pure(fx.DAY1, ms, method=method, **kw)


def both(fixture):
    return [("L", fixture()), ("S", fx.mirror(fixture()))]


def a_entries(journal_or_res) -> list[dict]:
    j = journal_or_res.journal if hasattr(journal_or_res, "journal") else journal_or_res
    return [e["record"] for e in j if e["kind"] == "entry_attempt" and e["record"]["scenario_id"][:2] in ("AL", "AS")]


def steps(journal_or_res) -> list[tuple]:
    """(time, state, transition, reason head, response outcome) per A entry-attempt record."""
    return [(r["env"]["clock_time"][11:19], r["state"], r["transition"],
             (r["reason"] or "").split(":")[0].split(",")[0] if r["transition"] != "ISSUE" else "CALL",
             (r.get("response") or {}).get("outcome")) for r in a_entries(journal_or_res)]


def calls(journal_or_res) -> list[dict]:
    j = journal_or_res.journal if hasattr(journal_or_res, "journal") else journal_or_res
    return [e["record"] for e in j if e["kind"] == "call"]


def px(x, side):
    return D(str(x)) if side == "L" else PIVOT - D(str(x))


OPEN = ("04:01:00", "WAIT_PRICE", "WAIT_OPEN", "IMMEDIATE_ECONOMIC_FAILURE_RETURN_CORRIDOR_USABLE", N)
REF = ("04:02:00", "WAIT_RESPONSE", "RESPONSE_REFERENCE", "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04", N)


def ref_step(t="04:02:00"):
    return (t, "WAIT_RESPONSE", "RESPONSE_REFERENCE", "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04", N)


# ---------------------------------------------------------------------------------------------------------------------
# MP-004 §1 / §6 literal predicates and illustrative economics
# ---------------------------------------------------------------------------------------------------------------------

TICK = D("0.1")
LONG_REF, SHORT_REF = (D(1002), D(1008)), (D(1032), D(1038))  # (L0, H0) of the §6 reference bars


@pytest.mark.parametrize("row,long_bar,short_bar,verdict", [
    ("valid", (1003, 1010, 1009), (1030, 1037, 1031), "RECOVERY"),
    ("contrary equality + exact favourable threshold", (1002, "1008.1", "1008.1"), ("1031.9", 1038, "1031.9"),
     "RECOVERY"),
    ("favourable equality only", (1002, 1008, 1008), (1032, 1038, 1032), "NONE"),
    ("intermediate violation", ("1001.9", 1007, 1005), (1033, "1038.1", 1035), "CONTRADICTION"),
    ("violation and recovery in one bar", ("1001.9", 1010, 1009), (1030, "1038.1", 1031), "CONTRADICTION"),
    ("V and recovery in one bar (local view)", (990, 1010, 1009), (1030, 1050, 1031), "CONTRADICTION"),
    ("economics insufficient (local view)", (1003, 1019, 1019), (1021, 1037, 1021), "RECOVERY"),
    ("outside corridor (local view)", (1003, 1021, 1021), (1019, 1037, 1019), "RECOVERY"),
])
def test_mp004_section_6_predicates_literally(row, long_bar, short_bar, verdict):
    lo, hi, c = (D(str(x)) for x in long_bar)
    assert local_verdict(1, LONG_REF[1], LONG_REF[0], TICK, lo, hi, c) == verdict, row
    lo, hi, c = (D(str(x)) for x in short_bar)
    assert local_verdict(-1, SHORT_REF[1], SHORT_REF[0], TICK, lo, hi, c) == verdict, row


def test_mp004_section_6_illustrative_economics_with_the_inherited_predicate():
    """14 bps, ratio 1.2, LONG V 990 / T 1050, SHORT V 1050 / T 990. The valid paths pass (LONG ~1.94; SHORT ~1.935
    with the inherited formula - MP-004 §6 prints "circa 2,08" for SHORT, an illustrative-arithmetic slip that
    changes no outcome, recorded in the WP-014 evidence); the insufficient-economics closes fail (~0.97 both)."""
    k, r = D(14), D("1.2")

    def ratio(d, p, v, t):
        c = geo.predicate(d, D(p), D(v), D(t), k, r)
        return (c.g - k) / (c.q + k), c.ok

    rl, okl = ratio(1, 1009, 990, 1050)
    rs, oks = ratio(-1, 1031, 1050, 990)
    assert okl and oks and round(rl, 2) == D("1.94") and round(rs, 3) == D("1.935")
    for d, p, v, t in ((1, 1019, 990, 1050), (-1, 1021, 1050, 990)):
        x, ok = ratio(d, p, v, t)
        assert not ok and round(x, 2) == D("0.97")
    # the independent rational reference agrees
    assert ref.passes(1, 1009, 990, 1050, 14) and ref.passes(-1, 1031, 1050, 990, 14)
    assert not ref.passes(1, 1019, 990, 1050, 14) and not ref.passes(-1, 1021, 1050, 990, 14)


def test_primary_reason_is_deterministic_by_class_then_code():
    assert primary_reason(["TOO_LATE", "REWARD_RISK_BELOW_MINIMUM", "CLOSE_OUTSIDE_RETURN_CORRIDOR"]) == \
        "CLOSE_OUTSIDE_RETURN_CORRIDOR"
    assert primary_reason(["SLOT_OCCUPIED", "QUOTE_STALE"]) == "QUOTE_STALE"
    assert primary_reason(["PRIORITY"]) == "PRIORITY" and reason_class("PRIORITY") == "SELECTION"
    assert reason_class("TRADE_1M_STALE") == "OTHER_GATES" and reason_class("NO_ROOM_AFTER_COSTS") == "ECONOMICS_GEOMETRY"
    assert reason_class("RESPONSE_OBSERVED_LATE_NOT_CURRENT") == "LATE_OBSERVATION"


# ---------------------------------------------------------------------------------------------------------------------
# valid path, equalities, intermediate bars
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.valid), ids=["LONG", "SHORT"])
def test_valid_first_recovery_issues_once_at_its_own_close(side, ms):
    res = run(ms)
    assert steps(res) == [OPEN, REF, ("04:03:00", "ISSUED", "ISSUE", "CALL", "ISSUED")]
    prep, issue = a_entries(res)[1], a_entries(res)[2]
    r0 = prep["response"]
    assert (D(r0["H0"]), D(r0["L0"])) == ((D(100008), D(99990)) if side == "L" else (D(100010), D(99992)))
    assert r0["published_at"] == "2025-09-01T04:02:00+00:00" == iso(T(4, 2)).replace("Z", "+00:00")
    assert r0["published_cursor"] == str(prep["env"]["factual_cursor"]) and r0["phase"] == "WAIT_RESPONSE"
    assert r0["reference_bar"].endswith("@2025-09-01T04:01:00Z") and r0["reference_end"].startswith("2025-09-01T04:02")
    r1 = issue["response"]
    assert {k: r1[k] for k in ("H0", "L0", "published_at", "published_cursor")} == \
        {k: r0[k] for k in ("H0", "L0", "published_at", "published_cursor")}  # one reference, never moved
    assert r1["response_bar"].endswith("@2025-09-01T04:02:00Z") and r1["response_current"] == "true"
    assert r1["bars_checked"] == "1" and issue["env"]["professional_seq"] > prep["env"]["professional_seq"]
    [c] = calls(res)
    assert (c["issued_at"], c["entry_mode"]) == ("2025-09-01T04:03:00Z", "RETURN")
    assert (D(c["issue_reference"]), D(c["target"]), D(c["invalidation"])) == (px(100012, side), px(100700, side),
                                                                               px(99700, side))
    d = 1 if side == "L" else -1
    assert ref.passes(d, px(100012, side), px(99700, side), px(100700, side), 14)  # separate economics per side
    # ISSUE is a publication, not a fill: the pinned evaluator enters at its first admissible open after the issue
    [p] = res.paths("PRIMARY")
    assert p["entry"]["time_start"] == "2025-09-01T04:04:00Z" and D(p["entry"]["price"]) == px(100005, side)
    # v0.4 on the same tape issues at the usable return itself (04:02, close 99995): the MP-004 delta
    [c4] = calls(run(ms, method="v0.4"))
    assert (c4["issued_at"], D(c4["issue_reference"])) == ("2025-09-01T04:02:00Z", px(99995, side))


@pytest.mark.parametrize("side,ms", both(fx.equality), ids=["LONG", "SHORT"])
def test_contrary_equality_and_exact_favourable_threshold_recover(side, ms):
    res = run(ms)
    assert steps(res)[-1] == ("04:03:00", "ISSUED", "ISSUE", "CALL", "ISSUED")
    assert D(calls(res)[0]["issue_reference"]) == px(D("100008.1"), side)


@pytest.mark.parametrize("side,ms", both(fx.favourable_equality_only), ids=["LONG", "SHORT"])
def test_favourable_equality_alone_is_no_recovery_and_the_wait_continues_to_the_deadline(side, ms):
    res = run(ms)
    assert steps(res) == [OPEN, REF, ("05:30:00", "TERMINAL", "TERMINAL", "ORIGINAL_SETUP_DEADLINE",
                                      "ENDED_BY_PRIORITY_CAUSE")]
    assert a_entries(res)[-1]["response"]["bars_checked"] == "87" and not calls(res)


@pytest.mark.parametrize("side,ms", both(fx.intermediate_violation_then_valid), ids=["LONG", "SHORT"])
def test_intermediate_violation_terminates_and_a_later_recovery_never_reopens(side, ms):
    res = run(ms)
    assert steps(res) == [OPEN, REF, ("04:03:00", "TERMINAL", "TERMINAL", "LOCAL_RESPONSE_CONTRADICTED",
                                      "CONTRADICTED")]
    last = a_entries(res)[-1]["response"]
    assert last["decisive_bar"].endswith("@2025-09-01T04:02:00Z") and "response_bar" not in last
    assert not calls(res)
    # the contradiction ends only this child: the structural scenario stays confirmed
    scen = [e["record"] for e in res.journal if e["kind"] == "scenario" and e["record"]["scenario_id"][:2] in ("AL", "AS")]
    assert not [s for s in scen if s["transition"] == "TERMINAL" and s["env"]["clock_time"] < "2025-09-01T04:30"]


@pytest.mark.parametrize("side,ms", both(fx.violation_and_recovery_same_bar), ids=["LONG", "SHORT"])
def test_violation_and_favourable_close_in_one_bar_is_a_contradiction(side, ms):
    res = run(ms)
    assert steps(res)[-1] == ("04:03:00", "TERMINAL", "TERMINAL", "LOCAL_RESPONSE_CONTRADICTED", "CONTRADICTED")
    assert not calls(res)


@pytest.mark.parametrize("side,ms", both(fx.v_and_recovery_same_bar), ids=["LONG", "SHORT"])
def test_v_contact_takes_priority_over_a_local_recovery_without_intrabar_order(side, ms):
    res = run(ms)
    assert steps(res)[-1] == ("04:03:00", "TERMINAL", "TERMINAL", "SCENARIO_TERMINAL", "ENDED_BY_PRIORITY_CAUSE")
    last = a_entries(res)[-1]
    assert last["reason"] == "SCENARIO_TERMINAL:INVALIDATED:V_CONTACT"
    assert last["response"]["observed_in_priority_dispatch"].startswith("CONTRADICTION:")  # annotated, not counted
    assert "response_bar" not in last["response"] and not calls(res)


# ---------------------------------------------------------------------------------------------------------------------
# economics / geometry / selection at the first recovery (each consumes the child)
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.economics_insufficient), ids=["LONG", "SHORT"])
def test_recovery_with_insufficient_economics_is_not_issuable_and_consumes_the_child(side, ms):
    res = run(ms)
    assert steps(res) == [OPEN, REF, ("04:03:00", "TERMINAL", "TERMINAL", "RESPONSE_NOT_ISSUABLE", "NOT_ISSUABLE")]
    last = a_entries(res)[-1]
    assert last["blockers"] == ["REWARD_RISK_BELOW_MINIMUM"]
    assert (last["response"]["primary_reason"], last["response"]["primary_class"]) == (
        "REWARD_RISK_BELOW_MINIMUM", "ECONOMICS_GEOMETRY")
    d = 1 if side == "L" else -1
    assert not ref.passes(d, px(100030, side), px(99700, side), px(100700, side), 14)  # independent, per side
    assert not calls(res)


@pytest.mark.parametrize("side,ms", both(fx.outside_corridor), ids=["LONG", "SHORT"])
def test_recovery_outside_the_corridor_is_not_issuable(side, ms):
    res = run(ms)
    last = a_entries(res)[-1]
    assert steps(res)[-1] == ("04:03:00", "TERMINAL", "TERMINAL", "RESPONSE_NOT_ISSUABLE", "NOT_ISSUABLE")
    assert "CLOSE_OUTSIDE_RETURN_CORRIDOR" in last["blockers"]
    assert last["response"]["primary_reason"] == "CLOSE_OUTSIDE_RETURN_CORRIDOR" and not calls(res)


def _occupier(side):
    d = 1 if side == "L" else -1
    return CallV3(cid="call-occupier", aid="x#entry", family="B", d=d, origin="HISTORICAL_MODELED",
                  issued_at=T(4, 2), issue_seq=0, trigger_start=T(4), ref=D(100000), v=D(90000) if d > 0 else D(110000),
                  t=D(110000) if d > 0 else D(90000), target_type="LANDMARK", limiting=None, s15=D(2000),
                  area=(D(99000), D(101000)), expected=(30, 240), min_residual=30, hard_deadline=T(10),
                  progress_at=T(7), premise_kind="X", premise_level=D(1), scenario_id="x", confirmed_at=T(4, 2),
                  t_confirm=D(110000))


@pytest.mark.parametrize("side,ms", both(fx.valid), ids=["LONG", "SHORT"])
def test_selection_slot_occupied_is_not_issuable_without_retry(side, ms):
    """White-box: an unrelated ongoing call occupies the slot from after the 04:02 dispatch."""
    st = Stepper(ms, method="v0.5")
    st.run_until(T(4, 2))
    st.core.call = _occupier(side)
    st.run_until(T(4, 10))
    assert steps(st.journal) == [OPEN, REF, ("04:03:00", "TERMINAL", "REJECT", "RESPONSE_NOT_ISSUABLE",
                                             "NOT_ISSUABLE")]
    last = a_entries(st.journal)[-1]
    assert last["blockers"] == ["SLOT_OCCUPIED"] and last["response"]["primary_class"] == "SELECTION"
    assert not [c for c in calls(st.journal) if c["attempt_id"][:2] in ("AL", "AS")]


def _inject(st, t, make):
    """White-box: at the dispatch ``t`` add one extra actionable selection candidate built from the real one."""
    core = st.core
    orig = core._waits

    def waits(minutes, now):
        out = orig(minutes, now)
        if now == t and out:
            out.append(make(core, out[0]))
        return out

    core._waits = waits


def _rec():
    return {"geometry": {}, "containing": (), "selected": None, "limiting": None, "clocks": {}, "diagnostic": {}}


@pytest.mark.parametrize("side,ms", both(fx.valid), ids=["LONG", "SHORT"])
def test_selection_conflict_with_an_actionable_opposite_candidate(side, ms):
    def make(core, e):
        s = e["s"]
        fake = core.SCEN_CLS(sid=f"B{'S' if s.d > 0 else 'L'}-fake", family="B", d=-s.d, owner="box-fake",
                             born_at=T(4), born_seq=0, sources=[], setup_deadline=T(5), s15=D(2000), z=D(200))
        return {**{k: v for k, v in e.items() if k != "wait"}, "s": fake, "mode": "IMMEDIATE", "rec": _rec()}

    st = Stepper(ms, method="v0.5")
    st.run_until(T(4, 2))
    _inject(st, T(4, 3), make)
    st.run_until(T(4, 10))
    last = a_entries(st.journal)[-1]
    assert steps(st.journal)[-1] == ("04:03:00", "TERMINAL", "REJECT", "RESPONSE_NOT_ISSUABLE", "NOT_ISSUABLE")
    assert last["blockers"] == ["CONFLICTED"] and not calls(st.journal)


@pytest.mark.parametrize("side,ms", both(fx.valid), ids=["LONG", "SHORT"])
def test_selection_priority_candidate_in_the_same_direction_wins(side, ms):
    def make(core, e):
        s = e["s"]
        fake = dataclasses.replace(s, sid=s.sid[:3] + "0000-priority", born_at=s.born_at - timedelta(minutes=15),
                                   entry="PENDING", call_id=None)
        return {**{k: v for k, v in e.items() if k != "wait"}, "s": fake, "mode": "IMMEDIATE", "rec": _rec()}

    st = Stepper(ms, method="v0.5")
    st.run_until(T(4, 2))
    _inject(st, T(4, 3), make)
    st.run_until(T(4, 3, ))
    mine = [r for r in a_entries(st.journal) if "priority" not in r["scenario_id"]]
    assert [(r["transition"], r["reason"]) for r in mine][-1] == ("REJECT", "RESPONSE_NOT_ISSUABLE:PRIORITY")
    assert [c["scenario_id"] for c in calls(st.journal)] == [mine[-1]["scenario_id"][:3] + "0000-priority"]


# ---------------------------------------------------------------------------------------------------------------------
# deadlines, caps, coverage
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.deadline_at_recovery), ids=["LONG", "SHORT"])
def test_deadline_at_the_recovery_dispatch_precedes_the_decision(side, ms):
    res = run(ms)
    assert steps(res)[-1] == ("05:30:00", "TERMINAL", "TERMINAL", "ORIGINAL_SETUP_DEADLINE", "ENDED_BY_PRIORITY_CAUSE")
    last = a_entries(res)[-1]["response"]
    assert last["observed_in_priority_dispatch"] == "RECOVERY:okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T05:29:00Z"
    assert "response_bar" not in last and not calls(res)  # never a decisive recovery or a call


@pytest.mark.parametrize("side,ms", both(fx.new_cap_before_recovery), ids=["LONG", "SHORT"])
def test_a_new_cap_before_the_recovery_tightens_the_economics_without_resetting_the_reference(side, ms):
    res = run(ms)
    ents = [e for e in a_entries(res) if e["transition"] != "BLOCKERS"]  # inherited WAIT_RETURN blocker records
    assert [(s[0], s[1], s[2], s[3]) for s in steps(res) if s[2] != "BLOCKERS"] == [
        OPEN[:4], ref_step("04:45:00")[:4], ("05:00:00", "WAIT_RESPONSE", "CAP_REVISION", "NEW_ELIGIBLE_ZONE"),
        ("05:01:00", "TERMINAL", "TERMINAL", "RESPONSE_NOT_ISSUABLE")]
    assert not [s for s in steps(res) if s[2] == "BLOCKERS" and s[0] > "04:45:00"]  # none while waiting for the response
    cap = ents[2]
    assert D(cap["cap_history"][-1]["cap"]) == px(100495, side)
    assert {k: cap["response"][k] for k in ("H0", "L0", "published_at")} == \
        {k: ents[1]["response"][k] for k in ("H0", "L0", "published_at")}  # the reference does not move
    last = ents[-1]
    assert last["response"]["response_bar"].endswith("@2025-09-01T05:00:00Z")
    assert last["response"]["primary_class"] == "ECONOMICS_GEOMETRY" and "REWARD_RISK_BELOW_MINIMUM" in last["blockers"]
    d = 1 if side == "L" else -1
    assert ref.passes(d, px(100012, side), px(99700, side), px(100700, side), 14)  # would pass the original cap
    assert not ref.passes(d, px(100012, side), px(99700, side), px(100495, side), 14)
    assert not calls(res)


@pytest.mark.parametrize("side,ms", both(fx.cap_contact_in_activation_bar), ids=["LONG", "SHORT"])
def test_cap_contact_inside_the_activation_bar_is_ambiguous_and_takes_priority(side, ms):
    res = run(ms)
    assert steps(res)[-1] == ("05:00:00", "TERMINAL", "TERMINAL", "CAP_ACTIVATION_CONTACT_AMBIGUOUS",
                              "ENDED_BY_PRIORITY_CAUSE")
    assert a_entries(res)[-1]["response"]["observed_in_priority_dispatch"].startswith("RECOVERY:")
    assert not calls(res)


@pytest.mark.parametrize("side,ms", both(fx.gap_before_valid), ids=["LONG", "SHORT"])
def test_missing_minute_is_coverage_loss_never_an_absence_of_violation(side, ms):
    res = run(ms)
    assert steps(res)[-1] == ("04:03:00", "TERMINAL", "TERMINAL", "SCENARIO_TERMINAL", "ENDED_BY_PRIORITY_CAUSE")
    assert a_entries(res)[-1]["reason"].startswith("SCENARIO_TERMINAL:UNASSESSABLE:REQUIRED_MONITORING_GAP")
    assert not calls(res)


@pytest.mark.parametrize("side,ms", both(fx.blocked_first), ids=["LONG", "SHORT"])
def test_a_blocked_return_does_not_prepare_the_first_usable_one_does(side, ms):
    res = run(ms)
    # the inherited WAIT_RETURN blocker records: blocked at 04:02, cleared at 04:03 (then the reference)
    assert [(s[0], s[2]) for s in steps(res)] == [("04:01:00", "WAIT_OPEN"), ("04:02:00", "BLOCKERS"),
                                                  ("04:03:00", "BLOCKERS"), ("04:03:00", "RESPONSE_REFERENCE"),
                                                  ("04:04:00", "ISSUE")]
    assert a_entries(res)[1]["response"] is None  # a blocked bar prepares nothing
    assert a_entries(res)[3]["response"]["reference_bar"].endswith("@2025-09-01T04:02:00Z")


# ---------------------------------------------------------------------------------------------------------------------
# publication, cursor and the two §8 joints (delayed receipts)
# ---------------------------------------------------------------------------------------------------------------------

def delayed(ms, delays: dict):
    st = Stepper(ms, events=fx.delayed_events(ms, {fx.index_of(t): s for t, s in delays.items()}), method="v0.5")
    st.finish()
    return st


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("first", ["VALID", "VIOLATE"])
def test_late_reference_bars_ending_at_or_before_p0_give_no_local_response(side, first):
    """The reference [04:01,04:02) is received at 04:03 (p0 04:03); [04:02,04:03) is received at 04:03:30 - a recovery
    or a violation there ends at p0 and is ignored; only bars starting at/after p0 can decide ([04:03,04:04) ISSUE)."""
    ms = fx.tape(getattr(fx, first), fx.VALID)
    st = delayed(ms if side == "L" else fx.mirror(ms), {T(4, 1): 60, T(4, 2): 30})
    assert steps(st.journal) == [OPEN, ref_step("04:03:00"), ("04:04:00", "ISSUED", "ISSUE", "CALL", "ISSUED")]
    issue = a_entries(st.journal)[-1]["response"]
    assert issue["published_at"] == "2025-09-01T04:03:00+00:00" and issue["bars_checked"] == "1"
    assert issue["response_bar"].endswith("@2025-09-01T04:03:00Z")


@pytest.mark.parametrize("side", ["L", "S"])
def test_contact_straddling_the_publication_is_unassessable_without_renewal(side):
    """§8 joint 1: p0 04:02:30 (reference received 30 s late); [04:02,04:03) straddles p0 and breaks L0 (SHORT H0):
    LOCAL_CONTACT_TIME_AMBIGUOUS, no renewal - the later valid bar is never examined."""
    ms = fx.tape(fx.VIOLATE, fx.VALID)
    st = delayed(ms if side == "L" else fx.mirror(ms), {T(4, 1): 30})
    assert steps(st.journal) == [OPEN, ref_step("04:02:30"), ("04:03:00", "TERMINAL", "TERMINAL",
                                                              "LOCAL_CONTACT_TIME_AMBIGUOUS", "UNASSESSABLE")]
    assert not calls(st.journal)


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("bar", ["VALID", "EQUAL"])
def test_a_bar_straddling_the_publication_without_violation_cannot_confirm(side, bar):
    """A favourable straddling bar (also with the contrary extreme exactly at L0: equality is not ambiguous) neither
    confirms nor ends the child; the next bars decide (neutral, then a valid recovery issues at 04:05)."""
    ms = fx.tape(getattr(fx, bar), *fx.neutral(1), fx.VALID)
    st = delayed(ms if side == "L" else fx.mirror(ms), {T(4, 1): 30})
    assert steps(st.journal) == [OPEN, ref_step("04:02:30"), ("04:05:00", "ISSUED", "ISSUE", "CALL", "ISSUED")]
    assert a_entries(st.journal)[-1]["response"]["bars_checked"] == "3"


@pytest.mark.parametrize("side", ["L", "S"])
def test_first_recovery_observed_late_is_not_issuable_and_never_substituted(side):
    """§8 joint 2: [04:02,04:03) (valid) is received with [04:03,04:04) (also valid) in the 04:04 dispatch: the first
    ordered recovery is decisive but not the current bar - not issuable, the second is never used."""
    ms = fx.two_valid()
    st = delayed(ms if side == "L" else fx.mirror(ms), {T(4, 2): 60})
    assert steps(st.journal) == [OPEN, REF, ("04:04:00", "TERMINAL", "TERMINAL", "RESPONSE_NOT_ISSUABLE",
                                             "NOT_ISSUABLE")]
    r = a_entries(st.journal)[-1]["response"]
    assert (r["primary_reason"], r["primary_class"], r["response_current"]) == (
        "RESPONSE_OBSERVED_LATE_NOT_CURRENT", "LATE_OBSERVATION", "false")
    assert r["response_bar"].endswith("@2025-09-01T04:02:00Z") and not calls(st.journal)


@pytest.mark.parametrize("side", ["L", "S"])
def test_in_one_dispatch_the_safety_checks_of_every_bar_precede_the_recovery(side):
    """[04:02,04:03) valid recovery and [04:03,04:04) a contradiction admitted together: MP-004 §2/§3 order - the
    local contradiction precedes the recovery (annotated, never counted as a decisive recovery)."""
    ms = fx.recovery_then_violation()
    st = delayed(ms if side == "L" else fx.mirror(ms), {T(4, 2): 60})
    assert steps(st.journal)[-1] == ("04:04:00", "TERMINAL", "TERMINAL", "LOCAL_RESPONSE_CONTRADICTED", "CONTRADICTED")
    r = a_entries(st.journal)[-1]["response"]
    assert r["decisive_bar"].endswith("@2025-09-01T04:03:00Z")
    assert r["recovery_close_observed_before_priority"].endswith("@2025-09-01T04:02:00Z")


# ---------------------------------------------------------------------------------------------------------------------
# window boundaries
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side,ms", both(fx.valid), ids=["LONG", "SHORT"])
def test_warmup_reference_is_cleared_at_the_evaluation_start_and_never_reused(side, ms):
    res = run(ms, eval_start=T(4, 3))
    assert steps(res) == [OPEN, REF, ("04:03:00", "CLEARED", "CLEARED", "EVALUATION_START_CLEARS_PENDING_ENTRY",
                                      "CLEARED")]
    assert not calls(res)
    scen = [e["record"] for e in res.journal if e["kind"] == "scenario" and e["record"]["scenario_id"][:2] in ("AL", "AS")]
    assert scen[-1]["warmup_origin"] is True  # the structural scenario stays labelled warmup context


@pytest.mark.parametrize("side,ms", both(fx.favourable_equality_only), ids=["LONG", "SHORT"])
def test_evaluation_end_terminates_the_response_wait(side, ms):
    res = run(ms, eval_end=T(4, 30))
    assert steps(res)[-1] == ("04:30:00", "TERMINAL", "TERMINAL", "EVALUATION_WINDOW_ENDED", "ENDED_BY_PRIORITY_CAUSE")


# ---------------------------------------------------------------------------------------------------------------------
# inspection: waiting for the response is not an available entry
# ---------------------------------------------------------------------------------------------------------------------

def test_view_distinguishes_waiting_for_the_response_from_an_entry():
    st = Stepper(fx.favourable_equality_only(), method="v0.5")
    st.run_until(T(4, 1))
    row = next(r for r in st.core.scenarios_view(st.core.clock) if r["scenario_id"].startswith("AL"))
    assert row["waiting"]["phase"] == "WAIT_RETURN" and "usable price" in row["waiting"]["text"]
    st.run_until(T(4, 5))
    row = next(r for r in st.core.scenarios_view(st.core.clock) if r["scenario_id"].startswith("AL"))
    w = row["waiting"]
    assert w["phase"] == "WAIT_RESPONSE" and "no call yet, no entry" in w["text"]
    assert w["response"]["recovery_rule"] == "a later complete 1m close >= 100008.1 with low >= 99990"
    assert w["response"]["contradiction_rule"] == "low < 99990 ends this entry attempt"
    assert st.core.call is None and "WAITING_FOR_LOCAL_RESPONSE" in st.core._diag_conditions(st.core.clock)
    insp = st.core.inspect()
    assert insp["method_semantics"].startswith("MP-004 v0.5")
    assert next(iter(insp["responses"].values()))["phase"] == "WAIT_RESPONSE"


_ = Decimal
