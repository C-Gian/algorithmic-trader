"""Catena di elaborazione offline: minuti validati -> barre -> osservazioni -> esiti -> bundle."""

from __future__ import annotations

from .aggregate import Bar, aggregate
from .conventions import Conventions
from .minutes import MinuteStore
from .observe import observe
from .outcomes import build_study_rows, study_origins
from .summary import summarize

AVAILABILITY_KEYS = (
    ("vol", "tr"), ("vol", "A"), ("avg", "sma20"), ("avg", "sma50"), ("avg", "dist"), ("avg", "slope"),
    ("avg", "pos"), ("avg", "cross"), ("piv", "structure"), ("volu", "ratio"), ("fib", "anchors"),
)
LEVEL_KINDS = ("PIVOT_HIGH", "PIVOT_LOW", "DAY_HIGH", "DAY_LOW")


def availability(rec: dict | None) -> dict:
    """Disponibilità per singola misura (True oppure motivo), non un unico stato globale."""
    if rec is None:
        return {f"{a}.{b}": "INSUFFICIENT_HISTORY" for a, b in AVAILABILITY_KEYS} | {f"lvl.{k}": "INSUFFICIENT_HISTORY" for k in LEVEL_KINDS}
    out = {}
    for fam, key in AVAILABILITY_KEYS:
        m = rec[fam][key]
        out[f"{fam}.{key}"] = True if m["v"] is not None else m["r"]
    for lv in rec["lvl"]:
        out[f"lvl.{lv['kind']}"] = True if lv.get("price") is not None else lv.get("reason")
    return out


def run_chain(store: MinuteStore, conv: Conventions) -> dict:
    bars45 = aggregate(store, conv.bar_ms)
    bars1d = aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    rows = build_study_rows(store, conv, observed, bars45)
    avail = []
    for t in study_origins(conv):
        k45 = (t - conv.input_start) // conv.bar_ms - 1
        kd = (t - t % conv.day_ms - conv.input_start) // conv.day_ms - 1
        avail.append({"45m": availability(observed["45m"][k45]), "1D": availability(observed["1D"][kd] if kd >= 0 else None)})
    summary = summarize(rows, avail, conv)
    return {"bars45": bars45, "bars1d": bars1d, "observed": observed, "rows": rows, "summary": summary}


def columnar(bars: list[Bar]) -> dict:
    """Barre in colonne compatte; OHLC null per barre INCOMPLETE."""
    return {
        "open": [b.start for b in bars],
        "status": [b.status for b in bars],
        "o": [b.o for b in bars], "h": [b.h for b in bars], "l": [b.l for b in bars], "c": [b.c for b in bars],
        "v": [b.v for b in bars], "q": [b.q for b in bars], "trades": [b.trades for b in bars],
        "valid": [b.valid for b in bars], "missing": [b.missing for b in bars], "invalid": [b.invalid for b in bars],
    }
