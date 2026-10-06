"""WP-011 durable integration (DB): MP-002 v0.3 adviser evaluations over a real receipt-pinned pack prepared offline
from the hand fixture, through the observation worker (engine observe.stream.v4), next to the unchanged v0.2 path.
Engineering checks only (tiny synthetic inputs; no market evidence, no economic evaluation)."""

from __future__ import annotations

import pytest
from adviser3_fixtures import DAY1, a3_return_long
from adviser_db import EV_END, EV_START, fake_from, journal, prepare_pack, records, replay, run_all, worker, write_presets
from fastapi.testclient import TestClient
from pack_fixtures import connect
from psycopg.types.json import Jsonb

from algotrader.adviser.harness import run_pure
from algotrader.api import create_app
from algotrader.observe import control, deep
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import SimulatedCrash

pytestmark = pytest.mark.db
MINS = a3_return_long(tail=520)


def _prepared(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    return root, art, prepare_pack(database_url, root, fake_from(MINS))


def _launch(database_url, root, pack, method="v0.3", paused=False, speed=0):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], speed, paused,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation",
                                     adviser_method=method)


def _pure():
    n = int((EV_END - DAY1).total_seconds() // 60) + 365
    return run_pure(DAY1, MINS[:n], eval_start=EV_START, eval_end=EV_END, method="v0.3")


def _signature(database_url, rid):
    with connect(database_url) as c:
        fin = c.execute("SELECT commitment FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
    return ([e["digest"] for e in journal(database_url, rid)], [r["digest"] for r in records(database_url, rid)],
            dict((fin or {}).get("commitment", {})))


def crash_once_after(rid, at):
    fired = {"done": False}

    def hook(replay_id, cursor):
        if replay_id == rid and cursor >= at and not fired["done"]:
            fired["done"] = True
            raise SimulatedCrash()
    return hook


def test_v03_pack_evaluation_equals_the_pure_fold_with_reconciliation_v6(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed", row["error"]
    assert row["engine_format"] == "observe.stream.v4" and row["engine"]["adviser"]["method"] == "v0.3"
    assert row["engine"]["adviser"]["format"] == "algotrader.adviser-runtime.v3"
    assert row["engine"]["adviser"]["identity"]["implementation"] == "adviser.core.v3"
    v = row["manifest"]["validation"]
    assert v["validator_version"] == "6" and row["assurance"]["state"] == "passed", \
        [c for c in v["checks"] if not c["passed"]]
    names = {c["name"]: c["passed"] for c in v["checks"]}
    assert names["adviser_method_binding"] and names["adviser_lineage_immutability"] and names["adviser_finish_rederived"]
    assert row["manifest"]["adviser"]["method"] == "v0.3"
    pure = _pure()

    def strip(x):  # envelope/cursor excluded: the durable feed pins build/code identity and its own cursor numbering
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k not in ("env", "cursor")}
        return [strip(v) for v in x] if isinstance(x, list) else x

    assert [(e["kind"], strip(e["record"])) for e in journal(database_url, rid)] == \
        [(e["kind"], strip(e["record"])) for e in pure.journal]
    assert [r["record"] for r in records(database_url, rid) if r["kind"] == "path"] == pure.paths()
    calls = [e["record"] for e in journal(database_url, rid) if e["kind"] == "call"]
    assert len(calls) == 1 and calls[0]["entry_mode"] == "RETURN" and calls[0]["target"] == "100700.0"


def test_v03_cadence_crash_reclaim_step_and_corrupt_restore_give_identical_outputs(database_url, tmp_path,
                                                                                   monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    assert want[0] and want[1] and want[2]
    # cadence 7, hard crash right after a commit inside the WAIT period, reclaim by another worker
    rid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:b", checkpoint_events=7,
                       after_commit=crash_once_after(rid, 3 * 1681)))
    with connect(database_url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))
    run_all(worker(database_url, root, art, "observe:c", checkpoint_events=7))
    r = replay(database_url, rid)
    assert r["status"] == "completed" and r["assurance"]["state"] == "passed", r["error"]
    assert _signature(database_url, rid) == want
    # STEP (cadence 1) over a prefix, then paced resume
    sid = _launch(database_url, root, pack, paused=True, speed=400)
    w = worker(database_url, root, art, "observe:d", checkpoint_events=13)
    run_all(w)
    with connect(database_url) as c:
        for _ in range(30):
            control.step(c, sid)
            run_all(w)
        control.resume(c, sid)
    run_all(w)
    assert replay(database_url, sid)["status"] == "completed" and _signature(database_url, sid) == want
    # corrupted newest restore point: fall back to an older verified point, regenerate and verify the suffix
    cid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:e", checkpoint_events=500,
                       after_commit=crash_once_after(cid, 5100)))
    with connect(database_url) as c:
        c.execute("UPDATE observation_restore_points SET adviser_blob = 'x'::bytea WHERE replay_id = %s AND cursor = "
                  "(SELECT max(cursor) FROM observation_restore_points WHERE replay_id = %s)", (cid, cid))
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (cid,))
    run_all(worker(database_url, root, art, "observe:f", checkpoint_events=500))
    r = replay(database_url, cid)
    assert r["status"] == "completed", r["error"]
    assert any(e["event"] == "restore_fallback" for e in r["diagnostic_log"])
    assert _signature(database_url, cid) == want


