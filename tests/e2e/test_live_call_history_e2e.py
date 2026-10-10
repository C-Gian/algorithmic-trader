"""Live call history (cockpit, E2E with synthetic payloads only): from the call shown in the live cockpit the Owner
opens THAT call's recorded history. Identity is run + call; a held older response arriving after a call/session/run
switch is never shown; revisions keep recorded order and stored values with UTC times; no-revision, partial, missing
and error states are distinct; available / not-current / terminal states are distinct; a new revision in the cockpit
poll triggers one refetch (no dedicated timer); consulting issues GET requests only."""

from __future__ import annotations

import json
import sys

import pytest
from playwright.sync_api import Route, expect

from test_adviser_e2e import OFFENDERS
from test_ui_smoke import ROOT, browser, evidence_dir, stack  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]
sys.path.insert(0, str(ROOT / "tests"))

T = "2026-10-10T09:{:02d}:00Z"


def call_view(cid: str, rev: int, entry: str = "AVAILABLE", not_current: bool = False) -> dict:
    v = {"call_id": cid, "family": "A", "family_text": "continuation", "direction": "LONG", "origin": "LIVE",
         "issued_at": T.format(0), "issue_reference": "100", "target": "120", "target_type": "LEVEL", "stop": "90",
         "structural_area": ["95", "99"], "admissible_bounds": None if not_current else ["96", "99"],
         "entry_status": "UNVERIFIED" if not_current else entry, "entry_reasons": [], "thesis_status": "ONGOING",
         "hard_deadline": "2026-10-10T12:00:00Z", "remaining_minutes": 150, "expected_minutes": [30, 180],
         "duration_window": [30, 150], "progress_check_at": T.format(30), "premise": "p", "limiting_landmark": None,
         "revision": rev, "guidance": f"guidance now {cid}"}
    if not_current:
        v.update(presentation="NOT_CURRENT", entry_status_saved=entry)
    return v


def live(run: str, session: str, call: dict | None, recent: list | None = None, stale: bool = False) -> dict:
    return {"session": {"session_id": session, "status": "stopped" if stale else "running", "phase": "LIVE",
                        "created_at": T.format(0), "started_at": T.format(0), "stopped_at": None,
                        "stop_requested": False, "error": None, "identity": None, "heartbeat_age_seconds": 1.0,
                        "progress": {}, "connection": {}, "notes": [], "method": "v0.6"},
            "state": "STOPPED" if stale else "LIVE", "running": not stale, "current": not stale,
            "message": "m", "alerts": [], "notice": "n",
            "view": {"status": "LIVE", "connected": True, "live_since": None, "last_receipt": None, "run_id": run,
                     "clock": T.format(10), "origin": "LIVE", "stale_session": stale,
                     "market_view": {"observed_context": "UP", "phase": "REACTION", "expected_direction": "UP",
                                     "conditional": True, "table_row": "ONGOING_CALL", "principal": None,
                                     "alternatives": [], "ongoing_call_id": None, "horizon_minutes": [30, 180],
                                     "levels": {}, "reasons": [], "counterevidence": [], "blockers": []},
                     "call": call, "lenses": [], "recent_calls": recent or [], "attempts": [], "box": None,
                     "readiness": [], "levels": None, "chart": {"minutes": [
                         {"t": T.format(i), "o": "100", "h": "101", "l": "99", "c": str(100 + i % 3)} for i in range(5)],
                         "m15": []}, "notes": [], "counters": {}, "scenarios": []}}


def rev(cid: str, n: int, entry: str, thesis: str = "ONGOING", terminal: str | None = None) -> dict:
    return {"call_id": cid, "revision": n, "entry_status": entry, "entry_reasons": [f"REASON_{cid}_{n}"],
            "thesis_status": thesis, "terminal_reason": terminal, "current_admissible_bounds": ["96", "99"]
            if entry == "AVAILABLE" else None, "remaining_minutes": str(150 - n), "duration_window_minutes": None,
            "guidance": f"recorded guidance {cid} r{n}", "changed": ["thesis"] if terminal else ["entry"],
            "env": {"published_at": f"2026-10-10T09:{10 + n:02d}:00+00:00"}}


