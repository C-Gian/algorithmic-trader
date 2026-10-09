"""WP-015 (pure): MP-005 §6 reporting - the INITIAL_RESPONSE_INCOMPATIBLE terminal counts P and X only, is a subset of
X (never added twice) with a ratio over P, by base, direction and WAIT-open month; the identities stay unchanged; the
declared loss of C/R classifications; the Markdown carried by Copy report for chat; the v0.5/v0.6 comparison summary.
Synthetic engineering inputs only - no market data, no economic evaluation."""

from __future__ import annotations

import adviser6_fixtures as fx
import pytest
from test_mp004_report import ENG2, _facts, continuous_journal, ent, prepared

from algotrader.adviser import compare as cmp
from algotrader.adviser import report5 as r5
from algotrader.adviser import report6 as r6
from algotrader.adviser.core6 import REASON
from algotrader.adviser.harness import run_pure

ENG = {"adviser": {"eval_start": fx.DAY2.isoformat(), "eval_end": fx.DAY2.replace(day=2).isoformat()}}


def acc(journal, status="completed", eng=ENG):
    return r6.response_accounting(engine=eng, journal=journal, status=status)


def counts(**kw):
    return {**dict.fromkeys(r5.KEYS, 0), **kw}


@pytest.mark.parametrize("name,expected,base", [
    ("h1_economics", counts(W=1, P=1, X=1), "HISTORICAL_ECONOMICS"),
    ("h2_corridor", counts(W=1, P=1, X=1), "CORRIDOR"),
    ("h3_single_tick", counts(W=1, P=1, R=1, I=1), None),
    ("h4_deadline_collision", counts(W=1), None),
    ("h5_persistence", counts(W=1, P=1, X=1), "HISTORICAL_ECONOMICS"),
])
@pytest.mark.parametrize("side", ["L", "S"])
def test_fixture_journals_count_p_and_x_only_with_the_subset_of_x(name, expected, base, side):
    ms = getattr(fx, name)()
    res = run_pure(fx.DAY1, ms if side == "L" else fx.mirror(ms), eval_start=fx.DAY2, method="v0.6")
    t = acc(res.journal)["total"]
    assert t["counts"] == expected and t["identities_hold"], t["identities"]
    inc = t["initial_incompatibility"]
    assert inc["count"] == (1 if base else 0) and inc["subset_of_X"]
    assert t["identities"]["initial_incompatible_subset_of_X"]
    if base:
        assert inc["by_base"] == {"CORRIDOR": int(base == "CORRIDOR"),
                                  "HISTORICAL_ECONOMICS": int(base == "HISTORICAL_ECONOMICS")}
        assert inc["ratio_over_P"] == "1.0000" and t["other_endings_by_priority_cause"] == {REASON: 1}
        assert inc["by_direction"] == {"LONG": int(side == "L"), "SHORT": int(side == "S")}
        assert inc["concurrent_annotations"] == ({"HISTORICAL_ECONOMICS": 1} if base == "CORRIDOR" else {})
        ex = inc["examples"][0]
        assert ex["incompatibility_base"] == base and ex["C0"] and ex["F"]
    elif expected["P"]:
        assert inc["ratio_over_P"] == "0.0000"
    else:
        assert inc["ratio_over_P"] is None  # zero denominator = undefined
        assert t["ended_before_reference"] == {"ORIGINAL_SETUP_DEADLINE": 1}


def incompatible_end(at, eid, base="CORRIDOR", direction="LONG"):
    return ent(at, "TERMINAL", eid, reason=f"{REASON}:{base}", direction=direction,
               response={"outcome": REASON, "incompatibility_base": base, "bars_checked": "0",
                         "incompatibility_annotations": "HISTORICAL_ECONOMICS" if base == "CORRIDOR" else None})


def continuous_journal6():
    """The WP-014 continuous journal plus: a September SHORT child ended CORRIDOR at its preparation; an October LONG
    child opened 31 Oct 23:58 (October cohort) prepared and ended HISTORICAL_ECONOMICS at 23:59 in its preparation
    dispatch."""
    extra = [
        ent("2025-09-12T10:00:00+00:00", "WAIT_OPEN", "AS-6#entry", direction="SHORT"),
        ent("2025-09-12T10:01:00+00:00", "RESPONSE_REFERENCE", "AS-6#entry", direction="SHORT", response=prepared("e")),
        incompatible_end("2025-09-12T10:01:00+00:00", "AS-6#entry", "CORRIDOR", "SHORT"),
        ent("2025-10-05T23:58:00+00:00", "WAIT_OPEN", "AL-7#entry"),
        ent("2025-10-05T23:59:00+00:00", "RESPONSE_REFERENCE", "AL-7#entry", response=prepared("f")),
        incompatible_end("2025-10-05T23:59:00+00:00", "AL-7#entry", "HISTORICAL_ECONOMICS"),
    ]
    return sorted(continuous_journal() + extra, key=lambda e: e["clock_time"])


