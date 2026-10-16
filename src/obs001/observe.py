"""Osservatore causale OBS-001/v1, applicato indipendentemente a 45m e 1D.

Elabora le barre in ordine e, alla chiusura di ciascuna, produce un record immutabile che usa
soltanto barre terminate entro quella chiusura. Gli eventi (pivot, scarti, versioni Fibonacci,
attraversamenti, incroci, azzeramenti per lacuna) portano event_time e available_at.
Ogni misura è {"v": valore, "r": None} oppure {"v": None, "r": motivo}: uno zero noto resta zero.
"""

from __future__ import annotations

import math
from collections import deque

from .aggregate import Bar
from .conventions import DAY_MS, Conventions

INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
ZERO_DENOMINATOR = "ZERO_DENOMINATOR"
NO_CONFIRMED_PIVOTS = "NO_CONFIRMED_PIVOTS"
ANCHORS_EQUAL = "ANCHORS_EQUAL"

SYMBOL = "BTCUSDT"


def val(v):
    return {"v": v, "r": None}


def miss(reason: str):
    return {"v": None, "r": reason}


def mean(xs) -> float:
    return math.fsum(xs) / len(xs)


def median(xs) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def floor_day(t: int) -> int:
    return t - t % DAY_MS


def _ratio(num: float, den: dict) -> dict:
    """num / A dove A è una misura: A assente propaga il motivo, A=0 è ZERO_DENOMINATOR."""
    if den["v"] is None:
        return miss(den["r"])
    if den["v"] == 0:
        return miss(ZERO_DENOMINATOR)
    return val(num / den["v"])


def _pivot_ref(p: dict | None) -> dict | None:
    if p is None:
        return None
    return {k: p[k] for k in ("kind", "price", "candidateOpen", "eventTime", "availableAt")}


