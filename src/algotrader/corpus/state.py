"""Local corpus state: which immutable dataset a logical chunk is bound to.

A binding is operational state in PostgreSQL (``corpus_chunks``); the dataset itself
stays where ``marketdata.dataset`` put it and is never copied. A chunk counts as
PREPARED only while its bound dataset directory exists, its ``manifest.json`` still
has the SHA-256 recorded at binding time and the last full verification passed.
Binding refuses any dataset whose logical request is not exactly the chunk
(source, instrument, bar, families, start, end, official OKX host).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from ..marketdata import dataset as md
from ..marketdata.contracts import HISTORICAL_FAMILIES, DatasetManifest
from ..marketdata.okx_authority import validate_okx_rest_base_url
from .plan import Chunk, CorpusPlan


class CorpusMismatch(Exception):
    """A dataset is not the logical chunk it would be bound to."""


class ChunkStatus(StrEnum):
    PREPARED = "prepared"
    PREPARING = "preparing"
    NOT_PREPARED = "not_prepared"
    INVALID = "invalid"  # bound, but the local dataset is missing, altered or failed verification
    PLANNED = "planned"  # locked: not preparable in this version


ACTIVE_JOB_STATUSES = ("queued", "running")


def manifest_sha256(path: Path) -> str:
    return hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()


def check_logical_match(chunk: Chunk, inst_id: str, m: DatasetManifest) -> None:
    r = m.request
    problems = []
    if r.source != "okx":
        problems.append(f"source {r.source!r} is not okx")
    try:
        validate_okx_rest_base_url(r.base_url)
    except ValueError as exc:
        problems.append(f"base_url not an official OKX host: {exc}")
    if r.inst_id != inst_id:
        problems.append(f"instrument {r.inst_id} != {inst_id}")
    if r.bar != "1m":
        problems.append(f"bar {r.bar} != 1m")
    if set(r.families) != set(HISTORICAL_FAMILIES):
        problems.append("dataset does not contain all four historical families")
    if r.start != chunk.start or r.end != chunk.end:
        problems.append(f"interval {r.start.isoformat()} -> {r.end.isoformat()} is not the chunk interval "
                        f"{chunk.start.isoformat()} -> {chunk.end.isoformat()}")
    if problems:
        raise CorpusMismatch(f"dataset {m.dataset_id} cannot be bound to {chunk.chunk_id}: " + "; ".join(problems))


def storage_summary(path: Path, m: DatasetManifest) -> dict[str, Any]:
    """Measured size facts for the Director's later storage decision (Git / LFS / pinned archive)."""
    q = md.load_quality(path)
    raw = sum(f.bytes for f in m.files if f.name.startswith("raw/"))
    parquet = sum(f.bytes for f in m.files if f.name.endswith(".parquet"))
    manifest_bytes = (path / "manifest.json").stat().st_size
    total = sum(f.bytes for f in m.files) + manifest_bytes
    return {
        "total_bytes": total,
        "raw_bytes": raw,
        "parquet_bytes": parquet,
        "metadata_bytes": total - raw - parquet,
        "file_count": len(m.files) + 1,
        "raw_page_count": m.raw_page_count,
        "quality_status": q.status.value,
        "families": [
            {"family": f.family.value, "rows": f.rows, "pages": f.pages,
             "expected_rows": fq.expected_rows, "missing_rows": fq.missing_rows, "gaps": len(fq.gaps),
             "status": fq.status.value,
             "first_time": f.first_time.isoformat() if f.first_time else None,
             "last_time": f.last_time.isoformat() if f.last_time else None}
            for f, fq in zip(m.families, q.families)
        ],
        "note": "bytes of the immutable dataset directory as listed in its manifest; nothing is committed to Git",
    }


def verify_dataset(data_root: Path, dataset_id: str, progress=None) -> tuple[Path | None, list[str]]:
    path = md.dataset_path(data_root, dataset_id)
    if path is None:
        return None, [f"dataset {dataset_id} is not present in the local data root"]
    return path, md.verify(path, progress=progress)


def bind(conn: psycopg.Connection, plan: CorpusPlan, chunk: Chunk, path: Path, job_id: str | None,
         outcome: str, verified_at: datetime, generation: int | None = None) -> dict[str, Any]:
    """Insert/replace the chunk binding. Caller must have verified ``path``; runs in the caller's transaction."""
    m = md.load_manifest(path)
    check_logical_match(chunk, plan.inst_id, m)
    storage = storage_summary(path, m)
    prev = conn.execute("SELECT dataset_id FROM corpus_chunks WHERE chunk_id = %s", (chunk.chunk_id,)).fetchone()
    conn.execute(
        """
        INSERT INTO corpus_chunks (chunk_id, plan_id, start_time, end_time, inst_id, base_url, dataset_id,
            manifest_sha256, quality_status, verification_ok, verification_problems, verified_at, retrieved_at,
            bytes_on_disk, storage, bound_at, bound_by_job, outcome, previous_dataset_id, bound_generation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, '[]'::jsonb, %s, %s, %s, %s, now(), %s, %s, %s, %s)
        ON CONFLICT (chunk_id) DO UPDATE SET plan_id = excluded.plan_id, start_time = excluded.start_time,
            end_time = excluded.end_time, inst_id = excluded.inst_id, base_url = excluded.base_url,
            dataset_id = excluded.dataset_id, manifest_sha256 = excluded.manifest_sha256,
            quality_status = excluded.quality_status, verification_ok = true, verification_problems = '[]'::jsonb,
            verified_at = excluded.verified_at, retrieved_at = excluded.retrieved_at,
            bytes_on_disk = excluded.bytes_on_disk, storage = excluded.storage, bound_at = now(),
            bound_by_job = excluded.bound_by_job, outcome = excluded.outcome,
            bound_generation = excluded.bound_generation,
            previous_dataset_id = CASE WHEN corpus_chunks.dataset_id <> excluded.dataset_id
                                       THEN corpus_chunks.dataset_id ELSE corpus_chunks.previous_dataset_id END
        """,
        (chunk.chunk_id, plan.plan_id, chunk.start, chunk.end, plan.inst_id, m.request.base_url, m.dataset_id,
         manifest_sha256(path), storage["quality_status"], verified_at, m.retrieval_started_at,
         storage["total_bytes"], Jsonb(storage), job_id, outcome,
         prev["dataset_id"] if prev and prev["dataset_id"] != m.dataset_id else None, generation),
    )
    return storage


