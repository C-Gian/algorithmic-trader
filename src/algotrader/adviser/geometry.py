"""Structural area versus current admissible prices (MP-001 §8), exact arithmetic.

Direction d = +1 LONG / -1 SHORT. For price p: G = 10000*d*(T-p)/p, Q = 10000*d*(p-V)/p. With a pinned round-trip
adequacy envelope K the predicate is G > K, Q > 0, (G-K)/(Q+K) >= r (r = 1.2). The structural area
LONG = [max(V+tick, tc - 0.25*S15), min(T-tick, tc + 0.25*S15)] (SHORT mirrors) is an immutable container, not a
promise that every price inside it is acceptable. The current admissible set is the tick prices in the area that
satisfy the predicate; for a constant K the bound is LONG p <= (T+rV)/((1+r)(1+K/10000)), SHORT
p >= (T+rV)/((1+r)(1-K/10000)), rounded inward and verified with the direct predicate at the endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .measures import div, round_down, round_up

BPS = Decimal(10000)


@dataclass(frozen=True)
class Check:
    ok: bool
    g: Decimal | None
    q: Decimal | None
    margin: Decimal | None  # G - r*Q - (1+r)*K  (>= 0 iff the ratio predicate holds, given Q+K > 0)
    reason: str | None


def predicate(d: int, p: Decimal, v: Decimal, t: Decimal, k: Decimal, r: Decimal) -> Check:
    if p <= 0 or k >= BPS or k < 0:
        return Check(False, None, None, None, "INVALID_INPUT")
    g = div(BPS * d * (t - p), p)
    qq = div(BPS * d * (p - v), p)
    margin = g - r * qq - (1 + r) * k
    if not g > k:
        return Check(False, g, qq, margin, "NO_ROOM_AFTER_COSTS")
    if not qq > 0:
        return Check(False, g, qq, margin, "AT_OR_BEYOND_INVALIDATION")
    if not div(g - k, qq + k) >= r:
        return Check(False, g, qq, margin, "REWARD_RISK_BELOW_MINIMUM")
    return Check(True, g, qq, margin, None)


def structural_area(d: int, tc: Decimal, v: Decimal, t: Decimal, s15: Decimal, frac: Decimal,
                    tick: Decimal) -> tuple[Decimal, Decimal] | None:
    """Inward tick-rounded container; None when empty."""
    half = s15 * frac
    if d > 0:
        lo, hi = max(v + tick, tc - half), min(t - tick, tc + half)
    else:
        lo, hi = max(t + tick, tc - half), min(v - tick, tc + half)
    lo, hi = round_up(lo, tick), round_down(hi, tick)
    return (lo, hi) if lo <= hi else None


def admissible_bounds(d: int, area: tuple[Decimal, Decimal], v: Decimal, t: Decimal, k: Decimal, r: Decimal,
                      tick: Decimal) -> tuple[Decimal, Decimal] | None:
    """Current admissible tick prices inside ``area`` for constant envelope K (verified at the inner endpoint)."""
    if k >= BPS or k < 0:
        return None
    lo, hi = area
    if d > 0:
        bound = round_down(div(t + r * v, (1 + r) * (1 + div(k, BPS))), tick)
        hi = min(hi, bound)
        while hi >= lo and not predicate(d, hi, v, t, k, r).ok:  # endpoint verification (exactness guard)
            hi -= tick
    else:
        bound = round_up(div(t + r * v, (1 + r) * (1 - div(k, BPS))), tick)
        lo = max(lo, bound)
        while lo <= hi and not predicate(d, lo, v, t, k, r).ok:
            lo += tick
    if lo > hi:
        return None
    return lo, hi


def in_area(p: Decimal, area: tuple[Decimal, Decimal] | None) -> bool:
    return area is not None and area[0] <= p <= area[1]