class ScaleObserver:
    def __init__(self, scale: str, conv: Conventions):
        self.scale = scale
        av = conv.section("averages")
        self.n_tr = conv.section("volatility")["trWindow"]
        self.fast, self.slow, self.lag = av["fast"], av["slow"], av["slopeLag"]
        self.vol_window = conv.section("volume")["medianWindow"]
        pv = conv.section("pivots")
        self.left, self.right = pv["left"], pv["right"]
        fib = conv.section("fibonacci")
        self.retr, self.proj = fib["retracements"], fib["projections"]
        self.keep = max(self.slow, self.lag + self.fast, self.vol_window + 1, self.left + self.right + 1) + 1
        self.events: list[dict] = []
        self.fib_version = 0
        self.segment = 0
        self._reset()

    # ------------------------------------------------------------------ stato

    def _reset(self) -> None:
        self.bars: deque[Bar] = deque(maxlen=self.keep)
        self.seg_len = 0
        self.trs: deque[float] = deque(maxlen=self.n_tr)
        self.sma_fast_hist: deque[float] = deque(maxlen=self.lag + 1)
        self.prev_dist: dict | None = None
        self.highs: list[dict] = []
        self.lows: list[dict] = []
        self.fib_seq: list[dict] = []
        self.prev_close: float | None = None
        self.prev_levels: list[dict] = []

    def _event(self, etype: str, event_time: int, available_at: int, **data) -> dict:
        key = data.get("kind") or data.get("levelId") or data.get("direction") or ""
        ev = {
            "id": f"{SYMBOL}:{self.scale}:{etype}:{event_time}:{key}",
            "scale": self.scale, "type": etype, "eventTime": event_time, "availableAt": available_at, **data,
        }
        self.events.append(ev)
        return ev

    # ------------------------------------------------------------------ passo

    def step(self, bar: Bar, prev_day: Bar | None) -> dict:
        rec = {
            "id": f"{SYMBOL}:{self.scale}:{bar.end}",
            "open": bar.start, "end": bar.end, "availableAt": bar.end,
            "status": bar.status,
            "inputRef": {"minutes": [bar.start, bar.end], "valid": bar.valid, "missing": bar.missing, "invalid": bar.invalid},
        }
        if not bar.complete:
            return self._incomplete(rec, bar, prev_day)

        if self.seg_len == 0:
            self.segment += 1
        self.bars.append(bar)
        self.seg_len += 1
        rec["segment"] = {"id": self.segment, "bars": self.seg_len}
        rec["C"] = bar.c
        closes = [b.c for b in self.bars]

        # 5.1 Volatilità
        if self.seg_len >= 2:
            prev = self.bars[-2]
            tr = max(bar.h - bar.l, abs(bar.h - prev.c), abs(bar.l - prev.c))
            self.trs.append(tr)
            tr_m = val(tr)
        else:
            tr_m = miss(INSUFFICIENT_HISTORY)
        a_m = val(mean(self.trs)) if self.seg_len >= self.n_tr + 1 else miss(INSUFFICIENT_HISTORY)
        rec["vol"] = {"tr": tr_m, "A": a_m, "AoverC": val(a_m["v"] / bar.c) if a_m["v"] is not None else miss(a_m["r"])}

        # 5.2 Medie
        sma_f = val(mean(closes[-self.fast:])) if self.seg_len >= self.fast else miss(INSUFFICIENT_HISTORY)
        sma_s = val(mean(closes[-self.slow:])) if self.seg_len >= self.slow else miss(INSUFFICIENT_HISTORY)
        if sma_f["v"] is not None:
            self.sma_fast_hist.append(sma_f["v"])
        dist = _ratio(sma_f["v"] - sma_s["v"], a_m) if self.seg_len >= self.slow else miss(INSUFFICIENT_HISTORY)
        if self.seg_len >= self.fast + self.lag:
            slope = _ratio(sma_f["v"] - self.sma_fast_hist[-1 - self.lag], a_m)
        else:
            slope = miss(INSUFFICIENT_HISTORY)
        pos = _ratio(bar.c - sma_f["v"], a_m) if self.seg_len >= self.n_tr + 1 and sma_f["v"] is not None else miss(INSUFFICIENT_HISTORY)
        if self.seg_len < self.slow + 1:
            cross = miss(INSUFFICIENT_HISTORY)
        elif dist["v"] is None or self.prev_dist is None or self.prev_dist["v"] is None:
            cross = miss(dist["r"] or (self.prev_dist or {}).get("r") or INSUFFICIENT_HISTORY)
        else:
            p, c = self.prev_dist["v"], dist["v"]
            direction = "UP" if p <= 0 < c else "DOWN" if p >= 0 > c else "NONE"
            cross = val(direction)
            if direction != "NONE":
                self._event("SMA_CROSS", bar.end, bar.end, direction=direction, previous=p, current=c)
        self.prev_dist = dist
        rec["avg"] = {"sma20": sma_f, "sma50": sma_s, "dist": dist, "slope": slope, "pos": pos, "cross": cross}

        # 5.5 Volume
        if self.seg_len >= self.vol_window + 1:
            med = median([b.v for b in list(self.bars)[-self.vol_window - 1:-1]])
            ratio = miss(ZERO_DENOMINATOR) if med == 0 else val(bar.v / med)
            med_m = val(med)
        else:
            ratio = med_m = miss(INSUFFICIENT_HISTORY)
        rec["volu"] = {"base": bar.v, "quote": bar.q, "trades": bar.trades, "takerBase": bar.tb, "takerQuote": bar.tq, "median": med_m, "ratio": ratio}

        # 5.3 Pivot (candidata = barra i-2, conferma alla chiusura di i)
        rec["piv"] = {"check": self._pivots(bar)}
        rec["piv"].update(self._structure())

        # 5.6 Fibonacci (dopo l'eventuale nuovo pivot, disponibile a questa chiusura)
        rec["fib"] = self._fibonacci(bar.c, a_m)

        # 5.4 Livelli e attraversamenti
        levels = self._levels(bar, prev_day, a_m)
        rec["lvl"] = levels
        rec["crossings"] = self._crossings(bar, a_m)
        self.prev_close = bar.c
        self.prev_levels = [lv for lv in levels if lv.get("price") is not None]
        return rec

    def _incomplete(self, rec: dict, bar: Bar, prev_day: Bar | None) -> dict:
        if self.seg_len > 0:
            self._event(
                "SEGMENT_RESET", bar.end, bar.end, reason=INCOMPLETE_INPUT,
                segment=self.segment, segmentBars=self.seg_len, valid=bar.valid, missing=bar.missing, invalid=bar.invalid,
            )
        self._reset()
        m = miss(INCOMPLETE_INPUT)
        rec["segment"] = None
        rec["C"] = None
        rec["vol"] = {"tr": m, "A": m, "AoverC": m}
        rec["avg"] = {k: m for k in ("sma20", "sma50", "dist", "slope", "pos", "cross")}
        rec["volu"] = {"base": None, "quote": None, "trades": None, "takerBase": None, "takerQuote": None, "median": m, "ratio": m}
        rec["piv"] = {"check": m, "structure": m, "highs": [], "lows": []}
        rec["fib"] = {"version": self.fib_version, "anchors": m}
        rec["lvl"] = self._levels(None, prev_day, m)
        rec["crossings"] = []
        return rec

    # ------------------------------------------------------------------ pivot

    def _pivots(self, bar: Bar) -> dict:
        width = self.left + self.right + 1
        if self.seg_len < width:
            return miss(INSUFFICIENT_HISTORY)
        window = list(self.bars)[-width:]
        cand = window[self.left]
        others = window[: self.left] + window[self.left + 1:]

        def status(value, neighbours, higher: bool) -> str:
            if higher:
                if all(value > x for x in neighbours):
                    return "PIVOT"
                return "TIE" if all(value >= x for x in neighbours) else "NOT_EXTREME"
            if all(value < x for x in neighbours):
                return "PIVOT"
            return "TIE" if all(value <= x for x in neighbours) else "NOT_EXTREME"

        hs = status(cand.h, [b.h for b in others], True)
        ls = status(cand.l, [b.l for b in others], False)
        base = {"candidateOpen": cand.start, "eventTime": cand.end, "availableAt": bar.end}
        if hs == "PIVOT" and ls == "PIVOT":
            self._event("PIVOT_DUAL_AMBIGUOUS", cand.end, bar.end, kind="DUAL", candidateOpen=cand.start, high=cand.h, low=cand.l)
            return val({**base, "high": "DUAL_AMBIGUOUS", "low": "DUAL_AMBIGUOUS"})
        for kind, st, price in (("HIGH", hs, cand.h), ("LOW", ls, cand.l)):
            if st == "TIE":
                self._event("PIVOT_REJECTED", cand.end, bar.end, kind=kind, reason="TIE", candidateOpen=cand.start, price=price)
            elif st == "PIVOT":
                pivot = {
                    "id": f"{SYMBOL}:{self.scale}:PIVOT_{kind}:{cand.start}", "kind": kind, "price": price,
                    "candidateOpen": cand.start, "eventTime": cand.end, "availableAt": bar.end,
                }
                self._event("PIVOT_CONFIRMED", cand.end, bar.end, kind=kind, price=price, candidateOpen=cand.start, pivotId=pivot["id"])
                (self.highs if kind == "HIGH" else self.lows).append(pivot)
                del (self.highs if kind == "HIGH" else self.lows)[:-2]
                self._fib_update(pivot)
        return val({**base, "high": hs, "low": ls})

    def _structure(self) -> dict:
        highs, lows = self.highs[-2:], self.lows[-2:]
        out = {"highs": [_pivot_ref(p) for p in highs], "lows": [_pivot_ref(p) for p in lows]}
        if len(highs) < 2 or len(lows) < 2:
            out["structure"] = miss(NO_CONFIRMED_PIVOTS)
            return out
        hu, hd = highs[1]["price"] > highs[0]["price"], highs[1]["price"] < highs[0]["price"]
        lu, ld = lows[1]["price"] > lows[0]["price"], lows[1]["price"] < lows[0]["price"]
        out["structure"] = val("UP" if hu and lu else "DOWN" if hd and ld else "MIXED")
        return out

    # -------------------------------------------------------------- Fibonacci

    def _fib_update(self, pivot: dict) -> None:
        seq = self.fib_seq
        if seq and seq[-1]["kind"] == pivot["kind"]:
            last = seq[-1]
            more = pivot["price"] > last["price"] if pivot["kind"] == "HIGH" else pivot["price"] < last["price"]
            if not more:
                self._event("FIB_SEQUENCE", pivot["eventTime"], pivot["availableAt"], kind=pivot["kind"], action="KEEP",
                            version=self.fib_version, kept=_pivot_ref(last), ignored=_pivot_ref(pivot))
                return
            seq[-1] = pivot
            action, before = "REPLACE", _pivot_ref(last)
        else:
            seq.append(pivot)
            action, before = "APPEND", None
        del seq[:-2]
        self.fib_version += 1
        self._event("FIB_SEQUENCE", pivot["eventTime"], pivot["availableAt"], kind=pivot["kind"], action=action,
                    version=self.fib_version, before=before, after=_pivot_ref(pivot),
                    anchors=[_pivot_ref(p) for p in seq[-2:]] if len(seq) >= 2 else None)

    def _fibonacci(self, close: float, a_m: dict) -> dict:
        seq = self.fib_seq
        if len(seq) < 2:
            return {"version": self.fib_version, "anchors": miss(NO_CONFIRMED_PIVOTS)}
        p0, p1 = seq[-2], seq[-1]
        out = {"version": self.fib_version, "anchors": val({"P0": _pivot_ref(p0), "P1": _pivot_ref(p1)})}
        span = p1["price"] - p0["price"]
        if span == 0:
            out["anchors"] = miss(ANCHORS_EQUAL)
            return out
        u = (close - p0["price"]) / span
        out["u"], out["r"] = u, 1 - u
        out["retracements"] = [
            {"ratio": r, "price": (price := p1["price"] - r * span), "dist": _ratio(close - price, a_m)} for r in self.retr
        ]
        out["projections"] = [
            {"ratio": k, "price": (price := p0["price"] + k * span), "dist": _ratio(close - price, a_m)} for k in self.proj
        ]
        return out

    # ---------------------------------------------------------------- livelli

    def _levels(self, bar: Bar | None, prev_day: Bar | None, a_m: dict) -> list[dict]:
        close = bar.c if bar is not None else None

        def dist(price):
            return _ratio(close - price, a_m) if close is not None else miss(INCOMPLETE_INPUT)

        out = []
        for kind, pivots in (("PIVOT_HIGH", self.highs), ("PIVOT_LOW", self.lows)):
            if pivots:
                p = pivots[-1]
                out.append({"id": p["id"], "kind": kind, "price": p["price"], "origin": p["candidateOpen"],
                            "eventTime": p["eventTime"], "availableAt": p["availableAt"], "dist": dist(p["price"])})
            else:
                out.append({"id": None, "kind": kind, "price": None, "reason": NO_CONFIRMED_PIVOTS if bar else INCOMPLETE_INPUT})
        for kind in ("DAY_HIGH", "DAY_LOW"):
            if prev_day is None:
                out.append({"id": None, "kind": kind, "price": None, "reason": INSUFFICIENT_HISTORY})
            elif not prev_day.complete:
                out.append({"id": None, "kind": kind, "price": None, "reason": INCOMPLETE_INPUT, "origin": prev_day.start})
            else:
                price = prev_day.h if kind == "DAY_HIGH" else prev_day.l
                out.append({"id": f"{SYMBOL}:1D:{kind}:{prev_day.start}", "kind": kind, "price": price, "origin": prev_day.start,
                            "eventTime": prev_day.end, "availableAt": prev_day.end, "dist": dist(price)})
        return out

    def _crossings(self, bar: Bar, a_m: dict) -> list[dict]:
        if self.prev_close is None:
            return []
        out = []
        cp, c = self.prev_close, bar.c
        for lv in self.prev_levels:
            price = lv["price"]
            direction = "UP" if cp <= price < c else "DOWN" if cp >= price > c else None
            if direction:
                ev = self._event("LEVEL_CROSS", bar.end, bar.end, levelId=lv["id"], levelKind=lv["kind"], price=price,
                                 direction=direction, previousClose=cp, close=c, A=a_m["v"], AReason=a_m["r"])
                out.append({"levelId": lv["id"], "levelKind": lv["kind"], "price": price, "direction": direction, "eventId": ev["id"]})
        return out


