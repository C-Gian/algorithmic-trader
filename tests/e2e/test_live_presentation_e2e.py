"""WP-009 correction, finding 4 (E2E presentation): the cockpit renders a non-current session's saved call without any
usable-entry presentation. The page is served the REAL ``live_status`` payload (stopped / unresponsive / disconnected
session whose saved call entry was AVAILABLE) and must show the not-current badge, "Non è possibile confermare la
disponibilità dell'ingresso", no admissible range and no "Call live" badge; the current session keeps its saved
presentation (cockpit clarity pass: Italian main panel, same protections)."""

from __future__ import annotations

import json
import sys

import pytest
from playwright.sync_api import expect

from test_ui_smoke import ROOT, browser, evidence_dir, stack  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

sys.path.insert(0, str(ROOT / "tests"))
from test_adviser_correction_live import _Conn, _row  # noqa: E402

from algotrader.adviser import api as adv_api  # noqa: E402


def _payload(row) -> str:
    st = adv_api.live_status(_Conn(row))
    for k in ("view",):
        v = st[k]
        v.update({"origin": "LIVE", "live_since": None, "last_receipt": None, "run_id": "r", "clock": None,
                  "recent_calls": [], "attempts": [], "box": None, "readiness": [], "levels": None,
                  "chart": {"minutes": [], "m15": []}, "notes": [], "counters": {},
                  "market_view": {"observed_context": "UP", "phase": "REACTION", "expected_direction": "UP",
                                  "conditional": True, "table_row": "ONGOING_CALL", "principal": None,
                                  "alternatives": [], "ongoing_call_id": "c1", "horizon_minutes": [30, 180],
                                  "levels": {}, "reasons": [], "counterevidence": [], "blockers": []}})
        v["call"].update({"thesis_status": "ONGOING", "expected_minutes": [30, 180], "duration_window": [30, 180],
                          "progress_check_at": "2025-09-01T07:00:00Z", "premise": "p", "limiting_landmark": None,
                          "revision": 1, "hard_deadline": "2025-09-01T09:00:00Z", "issue_reference": "100000"})
    return json.dumps(st, default=str)


@pytest.mark.parametrize("case", ["stopped", "unresponsive", "disconnected", "current"])
def test_cockpit_never_presents_a_usable_entry_for_a_non_current_session(stack, browser, case):  # noqa: F811
    row = {"stopped": _row(status="stopped"), "unresponsive": _row(lease=-1),
           "disconnected": _row(view_status="DISCONNECTED", connected=False), "current": _row()}[case]
    body = _payload(row)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/api/adviser/live", lambda route: route.fulfill(status=200, body=body,
                                                                  headers={"content-type": "application/json"}))
    page.goto(f"{stack.base}/#market")
    page.wait_for_timeout(2500)  # at least one poll of the scripted status
    assert not errors, errors
    expect(page.get_by_test_id("live-call")).to_be_visible(timeout=15_000)
    if case == "current":
        expect(page.get_by_test_id("live-entry")).to_contain_text("Ingresso disponibile secondo il sistema")
        expect(page.get_by_test_id("live-admissible")).to_contain_text("1 – 2")
        expect(page.get_by_test_id("live-call-not-current")).to_have_count(0)
    else:
        expect(page.get_by_test_id("live-call-not-current")).to_be_visible()
        expect(page.get_by_test_id("live-entry")).to_contain_text("Non è possibile confermare la disponibilità")
        expect(page.get_by_test_id("live-entry")).not_to_contain_text("Ingresso disponibile")
        expect(page.get_by_test_id("live-admissible")).to_have_count(0)
        expect(page.get_by_test_id("live-entry-reasons")).to_contain_text("sessione non corrente")
        expect(page.get_by_test_id("live-call")).not_to_contain_text("Call live")
        expect(page.get_by_test_id("live-not-current")).to_be_visible()
    assert not errors, errors
    ctx.close()
