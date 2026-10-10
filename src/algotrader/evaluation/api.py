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

from ..corpus import presets as ps
from ..corpus import state
from ..corpus.plan import load_plan
from ..observe import control
from ..observe import diagnostics as diag
from ..observe.api import REPLAY_SELECT, replay_view, storage_facts
from ..observe.deep_api import assurance_summary
from ..observe.contracts import SourceKind
from ..observe.sources import SourceRejected
from . import report as rp

PRESET = "observation-only"
PRESET_LABEL = "Market replay — data and engine check"
ADVISER_PRESET = "adviser-evaluation"
ADVISER_LABEL = "Adviser evaluation"


class StartEvaluation(BaseModel):
    chunk_id: str | None = Field(default=None, min_length=1, max_length=100)  # earlier single-month workflow
    pack_id: str | None = Field(default=None, min_length=1, max_length=100)  # prepared evaluation pack (R3)
    acknowledge_limitations: bool = False  # explicit Owner acknowledgement for a READY_WITH_LIMITATIONS pack
    run_type: str = Field(default="observation_only", pattern="^(observation_only|adviser_evaluation)$")
    method: str | None = Field(default=None, pattern="^v0\\.[23456]$")  # adviser release; absent = v0.2 default
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


def pack_snapshot(c, data_root: Path, pack_id: str, acknowledged: bool) -> dict[str, Any]:
    """Pack facts frozen into the evaluation at launch (identities, windows, coverage, capabilities, limits)."""
    from ..corpus import pack as pk

    rec = pk.pack_receipt(c, pack_id)
    doc = pk.open_pack(data_root, pack_id, rec)
    job = c.execute("SELECT job_id, outcome, started_at, finished_at, children, base_url FROM corpus_pack_jobs "
                    "WHERE pack_id = %s ORDER BY created_at LIMIT 1", (pack_id,)).fetchone()
    st = doc["storage"]
    downloaded = [x for x in (job["children"] if job else []) if x.get("status") == "completed"]
    return {
        "plan_id": doc["presets_schema"], "plan_version": doc["presets_version"],
        "chunk_id": doc["preset"]["preset_id"], "chunk_label": doc["preset"]["label"],
        "start": doc["requested_start"], "end": doc["requested_end"],
        "dataset_id": pack_id, "manifest_sha256": rec["manifest_sha256"], "base_url": job["base_url"] if job else None,
        "quality_status": "clean" if doc["status"] == "READY" else "degraded",
        "verified_at": rec["created_at"].isoformat(), "retrieved_at": None,
        "bytes_on_disk": (st.get("source_package_bytes") or 0) + (st.get("pack_cache_bytes") or 0),
        "storage": {"total_bytes": (st.get("source_package_bytes") or 0) + (st.get("pack_cache_bytes") or 0),
                    "source_package_bytes": st.get("source_package_bytes"),
                    "pack_cache_bytes": st.get("pack_cache_bytes")},
        "binding_outcome": job["outcome"] if job else None,
        "acquisition": ({"job_id": job["job_id"], "outcome": job["outcome"],
                         "elapsed_seconds": ((job["finished_at"] - job["started_at"]).total_seconds()
                                             if job["started_at"] and job["finished_at"] else None),
                         "downloaded_children": len(downloaded),
                         "bytes_fetched": sum(x.get("bytes") or 0 for x in downloaded)} if job else None),
        "pack": {k: doc[k] for k in ("pack_id", "preset", "preset_sha256", "method", "rules_version", "register_sha256",
                                     "capability_profile", "capability_profile_sha256", "windows", "boundaries",
                                     "evidence_classes", "requested_start", "requested_end", "tail_end", "clock_end",
                                     "instrument", "sources", "feed", "coverage", "overlap", "capabilities",
                                     "input_readiness_preview", "status", "limitations", "storage")}
                | {"manifest_sha256": rec["manifest_sha256"], "acknowledged_limitations": acknowledged},
    }


