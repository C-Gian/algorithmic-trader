"""WP-009 live adviser matrix (E) with mocked services only: public ticker shape/invalid/stale/crossed/future/older/
duplicate snapshots and pacing; LIVE activation after current receipts; a live call priced at the measured ask; 5 s
quote expiry without new input (UNVERIFIED, thesis unaffected); restart gap / >96 h abandonment / instrument metadata
reset; no old alert replay; input-tape reproduction of the same semantics. No network, no market claim."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from adviser_fixtures import DAY1, DAY2, a_fixture

from algotrader.adviser import live as lv
from algotrader.adviser.core import Quote
from algotrader.adviser.quotes import QuoteClient, QuoteRejected, parse_ticker
from algotrader.feed.contracts import Family

D = Decimal
MIN = timedelta(minutes=1)
SEC = timedelta(seconds=1)
COMPAT = {"inst_id": "BTC-USDT-SWAP", "index_id": "BTC-USDT", "tick_sz": "0.1", "ct_val": "0.01", "ct_mult": "1",
          "lot_sz": "0.01", "settle_ccy": "USDT"}
MINUTES = a_fixture()


def ticker(bid="100", ask="100.1", ts: datetime | None = None, inst="BTC-USDT-SWAP", code="0") -> bytes:
    ts = ts or datetime(2025, 9, 1, tzinfo=UTC)
    return json.dumps({"code": code, "msg": "", "data": [{
        "instType": "SWAP", "instId": inst, "last": "100", "lastSz": "1", "askPx": ask, "askSz": "5", "bidPx": bid,
        "bidSz": "7", "open24h": "99", "high24h": "101", "low24h": "98", "volCcy24h": "1", "vol24h": "100",
        "sodUtc0": "99", "sodUtc8": "99", "ts": str(int(ts.timestamp() * 1000))}]}).encode()


# -- quotes ---------------------------------------------------------------------------------------------------------


def test_ticker_parser_accepts_the_official_shape_and_rejects_every_invalid_snapshot():
    t = datetime(2025, 9, 1, 12, tzinfo=UTC)
    q = parse_ticker(ticker("100000.1", "100000.2", t), "BTC-USDT-SWAP", t + SEC, None)
    assert (q.bid, q.ask, q.source_ts, q.received_at) == (D("100000.1"), D("100000.2"), t, t + SEC)
    bad = [
        (ticker("0", "1", t), None, "nonpositive"), (ticker("101", "100", t), None, "crossed"),
        (ticker(inst="ETH-USDT-SWAP", ts=t), None, "instrument"), (b"not json", None, "JSON"),
        (ticker(code="50011", ts=t), None, "envelope"), (ticker(ts=t + 5 * SEC), None, "future"),
        (ticker(ts=t - SEC), t, "older"), (ticker(ts=t), t, "NOT_NEWER"),
    ]
    for body, last, why in bad:
        with pytest.raises(QuoteRejected, match=why):
            parse_ticker(body, "BTC-USDT-SWAP", t + SEC, last)
    assert parse_ticker(ticker("100", "100", t), "BTC-USDT-SWAP", t + SEC, None).bid == D(100)  # locked, not crossed


def test_quote_client_is_paced_sequential_bounded_and_never_fabricates():
    t = [datetime(2025, 9, 1, 12, tzinfo=UTC)]
    mono = [0.0]
    sleeps: list[float] = []
    calls: list[str] = []
    replies = [(503, b"busy"), (200, ticker(ts=t[0])), (200, ticker(ts=t[0])), (200, ticker(ts=t[0] + SEC))]

    def transport(url, headers, timeout):
        calls.append(url)
        assert "ok-access-key" not in {k.lower() for k in headers}
        return replies.pop(0)

    def sleep(s):
        sleeps.append(s)
        mono[0] += s

    c = QuoteClient("https://www.okx.com", transport=transport, sleep=sleep, monotonic=lambda: mono[0],
                    clock=lambda: t[0] + SEC)
    assert c.poll() is not None  # 503 retried once (bounded) then accepted
    assert c.poll() is None and c.stats.not_newer == 1  # same snapshot again: its age is never refreshed
    assert c.poll() is not None
    assert all(u.endswith("/api/v5/market/ticker?instId=BTC-USDT-SWAP") for u in calls)
    assert sum(sleeps) >= 2.0  # <= 1 request/second across the four requests (first unpaced)
    with pytest.raises(ValueError):
        QuoteClient("https://evil.example.com")


# -- live session ---------------------------------------------------------------------------------------------------


def fetcher(minutes=MINUTES, start=DAY1, fail: set | None = None):
    def fetch(fam: Family, a: datetime, b: datetime):
        if fail and fam in fail:
            raise ConnectionError("archive unreachable")
        out = []
        for i, m in enumerate(minutes):
            t = start + i * MIN
            if a <= t < b and not m.gap:
                if fam == Family.TRADE_BAR_1M:
                    out.append((t, m.o, m.h, m.lo, m.c, ("100", "1", str(m.c))))
                else:
                    out.append((t, m.c, m.c, m.c, m.c, ("0", "0", "0")))
        return out
    return fetch


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def minute_at(t: datetime):
    return MINUTES[int((t - DAY1) / MIN)]


def feed_live(sess: lv.LiveSession, clock: Clock, start: datetime, end: datetime, quotes: bool = True,
              spread=D("0.1")) -> None:
    """Live minutes [start, end): quote at bar end + 0.5 s, completed push at + 1 s, tick at + 1.5 s."""
    t = start
    while t < end:
        m = minute_at(t)
        close = t + MIN
        if quotes:
            clock.t = close + timedelta(milliseconds=500)
            sess.on_quote(Quote(m.c - spread, m.c + spread, clock.t, clock.t, "BTC-USDT-SWAP", "q" * 64), clock.t)
        clock.t = close + SEC
        sess.on_live_bar(Family.TRADE_BAR_1M, t, (m.o, m.h, m.lo, m.c), ("100", "1", str(m.c)), clock.t)
        sess.on_live_bar(Family.MARK_BAR_1M, t, (m.c, m.c, m.c, m.c), ("0", "0", "0"), clock.t)
        sess.on_live_bar(Family.INDEX_BAR_1M, t, (m.c, m.c, m.c, m.c), ("0", "0", "0"), clock.t)
        clock.t = close + timedelta(milliseconds=1500)
        sess.tick(clock.t)
        t = close


@pytest.fixture(scope="module")
def live_run():
    clock = Clock(DAY2 + timedelta(hours=4, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    sess.start(None, fetcher())
    assert sess.status == "WARMING_UP" and sess.driver.rt.core.origin == "RECONSTRUCTED"
    sess.connected = True
    feed_live(sess, clock, DAY2 + timedelta(hours=4), DAY2 + timedelta(hours=5, minutes=21))
    journal, _, tape = sess.driver.take()
    return sess, clock, journal, tape


def test_live_activation_needs_current_receipts_and_new_calls_need_post_activation_arms(live_run):
    sess, _, journal, _ = live_run
    assert sess.status == "LIVE" and sess.live_since == DAY2 + timedelta(hours=4, minutes=1, seconds=1)
    origins = [e["record"]["category"] for e in journal if e["kind"] == "observation" and e["record"]["name"] == "origin"]
    assert origins[:2] == ["RECONSTRUCTED", "LIVE"]
    calls = [e["record"] for e in journal if e["kind"] == "call"]
    assert len(calls) == 1
    c = calls[0]
    assert c["env"]["origin"] == "LIVE" and c["issued_at"] == "2025-09-01T05:21:01Z"
    a = c["actionability"]
    # the side price is the measured ask (close 242 + 0.1), never the candle close or the midpoint
    assert a["execution_mode"] == "LIVE_QUOTED" and a["side_price_source"] == "MEASURED_ASK"
    assert D(a["side_price"]) == D(100242) + D("0.1")
    assert D(a["cost_envelope_bps"]) > 14  # fees + slippage + prospective exit half-spread
    alerts = lv.alerts_from(journal, "run")
    assert [x["change_type"] for x in alerts] == ["NEW_CALL"]


def test_quote_expiry_after_five_seconds_without_new_input_marks_entry_unverified(live_run):
    sess, clock, _, _ = live_run
    core = sess.driver.rt.core
    assert core.call is not None and core.call.entry == "AVAILABLE"
    issued = core.call.issued_at
    clock.t = issued + timedelta(seconds=6)
    sess.tick(clock.t)  # no new bar, no new quote: the quote-freshness timer alone changes actionability
    assert core.call.entry == "UNVERIFIED" and "QUOTE_STALE" in core.call.entry_reasons
    assert core.call.thesis == "ONGOING"  # missing quotes never end the thesis
    journal, _, _ = sess.driver.take()
    mc = [e["record"] for e in journal if e["kind"] == "material_change"]
    assert [m["change_type"] for m in mc] == ["ENTRY_UNVERIFIED"]
    assert lv.alerts_from(journal, "run") == []  # display/actionability change, not an alert


def test_input_tape_reproduces_the_same_semantic_outputs(live_run):
    sess, _, journal, tape = live_run
    d = lv.replay_tape(tape, lv.live_config(COMPAT, "test"), sess.epoch.cov_from)
    j2, _, _ = d.take()
    assert [e["digest"] for e in j2] == [e["digest"] for e in journal]


def _persisted(sess: lv.LiveSession) -> dict:
    sess.driver.take()
    tb, ts, ab, as_ = sess.driver.encode()
    return {"compat": sess.compat, "run_id": sess.epoch.run_id, "epoch_started": sess.epoch.started,
            "cov_from": sess.epoch.cov_from, "temporal_blob": tb, "temporal_sha256": ts, "adviser_blob": ab,
            "adviser_sha256": as_, "clock": sess.driver.temporal.clock}


def _ongoing():
    clock = Clock(DAY2 + timedelta(hours=4, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    sess.start(None, fetcher())
    sess.connected = True
    feed_live(sess, clock, DAY2 + timedelta(hours=4), DAY2 + timedelta(hours=5, minutes=25))
    assert sess.driver.rt.core.call is not None
    return sess, clock


def test_restart_gap_makes_an_ongoing_live_thesis_unassessable_without_any_alert():
    sess, clock = _ongoing()
    p = _persisted(sess)
    clock.t = clock.t + timedelta(minutes=30)
    s2 = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    s2.start(p, fetcher())
    assert s2.epoch.run_id == sess.epoch.run_id and s2.status == "WARMING_UP"
    assert s2.driver.rt.core.call is None
    journal, _, _ = s2.driver.take()
    revs = [e["record"] for e in journal if e["kind"] == "call_revision"]
    assert revs[0]["thesis_status"] == "UNASSESSABLE" and revs[0]["terminal_reason"] == "RESTART_GAP_OVERLAPS_THESIS"
    assert lv.alerts_from(journal, "run") == []  # never an old alert replayed as new
    assert not [e for e in journal if e["kind"] == "call"]  # reconstruction issues no new call
    assert any(n["event"] == "reconstructed" for n in s2.notes)


def test_downtime_beyond_96h_abandons_continuity_explicitly():
    sess, clock = _ongoing()
    p = _persisted(sess)
    clock.t = clock.t + timedelta(hours=97)
    s2 = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    s2.start(p, fetcher())
    assert s2.epoch.run_id != sess.epoch.run_id
    assert any(n["event"] == "continuity_reset" and n["reason"] == "DOWNTIME_BEYOND_96H" for n in s2.notes)
    old = s2.abandoned[0]["journal"]
    revs = [e["record"] for e in old if e["kind"] == "call_revision"]
    assert revs and revs[-1]["terminal_reason"] == "CONTINUITY_ABANDONED_DOWNTIME_BEYOND_96H"
    assert s2.progress["minutes"] == 96 * 60  # at most 96 h of fresh reconstruction per startup


def test_instrument_metadata_change_resets_instead_of_mixing_tick_definitions():
    sess, clock = _ongoing()
    p = _persisted(sess)
    s2 = lv.LiveSession(compat={**COMPAT, "tick_sz": "0.5"}, build="test", clock=clock)
    s2.start(p, fetcher())
    assert s2.epoch.run_id != sess.epoch.run_id
    assert any(n.get("reason") == "INSTRUMENT_METADATA_CHANGED" for n in s2.notes)


def test_unobtainable_core_history_leaves_warming_up_not_endless_retries():
    clock = Clock(DAY2 + timedelta(hours=4, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    sess.start(None, fetcher(fail={Family.TRADE_BAR_1M}))
    assert sess.status == "WARMING_UP"
    assert any(n["event"] == "catch_up_failed" and n["family"] == "trade_bar_1m" for n in sess.notes)
    v = sess.driver.rt.core.compute_view(sess.driver.temporal.clock)
    assert v["expected_direction"] == "UNAVAILABLE"
