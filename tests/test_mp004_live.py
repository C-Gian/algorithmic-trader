"""WP-014 live path for v0.5 (mocked services and synthetic tapes only; never an Owner live session).

The live session consumes the same causal MP-004 state machine with actual receipt/dispatch times: the reference is
published at the actual dispatch tick (never the bar's nominal end), waiting for the response is shown as a wait (never
an entry, never an alert), the recovery is decided on its complete close but the economics use the current valid side
price (ask LONG / bid SHORT); a stale quote at the recovery consumes the child without waiting for a better quote. The
recorded input tape reproduces the same semantic outputs."""

from __future__ import annotations

from datetime import timedelta

import adviser5_fixtures as fx
import pytest
from adviser3_fixtures import DAY2
from test_adviser_live import COMPAT, Clock, _persisted, fetcher

from algotrader.adviser import live as lv
from algotrader.adviser.core import Quote
from algotrader.feed.contracts import Family

MIN = timedelta(minutes=1)
START = DAY2 + timedelta(hours=3, minutes=16)


def feed(sess, clock, mins, start, end, skip_quote=()):
    t = start
    while t < end:
        m = mins[int((t - (DAY2 - timedelta(days=1))) / MIN)]
        close = t + MIN
        clock.t = close + timedelta(milliseconds=500)
        if t not in skip_quote:
            sess.on_quote(Quote(m.c, m.c, clock.t, clock.t, "BTC-USDT-SWAP", "q" * 64), clock.t)
        clock.t = close + timedelta(seconds=1)
        for fam in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
            ohlc = (m.o, m.h, m.lo, m.c) if fam == Family.TRADE_BAR_1M else (m.c, m.c, m.c, m.c)
            sess.on_live_bar(fam, t, ohlc, ("100", "1", str(m.c)), clock.t)
        clock.t = close + timedelta(milliseconds=1500)
        sess.tick(clock.t)
        t = close


