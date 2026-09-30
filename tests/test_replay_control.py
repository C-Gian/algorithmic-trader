"""Durable replay control (pause/resume/step/speed/cancel) and trace invariance.

Every operational path must produce the semantic trace of the pinned fixture
computed purely in-process (``reference_trace``) and exactly the same fills.
Control commands go through ``algotrader.control`` (the functions the API
uses); worker "sleeps" are fake so the tests are fast and deterministic.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from algotrader import control, db
from algotrader.contracts import EVENT_KIND_CONTRACTS, RunConfig
from algotrader.worker import SimulatedCrash, Worker, fetch_events

pytestmark = pytest.mark.db

TOTAL = 120
REFERENCE_FILLS = 8


def make_worker(url: str, root: Path, name: str, sleep: Callable[[float], None] = lambda s: None) -> Worker:
    def crash() -> None:
        raise SimulatedCrash()

    return Worker(url=url, worker_id=name, lease_seconds=5, artifact_root=root, crash=crash, sleep=sleep)


def new_run(url: str, run_id: str, speed: float = 1000, paused: bool = False) -> str:
    with db.connection(url) as c:
        return control.create_run(c, RunConfig(), speed=speed, paused=paused, run_id=run_id)


def cmd(url: str, fn, run_id: str, *args) -> None:
    with db.connection(url) as c:
        fn(c, run_id, *args)


def run_row(url: str, run_id: str) -> dict:
    with db.connection(url) as c:
        return c.execute(
            "SELECT r.*, coalesce(k.next_step, 0) AS steps_done FROM runs r "
            "LEFT JOIN run_checkpoints k USING (run_id) WHERE r.run_id = %s",
            (run_id,),
        ).fetchone()


def journal(url: str, run_id: str) -> list[dict]:
    with db.connection(url) as c:
        return fetch_events(c, run_id)


def expire_leases(url: str) -> None:
    with db.connection(url) as c, c.transaction():
        c.execute("UPDATE runs SET lease_expires_at = now() - interval '1 second' WHERE status = 'running'")


def on_sleep_call(n: int, action: Callable[[], None]) -> Callable[[float], None]:
    """A fake sleep that runs ``action`` on its n-th call (1-based)."""
    calls = {"n": 0}

    def sleep(_: float) -> None:
        calls["n"] += 1
        if calls["n"] == n:
            action()

    return sleep


def assert_reference(url: str, run_id: str, reference_trace) -> dict:
    run = run_row(url, run_id)
    assert run["status"] == "completed", run["error"]
    assert (run["manifest"]["semantic_trace_hash"], run["manifest"]["event_count"]) == reference_trace
    fills = [e["payload"]["fill_id"] for e in journal(url, run_id) if e["kind"] == "fill"]
    assert len(fills) == len(set(fills)) == REFERENCE_FILLS
    assert run["manifest"]["validation"]["passed"]
    return run


def test_pause_parks_run_and_makes_no_progress_until_resume(database_url, artifact_root, reference_trace):
    new_run(database_url, "p", speed=1000)  # one 1 ms sleep after every step
    pause = lambda: cmd(database_url, control.pause, "p")  # noqa: E731
    w = make_worker(database_url, artifact_root, "w1", sleep=on_sleep_call(30, pause))
    assert w.run_once()
    run = run_row(database_url, "p")
    # paused during the wait after step 29: the worker stops at the committed checkpoint
    assert (run["status"], run["paused"], run["steps_done"]) == ("paused", True, 30)
    assert run["lease_owner"] is None and run["manifest"] is None
    n_events = len(journal(database_url, "p"))

    for _ in range(3):  # paused runs are not claimable: no new semantic events
        assert make_worker(database_url, artifact_root, "idle").run_once() is False
    assert len(journal(database_url, "p")) == n_events
    assert run_row(database_url, "p")["steps_done"] == 30

    cmd(database_url, control.resume, "p")
    assert run_row(database_url, "p")["status"] == "queued"
    assert make_worker(database_url, artifact_root, "w2").run_once()
    run = assert_reference(database_url, "p", reference_trace)
    assert run["attempt"] == 1  # pause/resume is not a recovery attempt
    commands = [e["command"] for e in run["control_log"]]
    assert commands == ["start", "pause", "parked", "resume"]
    assert run["manifest"]["control_log"][-1]["command"] == "resume"


def test_step_advances_exactly_one_bar_and_stays_paused(database_url, artifact_root, reference_trace):
    new_run(database_url, "s", speed=1000, paused=True)
    assert make_worker(database_url, artifact_root, "w").run_once() is False  # paused before start
    assert journal(database_url, "s") == []
    for i in range(25):  # a meaningful interval of repeated single steps
        cmd(database_url, control.step, "s")
        assert make_worker(database_url, artifact_root, f"w{i}").run_once()
        run = run_row(database_url, "s")
        assert (run["status"], run["paused"], run["step_budget"], run["steps_done"]) == ("paused", True, 0, i + 1)
        steps = {e["step"] for e in journal(database_url, "s")}
        assert steps == set(range(i + 1))  # exactly one more input bar (several events)
    # three STEP commands grant exactly three bars
    for _ in range(3):
        cmd(database_url, control.step, "s")
    assert make_worker(database_url, artifact_root, "w-multi").run_once()
    assert run_row(database_url, "s")["steps_done"] == 28
    cmd(database_url, control.resume, "s")
    make_worker(database_url, artifact_root, "w-end").run_once()
    assert_reference(database_url, "s", reference_trace)


def test_step_emits_multiple_events_for_one_bar(database_url, artifact_root):
    new_run(database_url, "m", paused=True)
    cmd(database_url, control.step, "m")
    make_worker(database_url, artifact_root, "w").run_once()
    evs = journal(database_url, "m")
    assert {e["step"] for e in evs} == {0} and len(evs) > 3
    assert {e["kind"] for e in evs} <= set(EVENT_KIND_CONTRACTS)


def test_control_commands_are_validated(database_url, artifact_root):
    new_run(database_url, "v", speed=0)
    with pytest.raises(control.ControlRejected, match="only valid while paused"):
        cmd(database_url, control.step, "v")
    with pytest.raises(control.ControlRejected, match="not paused"):
        cmd(database_url, control.resume, "v")
    with pytest.raises(control.ControlRejected, match="speed"):
        cmd(database_url, control.set_speed, "v", 5000)
    with pytest.raises(control.RunNotFound):
        cmd(database_url, control.pause, "nope")
    cmd(database_url, control.pause, "v")
    cmd(database_url, control.pause, "v")  # idempotent
    assert make_worker(database_url, artifact_root, "w").run_once() is False
    for _ in range(TOTAL):
        cmd(database_url, control.step, "v")
    with pytest.raises(control.ControlRejected, match="no input bars left"):
        cmd(database_url, control.step, "v")
    cmd(database_url, control.resume, "v")
    make_worker(database_url, artifact_root, "w").run_once()
    for fn in (control.pause, control.resume, control.step, control.cancel):
        with pytest.raises(control.ControlRejected, match="already completed"):
            cmd(database_url, fn, "v")


def test_speed_changes_during_run_change_pacing_not_decisions(database_url, artifact_root, reference_trace):
    new_run(database_url, "sp", speed=0.5)  # 2 s per bar in 0.25 s chunks
    slept: list[float] = []
    changes = {3: 1000.0, 20: 2.0, 30: 0.0}

    def sleep(s: float) -> None:
        slept.append(s)
        if len(slept) in changes:
            cmd(database_url, control.set_speed, "sp", changes[len(slept)])

    make_worker(database_url, artifact_root, "w", sleep=sleep).run_once()
    run = assert_reference(database_url, "sp", reference_trace)
    assert slept[:3] == [0.25, 0.25, 0.25]  # speed 0.5 until the first change
    assert 0.001 in slept and 0.25 in slept[20:30]  # 1000 bars/s, then 2 bars/s
    assert len(slept) == 30  # speed 0 (max): no further sleeping
    assert run["speed"] == 0 and run["manifest"]["replay_control"]["speed"] == 0
    assert [e["speed"] for e in run["control_log"] if e["command"] == "speed"] == [1000.0, 2.0, 0.0]


def test_pause_wait_resume_with_slow_speed_is_invariant(database_url, artifact_root, reference_trace):
    new_run(database_url, "slow", speed=0.5)
    w = make_worker(database_url, artifact_root, "w", sleep=on_sleep_call(17, lambda: cmd(database_url, control.pause, "slow")))
    w.run_once()
    assert run_row(database_url, "slow")["status"] == "paused"
    cmd(database_url, control.set_speed, "slow", 0)  # speed change while paused
    cmd(database_url, control.resume, "slow")
    make_worker(database_url, artifact_root, "w2").run_once()
    assert_reference(database_url, "slow", reference_trace)


def test_cancel_while_paused(database_url, artifact_root):
    new_run(database_url, "cp")
    make_worker(database_url, artifact_root, "w", sleep=on_sleep_call(12, lambda: cmd(database_url, control.pause, "cp"))).run_once()
    assert run_row(database_url, "cp")["status"] == "paused"
    cmd(database_url, control.cancel, "cp")
    with pytest.raises(control.ControlRejected, match="cancellation already requested"):
        cmd(database_url, control.step, "cp")
    assert make_worker(database_url, artifact_root, "w2").run_once()
    run = run_row(database_url, "cp")
    assert run["status"] == "cancelled" and run["steps_done"] == 12
    assert run["manifest"]["status"] == "cancelled" and run["manifest"]["steps_processed"] == 12
    assert (artifact_root / "runs" / "cp" / "manifest.json").is_file()


def test_worker_restart_while_paused_preserves_control(database_url, artifact_root, reference_trace):
    new_run(database_url, "rp")
    w1 = make_worker(database_url, artifact_root, "w1", sleep=on_sleep_call(50, lambda: cmd(database_url, control.pause, "rp")))
    w1.run_once()
    w1.close()  # worker process gone; nothing to recover because the run was parked
    w2 = make_worker(database_url, artifact_root, "w2")
    assert w2.run_once() is False
    run = run_row(database_url, "rp")
    assert (run["status"], run["paused"], run["steps_done"], run["attempt"]) == ("paused", True, 50, 1)
    cmd(database_url, control.step, "rp")
    w2.run_once()
    assert run_row(database_url, "rp")["steps_done"] == 51
    cmd(database_url, control.resume, "rp")
    w2.run_once()
    assert assert_reference(database_url, "rp", reference_trace)["recovery_log"] == []


def test_unclean_restart_mid_run_recovers_same_trace(database_url, artifact_root, reference_trace):
    new_run(database_url, "kill")

    def die() -> None:
        raise SimulatedCrash()  # process killed between steps, lease still held

    w1 = make_worker(database_url, artifact_root, "w1", sleep=on_sleep_call(40, die))
    with pytest.raises(SimulatedCrash):
        w1.run_once()
    w1.close()
    fills_before = [e for e in journal(database_url, "kill") if e["kind"] == "fill"]
    expire_leases(database_url)
    make_worker(database_url, artifact_root, "w2").run_once()
    run = assert_reference(database_url, "kill", reference_trace)
    assert run["attempt"] == 2 and run["interruptions"] == 0
    assert [r["event"] for r in run["recovery_log"]] == ["lease_expired_reclaimed"]
    assert fills_before == [e for e in journal(database_url, "kill") if e["kind"] == "fill"][: len(fills_before)]


def test_repeated_restarts_with_progress_never_exhaust_attempts(database_url, artifact_root, reference_trace):
    """Ordinary restarts of a progressing run must not require manual repair."""
    new_run(database_url, "many")

    def die() -> None:
        raise SimulatedCrash()

    for i in range(5):  # more restarts than max_attempts (3), each after progress
        w = make_worker(database_url, artifact_root, f"w{i}", sleep=on_sleep_call(10, die))
        with pytest.raises(SimulatedCrash):
            w.run_once()
        w.close()
        expire_leases(database_url)
    make_worker(database_url, artifact_root, "w-final").run_once()
    run = assert_reference(database_url, "many", reference_trace)
    assert run["attempt"] == 6


def test_control_never_enters_semantic_journal(database_url, artifact_root, reference_trace):
    new_run(database_url, "iso", paused=True)
    for _ in range(5):
        cmd(database_url, control.step, "iso")
    cmd(database_url, control.set_speed, "iso", 7)
    make_worker(database_url, artifact_root, "w").run_once()
    cmd(database_url, control.set_speed, "iso", 0)
    cmd(database_url, control.resume, "iso")
    make_worker(database_url, artifact_root, "w").run_once()
    run = assert_reference(database_url, "iso", reference_trace)
    kinds = {e["kind"] for e in journal(database_url, "iso")}
    assert kinds == set(EVENT_KIND_CONTRACTS)
    assert "speed" not in run["config"] and "speed" not in run["manifest"]["config"]
    assert len(run["control_log"]) > 5


def test_migration_upgrades_v1_database(empty_database_url, artifact_root, reference_trace):
    """A WP-001 (schema v1) database with speed stored in the run config is upgraded in place."""
    from psycopg.types.json import Jsonb

    db.migrate(empty_database_url, target=1)
    with db.connection(empty_database_url) as c, c.transaction():
        c.execute(
            "INSERT INTO runs (run_id, status, config, total_steps) VALUES ('old', 'queued', %s, 120)",
            (Jsonb({"fixture_id": "synthetic-btc-perp-v1", "seed": 20260929, "speed": 0,
                    "fault": "none", "fault_at_step": 45}),),
        )
    db.migrate(empty_database_url)
    db.migrate(empty_database_url)  # idempotent
    run = run_row(empty_database_url, "old")
    assert "speed" not in run["config"] and run["speed"] == 0 and run["paused"] is False
    with db.connection(empty_database_url) as c:
        versions = [r["version"] for r in c.execute("SELECT version FROM schema_migrations ORDER BY 1")]
    assert versions == list(range(1, db.SCHEMA_VERSION + 1))
    make_worker(empty_database_url, artifact_root, "w").run_once()
    assert_reference(empty_database_url, "old", reference_trace)
