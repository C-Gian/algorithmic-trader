"""UTC interval arithmetic only, extracted from the old temporal calendar.

Width AND grid origin are required; there is no default trading timeframe,
session, timezone for display, availability policy or closed-bar assumption.
Computing [start, end) does NOT certify that its market data is complete/known.
Calendar months/weeks and old horizon roles are intentionally not inherited.
"""

from datetime import UTC, datetime, timedelta


def to_utc(value: datetime) -> datetime:
    """Reject naive/undefined-offset datetimes; preserve the instant in UTC."""
    if not isinstance(value, datetime):
        raise TypeError("expected a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("an explicit UTC offset is required")
    return value.astimezone(UTC)


def interval_bounds(
    instant: datetime, *, minutes: int, origin: datetime
) -> tuple[datetime, datetime]:
    """Half-open grid interval containing instant, relative to explicit origin.

    Integer-minute widths only. An instant exactly at end belongs to the next
    interval. Works before origin as well. Overflow at datetime limits is not
    clipped: Python raises OverflowError rather than returning false coverage.
    """
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        raise TypeError("minutes must be an integer")
    if minutes <= 0:
        raise ValueError("minutes must be positive")
    anchor = to_utc(origin)
    if anchor.second or anchor.microsecond:
        raise ValueError("origin must be UTC-minute aligned")
    current = to_utc(instant)
    width = timedelta(minutes=minutes)
    start = anchor + ((current - anchor) // width) * width
    return start, start + width
