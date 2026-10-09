"""Hand-designed synthetic paths for the MP-005 v0.6 fixtures (engineering inputs, NOT market data).

Two layers, as for MP-004:

1. **Literal MP-005 §8/§9 rows** (``SEC8``/``SEC9``): the specification's own abstract prices, ticks and costs, checked
   directly through the pinned functions (``geometry.admissible_bounds``/``predicate``, ``core5.local_verdict``,
   ``core6.initial_compatibility`` and the live cost formula of ``AdviserCore._side_price``).
2. **Reachable engine tapes** on the MP-002 base A LONG path of ``adviser5_fixtures`` (tick 0.1, historical K 14 bps,
   r 1.2): A confirmation published 04:01, WAIT_PRICE corridor C0 = [99900, 100049.9], V 99700, T_confirm 100700,
   fixed-K economic region A0 = [99900, 100014.5], original setup deadline 05:30. The first usable return is the
   minute [04:01,04:02) (close 99995 inside A0), so the reference is prepared and published at 04:02 with L0 99990;
   only H0 varies:

   * ``REF_ECON``  H0 100014.5 -> F >= 100014.6: F ∩ C0 = [100014.6, 100049.9] but F ∩ A0 = ∅ -> HISTORICAL_ECONOMICS
     (MP-005 §8 H1 analogue);
   * ``REF_COR``   H0 100049.9 -> F >= 100050.0 > the corridor top: F ∩ C0 = ∅ -> CORRIDOR, the economic
     incompatibility annotated (H2 analogue);
   * ``REF_ONE``   H0 100014.4 -> F >= 100014.5: J0 = {100014.5}, one tick, non-empty (H3 analogue); the recovery
     ``ONE_EDGE`` closes exactly at 100014.5 with low = L0 (contrary equality) and is issued at the economic edge.

   SHORT = the positive-price reflection x -> 200000 - x (C0 [99950.1, 100100], A0 [99985.5, 100100] computed
   separately, never by reflection: it equals 200000 - 100014.5 here by arithmetic).
"""

from __future__ import annotations

from adviser5_fixtures import (  # noqa: F401  (re-exported for the tests)
    DAY1,
    DAY2,
    MIN,
    REF,
    VALID,
    D,
    T,
    a3,
    a3_base,
    delayed_events,
    flat,
    index_of,
    minute,
    mirror,
    neutral,
)

L0 = D(99990)
REF_ECON = minute(100005, D("100014.5"), 99990, 99995)
REF_COR = minute(100005, D("100049.9"), 99990, 99995)
REF_ONE = minute(100005, D("100014.4"), 99990, 99995)
ONE_EDGE = minute(99995, D("100014.5"), 99990, D("100014.5"))   # close = H0 + tick = A0 top, low = L0
ECON_RECOVERY = minute(99995, D("100014.6"), 99990, D("100014.6"))  # satisfies the local predicate of REF_ECON
COR_RECOVERY = minute(99995, D("100050"), 99990, D("100050"))      # satisfies the local predicate of REF_COR
CONTRADICT = minute(99995, 100005, D("99989.9"), 100000)            # low < L0 (H5 B1 analogue)


def h1_economics() -> list:
    """REF_ECON prepares at 04:02 and ends INITIAL_RESPONSE_INCOMPATIBLE:HISTORICAL_ECONOMICS in that dispatch; the
    next bar [04:02,04:03) satisfies the local recovery predicate arithmetically and produces nothing."""
    return a3([REF_ECON, ECON_RECOVERY], tail_price=100000)


def h2_corridor() -> list:
    return a3([REF_COR, COR_RECOVERY], tail_price=100000)


def h3_single_tick() -> list:
    """REF_ONE: J0 = {100014.5}; WAIT_RESPONSE at 04:02; ONE_EDGE at [04:02,04:03) -> ISSUE 04:03."""
    return a3([REF_ONE, ONE_EDGE], tail_price=100000)