def record_verification(conn: psycopg.Connection, chunk_id: str, ok: bool, problems: list[str]) -> None:
    conn.execute("UPDATE corpus_chunks SET verification_ok = %s, verification_problems = %s, verified_at = %s "
                 "WHERE chunk_id = %s", (ok, Jsonb(problems), datetime.now(UTC), chunk_id))


def find_local_match(data_root: Path, plan: CorpusPlan, chunk: Chunk) -> list[DatasetManifest]:
    """Local datasets whose logical request is exactly this chunk (newest first). Not yet verified."""
    out = []
    for m in md.list_manifests(data_root):
        try:
            check_logical_match(chunk, plan.inst_id, m)
        except CorpusMismatch:
            continue
        out.append(m)
    return out


def binding_state(data_root: Path, binding: dict[str, Any] | None) -> tuple[bool, str | None]:
    """Cheap local check used by status views: (usable, problem). Full hashing happens in jobs/launch."""
    if binding is None:
        return False, None
    path = md.dataset_path(data_root, binding["dataset_id"])
    if path is None:
        return False, "the bound dataset is no longer present in the local data root"
    try:
        if manifest_sha256(path) != binding["manifest_sha256"]:
            return False, "the bound dataset manifest changed since binding"
    except OSError as exc:
        return False, f"the bound dataset manifest is unreadable: {exc}"
    if not binding["verification_ok"]:
        return False, "the last full verification failed: " + "; ".join(binding["verification_problems"] or [])
    return True, None


def binding_state_cheap(data_root: Path, binding: dict[str, Any] | None) -> tuple[bool, str | None]:
    """Launch-time check without hashing: bound, last verification passed, directory still present.

    The manifest hash recorded at binding is re-checked by the worker-owned preparation phase.
    """
    if binding is None:
        return False, None
    if md.dataset_path(data_root, binding["dataset_id"]) is None:
        return False, "the bound dataset is no longer present in the local data root"
    if not binding["verification_ok"]:
        return False, "the last full verification failed: " + "; ".join(binding["verification_problems"] or [])
    return True, None


def chunk_view(plan: CorpusPlan, chunk: Chunk, binding: dict[str, Any] | None, job: dict[str, Any] | None,
               data_root: Path) -> dict[str, Any]:
    usable, problem = binding_state(data_root, binding)
    active = job is not None and job["status"] in ACTIVE_JOB_STATUSES
    if not chunk.preparable:
        status = ChunkStatus.PLANNED
    elif active:
        status = ChunkStatus.PREPARING
    elif usable:
        status = ChunkStatus.PREPARED
    elif binding is not None:
        status = ChunkStatus.INVALID
    else:
        status = ChunkStatus.NOT_PREPARED
    local = None
    if binding is not None:
        local = {
            "dataset_id": binding["dataset_id"],
            "manifest_sha256": binding["manifest_sha256"],
            "base_url": binding["base_url"],
            "quality_status": binding["quality_status"],
            "verification_ok": binding["verification_ok"],
            "verification_problems": binding["verification_problems"],
            "verified_at": binding["verified_at"].isoformat() if binding["verified_at"] else None,
            "retrieved_at": binding["retrieved_at"].isoformat() if binding["retrieved_at"] else None,
            "bytes_on_disk": binding["bytes_on_disk"],
            "storage": binding["storage"],
            "bound_at": binding["bound_at"].isoformat(),
            "bound_by_job": binding["bound_by_job"],
            "outcome": binding["outcome"],
            "previous_dataset_id": binding["previous_dataset_id"],
            "usable": usable,
            "problem": problem,
            "reuse": ("Reused locally: evaluations and later preparations use this verified dataset; "
                      "nothing is downloaded again" if usable else "Not reusable until prepared again"),
        }
    return {
        "chunk_id": chunk.chunk_id,
        "label": chunk.label,
        "start": chunk.start.isoformat(),
        "end": chunk.end.isoformat(),
        "preparable": chunk.preparable,
        "note": chunk.note,
        "status": status.value,
        "source": plan.source,
        "inst_id": plan.inst_id,
        "local": local,
    }


def bindings(conn: psycopg.Connection) -> dict[str, dict[str, Any]]:
    return {r["chunk_id"]: r for r in conn.execute("SELECT * FROM corpus_chunks").fetchall()}


def plan_doc(plan: CorpusPlan) -> dict[str, Any]:
    return json.loads(plan.model_dump_json())
