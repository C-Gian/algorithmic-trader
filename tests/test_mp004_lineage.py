"""WP-014 (pure): the reconciliation v8 A RETURN response lineage (``adviser.reconcile._v5_response_lineage``) and the
inherited v0.4 anchor lineage on v0.5 journals. Every §6 fixture journal passes; each tampering of the stored
entry-attempt records (a second or moved reference, a call without a pre-existing reference, a decision before the
publication or in the same dispatch, a record after the ending, an inconsistent outcome, a RETURN_USABLE record)
fails. Synthetic engineering inputs only."""

from __future__ import annotations

import copy

import adviser5_fixtures as fx
import pytest
from adviser3_fixtures import Stepper

from algotrader.adviser.harness import run_pure
from algotrader.adviser.reconcile import _v3_lineage, _v4_anchor_lineage, _v5_response_lineage

T = fx.T
NAMES = ("valid", "equality", "favourable_equality_only", "intermediate_violation_then_valid",
         "violation_and_recovery_same_bar", "v_and_recovery_same_bar", "economics_insufficient", "outside_corridor",
         "deadline_at_recovery", "gap_before_valid", "blocked_first", "new_cap_before_recovery",
         "cap_contact_in_activation_bar")


def journal(name="valid", side="L"):
    ms = getattr(fx, name)()
    return run_pure(fx.DAY1, ms if side == "L" else fx.mirror(ms), eval_start=fx.DAY2, method="v0.5").journal


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("side", ["L", "S"])
def test_every_fixture_journal_passes_the_response_anchor_and_scenario_lineage(name, side):
    j = journal(name, side)
    calls = {e["record"]["call_id"]: e["record"] for e in j if e["kind"] == "call"}
    assert _v5_response_lineage(j) == [] and _v4_anchor_lineage(j) == [] and _v3_lineage(j, calls) == []


def test_delayed_receipt_journals_pass():
    for ms, delays in ((fx.two_valid(), {T(4, 2): 60}), (fx.recovery_then_violation(), {T(4, 2): 60}),
                       (fx.tape(fx.VIOLATE, fx.VALID), {T(4, 1): 30}), (fx.tape(fx.VALID, fx.VALID),
                                                                         {T(4, 1): 60, T(4, 2): 30})):
        st = Stepper(ms, events=fx.delayed_events(ms, {fx.index_of(t): s for t, s in delays.items()}), method="v0.5")
        st.finish()
        assert _v5_response_lineage(st.journal) == []


def _entries(j):
    return [e for e in j if e["kind"] == "entry_attempt" and e["record"]["scenario_id"][:2] in ("AL", "AS")]


def _tampered(fn, name="valid"):
    j = copy.deepcopy(journal(name))
    fn(j, _entries(j))
    return _v5_response_lineage(j)


def test_tampering_with_the_reference_or_its_decision_fails():
    def second_reference(j, ents):
        dup = copy.deepcopy(ents[1])
        j.insert(j.index(ents[1]) + 1, dup)

    def moved_reference(j, ents):
        ents[2]["record"]["response"]["H0"] = "100009"

    def wrong_publication(j, ents):
        ents[1]["record"]["response"]["published_at"] = "2025-09-01T04:01:00+00:00"

    def issue_without_reference(j, ents):
        j.remove(ents[1])

    def same_dispatch_decision(j, ents):
        ents[2]["record"]["env"]["professional_seq"] = ents[1]["record"]["env"]["professional_seq"]

    def decided_before_publication(j, ents):
        ents[2]["record"]["response"]["response_bar"] = "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04:01:00Z"

    def wrong_outcome(j, ents):
        ents[2]["record"]["response"]["outcome"] = "NOT_ISSUABLE"

    def record_after_ending(j, ents):
        j.append(copy.deepcopy(ents[1]))

    def usable_record(j, ents):
        ents[1]["record"]["transition"] = "RETURN_USABLE"

    expect = {second_reference: "reference not prepared once", moved_reference: "reference changed",
              wrong_publication: "reference publication differs", issue_without_reference: "without a pre-existing",
              same_dispatch_decision: "in a later dispatch", decided_before_publication: "not wholly after",
              wrong_outcome: "inconsistent with ISSUE", record_after_ending: "after its ending",
              usable_record: "RETURN_USABLE record"}
    for fn, text in expect.items():
        problems = _tampered(fn)
        assert problems and any(text in p for p in problems), (fn.__name__, problems)


def test_contradiction_and_not_issuable_outcomes_are_bound_to_their_reasons():
    def flip(j, ents):
        ents[-1]["record"]["response"]["outcome"] = "ISSUED"

    assert any("inconsistent with LOCAL_RESPONSE_CONTRADICTED" in p
               for p in _tampered(flip, "intermediate_violation_then_valid"))
    assert any("inconsistent with RESPONSE_NOT_ISSUABLE" in p for p in _tampered(flip, "economics_insufficient"))

    def no_ref(j, ents):
        j.remove(ents[1])

    assert any("ended RESPONSE_NOT_ISSUABLE without a reference" in p
               for p in _tampered(no_ref, "economics_insufficient"))
