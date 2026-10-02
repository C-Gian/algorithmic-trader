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
"""

from __future__ import annotations

import hashlib
import zlib
from datetime import datetime

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
from .feedcache import extend_commitment

STATE_FORMAT = "algotrader.observe-state.v1"
ENGINE_FORMAT = "observe.stream.v1"


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


def fingerprint(cache_id: str, freshness: FreshnessPolicy) -> str:
    """Compatibility fingerprint: engine/state format + feed cache + freshness/history policy."""
    return hashlib.sha256(canonical({"engine": ENGINE_FORMAT, "state": STATE_FORMAT, "cache": cache_id,
                                     "freshness": freshness.model_dump(mode="json")})).hexdigest()


class Kernel:
    """Sequential application of canonical event lines to the observable state."""

    def __init__(self, feed_meta: Feed, freshness: FreshnessPolicy, state: ObservableState | None,
                 commitment: bytes) -> None:
        self.feed = feed_meta
        self.freshness = freshness
        self.state = state if state is not None else initial_state(feed_meta, freshness)
        self.commitment = commitment
        self.counters = {"events_decoded": 0, "events_applied": 0, "snapshots_built": 0, "state_encodes": 0}

    @property
    def cursor(self) -> int:
        return self.state.cursor.applied_events

    def apply_line(self, line: bytes) -> FeedEvent:
        e = FeedEvent.model_validate_json(line)
        self.counters["events_decoded"] += 1
        self.state = apply(self.state, e)  # the accepted pure reducer (ordering/duplicate checks included)
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
