"""Optional Deep validation of a streaming observation run (validator ``observe.deep-reference`` v1).

An explicitly launched, durable diagnostic job linked to one terminal (or parked) streaming run. It is never
started automatically and is never required for a normal report. It re-executes the run's admitted prefix with
a SEPARATE reference loop - its own sequential fold with the accepted pure reducer ``feed.state.apply`` and
snapshot function, starting from the initial state, without the production kernel's checkpoint / restore /
commit path - and compares, at every committed range boundary and retained restore point:

* the rolling input commitment (which bytes were consumed),
* the restorable-state SHA-256 (explicit state codec) and
* the materialized observable-snapshot digest

with what the run committed. Coverage, comparison cursors and scope are disclosed. It examines the run's
**canonical feed cache** (receipt- and pin-checked); it does not re-normalize the original source package, so
it is not an independent source audit, and it shares the accepted reducer code.

Input is streamed partition by partition; reference state is bounded by the history limit. Diagnostic state
(cursor, commitment, explicit state, comparisons so far) is saved every ``SAVE_EVENTS`` events / ``SAVE_SECONDS``,
so a reclaimed or resumed job continues from there (pause parks there). Results are stored only in the
diagnostic row; the originating run's records, artifacts and terminal report are never modified. A mismatch
becomes a persistent linked assurance warning shown with the run.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from psycopg.types.json import Jsonb

from .. import ops
from ..feed.contracts import FeedEvent
from ..feed.state import apply, initial_state, snapshot
from ..ops import OperationCancelled
from .contracts import ObservationReplayConfig
from .feedcache import CacheError, CacheReader, extend_commitment, initial_commitment, open_cache
from .job import JobSpec, LeaseLost, ReplayJob
from .kernel import pack_state, unpack_state

log = logging.getLogger("algotrader.observe.deep")
VALIDATOR_ID = "observe.deep-reference"
VALIDATOR_VERSION = "1"
SCOPE = (
    "Reference re-execution of the run's committed admitted prefix from the initial state, using its "
    "own sequential fold of the accepted pure reducer and snapshot function (not the production kernel, "
    "checkpoint, restore or commit path), compared with every committed range boundary (input commitment, "
    "state SHA-256, snapshot digest where recorded) and every retained restore point. Input: the run's receipt- "
    "and pin-checked canonical feed cache; the original source package is NOT re-normalized, so this is not an "
    "independent source audit, and the reducer code is shared with the engine, so it is not a wholly independent "
    "method.")
SAVE_EVENTS = 5000
SAVE_SECONDS = 2.0
MAX_MISMATCHES = 20
TERMINAL = ("completed", "cancelled", "failed")


def new_validation_id() -> str:
    import uuid

    return f"deep-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


class DeepRejected(Exception):
    pass


def create_deep_validation(conn, replay_id: str) -> str:
    """Durable launch (<=1 s): pin the run's committed boundary; no expensive work here."""
    import psycopg

    row = conn.execute(
        "SELECT r.*, c.cursor FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id) "
        "WHERE replay_id = %s", (replay_id,)).fetchone()
    if row is None:
        raise LookupError(replay_id)
    if row.get("engine_format") != "observe.stream.v1" or row["engine"] is None:
        raise DeepRejected("Deep validation applies to streaming-engine runs (observe.stream.v1) only")
    if row["status"] not in ("completed", "cancelled", "failed", "paused"):
        raise DeepRejected(f"the run is {row['status']}; Deep validation runs on a finished or paused run")
    if not row["cursor"]:
        raise DeepRejected("the run has no committed events to validate")
    eng = row["engine"]
    plan = {"replay_id": replay_id, "committed_cursor": row["cursor"], "total_events": row["total_events"],
            "run_status_at_launch": row["status"], "cache_id": eng["cache_id"],
            "cache_manifest_sha256": eng["cache_manifest_sha256"], "state_format": eng["state_format"],
            "validator": VALIDATOR_ID, "validator_version": VALIDATOR_VERSION, "mode": "canonical-cache-only",
            "scope": SCOPE}
    vid = new_validation_id()
    conn.commit()  # end the read transaction: the launch below is its own committed transaction
    try:
        with conn.transaction():
            conn.execute(
                """INSERT INTO observation_deep_validations (validation_id, replay_id, status, plan, progress)
                   VALUES (%s, %s, 'queued', %s, %s)""",
                (vid, replay_id, Jsonb(plan), Jsonb({"waiting": "queued: waiting for an observation worker"})))
    except psycopg.errors.UniqueViolation:
        raise DeepRejected("a Deep validation of this run is already queued, running or paused") from None
    return vid


