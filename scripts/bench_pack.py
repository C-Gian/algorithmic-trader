"""Bounded engineering measurement for evaluation packs at two tiny synthetic fixture sizes (WP-008-R3).

NOT a historical evaluation, performance gate or annual claim: deterministic synthetic OKX rows served offline through
the accepted acquisition path, a disposable database, and the real pack job + streaming replay. For each size it
records pack preparation (children, events, composed cache bytes = added disk), replay events/transactions/
checkpoints, compute RSS, and the pause control latency (request -> parked) of a paced (1,000 events/s) replay.

    uv run python scripts/bench_pack.py --admin-url postgresql://postgres:PASS@127.0.0.1:5432/postgres --out DIR
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


def run_size(admin: str, eval_hours: int) -> dict:
    import psycopg
    from psycopg import sql

    import pack_fixtures as pf
    from algotrader import db
    from algotrader.corpus import pack as pk
    from algotrader.corpus import pack_job as pj
    from algotrader.corpus import presets as ps
    from algotrader.observe import control
    from algotrader.observe.contracts import SourceKind
    from algotrader.observe.worker import ObservationWorker

    name = f"bench_pack_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = psycopg.conninfo.make_conninfo(**{**psycopg.conninfo.conninfo_to_dict(admin), "dbname": name})
    try:
        db.migrate(url)
        tmp = Path(tempfile.mkdtemp(prefix="bench-pack-"))
        ev_end = pf.EV_START + timedelta(hours=eval_hours)
        p = tmp / "presets.json"
        p.write_text(json.dumps(pf.presets_doc(ev_end=ev_end)), encoding="utf-8")
        os.environ["ALGOTRADER_CORPUS_PRESETS"] = str(p)
        root = tmp / "data"
        f = pf.synthetic_fake(pf.FAKE_START, ev_end + timedelta(hours=2), gap_every=None)
        pf.acquire(root, f, pf.EV_START, ev_end)  # evaluation interval already local
        f.calls.clear()
        with pf.connect(url) as c:
            P = ps.load_presets()
            jid = pj.create_pack_job(c, P, P.default)
        t0 = time.perf_counter()
        pf.drain(pf.corpus_worker(url, root, f))
        prep_s = time.perf_counter() - t0
        with pf.connect(url) as c:
            job = c.execute("SELECT * FROM corpus_pack_jobs WHERE job_id = %s", (jid,)).fetchone()
            rec = pk.pack_receipt(c, job["pack_id"])
            doc = pk.open_pack(root, job["pack_id"], rec)
            rid = control.create_replay(c, root, SourceKind.PACK, job["pack_id"], 1000, False,
                                        expected_manifest_sha256=rec["manifest_sha256"])
        w = ObservationWorker(url, root, tmp / "art", worker_id="observe:bench", isolate=True, poll_interval=0.02,
                              checkpoint_events=200)
        stop = threading.Event()
        th = threading.Thread(target=w.run_forever, args=(stop.is_set,), daemon=True)
        t1 = time.perf_counter()
        th.start()
        total = doc["feed"]["event_count"]
        pause_latency = None
        with pf.connect(url) as c:
            while True:
                r = c.execute("SELECT status, c.cursor FROM observation_replays LEFT JOIN observation_checkpoints c "
                              "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()
                if r["status"] in ("completed", "failed", "cancelled"):
                    break
                if pause_latency is None and (r["cursor"] or 0) >= total // 3:
                    tp = time.perf_counter()
                    control.pause(c, rid)
                    while c.execute("SELECT status FROM observation_replays WHERE replay_id = %s",
                                    (rid,)).fetchone()["status"] != "paused":
                        time.sleep(0.01)
                    pause_latency = time.perf_counter() - tp
                    control.resume(c, rid)
                time.sleep(0.02)
            row = c.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
        replay_s = time.perf_counter() - t1
        stop.set()
        th.join(10)
        gens = row["metrics"]
        return {
            "eval_hours": eval_hours,
            "requested_minutes": doc["windows"]["warmup"]["minutes"] + doc["windows"]["evaluation"]["minutes"]
            + doc["windows"]["tail"]["minutes"],
            "pack": {"status": doc["status"], "event_count": total, "sources": len(doc["sources"]),
                     "children_downloaded": len(job["children"]), "okx_requests": len(f.calls),
                     "pack_cache_bytes_added": doc["storage"]["pack_cache_bytes"],
                     "pack_cache_partitions": doc["storage"]["pack_cache_partitions"],
                     "source_package_bytes": doc["storage"]["source_package_bytes"],
                     "prepare_wall_s": round(prep_s, 2)},
            "replay": {"status": row["status"], "validator_version": row["manifest"]["validation"]["validator_version"],
                       "passed": row["manifest"]["validation"]["passed"], "wall_s": round(replay_s, 2),
                       "pause_applied_s": round(pause_latency, 3) if pause_latency is not None else None,
                       "per_generation": {g: {k: m.get(k) for k in ("events_applied", "transactions_committed",
                                                                     "checkpoints_committed", "delivery_rows_written",
                                                                     "prefix_restore_events", "max_rss_bytes",
                                                                     "checkpoint_state_bytes",
                                                                     "checkpoint_temporal_bytes", "cpu_seconds")}
                                          for g, m in gens.items()}},
        }
    finally:
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin-url", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import platform

    res = {"note": "tiny synthetic engineering fixtures; not a historical evaluation, gate or annual claim",
           "platform": f"{platform.platform()} · Python {platform.python_version()} · {os.cpu_count()} logical CPUs",
           "sizes": [run_size(a.admin_url, h) for h in (6, 24)]}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "bench_pack.json").write_text(json.dumps(res, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(res, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
