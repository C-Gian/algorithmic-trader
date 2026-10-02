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
