"""Ledger di esecuzione modellata e costi CAND-001/v1 (sezioni 6, 8, 9, 11 del protocollo).

Processa i minuti negoziati 1m in ordine, solo mentre esistono posizione o richieste. Precedenze
all'apertura u: (1) funding (contabilizzato a posteriori con la regola di detenzione), (2) gap oltre
stop/target, (3) uscite dovute, (4) attivazione stop aggiornato, (5) ingresso condizionato; poi
contatti intraminuto con STOP_FIRST. Le uscite intrabar si concludono a u+60s.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

from obs001.minutes import VALID, MinuteStore

MS_MIN = 60_000


@dataclass
class Position:
    id: str
    episode_id: str
    d: int
    entry_time: int
    eref: float
    e: float
    q: float
    s0: float
    t: float
    a0: float
    r0: float
    g0: float
    call_time: int
    stop: float
    stops: list = field(default_factory=list)
    pending_stop: dict | None = None
    pending_exit: dict | None = None

    @property
    def time_exit(self) -> int:
        return self.entry_time + 24 * 3_600_000


class Ledger:
    def __init__(self, cand, store: MinuteStore, window: tuple[int, int], funding: list[dict], mark: dict[int, float]):
        self.cand = cand
        self.econ = cand.econ
        self.f = self.econ["baseline"]["fee"]
        self.s = self.econ["baseline"]["slippage"]
        self.n0 = self.econ["notionalUSDT"]
        self.min_rr = cand.p["minRewardRisk"]
        self.store = store
        self.start, self.end = window
        self.funding = sorted(funding, key=lambda x: x["tau"])
        self.funding_taus = [x["tau"] for x in self.funding]
        self.mark = mark  # minuto u -> close mark del minuto [u-60s, u)
        self.position: Position | None = None
        self.pending_entry: dict | None = None
        self.trades: list[dict] = []
        self.requests: list[dict] = []
        self.cursor = self.start
        self.halted: dict | None = None
        self.realized = 0.0  # somma netti modellati (baseline) delle operazioni chiuse; None se un netto manca
        self.realized_missing = False
        self.curve: list[tuple[int, float]] = [(self.start, 0.0)]
        self.notices: list[tuple[str, str, int, str, dict]] = []  # notifiche per il motore: (tipo, episodio, tempo, esito, fatti)

    # --------------------------------------------------------------- richieste

    def accept(self, actions: list[dict]) -> None:
        for a in actions:
            if a["type"] == "ENTRY":
                self.pending_entry = a
            elif a["type"] == "EXIT" and self.position is not None:
                self.position.pending_exit = a
            elif a["type"] == "STOP_UPDATE" and self.position is not None:
                self.position.pending_stop = a

    def busy(self) -> bool:
        return self.position is not None or self.pending_entry is not None

    # ----------------------------------------------------------------- minuti

    def advance(self, until: int) -> None:
        """Processa i minuti [cursor, until) necessari: solo con posizione o richieste attive."""
        while self.cursor < until and self.halted is None:
            if not self.busy():
                self.cursor = until
                break
            self.minute(self.cursor)
            self.cursor += MS_MIN

    def minute(self, u: int) -> None:
        st = self.store
        i = st.index(u)
        valid = 0 <= i < st.n and st.status[i] == VALID
        pos = self.position
        last = u == self.end - MS_MIN
        if pos is not None:
            if not valid:
                self.halt(u, "minuto negoziato assente mentre la posizione è aperta")
                return
            o = st.o[i]
            d = pos.d
            if d * (o - pos.stop) <= 0:
                self.close(u, "STOP", o, u, gap=True)
            elif d * (o - pos.t) >= 0:
                self.close(u, "TARGET", o, u, gap=True)
            else:
                due = []
                if pos.pending_exit and pos.pending_exit["executeAt"] <= u:
                    due.append(pos.pending_exit["reason"])
                if u >= pos.time_exit:
                    due.append("TIME_EXIT")
                if last:
                    due.append("END_OF_SEGMENT")
                if due:
                    self.close(u, due[0], o, u, due=due)
                elif pos.pending_stop and pos.pending_stop["effectiveAt"] <= u:
                    upd = pos.pending_stop
                    pos.pending_stop = None
                    pos.stops.append({"decidedAt": upd["decidedAt"], "effectiveAt": u, "from": pos.stop, "to": upd["stop"],
                                      "pivot": upd["pivot"], "pivotCandidateOpen": upd["pivotCandidateOpen"]})
                    pos.stop = upd["stop"]
                    if d * (o - pos.stop) <= 0:
                        self.close(u, "STOP", o, u, gap=True, at_activation=True)
        if self.position is None and self.pending_entry and self.pending_entry["executeAt"] <= u:
            self.try_entry(u, valid, last)
        pos = self.position
        if pos is not None:
            h, l = st.h[i], st.l[i]
            d = pos.d
            stop_hit = l <= pos.stop if d == 1 else h >= pos.stop
            target_hit = h >= pos.t if d == 1 else l <= pos.t
            if stop_hit and target_hit:
                self.close(u, "STOP", pos.stop, u + MS_MIN, intrabar=True, both=True)
            elif stop_hit:
                self.close(u, "STOP", pos.stop, u + MS_MIN, intrabar=True)
            elif target_hit:
                self.close(u, "TARGET", pos.t, u + MS_MIN, intrabar=True)
            else:
                self.mark_to_market(u + MS_MIN, st.c[i])

    # --------------------------------------------------------------- ingresso

    def try_entry(self, u: int, valid: bool, last: bool) -> None:
        req = self.pending_entry
        self.pending_entry = None
        d, s0, t = req["d"], req["S0"], req["T"]
        base = {"episodeId": req["episodeId"], "callTime": req["callTime"], "executeAt": u, "side": "LONG" if d == 1 else "SHORT",
                "S0": s0, "T": t}
        if u >= self.end - MS_MIN or last:
            outcome, facts = "CANCELLED_END_OF_WINDOW", {}
        elif not valid:
            outcome, facts = "CANCELLED_NO_QUOTE", {}
        else:
            o = self.store.o[self.store.index(u)]
            e = o * (1 + d * self.s)
            r0, g0 = d * (e - s0), d * (t - e)
            ratio = g0 / r0 if r0 > 0 else None
            facts = {"Oref": o, "E": e, "R0": r0, "G0": g0, "ratio": ratio}
            if r0 > 0 and g0 > 0 and ratio >= self.min_rr and math.isfinite(e):
                q = self.n0 / e
                self.position = Position(id=f"TR:{req['episodeId'][3:]}", episode_id=req["episodeId"], d=d, entry_time=u, eref=o, e=e,
                                         q=q, s0=s0, t=t, a0=req["A0"], r0=r0, g0=g0, call_time=req["callTime"], stop=s0)
                outcome = "FILLED"
                facts["q"] = q
            else:
                outcome = "REJECTED_PRICE"
        self.requests.append({**base, "outcome": outcome, **facts})
        self.notices.append(("ENTRY", req["episodeId"], u, outcome, facts))

    # ----------------------------------------------------------------- uscita

    def close(self, u: int, reason: str, ref: float, acct: int, gap: bool = False, intrabar: bool = False, both: bool = False,
              due: list | None = None, at_activation: bool = False) -> None:
        pos = self.position
        self.position = None
        d, q = pos.d, pos.q
        x = ref * (1 - d * self.s)
        trade = {
            "id": pos.id, "episodeId": pos.episode_id, "side": "LONG" if d == 1 else "SHORT", "d": d, "callTime": pos.call_time,
            "entryTime": pos.entry_time, "Eref": pos.eref, "E": pos.e, "q": q, "N0": self.n0, "S0": pos.s0, "T": pos.t, "A0": pos.a0,
            "R0": pos.r0, "G0": pos.g0, "stops": pos.stops, "finalStop": pos.stop,
            "exit": {"reason": reason, "minute": u, "accountingTime": acct, "interval": [u, u + MS_MIN] if intrabar else None,
                     "Xref": ref, "X": x, "gap": gap, "intrabar": intrabar, "bothTouched": both, "due": due or [],
                     "atStopActivation": at_activation},
        }
        trade.update(self.economics(trade, self.f, self.s, x))
        if both:
            xa = pos.t * (1 - d * self.s)
            alt = self.economics(trade, self.f, self.s, xa)
            trade["targetFirst"] = {"Xref": pos.t, "X": xa, "pricePnL": alt["pricePnL"], "net": alt["net"],
                                    "delta": None if alt["net"] is None or trade["net"] is None else alt["net"] - trade["net"]}
        fs, ss = self.econ["stress"]["fee"], self.econ["stress"]["slippage"]
        stress = self.economics(trade, fs, ss, ref * (1 - d * ss), entry_fill=pos.eref * (1 + d * ss))
        trade["stress"] = {"fee": fs, "slippage": ss, **{k: stress[k] for k in ("pricePnL", "feeEntry", "feeExit", "net")}}
        trade["durationMin"] = (acct - pos.entry_time) / MS_MIN
        trade["riskInitial"] = q * pos.r0
        trade["netBps"] = None if trade["net"] is None else trade["net"] / self.n0 * 10_000
        trade["netOverRisk"] = None if trade["net"] is None or trade["riskInitial"] <= 0 else trade["net"] / trade["riskInitial"]
        self.trades.append(trade)
        if trade["net"] is None:
            self.realized_missing = True
        else:
            self.realized += trade["net"]
        self.curve.append((acct, None if self.realized_missing else self.realized))
        self.pending_entry = None
        self.notices.append(("CLOSE", pos.episode_id, acct, reason, {"tradeId": pos.id}))

    def economics(self, trade: dict, f: float, s: float, x: float, entry_fill: float | None = None) -> dict:
        d, q = trade["d"], trade["q"]
        e = trade["E"] if entry_fill is None else entry_fill
        price_pnl = d * q * (x - e)
        ref_pnl = d * q * (trade["exit"]["Xref"] - trade["Eref"]) if "exit" in trade else None
        fee_in, fee_out = f * q * e, f * q * x
        fund = self.funding_for(trade)
        net = None if fund["total"] is None else price_pnl - fee_in - fee_out + fund["total"]
        return {"pricePnL": price_pnl, "pricePnLRef": ref_pnl, "slippageCost": None if ref_pnl is None else price_pnl - ref_pnl,
                "feeEntry": fee_in, "feeExit": fee_out, "funding": fund, "net": net,
                "netRange": None if net is None else [net + fund["ambiguityLow"], net + fund["ambiguityHigh"]]}

    # ---------------------------------------------------------------- funding

    def funding_for(self, trade: dict) -> dict:
        """Cashflow di funding con regola entryTime < tau <= exitAccountingTime e proxy mark1m.
        Eventi entro 60s da ingresso/uscita, o nel minuto di un'uscita intrabar: ambigui, con intervallo."""
        entry = trade["entryTime"]
        ex = trade.get("exit")
        acct = ex["accountingTime"] if ex else trade["gap"]["at"]  # percorso irrisolto: solo fino alla lacuna
        d, q = trade["d"], trade["q"]
        intrabar_minute = ex["minute"] if ex and ex["intrabar"] else None
        lo = bisect.bisect_left(self.funding_taus, entry - MS_MIN)
        hi = bisect.bisect_right(self.funding_taus, acct + MS_MIN)
        events, total, low, high, missing, range_incomplete = [], 0.0, 0.0, 0.0, False, False
        for ev in self.funding[lo:hi]:
            tau = ev["tau"]
            counted = entry < tau <= acct
            ambiguous = abs(tau - entry) < MS_MIN or abs(tau - acct) < MS_MIN or (intrabar_minute is not None and intrabar_minute <= tau < intrabar_minute + MS_MIN)
            if not counted and not ambiguous:
                continue
            u = tau - tau % MS_MIN
            m = self.mark.get(u)
            cash = None if m is None or ev["rate"] is None else -d * q * m * ev["rate"]
            events.append({"tau": tau, "rate": ev["rate"], "intervalHours": ev["intervalHours"], "markMinute": u - MS_MIN, "M": m,
                           "cashflow": cash, "counted": counted, "ambiguous": ambiguous})
            if cash is None:
                if counted:
                    missing = True  # cashflow pertinente non valutabile: netto mancante, mai zero
                else:
                    range_incomplete = True  # solo l'alternativa ambigua non è valutabile
                continue
            if counted:
                total += cash
                if ambiguous:  # alternativa: escluso
                    low, high = low + min(0.0, -cash), high + max(0.0, -cash)
            elif ambiguous:  # alternativa: incluso
                low, high = low + min(0.0, cash), high + max(0.0, cash)
        return {"events": events, "total": None if missing else total, "missing": missing,
                "ambiguityLow": 0.0 if missing else low, "ambiguityHigh": 0.0 if missing else high,
                "ambiguous": any(e["ambiguous"] for e in events), "ambiguityRangeIncomplete": range_incomplete}

    # ------------------------------------------------------------- percorso

    def mark_to_market(self, at: int, close: float) -> None:
        if self.realized_missing:
            return
        pos = self.position
        fee_in = self.f * pos.q * pos.e
        lo = bisect.bisect_right(self.funding_taus, pos.entry_time)
        hi = bisect.bisect_right(self.funding_taus, at)
        fund = 0.0
        for ev in self.funding[lo:hi]:
            m = self.mark.get(ev["tau"] - ev["tau"] % MS_MIN)
            if m is None or ev["rate"] is None:
                return  # percorso non valorizzabile in questo minuto: nessun punto inventato
            fund += -pos.d * pos.q * m * ev["rate"]
        self.curve.append((at, self.realized + pos.d * pos.q * (close - pos.e) - fee_in + fund))

    def halt(self, u: int, why: str) -> None:
        """Lacuna con posizione aperta: percorso irrisolto, finestra interrotta (sezione 11).
        Si conserva quanto era noto; nessuna uscita, prezzo o risultato inventato."""
        pos = self.position
        self.halted = {"at": u, "reason": why, "positionId": pos.id if pos else None}
        if pos is not None:
            trade = {
                "id": pos.id, "episodeId": pos.episode_id, "side": "LONG" if pos.d == 1 else "SHORT", "d": pos.d, "status": "UNRESOLVED_DATA_GAP",
                "callTime": pos.call_time, "entryTime": pos.entry_time, "Eref": pos.eref, "E": pos.e, "q": pos.q, "N0": self.n0, "S0": pos.s0,
                "T": pos.t, "A0": pos.a0, "R0": pos.r0, "G0": pos.g0, "stops": pos.stops, "finalStop": pos.stop,
                "pendingStop": pos.pending_stop, "pendingExit": pos.pending_exit, "gap": {"at": u, "reason": why}, "exit": None,
                "feeEntry": self.f * pos.q * pos.e, "pricePnL": None, "pricePnLRef": None, "slippageCost": None, "feeExit": None,
                "net": None, "netRange": None, "netBps": None, "netOverRisk": None, "riskInitial": pos.q * pos.r0,
                "durationUntilGapMin": (u - pos.entry_time) / MS_MIN, "durationMin": None,
                "stress": {"fee": self.econ["stress"]["fee"], "slippage": self.econ["stress"]["slippage"], "pricePnL": None, "feeEntry": None,
                           "feeExit": None, "net": None},
            }
            trade["funding"] = self.funding_for(trade)  # cashflow valutabili fino alla lacuna
            self.trades.append(trade)
            self.realized_missing = True
            self.curve.append((u, None))
            self.position = None
        self.notices.append(("HALT", pos.episode_id if pos else "", u, "UNRESOLVED_DATA_GAP", {}))
