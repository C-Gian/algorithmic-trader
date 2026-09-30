"""Terminal observation-replay artifacts and validation.

Written once per replay under ``<artifact root>/observations/<replay_id>/``:

* ``config.json``         - the replay config (source, verification, feed identity, policies);
* ``deliveries.jsonl``    - the ordered committed delivery identities (+ snapshot digest after each);
* ``final_snapshot.json`` - the final ObservableSnapshot (full, including bounded history);
* ``validation.json``     - independent re-derivation checks;
* ``manifest.json``       - written last and atomically; lists every file with its SHA-256.

Immutable source evidence is referenced (dataset / recording id), never copied.
A finalize that is repeated after an interruption reuses an existing manifest.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..feed.contracts import ObservableSnapshot
from ..feed.state import snapshot_at
from .contracts import (
    LABELS,
    OBSERVE_CONTRACT_STATUS,
    OBSERVE_SCHEMA_REVISION,
    OBSERVE_SCHEMA_VERSION,
    ArtifactFile,
    DeliveryRecord,
    ObservationReplayConfig,
    ObservationReplayManifest,
    ReplayStatus,
    ReplayValidation,
    ValidationCheck,
)
from .core import ReplayCore, as_of
from .sources import LoadedSource, feed_identity


def replay_dir(root: Path, replay_id: str) -> Path:
    return root / "observations" / replay_id


def _sha256(path: Path) -> tuple[str, int, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data), data.count(b"\n")


def _no_future(snap: ObservableSnapshot) -> str | None:
    for c in snap.channels:
        for e in (c.latest_valid, c.last_quality, *c.history):
            if e is not None and e.available_time > snap.as_of:
                return f"{c.channel_id}: {e.event_id} available {e.available_time.isoformat()} > as_of"
    return None


def validate(config: ObservationReplayConfig, source: LoadedSource | None, deliveries: list[DeliveryRecord],
             cursor: int, final_digest: str, status: ReplayStatus) -> tuple[ReplayValidation, ObservableSnapshot | None]:
    """Re-derive the replay from the immutable source and compare with what was committed."""
    checks: list[ValidationCheck] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ValidationCheck(name=name, passed=ok, detail=detail))

    if source is None:
        check("source_loadable", False, "the source could not be loaded; nothing could be re-derived")
        return ReplayValidation(passed=False, checks=tuple(checks)), None
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
    for d in deliveries[:cursor]:
        if pos.cursor >= core.total:
            mismatch = f"delivery {d.seq} beyond the feed"
            break
        pos, rec = core.step(pos)
        if rec.snapshot_digest != d.snapshot_digest and mismatch is None:
            mismatch = f"delivery {d.seq}: committed digest differs from the pure re-derivation"
        future = future or _no_future(pos.snapshot)
    check("digests_match_pure_replay", mismatch is None and pos.snapshot.content_digest == final_digest,
          mismatch or f"every per-delivery snapshot digest and the final digest {final_digest[:16]} re-derived")
    check("no_future_knowledge", future is None,
          future or "no snapshot contained evidence available after its information time")
    check("observation_only", set(pos.snapshot.labels) >= {"OBSERVATION_ONLY", "NO_INTERPRETATION"},
          f"snapshot labels {list(pos.snapshot.labels)}; no MarketView/decision/order/account records")
    if status == ReplayStatus.COMPLETED:
        pure = snapshot_at(source.feed, as_of(source.feed, core.total), config.freshness_policy)
        check("completed_equals_pure_cutoff_snapshot",
              cursor == core.total and pure.content_digest == final_digest,
              f"all {core.total} deliveries applied; final state equals snapshot_at(feed, last availability)")
    return ReplayValidation(passed=all(c.passed for c in checks), checks=tuple(checks)), pos.snapshot


def write_replay_artifacts(root: Path, row: dict[str, Any], status: ReplayStatus, error: str | None,
                           finished_at: datetime, deliveries: list[DeliveryRecord], cursor: int, final_digest: str,
                           source: LoadedSource | None) -> ObservationReplayManifest:
    out = replay_dir(root, row["replay_id"])
    if (out / "manifest.json").is_file():  # finalize repeated after an interruption: never rewrite
        return ObservationReplayManifest.model_validate_json((out / "manifest.json").read_text(encoding="utf-8"))
    config = ObservationReplayConfig.model_validate(row["config"])
    validation, final = validate(config, source, deliveries, cursor, final_digest, status)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
    with (out / "deliveries.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for d in deliveries:
            f.write(d.model_dump_json() + "\n")
    if final is not None:
        (out / "final_snapshot.json").write_text(final.model_dump_json(indent=2), encoding="utf-8")
    (out / "validation.json").write_text(validation.model_dump_json(indent=2), encoding="utf-8")
    files = []
    for p in sorted(x for x in out.iterdir() if x.is_file() and x.name != "manifest.json"
                    and not x.name.startswith(".")):
        digest, size, lines = _sha256(p)
        files.append(ArtifactFile(name=p.name, sha256=digest, bytes=size, lines=lines if p.suffix == ".jsonl" else None))
    manifest = ObservationReplayManifest(
        schema_version=OBSERVE_SCHEMA_VERSION,
        contract_status=OBSERVE_CONTRACT_STATUS,
        schema_revision=OBSERVE_SCHEMA_REVISION,
        replay_id=row["replay_id"],
        status=status,
        labels=LABELS,
        config=config,
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=finished_at,
        applied_events=cursor,
        total_events=row["total_events"],
        final_as_of=final.as_of if final is not None else finished_at,
        final_snapshot_id=final.snapshot_id if final is not None else "",
        final_content_digest=final_digest,
        attempts=row["attempt"],
        recovery_log=list(row["recovery_log"]),
        control_log=list(row["control_log"]),
        error=error,
        validation=validation,
        source_reference=(source.reference if source is not None
                          else f"{config.source.kind.value}s/{config.source.source_id}"),
        artifacts=tuple(files),
    )
    tmp = out / ".manifest.json.tmp"
    tmp.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, out / "manifest.json")
    return manifest


def load_replay_manifest(root: Path, replay_id: str) -> ObservationReplayManifest | None:
    p = replay_dir(root, replay_id) / "manifest.json"
    return ObservationReplayManifest.model_validate_json(p.read_text(encoding="utf-8")) if p.is_file() else None
