"""Unico seguito 24h OBS-002/v1 (task §4), modulo distinto dalla popolazione e mai suo input.

Riferimento C_t e normalizzatore A_t=A45m(t) congelati all'origine. Futuro: minuti negoziati
esattamente [t, t+H). final = d*(C_end - C_t)/A; favorevole e contrario non negativi da high/low 1m
con origine 0. Riferimenti simmetrici ±A da C_t, solo descrittivi (non stop/target, nessun costo):
primo contatto favorevole F e contrario A a risoluzione 1m e una di sei classi. Nessuna fill.
"""

from __future__ import annotations

from obs001.minutes import VALID, MinuteStore

MS_MIN = 60_000
RIGHT_CENSORED, GAP, MISSING_A, ZERO_A = "RIGHT_CENSORED", "GAP", "MISSING_A", "ZERO_A"
CLASSES = ("F_ONLY", "A_ONLY", "F_BEFORE_A", "A_BEFORE_F", "BOTH_UNORDERED", "NEITHER")
FLAGS = (RIGHT_CENSORED, GAP, MISSING_A, ZERO_A)


def _contact_class(cf: dict | None, ca: dict | None) -> str:
    if cf is None and ca is None:
        return "NEITHER"
    if ca is None:
        return "F_ONLY"
    if cf is None:
        return "A_ONLY"
    if cf["minute"] != ca["minute"]:
        return "F_BEFORE_A" if cf["minute"] < ca["minute"] else "A_BEFORE_F"
    # Stesso minuto: è ordinato solo se l'apertura è già sul/oltre uno dei due riferimenti.
    if cf["atOpen"]:
        return "F_BEFORE_A"
    if ca["atOpen"]:
        return "A_BEFORE_F"
    return "BOTH_UNORDERED"


def _scan(store: MinuteStore, i0: int, i1: int, d: int, f: float | None, adv: float | None) -> dict:
    """Minuti [i0, i1) tutti validi: estremi con il loro primo minuto e primi contatti ±A."""
    st = store
    hi, lo, i_hi, i_lo = -float("inf"), float("inf"), None, None
    cf = ca = None
    for i in range(i0, i1):
        h, l = st.h[i], st.l[i]
        if h > hi:
            hi, i_hi = h, i
        if l < lo:
            lo, i_lo = l, i
        if f is None:
            continue
        o = st.o[i]
        u = st.start + i * MS_MIN
        if cf is None and (h >= f if d == 1 else l <= f):
            at_open = o >= f if d == 1 else o <= f
            cf = {"minute": u, "atOpen": at_open, "interval": [u, u] if at_open else [u, u + MS_MIN]}
        if ca is None and (l <= adv if d == 1 else h >= adv):
            at_open = o <= adv if d == 1 else o >= adv
            ca = {"minute": u, "atOpen": at_open, "interval": [u, u] if at_open else [u, u + MS_MIN]}
    if i_hi is None:
        return {"minutes": 0}
    t = lambda i: st.start + i * MS_MIN  # noqa: E731
    return {"minutes": i1 - i0, "maxHigh": hi, "maxHighFirstMinute": t(i_hi), "minLow": lo, "minLowFirstMinute": t(i_lo),
            "closeLast": st.c[i1 - 1], "lastMinute": t(i1 - 1), "contactF": cf, "contactA": ca}


def _norm(s: dict, d: int, c: float, a: float | None) -> dict:
    if not s["minutes"] or a is None:
        return {"final": None, "favourable": None, "adverse": None}
    up, down = max(0.0, s["maxHigh"] - c) / a, max(0.0, c - s["minLow"]) / a
    return {"final": d * (s["closeLast"] - c) / a, "favourable": up if d == 1 else down, "adverse": down if d == 1 else up}


def outcome(store: MinuteStore, t: int, c: float, a_measure: dict, d: int, horizon_ms: int, end: int, marker: float = 1.0) -> dict:
    t_end = t + horizon_ms
    flags = [RIGHT_CENSORED] if t_end > end else []
    a = a_measure["v"]
    if a is None:
        a_flag = MISSING_A
    elif a <= 0:
        a_flag = ZERO_A
    else:
        a_flag = None
    stop = min(t_end, end, store.end)
    i0, i1 = store.index(t), store.index(stop)
    first_bad = next((i for i in range(i0, i1) if store.status[i] != VALID), None)
    if first_bad is not None:
        flags.append(GAP)
    if a_flag:
        flags.append(a_flag)
    a_ok = None if a_flag else a
    f = adv = None
    if a_ok is not None:
        f, adv = c + d * marker * a_ok, c - d * marker * a_ok
    prefix_end = first_bad if first_bad is not None else i1
    s = _scan(store, i0, prefix_end, d, f, adv)
    out = {"t": t, "horizonEnd": t_end, "C": c, "A": a, "markers": None if f is None else {"F": f, "A": adv},
           "flags": flags, "complete": not flags,
           "coverage": {"minutesExpected": horizon_ms // MS_MIN, "minutesValidContiguous": s["minutes"],
                        "firstGapMinute": None if first_bad is None else store.start + first_bad * MS_MIN}}
    if not flags:
        out.update({"Cend": s["closeLast"], "maxHigh": s["maxHigh"], "maxHighFirstMinute": s["maxHighFirstMinute"],
                    "minLow": s["minLow"], "minLowFirstMinute": s["minLowFirstMinute"], **_norm(s, d, c, a_ok),
                    "contactF": s["contactF"], "contactA": s["contactA"], "class": _contact_class(s["contactF"], s["contactA"]),
                    "partial": None})
        return out
    out.update({"Cend": None, "maxHigh": None, "maxHighFirstMinute": None, "minLow": None, "minLowFirstMinute": None,
                "final": None, "favourable": None, "adverse": None, "contactF": None, "contactA": None, "class": None})
    # Prefisso noto fino alla prima lacuna o alla fine dei dati: parziale, mai esito completo.
    part = None
    if s["minutes"]:
        part = {"label": "PREFISSO PARZIALE: non è un esito 24h completo", "minutes": s["minutes"], "lastMinute": s["lastMinute"],
                "maxHigh": s["maxHigh"], "minLow": s["minLow"], "closeLast": s["closeLast"], **_norm(s, d, c, a_ok),
                "contactF": s["contactF"], "contactA": s["contactA"]}
    out["partial"] = part
    return out
