"""WP-009 correction, finding 5 (DB worker, offline fakes only): the live session owns instrument metadata acquisition,
catch-up and live operation. Stop during a slow catch-up is honoured between bounded units (no LIVE, no alert, no
further history request after the worker returns); lease/fence loss during startup and a startup failure both signal
and join the startup thread and close the owned candle socket. No network, no Owner stack."""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import timedelta

import pytest
from adviser_db import fake_from
from adviser_fixtures import DAY2, a_fixture
from okx_fake import client
from pack_fixtures import connect
from test_adviser_live_db import FakeClock

from algotrader.adviser import live as lv

pytestmark = pytest.mark.db


class SlowRest:
    """Delegating public client whose history pages take ``delay`` seconds each (a long 96 h catch-up)."""

    def __init__(self, inner, delay=0.2, fail_instrument=False):
        self.inner, self.delay, self.fail_instrument = inner, delay, fail_instrument
        self.pages = 0
        self.lock = threading.Lock()

    def instrument(self, inst):
        if self.fail_instrument:
            raise ConnectionError("instrument metadata unavailable")
        return self.inner.instrument(inst)

    def history_page(self, *a, **kw):
        time.sleep(self.delay)
        with self.lock:
            self.pages += 1
        return self.inner.history_page(*a, **kw)


class IdleWS:
    def __init__(self):
        self.closed = threading.Event()
        self.sent = []

    async def send(self, text):
        self.sent.append(text)

    async def recv(self):
        await asyncio.sleep(3600)

    async def close(self):
        self.closed.set()


class NoQuotes:
    stats = None

    def poll(self):
        time.sleep(0.01)
        return None


def _worker(database_url, rest, ws, clock):
    async def connect_ws(url):
        return ws

    w = lv.LiveAdviserWorker(database_url, worker_id="adviser:corr", lease_seconds=30,
                             rest_client_factory=lambda base: rest, quote_client_factory=lambda base: NoQuotes(),
                             ws_connect=connect_ws, clock=clock, tick_seconds=0.01, save_seconds=0.05, build="test")
    th = threading.Thread(target=w.run_once, daemon=True)
    th.start()
    return th


def _wait(pred, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return
        time.sleep(0.05)
    raise AssertionError("timeout")


def _session(database_url, sid):
    with connect(database_url) as c:
        return c.execute("SELECT * FROM adviser_live_sessions WHERE session_id = %s", (sid,)).fetchone()


def _setup(database_url, **kw):
    clock = FakeClock(DAY2 + timedelta(hours=4, seconds=30))
    rest = SlowRest(client(fake_from(a_fixture())), **kw)
    ws = IdleWS()
    with connect(database_url) as c:
        sid = lv.start_session(c)
    return clock, rest, ws, sid


def test_stop_during_a_slow_catch_up_is_cooperative_and_never_enters_live(database_url):
    clock, rest, ws, sid = _setup(database_url)
    th = _worker(database_url, rest, ws, clock)
    _wait(lambda: rest.pages >= 2)
    with connect(database_url) as c:
        lv.stop_session(c, sid)
    th.join(30)
    assert not th.is_alive()
    pages = rest.pages
    time.sleep(0.6)
    assert rest.pages == pages  # no history request after the worker returned (startup thread joined)
    assert ws.closed.is_set()  # the owned candle socket is closed
    s = _session(database_url, sid)
    assert s["status"] == "stopped" and s["progress"]["phase"] == "CANCELLED"
    assert (s["view"] or {}).get("status") in (None, "STOPPED")
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM adviser_alerts").fetchone()["n"] == 0
        assert c.execute("SELECT count(*) AS n FROM adviser_journal WHERE kind = 'call'").fetchone()["n"] == 0
        origins = [r["record"]["category"] for r in c.execute(
            "SELECT record FROM adviser_journal WHERE kind = 'observation' AND record->>'name' = 'origin'").fetchall()]
    assert "LIVE" not in origins


def test_fence_loss_during_startup_joins_the_startup_thread_and_closes_the_socket(database_url):
    clock, rest, ws, sid = _setup(database_url, delay=0.5)
    th = _worker(database_url, rest, ws, clock)
    _wait(lambda: rest.pages >= 2)
    with connect(database_url) as c:  # another owner takes the lease (generation fence)
        c.execute("UPDATE adviser_live_sessions SET lease_generation = lease_generation + 1, lease_owner = 'other' "
                  "WHERE session_id = %s", (sid,))
        c.commit()
    at_fence = rest.pages
    th.join(30)
    assert not th.is_alive()
    pages = rest.pages
    # cooperative: the heartbeat observes the fence within one save interval and the startup thread stops at its
    # next page boundary (no completion of the whole catch-up after the lease was lost)
    assert pages <= at_fence + 2, (at_fence, pages)
    time.sleep(0.6)
    assert rest.pages == pages and ws.closed.is_set()
    s = _session(database_url, sid)
    assert s["status"] == "running" and s["lease_owner"] == "other"  # the fenced worker wrote nothing more


def test_startup_failure_is_visible_and_releases_owned_work(database_url):
    clock, rest, ws, sid = _setup(database_url, fail_instrument=True)
    th = _worker(database_url, rest, ws, clock)
    th.join(30)
    assert not th.is_alive() and ws.closed.is_set() and rest.pages == 0
    s = _session(database_url, sid)
    assert s["status"] == "failed" and "instrument metadata unavailable" in s["error"]
