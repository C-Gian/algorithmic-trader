"""WP-012 bounded browser journey (tiny offline hand fixture ``contact_then_rearm``; mocked OKX only; no month replay).

Historical Workbench: prepare the pack once -> "Revised v0.3" completes (baseline) -> "Candidate v0.4" paced: paused
while its A scenario is "under observation; waiting for a new completed reaction" (anchor lost at 03:51), STEP past the
04:00 replacement until the follow view shows the new active anchor, resumed to completion -> the v0.4 result shows the
anchor diagnostics -> a third v0.4 run is cancelled (incomplete) -> read-only baseline v0.3 vs candidate v0.4
comparison (COMPARABLE, MP-003 limitation, anchor row) -> Copy comparison and Copy report equal their Markdown exports
-> readable at 1024 and 390 px without overflow; the live cockpit offers v0.4 before Start.
"""

from __future__ import annotations

import re
import sys
import threading

import httpx
import pytest
from playwright.sync_api import expect

from test_ui_smoke import ROOT, WEB_DIST, Stack, browser, evidence_dir, no_horizontal_overflow, record, wait_for  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

sys.path.insert(0, str(ROOT / "tests"))
import adviser4_fixtures as fx4  # noqa: E402
from adviser_db import EV_END, fake_from, write_presets  # noqa: E402
from adviser3_fixtures import DAY1  # noqa: E402
from okx_fake import client  # noqa: E402
from test_adviser_e2e import OFFENDERS  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402

