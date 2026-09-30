"""Durable real-market observation-replay worker (``observe:`` worker ids).

A replay is owned by whichever observation worker holds its lease - never by a
browser request. Every step commits, in one PostgreSQL transaction fenced by the
lease owner:

* the committed cursor advanced by exactly one with a compare-and-set
  (``cursor = k`` -> ``k + 1``), plus the snapshot digest/view it produced;
* the append-only delivery record, keyed by (replay, seq) and (replay, event_id).

The observable state itself is never trusted from storage: on every claim it is
rebuilt as the pure prefix ``apply_all(initial, feed.events[:cursor])`` and its
snapshot digest must equal the digest persisted with that cursor, otherwise the
replay fails explicitly (recovery would not be safe). A crash before commit
rolls the step back; a crash after commit is a no-op on retry (the CAS fails and
the worker reloads). After ``max_attempts`` consecutive interruptions without a
committed delivery the replay fails with an explanation.

This path never imports the synthetic trader, risk, account or engine modules
and never writes ``runs``/``run_events`` rows.
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

from .. import db
from ..feed.ordering import FeedError
from .artifacts import write_replay_artifacts
from .contracts import DeliveryRecord, ObservationReplayConfig, ReplayStatus
from .core import Position, ReplayCore, snapshot_view
from .sources import LoadedSource, SourceRejected, feed_identity, load_source

log = logging.getLogger("algotrader.observe")
WORKER_PREFIX = "observe:"
_CONTROL_COLUMNS = "cancel_requested, paused, step_budget, speed"


class SimulatedCrash(BaseException):
    """In-process stand-in for a hard worker death (tests)."""


class LeaseLost(Exception):
    pass


class _AlreadyApplied(Exception):
    def __init__(self, control: dict[str, Any]) -> None:
        super().__init__("delivery already committed")
        self.control = control


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
        lease_seconds: float = 10.0,
        poll_interval: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
        before_commit: Callable[[str, int], None] | None = None,
        after_commit: Callable[[str, int], None] | None = None,
    ) -> None:
        from ..marketdata.dataset import default_data_root

        self.url = url or db.database_url()
        self.data_root = data_root or default_data_root()
        self.artifact_root = artifact_root or default_artifact_root()
        self.worker_id = worker_id or f"{WORKER_PREFIX}{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        if not self.worker_id.startswith(WORKER_PREFIX):
            raise ValueError(f"observation worker ids must start with {WORKER_PREFIX!r}")
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self.sleep = sleep
        self.before_commit = before_commit  # test hooks (crash injection)
        self.after_commit = after_commit
        self._conn: psycopg.Connection | None = None
        self._beat_at = 0.0

    # -- connection / health ---------------------------------------------------

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = db.connect(self.url, autocommit=True)
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
        log.info("observation worker %s started (data root %s)", self.worker_id, self.data_root)
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
        row, fail_reason = claim
        if row["cancel_requested"]:
            self.finalize(row["replay_id"], ReplayStatus.CANCELLED, "cancelled by user before completion")
        elif fail_reason:
            self.finalize(row["replay_id"], ReplayStatus.FAILED, fail_reason)
        else:
            self.process(row)
        return True

    # -- lease -----------------------------------------------------------------

    def claim(self) -> tuple[dict[str, Any], str | None] | None:
        conn = self.conn
        with conn.transaction():
            row = conn.execute(
                """
                SELECT r.*, c.cursor AS ckpt_cursor
                FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id)
                WHERE (r.status IN ('queued', 'paused') AND (NOT r.paused OR r.step_budget > 0 OR r.cancel_requested))
                   OR (r.status = 'running' AND r.lease_expires_at < now())
                ORDER BY r.created_at
                LIMIT 1
                FOR UPDATE OF r SKIP LOCKED
                """
            ).fetchone()
            if row is None:
                return None
            recovery_log = list(row["recovery_log"])
            reclaimed = row["status"] == ReplayStatus.RUNNING
            attempt = row["attempt"] + 1 if reclaimed or row["attempt"] == 0 else row["attempt"]
            interruptions = row["interruptions"] + 1 if reclaimed else row["interruptions"]
            fail_reason = None
            if reclaimed:
                resume = row["ckpt_cursor"] or 0
                recovery_log.append({
                    "at": _now(), "attempt": attempt, "event": "lease_expired_reclaimed",
                    "detail": (f"worker {row['lease_owner']} stopped heartbeating (last heartbeat "
                               f"{row['heartbeat_at'].isoformat() if row['heartbeat_at'] else 'never'}); reclaimed "
                               f"by {self.worker_id}, resuming after committed feed cursor {resume}"),
                })
                if interruptions >= row["max_attempts"]:
                    fail_reason = (f"worker interrupted on {interruptions} consecutive attempts (max "
                                   f"{row['max_attempts']}); last committed cursor {resume} of {row['total_events']}. "
                                   "Replay marked failed; no further automatic recovery.")
            conn.execute(
                """
                UPDATE observation_replays SET status = 'running', lease_owner = %s,
                    lease_expires_at = now() + make_interval(secs => %s), heartbeat_at = now(),
                    attempt = %s, interruptions = %s, started_at = coalesce(started_at, now()),
                    recovery_log = %s, throughput_since = now(), throughput_base = %s
                WHERE replay_id = %s
                """,
                (self.worker_id, self.lease_seconds, attempt, interruptions, Jsonb(recovery_log),
                 row["ckpt_cursor"] or 0, row["replay_id"]),
            )
            row.update(status="running", attempt=attempt, lease_owner=self.worker_id, recovery_log=recovery_log)
        log.info("claimed %s attempt %s", row["replay_id"], attempt)
        return row, fail_reason

    def control(self, replay_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            f"""
            UPDATE observation_replays SET heartbeat_at = now(), lease_expires_at = now() + make_interval(secs => %s)
            WHERE replay_id = %s AND lease_owner = %s AND status = 'running'
            RETURNING {_CONTROL_COLUMNS}
            """,
            (self.lease_seconds, replay_id, self.worker_id),
        ).fetchone()
        if row is None:
            raise LeaseLost(replay_id)
        self.beat(replay_id)
        return row

    def park(self, replay_id: str, cursor: int) -> bool:
        note = {"at": _now(), "command": "parked", "at_cursor": cursor, "worker": self.worker_id}
        parked = self.conn.execute(
            """
            UPDATE observation_replays SET status = 'paused', lease_owner = NULL, lease_expires_at = NULL,
                heartbeat_at = now(), control_log = control_log || %s
            WHERE replay_id = %s AND lease_owner = %s AND status = 'running'
              AND paused AND step_budget = 0 AND NOT cancel_requested
            """,
            (Jsonb([note]), replay_id, self.worker_id),
        ).rowcount
        return bool(parked)

    # -- checkpoint ------------------------------------------------------------

    def checkpoint(self, replay_id: str) -> dict[str, Any] | None:
        return self.conn.execute(
            "SELECT cursor, snapshot_digest FROM observation_checkpoints WHERE replay_id = %s", (replay_id,)
        ).fetchone()

    def _restore(self, replay_id: str, core: ReplayCore) -> Position:
        """Rebuild the state as the pure feed prefix at the committed cursor and check its digest."""
        ck = self.checkpoint(replay_id)
        if ck is None:
            pos = core.at(0)
            self.conn.execute(
                """INSERT INTO observation_checkpoints
                       (replay_id, cursor, info_time, last_event_id, snapshot_id, snapshot_digest, snapshot_view)
                   VALUES (%s, 0, %s, NULL, %s, %s, %s) ON CONFLICT (replay_id) DO NOTHING""",
                (replay_id, pos.snapshot.as_of, pos.snapshot.snapshot_id, pos.snapshot.content_digest,
                 Jsonb(snapshot_view(pos.snapshot))),
            )
            ck = self.checkpoint(replay_id)
        pos = core.at(ck["cursor"])
        if pos.snapshot.content_digest != ck["snapshot_digest"]:
            raise _UnsafeRecovery(f"committed cursor {ck['cursor']}: persisted snapshot digest "
                                  f"{ck['snapshot_digest'][:16]} differs from the pure feed prefix "
                                  f"{pos.snapshot.content_digest[:16]}; recovery is not safe")
        return pos

    def commit(self, replay_id: str, before: Position, after: Position, rec: DeliveryRecord,
               payload: dict[str, Any], consume_step: bool) -> dict[str, Any]:
        conn = self.conn
        with conn.transaction():
            fence = conn.execute(
                f"""
                UPDATE observation_replays SET heartbeat_at = now(),
                    lease_expires_at = now() + make_interval(secs => %s), interruptions = 0,
                    step_budget = CASE WHEN %s THEN greatest(step_budget - 1, 0) ELSE step_budget END
                WHERE replay_id = %s AND lease_owner = %s AND status = 'running'
                RETURNING {_CONTROL_COLUMNS}
                """,
                (self.lease_seconds, consume_step, replay_id, self.worker_id),
            ).fetchone()
            if fence is None:
                raise LeaseLost(replay_id)
            cas = conn.execute(
                """
                UPDATE observation_checkpoints SET cursor = %s, info_time = %s, last_event_id = %s,
                    snapshot_id = %s, snapshot_digest = %s, snapshot_view = %s, updated_at = now()
                WHERE replay_id = %s AND cursor = %s
                """,
                (after.cursor, rec.available_time, rec.event_id, after.snapshot.snapshot_id,
                 after.snapshot.content_digest, Jsonb(snapshot_view(after.snapshot)), replay_id, before.cursor),
            )
            if cas.rowcount == 0:
                raise _AlreadyApplied(fence)  # rolls back: nothing written
            conn.execute(
                """INSERT INTO observation_deliveries (replay_id, seq, event_id, family, kind, available_time, record,
                       payload) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (replay_id, rec.seq, rec.event_id, rec.family.value, rec.kind.value, rec.available_time,
                 Jsonb(json.loads(rec.model_dump_json())), Jsonb(payload)),
            )
            if self.before_commit is not None:
                self.before_commit(replay_id, rec.seq)
        if self.after_commit is not None:
            self.after_commit(replay_id, rec.seq)
        return fence

    # -- processing --------------------------------------------------------------

    def _load(self, row: dict[str, Any]) -> LoadedSource:
        cfg = ObservationReplayConfig.model_validate(row["config"])
        source = load_source(self.data_root, cfg.source.kind, cfg.source.source_id)
        if feed_identity(source.feed) != cfg.feed:
            raise SourceRejected("source evidence no longer matches the feed identity recorded at launch "
                                 f"({cfg.feed.content_identity}); replay cannot continue safely")
        return source

    def process(self, row: dict[str, Any]) -> None:
        replay_id = row["replay_id"]
        cfg = ObservationReplayConfig.model_validate(row["config"])
        try:
            try:
                source = self._load(row)
            except SourceRejected as exc:
                self.finalize(replay_id, ReplayStatus.FAILED, f"source not replayable: {exc}")
                return
            core = ReplayCore(source.feed, cfg.freshness_policy)
            pos = self._restore(replay_id, core)
            ctl = self.control(replay_id)
            while pos.cursor < core.total:
                if ctl["cancel_requested"]:
                    self.finalize(replay_id, ReplayStatus.CANCELLED, "cancelled by user before completion", source)
                    return
                if ctl["paused"] and ctl["step_budget"] == 0:
                    if self.park(replay_id, pos.cursor):
                        log.info("%s paused at cursor %s; parked", replay_id, pos.cursor)
                        return
                    ctl = self.control(replay_id)
                    continue
                stepping = bool(ctl["paused"])  # while paused only a STEP grant allows a delivery
                event = core.feed.events[pos.cursor]
                after, rec = core.step(pos)
                try:
                    ctl = self.commit(replay_id, pos, after, rec, event.payload.model_dump(mode="json"), stepping)
                    pos = after
                except _AlreadyApplied as already:
                    log.warning("%s delivery %s already committed; restoring from checkpoint", replay_id, pos.cursor)
                    restored = self._restore(replay_id, core)
                    if restored.cursor <= pos.cursor:
                        raise _UnsafeRecovery(f"checkpoint inconsistent at cursor {pos.cursor}") from None
                    pos, ctl = restored, already.control
                ctl = self._pace(replay_id, ctl)
            if ctl["cancel_requested"]:
                self.finalize(replay_id, ReplayStatus.CANCELLED, "cancelled by user before completion", source)
                return
            self.finalize(replay_id, ReplayStatus.COMPLETED, None, source)
        except LeaseLost:
            log.error("%s: lease lost; another worker owns the replay now", replay_id)
        except (_UnsafeRecovery, FeedError) as exc:
            log.error("%s: %s", replay_id, exc)
            self.finalize(replay_id, ReplayStatus.FAILED, f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # deterministic processing/persistence error -> explicit failure
            log.exception("%s failed", replay_id)
            self.finalize(replay_id, ReplayStatus.FAILED, f"{type(exc).__name__}: {exc}")

    def _pace(self, replay_id: str, ctl: dict[str, Any]) -> dict[str, Any]:
        """Sleep at the persisted pacing (events/s); re-read control every chunk. Never affects state."""
        waited = 0.0
        while not (ctl["cancel_requested"] or ctl["paused"]):
            interval = 1.0 / ctl["speed"] if ctl["speed"] > 0 else 0.0
            if waited >= interval - 1e-9:
                break
            chunk = min(interval - waited, 0.25)
            self.sleep(chunk)
            waited += chunk
            ctl = self.control(replay_id)
        return ctl

    # -- completion ------------------------------------------------------------

    def finalize(self, replay_id: str, status: ReplayStatus, error: str | None,
                 source: LoadedSource | None = None) -> None:
        conn = self.conn
        row = conn.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (replay_id,)).fetchone()
        if source is None:
            try:
                source = self._load(row)
            except (SourceRejected, FeedError):
                source = None
        ck = conn.execute("SELECT cursor, snapshot_digest FROM observation_checkpoints WHERE replay_id = %s",
                          (replay_id,)).fetchone()
        deliveries = [DeliveryRecord.model_validate(r["record"]) for r in conn.execute(
            "SELECT record FROM observation_deliveries WHERE replay_id = %s ORDER BY seq", (replay_id,)).fetchall()]
        cursor = ck["cursor"] if ck else 0
        digest = ck["snapshot_digest"] if ck else ""
        if ck is None and source is not None:
            core = ReplayCore(source.feed, ObservationReplayConfig.model_validate(row["config"]).freshness_policy)
            digest = core.at(0).snapshot.content_digest
        manifest = write_replay_artifacts(self.artifact_root, row, status, error, datetime.now(UTC), deliveries,
                                          cursor, digest, source)
        with conn.transaction():
            updated = conn.execute(
                """
                UPDATE observation_replays SET status = %s, error = %s, finished_at = %s, manifest = %s,
                    lease_owner = NULL, lease_expires_at = NULL, heartbeat_at = now()
                WHERE replay_id = %s AND lease_owner = %s AND status = 'running'
                """,
                (manifest.status.value, manifest.error, manifest.finished_at,
                 Jsonb(json.loads(manifest.model_dump_json())), replay_id, self.worker_id),
            )
            if updated.rowcount == 0:
                raise LeaseLost(replay_id)
        log.info("%s finalized as %s (validation %s)", replay_id, manifest.status,
                 "PASS" if manifest.validation.passed else "FAIL")


class _UnsafeRecovery(Exception):
    pass
