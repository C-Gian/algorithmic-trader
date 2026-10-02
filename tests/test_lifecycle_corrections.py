"""WP-008-R1A correction (Director review of 66a2dce): bounded cancellation, comparable ETA windows and
explicit active / waiting / unknown timing.

Short deterministic offline fixtures (a few dozen feed events). Cancellation latency and reference-work
counters are measured after a nontrivial committed prefix, after pause/resume, and in each terminal phase.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client

from algotrader.api import create_app
from algotrader.marketdata import dataset as md
from algotrader.observe import control
from algotrader.observe import diagnostics as diag
from algotrader.observe.contracts import ReplayRuntimeState, SourceKind
from algotrader.observe.job import JobSpec, ReplayJob
from algotrader.observe.worker import ObservationWorker

pytestmark = pytest.mark.db


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


def row_of(conn, rid):
    return conn.execute("SELECT r.*, k.cursor FROM observation_replays r LEFT JOIN observation_checkpoints k "
                        "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()


def n_deliveries(conn, rid) -> int:
    return conn.execute("SELECT count(*) AS n FROM observation_deliveries WHERE replay_id = %s",
                        (rid,)).fetchone()["n"]


def wait_until(pred, timeout=60.0, every=0.02):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        v = pred()
        if v:
            return v
        time.sleep(every)
    raise AssertionError("condition not reached in time")


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:fix")
    kw.setdefault("checkpoint_events", 5)
    kw.setdefault("isolate", False)
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, **kw)


def counters(row) -> dict:
    return row["metrics"][str(row["lease_generation"])]


def assert_bounded_cancel(row, prefix: int) -> None:
    m = row["manifest"]
    assert row["status"] == "cancelled" and row["assurance"]["state"] == "incomplete"
    assert m["validation"]["outcome"] == "incomplete" and m["validation"]["passed"] is False
    assert [c["name"] for c in m["validation"]["checks"]] == ["validation_not_run"]
    assert {a["name"] for a in m["artifacts"]} == {"config.json", "validation.json"}
    assert m["applied_events"] == row["cursor"] == prefix
    c = counters(row)
    assert c["validation_deliveries_rederived"] == 0


# ---------------------------------------------------------------------------
# 1. Bounded cancellation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("isolate", [False, True], ids=["inline", "compute-process-under-cpu-load"])
def test_cancel_after_partial_prefix_is_bounded(database_url, env, conn, isolate):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    # CPU-bound busy work per applied event (holds the GIL) emulates local CPU load during REPLAYING
    w = worker(database_url, root, art, isolate=isolate, heartbeat_interval=0.3,
               faults={"REPLAYING_cpu_per_unit": 0.05})
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    wait_until(lambda: (row_of(conn, rid)["cursor"] or 0) >= 20, timeout=90)
    t0 = time.perf_counter()
    assert api.post(f"/api/observations/{rid}/cancel").status_code == 200
    ack = time.perf_counter() - t0
    wait_until(lambda: row_of(conn, rid)["status"] == "cancelled", timeout=30)
    latency = time.perf_counter() - t0
    t.join(30)
    row = row_of(conn, rid)
    prefix = row["cursor"]
    assert 20 <= prefix < row["total_events"]
    assert_bounded_cancel(row, prefix)
    c = counters(row)
    assert c["deliveries_loaded_for_finalize"] == 0  # no full-prefix load
    assert c["source_verifications"] == 1 and c["feed_builds"] == 1  # preparation only (once): no source reload
    rs = conn.execute("SELECT * FROM observation_ranges WHERE replay_id = %s ORDER BY from_cursor", (rid,)).fetchall()
    assert rs[-1]["to_cursor"] == prefix and sum(r["event_count"] for r in rs) == prefix  # committed input preserved
    assert n_deliveries(conn, rid) == 0  # no per-event rows in the streaming engine
    assert ack < 1.0 and latency < 2.0, (ack, latency)
    print(f"[{'process' if isolate else 'inline'}] cancel after {prefix} committed events: acknowledged "
          f"{ack * 1000:.0f} ms, terminal CANCELLED in {latency:.2f} s; re-derived 0, delivery rows loaded 0")
    rep = api.get(f"/api/observations/{rid}/report.json").json()
    assert rep["status"] == "cancelled" and rep["assurance"]["state"] == "incomplete"
    assert rep["coverage"]["committed_cursor"] == prefix and rep["manifest"]["claimed"]


def test_cancel_while_paused_after_resume_is_bounded(database_url, env, conn):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0,
                                              "paused": True}).json()["replay_id"]
    w = worker(database_url, root, art)
    w.run_once()  # prepare + park at 0
    for _ in range(3):
        api.post(f"/api/observations/{rid}/step")
        w.run_once()
    control.set_speed(conn, rid, 10)
    api.post(f"/api/observations/{rid}/resume")
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    wait_until(lambda: (row_of(conn, rid)["cursor"] or 0) >= 8)
    api.post(f"/api/observations/{rid}/pause")
    t.join(30)
    row = row_of(conn, rid)
    assert row["status"] == "paused"
    prefix, gen_before = row["cursor"], row["lease_generation"]
    t0 = time.perf_counter()
    assert api.post(f"/api/observations/{rid}/cancel").status_code == 200
    w.run_once()  # a new generation claims only to finalize the cancellation
    latency = time.perf_counter() - t0
    row = row_of(conn, rid)
    assert row["lease_generation"] == gen_before + 1
    assert_bounded_cancel(row, prefix)
    c = counters(row)
    # the finalizing generation did no reference work at all: no source reload, no prefix rebuild, no load
    assert c["source_verifications"] == 0 and c["feed_builds"] == 0 and c["prefix_restore_events"] == 0
    assert c["deliveries_loaded_for_finalize"] == 0 and c["events_applied"] == 0
    assert latency < 2.0, latency
    print(f"paused/resumed cancel at cursor {prefix}: terminal CANCELLED in {latency:.2f} s with zero reference work")


@pytest.mark.parametrize("at", ["FINALIZING", "VALIDATING", "GENERATING_REPORT"])
def test_cancel_in_terminal_phases_is_checked_before_publication(database_url, env, conn, at):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    orig = ReplayJob.enter_phase

    def cancel_on_entry(self, phase, **kw):
        orig(self, phase, **kw)
        if phase == at and self.spec.worker_id == "observe:term":
            control.cancel(conn, rid)  # the Owner presses Cancel just as this phase starts

    ReplayJob.enter_phase = cancel_on_entry
    try:
        t0 = time.perf_counter()
        worker(database_url, root, art, worker_id="observe:term", progress_interval=0.05).run_once()
        took = time.perf_counter() - t0
    finally:
        ReplayJob.enter_phase = orig
    row = row_of(conn, rid)
    assert row["cursor"] == row["total_events"]  # the replay cursor itself was complete
    assert row["status"] == "cancelled" and row["assurance"]["state"] == "incomplete"
    m = row["manifest"]
    assert m["status"] == "cancelled" and m["validation"]["passed"] is False
    assert "final_snapshot.json" not in {a["name"] for a in m["artifacts"]}
    c = counters(row)
    if at == "VALIDATING":  # cancellable validation stops early and reports INCOMPLETE checks
        assert c["validation_deliveries_rederived"] < row["total_events"] and "during VALIDATING" in row["error"]
    else:
        assert f"during {at}" in row["error"] and [x["name"] for x in m["validation"]["checks"]] == [
            "validation_not_run"]
    if at == "FINALIZING":
        assert c["validation_deliveries_rederived"] == 0
    # nothing COMPLETED was ever published for this generation
    gdir = art / "observations" / rid / m["artifact_dir"]
    assert '"status": "cancelled"' in (gdir / "manifest.json").read_text(encoding="utf-8")
    assert not list((art / "observations" / rid).glob(".staging-*"))
    print(f"cancel at {at}: finished CANCELLED/INCOMPLETE in {took:.2f} s (fixture total incl. preparation)")


def test_cancel_reaching_the_commit_lock_prevents_a_completed_publication(database_url, env, conn):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    orig = ReplayJob._terminal

    def late_cancel(self, status, *a, **kw):
        if kw.get("abort_if_cancelled"):  # validation passed; cancellation arrives right before the commit lock
            conn.execute("UPDATE observation_replays SET cancel_requested = true WHERE replay_id = %s", (rid,))
        return orig(self, status, *a, **kw)

    ReplayJob._terminal = late_cancel
    try:
        worker(database_url, root, art).run_once()
    finally:
        ReplayJob._terminal = orig
    row = row_of(conn, rid)
    assert row["status"] == "cancelled" and row["manifest"]["status"] == "cancelled"
    assert "terminal commit boundary" in row["error"] and row["assurance"]["state"] == "incomplete"
    assert not list((art / "observations" / rid).glob(".staging-*"))
    # after a terminal commit the cancel command is serialized behind it and rejected (atomic boundary)
    rid2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    worker(database_url, root, art).run_once()
    assert row_of(conn, rid2)["status"] == "completed"
    assert api.post(f"/api/observations/{rid2}/cancel").status_code == 409


# ---------------------------------------------------------------------------
# 2. ETA windows
# ---------------------------------------------------------------------------


def test_replay_eta_window_excludes_long_preparation(database_url, env, conn):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 10}).json()[
        "replay_id"]
    w = worker(database_url, root, art, progress_interval=0.05, faults={"VERIFYING_SOURCE_cpu_per_unit": 0.25})
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    v = wait_until(lambda: (lambda x: x if x["operation"]["phase"] == "VERIFYING_SOURCE" else None)(
        api.get(f"/api/observations/{rid}").json()))
    assert v["progress"]["eta_seconds"] is None  # no replay ETA during preparation
    wait_until(lambda: (row_of(conn, rid)["cursor"] or 0) >= 15, timeout=60)
    row = row_of(conn, rid)
    v = api.get(f"/api/observations/{rid}").json()
    t.join(60)
    prep = sum(e["wall_seconds"] or 0 for e in row_of(conn, rid)["phase_history"]
               if e["phase"] in ("PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED", "INITIALIZING"))
    assert prep > 2.0  # a long preparation really happened first
    assert row["throughput_since"] >= row["phase_started_at"]  # window starts at REPLAYING, never at claim
    eta, basis = v["progress"]["eta_seconds"], v["progress"]["eta_basis"]
    assert eta is not None and "wall-clock replay time in the current REPLAYING window" in basis
    assert "declared pacing waits" in basis and "not active compute throughput" in basis
    remaining = v["progress"]["total_events"] - v["progress"]["applied_events"]
    expected = remaining / 10.0  # pacing 10 events/s
    assert expected * 0.5 < eta < expected * 1.6, (eta, expected, prep)  # not inflated by preparation
    print(f"replay ETA {eta:.1f}s vs pacing-implied {expected:.1f}s after {prep:.1f}s of preparation")


def test_substage_unit_and_total_changes_reset_the_rate_window(database_url, env, conn):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    w = worker(database_url, root, art)
    _r, gen, _f, _x = w.claim()
    job = ReplayJob(JobSpec(database_url, rid, w.worker_id, gen, str(root), str(art), progress_interval=0.0))
    job.enter_phase("VERIFYING_SOURCE")
    for i in range(0, 41, 10):
        job.milestone("hash dataset files", i, 40, "files", force=True)
        time.sleep(0.05)
    p = row_of(conn, rid)["progress"]
    assert (p["rate_base_done"], p["done"], p["unit"]) == (0, 40, "files") and p["rate_window_seconds"] > 0
    job.milestone("check raw source pages", 0, 500, "pages", force=True)
    p = row_of(conn, rid)["progress"]
    assert p["rate_base_done"] == 0 and p["rate_window_seconds"] == 0 and p["unit"] == "pages"
    assert api.get(f"/api/observations/{rid}").json()["operation"]["eta"]["seconds"] is None
    job.milestone("check raw source pages", 300, 500, "pages", force=True)
    job.milestone("check raw source pages", 300, 900, "pages", force=True)  # total changed: new window
    p = row_of(conn, rid)["progress"]
    assert p["rate_base_done"] == 300 and p["rate_window_seconds"] == 0
    job.enter_phase("BUILDING_FEED")  # a new phase never inherits a rate base
    p = row_of(conn, rid)["progress"]
    assert p["rate_base_done"] is None and p["phase"] == "BUILDING_FEED"
    job.close()


# ---------------------------------------------------------------------------
# 3. Timing accounting
# ---------------------------------------------------------------------------


def test_pacing_waits_are_declared_and_excluded_from_active_time(database_url, env, conn):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=40)
    worker(database_url, root, art, sleep=time.sleep).run_once()
    row = row_of(conn, rid)
    assert row["status"] == "completed"
    span = next(e for e in row["phase_history"] if e["phase"] == "REPLAYING")
    c = counters(row)
    assert span["measured"] and span["waiting_seconds"] == pytest.approx(c["pacing_sleep_seconds"], abs=0.05)
    assert span["waiting_seconds"] > 1.0  # 61 events at 40 events/s
    assert span["active_seconds"] < span["wall_seconds"] - span["waiting_seconds"] + 0.5
    op = api.get(f"/api/observations/{rid}").json()["operation"]
    rp = next(p for p in op["timeline"]["phases"] if p["phase"] == "REPLAYING")
    assert rp["waiting_seconds"] == pytest.approx(span["waiting_seconds"], abs=1e-6)
    assert op["timeline"]["active_complete"] is True and op["timeline"]["unmeasured_spans"] == 0
    q = next(e for e in row["phase_history"] if e["phase"] == "QUEUED")
    assert q["active_seconds"] == 0.0 and q["waiting_seconds"] == q["wall_seconds"]


def test_interrupted_spans_stay_unknown_and_terminal_text_follows_the_cursor(database_url, env, conn):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    from algotrader.observe.job import SimulatedCrash

    def crash(replay_id, cursor):
        if cursor == 10:
            raise SimulatedCrash()

    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", before_commit=crash).run_once()
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))
    worker(database_url, root, art, worker_id="observe:b").run_once()
    row = row_of(conn, rid)
    spans = [e for e in row["phase_history"] if e["interrupted"]]
    assert [e["phase"] for e in spans] == ["REPLAYING"]
    assert spans[0]["active_seconds"] is None and spans[0]["measured"] is False  # unknown, not zero
    v = api.get(f"/api/observations/{rid}").json()
    tl = v["operation"]["timeline"]
    assert tl["unmeasured_spans"] == 1 and tl["active_complete"] is False
    assert next(p for p in tl["phases"] if p["phase"] == "REPLAYING")["unmeasured_spans"] == 1
    assert "unmeasured" in api.get(f"/api/observations/{rid}/report.md").text
    # completion is operational; assurance is reported separately
    assert v["runtime_state"] == "completed" and "assurance passed is reported separately" in v["runtime_detail"]
    # terminal-phase text never claims a complete cursor for a partial run
    base = dict(row)
    base.update(status="running", phase="VALIDATING", applied=10, cancel_requested=False, paused=False,
                lease_expires_at=datetime(2999, 1, 1, tzinfo=UTC),
                progress={"finalizing_as": "failed"}, suspended_at=None)
    state, detail = diag.runtime_state(base, lease_expired=False)
    assert state == ReplayRuntimeState.FINISHING and "partial run at cursor 10/" in detail
    assert "cursor complete" not in detail and "as failed" in detail
    base.update(applied=base["total_events"], progress={"finalizing_as": "completed"})
    _s, detail = diag.runtime_state(base, lease_expired=False)
    assert "replay cursor complete" in detail and "completion is separate from assurance" in detail
