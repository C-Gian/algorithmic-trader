"""WP-009 correction, finding 1 (pure): an ordinary protected minute that opens at/beyond V fills at the adverse open
(known model opening boundary) for LONG and SHORT, not at V over the minute; equality is inclusive; funding ownership
follows the open boundary; both-level minutes whose open is inside stay AMBIGUOUS; HORIZON_ONLY keeps no protection."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from test_adviser_evaluator import MIN, P0, T0, bar, call_entry, feed, make, paths

from algotrader.adviser.evaluator import Evaluator, _iso
from algotrader.adviser.params import load

D = Decimal


def _entered(d=1, funding_mode="PRICE_NET_ONLY"):
    ev = Evaluator(load(), D("0.1"), eval_start=T0 - timedelta(hours=1), eval_end=T0 + timedelta(hours=10),
                   funding_mode=funding_mode, sample_views=False)
    v, t = (P0 - 50, P0 + 400) if d > 0 else (P0 + 50, P0 - 400)
    ev.on_journal([call_entry(d=d, v=v, t=t)])
    feed(ev, [bar(T0, P0, P0, P0, P0), bar(T0 + MIN, P0, P0, P0, P0)])  # primary enters at the 10:01 open P0
    assert ev.calls["call-1"]["paths"]["PRIMARY"].status == "OPEN"
    return ev


def test_ordinary_long_stop_gap_fills_at_the_adverse_open_boundary():
    ev = _entered()
    feed(ev, [bar(T0 + 2 * MIN, P0 - 100, P0 - 60, P0 - 120, P0 - 90)])  # Director counterexample
    p = paths(ev)["PRIMARY"]
    assert p["exit"]["price"] == str(P0 - 100) and p["exit"]["reason"] == "STOP_GAP_ADVERSE_OPEN"
    assert p["exit_class"] == "STOP_GAP" and p["exit"]["time_start"] == p["exit"]["time_end"]
    assert p["exit"]["time_start"].endswith("10:02:00Z")
    for v in ("ENTRY_DELAY_0", "ENTRY_DELAY_120"):  # every guidance variant that is open uses the same rule
        q = paths(ev).get(v)
        if q is not None and q["exit"] is not None:
            assert q["exit"]["reason"] == "STOP_GAP_ADVERSE_OPEN"


def test_ordinary_short_stop_gap_is_the_exact_reflection():
    ev = _entered(d=-1)
    feed(ev, [bar(T0 + 2 * MIN, P0 + 100, P0 + 120, P0 + 60, P0 + 90)])
    p = paths(ev)["PRIMARY"]
    assert p["direction"] == "SHORT" and p["exit"]["price"] == str(P0 + 100)
    assert p["exit"]["reason"] == "STOP_GAP_ADVERSE_OPEN" and p["exit"]["time_start"] == p["exit"]["time_end"]
    assert D(p["gross"]) == -(D(P0 + 100) / P0 - 1)


def test_open_exactly_at_v_is_inclusive_and_beats_a_later_target_print():
    ev = _entered()
    feed(ev, [bar(T0 + 2 * MIN, P0 - 50, P0 + 401, P0 - 50, P0)])  # opens at V, later trades through T
    p = paths(ev)["PRIMARY"]
    assert p["status"] == "CLOSED" and p["exit"]["price"] == str(P0 - 50)
    assert p["exit"]["reason"] == "STOP_GAP_ADVERSE_OPEN"


def test_both_levels_with_an_inside_open_remain_ambiguous_never_target_first():
    ev = _entered()
    feed(ev, [bar(T0 + 2 * MIN, P0 - 49, P0 + 401, P0 - 51, P0)])
    assert paths(ev)["PRIMARY"]["status"] == "AMBIGUOUS"


def test_horizon_only_keeps_its_declared_no_protection_scope():
    ev = _entered()
    feed(ev, [bar(T0 + 2 * MIN, P0 - 100, P0 - 60, P0 - 120, P0 - 90)])
    assert "HORIZON_ONLY" not in paths(ev)
    assert ev.calls["call-1"]["paths"]["HORIZON_ONLY"].status == "OPEN"


def _with_settlement(u):
    ev = _entered(funding_mode="AUTHORITATIVE_IF_COVERED")
    ev.funding = [{"event_time": u.isoformat(), "rate": "0.001", "event_id": "f"}]
    ev.mark_closes[_iso(u)] = str(P0)
    return ev


def test_gap_fill_funding_ownership_uses_the_open_boundary_not_the_minute_interval():
    # settlement strictly inside the gap minute: the open-boundary exit precedes it (was ambiguous for STOP_TOUCH)
    ev = _with_settlement(T0 + 2 * MIN + timedelta(seconds=30))
    feed(ev, [bar(T0 + 2 * MIN, P0 - 100, P0 - 60, P0 - 120, P0 - 90)])
    p = paths(ev)["PRIMARY"]
    assert p["funding_status"] == "AUTHORITATIVE_COVERED" and D(p["funding"]) == 0
    # settlement exactly at the gap open: held before u, exit exactly at u pays/receives
    ev = _with_settlement(T0 + 2 * MIN)
    feed(ev, [bar(T0 + 2 * MIN, P0 - 100, P0 - 60, P0 - 120, P0 - 90)])
    p = paths(ev)["PRIMARY"]
    assert p["funding_status"] == "AUTHORITATIVE_COVERED" and D(p["funding"]) == D("-0.001")


def test_pending_exit_gap_and_ordinary_gap_agree():
    ev = make()
    ev.on_journal([call_entry()])
    feed(ev, [bar(T0, P0, P0, P0, P0), bar(T0 + MIN, P0, P0, P0, P0)])
    from test_adviser_evaluator import rev
    ev.on_journal([rev(T0 + timedelta(minutes=1, seconds=30), thesis="RETIRED", enabled=False,
                       reason="THESIS_FAILED")])  # pending exit at the 10:03 open
    feed(ev, [bar(T0 + 2 * MIN, P0 - 80, P0 - 70, P0 - 90, P0 - 75)])  # ordinary gap before the pending boundary
    p = paths(ev)["PRIMARY"]
    assert p["exit"]["reason"] == "STOP_GAP_ADVERSE_OPEN" and p["exit"]["time_start"].endswith("10:02:00Z")
