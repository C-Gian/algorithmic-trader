"""Fenced compute side of one observation-replay attempt (WP-008-R1A lifecycle, WP-008-R1B engine).

The supervisor (``worker.ObservationWorker``) claims a replay under a new monotonic **lease generation**
and runs this job in a separate compute process (production) or inline (tests). The job never renews the
lease. Every durable write - phase/progress milestones, prepared config + pinned engine identities,
checkpoint cursor + committed range + restore point, parking, artifact publication and terminal status -
is fenced by ``(replay_id, lease_owner, lease_generation, status = 'running')``.

R1B streaming engine (``observe.stream.v1``):

* PREPARING_SOURCE locates the source and its immutable feed cache (``feedcache``); a cold preparation
  verifies the source ONCE (VERIFYING_SOURCE) and stream-builds the cache (BUILDING_FEED). A warm or restored
  run never normalizes or verifies the source package again.
* INITIALIZING restores the explicit state from the newest verified restore point (falling back to an older
  verified one with diagnostic evidence) and reprocesses only the bounded uncommitted suffix; no valid
  checkpoint is a visible failure, never a silent replay from zero.
* REPLAYING applies every canonical event with the accepted reducer through one kernel (max, paced, STEP).
  No per-event snapshot, delivery row or transaction: a checkpoint commits a compact input range + a
  restore point + the materialized snapshot every ``checkpoint_seconds`` of active compute or
  ``checkpoint_events`` events (and at pause / STEP / end / cancel). Controls are polled every
  ``control_poll`` seconds of wall time.
* FINALIZING -> VALIDATING (bounded reconciliation, see ``reconcile``) -> GENERATING_REPORT, published under
  the replay row lock. Observed cancellation uses the R1A bounded path.
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
from .artifacts import StagedArtifacts, stage_bounded_artifacts, stage_stream_artifacts
from .contracts import (
    ObservationLaunch,
    ObservationReplayConfig,
    ReplayStatus,
    SourceKind,
    ValidationOutcome,
)
from .core import snapshot_view
from .feedcache import (
    CACHE_FORMAT,
    COMMITMENT_FORMAT,
    CacheError,
    CacheReader,
    FeedCache,
    initial_commitment,
    open_cache,
    order_sort_key,
    quarantine,
)
from ..temporal import engine as temporal_engine
from ..temporal.engine import TemporalError
from .kernel import (
    ENGINE_FORMAT,
    STATE_FORMAT,
    Kernel,
    StateError,
    fingerprint,
    new_temporal,
    restore_temporal,
    temporal_config,
    unpack_state,
)
from .sources import PreparedSource, SourceRejected, feed_identity, prepare_stream_source

log = logging.getLogger("algotrader.observe")
_CONTROL_COLUMNS = "cancel_requested, paused, step_budget, speed"
EXIT_LEASE_LOST = 4
EXIT_DB_UNAVAILABLE = 3


class SimulatedCrash(BaseException):
    """In-process stand-in for a hard worker death (tests)."""


class LeaseLost(Exception):
    pass


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
    # checkpoint cadence (engineering controls, not semantic times) and control polling
    checkpoint_seconds: float = 2.0
    checkpoint_events: int = 5000
    control_poll: float = 0.25
    # Set by the claim when this attempt only has to finalize (cancel before start / too many interruptions).
    finalize: str | None = None
    finalize_error: str | None = None
    kind: str = "replay"  # "replay" (observation replay) or "deep" (Deep validation; replay_id = validation id)
    # Test-only fault injection (never exposed through the API/CLI): CPU-bound busy work per unit so that
    # bounded fixtures can exceed a deliberately short lease, or a silent stall without milestones.
    faults: dict[str, float] = field(default_factory=dict)


@dataclass
class Counters:
    """Cheap bounded counters (no per-event expensive measurement)."""

    source_verifications: int = 0
    feed_builds: int = 0
    cache_build_events: int | None = None
    sort_spill_runs: int | None = None
    cache_reused: bool | None = None
    preparation: dict | None = None
    feed_events: int | None = None
    source_records_read: int = 0  # canonical event lines read from the verified cache
    events_decoded: int = 0
    events_applied: int = 0
    snapshots_built: int = 0
    state_encodes: int = 0
    delivery_rows_written: int = 0  # always 0 for streaming runs
    transactions_committed: int = 0
    checkpoints_committed: int = 0
    ranges_committed: int = 0
    restore_suffix_events: int = 0
    restore_fallbacks: int = 0
    prefix_restore_events: int = 0  # always 0: restores never rebuild the full prefix
    cache_bytes_read: int = 0
    cache_partitions_read: int = 0
    checkpoint_state_bytes: int = 0
    checkpoint_temporal_bytes: int = 0  # compressed temporal restore state (observe.stream.v2 runs)
    validation_deliveries_rederived: int = 0  # always 0: no reference re-derivation at finalization
    deliveries_loaded_for_finalize: int = 0  # always 0: no per-event records exist
    output_bytes: int | None = None
    pacing_sleep_seconds: float = 0.0
    max_checkpoint_gap_events: int = 0
    max_control_gap_seconds: float = 0.0

    def doc(self) -> dict[str, Any]:
        return {**self.__dict__, "pacing_sleep_seconds": round(self.pacing_sleep_seconds, 3),
                "max_control_gap_seconds": round(self.max_control_gap_seconds, 3)}


def _busy(seconds: float) -> None:
    """CPU-bound busy loop (holds the GIL; used only by test fault injection)."""
    end = time.perf_counter() + seconds
    x = 0
    while time.perf_counter() < end:
        x += 1


class ReplayJob:
    TABLE = "observation_replays"  # lifecycle table (Deep validation jobs reuse the same machinery)
    KEY = "replay_id"
    CONTROLS = _CONTROL_COLUMNS
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
        return (f"{self.KEY} = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'",
                (self.rid, self.spec.worker_id, self.spec.generation))

    def _row(self) -> dict[str, Any]:
        cond, args = self.fence
        row = self.conn.execute(f"SELECT * FROM {self.TABLE} WHERE {cond}", args).fetchone()
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
        row = self.conn.execute(f"SELECT attempt, phase, phase_started_at FROM {self.TABLE} WHERE {cond}",
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
            f"""UPDATE {self.TABLE} SET phase = %s, phase_started_at = now(),
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
        if self.spec.faults.get(f"{self._phase}_hard_exit") and done >= self.spec.faults.get(
                f"{self._phase}_hard_exit_at", 0):
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
        row = self.conn.execute(f"UPDATE {self.TABLE} SET {sets} WHERE {cond} RETURNING cancel_requested",
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
        row = self.conn.execute(f"SELECT cancel_requested FROM {self.TABLE} WHERE {cond}", args).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        return bool(row["cancel_requested"])

    def _timings(self) -> list[dict]:
        row = self.conn.execute(f"SELECT phase_history FROM {self.TABLE} WHERE {self.KEY} = %s",
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

    def _prep_fault(self, stage: str) -> None:
        """Test-only preparation fault hooks (``prep_<stage>`` in ``faults``): simulated crash / mutation."""
        action = self.spec.faults.get(f"prep_{stage}")
        if action == "crash":
            raise SimulatedCrash(stage)
        if callable(getattr(self, "_prep_fault_cb", None)):
            self._prep_fault_cb(stage)

    def _prepare(self, row: dict[str, Any]) -> PreparedSource:
        """PREPARING_SOURCE (+ VERIFYING_SOURCE / BUILDING_FEED on a cold cache). Pins config + engine."""
        configured = row["config"] is not None
        if configured:
            cfg = ObservationReplayConfig.model_validate(row["config"])
            kind, source_id, expected_sha = cfg.source.kind, cfg.source.source_id, None
        else:
            launch = ObservationLaunch.model_validate(row["launch"])
            kind, source_id, expected_sha = launch.source_kind, launch.source_id, launch.expected_manifest_sha256
        self.enter_phase("PREPARING_SOURCE", detail=f"locating {kind.value} {source_id} and its feed cache")
        build_counters: dict[str, Any] = {}

        def on_phase(p: str) -> None:
            self.enter_phase(p, detail=(f"verifying {kind.value} {source_id} once" if p == "VERIFYING_SOURCE" else
                                        "streaming the verified source into an immutable feed cache"),
                             noninterruptible_units=["cache directory publication (single rename)"])

        from .sources import ReceiptStore

        prepared = prepare_stream_source(self.data_root, kind, source_id, receipts=ReceiptStore(self.conn),
                                         verify_hook=self.hook, build_hook=self.hook, on_phase=on_phase,
                                         counters=build_counters, expected_manifest_sha256=expected_sha,
                                         created_by={"replay_id": self.rid, "generation": self.spec.generation},
                                         fault=self._prep_fault)
        c = self.counters
        c.source_verifications += build_counters.get("source_verifications", 0)
        c.feed_builds += build_counters.get("feed_builds", 0)
        c.cache_build_events = build_counters.get("cache_build_events", c.cache_build_events)
        c.sort_spill_runs = build_counters.get("sort_spill_runs", c.sort_spill_runs)
        c.cache_reused = prepared.warm
        c.preparation = {k: build_counters[k] for k in ("sort", "durability", "cache_quarantined",
                                                         "bridge_first_completions") if k in build_counters}
        c.feed_events = prepared.cache.event_count
        cache = prepared.cache
        if configured:
            eng = row["engine"] or {}
            if (eng.get("cache_id") != cache.cache_id or eng.get("cache_manifest_sha256") != cache.manifest_sha256
                    or prepared.receipt["cache_manifest_sha256"] != eng.get("cache_manifest_sha256")):
                raise SourceRejected(f"feed cache {cache.cache_id} differs from the cache pinned at preparation "
                                     f"({eng.get('cache_id')}); the run cannot continue on different input")
            if feed_identity(prepared.loaded.feed) != cfg.feed:
                raise SourceRejected("feed identity differs from the identity recorded at preparation")
            return prepared
        from .control import build_config

        config = build_config(self.rid, prepared.loaded)
        engine = {
            "format": ENGINE_FORMAT, "state_format": STATE_FORMAT, "cache_format": CACHE_FORMAT,
            "commitment_format": COMMITMENT_FORMAT, "cache_id": cache.cache_id,
            "cache_manifest_sha256": cache.manifest_sha256, "partition_events": cache.manifest["partition_events"],
            "source_manifest_sha256": prepared.source_manifest_sha256,
            "fingerprint": fingerprint(cache.cache_id, config.freshness_policy, ENGINE_FORMAT),
            "temporal": temporal_config(cache.feed_manifest),
            "pack": ({"pack_id": source_id, "pack_manifest_sha256": prepared.source_manifest_sha256}
                     if kind == SourceKind.PACK else None),
            "checkpoint_policy": {"active_seconds": self.spec.checkpoint_seconds,
                                  "events": self.spec.checkpoint_events, "control_poll_seconds": self.spec.control_poll,
                                  "retained_restore_points": 2},
            "cache_reused_at_preparation": prepared.warm,
        }
        cond, args = self.fence
        done = self.conn.execute(
            f"""UPDATE observation_replays SET config = %s, total_events = %s, engine = %s, engine_format = %s
                WHERE {cond} AND config IS NULL RETURNING 1""",
            (Jsonb(json.loads(config.model_dump_json())), config.feed.event_count, Jsonb(engine), ENGINE_FORMAT,
             *args),
        ).fetchone()
        if done is None:
            raise LeaseLost(self.rid)
        return prepared

    # -- checkpoint / restore -------------------------------------------------------------------

    def checkpoint(self) -> dict[str, Any] | None:
        return self.conn.execute(
            "SELECT cursor, snapshot_digest, snapshot_id, info_time FROM observation_checkpoints WHERE replay_id = %s",
            (self.rid,)).fetchone()

    def _engine(self) -> dict[str, Any]:
        return self.conn.execute("SELECT engine FROM observation_replays WHERE replay_id = %s",
                                 (self.rid,)).fetchone()["engine"]

    def _note(self, entry: dict[str, Any]) -> None:
        cond, args = self.fence
        self.conn.execute(f"UPDATE {self.TABLE} SET diagnostic_log = diagnostic_log || %s WHERE {cond}",
                          (Jsonb([{"at": _now().isoformat(), "generation": self.spec.generation, **entry}]), *args))

    def _restore(self, cache: FeedCache, reader: CacheReader, freshness, reclaimed: bool) -> Kernel:
        """Direct restore from the newest verified restore point; only the bounded suffix is reprocessed."""
        engine = self._engine()
        ck = self.checkpoint()
        if ck is None:
            self._restoring = False
            self.enter_phase("INITIALIZING", detail="initial observable state (cursor 0)")
            kernel = Kernel(cache.feed_meta, freshness, None, initial_commitment(cache.cache_id),
                            new_temporal(cache.feed_manifest, engine))
            snap = kernel.snapshot()
            blob, sha = kernel.pack()
            cond, args = self.fence
            with self.conn.transaction():
                if self.conn.execute(f"SELECT 1 FROM observation_replays WHERE {cond} FOR UPDATE", args).fetchone() is None:
                    raise LeaseLost(self.rid)
                self.conn.execute(
                    """INSERT INTO observation_checkpoints
                           (replay_id, cursor, info_time, last_event_id, snapshot_id, snapshot_digest, snapshot_view,
                            temporal_view)
                       VALUES (%s, 0, %s, NULL, %s, %s, %s, %s) ON CONFLICT (replay_id) DO NOTHING""",
                    (self.rid, snap.as_of, snap.snapshot_id, snap.content_digest, Jsonb(snapshot_view(snap)),
                     Jsonb(kernel.temporal.summary()) if kernel.temporal is not None else None))
                self._insert_restore_point(kernel, snap, blob, sha, engine)
            self.counters.transactions_committed += 1
            return kernel
        target = ck["cursor"]
        self._restoring = reclaimed and target > 0
        self.enter_phase("INITIALIZING", detail=f"direct restore at committed cursor {target}")
        points = self.conn.execute(
            "SELECT * FROM observation_restore_points WHERE replay_id = %s AND cursor <= %s ORDER BY cursor DESC",
            (self.rid, target)).fetchall()
        kernel = None
        for rp in points:
            try:
                if rp["state_format"] != STATE_FORMAT or rp["fingerprint"] != engine["fingerprint"]:
                    raise StateError(f"format/compatibility fingerprint mismatch at cursor {rp['cursor']}")
                state = unpack_state(bytes(rp["state_blob"]), rp["state_sha256"])
                temporal = restore_temporal(rp, engine)
                if state.cursor.applied_events != rp["cursor"]:
                    raise StateError(f"state cursor {state.cursor.applied_events} != restore point {rp['cursor']}")
                expected = (initial_commitment(cache.cache_id).hex() if rp["cursor"] == 0 else
                            (self.conn.execute("SELECT commitment_after FROM observation_ranges WHERE replay_id = %s "
                                               "AND to_cursor = %s", (self.rid, rp["cursor"])).fetchone() or {})
                            .get("commitment_after"))
                if rp["commitment"] != expected:
                    raise StateError(f"restore point {rp['cursor']} commitment does not match its committed range")
                kernel = Kernel(cache.feed_meta, freshness, state, bytes.fromhex(rp["commitment"]), temporal)
                break
            except StateError as exc:
                self.counters.restore_fallbacks += 1
                self._note({"event": "restore_point_rejected", "cursor": rp["cursor"], "detail": str(exc)})
        if kernel is None:
            raise _UnsafeRecovery(f"no valid restore checkpoint at or before committed cursor {target} "
                                  f"({len(points)} candidate(s) rejected); an explicit rebuild would be required - "
                                  "nothing was replayed from zero")
        if kernel.cursor < target:  # bounded uncommitted-suffix reprocessing after a fallback
            for seq, line in reader.iter_from(kernel.cursor):
                if seq >= target:
                    break
                kernel.apply_line(line)
                self.counters.source_records_read += 1
                self.counters.restore_suffix_events += 1
                self.hook("reapply committed suffix", self.counters.restore_suffix_events, None, "events")
            expected = self.conn.execute("SELECT commitment_after, temporal_sha256 FROM observation_ranges WHERE "
                                         "replay_id = %s AND to_cursor = %s", (self.rid, target)).fetchone()
            if expected is None or kernel.commitment.hex() != expected["commitment_after"]:
                raise _UnsafeRecovery(f"suffix reprocessing to cursor {target} does not reproduce the committed "
                                      "input commitment; recovery is not safe")
            if kernel.temporal is not None and kernel.pack_temporal()[1] != expected["temporal_sha256"]:
                raise _UnsafeRecovery(f"suffix reprocessing to cursor {target} does not reproduce the committed "
                                      "temporal state; recovery is not safe")
            self._note({"event": "restore_fallback", "restored_cursor": target - self.counters.restore_suffix_events,
                        "committed_cursor": target, "suffix_events": self.counters.restore_suffix_events,
                        "detail": "newest restore point rejected; restored an older verified point and reprocessed "
                                  "only the bounded suffix"})
        snap = kernel.snapshot()
        if snap.content_digest != ck["snapshot_digest"]:
            raise _UnsafeRecovery(f"restored state at cursor {target} has snapshot digest {snap.content_digest[:16]}, "
                                  f"committed {ck['snapshot_digest'][:16]}; recovery is not safe")
        return kernel

    def _insert_restore_point(self, kernel: Kernel, snap, blob: bytes, sha: str, engine: dict[str, Any],
                              temporal: tuple[bytes, str] | None = None) -> None:
        if kernel.temporal is not None and temporal is None:
            temporal = kernel.pack_temporal()
        self.conn.execute(
            """INSERT INTO observation_restore_points (replay_id, cursor, generation, state_format, fingerprint,
                   state_blob, state_sha256, snapshot_id, snapshot_digest, info_time, commitment, temporal_format,
                   temporal_blob, temporal_sha256)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (self.rid, kernel.cursor, self.spec.generation, STATE_FORMAT, engine["fingerprint"], blob, sha,
             snap.snapshot_id, snap.content_digest, snap.as_of, kernel.commitment.hex(),
             temporal_engine.STATE_FORMAT if temporal else None, temporal[0] if temporal else None,
             temporal[1] if temporal else None))
        # retention: the latest two non-terminal restore points (plus any terminal one), atomically
        self.conn.execute(
            """DELETE FROM observation_restore_points WHERE replay_id = %s AND NOT terminal AND cursor < (
                   SELECT min(cursor) FROM (SELECT cursor FROM observation_restore_points
                                            WHERE replay_id = %s AND NOT terminal ORDER BY cursor DESC LIMIT 2) k)""",
            (self.rid, self.rid))
        self.counters.checkpoint_state_bytes = len(blob)
        if temporal:
            self.counters.checkpoint_temporal_bytes = len(temporal[0])

    def control(self) -> dict[str, Any]:
        cond, args = self.fence
        row = self.conn.execute(f"SELECT {self.CONTROLS} FROM {self.TABLE} WHERE {cond}", args).fetchone()
        if row is None:
            raise LeaseLost(self.rid)
        return row

    def commit_checkpoint(self, kernel: Kernel, from_cursor: int, commit_before: bytes, first_order: str,
                          last_order: str, engine: dict[str, Any], consume_step: bool = False) -> dict[str, Any]:
        """One fenced transaction: CAS cursor, compact range, restore point (+ retention), snapshot view."""
        snap = kernel.snapshot()
        blob, sha = kernel.pack()
        tblob = kernel.pack_temporal()
        tview = kernel.temporal.summary() if kernel.temporal is not None else None
        tcols = ((tblob[1], kernel.temporal.commitment(), kernel.temporal.aggregate_chain, kernel.temporal.dispatch_seq)
                 if tblob is not None else (None, None, None, None))
        conn = self.conn
        cond, args = self.fence
        with conn.transaction():
            fence = conn.execute(
                f"""UPDATE observation_replays SET interruptions = 0, last_progress_at = now(),
                        progress_seq = progress_seq + 1,
                        step_budget = CASE WHEN %s THEN greatest(step_budget - 1, 0) ELSE step_budget END
                    WHERE {cond} RETURNING {_CONTROL_COLUMNS}""",
                (consume_step, *args)).fetchone()
            if fence is None:
                raise LeaseLost(self.rid)
            last = kernel.state.cursor
            cas = conn.execute(
                """UPDATE observation_checkpoints SET cursor = %s, info_time = %s, last_event_id = %s,
                       snapshot_id = %s, snapshot_digest = %s, snapshot_view = %s, temporal_view = %s,
                       updated_at = now()
                   WHERE replay_id = %s AND cursor = %s""",
                (kernel.cursor, snap.as_of, last.last_event_id, snap.snapshot_id, snap.content_digest,
                 Jsonb(snapshot_view(snap)), Jsonb(tview) if tview is not None else None, self.rid, from_cursor))
            if cas.rowcount == 0:
                raise _UnsafeRecovery(f"committed cursor is no longer {from_cursor}; refusing to commit a range")
            conn.execute(
                """INSERT INTO observation_ranges (replay_id, range_seq, generation, from_cursor, to_cursor,
                       event_count, first_order, last_order, commitment_before, commitment_after, snapshot_digest,
                       state_sha256, temporal_sha256, temporal_commitment, aggregate_chain, dispatch_seq)
                   VALUES (%s, (SELECT coalesce(max(range_seq) + 1, 0) FROM observation_ranges WHERE replay_id = %s),
                           %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (self.rid, self.rid, self.spec.generation, from_cursor, kernel.cursor, kernel.cursor - from_cursor,
                 first_order, last_order, commit_before.hex(), kernel.commitment.hex(), snap.content_digest, sha,
                 *tcols))
            self._insert_restore_point(kernel, snap, blob, sha, engine, tblob)
            if self.before_commit is not None:
                self.before_commit(self.rid, kernel.cursor)
        self.counters.transactions_committed += 1
        self.counters.checkpoints_committed += 1
        self.counters.ranges_committed += 1
        self.counters.max_checkpoint_gap_events = max(self.counters.max_checkpoint_gap_events,
                                                      kernel.cursor - from_cursor)
        if self.after_commit is not None:
            self.after_commit(self.rid, kernel.cursor)
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
        row = self.conn.execute(f"SELECT phase_started_at FROM {self.TABLE} WHERE {self.KEY} = %s",
                                (self.rid,)).fetchone()
        return row["phase_started_at"] if row else None

    # -- processing ---------------------------------------------------------------------------

    def process(self, row: dict[str, Any]) -> None:
        reclaimed = bool(row["recovery_log"]) and \
            row["recovery_log"][-1].get("generation") == self.spec.generation
        self._restoring = reclaimed and row["config"] is not None
        cache: FeedCache | None = None
        try:
            try:
                prepared = self._prepare(row)
            except OperationCancelled:
                self.finalize(ReplayStatus.CANCELLED, "cancelled by user during source preparation", None,
                              reload=False)
                return
            except SourceRejected as exc:
                self.finalize(ReplayStatus.FAILED, f"source not replayable: {exc}", None, reload=False)
                return
            cache = prepared.cache
            row = self._row()
            cfg = ObservationReplayConfig.model_validate(row["config"])
            engine = row["engine"]
            reader = CacheReader(cache, self._reader_counters)
            try:
                kernel = self._restore(cache, reader, cfg.freshness_policy, reclaimed)
            except OperationCancelled:
                self.finalize(ReplayStatus.CANCELLED, "cancelled by user during initialization", None)
                return
            self._kernel = kernel
            self._cancellable = False  # replay controls are polled below
            self._restoring = False
            self._replay(kernel, cache, reader, engine)
        except CacheError as exc:
            log.error("%s: %s", self.rid, exc)
            moved = quarantine(cache, str(exc)) if cache is not None else None
            self.finalize(ReplayStatus.FAILED, f"feed cache rejected: {exc}" + (
                f" (quarantined as {moved.name}; the next launch rebuilds it from the verified source)"
                if moved else ""), None, reload=False)
        except (_UnsafeRecovery, FeedError, StateError, TemporalError) as exc:
            log.error("%s: %s", self.rid, exc)
            self.finalize(ReplayStatus.FAILED, f"{type(exc).__name__}: {exc}", None, reload=False)
        except (LeaseLost, SimulatedCrash, psycopg.OperationalError):
            raise
        except Exception as exc:  # deterministic processing/persistence error -> explicit failure
            log.exception("%s failed", self.rid)
            self.finalize(ReplayStatus.FAILED, f"{type(exc).__name__}: {exc}", None, reload=False)

    @property
    def _reader_counters(self) -> dict[str, Any]:
        if not hasattr(self, "_rc"):
            self._rc: dict[str, Any] = {}
        return self._rc

    def _sync_counters(self, kernel: Kernel | None) -> None:
        c = self.counters
        if kernel is not None:
            for k in ("events_decoded", "events_applied", "snapshots_built", "state_encodes"):
                setattr(c, k, kernel.counters[k])
        c.cache_bytes_read = self._reader_counters.get("cache_bytes_read", 0)
        c.cache_partitions_read = self._reader_counters.get("cache_partitions_read", 0)

    def _metrics_doc(self) -> dict[str, Any]:
        self._sync_counters(getattr(self, "_kernel", None))
        return {str(self.spec.generation): {**self.counters.doc(), **ops.process_metrics(),
                                            "pid": os.getpid(), "recorded_at": _now().isoformat()}}

    def _replay(self, kernel: Kernel, cache: FeedCache, reader: CacheReader, engine: dict[str, Any]) -> None:
        total = cache.event_count
        ctl = self.control()
        speed = ctl["speed"]
        stall = max(self.spec.stall_limit or ops.STALL_LIMITS["REPLAYING"], 3.0 / speed if speed > 0 else 0)
        self.enter_phase("REPLAYING", detail="streaming kernel: every event applied; committed at checkpoints",
                         stall_limit=stall, total=total, done=kernel.cursor, unit="events",
                         checkpoint_policy=engine["checkpoint_policy"])
        committed = kernel.cursor
        commit_before = kernel.commitment
        first_order = last_order = None
        t_ckpt_wall = time.monotonic()
        wait_at_ckpt = self._phase_wait
        t_poll = time.monotonic()

        def checkpoint(consume_step: bool = False) -> dict[str, Any] | None:
            nonlocal committed, commit_before, first_order, last_order, t_ckpt_wall, wait_at_ckpt
            if kernel.cursor == committed:
                return None
            got = self.commit_checkpoint(kernel, committed, commit_before, first_order, last_order, engine,
                                         consume_step)
            committed, commit_before, first_order, last_order = kernel.cursor, kernel.commitment, None, None
            t_ckpt_wall, wait_at_ckpt = time.monotonic(), self._phase_wait
            return got

        it = reader.iter_from(kernel.cursor)
        while True:
            now = time.monotonic()
            gap = now - t_poll
            if gap >= self.spec.control_poll or ctl["paused"]:
                self.counters.max_control_gap_seconds = max(self.counters.max_control_gap_seconds, gap)
                ctl = self.control()
                t_poll = time.monotonic()
            if ctl["cancel_requested"]:
                checkpoint()  # the accepted prefix is committed at this boundary
                self.finalize(ReplayStatus.CANCELLED, "cancelled by user before completion", None)
                return
            if ctl["paused"] and ctl["step_budget"] == 0:
                checkpoint()
                if self.park(kernel.cursor):
                    log.info("%s paused at cursor %s; parked", self.rid, kernel.cursor)
                    return
                ctl = self.control()
                continue
            stepping = bool(ctl["paused"])  # while paused only a STEP grant allows exactly one event
            try:
                seq, line = next(it)
            except StopIteration:
                break
            if seq != kernel.cursor:  # runtime admission check: total-order position continuity
                raise FeedError(f"admission discontinuity: cache position {seq} != kernel cursor {kernel.cursor}")
            e = kernel.apply_line(line)
            self.counters.source_records_read += 1
            key = order_sort_key(e).decode().replace("\x00", "|")
            first_order = first_order or key
            last_order = key
            if stepping:
                got = checkpoint(consume_step=True)  # STEP: exactly one source event, durably committed
                ctl = got or ctl
                t_poll = time.monotonic()
                continue
            active_since = (time.monotonic() - t_ckpt_wall) - (self._phase_wait - wait_at_ckpt)
            wall_since = time.monotonic() - t_ckpt_wall
            if (kernel.cursor - committed >= self.spec.checkpoint_events or active_since >= self.spec.checkpoint_seconds
                    or (ctl["speed"] > 0 and wall_since >= self.spec.checkpoint_seconds)):
                got = checkpoint()
                ctl = got or ctl
                t_poll = time.monotonic()
            self.milestone("apply feed events", kernel.cursor, total, "events", committed_cursor=committed)
            if ctl["speed"] > 0:
                ctl = self._pace(ctl)
                t_poll = time.monotonic()
        checkpoint()
        ctl = self.control()
        if ctl["cancel_requested"]:
            self.finalize(ReplayStatus.CANCELLED, "cancelled by user before completion", None)
            return
        self.finalize(ReplayStatus.COMPLETED, None, None)

    def _pace(self, ctl: dict[str, Any]) -> dict[str, Any]:
        """Sleep at the persisted pacing (events/s); re-read control every chunk. Never affects state."""
        waited = 0.0
        while not (ctl["cancel_requested"] or ctl["paused"]):
            interval = 1.0 / ctl["speed"] if ctl["speed"] > 0 else 0.0
            if waited >= interval - 1e-9:
                break
            chunk = min(interval - waited, self.spec.control_poll)
            self.sleep(chunk)
            waited += chunk
            self._phase_wait += chunk  # declared wait: excluded from active time
            self.counters.pacing_sleep_seconds += chunk
            ctl = self.control()
        return ctl

    # -- completion ---------------------------------------------------------------------------

    def finalize(self, status: ReplayStatus, error: str | None, source: Any = None, reload: bool = True) -> None:
        """Terminal phases. Every non-COMPLETED outcome, and any observed cancellation, finishes on the bounded
        path (config + committed checkpoint facts). COMPLETED runs: FINALIZING -> VALIDATING (bounded stream
        reconciliation) -> GENERATING_REPORT, published under the replay row lock."""
        row = self._row()
        self._row_cache = row
        self._restoring = False
        if row["config"] is None:
            self._terminal(status, error, None, {"state": ops.Assurance.NOT_CHECKED.value,
                                                 "detail": "the source was never prepared: nothing to validate"})
            return
        ck = self.checkpoint()
        cursor = ck["cursor"] if ck else 0
        if status != ReplayStatus.COMPLETED or self._cancel_requested():
            self._finalize_bounded(status, error, ck, self._phase or "QUEUED",
                                   cancelled=status != ReplayStatus.FAILED)
            return
        self._cancellable, self._cancel_consumed, self.cancel_seen = True, False, False
        self._progress_target(status, cursor, row["total_events"])
        engine = row["engine"]
        cfg = ObservationReplayConfig.model_validate(row["config"])
        staged: StagedArtifacts | None = None
        try:
            self.enter_phase("FINALIZING", detail="sealing the terminal checkpoint and compact range records",
                             finalizing_as=status.value, cursor=cursor, total_events=row["total_events"])
            cond, args = self.fence
            self.conn.execute(
                f"""UPDATE observation_restore_points SET terminal = true WHERE replay_id = %s AND cursor = %s
                    AND EXISTS (SELECT 1 FROM observation_replays WHERE {cond})""", (self.rid, cursor, *args))
            ranges = self.conn.execute("SELECT * FROM observation_ranges WHERE replay_id = %s ORDER BY from_cursor",
                                       (self.rid,)).fetchall()
            terminal = self.conn.execute("SELECT * FROM observation_restore_points WHERE replay_id = %s AND cursor = %s",
                                         (self.rid, cursor)).fetchone()
            self.hook("load committed range records", len(ranges), len(ranges), "ranges")
            cache = open_cache(self.data_root, engine["cache_id"], expected_manifest_sha256=engine["cache_manifest_sha256"])
            from .contracts import VALIDATOR_ID  # noqa: F401 - revision-1 validator id kept for old runs
            from .reconcile import VALIDATOR_ID as RID
            from .reconcile import VALIDATOR_SCOPE as RSCOPE
            from .reconcile import VALIDATOR_VERSION as RVER
            from .reconcile import reconcile

            self._set_assurance({"state": ops.Assurance.INCOMPLETE.value, "detail": "reconciliation in progress",
                                 "validator": RID, "validator_version": RVER, "scope": RSCOPE})
            self.enter_phase("VALIDATING", finalizing_as=status.value, cursor=cursor, total_events=row["total_events"])

            def vhook(stage: str, done: int, total: int | None, unit: str) -> None:
                try:
                    self.hook(stage, done, total, unit)
                except OperationCancelled:
                    self._cancel_consumed = True
                    raise

            receipt = self.conn.execute("SELECT * FROM observation_feed_caches WHERE cache_id = %s",
                                        (engine["cache_id"],)).fetchone()
            temporal_doc: dict[str, Any] | None = {} if engine.get("temporal") else None
            pack_facts = self._pack_facts(engine)
            validation, snap = reconcile(status=status, cache=cache, ranges=ranges, cursor=cursor, terminal=terminal,
                                         committed_snapshot_digest=ck["snapshot_digest"], engine=engine,
                                         freshness=cfg.freshness_policy, hook=vhook, receipt=receipt,
                                         temporal_out=temporal_doc, pack=pack_facts)
            if validation.outcome == ValidationOutcome.INCOMPLETE:
                status = ReplayStatus.CANCELLED
                error = ("cancelled by user during VALIDATING: the replay cursor was complete, but reconciliation did "
                         "not finish; assurance INCOMPLETE")
            self.enter_phase("GENERATING_REPORT", finalizing_as=status.value, cursor=cursor,
                             total_events=row["total_events"])
            if self.spec.faults.get("publish_error"):
                raise OSError("simulated artifact publication failure (test fault)")
            staged = stage_stream_artifacts(
                self.artifact_root, row, status, error, _now(), cursor, ranges, engine, validation, snap,
                ck["snapshot_digest"], generation=self.spec.generation, hook=self.hook, timings=self._timings,
                metrics=lambda: self._metrics_doc()[str(self.spec.generation)], temporal=temporal_doc or None)
            self.counters.output_bytes = staged.output_bytes
            m = staged.manifest
            v = m.validation
            assurance = {"state": (v.outcome or ValidationOutcome.FAILED).value, "validator": v.validator,
                         "validator_version": v.validator_version, "scope": v.scope,
                         "checks_passed": sum(1 for c in v.checks if c.passed), "checks_total": len(v.checks)}
            self._terminal(m.status, m.error, m, assurance, expected_cursor=cursor, staged=staged,
                           abort_if_cancelled=m.status == ReplayStatus.COMPLETED and not self._cancel_consumed)
        except OperationCancelled as exc:
            if staged is not None:
                staged.discard()
            self._finalize_bounded(status, error, ck, f"{self._phase} ({exc})", cancelled=True)
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

    def _pack_facts(self, engine: dict[str, Any]) -> dict[str, Any] | None:
        """Pack pins re-read at finalization (manifest file, publication receipt) for reconciliation."""
        pin = engine.get("pack")
        if not pin:
            return None
        import hashlib

        from ..corpus.pack import packs_root

        path = packs_root(self.data_root) / pin["pack_id"] / "manifest.json"
        try:
            raw = path.read_bytes()
            file_sha, doc = hashlib.sha256(raw).hexdigest(), json.loads(raw)
        except (OSError, ValueError):
            file_sha, doc = None, None
        receipt = self.conn.execute("SELECT * FROM corpus_packs WHERE pack_id = %s", (pin["pack_id"],)).fetchone()
        return {"pin": pin, "file_sha256": file_sha, "manifest": doc, "receipt": receipt}

    def _progress_target(self, status: ReplayStatus, cursor: int, total: int | None) -> None:
        self._progress = {**self._progress, "finalizing_as": status.value, "cursor": cursor, "total_events": total}

    def _finalize_bounded(self, status: ReplayStatus, error: str | None, ck: dict[str, Any] | None,
                          where: str, cancelled: bool = True) -> None:
        """Bounded terminal path (observed cancellation, or a failure): config + committed checkpoint facts only."""
        where_reason = f"cancellation observed during {where}"
        row = self._row()
        self._row_cache = row
        cursor = ck["cursor"] if ck else 0
        total = row["total_events"]
        full = ck is not None and total is not None and cursor == total
        if status == ReplayStatus.FAILED and not cancelled:
            final, err = ReplayStatus.FAILED, error or "failed"
            where_reason = f"failure during {where}"
        elif status == ReplayStatus.FAILED:
            final, err = ReplayStatus.FAILED, (f"{error}; cancellation requested during {where}: the terminal "
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
        self.enter_phase("GENERATING_REPORT", detail="bounded terminal report (config + checkpoint facts only)",
                         finalizing_as=final.value, cursor=cursor, total_events=total)
        staged = stage_bounded_artifacts(
            self.artifact_root, row, final, err, _now(), cursor, ck_full, where_reason,
            generation=self.spec.generation, timings=self._timings,
            metrics=lambda: self._metrics_doc()[str(self.spec.generation)])
        self.counters.output_bytes = staged.output_bytes
        try:
            self._terminal(final, err, staged.manifest,
                           {"state": ops.Assurance.INCOMPLETE.value, "validator": staged.manifest.validation.validator,
                            "validator_version": staged.manifest.validation.validator_version,
                            "scope": staged.manifest.validation.scope,
                            "detail": f"bounded terminal path ({where_reason}); terminal validation not run"},
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
    if spec.kind == "deep":
        from .deep import DeepJob

        job = DeepJob(spec)
    else:
        job = ReplayJob(spec)
    try:
        job.run()
    except psycopg.OperationalError as exc:
        log.error("%s: database unavailable in compute process: %s", spec.replay_id, exc)
        os._exit(EXIT_DB_UNAVAILABLE)
