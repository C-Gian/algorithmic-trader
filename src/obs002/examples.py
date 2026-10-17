"""Esempi OBS-002 con la regola del task §6, fissata prima dell'estrazione.

Sulla popolazione principale (ordinal 1 in DEV): primo cronologico per verso e profilo (8); primo
CONCORDANT con final <= 0 e primo OPPOSITE con final > 0 complessivi (categorie retrospettive,
esiti completi); primo RIGHT_CENSORED; primo BOTH_UNORDERED completo. Dal registro di tutti i
tentativi DEV: primo tentativo ripetuto (ordinal > 1). Ordine t poi attemptId; deduplicazione per
attemptId conservando le categorie; massimo 13; categoria vuota dichiarata, mai sostituita.
"""

from __future__ import annotations

from .population import PROFILES, SIDE

MAX_CASES = 13


def select(dev: list[dict], outcomes: dict) -> dict:
    primary = [a for a in dev if a["ordinal"] == 1]
    key = lambda a: (a["t"], a["attemptId"])  # noqa: E731
    o = lambda a: outcomes[a["attemptId"]]  # noqa: E731
    rules: list[tuple[str, list[dict]]] = []
    for side in SIDE.values():
        for p in PROFILES:
            rules.append((f"FIRST_{side}_{p}", [a for a in primary if a["side"] == side and a["snapshot"]["profile"]["profile"] == p]))
    rules += [
        ("FIRST_CONCORDANT_FINAL_LE_0", [a for a in primary if a["snapshot"]["profile"]["profile"] == "CONCORDANT" and o(a)["complete"] and o(a)["final"] <= 0]),
        ("FIRST_OPPOSITE_FINAL_GT_0", [a for a in primary if a["snapshot"]["profile"]["profile"] == "OPPOSITE" and o(a)["complete"] and o(a)["final"] > 0]),
        ("FIRST_RIGHT_CENSORED", [a for a in primary if "RIGHT_CENSORED" in o(a)["flags"]]),
        ("FIRST_REPEATED_ATTEMPT", [a for a in dev if a["ordinal"] > 1]),
        ("FIRST_BOTH_UNORDERED", [a for a in primary if o(a)["complete"] and o(a)["class"] == "BOTH_UNORDERED"]),
    ]
    cases: dict[str, dict] = {}
    empty = []
    for cat, items in rules:
        if not items:
            empty.append(cat)
            continue
        a = min(items, key=key)
        c = cases.setdefault(a["attemptId"], {"attemptId": a["attemptId"], "t": a["t"], "side": a["side"], "ordinal": a["ordinal"],
                                              "profile": a["snapshot"]["profile"]["profile"], "categories": []})
        c["categories"].append(cat)
    out = sorted(cases.values(), key=lambda c: (c["t"], c["attemptId"]))
    if len(out) > MAX_CASES:
        raise AssertionError(f"{len(out)} casi > {MAX_CASES}")
    return {"rule": "current_task OBS-002 §6", "cases": out, "emptyCategories": empty}
