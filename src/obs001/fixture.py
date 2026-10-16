"""Piccolo bundle SINTETICO per i test della dashboard (prezzi inventati, non BTC).

Usa lo stesso motore e lo stesso schema del bundle reale, con periodi ridotti a quattro giorni
(inizializzazione 2 giorni, studio 2 giorni). Contrassegnato `synthetic: true`.
Uso: python -m obs001.fixture <percorso di uscita>
"""

from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

from . import ENGINE_VERSION
from .bundle import build_bundle
from .conventions import DAY_MS, MINUTE_MS, Conventions, canonical_json, iso, load_conventions, sha256_bytes
from .minutes import MISSING, MinuteStore
from .pipeline import run_chain


def synthetic_conventions() -> Conventions:
    base = load_conventions()
    raw = copy.deepcopy(base.raw)
    start = base.input_start
    raw["periods"] = {"inputStart": iso(start), "studyStart": iso(start + 2 * DAY_MS), "end": iso(start + 4 * DAY_MS)}
    raw["study"]["months"] = ["2025-06"]
    raw["study"]["theoreticalOrigins"] = 64
    raw["study"]["theoreticalRightCensored"] = 31
    raw["description"] = "Fixture sintetica di test: NON sono le convenzioni registrate."
    return Conventions(raw=raw, hash=sha256_bytes(canonical_json(raw)), input_start=start, study_start=start + 2 * DAY_MS,
                       end=start + 4 * DAY_MS, bar_ms=base.bar_ms, day_ms=base.day_ms)


def build() -> dict:
    conv = synthetic_conventions()
    store = MinuteStore(conv.input_start, conv.end)
    rng = random.Random(2025)
    price = 100.0
    for t in range(conv.input_start, conv.end, MINUTE_MS):
        o = price
        c = max(1.0, o + rng.uniform(-0.6, 0.6))
        store.set_minute(store.index(t), (o, max(o, c) + rng.uniform(0, 0.4), min(o, c) - rng.uniform(0, 0.4), c, rng.uniform(1, 9), 0.0, rng.randint(1, 20), 0.0, 0.0))
        price = c
    # Una lacuna di un minuto il secondo giorno: una barra 45m INCOMPLETE e il giorno 2 incompleto.
    store.status[store.index(conv.input_start + DAY_MS + 10 * 45 * MINUTE_MS + 7 * MINUTE_MS)] = MISSING
    chain = run_chain(store, conv)
    counts = {"input": store.counts(), "initialization": store.counts(conv.input_start, conv.study_start), "study": store.counts(conv.study_start, conv.end)}
    manifest = {"totals": counts, "files": [], "instrumentMetadata": {"instrument": None}}
    run_ref = {"runId": "SYNTHETIC-FIXTURE", "inputHash": None, "engineVersion": ENGINE_VERSION, "synthetic": True}
    return build_bundle(conv, chain, manifest, run_ref)


def main() -> int:
    out = Path(sys.argv[1])
    out.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"{out} {out.stat().st_size} byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
