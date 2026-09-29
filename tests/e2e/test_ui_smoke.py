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
from pathlib import Path

import httpx
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
    def __init__(self, database_url: str, artifact_root: Path, log_dir: Path) -> None:
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.env = {
            **os.environ,
            "ALGOTRADER_DATABASE_URL": database_url,
            "ALGOTRADER_ARTIFACT_ROOT": str(artifact_root),
            "ALGOTRADER_WEB_DIST": str(WEB_DIST),
            "PYTHONUNBUFFERED": "1",
        }
        self.log_dir = log_dir
        self.api = self._spawn("api", ["api", "--port", str(self.port)])
        self.worker: subprocess.Popen | None = None
        self.start_worker()
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
        for proc in (self.worker, self.api):
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait(10)

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
    page.goto(base)
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
    page.goto(stack.base)  # fresh browser, no hash: reconstructs from backend
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
        "run_id": run_id, "status": manifest["status"], "speed": manifest["config"]["speed"],
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