def control(conn, validation_id: str, command: str) -> None:
    with conn.transaction():
        row = conn.execute("SELECT status, paused, cancel_requested FROM observation_deep_validations "
                           "WHERE validation_id = %s FOR UPDATE", (validation_id,)).fetchone()
        if row is None:
            raise LookupError(validation_id)
        if row["status"] in TERMINAL:
            raise DeepRejected(f"Deep validation already {row['status']}")
        entry = Jsonb([{"at": datetime.now(UTC).isoformat(), "command": command}])
        if command == "cancel":
            conn.execute("UPDATE observation_deep_validations SET cancel_requested = true, "
                         "control_log = control_log || %s WHERE validation_id = %s", (entry, validation_id))
        elif command == "pause":
            if row["cancel_requested"]:
                raise DeepRejected("cancellation already requested")
            conn.execute("UPDATE observation_deep_validations SET paused = true, control_log = control_log || %s "
                         "WHERE validation_id = %s", (entry, validation_id))
        elif command == "resume":
            if not row["paused"]:
                raise DeepRejected("not paused")
            conn.execute("UPDATE observation_deep_validations SET paused = false, control_log = control_log || %s, "
                         "status = CASE WHEN status = 'paused' THEN 'queued' ELSE status END "
                         "WHERE validation_id = %s", (entry, validation_id))
        else:
            raise DeepRejected(f"unknown command {command}")


