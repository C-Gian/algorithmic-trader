"""WP-014 essential browser journey (tiny offline hand fixture; mocked OKX only; no month replay).

Historical Workbench: prepare the pack once -> v0.5 is recognisable before Start (label, status, purpose, pin) ->
"Candidate v0.4" completes (baseline) -> "Candidate v0.5" paced: paused before the 04:02 reference at a committed cursor,
then exact STEP grants to a fixed delivery where its A scenario shows "return reference prepared; waiting for a local
recovery (not a call)" and no call -> resumed to completion -> the v0.5 result shows the MP-004 §7 counts -> Copy
report equals the Markdown export and carries the §7 table -> read-only baseline v0.4 vs candidate v0.5 comparison
(COMPARABLE, MP-004 limitation, response row) -> readable at 1024 and 390 px without overflow; the live cockpit offers
v0.5 before Start.
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
import adviser5_fixtures as fx5  # noqa: E402
from adviser_db import EV_END, fake_from, write_presets  # noqa: E402
from adviser3_fixtures import DAY1  # noqa: E402
from okx_fake import client  # noqa: E402
from test_adviser_e2e import OFFENDERS  # noqa: E402

from algotrader.corpus.job import CorpusWorker  # noqa: E402

N = int((EV_END - DAY1).total_seconds() // 60) + 365
_M = fx5.tape(*fx5.neutral(10), fx5.VALID)  # reference at 04:02, ten waiting minutes, recovery [04:12,04:13)
MINS = (_M + fx5.flat(max(0, N - len(_M)), _M[-1].c))[:N]
PREP_DISPATCH = 3 * (1440 + 4 * 60 + 2)  # first delivery available after the 04:02 dispatch (reference prepared)
APPROACH = PREP_DISPATCH - 450  # paced runs report a committed cursor that can trail the kernel (see test_mp003_e2e)
OBSERVE_AT = PREP_DISPATCH + 2
PIN = {"v0.4": "MP-003 v0.4", "v0.5": "MP-004 v0.5"}


@pytest.fixture
def bench5(database_url, artifact_root, tmp_path, monkeypatch):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    write_presets(tmp_path, monkeypatch)
    stack = Stack(database_url, artifact_root, tmp_path)
    f = fake_from(MINS)
    stop = threading.Event()
    worker = CorpusWorker(database_url, stack.data_root, worker_id="corpus:e2e-mp004", poll_interval=0.2,
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
    expect(page.get_by_test_id("eval-method-pin")).to_have_text(PIN[method])
    expect(page.get_by_test_id("start-evaluation")).to_contain_text(method)
    page.get_by_test_id("eval-speed").select_option(speed)
    before = page.evaluate("() => window.location.hash")
    page.get_by_test_id("start-evaluation").click()
    page.wait_for_function(f"() => window.location.hash !== {before!r} && /backtest\\/ev=eval-/.test(window.location.hash)")
    return page.evaluate("() => window.location.hash.split('ev=')[1]")


def _applied(stack, rid) -> int:
    return stack.get(f"/api/observations/{rid}")["progress"]["applied_events"]


def _status(stack, rid) -> str:
    return stack.get(f"/api/observations/{rid}")["status"]


def test_owner_runs_v05_sees_the_response_wait_and_compares_with_v04(bench5, browser, evidence_dir):
    stack = bench5
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(f"{stack.base}/#backtest")
    card = page.get_by_test_id("pack-default")
    card.get_by_test_id("pack-prepare").click()
    expect(card.get_by_test_id("pack-state")).to_have_text("Ready", timeout=120_000)
    # recognisable before Start
    expect(page.get_by_test_id("method-v0.5")).to_contain_text("Candidate v0.5 — RETURN waits for a local recovery")
    expect(page.get_by_test_id("method-v0.5")).to_contain_text("Engineering review pending")
    expect(page.get_by_test_id("method-v0.5-purpose")).to_contain_text("fixes one reference bar")
    expect(page.get_by_test_id("method-v0.2-input")).to_be_checked()  # explicit default unchanged

    e4 = _start(page, "v0.4")
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)

    e5 = _start(page, "v0.5", speed="100")
    rid5 = stack.get(f"/api/evaluations/{e5}")["replay"]["replay_id"]
    wait_for(lambda: _applied(stack, rid5) >= APPROACH, timeout=180)
    page.get_by_test_id("obs-pause").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=20_000)
    wait_for(lambda: _status(stack, rid5) == "paused", timeout=30)
    parked = _applied(stack, rid5)
    assert APPROACH <= parked < PREP_DISPATCH, (parked, PREP_DISPATCH)  # barrier: before the reference
    for _ in range(OBSERVE_AT - parked):  # exact STEP grants: one committed delivery each, no overshoot
        httpx.post(f"{stack.base}/api/observations/{rid5}/step", timeout=30).raise_for_status()
    wait_for(lambda: _status(stack, rid5) == "paused" and _applied(stack, rid5) == OBSERVE_AT, timeout=180)
    prog = page.get_by_test_id("adviser-progress")
    expect(prog).to_contain_text("return reference prepared; waiting for a local recovery (not a call)",
                                 timeout=30_000)
    expect(prog).to_contain_text("Call")
    assert stack.get(f"/api/observations/{rid5}")["adviser"]["committed"]["call"] is None  # waiting is not an entry
    page.screenshot(path=str(evidence_dir / "70-mp004-response-wait-paused.png"), full_page=True)
    page.get_by_test_id("obs-speed").select_option("0")
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=180_000)
    expect(page.get_by_test_id("active-run")).to_contain_text("Candidate v0.5")  # results bound to the pinned method
    expect(page.get_by_test_id("report-card")).to_have_attribute("data-state", "ready", timeout=30_000)
    expect(page.get_by_test_id("adv-v5-responses")).to_be_visible()
    expect(page.get_by_test_id("adv-v5-prepared")).to_contain_text("1 / 1")
    expect(page.get_by_test_id("adv-v5-recoveries")).to_contain_text("1")
    expect(page.get_by_test_id("adv-v5-table")).to_contain_text("Total")
    md_report = httpx.get(f"{stack.base}/api/evaluations/{e5}/report.md", timeout=30).text
    page.get_by_test_id("copy-report").click()
    expect(page.get_by_test_id("copy-report")).to_contain_text("Copied")
    assert page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n") == md_report
    assert "Candidate v0.5 (MP-004" in md_report and "### A RETURN response (MP-004 §7" in md_report
    assert "| Total | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0 |" in md_report
    page.screenshot(path=str(evidence_dir / "71-mp004-v05-result.png"), full_page=True)

    evaluations_before = len(stack.get("/api/evaluations"))
    expect(page.get_by_test_id("compare-card")).to_be_visible(timeout=20_000)
    page.get_by_test_id("compare-a").select_option(e4)
    page.get_by_test_id("compare-b").select_option(e5)
    page.get_by_test_id("compare-run").click()
    expect(page.get_by_test_id("compare-verdict")).to_have_text(re.compile("^comparable$", re.I), timeout=30_000)
    expect(page.get_by_test_id("compare-table")).to_contain_text("baseline v0.4")
    expect(page.get_by_test_id("compare-table")).to_contain_text("candidate v0.5")
    expect(page.get_by_test_id("compare-responses")).to_contain_text("1 · 1 · 0 · 1 · 0 · 1 · 0 · 0")
    expect(page.get_by_test_id("compare-limitations")).to_contain_text("only in the A RETURN child")
    md = httpx.get(f"{stack.base}/api/evaluations/compare/report.md", params={"a": e4, "b": e5}, timeout=30).text
    page.get_by_test_id("copy-comparison").click()
    expect(page.get_by_test_id("copy-comparison")).to_contain_text("Copied")
    copied = page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")
    assert copied == md and "baseline v0.4 (A) vs candidate v0.5 (B)" in copied
    assert len(stack.get("/api/evaluations")) == evaluations_before  # comparing launched nothing
    page.screenshot(path=str(evidence_dir / "72-mp004-comparison.png"), full_page=True)

    for size in ((1024, 800), (390, 844)):
        c2 = browser.new_context(viewport={"width": size[0], "height": size[1]})
        p2 = c2.new_page()
        p2.goto(f"{stack.base}/#backtest/ev={e5}")
        expect(p2.get_by_test_id("adv-v5-responses")).to_be_visible(timeout=30_000)
        expect(p2.get_by_test_id("compare-card")).to_be_visible()
        p2.wait_for_timeout(400)
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        p2.screenshot(path=str(evidence_dir / f"73-mp004-workbench-{size[0]}.png"), full_page=True)
        p2.goto(f"{stack.base}/#market")
        sel = p2.get_by_test_id("live-method-select")
        expect(sel).to_be_visible(timeout=20_000)
        expect(sel).to_contain_text("Candidate v0.5")
        assert no_horizontal_overflow(p2), (size, p2.evaluate(OFFENDERS))
        c2.close()
    ctx.close()
    record(evidence_dir, "e2e-mp004-comparison", {"v04": e4, "v05": e5})
