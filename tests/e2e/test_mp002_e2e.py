"""WP-011 bounded browser journey (tiny offline hand fixture; mocked OKX only; no historical/month replay).

Historical Workbench: prepare the pack once -> Adviser evaluation with "Original v0.2" -> completed -> a second
evaluation with "Revised v0.3 — confirmation then usable entry" on the SAME pack, paused / STEP / resumed -> the v0.3
result shows the waiting-for-a-usable-price funnel and its RETURN call -> a third v0.3 run is cancelled (incomplete)
-> read-only comparison of the two completed runs (COMPARABLE) and of a completed vs the cancelled run (INCOMPLETE)
-> Copy comparison for chat equals the Markdown export -> readable at 1024 and 390 px without overflow. The live
cockpit offers the method choice before Start.
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
from adviser3_fixtures import a3_return_long  # noqa: E402
from adviser_db import fake_from, write_presets  # noqa: E402
from okx_fake import client  # noqa: E402
from test_adviser_e2e import OFFENDERS  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402


@pytest.fixture
def bench3(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    write_presets(tmp_path, monkeypatch)
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake_from(a3_return_long(tail=520))
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-mp002", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(f, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack
    finally:
        stop.set()
        t.join(15)
        stack.stop()


def _start(page, method: str, speed: str = "0") -> str:
    page.get_by_test_id("run-type-adviser-input").check()
    page.get_by_test_id(f"method-{method}-input").check()
    expect(page.get_by_test_id("eval-method-pin")).to_have_text("MP-001 v0.2" if method == "v0.2" else "MP-002 v0.3")
    page.get_by_test_id("eval-speed").select_option(speed)
    before = page.evaluate("() => window.location.hash")
    page.get_by_test_id("start-evaluation").click()
    page.wait_for_function(f"() => window.location.hash !== {before!r} && /backtest\\/ev=eval-/.test(window.location.hash)")
    return page.evaluate("() => window.location.hash.split('ev=')[1]")


def test_owner_compares_original_and_revised_methods_on_the_same_pack(bench3, browser, evidence_dir):
    stack = bench3
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready", timeout=120_000)
    expect(page.get_by_test_id("method-choice")).to_contain_text("Original v0.2")
    expect(page.get_by_test_id("method-v0.3")).to_contain_text("Engineering review pending")
    expect(page.get_by_test_id("method-v0.2-input")).to_be_checked()  # explicit default: the baseline

    e2 = _start(page, "v0.2")
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    assert stack.get(f"/api/evaluations/{e2}")["method"]["method"] == "v0.2"

    e3 = _start(page, "v0.3", speed="1")
    rid3 = stack.get(f"/api/evaluations/{e3}")["replay"]["replay_id"]
    wait_for(lambda: stack.get(f"/api/observations/{rid3}")["progress"]["applied_events"] >= 3, timeout=90)
    page.get_by_test_id("obs-pause").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=20_000)
    n = stack.get(f"/api/observations/{rid3}")["progress"]["applied_events"]
    page.get_by_test_id("obs-step").click()
    wait_for(lambda: stack.get(f"/api/observations/{rid3}")["progress"]["applied_events"] == n + 1, timeout=30)
    page.get_by_test_id("obs-speed").select_option("0")
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    expect(page.get_by_test_id("active-run")).to_contain_text("Revised v0.3")
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=30_000)
    expect(page.get_by_test_id("adv-v3-funnel")).to_be_visible()
    expect(page.get_by_test_id("adv-v3-waits")).to_contain_text("1")
    expect(page.get_by_test_id("adv-v3-modes")).to_contain_text("A RETURN 1")
    expect(page.get_by_test_id("adv-v3-threshold")).to_contain_text("1 / 20")
    page.get_by_test_id("adv-call-row").first.click()
    expect(page.get_by_test_id("call-detail")).to_contain_text("LONG")
    page.screenshot(path=str(evidence_dir / "50-mp002-v03-result.png"), full_page=True)

    ec = _start(page, "v0.3", speed="1")
    ridc = stack.get(f"/api/evaluations/{ec}")["replay"]["replay_id"]
    wait_for(lambda: stack.get(f"/api/observations/{ridc}")["progress"]["applied_events"] >= 2, timeout=90)
    page.get_by_test_id("obs-cancel").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("CANCELLED", timeout=60_000)

    evaluations_before = len(stack.get("/api/evaluations"))
    cmp_card = page.get_by_test_id("compare-card")
    expect(cmp_card).to_be_visible(timeout=20_000)
    page.get_by_test_id("compare-a").select_option(e2)
    page.get_by_test_id("compare-b").select_option(ec)
    page.get_by_test_id("compare-run").click()
    expect(page.get_by_test_id("compare-verdict")).to_contain_text(re.compile("incomplete", re.I), timeout=30_000)
    page.get_by_test_id("compare-b").select_option(e3)
    page.get_by_test_id("compare-run").click()
    expect(page.get_by_test_id("compare-verdict")).to_have_text(re.compile("^comparable$", re.I), timeout=30_000)
    expect(page.get_by_test_id("compare-table")).to_contain_text("v0.3")
    expect(page.get_by_test_id("compare-limitations")).to_contain_text("cannot attribute any difference to RETURN alone")
    md = httpx.get(f"{stack.base}/api/evaluations/compare/report.md", params={"a": e2, "b": e3}, timeout=30).text
    page.get_by_test_id("copy-comparison").click()
    expect(page.get_by_test_id("copy-comparison")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md and "Comparability: COMPARABLE" in copied and "## Comparison limitations" in copied
    assert len(stack.get("/api/evaluations")) == evaluations_before  # comparing launched nothing
    page.screenshot(path=str(evidence_dir / "51-mp002-comparison.png"), full_page=True)

    for size in ((1024, 800), (390, 844)):
        c2 = browser.new_context(viewport={"width": size[0], "height": size[1]})
        p2 = c2.new_page()
        p2.goto(f"{stack.base}/#backtest/ev={e3}")
        expect(p2.get_by_test_id("adv-v3-funnel")).to_be_visible(timeout=30_000)
        expect(p2.get_by_test_id("compare-card")).to_be_visible()
        p2.wait_for_timeout(400)
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        p2.screenshot(path=str(evidence_dir / f"52-mp002-workbench-{size[0]}.png"), full_page=True)
        p2.goto(f"{stack.base}/#market")
        expect(p2.get_by_test_id("live-method-select")).to_be_visible(timeout=20_000)
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        c2.close()
    ctx.close()
    record(evidence_dir, "e2e-mp002-comparison", {"v02": e2, "v03": e3, "cancelled": ec})
