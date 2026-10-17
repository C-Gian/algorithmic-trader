"""Costruttori sintetici per i test MOVE-001 (prezzi inventati, non BTC). Pivot iniettati a mano come
eventi FIB_SEQUENCE con availableAt = chiusura della seconda barra a destra (2+2)."""

from __future__ import annotations

from obs001.aggregate import COMPLETE, INCOMPLETE, Bar

from move001.cycle import Cycle

BAR = 45 * 60_000
T0 = 1_664_582_400_000  # 2022-10-01T00:00Z, solo origine sintetica


def m(v, r="NO_CONFIRMED_PIVOTS"):
    return {"v": v, "r": None if v is not None else r}


class Mv:
    def __init__(self, n=60, price=108.0, structure="MIXED"):
        self.n = n
        self.bars = [Bar(T0 + k * BAR, T0 + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=price, h=price + 0.2, l=price - 0.2, c=price, v=1.0) for k in range(n)]
        self.recs = [{"status": "COMPLETE", "segment": {"id": 1, "bars": k + 1}, "piv": {"structure": m(structure)}} for k in range(n)]
        self.events = []

    def bar(self, k, h, l, c, o=None):
        o = c if o is None else o
        self.bars[k] = Bar(T0 + k * BAR, T0 + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=o, h=max(h, o, c), l=min(l, o, c), c=c, v=1.0)
        return self

    def structure(self, k_from, value, k_to=None):
        for k in range(k_from, (k_to if k_to is not None else self.n - 1) + 1):
            self.recs[k]["piv"]["structure"] = m(value)
        return self

    def pivot(self, kind, price, k, action="APPEND"):
        co = T0 + k * BAR
        after = {"kind": kind, "price": price, "candidateOpen": co, "eventTime": co + BAR, "availableAt": co + 3 * BAR}
        self.events.append({"id": f"E{len(self.events)}", "type": "FIB_SEQUENCE", "action": action, "availableAt": after["availableAt"],
                            "eventTime": after["eventTime"], "kind": kind, "version": len(self.events) + 1, "after": after})
        return self

    def gap(self, k):
        self.bars[k] = Bar(T0 + k * BAR, T0 + (k + 1) * BAR, INCOMPLETE, 40, 5, 0)
        self.recs[k] = {"status": "INCOMPLETE", "segment": None, "piv": {"structure": m(None, "INCOMPLETE_INPUT")}}
        for j in range(k + 1, self.n):
            self.recs[j]["segment"] = {"id": 2, "bars": j - k}
        return self

    def mirror(self, axis=220.0):
        out = Mv(self.n)
        for k, b in enumerate(self.bars):
            out.bars[k] = Bar(b.start, b.end, b.status, b.valid, b.missing, b.invalid,
                              **({} if not b.complete else {"o": axis - b.o, "h": axis - b.l, "l": axis - b.h, "c": axis - b.c, "v": b.v}))
            s = self.recs[k]["piv"]["structure"]["v"]
            out.recs[k] = {**self.recs[k], "piv": {"structure": m({"UP": "DOWN", "DOWN": "UP"}.get(s, s), "NO_CONFIRMED_PIVOTS")}}
        flip = {"LOW": "HIGH", "HIGH": "LOW"}
        for e in self.events:
            a = e["after"]
            out.events.append({**e, "kind": flip[e["kind"]], "after": {**a, "kind": flip[a["kind"]], "price": axis - a["price"]}})
        return out

    def run(self, end_k=None):
        end = T0 + ((end_k if end_k is not None else self.n - 1) + 1) * BAR
        return Cycle(self.bars, self.recs, self.events, T0, BAR, end).run()

    @staticmethod
    def t(k):
        return T0 + (k + 1) * BAR


def base(n=60, **kw):
    """§8.1: Q LOW 100 (barra 2), B HIGH 110 (5), P0 LOW 104 (7, noto alla chiusura 9); rottura alla barra 10
    con chiusure 109 -> 111 e low 105. P1 HIGH 116 sulla barra 11, pubblicato alla chiusura 13."""
    mv = Mv(n, **kw)
    mv.pivot("LOW", 100, 2).pivot("HIGH", 110, 5).pivot("LOW", 104, 7)
    mv.bar(9, 109.5, 108, 109).bar(10, 111.5, 105, 111, o=109)
    return mv


def with_p1(mv):
    mv.bar(11, 116, 110, 115).bar(12, 115.5, 110, 112).bar(13, 114, 109, 111)
    mv.pivot("HIGH", 116, 11)
    return mv


def kinds(cy, upto=None, admin=False):
    """Eventi del ledger; OPEN_AT_END (amministrativo, fine copertura) incluso solo se richiesto."""
    return [(e["type"], e.get("reason") or e.get("fact") or e.get("outcome"), e["t"]) for e in cy.ledger
            if (upto is None or e["t"] <= upto) and (admin or e["type"] != "OPEN_AT_END")]


def types(cy):
    return [e["type"] for e in cy.ledger if e["type"] != "OPEN_AT_END"]