def test_months_follow_the_wait_open_cohort_and_the_subset_never_adds_to_x():
    a = acc(continuous_journal6(), status="running", eng=ENG2)
    t = a["total"]
    assert t["counts"] == counts(W=7, P=6, C=1, R=2, N=1, I=1, X=2, A=1) and t["identities_hold"]
    assert t["initial_incompatibility"]["count"] == 2 == t["counts"]["X"]  # subset (here all of X), not added again
    assert t["initial_incompatibility"]["by_base"] == {"CORRIDOR": 1, "HISTORICAL_ECONOMICS": 1}
    assert t["initial_incompatibility"]["ratio_over_P"] == "0.3333"
    m = a["months"]
    assert m["2025-09"]["initial_incompatibility"]["count"] == 1 and m["2025-10"]["initial_incompatibility"]["count"] == 1
    assert a["months_reconcile"]["months_sum_to_total"] and a["months_reconcile"]["every_month_identities_hold"]
    assert a["months_reconcile"]["initial_incompatible_months_sum_to_total"]
    # the same journal read by the v0.5 report gives the same W/P/C/R/N/I/X/A (no double counting in v0.6)
    assert r5.response_accounting(engine=ENG2, journal=continuous_journal6(), status="running")["total"]["counts"] == \
        t["counts"]


def test_identity_failure_of_the_subset_is_visible():
    j = continuous_journal6()
    a = acc(j, status="running", eng=ENG2)
    sec = a["total"]
    sec["other_endings_by_priority_cause"] = {}  # simulate a broken partition
    r6._attach(sec, [f for f in r5.child_fates(j).values() if f["opened_at"] >= "2025-09-01"])
    assert not sec["initial_incompatibility"]["subset_of_X"] and not sec["identities_hold"]


def test_markdown_for_copy_report_carries_the_subset_bases_months_and_the_declared_loss():
    a = acc(continuous_journal6(), status="running", eng=ENG2)
    md = "\n".join(r6.incompatibility_markdown(a))
    assert "#### Initial response incompatibility (MP-005 §6; subset of X)" in md
    assert "| Total | 2 | 1 | 1 | 2 | 6 | 0.3333 | yes |" in md
    assert "| 2025-09 | 1 | 1 | 0 |" in md and "| 2025-10 | 1 | 0 | 1 |" in md
    assert "never added a second time" in md and "not invalidated" in md and "no later local classification" in md
    assert "initial incompatibility sums to total yes" in md
    empty = "\n".join(r6.incompatibility_markdown(acc([], eng=ENG2)))
    assert "| Total | 0 | 0 | 0 | 0 | 0 | undef. | yes |" in empty


def test_comparison_names_the_mp005_delta_and_carries_the_subset():
    base = {"report_version": "adviser.report.v5", "calls": {"count": 1}, "outcomes": {"variants": {"PRIMARY": {}}},
            "funnel": {"evidence_threshold": {"status": "NOT_APPLICABLE"}}, "anchors": {"owners": {}},
            "responses": r5.response_accounting(engine=ENG2, journal=continuous_journal(), status="completed")}
    acc6 = acc(continuous_journal6(), eng=ENG2)
    cand = {**base, "report_version": "adviser.report.v6", "responses": acc6}
    c = cmp.build(_facts("v0.5", base), _facts("v0.6", cand))
    assert c["comparability"]["verdict"] == "COMPARABLE"
    assert [x["id"] for x in c["limitations"]] == ["V06_MP005_INITIAL_RESPONSE_INCOMPATIBILITY_DELTA"]
    assert "lose the later C/R classification" in c["limitations"][0]["text"]
    assert c["conclusion"]["verdict"] == "REPORTED_FOR_DIRECTOR_REVIEW"
    assert c["b"]["responses"]["initial_incompatibility"]["count"] == 2
    assert "initial_incompatibility" not in c["a"]["responses"]
    md = cmp.render_markdown(c)
    assert "baseline v0.5 (A) vs candidate v0.6 (B)" in md
    assert "INITIAL_RESPONSE_INCOMPATIBLE (MP-005; subset of X, not added again): 2" in md
    assert "v0.5 -> v0.6: the initial response incompatibility terminal" in c["scope"]
    # v0.4/v0.6 names both deltas; v0.4/v0.5 is unchanged
    four = {**base, "report_version": "adviser.report.v4"}
    four.pop("responses")
    assert [x["id"] for x in cmp.build(_facts("v0.4", four), _facts("v0.6", cand))["limitations"]] == [
        "V05_MP004_RETURN_RESPONSE_DELTA", "V06_MP005_INITIAL_RESPONSE_INCOMPATIBILITY_DELTA"]
    assert [x["id"] for x in cmp.build(_facts("v0.4", four), _facts("v0.5", base))["limitations"]] == [
        "V05_MP004_RETURN_RESPONSE_DELTA"]
