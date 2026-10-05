"""Incremental causal kernel and explicit restorable state (WP-008-R1B).

One sequential kernel serves max-speed, paced and STEP execution. It applies every admitted event with
the accepted pure reducer ``feed.state.apply`` (the same code as the small-fixture reference
``observe.core``), but it does NOT build/hash a public snapshot, delta or delivery record per event:
snapshots are materialized only at checkpoints, inspections and terminal boundaries. Because the reducer
is identical, the state after k events equals the reference prefix state, and a snapshot materialized at
cursor k has exactly the reference digest (verified by differential tests).

State format ``algotrader.observe-state.v1``: explicit validated JSON (never pickle) of the reducer state -
freshness policy, feed manifest reference, every channel's coverage / latest valid / latest slot / last
quality / counts / bounded history / rejection flag, and the cursor (applied count, last event id, last
total-order key). Stored zlib-compressed with the SHA-256 of its canonical JSON.

Engine ``observe.stream.v2`` (WP-008-R2) additionally drives the causal temporal substrate
(``algotrader.temporal.v1``, engine ``temporal.engine.v1``) with every applied event, beside - never inside - the
factual reducer. Its explicit restore state (``algotrader.temporal-state.v1``) is stored separately next to the
unchanged factual state, so the factual state SHA-256 / snapshot digests keep their exact R1B/R1C meaning.
``observe.stream.v1`` runs (no temporal state) remain readable and keep their own compatibility fingerprint.
"""

from __future__ import annotations

import hashlib
import zlib
from datetime import datetime
from typing import Any

from ..feed.adapter import Feed
from ..feed.contracts import (
    ChannelCounts,
    ChannelCoverage,
    FeedCursor,
    FeedEvent,
    FreshnessPolicy,
    ObservableSnapshot,
)
from ..feed.ordering import canonical
from ..feed.state import ChannelState, ObservableState, apply, initial_state, snapshot
from ..temporal import engine as temporal_engine
from ..temporal.contracts import TEMPORAL_SCHEMA_REVISION, TEMPORAL_SCHEMA_VERSION
from ..temporal.engine import TemporalError
from .feedcache import extend_commitment

STATE_FORMAT = "algotrader.observe-state.v1"
ENGINE_FORMAT_V1 = "observe.stream.v1"  # R1B/R1C runs: factual state only
ENGINE_FORMAT = "observe.stream.v2"  # R2 runs: factual state + causal temporal substrate
ENGINE_FORMAT_V3 = "observe.stream.v3"  # WP-009 adviser evaluations: + algotrader.adviser-runtime.v2 professional state (v1 states are incompatible)
ENGINE_FORMAT_V4 = "observe.stream.v4"  # WP-011 MP-002 v0.3 adviser evaluations: + algotrader.adviser-runtime.v3
STREAM_ENGINE_FORMATS = frozenset({ENGINE_FORMAT_V1, ENGINE_FORMAT, ENGINE_FORMAT_V3, ENGINE_FORMAT_V4})


class StateError(Exception):
    """A stored state is missing, incompatible or corrupt."""


def _ev(e: FeedEvent | None) -> dict | None:
    return None if e is None else e.model_dump(mode="json")


def encode_state(state: ObservableState) -> dict:
    return {
        "format": STATE_FORMAT,
        "freshness": state.freshness.model_dump(mode="json"),
        "feed_manifest_ref": [state.feed_manifest_ref[0], state.feed_manifest_ref[1], state.feed_manifest_ref[2],
                              list(state.feed_manifest_ref[3])],
        "channels": [[cid, {
            "coverage": st.coverage.model_dump(mode="json"), "latest_valid": _ev(st.latest_valid),
            "latest_slot": _ev(st.latest_slot), "last_quality": _ev(st.last_quality),
            "quality_since_valid": st.quality_since_valid, "counts": st.counts.model_dump(mode="json"),
            "history": [_ev(h) for h in st.history], "seen_rejected": st.seen_rejected,
        }] for cid, st in state.channels],
        "cursor": state.cursor.model_dump(mode="json"),
    }


