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
from psycopg.types.json import Jsonb
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


# ---------------------------------------------------------------------------
# R1C correction regressions (delivery/WP-008-R1C-DIRECTOR-REVIEW.md)
# ---------------------------------------------------------------------------


def test_reconciliation_requires_a_trusted_receipt(database_url, conn, env):
    api, root, art, ds = env
    row = completed_run(database_url, conn, root, art, ds)
    base = reconcile_inputs(conn, root, row)
    for receipt in (None, {**base["receipt"], "cache_manifest_sha256": "e" * 64},
                    {**base["receipt"], "event_count": base["receipt"]["event_count"] + 1}):
        out, _ = reconcile(**{**base, "receipt": receipt})
        assert out.outcome == ValidationOutcome.FAILED and not out.passed
        bad = [c.name for c in out.checks if not c.passed]
        assert bad == ["cache_receipt_and_pin"], bad
    out, _ = reconcile(**{**base, "receipt": None})
    assert "no trusted receipt" in next(c.detail for c in out.checks if c.name == "cache_receipt_and_pin")


def _receipt_dropper(conn, saved: list):
    """After-commit hook: removes the run's trusted receipt after preparation pinned the cache, i.e. between
    preparation and the final reconciliation of a real run."""

    def drop(replay_id, cursor):
        if not saved and not replay_id.startswith("deep-"):
            eng = conn.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (replay_id,)).fetchone()
            cid = eng["engine"]["cache_id"]
            saved.append(conn.execute("SELECT * FROM observation_feed_caches WHERE cache_id = %s", (cid,)).fetchone())
            conn.execute("DELETE FROM observation_feed_caches WHERE cache_id = %s", (cid,))

    return drop


