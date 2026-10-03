"""Durable evaluation-pack preparation (parent job owned by the corpus worker; Owner-triggered only).

``create_pack_job`` only inserts a queued row (no network, no hashing). The corpus worker claims it under a fenced
lease generation and, for the preset's full requested interval [warmup start, tail end):

1. **reuse** - a published pack with the same preset identity whose manifest/receipt/cache still verify is reused
   (outcome ``reused_pack``; zero network requests);
2. **plan** - compatible local packages are sliced deterministically (``pack.plan_slices``); uncovered ranges
   become sequential acquisition children split at UTC month boundaries and the 31-day bound;
3. **acquire** - each pending child uses the accepted ``OkxPublicClient`` + ``marketdata.dataset.acquire`` and is
   verified before being recorded completed (its immutable dataset is kept even if the parent is cancelled or
   fails, so a later Prepare reuses it locally instead of downloading it again);
4. **source caches** - every slice's package is prepared through the accepted verify-once/receipt-pinned cache;
5. **compose** - one canonical pack feed cache over the full interval plus its cache receipt;
6. **publish** - manifest staged and fsynced; under the fenced row lock (the same lock ``cancel_pack_job`` takes)
   the directory rename, the ``corpus_packs`` receipt and COMPLETED commit together. A cancellation that wins the
   lock prevents publication; a cancel after the commit is rejected (already terminal).

Restart: a lapsed lease is reclaimed by a new generation; the new attempt re-plans from local packages, so
completed children are reused, never re-acquired. An interrupted child restarts from scratch (no byte resume).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .. import ops
from ..feed.ordering import canonical
from ..marketdata import dataset as md
from ..marketdata.okx_authority import validate_okx_rest_base_url
from ..observe import feedcache as fc
from ..observe.sources import ReceiptStore, SourceRejected
from . import pack as pk
from . import presets as ps
from .job import AcquisitionCancelled, LeaseLost, _Heartbeat, configured_base_url

log = logging.getLogger("algotrader.corpus.pack")
TERMINAL = ("completed", "cancelled", "failed")
PACK_PHASES = ("QUEUED", "PREPARING_SOURCE", "DOWNLOADING", "VERIFYING_SOURCE", "BUILDING_FEED", "BINDING")
RECOVERY_BEHAVIOR = (
    "If the worker stops, the job is reclaimed after its lease expires by a new fenced generation that re-plans from "
    "local packages: completed children (immutable datasets) are reused and never downloaded again; an interrupted "
    "child restarts from scratch (no byte-level resume). Nothing is published until the pack and its receipt are "
    "durable.")


class PackJobRejected(Exception):
    pass


class SimulatedPackCrash(BaseException):
    """Test-only stand-in for a hard worker death at a pack publication stage."""


def new_job_id() -> str:
    return f"pack-job-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def create_pack_job(conn: psycopg.Connection, f: ps.PresetsFile, preset: ps.Preset,
                    base_url: str | None = None) -> str:
    """Durable launch only (explicit Owner action): no network, no hashing."""
    ps.check_windows(f, preset)
    try:
        base = base_url or configured_base_url()
        validate_okx_rest_base_url(base)
    except ValueError as exc:
        raise PackJobRejected(f"market-data source rejected: {exc}") from None
    job_id = new_job_id()
    try:
        with conn.transaction():
            conn.execute(
                """INSERT INTO corpus_pack_jobs (job_id, preset_id, preset, preset_sha256, status, base_url)
                   VALUES (%s, %s, %s, %s, 'queued', %s)""",
                (job_id, preset.preset_id, Jsonb(ps.preset_doc(preset)), ps.preset_sha256(f, preset), base))
    except psycopg.errors.UniqueViolation:
        raise PackJobRejected(f"{preset.preset_id} already has an active preparation") from None
    return job_id


def cancel_pack_job(conn: psycopg.Connection, job_id: str) -> None:
    with conn.transaction():
        row = conn.execute("SELECT status FROM corpus_pack_jobs WHERE job_id = %s FOR UPDATE", (job_id,)).fetchone()
        if row is None:
            raise LookupError(job_id)
        if row["status"] in TERMINAL:
            raise PackJobRejected(f"job already {row['status']}")
        if row["status"] == "queued":
            conn.execute("UPDATE corpus_pack_jobs SET status = 'cancelled', cancel_requested = true, "
                         "finished_at = now(), error = 'cancelled before a worker started it' WHERE job_id = %s",
                         (job_id,))
        else:
            conn.execute("UPDATE corpus_pack_jobs SET cancel_requested = true WHERE job_id = %s", (job_id,))


def published_pack(conn, data_root: Path, preset_sha: str) -> tuple[dict | None, list[str]]:
    """Newest still-trustworthy published pack for this preset identity (manifest, receipt and cache verified)."""
    problems = []
    for rec in conn.execute("SELECT * FROM corpus_packs WHERE preset_sha256 = %s ORDER BY created_at DESC",
                            (preset_sha,)).fetchall():
        try:
            doc = pk.open_pack(data_root, rec["pack_id"], rec)
            fc.open_cache(data_root, rec["cache_id"], expected_manifest_sha256=rec["cache_manifest_sha256"])
            return {**doc, "_receipt": rec}, problems
        except (pk.PackError, fc.CacheError) as exc:
            problems.append(f"{rec['pack_id']}: {exc}")
    return None, problems


class PackJobRunner:
    TABLE = "corpus_pack_jobs"

    def __init__(self, worker) -> None:
        self.w = worker
        self.data_root: Path = worker.data_root

    # -- lease ------------------------------------------------------------------------------------

    def claim(self, conn) -> tuple[dict[str, Any], str | None] | None:
        with conn.transaction():
            row = conn.execute(
                """SELECT * FROM corpus_pack_jobs
                   WHERE status = 'queued' OR (status = 'running' AND lease_expires_at < now())
                   ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
            if row is None:
                return None
            reclaimed = row["status"] == "running"
            generation = row["lease_generation"] + 1
            history = list(row["phase_history"] or [])
            recovery = list(row["recovery_log"] or [])
            now = datetime.now(UTC)
            if row["status"] == "queued":
                history.append(ops.closed_entry("QUEUED", generation, row["attempt"] + 1, row["created_at"], now,
                                                0.0, waiting=True))
            elif (row["progress"] or {}).get("shared_phase"):
                p = row["progress"]
                started = ops.parse_iso(p.get("phase_started_at"))
                ended = row["heartbeat_at"] or now
                history.append(ops.closed_entry(p["shared_phase"], row["lease_generation"], row["attempt"], started,
                                                max(ended, started) if started else ended, None, interrupted=True,
                                                note="attempt interrupted; active time unknown"))
            interruptions = row["interruptions"] + 1 if reclaimed else row["interruptions"]
            fail = None
            if reclaimed:
                recovery.append({"at": now.isoformat(), "attempt": row["attempt"] + 1, "generation": generation,
                                 "event": "lease_expired_reclaimed",
                                 "detail": f"worker {row['lease_owner']} stopped heartbeating; reclaimed by "
                                           f"{self.w.worker_id}; completed children are reused from local packages"})
                if interruptions >= row["max_attempts"]:
                    fail = (f"worker interrupted on {interruptions} consecutive attempts; nothing was published. "
                            "Prepare again to retry.")
            conn.execute(
                """UPDATE corpus_pack_jobs SET status = 'running', lease_owner = %s, heartbeat_at = now(),
                       lease_expires_at = now() + make_interval(secs => %s), attempt = attempt + 1,
                       interruptions = %s, recovery_log = %s, started_at = coalesce(started_at, now()),
                       attempt_started_at = now(), progress = '{}'::jsonb, lease_generation = %s, phase_history = %s
                   WHERE job_id = %s""",
                (self.w.worker_id, self.w.lease_seconds, interruptions, Jsonb(recovery), generation, Jsonb(history),
                 row["job_id"]))
            row.update(status="running", lease_owner=self.w.worker_id, attempt=row["attempt"] + 1,
                       lease_generation=generation, phase_history=history, recovery_log=recovery)
        self.w.generation = generation
        return row, fail

    @property
    def fence(self) -> str:
        return "job_id = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'"

    def _args(self, job_id: str) -> tuple:
        return (job_id, self.w.worker_id, self.w.generation)

    def _update(self, conn, job_id: str, **cols) -> None:
        sets = ", ".join(f"{k} = %s" for k in cols)
        vals = [Jsonb(v) if isinstance(v, (dict, list)) else v for v in cols.values()]
        if conn.execute(f"UPDATE corpus_pack_jobs SET {sets} WHERE {self.fence}",
                        (*vals, *self._args(job_id))).rowcount == 0:
            raise LeaseLost()

    def _finish(self, conn, job_id: str, status: str, error: str | None, hb: _Heartbeat | None = None,
                **cols) -> None:
        history = hb.close_phase() if hb is not None else None
        extra = {"progress": {**(hb.progress if hb else {}), "phase": status}, **cols}
        if history is not None:
            extra["phase_history"] = history
        sets = ", ".join(f"{k} = %s" for k in extra)
        vals = [Jsonb(v) if isinstance(v, (dict, list)) else v for v in extra.values()]
        conn.execute(f"""UPDATE corpus_pack_jobs SET status = %s, error = %s, finished_at = now(), heartbeat_at = now(),
                             lease_owner = NULL, lease_expires_at = NULL, {sets}
                         WHERE {self.fence}""", (status, error, *vals, *self._args(job_id)))

    def run_once(self, conn) -> bool:
        claimed = self.claim(conn)
        if claimed is None:
            return False
        row, fail = claimed
        if row["cancel_requested"]:
            self._finish(conn, row["job_id"], "cancelled", "cancelled by the Owner before completion; nothing published")
        elif fail:
            self._finish(conn, row["job_id"], "failed", fail)
        else:
            self.process(conn, row)
        return True

    # -- processing -------------------------------------------------------------------------------

    def _check(self, hb: _Heartbeat) -> None:
        if hb.lost:
            raise LeaseLost()
        if hb.cancel:
            raise AcquisitionCancelled()

    def _hook(self, hb: _Heartbeat, phase: str):
        def hook(stage: str, done: int, total: int | None, unit: str) -> None:
            hb.publish({**hb.progress, "phase": phase, "stage": stage, "done": done, "total": total, "unit": unit})
            self._check(hb)
        return hook

    def _fault(self, stage: str) -> None:
        if self.w.pack_fault is not None:
            self.w.pack_fault(stage)

    def process(self, conn, row: dict[str, Any]) -> None:
        job_id = row["job_id"]
        hb = _Heartbeat(self.w, job_id, row["lease_generation"], row["attempt"], row["phase_history"],
                        table=self.TABLE)
        hb.publish({"phase": "planning", "detail": "checking published packs and local source packages"})
        hb.start()
        try:
            self._prepare(conn, row, hb)
        except AcquisitionCancelled:
            self._finish(conn, job_id, "cancelled", "cancelled by the Owner at a safe boundary; completed children "
                         "(immutable datasets) are kept for reuse; nothing was published", hb)
        except LeaseLost:
            log.error("%s: lease lost; another worker owns the job now", job_id)
        except (pk.PackError, SourceRejected, md.DatasetError) as exc:
            self._finish(conn, job_id, "failed", f"{type(exc).__name__}: {exc}", hb)
        except Exception as exc:  # explicit, visible failure
            log.exception("pack job %s failed", job_id)
            self._finish(conn, job_id, "failed", f"{type(exc).__name__}: {exc}", hb)
        finally:
            hb.stop()

    def _prepare(self, conn, row: dict[str, Any], hb: _Heartbeat) -> None:
        job_id = row["job_id"]
        f = ps.load_presets()
        preset = ps.Preset.model_validate(row["preset"])
        ps.check_windows(f, preset)
        if ps.preset_sha256(f, preset) != row["preset_sha256"]:
            raise pk.PackError("the preset identity changed since the job was created; prepare again")
        for stale in pk.packs_root(self.data_root).glob(".tmp-*") if pk.packs_root(self.data_root).is_dir() else ():
            shutil.rmtree(stale, ignore_errors=True)  # an interrupted attempt's unpublished staging only

        # 1. reuse a trustworthy published pack: no network
        doc, problems = published_pack(conn, self.data_root, row["preset_sha256"])
        if problems:
            self._update(conn, job_id, diagnostic_log=[{"event": "published_pack_rejected", "detail": p}
                                                       for p in problems])
        if doc is not None:
            self._finish(conn, job_id, "completed", None, hb, outcome="reused_pack", pack_id=doc["pack_id"],
                         result=summary(doc, reused=True))
            return

        # 2. plan from local packages
        lo, hi = preset.warmup.start, preset.tail.end
        bound = {r["dataset_id"] for r in conn.execute("SELECT dataset_id FROM corpus_chunks").fetchall()}
        sources = pk.local_sources(self.data_root, f.instrument, bound)
        plan = pk.plan_slices(sources, lo, hi, f.acquisition_max_span_days)
        children = [{"kind": "acquire", "start": pk._iso(a), "end": pk._iso(b), "status": "pending"}
                    for a, b in plan.acquisitions]
        self._update(conn, job_id, plan=plan_doc(plan, sources, pk.estimate_bytes(sources, plan.acquisitions)),
                     children=children)
        self._check(hb)

        # 3. sequential acquisitions (explicit Owner action already given by Prepare)
        if plan.acquisitions:
            client = self.w.client_factory(row["base_url"])
            if client.base_url != row["base_url"]:
                raise RuntimeError(f"client base URL {client.base_url} differs from the job's {row['base_url']}")
            for i, (a, b) in enumerate(plan.acquisitions):
                hb.publish({"phase": "downloading", "detail": f"acquiring child {i + 1}/{len(plan.acquisitions)} "
                                                              f"{pk._iso(a)} -> {pk._iso(b)}", "child": i})

                def on_progress(p: md.AcquireProgress, i=i) -> None:
                    hb.publish({"phase": p.phase, "detail": f"child {i + 1}/{len(plan.acquisitions)}",
                                "windows_done": p.windows_done, "windows_total": p.windows_total,
                                "pages": p.pages, "bytes": p.bytes, "child": i})
                    self._check(hb)

                try:
                    result = md.acquire(client, self.data_root, a, b, inst_id=f.instrument, progress=on_progress)
                    problems = md.verify(result.path)
                    if problems:
                        raise pk.PackError(f"acquired child {pk._iso(a)} -> {pk._iso(b)} failed verification: "
                                           f"{problems}")
                except AcquisitionCancelled:
                    children[i] = {**children[i], "status": "cancelled"}
                    self._update(conn, job_id, children=children)
                    raise
                except Exception as exc:
                    children[i] = {**children[i], "status": "failed", "error": f"{type(exc).__name__}: {exc}"}
                    self._update(conn, job_id, children=children)
                    raise pk.PackError(f"required acquisition {pk._iso(a)} -> {pk._iso(b)} failed: {exc}; prepare "
                                       "again to retry (completed children are kept and reused)") from None
                children[i] = {**children[i], "status": "completed", "dataset_id": result.manifest.dataset_id,
                               "outcome": "acquired_identical_existing" if result.reused else "acquired",
                               "bytes": sum(x.bytes for x in result.manifest.files)}
                self._update(conn, job_id, children=children)  # recorded even if a cancel arrives now
                self._check(hb)
            sources = pk.local_sources(self.data_root, f.instrument, bound)
            plan = pk.plan_slices(sources, lo, hi, f.acquisition_max_span_days)
            if plan.missing:
                raise pk.PackError(f"requested interval still not covered after acquisition: {plan.missing}")
        acquired_ids = {c.get("dataset_id") for c in children if c["status"] == "completed"}

        # 4. per-source receipt-pinned caches (verify once when cold)
        hb.publish({"phase": "source_caches", "detail": f"preparing {len(plan.slices)} source slice cache(s)"})
        receipts = ReceiptStore(conn)
        slices = [(s.dataset_id, s.start, s.end, "acquired" if s.dataset_id in acquired_ids else "local")
                  for s in plan.slices]
        contribs = pk.prepare_contributors(self.data_root, receipts, slices, self._hook(hb, "source_caches"))

        # 5. compose one canonical pack feed cache
        hb.publish({"phase": "composing", "detail": "composing one canonical feed over the full requested interval"})
        work = fc.cache_root(self.data_root) / f".pack-work-{job_id}-{self.w.generation}"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        try:
            prov = work / "provenance.jsonl"
            counters: dict[str, Any] = {}
            cache, stats = pk.build_pack_cache(self.data_root, contribs, preset, work,
                                               self._hook(hb, "composing"), counters, provenance=prov)
            key = cache.manifest["key"]
            crec = receipts.get(cache.cache_id)
            if crec is None:
                crec = receipts.put(cache, key, "pack", cache.cache_id,
                                    hashlib.sha256(canonical(key)).hexdigest(), counters.get("durability", "unknown"),
                                    "composed from receipt-pinned verified source caches", {"pack_job": job_id})
            if crec["cache_manifest_sha256"] != cache.manifest_sha256:
                raise pk.PackError("pack feed cache does not match its trusted receipt")
            prov_name = prov_sha = None
            if stats.provenance_lines:
                prov_name, prov_sha = "provenance.jsonl", hashlib.sha256(prov.read_bytes()).hexdigest()
            doc = pk.manifest_body(f, preset, contribs, cache, stats, prov_sha, prov_name)
            staged = pk.stage_pack(self.data_root, doc, prov if prov_name else None)
        finally:
            shutil.rmtree(work, ignore_errors=True)

        # 6. fenced publication: rename + receipt + COMPLETED under the row lock
        hb.publish({"phase": "publishing", "detail": f"publishing {doc['pack_id']} (fenced)"})
        self._fault("before_publish_lock")
        msha = hashlib.sha256(pk.render_manifest(doc)).hexdigest()
        with conn.transaction():
            lock = conn.execute(f"SELECT cancel_requested FROM corpus_pack_jobs WHERE {self.fence} FOR UPDATE",
                                self._args(job_id)).fetchone()
            if lock is None:
                shutil.rmtree(staged, ignore_errors=True)
                raise LeaseLost()
            if lock["cancel_requested"]:
                shutil.rmtree(staged, ignore_errors=True)
                raise AcquisitionCancelled()
            how = pk.publish_staged(self.data_root, doc["pack_id"], staged)
            self._fault("after_rename")
            conn.execute(
                """INSERT INTO corpus_packs (pack_id, manifest_sha256, preset_id, preset_sha256, cache_id,
                       cache_manifest_sha256, content_identity, event_count, status, created_by_job, generation)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (pack_id) DO NOTHING""",
                (doc["pack_id"], msha, preset.preset_id, row["preset_sha256"], cache.cache_id, cache.manifest_sha256,
                 doc["feed"]["content_identity"], doc["feed"]["event_count"], doc["status"], job_id,
                 self.w.generation))
            rec = pk.pack_receipt(conn, doc["pack_id"])
            if rec["manifest_sha256"] != msha:
                raise pk.PackError(f"pack {doc['pack_id']} receipt differs from the published manifest")
            self._fault("before_commit")
            self._finish(conn, job_id, "completed", None, hb,
                         outcome={"published": "prepared", "converged": "prepared_converged"}.get(
                             how, "prepared_replaced_untrusted_directory"),
                         pack_id=doc["pack_id"], result=summary(doc, reused=False))
        log.info("%s: pack %s %s", job_id, doc["pack_id"], how)


def plan_doc(plan: pk.Plan, sources: list[pk.LocalSource], estimate: dict) -> dict:
    return {"slices": [{"dataset_id": s.dataset_id, "start": pk._iso(s.start), "end": pk._iso(s.end)}
                       for s in plan.slices],
            "missing": [[pk._iso(a), pk._iso(b)] for a, b in plan.missing],
            "acquisitions": [[pk._iso(a), pk._iso(b)] for a, b in plan.acquisitions],
            "local_packages": [{"dataset_id": s.dataset_id, "start": pk._iso(s.request_start),
                                "end": pk._iso(s.request_end), "bound": s.bound, "bytes": s.bytes} for s in sources],
            "estimate": estimate}


def summary(doc: dict, reused: bool) -> dict:
    return {"pack_id": doc["pack_id"], "status": doc["status"], "reused": reused,
            "event_count": doc["feed"]["event_count"], "content_identity": doc["feed"]["content_identity"],
            "sources": [{"dataset_id": s["dataset_id"], "start": s["start"], "end": s["end"]}
                        for s in doc["sources"]],
            "limitations": doc["limitations"], "storage": doc["storage"]}
