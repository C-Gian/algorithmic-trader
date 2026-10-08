"""Hand-designed synthetic paths for the MP-004 v0.5 fixtures (engineering inputs, NOT market data).

They extend the MP-002 base A LONG path of ``adviser3_fixtures`` (tick 0.1, historical K_cost 14 bps, r 1.2): A
confirmation published at 04:01 (minute [04:00,04:01) closes 100050), WAIT_PRICE with V (structural = operational)
99700, T_confirm 100700, corridor [99900, 100049.9] and fixed-K economic upper bound 100014.5. Original setup deadline
05:30 (birth 03:30 + 2 h).

``REF`` is the first usable return [04:01,04:02) o 100005 h 100008 l 99990 c 99995 (an opening gap below the
confirmation close keeps H0 inside the economic region): close in the corridor and <= 100014.5, so v0.4 would issue at
04:02, while v0.5 PREPARES the reference at 04:02 - H0 100008, L0 99990, p0 04:02, cursor c0. LONG recovery = a later
complete close >= 100008.1 with low >= 99990; contradiction = low < 99990.

``NEUTRAL`` minutes (o/c 100000, h 100005, l 100000) neither recover nor contradict. The SHORT fixtures are the
positive-price reflection ``mirror`` about 100000 (x -> 200000 - x): corridor [99950.1, 100100], V 100300, T 99300,
economic lower bound 99985.5, H0 100010, L0 99992 (recovery close <= 99991.9 with high <= 100010; contradiction
high > 100010). Economics are computed separately for SHORT (never by reflection).
"""

from __future__ import annotations

from adviser3_fixtures import (  # noqa: F401  (re-exported for the tests)
    DAY1,
    DAY2,
    MIN,
    D,
    Stepper,
    T,
    a3,
    a3_base,
    delayed_events,
    flat,
    index_of,
    minute,
    mirror,
    walk,
)

REF = minute(100005, 100008, 99990, 99995)
H0, L0 = D(100008), D(99990)


def neutral(n: int = 1) -> list:
    return [minute(100000, 100005, 100000, 100000) for _ in range(n)]


def tape(*post, tail_price=100000, tail: int = 420) -> list:
    """a3 base + the reference minute [04:01,04:02) + ``post`` minutes from 04:02 + a neutral tail."""
    return a3([REF, *post], tail=tail, tail_price=tail_price)


# -- MP-004 §6 rows (LONG; SHORT = mirror) ------------------------------------------------------------------------------

VALID = minute(99995, 100012, 99992, 100012)          # close >= 100008.1, low >= 99990; 100012 <= 100014.5
EQUAL = minute(99995, D("100008.1"), 99990, D("100008.1"))  # contrary equality + exact favourable threshold
FAV_EQ = minute(99995, 100008, 99992, 100008)        # favourable equality only: no recovery
VIOLATE = minute(99995, 100007, D("99989.9"), 100005)  # low < L0: contradiction
VIOLATE_RECOVER = minute(99995, 100012, D("99989.9"), 100012)  # violation + favourable close in one bar
V_RECOVER = minute(99995, 100012, 99700, 100012)     # touches V 99700 (scenario invalidation) and closes favourable
ECON_LOW = minute(99995, 100030, 99992, 100030)      # corridor respected, reward/risk < 1.2 at 14 bps
OUTSIDE = minute(99995, 100060, 99992, 100060)       # close above the corridor top 100049.9


def valid() -> list:
    """ISSUE at 04:03 (the recovery [04:02,04:03) is the current bar), then neutral."""
    return tape(VALID)


def equality() -> list:
    return tape(EQUAL)


def favourable_equality_only() -> list:
    """No recovery and no contradiction until the original deadline 05:30 (child EXPIRED, no call)."""
    return tape(FAV_EQ)


def intermediate_violation_then_valid() -> list:
    return tape(VIOLATE, VALID)


def violation_and_recovery_same_bar() -> list:
    return tape(VIOLATE_RECOVER, VALID)


def v_and_recovery_same_bar() -> list:
    return tape(V_RECOVER)


def economics_insufficient() -> list:
    return tape(ECON_LOW)


def outside_corridor() -> list:
    return tape(OUTSIDE)


def deadline_at_recovery() -> list:
    """Neutral minutes until [05:29,05:30), a valid recovery completing exactly at the original deadline 05:30."""
    return tape(*neutral(87), VALID)


