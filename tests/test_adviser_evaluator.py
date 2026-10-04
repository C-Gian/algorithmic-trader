"""WP-009 evaluator matrix (pure; MP-001 §11 / disposition B7): pre-open frontier versus the bar's later HLC,
opening-price geometry, collision table (single contact, both levels, pending-exit gaps, guidance during a protective
minute), censoring at the first missing minute, tail/data end, entry-delay alignment and the warmup/evaluation window.
Inputs are journal-shaped call/revision records and complete minutes; nothing here reads the reasoning core."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from algotrader.adviser.evaluator import Evaluator
from algotrader.adviser.measures import Bar
from algotrader.adviser.params import load

D = Decimal
MIN = timedelta(minutes=1)
T0 = datetime(2025, 9, 1, 10, 0, tzinfo=UTC)
P0 = D(100000)


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def call_entry(issued=T0, d=1, v=P0 - 50, t=P0 + 400, area=(P0 - 10, P0 + 10), family="A", hard_h=4,
               origin="HISTORICAL_MODELED"):
    rec = {"call_id": "call-1", "attempt_id": "AL-1", "family": family, "direction": "LONG" if d > 0 else "SHORT",
           "issued_at": iso(issued), "invalidation": str(v), "target": str(t),
           "structural_area": [str(area[0]), str(area[1])], "hard_deadline": iso(issued + timedelta(hours=hard_h)),
           "env": {"origin": origin, "published_at": iso(issued)}}
    return {"kind": "call", "record": rec}


def rev(at, thesis="ONGOING", enabled=True, reason=None, n=1):
    return {"kind": "call_revision", "record": {
        "call_id": "call-1", "revision": n, "thesis_status": thesis, "entry_conditions_enabled": enabled,
        "terminal_reason": reason, "env": {"published_at": iso(at)}}}


def bar(start, o, h, lo, c):
    return Bar(start, start + MIN, D(o), D(h), D(lo), D(c), D(1), start + MIN, f"m{start.isoformat()}")


def make(es=T0 - timedelta(hours=1), ee=T0 + timedelta(hours=10)):
    return Evaluator(load(), D("0.1"), eval_start=es, eval_end=ee, sample_views=False)


def paths(ev):
    return {r["record"]["variant"]: r["record"] for r in ev.records if r["kind"] == "path"}


def feed(ev, minutes):
    for m in minutes:
        ev.on_minutes([m], [])


def test_entry_uses_the_opening_price_only_never_the_later_hlc():
    ev = make()
    ev.on_journal([call_entry()])
    # primary boundary 10:01: the open (P0+20) is outside the area although the bar later trades inside it
    feed(ev, [bar(T0, P0, P0 + 1, P0 - 1, P0 + 20), bar(T0 + MIN, P0 + 20, P0 + 21, P0 - 5, P0 + 1)])
    feed(ev, [bar(T0 + 2 * MIN, P0 + 1, P0 + 2, P0, P0 + 1)])  # 10:02 open P0+1 inside: entry here
    ev.finish(T0 + timedelta(hours=8))
    p = paths(ev)["PRIMARY"]
    assert p["entry"]["price"] == str(P0 + 1) and p["entry"]["time_start"].endswith("10:02:00Z")
    assert p["rejected_opens"] == 1 and p["entry_attempts"] == 2
    d0 = paths(ev)["ENTRY_DELAY_0"]
    assert d0["entry"]["time_start"].endswith("10:00:00Z")  # delay 0 at an exact minute: that minute's own open


def test_pre_open_state_is_the_latest_revision_published_at_or_before_the_boundary():
    ev = make()
    ev.on_journal([call_entry()])
    feed(ev, [bar(T0, P0, P0, P0, P0)])
    # entry conditions disabled at 10:00:30 (e.g. an event restriction), before the 10:01 boundary
    ev.on_journal([rev(T0 + timedelta(seconds=30), enabled=False)])
    feed(ev, [bar(T0 + MIN, P0, P0, P0, P0)])
    ev.on_journal([rev(T0 + 2 * MIN, enabled=True, n=2)])  # re-enabled exactly at the 10:02 boundary
    feed(ev, [bar(T0 + 2 * MIN, P0 + 2, P0 + 2, P0 + 2, P0 + 2)])
    ev.finish(T0 + timedelta(hours=8))
    assert paths(ev)["PRIMARY"]["entry"]["time_start"].endswith("10:02:00Z")


def test_target_reached_without_entry_is_no_entry_not_a_win():
    ev = make()
    ev.on_journal([call_entry()])
    feed(ev, [bar(T0, P0, P0 + 500, P0, P0 + 450)])  # the call's own minute reaches T
    ev.on_journal([rev(T0 + MIN, thesis="TARGET_REACHED", enabled=False, reason="CERTIFIED_TARGET_CONTACT")])
    feed(ev, [bar(T0 + MIN, P0 + 450, P0 + 451, P0 + 449, P0 + 450)])  # open outside the area anyway
    feed(ev, [bar(T0 + 2 * MIN, P0, P0, P0, P0)])
    ev.finish(T0 + timedelta(hours=8))
    p = paths(ev)
    assert p["PRIMARY"]["status"] == "NO_ENTRY" and p["PRIMARY"]["gross"] is None
    assert p["HORIZON_ONLY"]["status"] == "NO_ENTRY"


def _entered(ev):
    ev.on_journal([call_entry()])
    feed(ev, [bar(T0, P0, P0, P0, P0), bar(T0 + MIN, P0, P0, P0, P0)])  # primary enters at 10:01 open P0


def test_single_contacts_and_both_levels_in_one_minute():
    ev = make()
    _entered(ev)
    feed(ev, [bar(T0 + 2 * MIN, P0, P0 + 401, P0 - 51, P0)])  # both T (P0+400) and V (P0-50) in one minute
    ev.finish(T0 + timedelta(hours=8))
    p = paths(ev)["PRIMARY"]
    assert p["status"] == "AMBIGUOUS" and p["exit"] is None
    b = p["bounds"]
    assert D(b["favorable_target_price_net"]) > 0 > D(b["adverse_stop_price_net"])
    ev = make()
    _entered(ev)
    feed(ev, [bar(T0 + 2 * MIN, P0, P0 + 1, P0 - 50, P0 - 40)])  # inclusive stop contact at exactly V
    p = paths(ev)["PRIMARY"]
    assert p["exit_class"] == "STOP" and p["exit"]["price"] == str(P0 - 50)
    assert p["exit"]["time_start"].endswith("10:02:00Z") and p["exit"]["time_end"].endswith("10:03:00Z")


def test_entry_minute_itself_is_protected():
    ev = make()
    ev.on_journal([call_entry()])
    feed(ev, [bar(T0, P0, P0, P0, P0), bar(T0 + MIN, P0, P0 + 1, P0 - 60, P0 - 55)])
    p = paths(ev)["PRIMARY"]
    assert p["entry"]["time_start"].endswith("10:01:00Z") and p["exit_class"] == "STOP"


def test_pending_exit_collision_table():
    def run(open_px, protect=None):
        ev = make()
        _entered(ev)
        # guidance retirement published 10:02:30 -> modeled exit at ceil(10:02:30 + 60 s) = 10:04 open
        feed(ev, [bar(T0 + 2 * MIN, P0, P0 + 1, P0 - 1, P0)])
        ev.on_journal([rev(T0 + timedelta(minutes=2, seconds=30), thesis="RETIRED", enabled=False,
                           reason="THESIS_FAILED")])
        feed(ev, [protect or bar(T0 + 3 * MIN, P0, P0 + 1, P0 - 1, P0)])
        feed(ev, [bar(T0 + 4 * MIN, open_px, open_px, open_px, open_px)])
        return paths(ev)["PRIMARY"]

    gap_v = run(P0 - 80)
    assert gap_v["exit_class"] == "STOP_GAP" and gap_v["exit"]["price"] == str(P0 - 80)  # adverse open, not V
    assert gap_v["exit"]["time_start"] == gap_v["exit"]["time_end"]  # a certified open boundary
    gap_t = run(P0 + 450)
    assert gap_t["exit_class"] == "TARGET_GAP" and gap_t["exit"]["price"] == str(P0 + 400)  # conservative T
    disc = run(P0 + 5)
    assert disc["exit_class"] == "GUIDANCE_RETIRED" and disc["exit"]["reason"] == "DISCRETIONARY_OPEN"
    # a protective contact in a fully observed minute before the pending boundary prevails
    prot = run(P0 + 5, protect=bar(T0 + 3 * MIN, P0, P0 + 1, P0 - 55, P0 - 10))
    assert prot["exit_class"] == "STOP" and prot["exit"]["time_start"].endswith("10:03:00Z")


def test_missing_minute_before_first_contact_censors_the_path():
    ev = make()
    _entered(ev)
    ev.on_minutes([("GAP", T0 + 2 * MIN, "TRADE_1M_MISSING")], [])
    feed(ev, [bar(T0 + 3 * MIN, P0, P0 + 500, P0, P0 + 450)])  # a later target print cannot be first-certain
    p = paths(ev)["PRIMARY"]
    assert p["status"] == "CENSORED" and p["censored_from"].endswith("10:02:00Z") and p["exit"] is None
    assert p["bounds"]["known_prefix_mfe"] is not None


def test_tail_end_before_evidence_is_unresolved_not_a_forced_close():
    ev = make()
    _entered(ev)
    feed(ev, [bar(T0 + 2 * MIN, P0, P0 + 1, P0 - 1, P0)])
    ev.finish(T0 + 3 * MIN)
    p = paths(ev)
    assert p["PRIMARY"]["status"] == "UNRESOLVED" and p["PRIMARY"]["price_net"] is None
    assert p["HORIZON_ONLY"]["status"] == "UNRESOLVED"


def test_only_historical_calls_issued_inside_the_evaluation_window_are_scored():
    ev = make(es=T0 + timedelta(hours=1))
    ev.on_journal([call_entry()])  # issued in the warmup
    feed(ev, [bar(T0, P0, P0, P0, P0), bar(T0 + MIN, P0, P0, P0, P0)])
    ev.finish(T0 + timedelta(hours=8))
    assert paths(ev) == {}
    ev = make()
    ev.on_journal([call_entry(origin="LIVE")])  # live/reconstructed calls are never hypothetical-evaluated here
    assert ev.calls == {}


def test_horizon_only_baseline_exits_at_issue_plus_family_horizon_without_stop():
    ev = make()
    ev.on_journal([call_entry(hard_h=2, family="C")])
    minutes = [bar(T0 + i * MIN, P0, P0 + 1, P0 - 1, P0) for i in range(2)]
    minutes += [bar(T0 + i * MIN, P0, P0 + 1, P0 - 70, P0 - 60) for i in range(2, 125)]  # V breached: no stop here
    feed(ev, minutes)
    p = paths(ev)
    assert p["PRIMARY"]["exit_class"] == "STOP"
    h = p["HORIZON_ONLY"]
    assert h["exit_class"] == "HORIZON_EXIT" and h["exit"]["time_start"].endswith("12:01:00Z")  # ceil(12:00 + 60 s)
    assert h["entry"] == p["PRIMARY"]["entry"]  # conditioned on the same primary entry
