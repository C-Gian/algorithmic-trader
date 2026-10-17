"""Pacchetti di consultazione OBS-002 per i casi selezionati (task §6), letti dallo Studio storico.

Un pacchetto per caso, piccolo: barre, osservazioni ed eventi OBS-001/v1 calcolati sull'intero
prefisso dal 2022-10-01 e poi ritagliati (nessun ricalcolo sulla sola finestra), le origini 45m
attorno al caso e, nella sezione a posteriori, il seguito 24h esistente (righe OBS-001 per
origine) più l'esito OBS-002 del solo caso. Identità OBS-002, non un bundle OBS-001 originale né
un backtest CAND: il riepilogo OBS-001 non è pertinente e non viene prodotto (summary null).
"""

from __future__ import annotations

from obs001.aggregate import Bar
from obs001.minutes import MinuteStore
from obs001.observe import floor_day
from obs001.outcomes import daily_relation, outcome_for, structure_state
from obs001.pipeline import columnar

from . import CASE_SCHEMA, ENGINE_VERSION

DAY = 86_400_000
DAYS_BEFORE = 35
ORIGINS_AROUND = 16  # chiusure 45m prima e dopo il caso selezionabili nel lettore


def _slice_bars(bars: list[Bar], lo: int, hi: int) -> dict:
    return columnar(bars[lo:hi])


def package(case: dict, attempt: dict, outcome: dict, chain: dict, store: MinuteStore, conv, study, run_ref: dict, files: list[dict]) -> dict:
    t = attempt["t"]
    bar = conv.bar_ms
    start = max(study.input_start, floor_day(t) - DAYS_BEFORE * DAY)
    end = min(study.end, floor_day(t) + 2 * DAY)
    o_lo = max(start + bar, t - ORIGINS_AROUND * bar, study.study_start)
    o_hi = min(t + ORIGINS_AROUND * bar, end - bar)
    origins = list(range(o_lo, o_hi + 1, bar))
    k_lo, k_hi = (start - study.input_start) // bar, (end - study.input_start) // bar
    d_lo, d_hi = (start - study.input_start) // DAY, (end - study.input_start) // DAY
    rec45, rec1d = chain["observed"]["45m"], chain["observed"]["1D"]
    rows = []
    for o in origins:
        k = (o - study.input_start) // bar - 1
        kd = (floor_day(o) - study.input_start) // DAY - 1
        r45, r1d = rec45[k], rec1d[kd] if kd >= 0 else None
        a_m = r45["vol"]["A"]
        row = outcome_for(store, conv, o, r45["C"], a_m["v"], a_m["r"])
        s45, s1d = structure_state(r45), structure_state(r1d)
        row.update({"month": _month(o), "s45": s45, "s1d": s1d, "dailyRelation": daily_relation(s45, s1d),
                    "s45Reason": r45["piv"]["structure"]["r"], "s1dReason": r1d["piv"]["structure"]["r"] if r1d else "INSUFFICIENT_HISTORY"})
        rows.append(row)
    events = {s: [e for e in chain["observed"]["events"][s] if start <= e["availableAt"] < end] for s in ("45m", "1D")}
    causal = {k: v for k, v in attempt.items()}
    months = sorted({_month(x) for x in range(start, end, DAY)})
    return {
        "kind": "OBS002_CASE", "schema": CASE_SCHEMA, "engineVersion": ENGINE_VERSION,
        "study": {"id": study.raw["id"], "hash": study.hash, "label": "OBS-002 · pacchetto di consultazione di un caso (non OBS-001, non backtest)"},
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
        "bars": {"45m": _slice_bars(chain["bars45"], k_lo, k_hi), "1D": _slice_bars(chain["bars1d"], d_lo, d_hi)},
        "observations": {"45m": rec45[k_lo:k_hi], "1D": rec1d[d_lo:d_hi]},
        "events": events,
        "origins": origins,
        "case": {"attemptId": attempt["attemptId"], "t": t, "side": attempt["side"], "categories": case["categories"],
                 "profile": attempt["snapshot"]["profile"]["profile"], "ordinal": attempt["ordinal"], "causal": causal,
                 "note": "Informazioni note alla chiusura t; nessuna call, ordine o operazione."},
        "retrospective": {
            "label": "A POSTERIORI — seguito retrospettivo, non disponibile al momento dell'origine",
            "rows": rows, "summary": None,
            "summaryNote": "Il riepilogo di OBS-002 è nel report docs/research/OBS-002-results.md; la tabulazione OBS-001 non è pertinente a questo pacchetto.",
            "obs002": {"attemptId": attempt["attemptId"], "outcome": outcome},
        },
    }


def _month(t: int) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m")
