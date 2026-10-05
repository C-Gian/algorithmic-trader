"""WP-009 correction, findings 2-3 (pure). Freshness needs BOTH ages <= allowance, so the first stale instant of a
recently received old bar is event_end + allowance + 1 us (not receipt + allowance); residual time holds while
remaining >= minimum and the first too-late instant is scheduled without any new input. C's pre-trigger withdrawal on a
15m close beyond L-z is applied to every NEWLY admitted close exactly once, whatever its receipt delay."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from adviser_rig import Rig, rec
from test_adviser_evaluator import P0, bar, call_entry, feed, make, rev
from test_adviser_rules import MIN, T, _ongoing_call, balanced_h1, prime

from algotrader.adviser.core import EPS, Attempt, Box
from algotrader.adviser.runtime import AdviserRuntime
from algotrader.feed.ordering import canonical

D = Decimal
SEC = timedelta(seconds=1)
OSC = [P0 + (10 if i % 2 else -10) for i in range(30)]


# -- finding 2: both-age freshness ----------------------------------------------------------------------------------

def _late_receipt():
    r = Rig()
    prime(r, T, OSC, balanced_h1(T))
    c = r.core
    c.last_1m = replace(c.last_1m, known_at=T + 60 * SEC)  # minute ended 12:00, received 12:01
    c.clock = T + 60 * SEC
    c.call = _ongoing_call(c.clock, issued=c.clock)
    c._touch()
    return r, c


def test_recently_received_old_bar_is_stale_at_event_end_plus_allowance_without_new_input():
    r, c = _late_receipt()
    assert c.next_deadline() == T + 120 * SEC + EPS  # Director counterexample: was 12:03:00.000001
    assert c.ready_1m(T + 120 * SEC) and not c.ready_1m(T + 120 * SEC + EPS)  # equality still fresh
    rt = AdviserRuntime(c)
    rt.advance(T + 121 * SEC)
    assert c.clock == T + 120 * SEC + EPS
    assert c.call is None and c.recent_calls[-1]["terminal"] == "UNASSESSABLE"


def test_freshness_equality_keeps_the_thesis_until_the_first_failing_microsecond():
    r, c = _late_receipt()
    rt = AdviserRuntime(c)
    rt.advance(T + 120 * SEC)  # exactly at the allowance: nothing due, thesis continues
    assert c.call is not None and c.call.thesis == "ONGOING" and c.clock == T + 60 * SEC


def test_restored_core_schedules_the_same_first_failing_boundary():
    r, c = _late_receipt()
    rt = AdviserRuntime(c)
    doc = json.loads(canonical(rt.encode()))
    rt2 = AdviserRuntime.decode(doc, r.cfg, None)
    assert rt2.core.next_deadline() == c.next_deadline() == T + 120 * SEC + EPS
    rt.advance(T + 121 * SEC)
    rt2.advance(T + 121 * SEC)
    j1, j2 = rt.take()[0], rt2.take()[0]
    assert [e["digest"] for e in j1] == [e["digest"] for e in j2] and j1
    assert canonical(rt.encode()) == canonical(rt2.encode())


# -- finding 2: residual closure without new input -----------------------------------------------------------------

def _residual():
    r = Rig()
    prime(r, T, OSC, balanced_h1(T))
    c = r.core
    c.call = _ongoing_call(T, issued=T - timedelta(hours=3, minutes=30), hard=T + timedelta(minutes=30))
    c.call.progress_done = True
    c.last_1m = replace(c.last_1m, c=P0)
    c._reassess_call(T)
    c._touch()
    return r, c


def test_residual_equality_keeps_entry_and_the_first_too_late_instant_closes_it_without_input():
    r, c = _residual()
    assert c.call.entry == "AVAILABLE"  # remaining == 30 m == minimum: still allowed
    assert c.next_deadline() == T + EPS
    rt = AdviserRuntime(c)
    before = c.counters["dispatches"]
    rt.advance(T + EPS)
    assert c.call.entry == "CLOSED" and "TOO_LATE" in c.call.entry_reasons and c.call.thesis == "ONGOING"
    assert c.counters["dispatches"] == before + 1  # exactly one timer dispatch, no fabricated data
    assert rt.advance(T + EPS) == 0  # draining again dispatches nothing


def test_residual_disable_is_published_before_the_next_opening_boundary():
    """Evaluator pre-open eligibility: a residual closure published at hard - 30 m + 1 us disables the next boundary;
    the boundary exactly at hard - 30 m (equality) remains eligible."""
    issued = T - timedelta(hours=3, minutes=31)
    hard = issued + timedelta(hours=4)
    off = hard - timedelta(minutes=30) + EPS

    def run(entry_start):
        ev = make(es=issued - timedelta(hours=1), ee=issued + timedelta(hours=10))
        ev.on_journal([call_entry(issued=issued)])
        t = issued.replace(second=0) + MIN
        while t < entry_start:  # opens outside the structural area until the chosen boundary
            feed(ev, [bar(t, P0 + 30, P0 + 30, P0 + 30, P0 + 30)])
            t += MIN
        ev.on_journal([rev(off, enabled=False, n=1)])
        feed(ev, [bar(t, P0, P0, P0, P0)])
        return ev.calls.get("call-1")

    on_equality = run(hard - timedelta(minutes=30))
    assert on_equality["paths"]["PRIMARY"].status == "OPEN"
    after = run(hard - timedelta(minutes=29))
    ps = after["paths"]["PRIMARY"]
    assert ps.status == "WAIT_ENTRY" and ps.attempts == ps.rejected  # the disabled boundary is not even tried


# -- finding 3: C withdrawal on newly admitted closes --------------------------------------------------------------

def _c_rig(d=1):
    r = Rig()
    prime(r, T - timedelta(minutes=15), OSC, balanced_h1(T - timedelta(minutes=15)))
    c = r.core
    if d > 0:
        bx = Box("box-c", P0 + 5, P0 + 2005, P0 + 1005, D(30), D(3), T - timedelta(hours=1), 1, T + timedelta(hours=3),
                 ["s"])
        k_t, v_t = P0 + 100, P0 - 500
    else:  # exact reflection: L' = -(P0-5), far edge P0-2
        bx = Box("box-c", P0 - 2005, P0 - 5, P0 - 1005, D(30), D(3), T - timedelta(hours=1), 1,
                 T + timedelta(hours=3), ["s"])
        k_t, v_t = -(P0 - 100), -(P0 + 500)
    bx.used["C+" if d > 0 else "C-"] = True
    c.box = bx
    at = Attempt(aid="CX-probe", family="C", d=d, owner=bx.bid, born_at=T - timedelta(minutes=15), born_seq=1,
                 sources=["s"], deadline=T + timedelta(minutes=45), s15=D(30), z=D(3), status="ARMED", k_t=k_t,
                 v_t=v_t, arm_at=T - timedelta(minutes=15), arm_seq=2)
    c.attempts[at.aid] = at
    return r, c, at


def _below(d):  # a 15m close strictly beyond the far edge (L-z), for direction d
    return (P0 + 1, P0 + 2, P0, P0 + 1) if d > 0 else (P0 - 1, P0, P0 - 2, P0 - 1)


def _withdrawn(r, aid):
    return [x for x in r.candidates(aid) if x["transition"] == "WITHDRAW"]




@pytest.mark.parametrize("d", [1, -1])
@pytest.mark.parametrize("delay", [timedelta(0), SEC, timedelta(minutes=7)])
def test_c_close_beyond_far_edge_withdraws_whatever_the_receipt_delay(d, delay):
    r, c, at = _c_rig(d)
    o, h, lo, cl = _below(d)
    r._bar(T - MIN, o, h, lo, cl)
    c.admit_sealed(rec("15m", T - timedelta(minutes=15), o, h, lo, cl))
    r.dispatch(T + delay)
    assert at.aid not in c.attempts
    w = _withdrawn(r, at.aid)
    assert len(w) == 1 and w[0]["reason"] == "CLOSE_BEYOND_LOWER_FAR_EDGE_BEFORE_TRIGGER"
    assert c.context(c.clock) == "BALANCED"  # neither context loss nor adverse expansion masks the rule


def test_c_close_at_the_far_edge_does_not_withdraw():
    r, c, at = _c_rig(1)
    r._bar(T - MIN, P0 + 2, P0 + 3, P0 + 1, P0 + 2)  # close == L - z: not strictly beyond
    c.admit_sealed(rec("15m", T - timedelta(minutes=15), P0 + 2, P0 + 3, P0 + 1, P0 + 2))
    r.dispatch(T + SEC)
    assert at.aid in c.attempts


def test_c_withdrawal_precedes_a_coincident_trigger_in_the_same_delayed_dispatch():
    r, c, at = _c_rig(1)
    r._bar(T - MIN, P0 + 1, P0 + 2, P0, P0 + 1)
    c.admit_sealed(rec("15m", T - timedelta(minutes=15), P0 + 1, P0 + 2, P0, P0 + 1))
    r._bar(T, P0 + 50, P0 + 120, P0 + 40, P0 + 110)  # would satisfy C's trigger (close >= K+tick, low > V)
    r.dispatch(T + MIN + SEC)
    assert at.aid not in c.attempts and c.call is None
    assert [x["transition"] for x in r.candidates(at.aid)] == ["WITHDRAW"]


def test_an_old_close_already_in_the_window_is_never_reapplied():
    r, c, at = _c_rig(1)
    del c.attempts[at.aid]
    r._bar(T - MIN, P0 + 1, P0 + 2, P0, P0 + 1)
    c.admit_sealed(rec("15m", T - timedelta(minutes=15), P0 + 1, P0 + 2, P0, P0 + 1))
    r.dispatch(T + SEC)  # the close is admitted while no C attempt exists
    c.attempts[at.aid] = at  # a later C attempt (fixture) for the same box
    r._bar(T, P0 + 10, P0 + 12, P0 + 8, P0 + 10)
    r.dispatch(T + MIN + SEC)  # no new 15m close: the old one must not withdraw it
    assert at.aid in c.attempts


def test_c_withdrawal_after_restore_matches_the_uninterrupted_fold():
    """Restore between the arm and the late close: the restored fold withdraws exactly like the uninterrupted one."""
    def close_and_dispatch(r, c):
        r._bar(T - MIN, P0 + 1, P0 + 2, P0, P0 + 1)
        c.admit_sealed(rec("15m", T - timedelta(minutes=15), P0 + 1, P0 + 2, P0, P0 + 1))
        return [e["digest"] for e in r.dispatch(T + timedelta(minutes=3))]

    r1, c1, at = _c_rig(1)
    straight = close_and_dispatch(r1, c1)
    r2, c2, _ = _c_rig(1)
    doc = json.loads(canonical(AdviserRuntime(c2).encode()))
    r2.core = AdviserRuntime.decode(doc, r2.cfg, None).core
    restored = close_and_dispatch(r2, r2.core)
    assert restored == straight and at.aid not in r2.core.attempts and at.aid not in c1.attempts
