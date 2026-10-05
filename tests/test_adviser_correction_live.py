"""WP-009 correction, findings 4-5 (pure, mocked inputs only). Candle-session connection is a TAPED adequacy input:
loss (even with fresh quotes) makes entry UNVERIFIED with one committed alert; reconnection alone is not adequate until a
fresh complete trade bar is received after it (then one reopening); a silent stale socket follows the registered 1m
staleness terminal rule; the Owner's Stop is taped (UNVERIFIED) but never alerted; the tape reproduces all of it. The
API/Copy-analysis boundary never presents a usable entry for a non-current session (stored history unchanged).
Startup catch-up honours Stop between bounded units (history pages, replayed minutes)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from test_adviser_live import COMPAT, DAY2, SEC, Clock, _ongoing, feed_live, fetcher

from algotrader.adviser import api as adv_api
from algotrader.adviser import live as lv
from algotrader.adviser.core import Quote
from algotrader.adviser.runtime import AdviserRuntime
from algotrader.feed.contracts import Family

D = Decimal
MIN = timedelta(minutes=1)


def _quote(sess, clock, dt=SEC):
    clock.t += dt
    core = sess.driver.rt.core
    px = core.call.ref if core.call is not None else core.last_1m.c  # an admissible side price (as in the probe)
    sess.on_quote(Quote(px - D("0.1"), px + D("0.1"), clock.t, clock.t, "BTC-USDT-SWAP", "q" * 64), clock.t)
    sess.tick(clock.t)


def _alerts(sess):
    j, _, _ = sess.driver.take()
    return j, [a["change_type"] for a in lv.alerts_from(j, "run")]


def _available():
    sess, clock = _ongoing()
    core = sess.driver.rt.core
    _quote(sess, clock)
    assert core.call.entry == "AVAILABLE" and core.connection["state"] == "CONNECTED"
    sess.driver.take()
    return sess, clock, core


def test_disconnect_with_fresh_quotes_makes_entry_unverified_and_alerts_once():
    sess, clock, core = _available()
    sess.on_connection("DISCONNECTED", clock.t)
    _quote(sess, clock)  # a fresh, admissible public quote cannot substitute for the candle session
    assert core.call.entry == "UNVERIFIED" and core.call.entry_reasons == ["CANDLE_CONNECTION_LOST"]
    assert core.call.thesis == "ONGOING" and sess.status == "DISCONNECTED"
    _, alerts = _alerts(sess)
    assert alerts == ["ENTRY_UNVERIFIED"]
    for _ in range(20):  # further ticks/quotes while still disconnected: no per-tick alerts
        _quote(sess, clock)
    assert _alerts(sess)[1] == []


def test_reconnection_alone_is_not_adequate_until_a_fresh_bar_then_one_reopening():
    sess, clock, core = _available()
    sess.on_connection("DISCONNECTED", clock.t)
    _quote(sess, clock)
    sess.driver.take()
    clock.t += 10 * SEC
    sess.on_connection("CONNECTED", clock.t)
    _quote(sess, clock)
    assert core.call.entry == "UNVERIFIED" and core.call.entry_reasons == ["CANDLE_CONNECTION_AWAITING_FRESH_BAR"]
    assert _alerts(sess)[1] == []
    start = clock.t.replace(second=0, microsecond=0)
    feed_live(sess, clock, start, start + MIN)  # a fresh complete trade bar received after the reconnection
    assert core.connection["state"] == "CONNECTED"
    assert not set(core.call.entry_reasons) & {"CANDLE_CONNECTION_LOST", "CANDLE_CONNECTION_AWAITING_FRESH_BAR"}
    j, alerts = _alerts(sess)
    if core.call.entry == "AVAILABLE":
        assert alerts == ["ENTRY_REOPENED"]
    else:  # the fixture price may have left the area meanwhile: then no reopening may be claimed
        assert "ENTRY_REOPENED" not in alerts


def test_silent_stale_socket_follows_the_registered_staleness_terminal_rule():
    sess, clock, core = _available()
    cid = core.call.cid
    last_end = core.last_1m.end
    for _ in range(150):  # socket "connected" but silent: only quotes and ticks for 150 s
        _quote(sess, clock)
    assert clock.t > last_end + timedelta(seconds=120)
    assert core.call is None and core.recent_calls[-1]["call_id"] == cid
    assert core.recent_calls[-1]["terminal"] == "UNASSESSABLE"
    j, alerts = _alerts(sess)
    assert alerts.count("TERMINAL") == 1


def test_owner_stop_is_taped_unverified_but_never_alerted():
    sess, clock, core = _available()
    sess.on_connection("STOPPED", clock.t)
    sess.tick(clock.t)
    assert core.call.entry == "UNVERIFIED" and core.call.entry_reasons == ["LIVE_SESSION_STOPPED"]
    j, alerts = _alerts(sess)
    assert alerts == [] and [e["record"]["change_type"] for e in j if e["kind"] == "material_change"] ==         ["ENTRY_UNVERIFIED"]


def test_the_tape_reproduces_disconnect_reconnect_and_stop():
    sess, clock = _ongoing()
    core = sess.driver.rt.core
    _quote(sess, clock)
    sess.on_connection("DISCONNECTED", clock.t)
    _quote(sess, clock)
    clock.t += 5 * SEC
    sess.on_connection("CONNECTED", clock.t)
    _quote(sess, clock)
    start = clock.t.replace(second=0, microsecond=0)
    feed_live(sess, clock, start, start + MIN)
    sess.on_connection("STOPPED", clock.t)
    sess.tick(clock.t)
    journal, _, tape = sess.driver.take()
    assert {c["cmd"] for c in tape} >= {"connection", "quote", "admit", "advance"}
    replay = lv.replay_tape(tape, lv.live_config(COMPAT, "test"), sess.epoch.cov_from)
    j2, _, _ = replay.take()
    assert [e["digest"] for e in j2] == [e["digest"] for e in journal]
    assert replay.rt.core.connection == core.connection


def test_restored_state_keeps_connection_adequacy():
    sess, clock, core = _available()
    sess.on_connection("DISCONNECTED", clock.t)
    _quote(sess, clock)
    sess.driver.take()
    tb, ts, ab, as_ = sess.driver.encode()
    d2 = lv.LiveDriver.decode(tb, ts, ab, as_, lv.live_config(COMPAT, "test"))
    assert d2.rt.core.connection == core.connection and d2.rt.core.call.entry == "UNVERIFIED"


# -- presentation boundary (API / UI / Copy analysis) ---------------------------------------------------------------

class _Res:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, session):
        self.session = session

    def execute(self, sql, args=()):
        return _Res([self.session] if "adviser_live_sessions" in sql else [])


def _row(status="running", view_status="LIVE", connected=True, lease=30, hb=1.0):
    now = datetime.now(UTC)
    call = {"call_id": "c1", "direction": "LONG", "family": "A", "family_text": "x", "issued_at": "t", "origin": "LIVE",
            "entry_status": "AVAILABLE", "entry_reasons": [], "structural_area": ["1", "2"],
            "admissible_bounds": ["1", "2"], "target": "3", "target_type": "LANDMARK", "stop": "0",
            "hard_deadline": "t", "remaining_minutes": "100", "guidance": "g"}
    view = {"status": view_status, "connected": connected, "call": call, "market_view": {}, "lenses": []}
    return {"session_id": "s", "status": status, "phase": view_status, "created_at": now, "started_at": now,
            "stopped_at": None, "stop_requested": False, "error": None, "identity": None,
            "heartbeat_at": now - timedelta(seconds=hb), "lease_expires_at": now + timedelta(seconds=lease),
            "progress": {}, "connection": {}, "diagnostic_log": [], "view": view}


def test_current_live_session_presents_the_saved_entry_unchanged():
    st = adv_api.live_status(_Conn(_row()))
    assert st["current"] and st["view"]["call"]["entry_status"] == "AVAILABLE"
    assert st["view"]["call"]["admissible_bounds"] == ["1", "2"]
    assert "Entry now: **AVAILABLE**" in adv_api.analysis_markdown(st)


def test_non_current_sessions_never_present_a_usable_entry():
    cases = {"STOPPED": _row(status="stopped"), "FAILED": _row(status="failed"),
             "UNRESPONSIVE": _row(lease=-1), "DISCONNECTED": _row(view_status="DISCONNECTED", connected=False),
             "LIVE_STALE_HEARTBEAT": _row(hb=60), "LIVE_NOT_CONNECTED": _row(connected=False)}
    for name, row in cases.items():
        st = adv_api.live_status(_Conn(row))
        call = st["view"]["call"]
        assert not st["current"], name
        assert call["entry_status"] == "UNVERIFIED" and call["entry_status_saved"] == "AVAILABLE", name
        assert call["admissible_bounds"] is None and call["presentation"] == "NOT_CURRENT", name
        assert any(r.startswith("SESSION_NOT_CURRENT:") for r in call["entry_reasons"]), name
        md = adv_api.analysis_markdown(st)
        assert "Not current advice" in md and "Entry now: **AVAILABLE**" not in md, name
        assert row["view"]["call"]["entry_status"] == "AVAILABLE"  # the stored view/history is not rewritten


# -- cooperative startup Stop ----------------------------------------------------------------------------------------

def _fresh_session(now):
    sess = lv.LiveSession(COMPAT, "test", lambda: now)
    start = now - timedelta(minutes=10)
    sess.epoch = lv.new_epoch(start, COMPAT)
    sess.driver = lv.LiveDriver(lv.new_temporal(start), AdviserRuntime(
        lv.AdviserCore(lv.live_config(COMPAT, "test")), None))
    return sess


def _ten(a):
    return [(a + i * MIN, D(100000), D(100001), D(99999), D(100000), ("1", "1", "1")) for i in range(10)]


def test_stop_after_the_last_acquisition_performs_no_replay_work():
    now = datetime(2025, 9, 1, 12, tzinfo=UTC)
    sess = _fresh_session(now)

    def fetch(fam, a, b):
        if fam == Family.INDEX_BAR_1M:
            sess.cancel_requested = True  # Director probe: Stop observed after the last family acquisition
        return _ten(a)

    sess.reconstruct(fetch, now)
    assert sess.driver.cursor == 0 and sess.progress.get("replayed_minutes") is None
    assert sess.progress["phase"] == "CANCELLED" and sess.status == "STOPPING"


def test_stop_during_replay_stops_at_the_next_minute():
    now = datetime(2025, 9, 1, 12, tzinfo=UTC)
    sess = _fresh_session(now)
    adv = sess.driver.advance

    def advance(t, record_noop=False):
        if sess.progress.get("replayed_minutes") == 3:
            sess.cancel_requested = True  # Stop observed while the 4th minute is being folded
        return adv(t, record_noop)

    sess.driver.advance = advance
    sess.reconstruct(lambda fam, a, b: _ten(a), now)
    # the in-flight minute completes atomically; no further unit starts
    assert sess.progress["replayed_minutes"] == 4 and sess.progress["phase"] == "CANCELLED"


def test_history_fetcher_checks_stop_between_pages():
    flag = {"stop": False}
    pages = []

    class Page:
        def __init__(self, data):
            self.data = data

    class Client:
        def history_page(self, fam, inst, after, before, limit):
            pages.append(after)
            flag["stop"] = True  # Stop arrives while the first page is in flight
            base = after - 100 * 60000
            return Page([[str(base + i * 60000), "1", "1", "1", "1", "1", "1", "1", "1"] for i in range(100)])

    fetch = lv.history_fetcher(Client(), lambda: flag["stop"])
    start = datetime(2025, 9, 1, tzinfo=UTC)
    try:
        fetch(Family.TRADE_BAR_1M, start, start + timedelta(hours=5))
        raise AssertionError("expected CatchUpCancelled")
    except lv.CatchUpCancelled:
        pass
    assert len(pages) == 1


def test_start_with_stop_already_observed_never_activates_live():
    clock = Clock(DAY2 + timedelta(hours=4, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    sess.cancel_requested = True
    sess.start(None, fetcher())
    assert sess.status == "STOPPING" and sess.driver.cursor == 0
    assert sess.driver.rt.core.origin == "RECONSTRUCTED"