N = int((EV_END - DAY1).total_seconds() // 60) + 365
_M = fx4.contact_then_rearm()
MINS = (_M + fx4.flat(max(0, N - len(_M)), _M[-1].c))[:N]
CONTACT_DISPATCH = 3 * (1440 + 3 * 60 + 51)  # first delivery available after the 03:51 dispatch (anchor lost)
REARM_DISPATCH = 3 * (1440 + 4 * 60)


@pytest.fixture
def bench4(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    write_presets(tmp_path, monkeypatch)
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake_from(MINS)
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-mp003", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(f, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack
    finally:
        stop.set()
        t.join(15)
        stack.stop()


PIN = {"v0.2": "MP-001 v0.2", "v0.3": "MP-002 v0.3", "v0.4": "MP-003 v0.4"}


def _start(page, method: str, speed: str = "0") -> str:
    page.get_by_test_id("run-type-adviser-input").check()
    page.get_by_test_id(f"method-{method}-input").check()
    expect(page.get_by_test_id("eval-method-pin")).to_have_text(PIN[method])
    page.get_by_test_id("eval-speed").select_option(speed)
    before = page.evaluate("() => window.location.hash")
    page.get_by_test_id("start-evaluation").click()
    page.wait_for_function(f"() => window.location.hash !== {before!r} && /backtest\\/ev=eval-/.test(window.location.hash)")
    return page.evaluate("() => window.location.hash.split('ev=')[1]")


def _applied(stack, rid) -> int:
    return stack.get(f"/api/observations/{rid}")["progress"]["applied_events"]


def test_owner_runs_v04_sees_anchor_observation_and_compares_with_v03(bench4, browser, evidence_dir):
    stack = bench4
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready", timeout=120_000)
    expect(page.get_by_test_id("method-v0.3")).to_contain_text("Technically accepted")
    expect(page.get_by_test_id("method-v0.4")).to_contain_text("Engineering review pending")
    expect(page.get_by_test_id("method-v0.4-purpose")).to_contain_text("invalidates only that reaction anchor")
    expect(page.get_by_test_id("method-v0.2-input")).to_be_checked()  # explicit default unchanged

    e3 = _start(page, "v0.3")
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)

    e4 = _start(page, "v0.4", speed="100")
    rid4 = stack.get(f"/api/evaluations/{e4}")["replay"]["replay_id"]
    wait_for(lambda: _applied(stack, rid4) >= CONTACT_DISPATCH - 120, timeout=180)
    httpx.post(f"{stack.base}/api/observations/{rid4}/speed", json={"speed": 1}, timeout=30).raise_for_status()
    wait_for(lambda: _applied(stack, rid4) >= CONTACT_DISPATCH + 2, timeout=240)
    page.get_by_test_id("obs-pause").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=20_000)
    prog = page.get_by_test_id("adviser-progress")
    expect(prog).to_contain_text("Scenario under observation; waiting for a new completed reaction", timeout=30_000)
    page.screenshot(path=str(evidence_dir / "60-mp003-observation-paused.png"), full_page=True)
    n = _applied(stack, rid4)
    for _ in range(REARM_DISPATCH - n + 3):  # STEP one delivery at a time past the 04:00 replacement
        page.get_by_test_id("obs-step").click()
        k = _applied(stack, rid4)
        wait_for(lambda k=k: _applied(stack, rid4) >= k + 1 or _applied(stack, rid4) > REARM_DISPATCH, timeout=30)
        if _applied(stack, rid4) > REARM_DISPATCH + 1:
            break
    expect(prog).to_contain_text("Active reaction anchor (anchor 2)", timeout=30_000)
    page.screenshot(path=str(evidence_dir / "61-mp003-new-anchor.png"), full_page=True)
    page.get_by_test_id("obs-speed").select_option("0")
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    expect(page.get_by_test_id("active-run")).to_contain_text("Candidate v0.4")
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=30_000)
    expect(page.get_by_test_id("adv-v4-anchors")).to_be_visible()
    expect(page.get_by_test_id("adv-v4-lost")).to_contain_text("1")
    expect(page.get_by_test_id("adv-v4-rearmed")).to_contain_text("1")
    expect(page.get_by_test_id("adv-v4-confirmed-after")).to_contain_text("1")
    md_report = httpx.get(f"{stack.base}/api/evaluations/{e4}/report.md", timeout=30).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    assert page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n") == md_report
    assert "Candidate v0.4 (MP-003" in md_report
    page.screenshot(path=str(evidence_dir / "62-mp003-v04-result.png"), full_page=True)

    ec = _start(page, "v0.4", speed="1")
    ridc = stack.get(f"/api/evaluations/{ec}")["replay"]["replay_id"]
    wait_for(lambda: _applied(stack, ridc) >= 2, timeout=90)
    page.get_by_test_id("obs-cancel").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("CANCELLED", timeout=60_000)

    evaluations_before = len(stack.get("/api/evaluations"))
    expect(page.get_by_test_id("compare-card")).to_be_visible(timeout=20_000)
    page.get_by_test_id("compare-a").select_option(e3)
    page.get_by_test_id("compare-b").select_option(ec)
    page.get_by_test_id("compare-run").click()
    expect(page.get_by_test_id("compare-verdict")).to_contain_text(re.compile("incomplete", re.I), timeout=30_000)
    page.get_by_test_id("compare-b").select_option(e4)
    page.get_by_test_id("compare-run").click()
    expect(page.get_by_test_id("compare-verdict")).to_have_text(re.compile("^comparable$", re.I), timeout=30_000)
    expect(page.get_by_test_id("compare-table")).to_contain_text("baseline v0.3")
    expect(page.get_by_test_id("compare-table")).to_contain_text("candidate v0.4")
    expect(page.get_by_test_id("compare-anchors")).to_contain_text("1 / 1 / 1")
    expect(page.get_by_test_id("compare-limitations")).to_contain_text("pre-confirmation anchor domain")
    md = httpx.get(f"{stack.base}/api/evaluations/compare/report.md", params={"a": e3, "b": e4}, timeout=30).text
    page.get_by_test_id("copy-comparison").click()
    expect(page.get_by_test_id("copy-comparison")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md and "baseline v0.3 (A) vs candidate v0.4 (B)" in copied
    assert len(stack.get("/api/evaluations")) == evaluations_before  # comparing launched nothing
    page.screenshot(path=str(evidence_dir / "63-mp003-comparison.png"), full_page=True)

    for size in ((1024, 800), (390, 844)):
        c2 = browser.new_context(viewport={"width": size[0], "height": size[1]})
        p2 = c2.new_page()
        p2.goto(f"{stack.base}/#backtest/ev={e4}")
        expect(p2.get_by_test_id("adv-v4-anchors")).to_be_visible(timeout=30_000)
        expect(p2.get_by_test_id("compare-card")).to_be_visible()
        p2.wait_for_timeout(400)
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        p2.screenshot(path=str(evidence_dir / f"64-mp003-workbench-{size[0]}.png"), full_page=True)
        p2.goto(f"{stack.base}/#market")
        sel = p2.get_by_test_id("live-method-select")
        expect(sel).to_be_visible(timeout=20_000)
        expect(sel).to_contain_text("Candidate v0.4")
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        c2.close()
    ctx.close()
    record(evidence_dir, "e2e-mp003-comparison", {"v03": e3, "v04": e4, "cancelled": ec})
