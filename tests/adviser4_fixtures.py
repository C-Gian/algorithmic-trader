"""Hand-designed synthetic paths for the MP-003 v0.4 fixtures (engineering inputs, NOT market data).

They extend the MP-002 base A LONG path of ``adviser3_fixtures`` (tick 0.1): impulse A 97000, B 100900, birth S15
2000, z 200 -> A+z 97200, B+z 101100, B-0.25*S15 100400; birth published 03:30 (original setup deadline 05:30).

``arm_base()`` ends with the reaction bar [03:30,03:45) o 100700 h 100700 l 100000 c 100049.9 -> first ARM published
at 03:45: R 100000, K 100700, V 99800 (anchor epoch 1). Each variant below states its hand-expected transitions; the
MP-003 §6 row it covers is named in the test. SHORT fixtures are the positive-price reflection ``mirror`` about 100000
(x -> 200000 - x), whose structural levels reflect exactly (economics are never asserted by reflection).
"""

from __future__ import annotations

from adviser3_fixtures import (  # noqa: F401  (re-exported for the tests)
    DAY1,
    DAY2,
    LOW,
    MIN,
    D,
    T,
    bar15,
    delayed_events,
    flat,
    index_of,
    minute,
    mirror,
    oscillation,
    walk,
)

A_, B_, Z = D(97000), D(100900), D(200)
R1, K1, V1 = D(100000), D(100700), D(99800)


def birth_base() -> list:
    """Up to the A birth published at 03:30 (the impulse bar [03:15,03:30) has high B 100900, close 100700)."""
    ms = oscillation(26 * 4)
    x = LOW
    for _ in range(5):
        ms += bar15(x, x + 650, x, x + 650, order="LH")
        x += 650
    ms += bar15(x, B_, x, D(100700), order="LH")
    return ms


def arm_base() -> list:
    """... + the reaction bar [03:30,03:45): first ARM published at 03:45 (R 100000, K 100700, V 99800)."""
    return birth_base() + bar15(D(100700), D(100700), R1, D("100049.9"))


def tail(ms: list, n: int = 420) -> list:
    return ms + flat(n, ms[-1].c)


# -- MP-003 §6 rows 4-6: local contact, prospective replacement, fresh confirmation -----------------------------------

def contact_then_rearm() -> list:
    """Bar [03:45,04:00): drift to 99900, minute [03:50,03:51) low 99790 <= V 99800 (contact, ANCHOR_LOST at 03:51), a
    recovery to 100300 (the bar high) and close 99950. At 04:00 the complete bar is a strictly deeper clean reaction
    (99790 < lost R 100000, > A+z 97200): REARM epoch 2, R 99790, K 100300, V 99590, published 04:00. The minutes
    [04:00,04:10) climb to 100350; the first close >= 100300.1 with low > 99590 confirms at its own publication."""
    post = walk(D("100049.9"), 99900, 5) + [minute(99900, 99900, 99790, 99850)] + walk(99850, 100300, 4)
    post += walk(100300, 99950, 5) + walk(99950, 100350, 10)
    return tail(arm_base() + post)


def contact_at_equality() -> list:
    """Minute [03:50,03:51) low exactly V 99800: inclusive equality is contact (ANCHOR_LOST)."""
    post = walk(D("100049.9"), 99900, 5) + [minute(99900, 99900, 99800, 99850)] + walk(99850, 99950, 9)
    return tail(arm_base() + post)


def replacement_tie() -> list:
    """Replacement equality boundary: contact on a wick to 97150 (<= A+z: the contact bar is no clean reaction), then
    bar [04:00,04:15) has low exactly the lost R 100000 (a tie is NOT strictly deeper: no REARM) and bar [04:15,04:30)
    has low 99999.9: REARM epoch 2 at 04:30 (R 99999.9, K = that bar's high 100400, V 99799.9)."""
    post = walk(D("100049.9"), 100100, 5) + [minute(100100, 100100, 97150, 100100)] + walk(100100, 100500, 9)
    post += walk(100500, 100000, 5) + walk(100000, 100300, 10)
    post += walk(100300, D("99999.9"), 5) + walk(D("99999.9"), 100400, 5) + walk(100400, 100200, 5)
    return tail(arm_base() + post)


