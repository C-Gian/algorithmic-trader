"""WP-014 (pure): MP-004 §7 response accounting from committed entry-attempt records - counts and identities on the
real §6 fixture journals, month boundaries of a continuous run, partial reports, warmup clearings, undefined ratios,
the deterministic not-issuable reason, the Markdown carried by Copy report for chat, and the v0.4/v0.5 comparison
summary. Synthetic engineering inputs only - no market data, no economic evaluation."""

from __future__ import annotations

import adviser5_fixtures as fx
import pytest
from adviser3_fixtures import Stepper

from algotrader.adviser import compare as cmp
from algotrader.adviser import report5 as r5
from algotrader.adviser.harness import run_pure

T = fx.T
ENG_DAY = {"adviser": {"eval_start": fx.DAY2.isoformat(), "eval_end": (fx.DAY2.replace(day=2)).isoformat()}}
ZERO = dict.fromkeys(r5.KEYS, 0)


def acc(journal, status="completed", eng=ENG_DAY):
    return r5.response_accounting(engine=eng, journal=journal, status=status)


def counts(**kw):
    return {**ZERO, **kw}


# ---------------------------------------------------------------------------------------------------------------------
# the §6 fixture journals
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected,extra", [
    ("valid", counts(W=1, P=1, R=1, I=1), {}),
    ("equality", counts(W=1, P=1, R=1, I=1), {}),
    ("intermediate_violation_then_valid", counts(W=1, P=1, C=1), {}),
    ("violation_and_recovery_same_bar", counts(W=1, P=1, C=1), {}),
    ("economics_insufficient", counts(W=1, P=1, R=1, N=1), {"primary": {"REWARD_RISK_BELOW_MINIMUM": 1}}),
    ("outside_corridor", counts(W=1, P=1, R=1, N=1), {"primary": {"CLOSE_OUTSIDE_RETURN_CORRIDOR": 1}}),
    ("favourable_equality_only", counts(W=1, P=1, X=1), {"x": {"ORIGINAL_SETUP_DEADLINE": 1}}),
    ("deadline_at_recovery", counts(W=1, P=1, X=1), {"x": {"ORIGINAL_SETUP_DEADLINE": 1}, "annot": {"RECOVERY": 1}}),
    ("v_and_recovery_same_bar", counts(W=1, P=1, X=1), {"x": {"SCENARIO_TERMINAL:INVALIDATED:V_CONTACT": 1},
                                                         "annot": {"CONTRADICTION": 1}}),
    ("gap_before_valid", counts(W=1, P=1, X=1), {"x": {"SCENARIO_TERMINAL:UNASSESSABLE:REQUIRED_MONITORING_GAP": 1}}),
    ("new_cap_before_recovery", counts(W=1, P=1, R=1, N=1), {"primary": {"REWARD_RISK_BELOW_MINIMUM": 1}}),
    ("cap_contact_in_activation_bar", counts(W=1, P=1, X=1), {"x": {"CAP_ACTIVATION_CONTACT_AMBIGUOUS": 1}}),
])
@pytest.mark.parametrize("side", ["L", "S"])
def test_fixture_journals_reconcile_to_the_registered_identities(name, expected, extra, side):
    ms = getattr(fx, name)()
    res = run_pure(fx.DAY1, ms if side == "L" else fx.mirror(ms), eval_start=fx.DAY2, method="v0.5")
    t = acc(res.journal)["total"]
    assert t["counts"] == expected and t["identities_hold"], t["identities"]
    assert t["by_direction"]["LONG" if side == "L" else "SHORT"] == expected
    if "primary" in extra:
        assert t["not_issuable"]["primary_reason"] == extra["primary"]
        assert t["not_issuable"]["primary_class"] == {"ECONOMICS_GEOMETRY": 1}
    if "x" in extra:
        assert t["other_endings_by_priority_cause"] == extra["x"]
    if "annot" in extra:
        assert t["local_conditions_annotated_in_priority_dispatches"] == extra["annot"]


