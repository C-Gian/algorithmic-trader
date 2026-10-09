"""WP-015 durable integration (DB): MP-005 v0.6 adviser evaluations over a real receipt-pinned pack prepared offline
from the hand fixture ``adviser6_fixtures.h1_economics`` (confirmation 04:01 -> WAIT_RETURN; the usable return
[04:01,04:02) prepares the reference at 04:02 and, in that same dispatch, ends INITIAL_RESPONSE_INCOMPATIBLE:
HISTORICAL_ECONOMICS), through the observation worker (engine observe.stream.v7), next to the unchanged v0.5 path.
Engineering checks only (tiny synthetic inputs; no market evidence, no economic evaluation)."""

from __future__ import annotations

import adviser6_fixtures as fx
import pytest
from adviser_db import EV_END, EV_START, fake_from, journal, records, replay, run_all, worker
from adviser3_fixtures import DAY1
from fastapi.testclient import TestClient
from pack_fixtures import connect
from psycopg.types.json import Jsonb
from test_mp004_db import EV_PER_MIN, _cursor, _expire_lease, _prepared, _signature, _strip, crash_once_after

from algotrader.adviser.core6 import REASON
from algotrader.adviser.harness import run_pure
from algotrader.api import create_app
from algotrader.observe import control, deep
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import SimulatedCrash

pytestmark = pytest.mark.db
N = int((EV_END - DAY1).total_seconds() // 60) + 365
_M = fx.h1_economics()
MINS = (_M + fx.flat(max(0, N - len(_M)), _M[-1].c))[:N]
_ = fake_from


def _launch(database_url, root, pack, method="v0.6", paused=False, speed=0):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], speed, paused,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation",
                                     adviser_method=method)


def _pure(method="v0.6", mins=MINS):
    return run_pure(DAY1, mins, eval_start=EV_START, eval_end=EV_END, method=method)


def _a_entries(dj):
    return [e for e in dj if e["kind"] == "entry_attempt" and e["record"]["scenario_id"].startswith("AL")]


