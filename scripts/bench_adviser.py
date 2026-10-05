"""Bounded WP-009 engineering measurement (synthetic, offline; NOT market data, NOT an economic result).

Two sizes (1 and 2 synthetic days of 1m trade/mark/index minutes) through the pure harness that applies the kernel's
exact order (factual event -> temporal -> professional barriers -> admission): wall time, events/s, professional
dispatches, journal/evaluation records and bytes, explicit restore-state size and encode/decode (direct restore)
time, peak traced Python memory and process RSS. Output: delivery/evidence/WP-009-bench-adviser.json.

Usage: uv run python scripts/bench_adviser.py
"""

from __future__ import annotations

import json
import random
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from algotrader import ops
from algotrader.adviser.engine import pack_runtime
from algotrader.adviser.harness import Minute, run_pure
from algotrader.adviser.runtime import AdviserRuntime
from algotrader.feed.ordering import canonical

ROOT = Path(__file__).resolve().parents[1]
START = datetime(2025, 9, 1, tzinfo=UTC)


def synthetic(minutes: int, seed: int = 11) -> list[Minute]:
    """Regime-switching random walk (trend / range / compression) so every family's machinery is exercised."""
    rnd = random.Random(seed)
    p = Decimal(100000)
    out = []
    for i in range(minutes):
        regime = (i // 240) % 3
        drift = Decimal(6) if regime == 0 else Decimal(0)
        vol = 25 if regime != 2 else 6
        step = drift + Decimal(rnd.randint(-vol, vol))
        o, c = p, p + step
        h = max(o, c) + Decimal(rnd.randint(0, vol))
        lo = min(o, c) - Decimal(rnd.randint(0, vol))
        out.append(Minute(o, h, lo, c))
        p = c
    return out


def measure(days: int) -> dict:
    mins = synthetic(days * 1440)
    tracemalloc.start()
    t0 = time.perf_counter()
    res = run_pure(START, mins, eval_start=START + (START - START))
    wall = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    rt = res.runtime
    blob, sha = pack_runtime(rt)
    t1 = time.perf_counter()
    doc = json.loads(canonical(rt.encode()))
    AdviserRuntime.decode(doc, rt.core.cfg, None if rt.ev is None else type(rt.ev)(
        rt.core.p, rt.core.tick, eval_start=rt.ev.eval_start, eval_end=rt.ev.eval_end))
    restore = time.perf_counter() - t1
    events = days * 1440 * 3
    jbytes = sum(len(canonical(e["record"])) for e in res.journal)
    rbytes = sum(len(canonical(r["record"])) for r in res.records)
    return {"synthetic_days": days, "events": events, "wall_seconds": round(wall, 3),
            "events_per_second": round(events / wall, 1), "professional_dispatches": rt.dispatches,
            "journal_records": len(res.journal), "journal_bytes": jbytes, "evaluation_records": len(res.records),
            "evaluation_bytes": rbytes, "calls": len(res.calls()),
            "restore_state_compressed_bytes": len(blob), "restore_encode_decode_seconds": round(restore, 4),
            "peak_traced_python_bytes": peak, "process": ops.process_metrics()}


def main() -> None:
    out = {"label": "WP-009 bounded engineering measurement — synthetic fixtures, executor machine; not a month/year "
                    "or economic result", "python": sys.version.split()[0],
           "sizes": [measure(1), measure(2)]}
    a, b = out["sizes"]
    out["scaling"] = {"wall_ratio_2d_over_1d": round(b["wall_seconds"] / a["wall_seconds"], 2),
                      "state_ratio_2d_over_1d": round(b["restore_state_compressed_bytes"]
                                                      / a["restore_state_compressed_bytes"], 2)}
    per_month = b["wall_seconds"] / 2 * 30
    out["qualified_month_estimate_seconds_fold_only"] = round(per_month, 1)
    p = ROOT / "delivery" / "evidence" / "WP-009-bench-adviser.json"
    p.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
