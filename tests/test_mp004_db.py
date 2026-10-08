"""WP-014 durable integration (DB): MP-004 v0.5 adviser evaluations over a real receipt-pinned pack prepared offline
from the hand fixture ``adviser5_fixtures.valid`` (confirmation 04:01 -> WAIT_RETURN; the usable return [04:01,04:02)
prepares the reference at 04:02; the recovery [04:02,04:03) issues at 04:03), through the observation worker (engine
observe.stream.v6), next to the unchanged v0.4 path. Engineering checks only (tiny synthetic inputs; no market
evidence, no economic evaluation)."""

from __future__ import annotations

import adviser5_fixtures as fx
import pytest
from adviser_db import EV_END, EV_START, fake_from, journal, prepare_pack, records, replay, run_all, worker, write_presets
from adviser3_fixtures import DAY1
from fastapi.testclient import TestClient
from pack_fixtures import connect
from psycopg.types.json import Jsonb

from algotrader.adviser.harness import run_pure
from algotrader.api import create_app
from algotrader.observe import control, deep
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import SimulatedCrash

pytestmark = pytest.mark.db
N = int((EV_END - DAY1).total_seconds() // 60) + 365
_M = fx.valid()
MINS = (_M + fx.flat(max(0, N - len(_M)), _M[-1].c))[:N]
_MW = fx.favourable_equality_only()  # a reference still waiting at 04:30 (cancel / partial report)
MINS_WAIT = (_MW + fx.flat(max(0, N - len(_MW)), _MW[-1].c))[:N]
EV_PER_MIN = 3  # trade + mark + index per minute in this fixture
DAY2_0 = 1440


def _cursor(h, m):
    return EV_PER_MIN * (DAY2_0 + 60 * h + m)


def _prepared(database_url, tmp_path, monkeypatch, mins=MINS):
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    return root, art, prepare_pack(database_url, root, fake_from(mins))


def _launch(database_url, root, pack, method="v0.5", paused=False, speed=0):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], speed, paused,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation",
                                     adviser_method=method)


def _pure(method="v0.5", mins=MINS):
    return run_pure(DAY1, mins, eval_start=EV_START, eval_end=EV_END, method=method)


def _signature(database_url, rid):
    with connect(database_url) as c:
        fin = c.execute("SELECT commitment FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
    return ([e["digest"] for e in journal(database_url, rid)], [r["digest"] for r in records(database_url, rid)],
            dict((fin or {}).get("commitment", {})))


def _strip(x):  # envelope/cursors excluded: the durable feed pins build/code identity and its own cursor numbering
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k not in ("env", "cursor", "anchor_published_cursor",
                                                                "destination_monitoring_cursor", "published_cursor")}
    return [_strip(v) for v in x] if isinstance(x, list) else x


def crash_once_after(rid, at):
    fired = {"done": False}

    def hook(replay_id, cursor):
        if replay_id == rid and cursor >= at and not fired["done"]:
            fired["done"] = True
            raise SimulatedCrash()
    return hook


def _expire_lease(database_url, rid):
    with connect(database_url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))


def _a_entries(dj):
    return [e for e in dj if e["kind"] == "entry_attempt" and e["record"]["scenario_id"].startswith("AL")]