class DeepJob(ReplayJob):
    TABLE = "observation_deep_validations"
    KEY = "validation_id"
    CONTROLS = "cancel_requested, paused"

    def __init__(self, spec: JobSpec, **kw: Any) -> None:
        super().__init__(spec, **kw)
        self.counters_deep = {"events_reexecuted": 0, "snapshots_built": 0, "state_encodes": 0, "saves": 0,
                              "resumed_from": 0, "cache_bytes_read": 0}

    def _metrics_doc(self) -> dict[str, Any]:  # noqa: D401 - deep-specific counters
        return {str(self.spec.generation): {**self.counters_deep, **ops.process_metrics()}}

    def run(self) -> None:
        try:
            row = self._row()
            self._row_cache = row
            if self.spec.finalize:
                self._finish(self.spec.finalize, self.spec.finalize_error, incomplete=True)
                return
            self._validate(row)
        except LeaseLost:
            log.warning("%s g%s: lease lost (fenced)", self.rid, self.spec.generation)
        finally:
            self.close()

    # -- persistence ------------------------------------------------------------------------

    def _save(self, cursor: int, commitment: bytes, state, comparisons: dict[str, Any]) -> None:
        blob, sha = pack_state(state)
        cond, args = self.fence
        done = self.conn.execute(
            f"""UPDATE observation_deep_validations SET resume_cursor = %s, resume_commitment = %s,
                    resume_state = %s, resume_state_sha = %s, comparisons = %s, last_progress_at = now(),
                    progress_seq = progress_seq + 1
                WHERE {cond} RETURNING 1""",
            (cursor, commitment.hex(), blob, sha, Jsonb(comparisons), *args)).fetchone()
        if done is None:
            raise LeaseLost(self.rid)
        self.counters_deep["saves"] += 1

    @staticmethod
    def _incomplete_result(row: dict[str, Any], outcome: str, detail: str | None) -> dict[str, Any]:
        comparisons = row["comparisons"] or {}
        return {"outcome": outcome, "validator": VALIDATOR_ID, "validator_version": VALIDATOR_VERSION, "scope": SCOPE,
                "compared": comparisons.get("compared", 0), "mismatches": comparisons.get("mismatches", []),
                "covered_events": row["resume_cursor"], "target_events": row["plan"]["committed_cursor"],
                "run_total_events": row["plan"].get("total_events"), "detail": detail}

    def _finish(self, status: str, error: str | None, *, incomplete: bool = False,
                result: dict[str, Any] | None = None) -> None:
        """Fenced terminal commit, serialized with ``control`` by the diagnostic row lock.

        ``control`` locks the same row and rejects terminal jobs, so a cancel is ordered strictly before or after
        this commit: a cancel that wins the lock turns a would-be COMPLETED result into CANCELLED / INCOMPLETE
        (no conclusion about the run); a cancel arriving after the commit is rejected (already terminal).
        Inline test seams: ``before_commit(id, -1)`` before the lock, ``(id, -2)`` while holding it,
        ``after_commit(id, -1)`` after the commit."""
        cond, args = self.fence
        if self.before_commit is not None:
            self.before_commit(self.rid, -1)  # test seam: just before the terminal lock
        with self.conn.transaction():
            row = self.conn.execute(f"SELECT * FROM observation_deep_validations WHERE {cond} FOR UPDATE",
                                    args).fetchone()
            if row is None:
                raise LeaseLost(self.rid)
            if self.before_commit is not None:
                self.before_commit(self.rid, -2)  # test seam: holding the terminal lock
            if row["cancel_requested"] and status == "completed":
                where = self._phase or "the terminal boundary"
                status = "cancelled"
                error = (f"cancelled by user during {where}, before the terminal commit: the reference execution "
                         f"covered {row['resume_cursor']}/{row['plan']['committed_cursor']} events, but the "
                         "validation did not finish; INCOMPLETE (no conclusion about the run)")
                result = self._incomplete_result(row, "incomplete", error)
            elif result is None:
                result = self._incomplete_result(row, "incomplete" if incomplete else "error", error)
            closing = [self._closed(self._phase, self._phase_started())] if self._phase else []
            self.conn.execute(
                f"""UPDATE observation_deep_validations SET status = %s, error = %s, result = %s, finished_at = now(),
                        lease_owner = NULL, lease_expires_at = NULL, heartbeat_at = now(),
                        phase_history = phase_history || %s, phase_started_at = NULL, progress = progress || %s,
                        metrics = metrics || %s
                    WHERE {cond}""",
                (status, error, Jsonb(result), Jsonb(closing), Jsonb({"waiting": None}),
                 Jsonb(self._metrics_doc()), *args))
        if self.after_commit is not None:
            self.after_commit(self.rid, -1)  # test seam: just after the terminal commit
        log.info("%s finished %s (%s)", self.rid, status, result.get("outcome"))

    def _cancel_now(self, cursor: int, commitment: bytes | None, state, comparisons: dict[str, Any] | None,
                    target: int) -> None:
        """Bounded cancellation: save what was computed (if anything) and finish CANCELLED / INCOMPLETE."""
        if state is not None and commitment is not None and comparisons is not None:
            self._save(cursor, commitment, state, comparisons)
        self._finish("cancelled", f"cancelled by user during {self._phase} at reference cursor {cursor} of {target}; "
                                  "INCOMPLETE (no conclusion about the run)", incomplete=True)

    def _park(self, cursor: int, commitment: bytes, state, comparisons: dict[str, Any]) -> bool:
        self._save(cursor, commitment, state, comparisons)
        cond, args = self.fence
        closing = [self._closed(self._phase, self._phase_started())] if self._phase else []
        parked = self.conn.execute(
            f"""UPDATE observation_deep_validations SET status = 'paused', lease_owner = NULL, lease_expires_at = NULL,
                    phase_history = phase_history || %s, phase_started_at = NULL,
                    progress = progress || %s
                WHERE {cond} AND paused AND NOT cancel_requested""",
            (Jsonb(closing), Jsonb({"waiting": f"paused at reference cursor {cursor} (resumable)"}), *args)).rowcount
        return bool(parked)

    # -- reference execution ------------------------------------------------------------------

    def _validate(self, row: dict[str, Any]) -> None:
        plan = row["plan"]
        replay = self.conn.execute("SELECT config, engine FROM observation_replays WHERE replay_id = %s",
                                   (plan["replay_id"],)).fetchone()
        cfg = ObservationReplayConfig.model_validate(replay["config"])
        self.enter_phase("PREPARING_SOURCE", detail="open the run's pinned canonical feed cache (pin + receipt)")
        if self.cancel_seen:
            self._cancel_now(0, None, None, None, plan["committed_cursor"])
            return
        receipt = self.conn.execute("SELECT cache_manifest_sha256 FROM observation_feed_caches WHERE cache_id = %s",
                                    (plan["cache_id"],)).fetchone()
        try:
            if receipt is None or receipt["cache_manifest_sha256"] != plan["cache_manifest_sha256"]:
                raise CacheError("the run's cache pin has no matching trusted receipt")
            cache = open_cache(self.data_root, plan["cache_id"], expected_manifest_sha256=plan["cache_manifest_sha256"])
        except CacheError as exc:
            self._finish("failed", f"cannot run Deep validation: {exc} (the cache can be rebuilt by launching a new "
                                   "replay of the same verified source)")
            return
        target = plan["committed_cursor"]
        ranges = self.conn.execute(
            "SELECT range_seq, to_cursor, commitment_after, snapshot_digest, state_sha256 FROM observation_ranges "
            "WHERE replay_id = %s AND to_cursor <= %s ORDER BY to_cursor", (plan["replay_id"], target)).fetchall()
        points = self.conn.execute(
            "SELECT cursor, state_sha256, snapshot_digest, commitment, terminal FROM observation_restore_points "
            "WHERE replay_id = %s AND cursor <= %s", (plan["replay_id"], target)).fetchall()
        expect: dict[int, list[tuple[str, str, str]]] = {}
        for r in ranges:
            expect.setdefault(r["to_cursor"], []).append(("commitment", r["commitment_after"],
                                                          f"range {r['range_seq']}"))
            if r["snapshot_digest"]:
                expect[r["to_cursor"]].append(("snapshot", r["snapshot_digest"], f"range {r['range_seq']}"))
                expect[r["to_cursor"]].append(("state", r["state_sha256"], f"range {r['range_seq']}"))
        for p in points:
            label = "terminal restore point" if p["terminal"] else "restore point"
            expect.setdefault(p["cursor"], []).extend([("commitment", p["commitment"], label),
                                                       ("snapshot", p["snapshot_digest"], label),
                                                       ("state", p["state_sha256"], label)])
        feed_meta = cache.feed_meta
        comparisons = row["comparisons"] or {"compared": 0, "mismatches": []}
        if row["resume_cursor"] and row["resume_state"] is not None:
            state = unpack_state(bytes(row["resume_state"]), row["resume_state_sha"])
            commitment = bytes.fromhex(row["resume_commitment"])
            start = row["resume_cursor"]
            self.counters_deep["resumed_from"] = start
            self._note({"event": "deep_resumed", "cursor": start,
                        "detail": f"resumed the reference execution from saved diagnostic state at cursor {start}"})
        else:
            state = initial_state(feed_meta, cfg.freshness_policy)
            commitment = initial_commitment(cache.cache_id)
            start = 0
        self.enter_phase("VALIDATING", detail="independent reference re-execution of the committed prefix",
                         total=target, done=start, unit="events")
        reader = CacheReader(cache, {})
        last_save, saved_at = start, time.monotonic()
        cursor = start
        if self.cancel_seen:
            self._cancel_now(cursor, None, None, None, target)
            return
        try:
            for seq, line in reader.iter_from(start):
                if seq >= target:
                    break
                e = FeedEvent.model_validate_json(line)
                state = apply(state, e)
                commitment = extend_commitment(commitment, line)
                cursor = seq + 1
                self.counters_deep["events_reexecuted"] += 1
                checks = expect.get(cursor)
                if checks:
                    snap = snapshot(state, e.available_time, feed_meta)
                    self.counters_deep["snapshots_built"] += 1
                    sha = pack_state(state)[1]
                    self.counters_deep["state_encodes"] += 1
                    actual = {"commitment": commitment.hex(), "snapshot": snap.content_digest, "state": sha}
                    for kind, want, label in checks:
                        comparisons["compared"] += 1
                        if want is not None and actual[kind] != want and len(comparisons["mismatches"]) < MAX_MISMATCHES:
                            comparisons["mismatches"].append({"cursor": cursor, "kind": kind, "at": label,
                                                              "expected": want, "reference": actual[kind]})
                self.milestone("reference re-execution", cursor, target, "events")
                if self.cancel_seen:
                    raise OperationCancelled("reference re-execution")
                if cursor - last_save >= SAVE_EVENTS or time.monotonic() - saved_at >= SAVE_SECONDS:
                    ctl = self.control()
                    if ctl["cancel_requested"]:
                        raise OperationCancelled("reference re-execution")
                    if ctl["paused"]:
                        if self._park(cursor, commitment, state, comparisons):
                            return
                    self._save(cursor, commitment, state, comparisons)
                    last_save, saved_at = cursor, time.monotonic()
        except OperationCancelled:
            self._cancel_now(cursor, commitment, state, comparisons, target)
            return
        except CacheError as exc:
            self._finish("failed", f"feed cache rejected during Deep validation: {exc}")
            return
        self.enter_phase("GENERATING_REPORT")
        covered = cursor == target
        mism = comparisons["mismatches"]
        result = {
            "outcome": "mismatch" if mism else ("match" if covered else "incomplete"),
            "validator": VALIDATOR_ID, "validator_version": VALIDATOR_VERSION, "scope": SCOPE,
            "mode": plan["mode"], "input_examined": "canonical feed cache only (source package not re-normalized)",
            "covered_events": cursor, "target_events": target, "run_total_events": plan["total_events"],
            "comparison_cursors": len(expect), "compared": comparisons["compared"], "mismatches": mism,
            "range_records": len(ranges), "restore_points": len(points),
            "ranges_without_recorded_snapshot": sum(1 for r in ranges if not r["snapshot_digest"]),
            "cache_id": plan["cache_id"], "cache_manifest_sha256": plan["cache_manifest_sha256"],
        }
        self._save(cursor, commitment, state, comparisons)
        self._finish("completed", None, result=result)
