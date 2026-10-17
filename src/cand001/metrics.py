"""Metriche e tabelle CAND-001/v1 (sezione 12): anni, mesi, DEV totale, esempi cronologici prefissati.

Operazioni assegnate al mese/anno d'ingresso per le distribuzioni per trade; cashflow e curva al loro
timestamp. Somme per N0=1000 USDT, non rendimento composto. Netto mancante se manca un cashflow.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from obs001.summary import describe

from . import decision as D

QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9]
ENTRY_OUTCOMES = ("FILLED", "REJECTED_PRICE", "CANCELLED_NO_QUOTE", "CANCELLED_END_OF_WINDOW")
EXIT_REASONS = ("STOP", "TARGET", "EXIT_STRUCTURE", "TIME_EXIT", "END_OF_SEGMENT")
MISSING_DATA = (D.INVALIDATED_DATA, "CANCELLED_NO_QUOTE", D.ABSTAIN_INCOMPLETE, D.ABSTAIN_VOLATILITY)


def month_of(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, UTC).strftime("%Y-%m")


def year_of(t: int) -> str:
    return month_of(t)[:4]


def _sum(values):
    vals = list(values)
    return None if any(v is None for v in vals) else math.fsum(vals)


def drawdown(curve: list[tuple[int, float | None]], start: int, end: int) -> dict:
    before = [v for t, v in curve if t < start]
    base = before[-1] if before else 0.0
    pts = [v for t, v in curve if start <= t <= end]
    if base is None or any(v is None for v in pts):
        return {"maxDrawdown": None, "missing": True}
    peak, worst, run = base, 0.0, base
    for v in pts:
        peak = max(peak, v)
        worst = min(worst, v - peak)
        run = v
    return {"maxDrawdown": worst, "maxDrawdownBps": worst / 1000 * 10_000, "start": base, "end": run, "points": len(pts), "missing": False}


def trade_stats(trades: list[dict], n0: float) -> dict:
    closed = [t for t in trades if t.get("exit")]
    nets = [t["net"] for t in closed]
    known = [x for x in nets if x is not None]
    wins = [x for x in known if x > 0]
    losses = [x for x in known if x < 0]
    streak = best = 0
    for x in known:
        streak = streak + 1 if x < 0 else 0
        best = max(best, streak)
    abs_sum = math.fsum(abs(x) for x in known)
    pos_sum, neg_sum = math.fsum(wins), math.fsum(-x for x in losses)
    top = sorted(known, key=lambda x: -abs(x))[:5]
    return {
        "n": len(trades), "closed": len(closed), "unresolved": len(trades) - len(closed),
        "long": sum(t["d"] == 1 for t in trades), "short": sum(t["d"] == -1 for t in trades),
        "netMissing": sum(x is None for x in nets),
        "pricePnLRef": _sum(t["pricePnLRef"] for t in closed), "slippage": _sum(t["slippageCost"] for t in closed),
        "pricePnL": _sum(t["pricePnL"] for t in closed), "fees": _sum(t["feeEntry"] + t["feeExit"] for t in closed),
        "funding": _sum(t["funding"]["total"] for t in closed), "net": _sum(nets) if closed else 0.0,
        "netBps": None if _sum(nets) is None else (_sum(nets) or 0.0) / n0 * 10_000,
        "stressNet": _sum(t["stress"]["net"] for t in closed) if closed else 0.0,
        "ambiguityLow": _sum(t["funding"]["ambiguityLow"] for t in closed), "ambiguityHigh": _sum(t["funding"]["ambiguityHigh"] for t in closed),
        "targetFirstDelta": _sum(t["targetFirst"]["delta"] for t in closed if "targetFirst" in t),
        "perTrade": {
            "net": describe(known, QUANTILES), "netBps": describe([x / n0 * 10_000 for x in known], QUANTILES),
            "durationMin": describe([t["durationMin"] for t in closed], QUANTILES),
            "riskInitialOverN0": describe([t["riskInitial"] / n0 for t in closed], QUANTILES),
            "netOverRisk": describe([t["netOverRisk"] for t in closed if t["netOverRisk"] is not None], QUANTILES),
        },
        "positiveShare": len(wins) / len(known) if known else None,
        "payoff": (pos_sum / len(wins)) / (neg_sum / len(losses)) if wins and losses else None,
        "profitFactor": pos_sum / neg_sum if neg_sum > 0 else None,
        "maxLosingStreak": best,
        "concentration": {
            "top5AbsShare": math.fsum(abs(x) for x in top) / abs_sum if abs_sum > 0 else None,
            "best5PositiveShare": math.fsum(sorted(wins, reverse=True)[:5]) / pos_sum if pos_sum > 0 else None,
            "worst5NegativeShare": math.fsum(sorted((-x for x in losses), reverse=True)[:5]) / neg_sum if neg_sum > 0 else None,
        },
        "exits": {r: sum(1 for t in closed if t["exit"]["reason"] == r) for r in EXIT_REASONS},
        "gapExits": sum(1 for t in closed if t["exit"]["gap"]),
        "bothTouched": sum(1 for t in closed if t["exit"]["bothTouched"]),
        "protectionUpdates": sum(len(t["stops"]) for t in closed), "tradesWithProtectionUpdate": sum(1 for t in closed if t["stops"]),
        "fundingEvents": sum(sum(1 for e in t["funding"]["events"] if e["counted"]) for t in closed),
        "fundingAmbiguousTrades": sum(1 for t in closed if t["funding"]["ambiguous"]),
        "fundingMissingTrades": sum(1 for t in closed if t["funding"]["missing"]),
        "exposureMin": math.fsum(t["durationMin"] for t in closed),
    }


def period_table(res: dict, start: int, end: int, cand) -> dict:
    eng, led = res["engine"], res["ledger"]
    n0 = cand.econ["notionalUSDT"]
    bar = res["obs"]["conv"].bar_ms
    recs = res["obs"]["observed"]["45m"]
    inp = eng.input_start
    closes = list(range(max(start, res["window"][0]), min(end, res["window"][1]), bar))
    valid = sum(1 for t in closes if recs[(t - inp) // bar - 1]["status"] == "COMPLETE")
    legs = [lg for lg in eng.legs if start <= lg["t"] < end]
    eps = [e for e in eng.episodes if start <= e.t0 < end]
    calls = [e for e in eng.episodes if e.call and start <= e.call["t"] < end]
    reqs = [r for r in led.requests if start <= r["executeAt"] < end]
    trades = [t for t in led.trades if start <= t["entryTime"] < end]
    terminations: dict[str, int] = {}
    for e in eps:
        code = e.termination["code"] if e.termination else e.status
        terminations[code] = terminations.get(code, 0) + 1
    legs_by: dict[str, int] = {}
    for lg in legs:
        legs_by[lg["outcome"]] = legs_by.get(lg["outcome"], 0) + 1
    states: dict[str, int] = {}
    for dec in eng.decisions:
        if start <= dec["t"] < end:
            states[dec["state"]] = states.get(dec["state"], 0) + 1
    stats = trade_stats(trades, n0)
    stats["exposureShare"] = stats["exposureMin"] * 60_000 / ((min(end, res["window"][1]) - max(start, res["window"][0])) or 1)
    return {
        "start": start, "end": end, "closes": len(closes), "validCloses": valid,
        "legs": len(legs), "legsByOutcome": legs_by, "episodes": len(eps), "episodesByTermination": terminations,
        "calls": len(calls), "callsLong": sum(e.d == 1 for e in calls), "callsShort": sum(e.d == -1 for e in calls),
        "requests": {o: sum(1 for r in reqs if r["outcome"] == o) for o in ENTRY_OUTCOMES},
        "decisionStates": states, "trades": stats, "drawdown": drawdown(led.curve, start, end),
    }


def cashflow_by_month(trades: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}

    def add(t, key, v):
        cell = out.setdefault(month_of(t), {"pricePnL": 0.0, "fees": 0.0, "funding": 0.0, "missing": False})
        if v is None:
            cell["missing"] = True
        else:
            cell[key] += v

    for tr in trades:
        if not tr.get("exit"):
            add(tr["entryTime"], "fees", None)
            continue
        add(tr["entryTime"], "fees", tr["feeEntry"])
        add(tr["exit"]["accountingTime"], "pricePnL", tr["pricePnL"])
        add(tr["exit"]["accountingTime"], "fees", tr["feeExit"])
        for ev in tr["funding"]["events"]:
            if ev["counted"]:
                add(ev["tau"], "funding", ev["cashflow"])
    for cell in out.values():
        cell["net"] = None if cell["missing"] else cell["pricePnL"] - cell["fees"] + cell["funding"]
    return out


def periods(window: tuple[int, int]) -> dict[str, tuple[int, int]]:
    from obs001.conventions import parse_utc

    start, end = window
    out = {}
    y = int(year_of(start))
    while True:
        ys, ye = parse_utc(f"{y:04d}-01-01T00:00:00Z"), parse_utc(f"{y + 1:04d}-01-01T00:00:00Z")
        if ys >= end:
            break
        out[str(y)] = (max(ys, start), min(ye, end))
        y += 1
    return out


def summarize(res: dict, cand, phase: str) -> dict:
    from .config import months_between
    from obs001.inputs import month_bounds

    window = res["window"]
    tables = {name: period_table(res, s, e, cand) for name, (s, e) in periods(window).items()}
    tables[phase] = period_table(res, window[0], window[1], cand)
    months = {m: period_table(res, *month_bounds(m), cand) for m in months_between(*window)}
    flows = cashflow_by_month(res["ledger"].trades)
    for m, row in months.items():
        row["cashflowByTimestamp"] = flows.get(m, {"pricePnL": 0.0, "fees": 0.0, "funding": 0.0, "missing": False, "net": 0.0})
    return {"phase": phase, "periods": list(tables), "tables": tables, "months": months, "examples": examples(res),
            "reconciliation": reconcile(res, tables[phase]), "halted": res["ledger"].halted}


def examples(res: dict) -> dict:
    eng, led = res["engine"], res["ledger"]
    out: dict[str, dict] = {}
    for side, d in (("LONG", 1), ("SHORT", -1)):
        eps = sorted((e for e in eng.episodes if e.d == d), key=lambda e: (e.t0, e.id))
        trades = sorted((t for t in led.trades if t["d"] == d and t.get("exit")), key=lambda t: (t["entryTime"], t["id"]))

        def first(items, key):
            items = sorted(items, key=key)
            return items[0] if items else None

        def ep_ref(e, t):
            return {"kind": "episode", "id": e.id, "t": t} if e else None

        def tr_ref(t):
            return {"kind": "trade", "id": t["id"], "episodeId": t["episodeId"], "t": t["entryTime"]} if t else None

        call = first([e for e in eps if e.call], lambda e: (e.call["t"], e.id))
        neg = next((t for t in trades if t["net"] is not None and t["net"] < 0), None)
        pos = next((t for t in trades if t["net"] is not None and t["net"] > 0), None)
        prot = next((t for t in trades if t["stops"]), None)
        react = first([e for e in eps if e.termination and e.termination["code"] in D.REACTION_INVALIDATED], lambda e: (e.termination["t"], e.id))
        rr = first([e for e in eps if e.termination and e.termination["code"] == D.ABSTAIN_REWARD_RISK], lambda e: (e.termination["t"], e.id))
        miss_eps = [e for e in eps if e.termination and e.termination["code"] in MISSING_DATA]
        miss_legs = [lg for lg in eng.legs if lg["d"] == d and lg["outcome"] in MISSING_DATA]
        miss_reqs = [r for r in led.requests if r["side"] == side and r["outcome"] == "CANCELLED_NO_QUOTE"]
        cands = [(e.termination["t"], e.id, ep_ref(e, e.termination["t"])) for e in miss_eps]
        cands += [(lg["t"], lg["id"], {"kind": "leg", "id": lg["id"], "t": lg["t"]}) for lg in miss_legs]
        cands += [(r["executeAt"], r["episodeId"], ep_ref(next(e for e in eps if e.id == r["episodeId"]), r["executeAt"])) for r in miss_reqs]
        miss = sorted(cands, key=lambda x: (x[0], x[1]))[0][2] if cands else None
        out[side] = {
            "FIRST_CALL": ep_ref(call, call.call["t"]) if call else None,
            "FIRST_TRADE": tr_ref(trades[0] if trades else None),
            "FIRST_NEGATIVE_TRADE": tr_ref(neg), "FIRST_POSITIVE_TRADE": tr_ref(pos), "FIRST_PROTECTION_UPDATE": tr_ref(prot),
            "FIRST_ABSTAIN_REACTION_INVALIDATED": ep_ref(react, react.termination["t"]) if react else None,
            "FIRST_ABSTAIN_REWARD_RISK": ep_ref(rr, rr.termination["t"]) if rr else None,
            "FIRST_ABSTAIN_MISSING_DATA": miss,
        }
    return out


def reconcile(res: dict, total: dict) -> dict:
    """Conti delle opportunità e del ledger: ogni violazione è un errore, non una nota."""
    eng, led = res["engine"], res["ledger"]
    problems = []
    calls = [e for e in eng.episodes if e.call]
    if len(led.requests) != len(calls):
        problems.append(f"richieste {len(led.requests)} != call {len(calls)}")
    filled = sum(1 for r in led.requests if r["outcome"] == "FILLED")
    if filled != len(led.trades):
        problems.append(f"fill {filled} != trade {len(led.trades)}")
    if sum(1 for lg in eng.legs if lg["outcome"] == "RECOGNIZED") != len(eng.episodes):
        problems.append("gambe riconosciute != episodi")
    closed = [t for t in led.trades if t.get("exit")]
    net = _sum(t["net"] for t in closed)
    if net is not None and not led.realized_missing and abs(net - led.realized) > 1e-6:
        problems.append("somma netti != realizzato del ledger")
    parts = _sum(t["pricePnL"] - t["feeEntry"] - t["feeExit"] + (t["funding"]["total"] or 0.0) for t in closed)
    if net is not None and abs(parts - net) > 1e-6:
        problems.append("componenti non sommano al netto")
    if problems:
        raise AssertionError("; ".join(problems))
    return {"calls": len(calls), "requests": len(led.requests), "trades": len(led.trades), "net": net, "reconciled": True}
