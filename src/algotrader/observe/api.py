"""Real-market observation-replay API (``/api/observations``), separate from synthetic ``/api/runs``.

The API only records commands and reads persisted state; the observation worker
owns execution. Nothing here reads or writes synthetic semantic.v1 run data.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..marketdata import dataset as md
from ..recorder import journal as rj
from .. import version
from . import control
from . import diagnostics as diag
from .artifacts import files_dir
from .contracts import LABELS, ObservationReplayConfig, SourceKind
from .deep_api import assurance_summary
from .feedcache import CacheError, CacheReader, decode, open_cache
from .kernel import STREAM_ENGINE_FORMATS
from .sources import MODELED_LABEL, RECORDED_LABEL, SourceRejected, locate_source

REPLAY_SELECT = """
SELECT r.*, c.cursor AS applied, c.info_time, c.last_event_id, c.snapshot_id, c.snapshot_digest, c.temporal_view,
       c.adviser_view
FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id)
"""


class StartObservation(BaseModel):
    source_kind: SourceKind
    source_id: str = Field(min_length=1, max_length=200)
    speed: float = Field(default=20.0, ge=0, le=control.MAX_SPEED)
    paused: bool = False


class SetSpeed(BaseModel):
    speed: float = Field(ge=0, le=control.MAX_SPEED)


def _pending_source(row: dict[str, Any]) -> dict[str, Any]:
    """Source facts before preparation: only what the launch envelope genuinely knows."""
    return {"kind": row["source_kind"], "source_id": row["source_id"], "source_schema": None, "inst_id": None,
            "index_id": None, "source_status": "PENDING", "coverage": [], "warnings": [], "exclusions": [],
            "notes": ["source verification and feed construction run as durable worker-owned phases"],
            "pending": True}


def replay_view(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    cfg = ObservationReplayConfig.model_validate(row["config"]) if row["config"] is not None else None
    applied = row.get("applied") or 0
    hb = row["heartbeat_at"]
    op = diag.operation(row, now)
    lease_expired = bool(row["status"] == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)
    state, detail = diag.runtime_state(row, lease_expired)
    pol = cfg.availability_policy if cfg else None
    eta = op["eta"]
    return {
        "replay_id": row["replay_id"],
        "kind": "market_observation_replay",
        "run_type": (row.get("launch") or {}).get("run_type", "observation"),
        "run_type_label": ("Adviser evaluation" if (row.get("launch") or {}).get("run_type") == "adviser_evaluation"
                           else "Market replay — data and engine check"),
        "status": row["status"],
        "runtime_state": state.value,
        "runtime_detail": detail,
        "configured": cfg is not None,
        "source": json.loads(cfg.source.model_dump_json()) if cfg else _pending_source(row),
        "verification": json.loads(cfg.verification.model_dump_json()) if cfg else None,
        "availability": ({"basis": pol.basis.value, "policy_id": pol.policy_id, "measured": pol.measured,
                          "label": cfg.availability_label, "note": pol.note} if cfg else None),
        "freshness_policy": json.loads(cfg.freshness_policy.model_dump_json()) if cfg else None,
        "feed": json.loads(cfg.feed.model_dump_json()) if cfg else None,
        "clock_policy": cfg.clock_policy if cfg else None,
        "control": {"paused": row["paused"], "step_budget": row["step_budget"], "speed": row["speed"],
                    "unit": "events/s"},
        "created_at": row["created_at"].isoformat(),
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
        "cancel_requested": row["cancel_requested"],
        "attempt": row["attempt"],
        "max_attempts": row["max_attempts"],
        "recovery_log": row["recovery_log"],
        "control_log": row["control_log"],
        "error": row["error"],
        "lease_owner": row["lease_owner"],
        "lease_expired": lease_expired,
        "has_manifest": row["manifest"] is not None,
        "validation_passed": row["manifest"]["validation"]["passed"] if row["manifest"] else None,
        "progress": {
            "applied_events": applied,
            # committed = durable checkpoint cursor (the only admission boundary, survives crashes); computed = the
            # compute process's in-memory cursor reported with progress (may run ahead until the next commit)
            "committed_events": applied,
            "computed_events": max(applied, int((row["progress"] or {}).get("done") or 0))
            if row["phase"] == "REPLAYING" and (row["progress"] or {}).get("unit") == "events" else applied,
            "total_events": row["total_events"],
            "information_time": row["info_time"].isoformat() if row.get("info_time") else None,
            "last_event_id": row.get("last_event_id"),
            "snapshot_id": row.get("snapshot_id"),
            "snapshot_digest": row.get("snapshot_digest"),
            "heartbeat_age_seconds": (now - hb).total_seconds() if hb else None,
            "elapsed_seconds": (((row["finished_at"] or now) - row["started_at"]).total_seconds()
                                if row["started_at"] else None),
            "eta_seconds": eta["seconds"] if op["phase"] == "REPLAYING" else None,
            "eta_basis": eta["basis"] if op["phase"] == "REPLAYING" else (
                "replay ETA applies only while REPLAYING; see the current-phase ETA"),
        },
        "operation": op,
        "code_version": (cfg.code_version if cfg else (row.get("launch") or {}).get("code_version")),
        "code_version_label": version.describe(cfg.code_version if cfg else (row.get("launch") or {}).get(
            "code_version")),
        "labels": list(cfg.labels) if cfg else list(LABELS),
        "temporal": temporal_view(row),
        "adviser": adviser_view(row),
    }


def adviser_view(row: dict[str, Any]) -> dict[str, Any] | None:
    """Committed professional inspection of an adviser evaluation run (latest committed checkpoint view)."""
    adv = (row.get("engine") or {}).get("adviser")
    if not adv:
        return ({"pending": True, "note": "adviser configuration is pinned by the worker-owned preparation"}
                if (row.get("launch") or {}).get("run_type") == "adviser_evaluation" else None)
    v = row.get("adviser_view") or {}
    return {"identity": {k: adv["identity"][k] for k in ("model", "rules_version", "rules_sha256", "register_sha256",
                                                          "implementation", "capability_profile_sha256",
                                                          "identity_sha256")},
            "profile": adv["profile"], "windows": {"warmup_start": adv["warmup_start"], "evaluation_start":
                                                   adv["eval_start"], "evaluation_end": adv["eval_end"],
                                                   "tail_end": adv["tail_end"], "clock_end": adv["clock_end"]},
            "committed": {k: v.get(k) for k in ("clock", "window", "origin", "view", "call", "recent_calls",
                                                "attempts", "box", "lenses", "readiness", "journal_seq",
                                                "professional_seq")} if v else None,
            "counters": (v.get("counters") or {}) if v else None,
            "note": "committed adviser state at the latest checkpoint; hypothetical outcomes are separate"}


def temporal_view(row: dict[str, Any]) -> dict[str, Any] | None:
    """Committed temporal substrate inspection (R2 runs): pinned configuration + the view committed with the latest
    checkpoint. Factual infrastructure only - no adviser, no interpretation. None for runs without it."""
    tc = (row.get("engine") or {}).get("temporal")
    if not tc:
        return None
    return {"note": "temporal substrate only; no adviser", "contract": tc["contract"],
            "contract_revision": tc["contract_revision"], "profile_id": tc["profile"]["profile_id"],
            "profile_fingerprint": tc["fingerprint"], "clock_policy": tc["clock_policy"],
            "seal_policy": tc["seal_policy"], "clock_end": tc["clock_end"],
            "closure_allowance": tc["profile"]["closure_allowance"],
            "committed": row.get("temporal_view")}


MAX_WINDOW = 5000  # bounded inspection windows (events / bars per request)
DEFAULT_BARS = 240


def is_stream(row: dict[str, Any]) -> bool:
    return row.get("engine_format") in STREAM_ENGINE_FORMATS


def _committed_reader(md_root: Path, row: dict[str, Any]) -> tuple[CacheReader, int]:
    """Reader over the pinned feed cache + the committed cursor (the only admission boundary exposed)."""
    eng = row["engine"]
    try:
        cache = open_cache(md_root, eng["cache_id"], expected_manifest_sha256=eng["cache_manifest_sha256"],
                           check_files=False)
    except CacheError as exc:
        raise HTTPException(410, f"feed cache unavailable for inspection: {exc}") from None
    return CacheReader(cache), int(row.get("applied") or 0)


def _delivery_doc(seq: int, e) -> dict[str, Any]:
    return {"seq": seq, "event_id": e.event_id, "channel_id": e.channel.channel_id, "family": e.channel.family.value,
            "kind": e.kind.value, "event_time": e.event_time.isoformat(),
            "event_end_time": e.event_end_time.isoformat() if e.event_end_time else None,
            "available_time": e.available_time.isoformat(), "quality_reason": getattr(e.payload, "reason", None),
            "snapshot_id": None, "snapshot_digest": None, "changes": [],
            "payload": e.payload.model_dump(mode="json"),
            "note": "streaming run: committed feed evidence read from the verified cache; no per-event snapshot"}


def storage_facts(c, replay_id: str) -> dict[str, Any]:
    """Bounded facts about durable storage of one replay (aggregates only)."""
    r = c.execute("SELECT count(*) AS n, max(to_cursor) AS hi FROM observation_ranges WHERE replay_id = %s",
                  (replay_id,)).fetchone()
    rps = c.execute("SELECT cursor, terminal, generation FROM observation_restore_points WHERE replay_id = %s "
                    "ORDER BY cursor", (replay_id,)).fetchall()
    d = c.execute("SELECT count(*) AS n FROM observation_deliveries WHERE replay_id = %s", (replay_id,)).fetchone()
    return {"ranges": r["n"], "ranges_to_cursor": r["hi"], "restore_points": [dict(x) for x in rps],
            "delivery_rows": d["n"]}


def build_router(conn: Callable, md_root: Path, art_root: Path) -> APIRouter:
    r = APIRouter(prefix="/api/observations")

    def get_row(c, replay_id: str) -> dict[str, Any]:
        row = c.execute(REPLAY_SELECT + " WHERE r.replay_id = %s", (replay_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"observation replay {replay_id} not found")
        return row

    # -- sources ----------------------------------------------------------------

    @r.get("/sources")
    def sources() -> dict[str, Any]:
        datasets = []
        for m in md.list_manifests(md_root):
            datasets.append({
                "kind": "dataset", "source_id": m.dataset_id, "inst_id": m.instrument.inst_id,
                "coverage_from": m.request.start.isoformat(), "coverage_until": m.request.end.isoformat(),
                "status": m.quality_status.value if hasattr(m.quality_status, "value") else str(m.quality_status),
                "availability_basis": "MODELED", "replayable": True, "reason": None,
            })
        recordings = []
        for p in rj.list_sessions(md_root):
            if not rj.is_finalized(p):
                recordings.append({"kind": "recording", "source_id": p.name, "status": "not finalized",
                                   "availability_basis": "RECORDED", "replayable": False,
                                   "reason": "still recording or awaiting recovery", "inst_id": None,
                                   "coverage_from": None, "coverage_until": None})
                continue
            m = rj.load_manifest(p)
            failed = m.status.value == "failed"
            recordings.append({
                "kind": "recording", "source_id": m.session_id, "inst_id": m.inst_id,
                "coverage_from": m.started_at.isoformat(), "coverage_until": m.stopped_at.isoformat(),
                "status": m.status.value, "availability_basis": "RECORDED", "replayable": not failed,
                "reason": "FAILED session: no usable market data" if failed else None,
            })
        return {"data_root": str(md_root), "datasets": datasets, "recordings": recordings}

    @r.get("/sources/{kind}/{source_id}")
    def preflight(kind: SourceKind, source_id: str) -> dict[str, Any]:
        """Cheap source preview (no hashing, no feed build). Verification is a durable preparation phase."""
        try:
            path = locate_source(md_root, kind, source_id)
        except SourceRejected as exc:
            raise HTTPException(422, str(exc)) from None
        if kind == SourceKind.DATASET:
            m = md.load_manifest(path)
            facts = {"inst_id": m.instrument.inst_id, "coverage_from": m.request.start.isoformat(),
                     "coverage_until": m.request.end.isoformat(),
                     "source_status": md.load_quality(path).status.value}
            basis, label = "MODELED", MODELED_LABEL
        else:
            m = rj.load_manifest(path)
            facts = {"inst_id": m.inst_id, "coverage_from": m.started_at.isoformat(),
                     "coverage_until": m.stopped_at.isoformat(), "source_status": m.status.value}
            basis, label = "RECORDED", RECORDED_LABEL
        return {
            "source": {"kind": kind.value, "source_id": source_id, **facts},
            "verification": None,
            "verification_note": ("Not verified here: full hash/row verification and feed construction run as "
                                  "visible, cancellable phases of the durable replay job after launch."),
            "feed": None,
            "availability": {"basis": basis, "label": label, "policy_id": None, "measured": False,
                             "note": "availability basis follows the source kind"},
            "reference": f"{kind.value}s/{source_id}",
        }

    # -- replays ----------------------------------------------------------------

    @r.post("", status_code=201)
    def start(body: StartObservation) -> dict[str, Any]:
        with conn() as c:
            try:
                rid = control.create_replay(c, md_root, body.source_kind, body.source_id, body.speed, body.paused)
            except SourceRejected as exc:
                raise HTTPException(422, str(exc)) from None
            except control.ControlRejected as exc:
                raise HTTPException(422, str(exc)) from None
            return replay_view(get_row(c, rid))

    @r.get("")
    def list_replays(limit: int = 50) -> list[dict[str, Any]]:
        with conn() as c:
            rows = c.execute(REPLAY_SELECT + " ORDER BY r.created_at DESC LIMIT %s", (limit,)).fetchall()
        return [replay_view(x) for x in rows]

    @r.get("/{replay_id}")
    def detail(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            row = get_row(c, replay_id)
            v = replay_view(row)
            v["assurance_summary"] = assurance_summary(c, replay_id, v["operation"]["assurance"], v["status"])
            return v

    def state(c, replay_id: str) -> dict[str, Any]:
        row = get_row(c, replay_id)
        ck = c.execute("SELECT snapshot_view FROM observation_checkpoints WHERE replay_id = %s",
                       (replay_id,)).fetchone()
        v = replay_view(row)
        v["assurance_summary"] = assurance_summary(c, replay_id, v["operation"]["assurance"], v["status"])
        return {"replay": v, "state": ck["snapshot_view"] if ck else None}

    @r.get("/{replay_id}/state")
    def current_state(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            return state(c, replay_id)

    @r.get("/{replay_id}/deliveries")
    def deliveries(replay_id: str, after_seq: int = -1, latest: int | None = Query(None, ge=1, le=1000),
                   limit: int = Query(500, ge=1, le=5000)) -> list[dict[str, Any]]:
        with conn() as c:
            row = get_row(c, replay_id)
            if is_stream(row):
                reader, committed = _committed_reader(md_root, row)
                if latest is not None:
                    lo, hi = max(0, committed - latest), committed
                else:
                    lo = after_seq + 1
                    hi = min(committed, lo + min(limit, MAX_WINDOW))
                return [_delivery_doc(seq, decode(line)) for seq, line in reader.lines(lo, hi)] if lo < hi else []
            if latest is not None:
                rows = c.execute("SELECT record, payload FROM observation_deliveries WHERE replay_id = %s "
                                 "ORDER BY seq DESC LIMIT %s", (replay_id, latest)).fetchall()
                rows.reverse()
            else:
                rows = c.execute("SELECT record, payload FROM observation_deliveries WHERE replay_id = %s AND seq > %s "
                                 "ORDER BY seq LIMIT %s", (replay_id, after_seq, limit)).fetchall()
        return [{**x["record"], "payload": x["payload"]} for x in rows]

    @r.get("/{replay_id}/traded-bars")
    def traded_bars(replay_id: str, tail: int | None = Query(None, ge=1, le=5000)) -> dict[str, Any]:
        """Committed traded-bar deliveries only (valid bars and slot-quality events). Never mark/index.

        ``tail`` returns only the latest N traded deliveries (a bounded chart window for long replays).
        """
        with conn() as c:
            row = get_row(c, replay_id)
            if is_stream(row):
                return stream_bars(row, tail)
            if tail is None:
                rows = c.execute(
                    "SELECT record, payload FROM observation_deliveries WHERE replay_id = %s "
                    "AND family = 'trade_bar_1m' ORDER BY seq", (replay_id,)).fetchall()
            else:
                rows = c.execute(
                    "SELECT record, payload FROM observation_deliveries WHERE replay_id = %s "
                    "AND family = 'trade_bar_1m' ORDER BY seq DESC LIMIT %s", (replay_id, tail)).fetchall()
                rows.reverse()
        bars = []
        for x in rows:
            rec, p = x["record"], x["payload"] or {}
            item = {"seq": rec["seq"], "event_time": rec["event_time"], "available_time": rec["available_time"],
                    "kind": rec["kind"], "quality_reason": rec["quality_reason"]}
            if rec["kind"] == "bar_observation":
                item.update({k: p[k] for k in ("open", "high", "low", "close", "volume_base", "volume_base_ccy")})
            bars.append(item)
        return {"channel_family": "trade_bar_1m", "information_time": row["info_time"].isoformat()
                if row.get("info_time") else None, "bars": bars}

    def stream_bars(row: dict[str, Any], tail: int | None) -> dict[str, Any]:
        """Latest traded-bar evidence strictly before the committed cursor (bounded backward scan)."""
        want = min(tail or DEFAULT_BARS, MAX_WINDOW)
        reader, committed = _committed_reader(md_root, row)
        pe = reader.cache.manifest["partition_events"]
        bars: list[dict[str, Any]] = []
        scanned, budget = 0, want * 20
        idx = (committed - 1) // pe if committed else -1
        while idx >= 0 and len(bars) < want and scanned < budget:
            p = reader.cache.partitions[idx]
            lines = reader.partition_lines(idx)
            for j in range(min(committed - p["first_seq"], p["count"]) - 1, -1, -1):
                scanned += 1
                e = decode(lines[j])
                if e.channel.family.value != "trade_bar_1m":
                    continue
                item = {"seq": p["first_seq"] + j, "event_time": e.event_time.isoformat(),
                        "available_time": e.available_time.isoformat(), "kind": e.kind.value,
                        "quality_reason": getattr(e.payload, "reason", None)}
                if e.kind.value == "bar_observation":
                    pl = e.payload.model_dump(mode="json")
                    item.update({k: pl[k] for k in ("open", "high", "low", "close", "volume_base", "volume_base_ccy")})
                bars.append(item)
                if len(bars) >= want:
                    break
            idx -= 1
        bars.reverse()
        return {"channel_family": "trade_bar_1m",
                "information_time": row["info_time"].isoformat() if row.get("info_time") else None,
                "bars": bars, "bounded_window": want, "committed_cursor": committed,
                "source": "verified feed cache, committed prefix only"}

    def command(replay_id: str, fn, *args) -> dict[str, Any]:
        with conn() as c:
            try:
                fn(c, replay_id, *args)
            except control.ReplayNotFound:
                raise HTTPException(404, f"observation replay {replay_id} not found") from None
            except control.ControlRejected as exc:
                raise HTTPException(409, str(exc)) from None
            return replay_view(get_row(c, replay_id))

    @r.post("/{replay_id}/pause")
    def pause(replay_id: str) -> dict[str, Any]:
        return command(replay_id, control.pause)

    @r.post("/{replay_id}/resume")
    def resume(replay_id: str) -> dict[str, Any]:
        return command(replay_id, control.resume)

    @r.post("/{replay_id}/step")
    def step(replay_id: str) -> dict[str, Any]:
        return command(replay_id, control.step)

    @r.post("/{replay_id}/speed")
    def speed(replay_id: str, body: SetSpeed) -> dict[str, Any]:
        return command(replay_id, control.set_speed, body.speed)

    @r.post("/{replay_id}/cancel")
    def cancel(replay_id: str) -> dict[str, Any]:
        return command(replay_id, control.cancel)

    @r.get("/{replay_id}/stream")
    def stream(replay_id: str) -> StreamingResponse:
        with conn() as c:
            get_row(c, replay_id)

        def gen() -> Iterator[str]:
            last_key, last_sent = None, 0.0
            with conn() as c:
                while True:
                    doc = state(c, replay_id)
                    rv = doc["replay"]
                    key = (rv["status"], rv["runtime_state"], rv["progress"]["applied_events"], rv["attempt"],
                           rv["operation"]["phase"], rv["operation"]["health"],
                           rv["operation"]["progress"]["progress_seq"],
                           len(rv["recovery_log"]), len(rv["control_log"]), rv["lease_expired"],
                           rv["cancel_requested"], tuple(rv["control"].values()))
                    if key != last_key or time.monotonic() - last_sent >= 2:
                        yield f"event: snapshot\ndata: {json.dumps(doc)}\n\n"
                        last_key, last_sent = key, time.monotonic()
                    else:
                        yield ": keep-alive\n\n"
                    if rv["status"] in control.TERMINAL:
                        yield "event: end\ndata: {}\n\n"
                        return
                    time.sleep(0.4)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    def report_doc(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            row = get_row(c, replay_id)
            ev = c.execute("SELECT evaluation_id FROM evaluations WHERE replay_id = %s", (replay_id,)).fetchone()
            storage = storage_facts(c, replay_id)
            current = assurance_summary(c, replay_id, row.get("assurance"), row["status"])
        doc = diag.diagnostic_report(row, art_root, datetime.now(UTC), ev, storage)
        doc["current_assurance"] = {**current, "captured_at": datetime.now(UTC).isoformat(),
                                    "note": "current linked assurance (may change when Deep validations run); the "
                                            "run's terminal records are immutable"}
        return doc

    @r.get("/{replay_id}/report.json")
    def report_json(replay_id: str, download: bool = False) -> PlainTextResponse:
        doc = report_doc(replay_id)
        headers = {"Content-Disposition": f'attachment; filename="{replay_id}-diagnostic.json"'} if download else {}
        return PlainTextResponse(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                                 media_type="application/json", headers=headers)

    @r.get("/{replay_id}/report.md")
    def report_md(replay_id: str, download: bool = False) -> PlainTextResponse:
        doc = report_doc(replay_id)
        headers = {"Content-Disposition": f'attachment; filename="{replay_id}-diagnostic.md"'} if download else {}
        return PlainTextResponse(diag.render_markdown(doc), media_type="text/markdown; charset=utf-8",
                                 headers=headers)

    @r.get("/{replay_id}/manifest")
    def manifest(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            row = get_row(c, replay_id)
        if row["manifest"] is None:
            raise HTTPException(404, f"replay {replay_id} has no manifest yet (status {row['status']})")
        return row["manifest"]

    @r.get("/{replay_id}/files/{name}")
    def file(replay_id: str, name: str):
        m = manifest(replay_id)
        if name != "manifest.json" and name not in {a["name"] for a in m["artifacts"]}:
            raise HTTPException(404, f"no artifact {name}")
        path = files_dir(art_root, replay_id, m) / name
        if not path.is_file():
            raise HTTPException(410, f"artifact {name} is recorded in the manifest but missing on disk")
        return FileResponse(path, filename=name)

    return r
