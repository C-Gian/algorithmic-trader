"""End-to-end smoke: browser UI -> run start -> worker process -> PostgreSQL -> UI result.

Starts the real API (uvicorn) and worker as separate OS processes against a
fresh database and drives the built web UI with Playwright/Chromium.

Requires the built UI (``npm --prefix web run build``) and
``uv run playwright install chromium``. Screenshots and a JSON summary are
written to ``ALGOTRADER_EVIDENCE_DIR`` (default: pytest tmp dir).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import httpx
import psycopg
import psycopg.rows
import pytest
from playwright.sync_api import Page, expect, sync_playwright

pytestmark = [pytest.mark.e2e, pytest.mark.db]

ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = ROOT / "web" / "dist"
LEASE_SECONDS = "2"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Stack:
    def __init__(self, database_url: str, artifact_root: Path, log_dir: Path, port: int | None = None) -> None:
        self.port = port or _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.env = {
            **os.environ,
            "ALGOTRADER_DATABASE_URL": database_url,
            "ALGOTRADER_ARTIFACT_ROOT": str(artifact_root),
            "ALGOTRADER_DATA_ROOT": str(log_dir / "data"),
            "ALGOTRADER_WEB_DIST": str(WEB_DIST),
            "PYTHONUNBUFFERED": "1",
        }
        self.log_dir = log_dir
        self.data_root = log_dir / "data"
        self.api = self._spawn("api", ["api", "--port", str(self.port)])
        self.worker: subprocess.Popen | None = None
        self.start_worker()
        # real-market observation-replay worker (separate process and capability)
        self.observer = self._spawn("observer", ["observe-worker", "--lease-seconds", LEASE_SECONDS,
                                                 "--poll-interval", "0.2"])
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{self.base}/api/health", timeout=1).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.2)
        raise RuntimeError("API did not start")

    def _spawn(self, name: str, args: list[str]) -> subprocess.Popen:
        log = open(self.log_dir / f"{name}-{time.monotonic_ns()}.log", "wb")
        return subprocess.Popen(
            [sys.executable, "-m", "algotrader.cli", *args], env=self.env, stdout=log, stderr=subprocess.STDOUT
        )

    def start_worker(self) -> None:
        self.worker = self._spawn("worker", ["worker", "--lease-seconds", LEASE_SECONDS, "--poll-interval", "0.2"])

    def stop(self) -> None:
        for proc in (self.observer, self.worker, self.api):
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait(10)

    def kill(self) -> list[int]:
        """Hard-kill worker and API processes (no graceful shutdown); returns exit codes."""
        codes = []
        for proc in (self.worker, self.api):
            proc.kill()
            codes.append(proc.wait(10))
        self.observer.kill()
        self.observer.wait(10)
        return codes

    def get(self, path: str):
        return httpx.get(f"{self.base}{path}", timeout=10).json()


@pytest.fixture
def evidence_dir(tmp_path: Path) -> Path:
    d = Path(os.environ.get("ALGOTRADER_EVIDENCE_DIR", tmp_path / "evidence"))
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def stack(database_url, artifact_root, tmp_path):
    if not (WEB_DIST / "index.html").is_file():
        pytest.fail("web UI not built: run `npm --prefix web ci && npm --prefix web run build`")
    s = Stack(database_url, artifact_root, tmp_path)
    try:
        yield s
    finally:
        s.stop()


@pytest.fixture
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            yield b
        finally:
            b.close()


def panel_status(page: Page):
    return page.get_by_test_id("run-panel").get_by_test_id("run-status")


def start_from_ui(page: Page, base: str, speed: str, fault: str = "none") -> str:
    page.goto(base + "/#replay/demo")  # Synthetic Demo mode of the Replay Lab (Market is the landing page)
    expect(page.get_by_test_id("demo-banner")).to_contain_text("DEMO / SYNTHETIC")
    page.get_by_test_id("speed").select_option(speed)
    page.get_by_test_id("fault").select_option(fault)
    page.get_by_test_id("start-run").click()
    expect(page.get_by_test_id("run-panel")).to_be_visible()
    page.wait_for_function("() => /run=run-/.test(window.location.hash)")
    return page.evaluate("() => window.location.hash.split('run=')[1]")


def record(evidence_dir: Path, name: str, data: dict) -> None:
    (evidence_dir / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_ui_run_survives_browser_close_and_completes(stack, browser, evidence_dir, reference_trace):
    ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = ctx.new_page()
    run_id = start_from_ui(page, stack.base, "20")  # 20 bars/s
    expect(page.get_by_test_id("sim-time")).not_to_have_text("—", timeout=15_000)
    page.wait_for_function(
        "() => Number(document.querySelector('[data-testid=progress]').textContent.split('/')[0]) >= 15",
        timeout=20_000,
    )
    expect(page.get_by_test_id("market-view")).to_contain_text("DEMO")
    page.screenshot(path=str(evidence_dir / "01-running.png"), full_page=True)
    ctx.close()  # browser closed mid-run: the worker keeps going

    time.sleep(1.5)
    mid = stack.get(f"/api/runs/{run_id}")
    assert mid["status"] in ("running", "completed")

    ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = ctx.new_page()
    page.goto(stack.base + "/#replay/demo")  # fresh browser, no run hash: reconstructs from backend
    expect(page.get_by_test_id("run-panel")).to_contain_text(run_id)
    expect(panel_status(page)).to_have_text("COMPLETED", timeout=30_000)
    expect(page.get_by_test_id("validation")).to_have_text("PASS", timeout=10_000)
    history = page.get_by_test_id("action-history")
    for action in ("LONG", "SHORT", "NO_TRADE", "REDUCE", "EXIT"):
        expect(history).to_contain_text(action)
    expect(history).to_contain_text("BLOCKED by risk: exposure_cap_1x")
    expect(history).to_contain_text("BLOCKED by risk: data_quality_for_new_exposure")
    page.screenshot(path=str(evidence_dir / "02-completed-after-reopen.png"), full_page=True)
    ctx.close()

    manifest = stack.get(f"/api/runs/{run_id}/manifest")
    assert manifest["semantic_trace_hash"] == reference_trace[0]
    record(evidence_dir, "e2e-browser-reopen", {
        "run_id": run_id, "status": manifest["status"], "replay_control": manifest["replay_control"],
        "semantic_trace_hash": manifest["semantic_trace_hash"], "reference_trace_hash": reference_trace[0],
        "validation": manifest["validation"], "attempts": manifest["attempts"],
    })


def test_ui_worker_crash_is_visible_and_recovers(stack, browser, evidence_dir, reference_trace):
    ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = ctx.new_page()
    run_id = start_from_ui(page, stack.base, "0", "crash_once")
    code = stack.worker.wait(30)
    assert code == 86  # the worker OS process really died mid-step
    expect(page.get_by_test_id("recovery-log")).to_contain_text("controlled_fault_injected", timeout=10_000)
    # lease (2 s) expires with no worker alive; the UI must surface it
    expect(page.get_by_test_id("run-panel")).to_contain_text("lease expired", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "03-worker-dead-lease-expired.png"), full_page=True)
    stuck = stack.get(f"/api/runs/{run_id}")
    assert stuck["status"] == "running" and stuck["lease_expired"] and stuck["progress"]["steps_done"] == 45

    stack.start_worker()  # supervisor restart (docker compose: restart policy)
    expect(panel_status(page)).to_have_text("COMPLETED", timeout=30_000)
    expect(page.get_by_test_id("recovery-log")).to_contain_text("lease_expired_reclaimed")
    expect(page.get_by_test_id("validation")).to_have_text("PASS", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "04-recovered-completed.png"), full_page=True)
    ctx.close()

    manifest = stack.get(f"/api/runs/{run_id}/manifest")
    fills = stack.get(f"/api/runs/{run_id}/events?kind=fill")
    assert manifest["semantic_trace_hash"] == reference_trace[0]
    assert manifest["attempts"] == 2
    assert len({f["payload"]["fill_id"] for f in fills}) == len(fills) == 8
    record(evidence_dir, "e2e-worker-crash-recovery", {
        "run_id": run_id, "worker_exit_code": code, "status": manifest["status"],
        "attempts": manifest["attempts"], "recovery_log": manifest["recovery_log"],
        "fills": len(fills), "unique_fill_ids": len({f["payload"]["fill_id"] for f in fills}),
        "semantic_trace_hash": manifest["semantic_trace_hash"], "reference_trace_hash": reference_trace[0],
    })


def test_ui_cancel_leaves_inspectable_artifacts(stack, browser, evidence_dir):
    ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = ctx.new_page()
    run_id = start_from_ui(page, stack.base, "4")
    page.wait_for_function(
        "() => Number(document.querySelector('[data-testid=progress]').textContent.split('/')[0]) >= 3",
        timeout=20_000,
    )
    page.get_by_test_id("cancel-run").click()
    expect(panel_status(page)).to_have_text("CANCELLED", timeout=15_000)
    expect(page.get_by_test_id("artifacts")).to_contain_text("decisions.parquet", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "05-cancelled-artifacts.png"), full_page=True)
    ctx.close()
    manifest = stack.get(f"/api/runs/{run_id}/manifest")
    assert manifest["status"] == "cancelled" and manifest["steps_processed"] < 120
    record(evidence_dir, "e2e-cancel", {
        "run_id": run_id, "status": manifest["status"], "steps_processed": manifest["steps_processed"],
        "artifacts": [a["name"] for a in manifest["artifacts"]], "validation": manifest["validation"],
    })


def wait_for(fn, timeout: float = 20.0, interval: float = 0.1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fn():
            return
        time.sleep(interval)
    raise AssertionError("condition not met in time")


def test_ui_pause_step_speed_resume_survive_browser_reconnect(stack, browser, evidence_dir, reference_trace):
    ctx = browser.new_context(viewport={"width": 1400, "height": 1200})
    page = ctx.new_page()
    run_id = start_from_ui(page, stack.base, "4")
    page.wait_for_function(
        "() => Number(document.querySelector('[data-testid=progress]').textContent.split('/')[0]) >= 5",
        timeout=20_000,
    )
    page.get_by_test_id("pause-run").click()
    expect(panel_status(page)).to_have_text("PAUSED", timeout=10_000)
    parked = stack.get(f"/api/runs/{run_id}")
    assert parked["status"] == "paused" and parked["lease_owner"] is None
    paused_at = parked["progress"]["steps_done"]
    events_at_pause = len(stack.get(f"/api/runs/{run_id}/events?limit=5000"))
    time.sleep(2.5)  # a paused run makes no progress (it would do ~10 bars at 4 bars/s)
    still = stack.get(f"/api/runs/{run_id}")
    assert still["progress"]["steps_done"] == paused_at and still["runtime_state"] == "paused"
    assert len(stack.get(f"/api/runs/{run_id}/events?limit=5000")) == events_at_pause
    expect(page.get_by_test_id("progress")).to_have_text(f"{paused_at}/120")
    expect(page.get_by_test_id("eta")).to_have_text("unavailable")
    expect(page.get_by_test_id("worker-health")).to_contain_text("1 alive")
    page.screenshot(path=str(evidence_dir / "06-paused.png"), full_page=True)
    ctx.close()  # browser closed while paused

    ctx = browser.new_context(viewport={"width": 1400, "height": 1200})
    page = ctx.new_page()
    page.goto(stack.base + "/#replay/demo")  # fresh browser (no run hash) reconstructs the paused run from the backend
    expect(page.get_by_test_id("run-panel")).to_contain_text(run_id)
    expect(panel_status(page)).to_have_text("PAUSED")
    expect(page.get_by_test_id("progress")).to_have_text(f"{paused_at}/120")

    page.get_by_test_id("step-run").click()

    def parked_after_step() -> bool:
        r = stack.get(f"/api/runs/{run_id}")
        return r["status"] == "paused" and r["progress"]["steps_done"] == paused_at + 1

    wait_for(parked_after_step)
    expect(page.get_by_test_id("progress")).to_have_text(f"{paused_at + 1}/120", timeout=10_000)
    expect(panel_status(page)).to_have_text("PAUSED")
    time.sleep(1.5)
    stepped = stack.get(f"/api/runs/{run_id}")
    assert stepped["progress"]["steps_done"] == paused_at + 1 and stepped["control"]["step_budget"] == 0
    step_events = [e for e in stack.get(f"/api/runs/{run_id}/events?limit=5000") if e["seq"] >= events_at_pause]
    assert {e["step"] for e in step_events} == {paused_at}  # exactly one input bar, several events
    page.get_by_test_id("run-speed").select_option("20")  # speed change while paused
    expect(page.get_by_test_id("speed-now")).to_have_text("20 bars/s", timeout=10_000)
    expect(page.get_by_test_id("control-log")).to_contain_text("step")
    page.screenshot(path=str(evidence_dir / "07-stepped-still-paused.png"), full_page=True)

    page.get_by_test_id("resume-run").click()
    expect(page.get_by_test_id("pause-run")).to_be_visible(timeout=10_000)
    page.get_by_test_id("run-speed").select_option("0")  # speed change while running
    expect(panel_status(page)).to_have_text("COMPLETED", timeout=30_000)
    expect(page.get_by_test_id("validation")).to_have_text("PASS", timeout=10_000)
    ctx.close()

    manifest = stack.get(f"/api/runs/{run_id}/manifest")
    fills = stack.get(f"/api/runs/{run_id}/events?kind=fill")
    assert manifest["semantic_trace_hash"] == reference_trace[0]
    assert len({f["payload"]["fill_id"] for f in fills}) == len(fills) == 8
    commands = [e["command"] for e in manifest["control_log"]]
    assert commands[:3] == ["start", "pause", "parked"] and "step" in commands and "resume" in commands
    record(evidence_dir, "e2e-pause-step-resume", {
        "run_id": run_id, "paused_at_step": paused_at, "events_at_pause": events_at_pause,
        "steps_after_single_step": stepped["progress"]["steps_done"],
        "events_emitted_by_single_step": len(step_events),
        "status": manifest["status"], "schema_version": manifest["schema_version"],
        "control_log": manifest["control_log"], "replay_control": manifest["replay_control"],
        "fills": len(fills), "semantic_trace_hash": manifest["semantic_trace_hash"],
        "reference_trace_hash": reference_trace[0],
    })


def test_full_api_and_worker_restart_preserves_run(stack, browser, evidence_dir, reference_trace,
                                                     database_url, artifact_root, tmp_path):
    ctx = browser.new_context(viewport={"width": 1400, "height": 1200})
    page = ctx.new_page()
    run_id = start_from_ui(page, stack.base, "20")
    page.wait_for_function(
        "() => Number(document.querySelector('[data-testid=progress]').textContent.split('/')[0]) >= 25",
        timeout=20_000,
    )
    ctx.close()
    exit_codes = stack.kill()  # API and worker die abruptly mid-run
    with psycopg.connect(database_url) as c:  # state left behind, read directly from PostgreSQL
        status, lease_owner, done = c.execute(
            "SELECT r.status, r.lease_owner, k.next_step FROM runs r JOIN run_checkpoints k USING (run_id) "
            "WHERE run_id = %s", (run_id,)
        ).fetchone()
        fills_before = [r[0] for r in c.execute(
            "SELECT payload->>'fill_id' FROM run_events WHERE run_id = %s AND kind = 'fill' ORDER BY seq", (run_id,)
        ).fetchall()]
    assert status == "running" and lease_owner is not None and 25 <= done < 120

    fresh = Stack(database_url, artifact_root, tmp_path, port=stack.port)  # fresh API + worker processes
    try:
        ctx = browser.new_context(viewport={"width": 1400, "height": 1200})
        page = ctx.new_page()
        page.goto(fresh.base + "/#replay/demo")  # fresh browser, no run hash
        expect(page.get_by_test_id("run-panel")).to_contain_text(run_id)
        expect(panel_status(page)).to_have_text("COMPLETED", timeout=45_000)
        expect(page.get_by_test_id("recovery-log")).to_contain_text("lease_expired_reclaimed")
        expect(page.get_by_test_id("validation")).to_have_text("PASS", timeout=10_000)
        page.screenshot(path=str(evidence_dir / "08-completed-after-full-restart.png"), full_page=True)
        ctx.close()

        manifest = fresh.get(f"/api/runs/{run_id}/manifest")
        fills = fresh.get(f"/api/runs/{run_id}/events?kind=fill")
        fill_ids = [f["payload"]["fill_id"] for f in fills]
        assert manifest["semantic_trace_hash"] == reference_trace[0]
        assert manifest["event_count"] == reference_trace[1]
        assert len(fill_ids) == len(set(fill_ids)) == 8
        assert fills_before == fill_ids[: len(fills_before)]
        assert manifest["attempts"] == 2 and manifest["status"] == "completed"
        record(evidence_dir, "e2e-full-restart", {
            "run_id": run_id, "killed_exit_codes": exit_codes, "steps_committed_at_kill": done,
            "fills_before_kill": len(fills_before), "fills_final": len(fill_ids),
            "unique_fill_ids": len(set(fill_ids)), "attempts": manifest["attempts"],
            "recovery_log": manifest["recovery_log"], "status": manifest["status"],
            "semantic_trace_hash": manifest["semantic_trace_hash"], "reference_trace_hash": reference_trace[0],
            "event_count": manifest["event_count"], "reference_event_count": reference_trace[1],
        })
    finally:
        fresh.stop()


def test_ui_data_view_shows_dataset_provenance_and_quality(stack, browser, evidence_dir):
    """Owner-facing Data view over fixture-derived datasets (offline; no OKX access in CI)."""
    sys.path.insert(0, str(ROOT / "tests"))
    from okx_fake import CONFIRMED_END, FIXTURE_END, FIXTURE_START, FakeOkx, client

    from algotrader.marketdata.dataset import acquire

    clean = acquire(client(FakeOkx()), stack.data_root, FIXTURE_START, CONFIRMED_END).manifest
    degraded = acquire(client(FakeOkx()), stack.data_root, FIXTURE_START, FIXTURE_END).manifest

    ctx = browser.new_context(viewport={"width": 1400, "height": 1400})
    page = ctx.new_page()
    page.goto(stack.base)
    page.get_by_test_id("nav-data").click()
    expect(page.get_by_test_id("dataset-list")).to_contain_text(clean.dataset_id)
    page.get_by_test_id("dataset-list").get_by_text(degraded.dataset_id).click()
    detail = page.get_by_test_id("dataset-detail")
    expect(page.get_by_test_id("dataset-id")).to_have_text(degraded.dataset_id)
    expect(detail.get_by_test_id("dataset-quality")).to_have_text("DEGRADED")
    expect(page.get_by_test_id("dataset-source")).to_contain_text("OKX · https://www.okx.com")
    expect(page.get_by_test_id("dataset-instrument")).to_have_text("BTC-USDT-SWAP")
    expect(page.get_by_test_id("dataset-schema")).to_have_text("algotrader.marketdata.v1")
    expect(page.get_by_test_id("dataset-requested")).to_contain_text("2026-09-30 07:50:00 UTC")
    families = page.get_by_test_id("dataset-families")
    expect(families).to_contain_text("trade_candles_1m")
    expect(families).to_contain_text("funding_rates")
    expect(page.get_by_test_id("dataset-findings")).to_contain_text("incomplete_candle_rejected")
    expect(page.get_by_test_id("dataset-findings")).to_contain_text("missing_intervals")
    expect(detail).not_to_contain_text("1x exposure cap")  # stale product wording removed
    expect(detail).to_contain_text("venue metadata only")
    page.get_by_test_id("dataset-verify").click()
    expect(page.get_by_test_id("dataset-verify-result")).to_contain_text("OK", timeout=10_000)
    expect(page.get_by_test_id("dataset-provenance")).to_contain_text("request_log.jsonl")
    page.screenshot(path=str(evidence_dir / "09-data-view-degraded-dataset.png"), full_page=True)
    page.get_by_test_id("dataset-list").get_by_text(clean.dataset_id).click()
    expect(detail.get_by_test_id("dataset-quality")).to_have_text("CLEAN")
    page.screenshot(path=str(evidence_dir / "10-data-view-clean-dataset.png"), full_page=True)
    ctx.close()
    record(evidence_dir, "e2e-data-view", {
        "note": "fixture-derived datasets (captured OKX responses served offline); not live data",
        "clean": {"dataset_id": clean.dataset_id, "quality": clean.quality_status},
        "degraded": {"dataset_id": degraded.dataset_id, "quality": degraded.quality_status},
        "datasets_api": stack.get("/api/datasets")["datasets"],
    })


def test_ui_public_recorder_start_stop_and_completed_session(stack, browser, evidence_dir, database_url):
    """Recorder panel: Owner start/stop + a completed offline-recorded session (fake OKX network, no live access)."""
    sys.path.insert(0, str(ROOT / "tests"))
    import threading as _threading

    from recorder_fake import BUSINESS as FAKE_BUSINESS, ENDPOINTS as FAKE_EP, PUBLIC as FAKE_PUBLIC
    from test_recorder_job import fake_worker

    from algotrader.recorder import job as recjob

    with psycopg.connect(database_url, row_factory=psycopg.rows.dict_row) as c:
        sid = recjob.create_session(c, timedelta(minutes=30), FAKE_EP)
    worker, net = fake_worker(database_url, stack.data_root)
    t = _threading.Thread(target=worker.run_once)
    t.start()
    wait_for(lambda: net.done, timeout=30)
    with psycopg.connect(database_url, row_factory=psycopg.rows.dict_row) as c:
        recjob.stop_session(c, sid)
    t.join(30)

    ctx = browser.new_context(viewport={"width": 1400, "height": 1300})
    page = ctx.new_page()
    page.goto(stack.base)
    page.get_by_test_id("nav-recorder").click()  # first-class destination
    expect(page.get_by_test_id("page-recorder")).to_be_visible()
    panel = page.get_by_test_id("recorder-panel")
    expect(panel).to_contain_text("Public market evidence collection — no trading")
    done = page.get_by_test_id(f"recorder-session-{sid}")
    expect(done.get_by_test_id("recorder-status")).to_have_text("CLEAN", timeout=15_000)
    report = done.get_by_test_id("recorder-report")
    trade_row = report.get_by_test_id("report-row-candle1m:BTC-USDT-SWAP")
    expect(trade_row.get_by_test_id("completed-bars")).to_have_text("2", timeout=15_000)
    expect(report).to_contain_text("client-observed, not exchange publication")
    page.reload()  # refresh on the section deep link returns to the Recorder
    expect(page.get_by_test_id("page-recorder")).to_be_visible()
    # Owner starts a session from the browser; no recorder worker runs in this CI stack (no live network),
    # so it stays queued until stopped -> cancelled.
    page.get_by_test_id("recorder-duration").select_option("30")
    page.get_by_test_id("recorder-start").click()
    queued = page.locator("[data-testid^=recorder-session-]").first
    expect(queued.get_by_test_id("recorder-status")).to_have_text("QUEUED", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "11-recorder-panel.png"), full_page=True)
    queued.get_by_test_id("recorder-stop").click()
    expect(queued.get_by_test_id("recorder-status")).to_have_text("CANCELLED", timeout=10_000)
    ctx.close()
    sessions = stack.get("/api/recorder/sessions")["sessions"]
    record(evidence_dir, "e2e-recorder", {
        "note": "offline fake OKX transports built from captured public messages; not live data",
        "completed_session": stack.get(f"/api/recorder/sessions/{sid}")["report"],
        "statuses": [(s["session_id"], s["status"]) for s in sessions],
    })


COCKPIT_AREAS = ("live-direction", "live-call", "live-price", "live-changes", "live-technical")
SECTIONS = {"market": "page-overview", "backtest": "page-backtest", "replay": "page-replay", "data": "page-data",
            "recorder": "page-recorder"}


def no_horizontal_overflow(page: Page) -> bool:
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_shell_market_overview_is_default_honest_and_navigable(stack, browser, evidence_dir):
    """Market (Home) is the landing page: the live adviser cockpit honestly states it is stopped (nothing monitored,
    no current assessment) and never shows synthetic Replay Lab output; every destination is reachable,
    refresh-stable and free of page overflow."""
    run_id = httpx.post(f"{stack.base}/api/runs", json={"speed": 0}, timeout=10).json()["run_id"]
    wait_for(lambda: stack.get(f"/api/runs/{run_id}")["status"] == "completed", timeout=30)
    latest = stack.get(f"/api/runs/{run_id}/snapshot")["latest"]
    synthetic_texts = [run_id, latest["decision"]["reason"], latest["market_view"]["summary"]]

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(stack.base)
    overview = page.get_by_test_id("page-overview")
    expect(overview).to_be_visible()
    expect(page.get_by_test_id("nav-market")).to_have_attribute("aria-current", "page")
    expect(page.get_by_test_id("live-state")).to_contain_text("Stopped", timeout=15_000)
    expect(page.get_by_test_id("live-message")).to_contain_text("nothing is monitored")
    expect(page.get_by_test_id("live-start")).to_be_visible()
    for area in COCKPIT_AREAS:
        expect(page.get_by_test_id(area)).to_be_visible()
    expect(page.get_by_test_id("live-call")).to_contain_text("Nessuna valutazione in corso")
    expect(page.get_by_test_id("live-expected")).to_have_text("Non disponibile")
    # real readiness is shown; synthetic output is not
    expect(page.get_by_test_id("overview-run-workers")).to_have_text("1", timeout=10_000)
    expect(page.get_by_test_id("readiness")).to_contain_text("Integrated adviser")
    for text in synthetic_texts:
        expect(overview).not_to_contain_text(text)
    for testid in ("permitted-action", "view-bias", "demo-banner", "run-panel", "position"):
        expect(page.get_by_test_id(testid)).to_have_count(0)
    for word in ("BULLISH", "BEARISH"):
        expect(overview).not_to_contain_text(word)
    assert no_horizontal_overflow(page)
    page.screenshot(path=str(evidence_dir / "12-market-overview-1440.png"), full_page=True)

    for section, testid in SECTIONS.items():
        page.get_by_test_id(f"nav-{section}").click()
        expect(page.get_by_test_id(testid)).to_be_visible()
        expect(page.get_by_test_id(f"nav-{section}")).to_have_attribute("aria-current", "page")
        page.wait_for_timeout(300)
        assert no_horizontal_overflow(page), section
    page.get_by_test_id("nav-replay").click()
    expect(page.get_by_test_id("market-replay")).to_be_visible()  # real Market Replay is the primary mode
    expect(page.get_by_test_id("mode-market")).to_have_attribute("aria-selected", "true")
    page.get_by_test_id("mode-demo").click()
    expect(page.get_by_test_id("demo-banner")).to_contain_text("DEMO / SYNTHETIC")
    expect(page.get_by_test_id("run-panel")).to_contain_text(run_id)
    expect(page.get_by_test_id("market-replay")).to_have_count(0)
    page.get_by_test_id("nav-data").click()
    page.reload()  # section deep link survives refresh
    expect(page.get_by_test_id("page-data")).to_be_visible()
    ctx.close()

    ctx = browser.new_context(viewport={"width": 1024, "height": 768})  # narrower desktop / tablet
    page = ctx.new_page()
    for section, testid in SECTIONS.items():
        page.goto(f"{stack.base}/#{section}")
        expect(page.get_by_test_id(testid)).to_be_visible()
        page.wait_for_timeout(300)
        assert no_horizontal_overflow(page), section
    page.goto(f"{stack.base}/#run={run_id}")  # legacy run deep link still opens the Replay Lab run
    expect(page.get_by_test_id("run-panel")).to_contain_text(run_id)
    page.screenshot(path=str(evidence_dir / "13-replay-lab-1024.png"), full_page=True)
    ctx.close()
    record(evidence_dir, "e2e-shell-overview", {"synthetic_run": run_id, "cockpit_areas": list(COCKPIT_AREAS),
                                                "sections": list(SECTIONS)})


def obs(stack, rid: str) -> dict:
    return stack.get(f"/api/observations/{rid}")


def test_ui_market_replay_dataset_and_recording_observation_only(stack, browser, evidence_dir):
    """Real-market observation replay from the browser (offline fixtures): launch, REAL/MODELED labelling,
    pause, one-event step, refresh, resume, completion, channel state, artifacts, RECORDED recording replay,
    and strict separation from the synthetic DEMO."""
    sys.path.insert(0, str(ROOT / "tests"))
    from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client
    from recorder_fake import BUSINESS as FB, PUBLIC as FP, captured_script, record_session

    from algotrader.marketdata.dataset import acquire
    from algotrader.recorder.journal import finalize

    import threading as _threading

    ds = acquire(client(FakeOkx()), stack.data_root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    made: list = []  # record_session runs its own asyncio loop: keep it off Playwright's (sync API) thread
    t = _threading.Thread(target=lambda: made.append(record_session(
        stack.data_root, {FP: [captured_script("public")], FB: [captured_script("business")]}, session_id="rec-e2e")))
    t.start()
    t.join(60)
    finalize(made[0][0], "e2e fixture", False, "test-host", 1, None)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(stack.base)
    page.get_by_test_id("nav-replay").click()
    expect(page.get_by_test_id("market-replay")).to_be_visible()
    expect(page.get_by_test_id("real-banner")).to_contain_text("REAL MARKET EVIDENCE")
    page.get_by_test_id("obs-kind-dataset").click()
    page.get_by_test_id("obs-source").select_option(ds)
    expect(page.get_by_test_id("obs-preflight-availability")).to_contain_text("Modeled availability", timeout=10_000)
    expect(page.get_by_test_id("obs-preflight")).to_contain_text("not measured publication timing")
    page.get_by_test_id("obs-start-speed").select_option("1")  # 1 event/s: slow enough to pause mid-replay
    page.get_by_test_id("obs-start").click()
    panel = page.get_by_test_id("obs-panel")
    expect(panel).to_be_visible()
    page.wait_for_function("() => /obs=obs-/.test(window.location.hash)")
    rid = page.evaluate("() => window.location.hash.split('obs=')[1]")
    expect(page.get_by_test_id("obs-real-badge")).to_contain_text("Real market evidence")
    expect(page.get_by_test_id("obs-availability")).to_contain_text("Modeled availability")
    expect(page.get_by_test_id("obs-availability-label")).to_contain_text("MODELED")
    expect(page.get_by_test_id("obs-availability-label")).to_contain_text("not measured publication timing")
    expect(page.get_by_test_id("intelligence-boundary")).to_contain_text(
        "Professional interpretation and LONG/SHORT/NO_TRADE are not connected yet")
    wait_for(lambda: obs(stack, rid)["progress"]["applied_events"] >= 2, timeout=20)

    page.get_by_test_id("obs-pause").click()
    expect(panel.get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=10_000)
    paused = obs(stack, rid)
    at, total = paused["progress"]["applied_events"], paused["progress"]["total_events"]
    assert paused["status"] == "paused" and paused["lease_owner"] is None
    time.sleep(2.0)  # a parked replay applies nothing
    assert obs(stack, rid)["progress"]["applied_events"] == at
    expect(page.get_by_test_id("obs-cursor")).to_have_text(f"{at}/{total}")

    page.get_by_test_id("obs-step").click()  # exactly one feed delivery

    def stepped() -> bool:
        r = obs(stack, rid)
        return r["status"] == "paused" and r["progress"]["applied_events"] == at + 1

    wait_for(stepped)
    expect(page.get_by_test_id("obs-cursor")).to_have_text(f"{at + 1}/{total}", timeout=10_000)
    deliveries = stack.get(f"/api/observations/{rid}/deliveries?latest=1000")
    assert [d["seq"] for d in deliveries] == list(range(at + 1))
    page.screenshot(path=str(evidence_dir / "14-market-replay-paused-stepped.png"), full_page=True)

    page.reload()  # refresh / reconnect: state reconstructed from the backend
    expect(page.get_by_test_id("obs-panel").get_by_test_id("obs-status")).to_have_text("PAUSED", timeout=10_000)
    expect(page.get_by_test_id("obs-cursor")).to_have_text(f"{at + 1}/{total}")
    expect(page.get_by_test_id("observable-state")).to_be_visible()

    page.get_by_test_id("obs-speed").select_option("0")  # pacing change (max) while paused
    expect(page.get_by_test_id("obs-speed-now")).to_have_text("max", timeout=10_000)
    page.get_by_test_id("obs-resume").click()
    expect(page.get_by_test_id("obs-panel").get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=30_000)
    expect(page.get_by_test_id("obs-validation")).to_have_text("PASS", timeout=10_000)
    expect(page.get_by_test_id("obs-cursor")).to_have_text(f"{total}/{total}")

    # per-channel observable state: explicit roles, never substituted
    trade = page.get_by_test_id("channel-trade_bar_1m")
    expect(trade).to_contain_text("Traded price")
    expect(trade.get_by_test_id("channel-condition")).not_to_have_text("NEVER SEEN")
    expect(page.get_by_test_id("channel-mark_bar_1m")).to_contain_text("not an execution price")
    expect(page.get_by_test_id("channel-index_bar_1m")).to_contain_text("not an execution price")
    expect(page.get_by_test_id("channel-funding_settlement")).to_contain_text("Settled funding")
    expect(page.get_by_test_id("delivery-timeline").get_by_test_id("delivery-row").first).to_be_visible()
    expect(page.get_by_test_id("market-chart")).to_be_visible()
    expect(page.get_by_test_id("obs-artifacts")).to_contain_text("ranges.jsonl")  # streaming: compact committed ranges
    expect(page.get_by_test_id("obs-artifacts")).to_contain_text("engine.json")
    expect(page.get_by_test_id("obs-artifacts")).not_to_contain_text("deliveries.jsonl")
    expect(page.get_by_test_id("obs-artifacts")).to_contain_text("final_snapshot.json")
    assert no_horizontal_overflow(page)
    page.screenshot(path=str(evidence_dir / "15-market-replay-completed-dataset.png"), full_page=True)
    manifest = stack.get(f"/api/observations/{rid}/manifest")
    assert manifest["validation"]["passed"] and manifest["applied_events"] == manifest["total_events"] == total
    commands = [e["command"] for e in manifest["control_log"]]
    assert commands[0] == "start" and "pause" in commands and "step" in commands and "resume" in commands
    quality = [d for d in stack.get(f"/api/observations/{rid}/deliveries?latest=1000") if d["kind"] == "slot_quality"]
    assert quality  # the degraded fixture's missing/rejected slots are delivered as quality evidence, never filled

    # recorded session: RECORDED (client-observed receipt) availability
    page.get_by_test_id("obs-kind-recording").click()
    page.get_by_test_id("obs-source").select_option("rec-e2e")
    expect(page.get_by_test_id("obs-preflight-availability")).to_contain_text("Recorded availability", timeout=10_000)
    page.get_by_test_id("obs-start-speed").select_option("0")
    page.get_by_test_id("obs-start").click()
    page.wait_for_function("(rid) => /obs=obs-/.test(window.location.hash) && !window.location.hash.includes(rid)", arg=rid)
    rid2 = page.evaluate("() => window.location.hash.split('obs=')[1]")
    expect(page.get_by_test_id("obs-panel").get_by_test_id("obs-status")).to_have_text("COMPLETED", timeout=30_000)
    expect(page.get_by_test_id("obs-availability")).to_contain_text("Recorded availability")
    expect(page.get_by_test_id("obs-availability-label")).to_contain_text("client-observed receipt")
    expect(page.get_by_test_id("obs-source-id")).to_contain_text("recording · rec-e2e")
    expect(page.get_by_test_id("obs-validation")).to_have_text("PASS", timeout=10_000)
    page.screenshot(path=str(evidence_dir / "16-market-replay-recording.png"), full_page=True)
    assert obs(stack, rid2)["availability"]["basis"] == "RECORDED"

    # synthetic DEMO stays separate: no runs were created, and the demo mode shows none of the real replays
    assert stack.get("/api/runs") == []
    page.get_by_test_id("mode-demo").click()
    expect(page.get_by_test_id("demo-banner")).to_contain_text("DEMO / SYNTHETIC")
    expect(page.get_by_test_id("synthetic-demo")).not_to_contain_text(rid)
    expect(page.get_by_test_id("market-replay")).to_have_count(0)

    # launch affordance from Data preselects the dataset in Market Replay (no replay logic in Data)
    page.goto(f"{stack.base}/#data={ds}")
    page.get_by_test_id("dataset-replay").click()
    expect(page.get_by_test_id("market-replay")).to_be_visible()
    expect(page.get_by_test_id("obs-source")).to_have_value(ds, timeout=10_000)
    ctx.close()
    record(evidence_dir, "e2e-market-replay", {
        "note": "offline fixtures (captured OKX public responses/messages); not live data; observation only",
        "dataset_replay": {"replay_id": rid, "paused_at": at, "stepped_to": at + 1, "total_events": total,
                           "quality_deliveries": len(quality), "validation": manifest["validation"],
                           "final_content_digest": manifest["final_content_digest"], "control_log": commands},
        "recording_replay": {"replay_id": rid2, "availability": obs(stack, rid2)["availability"]},
    })
