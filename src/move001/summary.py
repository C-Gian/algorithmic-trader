"""Conteggi e durate MOVE-001/v1 (contratto §12.2), schema fissato prima dei dati.

Un evento appartiene al periodo della barra la cui chiusura lo rende disponibile (barra aperta a
t - 45m). Stock = riferimento principale presente dopo l'ultima chiusura prima del periodo e
dopo l'ultima del periodo. Ogni partizione è riconciliata; una discrepanza è un errore.
"""

from __future__ import annotations

from datetime import UTC, datetime

from obs001.summary import quantile

from .cycle import (ABSENT, ADOPTED, C_FORMATION, C_SUSP_NO_P1, C_SUSP_P1, C_USABLE, CONDITIONS, LOST, OPPOSITE, OPPOSITE_AT_BIRTH,
                    OUTCOMES, REACHED, REPLACED, INTERRUPTED, SIDE, TEST)

SIDES = tuple(SIDE.values())


def month_of(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m")


def stats(values: list[float]) -> dict:
    s = sorted(values)
    return {"n": len(s), "min": s[0] if s else None, "p50": quantile(s, 0.5), "p90": quantile(s, 0.9), "max": s[-1] if s else None}


def _by(items, key) -> dict:
    out: dict = {}
    for x in items:
        k = key(x)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def period_table(cy, lo: int, hi: int, bar_ms: int) -> dict:
    """Barre aperte in [lo, hi): chiusure in (lo, hi]."""
    inside = lambda t: lo < t <= hi  # noqa: E731
    closes = [c for c in cy.closes if inside(c["t"])]
    complete = [c for c in closes if c["complete"]]
    ev = [e for e in cy.ledger if inside(e["t"])]
    st = [s for s in cy.structures if inside(s["t"])]
    before = [c for c in cy.closes if c["t"] <= lo]
    stock_start = 1 if before and before[-1]["refId"] else 0
    stock_end = 1 if closes and closes[-1]["refId"] else stock_start if not closes else 0
    births = [e for e in ev if e["type"] == "BIRTH"]
    archives = [e for e in ev if e["type"] == "ARCHIVE"]
    susp = [e for e in ev if e["type"] == "SUSPENSION"]
    facts = [e for e in ev if e["type"] == "FACT"]
    p1 = [e for e in ev if e["type"] == "P1_PUBLISHED"]
    side_split = lambda rows: {s: sum(1 for r in rows if r["side"] == s) for s in SIDES}  # noqa: E731
    out = {
        "closes": {"expected": int((hi - lo) // bar_ms), "observed": len(closes), "complete": len(complete), "incomplete": len(closes) - len(complete),
                   "byCondition": {c: sum(1 for x in complete if x["condition"] == c) for c in CONDITIONS},
                   "byConditionAndSide": {c: side_split([x for x in complete if x["condition"] == c]) for c in CONDITIONS if c != ABSENT}},
        "structures": {"qualified": len(st), "byOutcome": {o: sum(1 for s in st if s["outcome"] == o) for o in OUTCOMES},
                       "byOutcomeAndCandidateSide": {o: side_split([s for s in st if s["outcome"] == o]) for o in OUTCOMES},
                       "rejectedByOccupant": _by([s for s in st if s["outcome"] != ADOPTED and s["occupant"]],
                                                 lambda s: f"{s['outcome']}|occupante {s['occupant']['side']} {s['occupant']['condition']}"),
                       "freshnessWithFreeSlot": sum(1 for s in st if s["outcome"] != ADOPTED and not s["occupant"])},
        "births": {"total": len(births), **side_split(births), "withPredecessor": sum(1 for e in births if e["predecessor"])},
        "p1Available": {"total": len(p1), "duringFormation": sum(1 for e in p1 if not e["whileSuspended"]),
                        "whileSuspended": sum(1 for e in p1 if e["whileSuspended"]), **side_split(p1)},
        "firstUsable": {"total": sum(1 for e in ev if e["type"] == "USABLE"), **side_split([e for e in ev if e["type"] == "USABLE"])},
        "initialSuspensions": {r: side_split([e for e in susp if e["reason"] == r]) | {"total": sum(1 for e in susp if e["reason"] == r)}
                               for r in (TEST, OPPOSITE, OPPOSITE_AT_BIRTH)},
        "initialSuspensionsWithoutP1": sum(1 for e in susp if e["condition"] == C_SUSP_NO_P1),
        "furtherFacts": _by(facts, lambda e: e["fact"]),
        "furtherFactsWithFlags": sum(1 for e in facts if e.get("flags")),
        "archives": {r: side_split([e for e in archives if e["reason"] == r]) | {"total": sum(1 for e in archives if e["reason"] == r)}
                     for r in (LOST, REACHED, REPLACED, INTERRUPTED)},
        "lossesByConditionBefore": _by([e for e in archives if e["reason"] == LOST], lambda e: e["conditionBefore"]),
        "lossesWithP1SameBar": sum(1 for e in archives if e["reason"] == LOST and e.get("flags")),
        "suspensionsDoubleTest": sum(1 for e in susp if e.get("flags")),
        "openAtEnd": _by([e for e in ev if e["type"] == "OPEN_AT_END"], lambda e: f"{e['side']} {e['condition']} {e['judgement']}/{e['judgementReason']}"),
        "stock": {"start": stock_start, "births": len(births), "archives": len(archives), "end": stock_end},
    }
    problems = []
    s = out["stock"]
    if s["start"] + s["births"] - s["archives"] != s["end"]:
        problems.append("stock")
    if sum(out["closes"]["byCondition"].values()) != out["closes"]["complete"]:
        problems.append("condizioni di occupazione")
    if sum(out["structures"]["byOutcome"].values()) != out["structures"]["qualified"]:
        problems.append("strutture")
    if out["births"]["total"] != out["structures"]["byOutcome"][ADOPTED]:
        problems.append("nascite != adottate")
    if problems:
        raise AssertionError(f"riconciliazione fallita [{lo},{hi}): {problems}")
    return out


def durations(cy, refs, bar_ms: int) -> dict:
    """Per riferimento: nascita->P1, nascita->UTILIZZABILE, nascita->archiviazione, permanenza per condizione.
    Disponibili, censurate (aperte a fine copertura) e non raggiunte (archiviate prima) separate."""
    h = bar_ms / 3_600_000
    out = {}

    def item(name, pairs):
        avail = [v for v, kind in pairs if kind == "AVAILABLE"]
        cens = [v for v, kind in pairs if kind == "CENSORED"]
        out[name] = {"available": stats(avail), "availableHours": stats([v * h for v in avail]), "censored": stats(cens),
                     "censoredCount": len(cens), "notReached": sum(1 for _, kind in pairs if kind == "NOT_REACHED")}

    def to(ref, t):
        if t is not None:
            return (t - ref.birth_t) / bar_ms, "AVAILABLE"
        if ref.archived is None:
            return (cy.end - ref.birth_t) / bar_ms, "CENSORED"
        return None, "NOT_REACHED"

    item("birthToP1", [to(r, r.p1_t) for r in refs])
    item("birthToUsable", [to(r, r.usable_t) for r in refs])
    item("birthToArchiveOrEnd", [((r.archived["t"] - r.birth_t) / bar_ms, "AVAILABLE") if r.archived else ((cy.end - r.birth_t) / bar_ms, "CENSORED")
                                 for r in refs])
    for cond in (C_FORMATION, C_SUSP_P1, C_SUSP_NO_P1, C_USABLE):
        rows = [r for r in refs if r.closes[cond] > 0]
        item(f"permanence_{cond}", [(r.closes[cond], "AVAILABLE" if r.archived else "CENSORED") for r in rows])
    return out


def summarize(cy, study_start: int, end: int, bar_ms: int) -> dict:
    from obs001.conventions import parse_utc

    periods = {"DEV": (study_start, end), "2023": (study_start, parse_utc("2024-01-01T00:00:00Z")), "2024": (parse_utc("2024-01-01T00:00:00Z"), end),
               "PREFIX": (cy.input_start, study_start)}
    tables = {name: period_table(cy, lo, hi, bar_ms) for name, (lo, hi) in periods.items()}
    months = {}
    t = study_start
    while t < end:
        dt = datetime.fromtimestamp(t / 1000, UTC)
        nxt = int(dt.replace(year=dt.year + 1, month=1).timestamp() * 1000) if dt.month == 12 else int(dt.replace(month=dt.month + 1).timestamp() * 1000)
        months[month_of(t)] = period_table(cy, t, min(nxt, end), bar_ms)
        t = nxt
    dev_refs = [r for r in cy.refs if study_start < r.birth_t <= end]
    prefix_refs = [r for r in cy.refs if r.birth_t <= study_start]
    tri = [x for x in cy.triples if study_start < x["availableAt"] <= end]
    longest = sorted(dev_refs, key=lambda r: (-(((r.archived["t"] if r.archived else end) - r.birth_t)), r.id))[:5]
    out = {
        "tables": tables, "months": months,
        "durationsDev": durations(cy, dev_refs, bar_ms),
        "durationsBySide": {s: durations(cy, [r for r in dev_refs if r.side == s], bar_ms) for s in SIDES},
        "prefixReferences": [{"refId": r.id, "birthAt": r.birth_t, "archive": r.archived, "condition": None if r.archived else r.condition()} for r in prefix_refs],
        "triplesNotQualified": {"label": "triple correnti con availableAt in DEV, per esito; non sono strutture bloccate dal posto",
                                "byResult": _by(tri, lambda x: x["result"]), "byResultAndSide": _by(tri, lambda x: f"{x['result']}|{x['side']}")},
        "concentration": {"monthsByBirths": sorted(((m, v["births"]["total"]) for m, v in months.items()), key=lambda x: (-x[1], x[0]))[:5],
                          "longestOccupations": [{"refId": r.id, "bars": ((r.archived["t"] if r.archived else end) - r.birth_t) / bar_ms,
                                                  "archive": r.archived["reason"] if r.archived else "FINE_COPERTURA"} for r in longest]},
    }
    # mesi: somma delle nascite/archiviazioni = DEV; stock concatenato
    dev = tables["DEV"]
    if sum(m["births"]["total"] for m in months.values()) != dev["births"]["total"] or \
            sum(m["stock"]["archives"] for m in months.values()) != dev["stock"]["archives"]:
        raise AssertionError("mesi non sommano al DEV")
    prev = dev["stock"]["start"]
    for m, v in months.items():
        if v["stock"]["start"] != prev:
            raise AssertionError(f"stock non concatenato al mese {m}")
        prev = v["stock"]["end"]
    out["checks"] = {"reconciled": True, "devReferences": len(dev_refs), "prefixReferences": len(prefix_refs)}
    return out
