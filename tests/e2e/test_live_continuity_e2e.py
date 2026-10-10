"""Live entry-availability continuity (E2E; offline scripted fakes only, the same in-process live worker as
``test_adviser_e2e``): a call AVAILABLE -> the scripted public updates stop (no candle push, no ticker quote) while the
worker's clock advances -> the frozen quote-freshness rule makes the SAME call UNVERIFIED (QUOTE_STALE), served by the
real API and shown by the real cockpit, also after a page reload -> updates resume -> the cockpit follows whatever the
backend then establishes (here CLOSED, PRICE_OUTSIDE_STRUCTURAL_AREA: resuming never implies AVAILABLE). No stale
admissible band or AVAILABLE wording is ever presented as usable during the interruption.

Stored alerts (banner and *What changed* timeline) are checked during UNVERIFIED and CLOSED, before and after a reload:
each is a past event with its recorded local time, a past-tense headline from its recorded type, and the frozen text only
behind "Testo registrato a quell'ora"; current availability is pointed to the main panel, which equals the backend.
Method v0.2 is the cockpit default with this fixture: the banner, timeline and main panel exercised here are the
components shared by every method version (no v0.6-specific behaviour is certified by this test)."""

from __future__ import annotations

import sys
from datetime import timedelta

import pytest
from playwright.sync_api import expect

from test_ui_smoke import ROOT, WEB_DIST, Stack, browser, evidence_dir, record, wait_for  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]
sys.path.insert(0, str(ROOT / "tests"))
from adviser_fixtures import DAY2  # noqa: E402

# records every main-panel state the page ever renders (sampled every 25 ms), across reloads of this page
RECORDER = """window.__states = []; setInterval(() => {
  const s = document.querySelector('[data-testid=live-call]')?.dataset.state;
  if (s && window.__states[window.__states.length - 1] !== s) window.__states.push(s); }, 25);"""


def _call(stack) -> dict | None:
    st = stack.get("/api/adviser/live")
    return (st.get("view") or {}).get("call"), st


# past-tense headline per recorded change type (frontend presentation of stored alerts)
EVENT_IT = {
    "NEW_CALL": "Il sistema ha emesso una nuova call.",
    "ENTRY_REOPENED": "Il sistema ha segnalato che l'ingresso era di nuovo disponibile.",
    "ENTRY_WITHDRAWN": "Il sistema ha segnalato che l'ingresso non era più disponibile.",
    "ENTRY_UNVERIFIED": "Il sistema ha segnalato che la disponibilità dell'ingresso non era confermabile.",
    "TERMINAL": "Il sistema ha segnalato la conclusione della call.",
}
# the recorded instant rendered in the browser's local time with its zone (same Intl options as the cockpit)
LOCAL_OF = """(iso) => new Intl.DateTimeFormat("it-IT", {day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit",
  minute: "2-digit", second: "2-digit", timeZoneName: "short"}).format(new Date(iso.replace(/(\.\d{3})\d+/, "$1")))"""


def _check_historical_alerts(page, stack, band: list[str]) -> dict:
    """Banner and timeline show stored alerts as recorded past events; the main panel equals the backend state."""
    call, st = _call(stack)
    api = {a["alert_key"]: a for a in st["alerts"]}
    expect(page.get_by_test_id("live-call")).to_have_attribute("data-state", call["entry_status"])
    seen: dict = {}
    for area, box_id, pointer_id in (("banner", "live-alerts", "alerts-current-pointer"),
                                     ("timeline", "live-changes", "timeline-current-pointer")):
        box = page.get_by_test_id(box_id)
        expect(box.get_by_test_id(pointer_id)).to_contain_text("riquadro principale «Che cosa propone il sistema adesso»")
        items = box.get_by_test_id("historical-alert")
        expect(items.first).to_be_visible()
        visible = box.inner_text()  # rendered text only: the closed disclosures are not part of it
        for stale in ("Entry still valid now", "entry available inside", *band):
            assert stale not in visible, (area, stale, visible)
        rows = []
        for i in range(items.count()):
            it = items.nth(i)
            a = api[it.get_attribute("data-alert-key")]
            assert it.get_attribute("data-change-type") == a["change_type"]
            assert it.get_by_test_id("alert-time").inner_text() == page.evaluate(LOCAL_OF, a["created_at"])
            assert it.get_by_test_id("alert-event").inner_text() == EVENT_IT[a["change_type"]]
            assert it.get_by_test_id("alert-recorded").locator("summary").inner_text() == "Testo registrato a quell'ora"
            assert it.get_by_test_id("alert-recorded-text").text_content() == a["summary"]  # kept verbatim as history
            rows.append((it.get_by_test_id("alert-time").inner_text(), a["change_type"]))
        seen[area] = rows
    assert {k for _, k in seen["banner"]} >= {"ENTRY_REOPENED", "ENTRY_UNVERIFIED"}
    # the earlier AVAILABLE text stays consultable as history, qualified as relative to that past event
    reopened = page.get_by_test_id("live-changes").locator("[data-change-type=ENTRY_REOPENED]").first
    reopened.get_by_test_id("alert-recorded").locator("summary").click()
    expect(reopened.get_by_test_id("alert-recorded-text")).to_be_visible()
    expect(reopened.get_by_test_id("alert-recorded-text")).to_contain_text("Entry still valid now")
    expect(reopened.get_by_test_id("alert-recorded-note")).to_contain_text("non indicano un ingresso utilizzabile adesso")
    expect(page.get_by_test_id("live-call")).to_have_attribute("data-state", call["entry_status"])
    reopened.get_by_test_id("alert-recorded").locator("summary").click()  # closed again: history only on request
    expect(reopened.get_by_test_id("alert-recorded-text")).to_be_hidden()
    return {"backend_entry_status": call["entry_status"],
            "panel_state": page.get_by_test_id("live-call").get_attribute("data-state"),
            "banner_title": page.get_by_test_id("live-alerts").locator(".notice-title").inner_text(), **seen}