def adviser_section(c, ev: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any] | None:
    """Adviser report section from committed records (any job state); None for observation-only evaluations."""
    if ev["run_type"] != "adviser_evaluation":
        return None
    eng = replay.get("engine") or {}
    if not eng.get("adviser"):
        return {"section": "ADVISER_EVALUATION", "pending": True,
                "text": "adviser configuration is pinned by the worker-owned preparation (not yet prepared)"}
    from ..adviser import report as ar
    from ..adviser import report3 as ar3

    rid = replay["replay_id"]
    journal = c.execute("SELECT seq, kind, clock_time, record FROM adviser_journal WHERE run_id = %s ORDER BY seq",
                        (rid,)).fetchall()
    for e in journal:
        e["clock_time"] = e["clock_time"].isoformat()
    records = c.execute("SELECT seq, kind, record FROM adviser_evaluation_records WHERE run_id = %s ORDER BY seq",
                        (rid,)).fetchall()
    view = c.execute("SELECT adviser_view FROM observation_checkpoints WHERE replay_id = %s", (rid,)).fetchone()
    fin = c.execute("SELECT 1 FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
    from ..adviser import report4 as ar4
    from ..adviser import report5 as ar5
    from ..adviser import report6 as ar6

    key = eng["adviser"].get("method")
    builder = {"v0.6": ar6, "v0.5": ar5, "v0.4": ar4, "v0.3": ar3}.get(key, ar)
    return builder.build(engine=eng, journal=journal, records=records, view=(view or {}).get("adviser_view"),
                    status=replay["status"], clock_end_reached=fin is not None)


def build_router(conn: Callable, data_root: Path, art_root: Path) -> APIRouter:
    r = APIRouter(prefix="/api/evaluations")

    def get(c, evaluation_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        ev = c.execute("SELECT * FROM evaluations WHERE evaluation_id = %s", (evaluation_id,)).fetchone()
        if ev is None:
            raise HTTPException(404, f"evaluation {evaluation_id} not found")
        replay = c.execute(REPLAY_SELECT + " WHERE r.replay_id = %s", (ev["replay_id"],)).fetchone()
        return ev, replay

    def view(ev: dict[str, Any], replay: dict[str, Any], c=None) -> dict[str, Any]:
        rv = replay_view(replay)
        if c is not None:
            rv["assurance_summary"] = assurance_summary(c, replay["replay_id"], rv["operation"]["assurance"],
                                                        rv["status"])
        terminal = rv["status"] in control.TERMINAL
        adviser = ev["run_type"] == "adviser_evaluation"
        method = None
        if adviser:
            from ..adviser import methods

            pinned = ((replay.get("engine") or {}).get("adviser") or {})
            key = pinned.get("method") or (replay.get("launch") or {}).get("adviser_method") or "v0.2"
            rel = methods.get(key)
            method = {"method": key, "label": rel.label, "status": rel.status, "status_label": rel.status_label,
                      "model": rel.model, "pinned_at_preparation": bool(pinned),
                      "economic_usefulness": "UNVALIDATED"}
        return {
            "method": method,
            "evaluation_id": ev["evaluation_id"],
            "run_type": ev["run_type"],
            "run_type_label": ADVISER_LABEL if adviser else PRESET_LABEL,
            "preset": ev["preset"],
            "notice": rp.ADVISER_NOTICE if adviser else rp.NOT_CONNECTED,
            "created_at": ev["created_at"].isoformat(),
            "corpus": ev["corpus"],
            "replay": rv,
            # a report (or a diagnostic snapshot) is always available; it is terminal only when the run is
            "report_available": True,
            "report_terminal": terminal,
        }

    def start_pack(body: StartEvaluation) -> dict[str, Any]:
        from ..corpus import pack as pk

        with conn() as c:
            try:
                snapshot = pack_snapshot(c, data_root, body.pack_id, body.acknowledge_limitations)
            except pk.PackError as exc:
                raise HTTPException(409, f"pack {body.pack_id} is not usable: {exc}") from None
            p = snapshot["pack"]
            if p["status"] == "READY_WITH_LIMITATIONS" and not body.acknowledge_limitations:
                raise HTTPException(409, "this pack is READY WITH LIMITATIONS (source gaps); acknowledge the listed "
                                         "limitations to start an inspection run: " + "; ".join(p["limitations"]))
            adviser = body.run_type == "adviser_evaluation"
            if body.method is not None and not adviser:
                raise HTTPException(422, "a method is selected only for an adviser evaluation")
            if adviser and any(x["class"] != "DEVELOPMENT" for x in p["evidence_classes"].get("portions", [])):
                raise HTTPException(409, "protected (Jan-Aug 2026) evaluation is not enabled before the Director's "
                                         "contamination inventory and model freeze; choose a development pack")
            if p["evidence_classes"].get("label") == ps.STUDY_EVIDENCE_CLASS:
                # a registered study window admits only the run its study registers (still registered now)
                study = ps.registered_study(ps.Preset.model_validate(p["preset"]))
                if study is None:
                    raise HTTPException(409, "this pack's study window is no longer a registered study preset")
                if not adviser or (body.method or "v0.2") != study.method:
                    raise HTTPException(409, f"the registered study window {study.study_id} admits only an adviser "
                                             f"evaluation with method {study.method}")
            c.commit()
            evaluation_id = new_evaluation_id()
            try:
                with c.transaction():
                    replay_id = control.create_replay(c, data_root, SourceKind.PACK, body.pack_id, body.speed,
                                                      body.paused, evaluation_id=evaluation_id,
                                                      expected_manifest_sha256=snapshot["manifest_sha256"],
                                                      run_type="adviser_evaluation" if adviser else "observation",
                                                      adviser_method=(body.method or "v0.2") if adviser else None)
                    c.execute(
                        """INSERT INTO evaluations (evaluation_id, replay_id, run_type, preset, plan_id, chunk_id,
                               dataset_id, corpus, pack_id, preset_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (evaluation_id, replay_id, body.run_type, ADVISER_PRESET if adviser else PRESET,
                         snapshot["plan_id"], snapshot["chunk_id"], body.pack_id, Jsonb(snapshot), body.pack_id,
                         snapshot["chunk_id"]))
            except (SourceRejected, control.ControlRejected) as exc:
                raise HTTPException(422, str(exc)) from None
            return view(*get(c, evaluation_id), c)

    @r.post("", status_code=201)
    def start(body: StartEvaluation) -> dict[str, Any]:
        if (body.pack_id is None) == (body.chunk_id is None):
            raise HTTPException(422, "give exactly one of pack_id (evaluation pack) or chunk_id (single month)")
        if body.pack_id is not None:
            return start_pack(body)
        if body.run_type == "adviser_evaluation":
            raise HTTPException(422, "an adviser evaluation needs a prepared evaluation pack (pack_id)")
        plan = load_plan()
        chunk = plan.chunk(body.chunk_id)
        if chunk is None:
            raise HTTPException(404, f"chunk {body.chunk_id} is not in the corpus plan")
        with conn() as c:
            binding = c.execute("SELECT * FROM corpus_chunks WHERE chunk_id = %s", (chunk.chunk_id,)).fetchone()
            usable, problem = state.binding_state_cheap(data_root, binding)
            if not usable:
                raise HTTPException(409, f"{chunk.chunk_id} is not prepared" + (f": {problem}" if problem else ""))
            snapshot = corpus_snapshot(c, plan, chunk, binding)
            c.commit()  # end the read transaction; the launch below is one atomic transaction
            evaluation_id = new_evaluation_id()
            try:
                with c.transaction():
                    # durable launch only (<=1 s): the worker-owned preparation re-checks the bound manifest
                    # hash, re-verifies the dataset and builds its feed as visible, cancellable phases
                    replay_id = control.create_replay(c, data_root, SourceKind.DATASET, binding["dataset_id"],
                                                      body.speed, body.paused, evaluation_id=evaluation_id,
                                                      expected_manifest_sha256=binding["manifest_sha256"])
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
            return view(*get(c, evaluation_id), c)

    @r.get("")
    def list_evaluations(limit: int = 20) -> list[dict[str, Any]]:
        with conn() as c:
            evs = c.execute("SELECT * FROM evaluations ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
            return [view(ev, c.execute(REPLAY_SELECT + " WHERE r.replay_id = %s", (ev["replay_id"],)).fetchone())
                    for ev in evs]

    def compare_doc(a: str, b: str) -> dict[str, Any]:
        """Read-only comparison of two existing adviser evaluations (never launches, resumes or replays)."""
        from ..adviser import compare as cmp

        facts = []
        for eid in (a, b):
            doc = report_doc(eid)
            with conn() as c:
                ev, replay = get(c, eid)
            facts.append(cmp.run_facts(ev, replay, doc))
        return cmp.build(facts[0], facts[1])

    @r.get("/compare/report.json")
    def compare_json(a: str, b: str, download: bool = False) -> PlainTextResponse:
        doc = compare_doc(a, b)
        headers = {"Content-Disposition": f'attachment; filename="compare-{a}-{b}.json"'} if download else {}
        return PlainTextResponse(rp.render_json(doc), media_type="application/json", headers=headers)

    @r.get("/compare/report.md")
    def compare_md(a: str, b: str, download: bool = False) -> PlainTextResponse:
        from ..adviser import compare as cmp

        doc = compare_doc(a, b)
        headers = {"Content-Disposition": f'attachment; filename="compare-{a}-{b}.md"'} if download else {}
        return PlainTextResponse(cmp.render_markdown(doc), media_type="text/markdown; charset=utf-8", headers=headers)

    @r.get("/{evaluation_id}")
    def detail(evaluation_id: str) -> dict[str, Any]:
        with conn() as c:
            return view(*get(c, evaluation_id), c)

    def report_doc(evaluation_id: str) -> dict[str, Any]:
        with conn() as c:
            ev, replay = get(c, evaluation_id)
        now = datetime.now(UTC)
        with conn() as c:
            storage = storage_facts(c, replay["replay_id"])
            adviser = adviser_section(c, ev, replay)
        return rp.build_report(ev, replay, replay["manifest"], diag.operation(replay, now),
                               diag.diagnostic_report(replay, art_root, now, ev, storage), now, adviser=adviser)

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
