"""WP-012 durable integration (DB): MP-003 v0.4 adviser evaluations over a real receipt-pinned pack prepared offline
from the hand fixture ``contact_then_rearm`` (first arm 03:45, local V contact 03:50 -> ANCHOR_LOST 03:51, prospective
REARM 04:00, confirmation 04:09), through the observation worker (engine observe.stream.v5), next to the unchanged v0.3
path. Engineering checks only (tiny synthetic inputs; no market evidence, no economic evaluation)."""

from __future__ import annotations

import adviser4_fixtures as fx
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
_M = fx.contact_then_rearm()
MINS = (_M + fx.flat(max(0, N - len(_M)), _M[-1].c))[:N]
EV_PER_MIN = 3  # trade + mark + index per minute in this fixture
DAY2_0 = 1440  # minute index of day 2 00:00


def _cursor(h, m):
    return EV_PER_MIN * (DAY2_0 + 60 * h + m)


def _prepared(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    return root, art, prepare_pack(database_url, root, fake_from(MINS))


def _launch(database_url, root, pack, method="v0.4", paused=False, speed=0):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], speed, paused,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation",
                                     adviser_method=method)


def _pure(method="v0.4"):
    return run_pure(DAY1, MINS, eval_start=EV_START, eval_end=EV_END, method=method)