def observe(bars45: list[Bar], bars1d: list[Bar], conv: Conventions) -> dict:
    """Elabora sequenzialmente entrambe le scale. Il giorno precedente di una chiusura t è
    il giorno UTC [floor(t)-1g, floor(t)): a mezzanotte è quello appena terminato."""
    daily_by_end = {b.end: b for b in bars1d}
    o45, o1d = ScaleObserver("45m", conv), ScaleObserver("1D", conv)
    rec45 = [o45.step(b, daily_by_end.get(floor_day(b.end))) for b in bars45]
    rec1d = [o1d.step(b, daily_by_end.get(floor_day(b.end))) for b in bars1d]
    return {"45m": rec45, "1D": rec1d, "events": {"45m": o45.events, "1D": o1d.events}}


def snapshot_at(result: dict, conv: Conventions, t: int) -> dict:
    """Snapshot causale alla chiusura 45m t: record della barra 45m che termina in t, record
    dell'ultimo giorno terminato entro t ed eventi con available_at <= t."""
    k45 = (t - conv.input_start) // conv.bar_ms - 1
    kd = (floor_day(t) - conv.input_start) // conv.day_ms - 1
    rec45 = result["45m"][k45] if 0 <= k45 < len(result["45m"]) else None
    rec1d = result["1D"][kd] if 0 <= kd < len(result["1D"]) else None
    if rec45 is not None and rec45["end"] != t:
        raise ValueError("t non è una chiusura 45m della griglia")
    return {
        "t": t, "45m": rec45, "1D": rec1d,
        "events": {s: [e for e in result["events"][s] if e["availableAt"] <= t] for s in ("45m", "1D")},
    }
