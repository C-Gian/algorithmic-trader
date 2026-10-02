"""Deterministic synthetic OKX rows for bounded engineering fixtures (derived, NOT market data).

Served through the same offline ``FakeOkx`` transport and accepted acquisition path, so the resulting
datasets are ordinary verified ``marketdata.v1`` packages. Prices are a deterministic saw-tooth; they are
used only to exercise structure (sizes, gaps, partitions, checkpoints, memory), never as market evidence.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from okx_fake import FakeOkx

from algotrader.marketdata.contracts import Family

MIN = timedelta(minutes=1)


def synthetic_fake(start: datetime, end: datetime, gap_every: int | None = 97,
                   gaps: tuple[tuple[datetime, datetime], ...] = ()) -> FakeOkx:
    fake = FakeOkx()
    trade, mark, index, funding = [], [], [], []
    t, i = start, 0
    while t < end:
        ms = int(t.timestamp() * 1000)
        in_gap = any(a <= t < b for a, b in gaps)
        if not in_gap and not (gap_every and i % gap_every == gap_every - 1):  # periodic missing slots
            p = 80000 + (i * 37 % 1000) / 10
            o, h, lo, c = p, p + 5, p - 5, p + 1
            trade.append([str(ms), f"{o:.1f}", f"{h:.1f}", f"{lo:.1f}", f"{c:.1f}", "100", "1", "80000.5", "1"])
            mark.append([str(ms), f"{o:.1f}", f"{h:.1f}", f"{lo:.1f}", f"{c:.1f}", "1"])
            index.append([str(ms), f"{o + 40:.1f}", f"{h + 40:.1f}", f"{lo + 40:.1f}", f"{c + 40:.1f}", "1"])
        if ms % (8 * 3600 * 1000) == 0:
            funding.append({"formulaType": "withRate", "fundingRate": "0.0001", "fundingTime": str(ms),
                            "instId": "BTC-USDT-SWAP", "instType": "SWAP", "method": "current_period",
                            "realizedRate": "0.0001"})
        t += MIN
        i += 1
    fake.rows = {Family.TRADE_CANDLES: trade, Family.MARK_CANDLES: mark, Family.INDEX_CANDLES: index,
                 Family.FUNDING: funding}
    return fake


def shuffle_parquet(dataset_dir: Path, artifact: str = "trade_candles_1m.parquet", seed: int = 3) -> None:
    """Rewrite one normalized table with shuffled row order and update its manifest hash/size consistently.

    The raw pages (hence the dataset id) are unchanged, so the package still verifies; only the row order of
    the normalized artifact differs (an unsorted-Parquet engineering fixture)."""
    import hashlib

    import pyarrow.parquet as pq

    p = dataset_dir / artifact
    table = pq.read_table(p)
    idx = list(range(table.num_rows))
    random.Random(seed).shuffle(idx)
    pq.write_table(table.take(idx), p)
    m = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    data = p.read_bytes()
    for f in m["files"]:
        if f["name"] == artifact:
            f["sha256"], f["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
    (dataset_dir / "manifest.json").write_text(json.dumps(m, indent=2), encoding="utf-8")


def measure_cold_build(args: dict) -> dict:
    """Subprocess entry (spawn): one cold preparation of a dataset/recording; peak RSS + Python heap + counters.

    Runs without a database: receipts are kept in memory for the measurement only.
    """
    import tracemalloc

    from algotrader import ops
    from algotrader.observe import feedcache as fc
    from algotrader.observe.sources import prepare_stream_source

    for k, v in args.get("limits", {}).items():
        setattr(fc, k, v)

    class MemReceipts:
        def __init__(self):
            self.rows = {}

        def get(self, cid):
            return self.rows.get(cid)

        def put(self, cache, key, kind, sid, sha, durability, verification, created_by):
            from datetime import UTC
            from datetime import datetime as dt

            self.rows.setdefault(cache.cache_id, {"cache_manifest_sha256": cache.manifest_sha256,
                                                  "created_at": dt.now(UTC)})
            return self.rows[cache.cache_id]

    counters: dict = {}
    if args.get("trace", True):
        tracemalloc.start()
    p = prepare_stream_source(Path(args["root"]), args["kind"], args["source_id"], receipts=MemReceipts(),
                              counters=counters)
    heap = tracemalloc.get_traced_memory()[1] if args.get("trace", True) else None
    tracemalloc.stop()
    pm = ops.process_metrics()
    return {"events": p.cache.event_count, "content_identity": p.cache.feed_manifest.content_identity,
            "ordered_event_hash": p.cache.feed_manifest.ordered_event_hash, "heap_peak": heap,
            "rss_peak": pm.get("max_rss_bytes"), "rss_source": pm.get("max_rss_source") or pm.get(
                "max_rss_unknown_reason"), "sort": counters.get("sort"),
            "bridge_first_completions": counters.get("bridge_first_completions"),
            "exclusions": p.cache.manifest["source_facts"].get("exclusions_count"),
            "partitions": len(p.cache.partitions)}
