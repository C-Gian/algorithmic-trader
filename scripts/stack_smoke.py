"""Smoke a running application stack (Docker Compose or `algotrader serve`).

Starts a max-speed synthetic run through the API, waits for completion and
checks that the UI is served and the manifest/artifacts validate. Then
drives a second run through pause/step/speed/resume and checks that it
reproduces the same semantic trace.
Standard library only.

    python scripts/stack_smoke.py [http://127.0.0.1:8000]
"""

import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def call(path: str, body: dict | None = None):
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if resp.headers.get_content_type() == "application/json" else raw


def main() -> None:
    assert '<div id="root">' in call("/"), "web UI not served"
    print("health:", call("/api/health"))
    run_id = call("/api/runs", {"speed": 0})["run_id"]
    print("started", run_id)
    for _ in range(120):
        status = call(f"/api/runs/{run_id}")["status"]
        if status in ("completed", "failed", "cancelled"):
            break
        time.sleep(1)
    assert status == "completed", f"run ended as {status}"
    m = call(f"/api/runs/{run_id}/manifest")
    assert m["validation"]["passed"], m["validation"]
    assert len(m["artifacts"]) > 5
    report = call(f"/api/runs/{run_id}/artifacts/report.md")
    assert "DEMO / SYNTHETIC" in report
    assert m["schema_version"] == "algotrader.semantic.v1", m["schema_version"]
    print(json.dumps({k: m[k] for k in ("run_id", "status", "semantic_trace_hash", "event_count", "validation")}, indent=2))
    controlled = replay_controls()
    assert controlled["semantic_trace_hash"] == m["semantic_trace_hash"], "replay control changed the trace"
    assert call("/api/health")["workers"]["alive"] >= 1
    datasets = call("/api/datasets")  # read-only market-data catalog (no network fetch in the smoke)
    assert datasets["schema_version"] == "algotrader.marketdata.v1", datasets
    print(f"market-data catalog: {len(datasets['datasets'])} dataset(s) under {datasets['data_root']}")
    # public recorder: worker process alive and API reachable (no session is started: no network in the smoke)
    for _ in range(30):
        if call("/api/health")["recorder_workers"]["alive"] >= 1:
            break
        time.sleep(1)
    assert call("/api/health")["recorder_workers"]["alive"] >= 1, "recorder worker not heartbeating"
    print(f"recorder sessions: {len(call('/api/recorder/sessions')['sessions'])}")
    print("stack smoke OK")


def wait(run_id: str, pred, timeout: float = 60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = call(f"/api/runs/{run_id}")
        if pred(run):
            return run
        time.sleep(0.2)
    raise AssertionError(f"timeout waiting on {run_id}: {run['runtime_state']} {run['progress']}")


def replay_controls() -> dict:
    """Paused start -> two single steps -> speed change -> resume; same trace as max speed."""
    run_id = call("/api/runs", {"speed": 20, "paused": True})["run_id"]
    time.sleep(1)
    assert call(f"/api/runs/{run_id}")["progress"]["steps_done"] == 0, "paused run progressed"
    for n in (1, 2):
        call(f"/api/runs/{run_id}/step", {})
        wait(run_id, lambda r, n=n: r["status"] == "paused" and r["progress"]["steps_done"] == n)
    call(f"/api/runs/{run_id}/speed", {"speed": 0})
    call(f"/api/runs/{run_id}/resume", {})
    wait(run_id, lambda r: r["status"] in ("completed", "failed", "cancelled"))
    m = call(f"/api/runs/{run_id}/manifest")
    assert m["status"] == "completed" and m["validation"]["passed"], m["validation"]
    print("replay controls:", [e["command"] for e in m["control_log"]])
    return m


if __name__ == "__main__":
    main()
