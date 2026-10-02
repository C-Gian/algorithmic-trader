"""WP-008-R1A: observable job lifecycle and diagnosis (offline fixtures, disposable databases).

Covers the durable launch, worker-owned preparation with honest PENDING identity,
supervisor/compute separation (CPU-bound work longer than a short lease), distinct health
states (alive without progress, dead compute, unresponsive, recovering, DB outage /
disconnected), generation fencing against stale same-id owners (observation and corpus),
cancel during validation at a full cursor, diagnostic exports in every state (including
missing manifest and failed publication) and preservation of pre-upgrade runs.

No real network, no month/year replay: the fixtures are a few dozen feed events, and
CPU-bound phases are emulated with a test-only busy-loop fault per bounded unit.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client
from psycopg.types.json import Jsonb

from test_corpus import plan_file  # noqa: F401 - fixture reuse

from algotrader import db, ops
from algotrader.api import create_app
from algotrader.marketdata import dataset as md
from algotrader.observe import control
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import JobSpec, LeaseLost, ReplayJob
from algotrader.observe.worker import ObservationWorker

pytestmark = pytest.mark.db


def make_dataset(root: Path) -> str:
    return md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


@pytest.fixture
def env(database_url, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = make_dataset(root)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    return api, root, art, ds


def inline(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:inline")
    kw.setdefault("lease_seconds", 5)
    return ObservationWorker(database_url, root, art, poll_interval=0.01, isolate=False, **kw)


def row_of(conn, rid):
    return conn.execute("SELECT r.*, k.cursor FROM observation_replays r LEFT JOIN observation_checkpoints k "
                        "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()


def wait_until(pred, timeout=60.0, every=0.05):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        v = pred()
        if v:
            return v
        time.sleep(every)
    raise AssertionError("condition not reached in time")


def in_thread(fn) -> threading.Thread:
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Durable launch + worker-owned preparation
# ---------------------------------------------------------------------------


def test_launch_is_durable_and_prompt_while_preparation_is_slow(database_url, env, monkeypatch):
    api, root, art, ds = env
    slow = {"calls": 0}
    real_verify = md.verify

    def slow_verify(path, progress=None):  # deliberately slow source verification
        slow["calls"] += 1
        time.sleep(1.5)
        return real_verify(path, progress=progress)

    monkeypatch.setattr(md, "verify", slow_verify)
    t0 = time.perf_counter()
    res = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0})
    launch_seconds = time.perf_counter() - t0
    assert res.status_code == 201 and launch_seconds < 1.0, launch_seconds
    print(f"durable launch acknowledged in {launch_seconds * 1000:.0f} ms while verification sleeps 1.5 s")
    assert slow["calls"] == 0  # nothing verified/hashed/built inside the launch request
    v = res.json()
    rid = v["replay_id"]
    # honest PENDING identity: no placeholder verified identity, no zero total posing as known
    assert v["configured"] is False and v["feed"] is None and v["verification"] is None
    assert v["progress"]["total_events"] is None and v["source"]["source_status"] == "PENDING"
    assert v["operation"]["status"] == "queued" and v["operation"]["health"] == "waiting"
    launch = row_of(psycopg.connect(database_url, row_factory=psycopg.rows.dict_row), rid)["launch"]
    assert launch["source_id"] == ds and launch["schema_version"] == "algotrader.observe.v1"

    w = inline(database_url, root, art, progress_interval=0.05)
    t = in_thread(w.run_once)
    seen = wait_until(lambda: (lambda o: o if o["phase"] == "VERIFYING_SOURCE" else None)(
        api.get(f"/api/observations/{rid}").json()["operation"]), timeout=20)
    assert seen["health"] == "progressing" and seen["status"] == "running"
    snap = api.get(f"/api/observations/{rid}/report.json").json()  # copyable while preparing
    assert snap["snapshot"] and snap["identity"]["feed_content_identity"] == "PENDING"
    assert snap["phase"] in ("VERIFYING_SOURCE", "BUILDING_FEED") and snap["assurance"]["state"] == "not_checked"
    t.join(60)
    done = api.get(f"/api/observations/{rid}").json()
    assert done["status"] == "completed" and done["configured"] and done["validation_passed"]
    phases = {p["phase"]: p for p in done["operation"]["timeline"]["phases"]}
    for name in ("QUEUED", "PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED", "INITIALIZING", "REPLAYING",
                 "FINALIZING", "VALIDATING", "GENERATING_REPORT"):
        assert phases[name]["spans"] >= 1, name
    assert phases["VERIFYING_SOURCE"]["active_seconds"] >= 1.4  # the slow verification was measured
    # the verified config was persisted before the first causal application, and BUILDING_FEED re-verifies
    # (duplicate verification is a documented remaining cost removed in R1B)
    m = api.get(f"/api/observations/{rid}/manifest").json()
    counters = m["operational_metrics"]
    assert counters["source_verifications"] == 2 and counters["feed_builds"] == 1
    assert counters["events_applied"] == counters["snapshots_built"] - 2 == m["total_events"]
    assert counters["transactions_committed"] == counters["delivery_rows_written"] == m["total_events"]
    assert counters["validation_deliveries_rederived"] == m["total_events"]
    assert counters["cpu_seconds"] is not None


def test_preparation_failure_cancel_and_restart_are_visible(database_url, env, conn):
    api, root, art, ds = env
    # 1. missing source after a valid launch -> visible failed job with a report (no config, no manifest)
    other = make_dataset(root / "other")
    import shutil

    shutil.copytree(md.dataset_path(root / "other", other), md.datasets_dir(root) / f"{other}-x")
    bad = api.post("/api/observations", json={"source_kind": "dataset", "source_id": f"{other}-x"}).json()
    inline(database_url, root, art).run_once()
    v = api.get(f"/api/observations/{bad['replay_id']}").json()
    assert v["status"] == "failed" and "source not replayable" in v["error"] and v["configured"] is False
    rep = api.get(f"/api/observations/{bad['replay_id']}/report.md").text
    assert "FAILED" in rep and "PREPARING_SOURCE" in rep or "VERIFYING_SOURCE" in rep

    # 2. cancel while VERIFYING_SOURCE (CPU-bound per unit) -> cancelled at a safe boundary, never prepared
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds}).json()["replay_id"]
    w = inline(database_url, root, art, progress_interval=0.02, faults={"VERIFYING_SOURCE_cpu_per_unit": 0.2})
    t = in_thread(w.run_once)
    wait_until(lambda: row_of(conn, rid)["phase"] == "VERIFYING_SOURCE")
    t0 = time.perf_counter()
    assert api.post(f"/api/observations/{rid}/cancel").status_code == 200
    t.join(30)
    applied_in = time.perf_counter() - t0
    r = row_of(conn, rid)
    assert r["status"] == "cancelled" and "during source preparation" in r["error"] and r["config"] is None
    assert applied_in < 2.0, applied_in  # control applied within the bounded unit target
    print(f"cancel during VERIFYING_SOURCE applied in {applied_in:.2f} s")
    assert r["assurance"]["state"] == "not_checked"

    # 3. worker dies during BUILDING_FEED -> restart is discoverable: interrupted span + recovery entry
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds}).json()["replay_id"]
    from algotrader.observe.job import SimulatedCrash

    class Boom(SimulatedCrash):
        pass

    orig = ReplayJob.enter_phase

    def crash_on_build(self, phase, **kw):
        orig(self, phase, **kw)
        if phase == "BUILDING_FEED" and self.spec.worker_id == "observe:dies":
            raise Boom()

    ReplayJob.enter_phase = crash_on_build
    try:
        with pytest.raises(Boom):
            inline(database_url, root, art, worker_id="observe:dies").run_once()
    finally:
        ReplayJob.enter_phase = orig
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))
    v = api.get(f"/api/observations/{rid}").json()
    assert v["runtime_state"] == "unresponsive" and v["operation"]["health"] == "unresponsive"
    inline(database_url, root, art, worker_id="observe:next").run_once()
    r = row_of(conn, rid)
    assert r["status"] == "completed" and r["lease_generation"] == 2 and r["attempt"] == 2
    assert r["recovery_log"][-1]["generation"] == 2 and r["recovery_log"][-1]["previous_generation"] == 1
    interrupted = [e for e in r["phase_history"] if e["interrupted"]]
    assert [e["phase"] for e in interrupted] == ["BUILDING_FEED"] and interrupted[0]["generation"] == 1


# ---------------------------------------------------------------------------
# Supervisor / compute separation and truthful health
# ---------------------------------------------------------------------------


def test_cpu_bound_validation_longer_than_lease_stays_alive_without_false_recovery(database_url, env, conn):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    # separate compute PROCESS (production mode); CPU-bound busy work per validated delivery makes
    # VALIDATING last several times longer than the deliberately short 1.5 s lease
    w = ObservationWorker(database_url, root, art, worker_id="observe:iso", lease_seconds=1.5,
                          heartbeat_interval=0.3, poll_interval=0.05, isolate=True,
                          faults={"VALIDATING_cpu_per_unit": 0.06})
    t0 = time.perf_counter()
    t = in_thread(w.run_once)
    wait_until(lambda: row_of(conn, rid)["phase"] == "VALIDATING", timeout=90)
    observed = []
    while t.is_alive():
        v = api.get(f"/api/observations/{rid}").json()
        if v["operation"]["phase"] == "VALIDATING" and v["status"] == "running":
            observed.append((v["runtime_state"], v["operation"]["health"], v["lease_expired"],
                             v["operation"]["supervisor"].get("child_pid")))
        time.sleep(0.2)
    t.join()
    elapsed = time.perf_counter() - t0
    r = row_of(conn, rid)
    validating = sum(e["active_seconds"] or 0 for e in r["phase_history"] if e["phase"] == "VALIDATING")
    assert validating > 3 * 1.5, validating  # genuinely longer than the lease
    assert len(observed) >= 5
    assert all(o[0] == "finishing" and o[1] == "progressing" and o[2] is False for o in observed), observed
    assert all(o[3] for o in observed)  # the supervisor tracks a live compute child
    assert r["status"] == "completed" and r["attempt"] == 1 and r["lease_generation"] == 1
    assert r["recovery_log"] == [] and r["manifest"]["validation"]["passed"]
    assert r["supervisor"]["isolated_compute"] is True and r["supervisor"]["supervisor_pid"] != r["supervisor"][
        "child_pid"]
    print(f"cpu-bound validation fixture: {elapsed:.1f}s wall, VALIDATING {validating:.1f}s active, lease 1.5s")


def test_alive_without_progress_dead_compute_and_reclaim_are_distinct(database_url, env, conn):
    api, root, art, ds = env
    # alive compute, no milestones beyond the phase limit -> alive_no_progress (lease still renewed)
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    w = ObservationWorker(database_url, root, art, worker_id="observe:quiet", lease_seconds=1.5,
                          heartbeat_interval=0.3, isolate=True, stall_limit=1.0,
                          faults={"VALIDATING_silent_stall": 4.0})
    t = in_thread(w.run_once)
    v = wait_until(lambda: (lambda x: x if x["operation"]["health"] == "alive_no_progress" else None)(
        api.get(f"/api/observations/{rid}").json()), timeout=90)
    assert v["lease_expired"] is False and v["operation"]["phase"] == "VALIDATING"
    assert "no compute milestone" in v["operation"]["health_detail"]
    t.join(90)
    assert row_of(conn, rid)["status"] == "completed"

    # compute process dies hard -> compute_lost (supervisor stops renewing at once), then a fenced reclaim
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    dead = ObservationWorker(database_url, root, art, worker_id="observe:dead", lease_seconds=30,
                             heartbeat_interval=0.3, isolate=True, faults={"REPLAYING_hard_exit": 9})
    dead.run_once()  # returns after the child died
    v = api.get(f"/api/observations/{rid}").json()
    assert v["operation"]["health"] == "compute_lost" and v["runtime_state"] == "unresponsive"
    assert v["lease_expired"] is True  # lease released immediately rather than renewed for a dead child
    assert any(e["event"] == "compute_exited" and e["exitcode"] == 9 for e in v["operation"]["diagnostic_log"])
    # supervisor silent (no compute exit recorded) -> plain unresponsive
    conn.execute("UPDATE observation_replays SET supervisor = supervisor - 'compute_exit' WHERE replay_id = %s",
                 (rid,))
    assert api.get(f"/api/observations/{rid}").json()["operation"]["health"] == "unresponsive"
    conn.execute("UPDATE observation_replays SET supervisor = supervisor || %s WHERE replay_id = %s",
                 (Jsonb({"compute_exit": {"generation": 1, "exitcode": 9}}), rid))

    # actual fenced reclaim: RECOVERING only while the new generation is really restoring
    seen = []
    orig = ReplayJob._restore

    def observe_restore(self, core, reclaimed):
        pos = orig(self, core, reclaimed)
        seen.append(api.get(f"/api/observations/{rid}").json())
        return pos

    ReplayJob._restore = observe_restore
    try:
        inline(database_url, root, art, worker_id="observe:dead").run_once()  # same id, new generation
    finally:
        ReplayJob._restore = orig
    assert seen and seen[0]["runtime_state"] == "recovering" and seen[0]["operation"]["health"] == "recovering"
    assert seen[0]["operation"]["generation"] == 2
    r = row_of(conn, rid)
    assert r["status"] == "completed" and r["lease_generation"] == 2 and r["manifest"]["validation"]["passed"]
    assert "exited (code 9)" in r["recovery_log"][-1]["detail"]


def test_database_outage_is_disconnected_never_a_fake_stall_or_save(database_url, env, conn, tmp_path):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    w = inline(database_url, root, art, worker_id="observe:sup")
    _row, gen, _f, _r = w.claim()
    assert w.renew(rid, gen, None) == "ok"
    before = row_of(conn, rid)["heartbeat_at"]
    pid = w.conn.execute("SELECT pg_backend_pid() AS p").fetchone()["p"]
    conn.execute("SELECT pg_terminate_backend(%s)", (pid,))
    assert w.renew(rid, gen, None) == "disconnected"
    assert row_of(conn, rid)["heartbeat_at"] == before  # nothing was claimed as renewed/saved
    time.sleep(0.2)
    assert w.renew(rid, gen, None) == "ok"
    log = row_of(conn, rid)["diagnostic_log"]
    assert log[-1]["event"] == "db_outage" and "no progress was claimed" in log[-1]["detail"]
    # API-level: an unreachable database reports DISCONNECTED (503), not a stall
    bad = TestClient(create_app("postgresql://nobody:x@127.0.0.1:1/none", art, web_dist=tmp_path / "n",
                                data_root=root))
    h = bad.get("/api/health")
    assert h.status_code == 503 and h.json()["health"] == "disconnected"
    assert bad.get(f"/api/observations/{rid}").status_code == 503


# ---------------------------------------------------------------------------
# Fencing generations
# ---------------------------------------------------------------------------


def test_stale_generation_cannot_write_even_after_same_id_reacquisition(database_url, env, conn):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    w = inline(database_url, root, art, worker_id="observe:same")
    _r, g1, _f, _x = w.claim()
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))
    _r, g2, _f, _x = w.claim()  # the same worker id re-acquires: a NEW generation
    assert (g1, g2) == (1, 2)
    stale = ReplayJob(JobSpec(database_url, rid, "observe:same", g1, str(root), str(art)))
    with pytest.raises(LeaseLost):
        stale.enter_phase("PREPARING_SOURCE")  # phase/progress
    with pytest.raises(LeaseLost):
        stale.milestone("x", 1, 2, "u", force=True)
    with pytest.raises(LeaseLost):
        stale.control()
    stale._row_cache = {"attempt": 1}
    from algotrader.observe.contracts import ReplayStatus

    with pytest.raises(LeaseLost):
        stale._terminal(ReplayStatus.COMPLETED, None, None, {"state": "passed"})  # terminal status
    assert w.renew(rid, g1, None) == "lost"  # stale lease cannot be renewed
    # the stale attempt cannot persist a prepared config either
    with pytest.raises(LeaseLost):
        stale._prepare(row_of(conn, rid))
    r = row_of(conn, rid)
    assert r["status"] == "running" and r["lease_generation"] == 2 and r["config"] is None
    assert r["phase"] == "QUEUED"
    stale.close()
    # the current generation still completes normally and its artifacts live in g2
    current = ReplayJob(JobSpec(database_url, rid, "observe:same", g2, str(root), str(art)))
    current.run()
    r = row_of(conn, rid)
    assert r["status"] == "completed" and r["manifest"]["artifact_dir"] == "g2"


def test_stale_finalizer_cannot_overwrite_published_artifacts(database_url, env, conn):
    api, root, art, ds = env
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    inline(database_url, root, art).run_once()
    r = row_of(conn, rid)
    gdir = art / "observations" / rid / r["manifest"]["artifact_dir"]
    before = {p.name: p.read_bytes() for p in gdir.iterdir()}
    # an old generation finishing late publishes only into its own g<old> directory and is fenced in the DB
    from algotrader.observe.artifacts import publish_replay_artifacts
    from algotrader.observe.contracts import ReplayStatus

    old = dict(r)
    pub, _s, _e = publish_replay_artifacts(art, old, ReplayStatus.COMPLETED, None, datetime.now(UTC), [], 0,
                                           r["manifest"]["final_content_digest"], None, generation=0)
    assert pub.directory.name == "g0" and pub.directory != gdir
    assert {p.name: p.read_bytes() for p in gdir.iterdir()} == before
    assert row_of(conn, rid)["manifest"]["artifact_dir"] == r["manifest"]["artifact_dir"]
    assert api.get(f"/api/observations/{rid}/files/deliveries.jsonl").content == before["deliveries.jsonl"]


# ---------------------------------------------------------------------------
# Cancel during validation; diagnostic exports
# ---------------------------------------------------------------------------


def test_cancel_during_validation_at_full_cursor_is_incomplete_not_pass(database_url, env, conn):
    api, root, art, ds = env
    rid = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0}).json()[
        "replay_id"]
    w = inline(database_url, root, art, progress_interval=0.02, faults={"VALIDATING_cpu_per_unit": 0.05})
    t = in_thread(w.run_once)
    wait_until(lambda: row_of(conn, rid)["phase"] == "VALIDATING", timeout=60)
    v = api.get(f"/api/observations/{rid}").json()
    assert v["progress"]["applied_events"] == v["progress"]["total_events"]  # replay cursor is 100%
    assert v["status"] == "running" and v["runtime_state"] == "finishing"  # ... but NOT completed
    assert v["operation"]["assurance"]["state"] == "incomplete"
    assert v["operation"]["controls"]["pause"]["enabled"] is False and v["operation"]["controls"]["cancel"]["enabled"]
    assert api.post(f"/api/observations/{rid}/pause").status_code == 409
    snap = api.get(f"/api/observations/{rid}/report.json").json()
    assert snap["snapshot"] and snap["coverage"]["fraction"] == 1.0 and snap["assurance"]["state"] == "incomplete"
    t0 = time.perf_counter()
    assert api.post(f"/api/observations/{rid}/cancel").status_code == 200
    t.join(60)
    took = time.perf_counter() - t0
    r = row_of(conn, rid)
    m = r["manifest"]
    assert r["status"] == "cancelled" and "during VALIDATING" in r["error"]
    assert m["validation"]["outcome"] == "incomplete" and m["validation"]["passed"] is False
    assert any(c["name"] == "validation_completed" and not c["passed"] for c in m["validation"]["checks"])
    assert r["cursor"] == r["total_events"] and m["applied_events"] == m["total_events"]
    assert r["assurance"]["state"] == "incomplete"
    assert "final_snapshot.json" not in {a["name"] for a in m["artifacts"]}
    rederived = m["operational_metrics"]["validation_deliveries_rederived"]
    assert rederived < m["total_events"]  # did not finish a full reference replay
    assert took < 5.0, took
    print(f"cancel during VALIDATING applied in {took:.2f} s ({rederived}/{m['total_events']} deliveries re-derived)")


def test_evaluation_reports_in_every_state(database_url, conn, tmp_path, plan_file):  # noqa: F811
    from test_corpus import corpus_worker

    from algotrader.corpus import job as cj
    from algotrader.corpus.plan import load_plan

    root, art = tmp_path / "data", tmp_path / "art"
    cj.create_job(conn, load_plan(), "test-chunk")
    corpus_worker(database_url, root, FakeOkx()).run_once()
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    # queued snapshot
    eid = api.post("/api/evaluations", json={"chunk_id": "test-chunk", "speed": 0}).json()["evaluation_id"]
    q = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert q["status"] == "queued" and q["conclusion"]["verdict"] == "IN_PROGRESS_SNAPSHOT" and q["captured_at"]
    # report generation / publication failure -> failed run WITHOUT manifest, still exportable
    inline(database_url, root, art, faults={"publish_error": 1}).run_once()
    f = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert f["status"] == "failed" and "publication failed" in f["stopped_at"]["reason"]
    assert f["validation"]["ran"] is False and f["operation"]["assurance"]["state"] == "incomplete"
    assert f["manifest_check"]["claimed"] is False and f["completion"] == "INCOMPLETE"
    md_text = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "OPERATIONAL_FAILURE" in md_text and "| Call count | UNAVAILABLE |" in md_text
    # terminal reports are deterministic; the operation section carries measured phase timings
    assert api.get(f"/api/evaluations/{eid}/report.md").text == md_text
    assert f["operation"]["phases"] and f["operation"]["counters"]


def test_progress_timeline_and_eta_rules():
    now = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
    hist = [ops.closed_entry("QUEUED", 1, 1, now - timedelta(seconds=100), now - timedelta(seconds=90), 0.0,
                             waiting=True),
            ops.closed_entry("REPLAYING", 1, 1, now - timedelta(seconds=90), now - timedelta(seconds=60), 30.0),
            # paused for 40 s (no span), then a resumed REPLAYING span is open
            ]
    tl = ops.timeline(hist, "REPLAYING", now - timedelta(seconds=20), True, now, ops.OBSERVATION_PHASES)
    rep = next(p for p in tl["phases"] if p["phase"] == "REPLAYING")
    assert rep["active_seconds"] == pytest.approx(50.0) and rep["spans"] == 1 and rep["state"] == "current"
    assert tl["active_seconds_total"] == pytest.approx(50.0)  # queue wait and the pause are excluded
    assert next(p for p in tl["phases"] if p["phase"] == "VALIDATING")["state"] == "pending"
    eta, basis = ops.phase_eta(60, 100, 10, 25.0, "events")
    assert eta == pytest.approx(20.0) and "later phases are not included" in basis
    assert ops.phase_eta(60, None, 10, 25.0, "events")[0] is None  # unknown total -> unknown, not a guess
    assert ops.phase_eta(11, 100, 10, 25.0, "events")[0] is None  # not enough observed progress


# ---------------------------------------------------------------------------
# Pre-upgrade (legacy) runs are preserved and suspended
# ---------------------------------------------------------------------------


def test_pre_upgrade_runs_are_suspended_read_only_and_exportable(empty_database_url, tmp_path):
    url = empty_database_url
    db.migrate(url, target=5)  # the pre-R1A schema with a WP-008-era nonterminal run
    root, art = tmp_path / "data", tmp_path / "art"
    ds = make_dataset(root)
    from algotrader.observe.control import build_config
    from algotrader.observe.sources import load_dataset

    cfg = json.loads(build_config("obs-legacy", load_dataset(root, ds)).model_dump_json())
    with psycopg.connect(url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        for rid, status in (("obs-legacy", "running"), ("obs-legacy-done", "completed")):
            c.execute(
                """INSERT INTO observation_replays (replay_id, status, source_kind, source_id, config, total_events,
                       lease_owner, lease_expires_at, heartbeat_at, attempt, started_at, manifest)
                   VALUES (%s, %s, 'dataset', %s, %s, 129600, %s, now() + interval '10 minutes', now(), 1, now(), %s)""",
                (rid, status, ds, Jsonb({**cfg, "replay_id": rid}), "observe:old-binary" if status == "running"
                 else None, None),
            )
            c.execute("""INSERT INTO observation_checkpoints (replay_id, cursor, info_time, snapshot_id,
                             snapshot_digest, snapshot_view) VALUES (%s, 129600, now(), 's', 'd', '{}')""", (rid,))
            c.execute("""INSERT INTO observation_deliveries (replay_id, seq, event_id, family, kind, available_time,
                             record) VALUES (%s, 0, 'e0', 'trade_bar_1m', 'bar_observation', now(), '{}')""", (rid,))
        before = c.execute("SELECT * FROM observation_replays WHERE replay_id = 'obs-legacy'").fetchone()
    # a revision-1 terminal manifest on disk for the completed legacy run (files directly in the replay dir)
    out = art / "observations" / "obs-legacy-done"
    out.mkdir(parents=True)
    (out / "deliveries.jsonl").write_bytes(b"{}\n")
    legacy_manifest = {"schema_revision": 1, "replay_id": "obs-legacy-done",
                       "artifacts": [{"name": "deliveries.jsonl", "sha256": "x", "bytes": 3, "lines": 1}],
                       "validation": {"passed": True, "checks": []}}
    (out / "manifest.json").write_text(json.dumps(legacy_manifest), encoding="utf-8")
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("UPDATE observation_replays SET manifest = %s WHERE replay_id = 'obs-legacy-done'",
                  (Jsonb(legacy_manifest),))

    db.migrate(url)  # the R1A upgrade
    with psycopg.connect(url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        after = c.execute("SELECT * FROM observation_replays WHERE replay_id = 'obs-legacy'").fetchone()
        done = c.execute("SELECT * FROM observation_replays WHERE replay_id = 'obs-legacy-done'").fetchone()
        assert c.execute("SELECT count(*) AS n FROM observation_deliveries").fetchone()["n"] == 2
        assert c.execute("SELECT cursor FROM observation_checkpoints WHERE replay_id = 'obs-legacy'").fetchone()[
            "cursor"] == 129600
    # historical execution facts unchanged; only the additive suspension annotation was added
    for k in ("status", "config", "total_events", "lease_owner", "lease_expires_at", "attempt", "manifest", "error",
              "finished_at", "recovery_log"):
        assert after[k] == before[k], k
    assert after["lifecycle_version"] == 1 and after["suspended_at"] is not None
    assert after["suspension"]["historical_status"] == "running"
    assert done["suspended_at"] is None  # terminal legacy runs need no suspension

    # never auto-claimed by the new workers, even though its old lease would later expire
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 hour'")
    assert ObservationWorker(url, root, art, worker_id="observe:new", isolate=False).run_once() is False
    api = TestClient(create_app(url, art, web_dist=tmp_path / "no-ui", data_root=root))
    v = api.get("/api/observations/obs-legacy").json()
    assert v["runtime_state"] == "suspended" and v["operation"]["health"] == "suspended"
    assert v["operation"]["suspension"]["historical_status"] == "running"
    assert all(not x["enabled"] for x in v["operation"]["controls"].values())
    for cmd in ("pause", "cancel", "resume", "step"):
        assert api.post(f"/api/observations/obs-legacy/{cmd}").status_code == 409
    rep = api.get("/api/observations/obs-legacy/report.json").json()
    assert rep["suspension"] and rep["assurance"]["state"] == "not_checked" and rep["manifest"]["claimed"] is False
    assert rep["coverage"]["committed_cursor"] == 129600 and "same local dataset" in rep["next_diagnostic"]
    assert "terminal validation" in rep["assurance"]["detail"]
    md_text = api.get("/api/observations/obs-legacy/report.md").text
    assert "Suspension" in md_text and "129,600/129,600" in md_text
    # the legacy terminal manifest is verified where claimed, and its revision-1 files remain served
    rep = api.get("/api/observations/obs-legacy-done/report.json").json()
    assert rep["manifest"]["claimed"] and rep["manifest"]["manifest_file_present"]
    assert rep["manifest"]["manifest_file_matches_database"] and rep["manifest"]["artifacts"][0]["size_matches"]
    assert api.get("/api/observations/obs-legacy-done/files/deliveries.jsonl").status_code == 200
    assert api.get("/api/health").json()["observation_workers"]["suspended_legacy_replays"] == 1


# ---------------------------------------------------------------------------
# Corpus: shared semantics + generation fencing
# ---------------------------------------------------------------------------


def test_corpus_stale_generation_cannot_bind_or_finish(database_url, conn, tmp_path, plan_file):  # noqa: F811
    from test_corpus import corpus_worker

    from algotrader.corpus import job as cj
    from algotrader.corpus.plan import load_plan

    root = tmp_path / "data"
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    w = corpus_worker(database_url, root, FakeOkx(), worker_id="corpus:same")
    with w._conn() as c:
        row, _ = w.claim(c)
    g1 = w.generation
    conn.execute("UPDATE corpus_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s", (job_id,))
    w2 = corpus_worker(database_url, root, FakeOkx(), worker_id="corpus:same")
    with w2._conn() as c:
        w2.claim(c)
    assert (g1, w2.generation) == (1, 2)
    # the stale owner (same id, generation 1) finishes acquisition but cannot bind or set a terminal status
    with w._conn() as c:
        w.process(c, {**row, "lease_generation": g1})
    r = conn.execute("SELECT * FROM corpus_jobs WHERE job_id = %s", (job_id,)).fetchone()
    assert r["status"] == "running" and r["lease_generation"] == 2
    assert conn.execute("SELECT count(*) AS n FROM corpus_chunks").fetchone()["n"] == 0
    # the current generation completes and binds with its generation recorded; reuse stays network-free
    with w2._conn() as c:
        w2.process(c, conn.execute("SELECT * FROM corpus_jobs WHERE job_id = %s", (job_id,)).fetchone())
    b = conn.execute("SELECT * FROM corpus_chunks").fetchone()
    assert b["bound_generation"] == 2 and b["bound_by_job"] == job_id
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=root))
    view = api.get(f"/api/corpus/jobs/{job_id}").json()["operation"]
    assert view["status"] == "completed" and view["assurance"]["state"] == "passed" and view["generation"] == 2
    phases = {p["phase"] for p in view["timeline"]["phases"] if p["spans"]}
    # Either the stale owner finished its download before noticing the lost lease (the current generation then
    # verifies and adopts that finalized immutable dataset locally) or its fenced heartbeat saw the loss and it
    # aborted at a page boundary (the current generation downloads itself). The stale attempt's phase history and
    # writes are fenced out in both cases.
    outcome = conn.execute("SELECT outcome FROM corpus_jobs WHERE job_id = %s", (job_id,)).fetchone()["outcome"]
    assert outcome in ("adopted_local_dataset", "acquired", "acquired_identical_existing")
    assert {"QUEUED", "PREPARING_SOURCE", "VERIFYING_SOURCE", "BINDING"} <= phases
    assert ("DOWNLOADING" in phases) == outcome.startswith("acquired")
    rep = api.get(f"/api/corpus/jobs/{job_id}/report.json").json()
    assert rep["snapshot"] is False and rep["captured_at"] is None and rep["dataset_id"] == b["dataset_id"]
    fake = FakeOkx()
    job2 = cj.create_job(conn, load_plan(), "test-chunk")
    corpus_worker(database_url, root, fake).run_once()
    assert fake.calls == [] and conn.execute("SELECT outcome FROM corpus_jobs WHERE job_id = %s",
                                              (job2,)).fetchone()["outcome"] == "reused_binding"