def test_late_first_recovery_and_dispatch_precedence_are_counted_once():
    late = Stepper(fx.two_valid(), events=fx.delayed_events(fx.two_valid(), {fx.index_of(T(4, 2)): 60}),
                   method="v0.5")
    late.finish()
    t = acc(late.journal)["total"]
    assert t["counts"] == counts(W=1, P=1, R=1, N=1) and t["not_issuable"]["late_first_recovery"] == 1
    assert t["not_issuable"]["primary_class"] == {"LATE_OBSERVATION": 1}
    prec = Stepper(fx.recovery_then_violation(),
                   events=fx.delayed_events(fx.recovery_then_violation(), {fx.index_of(T(4, 2)): 60}), method="v0.5")
    prec.finish()
    assert acc(prec.journal)["total"]["counts"] == counts(W=1, P=1, C=1)  # never R and C for one child
    amb = Stepper(fx.tape(fx.VIOLATE, fx.VALID), events=fx.delayed_events(fx.tape(fx.VIOLATE, fx.VALID),
                                                                          {fx.index_of(T(4, 1)): 30}), method="v0.5")
    amb.finish()
    t = acc(amb.journal)["total"]
    assert t["counts"] == counts(W=1, P=1, X=1)  # ambiguity is never counted as a proven contradiction
    assert t["other_endings_by_priority_cause"] == {"LOCAL_CONTACT_TIME_AMBIGUOUS": 1}


def test_blocked_return_is_still_waiting_and_warmup_clearings_stay_apart():
    st = Stepper(fx.favourable_equality_only(), method="v0.5")
    st.run_until(T(4, 1, ))  # WAIT opened, nothing prepared yet
    t = acc(st.journal, status="running")["total"]
    assert t["counts"] == counts(W=1) and t["wait_return_open"] == 1 and t["identities_hold"]
    st.run_until(T(4, 20))
    t = acc(st.journal, status="running")["total"]
    assert t["counts"] == counts(W=1, P=1, A=1) and t["identities_hold"]  # waiting for the response at the cutoff
    warm = run_pure(fx.DAY1, fx.valid(), eval_start=T(4, 3), method="v0.5")
    eng = {"adviser": {"eval_start": T(4, 3).isoformat(), "eval_end": fx.DAY2.replace(day=2).isoformat()}}
    a = acc(warm.journal, eng=eng)
    assert a["total"]["counts"] == ZERO and a["warmup"]["children"] == 1
    assert a["warmup"]["cleared_at_evaluation_start"] == {"WAIT_RESPONSE": 1}


# ---------------------------------------------------------------------------------------------------------------------
# months of a continuous run, partial reports, ratios
# ---------------------------------------------------------------------------------------------------------------------

def ent(at, transition, eid, *, state=None, reason=None, response=None, direction="LONG", blockers=()):
    st = state or {"WAIT_OPEN": "WAIT_PRICE", "RESPONSE_REFERENCE": "WAIT_RESPONSE", "ISSUE": "ISSUED",
                   "CLEARED": "CLEARED"}.get(transition, "TERMINAL")
    rec = {"env": {"published_at": at, "clock_time": at}, "entry_attempt_id": eid, "family": "A",
           "direction": direction, "state": st, "transition": transition, "reason": reason, "mode": "RETURN",
           "blockers": list(blockers), "call_id": "c" if transition == "ISSUE" else None, "response": response}
    return {"kind": "entry_attempt", "clock_time": at, "record": rec}


def prepared(at):
    return {"phase": "WAIT_RESPONSE", "published_at": at, "outcome": None}


def continuous_journal():
    j = [
        # warmup child cleared at the evaluation start (never an evaluation reference)
        ent("2025-08-31T23:00:00+00:00", "WAIT_OPEN", "AL-w#entry"),
        ent("2025-08-31T23:01:00+00:00", "RESPONSE_REFERENCE", "AL-w#entry", response=prepared("x")),
        ent("2025-09-01T00:00:00+00:00", "CLEARED", "AL-w#entry", reason="EVALUATION_START_CLEARS_PENDING_ENTRY",
            response={"outcome": "CLEARED"}),
        # September: opened 30 Sep 23:58, prepared 23:59, issued 1 Oct 00:01 -> September (followed past the month end)
        ent("2025-09-30T23:58:00+00:00", "WAIT_OPEN", "AL-1#entry"),
        ent("2025-09-30T23:59:00+00:00", "RESPONSE_REFERENCE", "AL-1#entry", response=prepared("a")),
        ent("2025-10-01T00:01:00+00:00", "ISSUE", "AL-1#entry", reason="call-1", response={"outcome": "ISSUED"}),
        # September SHORT: contradicted
        ent("2025-09-10T10:00:00+00:00", "WAIT_OPEN", "AS-2#entry", direction="SHORT"),
        ent("2025-09-10T10:01:00+00:00", "RESPONSE_REFERENCE", "AS-2#entry", direction="SHORT", response=prepared("b")),
        ent("2025-09-10T10:05:00+00:00", "TERMINAL", "AS-2#entry", direction="SHORT",
            reason="LOCAL_RESPONSE_CONTRADICTED:bar", response={"outcome": "CONTRADICTED"}),
        # October: ended before a reference; a not-issuable selection rejection; a still-waiting response at the cutoff
        ent("2025-10-02T10:00:00+00:00", "WAIT_OPEN", "AL-3#entry"),
        ent("2025-10-02T11:00:00+00:00", "TERMINAL", "AL-3#entry", reason="ORIGINAL_SETUP_DEADLINE"),
        ent("2025-10-03T10:00:00+00:00", "WAIT_OPEN", "AL-4#entry"),
        ent("2025-10-03T10:01:00+00:00", "RESPONSE_REFERENCE", "AL-4#entry", response=prepared("c")),
        ent("2025-10-03T10:02:00+00:00", "REJECT", "AL-4#entry", reason="RESPONSE_NOT_ISSUABLE:SLOT_OCCUPIED",
            blockers=("SLOT_OCCUPIED",), response={"outcome": "NOT_ISSUABLE", "primary_reason": "SLOT_OCCUPIED",
                                                   "primary_class": "SELECTION"}),
        ent("2025-10-06T10:00:00+00:00", "WAIT_OPEN", "AL-5#entry"),
        ent("2025-10-06T10:01:00+00:00", "RESPONSE_REFERENCE", "AL-5#entry", response=prepared("d")),
    ]
    return sorted(j, key=lambda e: e["clock_time"])


