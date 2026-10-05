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

Version 2 (WP-008-R2) applies to temporal-enabled ``observe.stream.v2`` runs only (v1 runs keep version 1 and its
claim). Beside the factual fold it runs (a) a shadow fold of the shared temporal engine under the run's pinned
profile/clock policy, compared with the recorded temporal state SHA-256 and output commitment, and (b) the separate
naive reference aggregator (``temporal.reference.v1``), whose recomputed aggregate chain (record identity, content
digest, sealing barrier, admitted cursor) is compared with the run's recorded aggregate chain. Both use the same
streamed canonical-cache input (the declared clock-command tape is derived from it by the pinned clock policy). The
temporal folds are not persisted: a resumed job re-folds the temporal part from cursor 0 (disclosed counter).

Version 3 (WP-008-R2 correction; launches after it) keeps every version-2 comparison and, for a genuinely COMPLETED
temporal run, also consumes the run's pinned terminal clock command (``clock_end``) in both the shadow fold and the
separate reference aggregator, then compares the finished aggregate chain and temporal output (sealed/dispatch
commitments, dispatch sequence, clock time) with the immutable published ``temporal.json`` of the pinned artifact
generation (SHA-256/size from the manifest, values cross-checked with the manifest's temporal reference). Missing or
corrupt required terminal evidence fails the validation (no MATCH); inconsistent evidence is a mismatch. Paused,
cancelled, failed or partial targets keep the exact committed-prefix scope: no finish is applied or implied. Results
saved under version 2 keep their recorded boundary-only claim.
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
from ..temporal import engine as temporal_engine
from ..temporal.contracts import ClockPolicy, Horizon
from ..temporal.reference import REFERENCE_ID, ReferenceAggregator
from .kernel import STREAM_ENGINE_FORMATS, new_temporal, pack_state, unpack_state

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
VALIDATOR_VERSION_TEMPORAL = "3"
SCOPE_TEMPORAL = SCOPE + (
    " Version 3 (temporal-enabled runs) additionally re-folds the causal temporal substrate over the same input: a "
    "shadow fold of the shared temporal engine (pinned profile and clock policy) compared with every recorded "
    "temporal state SHA-256 and output commitment, and a separate naive reference aggregator (temporal.reference.v1; "
    "shares only the UTC calendar helpers and record-content formula) whose aggregate chain is compared with the "
    "run's recorded aggregate chain. For a completed run both paths also apply the pinned terminal clock command "
    "(clock_end) and are compared with the immutable published temporal.json (pinned generation and SHA-256); missing "
    "or corrupt terminal evidence fails the validation instead of matching. Paused, cancelled, failed or partial "
    "targets keep exact committed-prefix scope (no finish applied or implied). Dispatch readiness/deadline "
    "callbacks are covered by the shadow fold only.")
VALIDATOR_VERSION_ADVISER = "5"
SCOPE_ADVISER = SCOPE_TEMPORAL + (
    " Version 5 (adviser evaluation runs, engine observe.stream.v3) additionally runs a shadow fold of the shared "
    "professional method implementation (adviser core + evaluator, pinned identity/profile) over the same input and "
    "compares, at every committed range boundary, the adviser state SHA-256 and commitments (professional sequence, "
    "journal and evaluation sequence/chain). The STORED semantic.v2 journal and adviser-evaluation.v1 record bytes are "
    "re-hashed (canonical digest, contiguous sequence, chained hash) and every regenerated record digest and chain is "
    "compared with that recomputation, never with a stored digest column alone; stored records the shadow fold did "
    "not regenerate (extra) or regenerated records absent from storage (missing) are mismatches; for completed runs "
    "the professional clock-end finish commitment is compared as well. A run pinned to a different method "
    "implementation identity fails explicitly (no comparison under changed semantics). "
    "It shares the method/reducer implementation and the canonical cache: it is NOT an independent method validation, "
    "an economic check or a source audit; the independent hand-expected reference fixtures live in the test suite.")
TERMINAL_KEYS = ("aggregate_chain", "sealed_commitment", "dispatch_commitment", "dispatch_seq", "clock_time")


class TerminalEvidenceError(Exception):
    """Required published clock-end evidence of a completed run is absent or corrupt."""


def terminal_pin(row: dict[str, Any]) -> dict[str, Any] | None:
    """Launch-time pin of a completed temporal run's published clock-end output (None: prefix-only scope)."""
    eng = row["engine"] or {}
    if not eng.get("temporal") or row["status"] != "completed":
        return None
    m = row.get("manifest") or {}
    art = next((a for a in m.get("artifacts") or [] if a.get("name") == "temporal.json"), None)
    return {"required": True, "clock_end": eng["temporal"]["clock_end"], "artifact_dir": m.get("artifact_dir"),
            "lease_generation": m.get("lease_generation"), "artifact": art, "reference": m.get("temporal")}
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
    if row.get("engine_format") not in STREAM_ENGINE_FORMATS or row["engine"] is None:
        raise DeepRejected("Deep validation applies to streaming-engine runs (observe.stream.v1/v2) only")
    if row["status"] not in ("completed", "cancelled", "failed", "paused"):
        raise DeepRejected(f"the run is {row['status']}; Deep validation runs on a finished or paused run")
    if not row["cursor"]:
        raise DeepRejected("the run has no committed events to validate")
    eng = row["engine"]
    temporal = bool(eng.get("temporal"))
    adviser = bool(eng.get("adviser"))
    pin = terminal_pin(row) if temporal else None
    finish = None
    if adviser and row["status"] == "completed":
        f = conn.execute("SELECT commitment, adviser_sha256, from_cursor FROM adviser_finish WHERE run_id = %s",
                         (replay_id,)).fetchone()
        finish = dict(f) if f else None
    plan = {"replay_id": replay_id, "committed_cursor": row["cursor"], "total_events": row["total_events"],
            "run_status_at_launch": row["status"], "cache_id": eng["cache_id"],
            "cache_manifest_sha256": eng["cache_manifest_sha256"], "state_format": eng["state_format"],
            "validator": VALIDATOR_ID,
            "validator_version": (VALIDATOR_VERSION_ADVISER if adviser else
                                  VALIDATOR_VERSION_TEMPORAL if temporal else VALIDATOR_VERSION),
            "mode": "canonical-cache-only",
            "scope": SCOPE_ADVISER if adviser else SCOPE_TEMPORAL if temporal else SCOPE, "temporal": temporal,
            "terminal": pin, "adviser": adviser, "adviser_finish": finish}
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
        plan = row["plan"]
        return {"outcome": outcome, "validator": VALIDATOR_ID,
                "validator_version": plan.get("validator_version", VALIDATOR_VERSION), "scope": plan.get("scope", SCOPE),
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

    def _load_published_temporal(self, replay_id: str, pin: dict[str, Any]) -> dict[str, Any]:
        """The pinned, immutable published temporal.json, verified against the manifest's SHA-256 and size."""
        import hashlib
        import json

        from .artifacts import files_dir

        art, ref = pin.get("artifact"), pin.get("reference")
        if not art or not ref:
            raise TerminalEvidenceError("the completed run's manifest lists no temporal.json / temporal reference")
        path = files_dir(self.artifact_root, replay_id, {"artifact_dir": pin.get("artifact_dir")}) / "temporal.json"
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise TerminalEvidenceError(f"published temporal.json unreadable ({exc.__class__.__name__})") from None
        if len(data) != art.get("bytes") or hashlib.sha256(data).hexdigest() != art.get("sha256"):
            raise TerminalEvidenceError(f"published temporal.json in {pin.get('artifact_dir')} does not match the "
                                        "manifest's SHA-256/size (corrupt or replaced)")
        try:
            doc = json.loads(data)
        except ValueError:
            raise TerminalEvidenceError("published temporal.json is not valid JSON") from None
        if not isinstance(doc, dict) or any(k not in doc for k in TERMINAL_KEYS):
            raise TerminalEvidenceError("published temporal.json lacks required terminal fields")
        return doc

    def _terminal_compare(self, plan: dict[str, Any], pin: dict[str, Any], shadow, ref, comparisons: dict[str, Any],
                          target: int) -> dict[str, Any]:
        """Apply the pinned terminal clock command in both paths and compare with the published finished output."""
        published = self._load_published_temporal(plan["replay_id"], pin)
        clock_end = datetime.fromisoformat(pin["clock_end"])
        self.milestone("terminal clock-end barrier", target, target, "events", force=True)
        shadow.finish(clock_end)
        ref.finish(clock_end)
        manifest_ref = pin["reference"]
        checks = [(f"terminal_evidence_{k}", "published temporal.json vs manifest temporal reference",
                   str(published[k]), str(manifest_ref.get(k))) for k in TERMINAL_KEYS]
        checks += [
            ("terminal_aggregate_chain", "clock-end finish: published output vs separate reference aggregator",
             str(published["aggregate_chain"]), str(ref.chain)),
            ("terminal_shadow_aggregate_chain", "clock-end finish: published output vs shadow temporal fold",
             str(published["aggregate_chain"]), str(shadow.aggregate_chain)),
            ("terminal_sealed_commitment", "clock-end finish: published output vs shadow temporal fold",
             str(published["sealed_commitment"]), str(shadow.sealed_commitment)),
            ("terminal_dispatch_commitment", "clock-end finish: published output vs shadow temporal fold",
             str(published["dispatch_commitment"]), str(shadow.dispatch_commitment)),
            ("terminal_dispatch_seq", "clock-end finish: published output vs shadow temporal fold",
             str(published["dispatch_seq"]), str(shadow.dispatch_seq)),
            ("terminal_clock_time", "clock-end finish: published output vs pinned clock_end",
             str(published["clock_time"]), clock_end.isoformat()),
        ]
        for kind, label, want, actual in checks:
            comparisons["compared"] += 1
            if want != actual and len(comparisons["mismatches"]) < MAX_MISMATCHES:
                comparisons["mismatches"].append({"cursor": target, "kind": kind, "at": label, "expected": want,
                                                  "reference": actual})
        return {"compared": True, "comparisons": len(checks), "clock_end": pin["clock_end"],
                "artifact_dir": pin.get("artifact_dir"), "lease_generation": pin.get("lease_generation"),
                "artifact_sha256": pin["artifact"]["sha256"], "reference_sealed_records_final": len(ref.sealed),
                "shadow_sealed_records_final": shadow.counters["sealed"], "shadow_dispatches_final": shadow.dispatch_seq}

    def _adv_load_stored(self, replay_id: str, out: dict[str, dict[int, tuple[str, str]]]) -> list[dict[str, Any]]:
        """Re-hash the STORED professional record bytes: seq -> (recomputed digest, recomputed chain). A stored
        digest/chain/sequence that disagrees with the stored bytes is a mismatch of its own."""
        import hashlib

        from ..adviser.core import INITIAL_JOURNAL
        from ..adviser.evaluator import INITIAL_RECORDS
        from ..feed.ordering import canonical

        problems: list[dict[str, Any]] = []
        for table, initial in (("adviser_journal", INITIAL_JOURNAL), ("adviser_evaluation_records", INITIAL_RECORDS)):
            rows = self.conn.execute(f"SELECT seq, digest, chain, record FROM {table} WHERE run_id = %s ORDER BY seq",
                                     (replay_id,)).fetchall()
            h, expect, m = initial, 1, {}
            for r in rows:
                if r["seq"] != expect:
                    problems.append({"cursor": None, "kind": f"{table}_stored_sequence", "at": f"seq {r['seq']}",
                                     "expected": expect, "reference": r["seq"]})
                digest = hashlib.sha256(canonical(r["record"])).hexdigest()
                if digest != r["digest"]:
                    problems.append({"cursor": None, "kind": f"{table}_stored_bytes", "at": f"seq {r['seq']}",
                                     "expected": r["digest"], "reference": digest})
                # each link is verified locally from the STORED predecessor, so one altered row is localized
                link = hashlib.sha256(bytes.fromhex(h) + bytes.fromhex(digest)).hexdigest()
                if link != r["chain"]:
                    problems.append({"cursor": None, "kind": f"{table}_stored_chain", "at": f"seq {r['seq']}",
                                     "expected": r["chain"], "reference": link})
                m[r["seq"]] = (digest, link)
                h = r["chain"]
                expect = r["seq"] + 1
            out[table] = m
            self.counters_deep[f"{table}_stored_rehashed"] = len(rows)
        return problems

    def _adv_compare(self, comparisons: dict[str, Any], cursor: int) -> None:
        """Every regenerated professional record (digest AND chain) must equal the recomputation of the stored bytes
        with the same sequence."""
        journal, records = self._adv.take()
        seen_all = getattr(self, "_adv_seen", None)
        if seen_all is None:
            seen_all = self._adv_seen = {}
        for table, rows in (("adviser_journal", journal), ("adviser_evaluation_records", records)):
            seen = seen_all.setdefault(table, set())
            for r in rows:
                comparisons["compared"] += 1
                seen.add(r["seq"])
                want = self._adv_digests.get(table, {}).get(r["seq"])
                got = (r["digest"], r["chain"])
                if (want is None or tuple(want) != got) and len(comparisons["mismatches"]) < MAX_MISMATCHES:
                    comparisons["mismatches"].append({"cursor": cursor, "kind": f"{table}_record",
                                                      "at": f"seq {r['seq']}",
                                                      "expected": None if want is None else list(want),
                                                      "reference": list(got)})
            self.counters_deep[f"{table}_compared"] = self.counters_deep.get(f"{table}_compared", 0) + len(rows)

    def _adv_extra(self, comparisons: dict[str, Any], target: int) -> None:
        """At full coverage every stored professional record must have been regenerated (no extra stored rows)."""
        for table, stored in self._adv_digests.items():
            extra = sorted(set(stored) - self._adv_seen.get(table, set()))
            comparisons["compared"] += 1
            if extra and len(comparisons["mismatches"]) < MAX_MISMATCHES:
                comparisons["mismatches"].append({"cursor": target, "kind": f"{table}_extra_stored",
                                                  "at": f"seq {extra[0]}..{extra[-1]} ({len(extra)} rows)",
                                                  "expected": None, "reference": "not regenerated by the shadow fold"})

    def _adv_terminal(self, plan: dict[str, Any], adv, comparisons: dict[str, Any], target: int) -> dict[str, Any]:
        """The shadow temporal fold was finished by the temporal terminal comparison; finish the shadow professional
        fold at the same clock end and compare with the committed professional finish."""
        import json as _json

        from ..adviser.engine import pack_runtime

        fin = plan.get("adviser_finish")
        clock_end = datetime.fromisoformat(plan["terminal"]["clock_end"])
        adv.finish(clock_end)
        self._adv_compare(comparisons, target)
        got = {**adv.commitment(), "adviser_sha256": pack_runtime(adv)[1]}
        comparisons["compared"] += 1
        want = None if fin is None else {k: fin["commitment"].get(k) for k in got}
        if want != _json.loads(_json.dumps(got)) and len(comparisons["mismatches"]) < MAX_MISMATCHES:
            comparisons["mismatches"].append({"cursor": target, "kind": "adviser_finish",
                                              "at": "professional clock-end finish", "expected": want,
                                              "reference": got})
        return {"compared": fin is not None, "journal_seq": got["journal_seq"],
                "evaluation_seq": got["evaluation_seq"]}

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
            "SELECT range_seq, to_cursor, commitment_after, snapshot_digest, state_sha256, temporal_sha256, "
            "temporal_commitment, aggregate_chain, adviser_sha256, adviser_commitment FROM observation_ranges "
            "WHERE replay_id = %s AND to_cursor <= %s ORDER BY to_cursor", (plan["replay_id"], target)).fetchall()
        points = self.conn.execute(
            "SELECT cursor, state_sha256, snapshot_digest, commitment, terminal, temporal_sha256 "
            "FROM observation_restore_points WHERE replay_id = %s AND cursor <= %s",
            (plan["replay_id"], target)).fetchall()
        temporal = bool(plan.get("temporal"))
        expect: dict[int, list[tuple[str, str, str]]] = {}
        for r in ranges:
            expect.setdefault(r["to_cursor"], []).append(("commitment", r["commitment_after"],
                                                          f"range {r['range_seq']}"))
            if r["snapshot_digest"]:
                expect[r["to_cursor"]].append(("snapshot", r["snapshot_digest"], f"range {r['range_seq']}"))
                expect[r["to_cursor"]].append(("state", r["state_sha256"], f"range {r['range_seq']}"))
            if temporal:
                expect[r["to_cursor"]].extend([
                    ("temporal_state", r["temporal_sha256"], f"range {r['range_seq']} (shadow temporal fold)"),
                    ("temporal_commitment", r["temporal_commitment"], f"range {r['range_seq']} (shadow temporal fold)"),
                    ("aggregate_chain", r["aggregate_chain"], f"range {r['range_seq']} (reference aggregator)")])
            if plan.get("adviser"):
                import json as _json

                expect[r["to_cursor"]].extend([
                    ("adviser_state", r["adviser_sha256"], f"range {r['range_seq']} (shadow professional fold)"),
                    ("adviser_commitment", _json.dumps(r["adviser_commitment"], sort_keys=True),
                     f"range {r['range_seq']} (shadow professional fold)")])
        for p in points:
            label = "terminal restore point" if p["terminal"] else "restore point"
            expect.setdefault(p["cursor"], []).extend([("commitment", p["commitment"], label),
                                                       ("snapshot", p["snapshot_digest"], label),
                                                       ("state", p["state_sha256"], label)])
            if temporal:
                expect[p["cursor"]].append(("temporal_state", p["temporal_sha256"], label + " (shadow temporal fold)"))
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
        reader = CacheReader(cache, {})
        shadow = ref = adv = None
        adv_digests: dict[str, dict[int, str]] = {}
        if temporal:
            shadow = new_temporal(cache.feed_manifest, replay["engine"])
            prof = shadow.profile
            ref = ReferenceAggregator(tuple(cache.feed_manifest.coverage), tuple(Horizon(h) for h in prof.horizons),
                                      prof.closure_allowance, ClockPolicy(prof.clock_policy))
        if plan.get("adviser") and shadow is not None:
            from ..adviser.engine import AdviserStateError, new_runtime

            try:
                adv = new_runtime(replay["engine"])
            except AdviserStateError as exc:
                self._finish("failed", f"cannot run the professional shadow fold: {exc} (the run is pinned to a "
                                       "different method implementation identity; no comparison is possible)")
                return
            adv.attach(shadow)
            stored_problems = self._adv_load_stored(plan["replay_id"], adv_digests)
            if not start:  # a resumed validation already recorded these with its saved comparisons
                for m in stored_problems:
                    comparisons["compared"] += 1
                    if len(comparisons["mismatches"]) < MAX_MISMATCHES:
                        comparisons["mismatches"].append(m)
        self._adv, self._adv_digests = adv, adv_digests
        self._adv_seen = {"adviser_journal": set(), "adviser_evaluation_records": set()}
        if temporal and start:  # temporal folds are not persisted: re-fold them over the already covered prefix
            self.enter_phase("VALIDATING", detail="re-folding the temporal reference over the covered prefix",
                             total=start, done=0, unit="events")
            for seq, line in reader.iter_from(0):
                if seq >= start:
                    break
                e = FeedEvent.model_validate_json(line)
                shadow.on_event(e, seq)
                ref.feed(e)
                if adv is not None:
                    adv.before_admit(e)
                    adv.admit(e, seq)
                    self._adv_compare(comparisons, seq + 1)
                self.counters_deep["temporal_refold_events"] = seq + 1
                self.milestone("temporal re-fold of the covered prefix", seq + 1, start, "events")
                if self.cancel_seen:  # the saved factual diagnostic state stays as it was
                    self._cancel_now(start, None, None, None, target)
                    return
        self.enter_phase("VALIDATING", detail="reference re-execution of the committed prefix",
                         total=target, done=start, unit="events")
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
                if shadow is not None:
                    shadow.on_event(e, seq)
                    ref.feed(e)
                if adv is not None:
                    adv.before_admit(e)
                    adv.admit(e, seq)
                cursor = seq + 1
                if adv is not None:
                    self._adv_compare(comparisons, cursor)
                self.counters_deep["events_reexecuted"] += 1
                checks = expect.get(cursor)
                if checks:
                    snap = snapshot(state, e.available_time, feed_meta)
                    self.counters_deep["snapshots_built"] += 1
                    sha = pack_state(state)[1]
                    self.counters_deep["state_encodes"] += 1
                    actual = {"commitment": commitment.hex(), "snapshot": snap.content_digest, "state": sha}
                    if shadow is not None:
                        actual.update(temporal_state=temporal_engine.pack(shadow)[1],
                                      temporal_commitment=shadow.commitment(), aggregate_chain=ref.chain)
                    if adv is not None:
                        import json as _json

                        from ..adviser.engine import pack_runtime

                        actual.update(adviser_state=pack_runtime(adv)[1],
                                      adviser_commitment=_json.dumps(adv.commitment(), sort_keys=True))
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
        covered = cursor == target
        terminal = None
        if shadow is not None:
            pin = plan.get("terminal")
            if pin and covered:
                try:
                    terminal = self._terminal_compare(plan, pin, shadow, ref, comparisons, target)
                except TerminalEvidenceError as exc:
                    self._save(cursor, commitment, state, comparisons)
                    self._finish("failed", f"required terminal temporal evidence of the completed run is unusable: "
                                           f"{exc}; no match is possible without it")
                    return
                if self.cancel_seen:
                    self._cancel_now(cursor, commitment, state, comparisons, target)
                    return
                if adv is not None:
                    terminal["adviser"] = self._adv_terminal(plan, adv, comparisons, target)
            else:
                terminal = {"compared": False, "scope": (
                    "committed prefix only: the target is not a completed run with a published clock-end finish "
                    "(paused, cancelled, failed or partial); no finish was applied or implied")}
        if adv is not None and covered and (plan.get("run_status_at_launch") != "completed"
                                            or (terminal or {}).get("adviser") is not None):
            self._adv_extra(comparisons, target)
        self.enter_phase("GENERATING_REPORT")
        mism = comparisons["mismatches"]
        result = {
            "outcome": "mismatch" if mism else ("match" if covered else "incomplete"),
            "validator": VALIDATOR_ID, "validator_version": plan.get("validator_version", VALIDATOR_VERSION),
            "scope": plan.get("scope", SCOPE),
            "mode": plan["mode"], "input_examined": "canonical feed cache only (source package not re-normalized)",
            "covered_events": cursor, "target_events": target, "run_total_events": plan["total_events"],
            "comparison_cursors": len(expect), "compared": comparisons["compared"], "mismatches": mism,
            "range_records": len(ranges), "restore_points": len(points),
            "ranges_without_recorded_snapshot": sum(1 for r in ranges if not r["snapshot_digest"]),
            "cache_id": plan["cache_id"], "cache_manifest_sha256": plan["cache_manifest_sha256"],
        }
        if shadow is not None:
            result["temporal"] = {"reference": REFERENCE_ID, "shadow_engine": temporal_engine.ENGINE_ID,
                                  "clock_policy": shadow.profile.clock_policy.value,
                                  "reference_sealed_records": len(ref.sealed), "shadow_sealed_records":
                                      shadow.counters["sealed"], "shadow_dispatches": shadow.dispatch_seq,
                                  "temporal_refold_events": self.counters_deep.get("temporal_refold_events", 0),
                                  "terminal": terminal,
                                  "note": ("committed range boundaries / restore points, plus the clock-end finish "
                                           "for completed runs" if terminal and terminal.get("compared") else
                                           "comparisons at committed range boundaries / restore points only")}
        self._save(cursor, commitment, state, comparisons)
        self._finish("completed", None, result=result)
