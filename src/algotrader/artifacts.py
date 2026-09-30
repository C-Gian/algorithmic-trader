"""Immutable run artifacts: manifest, Parquet records, validation, report.

Artifacts live under ``<artifact_root>/runs/<run_id>/`` outside Git. They
are written to a temporary directory and atomically renamed; an existing
artifact directory is never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .contracts import SCHEMA_VERSION, ArtifactRef, ReplayControl, RunConfig, RunManifest, RunStatus
from .engine import INITIAL_COLLATERAL, Engine, canonical_json, trace_hash
from .validation import validate_run

LABELS = ("DEMO", "SYNTHETIC", "NOT_RESEARCH_EVIDENCE")


def code_version() -> str | None:
    env = os.environ.get("ALGOTRADER_CODE_VERSION")
    if env:
        return env
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout
        return sha + ("-dirty" if dirty.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(events: list[dict[str, Any]], kind: str, columns: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for e in events:
        if e["kind"] != kind:
            continue
        row = {"seq": e["seq"], "step": e["step"], "sim_time": e["sim_time"]}
        for col, getter in columns.items():
            value = getter(e["payload"])
            row[col] = None if value is None else str(value) if not isinstance(value, bool) else value
        row["payload_json"] = canonical_json(e["payload"]).decode()
        out.append(row)
    return out


TABLES: dict[str, tuple[str, dict[str, Any]]] = {
    "market_views": (
        "market_view",
        {
            "view_id": lambda p: p["view_id"],
            "validity": lambda p: p["validity"],
            "bias": lambda p: p["horizons"][0]["bias"],
            "confidence": lambda p: p["confidence"],
            "summary": lambda p: p["summary"],
        },
    ),
    "decisions": (
        "decision",
        {
            "decision_id": lambda p: p["decision_id"],
            "proposed_action": lambda p: p["proposed_action"],
            "permitted_action": lambda p: p["permitted_action"],
            "blocking_reasons": lambda p: ",".join(p["blocking_reasons"]),
            "reason": lambda p: p["reason"],
            "target_quantity": lambda p: p["target_quantity"],
        },
    ),
    "risk_decisions": (
        "risk_decision",
        {
            "risk_decision_id": lambda p: p["risk_decision_id"],
            "approved": lambda p: p["approved"],
            "approved_target_quantity": lambda p: p["approved_target_quantity"],
            "blocking_reasons": lambda p: ",".join(p["blocking_reasons"]),
        },
    ),
    "trade_plans": (
        "trade_plan",
        {"plan_id": lambda p: p["plan_id"], "status": lambda p: p["status"], "direction": lambda p: p["direction"]},
    ),
    "orders": (
        "order",
        {
            "order_id": lambda p: p["order_id"],
            "side": lambda p: p["side"],
            "quantity": lambda p: p["quantity"],
            "status": lambda p: p["status"],
            "reduce_only": lambda p: p["reduce_only"],
        },
    ),
    "fills": (
        "fill",
        {
            "fill_id": lambda p: p["fill_id"],
            "order_ref": lambda p: p["order_ref"],
            "side": lambda p: p["side"],
            "quantity": lambda p: p["quantity"],
            "price": lambda p: p["price"],
            "fee": lambda p: p["fee"],
        },
    ),
    "account": (
        "account",
        {
            "equity": lambda p: p["equity"],
            "collateral_balance": lambda p: p["collateral_balance"],
            "realized_pnl": lambda p: p["realized_pnl"],
            "unrealized_pnl": lambda p: p["unrealized_pnl"],
            "fees_paid": lambda p: p["fees_paid"],
            "position_quantity": lambda p: p["position"]["quantity"],
            "mark_price": lambda p: p["mark_price"],
        },
    ),
    "observations": (
        "observation",
        {
            "observation_id": lambda p: p["observation_id"],
            "quality": lambda p: p["quality"],
            "open": lambda p: p["open"],
            "high": lambda p: p["high"],
            "low": lambda p: p["low"],
            "close": lambda p: p["close"],
        },
    ),
}


def _write_parquet(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    if rows:
        table = pa.Table.from_pylist(rows)
    else:
        table = pa.table({c: pa.array([], type=pa.string()) for c in columns})
    pq.write_table(table, path, compression="zstd")


def _report(manifest: RunManifest, v: dict[str, Any]) -> str:
    lines = [
        f"# Run report — {manifest.run_id}",
        "",
        "**DEMO / SYNTHETIC — scripted dummy trader on a synthetic fixture. Not market data. "
        "Dummy P&L is not research evidence.**",
        "",
        f"- Status: `{manifest.status}`" + (f" — {manifest.error}" if manifest.error else ""),
        f"- Engine: `{manifest.engine_version}`; code `{manifest.code_version}`; "
        f"contracts `{manifest.schema_version}`",
        f"- Fixture: `{manifest.fixture['fixture_id']}` seed `{manifest.fixture['seed']}` "
        f"sha256 `{manifest.fixture['content_sha256'][:16]}…`",
        f"- Steps: {manifest.steps_processed}/{manifest.total_steps}; attempts: {manifest.attempts}",
        f"- Semantic trace hash: `{manifest.semantic_trace_hash}` ({manifest.event_count} events)",
        "",
        "## Validation" + (" — PASS" if v["passed"] else " — FAIL"),
        "",
    ]
    lines += [f"- {'PASS' if c['passed'] else 'FAIL'} `{c['name']}` — {c['detail']}" for c in v["checks"]]
    if manifest.recovery_log:
        lines += ["", "## Recovery log", ""]
        lines += [f"- attempt {r['attempt']}: {r['event']} — {r['detail']}" for r in manifest.recovery_log]
    if manifest.control_log:
        lines += ["", "## Replay control log (operational; not part of the semantic trace)", ""]
        lines += [
            f"- {r['at']}: {r['command']} " + ", ".join(f"{k}={v}" for k, v in r.items() if k not in ("at", "command"))
            for r in manifest.control_log
        ]
    return "\n".join(lines) + "\n"


def write_run_artifacts(
    root: Path,
    run: dict[str, Any],
    status: RunStatus,
    error: str | None,
    finished_at: datetime,
    events: list[dict[str, Any]],
    engine: Engine,
) -> RunManifest:
    run_id = run["run_id"]
    final_dir = root / "runs" / run_id
    manifest_path = final_dir / "manifest.json"
    if manifest_path.exists():  # immutable: a previous finalize already wrote them
        return RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    tmp = root / "runs" / f".{run_id}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    config = RunConfig.model_validate(run["config"])
    steps_processed = len({e["step"] for e in events if e["kind"] == "decision"})
    validation = validate_run(
        events,
        steps_processed,
        INITIAL_COLLATERAL,
        engine.fixture.instrument.instrument_id,
        complete=status == RunStatus.COMPLETED,
    )

    refs: list[ArtifactRef] = []

    def add(name: str, media_type: str, rows: int | None) -> None:
        p = tmp / name
        refs.append(ArtifactRef(name=name, path=f"runs/{run_id}/{name}", sha256=_sha256(p), rows=rows, media_type=media_type))

    all_rows = [
        {
            "seq": e["seq"],
            "step": e["step"],
            "kind": e["kind"],
            "sim_time": e["sim_time"],
            "payload_json": canonical_json(e["payload"]).decode(),
        }
        for e in events
    ]
    _write_parquet(tmp / "events.parquet", all_rows, ["seq", "step", "kind", "sim_time", "payload_json"])
    add("events.parquet", "application/vnd.apache.parquet", len(all_rows))
    for table, (kind, cols) in TABLES.items():
        rows = _rows(events, kind, cols)
        _write_parquet(tmp / f"{table}.parquet", rows, ["seq", "step", "sim_time", *cols, "payload_json"])
        add(f"{table}.parquet", "application/vnd.apache.parquet", len(rows))
    (tmp / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    add("validation.json", "application/json", None)

    manifest = RunManifest(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        labels=LABELS,
        status=status,
        engine_id=engine.trader.engine_id,
        engine_version=engine.engine_version,
        code_version=code_version(),
        config=config,
        config_hash=hashlib.sha256(canonical_json(config.model_dump(mode="json"))).hexdigest(),
        fixture=engine.fixture.describe(),
        instrument=engine.fixture.instrument,
        assumptions={
            "fill_model": "market orders fill at the next available bar open (no fill from unavailable data)",
            "costs": engine.costs.model_dump(mode="json"),
            "funding": "NOT_MODELED",
            "mark_index": "NOT_MODELED (mark = last valid synthetic close)",
            "initial_collateral": str(INITIAL_COLLATERAL),
            "labels": list(LABELS),
        },
        risk_policy=engine.policy.model_dump(mode="json"),
        created_at=run["created_at"],
        started_at=run["started_at"],
        finished_at=finished_at,
        steps_processed=steps_processed,
        total_steps=run["total_steps"],
        attempts=run["attempt"],
        recovery_log=tuple(run["recovery_log"]),
        control_log=tuple(run["control_log"]),
        replay_control=ReplayControl(paused=run["paused"], step_budget=run["step_budget"], speed=run["speed"]),
        error=error,
        semantic_trace_hash=trace_hash(events),
        event_count=len(events),
        validation={"passed": validation["passed"], "failed": [c["name"] for c in validation["checks"] if not c["passed"]]},
        artifacts=(),
    )
    (tmp / "report.md").write_text(_report(manifest, validation), encoding="utf-8")
    add("report.md", "text/markdown", None)
    manifest = manifest.model_copy(update={"artifacts": tuple(refs)})
    (tmp / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    final_dir.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, final_dir)
    return manifest
