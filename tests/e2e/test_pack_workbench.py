"""WP-008-R3 end-to-end: evaluation-pack preparation and a data and engine check in the Historical Workbench.

Real API and observation-worker processes against a fresh database; the corpus worker runs in-process with one shared
offline synthetic OKX fake (a network spy). A fixture presets file (``ALGOTRADER_CORPUS_PRESETS``) declares tiny
warmup/evaluation/tail windows. The evaluation interval is already local; only the warmup and tail slices are
downloaded. The fixture has a 3-minute trade/mark/index gap, so the pack is READY WITH LIMITATIONS and starting the
inspection run requires the explicit acknowledgement.

Flow: open the page (no network) -> Prepare -> progress -> Ready with limitations -> details (sources, coverage,
capabilities) -> copy the preparation report -> Prepare again (reused, zero requests) -> Start blocked until
acknowledged -> pause/resume -> finish -> data-coverage fact + Copy report for chat -> phone-width overflow check.
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
from okx_fake import client  # noqa: E402
from pack_fixtures import EV_END, EV_START, acquire, fake, write_presets  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402


@pytest.fixture
def packbench(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    write_presets(tmp_path, monkeypatch)
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake(gaps=((EV_START + timedelta(minutes=40), EV_START + timedelta(minutes=43)),))
    acquire(stack.data_root, f, EV_START, EV_END)  # the evaluation interval is already on this computer
    f.calls.clear()
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-pack", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(f, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack, f
    finally:
        stop.set()
        t.join(15)
        stack.stop()


def test_owner_prepares_a_pack_and_checks_it_with_acknowledged_limitations(packbench, browser, evidence_dir):
    stack, f = packbench
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True,
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    expect(card.get_by_test_id("pack-state")).to_have_text("Not prepared yet", timeout=15_000)
    expect(card.get_by_test_id("pack-plan")).to_contain_text("Already on this computer")
    expect(card.get_by_test_id("pack-plan")).to_contain_text("Needs download")
    expect(card.get_by_test_id("pack-windows")).to_contain_text("not scored")
    assert f.calls == []  # opening the page downloads nothing
    page.screenshot(path=str(evidence_dir / "30-pack-unprepared.png"), full_page=True)

    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-job")).to_be_visible(timeout=10_000)
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready with limitations", timeout=90_000)
    expect(card.get_by_test_id("pack-job-outcome")).to_contain_text("Prepared")
    expect(card.get_by_test_id("pack-limitations")).to_contain_text("WITH GAPS")
    downloads = len(f.calls)
    assert downloads > 0
    card.get_by_test_id("pack-details").locator("summary").click()
    expect(card.get_by_test_id("pack-sources")).to_contain_text("okx-btc-usdt-swap")
    expect(card.get_by_test_id("pack-coverage")).to_contain_text("Funding settlements")
    expect(card.get_by_test_id("pack-capabilities")).to_contain_text("NONE_UNKNOWN")
    expect(card.get_by_test_id("pack-capabilities")).to_contain_text("PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW")
    card.get_by_test_id("pack-copy-report").click()
    expect(card.get_by_test_id("pack-copy-report")).to_contain_text("Copied")
    prep_md = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert "Evaluation pack preparation" in prep_md and "Needs" not in prep_md.split("## Pack")[0][-1:]
    assert "Adviser metrics: UNAVAILABLE" in prep_md and "Warmup" in prep_md and "(unscored)" in prep_md
    page.screenshot(path=str(evidence_dir / "31-pack-ready-with-limitations.png"), full_page=True)

    # Prepare again: the verified pack is reused, nothing is downloaded
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-job-outcome")).to_contain_text("Already prepared", timeout=30_000)
    assert len(f.calls) == downloads

    # Step 2: a gap-containing pack needs the explicit acknowledgement
    expect(page.get_by_test_id("eval-source")).to_contain_text("pack", timeout=10_000)
    expect(page.get_by_test_id("eval-ack-notice")).to_be_visible()
    # WP-009: with a pack selected the default run type is the Adviser evaluation; this test checks the data/engine path
    expect(page.get_by_test_id("run-type-adviser-input")).to_be_checked()
    page.get_by_test_id("run-type-market-replay-input").check()
    expect(page.get_by_test_id("start-evaluation")).to_be_disabled()
    page.get_by_test_id("eval-ack").check()
    page.get_by_test_id("eval-speed").select_option("1")
    page.get_by_test_id("start-evaluation").click()
    expect(page.get_by_test_id("active-run")).to_be_visible()
    page.wait_for_function("() => /backtest\\/ev=eval-/.test(window.location.hash)")
    eid = page.evaluate("() => window.location.hash.split('ev=')[1]")
    rid = stack.get(f"/api/evaluations/{eid}")["replay"]["replay_id"]
    wait_for(lambda: stack.get(f"/api/observations/{rid}")["progress"]["applied_events"] >= 3, timeout=60)
    page.get_by_test_id("obs-pause").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=15_000)
    page.get_by_test_id("obs-speed").select_option("0")
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=120_000)
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=20_000)
    expect(page.get_by_test_id("fact-coverage")).to_contain_text("With source gaps")
    expect(page.get_by_test_id("fact-checks")).to_contain_text("PASS")
    expect(page.get_by_test_id("fact-adviser")).to_contain_text("Not in this run")
    md = httpx.get(f"{stack.base}/api/evaluations/{eid}/report.md", timeout=10).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md
    assert "## Evaluation pack (observation only; no adviser)" in copied and "limitations acknowledged" in copied
    assert "| Call count | UNAVAILABLE |" in copied and "Feed consumed: entirely" in copied
    for word in ("BULLISH", "BEARISH", "LONG ", "SHORT "):
        assert word not in copied
    page.screenshot(path=str(evidence_dir / "32-pack-run-completed.png"), full_page=True)
    ctx.close()

    phone = browser.new_context(viewport={"width": 390, "height": 844})
    p2 = phone.new_page()
    p2.goto(f"{stack.base}/#backtest/ev={eid}")
    expect(p2.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=20_000)
    p2.get_by_test_id("pack-default").get_by_test_id("pack-details").locator("summary").click()
    p2.wait_for_timeout(400)
    assert no_horizontal_overflow(p2)
    p2.screenshot(path=str(evidence_dir / "33-pack-phone-390.png"), full_page=True)
    phone.close()
    record(evidence_dir, "e2e-pack-workbench", {"evaluation_id": eid, "replay_id": rid, "okx_requests": downloads})
