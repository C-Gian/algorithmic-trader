"""UTC calendar anchors for the factual horizons (half-open intervals ``[start, end)``).

Minute/hour/day anchors are UTC midnight; weeks start Monday 00:00 UTC; months start on calendar day 1 and end at
the first day of the next calendar month. No local time, DST, fixed 30-day months or rolling windows exist here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .contracts import Horizon

MINUTE = timedelta(minutes=1)
_FIXED = {Horizon.M15: timedelta(minutes=15), Horizon.H1: timedelta(hours=1), Horizon.H4: timedelta(hours=4),
          Horizon.D1: timedelta(days=1), Horizon.W1: timedelta(days=7)}


class CalendarError(ValueError):
    """A time is not a valid UTC minute-aligned instant for this calendar."""


def utc(t: datetime) -> datetime:
    if t.tzinfo is None:
        raise CalendarError(f"naive datetime {t!r}: UTC required")
    return t.astimezone(UTC)


def is_minute_aligned(t: datetime) -> bool:
    return t.second == 0 and t.microsecond == 0


def interval_start(h: Horizon, t: datetime) -> datetime:
    t = utc(t)
    if h == Horizon.M15:
        return t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)
    if h == Horizon.H1:
        return t.replace(minute=0, second=0, microsecond=0)
    if h == Horizon.H4:
        return t.replace(hour=t.hour - t.hour % 4, minute=0, second=0, microsecond=0)
    day = t.replace(hour=0, minute=0, second=0, microsecond=0)
    if h == Horizon.D1:
        return day
    if h == Horizon.W1:
        return day - timedelta(days=day.weekday())  # Monday 00:00 UTC
    if h == Horizon.MO1:
        return day.replace(day=1)
    raise CalendarError(f"unknown horizon {h!r}")


def interval_end(h: Horizon, start: datetime) -> datetime:
    if h == Horizon.MO1:
        return start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    return start + _FIXED[h]


def expected_minutes(h: Horizon, start: datetime) -> int:
    return int((interval_end(h, start) - start) / MINUTE)


# Hard worst case of one open accumulator (a 31-day calendar month), declared for bounded-state evidence.
MAX_INTERVAL_MINUTES = 31 * 24 * 60
