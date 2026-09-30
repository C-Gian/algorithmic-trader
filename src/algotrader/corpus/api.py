"""Corpus API (``/api/corpus``): plan/status, Prepare, acquisition job list/detail/cancel.

The API only reads state and records commands; the corpus worker owns execution.
Private filesystem paths are not exposed.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from . import job as cj
from . import state
from .plan import load_plan

ETA_MIN_WINDOWS = 10
ETA_MIN_SECONDS = 5.0


def _runtime(row: dict[str, Any], lease_expired: bool) -> tuple[str, str]:
    status = row["status"]
    if status == "completed":
        return "completed", {
            "reused_binding": "verified local dataset reused; nothing downloaded",
            "adopted_local_dataset": "matching local dataset verified and bound; nothing downloaded",
            "acquired": "acquired from OKX, verified and bound",
            "acquired_identical_existing": "acquired; identical source bytes were already stored; verified and bound",
        }.get(row["outcome"] or "", "completed")
    if status == "cancelled":
        return "cancelled", row["error"] or "cancelled"
    if status == "failed":
        return "failed", row["error"] or "failed"
    if row["cancel_requested"]:
        return "cancel_requested", "cancellation requested; the worker stops at the next page boundary"
    if status == "running" and lease_expired:
        return "recovering", "worker stopped heartbeating; the job will be reclaimed and the chunk restarted from scratch"
    if status == "running":
        return "running", f"worker {row['lease_owner']} is preparing the chunk"
    return "queued", "waiting for a corpus worker"


def _eta(p: dict[str, Any], state_: str) -> tuple[float | None, str]:
    if state_ != "running":
        return None, f"unavailable while {state_}"
    done, total, secs = p.get("windows_done"), p.get("windows_total"), p.get("acquire_elapsed_seconds")
    if not total or done is None or secs is None:
        return None, "unavailable: no acquisition throughput observed yet"
    if done < ETA_MIN_WINDOWS or secs < ETA_MIN_SECONDS:
        return None, "unavailable: not enough windows completed to measure throughput"
    rate = done / secs
    return (total - done) / rate, f"measured {rate:.2f} windows/s over {secs:.0f}s of this attempt"


def job_view(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    lease_expired = bool(row["status"] == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)
    runtime, detail = _runtime(row, lease_expired)
    p = dict(row["progress"] or {})
    p.pop("work_dir", None)  # private path detail
    eta, eta_basis = _eta(p, runtime)
    total = p.get("windows_total")
    hb = row["heartbeat_at"]
    return {
        "job_id": row["job_id"],
        "chunk_id": row["chunk_id"],
        "plan_id": row["plan_id"],
        "status": row["status"],
        "runtime_state": runtime,
        "runtime_detail": detail,
        "cancel_requested": row["cancel_requested"],
        "source": {"source": "okx", "base_url": row["base_url"]},
        "created_at": row["created_at"].isoformat(),
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
        "attempt": row["attempt"],
        "max_attempts": row["max_attempts"],
        "recovery_log": row["recovery_log"],
        "recovery_behavior": cj.RECOVERY_BEHAVIOR,
        "lease_expired": lease_expired,
        "outcome": row["outcome"],
        "dataset_id": row["dataset_id"],
        "result": row["result"],
        "error": row["error"],
        "progress": {
            **p,
            "fraction": (p.get("windows_done", 0) / total) if total else None,
            "elapsed_seconds": (((row["finished_at"] or now) - row["started_at"]).total_seconds()
                                if row["started_at"] else None),
            "heartbeat_age_seconds": (now - hb).total_seconds() if hb else None,
            "eta_seconds": eta,
            "eta_basis": eta_basis,
        },
    }


def corpus_status(c, data_root: Path) -> dict[str, Any]:
    plan = load_plan()
    binds = state.bindings(c)
    latest = {r["chunk_id"]: r for r in c.execute(
        "SELECT DISTINCT ON (chunk_id) * FROM corpus_jobs ORDER BY chunk_id, created_at DESC").fetchall()}
    chunks = []
    for ch in plan.chunks:
        view = state.chunk_view(plan, ch, binds.get(ch.chunk_id), latest.get(ch.chunk_id), data_root)
        view["latest_job"] = job_view(latest[ch.chunk_id]) if ch.chunk_id in latest else None
        chunks.append(view)
    prepared = [x for x in chunks if x["status"] == "prepared"]
    return {
        "plan": {
            "plan_id": plan.plan_id, "plan_version": plan.plan_version, "description": plan.description,
            "source": plan.source, "inst_id": plan.inst_id, "bar": plan.bar,
            "families": [f.value for f in plan.families], "chunk_rule": plan.chunk_rule,
            "target": {"start": plan.target.start.isoformat(), "end": plan.target.end.isoformat()},
        },
        "summary": {
            "chunks": len(chunks),
            "prepared": len(prepared),
            "preparable": sum(1 for x in chunks if x["preparable"]),
            "planned_locked": sum(1 for x in chunks if not x["preparable"]),
            "prepared_bytes": sum((x["local"] or {}).get("bytes_on_disk") or 0 for x in prepared),
        },
        "chunks": chunks,
        "recovery_behavior": cj.RECOVERY_BEHAVIOR,
    }


def build_router(conn: Callable, data_root: Path) -> APIRouter:
    r = APIRouter(prefix="/api/corpus")

    def get_job(c, job_id: str) -> dict[str, Any]:
        row = c.execute("SELECT * FROM corpus_jobs WHERE job_id = %s", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"corpus job {job_id} not found")
        return row

    @r.get("")
    def status() -> dict[str, Any]:
        with conn() as c:
            return corpus_status(c, data_root)

    @r.post("/chunks/{chunk_id}/prepare", status_code=201)
    def prepare(chunk_id: str) -> dict[str, Any]:
        with conn() as c:
            try:
                job_id = cj.create_job(c, load_plan(), chunk_id)
            except LookupError:
                raise HTTPException(404, f"chunk {chunk_id} is not in the corpus plan") from None
            except cj.CorpusJobRejected as exc:
                raise HTTPException(409 if "active" in str(exc) else 422, str(exc)) from None
            return job_view(get_job(c, job_id))

    @r.get("/jobs")
    def jobs(limit: int = 20) -> list[dict[str, Any]]:
        with conn() as c:
            rows = c.execute("SELECT * FROM corpus_jobs ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
        return [job_view(x) for x in rows]

    @r.get("/jobs/{job_id}")
    def job(job_id: str) -> dict[str, Any]:
        with conn() as c:
            return job_view(get_job(c, job_id))

    @r.post("/jobs/{job_id}/cancel")
    def cancel(job_id: str) -> dict[str, Any]:
        with conn() as c:
            try:
                cj.cancel_job(c, job_id)
            except LookupError:
                raise HTTPException(404, f"corpus job {job_id} not found") from None
            except cj.CorpusJobRejected as exc:
                raise HTTPException(409, str(exc)) from None
            return job_view(get_job(c, job_id))

    return r
