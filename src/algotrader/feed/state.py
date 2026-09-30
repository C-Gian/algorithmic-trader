"""Pure observable-market-state reducer, point-in-time snapshots and deltas.

``apply(state, event) -> state'`` never mutates its input. The state owns the
observable history (bounded per channel by the freshness policy's
``history_limit``) so a future reasoning layer never re-reads raw datasets.

Invariants enforced here:

* events must arrive in strictly increasing feed order (the ordering policy);
* a valid observation only ever enters through a BAR_/FUNDING_OBSERVATION
  event; SLOT_QUALITY events carry no values into valid state;
* the latest valid value never regresses to an older market time (a late,
  older observation enters history but does not replace the latest);
* a stale last-valid value keeps its original times; nothing is refreshed or
  fabricated;
* a snapshot cannot be taken at an ``as_of`` earlier than knowledge already
  applied (no snapshot can contain events available after its cutoff).
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime

from .adapter import Feed
from .contracts import (
    FEED_SCHEMA_VERSION,
    REJECTED_REASONS,
    ChannelChange,
    ChannelCondition,
    ChannelCounts,
    ChannelCoverage,
    ChannelSnapshot,
    EventKind,
    Family,
    FeedCursor,
    FeedEvent,
    Freshness,
    FreshnessPolicy,
    ObservableSnapshot,
    QualityReason,
    SnapshotDelta,
)
from .ordering import FeedError, digest, sort_key

_COUNT_FIELD = {
    QualityReason.MISSING: "missing",
    QualityReason.INVALID_ROW: "invalid_row",
    QualityReason.CONFLICTING_DUPLICATE: "conflicting_duplicate",
    QualityReason.INCOMPLETE_REJECTED: "incomplete_rejected",
    QualityReason.EXCLUDED_UNCLASSIFIED: "excluded_unclassified",
}
LABELS = ("OBSERVATION_ONLY", "NO_INTERPRETATION")


@dataclass(frozen=True)
class ChannelState:
    coverage: ChannelCoverage
    latest_valid: FeedEvent | None = None
    latest_slot: FeedEvent | None = None  # newest slot evidence (any kind) by market time
    last_quality: FeedEvent | None = None
    quality_since_valid: int = 0
    counts: ChannelCounts = field(default_factory=ChannelCounts)
    history: tuple[FeedEvent, ...] = ()  # valid observations sorted by market time
    seen_rejected: bool = False


@dataclass(frozen=True)
class ObservableState:
    freshness: FreshnessPolicy
    feed_manifest_ref: tuple[str, str, str, tuple[str, ...]]  # (content id, ordering id, availability id, datasets)
    channels: tuple[tuple[str, ChannelState], ...]  # sorted by channel id
    cursor: FeedCursor = FeedCursor(applied_events=0, last_event_id=None, last_order=None)

    def channel(self, channel_id: str) -> ChannelState:
        for cid, st in self.channels:
            if cid == channel_id:
                return st
        raise KeyError(channel_id)


def initial_state(feed: Feed, freshness: FreshnessPolicy) -> ObservableState:
    m = feed.manifest
    chans = tuple(sorted((c.channel.channel_id, ChannelState(coverage=c)) for c in m.coverage))
    return ObservableState(
        freshness=freshness,
        feed_manifest_ref=(m.content_identity, m.ordering_policy_id, m.availability_policy.policy_id, m.dataset_ids),
        channels=chans,
    )


def _apply_channel(st: ChannelState, e: FeedEvent, limit: int) -> ChannelState:
    newest_slot = st.latest_slot is None or e.event_time >= st.latest_slot.event_time
    if e.kind == EventKind.SLOT_QUALITY:
        reason = e.payload.reason
        name = _COUNT_FIELD[reason]
        counts = st.counts.model_copy(update={name: getattr(st.counts, name) + 1})
        newer_than_valid = st.latest_valid is None or e.event_time > st.latest_valid.event_time
        return replace(
            st,
            latest_slot=e if newest_slot else st.latest_slot,
            last_quality=e,
            quality_since_valid=st.quality_since_valid + (1 if newer_than_valid else 0),
            counts=counts,
            seen_rejected=st.seen_rejected or reason in REJECTED_REASONS,
        )
    # valid observation
    newest_valid = st.latest_valid is None or e.event_time > st.latest_valid.event_time
    times = [h.event_time for h in st.history]
    i = bisect.bisect_left(times, e.event_time)
    history = (st.history[:i] + (e,) + st.history[i:])[-limit:]
    return replace(
        st,
        latest_valid=e if newest_valid else st.latest_valid,
        latest_slot=e if newest_slot else st.latest_slot,
        quality_since_valid=0 if newest_valid else st.quality_since_valid,
        counts=st.counts.model_copy(update={"valid": st.counts.valid + 1}),
        history=history,
    )


def apply(state: ObservableState, event: FeedEvent) -> ObservableState:
    """Pure reducer: return the state after one causally ordered feed event."""
    last = state.cursor.last_order
    if last is not None and sort_key(event.order) <= sort_key(last):
        raise FeedError(f"event {event.event_id} is not after the cursor {state.cursor.last_event_id} "
                        "(out of order or duplicate delivery)")
    cid = event.channel.channel_id
    for st_cid, st in state.channels:
        if st_cid == cid:
            if any(h.event_time == event.event_time for h in st.history) or (
                st.latest_slot is not None and st.latest_slot.event_time == event.event_time
            ):
                raise FeedError(f"second event for slot {cid} @ {event.event_time.isoformat()}")
            break
    else:
        raise FeedError(f"event {event.event_id} for undeclared channel {cid}")
    channels = tuple(
        (c, _apply_channel(s, event, state.freshness.history_limit) if c == cid else s) for c, s in state.channels
    )
    cursor = FeedCursor(applied_events=state.cursor.applied_events + 1, last_event_id=event.event_id, last_order=event.order)
    return replace(state, channels=channels, cursor=cursor)


def apply_all(state: ObservableState, events: Iterable[FeedEvent]) -> ObservableState:
    for e in events:
        state = apply(state, e)
    return state


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def _condition(st: ChannelState) -> ChannelCondition:
    if st.latest_slot is None:
        return ChannelCondition.NEVER_SEEN
    if st.latest_slot.kind != EventKind.SLOT_QUALITY:
        return ChannelCondition.VALID
    if st.latest_valid is None:
        return ChannelCondition.INVALID_ONLY if st.seen_rejected else ChannelCondition.GAP
    return ChannelCondition.GAP if st.latest_slot.payload.reason == QualityReason.MISSING else ChannelCondition.REJECTED


def _freshness(st: ChannelState, cond: ChannelCondition, as_of: datetime, policy: FreshnessPolicy) -> Freshness:
    if st.latest_valid is None:
        return Freshness.UNKNOWN
    max_age = policy.funding_max_age if st.coverage.channel.family == Family.FUNDING_SETTLEMENT else policy.bar_max_age
    if max_age is None:
        return Freshness.NOT_APPLICABLE
    if cond == ChannelCondition.VALID and as_of - st.latest_valid.available_time <= max_age:
        return Freshness.FRESH
    return Freshness.STALE


def _channel_snapshot(cid: str, st: ChannelState, as_of: datetime, policy: FreshnessPolicy,
                      availability_delay) -> ChannelSnapshot:
    cond = _condition(st)
    lv = st.latest_valid
    cov = st.coverage
    # the last moment this evidence package could have spoken for the channel
    coverage_known_until = cov.covered_until + availability_delay(cov.channel.family)
    return ChannelSnapshot(
        channel=cov.channel,
        channel_id=cid,
        condition=cond,
        freshness=_freshness(st, cond, as_of, policy),
        latest_valid=lv,
        age_since_available=as_of - lv.available_time if lv else None,
        age_since_event_end=as_of - (lv.event_end_time or lv.event_time) if lv else None,
        latest_slot_time=st.latest_slot.event_time if st.latest_slot else None,
        last_quality=st.last_quality,
        quality_slots_since_valid=st.quality_since_valid,
        counts=st.counts,
        beyond_coverage=as_of > coverage_known_until,
        history=st.history,
    )


def _strip_provenance(obj):
    """Market content only: drop package/provenance references for the content digest."""
    if isinstance(obj, dict):
        return {k: _strip_provenance(v) for k, v in obj.items()
                if k not in ("source", "dataset_ids", "feed_content_identity", "snapshot_id", "content_digest")}
    if isinstance(obj, list):
        return [_strip_provenance(v) for v in obj]
    return obj


def snapshot(state: ObservableState, as_of: datetime, feed: Feed) -> ObservableSnapshot:
    """Point-in-time snapshot. ``as_of`` must not precede knowledge already applied."""
    if state.cursor.last_order is not None and as_of < state.cursor.last_order.available_time:
        raise FeedError(f"as_of {as_of.isoformat()} precedes applied knowledge "
                        f"({state.cursor.last_order.available_time.isoformat()})")
    content_id, ordering_id, availability_id, datasets = state.feed_manifest_ref
    pol = feed.manifest.availability_policy

    def delay(family: Family):
        return pol.funding_delay if family == Family.FUNDING_SETTLEMENT else pol.bar_delay

    channels = tuple(_channel_snapshot(cid, st, as_of, state.freshness, delay) for cid, st in state.channels)
    body = dict(
        schema_version=FEED_SCHEMA_VERSION,
        as_of=as_of,
        information_cutoff=as_of,
        cursor=state.cursor,
        ordering_policy_id=ordering_id,
        availability_policy_id=availability_id,
        freshness_policy_id=state.freshness.policy_id,
        feed_content_identity=content_id,
        dataset_ids=datasets,
        channels=channels,
        labels=LABELS,
    )
    draft = ObservableSnapshot(snapshot_id="", content_digest="", **body)
    dumped = draft.model_dump(mode="json")
    content = digest(_strip_provenance(dumped))
    snap_id = "snap-" + digest({"content": content, "feed": content_id, "datasets": list(datasets)})[:24]
    return draft.model_copy(update={"content_digest": content, "snapshot_id": snap_id})


# ---------------------------------------------------------------------------
# Replay helpers and delta
# ---------------------------------------------------------------------------


def events_known_at(feed: Feed, cutoff: datetime) -> tuple[FeedEvent, ...]:
    """Feed events available at or before ``cutoff`` (the knowledge prefix)."""
    return tuple(e for e in feed.events if e.available_time <= cutoff)


def state_at(feed: Feed, cutoff: datetime, freshness: FreshnessPolicy) -> ObservableState:
    return apply_all(initial_state(feed, freshness), events_known_at(feed, cutoff))


def snapshot_at(feed: Feed, cutoff: datetime, freshness: FreshnessPolicy) -> ObservableSnapshot:
    return snapshot(state_at(feed, cutoff, freshness), cutoff, feed)


def advance(feed: Feed, state: ObservableState, cutoff: datetime) -> tuple[ObservableState, tuple[FeedEvent, ...]]:
    """Apply the next feed events available at or before ``cutoff``; return them as well."""
    pending = feed.events[state.cursor.applied_events:]
    applied = tuple(e for e in pending if e.available_time <= cutoff)
    # feed order is availability-first, so the known events form a contiguous prefix
    if applied and applied != pending[: len(applied)]:
        raise FeedError("feed is not availability-ordered")
    return apply_all(state, applied), applied


def make_delta(before: ObservableSnapshot, after: ObservableSnapshot, events: tuple[FeedEvent, ...]) -> SnapshotDelta:
    if after.cursor.applied_events - before.cursor.applied_events != len(events):
        raise FeedError("delta events do not match the cursor distance between snapshots")
    if before.feed_content_identity != after.feed_content_identity:
        raise FeedError("snapshots come from different feeds")
    prev = {c.channel_id: c for c in before.channels}
    changes = []
    for c in after.channels:
        p = prev[c.channel_id]
        changes.append(ChannelChange(
            channel_id=c.channel_id,
            new_events=sum(1 for e in events if e.channel.channel_id == c.channel_id),
            condition_before=p.condition, condition_after=c.condition,
            freshness_before=p.freshness, freshness_after=c.freshness,
            latest_valid_before=p.latest_valid.event_id if p.latest_valid else None,
            latest_valid_after=c.latest_valid.event_id if c.latest_valid else None,
        ))
    body = dict(
        schema_version=FEED_SCHEMA_VERSION,
        from_snapshot_id=before.snapshot_id, to_snapshot_id=after.snapshot_id,
        from_as_of=before.as_of, to_as_of=after.as_of,
        from_cursor=before.cursor, to_cursor=after.cursor,
        events=events, channel_changes=tuple(changes),
    )
    draft = SnapshotDelta(delta_id="", **body)
    return draft.model_copy(update={"delta_id": "delta-" + digest(draft.model_dump(mode="json"))[:24]})
