"""WP-014 correction (Astra review of 0526641): F1 first decisive local event, F2 inherited economic terminals during
WAIT_RESPONSE, F3 the earlier 20-owner RETURN convention NOT_APPLICABLE to v0.5, and the authorized alignments (late
recovery in OTHER_GATES, start = p0 in the active domain, WAIT-open cohort in the comparison). Synthetic engineering
inputs only; every regression runs LONG and SHORT where the rule is directional."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import adviser5_fixtures as fx
import pytest
from adviser3_fixtures import Stepper
from test_adviser_live import COMPAT, Clock, fetcher

from algotrader.adviser import compare as cmp
from algotrader.adviser import live as lv
from algotrader.adviser import methods
from algotrader.adviser import report3 as r3
from algotrader.adviser import report4 as r4
from algotrader.adviser import report5 as r5
from algotrader.adviser.core import Quote
from algotrader.adviser.core5 import primary_reason, reason_class
from algotrader.adviser.harness import historical_profile, run_pure
from algotrader.feed.contracts import Family

T, D = fx.T, Decimal
ENG = {"adviser": {"eval_start": fx.DAY2.isoformat(), "eval_end": fx.DAY2.replace(day=2).isoformat()}}


def side(ms, s):
    return ms if s == "L" else fx.mirror(ms)


def a_ents(journal):
    return [e["record"] for e in journal if e["kind"] == "entry_attempt" and e["record"]["scenario_id"][:2] in ("AL", "AS")]


def delayed(ms, delays):
    st = Stepper(ms, events=fx.delayed_events(ms, {fx.index_of(t): s for t, s in delays.items()}), method="v0.5")
    st.finish()
    return st


def counts(journal):
    return r5.response_accounting(engine=ENG, journal=journal, status="completed")["total"]


# ---------------------------------------------------------------------------------------------------------------------
# F1 - the first ordered decisive local event consumes the sequence
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s", ["L", "S"])
def test_f1_recovery_then_violation_in_one_dispatch_is_a_late_first_recovery(s):
    """[04:02,04:03) valid recovery and [04:03,04:04) a contrary break admitted together (04:04 dispatch): the first
    ordered decisive event is the recovery, already consumed (late, not current); the later break never reclassifies
    it."""
    st = delayed(side(fx.recovery_then_violation(), s), {T(4, 2): 60})
    last = a_ents(st.journal)[-1]
    assert last["reason"] == "RESPONSE_NOT_ISSUABLE:RESPONSE_OBSERVED_LATE_NOT_CURRENT"
    r = last["response"]
    assert (r["outcome"], r["response_current"]) == ("NOT_ISSUABLE", "false")
    assert r["response_bar"].endswith("@2025-09-01T04:02:00Z") and "decisive_bar" not in r
    t = counts(st.journal)
    assert {k: t["counts"][k] for k in ("C", "R", "N", "I")} == {"C": 0, "R": 1, "N": 1, "I": 0}
    assert t["not_issuable"]["late_first_recovery"] == 1 and t["identities_hold"]


@pytest.mark.parametrize("s", ["L", "S"])
def test_f1_violation_then_recovery_in_one_dispatch_is_a_contradiction(s):
    st = delayed(side(fx.intermediate_violation_then_valid(), s), {T(4, 2): 60})
    last = a_ents(st.journal)[-1]
    assert last["reason"].startswith("LOCAL_RESPONSE_CONTRADICTED:") and last["response"]["outcome"] == "CONTRADICTED"
    assert last["response"]["decisive_bar"].endswith("@2025-09-01T04:02:00Z") and "response_bar" not in last["response"]
    t = counts(st.journal)
    assert {k: t["counts"][k] for k in ("C", "R", "N", "I")} == {"C": 1, "R": 0, "N": 0, "I": 0}


@pytest.mark.parametrize("s", ["L", "S"])
def test_f1_violation_and_recovery_in_the_same_bar_stays_a_contradiction(s):
    res = run_pure(fx.DAY1, side(fx.violation_and_recovery_same_bar(), s), eval_start=fx.DAY2, method="v0.5")
    last = a_ents(res.journal)[-1]
    assert last["reason"].startswith("LOCAL_RESPONSE_CONTRADICTED:")
    assert counts(res.journal)["counts"]["C"] == 1 and counts(res.journal)["counts"]["R"] == 0


@pytest.mark.parametrize("s", ["L", "S"])
def test_f1_inherited_protections_still_cover_the_whole_dispatch(s):
    """Recovery [04:02,04:03) then a V contact [04:03,04:04) admitted together: the scenario V contact (inherited,
    whole dispatch) ends the child first - no decisive recovery is counted."""
    ms = fx.tape(fx.VALID, fx.minute(100005, 100006, 99700, 99800))
    st = delayed(side(ms, s), {T(4, 2): 60})
    last = a_ents(st.journal)[-1]
    assert last["reason"] == "SCENARIO_TERMINAL:INVALIDATED:V_CONTACT"
    assert counts(st.journal)["counts"]["R"] == 0 and counts(st.journal)["counts"]["X"] == 1


# ---------------------------------------------------------------------------------------------------------------------
# F2 - inherited economic terminals keep their place during WAIT_RESPONSE
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s", ["L", "S"])
def test_f2_cap_revision_emptying_the_historical_region_terminates_before_any_local_response(s):
    res = run_pure(fx.DAY1, side(fx.cap_empties_economic_region(fx.VALID, fx.VALID), s), eval_start=fx.DAY2,
                   method="v0.5")
    ents = [e for e in a_ents(res.journal) if e["transition"] != "BLOCKERS"]
    assert [(e["env"]["clock_time"][11:19], e["transition"]) for e in ents] == [
        ("04:01:00", "WAIT_OPEN"), ("04:45:00", "RESPONSE_REFERENCE"), ("05:00:00", "CAP_REVISION"),
        ("05:00:00", "TERMINAL")]
    last = ents[-1]
    assert last["reason"] == "NO_ECONOMIC_RETURN_REGION" and last["state"] == "TERMINAL"
    assert last["response"]["outcome"] == "ENDED_BY_PRIORITY_CAUSE"
    assert D(last["cap_history"][-1]["cap"]) == (D("100300.0") if s == "L" else D("99700.0"))
    assert not [c for c in (e["record"] for e in res.journal if e["kind"] == "call")]  # no reopening afterwards
    t = counts(res.journal)
    assert (t["counts"]["X"], t["counts"]["R"], t["counts"]["A"]) == (1, 0, 0)
    assert t["other_endings_by_priority_cause"] == {"NO_ECONOMIC_RETURN_REGION": 1}


@pytest.mark.parametrize("s", ["L", "S"])
def test_f2_empty_effective_corridor_terminates_before_any_local_response(s):
    """White-box: after the reference, the current cap is moved below the corridor (LONG 99850 / SHORT 100150); at the
    next dispatch the effective corridor is empty: EMPTY_RETURN_CORRIDOR, never a later local decision."""
    st = Stepper(side(fx.tape(fx.VALID), s), method="v0.5")
    st.run_until(T(4, 2))
    w = next(iter(st.core.waits.values()))
    assert w.phase == "WAIT_RESPONSE"
    w.cap = D(99850) if s == "L" else D(100150)
    st.finish()
    last = a_ents(st.journal)[-1]
    assert (last["env"]["clock_time"][11:19], last["reason"]) == ("04:03:00", "EMPTY_RETURN_CORRIDOR")
    assert not [e for e in st.journal if e["kind"] == "call"]
    assert counts(st.journal)["other_endings_by_priority_cause"] == {"EMPTY_RETURN_CORRIDOR": 1}


@pytest.mark.parametrize("s", ["L", "S"])
def test_f2_a_single_unsuitable_price_with_a_non_empty_region_is_not_issuable(s):
    """New cap 100495 leaves the region non-empty ([99900, 99920.4]): the recovery at 100012 is a single unsuitable
    price -> RESPONSE_NOT_ISSUABLE (N), distinct from the empty-region terminal (X)."""
    res = run_pure(fx.DAY1, side(fx.new_cap_before_recovery(), s), eval_start=fx.DAY2, method="v0.5")
    last = a_ents(res.journal)[-1]
    assert last["reason"] == "RESPONSE_NOT_ISSUABLE:REWARD_RISK_BELOW_MINIMUM"
    assert "NO_ECONOMIC_RETURN_REGION" not in last["blockers"]
    assert counts(res.journal)["counts"]["N"] == 1


def _live(mins, until, spreads):
    clock = Clock(fx.DAY2 + timedelta(hours=3, minutes=16, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.5")
    sess.start(None, fetcher(mins))
    sess.on_connection("CONNECTED", clock.t)
    t = fx.DAY2 + timedelta(hours=3, minutes=16)
    long_side = mins[0].c < 100000  # mirrored tapes start above 100000
    while t < until:
        m = mins[int((t - fx.DAY1) / timedelta(minutes=1))]
        close = t + timedelta(minutes=1)
        clock.t = close + timedelta(milliseconds=500)
        sp = D(spreads.get(t, 0))
        bid, ask = (m.c - sp, m.c) if long_side else (m.c, m.c + sp)  # the side price stays the close
        sess.on_quote(Quote(bid, ask, clock.t, clock.t, "BTC-USDT-SWAP", "q" * 64), clock.t)
        clock.t = close + timedelta(seconds=1)
        for fam in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
            ohlc = (m.o, m.h, m.lo, m.c) if fam == Family.TRADE_BAR_1M else (m.c, m.c, m.c, m.c)
            sess.on_live_bar(fam, t, ohlc, ("100", "1", str(m.c)), clock.t)
        clock.t = close + timedelta(milliseconds=1500)
        sess.tick(clock.t)
        t = close
    return sess


WIDE = {T(4, m): 300 for m in (4, 5, 6, 7)}  # half-spread ~15 bps: live K ~29 bps, no admissible price in the corridor


@pytest.mark.parametrize("s", ["L", "S"])
def test_f2_live_temporary_cost_block_is_not_terminal_while_waiting(s):
    """Live: the cost envelope is temporarily too wide during WAIT_RESPONSE (no admissible price): the wait continues
    (A at the cutoff); spreads normalise and the first wholly-domain recovery issues."""
    mins = side(fx.live_tape(*fx.neutral(4), fx.VALID), s)
    mid = _live(mins, T(4, 8), WIDE)
    j, _, _ = mid.driver.take()
    assert [e["transition"] for e in a_ents(j) if e["transition"] != "BLOCKERS"] == ["WAIT_OPEN", "RESPONSE_REFERENCE"]
    assert next(iter(mid.driver.rt.core.waits.values())).phase == "WAIT_RESPONSE"
    assert r5.response_accounting(engine=ENG, journal=j, status="running")["total"]["counts"]["A"] == 1
    done = _live(mins, T(4, 10), WIDE)
    j2, _, _ = done.driver.take()
    assert [e["transition"] for e in a_ents(j2) if e["transition"] != "BLOCKERS"][-1] == "ISSUE"


@pytest.mark.parametrize("s", ["L", "S"])
def test_f2_live_cost_block_at_the_recovery_consumes_the_child(s):
    mins = side(fx.live_tape(*fx.neutral(1), fx.VALID, fx.VALID), s)
    sess = _live(mins, T(4, 9), {T(4, 5): 300})
    j, _, _ = sess.driver.take()
    last = [e for e in a_ents(j) if e["transition"] != "BLOCKERS"][-1]
    assert last["reason"].startswith("RESPONSE_NOT_ISSUABLE:") and "TEMPORARY_COST_BLOCKED" in last["blockers"]
    assert not [e for e in j if e["kind"] == "call"]  # the later valid bar never reopens it


# ---------------------------------------------------------------------------------------------------------------------
# alignments
# ---------------------------------------------------------------------------------------------------------------------

def test_late_recovery_is_classified_in_other_gates_with_its_specific_reason():
    assert reason_class("RESPONSE_OBSERVED_LATE_NOT_CURRENT") == "OTHER_GATES"
    assert primary_reason(["RESPONSE_OBSERVED_LATE_NOT_CURRENT"]) == "RESPONSE_OBSERVED_LATE_NOT_CURRENT"
    st = delayed(fx.two_valid(), {T(4, 2): 60})
    t = counts(st.journal)
    assert t["not_issuable"]["primary_class"] == {"OTHER_GATES": 1} and t["not_issuable"]["late_first_recovery"] == 1
    assert t["not_issuable"]["primary_reason"] == {"RESPONSE_OBSERVED_LATE_NOT_CURRENT": 1}


def test_a_bar_starting_exactly_at_p0_is_in_the_active_domain():
    """Historical modeled publication p0 = 04:02 = the next bar's start: [04:02,04:03) is wholly in the domain and
    decides (start = p0 is not straddling; straddling needs start < p0 < end)."""
    res = run_pure(fx.DAY1, fx.valid(), eval_start=fx.DAY2, method="v0.5")
    ref, issue = [e for e in a_ents(res.journal) if e["transition"] in ("RESPONSE_REFERENCE", "ISSUE")]
    assert ref["response"]["published_at"] == "2025-09-01T04:02:00+00:00"
    assert issue["response"]["response_bar"].endswith("@2025-09-01T04:02:00Z")


# ---------------------------------------------------------------------------------------------------------------------
# F3 - the earlier 20-owner RETURN convention is NOT_APPLICABLE to v0.5
# ---------------------------------------------------------------------------------------------------------------------

def _report(method, minimum, monkeypatch):
    monkeypatch.setattr(r3, "EVIDENCE_MIN_OWNERS", minimum)
    ee = fx.DAY2 + timedelta(hours=10)
    res = run_pure(fx.DAY1, fx.valid(), eval_start=fx.DAY2, eval_end=ee, method=method)
    rel, profile = methods.get(method), historical_profile()
    adv = {"method": method, "identity": rel.composite_identity(profile, {"pack_id": "synthetic"}, None),
           "profile": profile.model_dump(mode="json"), "evaluator": res.runtime.ev.identity(), "tick": "0.1",
           "eval_start": fx.DAY2.isoformat(), "eval_end": ee.isoformat(), "warmup_start": fx.DAY1.isoformat(),
           "tail_end": ee.isoformat(), "clock_end": ee.isoformat()}
    builder = r5 if method == "v0.5" else r4
    rep = builder.build(engine={"adviser": adv}, journal=res.journal, records=res.records, view=None,
                        status="completed", clock_end_reached=True)
    return rep, "\n".join(builder.render_markdown(rep))


def test_f3_the_v05_verdict_and_markdown_do_not_move_across_the_inherited_minimum(monkeypatch):
    """One distinct A RETURN owner entered at 60 s. Inherited minimum 2 (= 19 -> 20 below) vs 1 (reached): the v0.5
    verdict, threshold status and Markdown are identical; the count stays descriptive."""
    below, md_below = _report("v0.5", 2, monkeypatch)
    reached, md_reached = _report("v0.5", 1, monkeypatch)
    for rep in (below, reached):
        et = rep["funnel"]["evidence_threshold"]
        assert et["status"] == "NOT_APPLICABLE" and et["registered_minimum_distinct_owners"] is None
        assert et["observed"] == 1 and rep["funnel"]["a_return_owners_entered_primary_60s"] == 1
        assert not any("INSUFFICIENT_EVIDENCE" in str(x) for x in rep.get("diagnosis") or [])
    assert below["conclusion"] == reached["conclusion"]
    assert below["conclusion"]["verdict"] == "REPORTED_FOR_DIRECTOR_REVIEW"
    assert "no registered evidence criterion" in below["conclusion"]["text"]
    assert md_below == md_reached
    assert "NOT_APPLICABLE" in md_below and "registered minimum for discussion" not in md_below


def test_f3_earlier_versions_keep_their_threshold_behaviour(monkeypatch):
    below, _ = _report("v0.4", 2, monkeypatch)
    reached, _ = _report("v0.4", 1, monkeypatch)
    assert below["funnel"]["evidence_threshold"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert reached["funnel"]["evidence_threshold"]["status"] == "MINIMUM_REPORTING_COUNT_REACHED"
    assert below["conclusion"]["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert reached["conclusion"]["verdict"] == "REPORTED_FOR_DIRECTOR_REVIEW"


def _facts(method, threshold_status, observed=1, months=None):
    a = {"report_version": f"adviser.report.v{method[-1]}", "calls": {"count": 1},
         "outcomes": {"variants": {"PRIMARY": {}}},
         "funnel": {"evidence_threshold": {"status": threshold_status, "observed": observed},
                    "a_return_owners_entered_primary_60s": observed}}
    if method == "v0.5":
        a["responses"] = {"total": {"counts": dict.fromkeys(r5.KEYS, 0), "ratios": {}, "identities_hold": True,
                                    "not_issuable": {"primary_reason": {}}},
                          "months": months or {}, "months_attribution": "x", "cutoff": None}
    return {"evaluation_id": f"ev-{method}", "replay_id": "r", "status": "completed", "method": method,
            "model": "m", "rules_version": "r", "rules_sha256": "s", "register_sha256": "g", "implementation": "i",
            "identity_sha256": method, "capability_profile_sha256": "p", "pins": {k: "same" for k in cmp.PIN_FIELDS},
            "pack_manifest_sha256": "m", "evaluator_terms": {}, "evaluator_sha256": "e", "assurance": "PASSED",
            "validation_outcome": "passed", "adviser": a}


@pytest.mark.parametrize("baseline_status", ["INSUFFICIENT_EVIDENCE", "MINIMUM_REPORTING_COUNT_REACHED"])
@pytest.mark.parametrize("observed", [19, 20])
def test_f3_the_comparison_never_transfers_the_baseline_criterion_to_the_v05_candidate(baseline_status, observed):
    c = cmp.build(_facts("v0.4", baseline_status, 20), _facts("v0.5", "NOT_APPLICABLE", observed))
    assert c["conclusion"]["verdict"] == "REPORTED_FOR_DIRECTOR_REVIEW"
    assert "no registered evidence criterion for the candidate" in c["conclusion"]["text"]
    assert "registered minimum" not in c["conclusion"]["text"]
    md = cmp.render_markdown(c)
    assert "Evidence criterion: NOT_APPLICABLE for v0.5" in md


def test_f3_comparison_months_carry_the_wait_open_cohort_explanation():
    months = {"2025-09": dict.fromkeys(r5.KEYS, 0)}
    c = cmp.build(_facts("v0.4", "INSUFFICIENT_EVIDENCE"), _facts("v0.5", "NOT_APPLICABLE", months=months))
    assert c["b"]["responses"]["cohort"] == cmp.RESPONSE_COHORT
    md = cmp.render_markdown(c)
    assert cmp.RESPONSE_COHORT in md and "month of issue" in cmp.RESPONSE_COHORT
