"""Motore decisionale CAND-001/v1 (sezioni 3-5 e 7 del protocollo).

Alla chiusura 45m t legge soltanto: record osservativi della barra che termina in t, eventi con
available_at == t, barre 45m terminate entro t e lo stato di occupazione/posizione corrente fornito
dal ledger (nessun minuto futuro, esito, funding o prezzo d'uscita). Produce stati reali del
candidato (NO_NEW_SETUP, WAIT_REACTION, WAIT_RESUMPTION, CALL, ABSTAIN, ...) e richieste per il
futuro (ingresso condizionato, uscita per struttura, aggiornamento protezione) con il loro ritardo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from obs001.aggregate import Bar

MS_MIN = 60_000

# Codici di astensione/terminazione (stabili, usati in ledger, report e app).
ABSTAIN_STRUCTURE = "ABSTAIN_STRUCTURE"
ABSTAIN_DURATION = "ABSTAIN_DURATION"
ABSTAIN_INCOMPLETE = "ABSTAIN_INCOMPLETE_INPUT"
ABSTAIN_VOLATILITY = "ABSTAIN_VOLATILITY_UNAVAILABLE"
ABSTAIN_AMPLITUDE = "ABSTAIN_AMPLITUDE"
ABSTAIN_REWARD_RISK = "ABSTAIN_REWARD_RISK"
SKIPPED_BUSY = "SKIPPED_BUSY"
INVALIDATED_DATA = "INVALIDATED_DATA"
INVALIDATED_STRUCTURE = "INVALIDATED_STRUCTURE"
INVALIDATED_DEPTH = "INVALIDATED_DEPTH"
INVALIDATED_TARGET_REACHED = "INVALIDATED_TARGET_REACHED"
EXPIRED = "EXPIRED"
NOT_EVALUATED_AFTER_GAP = "NOT_EVALUATED_AFTER_GAP"

REACTION_INVALIDATED = (INVALIDATED_STRUCTURE, INVALIDATED_DEPTH, INVALIDATED_TARGET_REACHED)


def pivot(p: dict) -> dict:
    return {k: p[k] for k in ("kind", "price", "candidateOpen", "eventTime", "availableAt")}


@dataclass
class Episode:
    id: str
    leg_id: str
    d: int
    p0: dict
    p1: dict
    a0: float
    length: float
    t0: int
    i: int  # indice della barra 45m candela di P1
    segment: int
    status: str = "WATCH_REACTION"
    states: list = field(default_factory=list)  # [{t, state, facts}]
    plan: dict | None = None
    call: dict | None = None
    termination: dict | None = None
    context0: dict | None = None

    @property
    def side(self) -> str:
        return "LONG" if self.d == 1 else "SHORT"


@dataclass
class PositionView:
    """Stato della posizione modellata noto al motore alla chiusura t (dal ledger, solo passato)."""

    episode_id: str
    d: int
    entry_time: int
    stop: float
    target: float
    a0: float


class DecisionEngine:
    def __init__(self, cand, bars45: list[Bar], recs45: list[dict], recs1d: list[dict], events45: list[dict],
                 input_start: int, bar_ms: int, day_ms: int, window: tuple[int, int]):
        self.p = cand.p
        self.s = cand.econ["baseline"]["slippage"]
        self.delay = self.p["actionDelaySeconds"] * 1000
        self.bars, self.recs, self.recs1d = bars45, recs45, recs1d
        self.input_start, self.bar_ms, self.day_ms = input_start, bar_ms, day_ms
        self.start, self.end = window
        self.events_at: dict[int, list[dict]] = {}
        for e in events45:
            self.events_at.setdefault(e["availableAt"], []).append(e)
        self.episode: Episode | None = None
        self.episodes: list[Episode] = []
        self.legs: list[dict] = []
        self.decisions: list[dict] = []
        self.last_termination = -math.inf
        self.halted_at: int | None = None

    # -------------------------------------------------------------- utilità

    def k_of(self, t: int) -> int:
        return (t - self.input_start) // self.bar_ms - 1

    def context(self, k: int, t: int) -> dict:
        """Fotografia delle sei famiglie a t (decisionali e contestuali), per spiegazione e ledger."""
        r = self.recs[k]
        kd = (t - t % self.day_ms - self.input_start) // self.day_ms - 1
        d1 = self.recs1d[kd] if 0 <= kd < len(self.recs1d) else None
        return {
            "t": t, "C": r["C"], "A": r["vol"]["A"], "structure45m": r["piv"]["structure"],
            "structure1D": d1["piv"]["structure"] if d1 else {"v": None, "r": "INSUFFICIENT_HISTORY"},
            "sma20": r["avg"]["sma20"], "sma50": r["avg"]["sma50"], "smaDist": r["avg"]["dist"],
            "volumeRatio": r["volu"]["ratio"], "fibVersion": r["fib"]["version"],
            "fibU": r["fib"].get("u"), "fibR": r["fib"].get("r"),
        }

    def new_leg(self, t: int, k: int) -> dict | None:
        """Gamba resa disponibile a t: APPEND o REPLACE della sequenza alternata con due estremi."""
        evs = [e for e in self.events_at.get(t, []) if e["type"] == "FIB_SEQUENCE" and e["action"] in ("APPEND", "REPLACE")]
        if not evs:
            return None
        anchors = self.recs[k]["fib"]["anchors"]
        if anchors["v"] is None:
            return None
        p0, p1 = anchors["v"]["P0"], anchors["v"]["P1"]
        d = 1 if (p0["kind"] == "LOW" and p1["kind"] == "HIGH") else -1
        return {"id": f"LEG:{'LONG' if d == 1 else 'SHORT'}:{p0['candidateOpen']}:{p1['candidateOpen']}", "t": t, "d": d,
                "action": evs[-1]["action"], "P0": pivot(p0), "P1": pivot(p1)}

    def record(self, t: int, state: str, episode: Episode | None = None, **facts) -> dict:
        rec = {"t": t, "state": state, "episodeId": episode.id if episode else None, **facts}
        self.decisions.append(rec)
        if episode is not None:
            episode.states.append({"t": t, "state": state, **facts})
        return rec

    # ------------------------------------------------------------ chiusura

    def on_close(self, t: int, position: PositionView | None, entry_pending: bool) -> list[dict]:
        """Decisione alla chiusura t. Restituisce richieste per il futuro (eseguite dal ledger)."""
        k = self.k_of(t)
        leg = self.new_leg(t, k)
        actions: list[dict] = []
        if self.halted_at is not None:
            self.record(t, NOT_EVALUATED_AFTER_GAP)
            if leg:
                self.legs.append({**leg, "outcome": NOT_EVALUATED_AFTER_GAP})
            return actions
        busy_reason = None
        if position is not None:
            actions.extend(self.manage(t, k, position))
            busy_reason = "posizione aperta"
        elif entry_pending:
            self.record(t, "ENTRY_PENDING", self.episode)
            busy_reason = "richiesta d'ingresso in attesa"
        elif self.episode is not None:
            actions.extend(self.evaluate(t, k, self.episode))
            busy_reason = "episodio in corso" if self.episode is not None else "episodio terminato a questa chiusura"
        elif self.last_termination >= t:
            busy_reason = "episodio terminato a questa chiusura"
        if leg is None:
            if busy_reason is None:
                self.record(t, "NO_NEW_SETUP")
            return actions
        if busy_reason is not None or t < self.start:
            self.legs.append({**leg, "outcome": SKIPPED_BUSY, "reason": busy_reason or "prima della finestra"})
            if busy_reason is not None:
                self.record(t, SKIPPED_BUSY, None, legId=leg["id"], reason=busy_reason)
            return actions
        actions.extend(self.recognize(t, k, leg))
        return actions

    # ------------------------------------------------------ riconoscimento

    def recognize(self, t: int, k: int, leg: dict) -> list[dict]:
        p, d = self.p, leg["d"]
        rec = self.recs[k]
        p0, p1 = leg["P0"], leg["P1"]
        length = d * (p1["price"] - p0["price"])
        reasons = []
        struct = rec["piv"]["structure"]["v"]
        if struct != ("UP" if d == 1 else "DOWN"):
            reasons.append(ABSTAIN_STRUCTURE)
        nbars = (p1["candidateOpen"] - p0["candidateOpen"]) // self.bar_ms
        if not (p["legMinBars"] <= nbars <= p["legMaxBars"]):
            reasons.append(ABSTAIN_DURATION)
        k0 = (p0["candidateOpen"] - self.input_start) // self.bar_ms
        if rec["status"] != "COMPLETE" or any(not self.bars[j].complete for j in range(k0, k + 1)):
            reasons.append(ABSTAIN_INCOMPLETE)
        a0 = rec["vol"]["A"]["v"]
        if a0 is None or a0 <= 0:
            reasons.append(ABSTAIN_VOLATILITY)
        elif not length >= p["legAmplitudeA"] * a0:
            reasons.append(ABSTAIN_AMPLITUDE)
        facts = {"legId": leg["id"], "side": "LONG" if d == 1 else "SHORT", "P0": p0, "P1": p1, "L": length, "A0": a0,
                 "legBars": nbars, "structure45m": struct}
        if reasons:
            self.legs.append({**leg, "outcome": reasons[0], "reasons": reasons, "L": length, "A0": a0, "legBars": nbars})
            self.record(t, "ABSTAIN", None, code=reasons[0], reasons=reasons, **facts)
            return []
        i = (p1["candidateOpen"] - self.input_start) // self.bar_ms
        ep = Episode(id=f"EP:{leg['id'][4:]}", leg_id=leg["id"], d=d, p0=p0, p1=p1, a0=a0, length=length, t0=t, i=i,
                     segment=rec["segment"]["id"], context0=self.context(k, t))
        self.legs.append({**leg, "outcome": "RECOGNIZED", "L": length, "A0": a0, "legBars": nbars, "episodeId": ep.id})
        self.episodes.append(ep)
        self.episode = ep
        self.record(t, "RECOGNIZED", ep, **facts)
        return self.evaluate(t, k, ep)

    # ---------------------------------------------- reazione e ripresa

    def reaction(self, ep: Episode, k: int) -> dict:
        bars = self.bars[ep.i + 1:k + 1]
        d = ep.d
        rext = min(b.l for b in bars) if d == 1 else max(b.h for b in bars)
        depth = d * (ep.p1["price"] - rext) / ep.length
        closes = [self.bars[j].c for j in range(ep.i, k + 1)]
        counter = sum(1 for j in range(1, len(closes)) if d * (closes[j] - closes[j - 1]) < 0)
        reached = any(b.h >= ep.p1["price"] for b in bars) if d == 1 else any(b.l <= ep.p1["price"] for b in bars)
        return {"Rext": rext, "depth": depth, "counterCloses": counter, "barsSinceP1": k - ep.i, "targetReached": reached}

    def terminate(self, ep: Episode, t: int, code: str, **facts) -> None:
        ep.status = code
        ep.termination = {"t": t, "code": code, **facts}
        self.record(t, code, ep, **facts)
        self.episode = None
        self.last_termination = t

    def evaluate(self, t: int, k: int, ep: Episode) -> list[dict]:
        p, d = self.p, ep.d
        rec = self.recs[k]
        # 1. input incompleto o nuova segmentazione
        if rec["status"] != "COMPLETE" or rec["segment"] is None or rec["segment"]["id"] != ep.segment or \
                any(not self.bars[j].complete for j in range(ep.i + 1, k + 1)):
            self.terminate(ep, t, INVALIDATED_DATA)
            return []
        r = self.reaction(ep, k)
        struct = rec["piv"]["structure"]["v"]
        c_k = self.bars[k].c
        if struct == ("DOWN" if d == 1 else "UP"):
            self.terminate(ep, t, INVALIDATED_STRUCTURE, structure45m=struct, **r)
            return []
        if r["depth"] > p["reactionDepthMax"] or d * (c_k - ep.p0["price"]) <= 0:
            self.terminate(ep, t, INVALIDATED_DEPTH, C=c_k, **r)
            return []
        if r["targetReached"]:
            self.terminate(ep, t, INVALIDATED_TARGET_REACHED, **r)
            return []
        if r["barsSinceP1"] > p["setupExpiryBars"]:
            self.terminate(ep, t, EXPIRED, **r)
            return []
        if r["depth"] < p["reactionDepthMin"] or r["counterCloses"] < p["reactionMinCounterCloses"]:
            ep.status = "WAIT_REACTION"
            self.record(t, "WAIT_REACTION", ep, **r)
            return []
        bar, prev = self.bars[k], self.bars[k - 1]
        trigger = t > ep.t0 and ((bar.c > prev.h and bar.c > bar.o) if d == 1 else (bar.c < prev.l and bar.c < bar.o))
        if not trigger:
            ep.status = "WAIT_RESUMPTION"
            self.record(t, "WAIT_RESUMPTION", ep, **r)
            return []
        return self.call(t, k, ep, r)

    def call(self, t: int, k: int, ep: Episode, r: dict) -> list[dict]:
        p, d, s = self.p, ep.d, self.s
        c_k = self.bars[k].c
        s0 = r["Rext"] - d * p["stopBufferA"] * ep.a0
        target = ep.p1["price"]
        e_star = c_k * (1 + d * s)
        risk, gain = d * (e_star - s0), d * (target - e_star)
        finite = all(math.isfinite(x) and x > 0 for x in (s0, target, e_star))
        ratio = gain / risk if risk > 0 else None
        plan = {"S0": s0, "T": target, "Estar": e_star, "risk": risk, "gain": gain, "ratio": ratio, "Ck": c_k,
                "Hprev": self.bars[k - 1].h, "Lprev": self.bars[k - 1].l, "Ok": self.bars[k].o, **r}
        ep.plan = plan
        if not (finite and risk > 0 and gain > 0 and ratio >= p["minRewardRisk"]):
            self.terminate(ep, t, ABSTAIN_REWARD_RISK, plan=plan)
            return []
        # Vincolo sulla quotazione d'ingresso (sezione 6): LONG E<=(T+1.5*S0)/2.5, SHORT E>=...
        bound = (target + p["minRewardRisk"] * s0) / (1 + p["minRewardRisk"])
        ep.call = {"t": t, "side": ep.side, "expectation": "tentativo di ritorno all'estremo P1 prima dell'invalidazione della reazione, entro 24h dall'eventuale ingresso",
                   "S0": s0, "T": target, "Estar": e_star, "entryBound": bound, "executeAt": t + self.delay,
                   "context": self.context(k, t)}
        ep.status = "CALL_REQUESTED"
        self.record(t, "CALL", ep, plan=plan, entryBound=bound, executeAt=t + self.delay)
        return [{"type": "ENTRY", "episodeId": ep.id, "d": d, "executeAt": t + self.delay, "S0": s0, "T": target,
                 "A0": ep.a0, "callTime": t}]

    # ----------------------------------------------------------- gestione

    def manage(self, t: int, k: int, pos: PositionView) -> list[dict]:
        d = pos.d
        rec = self.recs[k]
        ep = self.episode
        struct = rec["piv"]["structure"]["v"]
        if struct == ("DOWN" if d == 1 else "UP"):
            self.record(t, "EXIT_STRUCTURE_REQUESTED", ep, structure45m=struct, executeAt=t + self.delay)
            return [{"type": "EXIT", "reason": "EXIT_STRUCTURE", "executeAt": t + self.delay, "decidedAt": t}]
        want = "LOW" if d == 1 else "HIGH"
        actions = []
        for e in self.events_at.get(t, []):
            if e["type"] != "PIVOT_CONFIRMED" or e["kind"] != want:
                continue
            if e["candidateOpen"] < pos.entry_time:
                self.record(t, "PROTECTION_PIVOT_BEFORE_ENTRY", ep, pivot=e["price"], candidateOpen=e["candidateOpen"])
                continue
            s_new = e["price"] - d * self.p["stopBufferA"] * pos.a0
            c_t = rec["C"]
            checks = {"improves": d * (s_new - pos.stop) > 0, "belowClose": c_t is not None and d * (c_t - s_new) > 0,
                      "belowTarget": d * (pos.target - s_new) > 0, "positive": s_new > 0}
            facts = {"proposal": s_new, "current": pos.stop, "pivot": e["price"], "pivotCandidateOpen": e["candidateOpen"],
                     "pivotAvailableAt": e["availableAt"], "checks": checks}
            if all(checks.values()):
                self.record(t, "PROTECTION_UPDATE", ep, effectiveAt=t + self.delay, **facts)
                actions.append({"type": "STOP_UPDATE", "stop": s_new, "decidedAt": t, "effectiveAt": t + self.delay,
                                "pivot": e["price"], "pivotCandidateOpen": e["candidateOpen"], "previous": pos.stop})
            else:
                self.record(t, "PROTECTION_REJECTED", ep, **facts)
        if not actions:
            self.record(t, "HOLD", ep)
        return actions

    # ------------------------------------------------ notifiche dal ledger

    def entry_outcome(self, ep_id: str, u: int, outcome: str, **facts) -> None:
        ep = self.episode
        if ep is None or ep.id != ep_id:
            return
        if outcome == "FILLED":
            ep.status = "OPEN"
            self.record(u, "FILLED", ep, **facts)
        else:
            self.terminate(ep, u, outcome, **facts)

    def position_closed(self, ep_id: str, at: int, reason: str, **facts) -> None:
        ep = self.episode
        if ep is not None and ep.id == ep_id:
            self.terminate(ep, at, "CLOSED", exitReason=reason, **facts)

    def halt(self, at: int) -> None:
        self.halted_at = at
        if self.episode is not None:
            self.terminate(self.episode, at, "UNRESOLVED_DATA_GAP")
