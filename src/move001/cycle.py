"""Ciclo causale MOVE-001/v1 (contratto docs/research/MOVE-001.md §§2-7 e 11, versione 1.0.1).

A ogni chiusura 45m si leggono soltanto: la barra appena chiusa (e la precedente), il record
osservativo di quella barra (struttura 45m) e gli eventi OBS-001 con availableAt uguale alla
chiusura. Ordine deterministico (§11.3): continuità, eventi, riferimento esistente, tripla e
adozione/rifiuto, struttura del neonato. Nessun prezzo successivo, nessuna simulazione intrabar,
nessun esito economico. Il ledger è append-only: un riferimento archiviato non viene riscritto.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from obs001.aggregate import Bar

SIDE = {1: "LONG", -1: "SHORT"}
BASE_KIND = {1: "LOW", -1: "HIGH"}
FINAL_KIND = {1: "HIGH", -1: "LOW"}
OPPOSITE_STRUCTURE = {1: "DOWN", -1: "UP"}

UT, NS, IND = "UTILIZZABILE", "NON_SOSTIENE_PIU_LA_TESI", "INDETERMINATO"
FORMATION = "FORMAZIONE_NON_CONCLUSA"
TEST = "TEST_ORIGINE"
OPPOSITE = "STRUTTURA_OPPOSTA"
OPPOSITE_AT_BIRTH = "STRUTTURA_OPPOSTA_ALLA_NASCITA"
DATA = "DATI_INCOMPLETI"
LOST = "ORIGINE_IN_CHIUSURA"
REACHED = "ESTREMO_RAGGIUNTO"
REPLACED = "SOSTITUITO_DA_NUOVA_STRUTTURA"
INTERRUPTED = "CONTINUITA_INTERROTTA"
END = "FINE_COPERTURA"

ADOPTED = "ADOTTATA"
REJ_FORMATION = "NON_ADOTTATA_OCCUPATO_FORMAZIONE"
REJ_USABLE = "NON_ADOTTATA_OCCUPATO_UTILIZZABILE"
REJ_FRESH = "NON_ADOTTATA_FRESCHEZZA"
OUTCOMES = (ADOPTED, REJ_FORMATION, REJ_USABLE, REJ_FRESH)

# Condizioni di occupazione mutuamente esclusive alla fine di ogni chiusura completa
ABSENT, C_FORMATION, C_SUSP_P1, C_SUSP_NO_P1, C_USABLE = "ASSENTE", "FORMAZIONE", "SOSPESO_CON_P1", "SOSPESO_SENZA_P1", "UTILIZZABILE"
CONDITIONS = (ABSENT, C_FORMATION, C_SUSP_P1, C_SUSP_NO_P1, C_USABLE)

# Esito delle triple correnti con geometria valida (contate a parte, mai come strutture bloccate)
TRIPLE_GEOMETRY, TRIPLE_TESTED, TRIPLE_NO_CROSSING, TRIPLE_QUALIFIED = "GEOMETRIA_NON_QUALIFICANTE", "BASE_TESTATA_PRIMA_DELL_ATTRAVERSAMENTO", "NESSUN_ATTRAVERSAMENTO", "QUALIFICATA"


def pref(p: dict) -> dict:
    return {k: p[k] for k in ("id", "kind", "price", "candidateOpen", "eventTime", "availableAt", "version")}


@dataclass
class Ref:
    id: str
    d: int
    segment: int
    Q: dict
    B: dict
    P0: dict
    birth_t: int
    birth_k: int
    predecessor: str | None
    P1: dict | None = None
    p1_t: int | None = None
    usable_t: int | None = None
    suspended: dict | None = None  # prima sospensione metodologica: {reason, t, k, barOpen}
    archived: dict | None = None
    prev_opposite: bool = False
    closes: dict = field(default_factory=lambda: {c: 0 for c in CONDITIONS if c != ABSENT})

    @property
    def side(self) -> str:
        return SIDE[self.d]

    def condition(self) -> str:
        if self.suspended:
            return C_SUSP_P1 if self.P1 else C_SUSP_NO_P1
        return C_FORMATION if self.P1 is None else C_USABLE

    def judgement(self) -> tuple[str, str]:
        if self.suspended:
            return IND, self.suspended["reason"]
        return (IND, FORMATION) if self.P1 is None else (UT, "P1_NOTO")

    def as_dict(self) -> dict:
        return {"refId": self.id, "side": self.side, "d": self.d, "segment": self.segment, "Q": self.Q, "B": self.B, "P0": self.P0,
                "birthAt": self.birth_t, "predecessor": self.predecessor, "P1": self.P1, "p1At": self.p1_t, "usableAt": self.usable_t,
                "suspension": self.suspended, "archive": self.archived, "closesByCondition": dict(self.closes)}


class Cycle:
    def __init__(self, bars45: list[Bar], recs45: list[dict], events45: list[dict], input_start: int, bar_ms: int, end: int):
        self.bars, self.recs = bars45, recs45
        self.input_start, self.bar_ms, self.end = input_start, bar_ms, end
        self.events_at: dict[int, list[dict]] = {}
        for e in events45:
            if e["type"] == "FIB_SEQUENCE":
                self.events_at.setdefault(e["availableAt"], []).append(e)
        self.seq: list[dict] = []  # ultimi pivot accettati della sequenza alternata nel segmento corrente
        self.segment: int | None = None
        self.principal: Ref | None = None
        self.barrier: int | None = None  # P0 candidato deve avere candidateOpen > barrier (posto libero)
        self.considered: set = set()
        self.refs: list[Ref] = []
        self.ledger: list[dict] = []
        self.structures: list[dict] = []
        self.triples: list[dict] = []
        self.cur: dict | None = None  # stato della tripla corrente
        self.closes: list[dict] = []
        self.last_complete_end: int | None = None

    # ------------------------------------------------------------ utilità

    def emit(self, t: int, ref: Ref | None, typ: str, **facts) -> dict:
        ev = {"t": t, "type": typ, "refId": ref.id if ref else None, "side": ref.side if ref else None, **facts}
        self.ledger.append(ev)
        return ev

    def archive(self, ref: Ref, t: int, reason: str, judgement: tuple[str, str], **facts) -> None:
        ref.archived = {"t": t, "reason": reason, "judgement": judgement[0], "judgementReason": judgement[1], "conditionBefore": ref.condition(), **facts}
        self.emit(t, ref, "ARCHIVE", reason=reason, judgement=judgement[0], judgementReason=judgement[1], conditionBefore=ref.condition(), **facts)
        if self.principal is ref:
            self.principal = None

    def suspend(self, ref: Ref, t: int, k: int, reason: str, **facts) -> None:
        ref.suspended = {"reason": reason, "t": t, "k": k, "barOpen": self.bars[k].start, **facts}
        self.emit(t, ref, "SUSPENSION", reason=reason, condition=ref.condition(), **facts)

    # ------------------------------------------------------------ passo

    def run(self) -> "Cycle":
        for k, bar in enumerate(self.bars):
            if bar.end > self.end:
                break
            self.close(k, bar.end)
        self.finish_triple(self.end, "STUDY_END")
        if self.principal is not None:
            p = self.principal
            j = p.judgement()
            self.emit(self.end, p, "OPEN_AT_END", reason=END, judgement=j[0], judgementReason=j[1], condition=p.condition())
        return self

    def close(self, k: int, t: int) -> None:
        bar, rec = self.bars[k], self.recs[k]
        # 1. continuità
        if not bar.complete:
            if self.principal is not None:
                self.archive(self.principal, t, INTERRUPTED, (IND, DATA), lastCompleteClose=self.last_complete_end, firstIncompleteClose=t)
            self.finish_triple(t, "SEGMENT_END")
            self.seq, self.segment, self.barrier = [], None, None
            self.closes.append({"t": t, "complete": False, "condition": None, "refId": None, "side": None})
            return
        seg = rec["segment"]["id"]
        if seg != self.segment:
            self.seq, self.segment = [], seg
        # 2. eventi disponibili a questa chiusura
        p1_new = None
        p = self.principal
        for ev in self.events_at.get(t, []):
            if ev["action"] not in ("APPEND", "REPLACE"):
                continue  # KEEP: non accettato
            after = ev["after"]
            entry = {"id": f"{after['kind']}:{after['candidateOpen']}", "kind": after["kind"], "price": after["price"],
                     "candidateOpen": after["candidateOpen"], "eventTime": after["eventTime"], "availableAt": after["availableAt"],
                     "version": ev["version"]}
            if ev["action"] == "APPEND":
                self.seq.append(entry)
            else:
                self.seq[-1] = entry
            del self.seq[:-3]
            if p is not None and p.P1 is None and p1_new is None and after["kind"] == FINAL_KIND[p.d] and \
                    after["candidateOpen"] >= self.bars[p.birth_k].start and p.d * (after["price"] - p.B["price"]) > 0:
                p1_new = pref(entry)
        struct = rec["piv"]["structure"]["v"]
        # 3. riferimento esistente
        if p is not None:
            self.evaluate(p, k, t, struct, p1_new)
        # 4-5. tripla corrente, attraversamento, adozione e struttura del neonato
        self.consider(k, t, struct)
        self.last_complete_end = t
        p = self.principal
        cond = p.condition() if p else ABSENT
        if p:
            p.closes[cond] += 1
        self.closes.append({"t": t, "complete": True, "condition": cond, "refId": p.id if p else None, "side": p.side if p else None})

    def evaluate(self, r: Ref, k: int, t: int, struct: str | None, p1_new: dict | None) -> None:
        bar, d = self.bars[k], r.d
        P0 = r.P0["price"]
        p1_contact = r.P1 is not None and r.p1_t < t and (bar.h >= r.P1["price"] if d == 1 else bar.l <= r.P1["price"])
        if p1_new is not None:
            r.P1, r.p1_t = p1_new, t
            self.emit(t, r, "P1_PUBLISHED", P1=p1_new, whileSuspended=r.suspended is not None)
        # (a) perdita della base in chiusura
        if d * (bar.c - P0) <= 0:
            flags = ["P1_TOCCATO_STESSA_BARRA_ORDINE_IGNOTO"] if p1_contact else []
            self.archive(r, t, LOST, (NS, LOST), C=bar.c, flags=flags)
            self.barrier = bar.start
            return
        # (b) test della base recuperato in chiusura
        if (bar.l <= P0) if d == 1 else (bar.h >= P0):
            flags = ["DOPPIO_TEST_ORDINE_IGNOTO"] if p1_contact else []
            if r.suspended is None:
                self.suspend(r, t, k, TEST, flags=flags)
            else:
                self.emit(t, r, "FACT", fact=TEST, flags=flags)
        # (c) ritorno a P1 noto prima di questa chiusura
        elif p1_contact:
            if r.suspended is None:
                self.archive(r, t, REACHED, (UT, "P1_NOTO"))
                self.barrier = r.P0["candidateOpen"]
                return
            self.emit(t, r, "FACT", fact="P1_TOCCATO_DA_SOSPESO")
        # (d) struttura 45m opposta
        opp = struct == OPPOSITE_STRUCTURE[d]
        if opp and r.suspended is None:
            self.suspend(r, t, k, OPPOSITE)
        elif opp and not r.prev_opposite:
            self.emit(t, r, "FACT", fact=OPPOSITE)
        r.prev_opposite = opp
        # (e) primo passaggio a UTILIZZABILE
        if p1_new is not None and r.suspended is None:
            r.usable_t = t
            self.emit(t, r, "USABLE")

    # ------------------------------------------------------------ tripla

    def triple_now(self) -> dict | None:
        if len(self.seq) < 3:
            return None
        q, b, p0 = self.seq[-3:]
        kinds = (q["kind"], b["kind"], p0["kind"])
        d = 1 if kinds == ("LOW", "HIGH", "LOW") else -1 if kinds == ("HIGH", "LOW", "HIGH") else None
        key = (self.segment, q["id"], q["version"], b["id"], b["version"], p0["id"], p0["version"])
        ok = d is not None and d * (p0["price"] - q["price"]) > 0 and d * (b["price"] - p0["price"]) > 0 and \
            q["candidateOpen"] < b["candidateOpen"] < p0["candidateOpen"]
        return {"key": key, "d": d, "Q": q, "B": b, "P0": p0, "geometry": ok}

    def finish_triple(self, t: int, why: str) -> None:
        c = self.cur
        if c is None:
            return
        if not c["geometry"]:
            res = TRIPLE_GEOMETRY
        elif c["qualified"]:
            res = TRIPLE_QUALIFIED
        elif c["tested"]:
            res = TRIPLE_TESTED
        else:
            res = TRIPLE_NO_CROSSING
        self.triples.append({"availableAt": c["since"], "endedAt": t, "endedBy": why, "side": SIDE.get(c["d"]), "result": res})
        self.cur = None

    def tests_base(self, j: int, d: int, p0: float) -> bool:
        b = self.bars[j]
        return b.l <= p0 if d == 1 else b.h >= p0

    def consider(self, k: int, t: int, struct: str | None) -> None:
        tr = self.triple_now()
        if tr is None:
            self.finish_triple(t, "SEQUENCE_SHORT")
            return
        if self.cur is None or self.cur["key"] != tr["key"]:
            self.finish_triple(t, "NEW_TRIPLE")
            i0 = (tr["P0"]["candidateOpen"] - self.input_start) // self.bar_ms
            tested = tr["geometry"] and any(self.tests_base(j, tr["d"], tr["P0"]["price"]) for j in range(i0 + 1, k + 1))
            self.cur = {**tr, "since": t, "tested": tested, "qualified": False}
        else:
            c = self.cur
            if c["geometry"] and not c["tested"]:
                c["tested"] = self.tests_base(k, c["d"], c["P0"]["price"])
        c = self.cur
        if not c["geometry"] or c["tested"] or c["key"] in self.considered:
            return
        prev, bar, d, B = self.bars[k - 1], self.bars[k], c["d"], c["B"]["price"]
        if not (prev.complete and self.recs[k - 1]["segment"] and self.recs[k - 1]["segment"]["id"] == self.segment):
            return
        if not (d * (prev.c - B) <= 0 < d * (bar.c - B)):
            return
        self.considered.add(c["key"])
        c["qualified"] = True
        self.decide(c, k, t, struct)

    def decide(self, c: dict, k: int, t: int, struct: str | None) -> None:
        p, d = self.principal, c["d"]
        occupant = None if p is None else {"refId": p.id, "side": p.side, "condition": p.condition()}
        p0_open = c["P0"]["candidateOpen"]
        if p is None:
            outcome = REJ_FRESH if self.barrier is not None and p0_open <= self.barrier else ADOPTED
        elif p.suspended is not None:
            outcome = ADOPTED if p0_open > p.suspended["barOpen"] else REJ_FRESH
        elif p.P1 is None:
            outcome = REJ_FORMATION
        else:
            outcome = REJ_USABLE
        rec = {"t": t, "side": SIDE[d], "d": d, "Q": pref(c["Q"]), "B": pref(c["B"]), "P0": pref(c["P0"]), "outcome": outcome,
               "occupant": occupant, "barrier": self.barrier if p is None else (p.suspended["barOpen"] if p.suspended else None), "refId": None}
        self.structures.append(rec)
        if outcome != ADOPTED:
            if p is not None:
                self.emit(t, p, "CANDIDATE_REJECTED", outcome=outcome, candidateSide=SIDE[d], candidateB=c["B"]["price"], candidateP0=c["P0"]["price"],
                          candidateP0Open=p0_open)
            return
        bar = self.bars[k]
        r = Ref(id=f"MOV:{SIDE[d]}:{c['B']['candidateOpen']}:{p0_open}:{t}", d=d, segment=self.segment, Q=pref(c["Q"]), B=pref(c["B"]),
                P0=pref(c["P0"]), birth_t=t, birth_k=k, predecessor=p.id if p else None)
        if p is not None:
            self.archive(p, t, REPLACED, p.judgement(), replacedBy=r.id)
        rec["refId"] = r.id
        self.refs.append(r)
        self.principal = r
        self.barrier = None
        self.emit(t, r, "BIRTH", Q=r.Q, B=r.B, P0=r.P0, Cprev=self.bars[k - 1].c, C=bar.c, predecessor=r.predecessor)
        # 5. struttura già opposta alla nascita: nascita conservata, sospensione immediata
        opp = struct == OPPOSITE_STRUCTURE[d]
        r.prev_opposite = opp
        if opp:
            self.suspend(r, t, k, OPPOSITE_AT_BIRTH)
