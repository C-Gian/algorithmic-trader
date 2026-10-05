"""WP-011 live method selection (mocked services only): the method is chosen before Start and pinned; a persisted
lineage of another method is never converted (explicit continuity reset); the v0.3 input tape reproduces the same
semantics; reconstructed (pre-activation) structure never becomes live advice. No network, no market claim."""

from __future__ import annotations

from datetime import timedelta

import pytest
from adviser3_fixtures import DAY2, a3_return_long
from test_adviser_live import COMPAT, Clock, _persisted, fetcher

from algotrader.adviser import live as lv
from algotrader.adviser.core import Quote
from algotrader.feed.contracts import Family

MINS = a3_return_long()
MIN = timedelta(minutes=1)


def feed(sess, clock, start, end):
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


@pytest.fixture(scope="module")
def v03_session():
    clock = Clock(DAY2 + timedelta(hours=3, minutes=50, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.3")
    sess.start(None, fetcher(MINS))
    sess.on_connection("CONNECTED", clock.t)
    feed(sess, clock, DAY2 + timedelta(hours=3, minutes=50), DAY2 + timedelta(hours=4, minutes=10))
    journal, _, tape = sess.driver.take()
    return sess, clock, journal, tape


def test_live_session_pins_the_selected_method_and_shows_structural_scenarios(v03_session):
    sess, _, journal, _ = v03_session
    core = sess.driver.rt.core
    assert core.cfg.method.model == "btc.context-action.v0.3" and core.cfg.method.implementation == "adviser.core.v3"
    v = sess.view()
    assert v["method"] == "v0.3" and isinstance(v["scenarios"], list)
    assert lv._session_identity(sess)["method"] == "v0.3"
    # the A owner was armed during reconstruction: its confirmation never becomes a live call
    ent = [e["record"] for e in journal if e["kind"] == "entry_attempt"]
    assert ent and ent[-1]["state"] == "TERMINAL" and "ARMED_BEFORE_LIVE_ACTIVATION" in ent[-1]["blockers"]
    assert not [e for e in journal if e["kind"] == "call"]


def test_v03_input_tape_reproduces_the_same_semantic_outputs(v03_session):
    sess, _, journal, tape = v03_session
    d = lv.replay_tape(tape, lv.live_config(COMPAT, "test", "v0.3"), sess.epoch.cov_from)
    j2, _, _ = d.take()
    assert [e["digest"] for e in j2] == [e["digest"] for e in journal]


def test_restart_with_another_method_resets_continuity_instead_of_converting_the_lineage():
    clock = Clock(DAY2 + timedelta(hours=3, minutes=50, seconds=30))
    s1 = lv.LiveSession(compat=COMPAT, build="test", clock=clock)  # default v0.2
    s1.start(None, fetcher(MINS))
    p = {**_persisted(s1), "method": "v0.2"}
    s2 = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.3")
    s2.start(p, fetcher(MINS))
    assert s2.epoch.run_id != s1.epoch.run_id
    assert any(n.get("reason") == "METHOD_CHANGED:v0.2->v0.3" for n in s2.notes)
    assert s2.driver.rt.core.cfg.method.model == "btc.context-action.v0.3"
    s3 = lv.LiveSession(compat=COMPAT, build="test", clock=clock)  # same method: lineage continues
    s3.start({**_persisted(s1), "method": "v0.2"}, fetcher(MINS))
    assert s3.epoch.run_id == s1.epoch.run_id


@pytest.mark.db
def test_start_session_records_the_explicit_method_and_rejects_unknown(database_url):
    from pack_fixtures import connect

    from algotrader.adviser.api import live_status

    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_live_sessions")
        with pytest.raises(lv.LiveControlError):
            lv.start_session(c, "http://x", "v0.9")
        sid = lv.start_session(c, "http://x", "v0.3")
        row = c.execute("SELECT config FROM adviser_live_sessions WHERE session_id = %s", (sid,)).fetchone()
        assert row["config"]["method"] == "v0.3"
        assert live_status(c)["session"]["method"] == "v0.3"
        lv.stop_session(c, sid)
        sid2 = lv.start_session(c, "http://x")
        assert "method" not in c.execute("SELECT config FROM adviser_live_sessions WHERE session_id = %s",
                                         (sid2,)).fetchone()["config"]
        assert live_status(c)["session"]["method"] == "v0.2"
        lv.stop_session(c, sid2)
