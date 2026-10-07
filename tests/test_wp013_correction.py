"""WP-013 correction (Astra review of 41790dd, F1-F2 only; pure): the copyable continuous-run Markdown shows every
variant's populations and states, sums carry their population, monthly MarketView/sample/scenario/D-N summaries are
in the copyable text, and expected call-variant outcomes without a terminal record are counted (by variant and issue
month) apart from the arithmetic reconciliation of the available records. Synthetic records only - no market data,
no economic evaluation."""

from __future__ import annotations

import copy
from decimal import Decimal

from algotrader.adviser import report_periods as rp

V4 = ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY")
ENG = {"adviser": {"eval_start": "2025-09-01T00:00:00+00:00", "eval_end": "2025-11-01T00:00:00+00:00",
                   "evaluator": {"format": "algotrader.adviser-evaluation.v1", "sha256": "e",
                                 "profiles": {v: {"entry_delay_seconds": 60} for v in V4}}}}


def env(t):
    return {"published_at": t, "clock_time": t, "origin": "HISTORICAL_MODELED"}


def j(kind, t, **rec):
    return {"kind": kind, "clock_time": t, "record": {"env": env(t), **rec}}


def call(t, cid):
    return j("call", t, call_id=cid, issued_at=t, family="A", entry_mode="IMMEDIATE")


def path(cid, variant, status, net=None, exit_t=None):
    return {"kind": "path", "record": {"call_id": cid, "variant": variant, "status": status, "price_net": net,
                                       "exit_class": "TARGET" if status == "CLOSED" else None,
                                       "exit": {"time_end": exit_t} if exit_t else None}}


def base_journal(last="2025-10-01T00:05:00+00:00"):
    out = [j("market_view", "2025-09-01T00:00:00+00:00", table_row="NO_QUALIFIED_STRUCTURE"),
           j("scenario", "2025-09-30T23:40:00+00:00", family="A", transition="CONFIRM", scenario_id="AL-1"),
           j("entry_attempt", "2025-09-30T23:50:00+00:00", family="A", transition="ISSUE", entry_attempt_id="AL-1#e",
             reason="call-1", diagnostic={"in_D": "true", "in_N": "true"}),
           call("2025-09-30T23:50:00+00:00", "call-1"),
           j("market_view", last, table_row="BALANCED_RANGE")]
    return sorted(out, key=lambda e: e["clock_time"])


BASE = {"funnel": {"issued": 1, "a_confirmations": 1, "waiting": {"opened": 0}}}


def md_of(pr):
    return "\n".join(rp.render_markdown({"periods": pr}))


# 1 -------------------------------------------------------------------------------------------------------------------

def test_variant_populations_and_states_differ_and_are_in_the_copyable_markdown():
    recs = [path("call-1", "PRIMARY", "CLOSED", "0.0025", "2025-10-01T01:00:00Z"),
            path("call-1", "ENTRY_DELAY_0", "CLOSED", "0.0030", "2025-10-01T01:00:00Z"),
            path("call-1", "ENTRY_DELAY_120", "NO_ENTRY"),
            path("call-1", "HORIZON_ONLY", "CENSORED")]
    pr = rp.periods(engine=ENG, journal=base_journal(), records=recs, base=BASE, status="running")
    sep = pr["months"]["2025-09"]["hypothetical"]
    assert sep["PRIMARY"]["by_status"] == {"CLOSED": 1, "NO_ENTRY": 0, "CENSORED": 0, "UNRESOLVED": 0, "AMBIGUOUS": 0}
    assert sep["ENTRY_DELAY_120"]["by_status"]["NO_ENTRY"] == 1 and sep["HORIZON_ONLY"]["by_status"]["CENSORED"] == 1
    assert sep["ENTRY_DELAY_120"]["economic_result_observed"] is False
    assert sep["PRIMARY"]["sum_population"] == {"closed_with_price_net": 1, "records_available": 1, "expected_pairs": 1}
    md = md_of(pr)
    # one row per variant with records / CLOSED / with price-net / NO_ENTRY / CENSORED / UNRESOLVED / AMBIGUOUS
    assert "| 2025-09 | PRIMARY | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | +0.250% over 1 closed |" in md
    assert "| 2025-09 | ENTRY_DELAY_120 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | none observed (0 closed) |" in md
    assert "| 2025-09 | HORIZON_ONLY | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | none observed (0 closed) |" in md
    assert "| TOTAL | ENTRY_DELAY_0 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | +0.300% over 1 closed |" in md
    # a variant without a closed result never shows a bare 0.000% as an observed economic result
    assert "ENTRY_DELAY_120 0.000%" not in md and "HORIZON_ONLY 0.000%" not in md


