"""Bounded WP-011 engineering measurement (synthetic, offline; NOT market data, NOT an economic or month/year result).

1. Pure fold, v0.2 vs v0.3, 1 and 2 synthetic days (regime-switching walk; trade/mark/index minutes) through the
   harness that applies the kernel's exact order: wall time (no tracemalloc, so timing is not distorted), dispatches,
   journal records by kind (material records), explicit restore-state size and direct encode/decode time, process RSS.
2. Optional durable section (only with ALGOTRADER_TEST_DATABASE_URL pointing at a DISPOSABLE database): the v0.3 hand
   fixture prepared as a pack and run by the observation worker - committed transactions, restore-prefix events after a
   crash/reclaim (direct restore: 0 expected), pause-request-to-parked latency and journal rows by kind.

Output: delivery/evidence/WP-011-bench-mp002.json. Usage: uv run python scripts/bench_mp002.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from bench_adviser import synthetic  # noqa: E402

from algotrader import ops  # noqa: E402
from algotrader.adviser.engine import pack_runtime  # noqa: E402
from algotrader.adviser.harness import make_runtime, run_pure  # noqa: E402
from algotrader.feed.ordering import canonical  # noqa: E402

START = datetime(2025, 9, 1, tzinfo=UTC)


def pure(days: int, method: str) -> dict:
    mins = synthetic(days * 1440)
    t0 = time.perf_counter()
    res = run_pure(START, mins, eval_start=START, method=method)
    wall = time.perf_counter() - t0
    rt = res.runtime
    blob, _ = pack_runtime(rt)
    t1 = time.perf_counter()
    doc = json.loads(canonical(rt.encode()))
    type(rt).decode(doc, rt.core.cfg, make_runtime(eval_start=START, method=method).ev)
    restore = time.perf_counter() - t1
    events = days * 1440 * 3
    kinds = Counter(e["kind"] for e in res.journal)
    return {"method": method, "synthetic_days": days, "events": events, "wall_seconds": round(wall, 3),
            "events_per_second": round(events / wall, 1), "professional_dispatches": rt.dispatches,
            "journal_records": len(res.journal), "journal_records_by_kind": dict(sorted(kinds.items())),
            "evaluation_records": len(res.records), "calls": len(res.calls()),
            "restore_state_compressed_bytes": len(blob), "direct_restore_encode_decode_seconds": round(restore, 4),
            "process": ops.process_metrics()}


def durable(url: str) -> dict:
    import tempfile

    import pytest  # noqa: F401  (test helpers import it)
    from adviser3_fixtures import a3_return_long
    from adviser_db import fake_from, prepare_pack, replay, run_all, worker
    from pack_fixtures import connect

    from algotrader import db
    from algotrader.observe import control
    from algotrader.observe.contracts import SourceKind
    from algotrader.observe.job import SimulatedCrash

    db.migrate(url)
    tmp = Path(tempfile.mkdtemp(prefix="wp011-bench-"))
    os.environ["ALGOTRADER_CORPUS_PRESETS"] = str(tmp / "presets.json")
    from adviser_db import presets_doc

    (tmp / "presets.json").write_text(json.dumps(presets_doc()), encoding="utf-8")
    root, art = tmp / "data", tmp / "art"
    pack = prepare_pack(url, root, fake_from(a3_return_long(tail=520)))

    def launch():
        with connect(url) as c:
            return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], 0, False,
                                         expected_manifest_sha256=pack["manifest_sha256"],
                                         run_type="adviser_evaluation", adviser_method="v0.3")

    rid = launch()
    t0 = time.perf_counter()
    run_all(worker(url, root, art, "observe:bench-a", checkpoint_events=500))
    wall = time.perf_counter() - t0
    r = replay(url, rid)
    with connect(url) as c:
        kinds = {x["kind"]: x["n"] for x in c.execute(
            "SELECT kind, count(*) AS n FROM adviser_journal WHERE run_id = %s GROUP BY kind ORDER BY kind", (rid,))}
    metrics = next(iter(r["metrics"].values()), {}) if r["metrics"] else {}
    # crash right after a commit, reclaim: direct restore (no prefix replay)
    cid = launch()
    fired = {"x": False}

    def crash(replay_id, cursor):
        if replay_id == cid and cursor >= 3000 and not fired["x"]:
            fired["x"] = True
            raise SimulatedCrash()
    try:
        run_all(worker(url, root, art, "observe:bench-b", checkpoint_events=500, after_commit=crash))
    except SimulatedCrash:
        pass
    with connect(url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (cid,))
    run_all(worker(url, root, art, "observe:bench-c", checkpoint_events=500))
    rc = replay(url, cid)
    suffix = sum(v.get("restore_suffix_events", 0) for v in (rc["metrics"] or {}).values())
    # pause latency: request inside a commit hook, measured until the worker has parked the run
    pid = launch()
    seen: dict = {}

    def pause(replay_id, cursor):
        if replay_id == pid and cursor >= 2000 and "t" not in seen:
            with connect(url) as c:
                control.pause(c, replay_id)
            seen["t"] = time.perf_counter()
    run_all(worker(url, root, art, "observe:bench-d", checkpoint_events=500, after_commit=pause))
    latency = time.perf_counter() - seen["t"]
    paused = replay(url, pid)["status"]
    return {"fixture": "a3_return_long (v0.3 WAIT then RETURN), pack events " + str(r["total_events"]),
            "status": r["status"], "assurance": r["assurance"]["state"], "wall_seconds": round(wall, 3),
            "transactions_committed": metrics.get("transactions_committed"),
            "checkpoint_adviser_bytes": metrics.get("checkpoint_adviser_bytes"),
            "journal_rows_by_kind": kinds, "crash_reclaim_status": rc["status"],
            "restore_prefix_or_suffix_events_after_reclaim": suffix,
            "pause_request_to_parked_seconds": round(latency, 3), "pause_status": paused}


def main() -> None:
    out = {"label": "WP-011 bounded engineering measurement - synthetic fixtures on the executor machine; not a "
                    "month/year, performance-gate or economic result", "python": sys.version.split()[0],
           "pure": [pure(d, m) for m in ("v0.2", "v0.3") for d in (1, 2)]}
    for m in ("v0.2", "v0.3"):
        a, b = [x for x in out["pure"] if x["method"] == m]
        out[f"scaling_{m}"] = {"wall_ratio_2d_over_1d": round(b["wall_seconds"] / a["wall_seconds"], 2),
                               "state_ratio_2d_over_1d": round(b["restore_state_compressed_bytes"]
                                                               / a["restore_state_compressed_bytes"], 2)}
    url = os.environ.get("ALGOTRADER_TEST_DATABASE_URL")
    out["durable"] = durable(url) if url else "NOT_RUN (no disposable database configured)"
    p = ROOT / "delivery" / "evidence" / "WP-011-bench-mp002.json"
    p.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