def _dev(d: dict | None) -> FeedEvent | None:
    return None if d is None else FeedEvent.model_validate(d)


def decode_state(doc: dict) -> ObservableState:
    if doc.get("format") != STATE_FORMAT:
        raise StateError(f"state format {doc.get('format')!r} is not {STATE_FORMAT}")
    ref = doc["feed_manifest_ref"]
    channels = tuple(
        (cid, ChannelState(
            coverage=ChannelCoverage.model_validate(c["coverage"]), latest_valid=_dev(c["latest_valid"]),
            latest_slot=_dev(c["latest_slot"]), last_quality=_dev(c["last_quality"]),
            quality_since_valid=int(c["quality_since_valid"]), counts=ChannelCounts.model_validate(c["counts"]),
            history=tuple(FeedEvent.model_validate(h) for h in c["history"]), seen_rejected=bool(c["seen_rejected"]),
        ))
        for cid, c in doc["channels"]
    )
    return ObservableState(freshness=FreshnessPolicy.model_validate(doc["freshness"]),
                           feed_manifest_ref=(ref[0], ref[1], ref[2], tuple(ref[3])), channels=channels,
                           cursor=FeedCursor.model_validate(doc["cursor"]))


def pack_state(state: ObservableState) -> tuple[bytes, str]:
    """(zlib blob, sha256 of the canonical JSON)."""
    raw = canonical(encode_state(state))
    return zlib.compress(raw, 6), hashlib.sha256(raw).hexdigest()


def unpack_state(blob: bytes, sha256: str) -> ObservableState:
    try:
        raw = zlib.decompress(blob)
    except zlib.error as exc:
        raise StateError(f"state blob not decompressible: {exc}") from None
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise StateError("state blob SHA-256 mismatch (corrupt)")
    import json

    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise StateError(f"state JSON unreadable: {exc}") from None
    state = decode_state(doc)
    if canonical(encode_state(state)) != raw:
        raise StateError("state does not round-trip exactly")
    return state


def fingerprint(cache_id: str, freshness: FreshnessPolicy, engine_format: str = ENGINE_FORMAT_V1) -> str:
    """Compatibility fingerprint of the factual state: engine/state format + feed cache + freshness/history policy.
    (The temporal state carries its own profile fingerprint.)"""
    return hashlib.sha256(canonical({"engine": engine_format, "state": STATE_FORMAT, "cache": cache_id,
                                     "freshness": freshness.model_dump(mode="json")})).hexdigest()


def temporal_config(manifest, dependencies=None) -> dict[str, Any]:
    """Pinned temporal configuration of a new R2 run (profile, clock policy, finite clock end, fingerprint).
    Adviser runs pin the MP-001 named dependencies for readiness inspection (the core applies its own rules)."""
    profile = (temporal_engine.profile_for_feed(manifest) if dependencies is None else
               temporal_engine.profile_for_feed(manifest, dependencies=dependencies))
    eng = temporal_engine.for_feed(manifest, profile)
    return {"contract": TEMPORAL_SCHEMA_VERSION, "contract_revision": TEMPORAL_SCHEMA_REVISION,
            "engine": temporal_engine.ENGINE_ID, "state_format": temporal_engine.STATE_FORMAT,
            "profile": temporal_engine.profile_doc(profile), "fingerprint": eng.fingerprint,
            "clock_policy": profile.clock_policy.value, "seal_policy": profile.seal_policy_id,
            "clock_end": eng.default_clock_end().isoformat(), "labels": list(profile.labels)}


def new_temporal(manifest, engine: dict[str, Any]) -> temporal_engine.TemporalEngine | None:
    """A fresh temporal engine for a run's pinned configuration (None for observe.stream.v1 runs)."""
    tc = engine.get("temporal")
    if not tc:
        return None
    from ..temporal.contracts import TemporalProfile

    eng = temporal_engine.for_feed(manifest, TemporalProfile.model_validate(tc["profile"]))
    if eng.fingerprint != tc["fingerprint"]:
        raise StateError("temporal profile fingerprint differs from the configuration pinned at preparation")
    return eng