def test_a_run_pinned_to_one_method_never_resumes_under_another(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)

    def pause_at(replay_id, cursor):
        if cursor >= 2000:
            with connect(database_url) as c:
                control.pause(c, replay_id)
    run_all(worker(database_url, root, art, "observe:p", checkpoint_events=500, after_commit=pause_at))
    assert replay(database_url, rid)["status"] == "paused"
    before = _signature(database_url, rid)
    with connect(database_url) as c:  # tamper the pinned method (simulates a run pinned to another release)
        eng = c.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
        eng["adviser"]["method"] = "v0.2"
        c.execute("UPDATE observation_replays SET engine = %s WHERE replay_id = %s", (Jsonb(eng), rid))
        control.resume(c, rid)
    run_all(worker(database_url, root, art, "observe:q", checkpoint_events=500))
    r = replay(database_url, rid)
    assert r["status"] == "failed" and "INCOMPATIBLE_ADVISER_IDENTITY" in (r["error"] or "")
    assert _signature(database_url, rid)[:2] == before[:2]  # committed outputs preserved, nothing replayed


def test_deep_v7_matches_a_completed_v03_run_and_detects_stored_tamper(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    w = worker(database_url, root, art, "observe:h", checkpoint_events=700)
    run_all(w)
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, rid)
    run_all(w)
    with connect(database_url) as c:
        v = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    assert v["status"] == "completed", v["error"]
    assert v["result"]["outcome"] == "match" and v["result"]["validator_version"] == "7", v["result"]["mismatches"]
    assert "Version 7" in v["result"]["scope"]
    with connect(database_url) as c:  # alter one stored entry-attempt record (bytes only, digest untouched)
        row = c.execute("SELECT seq, record FROM adviser_journal WHERE run_id = %s AND kind = 'entry_attempt' "
                        "ORDER BY seq LIMIT 1", (rid,)).fetchone()
        rec = dict(row["record"])
        rec["reason"] = "TAMPERED"
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s",
                  (Jsonb(rec), rid, row["seq"]))
        vid2 = deep.create_deep_validation(c, rid)
    run_all(w)
    with connect(database_url) as c:
        v2 = c.execute("SELECT result FROM observation_deep_validations WHERE validation_id = %s", (vid2,)).fetchone()
    assert v2["result"]["outcome"] == "mismatch"
    assert any(m["kind"] == "adviser_journal_stored_bytes" for m in v2["result"]["mismatches"])


