"""Terminal observation-replay artifacts and validation.

Revision-1 replays (WP-007/WP-008) wrote their files directly under
``<artifact root>/observations/<replay_id>/``; those directories stay readable unchanged.

Revision-2 replays (WP-008-R1A) publish into a **generation-scoped immutable directory**
``observations/<replay_id>/g<generation>/``:

1. every file is written into a private staging directory ``.staging-g<generation>-<pid>``;
2. the staging directory is renamed to ``g<generation>`` (never overwritten once published);
3. only then does the worker attempt the fenced terminal DB commit that references it.

A stale finalizer (older generation) can therefore only ever publish its own ``g<old>``
directory, which no committed manifest references; it can never overwrite the files of the
current owner. Files:

* ``config.json``         - the replay config (source, verification, feed identity, policies);
* ``deliveries.jsonl``    - the ordered committed delivery identities (+ snapshot digest after each);
* ``final_snapshot.json`` - the final ObservableSnapshot (absent when validation did not finish);
* ``validation.json``     - re-derivation checks (outcome passed / failed / incomplete);
* ``manifest.json``       - written last; lists every file with its SHA-256.

Immutable source evidence is referenced (dataset / recording id), never copied.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..feed.contracts import ObservableSnapshot
from ..feed.state import apply, events_known_at, initial_state, snapshot
from ..ops import OperationCancelled
from .contracts import (
    LABELS,
    OBSERVE_CONTRACT_STATUS,
    OBSERVE_SCHEMA_REVISION,
    OBSERVE_SCHEMA_VERSION,
    VALIDATOR_ID,
    VALIDATOR_SCOPE,
    VALIDATOR_VERSION,
    ArtifactFile,
    DeliveryRecord,
    ObservationReplayConfig,
    ObservationReplayManifest,
    ReplayStatus,
    ReplayValidation,
    ValidationCheck,
    ValidationOutcome,
)
from .core import ReplayCore, as_of
from .sources import LoadedSource, feed_identity

# ``hook(stage, done, total, unit)`` - cooperative progress/cancellation between bounded units.
Hook = Callable[[str, int, int | None, str], None]


def _no_hook(stage: str, done: int, total: int | None, unit: str) -> None:  # noqa: ARG001
    return None


def replay_dir(root: Path, replay_id: str) -> Path:
    return root / "observations" / replay_id


def generation_dir_name(generation: int) -> str:
    return f"g{generation}"


def files_dir(root: Path, replay_id: str, manifest: dict[str, Any] | None) -> Path:
    """Directory holding the files a committed manifest references (revision 1: the replay directory)."""
    base = replay_dir(root, replay_id)
    sub = (manifest or {}).get("artifact_dir")
    if sub and "/" not in sub and "\\" not in sub and not sub.startswith("."):
        return base / sub
    return base


def _sha256(path: Path) -> tuple[str, int, int]:
    h, size, lines = hashlib.sha256(), 0, 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
            lines += chunk.count(b"\n")
    return h.hexdigest(), size, lines


def _no_future(snap: ObservableSnapshot) -> str | None:
    for c in snap.channels:
        for e in (c.latest_valid, c.last_quality, *c.history):
            if e is not None and e.available_time > snap.as_of:
                return f"{c.channel_id}: {e.event_id} available {e.available_time.isoformat()} > as_of"
    return None


def validate(config: ObservationReplayConfig, source: LoadedSource | None, deliveries: list[DeliveryRecord],
             cursor: int, final_digest: str, status: ReplayStatus,
             hook: Hook | None = None) -> tuple[ReplayValidation, ObservableSnapshot | None]:
    """Re-derive the replay from the immutable source and compare with what was committed.

    The checks and their mathematics are those of revision 1. ``hook`` only reports progress between
    re-derived deliveries; if it raises ``OperationCancelled`` the validation stops and is reported as
    INCOMPLETE (never PASS), listing the checks that did and did not run.
    """
    hook = hook or _no_hook
    checks: list[ValidationCheck] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ValidationCheck(name=name, passed=ok, detail=detail))

    def result(outcome: ValidationOutcome) -> ReplayValidation:
        return ReplayValidation(passed=outcome == ValidationOutcome.PASSED, checks=tuple(checks), outcome=outcome,
                                validator=VALIDATOR_ID, validator_version=VALIDATOR_VERSION, scope=VALIDATOR_SCOPE)

    if source is None:
        check("source_loadable", False, "the source could not be loaded; nothing could be re-derived")
        return result(ValidationOutcome.FAILED), None
    ident = feed_identity(source.feed)
    check("source_identity_unchanged", ident == config.feed,
          f"feed content {ident.content_identity}, ordered-event hash {ident.ordered_event_hash[:16]}")
    events = source.feed.events
    seqs = [d.seq for d in deliveries]
    check("deliveries_contiguous", seqs == list(range(cursor)),
          f"{len(deliveries)} committed deliveries for cursor {cursor}")
    ids = [d.event_id for d in deliveries]
    check("no_duplicate_delivery", len(set(ids)) == len(ids), f"{len(set(ids))} distinct event ids")
    order_ok = ids == [e.event_id for e in events[:cursor]] and all(
        d.available_time == e.available_time for d, e in zip(deliveries, events))
    check("deliveries_follow_feed_order", order_ok, "committed deliveries equal the feed.v1 total-order prefix")

    core = ReplayCore(source.feed, config.freshness_policy)
    pos = core.at(0)
    mismatch, future = None, _no_future(pos.snapshot)
    todo = deliveries[:cursor]
    try:
        for i, d in enumerate(todo):
            hook("re-derive committed deliveries", i, len(todo), "deliveries")
            if pos.cursor >= core.total:
                mismatch = f"delivery {d.seq} beyond the feed"
                break
            pos, rec = core.step(pos)
            if rec.snapshot_digest != d.snapshot_digest and mismatch is None:
                mismatch = f"delivery {d.seq}: committed digest differs from the pure re-derivation"
            future = future or _no_future(pos.snapshot)
        hook("re-derive committed deliveries", len(todo), len(todo), "deliveries")
    except OperationCancelled:
        check("validation_completed", False,
              f"cancelled after re-deriving {pos.cursor} of {len(todo)} committed deliveries; the digest, "
              "no-future-knowledge and final-state checks did not run - assurance is INCOMPLETE, not PASS")
        return result(ValidationOutcome.INCOMPLETE), None
    check("digests_match_pure_replay", mismatch is None and pos.snapshot.content_digest == final_digest,
          mismatch or f"every per-delivery snapshot digest and the final digest {final_digest[:16]} re-derived")
    check("no_future_knowledge", future is None,
          future or "no snapshot contained evidence available after its information time")
    check("observation_only", set(pos.snapshot.labels) >= {"OBSERVATION_ONLY", "NO_INTERPRETATION"},
          f"snapshot labels {list(pos.snapshot.labels)}; no MarketView/decision/order/account records")
    if status == ReplayStatus.COMPLETED:
        try:
            cutoff = as_of(source.feed, core.total)
            known = events_known_at(source.feed, cutoff)
            state = initial_state(source.feed, config.freshness_policy)
            for i, e in enumerate(known):  # the same fold as feed.state.snapshot_at, with progress
                hook("pure cutoff snapshot", i, len(known), "events")
                state = apply(state, e)
            hook("pure cutoff snapshot", len(known), len(known), "events")
            pure = snapshot(state, cutoff, source.feed)
        except OperationCancelled:
            check("validation_completed", False,
                  "cancelled while re-deriving the pure cutoff snapshot; assurance is INCOMPLETE, not PASS")
            return result(ValidationOutcome.INCOMPLETE), None
        check("completed_equals_pure_cutoff_snapshot",
              cursor == core.total and pure.content_digest == final_digest,
              f"all {core.total} deliveries applied; final state equals snapshot_at(feed, last availability)")
    outcome = ValidationOutcome.PASSED if all(c.passed for c in checks) else ValidationOutcome.FAILED
    return result(outcome), pos.snapshot


def _write_jsonl(path: Path, deliveries: list[DeliveryRecord], hook: Hook) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for i, d in enumerate(deliveries):
            if i % 1000 == 0:
                hook("serialize deliveries", i, len(deliveries), "deliveries")
            f.write(d.model_dump_json() + "\n")
    hook("serialize deliveries", len(deliveries), len(deliveries), "deliveries")


class PublishedArtifacts:
    """Result of a staged, generation-scoped publication (before the fenced DB commit)."""

    def __init__(self, manifest: ObservationReplayManifest, directory: Path, output_bytes: int) -> None:
        self.manifest = manifest
        self.directory = directory
        self.output_bytes = output_bytes


class StagedArtifacts:
    """Fully written but not yet published artifacts (``staging`` is None when the same generation already
    published - a repeated finalize never rewrites a published directory)."""

    def __init__(self, manifest: ObservationReplayManifest, staging: Path | None, final_dir: Path) -> None:
        self.manifest = manifest
        self.staging = staging
        self.final_dir = final_dir

    @property
    def output_bytes(self) -> int:
        return sum(a.bytes for a in self.manifest.artifacts)

    def discard(self) -> None:
        if self.staging is not None:
            shutil.rmtree(self.staging, ignore_errors=True)
            self.staging = None

    def publish(self) -> PublishedArtifacts:
        """Immutable publication of this generation's directory (the caller holds the DB fence).

        Staged files are fsynced (and, on POSIX, the staging and parent directories around the rename); after
        the rename every referenced file is re-hashed against the manifest, so a partial or corrupted
        publication is never referenced by a terminal commit."""
        if self.staging is not None:
            for f in self.staging.iterdir():
                if f.is_file():
                    with f.open("r+b") as fh:
                        os.fsync(fh.fileno())
            _fsync_dir(self.staging)
            try:
                os.replace(self.staging, self.final_dir)
                _fsync_dir(self.final_dir.parent)
            except OSError:
                if not (self.final_dir / "manifest.json").is_file():
                    raise
                shutil.rmtree(self.staging, ignore_errors=True)  # same-generation publication exists: keep it
                self.manifest = ObservationReplayManifest.model_validate_json(
                    (self.final_dir / "manifest.json").read_text("utf-8"))
            self.staging = None
        for a in self.manifest.artifacts:
            p = self.final_dir / a.name
            if not p.is_file() or _sha256(p)[0] != a.sha256:
                raise OSError(f"published artifact {a.name} does not match its manifest entry (partial or corrupt "
                              "publication); not referenced")
        return PublishedArtifacts(self.manifest, self.final_dir, self.output_bytes)


def _fsync_dir(path: Path) -> bool:
    if os.name == "nt":
        return False  # directory fsync is not available on Windows; not claimed
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def _staging(root: Path, replay_id: str, generation: int) -> tuple[Path, Path, ObservationReplayManifest | None]:
    base = replay_dir(root, replay_id)
    final_dir = base / generation_dir_name(generation)
    if (final_dir / "manifest.json").is_file():
        return final_dir, final_dir, ObservationReplayManifest.model_validate_json(
            (final_dir / "manifest.json").read_text(encoding="utf-8"))
    staging = base / f".staging-g{generation}-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    return staging, final_dir, None


def _hash_files(staging: Path, hook: Hook) -> tuple[ArtifactFile, ...]:
    files = []
    names = sorted(x for x in staging.iterdir() if x.is_file() and not x.name.startswith("."))
    for i, p in enumerate(names):
        hook("hash artifacts", i, len(names), "files")
        digest, size, lines = _sha256(p)
        files.append(ArtifactFile(name=p.name, sha256=digest, bytes=size, lines=lines if p.suffix == ".jsonl" else None))
    hook("hash artifacts", len(names), len(names), "files")
    return tuple(files)


def _manifest(row: dict[str, Any], config: ObservationReplayConfig, status: ReplayStatus, error: str | None,
              finished_at: datetime, cursor: int, validation: ReplayValidation, files: tuple[ArtifactFile, ...],
              generation: int, final_dir: Path, *, final_as_of: datetime, final_snapshot_id: str, final_digest: str,
              source_reference: str, timings: Callable[[], list[dict]] | None,
              metrics: Callable[[], dict] | None, temporal: dict | None = None) -> ObservationReplayManifest:
    return ObservationReplayManifest(
        schema_version=OBSERVE_SCHEMA_VERSION, contract_status=OBSERVE_CONTRACT_STATUS,
        schema_revision=OBSERVE_SCHEMA_REVISION, replay_id=row["replay_id"], status=status, labels=LABELS,
        config=config, created_at=row["created_at"], started_at=row["started_at"], finished_at=finished_at,
        applied_events=cursor, total_events=row["total_events"], final_as_of=final_as_of,
        final_snapshot_id=final_snapshot_id, final_content_digest=final_digest, attempts=row["attempt"],
        recovery_log=list(row["recovery_log"]), control_log=list(row["control_log"]), error=error,
        validation=validation, source_reference=source_reference, artifacts=files, lease_generation=generation,
        artifact_dir=final_dir.name, phase_timings=timings() if timings else None,
        operational_metrics=metrics() if metrics else None, temporal=temporal,
    )


def temporal_reference(engine: dict, summary: dict | None) -> dict | None:
    """Revision-3 manifest reference to the temporal substrate (identities + commitments; details in temporal.json)."""
    tc = (engine or {}).get("temporal")
    if not tc:
        return None
    s = summary or {}
    return {"artifact": "temporal.json" if summary is not None else None, "contract": tc["contract"],
            "contract_revision": tc["contract_revision"], "engine": tc["engine"], "state_format": tc["state_format"],
            "profile_id": tc["profile"]["profile_id"], "profile_fingerprint": tc["fingerprint"],
            "clock_policy": tc["clock_policy"], "seal_policy": tc["seal_policy"], "clock_end": tc["clock_end"],
            "clock_time": s.get("clock_time"), "admitted_cursor": s.get("admitted_cursor"),
            "dispatch_seq": s.get("dispatch_seq"), "sealed_commitment": s.get("sealed_commitment"),
            "aggregate_chain": s.get("aggregate_chain"), "dispatch_commitment": s.get("dispatch_commitment"),
            "labels": tc["labels"]}


def stage_replay_artifacts(root: Path, row: dict[str, Any], status: ReplayStatus, error: str | None,
                           finished_at: datetime, deliveries: list[DeliveryRecord], cursor: int,
                           final_digest: str, source: LoadedSource | None, *, generation: int,
                           phase: Callable[[str], None] | None = None, hook: Hook | None = None,
                           timings: Callable[[], list[dict]] | None = None,
                           metrics: Callable[[], dict] | None = None,
                           cancel_validation: bool = True) -> StagedArtifacts:
    """FINALIZING -> VALIDATING -> GENERATING_REPORT into a private staging directory (not yet published).

    A cancellation observed during VALIDATING turns a would-be COMPLETED run into CANCELLED with INCOMPLETE
    assurance (cursor coverage is kept exactly as committed). ``hook`` may raise ``OperationCancelled`` in
    the serialization / hashing units; the caller then discards the staging directory.
    """
    hook = hook or _no_hook
    phase = phase or (lambda _p: None)
    staging, final_dir, existing = _staging(root, row["replay_id"], generation)
    if existing is not None:  # same generation repeating finalize: never rewrite
        return StagedArtifacts(existing, None, final_dir)
    staged = StagedArtifacts(None, staging, final_dir)  # type: ignore[arg-type]
    try:
        config = ObservationReplayConfig.model_validate(row["config"])
        phase("FINALIZING")
        (staging / "config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
        _write_jsonl(staging / "deliveries.jsonl", deliveries, hook)

        phase("VALIDATING")
        validation, final = validate(config, source, deliveries, cursor, final_digest, status,
                                     hook=hook if cancel_validation else None)
        if validation.outcome == ValidationOutcome.INCOMPLETE and status == ReplayStatus.COMPLETED:
            status = ReplayStatus.CANCELLED
            error = ("cancelled by user during VALIDATING: the replay cursor was complete, but validation did not "
                     "finish; assurance INCOMPLETE")

        phase("GENERATING_REPORT")
        if final is not None:
            (staging / "final_snapshot.json").write_text(final.model_dump_json(indent=2), encoding="utf-8")
        (staging / "validation.json").write_text(validation.model_dump_json(indent=2), encoding="utf-8")
        files = _hash_files(staging, hook)
        manifest = _manifest(
            row, config, status, error, finished_at, cursor, validation, files, generation, final_dir,
            final_as_of=final.as_of if final is not None else finished_at,
            final_snapshot_id=final.snapshot_id if final is not None else "", final_digest=final_digest,
            source_reference=(source.reference if source is not None
                              else f"{config.source.kind.value}s/{config.source.source_id}"),
            timings=timings, metrics=metrics)
        (staging / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    except BaseException:
        staged.discard()
        raise
    staged.manifest = manifest
    return staged


def stage_bounded_artifacts(root: Path, row: dict[str, Any], status: ReplayStatus, error: str | None,
                            finished_at: datetime, cursor: int, checkpoint: dict[str, Any] | None, reason: str, *,
                            generation: int, timings: Callable[[], list[dict]] | None = None,
                            metrics: Callable[[], dict] | None = None) -> StagedArtifacts:
    """Bounded terminal artifacts for an observed cancellation (no prefix load, no source, no re-derivation).

    Written from the replay config and the committed checkpoint only: ``config.json``, ``validation.json``
    (outcome INCOMPLETE, explaining exactly what did not run) and ``manifest.json``. The committed delivery
    rows stay in the database; ``deliveries.jsonl`` / ``final_snapshot.json`` are not exported.
    """
    staging, final_dir, existing = _staging(root, row["replay_id"], generation)
    if existing is not None:
        return StagedArtifacts(existing, None, final_dir)
    staged = StagedArtifacts(None, staging, final_dir)  # type: ignore[arg-type]
    try:
        config = ObservationReplayConfig.model_validate(row["config"])
        validation = ReplayValidation(
            passed=False, outcome=ValidationOutcome.INCOMPLETE, validator=VALIDATOR_ID,
            validator_version=VALIDATOR_VERSION, scope=VALIDATOR_SCOPE,
            checks=(ValidationCheck(name="validation_not_run", passed=False, detail=(
                f"{reason}: terminal validation did not run (bounded terminal path). The committed input up to cursor "
                f"{cursor} and the committed checkpoint remain preserved in the database; no per-event trace or "
                "final snapshot was exported. Assurance INCOMPLETE, not PASS or FAIL.")),))
        (staging / "config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
        (staging / "validation.json").write_text(validation.model_dump_json(indent=2), encoding="utf-8")
        files = _hash_files(staging, _no_hook)
        ck = checkpoint or {}
        manifest = _manifest(
            row, config, status, error, finished_at, cursor, validation, files, generation, final_dir,
            final_as_of=ck.get("info_time") or finished_at, final_snapshot_id=ck.get("snapshot_id") or "",
            final_digest=ck.get("snapshot_digest") or "",
            source_reference=f"{config.source.kind.value}s/{config.source.source_id}",
            timings=timings, metrics=metrics, temporal=temporal_reference(row.get("engine") or {}, None))
        (staging / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    except BaseException:
        staged.discard()
        raise
    staged.manifest = manifest
    return staged


def stage_stream_artifacts(root: Path, row: dict[str, Any], status: ReplayStatus, error: str | None,
                           finished_at: datetime, cursor: int, ranges: list[dict], engine: dict,
                           validation: ReplayValidation, final: ObservableSnapshot | None,
                           committed_digest: str, *, generation: int, hook: Hook | None = None,
                           timings: Callable[[], list[dict]] | None = None,
                           metrics: Callable[[], dict] | None = None,
                           temporal: dict | None = None) -> StagedArtifacts:
    """Terminal artifacts of a streaming run (bounded: no per-event records exist or are synthesized).

    Temporal-enabled runs (``observe.stream.v2``) add ``temporal.json``: the verified terminal temporal summary
    (finished at the declared clock end for completed runs) - profile, clock/seal policy, newest sealed record per
    channel/horizon, readiness of the configured dependencies, late-excluded counts and commitments.

    ``engine.json`` (pinned engine/state/cache identities), ``ranges.jsonl`` (compact committed input ranges),
    ``final_snapshot.json`` (materialized from the verified terminal state), ``validation.json``
    (stream reconciliation, explicitly scoped) and ``manifest.json``.
    """
    hook = hook or _no_hook
    staging, final_dir, existing = _staging(root, row["replay_id"], generation)
    if existing is not None:
        return StagedArtifacts(existing, None, final_dir)
    staged = StagedArtifacts(None, staging, final_dir)  # type: ignore[arg-type]
    try:
        import json as _json

        config = ObservationReplayConfig.model_validate(row["config"])
        (staging / "config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
        (staging / "engine.json").write_text(_json.dumps(engine, indent=2, sort_keys=True), encoding="utf-8")
        with (staging / "ranges.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for r in ranges:
                f.write(_json.dumps({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()},
                                    sort_keys=True) + "\n")
        if final is not None:
            (staging / "final_snapshot.json").write_text(final.model_dump_json(indent=2), encoding="utf-8")
        (staging / "validation.json").write_text(validation.model_dump_json(indent=2), encoding="utf-8")
        if temporal is not None:
            (staging / "temporal.json").write_text(_json.dumps(temporal, indent=2, sort_keys=True), encoding="utf-8")
        files = _hash_files(staging, hook)
        manifest = _manifest(
            row, config, status, error, finished_at, cursor, validation, files, generation, final_dir,
            final_as_of=final.as_of if final is not None else finished_at,
            final_snapshot_id=final.snapshot_id if final is not None else "", final_digest=committed_digest,
            source_reference=f"{config.source.kind.value}s/{config.source.source_id}", timings=timings,
            metrics=metrics, temporal=temporal_reference(engine, temporal))
        (staging / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    except BaseException:
        staged.discard()
        raise
    staged.manifest = manifest
    return staged


def publish_replay_artifacts(root: Path, row: dict[str, Any], status: ReplayStatus, error: str | None,
                             finished_at: datetime, deliveries: list[DeliveryRecord], cursor: int,
                             final_digest: str, source: LoadedSource | None, *, generation: int,
                             **kw: Any) -> tuple[PublishedArtifacts, ReplayStatus, str | None]:
    """Stage then publish immediately (no DB fence; tests/tools only). Workers publish under the row lock."""
    staged = stage_replay_artifacts(root, row, status, error, finished_at, deliveries, cursor, final_digest, source,
                                    generation=generation, **kw)
    pub = staged.publish()
    return pub, pub.manifest.status, pub.manifest.error


def load_replay_manifest(root: Path, replay_id: str) -> ObservationReplayManifest | None:
    p = replay_dir(root, replay_id) / "manifest.json"
    return ObservationReplayManifest.model_validate_json(p.read_text(encoding="utf-8")) if p.is_file() else None