def detail(cid: str, revisions: list) -> dict:
    return {"call": {"call_id": cid, "attempt_id": f"att-{cid}", "family": "A", "direction": "LONG", "thesis": "t",
                     "issued_at": "2026-10-10T09:00:00+00:00", "issue_reference": "100", "invalidation": "90",
                     "target": "120", "target_type": "LEVEL", "structural_area": ["95", "99"],
                     "expected_minutes": [30, 180], "hard_deadline": "2026-10-10T12:00:00+00:00", "premise": "p",
                     "entry_status": "AVAILABLE", "thesis_status": "ONGOING",
                     "env": {"factual_cursor": 1, "origin": "LIVE", "published_at": "2026-10-10T09:00:00+00:00"},
                     "actionability": {"gain_bps": None, "risk_bps": None, "cost_envelope_bps": None,
                                       "admissible_bounds": ["96", "99"], "side_price": None, "side_price_source": None},
                     "limiting_landmark": None},
            "candidate": [], "actionability": [], "revisions": revisions, "material_changes": [],
            "market_view_at_issue": None, "hypothetical_paths": [], "hypothetical_paths_withheld_at_cutoff": 0}


def shot(page, loc, path) -> None:
    """Element evidence from a full-page render, so the sticky app header never covers the card."""
    box = loc.bounding_box()
    y = page.evaluate("() => window.scrollY")
    page.screenshot(path=path, full_page=True, clip={"x": box["x"], "y": box["y"] + y, "width": box["width"],
                                                     "height": box["height"]})


class Server:
    """Scripted read endpoints: the live status is replaced by the test; call details can be held and released."""

    def __init__(self, page) -> None:
        self.live: dict = {}
        self.details: dict[str, tuple[int, dict | str]] = {}
        self.hold: set[str] = set()
        self.held: list[tuple[Route, str]] = []
        self.calls: list[str] = []
        self.methods: list[str] = []
        page.on("request", lambda r: self.methods.append(f"{r.method} {r.url}") if "/api/" in r.url else None)
        page.route("**/api/adviser/live", lambda r: r.fulfill(status=200, body=json.dumps(self.live),
                                                              headers={"content-type": "application/json"}))
        page.route("**/api/adviser/runs/*/calls/*", self._call)

    def _call(self, route: Route) -> None:
        path = route.request.url.split("/api/adviser/runs/")[1]
        self.calls.append(path)
        if path in self.hold:
            self.held.append((route, path))
            return
        self._send(route, path)

    def _send(self, route: Route, path: str) -> None:
        status, body = self.details.get(path, (404, "call not found"))
        route.fulfill(status=status, body=body if isinstance(body, str) else json.dumps(body),
                      headers={"content-type": "application/json" if not isinstance(body, str) else "text/plain"})

    def release(self) -> None:
        for route, path in self.held:
            self._send(route, path)
        self.held.clear()


