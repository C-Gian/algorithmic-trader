"""Fenced compute side of one observation-replay attempt (WP-008-R1A).

The supervisor (``worker.ObservationWorker``) claims a replay under a new monotonic
**lease generation** and runs this job either in a separate compute process (production)
or inline (tests that inject in-process crashes). The job never renews the lease: only
the supervisor does, and only while the compute process exists.

Every durable write made here - phase/progress milestones, prepared config, checkpoint
cursor + delivery rows, parking, artifacts publication and terminal status - is fenced by
``(replay_id, lease_owner, lease_generation, status = 'running')``. A stale attempt (older
generation, even with the same worker id) therefore cannot write state, progress,
artifacts references or a terminal status.

Phases: PREPARING_SOURCE -> VERIFYING_SOURCE -> BUILDING_FEED (worker-owned preparation;
the verified identity/policies are persisted before the first causal application) ->
INITIALIZING (pure prefix rebuild) -> REPLAYING (one causal feed delivery per committed
step, unchanged) -> FINALIZING -> VALIDATING -> GENERATING_REPORT (generation-scoped
immutable publication, then the fenced terminal commit).

Unchanged from WP-007 by design (R1B/R1C remove them): eager feed construction, one
transaction + delivery row + full snapshot per event, full prefix rebuild on restore and
full terminal re-derivation. They are instrumented here with cheap counters.
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .. import db, ops
from ..feed.ordering import FeedError
from ..ops import OperationCancelled
from .artifacts import StagedArtifacts, stage_bounded_artifacts, stage_replay_artifacts
from .contracts import DeliveryRecord, ObservationLaunch, ObservationReplayConfig, ReplayStatus, ValidationOutcome
from .core import Position, ReplayCore, snapshot_view
from .sources import LoadedSource, SourceRejected, feed_identity, load_source, locate_source, manifest_sha256

log = logging.getLogger("algotrader.observe")
_CONTROL_COLUMNS = "cancel_requested, paused, step_budget, speed"
EXIT_LEASE_LOST = 4
EXIT_DB_UNAVAILABLE = 3


class SimulatedCrash(BaseException):
    """In-process stand-in for a hard worker death (tests)."""


class LeaseLost(Exception):
    pass


class _AlreadyApplied(Exception):
    def __init__(self, control: dict[str, Any]) -> None:
        super().__init__("delivery already committed")
        self.control = control


class _UnsafeRecovery(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class JobSpec:
    """Picklable description of one fenced attempt (passed to the compute process)."""

    url: str
    replay_id: str
    worker_id: str
    generation: int
    data_root: str
    artifact_root: str
    progress_interval: float = 0.5
    metrics_interval: float = 2.0
    stall_limit: float | None = None
    # Set by the claim when this attempt only has to finalize (cancel before start / too many interruptions).
    finalize: str | None = None
    finalize_error: str | None = None
    # Test-only fault injection (never exposed through the API/CLI): CPU-bound busy work per unit so that
    # bounded fixtures can exceed a deliberately short lease, or a silent stall without milestones.
    faults: dict[str, float] = field(default_factory=dict)


@dataclass
class Counters:
    """Cheap bounded counters (no per-event expensive measurement)."""

    source_verifications: int = 0
    feed_builds: int = 0
    feed_events: int | None = None
    events_applied: int = 0
    snapshots_built: int = 0
    delivery_rows_written: int = 0
    transactions_committed: int = 0
    prefix_restore_events: int = 0
    validation_deliveries_rederived: int = 0
    deliveries_loaded_for_finalize: int = 0
    output_bytes: int | None = None
    pacing_sleep_seconds: float = 0.0

    def doc(self) -> dict[str, Any]:
        return {**self.__dict__, "pacing_sleep_seconds": round(self.pacing_sleep_seconds, 3)}


def _busy(seconds: float) -> None:
    """CPU-bound busy loop (holds the GIL; used only by test fault injection)."""
    end = time.perf_counter() + seconds
    x = 0
    while time.perf_counter() < end:
        x += 1


class ReplayJob:
    def __init__(self, spec: JobSpec, *, sleep: Callable[[float], None] = time.sleep,
                 before_commit: Callable[[str, int], None] | None = None,
                 after_commit: Callable[[str, int], None] | None = None) -> None:
        self.spec = spec
        self.rid = spec.replay_id
        self.sleep = sleep
        self.before_commit = before_commit
        self.after_commit = after_commit
        self.data_root = Path(spec.data_root)
        self.artifact_root = Path(spec.artifact_root)
        self.counters = Counters()
        self._conn: psycopg.Connection | None = None
        self._phase: str | None = None
        self._phase_t0 = time.monotonic()
        self._last_publish = 0.0
        self._last_metrics = 0.0
        self._seq_hint = 0
        self._cancellable = True
        self.cancel_seen = False
        self._parent = multiprocessing.parent_process()
        self._milestone_base: tuple[float, int] | None = None
        self._restoring = False
        self._phase_wait = 0.0  # declared intentional waits (pacing) inside the current phase span
        self._milestone_key: tuple | None = None
        self._cancel_consumed = False  # a cancellation already turned into INCOMPLETE validation
        self._row_cache: dict[str, Any] = {}
        self._progress: dict[str, Any] = {}

    # -- connection / fence ----------------------------------------------------------

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = db.connect(self.spec.url, autocommit=True)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def fence(self) -> tuple[str, tuple[Any, ...]]:
        return ("replay_id = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'",
                (self.rid, self.spec.worker_id, self.spec.generation))

    def _row(self) -> dict[str, Any]:
        cond, args = self.fence
        row = self.conn.execute(f"SELECT * FROM observation_replays WHERE {cond}", args).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        return row

    def _check_parent(self) -> None:
        if self._parent is not None and not self._parent.is_alive():
            log.error("%s: supervisor process gone; compute stops (lease will lapse)", self.rid)
            os._exit(EXIT_LEASE_LOST)

    # -- phases and milestones ---------------------------------------------------------

    def _span_measure(self) -> tuple[float, float]:
        """(active, waiting) seconds of the open span: monotonic compute time minus declared waits."""
        elapsed = time.monotonic() - self._phase_t0
        return round(max(elapsed - self._phase_wait, 0.0), 3), round(self._phase_wait, 3)

    def _closed(self, phase: str, row_started: datetime | None) -> dict[str, Any]:
        active, waiting = self._span_measure()
        return ops.closed_entry(phase, self.spec.generation, self._row_cache["attempt"], row_started, _now(), active,
                                waiting_seconds=waiting)

    def enter_phase(self, phase: str, **progress: Any) -> None:
        cond, args = self.fence
        row = self.conn.execute(f"SELECT attempt, phase, phase_started_at FROM observation_replays WHERE {cond}",
                                args).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        self._row_cache = row
        closing = []
        if row["phase"] and row["phase_started_at"] is not None and self._phase is not None:
            closing.append(self._closed(row["phase"], row["phase_started_at"]))
        limit = self.spec.stall_limit or ops.STALL_LIMITS.get(phase, ops.DEFAULT_STALL_LIMIT)
        doc = {"stage": None, "done": None, "total": None, "unit": None, "stall_limit": limit,
               "restoring": self._restoring, "restoring_attempt": row["attempt"] if self._restoring else None,
               "waiting": None, "phase": phase, "phase_active_seconds": 0.0, "phase_waiting_seconds": 0.0,
               "rate_base_done": None, "rate_window_seconds": None, **progress}
        replaying = phase == "REPLAYING"
        # The replay ETA window starts when REPLAYING starts (never at claim/preparation); other phases clear it.
        updated = self.conn.execute(
            f"""UPDATE observation_replays SET phase = %s, phase_started_at = now(),
                    phase_history = phase_history || %s, progress = %s, last_progress_at = now(),
                    progress_seq = progress_seq + 1,
                    throughput_since = CASE WHEN %s THEN now() ELSE NULL END,
                    throughput_base = CASE WHEN %s THEN %s::int ELSE NULL END
                WHERE {cond} RETURNING cancel_requested""",
            (phase, Jsonb(closing), Jsonb(doc), replaying, replaying, progress.get("done") if replaying else None,
             *args),
        ).fetchone()
        if updated is None:
            raise LeaseLost(self.rid)
        self.cancel_seen = bool(updated["cancel_requested"])
        self._phase, self._phase_t0, self._phase_wait = phase, time.monotonic(), 0.0
        self._last_publish = time.monotonic()
        self._milestone_base, self._milestone_key = None, None
        self._progress = doc
        log.info("%s g%s: phase %s", self.rid, self.spec.generation, phase)

    def milestone(self, stage: str, done: int, total: int | None, unit: str, force: bool = False,
                  **extra: Any) -> None:
        """Publish a compute milestone (rate limited); read cancellation; check the supervisor exists."""
        unit_fault = self.spec.faults.get(f"{self._phase}_cpu_per_unit")
        if unit_fault:
            _busy(unit_fault)
        if self.spec.faults.get(f"{self._phase}_hard_exit"):
            os._exit(int(self.spec.faults[f"{self._phase}_hard_exit"]))  # test fault: compute process dies
        now = time.monotonic()
        if not force and now - self._last_publish < self.spec.progress_interval:
            return
        self._check_parent()
        stall = self.spec.faults.pop(f"{self._phase}_silent_stall", None)
        if stall:
            # test fault (one shot): stay alive but publish no milestone for ``stall`` seconds
            self.sleep(stall)
        self._last_publish = now
        active, waiting = self._span_measure()
        key = (stage, unit, total)
        if self._milestone_base is None or self._milestone_key != key:
            # a new comparable window: different substage, unit or total never shares a rate base
            self._milestone_base, self._milestone_key = (active, done), key
        base_active, base_done = self._milestone_base
        doc = {**self._progress, "stage": stage, "done": done, "total": total, "unit": unit, "phase": self._phase,
               "phase_active_seconds": active, "phase_waiting_seconds": waiting,
               "rate_window_seconds": round(active - base_active, 3), "rate_base_done": base_done,
               "rate_basis": "active compute seconds of this substage (declared waits excluded)", **extra}
        self._progress = doc
        cond, args = self.fence
        sets = "progress = %s, last_progress_at = now(), progress_seq = progress_seq + 1"
        params: list[Any] = [Jsonb(doc)]
        if now - self._last_metrics >= self.spec.metrics_interval:
            self._last_metrics = now
            sets += ", metrics = metrics || %s"
            params.append(Jsonb(self._metrics_doc()))
        row = self.conn.execute(f"UPDATE observation_replays SET {sets} WHERE {cond} RETURNING cancel_requested",
                                (*params, *args)).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        self.cancel_seen = bool(row["cancel_requested"])

    def hook(self, stage: str, done: int, total: int | None, unit: str) -> None:
        self.milestone(stage, done, total, unit, force=done == 0 or (total is not None and done >= total))
        if self.cancel_seen and self._cancellable and not self._cancel_consumed:
            raise OperationCancelled(stage)

    def _cancel_requested(self) -> bool:
        cond, args = self.fence
        row = self.conn.execute(f"SELECT cancel_requested FROM observation_replays WHERE {cond}", args).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        return bool(row["cancel_requested"])

    def _metrics_doc(self) -> dict[str, Any]:
        return {str(self.spec.generation): {**self.counters.doc(), **ops.process_metrics(),
                                            "pid": os.getpid(), "recorded_at": _now().isoformat()}}

    def _timings(self) -> list[dict]:
        row = self.conn.execute("SELECT phase_history FROM observation_replays WHERE replay_id = %s",
                                (self.rid,)).fetchone()
        active, waiting = self._span_measure()
        current = ops.closed_entry(self._phase or "?", self.spec.generation, self._row_cache["attempt"], None, _now(),
                                   active, waiting_seconds=waiting, note="open at publication")
        return [*list(row["phase_history"]), current]

    def _set_assurance(self, doc: dict[str, Any]) -> None:
        cond, args = self.fence
        self.conn.execute(f"UPDATE observation_replays SET assurance = %s WHERE {cond}", (Jsonb(doc), *args))

    # -- entry point -------------------------------------------------------------------------

    def run(self) -> None:
        try:
            row = self._row()
            self._row_cache = row
            if self.spec.finalize:
                self.finalize(ReplayStatus(self.spec.finalize), self.spec.finalize_error, None)
                return
            self.process(row)
        except LeaseLost:
            log.warning("%s g%s: lease lost (fenced); this attempt stops without writing", self.rid,
                        self.spec.generation)
        finally:
            self.close()

    # -- preparation --------------------------------------------------------------------------

    def _prepare(self, row: dict[str, Any]) -> LoadedSource:
        """Worker-owned PREPARING_SOURCE / VERIFYING_SOURCE / BUILDING_FEED (eager feed retained for R1A)."""
        configured = row["config"] is not None
        if configured:
            cfg = ObservationReplayConfig.model_validate(row["config"])
            kind, source_id = cfg.source.kind, cfg.source.source_id
            expected_sha = None
        else:
            launch = ObservationLaunch.model_validate(row["launch"])
            kind, source_id, expected_sha = launch.source_kind, launch.source_id, launch.expected_manifest_sha256
        self.enter_phase("PREPARING_SOURCE", detail=f"locating {kind.value} {source_id}")
        path = locate_source(self.data_root, kind, source_id)
        if expected_sha is not None:
            actual = manifest_sha256(path)
            if actual != expected_sha:
                raise SourceRejected(f"dataset {source_id} manifest changed since it was bound to the corpus "
                                     f"(sha256 {actual[:16]} != bound {expected_sha[:16]}); not replayed")
        self.milestone("source located", 1, 1, "steps", force=True)
        build_started = [False]
        self.counters.source_verifications += 1
        self.enter_phase("VERIFYING_SOURCE", detail=f"verifying {kind.value} {source_id}")

        def verify_hook(stage: str, done: int, total: int | None, unit: str) -> None:
            self.hook(stage, done, total, unit)

        def build_hook(stage: str, done: int, total: int | None, unit: str) -> None:
            if not build_started[0]:
                build_started[0] = True
                self.counters.feed_builds += 1
                self.enter_phase("BUILDING_FEED", detail="eager feed construction (R1A; streaming is R1B)",
                                 noninterruptible_units=["order events (single unit)",
                                                         "feed identity hashes (single unit)",
                                                         "bridge recorded journal (single unit)"])
            if stage.startswith("re-verify inside feed build"):
                if done == 0 and total and stage.endswith("files"):
                    self.counters.source_verifications += 1
            self.hook(stage, done, total, unit)

        source = load_source(self.data_root, kind, source_id, progress=verify_hook, build_progress=build_hook)
        self.counters.feed_events = len(source.feed.events)
        if configured:
            if feed_identity(source.feed) != cfg.feed:
                raise SourceRejected("source evidence no longer matches the feed identity recorded at preparation "
                                     f"({cfg.feed.content_identity}); replay cannot continue safely")
            return source
        # persist the exact verified identity/policies before the first causal application
        from .control import build_config

        config = build_config(self.rid, source)
        cond, args = self.fence
        done = self.conn.execute(
            f"""UPDATE observation_replays SET config = %s, total_events = %s
                WHERE {cond} AND config IS NULL RETURNING 1""",
            (Jsonb(json.loads(config.model_dump_json())), config.feed.event_count, *args),
        ).fetchone()
        if done is None:
            raise LeaseLost(self.rid)
        return source

    def _load_quietly(self, row: dict[str, Any]) -> LoadedSource | None:
        """Reload the source for terminal validation; cancellable (OperationCancelled propagates)."""
        try:
            return self._prepare(row)
        except (SourceRejected, FeedError):
            return None

    # -- checkpoint / restore -------------------------------------------------------------------

    def checkpoint(self) -> dict[str, Any] | None:
        return self.conn.execute(
            "SELECT cursor, snapshot_digest FROM observation_checkpoints WHERE replay_id = %s", (self.rid,)
        ).fetchone()

    def _restore(self, core: ReplayCore, reclaimed: bool) -> Position:
        """Rebuild the state as the pure feed prefix at the committed cursor and check its digest."""
        ck = self.checkpoint()
        if ck is None:
            pos = core.at(0)
            self.counters.snapshots_built += 1
            cond, args = self.fence
            with self.conn.transaction():
                if self.conn.execute(f"SELECT 1 FROM observation_replays WHERE {cond} FOR UPDATE", args).fetchone() is None:
                    raise LeaseLost(self.rid)
                self.conn.execute(
                    """INSERT INTO observation_checkpoints
                           (replay_id, cursor, info_time, last_event_id, snapshot_id, snapshot_digest, snapshot_view)
                       VALUES (%s, 0, %s, NULL, %s, %s, %s) ON CONFLICT (replay_id) DO NOTHING""",
                    (self.rid, pos.snapshot.as_of, pos.snapshot.snapshot_id, pos.snapshot.content_digest,
                     Jsonb(snapshot_view(pos.snapshot))),
                )
            ck = self.checkpoint()
        target = ck["cursor"]
        self._restoring = reclaimed and target > 0
        self.enter_phase("INITIALIZING", detail=f"pure prefix rebuild to committed cursor {target}")
        pos = core.at(target, progress=lambda d, t: self.hook("rebuild committed prefix", d, t, "events"))
        self.counters.prefix_restore_events += target
        self.counters.snapshots_built += 1
        if pos.snapshot.content_digest != ck["snapshot_digest"]:
            raise _UnsafeRecovery(f"committed cursor {target}: persisted snapshot digest "
                                  f"{ck['snapshot_digest'][:16]} differs from the pure feed prefix "
                                  f"{pos.snapshot.content_digest[:16]}; recovery is not safe")
        return pos

    def control(self) -> dict[str, Any]:
        cond, args = self.fence
        row = self.conn.execute(f"SELECT {_CONTROL_COLUMNS} FROM observation_replays WHERE {cond}", args).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        return row

    def commit(self, before: Position, after: Position, rec: DeliveryRecord, payload: dict[str, Any],
               consume_step: bool) -> dict[str, Any]:
        conn = self.conn
        cond, args = self.fence
        with conn.transaction():
            fence = conn.execute(
                f"""
                UPDATE observation_replays SET interruptions = 0, last_progress_at = now(),
                    progress_seq = progress_seq + 1,
                    step_budget = CASE WHEN %s THEN greatest(step_budget - 1, 0) ELSE step_budget END
                WHERE {cond}
                RETURNING {_CONTROL_COLUMNS}
                """,
                (consume_step, *args),
            ).fetchone()
            if fence is None:
                raise LeaseLost(self.rid)
            cas = conn.execute(
                """
                UPDATE observation_checkpoints SET cursor = %s, info_time = %s, last_event_id = %s,
                    snapshot_id = %s, snapshot_digest = %s, snapshot_view = %s, updated_at = now()
                WHERE replay_id = %s AND cursor = %s
                """,
                (after.cursor, rec.available_time, rec.event_id, after.snapshot.snapshot_id,
                 after.snapshot.content_digest, Jsonb(snapshot_view(after.snapshot)), self.rid, before.cursor),
            )
            if cas.rowcount == 0:
                raise _AlreadyApplied(fence)  # rolls back: nothing written
            conn.execute(
                """INSERT INTO observation_deliveries (replay_id, seq, event_id, family, kind, available_time, record,
                       payload) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (self.rid, rec.seq, rec.event_id, rec.family.value, rec.kind.value, rec.available_time,
                 Jsonb(json.loads(rec.model_dump_json())), Jsonb(payload)),
            )
            if self.before_commit is not None:
                self.before_commit(self.rid, rec.seq)
        self.counters.transactions_committed += 1
        self.counters.delivery_rows_written += 1
        if self.after_commit is not None:
            self.after_commit(self.rid, rec.seq)
        return fence

    def park(self, cursor: int) -> bool:
        cond, args = self.fence
        note = {"at": _now().isoformat(), "command": "parked", "at_cursor": cursor, "worker": self.spec.worker_id,
                "generation": self.spec.generation}
        closing = [self._closed(self._phase or "REPLAYING", self._phase_started())]
        parked = self.conn.execute(
            f"""
            UPDATE observation_replays SET status = 'paused', lease_owner = NULL, lease_expires_at = NULL,
                heartbeat_at = now(), control_log = control_log || %s, phase_history = phase_history || %s,
                phase_started_at = NULL, progress = progress || %s, metrics = metrics || %s
            WHERE {cond} AND paused AND step_budget = 0 AND NOT cancel_requested
            """,
            (Jsonb([note]), Jsonb(closing), Jsonb({"waiting": "paused at a committed cursor"}),
             Jsonb(self._metrics_doc()), *args),
        ).rowcount
        return bool(parked)

    def _phase_started(self) -> datetime | None:
        row = self.conn.execute("SELECT phase_started_at FROM observation_replays WHERE replay_id = %s",
                                (self.rid,)).fetchone()
        return row["phase_started_at"] if row else None

    # -- processing ---------------------------------------------------------------------------

    def process(self, row: dict[str, Any]) -> None:
        reclaimed = bool(row["recovery_log"]) and \
            row["recovery_log"][-1].get("generation") == self.spec.generation
        self._restoring = reclaimed and row["config"] is not None
        try:
            try:
                source = self._prepare(row)
            except OperationCancelled:
                self.finalize(ReplayStatus.CANCELLED, "cancelled by user during source preparation", None,
                              reload=False)
                return
            except SourceRejected as exc:
                self.finalize(ReplayStatus.FAILED, f"source not replayable: {exc}", None, reload=False)
                return
            cfg = ObservationReplayConfig.model_validate(self._row()["config"])
            core = ReplayCore(source.feed, cfg.freshness_policy)
            try:
                pos = self._restore(core, reclaimed)
            except OperationCancelled:
                self.finalize(ReplayStatus.CANCELLED, "cancelled by user during initialization", source)
                return
            self._cancellable = False  # replay controls are read from the commit fence below
            self._restoring = False
            ctl = self.control()
            speed = ctl["speed"]
            stall = max(self.spec.stall_limit or ops.STALL_LIMITS["REPLAYING"], 3.0 / speed if speed > 0 else 0)
            self.enter_phase("REPLAYING", detail="one causal feed delivery per committed step", stall_limit=stall,
                             total=core.total, done=pos.cursor, unit="events")
            while pos.cursor < core.total:
                if ctl["cancel_requested"]:
                    self.finalize(ReplayStatus.CANCELLED, "cancelled by user before completion", source)
                    return
                if ctl["paused"] and ctl["step_budget"] == 0:
                    if self.park(pos.cursor):
                        log.info("%s paused at cursor %s; parked", self.rid, pos.cursor)
                        return
                    ctl = self.control()
                    continue
                stepping = bool(ctl["paused"])  # while paused only a STEP grant allows a delivery
                event = core.feed.events[pos.cursor]
                after, rec = core.step(pos)
                self.counters.events_applied += 1
                self.counters.snapshots_built += 1
                try:
                    ctl = self.commit(pos, after, rec, event.payload.model_dump(mode="json"), stepping)
                    pos = after
                except _AlreadyApplied as already:
                    log.warning("%s delivery %s already committed; restoring from checkpoint", self.rid, pos.cursor)
                    restored = self._restore(core, False)
                    self.enter_phase("REPLAYING", detail="resumed after checkpoint reload", total=core.total,
                                     done=restored.cursor, unit="events")
                    if restored.cursor <= pos.cursor:
                        raise _UnsafeRecovery(f"checkpoint inconsistent at cursor {pos.cursor}") from None
                    pos, ctl = restored, already.control
                self.milestone("apply feed deliveries", pos.cursor, core.total, "events")
                ctl = self._pace(ctl)
            if ctl["cancel_requested"]:
                self.finalize(ReplayStatus.CANCELLED, "cancelled by user before completion", source)
                return
            self.finalize(ReplayStatus.COMPLETED, None, source)
        except (_UnsafeRecovery, FeedError) as exc:
            log.error("%s: %s", self.rid, exc)
            self.finalize(ReplayStatus.FAILED, f"{type(exc).__name__}: {exc}", None)
        except (LeaseLost, SimulatedCrash, psycopg.OperationalError):
            raise
        except Exception as exc:  # deterministic processing/persistence error -> explicit failure
            log.exception("%s failed", self.rid)
            self.finalize(ReplayStatus.FAILED, f"{type(exc).__name__}: {exc}", None)

    def _pace(self, ctl: dict[str, Any]) -> dict[str, Any]:
        """Sleep at the persisted pacing (events/s); re-read control every chunk. Never affects state."""
        waited = 0.0
        while not (ctl["cancel_requested"] or ctl["paused"]):
            interval = 1.0 / ctl["speed"] if ctl["speed"] > 0 else 0.0
            if waited >= interval - 1e-9:
                break
            chunk = min(interval - waited, 0.25)
            self.sleep(chunk)
            waited += chunk
            self._phase_wait += chunk  # declared wait: excluded from active time
            self.counters.pacing_sleep_seconds += chunk
            ctl = self.control()
        return ctl

    # -- completion ---------------------------------------------------------------------------

    def finalize(self, status: ReplayStatus, error: str | None, source: LoadedSource | None,
                 reload: bool = True) -> None:
        """Terminal phases. Once a cancellation is observed, finish on the bounded path (no prefix load, no
        source reload, no reference re-derivation). The final publish + terminal commit run under the row lock,
        which serializes against the cancel command: that rename+commit is the only atomic boundary."""
        row = self._row()
        self._row_cache = row
        self._restoring = False
        if row["config"] is None:
            self._terminal(status, error, None, {"state": ops.Assurance.NOT_CHECKED.value,
                                                 "detail": "the source was never prepared: nothing to validate"})
            return
        ck = self.checkpoint()
        cursor = ck["cursor"] if ck else 0
        if status == ReplayStatus.CANCELLED or self._cancel_requested():
            self._finalize_bounded(status, error, ck, self._phase or "QUEUED")
            return
        self._cancellable, self._cancel_consumed, self.cancel_seen = True, False, False
        self._progress_target(status, cursor, row["total_events"])
        staged: StagedArtifacts | None = None
        validation_stages = ("re-derive committed deliveries", "pure cutoff snapshot")

        def phase(p: str) -> None:
            if p == "VALIDATING":  # assurance becomes INCOMPLETE before the phase is visible
                from .contracts import VALIDATOR_ID, VALIDATOR_SCOPE, VALIDATOR_VERSION

                self._set_assurance({"state": ops.Assurance.INCOMPLETE.value, "detail": "validation in progress",
                                     "validator": VALIDATOR_ID, "validator_version": VALIDATOR_VERSION,
                                     "scope": VALIDATOR_SCOPE})
            if p != "FINALIZING":
                self.enter_phase(p, finalizing_as=status.value, cursor=cursor, total_events=row["total_events"])

        def hook(stage: str, done: int, total: int | None, unit: str) -> None:
            if stage == "re-derive committed deliveries":
                self.counters.validation_deliveries_rederived = done
            try:
                self.hook(stage, done, total, unit)
            except OperationCancelled:
                if stage in validation_stages:  # validation reports INCOMPLETE itself; later units continue
                    self._cancel_consumed = True
                raise

        try:
            if source is None and reload:
                source = self._load_quietly(row)
            digest = ck["snapshot_digest"] if ck else ""
            if ck is None and source is not None:
                core = ReplayCore(source.feed, ObservationReplayConfig.model_validate(row["config"]).freshness_policy)
                digest = core.at(0).snapshot.content_digest
            self.enter_phase("FINALIZING", detail="loading committed deliveries and serializing artifacts",
                             finalizing_as=status.value, cursor=cursor, total_events=row["total_events"])
            deliveries = []
            for i, r in enumerate(self.conn.execute(
                    "SELECT record FROM observation_deliveries WHERE replay_id = %s ORDER BY seq", (self.rid,))):
                if i % 1000 == 0:
                    self.hook("load committed deliveries", i, cursor, "deliveries")
                deliveries.append(DeliveryRecord.model_validate(r["record"]))
                self.counters.deliveries_loaded_for_finalize = i + 1
            self.hook("load committed deliveries", len(deliveries), cursor, "deliveries")
            if self.spec.faults.get("publish_error"):
                raise OSError("simulated artifact publication failure (test fault)")
            staged = stage_replay_artifacts(
                self.artifact_root, row, status, error, _now(), deliveries, cursor, digest, source,
                generation=self.spec.generation, phase=phase, hook=hook, timings=self._timings,
                metrics=lambda: self._metrics_doc()[str(self.spec.generation)], cancel_validation=True)
            self.counters.output_bytes = staged.output_bytes
            m = staged.manifest
            v = m.validation
            outcome = v.outcome or (ValidationOutcome.PASSED if v.passed else ValidationOutcome.FAILED)
            assurance = {"state": outcome.value, "validator": v.validator, "validator_version": v.validator_version,
                         "scope": v.scope, "checks_passed": sum(1 for c in v.checks if c.passed),
                         "checks_total": len(v.checks)}
            # a cancellation that reaches the commit lock first still prevents a COMPLETED publication
            self._terminal(m.status, m.error, m, assurance, expected_cursor=cursor, staged=staged,
                           abort_if_cancelled=m.status == ReplayStatus.COMPLETED and not self._cancel_consumed)
        except OperationCancelled as exc:
            if staged is not None:
                staged.discard()
            self._finalize_bounded(status, error, ck, f"{self._phase} ({exc})")
        except (LeaseLost, SimulatedCrash, psycopg.OperationalError):
            if staged is not None:
                staged.discard()
            raise
        except Exception as exc:  # report generation/publication failed: stay diagnosable, never "completed"
            if staged is not None:
                staged.discard()
            log.exception("%s: terminal publication failed", self.rid)
            self._terminal(ReplayStatus.FAILED,
                           f"terminal artifact/report publication failed during {self._phase}: "
                           f"{type(exc).__name__}: {exc}" + (f" (original outcome: {status.value}"
                                                             + (f", {error})" if error else ")")),
                           None, {"state": ops.Assurance.INCOMPLETE.value,
                                  "detail": "terminal publication failed; no manifest was recorded"},
                           expected_cursor=cursor)

    def _progress_target(self, status: ReplayStatus, cursor: int, total: int | None) -> None:
        self._progress = {**self._progress, "finalizing_as": status.value, "cursor": cursor, "total_events": total}

    def _finalize_bounded(self, status: ReplayStatus, error: str | None, ck: dict[str, Any] | None,
                          where: str) -> None:
        """Bounded terminal path after an observed cancellation: config + committed checkpoint facts only."""
        row = self._row()
        self._row_cache = row
        cursor = ck["cursor"] if ck else 0
        total = row["total_events"]
        full = ck is not None and total is not None and cursor == total
        if status == ReplayStatus.FAILED:
            final, err = ReplayStatus.FAILED, (f"{error}; cancellation requested during {where}: the reference "
                                               "validation was not run")
        elif status == ReplayStatus.COMPLETED:
            final, err = ReplayStatus.CANCELLED, (
                f"cancelled by user during {where}: the replay cursor {'was complete' if full else 'stopped'} at "
                f"{cursor}/{total}, but terminal validation/publication did not finish; assurance INCOMPLETE")
        else:
            final, err = ReplayStatus.CANCELLED, error or "cancelled by user before completion"
        ck_full = None
        if ck is not None:
            ck_full = self.conn.execute(
                "SELECT cursor, snapshot_id, snapshot_digest, info_time FROM observation_checkpoints "
                "WHERE replay_id = %s", (self.rid,)).fetchone()
        self.enter_phase("GENERATING_REPORT", detail="bounded cancellation report (config + checkpoint facts only)",
                         finalizing_as=final.value, cursor=cursor, total_events=total)
        staged = stage_bounded_artifacts(
            self.artifact_root, row, final, err, _now(), cursor, ck_full, f"cancellation observed during {where}",
            generation=self.spec.generation, timings=self._timings,
            metrics=lambda: self._metrics_doc()[str(self.spec.generation)])
        self.counters.output_bytes = staged.output_bytes
        try:
            self._terminal(final, err, staged.manifest,
                           {"state": ops.Assurance.INCOMPLETE.value, "validator": staged.manifest.validation.validator,
                            "validator_version": staged.manifest.validation.validator_version,
                            "scope": staged.manifest.validation.scope,
                            "detail": f"bounded cancellation during {where}; reference validation not run"},
                           expected_cursor=cursor, staged=staged)
        except BaseException:
            staged.discard()
            raise

    def _terminal(self, status: ReplayStatus, error: str | None, manifest: Any, assurance: dict[str, Any],
                  expected_cursor: int | None = None, staged: StagedArtifacts | None = None,
                  abort_if_cancelled: bool = False) -> None:
        """Fenced terminal commit. With ``staged`` the immutable publication happens inside the locked
        transaction, so the cancel command (which locks the same row) is ordered strictly before or after it."""
        cond, args = self.fence
        closing = [self._closed(self._phase, self._phase_started())] if self._phase else []
        with self.conn.transaction():
            row = self.conn.execute(f"SELECT cancel_requested FROM observation_replays WHERE {cond} FOR UPDATE",
                                    args).fetchone()
            if row is None:
                raise LeaseLost(self.rid)
            if expected_cursor is not None:
                ck = self.checkpoint()
                if (ck["cursor"] if ck else 0) != expected_cursor:
                    raise LeaseLost(f"{self.rid}: committed cursor moved during finalization")
            if abort_if_cancelled and row["cancel_requested"]:
                raise OperationCancelled("terminal commit boundary")
            if staged is not None:
                manifest = staged.publish().manifest
            self.conn.execute(
                f"""
                UPDATE observation_replays SET status = %s, error = %s, finished_at = now(), manifest = %s,
                    lease_owner = NULL, lease_expires_at = NULL, heartbeat_at = now(), assurance = %s,
                    phase_history = phase_history || %s, phase_started_at = NULL,
                    progress = progress || %s, metrics = metrics || %s
                WHERE {cond}
                """,
                (status.value, error,
                 Jsonb(json.loads(manifest.model_dump_json())) if manifest is not None else None,
                 Jsonb(assurance), Jsonb(closing), Jsonb({"waiting": None, "restoring": False}),
                 Jsonb(self._metrics_doc()), *args),
            )
        log.info("%s finalized as %s (assurance %s)", self.rid, status.value, assurance.get("state"))


def compute_main(spec: JobSpec) -> None:
    """Compute-process entry point (spawned by the supervisor)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    job = ReplayJob(spec)
    try:
        job.run()
    except psycopg.OperationalError as exc:
        log.error("%s: database unavailable in compute process: %s", spec.replay_id, exc)
        os._exit(EXIT_DB_UNAVAILABLE)
