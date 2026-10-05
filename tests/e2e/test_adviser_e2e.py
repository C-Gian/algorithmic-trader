"""WP-009 end-to-end browser journeys (tiny offline hand fixtures; mocked OKX only).

1. Historical Workbench: Prepare a pack (offline fake) -> Adviser evaluation (pinned method/profile, no parameters) ->
   pause / STEP / resume -> completed -> adviser facts, funnel, hypothetical-outcome labels -> click the call: scenario,
   revisions and the separately labelled hypothetical path -> Copy report for chat -> readable at 1024 and 390 px.
2. Market (Home): Start live adviser -> catch-up/warm-up -> LIVE -> view and a LONG call with entry/target/stop ->
   entry withdrawn as price leaves the admissible area -> terminal guidance -> Stop -> restart: the old thesis is
   UNASSESSABLE and no alert is repeated. A local in-process live worker uses scripted WebSocket/REST/ticker fakes.
"""

from __future__ import annotations

import sys
import threading
from datetime import timedelta

import httpx
import pytest
from playwright.sync_api import expect

from test_ui_smoke import ROOT, WEB_DIST, Stack, browser, evidence_dir, no_horizontal_overflow, record, wait_for  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

sys.path.insert(0, str(ROOT / "tests"))
from adviser_db import fake_from, write_presets  # noqa: E402

OFFENDERS = """() => { const w = document.documentElement.clientWidth; const out = [];
  const clipped = (el) => { for (let p = el.parentElement; p; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'hidden' || o === 'scroll') return true; }
    return false; };
  for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
    if (r.right > w + 1 && r.width > 0 && !clipped(el)) {
      const chain = []; for (let p = el; p && chain.length < 6; p = p.parentElement) chain.push(`${p.tagName}.${p.className}`);
      out.push(`${Math.round(r.right)} ${chain.join(' < ')}`); } }
  return out.slice(0, 6); }"""
from adviser_fixtures import DAY2, a_fixture  # noqa: E402
from okx_fake import client  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402


@pytest.fixture
def advbench(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    write_presets(tmp_path, monkeypatch)
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake_from(a_fixture())
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-adv", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(f, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack
    finally:
        stop.set()
        t.join(15)
        stack.stop()


def test_owner_runs_an_adviser_evaluation_and_inspects_its_call(advbench, browser, evidence_dir):
    stack = advbench
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready", timeout=120_000)
    expect(page.get_by_test_id("eval-source")).to_contain_text("pack", timeout=15_000)
    expect(page.get_by_test_id("run-type-adviser")).to_contain_text("Available")
    expect(page.get_by_test_id("run-type-adviser-input")).to_be_checked()
    expect(page.get_by_test_id("adviser-notice")).to_contain_text("hypothetical")
    expect(page.get_by_test_id("eval-adviser-pins")).to_contain_text("MP-001 v0.2")
    page.get_by_test_id("eval-speed").select_option("1")
    page.get_by_test_id("start-evaluation").click()
    expect(page.get_by_test_id("active-run")).to_be_visible()
    page.wait_for_function("() => /backtest\\/ev=eval-/.test(window.location.hash)")
    eid = page.evaluate("() => window.location.hash.split('ev=')[1]")
    rid = stack.get(f"/api/evaluations/{eid}")["replay"]["replay_id"]
    wait_for(lambda: stack.get(f"/api/observations/{rid}")["progress"]["applied_events"] >= 3, timeout=90)
    page.get_by_test_id("obs-pause").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=20_000)
    before = stack.get(f"/api/observations/{rid}")["progress"]["applied_events"]
    page.get_by_test_id("obs-step").click()
    wait_for(lambda: stack.get(f"/api/observations/{rid}")["progress"]["applied_events"] == before + 1, timeout=30)
    expect(page.get_by_test_id("adviser-progress")).to_be_visible()
    page.get_by_test_id("obs-speed").select_option("0")
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=30_000)
    expect(page.get_by_test_id("report-verdict")).to_contain_text("Adviser evaluation completed")
    expect(page.get_by_test_id("fact-checks")).to_contain_text("PASS")
    expect(page.get_by_test_id("fact-adviser")).to_contain_text("1 call")
    expect(page.get_by_test_id("adv-calls")).to_have_text("1")
    expect(page.get_by_test_id("adv-hypo-note")).to_contain_text("total net is unavailable")
    expect(page.get_by_test_id("adv-funnel")).to_contain_text("calls 1")
    # WP-009 correction: overlapping condition time, slot/priority exposure and staged room are labelled details
    page.get_by_test_id("adv-condition-time").locator("summary").click()
    expect(page.get_by_test_id("adv-condition-table")).to_contain_text("SLOT OCCUPIED")
    expect(page.get_by_test_id("adv-room-stages")).to_contain_text("A")
    page.get_by_test_id("adv-call-row").first.click()
    detail = page.get_by_test_id("call-detail")
    expect(detail).to_contain_text("LONG")
    expect(detail.get_by_test_id("call-revisions")).to_contain_text("Target reached")
    expect(detail.get_by_test_id("call-hypothetical")).to_contain_text("Hypothetical evaluation (separate; not a fill)")
    expect(detail.get_by_test_id("call-scenario")).to_contain_text("Market view at issue")
    expect(detail.get_by_test_id("call-chart")).to_be_visible(timeout=20_000)
    page.screenshot(path=str(evidence_dir / "40-adviser-evaluation-completed.png"), full_page=True)
    md = httpx.get(f"{stack.base}/api/evaluations/{eid}/report.md", timeout=20).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md
    assert "## Adviser evaluation (hypothetical; no orders, sizing or account)" in copied
    assert "**Calls: 1**" in copied and "PRIMARY" in copied and "total net UNAVAILABLE" in copied
    for size in ((1024, 800), (390, 844)):
        c2 = browser.new_context(viewport={"width": size[0], "height": size[1]})
        p2 = c2.new_page()
        p2.goto(f"{stack.base}/#backtest/ev={eid}")
        expect(p2.get_by_test_id("adviser-result")).to_be_visible(timeout=30_000)
        p2.get_by_test_id("adv-call-row").first.click()
        expect(p2.get_by_test_id("call-detail")).to_be_visible()
        p2.wait_for_timeout(400)
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        p2.screenshot(path=str(evidence_dir / f"41-adviser-result-{size[0]}.png"), full_page=True)
        c2.close()
    ctx.close()
    record(evidence_dir, "e2e-adviser-evaluation", {"evaluation_id": eid, "replay_id": rid})


