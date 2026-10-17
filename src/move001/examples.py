"""Casi MOVE-001 con la regola del contratto §12.3, fissata prima dell'elaborazione.

Primo cronologico per categoria fra gli eventi con istante nel DEV, ordinati per availableAt
dell'evento e poi ID stabile; per i rifiuti il caso è il riferimento occupante; per la sostituzione
il riferimento sostituito. In più il primo per nascita fra i riferimenti aperti a fine copertura.
Deduplicazione per riferimento con tutte le categorie; massimo 13; categoria vuota dichiarata.
"""

from __future__ import annotations

from .cycle import INTERRUPTED, LOST, OPPOSITE, OPPOSITE_AT_BIRTH, REACHED, REJ_FORMATION, REJ_USABLE, REPLACED, TEST

MAX_CASES = 13

RULES = (
    ("BIRTH_LONG", lambda e: e["type"] == "BIRTH" and e["side"] == "LONG"),
    ("BIRTH_SHORT", lambda e: e["type"] == "BIRTH" and e["side"] == "SHORT"),
    ("USABLE_AFTER_P1", lambda e: e["type"] == "USABLE"),
    ("ORIGIN_TEST", lambda e: (e["type"] == "SUSPENSION" and e["reason"] == TEST) or (e["type"] == "FACT" and e["fact"] == TEST)),
    ("BASE_LOST", lambda e: e["type"] == "ARCHIVE" and e["reason"] == LOST),
    ("OPPOSITE_STRUCTURE_AT_BIRTH", lambda e: e["type"] == "SUSPENSION" and e["reason"] == OPPOSITE_AT_BIRTH),
    ("OPPOSITE_STRUCTURE_LATER", lambda e: e["type"] == "SUSPENSION" and e["reason"] == OPPOSITE),
    ("GEOMETRIC_COMPLETION", lambda e: e["type"] == "ARCHIVE" and e["reason"] == REACHED),
    ("REPLACED_AFTER_SUSPENSION", lambda e: e["type"] == "ARCHIVE" and e["reason"] == REPLACED),
    ("NOT_ADOPTED_FORMATION", lambda e: e["type"] == "CANDIDATE_REJECTED" and e["outcome"] == REJ_FORMATION),
    ("NOT_ADOPTED_USABLE", lambda e: e["type"] == "CANDIDATE_REJECTED" and e["outcome"] == REJ_USABLE),
    ("CONTINUITY_INTERRUPTED", lambda e: e["type"] == "ARCHIVE" and e["reason"] == INTERRUPTED),
)


def select(ledger: list[dict], refs: list, study_start: int, end: int) -> dict:
    dev = [e for e in ledger if study_start < e["t"] <= end and e["refId"]]
    cases: dict[str, dict] = {}
    empty = []

    def add(cat: str, ref_id: str, t: int) -> None:
        c = cases.setdefault(ref_id, {"refId": ref_id, "categories": [], "firstEventAt": t})
        c["categories"].append({"category": cat, "t": t})
        c["firstEventAt"] = min(c["firstEventAt"], t)

    for cat, rule in RULES:
        hits = sorted((e for e in dev if rule(e)), key=lambda e: (e["t"], e["refId"]))
        if hits:
            add(cat, hits[0]["refId"], hits[0]["t"])
        else:
            empty.append(cat)
    open_end = sorted((r for r in refs if r.archived is None and study_start < r.birth_t <= end), key=lambda r: (r.birth_t, r.id))
    if open_end:
        add("OPEN_AT_END_FIRST_BORN", open_end[0].id, open_end[0].birth_t)
    else:
        empty.append("OPEN_AT_END_FIRST_BORN")
    out = sorted(cases.values(), key=lambda c: (c["firstEventAt"], c["refId"]))
    if len(out) > MAX_CASES:
        raise AssertionError(f"{len(out)} casi > {MAX_CASES}")
    return {"rule": "docs/research/MOVE-001.md §12.3", "cases": out, "emptyCategories": empty}
