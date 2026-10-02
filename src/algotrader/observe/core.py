"""Pure event-driven observation-replay core (no DB, no clock, no trader).

One step == one causal feed delivery, in the accepted ``feed.v1`` total order:

1. take the next ``FeedEvent`` (``feed.events[cursor]``);
2. apply it with the accepted pure reducer ``feed.state.apply``;
3. replay/information time := that event's ``available_time``;
4. derive the ``ObservableSnapshot`` with the accepted ``feed.state.snapshot``.

The state at cursor *k* is, by construction, ``apply_all(initial, events[:k])``;
a restarted replay rebuilds it from the committed cursor and checks the digest
persisted with that cursor, so a restart can never apply a committed delivery
twice or silently diverge.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ..feed.adapter import Feed
from ..feed.contracts import ChannelChange, FeedEvent, FreshnessPolicy, ObservableSnapshot
from ..feed.ordering import FeedError
from ..feed.state import ObservableState, apply, apply_all, initial_state, make_delta, snapshot
from .contracts import DeliveryRecord


@dataclass(frozen=True)
class Position:
    cursor: int  # applied deliveries
    state: ObservableState
    snapshot: ObservableSnapshot


def initial_as_of(feed: Feed) -> datetime:
    """Information time before any delivery: the start of the evidence coverage (nothing known yet)."""
    return min(c.covered_from for c in feed.manifest.coverage)


def as_of(feed: Feed, cursor: int) -> datetime:
    return feed.events[cursor - 1].available_time if cursor else initial_as_of(feed)


def changed(changes: tuple[ChannelChange, ...]) -> tuple[ChannelChange, ...]:
    return tuple(c for c in changes if c.new_events or c.condition_before != c.condition_after
                 or c.freshness_before != c.freshness_after or c.latest_valid_before != c.latest_valid_after)


class ReplayCore:
    def __init__(self, feed: Feed, freshness: FreshnessPolicy) -> None:
        self.feed = feed
        self.freshness = freshness

    @property
    def total(self) -> int:
        return len(self.feed.events)

    def at(self, cursor: int, progress: Callable[[int, int], None] | None = None) -> Position:
        """Position after exactly ``cursor`` committed deliveries (pure prefix replay).

        ``progress(done, total)`` is an optional cooperative hook called between applied events of the
        prefix rebuild (same fold as ``apply_all``); it may raise to cancel and never changes the state.
        """
        if not 0 <= cursor <= self.total:
            raise FeedError(f"cursor {cursor} outside feed of {self.total} events")
        state = initial_state(self.feed, self.freshness)
        if progress is None:
            state = apply_all(state, self.feed.events[:cursor])
        else:
            for i, e in enumerate(self.feed.events[:cursor]):
                progress(i, cursor)
                state = apply(state, e)
            progress(cursor, cursor)
        return Position(cursor, state, snapshot(state, as_of(self.feed, cursor), self.feed))

    def step(self, pos: Position) -> tuple[Position, DeliveryRecord]:
        """Apply the next feed delivery. Raises FeedError when the feed is exhausted."""
        if pos.cursor >= self.total:
            raise FeedError("no feed deliveries left")
        event: FeedEvent = self.feed.events[pos.cursor]
        state = apply(pos.state, event)
        snap = snapshot(state, event.available_time, self.feed)
        delta = make_delta(pos.snapshot, snap, (event,))
        record = DeliveryRecord(
            seq=pos.cursor,
            event_id=event.event_id,
            channel_id=event.channel.channel_id,
            family=event.channel.family,
            kind=event.kind,
            event_time=event.event_time,
            event_end_time=event.event_end_time,
            available_time=event.available_time,
            quality_reason=getattr(event.payload, "reason", None),
            snapshot_id=snap.snapshot_id,
            snapshot_digest=snap.content_digest,
            changes=changed(delta.channel_changes),
        )
        return Position(pos.cursor + 1, state, snap), record


def snapshot_view(snap: ObservableSnapshot) -> dict:
    """Compact JSON view for the API/UI: the snapshot without per-channel history (history length kept)."""
    doc = snap.model_dump(mode="json", exclude={"channels": {"__all__": {"history"}}})
    for ch, full in zip(doc["channels"], snap.channels):
        ch["history_len"] = len(full.history)
    return doc
