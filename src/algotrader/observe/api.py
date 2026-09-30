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
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..marketdata import dataset as md
from ..recorder import journal as rj
from . import control
from .artifacts import replay_dir
from .contracts import ObservationReplayConfig, ReplayRuntimeState, SourceKind
from .sources import SourceRejected, feed_identity, load_source

ETA_MIN_EVENTS = 5
ETA_MIN_SECONDS = 1.0

REPLAY_SELECT = """
SELECT r.*, c.cursor AS applied, c.info_time, c.last_event_id, c.snapshot_id, c.snapshot_digest
FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id)
"""


class StartObservation(BaseModel):
    source_kind: SourceKind
    source_id: str = Field(min_length=1, max_length=200)
    speed: float = Field(default=20.0, ge=0, le=control.MAX_SPEED)
    paused: bool = False


class SetSpeed(BaseModel):
    speed: float = Field(ge=0, le=control.MAX_SPEED)


def _runtime(row: dict[str, Any], lease_expired: bool) -> tuple[ReplayRuntimeState, str]:
    status = row["status"]
    if status in control.TERMINAL:
        return ReplayRuntimeState(status), {
            "completed": "all feed deliveries applied",
            "cancelled": "cancelled by user",
            "failed": "failed; see error",
        }[status]
    if row["cancel_requested"]:
        return ReplayRuntimeState.CANCEL_REQUESTED, "cancellation requested; worker will finalize the replay"
    if status == "running" and lease_expired:
        return ReplayRuntimeState.RECOVERING, "lease expired (worker stopped heartbeating); awaiting reclaim"
    if row["paused"]:
        if row["step_budget"] > 0:
            return ReplayRuntimeState.STEPPING, f"paused; {row['step_budget']} single feed delivery(ies) pending"
        if status == "running":
            return ReplayRuntimeState.PAUSING, "pause requested; worker finishes the current delivery"
        return ReplayRuntimeState.PAUSED, "paused at a committed feed cursor; no worker holds the replay"
    if status == "running":
        return ReplayRuntimeState.RUNNING, f"worker {row['lease_owner']} is applying feed deliveries"
    return ReplayRuntimeState.QUEUED, "waiting for an observation worker"


def _eta(row: dict[str, Any], state: ReplayRuntimeState, applied: int, now: datetime) -> tuple[float | None, str]:
    if state != ReplayRuntimeState.RUNNING:
        return None, f"unavailable while {state.value}"
    since, base = row["throughput_since"], row["throughput_base"]
    if since is None or base is None:
        return None, "unavailable: no throughput observed yet"
    window, done = (now - since).total_seconds(), applied - base
    if done < ETA_MIN_EVENTS or window < ETA_MIN_SECONDS:
        return None, "unavailable: not enough progress observed since the last start/resume/speed change"
    rate = done / window
    return (row["total_events"] - applied) / rate, f"observed {rate:.1f} events/s over the last {window:.0f}s"


def replay_view(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    cfg = ObservationReplayConfig.model_validate(row["config"])
    applied = row.get("applied") or 0
    hb = row["heartbeat_at"]
    lease_expired = bool(row["status"] == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)
    state, detail = _runtime(row, lease_expired)
    eta, eta_basis = _eta(row, state, applied, now)
    pol = cfg.availability_policy
    return {
        "replay_id": row["replay_id"],
        "kind": "market_observation_replay",
        "status": row["status"],
        "runtime_state": state.value,
        "runtime_detail": detail,
        "source": json.loads(cfg.source.model_dump_json()),
        "verification": json.loads(cfg.verification.model_dump_json()),
        "availability": {"basis": pol.basis.value, "policy_id": pol.policy_id, "measured": pol.measured,
                         "label": cfg.availability_label, "note": pol.note},
        "freshness_policy": json.loads(cfg.freshness_policy.model_dump_json()),
        "feed": json.loads(cfg.feed.model_dump_json()),
        "clock_policy": cfg.clock_policy,
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
            "total_events": row["total_events"],
            "information_time": row["info_time"].isoformat() if row.get("info_time") else None,
            "last_event_id": row.get("last_event_id"),
            "snapshot_id": row.get("snapshot_id"),
            "snapshot_digest": row.get("snapshot_digest"),
            "heartbeat_age_seconds": (now - hb).total_seconds() if hb else None,
            "elapsed_seconds": (((row["finished_at"] or now) - row["started_at"]).total_seconds()
                                if row["started_at"] else None),
            "eta_seconds": eta,
            "eta_basis": eta_basis,
        },
        "code_version": cfg.code_version,
        "labels": list(cfg.labels),
    }


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
        """Verify a source and build its feed (nothing is persisted)."""
        try:
            s = load_source(md_root, kind, source_id)
        except SourceRejected as exc:
            raise HTTPException(422, str(exc)) from None
        pol = s.feed.manifest.availability_policy
        return {
            "source": json.loads(s.summary.model_dump_json()),
            "verification": json.loads(s.verification.model_dump_json()),
            "feed": json.loads(feed_identity(s.feed).model_dump_json()),
            "availability": {"basis": pol.basis.value, "policy_id": pol.policy_id, "measured": pol.measured,
                             "label": s.availability_label, "note": pol.note},
            "reference": s.reference,
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
            return replay_view(get_row(c, replay_id))

    def state(c, replay_id: str) -> dict[str, Any]:
        row = get_row(c, replay_id)
        ck = c.execute("SELECT snapshot_view FROM observation_checkpoints WHERE replay_id = %s",
                       (replay_id,)).fetchone()
        return {"replay": replay_view(row), "state": ck["snapshot_view"] if ck else None}

    @r.get("/{replay_id}/state")
    def current_state(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            return state(c, replay_id)

    @r.get("/{replay_id}/deliveries")
    def deliveries(replay_id: str, after_seq: int = -1, latest: int | None = Query(None, ge=1, le=1000),
                   limit: int = Query(500, ge=1, le=5000)) -> list[dict[str, Any]]:
        with conn() as c:
            get_row(c, replay_id)
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
        path = replay_dir(art_root, replay_id) / name
        if not path.is_file():
            raise HTTPException(410, f"artifact {name} is recorded in the manifest but missing on disk")
        return FileResponse(path, filename=name)

    return r
