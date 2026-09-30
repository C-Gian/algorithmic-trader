"""Deterministic ordering, availability/freshness policies and canonical hashing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from ..marketdata.contracts import AVAILABILITY_POLICY_ID as MARKETDATA_POLICY_ID
from .contracts import (
    FAMILY_RANK,
    KIND_RANK,
    AvailabilityBasis,
    AvailabilityPolicy,
    FeedEvent,
    FreshnessPolicy,
    OrderKey,
)


class FeedError(Exception):
    """The feed would be ambiguous or non-causal."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _iso_duration(td: timedelta) -> str:
    return f"PT{int(td.total_seconds())}S" if td.microseconds == 0 else f"PT{td.total_seconds()}S"


def modeled_availability(bar_delay: timedelta = timedelta(0), funding_delay: timedelta = timedelta(0)) -> AvailabilityPolicy:
    """Feed availability = marketdata.v1 modeled availability + an explicit non-negative delay.

    The zero delay reproduces the WP-003 convention (bar close / funding time). It is a
    lower-bound modeling convention, not a measured publication latency; no delay value
    here is a measurement.
    """
    if bar_delay < timedelta(0) or funding_delay < timedelta(0):
        raise ValueError("availability delay must be non-negative (a delay can only postpone knowledge)")
    return AvailabilityPolicy(
        policy_id=f"feed.modeled.v1(bar+{_iso_duration(bar_delay)},funding+{_iso_duration(funding_delay)})",
        basis=AvailabilityBasis.MODELED,
        base_policy_id=MARKETDATA_POLICY_ID,
        bar_delay=bar_delay,
        funding_delay=funding_delay,
        measured=False,
        note=(
            "MODELED availability: marketdata.v1 modeled availability plus the stated delay. "
            + ("Zero delay is a lower-bound convention, not a measurement." if not (bar_delay or funding_delay)
               else "The delay is a modeling assumption, not a measurement.")
        ),
    )


def default_freshness(
    bar_max_age: timedelta = timedelta(minutes=2), history_limit: int = 240
) -> FreshnessPolicy:
    return FreshnessPolicy(
        policy_id=f"feed.freshness.v1(bar<={_iso_duration(bar_max_age)},funding=n/a,history={history_limit})",
        bar_max_age=bar_max_age,
        funding_max_age=None,
        history_limit=history_limit,
        note="Inspection default for developer tooling; not a validated research parameter.",
    )


def order_key(event_id: str, family, series_id: str, event_time, kind, available_time) -> OrderKey:
    return OrderKey(
        available_time=available_time,
        family_rank=FAMILY_RANK[family],
        series_id=series_id,
        event_time=event_time,
        kind_rank=KIND_RANK[kind],
        event_id=event_id,
    )


def sort_key(order: OrderKey) -> tuple:
    return (order.available_time, order.family_rank, order.series_id, order.event_time, order.kind_rank,
            order.event_id)


def slot_key(event: FeedEvent) -> tuple[str, Any]:
    return (event.channel.channel_id, event.event_time)


def order_events(events: Iterable[FeedEvent]) -> tuple[FeedEvent, ...]:
    """Total deterministic order; rejects ambiguous slots (two events for one channel slot)."""
    out = tuple(sorted(events, key=lambda e: sort_key(e.order)))
    seen: dict[tuple, str] = {}
    for e in out:
        k = slot_key(e)
        if k in seen:
            raise FeedError(f"ambiguous slot {k[0]} @ {k[1].isoformat()}: {seen[k]} and {e.event_id}")
        seen[k] = e.event_id
    return out


def event_digest_payload(event: FeedEvent) -> dict:
    return event.model_dump(mode="json")


def ordered_event_hash(events: Iterable[FeedEvent]) -> str:
    h = hashlib.sha256()
    for e in events:
        h.update(canonical(event_digest_payload(e)))
        h.update(b"\n")
    return h.hexdigest()
