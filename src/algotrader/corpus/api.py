"""Corpus API (``/api/corpus``): plan/status, Prepare, acquisition job list/detail/cancel.

The API only reads state and records commands; the corpus worker owns execution.
Private filesystem paths are not exposed.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from .. import ops

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
        return "unresponsive", ("worker stopped heartbeating (lease expired); awaiting reclaim by a new fenced attempt, "
                                "which restarts this chunk from scratch")
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


def operation(row: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Shared status / phase / health / assurance view (algotrader.ops.v1) of a corpus job."""
    status = row["status"]
    terminal = status in cj.TERMINAL
    lease_expired = bool(status == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)
    p = row["progress"] or {}
    phase = p.get("shared_phase") or ("QUEUED" if status == "queued" else None)
    waiting = None
    if p.get("phase") in ("instrument", "trade_candles_1m", "mark_candles_1m", "index_candles_1m",
                          "funding_rates") and p.get("rate_limited"):
        waiting = "rate limited by the source"
    health, detail = ops.derive_health(
        status=status, phase=phase, lease_expired=lease_expired, last_progress_at=row.get("last_progress_at"),
        heartbeat_at=row["heartbeat_at"], progress={"waiting": waiting}, supervisor=None,
        generation=row.get("lease_generation") or 0, now=now)
    started = ops.parse_iso(p.get("phase_started_at"))
    tl = ops.timeline(list(row.get("phase_history") or []), None if terminal else phase, started,
                      status == "running" and not lease_expired, now, ops.CORPUS_PHASES)
    if status == "completed":
        assurance = {"state": "passed", "validator": "marketdata.v1 verify", "scope":
                     "every file hash/size, row counts, raw pages and dataset identity verified before binding"}
    elif terminal:
        assurance = {"state": "not_checked" if status == "cancelled" else "failed",
                     "detail": row["error"] or status}
    else:
        assurance = {"state": "not_checked", "detail": "dataset verification runs before binding"}
    if p.get("verify_total"):
        done, total, unit = p.get("verify_done"), p.get("verify_total"), p.get("verify_unit")
    else:
        done, total, unit = p.get("windows_done"), p.get("windows_total"), "windows"
    return {
        "contract": ops.OPS_CONTRACT, "status": status, "phase": phase,
        "phase_label": ops.PHASE_LABEL.get(phase or "", "—"), "health": health.value,
        "health_label": ops.HEALTH_LABEL[health.value], "health_detail": detail, "assurance": assurance,
        "generation": row.get("lease_generation") or 0, "attempt": row["attempt"],
        "progress": {"stage": p.get("stage") or p.get("phase"), "done": done, "total": total, "unit": unit,
                     "fraction": (done / total) if (done is not None and total) else None,
                     "detail": p.get("detail"), "progress_seq": row.get("progress_seq") or 0,
                     "last_progress_at": ops.iso(row.get("last_progress_at"))},
        "timeline": tl,
        "controls": {"cancel": {"enabled": not terminal and not row["cancel_requested"],
                                "reason": None if not terminal and not row["cancel_requested"] else
                                ("cancellation already requested" if row["cancel_requested"] else f"job {status}")}},
    }


