"""Costruttori sintetici per i test OBS-002 (prezzi inventati, non BTC)."""

from __future__ import annotations

import random

from obs001.aggregate import COMPLETE, INCOMPLETE, Bar
from obs001.minutes import MinuteStore

from obs002.population import Population

BAR = 45 * 60_000
DAY = 86_400_000
MIN = 60_000
T0 = 1_664_582_400_000  # 2022-10-01T00:00Z, solo origine sintetica


def m(v, r="INSUFFICIENT_HISTORY"):
    return {"v": v, "r": None if v is not None else r}


def piv(kind, price, k):
    co = T0 + k * BAR
    return {"kind": kind, "price": price, "candidateOpen": co, "eventTime": co + BAR, "availableAt": co + 3 * BAR}


class Mk:
    """Barre 45m e record osservativi minimi; eventi FIB_SEQUENCE iniettati a mano."""

    def __init__(self, n=80, price=104.0, structure="UP", dist=1.0, slope=1.0, a=2.0):
        self.bars = [Bar(T0 + k * BAR, T0 + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=price, h=price + 0.2, l=price - 0.2, c=price, v=1.0)
                     for k in range(n)]
        self.recs = [self.rec(k, structure, dist, slope, a) for k in range(n)]
        self.events = []

    def rec(self, k, structure, dist, slope, a):
        b = self.bars[k]
        return {"open": b.start, "end": b.end, "status": "COMPLETE", "segment": {"id": 1, "bars": k + 1}, "C": b.c,
                "vol": {"A": m(a), "AoverC": m(a / b.c)},
                "avg": {"sma20": m(100.0), "sma50": m(99.0), "dist": m(dist), "slope": m(slope), "pos": m(0.5), "cross": m("NONE")},
                "volu": {"ratio": m(1.0), "base": 1.0, "median": m(1.0)},
                "piv": {"structure": m(structure, "NO_CONFIRMED_PIVOTS"), "highs": [], "lows": []},
                "fib": {"version": 0, "anchors": m(None, "NO_CONFIRMED_PIVOTS")}, "lvl": []}

    def set_bar(self, k, o, h, l, c):
        self.bars[k] = Bar(T0 + k * BAR, T0 + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=o, h=h, l=l, c=c, v=1.0)
        self.recs[k]["C"] = c

    def gap(self, k):
        self.bars[k] = Bar(T0 + k * BAR, T0 + (k + 1) * BAR, INCOMPLETE, 40, 5, 0)
        self.recs[k].update(status="INCOMPLETE", segment=None, C=None)
        for j in range(k + 1, len(self.recs)):
            self.recs[j]["segment"] = {"id": 2, "bars": j - k}

    def leg(self, p0, p1, available_k, action="APPEND", version=None):
        t = T0 + (available_k + 1) * BAR
        self.events.append({"id": f"E{len(self.events)}", "type": "FIB_SEQUENCE", "action": action, "availableAt": t, "eventTime": p1["eventTime"],
                            "kind": p1["kind"], "version": version or len(self.events) + 1, "anchors": [p0, p1]})
        return t

    def mirror(self):
        """Specchio SHORT: p -> 200 - p, high e low scambiati, ancore e struttura invertite."""
        out = Mk(len(self.bars))
        for k, b in enumerate(self.bars):
            out.set_bar(k, 200 - b.o, 200 - b.l, 200 - b.h, 200 - b.c)
            out.recs[k]["piv"]["structure"] = m({"UP": "DOWN", "DOWN": "UP"}.get(self.recs[k]["piv"]["structure"]["v"], "MIXED"))
            out.recs[k]["avg"]["dist"] = m(-self.recs[k]["avg"]["dist"]["v"])
            out.recs[k]["avg"]["slope"] = m(-self.recs[k]["avg"]["slope"]["v"])
        flip = {"LOW": "HIGH", "HIGH": "LOW"}
        for e in self.events:
            anchors = [{**p, "kind": flip[p["kind"]], "price": 200 - p["price"]} for p in e["anchors"]]
            out.events.append({**e, "kind": flip[e["kind"]], "anchors": anchors})
        return out

    def run(self, study_start=T0, end=None):
        n = len(self.bars)
        recs1d = [{"open": T0 + j * DAY, "piv": {"structure": m("UP"), "highs": [], "lows": []}} for j in range(n * BAR // DAY + 2)]
        return Population(self.bars, self.recs, recs1d, self.events, T0, BAR, DAY, study_start, end or T0 + n * BAR).run()

    def t(self, k):
        return T0 + (k + 1) * BAR


def long_case(n=80):
    """LONG: P0=100 (barra 10), P1=112 (barra 20) disponibile alla chiusura della barra 22.
    Reazione 21-22, primo tentativo alla barra 24; 25 continua senza arretramento; 26 arretra; 27 riprova."""
    mk = Mk(n)
    mk.set_bar(10, 101, 101.5, 100, 101)
    mk.set_bar(20, 110, 112, 109.5, 111)
    mk.set_bar(21, 111, 111.5, 108, 108.5)
    mk.set_bar(22, 108.5, 109, 106, 106.5)
    mk.set_bar(23, 106.5, 107.5, 106.2, 107)
    mk.set_bar(24, 107, 108.2, 106.8, 108)
    mk.set_bar(25, 108, 109.5, 107.9, 109.4)
    mk.set_bar(26, 109.4, 109.5, 108, 108.2)
    mk.set_bar(27, 108.2, 110, 108.1, 109.8)
    for k in range(28, n):
        mk.set_bar(k, 109.8, 109.9, 109.7, 109.8)
    mk.leg(piv("LOW", 100, 10), piv("HIGH", 112, 20), 22)
    return mk


def minute_store(start, n, price=100.0):
    st = MinuteStore(start, start + n * MIN)
    for i in range(n):
        st.set_minute(i, (price, price + 0.1, price - 0.1, price, 1.0, 0.0, 1, 0.0, 0.0))
    return st


def set_minute(st, u, o, h, l, c):
    st.set_minute(st.index(u), (o, h, l, c, 1.0, 0.0, 1, 0.0, 0.0))


def walk_bars(n, seed=3, price=100.0, start=T0):
    """Barre 45m complete a passeggiata casuale (per l'osservatore reale) e 1D aggregate da esse."""
    rng = random.Random(seed)
    bars = []
    for k in range(n):
        o = price
        c = max(1.0, o + rng.uniform(-1.5, 1.5))
        h, l = max(o, c) + rng.uniform(0, 0.8), max(0.5, min(o, c) - rng.uniform(0, 0.8))
        bars.append(Bar(start + k * BAR, start + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=o, h=h, l=l, c=c, v=rng.uniform(1, 5), q=1.0, trades=1, tb=0.0, tq=0.0))
        price = c
    return bars


def daily(bars45):
    out = []
    for j in range(len(bars45) // 32):
        seg = bars45[32 * j:32 * (j + 1)]
        out.append(Bar(seg[0].start, seg[-1].end, COMPLETE, 1440, 0, 0, o=seg[0].o, h=max(b.h for b in seg), l=min(b.l for b in seg), c=seg[-1].c,
                       v=sum(b.v for b in seg), q=1.0, trades=1, tb=0.0, tq=0.0))
    return out
