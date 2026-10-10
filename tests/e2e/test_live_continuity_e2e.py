"""Live entry-availability continuity (E2E; offline scripted fakes only, the same in-process live worker as
``test_adviser_e2e``): a call AVAILABLE -> the scripted public updates stop (no candle push, no ticker quote) while the
worker's clock advances -> the frozen quote-freshness rule makes the SAME call UNVERIFIED (QUOTE_STALE), served by the
real API and shown by the real cockpit, also after a page reload -> updates resume -> the cockpit follows whatever the
backend then establishes (here CLOSED, PRICE_OUTSIDE_STRUCTURAL_AREA: resuming never implies AVAILABLE). No stale
admissible band or AVAILABLE wording is ever presented as usable during the interruption."""

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
        page.screenshot(path=str(evidence_dir / "continuity-2-unverified-after-reload.png"), full_page=True)
        facts["3_after_reload"] = {
            "rendered_states": states_after_reload,
            # observation only (reported, not asserted): the unacknowledged-alerts banner and the timeline outside the
            # main panel keep earlier alert summaries, including ENTRY_REOPENED "Entry still valid now ..." with a range
            "alerts_banner": page.get_by_test_id("live-alerts").inner_text(),
            "api_alerts": [(a["change_type"], a["summary"]) for a in _call(stack)[1]["alerts"]]}

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
        page.screenshot(path=str(evidence_dir / "continuity-3-after-resume.png"), full_page=True)
        facts["4_resumed"] = {k: c4[k] for k in ("call_id", "revision", "entry_status", "entry_reasons", "thesis_status")}
        facts["rendered_states_since_reload"] = page.evaluate("() => window.__states")

        page.get_by_test_id("live-stop-button").click()
        th.join(60)
        ctx.close()
        record(evidence_dir, "e2e-live-continuity", facts)
    finally:
        stack.stop()