def test_v05_pack_evaluation_equals_the_pure_fold_with_reconciliation_v8(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed", row["error"]
    assert row["engine_format"] == "observe.stream.v6" and row["engine"]["adviser"]["method"] == "v0.5"
    assert row["engine"]["adviser"]["format"] == "algotrader.adviser-runtime.v5"
    assert row["engine"]["adviser"]["identity"]["implementation"] == "adviser.core.v5"
    v = row["manifest"]["validation"]
    assert v["validator_version"] == "8" and row["assurance"]["state"] == "passed", \
        [c for c in v["checks"] if not c["passed"]]
    assert "Version 8 (WP-014" in v["scope"] and "Version 7 (WP-012" in v["scope"]
    names = {c["name"]: c["passed"] for c in v["checks"]}
    assert names["adviser_method_binding"] and names["adviser_lineage_immutability"] and names["adviser_finish_rederived"]
    assert row["manifest"]["adviser"]["method"] == "v0.5" and row["manifest"]["schema_revision"] == 8
    pure = _pure()
    dj = journal(database_url, rid)
    assert [(e["kind"], _strip(e["record"])) for e in dj] == [(e["kind"], _strip(e["record"])) for e in pure.journal]
    assert [r["record"] for r in records(database_url, rid) if r["kind"] == "path"] == pure.paths()
    tr = [(e["record"]["env"]["clock_time"][11:19], e["record"]["transition"]) for e in _a_entries(dj)]
    assert tr == [("04:01:00", "WAIT_OPEN"), ("04:02:00", "RESPONSE_REFERENCE"), ("04:03:00", "ISSUE")]
    # the durable reference publication cursor is the run's own admitted cursor at that dispatch
    ref = _a_entries(dj)[1]
    assert ref["record"]["response"]["published_cursor"] == str(ref["factual_cursor"])


@pytest.mark.parametrize("crash_at", [("before_wait", (3, 50)), ("wait_return", (4, 1)), ("after_preparation", (4, 2)),
                                      ("at_recovery_issue", (4, 3)), ("after_issue", (4, 10)),
                                      ("final_commit", None)], ids=lambda x: x[0])
def test_v05_crash_reclaim_at_every_response_stage_gives_identical_outputs(database_url, tmp_path, monkeypatch,
                                                                           crash_at):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
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
    ents = _a_entries(journal(database_url, rid))
    assert [e["record"]["transition"] for e in ents].count("RESPONSE_REFERENCE") == 1  # never re-prepared
    assert [e["record"]["transition"] for e in ents].count("ISSUE") == 1  # never re-evaluated or reopened


def test_v05_step_paced_cadence_and_corrupt_restore_give_identical_outputs(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    # pause before the confirmation, STEP (one delivery each) through WAIT, preparation and the issue, then paced
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
        for _ in range(EV_PER_MIN * 8):  # 03:58 -> 04:06 one delivery at a time
            control.step(c, sid)
            run_all(w)
        control.resume(c, sid)
    run_all(w)
    assert replay(database_url, sid)["status"] == "completed" and _signature(database_url, sid) == want
    # corrupted newest restore point inside the response wait: fall back to an older verified point, regenerate, verify
    cid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:e", checkpoint_events=500,
                       after_commit=crash_once_after(cid, _cursor(4, 2) + 1)))
    with connect(database_url) as c:
        c.execute("UPDATE observation_restore_points SET adviser_blob = 'x'::bytea WHERE replay_id = %s AND cursor = "
                  "(SELECT max(cursor) FROM observation_restore_points WHERE replay_id = %s)", (cid, cid))
    _expire_lease(database_url, cid)
    run_all(worker(database_url, root, art, "observe:f", checkpoint_events=500))
    r = replay(database_url, cid)
    assert r["status"] == "completed", r["error"]
    assert any(e["event"] == "restore_fallback" for e in r["diagnostic_log"])
    assert _signature(database_url, cid) == want


def test_a_v05_run_never_resumes_under_v04(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)

    def pause_at(replay_id, cursor):
        if cursor >= _cursor(4, 2):
            with connect(database_url) as c:
                control.pause(c, replay_id)
    run_all(worker(database_url, root, art, "observe:p", checkpoint_events=500, after_commit=pause_at))
    assert replay(database_url, rid)["status"] == "paused"
    before = _signature(database_url, rid)
    with connect(database_url) as c:
        eng = c.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
        eng["adviser"]["method"] = "v0.4"
        c.execute("UPDATE observation_replays SET engine = %s WHERE replay_id = %s", (Jsonb(eng), rid))
        control.resume(c, rid)
    run_all(worker(database_url, root, art, "observe:q", checkpoint_events=500))
    r = replay(database_url, rid)
    assert r["status"] == "failed" and "INCOMPATIBLE_ADVISER_IDENTITY" in (r["error"] or "")
    assert _signature(database_url, rid)[:2] == before[:2]


def _deep_done(database_url, w, vid):
    run_all(w)
    with connect(database_url) as c:
        return c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()