# 2 / 3 ---------------------------------------------------------------------------------------------------------------

def test_end_of_month_call_without_terminal_records_is_pending_at_the_next_checkpoint():
    pr = rp.periods(engine=ENG, journal=base_journal(), records=[], base=BASE, status="running")
    oc = pr["outcome_completeness"]
    assert oc["state"] == "OUTCOMES_NOT_YET_RECORDED_AT_CHECKPOINT" and oc["run_status"] == "running"
    assert (oc["evaluable_calls"], oc["expected_pairs"], oc["terminal_records_available"],
            oc["awaiting_terminal_record"]) == (1, 4, 0, 4)
    assert oc["by_variant"]["PRIMARY"]["awaiting_by_issue_month"] == {"2025-09": 1, "2025-10": 0}
    sep, octo = pr["months"]["2025-09"]["hypothetical"], pr["months"]["2025-10"]["hypothetical"]
    assert all(sep[v]["awaiting_terminal_record"] == 1 and sep[v]["records_available"] == 0 for v in V4)
    assert all(octo[v]["expected_pairs"] == 0 for v in V4)
    # nothing is invented: no entry, outcome, economic result or censoring for the missing pairs
    assert all(sep[v]["by_status"] == dict.fromkeys(rp.STATUSES, 0) and not sep[v]["economic_result_observed"]
               for v in V4)
    # arithmetic reconciliation of the available records passes; it is not outcome completeness
    assert pr["reconciliation"]["all_passed"] and pr["reconciliation"]["scope"] == "ARITHMETIC_OF_AVAILABLE_RECORDS"
    md = md_of(pr)
    assert "outcome not yet recorded at checkpoint" in md
    assert "Reconciliation total vs months: PASS (arithmetic of the available records only" in md
    assert "Outcome completeness: OUTCOMES NOT YET RECORDED AT CHECKPOINT — 4 of 4 expected" in md
    assert "| 2025-09 | PRIMARY | 1 | 0 | 1 |" in md and "REPORT INCOMPLETE" not in md


def test_a_completed_run_missing_an_expected_terminal_record_makes_the_report_explicitly_incomplete():
    recs = [path("call-1", v, "CLOSED", "0.001", "2025-10-01T01:00:00Z") for v in V4[:3]]
    base = copy.deepcopy(BASE)
    pr = rp.periods(engine=ENG, journal=base_journal(), records=recs, base=base, status="completed")
    oc = pr["outcome_completeness"]
    assert oc["state"] == "REPORT_INCOMPLETE_EXPECTED_TERMINAL_RECORD_MISSING" and oc["awaiting_terminal_record"] == 1
    assert oc["by_variant"]["HORIZON_ONLY"]["awaiting_by_issue_month"]["2025-09"] == 1
    assert pr["reconciliation"]["all_passed"]  # the available records still reconcile arithmetically
    assert base == BASE  # the saved run facts handed in are not modified
    md = md_of(pr)
    assert "REPORT INCOMPLETE" in md and "saved status and assurance are unchanged" in md
    assert "HORIZON_ONLY 1 (2025-09 1)" in md


def test_feed_coverage_is_not_finalization_a_running_run_at_the_clock_end_is_still_pending():
    pr = rp.periods(engine=ENG, journal=base_journal(last="2025-11-01T00:00:00+00:00"), records=[], base=BASE,
                    status="running")
    assert pr["total"]["coverage"]["covered_minutes"] == pr["total"]["coverage"]["minutes"]
    assert pr["outcome_completeness"]["state"] == "OUTCOMES_NOT_YET_RECORDED_AT_CHECKPOINT"


# 4 -------------------------------------------------------------------------------------------------------------------

