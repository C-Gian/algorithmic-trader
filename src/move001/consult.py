"""Pacchetti di consultazione MOVE-001 (contratto §12.3) letti dallo Studio storico esistente.

Un file per riferimento: barre, osservazioni ed eventi OBS-001/v1 calcolati sull'intero prefisso e
poi ritagliati; origini dalle quattro chiusure prima della nascita fino a otto dopo l'ultimo fatto
del riferimento, al più fino alla fine copertura inclusa; ledger del riferimento con l'istante di ogni
fatto, così il lettore mostra solo ciò che era noto al momento scelto. Nessun esito 24h, nessuna riga di seguito, nessun riepilogo
OBS-001: kind MOVE001_CASE, non un caso OBS-002 né un risultato CAND.
"""

from __future__ import annotations

from obs001.observe import floor_day
from obs001.pipeline import columnar

from . import CASE_SCHEMA, ENGINE_VERSION

DAY = 86_400_000
DAYS_BEFORE = 35
BEFORE, AFTER = 4, 8
# Versione tecnica del solo generatore di consultazione (ciclo e semantica 1.0.1 invariati):
# /1 = consegna 1235e64 (ultima origine end - 45m); /2 = R1-B, ultima chiusura disponibile selezionabile.
CONSULT_VERSION = "move001.consult/2"
LABEL = "Rappresentazione sperimentale del movimento — nessuna decisione operativa"


def package(case: dict, ref, ledger: list[dict], structures: list[dict], chain: dict, store, conv, study, run_ref: dict, files: list[dict]) -> dict:
    bar = conv.bar_ms
    events = [e for e in ledger if e["refId"] == ref.id]
    last = max(e["t"] for e in events)
    o_lo = max(study.input_start + bar, ref.birth_t - BEFORE * bar)
    # R1-B: l'ultima origine può essere la fine copertura, chiusura dell'ultima barra disponibile; i minuti
    # del pacchetto restano [inputStart, end) e nessun dato successivo viene letto.
    o_hi = min(last + AFTER * bar, study.end)
    origins = list(range(o_lo, o_hi + 1, bar))
    start = max(study.input_start, floor_day(o_lo) - DAYS_BEFORE * DAY)
    end = min(study.end, floor_day(o_hi) + DAY)
    k_lo, k_hi = (start - study.input_start) // bar, (end - study.input_start) // bar
    d_lo, d_hi = (start - study.input_start) // DAY, (end - study.input_start) // DAY
    rec45, rec1d = chain["observed"]["45m"], chain["observed"]["1D"]
    months = sorted({x["month"] for x in files if _overlaps(x["month"], start, end)})
    rejected = [s for s in structures if s["occupant"] and s["occupant"]["refId"] == ref.id]
    return {
        "kind": "MOVE001_CASE", "schema": CASE_SCHEMA, "engineVersion": ENGINE_VERSION, "consultVersion": CONSULT_VERSION,
        "study": {"id": study.raw["id"], "version": study.raw["version"], "hash": study.hash, "label": LABEL},
        "conventions": {"id": conv.raw["id"], "hash": conv.hash, "config": conv.raw},
        "timeUnit": "ms epoch UTC",
        "source": {"name": "Binance Vision", "attribution": "Fonte: Binance Vision", "symbol": "BTCUSDT", "segment": "USDS-M futures (um)",
                   "contractType": "PERPETUAL", "priceType": "TRADE_KLINES", "interval": "1m",
                   "termsUrl": "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md",
                   "note": "Dati per uso personale di ricerca non produttiva; non redistribuire il pacchetto."},
        "periods": {"inputStart": start, "studyStart": origins[0], "end": end},
        "run": run_ref,
        "inputQuality": {"totals": {"input": store.counts(start, end), "initialization": store.counts(start, origins[0]),
                                    "study": store.counts(origins[0], end)},
                         "files": [{k: f[k] for k in ("month", "file", "sha256", "rows", "coverage")} for f in files if f["month"] in months]},
        "bars": {"45m": columnar(chain["bars45"][k_lo:k_hi]), "1D": columnar(chain["bars1d"][d_lo:d_hi])},
        "observations": {"45m": rec45[k_lo:k_hi], "1D": rec1d[d_lo:d_hi]},
        "events": {s: [e for e in chain["observed"]["events"][s] if start <= e["availableAt"] < end] for s in ("45m", "1D")},
        "origins": origins,
        "case": {"refId": ref.id, "side": ref.side, "categories": case["categories"], "birthAt": ref.birth_t, "segment": ref.segment,
                 "Q": ref.Q, "B": ref.B, "P0": ref.P0, "predecessor": ref.predecessor, "label": LABEL,
                 "ledger": events, "rejectedStructures": rejected,
                 "note": "Ogni fatto porta l'istante in cui diventa noto: al momento scelto si mostrano solo i fatti con istante <= momento."},
        "retrospective": {"label": "Nessun seguito: MOVE-001 non calcola esiti 24h", "rows": [], "summary": None,
                          "summaryNote": "I conteggi di MOVE-001 sono nel report docs/research/MOVE-001-results.md; nessuna tabulazione OBS-001 o esito 24h in questo pacchetto."},
    }


def _overlaps(month: str, start: int, end: int) -> bool:
    from obs001.inputs import month_bounds

    lo, hi = month_bounds(month)
    return lo < end and hi > start
