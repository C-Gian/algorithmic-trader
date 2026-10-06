"""WP-012 live path for v0.4 (mocked services and synthetic tapes only; never an Owner live session).

The live session consumes the same causal MP-003 state machine with actual receipt/dispatch times: the anchor loss and
the prospective replacement of the ``contact_then_rearm`` tape happen while live, never alert or create an entry, show
as "scenario under observation" in the view, and the recorded input tape reproduces the same semantic outputs. A
scenario armed during reconstruction stays pre-live (no catch-up call)."""

from __future__ import annotations

from datetime import timedelta

import adviser4_fixtures as fx
import pytest
from adviser3_fixtures import DAY2
from test_adviser_live import COMPAT, Clock, _persisted, fetcher

from algotrader.adviser import live as lv
from algotrader.adviser.core import Quote
from algotrader.feed.contracts import Family

MINS = fx.contact_then_rearm()
MIN = timedelta(minutes=1)


def feed(sess, clock, start, end, stop_after=None):
    t = start
    while t < end:
        m = MINS[int((t - (DAY2 - timedelta(days=1))) / MIN)]
        close = t + MIN
        clock.t = close + timedelta(milliseconds=500)
        sess.on_quote(Quote(m.c, m.c, clock.t, clock.t, "BTC-USDT-SWAP", "q" * 64), clock.t)
        clock.t = close + timedelta(seconds=1)
        for fam in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
            ohlc = (m.o, m.h, m.lo, m.c) if fam == Family.TRADE_BAR_1M else (m.c, m.c, m.c, m.c)
            sess.on_live_bar(fam, t, ohlc, ("100", "1", str(m.c)), clock.t)
        clock.t = close + timedelta(milliseconds=1500)
        sess.tick(clock.t)
        t = close
        if stop_after is not None and t >= stop_after:
            return


def _session(until):
    clock = Clock(DAY2 + timedelta(hours=3, minutes=46, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.4")
    sess.start(None, fetcher(MINS))
    sess.on_connection("CONNECTED", clock.t)
    feed(sess, clock, DAY2 + timedelta(hours=3, minutes=46), until)
    return sess, clock


@pytest.fixture(scope="module")
def v04_session():
    sess, clock = _session(DAY2 + timedelta(hours=4, minutes=12))
    journal, _, tape = sess.driver.take()
    return sess, clock, journal, tape


def test_live_v04_pins_the_method_and_processes_the_anchor_loss_and_replacement_live(v04_session):
    sess, _, journal, _ = v04_session
    core = sess.driver.rt.core
    assert core.cfg.method.model == "btc.context-action.v0.4" and core.cfg.method.implementation == "adviser.core.v4"
    assert lv._session_identity(sess)["method"] == "v0.4" and sess.view()["method"] == "v0.4"
    scen = [e["record"] for e in journal if e["kind"] == "scenario" and e["record"]["scenario_id"].startswith("AL")]
    tr = [(r["transition"], r["env"]["origin"]) for r in scen if r["transition"] in ("ANCHOR_LOST", "REARM", "CONFIRM")]
    assert tr == [("ANCHOR_LOST", "LIVE"), ("REARM", "LIVE"), ("CONFIRM", "LIVE")]
    rearm = next(r for r in scen if r["transition"] == "REARM")
    # live publication = the actual dispatch time (the tick after the 04:00 bar's receipt at 04:00:01), never the
    # 15m bar's market close 04:00:00 backdated
    assert rearm["anchor_published_at"] == rearm["env"]["clock_time"] == "2025-09-01T04:00:01.500000Z"
    # the scenario was armed during reconstruction (pre-live): no catch-up call and no anchor alert
    assert not [e for e in journal if e["kind"] == "call"]
    assert not [e for e in journal if e["kind"] == "material_change" and e["record"]["alertable"]]


def test_live_view_shows_an_observing_scenario_after_the_loss_never_an_entry():
    sess, _ = _session(DAY2 + timedelta(hours=3, minutes=55))
    rows = [s for s in sess.view()["scenarios"] if s["family"] == "A"]
    assert rows and rows[0]["status"] == "WATCH" and rows[0]["observing"]["text"].startswith(
        "Scenario under observation; waiting for a new completed reaction")
    assert rows[0]["anchor"]["status"] == "INVALIDATED" and rows[0]["anchor"]["ever_armed"] is True
    assert "waiting" not in rows[0] and sess.view().get("call") in (None, {})


def test_v04_live_input_tape_reproduces_the_same_semantic_outputs(v04_session):
    sess, _, journal, tape = v04_session
    d = lv.replay_tape(tape, lv.live_config(COMPAT, "test", "v0.4"), sess.epoch.cov_from)
    j2, _, _ = d.take()
    assert [e["digest"] for e in j2] == [e["digest"] for e in journal]


def test_restart_from_a_v03_lineage_resets_continuity_instead_of_converting_it():
    clock = Clock(DAY2 + timedelta(hours=3, minutes=46, seconds=30))
    s1 = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.3")
    s1.start(None, fetcher(MINS))
    s2 = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.4")
    s2.start({**_persisted(s1), "method": "v0.3"}, fetcher(MINS))
    assert s2.epoch.run_id != s1.epoch.run_id
    assert any(n.get("reason") == "METHOD_CHANGED:v0.3->v0.4" for n in s2.notes)
    assert s2.driver.rt.core.cfg.method.model == "btc.context-action.v0.4"


@pytest.mark.db
def test_start_session_records_v04(database_url):
    from pack_fixtures import connect

    from algotrader.adviser.api import live_status

    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_live_sessions")
        sid = lv.start_session(c, "http://x", "v0.4")
        row = c.execute("SELECT config FROM adviser_live_sessions WHERE session_id = %s", (sid,)).fetchone()
        assert row["config"]["method"] == "v0.4" and live_status(c)["session"]["method"] == "v0.4"
        lv.stop_session(c, sid)