def test_owner_starts_the_live_adviser_sees_a_call_and_restart_repeats_no_alert(database_url, artifact_root, tmp_path,
                                                                              browser, evidence_dir):
    import test_adviser_live_db as live_fakes

    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built")
    stack = Stack(database_url, artifact_root, tmp_path)
    try:
        clock = live_fakes.FakeClock(DAY2 + timedelta(hours=4, seconds=30))
        ctx = browser.new_context(viewport={"width": 1440, "height": 950}, permissions=["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        page.goto(f"{stack.base}/#market")
        expect(page.get_by_test_id("live-state")).to_contain_text("Stopped", timeout=15_000)
        expect(page.get_by_test_id("live-message")).to_contain_text("nothing is monitored")
        page.get_by_test_id("live-start").click()
        expect(page.get_by_test_id("live-stop-button")).to_be_visible(timeout=15_000)
        th, ws = live_fakes._run_worker(database_url, clock, live_fakes.ws_messages(
            DAY2 + timedelta(hours=4), DAY2 + timedelta(hours=8, minutes=30)))
        expect(page.get_by_test_id("live-state")).to_contain_text("Warming up", timeout=120_000)
        expect(page.get_by_test_id("live-direction")).to_be_visible()
        ws.gate.set()
        expect(page.get_by_test_id("live-call-direction")).to_have_text("LONG", timeout=120_000)
        expect(page.get_by_test_id("live-target")).to_contain_text("100798.5")
        expect(page.get_by_test_id("live-stop-guidance")).to_be_visible()
        expect(page.get_by_test_id("live-lenses")).to_contain_text("Structure & levels")
        expect(page.get_by_test_id("live-chart")).to_be_visible()
        page.screenshot(path=str(evidence_dir / "50-live-call.png"), full_page=True)
        # usable entry is withdrawn (price leaves the area, or the scripted once-a-minute quote ages past 5 s: one
        # ENTRY_UNVERIFIED alert per Director decision) while the thesis continues; later the target is hit
        wait_for(lambda: any(a["change_type"] in ("ENTRY_WITHDRAWN", "ENTRY_UNVERIFIED")
                             for a in stack.get("/api/adviser/live")["alerts"]), timeout=120)
        expect(page.get_by_test_id("live-no-trade")).to_be_visible(timeout=180_000)
        st = stack.get("/api/adviser/live")
        assert any(c["terminal"] == "TARGET_REACHED" for c in st["view"]["recent_calls"])
        page.get_by_test_id("copy-analysis").click()
        expect(page.get_by_test_id("copy-analysis")).to_contain_text("Copied")
        txt = page.evaluate("() => navigator.clipboard.readText()")
        assert "BTC adviser — current analysis" in txt and "No actionable trade now" in txt
        alerts = [a["alert_key"] for a in st["alerts"]]
        page.get_by_test_id("live-stop-button").click()
        th.join(60)
        expect(page.get_by_test_id("live-state")).to_contain_text("Stopped", timeout=30_000)
        # restart later: reconstruction only; nothing is re-alerted
        clock.set(DAY2 + timedelta(hours=9))
        page.get_by_test_id("live-start").click()
        expect(page.get_by_test_id("live-stop-button")).to_be_visible(timeout=15_000)  # queued before the one-shot worker
        th2, ws2 = live_fakes._run_worker(database_url, clock, [])
        ws2.gate.set()
        expect(page.get_by_test_id("live-state")).to_contain_text("Warming up", timeout=120_000)
        assert [a["alert_key"] for a in stack.get("/api/adviser/live")["alerts"]] == alerts
        page.get_by_test_id("live-stop-button").click()
        th2.join(60)
        for size in ((1024, 800), (390, 844)):
            c2 = browser.new_context(viewport={"width": size[0], "height": size[1]})
            p2 = c2.new_page()
            p2.goto(f"{stack.base}/#market")
            expect(p2.get_by_test_id("live-cockpit")).to_be_visible(timeout=15_000)
            p2.get_by_test_id("live-technical").locator("summary").click()
            p2.wait_for_timeout(300)
            assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
            p2.screenshot(path=str(evidence_dir / f"51-live-{size[0]}.png"), full_page=True)
            c2.close()
        ctx.close()
        record(evidence_dir, "e2e-live-adviser", {"alerts": alerts})
    finally:
        stack.stop()