def session(mins, until, skip_quote=(), method="v0.5"):
    clock = Clock(START + timedelta(seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method=method)
    sess.start(None, fetcher(mins))
    sess.on_connection("CONNECTED", clock.t)
    feed(sess, clock, mins, START, until, skip_quote)
    return sess, clock


def a_ents(journal):
    return [e["record"] for e in journal if e["kind"] == "entry_attempt" and e["record"]["scenario_id"][:2] in ("AL", "AS")]


@pytest.fixture(scope="module", params=["L", "S"])
def issued(request):
    # [04:04,04:05) starts before the live publication 04:04:01.5: it straddles p0 and cannot confirm (MP-004 §3);
    # the first bar wholly in the local domain is [04:05,04:06)
    mins = fx.live_tape(fx.neutral(1)[0], fx.VALID)
    mins = mins if request.param == "L" else fx.mirror(mins)
    sess, clock = session(mins, fx.T(4, 9))
    journal, _, tape = sess.driver.take()
    return request.param, sess, journal, tape


def test_live_v05_pins_the_method_publishes_the_reference_at_its_dispatch_and_issues_on_the_side_price(issued):
    side, sess, journal, _ = issued
    core = sess.driver.rt.core
    assert core.cfg.method.model == "btc.context-action.v0.5" and core.cfg.method.implementation == "adviser.core.v5"
    assert lv._session_identity(sess)["method"] == "v0.5" and sess.view()["method"] == "v0.5"
    ents = a_ents(journal)
    assert [(r["transition"], r["env"]["origin"]) for r in ents] == [
        ("WAIT_OPEN", "LIVE"), ("RESPONSE_REFERENCE", "LIVE"), ("ISSUE", "LIVE")]
    ref = ents[1]
    # live publication = the actual dispatch at the bar's receipt (04:04:01), never the bar's nominal end 04:04:00
    assert ref["env"]["clock_time"] == "2025-09-01T04:04:01Z"
    assert ref["response"]["published_at"] == "2025-09-01T04:04:01+00:00"
    assert ref["response"]["reference_end"] == "2025-09-01T04:04:00+00:00"
    [call] = [e["record"] for e in journal if e["kind"] == "call"]
    act = call["actionability"]
    assert call["issued_at"] == "2025-09-01T04:06:01Z" and call["entry_mode"] == "RETURN"
    assert ents[2]["response"]["bars_checked"] == "2"  # the straddling bar was checked (no violation), not decisive
    assert act["execution_mode"] == "LIVE_QUOTED"
    assert act["side_price_source"] == ("MEASURED_ASK" if side == "L" else "MEASURED_BID")
    assert act["side_price"] == ("100012" if side == "L" else "99988")  # ask LONG / bid SHORT at the recovery
    alerts = [e["record"] for e in journal if e["kind"] == "material_change" and e["record"]["alertable"]]
    # the reference and the wait never alert: the first alert is the NEW_CALL at the issue (afterwards the inherited
    # post-issue entry withdraw/reopen alerts follow the quote freshness, unchanged)
    assert alerts[0]["change_type"] == "NEW_CALL" and alerts[0]["env"]["clock_time"] == call["issued_at"]
    assert not [a for a in alerts if a["env"]["clock_time"] < call["issued_at"]]


def test_live_view_while_waiting_for_the_response_is_never_an_entry():
    sess, _ = session(fx.live_tape(fx.FAV_EQ, *fx.neutral(5)), fx.T(4, 10))
    rows = [s for s in sess.view()["scenarios"] if s["family"] == "A" and s.get("waiting")]
    assert rows and rows[0]["waiting"]["phase"] == "WAIT_RESPONSE"
    assert "no call yet, no entry" in rows[0]["waiting"]["text"]
    assert rows[0]["waiting"]["response"]["recovery_rule"].startswith("a later complete 1m close >= 100008.1")
    assert sess.view().get("call") in (None, {})
    journal, _, _ = sess.driver.take()
    assert not [e for e in journal if e["kind"] == "material_change" and e["record"]["alertable"]]


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("bar", ["VALID", "VIOLATE"])
def test_live_bar_straddling_the_publication_never_confirms_and_a_break_there_is_unassessable(side, bar):
    """Live publication follows the receipt (04:04:01), so the bar [04:04,04:05) after the reference always
    straddles p0 (MP-004 §3 / §8 joint 1): a recovery there cannot confirm, a contrary break is UNASSESSABLE."""
    mins = fx.live_tape(getattr(fx, bar), *fx.neutral(10))
    mins = mins if side == "L" else fx.mirror(mins)
    sess, _ = session(mins, fx.T(4, 9))
    journal, _, _ = sess.driver.take()
    ents = [r for r in a_ents(journal) if r["transition"] != "BLOCKERS"]
    assert ents[1]["transition"] == "RESPONSE_REFERENCE" and ents[1]["response"]["reference_bar"].endswith("04:03:00Z")
    if bar == "VALID":
        assert [r["transition"] for r in ents] == ["WAIT_OPEN", "RESPONSE_REFERENCE"]  # still waiting, no call
    else:
        assert ents[-1]["reason"].startswith("LOCAL_CONTACT_TIME_AMBIGUOUS:")
        assert ents[-1]["response"]["outcome"] == "UNASSESSABLE"
    assert not [e for e in journal if e["kind"] == "call"]


@pytest.mark.parametrize("side", ["L", "S"])
def test_stale_quote_at_the_recovery_consumes_the_child_without_waiting(side):
    """MP-004 §4/§6: valid recovery bar, side quote stale at that dispatch: R = 1, N = 1, I = 0."""
    mins = fx.live_tape(fx.neutral(1)[0], fx.VALID, fx.VALID)
    mins = mins if side == "L" else fx.mirror(mins)
    sess, _ = session(mins, fx.T(4, 10), skip_quote=(fx.T(4, 5),))
    journal, _, _ = sess.driver.take()
    ents = [r for r in a_ents(journal) if r["transition"] != "BLOCKERS"]  # inherited WAIT_RETURN blocker records
    assert [r["transition"] for r in ents] == ["WAIT_OPEN", "RESPONSE_REFERENCE", "TERMINAL"]
    last = ents[-1]
    assert last["reason"] == "RESPONSE_NOT_ISSUABLE:QUOTE_STALE" and "QUOTE_STALE" in last["blockers"]
    assert (last["response"]["primary_class"], last["response"]["response_current"]) == ("OTHER_GATES", "true")
    assert not [e for e in journal if e["kind"] == "call"]  # the later fresh valid bar is never used


def test_v05_live_input_tape_reproduces_the_same_semantic_outputs(issued):
    _, sess, journal, tape = issued
    d = lv.replay_tape(tape, lv.live_config(COMPAT, "test", "v0.5"), sess.epoch.cov_from)
    j2, _, _ = d.take()
    assert [e["digest"] for e in j2] == [e["digest"] for e in journal]


def test_restart_from_a_v04_lineage_resets_continuity_instead_of_converting_it():
    mins = fx.valid()
    clock = Clock(START + timedelta(seconds=30))
    s1 = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.4")
    s1.start(None, fetcher(mins))
    s2 = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.5")
    s2.start({**_persisted(s1), "method": "v0.4"}, fetcher(mins))
    assert s2.epoch.run_id != s1.epoch.run_id
    assert any(n.get("reason") == "METHOD_CHANGED:v0.4->v0.5" for n in s2.notes)
    assert s2.driver.rt.core.cfg.method.model == "btc.context-action.v0.5"


def test_live_restore_from_persisted_state_keeps_the_reference():
    """A live restart inside the response wait restores the prepared reference from the persisted v0.5 state."""
    mins = fx.live_tape(fx.FAV_EQ, *fx.neutral(30))
    s1, clock = session(mins, fx.T(4, 7))
    w1 = next(iter(s1.driver.rt.core.waits.values()))
    assert w1.phase == "WAIT_RESPONSE"
    s2 = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.5")
    s2.start(_persisted(s1), fetcher(mins))
    w2 = next(iter(s2.driver.rt.core.waits.values()), None)
    if w2 is not None:  # same continuity: the single reference is carried, never re-prepared
        assert w2.ref == w1.ref and w2.phase == "WAIT_RESPONSE"
    else:  # a restart gap made the continuity unassessable: never a fresh reference from catch-up
        assert not [e for e in s2.driver.take()[0] if e["kind"] == "entry_attempt"
                    and e["record"]["transition"] == "RESPONSE_REFERENCE"]


@pytest.mark.db
def test_start_session_records_v05(database_url):
    from pack_fixtures import connect

    from algotrader.adviser.api import live_status

    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_live_sessions")
        sid = lv.start_session(c, "http://x", "v0.5")
        row = c.execute("SELECT config FROM adviser_live_sessions WHERE session_id = %s", (sid,)).fetchone()
        assert row["config"]["method"] == "v0.5" and live_status(c)["session"]["method"] == "v0.5"
        lv.stop_session(c, sid)
