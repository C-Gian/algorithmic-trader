"""Durable real-market observation-replay worker: supervisor + fenced compute (``observe:`` worker ids).

WP-008-R1A splits the worker in two:

* the **supervisor** (this class) is lightweight: it claims a replay under a new monotonic
  ``lease_generation``, starts the compute attempt and renews the lease about every two
  seconds *only while the compute process exists*. It has its own database connection and
  runs in its own process, so CPU-bound replay/validation work can never starve the
  heartbeat (no shared GIL). Heartbeat is liveness, not progress.
* the **compute job** (``job.ReplayJob``) does preparation, replay, finalization,
  validation and publication, emitting compute milestones; every write it makes is fenced
  by ``(lease_owner, lease_generation, status = 'running')``.

If the compute process dies, the supervisor stops renewing, records the exit (fenced) and
lets the lease lapse immediately, so the run shows "compute lost - awaiting recovery"
until a new fenced attempt actually restores it. A database outage seen by the supervisor
is recorded once the database is reachable again; nothing is claimed as saved during it.

Pre-upgrade (lifecycle v1) replays and suspended replays are never claimed.
This path never imports the synthetic trader, risk, account or engine modules.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .. import db, ops
from .job import JobSpec, LeaseLost, ReplayJob, SimulatedCrash, compute_main  # noqa: F401 - re-exported

log = logging.getLogger("algotrader.observe")
WORKER_PREFIX = "observe:"
DEFAULT_LEASE_SECONDS = 30.0
DEFAULT_HEARTBEAT_SECONDS = 2.0
DB_TIMEOUT = "5s"  # bound every supervisor statement


def _now() -> str:
    return datetime.now(UTC).isoformat()


def default_artifact_root() -> Path:
    return Path(os.environ.get("ALGOTRADER_ARTIFACT_ROOT", "var/artifacts")).resolve()


class ObservationWorker:
    def __init__(
        self,
        url: str | None = None,
        data_root: Path | None = None,
        artifact_root: Path | None = None,
        worker_id: str | None = None,
        lease_seconds: float = DEFAULT_LEASE_SECONDS,
        poll_interval: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
        before_commit: Callable[[str, int], None] | None = None,
        after_commit: Callable[[str, int], None] | None = None,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_SECONDS,
        isolate: bool = True,
        stall_limit: float | None = None,
        progress_interval: float = 0.5,
        faults: dict[str, float] | None = None,
    ) -> None:
        from ..marketdata.dataset import default_data_root

        self.url = url or db.database_url()
        self.data_root = data_root or default_data_root()
        self.artifact_root = artifact_root or default_artifact_root()
        self.worker_id = worker_id or f"{WORKER_PREFIX}{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        if not self.worker_id.startswith(WORKER_PREFIX):
            raise ValueError(f"observation worker ids must start with {WORKER_PREFIX!r}")
        if isolate and (before_commit or after_commit):
            raise ValueError("in-process commit hooks require isolate=False")
        self.lease_seconds = lease_seconds
        self.heartbeat_interval = heartbeat_interval
        self.poll_interval = poll_interval
        self.sleep = sleep
        self.before_commit = before_commit  # test hooks (crash injection, inline only)
        self.after_commit = after_commit
        self.isolate = isolate
        self.stall_limit = stall_limit
        self.progress_interval = progress_interval
        self.faults = dict(faults or {})
        self._conn: psycopg.Connection | None = None
        self._beat_at = 0.0
        self._outage_since: float | None = None
        self._outage_started_at: str | None = None

    # -- connection / health ---------------------------------------------------

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = db.connect(self.url, autocommit=True, connect_timeout=5,
                                    options=f"-c statement_timeout={DB_TIMEOUT}")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def beat(self, current: str | None, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._beat_at < 1.0:
            return
        self._beat_at = now
        self.conn.execute(
            """INSERT INTO workers (worker_id, host, pid, current_run) VALUES (%s, %s, %s, %s)
               ON CONFLICT (worker_id) DO UPDATE SET heartbeat_at = now(), current_run = excluded.current_run""",
            (self.worker_id, socket.gethostname(), os.getpid(), current),
        )

    # -- main loop -------------------------------------------------------------

    def run_forever(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        log.info("observation supervisor %s started (data root %s, lease %ss, heartbeat %ss, isolate=%s)",
                 self.worker_id, self.data_root, self.lease_seconds, self.heartbeat_interval, self.isolate)
        while not should_stop():
            try:
                self.beat(None)
                if not self.run_once():
                    self.sleep(self.poll_interval)
            except (psycopg.OperationalError, LeaseLost) as exc:
                log.warning("observation worker loop error: %s", exc)
                self.close()
                self.sleep(self.poll_interval)

    def run_once(self) -> bool:
        claim = self.claim()
        if claim is None:
            return False
        row, generation, finalize, reason = claim
        spec = JobSpec(url=self.url, replay_id=row["replay_id"], worker_id=self.worker_id, generation=generation,
                       data_root=str(self.data_root), artifact_root=str(self.artifact_root),
                       progress_interval=self.progress_interval, stall_limit=self.stall_limit,
                       finalize=finalize, finalize_error=reason, faults=self.faults)
        if self.isolate:
            self._supervise_process(spec)
        else:
            self._supervise_inline(spec)
        return True

    # -- lease -----------------------------------------------------------------

    def claim(self) -> tuple[dict[str, Any], int, str | None, str | None] | None:
        conn = self.conn
        with conn.transaction():
            row = conn.execute(
                """
                SELECT r.*, c.cursor AS ckpt_cursor
                FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id)
                WHERE r.lifecycle_version >= 2 AND r.suspended_at IS NULL AND (
                      (r.status = 'queued' AND (r.config IS NULL OR NOT r.paused OR r.step_budget > 0
                                                OR r.cancel_requested))
                   OR (r.status = 'paused' AND (NOT r.paused OR r.step_budget > 0 OR r.cancel_requested))
                   OR (r.status = 'running' AND r.lease_expires_at < now()))
                ORDER BY r.created_at
                LIMIT 1
                FOR UPDATE OF r SKIP LOCKED
                """
            ).fetchone()
            if row is None:
                return None
            generation = row["lease_generation"] + 1
            recovery_log = list(row["recovery_log"])
            history_add: list[dict[str, Any]] = []
            reclaimed = row["status"] == "running"
            attempt = row["attempt"] + 1 if reclaimed or row["attempt"] == 0 else row["attempt"]
            interruptions = row["interruptions"] + 1 if reclaimed else row["interruptions"]
            finalize, reason = None, None
            now = datetime.now(UTC)
            if row["phase"] is None and row["status"] == "queued":
                history_add.append(ops.closed_entry("QUEUED", generation, attempt, row["created_at"], now, 0.0,
                                                    waiting=True))
            if reclaimed:
                resume = row["ckpt_cursor"] or 0
                exit_info = (row["supervisor"] or {}).get("compute_exit") or {}
                cause = (f"compute process of generation {row['lease_generation']} exited "
                         f"(code {exit_info.get('exitcode')})" if exit_info.get("generation") == row["lease_generation"]
                         else f"worker {row['lease_owner']} stopped heartbeating (last heartbeat "
                              f"{row['heartbeat_at'].isoformat() if row['heartbeat_at'] else 'never'})")
                recovery_log.append({
                    "at": _now(), "attempt": attempt, "generation": generation, "event": "lease_expired_reclaimed",
                    "previous_generation": row["lease_generation"],
                    "detail": (f"{cause}; reclaimed by {self.worker_id} under fencing generation {generation}, "
                               f"resuming after committed feed cursor {resume}"),
                })
                if row["phase"] and row["phase_started_at"] is not None:
                    ended = row["heartbeat_at"] or now
                    history_add.append(ops.closed_entry(row["phase"], row["lease_generation"], row["attempt"],
                                                        row["phase_started_at"], max(ended, row["phase_started_at"]),
                                                        None, interrupted=True,
                                                        note="attempt interrupted; active time unknown"))
                if interruptions >= row["max_attempts"]:
                    finalize = "failed"
                    reason = (f"worker interrupted on {interruptions} consecutive attempts (max "
                              f"{row['max_attempts']}); last committed cursor {resume} of "
                              f"{row['total_events'] if row['total_events'] is not None else 'PENDING'}. "
                              "Replay marked failed; no further automatic recovery.")
            if finalize is None and row["cancel_requested"]:
                finalize, reason = "cancelled", "cancelled by user before completion"
            conn.execute(
                """
                UPDATE observation_replays SET status = 'running', lease_owner = %s, lease_generation = %s,
                    lease_expires_at = now() + make_interval(secs => %s), heartbeat_at = now(),
                    attempt = %s, interruptions = %s, started_at = coalesce(started_at, now()),
                    recovery_log = %s, throughput_since = now(), throughput_base = %s,
                    phase_history = phase_history || %s,
                    phase_started_at = CASE WHEN %s THEN NULL ELSE phase_started_at END,
                    phase = coalesce(phase, 'QUEUED'),
                    supervisor = supervisor || %s
                WHERE replay_id = %s
                """,
                (self.worker_id, generation, self.lease_seconds, attempt, interruptions, Jsonb(recovery_log),
                 row["ckpt_cursor"] or 0, Jsonb(history_add), reclaimed,
                 Jsonb({"worker_id": self.worker_id, "supervisor_pid": os.getpid(), "generation": generation,
                        "isolated_compute": self.isolate, "heartbeat_interval": self.heartbeat_interval,
                        "lease_seconds": self.lease_seconds, "claimed_at": _now(), "child_pid": None,
                        "environment": ops.environment()}),
                 row["replay_id"]),
            )
        log.info("claimed %s attempt %s generation %s", row["replay_id"], attempt, generation)
        return row, generation, finalize, reason

    def renew(self, replay_id: str, generation: int, child_pid: int | None) -> str:
        """Renew the fenced lease. Returns 'ok', 'released' (no longer running), 'lost' or 'disconnected'."""
        try:
            row = self.conn.execute(
                """
                UPDATE observation_replays SET heartbeat_at = now(),
                    lease_expires_at = now() + make_interval(secs => %s),
                    supervisor = supervisor || jsonb_build_object('child_pid', %s::int,
                                                                  'child_checked_at', now()::text)
                WHERE replay_id = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'
                RETURNING 1
                """,
                (self.lease_seconds, child_pid, replay_id, self.worker_id, generation),
            ).fetchone()
            if row is None:
                cur = self.conn.execute("SELECT status, lease_generation FROM observation_replays WHERE replay_id = %s",
                                        (replay_id,)).fetchone()
                state = "lost" if cur is None or cur["lease_generation"] != generation else "released"
            else:
                state = "ok"
            self.beat(replay_id)
            if self._outage_since is not None:
                secs = time.monotonic() - self._outage_since
                self._note(replay_id, generation, {
                    "at": _now(), "event": "db_outage", "generation": generation, "since": self._outage_started_at,
                    "seconds": round(secs, 3),
                    "detail": ("the supervisor could not reach the database; the lease was not renewed and no "
                               "progress was claimed during the outage"),
                })
                self._outage_since = None
            return state
        except psycopg.OperationalError as exc:
            if self._outage_since is None:
                self._outage_since = time.monotonic()
                self._outage_started_at = _now()
                log.warning("%s: database unreachable from supervisor (%s)", replay_id, exc)
            self.close()
            return "disconnected"

    def _note(self, replay_id: str, generation: int, entry: dict[str, Any]) -> None:
        self.conn.execute(
            "UPDATE observation_replays SET diagnostic_log = diagnostic_log || %s "
            "WHERE replay_id = %s AND lease_generation = %s",
            (Jsonb([entry]), replay_id, generation),
        )

    def compute_exited(self, replay_id: str, generation: int, exitcode: int | None) -> None:
        """Fenced: record that the compute process died and let the lease lapse now (recovery may start)."""
        info = {"generation": generation, "exitcode": exitcode, "at": _now(), "worker_id": self.worker_id}
        try:
            self.conn.execute(
                """
                UPDATE observation_replays SET lease_expires_at = now(),
                    supervisor = supervisor || jsonb_build_object('compute_exit', %s::jsonb),
                    diagnostic_log = diagnostic_log || %s
                WHERE replay_id = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'
                """,
                (Jsonb(info), Jsonb([{**info, "event": "compute_exited",
                                      "detail": f"compute process ended with exit code {exitcode}; supervisor stopped "
                                                "renewing the lease; awaiting a new fenced attempt"}]),
                 replay_id, self.worker_id, generation),
            )
        except psycopg.OperationalError as exc:
            log.warning("%s: could not record compute exit (%s); the lease will lapse on its own", replay_id, exc)
            self.close()

    # -- supervision -------------------------------------------------------------

    def _supervise_process(self, spec: JobSpec) -> None:
        ctx = multiprocessing.get_context("spawn")
        proc = ctx.Process(target=compute_main, args=(spec,), name=f"observe-compute-{spec.replay_id}", daemon=True)
        proc.start()
        state = self.renew(spec.replay_id, spec.generation, proc.pid)
        while True:
            proc.join(self.heartbeat_interval)
            if not proc.is_alive():
                break
            state = self.renew(spec.replay_id, spec.generation, proc.pid)
            if state == "lost":
                log.error("%s: generation %s superseded; stopping stale compute process", spec.replay_id,
                          spec.generation)
                proc.terminate()
                proc.join(10)
                return
        if proc.exitcode not in (0, None):
            log.error("%s: compute process exited with %s", spec.replay_id, proc.exitcode)
            self.compute_exited(spec.replay_id, spec.generation, proc.exitcode)

    def _supervise_inline(self, spec: JobSpec) -> None:
        """Tests: compute in this thread, supervision in a helper thread with its own connection."""
        stop = threading.Event()
        helper = ObservationWorker(self.url, self.data_root, self.artifact_root, worker_id=self.worker_id,
                                   lease_seconds=self.lease_seconds, isolate=False)

        def beat() -> None:
            try:
                while not stop.wait(self.heartbeat_interval):
                    if helper.renew(spec.replay_id, spec.generation, None) == "lost":
                        return
            finally:
                helper.close()

        t = threading.Thread(target=beat, daemon=True, name=f"supervise-{spec.replay_id}")
        t.start()
        job = ReplayJob(spec, sleep=self.sleep, before_commit=self.before_commit, after_commit=self.after_commit)
        try:
            job.run()
        finally:
            stop.set()
            t.join(10)
