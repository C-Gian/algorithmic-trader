"""WP-013 bounded browser journey (tiny offline synthetic fixture; mocked OKX only; no month replay).

Historical Workbench with a registered preset that declares an EXPLICIT initialization: the pack panel shows the
evaluated period and the initialization separately (and says the initialization is not evaluated) -> Prepare ->
Ready -> the run setup says initialization and tail are not evaluated -> one continuous "Candidate v0.4" run across a
calendar-month boundary completes -> Copy report for chat equals the Markdown export and carries the context
attestation, launch pins and the reconciled total/monthly sections -> readable at 390 px without overflow.
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import timedelta

import httpx
import pytest
from playwright.sync_api import expect

from test_ui_smoke import ROOT, WEB_DIST, Stack, browser, evidence_dir, no_horizontal_overflow, record  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

sys.path.insert(0, str(ROOT / "tests"))
import adviser3_fixtures as f3  # noqa: E402
import adviser4_fixtures as fx4  # noqa: E402
from adviser_db import fake_from, presets_doc  # noqa: E402
from okx_fake import client  # noqa: E402

from algotrader.corpus import presets as ps  # noqa: E402
from algotrader.corpus.job import CorpusWorker  # noqa: E402

ST = f3.DAY1 - timedelta(minutes=270)
ES, EE = ST + timedelta(hours=24), ST + timedelta(hours=30)
N = 30 * 60 + 365
_M = f3.a3_return_long()
MINS = (_M + fx4.flat(max(0, N - len(_M)), _M[-1].c))[:N]


def _z(t) -> str:
    return t.isoformat().replace("+00:00", "Z")


@pytest.fixture
def bench13(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    doc = presets_doc(ev_start=ES, ev_end=EE)
    doc["fine_warmup_hours"] = 12
    doc["presets"][0].update({"preset_id": "continuous-fixture-v1", "label": "Continuous fixture (explicit init)",
                              "warmup": {"start": _z(ST), "end": _z(ES)}, "initialization": ps.INITIALIZATION_EXPLICIT})
    path = tmp_path / "presets.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PRESETS", str(path))
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake_from(MINS, start=ST)
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-wp013", poll_interval=0.2,
                          heartbeat_interval=0.3, client_factory=lambda base: client(f, base_url=base))
    t = threading.Thread(target=worker.run_forever, args=(stop.is_set,), daemon=True)
    t.start()
    try:
        yield stack
    finally:
        stop.set()
        t.join(15)
        stack.stop()


def test_owner_prepares_the_continuous_preset_runs_v04_once_and_copies_the_monthly_report(bench13, browser,
                                                                                          evidence_dir):
    stack = bench13
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    windows = card.get_by_test_id("pack-windows")
    expect(windows).to_contain_text("Initialization (context only, not evaluated)", timeout=15_000)
    expect(windows).to_contain_text("Evaluation (scored later)")
    expect(windows).not_to_contain_text("Warmup (not scored)")
    expect(card.get_by_test_id("pack-initialization-note")).to_contain_text("Nothing inside it is evaluated")
    expect(card.get_by_test_id("pack-initialization-note")).to_contain_text("no restart at month boundaries")
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready", timeout=120_000)
    page.screenshot(path=str(evidence_dir / "70-wp013-pack-initialization.png"), full_page=True)

    page.get_by_test_id("run-type-adviser-input").check()
    page.get_by_test_id("method-v0.4-input").check()
    expect(page.get_by_test_id("eval-method-pin")).to_have_text("MP-003 v0.4")
    expect(page.get_by_test_id("eval-pack-windows-note")).to_contain_text("initialization and tail are not evaluated")
    expect(page.get_by_test_id("eval-pack-windows-note")).to_contain_text("one continuous run")
    page.get_by_test_id("eval-speed").select_option("0")
    before = page.evaluate("() => window.location.hash")
    page.get_by_test_id("start-evaluation").click()
    page.wait_for_function(f"() => window.location.hash !== {before!r} && /backtest\\/ev=eval-/.test(window.location.hash)")
    eid = page.evaluate("() => window.location.hash.split('ev=')[1]")
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=30_000)

    md = httpx.get(f"{stack.base}/api/evaluations/{eid}/report.md", timeout=30).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md
    for s in ("Context at the evaluation start (initialization is not evaluated)", "### Launch pins",
              "PRIMARY entry delay 60 s", "Continuous run: total and monthly sections (one run, no monthly reset)",
              "| 2025-08 |", "| 2025-09 |", "Reconciliation total vs months: PASS", "not an account return",
              "context only, not evaluated"):
        assert s in copied, s
    rep = httpx.get(f"{stack.base}/api/evaluations/{eid}/report.json", timeout=30).json()["adviser"]
    assert rep["periods"]["months"]["2025-08"]["calls"]["resolved_after_period_end"] == 1
    page.screenshot(path=str(evidence_dir / "71-wp013-report.png"), full_page=True)

    phone = browser.new_context(viewport={"width": 390, "height": 844})
    pp = phone.new_page()
    pp.goto(f"{stack.base}/#backtest")
    expect(pp.get_by_test_id("pack-default").get_by_test_id("pack-windows")).to_contain_text("Initialization",
                                                                                           timeout=15_000)
    assert no_horizontal_overflow(pp)
    pp.screenshot(path=str(evidence_dir / "72-wp013-phone.png"), full_page=True)
