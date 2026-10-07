"""Evaluation-pack API (``/api/corpus/presets``, ``/selection``, ``/pack-jobs``, ``/packs``).

Opening these views never touches the network: they read the checked-in presets, local package manifests and
PostgreSQL state. Only an explicit Prepare (POST) records a durable pack job for the corpus worker.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from . import pack as pk
from . import pack_job as pj
from . import presets as ps

NO_NETWORK_NOTE = "Opening this page downloads nothing. Only the Prepare button starts a durable preparation."


class Selection(BaseModel):
    months: list[str] = Field(min_length=1, max_length=12)


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def selectable_months(f: ps.PresetsFile) -> list[dict]:
    out, t = [], f.target.start
    while t < f.target.end:
        cls = "PROTECTED_PROVISIONAL" if f.protected_provisional.start <= t < f.protected_provisional.end else \
            "DEVELOPMENT"
        out.append({"month": f"{t:%Y-%m}", "label": f"{t:%B %Y}", "class": cls})
        t = ps.add_months(t, 1)
    return out


def published_view(c, data_root: Path, preset_sha: str) -> dict | None:
    rec = c.execute("SELECT * FROM corpus_packs WHERE preset_sha256 = %s ORDER BY created_at DESC LIMIT 1",
                    (preset_sha,)).fetchone()
    if rec is None:
        return None
    try:
        doc = pk.open_pack(data_root, rec["pack_id"], rec)
        usable, problem = True, None
    except pk.PackError as exc:
        doc, usable, problem = None, False, str(exc)
    return {"pack_id": rec["pack_id"], "usable": usable, "problem": problem, "status": rec["status"],
            "created_at": rec["created_at"].isoformat(), "event_count": rec["event_count"],
            "manifest_sha256": rec["manifest_sha256"],
            "limitations": doc["limitations"] if doc else [], "coverage": doc["coverage"] if doc else [],
            "capabilities": doc["capabilities"] if doc else [],
            "sources": doc["sources"] if doc else [], "storage": doc["storage"] if doc else None,
            "overlap": doc["overlap"] if doc else None,
            "input_readiness_preview": doc["input_readiness_preview"] if doc else None,
            "feed": doc["feed"] if doc else None, "clock_end": doc["clock_end"] if doc else None}


def preset_view(c, data_root: Path, f: ps.PresetsFile, p: ps.Preset) -> dict[str, Any]:
    sha = ps.preset_sha256(f, p)
    bound = {r["dataset_id"] for r in c.execute("SELECT dataset_id FROM corpus_chunks").fetchall()}
    sources = pk.local_sources(data_root, f.instrument, bound)
    plan = pk.plan_slices(sources, p.warmup.start, p.tail.end, f.acquisition_max_span_days)
    job = c.execute("SELECT * FROM corpus_pack_jobs WHERE preset_sha256 = %s ORDER BY created_at DESC LIMIT 1",
                    (sha,)).fetchone()
    return {
        "preset": ps.preset_doc(p), "preset_sha256": sha, "windows": ps.windows_doc(p),
        "classification": ps.classify(f, p),
        "local": [{"dataset_id": s.dataset_id, "start": pk._iso(s.start), "end": pk._iso(s.end)} for s in plan.slices],
        "needed": [{"start": pk._iso(a), "end": pk._iso(b)} for a, b in plan.acquisitions],
        "estimate": pk.estimate_bytes(sources, plan.acquisitions),
        "published": published_view(c, data_root, sha),
        "latest_job": job_view(job) if job else None,
        "note": NO_NETWORK_NOTE,
        "adviser": "not implemented: this pack feeds a data and engine check only",
    }


def job_view(row: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    from .api import operation

    now = now or datetime.now(UTC)
    p = dict(row["progress"] or {})
    children = list(row["children"] or [])
    done = [x for x in children if x.get("status") == "completed"]
    return {
        "operation": operation(row, now, pj.PACK_PHASES), "job_id": row["job_id"], "preset_id": row["preset_id"],
        "preset_sha256": row["preset_sha256"], "status": row["status"], "cancel_requested": row["cancel_requested"],
        "base_url": row["base_url"], "created_at": row["created_at"].isoformat(),
        "started_at": _iso(row["started_at"]), "finished_at": _iso(row["finished_at"]),
        "attempt": row["attempt"], "max_attempts": row["max_attempts"], "recovery_log": row["recovery_log"],
        "diagnostic_log": row["diagnostic_log"], "recovery_behavior": pj.RECOVERY_BEHAVIOR,
        "outcome": row["outcome"], "pack_id": row["pack_id"], "plan": row["plan"], "children": children,
        "downloaded": {"children": len(done), "bytes": sum(x.get("bytes") or 0 for x in done)},
        "result": row["result"], "error": row["error"],
        "progress": {k: v for k, v in p.items() if k != "work_dir"},
    }


def job_report(row: dict[str, Any], data_root: Path, now: datetime) -> dict[str, Any]:
    v = job_view(row, now)
    terminal = row["status"] in pj.TERMINAL
    f = ps.load_presets()
    preset = ps.Preset.model_validate(row["preset"])
    doc = None  # the route fills the published pack facts from its receipt (see ``add_routes.report``)
    plan = row["plan"] or {}
    return {
        "report_kind": "EVALUATION_PACK_PREPARATION", "report_format": "algotrader.pack-report.v1",
        "snapshot": not terminal, "captured_at": None if terminal else now.isoformat(),
        "job_id": row["job_id"], "status": row["status"], "outcome": row["outcome"], "pack_id": row["pack_id"],
        "operation": {k: v["operation"][k] for k in ("phase", "phase_label", "health", "health_detail", "progress",
                                                       "generation", "attempt")},
        "identities": {"preset_id": preset.preset_id, "preset_sha256": row["preset_sha256"],
                       "presets": f"{f.schema_version} v{f.version}", "method": f.method,
                       "rules_version": f.rules_version, "register_sha256": ps.MP001_REGISTER_SHA256,
                       "capability_profile": f.capability_profile,
                       "capability_profile_sha256": ps.capability_profile_sha256(f)},
        "windows": ps.windows_doc(preset), "classification": ps.classify(f, preset),
        "plan": {"local_slices": plan.get("slices"), "needed": plan.get("acquisitions"),
                 "estimate": plan.get("estimate")},
        "children": v["children"], "downloaded": v["downloaded"],
        "pack": ({"status": doc["status"], "event_count": doc["feed"]["event_count"],
                  "content_identity": doc["feed"]["content_identity"], "sources": doc["sources"],
                  "coverage": doc["coverage"], "capabilities": doc["capabilities"], "limitations": doc["limitations"],
                  "overlap": doc["overlap"], "storage": doc["storage"],
                  "input_readiness_preview": doc["input_readiness_preview"],
                  "clock_end": doc["clock_end"], "tail_end": doc["tail_end"]} if doc else None),
        "assurance": ("every source package verified once through the receipt-pinned cache boundary; the pack manifest "
                      "and its feed cache are pinned by publication receipts. Data preparation never certifies adviser "
                      "readiness, uncontaminated economic evidence or trading performance."),
        "recovery_log": row["recovery_log"], "diagnostic_log": row["diagnostic_log"],
        "recovery_behavior": pj.RECOVERY_BEHAVIOR, "error": row["error"],
        "next_step": ("Start the data and engine check on this pack (observation only; no adviser)."
                      if row["status"] == "completed" else
                      "Prepare again to retry; completed children are reused." if terminal else
                      "In progress: this is a snapshot. Copy again later."),
        "adviser_metrics": "UNAVAILABLE: no adviser exists",
    }


def render_job_report(r: dict[str, Any]) -> str:
    op, ids, w = r["operation"], r["identities"], r["windows"]
    lines = [f"# Evaluation pack preparation — {'DIAGNOSTIC SNAPSHOT' if r['snapshot'] else 'terminal report'}", "",
             f"**{r['report_kind']}** · job `{r['job_id']}` · status **{r['status'].upper()}**"
             + (f" · outcome {r['outcome']}" if r["outcome"] else "") + (f" · captured {r['captured_at']}"
                                                                          if r["captured_at"] else ""),
             "", "> Data preparation only. No adviser exists; nothing is scored.", "",
             "## Identities",
             f"- Preset `{ids['preset_id']}` (`{ids['preset_sha256'][:16]}`) · {ids['presets']} · method "
             f"{ids['method']} / {ids['rules_version']} (register `{ids['register_sha256'][:12]}`, input requirements "
             f"only) · profile `{ids['capability_profile_sha256'][:12]}`",
             f"- Classification: {r['classification']['label']} — {r['classification']['note']}",
             "## Windows (UTC, half-open)",
             (f"- Initialization {w['warmup']['start']} → {w['warmup']['end']} ({w['initialization']['hours']} h; "
              "context only, not evaluated)" if w.get("initialization") else
              f"- Warmup {w['warmup']['start']} → {w['warmup']['end']} (unscored)"),
             f"- Evaluation {w['evaluation']['start']} → {w['evaluation']['end']} (scored later, by an adviser)",
             f"- Tail {w['tail']['start']} → {w['tail']['end']} (unscored)",
             "## Sources",
             f"- Already local: {len(r['plan']['local_slices'] or [])} slice(s); needed downloads: "
             f"{len(r['plan']['needed'] or [])} ({(r['plan']['estimate'] or {}).get('basis', '—')})",
             f"- Downloaded: {r['downloaded']['children']} child package(s), {r['downloaded']['bytes']:,} bytes"]
    for ch in r["children"]:
        lines.append(f"  - child {ch['start']} → {ch['end']}: {ch['status']}"
                     + (f" · {ch.get('dataset_id')}" if ch.get("dataset_id") else "")
                     + (f" · {ch.get('error')}" if ch.get("error") else ""))
    lines += ["## Progress", f"- Phase {op['phase'] or '—'} ({op['phase_label']}) · health {op['health']} · "
                             f"generation {op['generation']} · attempt {op['attempt']}"]
    pkd = r["pack"]
    if pkd:
        lines += ["## Pack", f"- `{r['pack_id']}` · **{pkd['status']}** · {pkd['event_count']:,} canonical events · "
                             f"content `{pkd['content_identity'][:28]}…` · clock end {pkd['clock_end']}",
                  f"- Storage: sources {pkd['storage'].get('source_package_bytes'):,} bytes (referenced) · pack "
                  f"cache {pkd['storage'].get('pack_cache_bytes'):,} bytes (added)",
                  f"- Overlap: {pkd['overlap']['overlapping_slots']} slot(s), {pkd['overlap']['identical_collapsed']} "
                  f"identical collapsed, {pkd['overlap']['gap_replaced_by_valid']} gap(s) superseded"]
        for c in pkd["coverage"]:
            if c["expected_slots"] is not None:
                lines.append(f"  - {c['family']} {c['window']}: {c['valid']}/{c['expected_slots']} usable · missing "
                             f"{c['missing']} · rejected {c['rejected']}")
            else:
                lines.append(f"  - {c['family']} {c['window']}: {c['valid']} settlement row(s) (not completeness "
                             "proof)")
        lines += [f"- {x['capability']}: {x['status']}" for x in pkd["capabilities"]]
        lines += [f"- Limitation: {x}" for x in pkd["limitations"]]
    if r["error"]:
        lines += ["## Error", f"- {r['error']}"]
    lines += ["", f"Next step: {r['next_step']}", f"Adviser metrics: {r['adviser_metrics']}", "",
              f"_{r['report_format']}_", ""]
    return "\n".join(lines)


def add_routes(r: APIRouter, conn: Callable, data_root: Path) -> None:
    def get_job(c, job_id: str) -> dict[str, Any]:
        row = c.execute("SELECT * FROM corpus_pack_jobs WHERE job_id = %s", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"pack job {job_id} not found")
        return row

    def resolve(months: list[str] | None = None, preset_id: str | None = None) -> tuple[ps.PresetsFile, ps.Preset]:
        f = ps.load_presets()
        try:
            return f, ps.resolve(f, preset_id, months)
        except ps.PresetError as exc:
            raise HTTPException(422, str(exc)) from None

    @r.get("/presets")
    def presets() -> dict[str, Any]:
        f = ps.load_presets()
        with conn() as c:
            views = [preset_view(c, data_root, f, p) for p in f.presets]
        return {"file": {"schema_version": f.schema_version, "version": f.version, "method": f.method,
                         "rules_version": f.rules_version, "register_sha256": ps.MP001_REGISTER_SHA256,
                         "capability_profile": f.capability_profile, "boundaries": f.boundaries,
                         "target": {"start": f.target.start.isoformat(), "end": f.target.end.isoformat()},
                         "development": {"start": f.development.start.isoformat(),
                                         "end": f.development.end.isoformat()},
                         "protected": {"start": f.protected_provisional.start.isoformat(),
                                       "end": f.protected_provisional.end.isoformat(),
                                       "contamination": f.protected_provisional.contamination}},
                "presets": views, "months": selectable_months(f), "note": NO_NETWORK_NOTE}

    @r.get("/selection")
    def selection(months: str) -> dict[str, Any]:
        f, p = resolve([m.strip() for m in months.split(",") if m.strip()])
        with conn() as c:
            return preset_view(c, data_root, f, p)

    def prepare_preset(f: ps.PresetsFile, p: ps.Preset) -> dict[str, Any]:
        with conn() as c:
            try:
                job_id = pj.create_pack_job(c, f, p)
            except pj.PackJobRejected as exc:
                raise HTTPException(409 if "active" in str(exc) else 422, str(exc)) from None
            return job_view(get_job(c, job_id))

    @r.post("/presets/{preset_id}/prepare", status_code=201)
    def prepare(preset_id: str) -> dict[str, Any]:
        f, p = resolve(preset_id=preset_id)
        return prepare_preset(f, p)

    @r.post("/selection/prepare", status_code=201)
    def prepare_selection(body: Selection) -> dict[str, Any]:
        f, p = resolve(body.months)
        return prepare_preset(f, p)

    @r.get("/pack-jobs")
    def pack_jobs(limit: int = 20) -> list[dict[str, Any]]:
        with conn() as c:
            rows = c.execute("SELECT * FROM corpus_pack_jobs ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
        return [job_view(x) for x in rows]

    @r.get("/pack-jobs/{job_id}")
    def pack_job(job_id: str) -> dict[str, Any]:
        with conn() as c:
            return job_view(get_job(c, job_id))

    @r.post("/pack-jobs/{job_id}/cancel")
    def cancel(job_id: str) -> dict[str, Any]:
        with conn() as c:
            try:
                pj.cancel_pack_job(c, job_id)
            except LookupError:
                raise HTTPException(404, f"pack job {job_id} not found") from None
            except pj.PackJobRejected as exc:
                raise HTTPException(409, str(exc)) from None
            return job_view(get_job(c, job_id))

    def report(job_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        with conn() as c:
            row = get_job(c, job_id)
            doc = job_report(row, data_root, now)
            if row["pack_id"]:
                try:
                    pd = pk.open_pack(data_root, row["pack_id"], pk.pack_receipt(c, row["pack_id"]))
                    doc["pack"] = {"status": pd["status"], "event_count": pd["feed"]["event_count"],
                                   "content_identity": pd["feed"]["content_identity"], "sources": pd["sources"],
                                   "coverage": pd["coverage"], "capabilities": pd["capabilities"],
                                   "limitations": pd["limitations"], "overlap": pd["overlap"], "storage": pd["storage"],
                                   "input_readiness_preview": pd["input_readiness_preview"],
                                   "clock_end": pd["clock_end"], "tail_end": pd["tail_end"]}
                except pk.PackError as exc:
                    doc["pack"] = None
                    doc["error"] = (doc["error"] or "") + f" (published pack not trustworthy now: {exc})"
        return doc

    @r.get("/pack-jobs/{job_id}/report.json")
    def report_json(job_id: str, download: bool = False) -> PlainTextResponse:
        headers = {"Content-Disposition": f'attachment; filename="{job_id}-report.json"'} if download else {}
        return PlainTextResponse(json.dumps(report(job_id), indent=2, sort_keys=True, default=str) + "\n",
                                 media_type="application/json", headers=headers)

    @r.get("/pack-jobs/{job_id}/report.md")
    def report_md(job_id: str, download: bool = False) -> PlainTextResponse:
        headers = {"Content-Disposition": f'attachment; filename="{job_id}-report.md"'} if download else {}
        return PlainTextResponse(render_job_report(report(job_id)), media_type="text/markdown; charset=utf-8",
                                 headers=headers)

    @r.get("/packs")
    def packs() -> list[dict[str, Any]]:
        with conn() as c:
            rows = c.execute("SELECT * FROM corpus_packs ORDER BY created_at DESC").fetchall()
            out = []
            for rec in rows:
                try:
                    pk.open_pack(data_root, rec["pack_id"], rec)
                    usable, problem = True, None
                except pk.PackError as exc:
                    usable, problem = False, str(exc)
                out.append({"pack_id": rec["pack_id"], "preset_id": rec["preset_id"], "status": rec["status"],
                            "event_count": rec["event_count"], "created_at": rec["created_at"].isoformat(),
                            "usable": usable, "problem": problem})
        return out

    @r.get("/packs/{pack_id}")
    def pack_detail(pack_id: str) -> dict[str, Any]:
        with conn() as c:
            rec = pk.pack_receipt(c, pack_id)
        try:
            return {"manifest": pk.open_pack(data_root, pack_id, rec), "receipt_manifest_sha256":
                    rec["manifest_sha256"] if rec else None}
        except pk.PackError as exc:
            raise HTTPException(409 if rec else 404, str(exc)) from None
