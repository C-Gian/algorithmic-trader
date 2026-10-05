"""WP-009 causality, window boundaries and typed events (pure): a future perturbation never changes earlier outputs;
warmup calls are cleared and never scored; no new call after the evaluation end; strict as-known calendar admits only
schedules known in time, restricts new entry around the release and records an observed price response."""

from __future__ import annotations

from datetime import timedelta

from adviser_fixtures import DAY1, DAY2, a_fixture
from adviser_rig import Rig, rec

from algotrader.adviser.core import EventInput
from algotrader.adviser.harness import run_pure
from algotrader.adviser.identity import Calendar, CapabilityProfile, Dislocation, Execution, FundingOutcomes, IncidentTape


def test_future_perturbation_never_changes_earlier_outputs():
    base = run_pure(DAY1, a_fixture(), eval_start=DAY2)
    alt = run_pure(DAY1, a_fixture(after_issue="stop"), eval_start=DAY2)  # identical up to the 05:21 issue
    cut = "2025-09-01T05:22:00Z"
    a = [e["digest"] for e in base.journal if e["clock_time"] < cut]
    b = [e["digest"] for e in alt.journal if e["clock_time"] < cut]
    assert a and a == b
    assert base.calls()[0]["call_id"] == alt.calls()[0]["call_id"]


def test_envelopes_disclose_unknown_calendar_and_modeled_execution():
    res = run_pure(DAY1, a_fixture(), eval_start=DAY2)
    lim = res.calls()[0]["env"]["limitations"]
    assert "CALENDAR_COVERAGE_UNKNOWN" in lim and "FUNDING_COMPLETENESS_UNPROVEN" in lim
    assert "HISTORICAL_MODELED_EXECUTION_NOT_MEASURED_QUOTES" in lim


def test_warmup_call_is_cleared_at_evaluation_start_and_never_scored():
    res = run_pure(DAY1, a_fixture(), eval_start=DAY2 + timedelta(hours=5, minutes=30))
    [call] = res.calls()  # issued 05:21, inside the warmup
    last = res.revisions(call["call_id"])[-1]
    assert last["thesis_status"] == "UNASSESSABLE" and last["terminal_reason"] == "EVALUATION_START_CLEARS_WARMUP_CALL"
    assert res.paths() == []
    assert res.runtime.core.boundary["evaluation_start"]["warmup_calls"] == 1


def test_no_new_call_after_the_evaluation_end_tail_only_monitors():
    res = run_pure(DAY1, a_fixture(), eval_start=DAY2, eval_end=DAY2 + timedelta(hours=5, minutes=20))
    assert res.calls() == []
    rej = [c for c in res.candidates("A") if c["transition"] == "REJECT"]
    assert rej and "EVALUATION_WINDOW_ENDED" in rej[0]["reason"]


def _calendar_rig():
    prof = CapabilityProfile(execution=Execution.HISTORICAL_BASE, calendar=Calendar.STRICT_AS_KNOWN_ALLOW_UNKNOWN,
                             dislocation=Dislocation.NOT_COVERED, incident_tape=IncidentTape.NOT_COVERED,
                             funding_outcomes=FundingOutcomes.PRICE_NET_ONLY)
    return Rig(profile=prof)


def test_strict_calendar_admits_only_as_known_schedules_and_restricts_entry_around_release():
    rig = _calendar_rig()
    t = rig.t
    ev_time = t + timedelta(minutes=30)
    late = EventInput("cpi-late", 1, "US_CPI", "US", ev_time, ev_time + timedelta(minutes=1), None, "p" * 64)
    rig.core.admit_capability(late)
    rig.minute(100, 100, 100, 100)
    assert "cpi-late" not in rig.core.events and rig.core.counters["events_unknown_vintage"] == 1
    ok = EventInput("cpi", 1, "US_CPI", "US", ev_time, t, None, "p" * 64)
    rig.core.admit_capability(ok)
    rig.minute(100, 100, 100, 100)
    assert rig.core._event_blockers(rig.t) == []  # outside [schedule - 15m, ...)
    for _ in range(15):
        rig.minute(100, 100, 100, 100)
    assert rig.core._event_blockers(rig.t) == ["EVENT_RESTRICTION:cpi"]
    # past schedule + 15m but the first wholly post-event 15m bar is not complete yet: still restricted
    for _ in range(27):  # until 00:44: schedule + 15m passed, post-event bar [00:30, 00:45) not complete yet
        rig.minute(100, 100, 100, 100)
    assert rig.core._event_blockers(rig.t) == ["EVENT_RESTRICTION:cpi"]
    # the first wholly post-event complete 15m bar closes: restriction ends, an observed response is recorded
    rig.core.admit_sealed(rec("15m", ev_time, 100, 101, 99, 101))
    rig.minute(101, 101, 101, 101, at=ev_time + timedelta(minutes=15))
    assert rig.core._event_blockers(rig.t) == []
    resp = rig.kinds("event_response")
    assert resp and resp[0]["label"] == "OBSERVED_PRICE_RESPONSE" and resp[0]["event_id"] == "cpi"
