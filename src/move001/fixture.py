"""Piccolo pacchetto MOVE-001 SINTETICO per i test del lettore (prezzi inventati, non BTC).

Stessa catena del pacchetto reale (osservatore OBS-001/v1, ciclo, package) su dieci giorni di minuti
casuali; contrassegnato `synthetic: true`. Il caso è il primo riferimento nato dopo il terzo giorno
con almeno quattro fatti nel ledger, oppure (--final) l'ultimo riferimento, aperto a fine copertura.
Uso: python -m move001.fixture <percorso di uscita> [--final]
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
from .cycle import Cycle


def build(final: bool = False) -> dict:
    base = load_study()
    study = dataclasses.replace(base, study_start=base.input_start + 3 * DAY_MS, end=base.input_start + 10 * DAY_MS)
    conv = observation_conventions(study)
    store = MinuteStore(study.input_start, study.end)
    rng = random.Random(1001)
    price = 100.0
    for t in range(study.input_start, study.end, MINUTE_MS):
        o = price
        c = max(1.0, o + rng.uniform(-0.6, 0.6))
        store.set_minute(store.index(t), (o, max(o, c) + rng.uniform(0, 0.4), min(o, c) - rng.uniform(0, 0.4), c, rng.uniform(1, 9), 0.0, rng.randint(1, 20), 0.0, 0.0))
        price = c
    bars45, bars1d = aggregate(store, conv.bar_ms), aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    cy = Cycle(bars45, observed["45m"], observed["events"]["45m"], study.input_start, conv.bar_ms, study.end).run()
    if final:
        ref = cy.refs[-1]
        if ref.archived is not None:
            raise RuntimeError("l'ultimo riferimento della fixture non è aperto a fine copertura")
    else:
        ref = next(r for r in cy.refs if r.birth_t > study.study_start and sum(1 for e in cy.ledger if e["refId"] == r.id) >= 4)
    case = {"categories": [{"category": "SYNTHETIC_FIXTURE_FINAL" if final else "SYNTHETIC_FIXTURE", "t": ref.birth_t}]}
    run_ref = {"runId": "SYNTHETIC-MOVE001-CASE", "inputHash": None, "engineVersion": ENGINE_VERSION, "synthetic": True}
    chain = {"bars45": bars45, "bars1d": bars1d, "observed": observed}
    return package(case, ref, cy.ledger, cy.structures, chain, store, conv, study, run_ref, [])


def main() -> int:
    out = Path(sys.argv[1])
    out.write_text(json.dumps(build("--final" in sys.argv[2:]), ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"{out} {out.stat().st_size} byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