def test_paired_v02_v03_evaluations_and_read_only_comparison(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    assert [m["method"] for m in api.get("/api/adviser/methods").json()["methods"]] == ["v0.2", "v0.3"]
    ids = {}
    for m in ("v0.2", "v0.3"):
        r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                               "method": m, "acknowledge_limitations": True})
        assert r.status_code == 201, r.text
        assert r.json()["method"]["method"] == m and r.json()["method"]["pinned_at_preparation"] is False
        ids[m] = r.json()["evaluation_id"]
    assert api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                              "method": "v0.4"}).status_code == 422
    # comparing before completion launches nothing and is labelled incomplete
    c0 = api.get("/api/evaluations/compare/report.json", params={"a": ids["v0.2"], "b": ids["v0.3"]}).json()
    assert c0["comparability"]["verdict"] in ("INCOMPLETE", "NOT_ADVISER_RUNS")
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"] == 2
    run_all(worker(database_url, root, art, "observe:x", checkpoint_events=2000))
    det = {m: api.get(f"/api/evaluations/{ids[m]}").json() for m in ids}
    assert det["v0.2"]["method"]["pinned_at_preparation"] and det["v0.2"]["method"]["label"] == "Original v0.2"
    assert det["v0.3"]["method"]["status"] == "ENGINEERING_REVIEW_PENDING"
    rep3 = api.get(f"/api/evaluations/{ids['v0.3']}/report.json").json()
    a3 = rep3["adviser"]
    assert a3["report_version"] == "adviser.report.v3" and a3["funnel"]["a_return_calls"] == 1
    assert a3["funnel"]["a_return_owners_entered_primary_60s"] == 1
    assert a3["funnel"]["evidence_threshold"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert a3["funnel"]["a_denominators"]["D_geometrically_evaluable"] == 1
    rep2 = api.get(f"/api/evaluations/{ids['v0.2']}/report.json").json()
    assert rep2["adviser"]["report_version"] == "adviser.report.v2"
    cmp = api.get("/api/evaluations/compare/report.json", params={"a": ids["v0.2"], "b": ids["v0.3"]}).json()
    assert cmp["comparability"]["verdict"] == "COMPARABLE", cmp["comparability"]
    assert cmp["a"]["method"] == "v0.2" and cmp["b"]["method"] == "v0.3"
    assert cmp["identities"]["a"]["implementation"] == "adviser.core.v2"
    assert cmp["identities"]["b"]["implementation"] == "adviser.core.v3"
    assert cmp["pins"]["a"]["pack_id"] == cmp["pins"]["b"]["pack_id"] == pack["pack_id"]
    assert cmp["conclusion"]["verdict"] == "INSUFFICIENT_EVIDENCE"
    md = api.get("/api/evaluations/compare/report.md", params={"a": ids["v0.2"], "b": ids["v0.3"]}).text
    assert "Comparability: COMPARABLE" in md and "not causal for RETURN alone" in md
    assert [x["id"] for x in cmp["limitations"]] == ["V02_DISLOCATION_BASELINE_DEFECT_CORRECTED_IN_V03"]
    assert "## Comparison limitations" in md and "cannot attribute any difference to RETURN alone" in md
    assert a3["funnel"]["a_destination_before_confirmation"]["count"] == 0
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"] == 2  # nothing launched
    md3 = api.get(f"/api/evaluations/{ids['v0.3']}/report.md").text
    assert "Revised v0.3" in md3 and "A RETURN owners entered at PRIMARY 60 s: 1" in md3


# -- WP-011 correction (Director review F1/F2): durable orchestration with a crash/reclaim at the boundary ----------


def _correction_minutes(kind):
    import adviser3_fixtures as fx
    from test_mp002_correction import collision

    mins = collision() if kind == "F1_box_collision" else fx.a3_stall_after_return()
    n = int((EV_END - DAY1).total_seconds() // 60) + 365
    return mins + fx.flat(max(0, n - len(mins)), mins[-1].c)


@pytest.mark.parametrize("kind", ["F1_box_collision", "F2_confirmed_samples"])
def test_correction_fixtures_durable_with_restore_at_the_boundary_equal_the_pure_fold(database_url, tmp_path,
                                                                                       monkeypatch, kind):
    mins = _correction_minutes(kind)
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    pack = prepare_pack(database_url, root, fake_from(mins))
    rid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):  # hard crash just after a commit at the 05:00 boundary, reclaim elsewhere
        run_all(worker(database_url, root, art, "observe:k", checkpoint_events=7,
                       after_commit=crash_once_after(rid, 3 * 1740)))
    with connect(database_url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))
    run_all(worker(database_url, root, art, "observe:l", checkpoint_events=7))
    row = replay(database_url, rid)
    assert row["status"] == "completed" and row["assurance"]["state"] == "passed", row["error"]
    n = int((EV_END - DAY1).total_seconds() // 60) + 365
    pure = run_pure(DAY1, mins[:n], eval_start=EV_START, eval_end=EV_END, method="v0.3")

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k not in ("env", "cursor")}
        return [strip(v) for v in x] if isinstance(x, list) else x

    dj = journal(database_url, rid)
    assert [(e["kind"], strip(e["record"])) for e in dj] == [(e["kind"], strip(e["record"])) for e in pure.journal]
    dr = [r["record"] for r in records(database_url, rid)]
    assert [strip(r) for r in dr] == [strip(r["record"]) for r in pure.records]
    if kind == "F1_box_collision":
        ret = [e["record"] for e in dj if e["kind"] == "observation" and e["record"]["category"] == "BOX_RETIRED"]
        assert len(ret) == 1 and ret[0]["env"]["clock_time"] == "2025-09-01T05:00:00Z"
        assert ret[0]["values"]["reason"].startswith("OPPOSITE_FAR_EDGE_CLOSE_DURING_B_LONG:")
    else:
        vs = {r["sample_time"]: r for r in dr if r.get("sample_time")}
        assert vs["2025-09-01T05:00:00Z"]["antecedent_activated_1h"] is True
        assert vs["2025-09-01T05:00:00Z"]["antecedent_activated_4h"] is True
        assert vs["2025-09-01T04:00:00Z"]["antecedent_activated_1h"] is True