ENG2 = {"adviser": {"eval_start": "2025-09-01T00:00:00+00:00", "eval_end": "2025-10-07T00:00:00+00:00"}}


def test_months_attribute_children_to_the_month_their_wait_opened_and_reconcile():
    a = acc(continuous_journal(), status="running", eng=ENG2)
    sep, octo, tot = a["months"]["2025-09"], a["months"]["2025-10"], a["total"]
    assert sep["counts"] == counts(W=2, P=2, C=1, R=1, I=1)  # the 1 Oct issue stays with its September child
    assert octo["counts"] == counts(W=3, P=2, R=1, N=1, A=1) and octo["ended_before_reference"] == \
        {"ORIGINAL_SETUP_DEADLINE": 1}
    assert tot["counts"] == counts(W=5, P=4, C=1, R=2, N=1, I=1, A=1) and a["months_reconcile"] == {
        "months_sum_to_total": True, "every_month_identities_hold": True}
    assert tot["by_direction"]["SHORT"] == counts(W=1, P=1, C=1)
    assert tot["not_issuable"]["primary_class"] == {"SELECTION": 1}
    assert a["warmup"]["cleared_at_evaluation_start"] == {"WAIT_RESPONSE": 1}


def test_partial_report_counts_the_open_wait_as_a_and_never_infers_an_outcome():
    j = continuous_journal()
    j.append(ent("2025-10-06T10:01:00+00:00", "RESPONSE_REFERENCE", "AL-6#entry", response=prepared("e")))  # no WAIT
    a = acc(j, status="running", eng=ENG2)
    assert a["total"]["counts"]["A"] == 1 and a["total"]["counts"]["P"] == 4  # a record without its WAIT is ignored
    j2 = continuous_journal() + [ent("2025-10-06T11:00:00+00:00", "WAIT_OPEN", "AL-7#entry")]
    a2 = acc(j2, status="running", eng=ENG2)
    t = a2["total"]
    assert t["wait_return_open"] == 1 and t["identities_hold"]
    assert "not complete" in a2["cutoff_meaning"] and a2["cutoff"] == "2025-10-06T11:00:00+00:00"
    # after the child's ending nothing more is read for it (no double terminal)
    j3 = continuous_journal() + [ent("2025-10-06T12:00:00+00:00", "TERMINAL", "AL-1#entry", reason="LATE")]
    assert acc(j3, eng=ENG2)["total"]["counts"] == acc(continuous_journal(), eng=ENG2)["total"]["counts"]


def test_ratios_are_undefined_on_zero_denominators_and_exact_otherwise():
    a = acc([], eng=ENG2)
    assert all(v is None for v in a["total"]["ratios"].values()) and a["total"]["identities_hold"]
    t = acc(continuous_journal(), eng=ENG2)["total"]
    assert t["ratios"] == {"P/W": "0.8000", "C/P": "0.2500", "R/P": "0.5000", "N/R": "0.5000", "I/R": "0.5000",
                           "I/P": "0.2500"}


def test_identity_failure_is_visible():
    bad = r5.tally([{"class": "I", "detail": {}, "reference": None, "direction": "LONG"}])  # issue without reference
    assert not bad["identities_hold"]
    assert bad["counts"]["I"] == 1 and bad["counts"]["P"] == 0 and not bad["identities"]["P_eq_C_plus_R_plus_X_plus_A"]