def test_deep_v9_matches_and_detects_response_tamper_at_start_and_after_a_nonzero_cursor_resume(database_url, tmp_path,
                                                                                                monkeypatch):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 400)
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    w = worker(database_url, root, art, "observe:h", checkpoint_events=700)
    run_all(w)
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, rid)
    v = _deep_done(database_url, w, vid)
    assert v["status"] == "completed", v["error"]
    assert v["result"]["outcome"] == "match" and v["result"]["validator_version"] == "9", v["result"]["mismatches"]
    assert "Version 9 (WP-014" in v["result"]["scope"]
    ref = next(e for e in journal(database_url, rid) if e["kind"] == "entry_attempt"
               and e["record"]["transition"] == "RESPONSE_REFERENCE")
    # (a) stored reference evidence altered before launch (bytes only, digest untouched): never MATCH
    with connect(database_url) as c:
        rec = {**ref["record"], "response": {**ref["record"]["response"], "H0": "100009"}}
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s", (Jsonb(rec), rid, ref["seq"]))
        vid2 = deep.create_deep_validation(c, rid)
    v2 = _deep_done(database_url, w, vid2)
    assert v2["result"]["outcome"] == "mismatch"
    assert any(m["kind"] == "adviser_journal_stored_bytes" for m in v2["result"]["mismatches"])
    with connect(database_url) as c:  # restore the original bytes
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s",
                  (Jsonb(ref["record"]), rid, ref["seq"]))
    # (b) a CLEAN validation paused at a nonzero cursor; the reference record's digest is then altered; resume
    with connect(database_url) as c:
        vid3 = deep.create_deep_validation(c, rid)
        deep.control(c, vid3, "pause")
    v3 = _deep_done(database_url, w, vid3)
    assert v3["status"] == "paused" and 0 < v3["resume_cursor"] < v3["plan"]["committed_cursor"]
    assert v3["comparisons"]["mismatches"] == []
    with connect(database_url) as c:
        c.execute("UPDATE adviser_journal SET digest = %s WHERE run_id = %s AND seq = %s", ("f" * 64, rid, ref["seq"]))
        deep.control(c, vid3, "resume")
    v3 = _deep_done(database_url, w, vid3)
    assert v3["status"] == "completed" and v3["result"]["outcome"] == "mismatch"
    assert [m["at"] for m in v3["result"]["mismatches"] if m["kind"] == "adviser_journal_stored_bytes"] == \
        [f"seq {ref['seq']}"]
    with connect(database_url) as c:
        c.execute("UPDATE adviser_journal SET digest = %s WHERE run_id = %s AND seq = %s",
                  (ref["digest"], rid, ref["seq"]))
        vid4 = deep.create_deep_validation(c, rid)
    assert _deep_done(database_url, w, vid4)["result"]["outcome"] == "match"


