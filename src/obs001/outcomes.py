"""Esiti retrospettivi a 24h, modulo distinto dall'osservatore e mai suo input.

Per ogni origine t della griglia di studio: p=C_t e a=A45m_t congelati all'origine; minuti
futuri [t, t+24h). final=(C_(t+24h)-p)/a, up=max(0,maxH-p)/a, down=max(0,p-minL)/a.
up/down sono ampiezze non negative, non profitti o perdite. Nessun prezzo portato avanti.
"""

from __future__ import annotations

from .conventions import MINUTE_MS, Conventions
from .minutes import VALID, MinuteStore
from .observe import floor_day

ORIGIN_INCOMPLETE = "ORIGIN_INCOMPLETE"
A_UNAVAILABLE = "A_UNAVAILABLE"
A_NOT_POSITIVE = "A_NOT_POSITIVE"
RIGHT_CENSORED = "RIGHT_CENSORED"
GAP = "GAP"


def study_origins(conv: Conventions) -> list[int]:
    step = conv.section("study")["originStepMinutes"] * MINUTE_MS
    return list(range(conv.study_start, conv.end, step))


def daily_relation(s45: str, s1d: str) -> str:
    if s45 not in ("UP", "DOWN"):
        return "NOT_APPLICABLE"
    if s1d in ("UP", "DOWN"):
        return "CONCORDANT" if s1d == s45 else "OPPOSITE"
    return "MIXED" if s1d == "MIXED" else "UNAVAILABLE"


def structure_state(rec: dict | None) -> str:
    if rec is None or rec["piv"]["structure"]["v"] is None:
        return "UNAVAILABLE"
    return rec["piv"]["structure"]["v"]


def outcome_for(store: MinuteStore, conv: Conventions, t: int, p: float | None, a: float | None, a_reason: str | None) -> dict:
    horizon = conv.section("study")["horizonMinutes"] * MINUTE_MS
    t_end = t + horizon
    right_censored = t_end > conv.end
    avail_end = min(t_end, conv.end, store.end)
    i0, i1 = store.index(t), store.index(avail_end)
    seg = store.status[i0:i1]
    valid = seg.count(VALID)
    gap = valid != len(seg)
    # Durata disponibile contigua da t: minuti validi consecutivi a partire dall'origine.
    contiguous = len(seg)
    for k, s in enumerate(seg):
        if s != VALID:
            contiguous = k
            break
    flags = ([RIGHT_CENSORED] if right_censored else []) + ([GAP] if gap else [])
    future_complete = not flags
    origin_status = "VALID" if p is not None else ORIGIN_INCOMPLETE
    if a is None:
        a_status = a_reason or A_UNAVAILABLE
    elif a <= 0:
        a_status = A_NOT_POSITIVE
    else:
        a_status = "VALID"
    out = {
        "t": t, "horizonEnd": t_end, "p": p, "a": a,
        "originStatus": origin_status, "aStatus": a_status, "futureStatus": "COMPLETE" if future_complete else "INCOMPLETE",
        "futureFlags": flags, "futureMinutesExpected": horizon // MINUTE_MS, "futureMinutesInRange": len(seg),
        "futureMinutesValid": valid, "futureMinutesContiguous": contiguous,
        "close24h": None, "maxHigh": None, "minLow": None, "final": None, "up": None, "down": None,
    }
    if future_complete:
        out["close24h"] = store.c[i1 - 1]
        out["maxHigh"] = max(store.h[i0:i1])
        out["minLow"] = min(store.l[i0:i1])
    if future_complete and p is not None and a_status == "VALID":
        out["final"] = (out["close24h"] - p) / a
        out["up"] = max(0.0, out["maxHigh"] - p) / a
        out["down"] = max(0.0, p - out["minLow"]) / a
    return out


def build_study_rows(store: MinuteStore, conv: Conventions, observed: dict, bars45) -> list[dict]:
    """Una riga per ciascuna delle origini teoriche, nessuna eliminata."""
    rows = []
    bars_by_end = {b.end: b for b in bars45}
    for t in study_origins(conv):
        k45 = (t - conv.input_start) // conv.bar_ms - 1
        kd = (floor_day(t) - conv.input_start) // conv.day_ms - 1
        rec45 = observed["45m"][k45]
        rec1d = observed["1D"][kd] if kd >= 0 else None
        s45, s1d = structure_state(rec45), structure_state(rec1d)
        a_m = rec45["vol"]["A"]
        o = outcome_for(store, conv, t, rec45["C"], a_m["v"], a_m["r"])
        if o["futureStatus"] == "COMPLETE":
            # Controllo incrociato: massimi/minimi delle 32 barre 45m complete coincidono coi minuti.
            future = [bars_by_end[t + (j + 1) * conv.bar_ms] for j in range(conv.section("study")["horizonBars45m"])]
            if max(b.h for b in future) != o["maxHigh"] or min(b.l for b in future) != o["minLow"]:
                raise AssertionError(f"incoerenza minuti/45m all'origine {t}")
            if future[-1].c != o["close24h"]:
                raise AssertionError(f"chiusura 24h incoerente all'origine {t}")
        o.update({
            "month": _month(t), "s45": s45, "s1d": s1d, "dailyRelation": daily_relation(s45, s1d),
            "s45Reason": rec45["piv"]["structure"]["r"], "s1dReason": rec1d["piv"]["structure"]["r"] if rec1d else "INSUFFICIENT_HISTORY",
        })
        rows.append(o)
    return rows


def _month(t: int) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m")
