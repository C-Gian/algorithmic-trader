"""Evaluation facade (``/api/evaluations``): launch/list/detail and terminal reports.

An evaluation is a thin record over one accepted durable observation replay of a
prepared corpus chunk. The replay itself (state, controls, worker, recovery,
artifacts) stays the source of truth under ``/api/observations``; nothing here
forks the observation engine or adds trading semantics.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from ..corpus import state
from ..corpus.plan import load_plan
from ..observe import control
from ..observe.api import REPLAY_SELECT, replay_view
from ..observe.contracts import SourceKind
from ..observe.sources import SourceRejected
from . import report as rp

PRESET = "observation-only"
PRESET_LABEL = "Observation-only historical evaluation"


class StartEvaluation(BaseModel):
    chunk_id: str = Field(min_length=1, max_length=100)
    speed: float = Field(default=0.0, ge=0, le=control.MAX_SPEED)
    paused: bool = False


def new_evaluation_id() -> str:
    return f"eval-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def corpus_snapshot(c, plan, chunk, binding: dict[str, Any]) -> dict[str, Any]:
    """Corpus facts frozen into the evaluation at launch (the report never depends on later rebinding)."""
    job = None
    if binding["bound_by_job"]:
        job = c.execute("SELECT job_id, outcome, started_at, finished_at, progress FROM corpus_jobs WHERE job_id = %s",
                        (binding["bound_by_job"],)).fetchone()
    acquisition = None
    if job is not None:
        p = job["progress"] or {}
        acquisition = {
            "job_id": job["job_id"], "outcome": job["outcome"],
            "elapsed_seconds": ((job["finished_at"] - job["started_at"]).total_seconds()
                                if job["started_at"] and job["finished_at"] else None),
            "pages": p.get("pages"), "bytes_fetched": p.get("bytes"),
            "acquire_elapsed_seconds": p.get("acquire_elapsed_seconds"),
        }
    return {
        "plan_id": plan.plan_id, "plan_version": plan.plan_version,
        "chunk_id": chunk.chunk_id, "chunk_label": chunk.label,
        "start": chunk.start.isoformat(), "end": chunk.end.isoformat(),
        "dataset_id": binding["dataset_id"], "manifest_sha256": binding["manifest_sha256"],
        "base_url": binding["base_url"], "quality_status": binding["quality_status"],
        "verified_at": binding["verified_at"].isoformat() if binding["verified_at"] else None,
        "retrieved_at": binding["retrieved_at"].isoformat() if binding["retrieved_at"] else None,
        "bytes_on_disk": binding["bytes_on_disk"], "storage": binding["storage"],
        "binding_outcome": binding["outcome"], "acquisition": acquisition,
    }


def build_router(conn: Callable, data_root: Path) -> APIRouter:
    r = APIRouter(prefix="/api/evaluations")

    def get(c, evaluation_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        ev = c.execute("SELECT * FROM evaluations WHERE evaluation_id = %s", (evaluation_id,)).fetchone()
        if ev is None:
            raise HTTPException(404, f"evaluation {evaluation_id} not found")
        replay = c.execute(REPLAY_SELECT + " WHERE r.replay_id = %s", (ev["replay_id"],)).fetchone()
        return ev, replay

    def view(ev: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
        rv = replay_view(replay)
        return {
            "evaluation_id": ev["evaluation_id"],
            "run_type": ev["run_type"],
            "run_type_label": PRESET_LABEL,
            "preset": ev["preset"],
            "notice": rp.NOT_CONNECTED,
            "created_at": ev["created_at"].isoformat(),
            "corpus": ev["corpus"],
            "replay": rv,
            "report_available": rv["status"] in control.TERMINAL and replay["manifest"] is not None,
        }

    @r.post("", status_code=201)
    def start(body: StartEvaluation) -> dict[str, Any]:
        plan = load_plan()
        chunk = plan.chunk(body.chunk_id)
        if chunk is None:
            raise HTTPException(404, f"chunk {body.chunk_id} is not in the corpus plan")
        with conn() as c:
            binding = c.execute("SELECT * FROM corpus_chunks WHERE chunk_id = %s", (chunk.chunk_id,)).fetchone()
            usable, problem = state.binding_state(data_root, binding)
            if not usable:
                raise HTTPException(409, f"{chunk.chunk_id} is not prepared" + (f": {problem}" if problem else ""))
            snapshot = corpus_snapshot(c, plan, chunk, binding)
            c.commit()  # end the read transaction; the launch below is one atomic transaction
            evaluation_id = new_evaluation_id()
            try:
                with c.transaction():
                    # the accepted observation path re-verifies the dataset and builds its feed
                    replay_id = control.create_replay(c, data_root, SourceKind.DATASET, binding["dataset_id"],
                                                      body.speed, body.paused)
                    c.execute(
                        """INSERT INTO evaluations (evaluation_id, replay_id, run_type, preset, plan_id, chunk_id,
                               dataset_id, corpus) VALUES (%s, %s, 'observation_only', %s, %s, %s, %s, %s)""",
                        (evaluation_id, replay_id, PRESET, plan.plan_id, chunk.chunk_id, binding["dataset_id"],
                         Jsonb(snapshot)),
                    )
            except SourceRejected as exc:
                with c.transaction():
                    state.record_verification(c, chunk.chunk_id, False, [str(exc)])
                raise HTTPException(422, str(exc)) from None
            except control.ControlRejected as exc:
                raise HTTPException(422, str(exc)) from None
            return view(*get(c, evaluation_id))

    @r.get("")
    def list_evaluations(limit: int = 20) -> list[dict[str, Any]]:
        with conn() as c:
            evs = c.execute("SELECT * FROM evaluations ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
            return [view(ev, c.execute(REPLAY_SELECT + " WHERE r.replay_id = %s", (ev["replay_id"],)).fetchone())
                    for ev in evs]

    @r.get("/{evaluation_id}")
    def detail(evaluation_id: str) -> dict[str, Any]:
        with conn() as c:
            return view(*get(c, evaluation_id))

    def report_doc(evaluation_id: str) -> dict[str, Any]:
        with conn() as c:
            ev, replay = get(c, evaluation_id)
        if replay["status"] not in control.TERMINAL or replay["manifest"] is None:
            raise HTTPException(409, f"evaluation {evaluation_id} is {replay['status']}; the report is produced when "
                                     "the run completes, is cancelled or fails")
        return rp.build_report(ev, replay, replay["manifest"])

    @r.get("/{evaluation_id}/report.json")
    def report_json(evaluation_id: str, download: bool = False) -> PlainTextResponse:
        doc = report_doc(evaluation_id)
        headers = {"Content-Disposition": f'attachment; filename="{evaluation_id}-report.json"'} if download else {}
        return PlainTextResponse(rp.render_json(doc), media_type="application/json", headers=headers)

    @r.get("/{evaluation_id}/report.md")
    def report_md(evaluation_id: str, download: bool = False) -> PlainTextResponse:
        doc = report_doc(evaluation_id)
        headers = {"Content-Disposition": f'attachment; filename="{evaluation_id}-report.md"'} if download else {}
        return PlainTextResponse(rp.render_markdown(doc), media_type="text/markdown; charset=utf-8", headers=headers)

    return r
