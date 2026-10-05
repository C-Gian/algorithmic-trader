"""Small INDEPENDENT reference for the MP-002 arithmetic, clocks and A routing table (tests only).

Exact rational arithmetic (``fractions.Fraction``), written from the rule text without importing the product's
geometry/core modules, so agreement is not shared-helper agreement. LONG and SHORT economics are computed separately
with their real positive price denominators (no affine reflection of a bound).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from fractions import Fraction as F

R_MIN = F(6, 5)  # net reward/risk 1.2
BPS = F(10000)


def g_q(d: int, p, v, t) -> tuple[F, F]:
    p, v, t = F(str(p)), F(str(v)), F(str(t))
    return BPS * d * (t - p) / p, BPS * d * (p - v) / p


def passes(d: int, p, v, t, k) -> bool:
    g, q = g_q(d, p, v, t)
    k = F(str(k))
    return g > k and q > 0 and (g - k) / (q + k) >= R_MIN


def bound_long(t, v, k) -> F:
    """Upper admissible LONG price for constant K: p <= (T + r V) / ((1 + r)(1 + K/10000))."""
    return (F(str(t)) + R_MIN * F(str(v))) / ((1 + R_MIN) * (1 + F(str(k)) / BPS))


def bound_short(t, v, k) -> F:
    """Lower admissible SHORT price: p >= (T + r V) / ((1 + r)(1 - K/10000))."""
    return (F(str(t)) + R_MIN * F(str(v))) / ((1 + R_MIN) * (1 - F(str(k)) / BPS))


def floor_tick(x: F, tick=F(1, 10)) -> F:
    return (x // tick) * tick


def ceil_tick(x: F, tick=F(1, 10)) -> F:
    return -((-x) // tick) * tick


def corridor_long(r, k_trigger, v, t, tick=F(1, 10)) -> tuple[F, F] | None:
    lo = max(ceil_tick(F(str(r)), tick), F(str(v)) + tick)
    hi = min(floor_tick(F(str(k_trigger)), tick), F(str(t)) - tick)
    return None if hi < lo else (lo, hi)


def corridor_short(r, k_trigger, v, t, tick=F(1, 10)) -> tuple[F, F] | None:
    """SHORT: prices between the trigger anchor K (below) and the reaction high R (above), strictly inside (T, V)."""
    lo = max(ceil_tick(F(str(k_trigger)), tick), F(str(t)) + tick)
    hi = min(floor_tick(F(str(r)), tick), F(str(v)) - tick)
    return None if hi < lo else (lo, hi)


def economic_long(cor, v, t, k, tick=F(1, 10)):
    if cor is None:
        return None
    hi = min(cor[1], floor_tick(bound_long(t, v, k), tick))
    while hi >= cor[0] and not passes(1, hi, v, t, k):
        hi -= tick
    return None if hi < cor[0] else (cor[0], hi)


def economic_short(cor, v, t, k, tick=F(1, 10)):
    if cor is None:
        return None
    lo = max(cor[0], ceil_tick(bound_short(t, v, k), tick))
    while lo <= cor[1] and not passes(-1, lo, v, t, k):
        lo += tick
    return None if lo > cor[1] else (lo, cor[1])


# -- clocks (MP-002 §7) -----------------------------------------------------------------------------------------

def a_clocks(tc: datetime, ti: datetime, setup_expiry: datetime) -> dict:
    h = tc + timedelta(hours=4)
    residual = h - ti
    return {"hard": h, "scenario_progress": tc + timedelta(hours=2), "call_progress": ti + residual / 2,
            "wait_until": setup_expiry, "issue_allowed": ti < setup_expiry and residual >= timedelta(minutes=30),
            "duration_window": (30, min(180, int(residual.total_seconds() // 60))),
            "horizon_only_request": h}


# -- A routing table (MP-002 §5) ---------------------------------------------------------------------------------

ROUTABLE = {"NO_ROOM_AFTER_COSTS", "REWARD_RISK_BELOW_MINIMUM", "EMPTY_STRUCTURAL_AREA", "PRICE_OUTSIDE_STRUCTURAL_AREA"}


def route(*, structural: str | None, target_contact: bool, prerequisites_ok: bool, nonselection: list[str],
          immediate: list[str], corridor_nonempty: bool, economic_nonempty: bool) -> str:
    """First matching row of the MP-002 §5 table -> child entry result."""
    if structural:
        return f"TERMINAL:{structural}"
    if target_contact:
        return "TERMINAL:PRE_ENTRY_TARGET_CONTACT"
    if not prerequisites_ok:
        return "TERMINAL:UNAVAILABLE_GEOMETRY"
    if nonselection:
        return "TERMINAL:NONSELECTION_GATE"
    if not immediate:
        return "IMMEDIATE"
    if not set(immediate) <= ROUTABLE:
        return "TERMINAL:IMMEDIATE_INCOMPATIBLE"
    if not corridor_nonempty:
        return "TERMINAL:EMPTY_RETURN_CORRIDOR"
    if not economic_nonempty:
        return "TERMINAL:NO_ECONOMIC_RETURN_REGION"
    return "WAIT_PRICE"
