"""FastAPI application: commands, snapshots, SSE updates and artifact access.

The API never runs a replay itself; it only records commands (start/cancel)
and reads persisted state. The worker owns execution.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from . import __version__, db
from .contracts import TERMINAL_STATUSES, FaultMode, RunConfig
from .synthetic import build_fixture
from .worker import default_artifact_root, fetch_events

DEFAULT_WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


class StartRun(BaseModel):
    speed: float = Field(default=4.0, ge=0, le=1000)
    fault: FaultMode = FaultMode.NONE
    fault_at_step: int = Field(default=45, ge=0)


def _run_view(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    elapsed = None
    if row["started_at"]:
        elapsed = ((row["finished_at"] or now) - row["started_at"]).total_seconds()
    hb = row["heartbeat_at"]
    return {
        "run_id": row["run_id"],
        "status": row["status"],
        "config": row["config"],
        "created_at": row["created_at"].isoformat(),
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
        "cancel_requested": row["cancel_requested"],
        "attempt": row["attempt"],
        "max_attempts": row["max_attempts"],
        "recovery_log": row["recovery_log"],
        "error": row["error"],
        "lease_owner": row["lease_owner"],
        "lease_expired": bool(
            row["status"] == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now
        ),
        "has_manifest": row["manifest"] is not None,
        "progress": {
            "steps_done": row.get("steps_done") or 0,
            "total_steps": row["total_steps"],
            "sim_time": row["ckpt_sim_time"].astimezone(UTC).isoformat() if row.get("ckpt_sim_time") else None,
            "heartbeat_at": hb.isoformat() if hb else None,
            "heartbeat_age_seconds": (now - hb).total_seconds() if hb else None,
            "elapsed_seconds": elapsed,
        },
        "labels": ["DEMO", "SYNTHETIC"],
    }


RUN_SELECT = """
SELECT r.*, c.next_step AS steps_done, c.sim_time AS ckpt_sim_time
FROM runs r LEFT JOIN run_checkpoints c USING (run_id)
"""


def create_app(database_url: str | None = None, artifact_root: Path | None = None, web_dist: Path | None = None) -> FastAPI:
    app = FastAPI(title="Algorithmic Trader (DEMO shell)", version=__version__)
    art_root = artifact_root or default_artifact_root()
    dist = web_dist or Path(os.environ.get("ALGOTRADER_WEB_DIST", DEFAULT_WEB_DIST))

    def conn():
        return db.connection(database_url)

    def get_run(c, run_id: str) -> dict[str, Any]:
        row = c.execute(RUN_SELECT + " WHERE r.run_id = %s", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"run {run_id} not found")
        return row

    def latest(c, run_id: str) -> dict[str, Any]:
        rows = c.execute(
            """
            SELECT DISTINCT ON (kind) kind, payload FROM run_events
            WHERE run_id = %s AND kind IN ('observation','market_view','decision','account','risk_decision')
            ORDER BY kind, seq DESC
            """,
            (run_id,),
        ).fetchall()
        return {r["kind"]: r["payload"] for r in rows}

    def snapshot(c, run_id: str) -> dict[str, Any]:
        return {"run": _run_view(get_run(c, run_id)), "latest": latest(c, run_id)}

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        with conn() as c:
            c.execute("SELECT 1")
            worker = c.execute(
                "SELECT max(heartbeat_at) AS hb FROM runs WHERE status = 'running'"
            ).fetchone()
        return {
            "status": "ok",
            "version": __version__,
            "database": "ok",
            "latest_running_heartbeat": worker["hb"].isoformat() if worker["hb"] else None,
            "labels": ["DEMO", "SYNTHETIC"],
        }

    @app.post("/api/runs", status_code=201)
    def start_run(body: StartRun) -> dict[str, Any]:
        cfg = RunConfig(speed=body.speed, fault=body.fault, fault_at_step=body.fault_at_step)
        fixture = build_fixture(cfg.fixture_id, cfg.seed)
        run_id = f"run-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
        with conn() as c, c.transaction():
            c.execute(
                "INSERT INTO runs (run_id, status, config, total_steps) VALUES (%s, 'queued', %s, %s)",
                (run_id, Jsonb(cfg.model_dump(mode="json")), fixture.total_steps),
            )
        with conn() as c:
            return _run_view(get_run(c, run_id))

    @app.get("/api/runs")
    def list_runs(limit: int = 50) -> list[dict[str, Any]]:
        with conn() as c:
            rows = c.execute(RUN_SELECT + " ORDER BY r.created_at DESC LIMIT %s", (limit,)).fetchall()
        return [_run_view(r) for r in rows]

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str) -> dict[str, Any]:
        with conn() as c:
            return _run_view(get_run(c, run_id))

    @app.post("/api/runs/{run_id}/cancel")
    def cancel_run(run_id: str) -> dict[str, Any]:
        with conn() as c:
            with c.transaction():
                row = get_run(c, run_id)
                if row["status"] in {s.value for s in TERMINAL_STATUSES}:
                    raise HTTPException(409, f"run already {row['status']}")
                c.execute("UPDATE runs SET cancel_requested = true WHERE run_id = %s", (run_id,))
            return _run_view(get_run(c, run_id))

    @app.get("/api/runs/{run_id}/snapshot")
    def run_snapshot(run_id: str) -> dict[str, Any]:
        with conn() as c:
            return snapshot(c, run_id)

    @app.get("/api/runs/{run_id}/prices")
    def prices(run_id: str) -> list[dict[str, Any]]:
        with conn() as c:
            get_run(c, run_id)
            rows = c.execute(
                "SELECT step, payload FROM run_events WHERE run_id = %s AND kind = 'observation' ORDER BY seq",
                (run_id,),
            ).fetchall()
            trades = c.execute(
                "SELECT step, payload FROM run_events WHERE run_id = %s AND kind = 'fill' ORDER BY seq", (run_id,)
            ).fetchall()
        fills = {r["step"]: r["payload"]["side"] for r in trades}
        return [
            {
                "step": r["step"],
                "time": r["payload"]["available_time"],
                "close": r["payload"]["close"],
                "quality": r["payload"]["quality"],
                "fill": fills.get(r["step"]),
            }
            for r in rows
        ]

    @app.get("/api/runs/{run_id}/events")
    def events(run_id: str, kind: str | None = None, after_seq: int = -1, limit: int = Query(500, le=5000)) -> list[dict[str, Any]]:
        with conn() as c:
            get_run(c, run_id)
            evs = fetch_events(c, run_id, kind)
        return [e for e in evs if e["seq"] > after_seq][:limit]

    @app.get("/api/runs/{run_id}/stream")
    def stream(run_id: str) -> StreamingResponse:
        with conn() as c:
            get_run(c, run_id)

        def gen() -> Iterator[str]:
            last_key = None
            last_sent = 0.0
            # Each (re)connection starts with a full snapshot (snapshot recovery).
            # Snapshots are re-sent at least every 2 s so heartbeat age and lease
            # expiry stay visible even when a dead worker makes no progress.
            with conn() as c:
                while True:
                    snap = snapshot(c, run_id)
                    run = snap["run"]
                    key = (
                        run["status"],
                        run["progress"]["steps_done"],
                        run["attempt"],
                        len(run["recovery_log"]),
                        run["lease_expired"],
                        run["cancel_requested"],
                    )
                    if key != last_key or time.monotonic() - last_sent >= 2:
                        yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
                        last_key, last_sent = key, time.monotonic()
                    else:
                        yield ": keep-alive\n\n"
                    if run["status"] in {s.value for s in TERMINAL_STATUSES}:
                        yield "event: end\ndata: {}\n\n"
                        return
                    time.sleep(0.5)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/api/runs/{run_id}/manifest")
    def manifest(run_id: str) -> dict[str, Any]:
        with conn() as c:
            row = get_run(c, run_id)
        if row["manifest"] is None:
            raise HTTPException(404, f"run {run_id} has no manifest yet (status {row['status']})")
        return row["manifest"]

    def artifact_path(run_id: str, name: str) -> Path:
        m = manifest(run_id)
        names = {a["name"] for a in m["artifacts"]} | {"manifest.json"}
        if name not in names:
            raise HTTPException(404, f"no artifact {name}")
        path = art_root / "runs" / run_id / name
        if not path.is_file():
            raise HTTPException(410, f"artifact {name} is recorded in the manifest but missing on disk")
        return path

    @app.get("/api/runs/{run_id}/artifacts")
    def list_artifacts(run_id: str) -> dict[str, Any]:
        m = manifest(run_id)
        return {"artifact_root": str(art_root), "artifacts": m["artifacts"]}

    @app.get("/api/runs/{run_id}/artifacts/{name}")
    def get_artifact(run_id: str, name: str, format: str | None = None, limit: int = Query(200, le=10000)):
        path = artifact_path(run_id, name)
        if format == "json" and name.endswith(".parquet"):
            table = pq.read_table(path)
            return {"name": name, "rows": table.num_rows, "records": table.slice(0, limit).to_pylist()}
        return FileResponse(path, filename=name)

    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    else:

        @app.get("/")
        def no_ui() -> dict[str, str]:
            return {"detail": "web UI not built: run `npm --prefix web ci && npm --prefix web run build`"}

    return app


def app_from_env() -> FastAPI:
    return create_app()