def test_paired_v04_v05_evaluations_reports_and_read_only_comparison(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    listed = api.get("/api/adviser/methods").json()
    assert [m["method"] for m in listed["methods"]] == ["v0.2", "v0.3", "v0.4", "v0.5"] and listed["default"] == "v0.2"
    assert listed["methods"][3]["status"] == "ENGINEERING_REVIEW_PENDING"
    assert listed["methods"][3]["label"] == "Candidate v0.5 — RETURN waits for a local recovery"
    ids = {}
    for m in ("v0.4", "v0.5"):
        r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                               "method": m, "acknowledge_limitations": True})
        assert r.status_code == 201, r.text
        ids[m] = r.json()["evaluation_id"]
        assert r.json()["method"]["method"] == m  # recognisable before the worker pins it
    assert api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                              "method": "v0.6"}).status_code == 422
    run_all(worker(database_url, root, art, "observe:x", checkpoint_events=2000))
    det = api.get(f"/api/evaluations/{ids['v0.5']}").json()
    assert det["method"]["method"] == "v0.5" and det["method"]["status"] == "ENGINEERING_REVIEW_PENDING"
    assert det["method"]["economic_usefulness"] == "UNVALIDATED" and det["method"]["pinned_at_preparation"]
    rep = api.get(f"/api/evaluations/{ids['v0.5']}/report.json").json()
    a5 = rep["adviser"]
    assert a5["report_version"] == "adviser.report.v5" and a5["method"]["method"] == "v0.5"
    assert rep["capabilities"]["professional_adviser"]["reason"].startswith("MP-004 btc.context-action.v0.5")
    t = a5["responses"]["total"]
    assert t["counts"] == {"W": 1, "P": 1, "C": 0, "R": 1, "N": 0, "I": 1, "X": 0, "A": 0} and t["identities_hold"]
    assert a5["responses"]["report_cross_checks"] == {"W_equals_waits_opened": True,
                                                      "I_equals_A_RETURN_calls_in_window": True}
    assert a5["funnel"]["waiting"]["observed_usable_return"] == 1 and "anchors" in a5
    md5 = api.get(f"/api/evaluations/{ids['v0.5']}/report.md").text
    assert "Candidate v0.5 (MP-004; engineering review pending" in md5
    assert "### A RETURN response (MP-004 §7; unit = A RETURN child)" in md5
    assert "| Total | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1.0000 |" in md5
    a4 = api.get(f"/api/evaluations/{ids['v0.4']}/report.json").json()["adviser"]
    assert a4["report_version"] == "adviser.report.v4" and "responses" not in a4
    with connect(database_url) as c:
        n_before = c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"]
    cmp = api.get("/api/evaluations/compare/report.json", params={"a": ids["v0.4"], "b": ids["v0.5"]}).json()
    assert cmp["comparability"]["verdict"] == "COMPARABLE", cmp["comparability"]
    assert cmp["roles"]["baseline"]["method"] == "v0.4" and cmp["roles"]["candidate"]["method"] == "v0.5"
    rpins = cmp["comparability"]["release_pins"]  # the baseline is the current packaged v0.4 (reuse condition)
    assert rpins["a"]["state"] == rpins["b"]["state"] == "MATCHES_CURRENT_PACKAGE"
    assert [x["id"] for x in cmp["limitations"]] == ["V05_MP004_RETURN_RESPONSE_DELTA"]
    assert cmp["b"]["responses"]["total"]["I"] == 1 and "responses" not in cmp["a"]
    assert cmp["identities"]["b"]["implementation"] == "adviser.core.v5"
    md = api.get("/api/evaluations/compare/report.md", params={"a": ids["v0.4"], "b": ids["v0.5"]}).text
    assert "baseline v0.4 (A) vs candidate v0.5 (B)" in md and "A RETURN response (MP-004 §7): W 1 · P 1" in md
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"] == n_before  # nothing launched


def test_cancelled_v05_run_keeps_its_prefix_and_a_partial_report_with_the_wait_open(database_url, tmp_path,
                                                                                    monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch, MINS_WAIT)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                           "method": "v0.5", "acknowledge_limitations": True})
    eid, rid = r.json()["evaluation_id"], r.json()["replay"]["replay_id"]

    def cancel_at(replay_id, cursor):
        if cursor >= _cursor(4, 30):
            with connect(database_url) as c:
                control.cancel(c, replay_id)
    run_all(worker(database_url, root, art, "observe:z", checkpoint_events=30, after_commit=cancel_at))
    row = replay(database_url, rid)
    assert row["status"] == "cancelled", row["error"]
    # the committed adviser view shows the response wait (never an entry)
    obs = api.get(f"/api/observations/{rid}").json()
    committed = (obs.get("adviser") or {}).get("committed") or {}
    assert next(iter(committed["responses"].values()))["phase"] == "WAIT_RESPONSE"
    rep = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert rep["completion"] == "INCOMPLETE" and rep["adviser"]["report_version"] == "adviser.report.v5"
    resp = rep["adviser"]["responses"]
    assert resp["total"]["counts"] == {"W": 1, "P": 1, "C": 0, "R": 0, "N": 0, "I": 0, "X": 0, "A": 1}
    assert "not complete" in resp["cutoff_meaning"] and resp["total"]["identities_hold"]
    md = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "| Total | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |" in md
    pure = _pure(mins=MINS_WAIT)
    dj = journal(database_url, rid)
    assert [(e["kind"], _strip(e["record"])) for e in dj] == \
        [(e["kind"], _strip(e["record"])) for e in pure.journal[:len(dj)]]