def test_terminal_records_available_later_are_counted_once_with_unchanged_attribution():
    early = rp.periods(engine=ENG, journal=base_journal(), records=[], base=BASE, status="running")
    recs = [path("call-1", "PRIMARY", "CLOSED", "-0.0040000000000000000000000000001", "2025-10-01T00:10:00Z"),
            path("call-1", "ENTRY_DELAY_0", "CLOSED", "0.0010", "2025-10-01T00:10:00Z"),
            path("call-1", "ENTRY_DELAY_120", "AMBIGUOUS"),
            path("call-1", "HORIZON_ONLY", "UNRESOLVED")]
    later = rp.periods(engine=ENG, journal=base_journal(last="2025-10-02T00:00:00+00:00"), records=recs, base=BASE,
                       status="running")
    assert early["months"]["2025-09"]["calls"]["call_ids"] == later["months"]["2025-09"]["calls"]["call_ids"] == \
        ["call-1"]
    oc = later["outcome_completeness"]
    assert oc["state"] == "COMPLETE" and oc["terminal_records_available"] == 4 and oc["duplicate_terminal_records"] == 0
    sep, tot = later["months"]["2025-09"]["hypothetical"], later["total"]["hypothetical"]
    assert sep["PRIMARY"]["exits_after_period_end"] == 1 and later["months"]["2025-10"]["hypothetical"]["PRIMARY"][
        "records_available"] == 0
    assert all(tot[v]["records_available"] == 1 for v in V4)
    assert Decimal(tot["PRIMARY"]["sum_price_net_normalized"]) == Decimal("-0.0040000000000000000000000000001")
    assert later["reconciliation"]["all_passed"], later["reconciliation"]["checks"]
    # a repeated terminal record for the same pair is not counted twice and is reported
    dup = rp.periods(engine=ENG, journal=base_journal(), records=recs + recs[:1], base=BASE, status="running")
    assert dup["total"]["hypothetical"]["PRIMARY"]["records_available"] == 1
    assert dup["outcome_completeness"]["duplicate_terminal_records"] == 1
    assert not dup["reconciliation"]["checks"]["no_duplicate_terminal_records"]


# 5 -------------------------------------------------------------------------------------------------------------------

def test_monthly_marketview_samples_scenarios_and_d_n_are_in_the_copyable_text():
    jr = base_journal()
    recs = [{"kind": "view_sample", "record": {"sample_time": "2025-09-30T23:00:00Z", "view": "UP",
                                               "outcome_1h": "UP", "outcome_4h": None}}]
    md = md_of(rp.periods(engine=ENG, journal=jr, records=recs, base=BASE, status="running"))
    assert "- 2025-09 MarketView: covered 43200/43200 min · assessable 43200 · unavailable 0 · rows " \
           "NO_QUALIFIED_STRUCTURE 43200" in md
    assert "- 2025-09 samples: 1 (UP 1) · 1h directional 1/1 matching sign, endpoint unavailable 0 · 4h directional " \
           "0/0 matching sign, endpoint unavailable 1" in md
    assert "- 2025-09 scenarios: A_CONFIRM 1 · A confirmations 1 · D 1 / N 1" in md
    assert "- 2025-10 scenarios: none · A confirmations 0 · D 0 / N 0" in md


# 6 -------------------------------------------------------------------------------------------------------------------

def test_compatibility_earlier_keys_kept_and_no_evaluator_pin_is_unknown_not_complete():
    recs = [path("call-1", "PRIMARY", "CLOSED", "0.0025", "2025-10-01T01:00:00Z")]
    pr = rp.periods(engine=ENG, journal=base_journal(), records=recs, base=BASE)  # earlier call shape (no status)
    h = pr["total"]["hypothetical"]["PRIMARY"]
    assert {"paths", "status", "exit_class", "closed_with_price_net", "exits_after_period_end",
            "sum_price_net_normalized", "sum_price_net_pct_presentation", "censored_or_unresolved"} <= set(h)
    assert pr["outcome_completeness"]["run_status"] == "UNKNOWN"
    assert pr["outcome_completeness"]["state"] == "OUTCOMES_NOT_YET_RECORDED_AT_CHECKPOINT"
    no_pin = {"adviser": {k: v for k, v in ENG["adviser"].items() if k != "evaluator"}}
    pr2 = rp.periods(engine=no_pin, journal=base_journal(), records=recs, base=BASE, status="completed")
    assert pr2["outcome_completeness"]["state"] == "UNKNOWN_EVALUATOR_NOT_PINNED"
    assert "UNKNOWN (no evaluator pinned)" in md_of(pr2)
