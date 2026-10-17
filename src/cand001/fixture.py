"""Piccolo bundle CAND-001 SINTETICO per i test della dashboard (prezzi inventati, non BTC).

Stesso motore, stesso schema del bundle reale; minuti a tratti di tendenza deterministici, nessun
funding (cashflow zero perché non esistono eventi, non per riempimento). Contrassegnato synthetic.
Uso: python -m cand001.fixture <percorso di uscita>
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from obs001.minutes import MinuteStore

from . import ENGINE_VERSION
from .backtest import run_window
from .bundle import build_bundle
from .config import load_candidate
from .metrics import summarize

MIN, DAY = 60_000, 86_400_000
T0 = 1_672_531_200_000  # 2023-01-01T00:00Z


def synthetic_store(start: int, end: int, seed: int) -> MinuteStore:
    rng = random.Random(seed)
    st = MinuteStore(start, end)
    price, drift, left = 100.0, 0.0, 0
    for t in range(start, end, MIN):
        if left <= 0:
            drift = rng.choice([-1, 1]) * rng.uniform(0.002, 0.012)
            left = rng.randint(200, 1500)
        left -= 1
        o = price
        c = max(1.0, o + drift + rng.gauss(0, 0.05))
        h = max(o, c) + abs(rng.gauss(0, 0.03))
        l = min(o, c) - abs(rng.gauss(0, 0.03))
        st.set_minute(st.index(t), (o, h, l, c, rng.uniform(1, 5), 0.0, 3, 0.0, 0.0))
        price = c
    return st


def build(seed: int = 7) -> dict:
    cand = load_candidate()
    start, end = T0 - 10 * DAY, T0 + 20 * DAY
    store = synthetic_store(start, end, seed)
    res = run_window(cand, store, (T0, end), [], {})
    summary = summarize(res, cand, "DEV")
    quality = {"trade": {"months": [], "totals": store.counts(), "initialization": store.counts(start, T0)},
               "funding": {"files": [], "series": {"events": 0, "anomalies": [], "certified": True}},
               "mark": {"files": [], "pointsNeeded": 0, "pointsAvailable": 0, "missingForTau": []}, "identity": {"ok": False, "reason": "fixture"}}
    run_ref = {"runId": "SYNTHETIC-CAND-FIXTURE", "inputHash": None, "engineVersion": ENGINE_VERSION,
               "candidateVersion": cand.raw["candidateVersion"], "configHash": cand.hash, "synthetic": True}
    return build_bundle(cand, res, summary, quality, run_ref, "DEV")


def main() -> int:
    out = Path(sys.argv[1])
    out.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"{out} {out.stat().st_size} byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
