"""WP-008 end-to-end: Owner evaluation workbench (Backtest) with offline fixtures only.

Real API and observation-worker processes against a fresh database; the corpus
worker runs in-process with the captured-fixture OKX transport (no network). A
tiny test corpus plan (``ALGOTRADER_CORPUS_PLAN``) matches the 20-minute fixture.

Flow: open Backtest -> initial chunk unprepared -> Prepare -> visible progress ->
prepared -> launch observation evaluation -> real chart/progress -> pause/step ->
complete -> Copy report for chat + downloads identify observation-only mode ->
refresh restores state. Screenshots at 1440x900, 1920x1080 and 1024x768.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, expect

from test_ui_smoke import ROOT, WEB_DIST, Stack, browser, evidence_dir, no_horizontal_overflow, record, wait_for  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

sys.path.insert(0, str(ROOT / "tests"))
from okx_fake import FakeOkx, client  # noqa: E402
from test_corpus import TEST_PLAN  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402

# backend report text for observation-only runs (unchanged: existing terminal reports stay byte-stable)
NOT_CONNECTED = ("Professional adviser not connected yet. This run validates data/replay/product workflow only; "
                 "trade-call metrics are unavailable.")
# WP-009 UI wording for the Market replay run type (the adviser now exists as its own run type)
UI_MARKET_REPLAY_NOTICE = "Market replay: this run validates data/replay/product workflow only"


@pytest.fixture
def workbench(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(TEST_PLAN), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PLAN", str(plan))
    stack = Stack(database_url, artifact_root, tmp_path)
    fake = FakeOkx()

    def slow(family, page):  # slow enough for the Owner-visible PREPARING state
        time.sleep(0.8)
        return page

    fake.page_hook = slow
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(fake, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack, fake
    finally:
        stop.set()
        t.join(15)
        stack.stop()


def chunk_status(page: Page):
    return page.get_by_test_id("chunk-detail").get_by_test_id("chunk-status")


def test_owner_prepares_corpus_runs_observation_evaluation_and_copies_report(workbench, browser, evidence_dir):
    stack, fake = workbench
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True,
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(stack.base)
    page.get_by_test_id("nav-backtest").click()
    expect(page.get_by_test_id("page-backtest")).to_be_visible()
    expect(page.get_by_test_id("nav-backtest")).to_have_attribute("aria-current", "page")
    expect(page.get_by_test_id("nav-backtest")).to_contain_text("Historical Workbench")
    expect(page.get_by_test_id("page-backtest")).to_contain_text("Historical Workbench")
    # explicit run types: Market replay available; Adviser evaluation needs a prepared pack (none here); Deep per run
    expect(page.get_by_test_id("run-type-market-replay")).to_contain_text("Market replay — data and engine check")
    expect(page.get_by_test_id("run-type-adviser")).to_contain_text("Needs a pack")
    expect(page.get_by_test_id("run-type-adviser-input")).to_be_disabled()
    expect(page.get_by_test_id("run-type-deep-validation")).to_contain_text("Implemented")
    expect(page.get_by_test_id("run-type-deep-validation")).to_contain_text("canonical feed cache")
    expect(page.get_by_test_id("historical-mode")).to_contain_text("HISTORICAL MODE")
    expect(page.get_by_test_id("history-banner")).to_contain_text("OBSERVATION ONLY")
    expect(page.get_by_test_id("capability-corpus")).to_contain_text("up", timeout=10_000)

    # the single-month ledger is the earlier workflow, kept behind a labelled disclosure (R3: packs are primary)
    expect(page.get_by_test_id("pack-card")).to_be_visible()
    page.get_by_test_id("corpus-card-legacy").locator("summary").first.click()
    # 1-2. corpus: initial chunk unprepared, later chunk planned/locked
    expect(page.get_by_test_id("ledger-test-chunk")).to_have_attribute("data-status", "not_prepared")
    expect(page.get_by_test_id("ledger-test-locked")).to_have_attribute("data-status", "planned")
    page.get_by_test_id("ledger-test-locked").click()
    expect(chunk_status(page)).to_have_text("PLANNED · LOCKED")
    expect(page.get_by_test_id("prepare-chunk")).to_have_count(0)
    page.get_by_test_id("ledger-test-chunk").click()
    expect(chunk_status(page)).to_have_text("NOT PREPARED")
    expect(page.get_by_test_id("adviser-notice")).to_contain_text(UI_MARKET_REPLAY_NOTICE)
    expect(page.get_by_test_id("start-evaluation")).to_be_disabled()
    assert no_horizontal_overflow(page)
    page.screenshot(path=str(evidence_dir / "17-backtest-unprepared-1440.png"), full_page=True)

    # 3-4. Prepare via the (offline) corpus worker; progress is visible, then prepared
    page.get_by_test_id("prepare-chunk").click()
    expect(chunk_status(page)).to_have_text("PREPARING", timeout=10_000)
    expect(page.get_by_test_id("prep-job")).to_be_visible()
    expect(page.get_by_test_id("prep-status")).to_have_text("RUNNING", timeout=15_000)
    expect(page.get_by_test_id("prep-phase")).not_to_have_text("waiting for worker", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "18-backtest-preparing.png"), full_page=True)
    expect(chunk_status(page)).to_have_text("PREPARED", timeout=60_000)
    expect(page.get_by_test_id("prep-outcome")).to_contain_text("Downloaded from OKX public REST, verified and bound")
    expect(page.get_by_test_id("chunk-verification")).to_contain_text("verified")
    expect(page.get_by_test_id("chunk-plain")).to_contain_text("Ready")  # plain-language state of the month
    expect(page.get_by_test_id("storage-facts")).to_be_hidden()  # technical facts are behind "Data details"
    page.get_by_test_id("chunk-more").locator("summary").click()
    expect(page.get_by_test_id("storage-facts")).to_be_visible()
    expect(page.get_by_test_id("chunk-reuse")).to_contain_text("nothing is downloaded again")
    calls_after_prepare = len(fake.calls)
    assert calls_after_prepare > 0
    page.reload()  # the binding is durable state, not page state
    expect(chunk_status(page)).to_have_text("PREPARED", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "19-backtest-prepared.png"), full_page=True)

    # 5-7. launch an observation-only evaluation; real chart + progress; pause / step
    expect(page.get_by_test_id("eval-chunk")).to_have_value("test-chunk", timeout=10_000)
    page.get_by_test_id("eval-speed").select_option("1")  # slow enough to pause mid-run
    page.get_by_test_id("start-evaluation").click()
    expect(page.get_by_test_id("active-run")).to_be_visible()
    page.wait_for_function("() => /backtest\\/ev=eval-/.test(window.location.hash)")
    eid = page.evaluate("() => window.location.hash.split('ev=')[1]")
    ev = stack.get(f"/api/evaluations/{eid}")
    rid = ev["replay"]["replay_id"]
    expect(page.get_by_test_id("obs-real-badge")).to_contain_text("Real market evidence")
    expect(page.get_by_test_id("obs-availability")).to_contain_text("Modeled availability")
    # a diagnostic snapshot (never a result) is copyable while the run is still going
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "snapshot")
    wait_for(lambda: stack.get(f"/api/observations/{rid}")["progress"]["applied_events"] >= 3, timeout=30)
    expect(page.get_by_test_id("obs-op-timeline")).to_be_hidden()  # beginners see the 4-step summary first
    page.get_by_test_id("run-steps-detail").locator("summary").click()
    expect(page.get_by_test_id("obs-op-timeline")).to_be_visible()
    expect(page.get_by_test_id("phase-VERIFYING_SOURCE")).to_have_attribute("data-state", "done")
    expect(page.get_by_test_id("phase-REPLAYING")).to_have_attribute("data-state", "current")
    expect(page.get_by_test_id("obs-op-health")).to_contain_text("Progressing")
    expect(page.get_by_test_id("run-story-title")).to_have_text("Replaying market history")
    expect(page.get_by_test_id("activity")).to_contain_text("1 replay")  # visible from any page
    expect(page.get_by_test_id("obs-panel")).not_to_contain_text("ASSURANCE WARNING")  # pending checks are normal
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    snap = page.evaluate("() => navigator.clipboard.readText()")
    assert "DIAGNOSTIC SNAPSHOT" in snap and "IN_PROGRESS_SNAPSHOT" in snap and "captured" in snap
    expect(page.locator("[data-testid=market-chart] .candle").first).to_be_visible(timeout=10_000)
    page.get_by_test_id("obs-pause").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=10_000)
    before = stack.get(f"/api/observations/{rid}")["progress"]["applied_events"]
    page.get_by_test_id("obs-step").click()
    wait_for(lambda: stack.get(f"/api/observations/{rid}")["progress"]["applied_events"] == before + 1, timeout=15)
    expect(page.get_by_test_id("obs-cursor")).to_contain_text(f"{before + 1}/", timeout=10_000)
    expect(page.get_by_test_id("stage-run")).to_contain_text("paused")
    page.screenshot(path=str(evidence_dir / "20-backtest-run-paused.png"), full_page=True)

    # 8. complete at max pacing
    page.get_by_test_id("obs-speed").select_option("0")
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=60_000)
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=15_000)
    expect(page.get_by_test_id("report-verdict")).to_contain_text("workflow valid", ignore_case=True)
    expect(page.get_by_test_id("report-completion")).to_have_text("COMPLETE")
    # a finished run reads as finished everywhere: no lingering phase, three separate outcome facts
    expect(page.get_by_test_id("run-story-title")).to_have_text("Finished")
    expect(page.get_by_test_id("obs-op-phase")).to_have_text("All phases done")
    expect(page.get_by_test_id("obs-replay-progress-note")).not_to_contain_text("not finished")
    expect(page.get_by_test_id("stage-run")).to_contain_text("report ready")
    expect(page.get_by_test_id("fact-operation")).to_contain_text("Finished")
    expect(page.get_by_test_id("fact-checks")).to_contain_text("PASS")
    expect(page.get_by_test_id("fact-adviser")).to_contain_text("Not in this run")
    # R2: the temporal substrate is inspectable inside the run's details, labelled as infrastructure only
    temporal = page.get_by_test_id("run-temporal")
    temporal.locator("summary").click()
    expect(temporal).to_contain_text("temporal substrate only; no adviser")
    expect(temporal).to_contain_text("temporal.clock.modeled-complete-prefix.v1")
    expect(page.get_by_test_id("temporal-track").first).to_be_visible()
    expect(page.get_by_test_id("temporal-readiness")).to_contain_text("demo.trade.15m")
    expect(page.get_by_test_id("report-verdict")).to_contain_text("Data and engine check passed")
    expect(page.get_by_test_id("report-verdict")).not_to_contain_text("independent validation")
    expect(page.get_by_test_id("activity")).to_contain_text("Nothing running", timeout=10_000)
    caps = page.get_by_test_id("report-capabilities")
    expect(caps).to_contain_text("Call count")
    expect(caps).to_contain_text("UNAVAILABLE", ignore_case=True)
    expect(caps).to_contain_text("NOT IMPLEMENTED", ignore_case=True)  # unchanged backend report capability rows
    for word in ("BULLISH", "BEARISH", "LONG ", "SHORT "):
        expect(page.get_by_test_id("active-run")).not_to_contain_text(word)
    page.screenshot(path=str(evidence_dir / "21-backtest-completed-report-1440.png"), full_page=True)

    # 9-10. Copy report for chat + downloads identify observation-only mode
    md = httpx.get(f"{stack.base}/api/evaluations/{eid}/report.md", timeout=10).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    # the OS clipboard may normalize line endings (Windows: CRLF); the content must be identical
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md
    assert "OBSERVATION_ONLY_EVALUATION" in copied and NOT_CONNECTED in copied
    assert "| Call count | UNAVAILABLE |" in copied and "WORKFLOW_VALID" in copied
    assert "finished (last phase GENERATING_REPORT closed)" in copied and "phase **GENERATING_REPORT**" not in copied
    assert "independent validation passed" not in copied and "code version " in copied and "code unknown" not in copied
    with page.expect_download() as dl:
        page.get_by_test_id("download-md").click()
    assert Path(dl.value.path()).read_text(encoding="utf-8") == md
    assert dl.value.suggested_filename == f"{eid}-report.md"
    with page.expect_download() as dl:
        page.get_by_test_id("download-json").click()
    doc = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    assert doc["report_kind"] == "OBSERVATION_ONLY_EVALUATION" and doc["completion"] == "COMPLETE"
    assert doc["capabilities"]["call_count"] == {"label": "Call count", "status": "UNAVAILABLE", "value": None,
                                                 "reason": "no professional adviser connected yet"}

    # 11. refresh restores the evaluation and its report; the prepared chunk was reused, not redownloaded
    page.reload()
    expect(page.get_by_test_id("active-run")).to_be_visible()
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=15_000)
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED")
    assert len(fake.calls) == calls_after_prepare

    # 12. optional Deep validation: never automatic; explicit launch -> its own job, report and linked assurance
    expect(page.get_by_test_id("assurance-headline")).to_contain_text("no Deep validation of this run")
    expect(page.get_by_test_id("deep-none")).to_be_visible()
    manifest_before = httpx.get(f"{stack.base}/api/observations/{rid}/manifest", timeout=10).json()
    page.get_by_test_id("deep-launch").click()
    expect(page.get_by_test_id("deep-status")).to_have_text("COMPLETED", timeout=60_000)
    expect(page.get_by_test_id("deep-outcome")).to_contain_text("MATCH")
    expect(page.get_by_test_id("deep-comparisons")).to_contain_text("0 mismatch")
    page.get_by_test_id("deep-copy-report").click()
    expect(page.get_by_test_id("deep-copy-report")).to_contain_text("Copied")
    deep_md = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert "Deep validation report" in deep_md and "MATCH" in deep_md and rid in deep_md
    manifest_after = httpx.get(f"{stack.base}/api/observations/{rid}/manifest", timeout=10).json()
    assert manifest_after == manifest_before  # the run's records/artifacts never change
    expect(page.get_by_test_id("assurance-deep")).to_have_text("match", timeout=10_000)  # refreshed without a reload
    page.reload()
    expect(page.get_by_test_id("assurance-headline")).to_contain_text("Deep validation", timeout=10_000)
    expect(page.get_by_test_id("assurance-deep")).to_have_text("match")
    page.screenshot(path=str(evidence_dir / "24-backtest-deep-validation.png"), full_page=True)
    ctx.close()

    for (w, h), name in (((1920, 1080), "22-backtest-1920.png"), ((1024, 768), "23-backtest-1024.png")):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        page.goto(f"{stack.base}/#backtest/ev={eid}")
        expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=15_000)
        page.wait_for_timeout(400)
        assert no_horizontal_overflow(page), (w, h)
        page.screenshot(path=str(evidence_dir / name), full_page=True)
        ctx.close()
    record(evidence_dir, "e2e-backtest-workbench", {"evaluation_id": eid, "replay_id": rid,
                                                    "report_markdown_bytes": len(md.encode()),
                                                    "fake_okx_requests": calls_after_prepare})
