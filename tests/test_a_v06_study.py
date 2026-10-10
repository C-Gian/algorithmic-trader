"""A v0.6 study path (pure, no DB): the registered study window and the study ledger's case separation.

The packaged ``study_presets.json`` must state exactly the windows of the pinned design (A-V06 design §5: evaluation
[2027-01-25T00:00Z, 2027-07-26T00:00Z), 35-day initialization, the registered 365-minute outcome tail) and is the only
preset accepted outside the logical target and off calendar months. Synthetic tapes only; no market data."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import study_fixtures as sf

from algotrader.adviser.harness import run_pure
from algotrader.corpus import presets as ps

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("a_v06_study_ledger", ROOT / "scripts" / "a_v06_study_ledger.py")
lg = importlib.util.module_from_spec(_spec)
sys.modules["a_v06_study_ledger"] = lg
_spec.loader.exec_module(lg)
Z = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731


def _sha_lf(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _real(monkeypatch):
    monkeypatch.delenv("ALGOTRADER_CORPUS_PRESETS", raising=False)
    monkeypatch.delenv("ALGOTRADER_STUDY_PRESETS", raising=False)
    return ps.load_presets(), ps.load_study_presets()


def test_registered_study_preset_states_the_pinned_design_windows(monkeypatch):
    f, sp = _real(monkeypatch)
    assert sp.fixture is False and [s.study_id for s in sp.studies] == ["A-V06-OPERATIONAL-EVALUATION"]
    s = sp.studies[0]
    for src in s.sources:  # the authoritative texts it was taken from are unchanged
        assert _sha_lf(ROOT / src.path) == src.sha256_lf, src.path
    design = (ROOT / "delivery/A-V06-OPERATIONAL-EVALUATION-DESIGN.md").read_text(encoding="utf-8")
    assert "[2027-01-25T00:00Z, 2027-07-26T00:00Z)" in design and "35 giorni precedenti l’inizio" in design
    p = s.preset
    assert (p.evaluation.start, p.evaluation.end) == (Z("2027-01-25T00:00:00Z"), Z("2027-07-26T00:00:00Z"))
    assert p.warmup.end == p.evaluation.start and p.evaluation.start - p.warmup.start == timedelta(days=35)
    reg = json.loads((ROOT / "delivery/MP-005-PARAMETERS.json").read_text(encoding="utf-8"))
    tail = next(v["outcome_tail_minutes"] for v in reg.values() if isinstance(v, dict) and "outcome_tail_minutes" in v)
    assert p.tail.minutes == tail == f.outcome_tail_minutes == 365 and p.tail.start == p.evaluation.end
    assert (s.run_type, s.method, p.initialization) == ("adviser_evaluation", "v0.6", ps.INITIALIZATION_EXPLICIT)
    ps.check_windows(f, p)  # accepted: outside the target [2025-09-01, 2026-09-01) and not on calendar months
    cls = ps.classify(f, p)
    assert cls["label"] == "REGISTERED_STUDY_WINDOW" and cls["portions"] == [] and not cls["certified_uncontaminated"]
    assert ps.resolve(f, p.preset_id) == p


def test_nothing_else_widens_the_date_range(monkeypatch):
    f, sp = _real(monkeypatch)
    p = sp.studies[0].preset
    shifted = p.model_copy(update={"evaluation": ps.Window(start=p.evaluation.start + timedelta(days=1),
                                                           end=p.evaluation.end),
                                   "warmup": ps.Window(start=p.warmup.start, end=p.evaluation.start + timedelta(days=1))})
    for bad in (shifted, p.model_copy(update={"preset_id": "copy-v1"}),
                p.model_copy(update={"evidence_class": "DEVELOPMENT"})):
        with pytest.raises(ps.PresetError):
            ps.check_windows(f, bad)
    with pytest.raises(ps.PresetError):
        ps.months_preset(f, ["2027-02"])  # the month builder stays inside the target
    for q in f.presets:  # earlier presets: unchanged classification shape and labels
        c = ps.classify(f, q)
        assert c["label"] == "DEVELOPMENT" and "study_id" not in c and q.evidence_class == "DEVELOPMENT"


def test_a_registered_study_window_may_not_overlap_development_or_protected(tmp_path, monkeypatch):
    sf.write_files(tmp_path, monkeypatch)  # fixture target/development/protected: 2025-06 .. 2025-08
    f = ps.load_presets()
    ok = ps.load_study_presets().studies[0].preset
    ps.check_windows(f, ok)
    inside = sf.study_preset(ev_start=datetime(2025, 7, 10, 2, tzinfo=UTC), ev_end=datetime(2025, 7, 10, 6, tzinfo=UTC),
                             init_start=datetime(2025, 7, 10, tzinfo=UTC))
    sf.write_files(tmp_path, monkeypatch, preset=inside)
    with pytest.raises(ps.PresetError, match="may not overlap the protected period"):
        ps.check_windows(ps.load_presets(), ps.load_study_presets().studies[0].preset)


# -- ledger case separation over pure folds of the same tape ----------------------------------------------------------

def _inputs(es, ee, n=None):
    r = run_pure(sf.DAY1, sf.tape(n), eval_start=es, eval_end=ee, method="v0.6")
    calls = {}
    for e in r.journal:
        if e["kind"] == "call":
            calls[e["record"]["call_id"]] = {"call": e["record"], "revisions": [], "hypothetical_paths": []}
    for x in r.records:
        if x["kind"] == "path":
            calls[x["record"]["call_id"]]["hypothetical_paths"].append(x["record"])
    jr = lambda k: [{"record": e["record"]} for e in r.journal if e["kind"] == k]  # noqa: E731
    inw = [c for c in calls.values() if es <= Z(c["call"]["issued_at"]) < ee]
    prim = sum(1 for c in inw for p in c["hypothetical_paths"] if p["variant"] == "PRIMARY")
    rep = {"evaluation_id": "eval-x", "replay_id": "obs-x", "status": "completed", "completion": "COMPLETE",
           "adviser": {"windows": {"evaluation": [es.isoformat(), ee.isoformat()], "warmup_start": sf.DAY1.isoformat(),
                                   "tail_end": ee.isoformat(), "clock_end_reached": True},
                       "launch_pins": {"capability_profile": {"funding_outcomes": "PRICE_NET_ONLY"}},
                       "calls": {"count": len(inw), "list": [{"call_id": c["call"]["call_id"]} for c in inw]},
                       "outcomes": {"variants": {"PRIMARY": {"paths": prim}}}}}
    return rep, {"replay_id": "obs-x", "calls": list(calls.values())}, jr("scenario"), jr("entry_attempt")


def _ledger_of(monkeypatch, es, ee, n=None, mutate=None, match=True):
    rep, calls, scen, ents = _inputs(es, ee, n)
    if mutate:
        mutate(rep, calls)
    monkeypatch.setattr(lg, "_check_identities", lambda p: {"all_match": match})
    return lg.build_ledger(rep, calls, scen, ents, mode="SYNTHETIC",
                           run_ids={"report": rep["replay_id"], "calls": calls["replay_id"]})


def test_warmup_confirmation_is_not_recovered(monkeypatch):
    d2 = sf.DAY2  # confirmation 04:01 lies before the start 04:02: the waiting child is cleared, nothing is issued
    led = _ledger_of(monkeypatch, d2 + timedelta(hours=4, minutes=2), d2 + timedelta(hours=6))
    (o,) = led["owners"]
    assert o["class"] == "PRE_EXISTING_AT_START" and o["status_at_start"] == "CONFIRMED" and not o["calls"]
    assert o["confirmations"] == [{"at": "2025-09-01T04:01:00Z", "in_window": False}]
    assert o["not_issued_reason"] and o["not_confirmed_reason"] is None
    assert led["population"]["primary_a_calls"] == 0 and led["calls"] == []


def test_no_issue_after_the_window_end(monkeypatch):
    led = _ledger_of(monkeypatch, sf.EV_START, sf.DAY2 + timedelta(hours=4, minutes=3))  # ends before the 04:03 issue
    (o,) = led["owners"]
    assert o["class"] == "BORN_IN_WINDOW" and o["confirmations"][0]["in_window"] and not o["calls"]
    assert o["not_issued_reason"] and led["population"]["primary_a_calls"] == 0 and led["calls"] == []


def test_an_included_path_without_result_is_never_zero(monkeypatch):
    n = int((sf.DAY2 + timedelta(hours=5) - sf.DAY1) / timedelta(minutes=1))  # data stop before the 06:03 exit
    led = _ledger_of(monkeypatch, sf.EV_START, sf.EV_END, n)
    (c,) = led["calls"]
    assert c["primary"] and c["class"] == "UNDETERMINED" and c["value"] is None and c["primary_status"] != "CLOSED"
    hour = next(h for h in led["hours"] if h["hour"] == "2025-09-01T04:00:00Z")
    assert hour["value"] is None and hour["status"] == "CONTAINS_UNDETERMINED"
    assert led["balance"]["status"] == "INCOMPLETE_UNDETERMINED_PATHS" and led["balance"]["complete_balance"] is None
    sub = led["balance"]["partial_subtotal"]
    assert sub["label"] == "PARTIAL" and sub["value"] == "0" and sub["excluded_undetermined"] == 1
    assert led["balance"]["observed_balance"] is None and Decimal(led["hours"][0]["value"]) == 0
    assert led["bootstrap"]["eligible"] is False


# -- attestation before a complete balance (review of 2018634) ------------------------------------------------------

def _att(led):
    return led["attestation"], led["balance"], led["hours"]


def test_complete_valid_case_keeps_the_previous_results(monkeypatch):
    led = _ledger_of(monkeypatch, sf.EV_START, sf.EV_END)
    att, bal, hours = _att(led)
    assert att["attested"] and bal["status"] == "COMPLETE" and bal["complete_balance"] == "-0.0014"
    assert bal["observed_balance"] == "-0.0014" and bal["partial_subtotal"] is None and led["bootstrap"]["eligible"]
    assert {h["hour"]: h["value"] for h in hours}["2025-09-01T04:00:00Z"] == "-0.0014"
    assert all(h["value"] == "0" for h in hours if h["hour"] != "2025-09-01T04:00:00Z")


@pytest.mark.parametrize("case", ["identity_mismatch", "run_not_completed", "other_run_export", "call_list_incomplete"])
def test_unattested_runs_never_give_a_balance_or_zero_hours(monkeypatch, case):
    mutate, match = None, True
    if case == "identity_mismatch":
        match = False
    elif case == "run_not_completed":
        def mutate(rep, calls):
            rep["status"], rep["completion"] = "paused", "INCOMPLETE"
    elif case == "other_run_export":
        def mutate(rep, calls):
            calls["replay_id"] = "obs-other"
    else:  # the export lost the call that the run's own report lists
        def mutate(rep, calls):
            calls["calls"] = []
    led = _ledger_of(monkeypatch, sf.EV_START, sf.EV_END, mutate=mutate, match=match)
    att, bal, hours = _att(led)
    assert not att["attested"] and bal["status"] == "NOT_ATTESTED_IDENTITY_OR_COMPLETENESS"
    assert bal["complete_balance"] is None and bal["observed_balance"] is None
    assert bal["partial_subtotal"] is None  # no subtotal presented as a reconciled study result
    assert all(h["value"] is None and h["status"] == "NOT_ATTESTED" for h in hours)  # never abstention hours


# -- input provisioning: acquisition plan of the registered study window ----------------------------------------------

def test_study_window_acquisition_plan_and_reuse_of_local_parts(monkeypatch):
    from algotrader.corpus import pack as pk

    f, sp = _real(monkeypatch)
    p = sp.studies[0].preset
    lo, hi = p.warmup.start, p.tail.end
    assert (lo, hi) == (Z("2026-12-21T00:00:00Z"), Z("2027-07-26T06:05:00Z"))  # initialization .. tail end, no margin
    plan = pk.plan_slices([], lo, hi, f.acquisition_max_span_days)
    months = ["2027-01-01", "2027-02-01", "2027-03-01", "2027-04-01", "2027-05-01", "2027-06-01", "2027-07-01"]
    bounds = [lo] + [Z(m + "T00:00:00Z") for m in months] + [hi]
    assert list(plan.acquisitions) == list(zip(bounds, bounds[1:])) and plan.slices == ()
    # a local package already covering part of the range (e.g. the HDP-001 trade parts) is reused, never re-fetched
    hdp = pk.LocalSource("hdp-part", Z("2026-12-01T00:00:00Z"), Z("2027-01-01T00:00:00Z"), False, 1, manifest=None)
    reuse = pk.plan_slices([hdp], lo, hi, f.acquisition_max_span_days)
    assert [(s.dataset_id, s.start, s.end) for s in reuse.slices] == [("hdp-part", lo, Z("2027-01-01T00:00:00Z"))]
    assert reuse.acquisitions[0][0] == Z("2027-01-01T00:00:00Z") and reuse.acquisitions[-1][1] == hi
