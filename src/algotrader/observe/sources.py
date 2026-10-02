"""Replayable evidence sources: verification and feed construction (pure file access; no DB, no network).

* Historical dataset: re-verify the immutable ``marketdata.v1`` package, then build
  the feed with the accepted adapter and the explicit zero-extra-delay MODELED
  availability convention (lower bound; not measured publication timing).
* Recorder session: must be finalized, verify, and not FAILED; the feed comes from
  the accepted recorded-session bridge (RECORDED first-completion local receipt).
  PARTIAL sessions replay with their outages listed as recorder availability
  loss - never as market gaps. Bridge exclusions stay visible.

A source with no usable market evidence (no valid bar observation) is rejected.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..feed.adapter import Feed, build_feed
from ..feed.contracts import AvailabilityBasis, EventKind
from ..feed.ordering import FeedError, modeled_availability
from ..marketdata import dataset as md
from ..marketdata.contracts import MARKETDATA_SCHEMA_VERSION
from ..recorder import journal as rj
from ..recorder.contracts import RECORDER_SCHEMA_VERSION, SessionStatus
from ..recorder.feed_bridge import build_recorded_feed
from .contracts import FeedIdentity, SourceKind, SourceSummary, SourceVerification

MODELED_LABEL = ("MODELED availability - not measured publication timing: each completed bar is known at its "
                 "bar close and each settled funding event at its funding time (zero-extra-delay lower-bound "
                 "convention). No live receipt measurement is applied to historical data.")
RECORDED_LABEL = ("RECORDED availability - client-observed receipt times: each bar is known at the local receipt "
                  "time of its first completed (confirm=1) push on the recording host; not the exchange's "
                  "publication time.")


class SourceRejected(Exception):
    """The source cannot launch a valid observation replay."""


# Optional cooperative hook ``(stage, done, total, unit)`` used by the worker-owned preparation phases.
Progress = Callable[[str, int, int | None, str], None]


def _no_hook(stage: str, done: int, total: int | None, unit: str) -> None:  # noqa: ARG001
    return None


def locate_source(root: Path, kind: SourceKind | str, source_id: str) -> Path:
    """Cheap launch-time check (no hashing, no parsing beyond a path test): the source exists locally.

    Full verification and feed construction happen later, inside the durable worker-owned job.
    """
    kind = SourceKind(kind)
    path = md.dataset_path(root, source_id) if kind == SourceKind.DATASET else rj.session_path(root, source_id)
    if path is None:
        raise SourceRejected(f"{kind.value} {source_id} not found in the local data root")
    if kind == SourceKind.RECORDING and not rj.is_finalized(path):
        raise SourceRejected(f"recording {source_id} is not finalized (still recording or awaiting recovery)")
    return path


def manifest_sha256(path: Path) -> str:
    return hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()


@dataclass(frozen=True)
class LoadedSource:
    summary: SourceSummary
    verification: SourceVerification
    feed: Feed
    availability_label: str
    reference: str  # where the immutable evidence lives


def feed_identity(feed: Feed) -> FeedIdentity:
    m = feed.manifest
    return FeedIdentity(
        schema_version=m.schema_version, contract_status=m.contract_status, schema_revision=m.schema_revision,
        content_identity=m.content_identity, ordered_event_hash=m.ordered_event_hash,
        ordering_policy_id=m.ordering_policy_id, event_count=m.event_count, event_counts=m.event_counts,
    )


def _require_usable(feed: Feed, what: str) -> None:
    if not any(e.kind in (EventKind.BAR_OBSERVATION, EventKind.FUNDING_OBSERVATION) for e in feed.events):
        raise SourceRejected(f"{what} contains no usable market evidence (no valid observation)")


def load_dataset(root: Path, dataset_id: str, progress: Progress | None = None,
                 build_progress: Progress | None = None) -> LoadedSource:
    path = md.dataset_path(root, dataset_id)
    if path is None:
        raise SourceRejected(f"dataset {dataset_id} not found")
    checked = datetime.now(UTC)
    problems = md.verify(path, progress=progress)
    verification = SourceVerification(
        verified=not problems, checked_at=checked, problems=tuple(problems),
        method="marketdata.v1 verify: every file hash/size, row counts and dataset identity re-checked")
    if problems:
        raise SourceRejected(f"dataset {dataset_id} failed verification: {'; '.join(problems)}")
    try:
        feed = build_feed(path, modeled_availability(), progress=build_progress)
    except FeedError as exc:
        raise SourceRejected(f"dataset {dataset_id}: feed not built ({exc})") from None
    _require_usable(feed, f"dataset {dataset_id}")
    quality = md.load_quality(path).status.value
    warnings = []
    if quality != "clean":
        warnings.append(f"dataset quality {quality.upper()}: missing/rejected slots are delivered as quality events "
                        "and never filled")
    m = feed.manifest
    summary = SourceSummary(
        kind=SourceKind.DATASET, source_id=dataset_id, source_schema=MARKETDATA_SCHEMA_VERSION,
        inst_id=m.inst_id, index_id=m.index_id, source_status=quality, coverage=m.coverage,
        warnings=tuple(warnings), exclusions=(), notes=(),
    )
    if m.availability_policy.basis != AvailabilityBasis.MODELED:
        raise SourceRejected(f"dataset {dataset_id}: expected MODELED availability")
    return LoadedSource(summary, verification, feed, MODELED_LABEL, f"datasets/{dataset_id}")


def load_recording(root: Path, session_id: str, progress: Progress | None = None,
                   build_progress: Progress | None = None) -> LoadedSource:
    path = rj.session_path(root, session_id)
    if path is None:
        raise SourceRejected(f"recording {session_id} not found")
    if not rj.is_finalized(path):
        raise SourceRejected(f"recording {session_id} is not finalized (still recording or awaiting recovery)")
    checked = datetime.now(UTC)
    problems = rj.verify(path, progress=progress)
    verification = SourceVerification(
        verified=not problems, checked_at=checked, problems=tuple(problems),
        method="recorder.v1 verify: every file hash/size/line count, contiguous journal seq, per-record raw hash")
    if problems:
        raise SourceRejected(f"recording {session_id} failed verification: {'; '.join(problems)}")
    manifest, report = rj.load_manifest(path), rj.load_report(path)
    if manifest.status == SessionStatus.FAILED:
        raise SourceRejected(f"recording {session_id} is FAILED (no usable market data); it cannot be replayed")
    hook = build_progress or _no_hook
    try:
        hook("bridge recorded journal (single unit)", 0, 1, "stages")
        bridge = build_recorded_feed(path)
        hook("bridge recorded journal (single unit)", 1, 1, "stages")
    except FeedError as exc:
        raise SourceRejected(f"recording {session_id}: feed not built ({exc})") from None
    _require_usable(bridge.feed, f"recording {session_id}")
    warnings = []
    if manifest.status == SessionStatus.PARTIAL:
        warnings.append("PARTIAL session: " + (manifest.stop_reason or "recorded with outages or missing channels"))
    for o in report.outages:
        conn = o.connection.value if o.connection else "session"
        end = o.end.isoformat() if o.end else "session end"
        warnings.append(f"recorder outage ({conn}) {o.start.isoformat()} -> {end}: recorder availability loss, "
                        "not a market gap; no gap events are fabricated")
    m = bridge.feed.manifest
    summary = SourceSummary(
        kind=SourceKind.RECORDING, source_id=session_id, source_schema=RECORDER_SCHEMA_VERSION,
        inst_id=m.inst_id, index_id=m.index_id, source_status=manifest.status.value, coverage=m.coverage,
        warnings=tuple(warnings), exclusions=bridge.excluded, notes=(bridge.funding_note,),
    )
    if m.availability_policy.basis != AvailabilityBasis.RECORDED:
        raise SourceRejected(f"recording {session_id}: expected RECORDED availability")
    return LoadedSource(summary, verification, bridge.feed, RECORDED_LABEL, f"recordings/{session_id}")


def load_source(root: Path, kind: SourceKind | str, source_id: str, progress: Progress | None = None,
                build_progress: Progress | None = None) -> LoadedSource:
    kind = SourceKind(kind)
    if kind == SourceKind.DATASET:
        return load_dataset(root, source_id, progress, build_progress)
    return load_recording(root, source_id, progress, build_progress)


# ---------------------------------------------------------------------------
# Streaming preparation (WP-008-R1B): verify once, build or reuse the immutable feed cache
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreparedSource:
    loaded: LoadedSource  # ``loaded.feed`` carries the feed manifest only (never the event list)
    cache: object  # feedcache.FeedCache
    warm: bool
    source_manifest_sha256: str
    receipt: dict


class ReceiptStore:
    """Trusted feed-cache receipts in PostgreSQL (outside the mutable cache directory)."""

    def __init__(self, conn) -> None:
        self.conn = conn

    def get(self, cache_id: str) -> dict | None:
        return self.conn.execute("SELECT * FROM observation_feed_caches WHERE cache_id = %s", (cache_id,)).fetchone()

    def put(self, cache, key: dict, source_kind: str, source_id: str, source_sha: str, durability: str,
            verification: str, created_by: dict) -> dict:
        from psycopg.types.json import Jsonb

        self.conn.execute(
            """INSERT INTO observation_feed_caches (cache_id, cache_manifest_sha256, cache_key, source_kind, source_id,
                   source_manifest_sha256, event_count, partitions, bytes_on_disk, durability, verification, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (cache_id) DO NOTHING""",
            (cache.cache_id, cache.manifest_sha256, Jsonb(key), source_kind, source_id, source_sha, cache.event_count,
             len(cache.partitions), sum(p["bytes"] for p in cache.partitions), durability, verification,
             Jsonb(created_by)))
        return self.get(cache.cache_id)


def snapshot_source(src: Path, dest: Path, hook: Progress) -> None:
    """Copy the source package into a private snapshot directory (bounded 1 MiB buffers, hook per file).

    Everything after this point - verification, normalization, source facts - reads ONLY the snapshot, so the
    bytes that are verified are exactly the bytes that are normalized and published.
    """
    import shutil

    files = [p for p in sorted(src.rglob("*")) if p.is_file()]
    dest.mkdir(parents=True)
    for i, p in enumerate(files):
        hook("snapshot source package", i, len(files), "files")
        out = dest / p.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        with p.open("rb") as fi, out.open("wb") as fo:
            shutil.copyfileobj(fi, fo, 1 << 20)
    hook("snapshot source package", len(files), len(files), "files")


def prepare_stream_source(root: Path, kind: SourceKind | str, source_id: str, *, receipts: ReceiptStore,
                          verify_hook: Progress | None = None, build_hook: Progress | None = None,
                          on_phase=None, counters: dict | None = None,
                          expected_manifest_sha256: str | None = None, created_by: dict | None = None,
                          fault=None) -> PreparedSource:
    """Locate -> reuse a receipt-pinned cache | snapshot, verify the snapshot once, build from it, publish
    durably and record a trusted receipt.

    Trust boundary (cold): a private snapshot of the source package is taken first; the snapshot is verified
    (marketdata.v1 / recorder.v1) and is the ONLY input to normalization and to the source facts. A mutation
    of the original package after (or during) the copy cannot enter the cache: either the snapshot no longer
    verifies, or its manifest differs from the located package and the preparation is rejected.
    Trust boundary (warm): the cache directory is accepted only if its manifest SHA-256 equals the trusted
    receipt recorded after a previous durable publication; partitions are SHA-256-verified when read. The
    original source package is not re-verified on warm launches (the receipt-pinned cache is the trusted
    verified snapshot of it); its manifest SHA-256 still selects the cache key.
    """
    import shutil
    import uuid

    from . import feedcache as fc
    from ..feed.adapter import dataset_feed_meta, iter_dataset_events
    from ..recorder.feed_bridge import FUNDING_NOTE, RECORDED_POLICY, RecordedStream

    kind = SourceKind(kind)
    counters = counters if counters is not None else {}
    on_phase = on_phase or (lambda _p: None)
    verify_hook = verify_hook or _no_hook
    build_hook = build_hook or _no_hook
    path = locate_source(root, kind, source_id)
    msha = manifest_sha256(path)
    if expected_manifest_sha256 is not None and msha != expected_manifest_sha256:
        raise SourceRejected(f"dataset {source_id} manifest changed since it was bound to the corpus "
                             f"(sha256 {msha[:16]} != bound {expected_manifest_sha256[:16]}); not replayed")
    policy = modeled_availability() if kind == SourceKind.DATASET else RECORDED_POLICY
    key = fc.cache_key(kind.value, source_id, msha, policy)
    cid = fc.cache_id_for(key)
    cdir = fc.cache_root(root) / cid
    receipt = receipts.get(cid)
    cache = None
    if cdir.exists():
        if receipt is None:
            moved = fc.quarantine_dir(cdir, cid, "published cache without a trusted receipt (crash before the "
                                                 "receipt commit, or not produced by a verified preparation)")
            counters["cache_quarantined"] = {"dir": moved.name if moved else None, "reason": "no trusted receipt"}
        else:
            try:
                cache = fc.open_cache(root, cid, key, expected_manifest_sha256=receipt["cache_manifest_sha256"])
            except fc.CacheError as exc:
                moved = fc.quarantine_dir(cdir, cid, f"does not match its trusted receipt: {exc}")
                counters["cache_quarantined"] = {"dir": moved.name if moved else None, "reason": str(exc)}
    warm = cache is not None
    if not warm:
        fc.cleanup_stale(root)
        snap_root = fc.cache_root(root) / f".snap-{cid}-{uuid.uuid4().hex[:8]}"
        snap = snap_root / path.name  # same directory name: the dataset id <-> directory check still applies
        try:
            on_phase("VERIFYING_SOURCE")
            snapshot_source(path, snap, verify_hook)
            if manifest_sha256(snap) != msha:
                raise SourceRejected(f"{kind.value} {source_id} changed while it was being prepared (its manifest "
                                     "differs from the located package); nothing was built")
            if fault:
                fault("after_snapshot")
            counters["source_verifications"] = counters.get("source_verifications", 0) + 1
            if kind == SourceKind.RECORDING:
                snap_manifest = rj.load_manifest(snap)
                if snap_manifest.status == SessionStatus.FAILED:
                    raise SourceRejected(f"recording {source_id} is FAILED (no usable market data); it cannot be "
                                         "replayed")
            problems = (md.verify(snap, progress=verify_hook) if kind == SourceKind.DATASET
                        else rj.verify(snap, progress=verify_hook))
            if problems:
                raise SourceRejected(f"{kind.value} {source_id} failed verification: {'; '.join(problems)}")
            if fault:
                fault("after_verification")
            on_phase("BUILDING_FEED")
            counters["feed_builds"] = counters.get("feed_builds", 0) + 1
            work = snap_root / "work"
            try:
                if kind == SourceKind.DATASET:
                    meta = dataset_feed_meta(snap)
                    quality = md.load_quality(snap).status.value
                    cache = fc.build_cache(
                        root, key, iter_dataset_events(snap, policy, progress=build_hook, workdir=work),
                        lambda: meta.coverage, policy, (meta.dataset_id,),
                        lambda: (meta.inst_id, meta.index_id, meta.instrument),
                        lambda: {"quality": quality, "warnings": [], "notes": []}, hook=build_hook,
                        counters=counters, fault=fault)
                else:
                    stream = RecordedStream(snap, workdir=work, hook=build_hook)
                    warnings = []
                    if snap_manifest.status == SessionStatus.PARTIAL:
                        warnings.append("PARTIAL session: " + (snap_manifest.stop_reason
                                                               or "recorded with outages or missing channels"))
                    for o in rj.load_report(snap).outages:
                        conn_ = o.connection.value if o.connection else "session"
                        end = o.end.isoformat() if o.end else "session end"
                        warnings.append(f"recorder outage ({conn_}) {o.start.isoformat()} -> {end}: recorder "
                                        "availability loss, not a market gap; no gap events are fabricated")
                    cache = fc.build_cache(
                        root, key, stream.events(), lambda: stream.coverage, policy, (stream.config.session_id,),
                        lambda: (stream.inst.inst_id, stream.inst.index_id, stream.instrument),
                        lambda: {"quality": snap_manifest.status.value, "warnings": warnings,
                                 "notes": [FUNDING_NOTE]},
                        hook=build_hook, counters=counters, exclusions=stream.iter_excluded, fault=fault)
                    counters["bridge_first_completions"] = stream.dedup_max_rows
            except FeedError as exc:
                raise SourceRejected(f"{kind.value} {source_id}: feed not built ({exc})") from None
        finally:
            shutil.rmtree(snap_root, ignore_errors=True)
        verification = (f"{'marketdata.v1' if kind == SourceKind.DATASET else 'recorder.v1'} verify of a private "
                        "snapshot of the source package; the cache was built only from that snapshot")
        if receipt is not None:  # rebuilding a cache whose receipt exists: it must reproduce the pinned bytes
            if receipt["cache_manifest_sha256"] != cache.manifest_sha256:
                fc.quarantine(cache, "rebuild does not reproduce the trusted receipt")
                raise fc.CacheError(f"feed cache {cid}: the rebuilt cache does not reproduce its trusted receipt "
                                    f"({cache.manifest_sha256[:16]} != {receipt['cache_manifest_sha256'][:16]})")
        else:
            if fault:
                fault("before_receipt")
            receipt = receipts.put(cache, key, kind.value, source_id, msha, counters.get("durability", "unknown"),
                                   verification, created_by or {})
            if receipt["cache_manifest_sha256"] != cache.manifest_sha256:
                raise fc.CacheError(f"feed cache {cid}: a different receipt was recorded concurrently")
    if not cache.manifest.get("usable"):
        raise SourceRejected(f"{kind.value} {source_id} contains no usable market evidence (no valid observation)")
    facts = cache.manifest["source_facts"]
    fm = cache.feed_manifest
    warnings = list(facts.get("warnings", []))
    if kind == SourceKind.DATASET:
        if facts["quality"] != "clean":
            warnings.insert(0, f"dataset quality {facts['quality'].upper()}: missing/rejected slots are delivered as "
                               "quality events and never filled")
        schema, label, ref = MARKETDATA_SCHEMA_VERSION, MODELED_LABEL, f"datasets/{source_id}"
        exclusions: tuple[str, ...] = ()
    else:
        schema, label, ref = RECORDER_SCHEMA_VERSION, RECORDED_LABEL, f"recordings/{source_id}"
        excl = []
        for i, text in enumerate(fc.iter_exclusions(cache)):
            if i >= fc.EXCLUSIONS_IN_CONFIG:
                break
            excl.append(text)
        more = facts.get("exclusions_count", 0) - len(excl)
        if more > 0:
            excl.append(f"... {more} more bridge exclusion(s) listed in feed cache {cid} exclusions.jsonl")
        exclusions = tuple(excl)
    summary = SourceSummary(kind=kind, source_id=source_id, source_schema=schema, inst_id=fm.inst_id,
                            index_id=fm.index_id, source_status=facts["quality"], coverage=fm.coverage,
                            warnings=tuple(warnings), exclusions=exclusions, notes=tuple(facts["notes"]))
    method = ((f"{schema} verify of a private snapshot of the source package (once), then a streaming build of "
               f"feed cache {cid} from that snapshot only; durable publication recorded as a trusted receipt")
              if not warm else
              (f"reused feed cache {cid}: its manifest SHA-256 matches the trusted receipt recorded "
               f"{receipt['created_at'].isoformat()} after a verified, durable preparation; the package manifest "
               f"SHA-256 {msha[:16]} selected the cache and every partition is SHA-256-verified when read"))
    verification = SourceVerification(verified=True, method=method, problems=(), checked_at=datetime.now(UTC))
    loaded = LoadedSource(summary, verification, cache.feed_meta, label, ref)
    return PreparedSource(loaded, cache, warm, msha, receipt)
