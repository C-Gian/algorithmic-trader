"""Costruttori sintetici per i test CAND-001 (prezzi inventati, non BTC)."""

from __future__ import annotations

from obs001.aggregate import COMPLETE, Bar
from obs001.minutes import MinuteStore

from cand001.config import load_candidate
from cand001.decision import DecisionEngine

CAND = load_candidate()
BAR = 45 * 60_000
DAY = 86_400_000
MIN = 60_000
T0 = 1_672_531_200_000  # 2023-01-01T00:00Z, solo origine sintetica


def m(v):
    return {"v": v, "r": None if v is not None else "INSUFFICIENT_HISTORY"}


def piv(kind, price, k):
    co = T0 + k * BAR
    return {"kind": kind, "price": price, "candidateOpen": co, "eventTime": co + BAR, "availableAt": co + 3 * BAR}


class Market:
    """Barre 45m, record osservativi minimi ed eventi costruiti a mano per il motore decisionale."""

    def __init__(self, n: int = 80, price: float = 104.0, a: float = 2.0, structure: str = "UP"):
        self.bars = [Bar(T0 + k * BAR, T0 + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=price, h=price + 0.2, l=price - 0.2, c=price, v=1.0)
                     for k in range(n)]
        self.recs = [self.rec(k, a, structure) for k in range(n)]
        self.events: list[dict] = []

    def rec(self, k, a, structure, anchors=None):
        b = self.bars[k]
        return {"status": "COMPLETE", "segment": {"id": 1, "bars": k + 1}, "C": b.c, "vol": {"A": m(a), "tr": m(1.0), "AoverC": m(0.01)},
                "piv": {"structure": m(structure)}, "fib": {"anchors": m(anchors), "version": 1, "u": None, "r": None},
                "avg": {"sma20": m(None), "sma50": m(None), "dist": m(None)}, "volu": {"ratio": m(None)}}

    def set_bar(self, k, o, h, l, c):
        self.bars[k] = Bar(T0 + k * BAR, T0 + (k + 1) * BAR, COMPLETE, 45, 0, 0, o=o, h=h, l=l, c=c, v=1.0)
        self.recs[k]["C"] = c

    def leg(self, p0, p1, available_k, action="APPEND"):
        """Rende disponibile la gamba P0->P1 alla chiusura della barra available_k (APPEND/REPLACE)."""
        t = T0 + (available_k + 1) * BAR
        for k in range(available_k, len(self.recs)):
            self.recs[k]["fib"]["anchors"] = m({"P0": p0, "P1": p1})
        self.events.append({"type": "FIB_SEQUENCE", "action": action, "availableAt": t, "eventTime": p1["eventTime"], "kind": p1["kind"]})
        return t

    def structure(self, k_from, value):
        for k in range(k_from, len(self.recs)):
            self.recs[k]["piv"]["structure"] = m(value)

    def engine(self, window=None):
        n = len(self.bars)
        recs1d = [{"piv": {"structure": m("DOWN")}} for _ in range(5)]
        return DecisionEngine(CAND, self.bars, self.recs, recs1d, self.events, T0, BAR, DAY, window or (T0, T0 + n * BAR))

    def t(self, k):
        return T0 + (k + 1) * BAR


def long_example(offset: int = 0):
    """Esempio LONG della sezione 13: P0=100 (barra 10), P1=112 (barra 20), A0=2, struttura UP.
    offset sposta l'esempio di altrettante barre (32 = un giorno, per avere un 1D chiuso)."""
    mk = Market(n=80 + offset)
    mk.set_bar(10 + offset, 101, 101.5, 100, 101)
    mk.set_bar(20 + offset, 110, 112, 109.5, 111)
    mk.set_bar(21 + offset, 111, 111.5, 108, 108.5)
    mk.set_bar(22 + offset, 108.5, 109, 106, 106.5)
    mk.set_bar(23 + offset, 106.5, 107.5, 106.2, 107)
    mk.set_bar(24 + offset, 107, 108.2, 106.8, 108)
    mk.leg(piv("LOW", 100, 10 + offset), piv("HIGH", 112, 20 + offset), 22 + offset)
    return mk


def short_example():
    mk = Market(price=108, structure="DOWN")
    mk.set_bar(10, 111, 112, 110.5, 111)
    mk.set_bar(20, 102, 102.5, 100, 101)
    mk.set_bar(21, 101, 104, 100.5, 103.5)
    mk.set_bar(22, 103.5, 106, 103, 105.5)
    mk.set_bar(23, 105.5, 105.8, 104.5, 105)
    mk.set_bar(24, 105, 105.2, 103.8, 104)
    mk.leg(piv("HIGH", 112, 10), piv("LOW", 100, 20), 22)
    return mk


def run_closes(engine, k_from, k_to, position=None, pending=False):
    out = []
    for k in range(k_from, k_to + 1):
        out.extend(engine.on_close(T0 + (k + 1) * BAR, position, pending))
    return out


def flat_store(start, end, price=100.0, spread=0.05):
    st = MinuteStore(start, end)
    for t in range(start, end, MIN):
        st.set_minute(st.index(t), (price, price + spread, price - spread, price, 1.0, 0.0, 1, 0.0, 0.0))
    return st


def set_minute(st, t, o, h, l, c):
    st.set_minute(st.index(t), (o, h, l, c, 1.0, 0.0, 1, 0.0, 0.0))


def trend_store(start, end, seed, store=None, price=100.0, from_t=None):
    """Minuti sintetici a tratti di tendenza (solo per test): deterministici dato il seed."""
    import random

    rng = random.Random(seed)
    st = store or MinuteStore(start, end)
    drift, left = 0.0, 0
    for t in range(from_t or start, end, MIN):
        if left <= 0:
            drift = rng.choice([-1, 1]) * rng.uniform(0.002, 0.012)
            left = rng.randint(200, 1500)
        left -= 1
        o = price
        c = max(1.0, o + drift + rng.gauss(0, 0.05))
        h = max(o, c) + abs(rng.gauss(0, 0.03))
        l = min(o, c) - abs(rng.gauss(0, 0.03))
        st.set_minute(st.index(t), (o, h, l, c, rng.uniform(1, 5), 0.0, 3, 0.0, 0.0))
        price = c
    return st
