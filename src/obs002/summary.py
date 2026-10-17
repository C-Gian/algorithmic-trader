"""Tabelle prefissate OBS-002/v1 (task §5): un solo schema, nessuna ricerca di gruppi o soglie.

Celle: verso × profilo congiunto (§3). Per ciascuna: numerosità, gruppi distinti, completezza e
motivi, classi di contatto, final/favorevole/contrario P10/P50/P90 (lineare h=(n-1)q) e il profilo
simultaneo delle coordinate delle sei famiglie con disponibilità. Popolazione principale (ordinal 1
in DEV) separata dal riepilogo secondario di tutti i tentativi DEV, dipendenti.
"""

from __future__ import annotations

from datetime import UTC, datetime

from obs001.summary import quantile

from .outcomes import CLASSES, FLAGS
from .population import PROFILES, SIDE

Q3 = (0.1, 0.5, 0.9)


def month_of(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m")


def q3(values: list[float]) -> dict:
    s = sorted(values)
    return {"n": len(s), **{f"p{round(q * 100)}": quantile(s, q) for q in Q3}}


def _measure(m: dict | None) -> tuple[float | None, str | None]:
    if m is None:
        return None, "NOT_PRESENT"
    return m["v"], m["r"]


# Coordinate fissate del profilo simultaneo: (nome, estrattore) continue e categoriali.
def _continuous(a: dict) -> dict:
    s = a["snapshot"]
    na, nb = s["levels"]["nearestAhead"], s["levels"]["nearestBehind"]
    fib = s["fibonacci"]
    return {
        "depth": (a["reaction"]["depth"], None),
        "LoverA": _measure(s["volatility"]["LoverA"]), "toP1OverA": _measure(s["volatility"]["toP1"]),
        "toRextOverA": _measure(s["volatility"]["toRext"]), "AoverC": _measure(s["volatility"]["AoverC"]),
        "nearestAheadOverA": _measure(na["dist"]) if na else (None, "NO_LEVEL_AHEAD"),
        "nearestBehindOverA": _measure(nb["dist"]) if nb else (None, "NO_LEVEL_BEHIND"),
        "dSmaDist": _measure(s["averages"]["dDist"]), "dSmaSlope": _measure(s["averages"]["dSlope"]),
        "dSmaPos": _measure(s["averages"]["dPos"]), "volumeRatio": _measure(s["volume"]["ratio"]),
        "fibR": (fib["r"], None) if fib["available"] else (None, fib["reason"]),
    }


def _categorical(a: dict) -> dict:
    s = a["snapshot"]
    na, nb = s["levels"]["nearestAhead"], s["levels"]["nearestBehind"]
    fib = s["fibonacci"]
    s1d = s["structure"]["s1D"]
    cross = s["averages"]["crossRelative"]
    return {
        "structure1D": s1d["v"] or "UNAVAILABLE",
        "nearestAheadKind": na["kind"] if na else "NONE",
        "nearestBehindKind": nb["kind"] if nb else "NONE",
        "levelAtC": "YES" if s["levels"]["atC"] else "NO",
        "crossRelative": cross["v"] or "UNAVAILABLE",
        "fibRelation": fib["relation"] if fib["available"] else "UNAVAILABLE",
        "fibSameAsContext": ("SAME" if fib["sameAsContext"] else "DIFFERENT") if fib["available"] else "UNAVAILABLE",
    }


def cell(attempts: list[dict], outcomes: dict) -> dict:
    out = {"attempts": len(attempts), "groups": len({a["groupId"] for a in attempts})}
    rows = [outcomes[a["attemptId"]] for a in attempts]
    out["complete"] = sum(1 for r in rows if r["complete"])
    out["incomplete"] = len(rows) - out["complete"]
    out["missingFlags"] = {f: sum(1 for r in rows if f in r["flags"]) for f in FLAGS}
    out["classes"] = {c: sum(1 for r in rows if r["class"] == c) for c in CLASSES}
    done = [r for r in rows if r["complete"]]
    for k in ("final", "favourable", "adverse"):
        out[k] = q3([r[k] for r in done])
    cont: dict[str, dict] = {}
    cats: dict[str, dict] = {}
    for a in attempts:
        for name, (v, r) in _continuous(a).items():
            c = cont.setdefault(name, {"values": [], "missing": {}})
            if v is None:
                c["missing"][r] = c["missing"].get(r, 0) + 1
            else:
                c["values"].append(v)
        for name, v in _categorical(a).items():
            cc = cats.setdefault(name, {})
            cc[v] = cc.get(v, 0) + 1
    out["coordinates"] = {n: {**q3(c["values"]), "available": len(c["values"]), "missing": c["missing"]} for n, c in cont.items()}
    out["categories"] = {n: dict(sorted(c.items())) for n, c in cats.items()}
    return out


def design(attempts: list[dict], outcomes: dict) -> dict:
    """Stesso disegno per ogni insieme: verso × profilo, più il totale del verso."""
    out = {}
    for side in SIDE.values():
        sa = [a for a in attempts if a["side"] == side]
        out[side] = {"ALL": cell(sa, outcomes),
                     **{p: cell([a for a in sa if a["snapshot"]["profile"]["profile"] == p], outcomes) for p in PROFILES}}
    return out


def overlap(attempts: list[dict], horizon_ms: int) -> dict:
    """Sovrapposizione delle finestre [t, t+H) fra tentativi: numerosità non indipendenti."""
    ts = sorted(a["t"] for a in attempts)
    overl = 0
    j0 = 0
    for i, t in enumerate(ts):
        while ts[j0] <= t - horizon_ms:
            j0 += 1
        left = i - j0  # finestre precedenti ancora aperte a t
        right = 0
        j = i + 1
        while j < len(ts) and ts[j] < t + horizon_ms:
            right += 1
            j += 1
        if left or right:
            overl += 1
    events = sorted([(t, 1) for t in ts] + [(t + horizon_ms, -1) for t in ts], key=lambda x: (x[0], x[1]))
    cur = peak = 0
    for _, step in events:
        cur += step
        peak = max(peak, cur)
    return {"attempts": len(ts), "overlappingAnother": overl, "maxConcurrentWindows": peak}


def flow(pop, study) -> dict:
    """Conteggi del flusso, sull'intero input e sulle sole origini DEV."""
    s0, end = study.study_start, study.end
    ev = pop.events
    by = lambda rows, key: {k: sum(1 for r in rows if key(r) == k) for k in sorted({key(r) for r in rows})}  # noqa: E731
    dev_ev = [e for e in ev if s0 <= e["t"] < end]
    vers = [v.as_dict() for v in pop.versions]
    dev_v = [v for v in vers if s0 <= v["availableAt"] < end]
    groups = [g.as_dict() for g in pop.groups.values()]
    atts = pop.attempts
    dev = [a for a in atts if a["inStudy"]]
    groups_dev = [g for g in groups if any(s0 <= int(x.split(":")[-1]) < end for x in g["attempts"])]
    dev_ids = {g["groupId"] for g in groups_dev}
    vby = {v["versionId"]: v for v in vers}
    active_in_dev = [g for g in groups if any(vby[vid]["retiredAt"] > s0 and vby[vid]["availableAt"] < end for vid in g["versions"])]
    return {
        "fibEvents": {"input": by(ev, lambda e: e["action"]), "dev": by(dev_ev, lambda e: e["action"])},
        "eventOutcomes": {"input": by(ev, lambda e: e["outcome"]), "dev": by(dev_ev, lambda e: e["outcome"])},
        "versions": {"input": len(vers), "dev": len(dev_v), "byRetireReason": by(vers, lambda v: v["retireReason"]),
                     "devByRetireReason": by(dev_v, lambda v: v["retireReason"]), "bySide": by(vers, lambda v: v["side"]),
                     "withoutAttempt": sum(1 for v in vers if not v["attempts"]), "devWithoutAttempt": sum(1 for v in dev_v if not v["attempts"])},
        "groups": {"input": len(groups), "startedBeforeStudy": sum(1 for g in groups if g["startedBeforeStudy"]),
                   "withoutAnyAttempt": sum(1 for g in groups if not g["attempts"]), "activeInDev": len(active_in_dev),
                   "activeInDevWithoutDevAttempt": sum(1 for g in active_in_dev if g["groupId"] not in dev_ids), "withDevAttempt": len(groups_dev),
                   "withDevAttemptStartedBeforeStudy": sum(1 for g in groups_dev if g["startedBeforeStudy"])},
        "attempts": {"input": len(atts), "initialization": len(atts) - len(dev), "dev": len(dev),
                     "devPrimary": sum(1 for a in dev if a["ordinal"] == 1), "devRepeated": sum(1 for a in dev if a["ordinal"] > 1),
                     "devRepeatedAfterInitializationAttempts": sum(1 for a in dev if a["priorAttemptsInInitialization"] > 0),
                     "devBySide": by(dev, lambda a: a["side"]), "devPrimaryBySide": by([a for a in dev if a["ordinal"] == 1], lambda a: a["side"]),
                     "devByOrdinal": by(dev, lambda a: min(a["ordinal"], 5))},
    }


def periods_of(study) -> dict[str, tuple[int, int]]:
    from obs001.conventions import parse_utc

    out = {"DEV": (study.study_start, study.end), "2023": (parse_utc("2023-01-01T00:00:00Z"), parse_utc("2024-01-01T00:00:00Z")),
           "2024": (parse_utc("2024-01-01T00:00:00Z"), study.end)}
    return out


def summarize(pop, outcomes: dict, study) -> dict:
    dev = [a for a in pop.attempts if a["inStudy"]]
    primary = [a for a in dev if a["ordinal"] == 1]
    periods = {name: design([a for a in primary if s <= a["t"] < e], outcomes) for name, (s, e) in periods_of(study).items()}
    months = sorted({month_of(t) for t in range(study.study_start, study.end, 86_400_000)})
    by_month = {m: design([a for a in primary if month_of(a["t"]) == m], outcomes) for m in months}
    per_group: dict[str, int] = {}
    for a in dev:
        per_group[a["groupId"]] = per_group.get(a["groupId"], 0) + 1
    hist: dict[int, int] = {}
    for n in per_group.values():
        hist[n] = hist.get(n, 0) + 1
    summary = {
        "flow": flow(pop, study),
        "main": periods["DEV"], "periods": periods, "months": by_month,
        "secondary": {"label": "tutti i tentativi DEV, collegati e dipendenti (non un nuovo studio)", "DEV": design(dev, outcomes)},
        "dependence": {"primaryOverlap": overlap(primary, study.horizon_ms), "allDevOverlap": overlap(dev, study.horizon_ms),
                       "devAttemptsPerGroup": dict(sorted(hist.items())), "devGroups": len(per_group)},
    }
    summary["checks"] = reconcile(summary, dev, primary, outcomes)
    return summary


def reconcile(summary: dict, dev: list[dict], primary: list[dict], outcomes: dict) -> dict:
    """Ogni partizione ricostruisce la popolazione: una discrepanza è un errore, non una nota."""
    problems = []
    f = summary["flow"]["attempts"]
    if f["devPrimary"] + f["devRepeated"] != f["dev"] or f["devPrimary"] != len(primary):
        problems.append("primari + ripetuti != tentativi DEV")
    for name, des in (("main", summary["main"]), ("secondary", summary["secondary"]["DEV"])):
        pop = primary if name == "main" else dev
        if sum(des[s]["ALL"]["attempts"] for s in SIDE.values()) != len(pop):
            problems.append(f"{name}: versi non sommano")
        for s in SIDE.values():
            allc = des[s]["ALL"]
            if sum(des[s][p]["attempts"] for p in PROFILES) != allc["attempts"]:
                problems.append(f"{name} {s}: profili non sommano")
            for c in [allc] + [des[s][p] for p in PROFILES]:
                if sum(c["classes"].values()) != c["complete"] or c["complete"] + c["incomplete"] != c["attempts"]:
                    problems.append(f"{name} {s}: classi/completezza non sommano")
                if any(v["available"] + sum(v["missing"].values()) != c["attempts"] for v in c["coordinates"].values()):
                    problems.append(f"{name} {s}: disponibilità coordinate non somma")
    if sum(summary["months"][m]["LONG"]["ALL"]["attempts"] + summary["months"][m]["SHORT"]["ALL"]["attempts"] for m in summary["months"]) != len(primary):
        problems.append("mesi non sommano")
    if len({a["attemptId"] for a in dev}) != len(dev) or any(a["attemptId"] not in outcomes for a in dev):
        problems.append("identità dei tentativi o esiti mancanti")
    if problems:
        raise AssertionError("; ".join(problems))
    return {"reconciled": True, "primary": len(primary), "dev": len(dev)}