def test_quote_interruption_reload_and_resume_follow_the_backend_state(database_url, artifact_root, tmp_path,
                                                                       browser, evidence_dir):
    import test_adviser_live_db as live_fakes

    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built")
    stack = Stack(database_url, artifact_root, tmp_path)
    facts: dict = {}
    try:
        clock = live_fakes.FakeClock(DAY2 + timedelta(hours=4, seconds=30))
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000})
        ctx.add_init_script(RECORDER)
        page = ctx.new_page()
        page.goto(f"{stack.base}/#market")
        expect(page.get_by_test_id("live-state")).to_contain_text("Stopped", timeout=15_000)
        page.get_by_test_id("live-start").click()
        expect(page.get_by_test_id("live-stop-button")).to_be_visible(timeout=15_000)
        # scripted public updates up to the minute after the issue: the last quote is received at 05:22:00.5
        th, ws = live_fakes._run_worker(database_url, clock, live_fakes.ws_messages(
            DAY2 + timedelta(hours=4), DAY2 + timedelta(hours=5, minutes=22)))
        expect(page.get_by_test_id("live-state")).to_contain_text("Warming up", timeout=120_000)
        ws.gate.set()
        panel = page.get_by_test_id("live-call")

        # 1. AVAILABLE, served by the API and shown with its admissible band
        wait_for(lambda: not ws.msgs and (_call(stack)[0] or {}).get("entry_status") == "AVAILABLE", timeout=120)
        c1, st1 = _call(stack)
        assert st1["state"] == "LIVE" and st1["current"] and c1["admissible_bounds"]
        expect(panel).to_have_attribute("data-state", "AVAILABLE", timeout=15_000)
        expect(page.get_by_test_id("live-admissible")).to_have_text(f"{c1['admissible_bounds'][0]} – {c1['admissible_bounds'][1]}")
        expect(page.locator(".band-admissible")).to_have_count(1)
        page.screenshot(path=str(evidence_dir / "continuity-1-available.png"), full_page=True)
        facts["1_available"] = {k: c1[k] for k in ("call_id", "revision", "entry_status", "entry_reasons", "admissible_bounds")}

        # 2. interruption: no further candle push or quote; only the worker's clock advances (8 s after the last quote)
        clock.set(DAY2 + timedelta(hours=5, minutes=22, seconds=8))
        wait_for(lambda: (_call(stack)[0] or {}).get("entry_status") == "UNVERIFIED", timeout=60)
        c2, st2 = _call(stack)
        assert c2["call_id"] == c1["call_id"] and c2["entry_reasons"] == ["QUOTE_STALE"] and c2["thesis_status"] == "ONGOING"
        assert c2["revision"] > c1["revision"] and st2["state"] == "LIVE" and st2["current"]  # session itself current
        assert c2.get("presentation") is None  # stale quote, not a non-current session
        expect(panel).to_have_attribute("data-state", "UNVERIFIED", timeout=15_000)
        expect(page.get_by_test_id("live-entry-consequence")).to_have_attribute("data-kind", "QUOTE")
        expect(page.get_by_test_id("live-admissible")).to_have_count(0)
        expect(page.locator(".band-admissible")).to_have_count(0)
        expect(page.get_by_test_id("live-entry")).not_to_contain_text("Ingresso disponibile")
        facts["2_interrupted"] = {k: c2[k] for k in ("call_id", "revision", "entry_status", "entry_reasons", "thesis_status")}
        band = list(c1["admissible_bounds"])
        facts["2_alerts_unverified"] = _check_historical_alerts(page, stack, band)

        # 3. reload during the interruption: the reloaded page never shows the old AVAILABLE
        clock.set(DAY2 + timedelta(hours=5, minutes=22, seconds=20))
        page.reload()
        expect(panel).to_have_attribute("data-state", "UNVERIFIED", timeout=15_000)
        page.wait_for_timeout(3500)  # at least two more cockpit polls while still interrupted
        states_after_reload = page.evaluate("() => window.__states")
        assert "AVAILABLE" not in states_after_reload, states_after_reload
        expect(page.get_by_test_id("live-admissible")).to_have_count(0)
        expect(page.locator(".band-admissible")).to_have_count(0)
        assert (_call(stack)[0] or {}).get("entry_status") == "UNVERIFIED"
        facts["3_after_reload"] = {
            "rendered_states": states_after_reload,
            "alerts": _check_historical_alerts(page, stack, band),
            "alerts_banner": page.get_by_test_id("live-alerts").inner_text(),
            "api_alerts": [(a["change_type"], a["created_at"], a["summary"]) for a in _call(stack)[1]["alerts"]]}
        page.screenshot(path=str(evidence_dir / "continuity-2-unverified-after-reload.png"), full_page=True)

        # 4. resume: the next scripted minute (quote 05:23:00.5, candle push 05:23:01); the backend decides
        rev = c2["revision"]
        ws.msgs.extend(live_fakes.ws_messages(DAY2 + timedelta(hours=5, minutes=22), DAY2 + timedelta(hours=5, minutes=23)))
        wait_for(lambda: not ws.msgs and (_call(stack)[0] or {}).get("revision", 0) > rev
                 and (_call(stack)[0] or {}).get("entry_status") != "UNVERIFIED", timeout=60)
        c4, st4 = _call(stack)
        assert c4["call_id"] == c1["call_id"] and st4["current"]
        assert (c4["entry_status"], c4["entry_reasons"]) == ("CLOSED", ["PRICE_OUTSIDE_STRUCTURAL_AREA"])
        expect(panel).to_have_attribute("data-state", c4["entry_status"], timeout=15_000)  # cockpit = backend
        expect(page.get_by_test_id("live-entry-reasons")).to_have_text("prezzo fuori dall'area d'ingresso")
        expect(page.get_by_test_id("live-admissible")).to_have_count(0)
        expect(page.locator(".band-admissible")).to_have_count(0)
        facts["4_resumed"] = {k: c4[k] for k in ("call_id", "revision", "entry_status", "entry_reasons", "thesis_status")}
        facts["4_alerts_closed"] = _check_historical_alerts(page, stack, band)
        page.screenshot(path=str(evidence_dir / "continuity-3-after-resume.png"), full_page=True)
        facts["rendered_states_since_reload"] = page.evaluate("() => window.__states")

        # 5. reload while CLOSED: the stored alerts stay history; the panel still equals the backend
        page.reload()
        expect(panel).to_have_attribute("data-state", "CLOSED", timeout=15_000)
        assert (_call(stack)[0] or {}).get("entry_status") == "CLOSED"
        facts["5_closed_after_reload"] = _check_historical_alerts(page, stack, band)
        expect(page.get_by_test_id("live-admissible")).to_have_count(0)
        assert "AVAILABLE" not in page.evaluate("() => window.__states")
        page.get_by_test_id("live-changes").locator("[data-change-type=ENTRY_REOPENED] summary").first.click()
        page.screenshot(path=str(evidence_dir / "continuity-4-closed-after-reload.png"), full_page=True)
        page.get_by_test_id("live-alerts").screenshot(path=str(evidence_dir / "alerts-banner-closed.png"))
        page.get_by_test_id("live-changes").screenshot(path=str(evidence_dir / "alerts-timeline-closed.png"))

        # 6. presentation only: a stored alert without a time shows "Orario non registrato", never the page's own clock
        def blank_times(route):
            resp = route.fetch()
            body = resp.json()
            for a in body.get("alerts", []):
                a["created_at"] = None
            route.fulfill(response=resp, json=body)

        page.route("**/api/adviser/live", blank_times)
        expect(page.get_by_test_id("live-alerts").get_by_test_id("alert-time").first).to_have_text(
            "Orario non registrato", timeout=15_000)
        times = page.get_by_test_id("historical-alert").get_by_test_id("alert-time").all_inner_texts()
        assert times and set(times) == {"Orario non registrato"}, times
        page.unroute("**/api/adviser/live")
        facts["6_missing_time"] = times

        page.get_by_test_id("live-stop-button").click()
        th.join(60)
        ctx.close()
        record(evidence_dir, "e2e-live-continuity", facts)
    finally:
        stack.stop()