def test_live_call_history_identity_order_states_and_read_only(stack, browser, evidence_dir):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 1280, "height": 1000})
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    s = Server(page)
    hist = page.get_by_test_id("live-call-history")

    # 1. the current call: identity, recorded order, stored values, UTC times, current/available status
    s.live = live("live-R1", "S1", call_view("c1", 2))
    s.details["live-R1/calls/c1"] = (200, detail("c1", [rev("c1", 1, "CLOSED"), rev("c1", 2, "AVAILABLE")]))
    page.goto(f"{stack.base}/#market")
    expect(page.get_by_test_id("live-call-direction")).to_have_text("LONG", timeout=15_000)
    page.get_by_test_id("live-call-history-open").click()
    expect(hist).to_have_attribute("data-state", "ok")
    expect(hist.get_by_test_id("history-identity")).to_contain_text("c1")
    expect(hist.get_by_test_id("history-identity")).to_contain_text("live-R1")
    expect(hist.get_by_test_id("history-identity")).to_contain_text("S1")
    expect(hist.get_by_test_id("history-status-current")).to_contain_text("Entry valid now")
    rows = hist.get_by_test_id("revision-row")
    expect(rows).to_have_count(2)
    assert rows.evaluate_all("els => els.map(e => e.dataset.revision)") == ["1", "2"]
    expect(rows.nth(0)).to_contain_text("2026-10-10 09:11:00 UTC")
    expect(rows.nth(0)).to_contain_text("REASON_c1_1")
    expect(rows.nth(1)).to_contain_text("recorded guidance c1 r2")
    expect(rows.nth(1)).to_contain_text("96 – 99")
    expect(hist).to_contain_text("2026-10-10 09:00:00 UTC")  # issue time, explicit UTC
    expect(hist).not_to_contain_text("Hypothetical")
    shot(page, hist, str(evidence_dir / "live-history-1-current.png"))

    # 2. a new revision in the cockpit poll triggers exactly one refetch; an unchanged poll triggers none
    n = len(s.calls)
    s.details["live-R1/calls/c1"] = (200, detail("c1", [rev("c1", 1, "CLOSED"), rev("c1", 2, "AVAILABLE"),
                                                         rev("c1", 3, "CLOSED")]))
    s.live = live("live-R1", "S1", call_view("c1", 3, entry="CLOSED"))
    expect(rows).to_have_count(3, timeout=10_000)
    expect(hist.get_by_test_id("history-status-current")).to_contain_text("Entry closed now")
    page.wait_for_timeout(4500)  # three cockpit polls with the same revision
    assert len(s.calls) == n + 1, s.calls[n:]

    # 3. not current: saved call of a stopped session
    s.live = live("live-R1", "S1", call_view("c1", 3, entry="CLOSED", not_current=True), stale=True)
    expect(hist.get_by_test_id("history-status-not-current")).to_be_visible(timeout=10_000)
    expect(hist.get_by_test_id("history-status-current")).to_have_count(0)

    # 4. terminal: the call left the view; its terminal revision is history only
    s.details["live-R1/calls/c1"] = (200, detail("c1", [rev("c1", 1, "CLOSED"), rev("c1", 2, "AVAILABLE"),
                                                         rev("c1", 3, "CLOSED"),
                                                         rev("c1", 4, "CLOSED", "INVALIDATED", "STOP_CONTACT")]))
    s.live = live("live-R1", "S1", None, recent=[{"call_id": "c1", "family": "A", "direction": "LONG",
                                                  "issued_at": T.format(0), "terminal": "INVALIDATED",
                                                  "reason": "STOP_CONTACT", "terminal_at": T.format(14),
                                                  "origin": "LIVE"}])
    expect(hist.get_by_test_id("history-status-terminal")).to_contain_text("Invalidated", timeout=10_000)
    expect(hist.get_by_test_id("history-status-terminal")).to_contain_text("No entry is available from this call now")
    expect(rows).to_have_count(4)
    expect(rows.nth(3)).to_contain_text("STOP_CONTACT")
    expect(rows.nth(2)).to_contain_text("Entry closed now")
    shot(page, hist, str(evidence_dir / "live-history-2-terminal.png"))

    # 5. call switch with an older response held and released last: never shown under the new identity
    s.live = live("live-R1", "S1", call_view("c5", 1))
    s.hold.add("live-R1/calls/c5")
    s.details["live-R1/calls/c5"] = (200, detail("c5", [rev("c5", 1, "AVAILABLE")]))
    s.details["live-R1/calls/c6"] = (200, detail("c6", [rev("c6", 1, "AVAILABLE")]))
    expect(page.get_by_test_id("live-call-history-open")).to_contain_text("r1", timeout=10_000)
    page.get_by_test_id("live-call-history-open").click()
    expect(hist.get_by_test_id("history-identity")).to_contain_text("c5")
    expect(hist.get_by_test_id("history-loading")).to_be_visible()
    expect(hist).to_have_attribute("data-state", "loading")
    s.live = live("live-R1", "S1", call_view("c6", 1))
    expect(page.get_by_test_id("live-guidance")).to_contain_text("c6", timeout=10_000)
    page.get_by_test_id("live-call-history-open").click()
    expect(hist.get_by_test_id("history-identity")).to_contain_text("c6")
    expect(hist).to_have_attribute("data-state", "ok")
    s.release()  # the stale c5 response arrives last
    page.wait_for_timeout(800)
    expect(hist.get_by_test_id("history-identity")).to_contain_text("c6")
    expect(hist).to_contain_text("recorded guidance c6 r1")
    expect(hist).not_to_contain_text("c5")

    # 6. session change (same run) and run change: records stay with their own identity
    s.live = live("live-R1", "S2", call_view("c6", 1))
    expect(hist.get_by_test_id("history-session-changed")).to_be_visible(timeout=10_000)
    s.live = live("live-R2", "S3", call_view("c9", 1))
    expect(hist.get_by_test_id("history-status-not-shown")).to_contain_text("another continuity run", timeout=10_000)
    expect(hist.get_by_test_id("history-identity")).to_contain_text("live-R1")
    shot(page, hist, str(evidence_dir / "live-history-3-other-run.png"))

    # 7. no revisions, partial, missing and error are distinct states
    s.details["live-R2/calls/c9"] = (200, detail("c9", []))
    page.get_by_test_id("live-call-history-open").click()
    expect(hist.get_by_test_id("history-identity")).to_contain_text("live-R2")
    expect(hist.get_by_test_id("history-no-revisions")).to_be_visible()
    s.details["live-R2/calls/c9"] = (200, detail("c9", [rev("c9", 1, "AVAILABLE"), rev("c9", 3, "CLOSED")]))
    hist.get_by_test_id("history-reload").click()
    expect(hist.get_by_test_id("history-partial")).to_contain_text("r2")
    shot(page, hist, str(evidence_dir / "live-history-4-partial.png"))
    s.details["live-R2/calls/c9"] = (404, "call c9 not found")
    hist.get_by_test_id("history-reload").click()
    expect(hist.get_by_test_id("history-missing")).to_be_visible()
    expect(hist.get_by_test_id("revision-row")).to_have_count(0)
    s.details["live-R2/calls/c9"] = (500, "boom")
    hist.get_by_test_id("history-reload").click()
    expect(hist.get_by_test_id("history-error")).to_contain_text("boom")
    expect(hist.get_by_test_id("revision-row")).to_have_count(0)
    shot(page, hist, str(evidence_dir / "live-history-5-error.png"))
    s.details["live-R2/calls/c9"] = (200, detail("c8", [rev("c8", 1, "AVAILABLE")]))  # a foreign record
    hist.get_by_test_id("history-reload").click()
    expect(hist.get_by_test_id("history-error")).to_contain_text("does not belong to the selected call")
    expect(hist).not_to_contain_text("recorded guidance c8")
    hist.get_by_test_id("history-close").click()
    expect(hist).to_have_count(0)

    # consulting the history only ever issued GET requests
    assert all(m.startswith("GET ") for m in s.methods), [m for m in s.methods if not m.startswith("GET ")]
    assert not errors, errors
    ctx.close()


def test_live_call_history_fits_a_phone_width(stack, browser, evidence_dir):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    s = Server(page)
    s.live = live("live-R1", "S1", call_view("c1", 2))
    s.details["live-R1/calls/c1"] = (200, detail("c1", [rev("c1", 1, "CLOSED"), rev("c1", 2, "AVAILABLE")]))
    page.goto(f"{stack.base}/#market")
    expect(page.get_by_test_id("live-call-direction")).to_have_text("LONG", timeout=15_000)
    page.wait_for_timeout(300)
    before = page.evaluate(OFFENDERS)  # the cockpit's own pre-existing offenders (method badge), not this panel
    page.get_by_test_id("live-call-history-open").click()
    hist = page.get_by_test_id("live-call-history")
    expect(hist.get_by_test_id("revision-row")).to_have_count(2, timeout=15_000)
    page.wait_for_timeout(300)
    assert page.evaluate(OFFENDERS) == before
    assert hist.evaluate("e => e.scrollWidth <= e.clientWidth && e.getBoundingClientRect().right <= "
                         "document.documentElement.clientWidth")
    shot(page, hist, str(evidence_dir / "live-history-6-phone.png"))
    ctx.close()
