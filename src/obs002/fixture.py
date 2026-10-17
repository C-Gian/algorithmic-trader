"""Piccolo pacchetto di caso OBS-002 SINTETICO per i test del lettore (prezzi inventati, non BTC).

Stessa catena del pacchetto reale (osservatore OBS-001/v1, popolazione, esito, package) su cinque
giorni di minuti casuali; contrassegnato `synthetic: true`. Il caso è il primo tentativo con esito
completo dopo il secondo giorno. Uso: python -m obs002.fixture <percorso di uscita>
"""

from __future__ import annotations

import dataclasses
import json
import random
import sys
from pathlib import Path

from obs001.aggregate import aggregate
from obs001.conventions import DAY_MS, MINUTE_MS
from obs001.minutes import MinuteStore
from obs001.observe import observe

from . import ENGINE_VERSION
from .config import load_study, observation_conventions
from .consult import package
from .outcomes import outcome
from .population import Population


def build() -> dict:
    base = load_study()
    study = dataclasses.replace(base, study_start=base.input_start + 2 * DAY_MS, end=base.input_start + 5 * DAY_MS)
    conv = observation_conventions(study)
    store = MinuteStore(study.input_start, study.end)
    rng = random.Random(2002)
    price = 100.0
    for t in range(study.input_start, study.end, MINUTE_MS):
        o = price
        c = max(1.0, o + rng.uniform(-0.6, 0.6))
        store.set_minute(store.index(t), (o, max(o, c) + rng.uniform(0, 0.4), min(o, c) - rng.uniform(0, 0.4), c, rng.uniform(1, 9), 0.0, rng.randint(1, 20), 0.0, 0.0))
        price = c
    bars45, bars1d = aggregate(store, conv.bar_ms), aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    pop = Population(bars45, observed["45m"], observed["1D"], observed["events"]["45m"], study.input_start, conv.bar_ms, conv.day_ms,
                     study.study_start, study.end).run()
    for a in pop.attempts:
        if not a["inStudy"]:
            continue
        o = outcome(store, a["t"], a["C"], a["snapshot"]["volatility"]["A"], a["d"], study.horizon_ms, study.end, study.marker_a)
        if o["complete"]:
            break
    else:
        raise RuntimeError("nessun tentativo completo nella fixture")
    chain = {"bars45": bars45, "bars1d": bars1d, "observed": observed}
    case = {"categories": ["SYNTHETIC_FIXTURE"]}
    run_ref = {"runId": "SYNTHETIC-OBS002-CASE", "inputHash": None, "engineVersion": ENGINE_VERSION, "synthetic": True}
    files = []
    return package(case, a, o, chain, store, conv, study, run_ref, files)


def main() -> int:
    out = Path(sys.argv[1])
    out.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"{out} {out.stat().st_size} byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