def test_v06_pack_evaluation_equals_the_pure_fold_with_reconciliation_v9(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    rid = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed", row["error"]
    assert row["engine_format"] == "observe.stream.v7" and row["engine"]["adviser"]["method"] == "v0.6"
    assert row["engine"]["adviser"]["format"] == "algotrader.adviser-runtime.v6"
    assert row["engine"]["adviser"]["identity"]["implementation"] == "adviser.core.v6"
    v = row["manifest"]["validation"]
    assert v["validator_version"] == "9" and row["assurance"]["state"] == "passed", \
        [c for c in v["checks"] if not c["passed"]]
    assert "Version 9 (WP-015" in v["scope"] and "Version 8 (WP-014" in v["scope"]
    names = {c["name"]: c["passed"] for c in v["checks"]}
    assert names["adviser_method_binding"] and names["adviser_lineage_immutability"] and names["adviser_finish_rederived"]
    assert row["manifest"]["adviser"]["method"] == "v0.6" and row["manifest"]["schema_revision"] == 9
    pure = _pure()
    dj = journal(database_url, rid)
    assert [(e["kind"], _strip(e["record"])) for e in dj] == [(e["kind"], _strip(e["record"])) for e in pure.journal]
    tr = [(e["record"]["env"]["clock_time"][11:19], e["record"]["transition"], e["record"]["reason"] or "")
          for e in _a_entries(dj) if e["record"]["transition"] != "BLOCKERS"]
    assert [x[:2] for x in tr] == [("04:01:00", "WAIT_OPEN"), ("04:02:00", "RESPONSE_REFERENCE"),
                                   ("04:02:00", "TERMINAL")] and tr[2][2] == f"{REASON}:HISTORICAL_ECONOMICS"
    ref, end = [e for e in _a_entries(dj) if e["record"]["transition"] in ("RESPONSE_REFERENCE", "TERMINAL")]
    assert ref["factual_cursor"] == end["factual_cursor"] and ref["seq"] + 1 == end["seq"]  # same dispatch, in order


@pytest.mark.parametrize("crash_at", [("wait_return", (4, 1)), ("at_preparation_and_terminal", (4, 2)),
                                      ("after_terminal", (4, 3)), ("later", (4, 30)), ("final_commit", None)],
                         ids=lambda x: x[0])
def test_v06_crash_reclaim_around_the_p_to_x_dispatch_gives_identical_outputs(database_url, tmp_path, monkeypatch,
                                                                             crash_at):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    total = replay(database_url, base)["total_events"]
    rid = _launch(database_url, root, pack)
    at = total if crash_at[1] is None else _cursor(*crash_at[1])
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:b", checkpoint_events=7, after_commit=crash_once_after(rid, at)))
    _expire_lease(database_url, rid)
    run_all(worker(database_url, root, art, "observe:c", checkpoint_events=7))
    r = replay(database_url, rid)
    assert r["status"] == "completed" and r["assurance"]["state"] == "passed", r["error"]
    assert not [e for e in r["diagnostic_log"] if e["event"] in ("restore_point_rejected", "restore_fallback")]
    assert _signature(database_url, rid) == want
    ents = [e["record"] for e in _a_entries(journal(database_url, rid))]
    assert [x["transition"] for x in ents].count("RESPONSE_REFERENCE") == 1  # never re-prepared
    assert [str(x["reason"]).startswith(REASON) for x in ents].count(True) == 1  # never repeated or reopened
    assert ents[-1]["reason"].startswith(REASON)  # nothing after the terminal (no later C/R or issue)


def test_v06_step_through_the_p_to_x_dispatch_gives_identical_outputs(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    sid = _launch(database_url, root, pack, speed=400)
    paused = {"done": False}

    def pause_before(replay_id, cursor):
        if replay_id == sid and cursor >= _cursor(3, 58) and not paused["done"]:
            paused["done"] = True
            with connect(database_url) as c:
                control.pause(c, replay_id)
    w = worker(database_url, root, art, "observe:d", checkpoint_events=13, after_commit=pause_before)
    run_all(w)
    assert replay(database_url, sid)["status"] == "paused"
    with connect(database_url) as c:
        for _ in range(EV_PER_MIN * 7):  # 03:58 -> 04:05 one delivery at a time (through the 04:02 P -> X dispatch)
            control.step(c, sid)
            run_all(w)
        control.resume(c, sid)
    run_all(w)
    assert replay(database_url, sid)["status"] == "completed" and _signature(database_url, sid) == want


def test_a_v06_run_never_resumes_under_v05(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    rid = _launch(database_url, root, pack)

    def pause_at(replay_id, cursor):
        if cursor >= _cursor(4, 3):
            with connect(database_url) as c:
                control.pause(c, replay_id)
    run_all(worker(database_url, root, art, "observe:p", checkpoint_events=500, after_commit=pause_at))
    assert replay(database_url, rid)["status"] == "paused"
    before = _signature(database_url, rid)
    with connect(database_url) as c:
        eng = c.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
        eng["adviser"]["method"] = "v0.5"
        c.execute("UPDATE observation_replays SET engine = %s WHERE replay_id = %s", (Jsonb(eng), rid))
        control.resume(c, rid)
    run_all(worker(database_url, root, art, "observe:q", checkpoint_events=500))
    r = replay(database_url, rid)
    assert r["status"] == "failed" and "INCOMPATIBLE_ADVISER_IDENTITY" in (r["error"] or "")
    assert _signature(database_url, rid)[:2] == before[:2]


def test_deep_v10_matches_and_detects_a_tampered_initial_terminal(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 400)
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    rid = _launch(database_url, root, pack)
    w = worker(database_url, root, art, "observe:h", checkpoint_events=700)
    run_all(w)

    def done(vid):
        run_all(w)
        with connect(database_url) as c:
            return c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, rid)
    v = done(vid)
    assert v["status"] == "completed" and v["result"]["outcome"] == "match", v["result"]["mismatches"]
    assert v["result"]["validator_version"] == "10" and "Version 10 (WP-015" in v["result"]["scope"]
    end = next(e for e in journal(database_url, rid) if str(e["record"].get("reason") or "").startswith(REASON))
    with connect(database_url) as c:  # stored base altered (bytes only): never MATCH
        rec = {**end["record"], "response": {**end["record"]["response"], "incompatibility_base": "CORRIDOR"}}
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s", (Jsonb(rec), rid, end["seq"]))
        vid2 = deep.create_deep_validation(c, rid)
    v2 = done(vid2)
    assert v2["result"]["outcome"] == "mismatch"
    assert any(m["kind"] == "adviser_journal_stored_bytes" for m in v2["result"]["mismatches"])
    with connect(database_url) as c:
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s",
                  (Jsonb(end["record"]), rid, end["seq"]))
        vid3 = deep.create_deep_validation(c, rid)
    assert done(vid3)["result"]["outcome"] == "match"


def test_paired_v05_v06_evaluations_reports_and_read_only_comparison(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    listed = api.get("/api/adviser/methods").json()
    assert [m["method"] for m in listed["methods"]] == ["v0.2", "v0.3", "v0.4", "v0.5", "v0.6"]
    six = listed["methods"][4]
    assert six["status"] == "ENGINEERING_REVIEW_PENDING" and six["label"].startswith("Candidate v0.6")
    assert six["economic_usefulness"] == "UNVALIDATED" and six["rules_manifest"][0]["file"].startswith("MP-005")
    ids = {}
    for m in ("v0.5", "v0.6"):
        r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                               "method": m, "acknowledge_limitations": True})
        assert r.status_code == 201, r.text
        ids[m] = r.json()["evaluation_id"]
        assert r.json()["method"]["method"] == m
    run_all(worker(database_url, root, art, "observe:x", checkpoint_events=2000))
    rep = api.get(f"/api/evaluations/{ids['v0.6']}/report.json").json()
    a6 = rep["adviser"]
    assert a6["report_version"] == "adviser.report.v6" and a6["method"]["method"] == "v0.6"
    assert rep["capabilities"]["professional_adviser"]["reason"].startswith("MP-005 btc.context-action.v0.6")
    t = a6["responses"]["total"]
    assert t["counts"] == {"W": 1, "P": 1, "C": 0, "R": 0, "N": 0, "I": 0, "X": 1, "A": 0} and t["identities_hold"]
    inc = t["initial_incompatibility"]
    assert inc["count"] == 1 and inc["by_base"] == {"CORRIDOR": 0, "HISTORICAL_ECONOMICS": 1} and inc["subset_of_X"]
    assert inc["ratio_over_P"] == "1.0000" and a6["funnel"]["evidence_threshold"]["status"] == "NOT_APPLICABLE"
    assert a6["responses"]["report_cross_checks"] == {"W_equals_waits_opened": True,
                                                      "I_equals_A_RETURN_calls_in_window": True}
    assert "information_loss" in a6["responses"]["initial_incompatibility_notes"]
    md6 = api.get(f"/api/evaluations/{ids['v0.6']}/report.md").text
    assert "Candidate v0.6 (MP-005; engineering review pending" in md6
    assert "### A RETURN response (MP-004 §7 with MP-005 §6; unit = A RETURN child)" in md6
    assert "| Total | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 1.0000 |" in md6
    assert "#### Initial response incompatibility (MP-005 §6; subset of X)" in md6
    assert "| Total | 1 | 0 | 1 | 1 | 1 | 1.0000 | yes |" in md6 and "no later local classification" in md6
    a5 = api.get(f"/api/evaluations/{ids['v0.5']}/report.json").json()["adviser"]
    assert a5["report_version"] == "adviser.report.v5"
    assert a5["responses"]["total"]["counts"] == {"W": 1, "P": 1, "C": 0, "R": 1, "N": 1, "I": 0, "X": 0, "A": 0}
    assert "initial_incompatibility" not in a5["responses"]["total"]
    with connect(database_url) as c:
        n_before = c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"]
    cmp = api.get("/api/evaluations/compare/report.json", params={"a": ids["v0.5"], "b": ids["v0.6"]}).json()
    assert cmp["comparability"]["verdict"] == "COMPARABLE", cmp["comparability"]
    assert [x["id"] for x in cmp["limitations"]] == ["V06_MP005_INITIAL_RESPONSE_INCOMPATIBILITY_DELTA"]
    assert cmp["b"]["responses"]["initial_incompatibility"]["count"] == 1
    assert cmp["identities"]["b"]["implementation"] == "adviser.core.v6"
    md = api.get("/api/evaluations/compare/report.md", params={"a": ids["v0.5"], "b": ids["v0.6"]}).text
    assert "baseline v0.5 (A) vs candidate v0.6 (B)" in md and "subset of X, not added again): 1" in md
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"] == n_before  # nothing launched