def h4_deadline_collision() -> list:
    """Prices stay above the corridor until [05:29,05:30), which is REF_ECON published exactly at the original setup
    deadline 05:30: the inherited deadline ends the child first (ORIGINAL_SETUP_DEADLINE, no reference); the next bar
    [05:30,05:31) is the H1 recovery bar (no late preparation, no reopening)."""
    return a3(flat(88, 100070) + [REF_ECON, ECON_RECOVERY], tail_price=100000)


def h5_persistence() -> list:
    """H1, then B1 [04:02,04:03) breaks the contrary extreme and B2 [04:03,04:04) closes beyond the favourable
    threshold: neither is a C or an R of the already ended child (restore cut between 04:02 and B1's admission)."""
    return a3([REF_ECON, CONTRADICT, ECON_RECOVERY], tail_price=100000)


def compatible_then(*post) -> list:
    """The MP-004 REF (H0 100008 < A0 top): compatible, so v0.6 behaves exactly as v0.5."""
    return a3([REF, *post], tail_price=100000)


# -- live (``adviser5_fixtures.live_tape`` with a chosen reference bar) ---------------------------------------------------

def live_tape6(ref, *post) -> list:
    """As ``adviser5_fixtures.live_tape`` (confirmation and WAIT at 04:02:01.5; the reference minute [04:03,04:04) is
    published at 04:04:01.5; ``post[0]`` = [04:04,04:05) straddles p0; ``post[1]`` = [04:05,04:06) is the first bar
    wholly in the local domain) with ``ref`` as the reference minute."""
    ms = a3_base()[:-1] + [minute(99950, 100000, 99950, 99980), minute(99980, 100050, 99980, 100050),
                           minute(100050, 100060, 100050, 100055), ref, *post]
    return ms + flat(420, 100000)


# -- literal MP-005 §8 / §9 rows (abstract prices; never market data) --------------------------------------------------

SEC8 = {  # tick 1, K 14, r 1.2; LONG/SHORT geometry: (R, K trigger, V, T/cap, corridor, economic region)
    "geometry": {"L": (95, 110, 90, 120, (95, 110), (95, 103)), "S": (105, 90, 110, 80, (90, 105), (97, 105))},
    # row: {side: (B0 o/h/l/c, B1 o/h/l/c or None, expected base or None)}
    "H1": {"L": ((100, 103, 99, 100), (100, 104, 99, 104), "HISTORICAL_ECONOMICS"),
           "S": ((100, 101, 97, 100), (100, 101, 96, 96), "HISTORICAL_ECONOMICS")},
    "H2": {"L": ((100, 110, 99, 100), (100, 111, 99, 111), "CORRIDOR"),
           "S": ((100, 101, 90, 100), (100, 101, 89, 89), "CORRIDOR")},
    "H3": {"L": ((100, 102, 99, 100), (100, 103, 99, 103), None),
           "S": ((100, 101, 98, 100), (100, 101, 97, 97), None)},
    "H5": {"L": ((100, 103, 99, 100), (100, 101, 98, 100), (100, 104, 99, 104)),
           "S": ((100, 101, 97, 100), (100, 102, 99, 100), (100, 101, 96, 96))},
}
SEC9 = {  # tick 0.01, fee 5/side, slippage 2/side, half-spread; r 1.2
    "geometry": {"L": ("100.00", "100.20", "99.80", "100.70", ("100.00", "100.20")),
                 "S": ("100.00", "99.80", "100.20", "99.30", ("99.80", "100.00"))},
    "B0": ("100.00", "100.01", "99.99", "100.00"), "B1": ("100.00", "100.01", "99.99", "100.00"),
    "B2": {"L": ("100.00", "100.04", "100.00", "100.03"), "S": ("100.00", "100.00", "99.96", "99.97")},
    "quotes": {"L1": ("99.99", "100.01"), "L2": ("99.80", "100.20"),
               "L3": {"L": ("100.02", "100.04"), "S": ("99.96", "99.98")}},
}
