"""Shared causal measurements (MP-001 §3), exact Decimal arithmetic only.

For complete bar j at horizon H: TR_j = max(high-low, |high-prev_close|, |low-prev_close|);
S_H = median of 20 contiguous TR (21 complete bars); zero scale is UNAVAILABLE (None).
ER_n = |C_j - C_(j-n)| / sum |C_k - C_(k-1)| over n transitions (zero denominator with complete inputs -> 0).
Signed displacement = (C_j - C_(j-n)) / S_H. Median of an even count is the mean of the two middle values.
These facets describe one price path; they are not independent votes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext

ZERO = Decimal(0)
# Ratios are compared exactly; the context precision only bounds non-terminating quotients (e.g. /3).
PRECISION = 50


@dataclass(frozen=True, slots=True)
class Bar:
    """A COMPLETE sealed trade bar (any horizon), in market prices."""

    start: datetime
    end: datetime
    o: Decimal
    h: Decimal
    lo: Decimal
    c: Decimal
    vol: Decimal | None  # base-currency volume (participation only)
    known_at: datetime
    rid: str

    def encode(self) -> list:
        return [self.start.isoformat(), self.end.isoformat(), str(self.o), str(self.h), str(self.lo), str(self.c),
                None if self.vol is None else str(self.vol), self.known_at.isoformat(), self.rid]

    @classmethod
    def decode(cls, x: list) -> Bar:
        return cls(datetime.fromisoformat(x[0]), datetime.fromisoformat(x[1]), Decimal(x[2]), Decimal(x[3]),
                   Decimal(x[4]), Decimal(x[5]), None if x[6] is None else Decimal(x[6]),
                   datetime.fromisoformat(x[7]), x[8])


def div(a: Decimal, b: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return a / b


def median(xs: list[Decimal]) -> Decimal:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("median of nothing")
    mid = n // 2
    if n % 2:
        return s[mid]
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return (s[mid - 1] + s[mid]) / 2


def true_range(h: Decimal, lo: Decimal, prev_close: Decimal) -> Decimal:
    return max(h - lo, abs(h - prev_close), abs(lo - prev_close))


def trs(bars: list[Bar]) -> list[Decimal]:
    """TR of bars[1:], each against its predecessor's close (len(bars)-1 values, oldest first)."""
    return [true_range(b.h, b.lo, a.c) for a, b in zip(bars, bars[1:])]


def scale(bars: list[Bar], n: int = 20) -> Decimal | None:
    """S = median of the last n TR (needs n+1 contiguous complete bars). Zero -> None (UNAVAILABLE)."""
    if len(bars) < n + 1:
        return None
    s = median(trs(bars[-(n + 1):]))
    return s if s > 0 else None


def efficiency(closes: list[Decimal]) -> Decimal | None:
    """ER over len(closes)-1 transitions; complete inputs with zero path -> 0."""
    if len(closes) < 2:
        return None
    path = sum((abs(b - a) for a, b in zip(closes, closes[1:])), ZERO)
    if path == 0:
        return ZERO
    return div(abs(closes[-1] - closes[0]), path)


def displacement(closes: list[Decimal], s: Decimal | None) -> Decimal | None:
    if s is None or len(closes) < 2:
        return None
    return div(closes[-1] - closes[0], s)


def round_down(p: Decimal, tick: Decimal) -> Decimal:
    return (p / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def round_up(p: Decimal, tick: Decimal) -> Decimal:
    return (p / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def zone_halfwidth(s15: Decimal, tick: Decimal, frac: Decimal, min_ticks: int) -> Decimal:
    """z = max(min_ticks ticks, frac * S15), frozen at landmark/episode/box creation."""
    return max(tick * min_ticks, s15 * frac)


def q(x: Decimal | None) -> str | None:
    """Stable exact text of a Decimal (no exponent for ordinary magnitudes)."""
    if x is None:
        return None
    t = format(x.normalize(), "f") if x == x.to_integral_value() or abs(x.as_tuple().exponent) < 30 else str(x)
    return t
