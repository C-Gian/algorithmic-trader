"""Riepiloghi descrittivi congelati di OBS-001/v1 (sezione 6 del task).

Pesi uguali per origine, totale pooled (non media delle medie mensili), quantili lineari con
h=(n-1)q. Nessuna soglia di successo, significatività, intervallo o classifica dei gruppi.
"""

from __future__ import annotations

import math

MEASURES = ("final", "up", "down")
S_STATES = ("UP", "DOWN", "MIXED", "UNAVAILABLE")
RELATIONS = ("CONCORDANT", "OPPOSITE", "MIXED", "UNAVAILABLE")
TOTAL = "TOTAL"


def quantile(sorted_values: list[float], q: float) -> float | None:
    n = len(sorted_values)
    if n == 0:
        return None
    h = (n - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, n - 1)
    return sorted_values[lo] + (h - lo) * (sorted_values[hi] - sorted_values[lo])


def describe(values: list[float], quantiles: list[float]) -> dict:
    s = sorted(values)
    out = {"n": len(s), "mean": math.fsum(s) / len(s) if s else None, "min": s[0] if s else None, "max": s[-1] if s else None}
    for q in quantiles:
        out[f"p{round(q * 100)}"] = quantile(s, q)
    return out


def _counts(rows: list[dict]) -> dict:
    flags = {"ORIGIN_INCOMPLETE": 0, "A_UNAVAILABLE": 0, "RIGHT_CENSORED": 0, "GAP": 0}
    for r in rows:
        if r["originStatus"] != "VALID":
            flags["ORIGIN_INCOMPLETE"] += 1
        if r["aStatus"] != "VALID":
            flags["A_UNAVAILABLE"] += 1
        for f in r["futureFlags"]:
            flags[f] += 1
    available = sum(1 for r in rows if r["final"] is not None)
    return {
        "n": len(rows),
        "originValid": sum(r["originStatus"] == "VALID" for r in rows),
        "aValid": sum(r["aStatus"] == "VALID" for r in rows),
        "futureComplete": sum(r["futureStatus"] == "COMPLETE" for r in rows),
        "measuresAvailable": available,
        "measuresMissing": len(rows) - available,
        "missingFlags": flags,
    }


def _group(rows: list[dict], quantiles: list[float]) -> dict:
    out = _counts(rows)
    avail = [r for r in rows if r["final"] is not None]
    out["stats"] = {m: describe([r[m] for r in avail], quantiles) for m in MEASURES}
    return out


def summarize(rows: list[dict], availability: list[dict], conv) -> dict:
    study = conv.section("study")
    quantiles = study["quantiles"]
    periods = list(study["months"]) + [TOTAL]
    by_period = {p: [r for r in rows if p == TOTAL or r["month"] == p] for p in periods}
    avail_by_period = {p: [a for a, r in zip(availability, rows) if p == TOTAL or r["month"] == p] for p in periods}

    tables = {}
    for p in periods:
        prow = by_period[p]
        cov = _counts(prow)
        cov["rightCensoredOrigins"] = sum("RIGHT_CENSORED" in r["futureFlags"] for r in prow)
        cov["availabilityAtOrigin"] = _availability(avail_by_period[p])
        tables[p] = {
            "coverage": cov,
            "s45": {s: _group([r for r in prow if r["s45"] == s], quantiles) for s in S_STATES},
            "relation": {
                s: {rel: _group([r for r in prow if r["s45"] == s and r["dailyRelation"] == rel], quantiles) for rel in RELATIONS}
                for s in ("UP", "DOWN")
            },
            "matrix": {s: {d: sum(1 for r in prow if r["s45"] == s and r["s1d"] == d) for d in S_STATES} for s in S_STATES},
        }
    checks = reconcile(rows, tables, study)
    return {"periods": periods, "tables": tables, "examples": examples(rows), "checks": checks}


def _availability(items: list[dict]) -> dict:
    out: dict = {}
    for item in items:
        for scale, measures in item.items():
            dst = out.setdefault(scale, {})
            for key, ok in measures.items():
                cell = dst.setdefault(key, {"available": 0, "missing": 0, "reasons": {}})
                if ok is True:
                    cell["available"] += 1
                else:
                    cell["missing"] += 1
                    cell["reasons"][ok] = cell["reasons"].get(ok, 0) + 1
    return out


def reconcile(rows: list[dict], tables: dict, study: dict) -> dict:
    """Somme delle partizioni: ogni violazione è un errore, non una nota."""
    total = tables[TOTAL]
    n = len(rows)
    problems = []
    if n != study["theoreticalOrigins"]:
        problems.append(f"origini {n} != {study['theoreticalOrigins']}")
    if sum(total["s45"][s]["n"] for s in S_STATES) != n:
        problems.append("partizione s45 non somma al totale")
    if sum(total["matrix"][s][d] for s in S_STATES for d in S_STATES) != n:
        problems.append("matrice s45×s1d non somma al totale")
    for s in ("UP", "DOWN"):
        if sum(total["relation"][s][rel]["n"] for rel in RELATIONS) != total["s45"][s]["n"]:
            problems.append(f"relazioni {s} non sommano a s45={s}")
    if sum(tables[m]["coverage"]["n"] for m in study["months"]) != n:
        problems.append("mesi non sommano al totale")
    for s in S_STATES:
        if sum(tables[m]["s45"][s]["n"] for m in study["months"]) != total["s45"][s]["n"]:
            problems.append(f"mesi non sommano per s45={s}")
    if any(r["dailyRelation"] != "NOT_APPLICABLE" for r in rows if r["s45"] not in ("UP", "DOWN")):
        problems.append("relazione giornaliera assegnata a s45 non direzionale")
    if problems:
        raise AssertionError("; ".join(problems))
    return {"origins": n, "rightCensored": total["coverage"]["rightCensoredOrigins"], "partitionsReconciled": True}


def examples(rows: list[dict]) -> dict:
    """Criteri retrospettivi dichiarati: per verso, la riga con final più opposto al verso (tie:
    origine più antica) e la prima origine disponibile del periodo. Non è un nuovo test."""
    out = {}
    for side in ("UP", "DOWN"):
        avail = [r for r in rows if r["s45"] == side and r["final"] is not None]
        if not avail:
            out[side] = {"contrary": None, "first": None}
            continue
        key = (lambda r: (r["final"], r["t"])) if side == "UP" else (lambda r: (-r["final"], r["t"]))
        contrary = min(avail, key=key)
        first = min(avail, key=lambda r: r["t"])
        out[side] = {"contrary": contrary["t"], "first": first["t"]}
    return out
