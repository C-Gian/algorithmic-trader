"""WP-013 durable integration (DB): a receipt-pinned pack for a preset with a registered EXPLICIT initialization, one
continuous v0.4 adviser evaluation across a calendar-month boundary (call issued 31 Aug 23:32, resolved 1 Sep 00:08)
through the observation worker, crash/restore inside the open call, and the report sections (context attestation,
launch pins, total + monthly sections) through the API, Copy report Markdown and exports. A fine-warmup run keeps its
earlier report and engine shape. Tiny synthetic engineering inputs only (no market evidence, no economic evaluation)."""

from __future__ import annotations

import json
from datetime import timedelta

import adviser3_fixtures as f3
import adviser4_fixtures as fx
import pytest
from adviser_db import fake_from, journal, prepare_pack, presets_doc, records, replay, run_all, worker
from fastapi.testclient import TestClient
from pack_fixtures import connect

from algotrader.adviser.harness import run_pure
from algotrader.api import create_app
from algotrader.corpus import presets as ps
from algotrader.observe import control
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import SimulatedCrash

pytestmark = pytest.mark.db

ST = f3.DAY1 - timedelta(minutes=270)  # initialization start (30 Aug 19:30)
ES, EE = ST + timedelta(hours=24), ST + timedelta(hours=30)  # evaluation 31 Aug 19:30 -> 1 Sep 01:30
N = 30 * 60 + 365
_M = f3.a3_return_long()
MINS = (_M + fx.flat(max(0, N - len(_M)), _M[-1].c))[:N]
EV_PER_MIN = 3


def _cursor_at(t):
    return EV_PER_MIN * int((t - ST).total_seconds() // 60)


def _explicit_presets(tmp_path, monkeypatch):
    doc = presets_doc(ev_start=ES, ev_end=EE)
    doc["fine_warmup_hours"] = 12  # the explicit initialization (24 h) is longer than the file's fine warmup
    p = doc["presets"][0]
    p.update({"preset_id": "continuous-fixture-v1", "label": "Continuous fixture",
              "warmup": {"start": ST.isoformat().replace("+00:00", "Z"), "end": ES.isoformat().replace("+00:00", "Z")},
              "initialization": ps.INITIALIZATION_EXPLICIT})
    path = tmp_path / "presets.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PRESETS", str(path))


def _prepared(database_url, tmp_path, monkeypatch):
    _explicit_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    return root, art, prepare_pack(database_url, root, fake_from(MINS, start=ST))


def _launch(database_url, root, pack):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], 0, False,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation",
                                     adviser_method="v0.4")


def _strip(x):
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k not in ("env", "cursor", "anchor_published_cursor",
                                                                "destination_monitoring_cursor", "published_cursor")}
    return [_strip(v) for v in x] if isinstance(x, list) else x