def supersede_tie() -> list:
    """No contact: bar [03:45,04:00) has low exactly R 100000 (> V 99800) and high 100500: the inherited inclusive
    lower-clean-R revision supersedes epoch 1 with epoch 2 (R 100000, K 100500, V 99800) at 04:00 (REVISE)."""
    post = walk(D("100049.9"), 100000, 5) + walk(100000, 100500, 5) + walk(100500, 100100, 5)
    return tail(arm_base() + post)


def contact_same_bar_backlog() -> list:
    """Row 6 / backlog: contact minute [03:58,03:59) low 99790, close 99950 at 04:00 after an earlier high 100600
    ([03:47,03:48) closes 100600); the complete bar [03:45,04:00) gives K 100600. Minutes [04:00,04:03) close 100700
    (>= K+tick) - used with a delayed receipt of the minute [03:59,04:00) so the contact, the seal and those minutes
    are admitted in ONE dispatch: none of them may confirm the anchor published at that dispatch."""
    post = walk(D("100049.9"), 100600, 2) + walk(100600, 100300, 11)
    post += [minute(100300, 100300, 99790, 99900), minute(99900, 99950, 99900, 99950)]
    post += [minute(99950, 100700, 99950, 100700), minute(100700, 100710, 100690, 100700),
             minute(100700, 100710, 100690, 100705)]
    return tail(arm_base() + post)


# -- rows 7 and 11: structural close predicate versus a 1m wick; no eligible reaction ---------------------------------

def wick_through_a_plus_z_then_rebound() -> list:
    """Row 11 (and row 7's negative half): minute [03:50,03:51) wicks to 97150 (<= V and <= A+z 97200, contact) but
    every 15m close stays above A+z, so there is no withdrawal; the contact bar's low 97150 is NOT a clean reaction
    (R must be > A+z) and later bars stay above the lost R 100000 with repeated minute recoveries above the old K
    100700 (never above B 100900): the same owner stays WATCH (no replacement, no confirmation, no call) until the
    original deadline 05:30 -> EXPIRED ORIGINAL_SETUP_DEADLINE."""
    post = walk(D("100049.9"), 100100, 5) + [minute(100100, 100100, 97150, 100100)] + walk(100100, 100500, 9)
    post += walk(100500, 100800, 15) + walk(100800, 100200, 15)
    for _ in range(4):
        post += walk(100200, 100850, 15) + walk(100850, 100200, 15)
    return tail(arm_base() + post)


def close_at_a_plus_z() -> list:
    """Row 7: contact (low 99700 at [03:50,03:51)) and then the complete bar [03:45,04:00) CLOSES 97200 <= A+z:
    WITHDRAWN CLOSE_AT_OR_BEYOND_A_PLUS_ZONE at 04:00 (no replacement), even though later minutes rebound above any
    K."""
    post = walk(D("100049.9"), 99900, 5) + [minute(99900, 99900, 99700, 99800)] + walk(99800, 97200, 9)
    post += walk(97200, 100800, 20)
    return tail(arm_base() + post)


# -- rows 1-3: destination monitoring origin ---------------------------------------------------------------------------

def never_armed(high_first=D(100950), high_eq=D(101100), high_spend=D("101100.1")) -> list:
    """Row 1: no reaction (closes never lower than 100700 before the bars below, lows above 100400). Bar [03:30,03:45)
    reaches 100950 (>= B, <= B+z): no terminal; bar [03:45,04:00) reaches exactly B+z 101100: no spend; bar
    [04:00,04:15) reaches 101100.1 > B+z: SPENT_HIGH_BEYOND_B_BEFORE_REACTION at 04:15."""
    post = bar15(D(100700), high_first, D(100650), D(100800), order="HL")
    post += bar15(D(100800), high_eq, D(100750), D(100900), order="HL")
    post += bar15(D(100900), high_spend, D(100850), D(101000), order="HL")
    return tail(birth_base() + post)


