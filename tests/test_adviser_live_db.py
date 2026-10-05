"""WP-009 live adviser worker (DB, mocked OKX REST/WebSocket/ticker only): Start -> bounded reconstruction ->
LIVE activation on current first-completion pushes -> live call with a single NEW_CALL alert -> Stop -> restart:
the old thesis becomes UNASSESSABLE without any repeated alert. No network access."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from adviser_db import fake_from
from adviser_fixtures import DAY1, DAY2, a_fixture
from okx_fake import client
from pack_fixtures import connect

from algotrader.adviser import live as lv
from algotrader.adviser.core import Quote

pytestmark = pytest.mark.db
MIN = timedelta(minutes=1)
SEC = timedelta(seconds=1)
MINUTES = a_fixture()


class FakeClock:
    def __init__(self, t: datetime) -> None:
        self.t = t
        self.lock = threading.Lock()

    def __call__(self) -> datetime:
        with self.lock:
            return self.t

    def set(self, t: datetime) -> None:
        with self.lock:
            self.t = max(self.t, t)


def ws_messages(start: datetime, end: datetime) -> list[tuple[datetime, str]]:
    out = []
    t = start
    while t < end:
        i = int((t - DAY1) / MIN)
        m = MINUTES[i]
        ms = str(int(t.timestamp() * 1000))
        recv = t + MIN + SEC
        out.append((recv - SEC / 2, json.dumps({"arg": {"channel": "candle1m", "instId": "BTC-USDT-SWAP"}, "data": [
            [ms, str(m.o), str(m.h), str(m.lo), str(m.c), "100", "1", str(m.c), "0"]]})))  # forming: ignored
        for ch, inst, row in (("candle1m", "BTC-USDT-SWAP", [ms, str(m.o), str(m.h), str(m.lo), str(m.c), "100", "1",
                                                             str(m.c), "1"]),
                              ("mark-price-candle1m", "BTC-USDT-SWAP", [ms, str(m.c), str(m.c), str(m.c), str(m.c), "1"]),
                              ("index-candle1m", "BTC-USDT", [ms, str(m.c), str(m.c), str(m.c), str(m.c), "1"])):
            out.append((recv, json.dumps({"arg": {"channel": ch, "instId": inst}, "data": [row]})))
        out.append((recv + SEC / 4, out[-3][1]))  # a later duplicate completion of the trade bar: never re-admitted
        t += MIN
    return out


class FakeWS:
    """Scripted pushes, released only once the test opens the gate (after the bounded catch-up), so the fake clock
    never runs ahead of the session's own startup."""

    def __init__(self, clock: FakeClock, msgs: list[tuple[datetime, str]]) -> None:
        self.clock, self.msgs, self.sent = clock, list(msgs), []
        self.gate = threading.Event()
        self.quotes: FakeQuotes | None = None

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def recv(self) -> str:
        while not self.gate.is_set():
            await asyncio.sleep(0.01)
        if not self.msgs:
            await asyncio.sleep(3600)
        t, text = self.msgs.pop(0)
        if self.quotes is not None and '"candle1m"' in text and '"1"]]' in text:
            # a fresh quote half a second before each completed trade push, taken by the poller first
            self.quotes.offer(t - SEC / 2)
            while not self.quotes.taken.is_set():
                await asyncio.sleep(0.001)
            await asyncio.sleep(0.01)  # let the quote loop enqueue it before this push
        self.clock.set(t)
        await asyncio.sleep(0)
        return text

    async def close(self) -> None:
        return None


