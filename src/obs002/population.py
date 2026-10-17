"""Popolazione causale OBS-002/v1 (task §2) e snapshot congiunto all'origine (task §3).

Alla chiusura 45m t si leggono soltanto: record osservativi della barra che termina in t, eventi
FIB_SEQUENCE con availableAt == t, barre 45m terminate entro t e l'ultimo giorno concluso entro t.
Ordine a ogni chiusura: azzeramento di segmento, aggiornamenti (nuove versioni, ritiri), poi
tentativi. Nessun esito futuro entra qui: la popolazione e gli snapshot sono costruiti prima e
indipendentemente dal seguito (outcomes.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from obs001.aggregate import Bar
from obs001.observe import floor_day

SIDE = {1: "LONG", -1: "SHORT"}
WANT = {1: "UP", -1: "DOWN"}

# Esclusioni qualitative degli eventi APPEND/REPLACE
ANCHORS_MISSING = "ANCHORS_MISSING"
ANCHORS_NOT_ALTERNATING = "ANCHORS_NOT_ALTERNATING"
ANCHORS_DIFFERENT_SEGMENT = "ANCHORS_DIFFERENT_SEGMENT"
L_NOT_POSITIVE = "L_NOT_POSITIVE"
# Motivi di ritiro di una versione
NEW_VERSION_SAME_DIRECTION = "NEW_VERSION_SAME_DIRECTION"
SEGMENT_RESET = "SEGMENT_RESET"
END_OF_STUDY = "END_OF_STUDY"  # conclusione amministrativa, non un fallimento

PROFILES = ("CONCORDANT", "OPPOSITE", "DISCORDANT", "UNAVAILABLE")


def val(v):
    return {"v": v, "r": None}


def miss(reason: str | None):
    return {"v": None, "r": reason or "MISSING"}


def signed(m: dict, d: int) -> dict:
    """d * misura, conservando il motivo se manca."""
    return val(d * m["v"]) if m["v"] is not None else miss(m["r"])


def over_a(x: float, a: dict) -> dict:
    if a["v"] is None:
        return miss(a["r"])
    if a["v"] == 0:
        return miss("ZERO_DENOMINATOR")
    return val(x / a["v"])


def pivot(p: dict) -> dict:
    return {k: p[k] for k in ("kind", "price", "candidateOpen", "eventTime", "availableAt")}


@dataclass
class Version:
    id: str
    group_id: str
    d: int
    p0: dict
    p1: dict
    length: float
    t0: int
    i: int  # indice della barra 45m candela di P1
    segment: int
    action: str
    fib_version: int
    retired_at: int | None = None
    retire_reason: str | None = None
    retire_facts: dict = field(default_factory=dict)
    attempts: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"versionId": self.id, "groupId": self.group_id, "side": SIDE[self.d], "d": self.d, "P0": self.p0, "P1": self.p1,
                "L": self.length, "availableAt": self.t0, "action": self.action, "fibVersion": self.fib_version, "segment": self.segment,
                "activeFrom": self.t0, "retiredAt": self.retired_at, "retireReason": self.retire_reason, **self.retire_facts,
                "attempts": list(self.attempts)}


@dataclass
class Group:
    id: str
    d: int
    p0: dict
    first_available: int
    started_before_study: bool
    versions: list = field(default_factory=list)
    attempts: list = field(default_factory=list)  # [(t, attemptId)]
    last_k: int | None = None

    def as_dict(self) -> dict:
        return {"groupId": self.id, "side": SIDE[self.d], "P0": self.p0, "firstAvailableAt": self.first_available,
                "startedBeforeStudy": self.started_before_study, "versions": list(self.versions),
                "attempts": [a for _, a in self.attempts]}


class Population:
    def __init__(self, bars45: list[Bar], recs45: list[dict], recs1d: list[dict], events45: list[dict],
                 input_start: int, bar_ms: int, day_ms: int, study_start: int, end: int):
        self.bars, self.recs, self.recs1d = bars45, recs45, recs1d
        self.input_start, self.bar_ms, self.day_ms = input_start, bar_ms, day_ms
        self.study_start, self.end = study_start, end
        self.fib_at: dict[int, list[dict]] = {}
        for e in events45:
            if e["type"] == "FIB_SEQUENCE":
                self.fib_at.setdefault(e["availableAt"], []).append(e)
        self.active: dict[int, Version | None] = {1: None, -1: None}
        self.versions: list[Version] = []
        self.groups: dict[str, Group] = {}
        self.attempts: list[dict] = []
        self.events: list[dict] = []  # ogni FIB_SEQUENCE considerato, con esito (versione o esclusione)

    # ------------------------------------------------------------ utilità

    def k_of(self, open_ms: int) -> int:
        return (open_ms - self.input_start) // self.bar_ms

    def seg(self, k: int) -> int | None:
        r = self.recs[k]
        return r["segment"]["id"] if r["status"] == "COMPLETE" and r["segment"] else None

    def retire(self, v: Version, t: int, reason: str, **facts) -> None:
        v.retired_at, v.retire_reason, v.retire_facts = t, reason, facts
        if self.active[v.d] is v:
            self.active[v.d] = None

    # ------------------------------------------------------------ passo

    def run(self) -> "Population":
        for k, bar in enumerate(self.bars):
            if bar.end > self.end:
                break
            self.close(k, bar.end)
        for d in (1, -1):
            if self.active[d] is not None:
                self.retire(self.active[d], self.end, END_OF_STUDY)
        return self

    def close(self, k: int, t: int) -> None:
        seg = self.seg(k)
        for d in (1, -1):
            v = self.active[d]
            if v is not None and (seg is None or v.segment != seg):
                self.retire(v, t, SEGMENT_RESET)  # azzeramento: ritira entrambi i contesti
        for ev in self.fib_at.get(t, []):
            self.update(ev, k, t, seg)
        if t >= self.end:
            return
        for d in (1, -1):
            v = self.active[d]
            if v is not None and t >= v.t0:
                self.try_attempt(v, k, t)

    def update(self, ev: dict, k: int, t: int, seg: int | None) -> None:
        rec = {"t": t, "eventId": ev["id"], "action": ev["action"], "fibVersion": ev["version"]}
        self.events.append(rec)
        if ev["action"] not in ("APPEND", "REPLACE"):
            rec["outcome"] = "NO_VERSION"  # KEEP non crea versioni
            return
        anchors = ev.get("anchors")
        if not anchors or len(anchors) < 2:
            rec["outcome"] = ANCHORS_MISSING
            return
        p0, p1 = pivot(anchors[-2]), pivot(anchors[-1])
        kinds = (p0["kind"], p1["kind"])
        d = 1 if kinds == ("LOW", "HIGH") else -1 if kinds == ("HIGH", "LOW") else None
        if d is None:
            rec["outcome"] = ANCHORS_NOT_ALTERNATING
            return
        segs = {self.seg(self.k_of(p0["candidateOpen"])), self.seg(self.k_of(p1["candidateOpen"])), seg}
        if None in segs or len(segs) != 1:
            rec["outcome"] = ANCHORS_DIFFERENT_SEGMENT
            return
        length = d * (p1["price"] - p0["price"])
        rec["side"] = SIDE[d]
        if not length > 0:
            rec["outcome"] = L_NOT_POSITIVE
            return
        gid = f"GRP:{SIDE[d]}:{p0['candidateOpen']}"
        vid = f"VER:{SIDE[d]}:{p0['candidateOpen']}:{p1['candidateOpen']}:{t}"
        old = self.active[d]
        if old is not None:
            self.retire(old, t, NEW_VERSION_SAME_DIRECTION, replacedBy=vid, sameGroup=old.group_id == gid)
        g = self.groups.get(gid)
        if g is None:
            g = self.groups[gid] = Group(id=gid, d=d, p0=p0, first_available=t, started_before_study=t < self.study_start)
        v = Version(id=vid, group_id=gid, d=d, p0=p0, p1=p1, length=length, t0=t, i=self.k_of(p1["candidateOpen"]), segment=seg,
                    action=ev["action"], fib_version=ev["version"])
        g.versions.append(vid)
        self.versions.append(v)
        self.active[d] = v
        rec.update(outcome="VERSION", versionId=vid, groupId=gid)

    # ------------------------------------------------------- tentativo

    def try_attempt(self, v: Version, k: int, t: int) -> None:
        bars, d, i = self.bars, v.d, v.i
        if k <= i + 1:
            return
        if any(not bars[j].complete or self.seg(j) != v.segment for j in range(i, k + 1)):
            return  # non accade senza un azzeramento già registrato; difensivo
        g = self.groups[v.group_id]
        # Arretramento dopo il P1 della versione e, se il gruppo ha già un tentativo, riarmo dopo di esso:
        # entrambe le condizioni sono suffissi che finiscono in k, quindi basta il più corto.
        start = i if g.last_k is None else max(i, g.last_k)
        if not any(d * (bars[j].c - bars[j - 1].c) < 0 for j in range(start + 1, k + 1)):
            return
        bar, prev = bars[k], bars[k - 1]
        if not ((bar.c > prev.h and bar.c > bar.o) if d == 1 else (bar.c < prev.l and bar.c < bar.o)):
            return
        prior_init = sum(1 for tt, _ in g.attempts if tt < self.study_start)
        att = {
            "attemptId": f"ATT:{SIDE[d]}:{v.p0['candidateOpen']}:{t}", "groupId": g.id, "versionId": v.id, "ordinal": len(g.attempts) + 1,
            "priorAttemptsInInitialization": prior_init, "inStudy": self.study_start <= t < self.end,
            "side": SIDE[d], "d": d, "t": t, "C": bar.c,
            "version": {"P0": v.p0, "P1": v.p1, "L": v.length, "availableAt": v.t0, "action": v.action, "fibVersion": v.fib_version},
            "reaction": self.reaction(v, k, start, g.last_k),
            "trigger": {"open": bar.o, "close": bar.c, "prevHigh": prev.h, "prevLow": prev.l,
                        "beyondPrev": d * (bar.c - (prev.h if d == 1 else prev.l)), "body": d * (bar.c - bar.o)},
        }
        att["snapshot"] = snapshot(self.recs[k], self.rec1d_at(t), att, v)
        g.attempts.append((t, att["attemptId"]))
        g.last_k = k
        v.attempts.append(att["attemptId"])
        self.attempts.append(att)

    def reaction(self, v: Version, k: int, rearm_start: int, last_k: int | None) -> dict:
        bars, d, i = self.bars, v.d, v.i
        seg = bars[i + 1:k + 1]
        rext = min(b.l for b in seg) if d == 1 else max(b.h for b in seg)
        counter = sum(1 for j in range(i + 1, k + 1) if d * (bars[j].c - bars[j - 1].c) < 0)
        rearm = sum(1 for j in range(rearm_start + 1, k + 1) if d * (bars[j].c - bars[j - 1].c) < 0)
        beyond = any(b.h >= v.p1["price"] for b in seg) if d == 1 else any(b.l <= v.p1["price"] for b in seg)
        return {"Rext": rext, "depth": d * (v.p1["price"] - rext) / v.length, "barsSinceP1": k - i,
                "closesSinceAvailable": (bars[k].end - v.t0) // self.bar_ms, "counterClosesSinceP1": counter,
                "counterClosesSinceRearmStart": rearm, "previousAttemptClose": None if last_k is None else bars[last_k].end,
                "P1Retouched": beyond}

    def rec1d_at(self, t: int) -> dict | None:
        kd = (floor_day(t) - self.input_start) // self.day_ms - 1  # ultimo giorno concluso entro t
        return self.recs1d[kd] if 0 <= kd < len(self.recs1d) else None


# ------------------------------------------------------------------ snapshot


def joint_profile(rec: dict, d: int) -> dict:
    """Unica rappresentazione di confronto fissata (task §3): contesto descrittivo, non punteggio."""
    s, dist, slope = rec["piv"]["structure"], rec["avg"]["dist"], rec["avg"]["slope"]
    missing = [name for name, m in (("structure45m", s), ("smaOrder", dist), ("sma20Slope", slope)) if m["v"] is None]
    if missing:
        return {"profile": "UNAVAILABLE", "missing": missing, "reasons": [m["r"] for m in (s, dist, slope) if m["v"] is None]}
    dd, ds = d * dist["v"], d * slope["v"]
    if s["v"] == WANT[d] and dd > 0 and ds > 0:
        prof = "CONCORDANT"
    elif s["v"] == WANT[-d] and dd < 0 and ds < 0:
        prof = "OPPOSITE"
    else:
        prof = "DISCORDANT"
    return {"profile": prof, "structure45m": s["v"], "dSmaOrder": dd, "dSlope": ds}


def _nearest(levels: list[dict], sign: int) -> dict | None:
    cand = [lv for lv in levels if lv.get("raw") is not None and sign * lv["raw"] > 0]
    if not cand:
        return None
    best = min(cand, key=lambda lv: (abs(lv["raw"]), lv["kind"], lv["id"]))
    return {"kind": best["kind"], "id": best["id"], "price": best["price"], "dist": best["dist"]}


def snapshot(rec: dict, rec1d: dict | None, att: dict, v: Version) -> dict:
    d, c = att["d"], rec["C"]
    a = rec["vol"]["A"]
    levels = []
    for lv in rec["lvl"]:
        if lv.get("price") is None:
            levels.append({"kind": lv["kind"], "id": lv.get("id"), "price": None, "reason": lv.get("reason")})
            continue
        raw = d * (lv["price"] - c)
        levels.append({"kind": lv["kind"], "id": lv["id"], "price": lv["price"], "origin": lv.get("origin"), "availableAt": lv["availableAt"],
                       "raw": raw, "dist": over_a(raw, a), "position": "AHEAD" if raw > 0 else "BEHIND" if raw < 0 else "AT_C"})
    fib = rec["fib"]
    if fib["anchors"]["v"] is not None:
        an = fib["anchors"]["v"]
        fd = 1 if an["P0"]["kind"] == "LOW" else -1
        fib_out = {"version": fib["version"], "available": True, "anchors": {"P0": an["P0"], "P1": an["P1"]},
                   "relation": "CONCORDANT" if fd == d else "OPPOSITE",
                   "sameAsContext": an["P0"]["candidateOpen"] == v.p0["candidateOpen"] and an["P1"]["candidateOpen"] == v.p1["candidateOpen"],
                   "u": fib["u"], "r": fib["r"],
                   "levels": [{"type": typ, "ratio": x["ratio"], "price": x["price"], "dist": over_a(d * (x["price"] - c), a)}
                              for typ in ("retracements", "projections") for x in fib.get(typ, [])]}
    else:
        fib_out = {"version": fib["version"], "available": False, "reason": fib["anchors"]["r"]}
    cross = rec["avg"]["cross"]
    cross_rel = miss(cross["r"]) if cross["v"] is None else val(
        "NONE" if cross["v"] == "NONE" else "IN_DIRECTION" if cross["v"] == WANT[d] else "AGAINST")
    s1d = rec1d["piv"]["structure"] if rec1d else miss("INSUFFICIENT_HISTORY")
    rx = att["reaction"]
    return {
        "profile": joint_profile(rec, d),
        "structure": {"s45m": rec["piv"]["structure"], "s1D": s1d, "highs45m": rec["piv"]["highs"], "lows45m": rec["piv"]["lows"],
                      "highs1D": rec1d["piv"]["highs"] if rec1d else [], "lows1D": rec1d["piv"]["lows"] if rec1d else [],
                      "day1D": rec1d["open"] if rec1d else None},
        "levels": {"all": [{k: x for k, x in lv.items() if k != "raw"} for lv in levels], "nearestAhead": _nearest(levels, 1),
                   "nearestBehind": _nearest(levels, -1), "atC": [lv["kind"] for lv in levels if lv.get("raw") == 0]},
        "averages": {"sma20": rec["avg"]["sma20"], "sma50": rec["avg"]["sma50"], "dDist": signed(rec["avg"]["dist"], d),
                     "dSlope": signed(rec["avg"]["slope"], d), "dPos": signed(rec["avg"]["pos"], d), "cross": cross, "crossRelative": cross_rel},
        "volume": {"ratio": rec["volu"]["ratio"], "base": rec["volu"]["base"], "median": rec["volu"]["median"]},
        "volatility": {"A": a, "AoverC": rec["vol"]["AoverC"], "LoverA": over_a(v.length, a),
                       "toP1": over_a(d * (v.p1["price"] - c), a), "toRext": over_a(d * (rx["Rext"] - c), a)},
        "fibonacci": fib_out,
    }
