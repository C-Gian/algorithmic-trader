"""Riscontro degli invarianti MOVE-001 su tutti i riferimenti, rideducendo i fatti dalle barre 45m.

Non decide nulla e non cambia output: rilegge ledger e riferimenti prodotti dal ciclo e controlla
che ogni fatto registrato sia giustificato dai prezzi e dai tempi disponibili allora. Una
violazione è un errore, non una nota.
"""

from __future__ import annotations

from .cycle import BASE_KIND, FINAL_KIND, LOST, REACHED, TEST


def verify(cy) -> dict:
    bars, bar_ms, inp = cy.bars, cy.bar_ms, cy.input_start
    k_of = lambda t: (t - inp) // bar_ms - 1  # noqa: E731  barra che chiude in t
    problems: list[str] = []
    by_ref: dict[str, list[dict]] = {}
    for e in cy.ledger:
        if e["refId"]:
            by_ref.setdefault(e["refId"], []).append(e)
    for r in cy.refs:
        d, P0, B, Q = r.d, r.P0["price"], r.B["price"], r.Q["price"]
        bad = lambda msg: problems.append(f"{r.id}: {msg}")  # noqa: E731
        if (r.Q["kind"], r.B["kind"], r.P0["kind"]) != (BASE_KIND[d], FINAL_KIND[d], BASE_KIND[d]):
            bad("tipi della tripla")
        if not (d * (P0 - Q) > 0 and d * (B - P0) > 0 and r.Q["candidateOpen"] < r.B["candidateOpen"] < r.P0["candidateOpen"]):
            bad("geometria della tripla")
        if r.P0["availableAt"] > r.birth_t:
            bad("P0 non ancora noto alla nascita")
        k = r.birth_k
        if bars[k].end != r.birth_t or not (d * (bars[k - 1].c - B) <= 0 < d * (bars[k].c - B)):
            bad("nessun nuovo attraversamento in chiusura alla nascita")
        i0 = (r.P0["candidateOpen"] - inp) // bar_ms
        if any((bars[j].l <= P0) if d == 1 else (bars[j].h >= P0) for j in range(i0 + 1, k + 1)):
            bad("base testata prima o alla nascita")
        end_t = r.archived["t"] if r.archived else cy.end
        last = k_of(end_t) if r.archived else k_of(cy.end) + 1
        for j in range(k + 1, last):  # chiusure intermedie: nessuna perdita in chiusura non registrata
            if d * (bars[j].c - P0) <= 0:
                bad(f"chiusura oltre la base non registrata a {bars[j].end}")
                break
        if r.P1 is not None:
            if not (r.P1["kind"] == FINAL_KIND[d] and r.P1["candidateOpen"] >= bars[k].start and d * (r.P1["price"] - B) > 0):
                bad("P1 non qualificato")
            if r.P1["availableAt"] != r.p1_t or r.p1_t <= r.birth_t or (r.archived and r.p1_t > r.archived["t"]):
                bad("tempo di pubblicazione di P1")
        if r.usable_t is not None and (r.usable_t != r.p1_t or (r.suspended and r.suspended["t"] < r.usable_t)):
            bad("passaggio a UTILIZZABILE incoerente")
        if r.suspended and r.suspended["reason"] == TEST:
            b = bars[k_of(r.suspended["t"])]
            if not ((b.l <= P0 < b.c) if d == 1 else (b.c < P0 <= b.h)):
                bad("sospensione per test non giustificata dalla barra")
        if r.archived:
            b = bars[k_of(r.archived["t"])]
            if r.archived["reason"] == LOST and not d * (b.c - P0) <= 0:
                bad("perdita senza chiusura oltre la base")
            if r.archived["reason"] == REACHED:
                if r.suspended or r.P1 is None or r.p1_t >= r.archived["t"] or not ((b.h >= r.P1["price"]) if d == 1 else (b.l <= r.P1["price"])):
                    bad("completamento non giustificato")
        evs = by_ref.get(r.id, [])
        if not evs or evs[0]["type"] != "BIRTH" or any(e["t"] < r.birth_t for e in evs):
            bad("ledger non inizia con la nascita")
        if r.archived and any(e["t"] > r.archived["t"] for e in evs):
            bad("fatti dopo l'archiviazione")
    # un solo principale: le chiusure riportano un riferimento attivo coerente con nascita e archiviazione
    life = {r.id: (r.birth_t, r.archived["t"] if r.archived else cy.end + 1) for r in cy.refs}
    for c in cy.closes:
        if c["refId"] is not None:
            b, a = life[c["refId"]]
            if not b <= c["t"] < a:
                problems.append(f"chiusura {c['t']}: principale fuori dalla sua vita")
    if problems:
        raise AssertionError(f"{len(problems)} violazioni, prima: {problems[0]}")
    return {"references": len(cy.refs), "closes": len(cy.closes), "violations": 0}