def _signature(database_url, rid):
    with connect(database_url) as c:
        fin = c.execute("SELECT commitment FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
    return ([e["digest"] for e in journal(database_url, rid)], [r["digest"] for r in records(database_url, rid)],
            dict((fin or {}).get("commitment", {})))


def test_continuous_explicit_initialization_run_is_one_run_equal_to_the_pure_fold(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed" and row["assurance"]["state"] == "passed", row["error"]
    adv = row["engine"]["adviser"]
    assert adv["warmup_start"].startswith("2025-08-30T19:30") and adv["eval_start"].startswith("2025-08-31T19:30")
    init = adv["initialization"]
    assert init["policy"] == ps.INITIALIZATION_EXPLICIT and init["hours"] == 24 and init["evaluated"] is False
    assert [c["window"] for c in init["coverage"]] == ["warmup"] * len(init["coverage"]) and init["coverage"]
    pure = run_pure(ST, MINS, eval_start=ES, eval_end=EE, method="v0.4")
    dj = journal(database_url, rid)
    assert [(e["kind"], _strip(e["record"])) for e in dj] == [(e["kind"], _strip(e["record"])) for e in pure.journal]
    assert [r["record"] for r in records(database_url, rid) if r["kind"] == "path"] == pure.paths()
    calls = [e["record"] for e in dj if e["kind"] == "call"]
    assert [c["issued_at"] for c in calls] == ["2025-08-31T23:32:00Z"]
    # exactly one evaluation-start transition (at the evaluation start); nothing restarts at the month boundary
    with connect(database_url) as c:
        av = c.execute("SELECT adviser_view FROM observation_checkpoints WHERE replay_id = %s", (rid,)).fetchone()
    b = (av["adviser_view"] or {}).get("boundary") or {}
    assert b.get("evaluation_start", {}).get("at", "").startswith("2025-08-31T19:30")
    assert not [e for e in dj if "EVALUATION_START" in json.dumps(e["record"])
                and not e["record"]["env"]["clock_time"].startswith("2025-08-31T19:30")]


def test_crash_and_restore_inside_the_open_call_across_the_month_boundary(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    rid = _launch(database_url, root, pack)
    at = _cursor_at(f3.DAY2 + timedelta(minutes=1))  # 1 Sep 00:01: the August call is still open
    fired = {"done": False}

    def hook(replay_id, cursor):
        if replay_id == rid and cursor >= at and not fired["done"]:
            fired["done"] = True
            raise SimulatedCrash()
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:b", checkpoint_events=7, after_commit=hook))
    with connect(database_url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))
    run_all(worker(database_url, root, art, "observe:c", checkpoint_events=7))
    r = replay(database_url, rid)
    assert r["status"] == "completed" and r["assurance"]["state"] == "passed", r["error"]
    assert not [e for e in r["diagnostic_log"] if e["event"] in ("restore_point_rejected", "restore_fallback")]
    assert _signature(database_url, rid) == want


def test_report_attests_context_pins_the_launch_and_reconciles_monthly_sections(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    presets = api.get("/api/corpus/presets").json()
    pv = presets["presets"][0]
    assert pv["preset"]["initialization"] == ps.INITIALIZATION_EXPLICIT and pv["windows"]["initialization"]["hours"] == 24
    r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                           "method": "v0.4", "acknowledge_limitations": True})
    assert r.status_code == 201, r.text
    eid = r.json()["evaluation_id"]
    run_all(worker(database_url, root, art, "observe:r", checkpoint_events=2000))
    rep = api.get(f"/api/evaluations/{eid}/report.json").json()
    a = rep["adviser"]
    assert a["report_version"] == "adviser.report.v4"
    ic = a["initial_context"]
    assert ic["initialization"]["hours"] == 24 and ic["initialization"]["evaluated"] is False
    assert ic["readiness"]["at_evaluation_start"]["trade.1h"] == "READY"
    assert ic["landmarks"]["PIVOTS_1H"]["memory_completeness"] == "NOT_CERTIFIED"
    assert ic["required_periods"]["previous_month"]["data"] == "INSUFFICIENT_BEFORE_INITIALIZATION"
    assert ic["landmarks"]["PREV_1MO_HIGH"]["state"] == "NOT_BUILT_DATA_INSUFFICIENT"
    lp = a["launch_pins"]
    assert lp["method"] == "v0.4" and lp["primary_is_60s"] and lp["pack_id"] == pack["pack_id"]
    pr = a["periods"]
    assert list(pr["months"]) == ["2025-08", "2025-09"] and pr["reconciliation"]["all_passed"], pr["reconciliation"]
    aug, sep = pr["months"]["2025-08"], pr["months"]["2025-09"]
    assert aug["calls"]["issued"] == 1 and sep["calls"]["issued"] == 0
    assert aug["calls"]["resolved_after_period_end"] == 1 and aug["calls"]["guidance_outcome"] == {"TARGET_REACHED": 1}
    assert aug["hypothetical"]["PRIMARY"]["exits_after_period_end"] == 1
    assert pr["total"]["calls"]["issued"] == a["funnel"]["issued"] == 1
    assert aug["coverage"]["minutes"] + sep["coverage"]["minutes"] == 6 * 60
    assert rep["pack"]["windows"]["initialization"]["hours"] == 24
    md = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "Context at the evaluation start (initialization is not evaluated)" in md
    assert "Continuous run: total and monthly sections" in md and "| 2025-08 |" in md and "| 2025-09 |" in md
    assert "Reconciliation total vs months: PASS" in md and "PRIMARY entry delay 60 s" in md
    assert "context only, not evaluated" in md and "not an account return" in md
    dl = api.get(f"/api/evaluations/{eid}/report.json", params={"download": "true"})
    assert dl.status_code == 200 and dl.json()["adviser"]["periods"]["reconciliation"]["all_passed"]
    # correction F1/F2: per-variant populations and states, monthly summaries and outcome completeness, consistent
    # across JSON, Markdown (= Copy report for chat) and the export
    oc = pr["outcome_completeness"]
    assert oc["state"] == "COMPLETE" and oc["run_status"] == "completed" and oc["expected_pairs"] == 4
    assert oc["configured_variants"] == ["PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY"]
    assert dl.json()["adviser"]["periods"]["outcome_completeness"] == oc
    assert "| TOTAL | HORIZON_ONLY | 1 | 1 | 0 |" in md and "Outcome completeness: COMPLETE — 4/4" in md
    assert "- 2025-08 MarketView: covered" in md and "- 2025-09 samples:" in md and "- 2025-08 scenarios:" in md
    # a completed run whose expected terminal record is missing: the REPORT is incomplete, the run is unchanged
    rid = r.json()["replay"]["replay_id"]
    before = replay(database_url, rid)
    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_evaluation_records WHERE run_id = %s AND kind = 'path' "
                  "AND record->>'variant' = 'HORIZON_ONLY'", (rid,))
    a2 = api.get(f"/api/evaluations/{eid}/report.json").json()["adviser"]
    oc2 = a2["periods"]["outcome_completeness"]
    assert oc2["state"] == "REPORT_INCOMPLETE_EXPECTED_TERMINAL_RECORD_MISSING" and oc2["awaiting_terminal_record"] == 1
    assert oc2["by_variant"]["HORIZON_ONLY"]["awaiting_by_issue_month"] == {"2025-08": 1, "2025-09": 0}
    assert a2["periods"]["reconciliation"]["all_passed"]  # the available records still reconcile arithmetically
    md2 = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "**REPORT INCOMPLETE**" in md2 and "HORIZON_ONLY 1 (2025-08 1)" in md2
    # F2-R1: an extraneous path record (unknown call) fails reconciliation, is visible and never enters the sums
    with connect(database_url) as c:
        row = c.execute("SELECT * FROM adviser_evaluation_records WHERE run_id = %s AND kind = 'path' ORDER BY seq "
                        "LIMIT 1", (rid,)).fetchone()
        alien = {**row["record"], "call_id": "alien"}
        cols = [k for k in row if k not in ("seq", "record")]
        c.execute(f"INSERT INTO adviser_evaluation_records (seq, record, {', '.join(cols)}) VALUES "
                  f"(%s, %s, {', '.join(['%s'] * len(cols))})",
                  [10**9, json.dumps(alien)] + [row[k] for k in cols])
    a3 = api.get(f"/api/evaluations/{eid}/report.json").json()["adviser"]["periods"]
    assert a3["path_records"]["extraneous"]["UNKNOWN_CALL"] == 1 and not a3["reconciliation"]["all_passed"]
    assert a3["total"]["hypothetical"] == a2["periods"]["total"]["hypothetical"]
    md3 = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "1 extraneous (unknown call 1)" in md3 and "Reconciliation total vs months: FAIL" in md3
    after = replay(database_url, rid)
    assert (after["status"], after["assurance"]) == (before["status"], before["assurance"]) and \
        after["status"] == "completed"


def test_a_fine_warmup_run_keeps_its_engine_document_and_report_shape(database_url, tmp_path, monkeypatch):
    from adviser_db import EV_END, EV_START, write_presets
    from adviser3_fixtures import DAY1

    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    n = int((EV_END - DAY1).total_seconds() // 60) + 365
    m = fx.contact_then_rearm()
    pack = prepare_pack(database_url, root, fake_from((m + fx.flat(max(0, n - len(m)), m[-1].c))[:n]))
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                           "method": "v0.4", "acknowledge_limitations": True})
    eid, rid = r.json()["evaluation_id"], r.json()["replay"]["replay_id"]
    run_all(worker(database_url, root, art, "observe:f", checkpoint_events=2000))
    assert "initialization" not in replay(database_url, rid)["engine"]["adviser"]
    rep = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert not {"initial_context", "periods", "launch_pins"} & set(rep["adviser"])
    assert "initialization" not in rep["pack"]["windows"] and EV_START.month == EV_END.month
    md = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "Warmup" in md and "Continuous run" not in md and "Initialization" not in md
