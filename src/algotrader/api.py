"""FastAPI application: commands, snapshots, SSE updates and artifact access.

The API never runs a replay itself; it only records commands (start/cancel)
and reads persisted state. The worker owns execution.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Query
import psycopg
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, control, db
from .contracts import SCHEMA_VERSION, FaultMode, ReplayControl, Run, RunConfig, RunProgress, RuntimeState
from .control import TERMINAL
from .corpus.api import build_router as corpus_router
from .evaluation.api import build_router as evaluation_router
from .marketdata.contracts import MARKETDATA_SCHEMA_VERSION, DatasetManifest, QualityReport
from .marketdata.dataset import dataset_path, default_data_root, list_manifests, load_manifest, load_quality, verify
from .observe.api import build_router as observation_router
from .recorder import job as recorder_job
from .recorder import journal as rec_journal
from .worker import default_artifact_root, fetch_events

DEFAULT_WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


class StartRun(BaseModel):
    speed: float = Field(default=4.0, ge=0, le=1000)
    paused: bool = False
    fault: FaultMode = FaultMode.NONE
    fault_at_step: int = Field(default=45, ge=0)


class StartRecording(BaseModel):
    max_duration_minutes: float = Field(default=360, gt=0, le=7 * 24 * 60)
    ws_public_url: str | None = None
    ws_business_url: str | None = None
    rest_base_url: str | None = None


def _duration_seconds(value: Any) -> float | None:
    """Pydantic serializes timedelta as an ISO-8601 duration (e.g. 'PT6H'); parse the simple forms."""
    import re

    if isinstance(value, (int, float)):
        return float(value)
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?)?", str(value))
    if not m:
        return None
    d, h, mi, sec = (float(x) if x else 0.0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + sec


class SetSpeed(BaseModel):
    speed: float = Field(ge=0, le=1000)


# A worker whose last heartbeat is older than this is reported as not alive.
WORKER_ALIVE_SECONDS = 10.0
# Minimum observed progress in the current throughput window before an ETA is shown.
ETA_MIN_STEPS = 3
ETA_MIN_SECONDS = 1.0


def _runtime(row: dict[str, Any], lease_expired: bool) -> tuple[RuntimeState, str]:
    status = row["status"]
    if status in TERMINAL:
        return RuntimeState(status), {
            "completed": "finished all input bars",
            "cancelled": "cancelled by user",
            "failed": "failed; see error",
        }[status]
    if row["cancel_requested"]:
        return RuntimeState.CANCEL_REQUESTED, "cancellation requested; worker will finalize the run"
    if status == "running" and lease_expired:
        return RuntimeState.RECOVERING, "lease expired (worker stopped heartbeating); awaiting reclaim by a worker"
    if row["paused"]:
        if row["step_budget"] > 0:
            return RuntimeState.STEPPING, f"paused; {row['step_budget']} single step(s) pending"
        if status == "running":
            return RuntimeState.PAUSING, "pause requested; worker finishes the current bar"
        return RuntimeState.PAUSED, "paused at a committed checkpoint; no worker holds the run"
    if status == "running":
        return RuntimeState.RUNNING, f"worker {row['lease_owner']} is processing bars"
    return RuntimeState.QUEUED, "waiting for a worker"


def _eta(row: dict[str, Any], state: RuntimeState, steps_done: int, now: datetime) -> tuple[float | None, str]:
    """ETA only from throughput observed since the last claim/resume/speed change."""
    if state != RuntimeState.RUNNING:
        return None, f"unavailable while {state.value}"
    since, base = row["throughput_since"], row["throughput_base_step"]
    if since is None or base is None:
        return None, "unavailable: no throughput observed yet"
    window = (now - since).total_seconds()
    done = steps_done - base
    if done < ETA_MIN_STEPS or window < ETA_MIN_SECONDS:
        return None, "unavailable: not enough progress observed since the last start/resume/speed change"
    rate = done / window
    return (row["total_steps"] - steps_done) / rate, f"observed {rate:.2f} bars/s over the last {window:.0f}s"


def _run_view(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    elapsed = None
    if row["started_at"]:
        elapsed = ((row["finished_at"] or now) - row["started_at"]).total_seconds()
    hb = row["heartbeat_at"]
    steps_done = row.get("steps_done") or 0
    lease_expired = bool(row["status"] == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)
    state, detail = _runtime(row, lease_expired)
    eta, eta_basis = _eta(row, state, steps_done, now)
    run = Run(
        run_id=row["run_id"],
        status=row["status"],
        runtime_state=state,
        runtime_detail=detail,
        config=row["config"],
        control=ReplayControl(paused=row["paused"], step_budget=row["step_budget"], speed=row["speed"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        cancel_requested=row["cancel_requested"],
        attempt=row["attempt"],
        max_attempts=row["max_attempts"],
        recovery_log=row["recovery_log"],
        control_log=row["control_log"],
        error=row["error"],
        lease_owner=row["lease_owner"],
        lease_expired=lease_expired,
        has_manifest=row["manifest"] is not None,
        progress=RunProgress(
            steps_done=steps_done,
            total_steps=row["total_steps"],
            sim_time=row.get("ckpt_sim_time"),
            heartbeat_at=hb,
            heartbeat_age_seconds=(now - hb).total_seconds() if hb else None,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            eta_basis=eta_basis,
        ),
        labels=("DEMO", "SYNTHETIC"),
    )
    return run.model_dump(mode="json")


RUN_SELECT = """
SELECT r.*, c.next_step AS steps_done, c.sim_time AS ckpt_sim_time
FROM runs r LEFT JOIN run_checkpoints c USING (run_id)
"""


def _capability(label: str, workers_alive: int, active_jobs: int) -> dict[str, Any]:
    if workers_alive:
        status = "available"
    else:
        status = "stalled" if active_jobs else "unavailable"  # jobs waiting with no worker vs. simply idle/off
    return {"label": label, "status": status, "workers_alive": workers_alive, "active_jobs": active_jobs}


def _dataset_summary(m: DatasetManifest, q: QualityReport) -> dict[str, Any]:
    return {
        "dataset_id": m.dataset_id,
        "schema_version": m.schema_version,
        "source": m.request.source,
        "base_url": m.request.base_url,
        "inst_id": m.instrument.inst_id,
        "requested": {"start": m.request.start.isoformat(), "end": m.request.end.isoformat()},
        "retrieved_at": m.retrieval_started_at.isoformat(),
        "quality_status": q.status.value,
        "families": [
            {
                "family": f.family.value,
                "rows": f.rows,
                "first_time": f.first_time.isoformat() if f.first_time else None,
                "last_time": f.last_time.isoformat() if f.last_time else None,
                "status": fq.status.value,
                "expected_rows": fq.expected_rows,
                "missing_rows": fq.missing_rows,
                "gaps": len(fq.gaps),
            }
            for f, fq in zip(m.families, q.families)
        ],
        "prior_versions": list(m.prior_versions),
    }


def create_app(
    database_url: str | None = None,
    artifact_root: Path | None = None,
    web_dist: Path | None = None,
    data_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Algorithmic Trader (DEMO shell)", version=__version__)
    art_root = artifact_root or default_artifact_root()
    md_root = data_root or default_data_root()
    dist = web_dist or Path(os.environ.get("ALGOTRADER_WEB_DIST", DEFAULT_WEB_DIST))

    def conn():
        return db.connection(database_url, connect_timeout=3)

    @app.exception_handler(psycopg.OperationalError)
    def database_disconnected(_request, exc: psycopg.OperationalError) -> JSONResponse:
        # The database cannot be reached: report DISCONNECTED; never a fabricated stall or a successful save.
        return JSONResponse(status_code=503, content={
            "status": "disconnected", "database": "disconnected", "health": "disconnected",
            "detail": "database unreachable: operation state cannot be read or confirmed right now",
            "error": type(exc).__name__,
        })

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
            running = c.execute(
                "SELECT max(heartbeat_at) AS hb FROM runs WHERE status = 'running'"
            ).fetchone()
            workers = c.execute(
                """
                SELECT worker_id, host, pid, started_at, current_run,
                       extract(epoch FROM now() - heartbeat_at)::float8 AS age
                FROM workers WHERE worker_id NOT LIKE 'recorder:%%' AND worker_id NOT LIKE 'observe:%%'
                  AND worker_id NOT LIKE 'corpus:%%'
                ORDER BY heartbeat_at DESC LIMIT 10
                """
            ).fetchall()
            recorders = c.execute(
                """
                SELECT worker_id, current_run, extract(epoch FROM now() - heartbeat_at)::float8 AS age
                FROM workers WHERE worker_id LIKE 'recorder:%%' ORDER BY heartbeat_at DESC LIMIT 5
                """
            ).fetchall()
            observers = c.execute(
                """
                SELECT worker_id, current_run, extract(epoch FROM now() - heartbeat_at)::float8 AS age
                FROM workers WHERE worker_id LIKE 'observe:%%' ORDER BY heartbeat_at DESC LIMIT 5
                """
            ).fetchall()
            corpus_workers = c.execute(
                """
                SELECT worker_id, current_run, extract(epoch FROM now() - heartbeat_at)::float8 AS age
                FROM workers WHERE worker_id LIKE 'corpus:%%' ORDER BY heartbeat_at DESC LIMIT 5
                """
            ).fetchall()
            active = c.execute(
                """
                SELECT (SELECT count(*) FROM runs WHERE status IN ('queued','running')) AS runs,
                       (SELECT count(*) FROM recorder_sessions WHERE status IN ('queued','running')) AS recordings,
                       (SELECT count(*) FROM observation_replays WHERE status IN ('queued','running')
                          AND suspended_at IS NULL) AS observations,
                       (SELECT count(*) FROM observation_replays WHERE suspended_at IS NOT NULL
                          AND status NOT IN ('completed','cancelled','failed')) AS suspended_observations,
                       (SELECT count(*) FROM corpus_jobs WHERE status IN ('queued','running')) AS corpus_jobs
                """
            ).fetchone()
        alive = [w for w in workers if w["age"] < WORKER_ALIVE_SECONDS]
        rec_alive = sum(1 for r in recorders if r["age"] < WORKER_ALIVE_SECONDS)
        obs_alive = sum(1 for r in observers if r["age"] < WORKER_ALIVE_SECONDS)
        corpus_alive = sum(1 for r in corpus_workers if r["age"] < WORKER_ALIVE_SECONDS)
        return {
            # Capability-aware health: each capability has its own worker; a missing optional worker
            # limits that capability only (it is not a whole-system outage).
            "capabilities": {
                "core": {"label": "API and database", "status": "available", "workers_alive": None,
                         "active_jobs": None},
                "market_replay": _capability("Real-market observation replay", obs_alive, active["observations"]),
                "corpus": _capability("Corpus acquisition", corpus_alive, active["corpus_jobs"]),
                "recorder": _capability("Public market recorder", rec_alive, active["recordings"]),
                "synthetic_replay": _capability("Synthetic DEMO replay", len(alive), active["runs"]),
            },
            "observation_workers": {
                "alive": obs_alive,
                "suspended_legacy_replays": active["suspended_observations"],
                "note": ("service availability comes from supervisor heartbeats (not blocked by CPU-bound compute); "
                         "each operation reports its own health separately"),
                "recent": [{"worker_id": r["worker_id"], "current_replay": r["current_run"],
                            "heartbeat_age_seconds": round(r["age"], 3)} for r in observers],
            },
            "corpus_workers": {
                "alive": corpus_alive,
                "recent": [{"worker_id": r["worker_id"], "current_job": r["current_run"],
                            "heartbeat_age_seconds": round(r["age"], 3)} for r in corpus_workers],
            },
            "recorder_workers": {
                "alive": rec_alive,
                "recent": [{"worker_id": r["worker_id"], "current_session": r["current_run"],
                            "heartbeat_age_seconds": round(r["age"], 3)} for r in recorders],
            },
            "status": "ok",
            "version": __version__,
            "schema_version": SCHEMA_VERSION,
            "database": "ok",
            "latest_running_heartbeat": running["hb"].isoformat() if running["hb"] else None,
            "workers": {
                "alive": len(alive),
                "alive_threshold_seconds": WORKER_ALIVE_SECONDS,
                "recent": [
                    {
                        "worker_id": w["worker_id"],
                        "host": w["host"],
                        "pid": w["pid"],
                        "started_at": w["started_at"].isoformat(),
                        "heartbeat_age_seconds": round(w["age"], 3),
                        "current_run": w["current_run"],
                        "alive": w["age"] < WORKER_ALIVE_SECONDS,
                    }
                    for w in workers[:5]
                ],
            },
            "labels": ["DEMO", "SYNTHETIC"],
        }

    @app.post("/api/runs", status_code=201)
    def start_run(body: StartRun) -> dict[str, Any]:
        cfg = RunConfig(fault=body.fault, fault_at_step=body.fault_at_step)
        with conn() as c:
            run_id = control.create_run(c, cfg, speed=body.speed, paused=body.paused)
            return _run_view(get_run(c, run_id))

    def command(run_id: str, fn, *args) -> dict[str, Any]:
        with conn() as c:
            try:
                fn(c, run_id, *args)
            except control.RunNotFound:
                raise HTTPException(404, f"run {run_id} not found") from None
            except control.ControlRejected as exc:
                raise HTTPException(409, str(exc)) from None
            return _run_view(get_run(c, run_id))

    @app.post("/api/runs/{run_id}/pause")
    def pause_run(run_id: str) -> dict[str, Any]:
        return command(run_id, control.pause)

    @app.post("/api/runs/{run_id}/resume")
    def resume_run(run_id: str) -> dict[str, Any]:
        return command(run_id, control.resume)

    @app.post("/api/runs/{run_id}/step")
    def step_run(run_id: str) -> dict[str, Any]:
        return command(run_id, control.step)

    @app.post("/api/runs/{run_id}/speed")
    def speed_run(run_id: str, body: SetSpeed) -> dict[str, Any]:
        return command(run_id, control.set_speed, body.speed)

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
        return command(run_id, control.cancel)

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
                        run["runtime_state"],
                        run["progress"]["steps_done"],
                        run["attempt"],
                        len(run["recovery_log"]),
                        len(run["control_log"]),
                        run["lease_expired"],
                        run["cancel_requested"],
                        tuple(run["control"].values()),
                    )
                    if key != last_key or time.monotonic() - last_sent >= 2:
                        yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
                        last_key, last_sent = key, time.monotonic()
                    else:
                        yield ": keep-alive\n\n"
                    if run["status"] in TERMINAL:
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

    # -- public market recorder (no trading) --------------------------------

    def recorder_row(c, session_id: str) -> dict[str, Any]:
        row = c.execute("SELECT * FROM recorder_sessions WHERE session_id = %s", (session_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"recording session {session_id} not found")
        return row

    def recorder_view(row: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        hb, started = row["heartbeat_at"], row["started_at"]
        return {
            "session_id": row["session_id"],
            "status": row["status"],
            "stop_requested": row["stop_requested"],
            "created_at": row["created_at"].isoformat(),
            "started_at": started.isoformat() if started else None,
            "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
            "elapsed_seconds": ((row["finished_at"] or now) - started).total_seconds() if started else None,
            "heartbeat_age_seconds": (now - hb).total_seconds() if hb else None,
            "lease_expired": bool(row["status"] == "running" and row["lease_expires_at"]
                                  and row["lease_expires_at"] < now),
            "endpoints": row["config"]["endpoints"],
            "channels": [f"{c['channel']}:{c['inst_id']}" for c in row["config"]["channels"]],
            "max_duration_seconds": _duration_seconds(row["config"]["max_duration"]),
            "stats": row["stats"],
            "error": row["error"],
            "session_path": f"recordings/{row['session_id']}",
            "manifest_status": row["manifest"]["status"] if row["manifest"] else None,
            "labels": ["PUBLIC_MARKET_RECORDING", "NO_TRADING"],
        }

    @app.get("/api/recorder/sessions")
    def recorder_sessions(limit: int = 20) -> dict[str, Any]:
        with conn() as c:
            rows = c.execute("SELECT * FROM recorder_sessions ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
        return {"data_root": str(md_root), "sessions": [recorder_view(r) for r in rows]}

    @app.post("/api/recorder/sessions", status_code=201)
    def start_recording(body: StartRecording) -> dict[str, Any]:
        eps = recorder_job.configured_endpoints()
        overrides = {k: v for k, v in body.model_dump().items() if k.endswith("_url") and v}
        try:
            endpoints = eps.model_copy(update=overrides)
            with conn() as c:
                sid = recorder_job.create_session(c, timedelta(minutes=body.max_duration_minutes), endpoints)
                return recorder_view(recorder_row(c, sid))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/api/recorder/sessions/{session_id}/stop")
    def stop_recording(session_id: str) -> dict[str, Any]:
        with conn() as c:
            try:
                recorder_job.stop_session(c, session_id)
            except LookupError:
                raise HTTPException(404, f"recording session {session_id} not found") from None
            except recorder_job.RecorderControlError as exc:
                raise HTTPException(409, str(exc)) from None
            return recorder_view(recorder_row(c, session_id))

    @app.get("/api/recorder/sessions/{session_id}")
    def recording_detail(session_id: str) -> dict[str, Any]:
        with conn() as c:
            view = recorder_view(recorder_row(c, session_id))
        path = rec_journal.session_path(md_root, session_id)
        if path is not None and rec_journal.is_finalized(path):
            view["manifest"] = json.loads(rec_journal.load_manifest(path).model_dump_json())
            view["report"] = json.loads(rec_journal.load_report(path).model_dump_json())
        return view

    @app.get("/api/recorder/sessions/{session_id}/verify")
    def recording_verify(session_id: str) -> dict[str, Any]:
        path = rec_journal.session_path(md_root, session_id)
        if path is None:
            raise HTTPException(404, f"no recording directory for {session_id}")
        problems = rec_journal.verify(path)
        return {"session_id": session_id, "ok": not problems, "problems": problems}

    @app.get("/api/recorder/sessions/{session_id}/files/{name:path}")
    def recording_file(session_id: str, name: str):
        path = rec_journal.session_path(md_root, session_id)
        if path is None or not rec_journal.is_finalized(path):
            raise HTTPException(404, f"no finalized recording {session_id}")
        m = rec_journal.load_manifest(path)
        if name != "manifest.json" and name not in {f.name for f in m.files}:
            raise HTTPException(404, f"no file {name} in recording {session_id}")
        return FileResponse(path / name, filename=Path(name).name)

    # -- real-market observation replay (separate path; algotrader.observe.v1) --

    app.include_router(observation_router(conn, md_root, art_root))

    # -- Owner evaluation workbench: corpus preparation + observation-only evaluations --

    app.include_router(corpus_router(conn, md_root))
    app.include_router(evaluation_router(conn, md_root, art_root))

    # -- market-data datasets (read-only inspection of the data root) ---------

    def dataset_dir(dataset_id: str) -> Path:
        path = dataset_path(md_root, dataset_id)
        if path is None:
            raise HTTPException(404, f"dataset {dataset_id} not found")
        return path

    @app.get("/api/datasets")
    def list_datasets() -> dict[str, Any]:
        out = []
        for m in list_manifests(md_root):
            out.append(_dataset_summary(m, load_quality(dataset_dir(m.dataset_id))))
        return {"data_root": str(md_root), "schema_version": MARKETDATA_SCHEMA_VERSION, "datasets": out}

    @app.get("/api/datasets/{dataset_id}")
    def dataset_detail(dataset_id: str) -> dict[str, Any]:
        path = dataset_dir(dataset_id)
        m, q = load_manifest(path), load_quality(path)
        return {
            "summary": _dataset_summary(m, q),
            "manifest": json.loads(m.model_dump_json()),
            "quality": json.loads(q.model_dump_json()),
        }

    @app.get("/api/datasets/{dataset_id}/verify")
    def dataset_verify(dataset_id: str) -> dict[str, Any]:
        problems = verify(dataset_dir(dataset_id))
        return {"dataset_id": dataset_id, "ok": not problems, "problems": problems}

    @app.get("/api/datasets/{dataset_id}/files/{name:path}")
    def dataset_file(dataset_id: str, name: str):
        path = dataset_dir(dataset_id)
        m = load_manifest(path)
        if name != "manifest.json" and name not in {f.name for f in m.files}:
            raise HTTPException(404, f"no file {name} in dataset {dataset_id}")
        return FileResponse(path / name, filename=Path(name).name)

    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    else:

        @app.get("/")
        def no_ui() -> dict[str, str]:
            return {"detail": "web UI not built: run `npm --prefix web ci && npm --prefix web run build`"}

    return app


def app_from_env() -> FastAPI:
    return create_app()
