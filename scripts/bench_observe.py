"""Reproducible offline engineering benchmark for the observation pipeline (WP-008-R1C).

SYNTHETIC INFRASTRUCTURE EVIDENCE ONLY - deterministic generated evidence served through the accepted offline
acquisition path (no network) plus captured short edge fixtures. It is NOT a historical month/year evaluation,
not a strategy test and not an Owner-hardware speedup claim. Real September evidence is launched by the Owner
in the app.

Tiers (each phase measured separately from the persisted operation records):

* ``pilot``  - 2-day dataset, full job path (separate compute processes), cold + warm + Deep validation;
* ``month``  - 30-day dataset (43,200 minutes, a 2-day long gap, shuffled Parquet rows), full job path:
               cold (snapshot / verify / cache / replay / reconcile / report), warm, pause + direct restore,
               Deep validation;
* ``partitions`` - the same month replayed with 500-event partitions (many-partition case, inline worker);
* ``recording``  - captured recorder session with 60 repeated completions per push (dedup-heavy);
* ``year``   - component level (no job/DB): a generated 365-day observation stream (~1.58 M events) through
               cold cache build, kernel replay with checkpoint-cadence state encoding and the reconciliation
               re-hash, in a fresh process with peak RSS and Python heap.

Usage::

    uv run python scripts/bench_observe.py --admin-url postgresql://postgres:postgres@127.0.0.1:55432/postgres \
        --out var/benchmarks/r1c --tiers pilot,month,partitions,recording,year --budget-minutes 60

A tier is skipped (and reported as SKIPPED - budget) if the declared budget would be exceeded.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import platform
import shutil
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

DAY = timedelta(days=1)
MIN = timedelta(minutes=1)
S0 = datetime(2026, 6, 1, tzinfo=UTC)

GATES = {  # reference release objectives (seconds) from the SR-003 disposition
    "month_cached_observation_s": 120.0, "month_terminal_report_s": 10.0, "month_cold_preparation_s": 120.0,
    "year_cached_observation_s": 900.0, "year_terminal_report_s": 30.0, "year_cold_preparation_s": 900.0,
}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def total_ram() -> int | None:
    try:
        if sys.platform == "win32":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = MS()
            ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return int(ms.ullTotalPhys)
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError, AttributeError):
        return None


def environment(out: Path) -> dict:
    import subprocess

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                                    cwd=ROOT).stdout.strip())
    except OSError:
        sha, dirty = None, None
    du = shutil.disk_usage(out)
    return {"captured_at": datetime.now(UTC).isoformat(), "build": sha, "worktree_dirty": dirty,
            "os": platform.platform(), "python": platform.python_version(), "cpu": platform.processor() or
            platform.machine(), "logical_cpus": os.cpu_count(), "ram_bytes": total_ram(),
            "storage": {"path": str(out), "total_bytes": du.total, "free_bytes": du.free},
            "runtime_limits": "local machine, no container CPU/memory limits applied by the benchmark"}


# ---------------------------------------------------------------------------
# Lazily generated offline OKX transport (rows computed per page; nothing retained)
# ---------------------------------------------------------------------------


def lazy_fake(start: datetime, end: datetime, gaps=(), gap_every: int | None = 97):
    from okx_fake import SOURCE_IDS, FakeOkx, envelope

    from algotrader.marketdata.contracts import Family

    s_ms, e_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    gap_ms = [(int(a.timestamp() * 1000), int(b.timestamp() * 1000)) for a, b in gaps]

    def present(ms: int) -> bool:
        i = (ms - s_ms) // 60000
        return not any(a <= ms < b for a, b in gap_ms) and not (gap_every and i % gap_every == gap_every - 1)

    def candle(fam, ms: int):
        i = (ms - s_ms) // 60000
        p = 80000 + (i * 37 % 1000) / 10
        o, h, lo, c = p, p + 5, p - 5, p + 1
        if fam == Family.TRADE_CANDLES:
            return [str(ms), f"{o:.1f}", f"{h:.1f}", f"{lo:.1f}", f"{c:.1f}", "100", "1", "80000.5", "1"]
        off = 40 if fam == Family.INDEX_CANDLES else 0
        return [str(ms), f"{o + off:.1f}", f"{h + off:.1f}", f"{lo + off:.1f}", f"{c + off:.1f}", "1"]

    class LazyOkx(FakeOkx):
        def __call__(self, url, headers, timeout):
            import urllib.parse

            from okx_fake import PATH_FAMILY

            parts = urllib.parse.urlsplit(url)
            params = dict(urllib.parse.parse_qsl(parts.query))
            family = PATH_FAMILY[parts.path]
            if family == Family.INSTRUMENT:
                return 200, self.instrument_body
            if params.get("instId") != SOURCE_IDS[family]:
                return 200, envelope([], "51001", "unknown instrument")
            after = int(params.get("after", 2 ** 62))
            before = int(params.get("before", -1))
            limit = int(params.get("limit", 100))
            rows = []
            if family == Family.FUNDING:
                step = 8 * 3600 * 1000
                ms = min(after - 1, e_ms - 1) // step * step
                while ms > before and ms >= s_ms and len(rows) < limit:
                    rows.append({"formulaType": "withRate", "fundingRate": "0.0001", "fundingTime": str(ms),
                                 "instId": "BTC-USDT-SWAP", "instType": "SWAP", "method": "current_period",
                                 "realizedRate": "0.0001"})
                    ms -= step
            else:
                ms = (min(after - 1, e_ms - 1) - s_ms) // 60000 * 60000 + s_ms
                while ms > before and ms >= s_ms and len(rows) < limit:
                    if present(ms):
                        rows.append(candle(family, ms))
                    ms -= 60000
            return 200, envelope(rows)

    return LazyOkx()


def acquire(root: Path, days: int, gap_days: float = 0.0) -> str:
    from okx_fake import client

    from algotrader.marketdata import dataset as md

    end = S0 + days * DAY
    gaps = ((S0 + 5 * DAY, S0 + 5 * DAY + gap_days * DAY),) if gap_days else ()
    return md.acquire(client(lazy_fake(S0, end, gaps)), root, S0, end).manifest.dataset_id


# ---------------------------------------------------------------------------
# Job-path measurement (persisted operation records are the measurement source)
# ---------------------------------------------------------------------------


def run_job(url: str, root: Path, art: Path, rid: str, isolate: bool = True) -> dict:
    from algotrader import db
    from algotrader.observe.worker import ObservationWorker

    w = ObservationWorker(url, root, art, worker_id=f"observe:bench-{uuid.uuid4().hex[:4]}", isolate=isolate,
                          poll_interval=0.05)
    t0 = time.perf_counter()
    while w.run_once():
        pass
    wall = time.perf_counter() - t0
    with db.connection(url) as c:
        r = c.execute("SELECT r.*, k.cursor FROM observation_replays r LEFT JOIN observation_checkpoints k "
                      "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()
        nranges = c.execute("SELECT count(*) AS n FROM observation_ranges WHERE replay_id = %s", (rid,)).fetchone()["n"]
        ndeliv = c.execute("SELECT count(*) AS n FROM observation_deliveries WHERE replay_id = %s",
                           (rid,)).fetchone()["n"]
    return summarize(r, wall, nranges, ndeliv)


def summarize(r: dict, wall: float, nranges: int, ndeliv: int) -> dict:
    phases: dict[str, dict] = {}
    for e in r["phase_history"]:
        p = phases.setdefault(e["phase"], {"active_s": 0.0, "wall_s": 0.0, "waiting_s": 0.0, "unmeasured": 0})
        p["wall_s"] += e.get("wall_seconds") or 0.0
        if e.get("measured", e.get("active_seconds") is not None):
            p["active_s"] += e.get("active_seconds") or 0.0
            p["waiting_s"] += e.get("waiting_seconds") or 0.0
        else:
            p["unmeasured"] += 1
    gens = r["metrics"] or {}
    m = (r["manifest"] or {}).get("operational_metrics") or gens.get(str(r["lease_generation"])) or {}
    act = {k: round(v["active_s"], 3) for k, v in phases.items()}
    prep = sum(act.get(k, 0) for k in ("PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED"))
    term = sum(act.get(k, 0) for k in ("FINALIZING", "VALIDATING", "GENERATING_REPORT"))
    return {"replay_id": r["replay_id"], "status": r["status"], "assurance": (r["assurance"] or {}).get("state"),
            "events": r["total_events"], "cursor": r["cursor"], "wall_including_process_spawn_s": round(wall, 3),
            "phase_active_s": act, "phase_wall_s": {k: round(v["wall_s"], 3) for k, v in phases.items()},
            "preparation_active_s": round(prep, 3), "terminal_report_active_s": round(term, 3),
            "replay_events_per_s": round(r["total_events"] / act["REPLAYING"], 1) if act.get("REPLAYING") else None,
            "counters": {k: m.get(k) for k in (
                "source_verifications", "feed_builds", "cache_reused", "cache_build_events", "sort_spill_runs",
                "events_applied", "snapshots_built", "state_encodes", "transactions_committed",
                "checkpoints_committed", "delivery_rows_written", "restore_suffix_events", "prefix_restore_events",
                "cache_bytes_read", "cache_partitions_read", "checkpoint_state_bytes", "output_bytes",
                "max_control_gap_seconds", "max_rss_bytes", "max_rss_source", "cpu_seconds")},
            "ranges": nranges, "delivery_rows": ndeliv}


def deep_job(url: str, root: Path, art: Path, rid: str) -> dict:
    from algotrader import db
    from algotrader.observe import deep
    from algotrader.observe.worker import ObservationWorker

    with db.connection(url) as c:
        vid = deep.create_deep_validation(c, rid)
        c.commit()
    w = ObservationWorker(url, root, art, worker_id="observe:bench-deep", isolate=True, poll_interval=0.05)
    t0 = time.perf_counter()
    while w.run_once():
        pass
    wall = time.perf_counter() - t0
    with db.connection(url) as c:
        d = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    act = {}
    for e in d["phase_history"]:
        act[e["phase"]] = round(act.get(e["phase"], 0) + (e.get("active_seconds") or 0), 3)
    gen = (d["metrics"] or {}).get(str(d["lease_generation"]), {})
    return {"validation_id": vid, "status": d["status"], "outcome": (d["result"] or {}).get("outcome"),
            "compared": (d["result"] or {}).get("compared"), "covered": (d["result"] or {}).get("covered_events"),
            "wall_including_process_spawn_s": round(wall, 3), "phase_active_s": act,
            "events_per_s": round(d["result"]["covered_events"] / act["VALIDATING"], 1) if act.get("VALIDATING") else None,
            "max_rss_bytes": gen.get("max_rss_bytes")}


def pause_restore(url: str, root: Path, art: Path, ds: str) -> dict:
    """Pause a replay at ~half, then resume: measures checkpoint save and DIRECT restore (no prefix replay)."""
    import threading

    from algotrader import db
    from algotrader.observe import control
    from algotrader.observe.contracts import SourceKind
    from algotrader.observe.worker import ObservationWorker

    with db.connection(url) as c:
        rid = control.create_replay(c, root, SourceKind.DATASET, ds, speed=0)
        c.commit()
    w = ObservationWorker(url, root, art, worker_id="observe:bench-pr", isolate=True, poll_interval=0.05)
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    with db.connection(url) as c:
        while True:
            r = c.execute("SELECT total_events, progress FROM observation_replays WHERE replay_id = %s",
                          (rid,)).fetchone()
            c.commit()
            if r["total_events"] and (r["progress"] or {}).get("done", 0) >= r["total_events"] // 2:
                break
            time.sleep(0.05)
        t0 = time.perf_counter()
        control.pause(c, rid)
        c.commit()
    t.join(120)
    pause_s = time.perf_counter() - t0
    with db.connection(url) as c:
        control.resume(c, rid)
        c.commit()
    res = run_job(url, root, art, rid)
    res["pause_applied_s"] = round(pause_s, 3)
    with db.connection(url) as c:
        r = c.execute("SELECT metrics, lease_generation FROM observation_replays WHERE replay_id = %s",
                      (rid,)).fetchone()
    g = r["metrics"][str(r["lease_generation"])]
    res["restore"] = {"prefix_restore_events": g.get("prefix_restore_events"),
                      "restore_suffix_events": g.get("restore_suffix_events"),
                      "events_applied_after_resume": g.get("events_applied"),
                      "initializing_active_s": res["phase_active_s"].get("INITIALIZING")}
    return res


def launch(url: str, root: Path, ds: str, kind: str = "dataset") -> str:
    from algotrader import db
    from algotrader.observe import control

    with db.connection(url) as c:
        rid = control.create_replay(c, root, kind, ds, speed=0)
        c.commit()
    return rid


# ---------------------------------------------------------------------------
# Year component tier (fresh process; no DB)
# ---------------------------------------------------------------------------


def year_component(args: dict) -> dict:
    import gzip
    import hashlib
    import tracemalloc
    from decimal import Decimal

    sys.path.insert(0, str(ROOT / "src"))
    from algotrader import ops
    from algotrader.feed.adapter import make_event
    from algotrader.feed.contracts import (
        ChannelCoverage, ChannelRef, EventKind, Family, IndexBarPayload, MarkBarPayload, QualityReason,
        SlotQualityPayload, SourceRef, TradeBarPayload)
    from algotrader.feed.ordering import default_freshness, modeled_availability
    from algotrader.observe import feedcache as fc
    from algotrader.observe.kernel import Kernel

    days = args["days"]
    start, end = S0, S0 + days * DAY
    gap = (S0 + 40 * DAY, S0 + 47 * DAY)  # a one-week long gap -> absent-slot quality evidence
    pol = modeled_availability()
    chans = [ChannelRef(source="okx", family=Family.TRADE_BAR_1M, series_id="BTC-USDT-SWAP"),
             ChannelRef(source="okx", family=Family.MARK_BAR_1M, series_id="BTC-USDT-SWAP"),
             ChannelRef(source="okx", family=Family.INDEX_BAR_1M, series_id="BTC-USDT")]
    src = SourceRef(dataset_id="synthetic-year", artifact="generated", row_index=None, raw_page_ref=None,
                    retrieved_at=None, source_availability_policy="generated")

    def events():  # generated lazily; nothing retained
        t, i = start, 0
        while t < end:
            p = Decimal(80000 + (i * 37 % 1000) / 10)
            for ch in chans:
                if gap[0] <= t < gap[1] or i % 997 == 996:
                    yield make_event(ch, EventKind.SLOT_QUALITY, t, t + MIN, t + MIN, pol, src,
                                     SlotQualityPayload(reason=QualityReason.MISSING, detail="generated gap"))
                elif ch.family == Family.TRADE_BAR_1M:
                    yield make_event(ch, EventKind.BAR_OBSERVATION, t, t + MIN, t + MIN, pol, src, TradeBarPayload(
                        open=p, high=p + 5, low=p - 5, close=p + 1, volume_contracts=Decimal(100),
                        volume_base=Decimal(1), volume_base_ccy="BTC", volume_quote=Decimal("80000.5"),
                        volume_quote_ccy="USDT"))
                elif ch.family == Family.MARK_BAR_1M:
                    yield make_event(ch, EventKind.BAR_OBSERVATION, t, t + MIN, t + MIN, pol, src,
                                     MarkBarPayload(open=p, high=p + 5, low=p - 5, close=p + 1))
                else:
                    yield make_event(ch, EventKind.BAR_OBSERVATION, t, t + MIN, t + MIN, pol, src,
                                     IndexBarPayload(index_id="BTC-USDT", open=p, high=p, low=p, close=p))
            t += MIN
            i += 1

    cov = tuple(ChannelCoverage(channel=c, covered_from=start, covered_until=end, expected_cadence=MIN) for c in chans)
    root = Path(args["root"])
    # Timing pass: NO tracemalloc (tracing slows CPython ~3x; a first run with tracing active measured 984 s replay).
    counters: dict = {}
    t0 = time.perf_counter()
    cache = fc.build_cache(root, {"generated": f"year-{days}", "format": fc.CACHE_FORMAT}, events(), lambda: cov, pol,
                           ("synthetic-year",), lambda: ("BTC-USDT-SWAP", "BTC-USDT", {"inst_id": "BTC-USDT-SWAP"}),
                           lambda: {"quality": "generated", "warnings": [], "notes": []}, counters=counters)
    cold = time.perf_counter() - t0
    rss_build = ops.process_metrics().get("max_rss_bytes")
    fresh = default_freshness()

    def replay_pass(limit: int | None, sample_every: int | None):
        k = Kernel(cache.feed_meta, fresh, None, fc.initial_commitment(cache.cache_id))
        reader = fc.CacheReader(cache, {})
        last_ck, ck_t, checkpoints, ck_bytes, samples = 0, time.monotonic(), 0, 0, []
        seg_t, seg = time.perf_counter(), max(1, (limit or cache.event_count) // 10)
        for _seq, line in reader.iter_from(0):
            k.apply_line(line)
            if k.cursor - last_ck >= 5000 or time.monotonic() - ck_t >= 2.0:
                k.snapshot()
                blob, _sha = k.pack()
                ck_bytes = len(blob)
                checkpoints += 1
                last_ck, ck_t = k.cursor, time.monotonic()
            if k.cursor % seg == 0:
                now = time.perf_counter()
                samples.append({"cursor": k.cursor, "events_per_s": round(seg / (now - seg_t), 1),
                                **({"heap_current_mb": round(tracemalloc.get_traced_memory()[0] / 2**20, 2)}
                                   if sample_every else {})})
                seg_t = now
            if limit and k.cursor >= limit:
                break
        k.snapshot()
        return k, checkpoints, ck_bytes, samples

    t0 = time.perf_counter()
    k, checkpoints, ck_bytes, segments = replay_pass(None, None)
    replay = time.perf_counter() - t0
    rss_replay = ops.process_metrics().get("max_rss_bytes")
    t0 = time.perf_counter()  # the terminal reconciliation's dominant cost: re-hash every consumed line
    h = fc.initial_commitment(cache.cache_id)
    for p in cache.partitions:
        data = (cache.path / p["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == p["sha256"]
        for line in gzip.decompress(data).split(b"\n")[:-1]:
            h = fc.extend_commitment(h, line)
    assert h.hex() == cache.manifest["final_commitment"] == k.commitment.hex()
    terminal = time.perf_counter() - t0
    # Memory pass (separate, traced, bounded): Python-heap plateau over the first heap_sample_events events.
    tracemalloc.start()
    _k2, _c2, _b2, heap_samples = replay_pass(args["heap_sample_events"], 1)
    heap_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    pm = ops.process_metrics()
    return {"days": days, "events": cache.event_count, "partitions": len(cache.partitions),
            "cache_bytes": sum(p["bytes"] for p in cache.partitions),
            "manifest_bytes": (cache.path / "manifest.json").stat().st_size,
            "cold_cache_build_s": round(cold, 2), "replay_s": round(replay, 2),
            "replay_events_per_s": round(cache.event_count / replay, 1), "replay_segments": segments,
            "terminal_rehash_s": round(terminal, 2),
            "checkpoints_equivalent": checkpoints, "state_blob_bytes": ck_bytes,
            "rss_peak_after_build_bytes": rss_build, "rss_peak_after_replay_bytes": rss_replay,
            "max_rss_bytes": pm.get("max_rss_bytes"),
            "rss_source": pm.get("max_rss_source") or pm.get("max_rss_unknown_reason"),
            "heap_pass": {"events": args["heap_sample_events"], "heap_peak_mb": round(heap_peak / 2**20, 1),
                          "samples": heap_samples,
                          "note": "separate traced pass; timings in this pass are not used"},
            "sort": counters.get("sort"),
            "note": "component level: no job, DB transactions or process spawn; DB checkpoint cost per commit is "
                    "measured in the month tier (one transaction per checkpoint). Cold preparation here is the "
                    "cache build only (no source snapshot/verification)."}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin-url", required=True, help="disposable PostgreSQL server (a new database is created)")
    ap.add_argument("--out", type=Path, default=ROOT / "var" / "benchmarks" / "r1c")
    ap.add_argument("--tiers", default="pilot,month,partitions,recording,year")
    ap.add_argument("--budget-minutes", type=float, default=60.0)
    ap.add_argument("--year-days", type=int, default=365)
    a = ap.parse_args()
    import psycopg
    from psycopg import sql

    from algotrader import db

    out = a.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    report: dict = {"kind": "R1C synthetic engineering benchmark (not a historical evaluation)",
                    "environment": environment(out), "gates": GATES, "tiers": {}, "budget_minutes": a.budget_minutes}
    deadline = time.monotonic() + a.budget_minutes * 60
    name = f"bench_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(a.admin_url, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = a.admin_url.rsplit("/", 1)[0] + "/" + name
    db.migrate(url)
    tiers = a.tiers.split(",")
    est = {"pilot": 2, "month": 12, "partitions": 6, "recording": 1, "year": 30}

    def budget(tier: str) -> bool:
        left = (deadline - time.monotonic()) / 60
        if left < est[tier]:
            report["tiers"][tier] = {"status": f"SKIPPED - budget ({left:.1f} min left, ~{est[tier]} min needed)"}
            return False
        return True

    try:
        if "pilot" in tiers and budget("pilot"):
            root, art = out / "pilot" / "data", out / "pilot" / "art"
            ds = acquire(root, 2)
            cold = run_job(url, root, art, launch(url, root, ds))
            warm = run_job(url, root, art, launch(url, root, ds))
            report["tiers"]["pilot"] = {"cold": cold, "warm": warm, "deep": deep_job(url, root, art, warm["replay_id"])}
            print("pilot done", flush=True)
        if "month" in tiers and budget("month"):
            from okx_synth import shuffle_parquet

            from algotrader.marketdata import dataset as md

            root, art = out / "month" / "data", out / "month" / "art"
            t0 = time.perf_counter()
            ds = acquire(root, 30, gap_days=2)
            shuffle_parquet(md.dataset_path(root, ds))
            acq = time.perf_counter() - t0
            cold = run_job(url, root, art, launch(url, root, ds))
            warm = run_job(url, root, art, launch(url, root, ds))
            pr = pause_restore(url, root, art, ds)
            dp = deep_job(url, root, art, warm["replay_id"])
            report["tiers"]["month"] = {"synthetic_acquisition_s": round(acq, 2), "cold": cold, "warm": warm,
                                        "pause_restore": pr, "deep": dp}
            print("month done", flush=True)
        if "partitions" in tiers and budget("partitions") and "month" in report["tiers"]:
            from algotrader.observe import feedcache as fc

            fc.PARTITION_EVENTS = 500  # inline worker: the many-partition case in this process
            root, art = out / "month" / "data", out / "partitions" / "art"
            ds = report["tiers"]["month"]["cold"]["replay_id"]
            from algotrader import db as _db

            with _db.connection(url) as c:
                src = c.execute("SELECT source_id FROM observation_replays WHERE replay_id = %s", (ds,)).fetchone()
            r = run_job(url, root, art, launch(url, root, src["source_id"]), isolate=False)
            report["tiers"]["partitions"] = {"partition_events": 500, "run": r}
            fc.PARTITION_EVENTS = 5000
            print("partitions done", flush=True)
        if "recording" in tiers and budget("recording"):
            from test_stream_bounds import heavy_recording

            root, art = out / "recording" / "data", out / "recording" / "art"
            sid = heavy_recording(root, 60, "rec-bench")
            report["tiers"]["recording"] = {"repeats": 60, "run": run_job(url, root, art,
                                                                          launch(url, root, sid, "recording"))}
            print("recording done", flush=True)
        if "year" in tiers and budget("year"):
            ctx = multiprocessing.get_context("spawn")
            with ctx.Pool(1) as pool:
                report["tiers"]["year"] = pool.apply(year_component, ({"root": str(out / "year"), "days": a.year_days,
                                                                       "heap_sample_events": min(300_000, a.year_days * 4320)},))
            print("year done", flush=True)
    finally:
        with psycopg.connect(a.admin_url, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
    report["gate_evaluation"] = evaluate(report)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out / "report.md").write_text(render(report), encoding="utf-8")
    print(render(report))


def evaluate(r: dict) -> list[dict]:
    rows = []
    m = r["tiers"].get("month") or {}
    if "warm" in m:
        rows += [
            {"gate": "month cached observation (warm run, launch->terminal incl. process spawn)",
             "measured_s": m["warm"]["wall_including_process_spawn_s"], "limit_s": GATES["month_cached_observation_s"]},
            {"gate": "month terminal validation/report (warm run, active)",
             "measured_s": m["warm"]["terminal_report_active_s"], "limit_s": GATES["month_terminal_report_s"]},
            {"gate": "month cold preparation (snapshot+verify+cache, active)",
             "measured_s": m["cold"]["preparation_active_s"], "limit_s": GATES["month_cold_preparation_s"]},
        ]
    y = r["tiers"].get("year") or {}
    if "replay_s" in y:
        rows += [
            {"gate": "year cached observation (component: kernel replay + checkpoint-cadence encoding)",
             "measured_s": y["replay_s"], "limit_s": GATES["year_cached_observation_s"]},
            {"gate": "year terminal validation (component: consumed-input re-hash)",
             "measured_s": y["terminal_rehash_s"], "limit_s": GATES["year_terminal_report_s"]},
            {"gate": "year cold preparation (component: cache build only; snapshot/verify not included)",
             "measured_s": y["cold_cache_build_s"], "limit_s": GATES["year_cold_preparation_s"]},
        ]
    for row in rows:
        row["result"] = "PASS" if row["measured_s"] is not None and row["measured_s"] <= row["limit_s"] else "FAIL"
    return rows


def render(r: dict) -> str:
    env = r["environment"]
    lines = ["# R1C synthetic engineering benchmark", "",
             "> Deterministic generated evidence through the offline acquisition path. Not a historical month/year "
             "evaluation, strategy test or Owner-hardware claim.", "",
             f"- Build `{env['build']}` (dirty={env['worktree_dirty']}) · {env['os']} · Python {env['python']}",
             f"- CPU {env['cpu']} · {env['logical_cpus']} logical · RAM "
             f"{(env['ram_bytes'] or 0) / 2**30:.1f} GiB · storage free {env['storage']['free_bytes'] / 2**30:.1f} GiB",
             f"- {env['runtime_limits']} · budget {r['budget_minutes']} min", "", "## Gates", "",
             "| Gate | Measured s | Limit s | Result |", "|---|---|---|---|"]
    for g in r["gate_evaluation"]:
        lines.append(f"| {g['gate']} | {g['measured_s']} | {g['limit_s']} | {g['result']} |")
    for name, t in r["tiers"].items():
        lines += ["", f"## {name}", "", "```json", json.dumps(t, indent=1, default=str)[:6000], "```"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
