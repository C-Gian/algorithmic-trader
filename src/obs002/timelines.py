"""Timeline degli esempi OBS-002: proiezione causale «noto a t» e migrazione R1 del derivato consegnato.

R1-A: i metadati di una versione sono proiettati per elenco consentito. Identità, ancore e
disponibilità (già note dalla creazione) sempre; ritiro e suoi fatti (motivo, replacedBy, sameGroup,
eventuali altri) solo se il ritiro è avvenuto entro t; tentativi della versione solo fino a t.
Un campo nuovo non previsto qui resta escluso finché il ritiro non è effettivo.
"""

from __future__ import annotations

from obs001.conventions import iso

KNOWN_FROM_CREATION = ("versionId", "groupId", "side", "d", "P0", "P1", "L", "availableAt", "action", "fibVersion", "segment", "activeFrom")
TIMELINE_R1_VERSION = "obs002.timeline/2"  # /1 = consegna c8ac744 (metadati di ritiro futuri non proiettati)


def attempt_time(attempt_id: str) -> int:
    return int(attempt_id.split(":")[-1])


def project_version(v: dict, t: int) -> dict:
    if v["availableAt"] > t:
        raise ValueError(f"versione {v['versionId']} non ancora disponibile a {t}")
    out = {k: v[k] for k in KNOWN_FROM_CREATION}
    retired = v["retiredAt"] is not None and v["retiredAt"] <= t
    out["retiredAt"] = v["retiredAt"] if retired else None
    out["retireReason"] = v["retireReason"] if retired else None
    if retired:
        out.update({k: x for k, x in v.items() if k not in KNOWN_FROM_CREATION + ("retiredAt", "retireReason", "attempts")})
    out["attempts"] = [x for x in v["attempts"] if attempt_time(x) <= t]
    return out


def timeline(case: dict, attempt: dict, outcome_row: dict, pop, c: dict) -> dict:
    """Noto a t (versioni proiettate, barre chiuse, snapshot) separato dal seguito retrospettivo."""
    t = attempt["t"]
    g = pop.groups[attempt["groupId"]]
    versions = [project_version(v.as_dict(), t) for v in pop.versions if v.group_id == g.id and v.t0 <= t]
    p0 = attempt["version"]["P0"]["candidateOpen"]
    bars = [{"open": b.start, "o": b.o, "h": b.h, "l": b.l, "c": b.c} for b in c["bars45"] if p0 <= b.start and b.end <= t]
    prior = [a for a in pop.attempts if a["groupId"] == g.id and a["t"] < t]
    return {"attemptId": attempt["attemptId"], "categories": case["categories"],
            "knownAtT": {"t": t, "tIso": iso(t), "groupVersionsSoFar": versions,
                         "priorAttemptsOfGroup": [{"attemptId": a["attemptId"], "t": a["t"]} for a in prior], "bars45SinceP0": bars,
                         "attempt": attempt},
            "afterT": {"label": "A POSTERIORI", "outcome": outcome_row}}


def migrate_examples(original: dict, population: dict) -> dict:
    """Derivato R1 di examples.json: rifà la sola proiezione di knownAtT.groupVersionsSoFar dalle versioni
    registrate in population.json. Lista, categorie, afterT, tentativi, barre e tentativi precedenti restano
    identici; nessun prezzo riletto, nessuna popolazione o esito ricalcolato, nessun esempio nuovo."""
    by_id = {v["versionId"]: v for v in population["versions"]}
    out = {k: v for k, v in original.items() if k != "timelines"}
    tls = []
    for tl in original["timelines"]:
        kn = tl["knownAtT"]
        t = kn["t"]
        ids = [v["versionId"] for v in kn["groupVersionsSoFar"]]
        group = kn["attempt"]["groupId"]
        expected = [v["versionId"] for v in population["versions"] if v["groupId"] == group and v["availableAt"] <= t]
        if ids != expected:
            raise AssertionError(f"{tl['attemptId']}: versioni della timeline diverse dalla popolazione registrata")
        tls.append({**tl, "knownAtT": {**kn, "groupVersionsSoFar": [project_version(by_id[i], t) for i in ids]}})
    out["timelines"] = tls
    return out