def test_markdown_for_copy_report_carries_total_months_and_identities():
    a = acc(continuous_journal(), status="running", eng=ENG2)
    md = "\n".join(r5.response_markdown(a))
    assert "### A RETURN response (MP-004 §7; unit = A RETURN child)" in md
    assert "| Total | 5 | 4 | 1 | 2 | 1 | 1 | 0 | 1 | 0.8000 |" in md
    assert "| 2025-09 | 2 | 2 | 1 | 1 | 0 | 1 | 0 | 0 |" in md and "| 2025-10 |" in md
    assert "sum to total yes" in md and "Warmup (not evaluated): 1 child(ren)" in md
    assert "a zero denominator is undefined" in md and "C/P does not measure real deterioration" in md
    empty = "\n".join(r5.response_markdown(acc([], eng=ENG2)))
    assert "| Total | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | undef. |" in empty


# ---------------------------------------------------------------------------------------------------------------------
# read-only comparison summary (v0.4 baseline vs v0.5 candidate)
# ---------------------------------------------------------------------------------------------------------------------

def _facts(method, adviser):
    return {"evaluation_id": f"ev-{method}", "replay_id": "r", "status": "completed", "method": method,
            "model": f"btc.context-action.{method}", "rules_version": "x", "rules_sha256": method,
            "register_sha256": "g", "implementation": "i", "identity_sha256": method, "capability_profile_sha256": "p",
            "pins": {k: "same" for k in cmp.PIN_FIELDS}, "pack_manifest_sha256": "m", "evaluator_terms": {},
            "evaluator_sha256": "e", "assurance": "PASSED", "validation_outcome": "passed", "adviser": adviser}


def test_comparison_names_the_mp004_delta_and_carries_the_response_counts():
    base = {"report_version": "adviser.report.v4", "calls": {"count": 13}, "outcomes": {"variants": {"PRIMARY": {}}},
            "funnel": {"evidence_threshold": {"status": "INSUFFICIENT_EVIDENCE"}}, "anchors": {"owners": {}}}
    acc5 = acc(continuous_journal(), eng=ENG2)
    cand = {**base, "report_version": "adviser.report.v5", "calls": {"count": 9}, "responses": acc5}
    c = cmp.build(_facts("v0.4", base), _facts("v0.5", cand))
    assert c["comparability"]["verdict"] == "COMPARABLE" and c["deltas_b_minus_a"]["calls"] == "-4"
    assert [x["id"] for x in c["limitations"]] == ["V05_MP004_RETURN_RESPONSE_DELTA"]
    assert c["b"]["responses"]["total"] == acc5["total"]["counts"] and c["a"].get("responses") is None
    assert c["b"]["anchors"] == {"owners": {}} and c["a"]["anchors"] == {"owners": {}}
    md = cmp.render_markdown(c)
    assert "baseline v0.4 (A) vs candidate v0.5 (B)" in md and "A RETURN response (MP-004 §7): W 5 · P 4" in md
    assert "  - 2025-09: W 2 · P 2" in md and "fewer stops are not improvement by themselves" in md
    # a v0.3/v0.5 pair names both deltas
    c3 = cmp.build(_facts("v0.3", base), _facts("v0.5", cand))
    assert [x["id"] for x in c3["limitations"]] == ["V04_MP003_PRECONFIRMATION_ANCHOR_DELTA",
                                                     "V05_MP004_RETURN_RESPONSE_DELTA"]


def test_release_pins_tell_whether_a_baseline_is_the_current_packaged_release():
    from algotrader.adviser import methods

    v4 = methods.get("v0.4")
    real = {**_facts("v0.4", {}), "model": v4.model, "rules_version": v4.rules_version,
            "rules_sha256": v4.rules_sha256(), "register_sha256": v4.register_sha256(),
            "implementation": v4.implementation}
    assert cmp.release_pin(real) == {"state": "MATCHES_CURRENT_PACKAGE", "differs": []}
    stale = {**real, "register_sha256": "0" * 64}
    assert cmp.release_pin(stale) == {"state": "DIFFERS_FROM_CURRENT_PACKAGE", "differs": ["register_sha256"]}
    c = cmp.build(stale, _facts("v0.5", {}))
    assert c["comparability"]["release_pins"]["a"]["state"] == "DIFFERS_FROM_CURRENT_PACKAGE"
    assert "Pinned release vs current package: A DIFFERS_FROM_CURRENT_PACKAGE (register_sha256)" in \
        cmp.render_markdown(c)