def test_receipt_removed_after_preparation_fails_real_terminal_assurance(database_url, conn, env):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    saved: list = []
    drain(worker(database_url, root, art, after_commit=_receipt_dropper(conn, saved)))
    assert saved and saved[0] is not None
    run = api.get(f"/api/observations/{rid}").json()
    assert run["status"] == "completed"  # the replay finished; its assurance cannot pass
    assert run["validation_passed"] is False and run["operation"]["assurance"]["state"] == "failed"
    m = conn.execute("SELECT manifest FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["manifest"]
    checks = {c["name"]: c for c in m["validation"]["checks"]}
    assert checks["cache_receipt_and_pin"]["passed"] is False
    assert "no trusted receipt" in checks["cache_receipt_and_pin"]["detail"]
    assert all(c["passed"] for n, c in checks.items() if n != "cache_receipt_and_pin")  # nothing else was wrong
    s = run["assurance_summary"]
    assert s["headline"].startswith("ASSURANCE WARNING") and "verified" not in s["headline"]


def _deep_row(conn, vid):
    return conn.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()


def _cancel_on_phase(monkeypatch, conn, phase):
    real = deep.DeepJob.enter_phase

    def enter(self, p, **kw):
        if p == phase:
            deep.control(conn, self.rid, "cancel")  # accepted before the job observes the phase
        return real(self, p, **kw)

    monkeypatch.setattr(deep.DeepJob, "enter_phase", enter)


def _artifact_bytes(art: Path) -> dict[str, bytes]:
    return {str(p.relative_to(art)): p.read_bytes() for p in sorted(art.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("phase", ["PREPARING_SOURCE", "VALIDATING", "GENERATING_REPORT"])
def test_deep_cancel_accepted_in_any_phase_never_completes(database_url, conn, env, monkeypatch, phase):
    api, root, art, ds = env
    row = completed_run(database_url, conn, root, art, ds)
    rid = row["replay_id"]
    before_row = conn.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    before_art = _artifact_bytes(art)
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    _cancel_on_phase(monkeypatch, conn, phase)
    drain(worker(database_url, root, art))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "cancelled" and d["result"]["outcome"] == "incomplete", (phase, d["result"])
    assert "INCOMPLETE" in d["error"] and phase in d["error"]
    counters = next(iter(_deep_row(conn, vid)["metrics"].values()))
    if phase == "PREPARING_SOURCE":
        assert counters["events_reexecuted"] == 0  # bounded: no reference work after an observed cancel
    if phase == "GENERATING_REPORT":
        assert d["result"]["covered_events"] == d["result"]["target_events"] == row["cursor"]
    assert api.post(f"/api/observations/deep-validations/{vid}/cancel").status_code == 409  # already terminal
    md_text = api.get(f"/api/observations/deep-validations/{vid}/report.md").text
    assert "CANCELLED" in md_text and "MATCH" not in md_text
    assert api.get(f"/api/observations/deep-validations/{vid}/report.md").text == md_text  # deterministic
    assert api.get(f"/api/observations/deep-validations/{vid}/report.json").text == \
        api.get(f"/api/observations/deep-validations/{vid}/report.json").text
    # the originating run's records and artifacts are untouched
    after_row = conn.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    assert after_row == before_row and _artifact_bytes(art) == before_art
    s = api.get(f"/api/observations/{rid}").json()["assurance_summary"]
    assert s["deep_validation"] == "incomplete" and "matched" not in s["headline"]
    assert s["run_validation"] == "passed" and s["headline"].startswith("Runtime integrity verified")


def test_deep_cancel_immediately_before_the_terminal_lock_wins(database_url, conn, env):
    api, root, art, ds = env
    rid = completed_run(database_url, conn, root, art, ds)["replay_id"]
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]

    def cancel_before_lock(job_id, where):
        if job_id == vid and where == -1:
            deep.control(conn, vid, "cancel")

    drain(worker(database_url, root, art, before_commit=cancel_before_lock))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "cancelled" and d["result"]["outcome"] == "incomplete"
    assert "before the terminal commit" in d["error"]
    assert d["result"]["covered_events"] == d["result"]["target_events"]  # exact diagnostic coverage kept


def test_deep_cancel_holding_the_row_lock_is_ordered_before_the_terminal_commit(database_url, conn, env):
    api, root, art, ds = env
    rid = completed_run(database_url, conn, root, art, ds)["replay_id"]
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    started: list[float] = []

    def cancel_in_flight(job_id, where):
        # a cancel command already holds the row lock (uncommitted) when the job reaches its terminal boundary
        if job_id != vid or where != -1:
            return
        other = psycopg.connect(database_url, row_factory=psycopg.rows.dict_row)
        other.execute("SELECT 1 FROM observation_deep_validations WHERE validation_id = %s FOR UPDATE", (vid,))
        other.execute("UPDATE observation_deep_validations SET cancel_requested = true WHERE validation_id = %s",
                      (vid,))

        def commit_later():
            time.sleep(0.4)
            other.commit()
            other.close()

        threading.Thread(target=commit_later, daemon=True).start()
        started.append(time.monotonic())

    drain(worker(database_url, root, art, before_commit=cancel_in_flight))
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert started and d["status"] == "cancelled" and d["result"]["outcome"] == "incomplete"


def test_deep_cancel_after_the_terminal_commit_is_rejected(database_url, conn, env):
    api, root, art, ds = env
    rid = completed_run(database_url, conn, root, art, ds)["replay_id"]
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    outcomes: list[str] = []
    blocked: list[threading.Thread] = []

    def cancel(c):
        try:
            deep.control(c, vid, "cancel")
            outcomes.append("accepted")
        except deep.DeepRejected as exc:
            outcomes.append(str(exc))

    def while_locked(job_id, where):
        if job_id != vid or where != -2:
            return

        def concurrent():
            with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c2:
                cancel(c2)

        t = threading.Thread(target=concurrent, daemon=True)
        t.start()
        t.join(0.4)
        assert t.is_alive()  # blocked on the row lock held by the terminal commit
        blocked.append(t)

    def after(job_id, where):
        if job_id == vid:
            cancel(conn)

    drain(worker(database_url, root, art, before_commit=while_locked, after_commit=after))
    blocked[0].join(10)
    d = api.get(f"/api/observations/deep-validations/{vid}").json()
    assert d["status"] == "completed" and d["result"]["outcome"] == "match"
    assert outcomes == ["Deep validation already completed"] * 2, outcomes
    assert not _deep_row(conn, vid)["cancel_requested"]


def test_deep_stale_generation_cannot_publish_a_terminal_result(database_url, conn, env):
    api, root, art, ds = env
    rid = completed_run(database_url, conn, root, art, ds)["replay_id"]
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]

    def reclaimed_elsewhere(job_id, where):
        if job_id == vid and where == -1:  # another worker took over under a new fencing generation
            conn.execute("UPDATE observation_deep_validations SET lease_generation = lease_generation + 1, "
                         "lease_owner = 'observe:other' WHERE validation_id = %s", (vid,))

    worker(database_url, root, art, before_commit=reclaimed_elsewhere).run_once()
    st = _deep_row(conn, vid)
    assert st["status"] == "running" and st["result"] is None and st["finished_at"] is None
    assert st["lease_owner"] == "observe:other"


def test_assurance_headline_keeps_failed_runtime_and_deep_match_separate(database_url, conn, env):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    saved: list = []
    drain(worker(database_url, root, art, after_commit=_receipt_dropper(conn, saved)))
    assert api.get(f"/api/observations/{rid}").json()["operation"]["assurance"]["state"] == "failed"
    # restore the receipt afterwards so the optional reference re-execution can run (and MATCH)
    r = saved[0]
    cols = list(r.keys())
    conn.execute(f"INSERT INTO observation_feed_caches ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                 [Jsonb(v) if isinstance(v, dict | list) else v for v in r.values()])
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    drain(worker(database_url, root, art))
    assert api.get(f"/api/observations/deep-validations/{vid}").json()["result"]["outcome"] == "match"
    s = api.get(f"/api/observations/{rid}").json()["assurance_summary"]
    assert s["run_validation"] == "failed" and s["deep_validation"] == "match"
    assert "verified" not in s["headline"] and "Runtime integrity FAILED" in s["headline"]
    assert s["headline"].startswith("ASSURANCE WARNING") and "matched" in s["headline"]
    assert any("Runtime integrity FAILED" in w for w in s["warnings"])
    diag = api.get(f"/api/observations/{rid}/report.md").text
    assert "Runtime (this run's own validation): failed" in diag
    assert "Reference (optional Deep validation): match" in diag


def test_assurance_headline_keeps_incomplete_runtime_and_limited_deep_coverage(database_url, conn, env):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)

    def cancel_mid_replay(replay_id, cursor):
        if replay_id == rid and cursor >= 14:
            control.cancel(conn, rid)

    drain(worker(database_url, root, art, after_commit=cancel_mid_replay))
    run = api.get(f"/api/observations/{rid}").json()
    assert run["status"] == "cancelled" and run["operation"]["assurance"]["state"] == "incomplete"
    vid = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    drain(worker(database_url, root, art))
    res = api.get(f"/api/observations/deep-validations/{vid}").json()["result"]
    assert res["outcome"] == "match" and res["target_events"] < res["run_total_events"]
    s = api.get(f"/api/observations/{rid}").json()["assurance_summary"]
    assert s["run_validation"] == "incomplete" and s["deep_validation"] == "match"
    assert "verified" not in s["headline"] and "Runtime assurance INCOMPLETE" in s["headline"]
    assert s["limitations"] and "uncommitted remainder was not examined" in s["limitations"][0]


def test_cancelled_deep_validation_after_a_preceding_match_is_not_reported_as_match(database_url, conn, env,
                                                                                     monkeypatch):
    api, root, art, ds = env
    rid = completed_run(database_url, conn, root, art, ds)["replay_id"]
    first = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    drain(worker(database_url, root, art))
    second = api.post(f"/api/observations/{rid}/deep-validations").json()["validation_id"]
    _cancel_on_phase(monkeypatch, conn, "VALIDATING")
    drain(worker(database_url, root, art))
    s = api.get(f"/api/observations/{rid}").json()["assurance_summary"]
    assert s["latest_deep_validation"] == second and s["deep_validation"] == "incomplete"
    assert s["reference"]["earlier_match"] == first
    assert "CANCELLED - INCOMPLETE" in s["headline"] and f"earlier Deep validation {first} matched" in s["headline"]
    assert "reference re-execution matched" not in s["headline"]