def restore_temporal(rp: dict[str, Any], engine: dict[str, Any]) -> temporal_engine.TemporalEngine | None:
    """Decode and verify a restore point's temporal state (required for temporal-enabled runs)."""
    tc = engine.get("temporal")
    if not tc:
        return None
    if rp.get("temporal_format") != tc["state_format"] or rp.get("temporal_blob") is None:
        raise StateError(f"restore point {rp['cursor']} has no {tc['state_format']} temporal state")
    try:
        eng = temporal_engine.unpack(bytes(rp["temporal_blob"]), rp["temporal_sha256"])
    except TemporalError as exc:
        raise StateError(f"temporal state at cursor {rp['cursor']}: {exc}") from None
    if eng.fingerprint != tc["fingerprint"]:
        raise StateError(f"temporal fingerprint mismatch at cursor {rp['cursor']}")
    if eng.cursor != rp["cursor"]:
        raise StateError(f"temporal cursor {eng.cursor} != restore point {rp['cursor']}")
    return eng


class Kernel:
    """Sequential application of canonical event lines to the observable state."""

    def __init__(self, feed_meta: Feed, freshness: FreshnessPolicy, state: ObservableState | None,
                 commitment: bytes, temporal: temporal_engine.TemporalEngine | None = None, adviser=None) -> None:
        self.feed = feed_meta
        self.freshness = freshness
        self.state = state if state is not None else initial_state(feed_meta, freshness)
        self.commitment = commitment
        self.temporal = temporal
        if temporal is not None and temporal.cursor != self.state.cursor.applied_events:
            raise StateError(f"temporal cursor {temporal.cursor} != factual cursor {self.state.cursor.applied_events}")
        self.adviser = adviser  # AdviserRuntime (observe.stream.v3) or None
        if adviser is not None:
            if temporal is None:
                raise StateError("an adviser runtime requires the temporal substrate")
            adviser.attach(temporal)
            if adviser.admitted != self.state.cursor.applied_events:
                raise StateError(f"adviser cursor {adviser.admitted} != factual cursor "
                                 f"{self.state.cursor.applied_events}")
        self.counters = {"events_decoded": 0, "events_applied": 0, "snapshots_built": 0, "state_encodes": 0}

    @property
    def cursor(self) -> int:
        return self.state.cursor.applied_events

    def apply_line(self, line: bytes) -> FeedEvent:
        e = FeedEvent.model_validate_json(line)
        self.counters["events_decoded"] += 1
        before = self.state.cursor.applied_events
        self.state = apply(self.state, e)  # the accepted pure reducer (ordering/duplicate checks included)
        if self.temporal is not None:
            self.temporal.on_event(e, before)  # factual admission first, then the temporal clock policy
        if self.adviser is not None:
            self.adviser.before_admit(e)  # professional barriers strictly before this event's availability
            self.adviser.admit(e, before)
        self.commitment = extend_commitment(self.commitment, line)
        self.counters["events_applied"] += 1
        return e

    def as_of(self) -> datetime:
        last = self.state.cursor.last_order
        if last is not None:
            return last.available_time
        return min(c.covered_from for c in self.feed.manifest.coverage)

    def snapshot(self) -> ObservableSnapshot:
        self.counters["snapshots_built"] += 1
        return snapshot(self.state, self.as_of(), self.feed)

    def pack(self) -> tuple[bytes, str]:
        self.counters["state_encodes"] += 1
        return pack_state(self.state)

    def pack_temporal(self) -> tuple[bytes, str] | None:
        return None if self.temporal is None else temporal_engine.pack(self.temporal)

    def pack_adviser(self) -> tuple[bytes, str] | None:
        if self.adviser is None:
            return None
        from ..adviser.engine import pack_runtime

        return pack_runtime(self.adviser)

    def finish(self, clock_end: datetime) -> None:
        """Professional clock-end finish (adviser runs): the temporal finish (final closures) then the adviser's
        remaining barriers/timers up to the declared finite clock end and the evaluator's tail censoring."""
        if self.temporal is None or self.adviser is None:
            raise StateError("finish() is only defined for adviser runs")
        self.temporal.finish(clock_end)
        self.adviser.finish(clock_end)