class FakeQuotes:
    """Scripted public quotes: one per offered instant (the latest complete close +/- 0.1), never fabricated."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.pending: list[datetime] = []
        self.taken = threading.Event()
        self.lock = threading.Lock()
        self.stats = None

    def offer(self, t: datetime) -> None:
        with self.lock:
            self.taken.clear()
            self.pending.append(t)

    def poll(self) -> Quote | None:
        time.sleep(0.001)
        with self.lock:
            if not self.pending:
                return None
            t = self.pending.pop(0)
            self.taken.set()
        self.clock.set(t)
        i = min(int((floor(t) - DAY1) / MIN) - 1, len(MINUTES) - 1)
        c = MINUTES[i].c
        return Quote(c - Decimal("0.1"), c + Decimal("0.1"), t, t, "BTC-USDT-SWAP", "q" * 64)


def floor(t: datetime) -> datetime:
    return t.replace(second=0, microsecond=0)


def _run_worker(database_url, clock, msgs):
    f = fake_from(MINUTES)
    ws = FakeWS(clock, msgs)

    async def connect_ws(url):
        return ws

    quotes = FakeQuotes(clock)
    ws.quotes = quotes
    w = lv.LiveAdviserWorker(database_url, worker_id="adviser:test", lease_seconds=30,
                             rest_client_factory=lambda base: client(f), quote_client_factory=lambda base: quotes,
                             ws_connect=connect_ws, clock=clock, tick_seconds=0.005, save_seconds=0.05, build="test")
    th = threading.Thread(target=w.run_once, daemon=True)
    th.start()
    return th, ws


def _wait(database_url, sql, args, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        with connect(database_url) as c:
            row = c.execute(sql, args).fetchone()
        if row:
            return row
        time.sleep(0.2)
    raise AssertionError(f"timeout waiting for {sql}")


def test_live_start_call_alert_stop_and_restart_without_repeated_alerts(database_url):
    clock = FakeClock(DAY2 + timedelta(hours=4, seconds=30))
    with connect(database_url) as c:
        sid = lv.start_session(c)
    th, ws = _run_worker(database_url, clock, ws_messages(DAY2 + timedelta(hours=4),
                                                         DAY2 + timedelta(hours=5, minutes=30)))
    _wait(database_url, "SELECT 1 FROM adviser_live_sessions WHERE session_id = %s AND view->>'status' = "
                        "'WARMING_UP'", (sid,))
    ws.gate.set()
    call = _wait(database_url, "SELECT * FROM adviser_journal WHERE kind = 'call'", ())
    _wait(database_url, "SELECT * FROM adviser_alerts WHERE change_type = 'NEW_CALL'", ())
    with connect(database_url) as c:
        lv.stop_session(c, sid)
    th.join(60)
    with connect(database_url) as c:
        s = c.execute("SELECT * FROM adviser_live_sessions WHERE session_id = %s", (sid,)).fetchone()
        alerts = c.execute("SELECT * FROM adviser_alerts ORDER BY created_at").fetchall()
        tape = c.execute("SELECT count(*) AS n FROM adviser_input_tape").fetchone()["n"]
        state = c.execute("SELECT * FROM adviser_live_state").fetchone()
    assert s["status"] == "stopped" and s["view"]["status"] == "STOPPED"
    assert call["record"]["env"]["origin"] == "LIVE" and call["origin"] == "LIVE"
    assert alerts[0]["change_type"] == "NEW_CALL"  # later entry withdrawals/reopenings are their own transitions
    assert len({a["alert_key"] for a in alerts}) == len(alerts)
    assert {a["change_type"] for a in alerts} <= {"NEW_CALL", "ENTRY_WITHDRAWN", "ENTRY_UNVERIFIED", "ENTRY_REOPENED",
                                                 "TERMINAL"}  # UNVERIFIED alerts once (Director, finding 4)
    assert tape > 0 and state is not None
    first_run = call["run_id"]
    # restart 30 minutes later: the old thesis overlapping the gap becomes UNASSESSABLE, never a new alert
    clock.set(DAY2 + timedelta(hours=6))
    with connect(database_url) as c:
        sid2 = lv.start_session(c)
    th2, ws2 = _run_worker(database_url, clock, [])
    ws2.gate.set()
    _wait(database_url, "SELECT * FROM adviser_journal WHERE kind = 'call_revision' AND "
                        "record->>'terminal_reason' = 'RESTART_GAP_OVERLAPS_THESIS'", ())
    with connect(database_url) as c:
        lv.stop_session(c, sid2)
    th2.join(60)
    with connect(database_url) as c:
        alerts2 = c.execute("SELECT * FROM adviser_alerts").fetchall()
        runs = {r["run_id"] for r in c.execute("SELECT DISTINCT run_id FROM adviser_journal").fetchall()}
        seqs = [r["seq"] for r in c.execute("SELECT seq FROM adviser_journal WHERE run_id = %s ORDER BY seq",
                                            (first_run,)).fetchall()]
    assert len(alerts2) == len(alerts)  # nothing re-alerted after the restart
    assert runs == {first_run}  # same continuity epoch (gap < 96 h)
    assert seqs == list(range(1, len(seqs) + 1))


_ = UTC