def gap_before_valid() -> list:
    """The trade minute [04:02,04:03) is MISSING, then [04:03,04:04) is a valid recovery: the confirmed scenario's
    monitoring has a required gap (existing protection) -> no issue through the hole."""
    gap = minute(100000, 100000, 100000, 100000)
    gap.gap = True
    return tape(gap, VALID)


def two_valid() -> list:
    """[04:02,04:03) valid recovery, [04:03,04:04) another valid recovery (used with a delayed receipt so both are
    admitted in one dispatch: the first is decisive but not current; no substitution by the second)."""
    return tape(VALID, minute(100012, 100013, 99995, 100010))


def recovery_then_violation() -> list:
    """[04:02,04:03) valid recovery then [04:03,04:04) a contradiction (both admitted in one dispatch under a delayed
    receipt: the dispatch's safety checks precede the recovery)."""
    return tape(VALID, VIOLATE)


def late_reference_then(*post) -> list:
    """Reference [04:01,04:02) received late (published 04:03); ``post`` from 04:02."""
    return tape(*post)


def blocked_first() -> list:
    """[04:01,04:02) closes 100080 above the corridor (a blocked return: it does not prepare), [04:02,04:03) is the
    first usable return (reference published 04:03), [04:03,04:04) a valid recovery (ISSUE 04:04)."""
    return a3([minute(100050, 100080, 100000, 100080), REF, VALID], tail_price=100000)


def cap_tape(*from_0459, pivot=100560) -> list:
    """The ``a3_cap_then_return`` geometry: a 15m pivot high 100560 in [04:15,04:30) becomes eligible at 05:00 (S15 650,
    z 65) and caps the target at floor(100560 - 65) = 100495. Prices stay above the corridor until the reference bar
    [04:44,04:45) (published 04:45, cap still 100700), then neutral until 04:59; ``from_0459`` minutes start at
    04:59. A recovery at [05:00,05:01) is decided against the NEW cap 100495 (no reset, no new attempt)."""
    post = walk(100050, 100150, 14) + walk(100150, pivot, 5) + walk(pivot, 100060, 10)  # [04:01,04:30)
    post += flat(14, 100060) + [REF] + neutral(14)                                          # [04:30,04:59)
    return a3(post + list(from_0459), tail_price=100000)


def new_cap_before_recovery() -> list:
    return cap_tape(*neutral(1), VALID)


def cap_contact_in_activation_bar() -> list:
    """The bar [04:59,05:00) ending at the cap activation is a valid recovery whose high 100500 reaches the new cap
    100495 (below T_confirm 100700): CAP_ACTIVATION_CONTACT_AMBIGUOUS precedes the local recovery."""
    return cap_tape(minute(100000, 100500, 99995, 100012))


def live_tape(*post) -> list:
    """Live variant. Live publications happen at the dispatch tick after the receipt (the receipt), so the bar right
    after each publication straddles it: (i) the 04:00 revision is published at its live dispatch after 04:00, hence one neutral minute
    [04:00,04:01) precedes the confirming minute [04:01,04:02) (close 100050; confirmation and WAIT at 04:02:01.5);
    (ii) [04:02,04:03) straddles the confirmation publication and is never sampled as a return (inherited rule; it
    stays above the corridor here); (iii) the reference minute [04:03,04:04) is published at 04:04:01.5, so
    ``post[0]`` = [04:04,04:05) straddles p0 and ``post[1]`` = [04:05,04:06) is the first bar wholly in the local
    domain (decided at 04:06:01.5)."""
    ms = a3_base()[:-1] + [minute(99950, 100000, 99950, 99980), minute(99980, 100050, 99980, 100050),
                           minute(100050, 100060, 100050, 100055), REF, *post]
    return ms + flat(420, 100000)


def cap_empties_economic_region(*from_0500) -> list:
    """As ``cap_tape`` with the 15m pivot high 100365: at 05:00 the cap revises to floor(100365 - 65) = 100300 (> the
    last close 100000, corridor still [99900, 100049.9]) and the fixed-K economic upper bound becomes
    (100300 + 1.2*99700)/(2.2*1.0014) = 99834.4 < 99900: the historical economic region is EMPTY (MP-004 keeps the
    inherited terminal before any local response). ``from_0500`` minutes start at 05:00."""
    return cap_tape(*neutral(1), *from_0500, pivot=100365)
