"""WP-008-R1C assurance: layered reconciliation, artifact publication integrity and optional Deep validation.

Bounded offline engineering fixtures; Deep validation of real substantial history stays Owner-launched.
"""

from __future__ import annotations

import copy
import threading
import time
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client

from algotrader.api import create_app
from algotrader.feed.ordering import default_freshness
from algotrader.marketdata import dataset as md
from algotrader.observe import control, deep
from algotrader.observe import feedcache as fc
from algotrader.observe.contracts import ReplayStatus, SourceKind, ValidationOutcome
from algotrader.observe.job import SimulatedCrash
from algotrader.observe.reconcile import reconcile
from algotrader.observe.worker import ObservationWorker

pytestmark = pytest.mark.db
FRESH = default_freshness()


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


@pytest.fixture
def env(database_url, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    return api, root, art, ds


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:assure")
    kw.setdefault("isolate", False)
    kw.setdefault("checkpoint_events", 7)
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, sleep=lambda s: None, **kw)


def drain(w) -> None:
    while w.run_once():
        pass


def completed_run(database_url, conn, root, art, ds) -> dict:
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    return conn.execute("SELECT r.*, k.cursor, k.snapshot_digest FROM observation_replays r JOIN "
                        "observation_checkpoints k USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()


def reconcile_inputs(conn, root, row):
    rid, eng = row["replay_id"], row["engine"]
    cache = fc.open_cache(root, eng["cache_id"], expected_manifest_sha256=eng["cache_manifest_sha256"])
    ranges = conn.execute("SELECT * FROM observation_ranges WHERE replay_id = %s ORDER BY from_cursor", (rid,)).fetchall()
    terminal = conn.execute("SELECT * FROM observation_restore_points WHERE replay_id = %s AND terminal",
                            (rid,)).fetchone()
    receipt = conn.execute("SELECT * FROM observation_feed_caches WHERE cache_id = %s", (eng["cache_id"],)).fetchone()
    return dict(status=ReplayStatus.COMPLETED, cache=cache, ranges=ranges, cursor=row["cursor"], terminal=terminal,
                committed_snapshot_digest=row["snapshot_digest"], engine=eng, freshness=FRESH,
                hook=lambda *a: None, receipt=receipt)


# ---------------------------------------------------------------------------
# Terminal reconciliation v2 (normal runs: bounded, no replay)
# ---------------------------------------------------------------------------


def test_reconciliation_detects_every_tampered_commitment_class(database_url, conn, env):
    api, root, art, ds = env
    row = completed_run(database_url, conn, root, art, ds)
    base = reconcile_inputs(conn, root, row)
    v, snap = reconcile(**base)
    assert v.outcome == ValidationOutcome.PASSED and snap is not None
    names = {c.name for c in v.checks}
    assert {"consumed_input_exact", "cache_receipt_and_pin", "commitments_reported"} <= names

    def failing(**changes) -> set[str]:
        args = {**base, **changes}
        out, _ = reconcile(**args)
        assert out.outcome == ValidationOutcome.FAILED
        return {c.name for c in out.checks if not c.passed}

    r = copy.deepcopy(base["ranges"])
    r[2]["commitment_after"], r[3]["commitment_before"] = "0" * 64, "0" * 64  # self-consistent chain, wrong bytes
    assert "consumed_input_exact" in failing(ranges=r)
    r = copy.deepcopy(base["ranges"])
    r[1]["first_order"], r[1]["last_order"] = r[1]["last_order"], r[1]["first_order"]
    assert "committed_ranges_contiguous" in failing(ranges=r)
    r = copy.deepcopy(base["ranges"])
    r[4]["first_order"] = r[3]["first_order"]  # not strictly after the previous range
    assert "committed_ranges_contiguous" in failing(ranges=r)
    r = copy.deepcopy(base["ranges"])
    r[-1]["snapshot_digest"] = "f" * 64
    assert "terminal_state_verified" in failing(ranges=r)
    assert "cache_receipt_and_pin" in failing(receipt={"cache_manifest_sha256": "e" * 64})
    assert "consumed_input_exact" in failing(cursor=row["cursor"] - 1, status=ReplayStatus.CANCELLED,
                                             ranges=base["ranges"])
    t = dict(base["terminal"])
    t["commitment"] = "a" * 64
    assert {"input_commitment_chain", "consumed_input_exact"} <= failing(terminal=t)


def test_partial_artifact_publication_is_never_referenced(database_url, conn, env, monkeypatch):
    api, root, art, ds = env
    from algotrader.observe import artifacts

    real = artifacts._sha256

    def corrupt_after_rename(path):  # a file damaged between staging and the post-publication check
        digest, size, lines = real(path)
        return ("0" * 64, size, lines) if path.name == "ranges.jsonl" and path.parent.name.startswith("g") else (
            digest, size, lines)

    monkeypatch.setattr(artifacts, "_sha256", corrupt_after_rename)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    row = conn.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    assert row["status"] == "failed" and row["manifest"] is None
    assert "partial or corrupt publication" in row["error"]
    rep = api.get(f"/api/observations/{rid}/report.json").json()
    assert rep["manifest"]["claimed"] is False


# ---------------------------------------------------------------------------
# Deep validation
# ---------------------------------------------------------------------------


def test_deep_validation_match_report_and_idempotent_rerun(database_url, conn, env):
    api, root, art, ds = env
    row = completed_run(database_url, conn, root, art, ds)
    rid = row["replay_id"]
    before = {k: row[k] for k in ("manifest", "assurance", "metrics", "status")}
    t0 = time.perf_counter()
    res = api.post(f"/api/observations/{rid}/deep-validations")
    ack = time.perf_counter() - t0
    assert res.status_code == 201 and ack < 1.0, ack
    v = res.json()
    vid = v["validation_id"]
    assert v["status"] == "queued" and v["mode"] == "canonical-cache-only"
    assert api.post(f"/api/observations/{rid}/deep-validations").status_code == 409  # one active per run
    snap = api.get(f"/api/observations/deep-validations/{vid}/report.json").json()
    assert snap["snapshot"] is True and snap["captured_at"]
    drain(worker(database_url, root, art))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "completed" and d["result"]["outcome"] == "match"
    res_ = d["result"]
    assert res_["covered_events"] == res_["target_events"] == row["cursor"]
    assert res_["compared"] >= 3 * len(conn.execute("SELECT 1 FROM observation_ranges WHERE replay_id = %s",
                                                     (rid,)).fetchall())
    assert "not an independent source audit" in res_["scope"]
    assert res_["input_examined"].startswith("canonical feed cache only")
    md_text = api.get(f"/api/observations/deep-validations/{vid}/report.md").text
    assert "MATCH" in md_text and "never changes the originating run" in md_text
    assert api.get(f"/api/observations/deep-validations/{vid}/report.md").text == md_text  # terminal: deterministic
    # the originating run is untouched; the current assurance summary links the result
    after = conn.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    assert {k: after[k] for k in before} == before
    summary = api.get(f"/api/observations/{rid}").json()["assurance_summary"]
    assert summary["deep_validation"] == "match" and not summary["warnings"]
    assert "matched" in summary["headline"]
    # a second Deep validation reproduces the same result (idempotent comparison evidence)
    v2 = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    drain(worker(database_url, root, art))
    d2 = api.get(f"/api/observations/deep-validations/{v2}").json()
    keys = ("outcome", "covered_events", "compared", "comparison_cursors", "mismatches")
    assert {k: d2["result"][k] for k in keys} == {k: res_[k] for k in keys}


def test_deep_validation_mismatch_becomes_a_linked_warning_without_touching_the_run(database_url, conn, env):
    api, root, art, ds = env
    row = completed_run(database_url, conn, root, art, ds)
    rid = row["replay_id"]
    # simulate a corrupted committed record (what Deep validation exists to detect)
    conn.execute("UPDATE observation_ranges SET snapshot_digest = %s WHERE replay_id = %s AND range_seq = 2",
                 ("9" * 64, rid))
    terminal_md = api.get(f"/api/observations/{rid}/report.md").text
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    drain(worker(database_url, root, art))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "completed" and d["result"]["outcome"] == "mismatch"
    m = d["result"]["mismatches"]
    assert len(m) == 1 and m[0]["kind"] == "snapshot" and m[0]["cursor"] == 21 and m[0]["at"] == "range 2"
    run = api.get(f"/api/observations/{rid}").json()
    assert run["status"] == "completed" and run["validation_passed"] is True  # original result preserved
    assert run["assurance_summary"]["warnings"] and run["assurance_summary"]["headline"].startswith("ASSURANCE WARNING")
    diag = api.get(f"/api/observations/{rid}/report.md").text
    assert "WARNING: Deep validation" in diag and diag != terminal_md


def test_deep_validation_cancel_pause_resume_and_restart(database_url, conn, env, monkeypatch):
    api, root, art, ds = env
    row = completed_run(database_url, conn, root, art, ds)
    rid = row["replay_id"]
    monkeypatch.setattr(deep, "SAVE_EVENTS", 10)
    # restart: the compute attempt dies after a diagnostic save; a new generation resumes from it
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    real_save = deep.DeepJob._save

    def crash_after_second_save(self, cursor, *a):
        real_save(self, cursor, *a)
        if cursor >= 20 and self.spec.worker_id == "observe:a":
            raise SimulatedCrash()

    monkeypatch.setattr(deep.DeepJob, "_save", crash_after_second_save)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a").run_once()
    monkeypatch.setattr(deep.DeepJob, "_save", real_save)
    conn.execute("UPDATE observation_deep_validations SET lease_expires_at = now() - interval '1 second' "
                 "WHERE validation_id = %s", (vid,))
    v = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert v["health"] == "unresponsive" and v["progress"]["saved_cursor"] == 20
    drain(worker(database_url, root, art, worker_id="observe:b"))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "completed" and d["result"]["outcome"] == "match" and d["generation"] == 2
    assert any(e["event"] == "deep_resumed" and e["cursor"] == 20 for e in d["diagnostic_log"])
    # cancel while running -> INCOMPLETE diagnostic, no conclusion about the run
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    w = worker(database_url, root, art, progress_interval=0.0, faults={"VALIDATING_cpu_per_unit": 0.05})
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    end = time.monotonic() + 30
    while time.monotonic() < end and conn.execute("SELECT phase FROM observation_deep_validations WHERE "
                                                  "validation_id = %s", (vid,)).fetchone()["phase"] != "VALIDATING":
        time.sleep(0.02)
    t0 = time.perf_counter()
    api.post(f"/api/observations/deep-validations/{vid}/cancel")
    t.join(30)
    took = time.perf_counter() - t0
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "cancelled" and d["result"]["outcome"] == "incomplete" and took < 2.0, took
    assert api.get(f"/api/observations/{rid}").json()["assurance_summary"]["deep_validation"] in ("incomplete",
                                                                                                    "match")
    # pause parks at a saved cursor; resume continues to a match
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    w = worker(database_url, root, art, progress_interval=0.0, faults={"VALIDATING_cpu_per_unit": 0.03})
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    end = time.monotonic() + 30
    while time.monotonic() < end and conn.execute("SELECT phase FROM observation_deep_validations WHERE "
                                                  "validation_id = %s", (vid,)).fetchone()["phase"] != "VALIDATING":
        time.sleep(0.02)
    api.post(f"/api/observations/deep-validations/{vid}/pause")
    t.join(30)
    p = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert p["status"] == "paused" and p["progress"]["saved_cursor"] > 0
    api.post(f"/api/observations/deep-validations/{vid}/resume")
    drain(worker(database_url, root, art))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "completed" and d["result"]["outcome"] == "match"


def test_deep_validation_rejects_unsupported_runs_and_lost_caches(database_url, conn, env):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    assert api.post(f"/api/observations/{rid}/deep-validations").status_code == 409  # not finished yet
    drain(worker(database_url, root, art))
    import shutil

    row = conn.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    shutil.rmtree(fc.cache_root(root) / row["engine"]["cache_id"])
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    drain(worker(database_url, root, art))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "failed" and "can be rebuilt by launching a new replay" in d["error"]
    assert api.get(f"/api/observations/{rid}").json()["validation_passed"] is True