def arm_source_touches_b() -> list:
    """Row 2: the reaction bar [03:30,03:45) touches B (high 100950 <= B+z) then reacts to 100000 and closes 100049.9:
    first ARM at 03:45 with K 100950 - no retroactive destination terminal from its own minutes. Minutes after 03:45
    stay in [99900, 100800] until [03:50,03:51) whose high is exactly B 100900: DESTINATION_REACHED at 03:51."""
    pre = birth_base() + bar15(D(100700), D(100950), R1, D("100049.9"), order="HL")
    post = walk(D("100049.9"), 100800, 5) + [minute(100800, B_, 100800, 100850)] + walk(100850, 100600, 9)
    return tail(pre + post)


def arm_then_lost_then_b() -> list:
    """Row 3: contact as in ``wick_through_a_plus_z_then_rebound`` (no clean replacement possible from the contact bar),
    then a later minute [04:20,04:21) reaches B 100900 while the scenario is WATCH (ever armed): DESTINATION_REACHED
    from the original first-arm origin; no pre-first-arm spend applies (a 15m high beyond B+z alone is not tested)."""
    post = walk(D("100049.9"), 100100, 5) + [minute(100100, 100100, 97150, 100100)] + walk(100100, 100500, 9)
    post += walk(100500, 100800, 20) + [minute(100800, 101200, 100800, 100850)] + walk(100850, 100500, 9)
    return tail(arm_base() + post)


def local_and_destination_same_minute() -> list:
    """Row 12: one minute [03:50,03:51) has low 99790 <= V and high 100900 >= B: scenario UNASSESSABLE
    DESTINATION_AND_LOCAL_ANCHOR_CONTACT_SAME_INTERVAL (no replacement, no certified success)."""
    post = walk(D("100049.9"), 100100, 5) + [minute(100100, B_, 99790, 100100)] + walk(100100, 100000, 9)
    return tail(arm_base() + post)


def monitoring_gap_after_loss() -> list:
    """Row 12: contact at 03:50 (WATCH, ever armed), then the trade minute [03:55,03:56) is MISSING: the ever-armed
    scenario's destination monitoring has a required gap -> UNASSESSABLE REQUIRED_MONITORING_GAP (no replacement)."""
    post = walk(D("100049.9"), 100100, 5) + [minute(100100, 100100, 97150, 100100)] + walk(100100, 100500, 4)
    gap = minute(100500, 100500, 100500, 100500)
    gap.gap = True
    post += [gap] + walk(100500, 100300, 4)
    return tail(arm_base() + post)


# -- row 8: original deadline first ------------------------------------------------------------------------------------

def deadline_with_candidate_replacement() -> list:
    """Row 8: contact on the wick (no clean replacement), rebound above the lost R; the bar [05:15,05:30) - which would
    otherwise be a strictly deeper clean reaction (low 99500 < lost R, close 99800) - completes exactly at the
    original deadline 05:30: EXPIRED first, no REARM."""
    post = walk(D("100049.9"), 100100, 5) + [minute(100100, 100100, 97150, 100100)] + walk(100100, 100500, 9)
    post += walk(100500, 100600, 75)                                       # 04:00-05:15 above the lost R
    post += walk(100600, 99500, 10) + walk(99500, 99800, 5)                 # [05:15,05:30): low 99500
    return tail(arm_base() + post)


# -- rows 9-10: no post-confirmation re-anchor --------------------------------------------------------------------------

def a3_wait_v_contact_then_rebound() -> list:
    """Row 9: the MP-002 base confirmation at 04:01 -> WAIT_PRICE (V 99700, corridor [99900, 100049.9]); the minute
    [04:01,04:02) touches 99700 and closes 99950; then a rebound to 100500. Confirmed scenario INVALIDATED, child
    terminal; no re-anchor, reconfirmation or RETURN issue."""
    import adviser3_fixtures as f3

    post = [minute(100050, 100050, 99700, 99950)] + walk(99950, 100500, 30)
    return f3.a3(post)


def a3_issued_then_v_contact() -> list:
    """Row 10: the MP-002 RETURN issue at 04:02 (a3_return_long first two minutes), then [04:03,04:04) touches V 99700:
    the issued call's existing protective contact (INVALIDATED) and the confirmed scenario terminal; no widening or
    replacement geometry."""
    import adviser3_fixtures as f3

    post = [minute(100050, 100050, 99990, 100000), minute(100000, 100010, 100000, 100010),
            minute(100010, 100010, 99690, 99800)] + walk(99800, 100300, 20)
    return f3.a3(post)
