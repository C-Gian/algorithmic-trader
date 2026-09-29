"""Durable worker: persistence, idempotency, recovery, cancellation, speed invariance."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from psycopg.types.json import Jsonb

from algotrader import db
from algotrader.contracts import FaultMode, RunConfig
from algotrader.engine import Engine
from algotrader.synthetic import build_fixture
from algotrader.worker import LeaseLost, SimulatedCrash, Worker, _AlreadyApplied, fetch_events

pytestmark = pytest.mark.db


def crash() -> None:
    raise SimulatedCrash()


def make_worker(url: str, root: Path, name: str, lease: float = 5.0, **kw) -> Worker:
    return Worker(url=url, worker_id=name, lease_seconds=lease, artifact_root=root, crash=crash, **kw)


def create_run(url: str, run_id: str, **cfg) -> None:
    config = RunConfig(**cfg)
    with db.connection(url) as c, c.transaction():
        c.execute(
            "INSERT INTO runs (run_id, status, config, total_steps) VALUES (%s, 'queued', %s, %s)",
            (run_id, Jsonb(config.model_dump(mode="json")), build_fixture().total_steps),
        )


def get_run(url: str, run_id: str) -> dict:
    with db.connection(url) as c:
        return c.execute("SELECT * FROM runs WHERE run_id = %s", (run_id,)).fetchone()


def events(url: str, run_id: str) -> list[dict]:
    with db.connection(url) as c:
        return fetch_events(c, run_id)


def expire_leases(url: str) -> None:
    with db.connection(url) as c, c.transaction():
        c.execute("UPDATE runs SET lease_expires_at = now() - interval '1 second' WHERE status = 'running'")


def test_worker_run_persists_identical_trace_and_artifacts(database_url, artifact_root, reference_trace):
    create_run(database_url, "r1", speed=0)
    w = make_worker(database_url, artifact_root, "w1")
    assert w.run_once()
    run = get_run(database_url, "r1")
    assert run["status"] == "completed" and run["attempt"] == 1 and run["lease_owner"] is None
    m = run["manifest"]
    assert (m["semantic_trace_hash"], m["event_count"]) == reference_trace
    assert m["validation"]["passed"] is True
    assert "DEMO" in m["labels"] and m["assumptions"]["funding"] == "NOT_MODELED"
    run_dir = artifact_root / "runs" / "r1"
    names = {a["name"] for a in m["artifacts"]}
    for required in ("events.parquet", "market_views.parquet", "decisions.parquet", "orders.parquet",
                     "fills.parquet", "account.parquet", "validation.json", "report.md"):
        assert required in names and (run_dir / required).is_file()
    on_disk = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["semantic_trace_hash"] == m["semantic_trace_hash"]


def test_speed_does_not_change_decisions(database_url, artifact_root, reference_trace):
    create_run(database_url, "fast", speed=0)
    create_run(database_url, "paced", speed=400)  # real pacing: 120 bars at 400 bars/s
    w = make_worker(database_url, artifact_root, "w1")
    assert w.run_once() and w.run_once()
    fast, paced = get_run(database_url, "fast"), get_run(database_url, "paced")
    assert fast["status"] == paced["status"] == "completed"
    assert fast["manifest"]["semantic_trace_hash"] == paced["manifest"]["semantic_trace_hash"] == reference_trace[0]


def test_slow_speed_with_fake_clock_is_invariant(database_url, artifact_root, reference_trace):
    slept: list[float] = []
    create_run(database_url, "slow", speed=0.5)  # 2 s per bar, fake sleep
    w = make_worker(database_url, artifact_root, "w1", sleep=slept.append)
    w.run_once()
    assert sum(slept) == pytest.approx(120 * 2.0)
    assert get_run(database_url, "slow")["manifest"]["semantic_trace_hash"] == reference_trace[0]


def test_crash_once_recovers_without_duplicate_accounting(database_url, artifact_root, reference_trace):
    create_run(database_url, "crash", speed=0, fault=FaultMode.CRASH_ONCE, fault_at_step=45)
    w1 = make_worker(database_url, artifact_root, "w1")
    with pytest.raises(SimulatedCrash):
        w1.run_once()
    w1.close()  # dead worker: its open transaction is gone, lease not released
    run = get_run(database_url, "crash")
    assert run["status"] == "running" and run["lease_owner"] == "w1"
    evs = events(database_url, "crash")
    assert max(e["step"] for e in evs) == 44  # step 45 was rolled back
    fills_before = [e for e in evs if e["kind"] == "fill"]

    w2 = make_worker(database_url, artifact_root, "w2")
    assert w2.claim() is None  # lease still valid: no double ownership
    expire_leases(database_url)
    assert w2.run_once()
    run = get_run(database_url, "crash")
    assert run["status"] == "completed" and run["attempt"] == 2
    log_events = [r["event"] for r in run["recovery_log"]]
    assert log_events == ["controlled_fault_injected", "lease_expired_reclaimed"]
    assert "resuming from committed checkpoint step 45" in run["recovery_log"][1]["detail"]
    evs = events(database_url, "crash")
    fill_ids = [e["payload"]["fill_id"] for e in evs if e["kind"] == "fill"]
    assert len(fill_ids) == len(set(fill_ids)) == 8
    assert fills_before == [e for e in evs if e["kind"] == "fill"][: len(fills_before)]
    assert run["manifest"]["semantic_trace_hash"] == reference_trace[0]
    assert run["manifest"]["validation"]["passed"]


def test_crash_always_fails_explicitly_after_max_attempts(database_url, artifact_root):
    create_run(database_url, "doomed", speed=0, fault=FaultMode.CRASH_ALWAYS, fault_at_step=10)
    for i in range(3):
        w = make_worker(database_url, artifact_root, f"w{i}")
        with pytest.raises(SimulatedCrash):
            w.run_once()
        w.close()
        expire_leases(database_url)
    make_worker(database_url, artifact_root, "w-final").run_once()
    run = get_run(database_url, "doomed")
    assert run["status"] == "failed"
    assert "interrupted on 3 consecutive attempts" in run["error"]
    assert "last committed step 10" in run["error"]
    assert run["manifest"]["status"] == "failed"
    assert (artifact_root / "runs" / "doomed" / "manifest.json").is_file()
    steps = [e["step"] for e in events(database_url, "doomed") if e["kind"] == "decision"]
    assert steps == list(range(10))  # no step duplicated across three attempts


def test_replaying_a_committed_step_is_a_noop(database_url, artifact_root):
    create_run(database_url, "idem", speed=0)
    w = make_worker(database_url, artifact_root, "w1")
    run, _ = w.claim()
    engine = Engine(build_fixture())
    s0 = engine.initial_state()
    s1, ev0 = engine.step(s0, engine.fixture.bars[0])
    w.commit_step("idem", 0, s1, ev0)
    s2, ev1 = engine.step(s1, engine.fixture.bars[1])
    w.commit_step("idem", 1, s2, ev1)
    n = len(events(database_url, "idem"))
    # a restarted worker holding stale in-memory state re-processes step 0 and step 1
    for step, state, evs in ((0, s1, ev0), (1, s2, ev1)):
        with pytest.raises(_AlreadyApplied):
            w.commit_step("idem", step, state, evs)
    assert len(events(database_url, "idem")) == n


def test_duplicate_fill_is_rejected_by_database(database_url, artifact_root):
    create_run(database_url, "dup", speed=0)
    with db.connection(database_url) as c, c.transaction():
        row = ("dup", 0, 0, "fill", "2026-01-01T00:00:00Z", Jsonb({"fill_id": "F-1"}))
        c.execute("INSERT INTO run_events VALUES (%s,%s,%s,%s,%s,%s)", row)
    with pytest.raises(Exception, match="run_events_fill_uniq"):
        with db.connection(database_url) as c, c.transaction():
            c.execute(
                "INSERT INTO run_events VALUES (%s,%s,%s,%s,%s,%s)",
                ("dup", 1, 0, "fill", "2026-01-01T00:00:00Z", Jsonb({"fill_id": "F-1"})),
            )


def test_stale_worker_is_fenced_out(database_url, artifact_root):
    create_run(database_url, "fence", speed=0)
    a = make_worker(database_url, artifact_root, "a")
    a.claim()
    expire_leases(database_url)
    b = make_worker(database_url, artifact_root, "b")
    b.claim()
    engine = Engine(build_fixture())
    s1, ev = engine.step(engine.initial_state(), engine.fixture.bars[0])
    with pytest.raises(LeaseLost):
        a.commit_step("fence", 0, s1, ev)
    b.commit_step("fence", 0, s1, ev)
    assert len(events(database_url, "fence")) == len(ev)


def test_cancel_mid_run_leaves_manifest_and_artifacts(database_url, artifact_root):
    create_run(database_url, "cxl", speed=1000)
    calls = {"n": 0}

    def sleep(_: float) -> None:
        calls["n"] += 1
        if calls["n"] == 20:
            with db.connection(database_url) as c, c.transaction():
                c.execute("UPDATE runs SET cancel_requested = true WHERE run_id = 'cxl'")

    make_worker(database_url, artifact_root, "w1", sleep=sleep).run_once()
    run = get_run(database_url, "cxl")
    assert run["status"] == "cancelled"
    m = run["manifest"]
    assert m["status"] == "cancelled" and 0 < m["steps_processed"] < 120
    assert m["validation"]["passed"]  # coverage is only required for completed runs
    assert (artifact_root / "runs" / "cxl" / "decisions.parquet").is_file()


def test_cancel_queued_run(database_url, artifact_root):
    create_run(database_url, "q", speed=0)
    with db.connection(database_url) as c, c.transaction():
        c.execute("UPDATE runs SET cancel_requested = true WHERE run_id = 'q'")
    make_worker(database_url, artifact_root, "w1").run_once()
    run = get_run(database_url, "q")
    assert run["status"] == "cancelled" and run["manifest"]["steps_processed"] == 0


def test_heartbeat_advances_during_paced_run(database_url, artifact_root):
    create_run(database_url, "hb", speed=20)
    w = make_worker(database_url, artifact_root, "w1")
    t0 = time.monotonic()
    heartbeats = []

    def sleep(s: float) -> None:
        time.sleep(0.001)
        if len(heartbeats) < 3:
            heartbeats.append(get_run(database_url, "hb")["heartbeat_at"])

    w.sleep = sleep
    w.run_once()
    assert time.monotonic() - t0 < 60
    assert heartbeats == sorted(heartbeats) and len(set(heartbeats)) > 1
