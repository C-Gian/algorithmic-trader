"""Smoke a running application stack (Docker Compose or `algotrader serve`).

Starts a max-speed synthetic run through the API, waits for completion and
checks that the UI is served and the manifest/artifacts validate.
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
    print(json.dumps({k: m[k] for k in ("run_id", "status", "semantic_trace_hash", "event_count", "validation")}, indent=2))
    print("stack smoke OK")


if __name__ == "__main__":
    main()