def diagnostic_report(row: dict[str, Any], now: datetime) -> dict[str, Any]:
    op = operation(row, now)
    terminal = row["status"] in cj.TERMINAL
    p = dict(row["progress"] or {})
    p.pop("work_dir", None)
    return {
        "report_kind": "CORPUS_PREPARATION_DIAGNOSTIC", "report_format": "algotrader.corpus-diagnostic.v1",
        "snapshot": not terminal, "captured_at": None if terminal else now.isoformat(),
        "job_id": row["job_id"], "chunk_id": row["chunk_id"], "plan_id": row["plan_id"],
        "source": {"source": "okx", "base_url": row["base_url"]},
        "status": row["status"], "phase": op["phase"], "health": op["health"],
        "health_detail": op["health_detail"] if not terminal else None, "assurance": op["assurance"],
        "outcome": row["outcome"], "dataset_id": row["dataset_id"] or "PENDING",
        "attempts": {"attempt": row["attempt"], "max_attempts": row["max_attempts"], "generation": op["generation"],
                     "recovery_log": list(row["recovery_log"] or [])},
        "timing": {"created_at": ops.iso(row["created_at"]), "started_at": ops.iso(row["started_at"]),
                   "finished_at": ops.iso(row["finished_at"]),
                   "active_seconds_total": op["timeline"]["active_seconds_total"],
                   "phases": [x for x in op["timeline"]["phases"] if x["spans"] or x["state"] == "current"]},
        "progress": {**op["progress"], "pages": p.get("pages"), "bytes_fetched": p.get("bytes"),
                     "windows_done": p.get("windows_done"), "windows_total": p.get("windows_total")},
        "network_note": ("counts are what this job recorded; a diagnostic snapshot never claims download "
                         "completion or network receipts that did not happen"),
        "result": row["result"], "error": row["error"],
        "recovery_behavior": cj.RECOVERY_BEHAVIOR,
    }


def render_markdown(r: dict[str, Any]) -> str:
    pr, a = r["progress"], r["assurance"]
    lines = [
        "# Corpus preparation diagnostic" + (" — snapshot (incomplete)" if r["snapshot"] else ""),
        "",
        f"**{r['report_kind']}** · job `{r['job_id']}` · chunk `{r['chunk_id']}`"
        + (f" · captured {r['captured_at']}" if r["captured_at"] else ""),
        f"**Status:** {r['status'].upper()} · phase **{r['phase'] or '—'}** · health **{r['health']}** · "
        f"assurance **{str(a.get('state')).upper()}**",
        "",
        f"- Source: OKX public REST {r['source']['base_url']} (read-only)",
        f"- Outcome: {r['outcome'] or '—'} · dataset {r['dataset_id']}",
        f"- Progress: {pr.get('stage') or '—'} {pr.get('done')}/{pr.get('total')} {pr.get('unit') or ''} · pages "
        f"{pr.get('pages')} · bytes {pr.get('bytes_fetched')}",
        f"- Attempts {r['attempts']['attempt']}/{r['attempts']['max_attempts']} · fencing generation "
        f"{r['attempts']['generation']}",
        f"- Active (measured) {r['timing']['active_seconds_total']:.1f} s",
    ]
    for x in r["timing"]["phases"]:
        lines.append(f"  - {x['label']}: {x['active_seconds']:.1f} s active"
                     + (f" · {x['interrupted_spans']} interrupted" if x["interrupted_spans"] else "")
                     + (" · CURRENT" if x["state"] == "current" else ""))
    for x in r["attempts"]["recovery_log"]:
        lines.append(f"  - recovery: attempt {x.get('attempt')} · {x.get('event')} — {x.get('detail')}")
    if r["health_detail"]:
        lines.append(f"- Health: {r['health_detail']}")
    if r["error"]:
        lines.append(f"- Error: {r['error']}")
    lines += ["", f"_{r['network_note']}_", f"_Recovery: {r['recovery_behavior']}_", ""]
    return "\n".join(lines)


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
        "operation": operation(row, now),
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

    @r.get("/jobs/{job_id}/report.json")
    def job_report_json(job_id: str, download: bool = False) -> PlainTextResponse:
        with conn() as c:
            doc = diagnostic_report(get_job(c, job_id), datetime.now(UTC))
        headers = {"Content-Disposition": f'attachment; filename="{job_id}-diagnostic.json"'} if download else {}
        return PlainTextResponse(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                                 media_type="application/json", headers=headers)

    @r.get("/jobs/{job_id}/report.md")
    def job_report_md(job_id: str, download: bool = False) -> PlainTextResponse:
        with conn() as c:
            doc = diagnostic_report(get_job(c, job_id), datetime.now(UTC))
        headers = {"Content-Disposition": f'attachment; filename="{job_id}-diagnostic.md"'} if download else {}
        return PlainTextResponse(render_markdown(doc), media_type="text/markdown; charset=utf-8", headers=headers)

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