def test_cancelled_v06_run_keeps_its_prefix_and_a_partial_report(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                           "method": "v0.6", "acknowledge_limitations": True})
    eid, rid = r.json()["evaluation_id"], r.json()["replay"]["replay_id"]

    def cancel_at(replay_id, cursor):
        if cursor >= _cursor(4, 10):
            with connect(database_url) as c:
                control.cancel(c, replay_id)
    run_all(worker(database_url, root, art, "observe:z", checkpoint_events=30, after_commit=cancel_at))
    assert replay(database_url, rid)["status"] == "cancelled"
    obs = api.get(f"/api/observations/{rid}").json()
    committed = (obs.get("adviser") or {}).get("committed") or {}
    assert committed["responses"] == {}  # no open wait at the checkpoint: P -> X happened in one dispatch
    rep = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert rep["completion"] == "INCOMPLETE" and rep["adviser"]["report_version"] == "adviser.report.v6"
    t = rep["adviser"]["responses"]["total"]
    assert t["counts"] == {"W": 1, "P": 1, "C": 0, "R": 0, "N": 0, "I": 0, "X": 1, "A": 0}
    assert t["initial_incompatibility"]["count"] == 1
    dj = journal(database_url, rid)
    pure = _pure()
    assert [(e["kind"], _strip(e["record"])) for e in dj] == \
        [(e["kind"], _strip(e["record"])) for e in pure.journal[:len(dj)]]
    assert records(database_url, rid) is not None
