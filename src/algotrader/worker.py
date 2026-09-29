"""Durable run worker.

A run is owned by whichever worker holds its lease, never by a browser
request. Each engine step is committed atomically together with its events
and the checkpoint, fenced by the lease owner and a compare-and-set on the
checkpoint step. Re-processing a step after an interruption is therefore a
no-op and cannot duplicate fills or accounting events.

If a worker dies, its lease expires; the next worker reclaims the run,
records the recovery, and resumes from the last committed checkpoint. After
``max_attempts`` the run becomes ``failed`` with an explicit explanation.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from . import db
from .artifacts import write_run_artifacts
from .contracts import FaultMode, RunConfig, RunStatus
from .engine import Engine, EngineState, Event
from .synthetic import build_fixture

log = logging.getLogger("algotrader.worker")

FAULT_EXIT_CODE = 86


class SimulatedCrash(BaseException):
    """In-process stand-in for a hard worker death (used by tests)."""


class LeaseLost(Exception):
    pass


def default_artifact_root() -> Path:
    return Path(os.environ.get("ALGOTRADER_ARTIFACT_ROOT", "var/artifacts")).resolve()


def hard_crash() -> None:
    logging.shutdown()
    os._exit(FAULT_EXIT_CODE)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Worker:
    def __init__(
        self,
        url: str | None = None,
        worker_id: str | None = None,
        lease_seconds: float = 15.0,
        poll_interval: float = 0.5,
        artifact_root: Path | None = None,
        crash: Callable[[], None] = hard_crash,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.url = url or db.database_url()
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self.artifact_root = artifact_root or default_artifact_root()
        self.crash = crash
        self.sleep = sleep
        self._conn: psycopg.Connection | None = None

    # -- connection ---------------------------------------------------------

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = db.connect(self.url, autocommit=True)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- main loop ----------------------------------------------------------

    def run_forever(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        log.info("worker %s started", self.worker_id)
        while not should_stop():
            try:
                if not self.run_once():
                    self.sleep(self.poll_interval)
            except (psycopg.OperationalError, LeaseLost) as exc:
                log.warning("worker loop error: %s", exc)
                self.close()
                self.sleep(self.poll_interval)

    def run_once(self) -> bool:
        claim = self.claim()
        if claim is None:
            return False
        run, fail_reason = claim
        if run["cancel_requested"]:
            self.finalize(run["run_id"], RunStatus.CANCELLED, "cancelled by user before completion")
        elif fail_reason:
            self.finalize(run["run_id"], RunStatus.FAILED, fail_reason)
        else:
            self.process(run)
        return True

    # -- lease --------------------------------------------------------------

    def claim(self) -> tuple[dict[str, Any], str | None] | None:
        conn = self.conn
        with conn.transaction():
            run = conn.execute(
                """
                SELECT r.*, c.next_step AS ckpt_step
                FROM runs r LEFT JOIN run_checkpoints c USING (run_id)
                WHERE r.status = 'queued'
                   OR (r.status = 'running' AND r.lease_expires_at < now())
                ORDER BY r.created_at
                LIMIT 1
                FOR UPDATE OF r SKIP LOCKED
                """
            ).fetchone()
            if run is None:
                return None
            recovery_log = list(run["recovery_log"])
            attempt = run["attempt"] + 1
            fail_reason = None
            if run["status"] == RunStatus.RUNNING:
                resume = run["ckpt_step"] or 0
                recovery_log.append(
                    {
                        "at": _now(),
                        "attempt": attempt,
                        "event": "lease_expired_reclaimed",
                        "detail": (
                            f"worker {run['lease_owner']} stopped heartbeating "
                            f"(last heartbeat {run['heartbeat_at'].isoformat() if run['heartbeat_at'] else 'never'}); "
                            f"reclaimed by {self.worker_id}, resuming from committed checkpoint step {resume}"
                        ),
                    }
                )
                if attempt > run["max_attempts"]:
                    fail_reason = (
                        f"worker interrupted on {run['attempt']} consecutive attempts "
                        f"(max {run['max_attempts']}); last committed step {resume} of {run['total_steps']}. "
                        "Run marked failed; no further automatic recovery."
                    )
            conn.execute(
                """
                UPDATE runs SET status = 'running', lease_owner = %s,
                    lease_expires_at = now() + make_interval(secs => %s),
                    heartbeat_at = now(), attempt = %s,
                    started_at = coalesce(started_at, now()), recovery_log = %s
                WHERE run_id = %s
                """,
                (self.worker_id, self.lease_seconds, attempt, Jsonb(recovery_log), run["run_id"]),
            )
            run.update(status="running", attempt=attempt, lease_owner=self.worker_id, recovery_log=recovery_log)
        log.info("claimed %s attempt %s", run["run_id"], attempt)
        return run, fail_reason

    def heartbeat(self, run_id: str) -> bool:
        """Extend the lease. Returns cancel_requested. Raises LeaseLost if fenced out."""
        row = self.conn.execute(
            """
            UPDATE runs SET heartbeat_at = now(), lease_expires_at = now() + make_interval(secs => %s)
            WHERE run_id = %s AND lease_owner = %s AND status = 'running'
            RETURNING cancel_requested
            """,
            (self.lease_seconds, run_id, self.worker_id),
        ).fetchone()
        if row is None:
            raise LeaseLost(run_id)
        return row["cancel_requested"]

    # -- processing -----------------------------------------------------------

    def load_state(self, run_id: str, engine: Engine) -> EngineState:
        row = self.conn.execute("SELECT state FROM run_checkpoints WHERE run_id = %s", (run_id,)).fetchone()
        if row is None:
            return engine.initial_state()
        return EngineState.model_validate(row["state"])

    def commit_step(
        self,
        run_id: str,
        expected_step: int,
        new_state: EngineState,
        events: list[Event],
        before_commit: Callable[[], None] | None = None,
    ) -> bool:
        """Atomically journal one step. Returns cancel_requested.

        Raises ``_AlreadyApplied`` (writing nothing) when this step was already
        committed, e.g. when re-processing after an interruption.
        """
        conn = self.conn
        with conn.transaction():
            fence = conn.execute(
                """
                UPDATE runs SET heartbeat_at = now(), lease_expires_at = now() + make_interval(secs => %s)
                WHERE run_id = %s AND lease_owner = %s AND status = 'running'
                RETURNING cancel_requested
                """,
                (self.lease_seconds, run_id, self.worker_id),
            ).fetchone()
            if fence is None:
                raise LeaseLost(run_id)
            sim_time = events[-1].sim_time if events else None
            # Compare-and-set: only advance a checkpoint that is exactly at expected_step.
            cas_sql = (
                """
                INSERT INTO run_checkpoints (run_id, next_step, next_seq, state, sim_time)
                VALUES (%(run_id)s, %(next_step)s, %(next_seq)s, %(state)s, %(sim_time)s)
                ON CONFLICT (run_id) DO NOTHING
                """
                if expected_step == 0
                else """
                UPDATE run_checkpoints SET next_step = %(next_step)s, next_seq = %(next_seq)s,
                    state = %(state)s, sim_time = %(sim_time)s, updated_at = now()
                WHERE run_id = %(run_id)s AND next_step = %(expected)s
                """
            )
            cas = conn.execute(
                cas_sql,
                {
                    "run_id": run_id,
                    "next_step": new_state.next_step,
                    "next_seq": new_state.next_seq,
                    "state": Jsonb(new_state.model_dump(mode="json")),
                    "sim_time": sim_time,
                    "expected": expected_step,
                },
            )
            if cas.rowcount == 0:
                # The checkpoint is not at expected_step: this step was already
                # committed. Roll back (nothing written) and let the caller reload.
                raise _AlreadyApplied(fence["cancel_requested"])
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO run_events (run_id, seq, step, kind, sim_time, payload) VALUES (%s, %s, %s, %s, %s, %s)",
                    [(run_id, e.seq, e.step, e.kind, e.sim_time, Jsonb(e.payload)) for e in events],
                )
            if before_commit is not None:
                before_commit()
        return fence["cancel_requested"]

    def _fault_hook(self, run: dict[str, Any], cfg: RunConfig, step: int) -> Callable[[], None] | None:
        """If a controlled fault is due at this step, record it and return the crash hook.

        The note is committed *before* the step transaction starts (the step
        transaction locks the run row). The hook then kills the worker with the
        step transaction still open, so PostgreSQL rolls the step back.
        """
        if cfg.fault == FaultMode.NONE or step != cfg.fault_at_step:
            return None
        if cfg.fault == FaultMode.CRASH_ONCE and run["attempt"] != 1:
            return None
        note = {
            "at": _now(),
            "attempt": run["attempt"],
            "event": "controlled_fault_injected",
            "detail": (
                f"DEMO fault '{cfg.fault}': worker {self.worker_id} terminated mid-step "
                f"{step} before commit; the uncommitted step is rolled back"
            ),
        }
        self.conn.execute(
            "UPDATE runs SET recovery_log = recovery_log || %s WHERE run_id = %s AND lease_owner = %s",
            (Jsonb([note]), run["run_id"], self.worker_id),
        )
        return self.crash

    def process(self, run: dict[str, Any]) -> None:
        run_id = run["run_id"]
        cfg = RunConfig.model_validate(run["config"])
        engine = Engine(build_fixture(cfg.fixture_id, cfg.seed))
        state = self.load_state(run_id, engine)
        total = engine.fixture.total_steps
        try:
            while state.next_step < total:
                step = state.next_step
                new_state, events = engine.step(state, engine.fixture.bars[step])
                try:
                    cancel = self.commit_step(run_id, step, new_state, events, self._fault_hook(run, cfg, step))
                    state = new_state
                except _AlreadyApplied as already:
                    log.warning("%s step %s already committed; reloading checkpoint", run_id, step)
                    state = self.load_state(run_id, engine)
                    if state.next_step <= step:
                        raise RuntimeError(f"checkpoint inconsistent at step {step}") from None
                    cancel = already.cancel_requested
                if cancel or self._pace(run_id, cfg.speed):
                    self.finalize(run_id, RunStatus.CANCELLED, "cancelled by user before completion")
                    return
            self.finalize(run_id, RunStatus.COMPLETED, None)
        except LeaseLost:
            log.error("%s: lease lost; another worker owns the run now", run_id)
        except Exception as exc:  # deterministic engine/persistence error -> explicit failure
            log.exception("%s failed", run_id)
            self.finalize(run_id, RunStatus.FAILED, f"{type(exc).__name__}: {exc}")

    def _pace(self, run_id: str, speed: float) -> bool:
        """Sleep according to replay speed. Pacing never affects decisions."""
        if speed <= 0:
            return False
        remaining = 1.0 / speed
        while remaining > 0:
            chunk = min(remaining, 0.25)
            self.sleep(chunk)
            remaining -= chunk
            if self.heartbeat(run_id):
                return True
        return False

    # -- completion -------------------------------------------------------------

    def finalize(self, run_id: str, status: RunStatus, error: str | None) -> None:
        conn = self.conn
        run = conn.execute("SELECT * FROM runs WHERE run_id = %s", (run_id,)).fetchone()
        events = fetch_events(conn, run_id)
        cfg = RunConfig.model_validate(run["config"])
        engine = Engine(build_fixture(cfg.fixture_id, cfg.seed))
        finished_at = datetime.now(UTC)
        manifest = write_run_artifacts(
            self.artifact_root, run, status, error, finished_at, events, engine
        )
        with conn.transaction():
            updated = conn.execute(
                """
                UPDATE runs SET status = %s, error = %s, finished_at = %s, manifest = %s,
                    lease_owner = NULL, lease_expires_at = NULL, heartbeat_at = now()
                WHERE run_id = %s AND lease_owner = %s AND status = 'running'
                """,
                (status.value, error, finished_at, Jsonb(json.loads(manifest.model_dump_json())), run_id, self.worker_id),
            )
            if updated.rowcount == 0:
                raise LeaseLost(run_id)
        log.info("%s finalized as %s", run_id, status)


class _AlreadyApplied(Exception):
    def __init__(self, cancel_requested: bool) -> None:
        super().__init__("step already applied")
        self.cancel_requested = cancel_requested


def fetch_events(conn: psycopg.Connection, run_id: str, kind: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT seq, step, kind, sim_time, payload FROM run_events WHERE run_id = %s"
    params: list[Any] = [run_id]
    if kind:
        sql += " AND kind = %s"
        params.append(kind)
    rows = conn.execute(sql + " ORDER BY seq", params).fetchall()
    return [
        {
            "seq": r["seq"],
            "step": r["step"],
            "kind": r["kind"],
            "sim_time": r["sim_time"].astimezone(UTC).isoformat(),
            "payload": r["payload"],
        }
        for r in rows
    ]
