"""WP-015 minimal browser journey (tiny offline hand fixture; mocked OKX only; no month replay).

Historical Workbench: prepare the pack once -> v0.6 is recognisable before Start (label, status, purpose, pin) ->
"Candidate v0.5" and "Candidate v0.6" complete on the MP-005 H1 tape (``adviser6_fixtures.h1_economics``: the 04:02
reference is initially incompatible on the historical economics) -> the v0.6 result shows the entry attempt ended at
the reference as part of X (not an extra count), with the declared loss of C/R classifications -> Copy report equals
the Markdown export and carries the subset table -> read-only baseline v0.5 vs candidate v0.6 comparison (COMPARABLE,
MP-005 limitation, subset row) -> readable at 1024 and 390 px; the live cockpit offers v0.6 before Start.
"""

from __future__ import annotations

import re
import sys
import threading

import httpx
import pytest
from playwright.sync_api import expect

from test_ui_smoke import ROOT, WEB_DIST, Stack, browser, evidence_dir, no_horizontal_overflow, record  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

sys.path.insert(0, str(ROOT / "tests"))
import adviser6_fixtures as fx6  # noqa: E402
from adviser_db import EV_END, fake_from, write_presets  # noqa: E402
from adviser3_fixtures import DAY1  # noqa: E402
from okx_fake import client  # noqa: E402
from test_adviser_e2e import OFFENDERS  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402

N = int((EV_END - DAY1).total_seconds() // 60) + 365
_M = fx6.h1_economics()
MINS = (_M + fx6.flat(max(0, N - len(_M)), _M[-1].c))[:N]
PIN = {"v0.5": "MP-004 v0.5", "v0.6": "MP-005 v0.6"}


@pytest.fixture
def bench6(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    write_presets(tmp_path, monkeypatch)
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake_from(MINS)
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-mp005", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(f, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack
    finally:
        stop.set()
        t.join(15)
        stack.stop()


def _start(page, method: str) -> str:
    page.get_by_test_id("run-type-adviser-input").check()
    page.get_by_test_id(f"method-{method}-input").check()
    expect(page.get_by_test_id("eval-method-pin")).to_have_text(PIN[method])
    expect(page.get_by_test_id("start-evaluation")).to_contain_text(method)
    page.get_by_test_id("eval-speed").select_option("0")
    before = page.evaluate("() => window.location.hash")
    page.get_by_test_id("start-evaluation").click()
    page.wait_for_function(f"() => window.location.hash !== {before!r} && /backtest\\/ev=eval-/.test(window.location.hash)")
    return page.evaluate("() => window.location.hash.split('ev=')[1]")


def test_owner_selects_v06_reads_the_initial_incompatibility_and_compares_with_v05(bench6, browser, evidence_dir):
    stack = bench6
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready", timeout=120_000)
    # recognisable before Start
    expect(page.get_by_test_id("method-v0.6")).to_contain_text("Candidate v0.6 — RETURN reference ends early")
    expect(page.get_by_test_id("method-v0.6")).to_contain_text("Engineering review pending")
    expect(page.get_by_test_id("method-v0.6-purpose")).to_contain_text("the scenario is not invalidated")
    expect(page.get_by_test_id("method-v0.2-input")).to_be_checked()  # explicit default unchanged

    e5 = _start(page, "v0.5")
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    e6 = _start(page, "v0.6")
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    expect(page.get_by_test_id("active-run")).to_contain_text("Candidate v0.6")  # results bound to the pinned method
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=30_000)
    expect(page.get_by_test_id("adv-v5-responses")).to_contain_text("Candidate v0.6")
    expect(page.get_by_test_id("adv-v5-table")).to_contain_text("Total")
    expect(page.get_by_test_id("adv-v6-ended")).to_contain_text("1 / 1")
    expect(page.get_by_test_id("adv-v6-incompatibility")).to_contain_text("part of X, not an extra count")
    expect(page.get_by_test_id("adv-v6-table")).to_contain_text("yes")
    expect(page.get_by_test_id("adv-v6-notes")).to_contain_text("not invalidated")
    expect(page.get_by_test_id("adv-v6-notes")).to_contain_text("no later local classification")
    expect(page.get_by_test_id("adv-v3-funnel")).to_contain_text("earlier 20-owner criterion not applicable")
    md_report = httpx.get(f"{stack.base}/api/evaluations/{e6}/report.md", timeout=30).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    assert page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n") == md_report
    assert "Candidate v0.6 (MP-005" in md_report and "| Total | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |" in md_report
    assert "#### Initial response incompatibility (MP-005 §6; subset of X)" in md_report
    assert "| Total | 1 | 0 | 1 | 1 | 1 | 1.0000 | yes |" in md_report
    page.screenshot(path=str(evidence_dir / "80-mp005-v06-result.png"), full_page=True)

    evaluations_before = len(stack.get("/api/evaluations"))
    expect(page.get_by_test_id("compare-card")).to_be_visible(timeout=20_000)
    page.get_by_test_id("compare-a").select_option(e5)
    page.get_by_test_id("compare-b").select_option(e6)
    page.get_by_test_id("compare-run").click()
    expect(page.get_by_test_id("compare-verdict")).to_have_text(re.compile("^comparable$", re.I), timeout=30_000)
    expect(page.get_by_test_id("compare-table")).to_contain_text("candidate v0.6")
    expect(page.get_by_test_id("compare-responses")).to_contain_text("1 · 1 · 0 · 1 · 1 · 0 · 0 · 0")
    expect(page.get_by_test_id("compare-responses")).to_contain_text("1 · 1 · 0 · 0 · 0 · 0 · 1 · 0")
    expect(page.get_by_test_id("compare-initial-incompatibility")).to_contain_text("1 · corridor 0 · economics 1")
    expect(page.get_by_test_id("compare-limitations")).to_contain_text("lose the later C/R classification")
    md = httpx.get(f"{stack.base}/api/evaluations/compare/report.md", params={"a": e5, "b": e6}, timeout=30).text
    page.get_by_test_id("copy-comparison").click()
    expect(page.get_by_test_id("copy-comparison")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md and "baseline v0.5 (A) vs candidate v0.6 (B)" in copied
    assert len(stack.get("/api/evaluations")) == evaluations_before  # comparing launched nothing
    page.screenshot(path=str(evidence_dir / "81-mp005-comparison.png"), full_page=True)

    for size in ((1024, 800), (390, 844)):
        c2 = browser.new_context(viewport={"width": size[0], "height": size[1]})
        p2 = c2.new_page()
        p2.goto(f"{stack.base}/#backtest/ev={e6}")
        expect(p2.get_by_test_id("adv-v6-incompatibility")).to_be_visible(timeout=30_000)
        p2.wait_for_timeout(400)
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        p2.screenshot(path=str(evidence_dir / f"82-mp005-workbench-{size[0]}.png"), full_page=True)
        p2.goto(f"{stack.base}/#market")
        sel = p2.get_by_test_id("live-method-select")
        expect(sel).to_be_visible(timeout=20_000)
        expect(sel).to_contain_text("Candidate v0.6")
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        c2.close()
    ctx.close()
    record(evidence_dir, "e2e-mp005", {"v05": e5, "v06": e6})