def _signature(database_url, rid):
    with connect(database_url) as c:
        fin = c.execute("SELECT commitment FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
    return ([e["digest"] for e in journal(database_url, rid)], [r["digest"] for r in records(database_url, rid)],
            dict((fin or {}).get("commitment", {})))


def _strip(x):  # envelope/cursor excluded: the durable feed pins build/code identity and its own cursor numbering
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


def test_v04_pack_evaluation_equals_the_pure_fold_with_reconciliation_v7(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed", row["error"]
    assert row["engine_format"] == "observe.stream.v5" and row["engine"]["adviser"]["method"] == "v0.4"
    assert row["engine"]["adviser"]["format"] == "algotrader.adviser-runtime.v4"
    assert row["engine"]["adviser"]["identity"]["implementation"] == "adviser.core.v4"
    v = row["manifest"]["validation"]
    assert v["validator_version"] == "7" and row["assurance"]["state"] == "passed", \
        [c for c in v["checks"] if not c["passed"]]
    assert "Version 7 (WP-012" in v["scope"]
    names = {c["name"]: c["passed"] for c in v["checks"]}
    assert names["adviser_method_binding"] and names["adviser_lineage_immutability"] and names["adviser_finish_rederived"]
    assert row["manifest"]["adviser"]["method"] == "v0.4"
    pure = _pure()
    dj = journal(database_url, rid)
    assert [(e["kind"], _strip(e["record"])) for e in dj] == [(e["kind"], _strip(e["record"])) for e in pure.journal]
    assert [r["record"] for r in records(database_url, rid) if r["kind"] == "path"] == pure.paths()
    tr = [(e["record"]["env"]["clock_time"][11:19], e["record"]["transition"]) for e in dj
          if e["kind"] == "scenario" and e["record"]["scenario_id"].startswith("AL")
          and "2025-09-01T03:4" <= e["record"]["env"]["clock_time"] < "2025-09-01T04:10"]
    assert tr == [("03:45:00", "ARM"), ("03:51:00", "ANCHOR_LOST"), ("04:00:00", "REARM"), ("04:09:00", "CONFIRM")]
    # the durable anchor publication cursor is the run's own admitted cursor at that dispatch
    rearm = next(e for e in dj if e["kind"] == "scenario" and e["record"]["transition"] == "REARM")
    assert rearm["record"]["anchor_published_cursor"] == rearm["factual_cursor"]


@pytest.mark.parametrize("crash_at", [("before_first_arm", (3, 40)), ("after_contact", (3, 52)),
                                      ("replacement_dispatch", (4, 0)), ("after_confirmation", (4, 10)),
                                      ("final_commit", None)], ids=lambda x: x[0])
def test_v04_crash_reclaim_at_every_anchor_stage_gives_identical_outputs(database_url, tmp_path, monkeypatch,
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


def test_v04_step_paced_cadence_and_corrupt_restore_give_identical_outputs(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    # pause just before the contact, STEP (one delivery each) through contact + replacement + confirmation, then paced
    sid = _launch(database_url, root, pack, speed=400)
    paused = {"done": False}

    def pause_before_contact(replay_id, cursor):
        if replay_id == sid and cursor >= _cursor(3, 44) and not paused["done"]:
            paused["done"] = True
            with connect(database_url) as c:
                control.pause(c, replay_id)
    w = worker(database_url, root, art, "observe:d", checkpoint_events=13, after_commit=pause_before_contact)
    run_all(w)
    assert replay(database_url, sid)["status"] == "paused"
    with connect(database_url) as c:
        for _ in range(EV_PER_MIN * 30):  # 03:44 -> 04:14 one delivery at a time
            control.step(c, sid)
            run_all(w)
        control.resume(c, sid)
    run_all(w)
    assert replay(database_url, sid)["status"] == "completed" and _signature(database_url, sid) == want
    # corrupted newest restore point after the replacement: fall back to an older verified point, regenerate, verify
    cid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:e", checkpoint_events=500,
                       after_commit=crash_once_after(cid, _cursor(4, 5))))
    with connect(database_url) as c:
        c.execute("UPDATE observation_restore_points SET adviser_blob = 'x'::bytea WHERE replay_id = %s AND cursor = "
                  "(SELECT max(cursor) FROM observation_restore_points WHERE replay_id = %s)", (cid, cid))
    _expire_lease(database_url, cid)
    run_all(worker(database_url, root, art, "observe:f", checkpoint_events=500))
    r = replay(database_url, cid)
    assert r["status"] == "completed", r["error"]
    assert any(e["event"] == "restore_fallback" for e in r["diagnostic_log"])
    assert _signature(database_url, cid) == want


def test_a_v04_run_never_resumes_under_v03(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)

    def pause_at(replay_id, cursor):
        if cursor >= _cursor(3, 55):
            with connect(database_url) as c:
                control.pause(c, replay_id)
    run_all(worker(database_url, root, art, "observe:p", checkpoint_events=500, after_commit=pause_at))
    assert replay(database_url, rid)["status"] == "paused"
    before = _signature(database_url, rid)
    with connect(database_url) as c:
        eng = c.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
        eng["adviser"]["method"] = "v0.3"
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


def test_deep_v8_matches_and_detects_anchor_tamper_at_start_and_after_a_nonzero_cursor_resume(database_url, tmp_path,
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
    assert v["result"]["outcome"] == "match" and v["result"]["validator_version"] == "8", v["result"]["mismatches"]
    assert "Version 8 (WP-012" in v["result"]["scope"]
    lost = next(e for e in journal(database_url, rid) if e["kind"] == "scenario"
                and e["record"]["transition"] == "ANCHOR_LOST")
    # (a) stored anchor evidence altered before launch (bytes only, digest untouched): never MATCH
    with connect(database_url) as c:
        rec = {**lost["record"], "anchor_status": "ACTIVE"}
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s", (Jsonb(rec), rid, lost["seq"]))
        vid2 = deep.create_deep_validation(c, rid)
    v2 = _deep_done(database_url, w, vid2)
    assert v2["result"]["outcome"] == "mismatch"
    assert any(m["kind"] == "adviser_journal_stored_bytes" for m in v2["result"]["mismatches"])
    with connect(database_url) as c:  # restore the original bytes
        c.execute("UPDATE adviser_journal SET record = %s WHERE run_id = %s AND seq = %s",
                  (Jsonb(lost["record"]), rid, lost["seq"]))
    # (b) a CLEAN validation paused at a nonzero cursor; the anchor record's digest is then altered; resume -> mismatch
    with connect(database_url) as c:
        vid3 = deep.create_deep_validation(c, rid)
        deep.control(c, vid3, "pause")
    v3 = _deep_done(database_url, w, vid3)
    assert v3["status"] == "paused" and 0 < v3["resume_cursor"] < v3["plan"]["committed_cursor"]
    assert v3["comparisons"]["mismatches"] == []
    with connect(database_url) as c:
        c.execute("UPDATE adviser_journal SET digest = %s WHERE run_id = %s AND seq = %s", ("f" * 64, rid, lost["seq"]))
        deep.control(c, vid3, "resume")
    v3 = _deep_done(database_url, w, vid3)
    assert v3["status"] == "completed" and v3["result"]["outcome"] == "mismatch"
    assert [m["at"] for m in v3["result"]["mismatches"] if m["kind"] == "adviser_journal_stored_bytes"] == \
        [f"seq {lost['seq']}"]
    with connect(database_url) as c:
        c.execute("UPDATE adviser_journal SET digest = %s WHERE run_id = %s AND seq = %s",
                  (lost["digest"], rid, lost["seq"]))
        vid4 = deep.create_deep_validation(c, rid)
    assert _deep_done(database_url, w, vid4)["result"]["outcome"] == "match"


def test_paired_v03_v04_evaluations_reports_and_read_only_comparison(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    listed = api.get("/api/adviser/methods").json()
    assert [m["method"] for m in listed["methods"]] == ["v0.2", "v0.3", "v0.4", "v0.5", "v0.6"] and listed["default"] == "v0.2"
    assert [m["status"] for m in listed["methods"]] == ["ACCEPTED_BASELINE", "TECHNICALLY_ACCEPTED",
                                                        "ENGINEERING_REVIEW_PENDING", "ENGINEERING_REVIEW_PENDING",
                                                        "ENGINEERING_REVIEW_PENDING"]  # WP-015 adds v0.6
    ids = {}
    for m in ("v0.2", "v0.3", "v0.4"):
        r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                               "method": m, "acknowledge_limitations": True})
        assert r.status_code == 201, r.text
        ids[m] = r.json()["evaluation_id"]
    assert api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                              "method": "v0.7"}).status_code == 422  # WP-015: v0.6 exists
    run_all(worker(database_url, root, art, "observe:x", checkpoint_events=2000))
    det = api.get(f"/api/evaluations/{ids['v0.4']}").json()
    assert det["method"]["method"] == "v0.4" and det["method"]["status"] == "ENGINEERING_REVIEW_PENDING"
    assert det["method"]["economic_usefulness"] == "UNVALIDATED" and det["method"]["pinned_at_preparation"]
    a4 = api.get(f"/api/evaluations/{ids['v0.4']}/report.json").json()["adviser"]
    assert a4["report_version"] == "adviser.report.v4" and a4["method"]["method"] == "v0.4"
    an = a4["anchors"]
    assert an["owners"] == {"lost_anchor": 1, "lost_anchor_warmup_origin": 0, "rearmed_by_replacement": 1,
                            "confirmed_after_replacement": 1, "structural_terminal_without_replacement": 0}
    assert (an["events"]["certified_contacts"], an["events"]["ambiguous_anchors"], an["events"]["replacements"]) == \
        (1, 0, 1)
    assert a4["funnel"]["a_confirmations"] == 1  # inherited registered funnel still reported
    md4 = api.get(f"/api/evaluations/{ids['v0.4']}/report.md").text
    assert "Candidate v0.4 (MP-003; engineering review pending" in md4 and "Pre-confirmation A anchors (owners): lost 1" \
        in md4 and "not the adviser chosen for this run" in md4
    a3 = api.get(f"/api/evaluations/{ids['v0.3']}/report.json").json()["adviser"]
    assert a3["report_version"] == "adviser.report.v3" and "anchors" not in a3
    assert a3["method"]["status"] == "TECHNICALLY_ACCEPTED"
    with connect(database_url) as c:
        n_before = c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"]
    cmp = api.get("/api/evaluations/compare/report.json", params={"a": ids["v0.3"], "b": ids["v0.4"]}).json()
    assert cmp["comparability"]["verdict"] == "COMPARABLE", cmp["comparability"]
    assert cmp["roles"]["baseline"]["method"] == "v0.3" and cmp["roles"]["candidate"]["method"] == "v0.4"
    assert [x["id"] for x in cmp["limitations"]] == ["V04_MP003_PRECONFIRMATION_ANCHOR_DELTA"]
    assert cmp["b"]["anchors"]["owners"]["lost_anchor"] == 1 and "anchors" not in cmp["a"]
    assert cmp["identities"]["b"]["implementation"] == "adviser.core.v4"
    md = api.get("/api/evaluations/compare/report.md", params={"a": ids["v0.3"], "b": ids["v0.4"]}).text
    assert "baseline v0.3 (A) vs candidate v0.4 (B)" in md and "Pre-confirmation anchors: owners lost 1" in md
    # v0.2/v0.3 comparison stays readable with its own limitation
    old = api.get("/api/evaluations/compare/report.json", params={"a": ids["v0.2"], "b": ids["v0.3"]}).json()
    assert old["comparability"]["verdict"] == "COMPARABLE"
    assert [x["id"] for x in old["limitations"]] == ["V02_DISLOCATION_BASELINE_DEFECT_CORRECTED_IN_V03"]
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM evaluations").fetchone()["n"] == n_before  # nothing launched


def test_cancelled_v04_run_keeps_its_committed_prefix_and_a_diagnostic_report(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                           "method": "v0.4", "acknowledge_limitations": True})
    eid, rid = r.json()["evaluation_id"], r.json()["replay"]["replay_id"]

    def cancel_at(replay_id, cursor):
        if cursor >= _cursor(3, 55):
            with connect(database_url) as c:
                control.cancel(c, replay_id)
    run_all(worker(database_url, root, art, "observe:z", checkpoint_events=300, after_commit=cancel_at))
    row = replay(database_url, rid)
    assert row["status"] == "cancelled", row["error"]
    rep = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert rep["completion"] == "INCOMPLETE" and rep["adviser"]["report_version"] == "adviser.report.v4"
    assert rep["adviser"]["anchors"]["owners"]["lost_anchor"] == 1  # committed prefix includes the 03:51 loss
    pure = _pure()
    dj = journal(database_url, rid)
    assert [(e["kind"], _strip(e["record"])) for e in dj] == \
        [(e["kind"], _strip(e["record"])) for e in pure.journal[:len(dj)]]
