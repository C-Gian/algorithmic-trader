"""Bundle CAND-001 per la dashboard (schema cand001.bundle/1) e tabelle Markdown dei risultati.

Il bundle non contiene orari di esecuzione né commit: dipende solo da input, configurazione e motore.
Contiene risultati, ledger, episodi con cronologia degli stati e, per gli episodi arrivati al trigger
e per gli esempi, finestre di barre 45m/1D con le osservazioni note ai momenti di decisione.
"""

from __future__ import annotations

from obs001.conventions import iso

from . import BUNDLE_SCHEMA, ENGINE_VERSION

WINDOW_BEFORE_BARS = 16
WINDOW_AFTER_BARS = 12
DAYS_BEFORE = 40


def _compact_record(rec: dict, rec1d: dict | None, t: int) -> dict:
    fib = rec["fib"]
    return {
        "t": t, "status": rec["status"], "C": rec["C"], "A": rec["vol"]["A"], "structure45m": rec["piv"]["structure"],
        "structure1D": rec1d["piv"]["structure"] if rec1d else {"v": None, "r": "INSUFFICIENT_HISTORY"},
        "highs": rec["piv"]["highs"], "lows": rec["piv"]["lows"],
        "levels": [{k: lv.get(k) for k in ("kind", "price", "availableAt", "reason")} for lv in rec["lvl"]],
        "sma20": rec["avg"]["sma20"], "sma50": rec["avg"]["sma50"], "smaDist": rec["avg"]["dist"], "volumeRatio": rec["volu"]["ratio"],
        "fib": {"version": fib["version"], "anchors": fib["anchors"], "u": fib.get("u"), "r": fib.get("r"),
                "retracements": [{"ratio": x["ratio"], "price": x["price"]} for x in fib.get("retracements", [])]},
    }


def _bars(bars, lo: int, hi: int) -> dict:
    sel = bars[lo:hi + 1]
    return {"open": [b.start for b in sel], "status": [b.status for b in sel], "o": [b.o for b in sel], "h": [b.h for b in sel],
            "l": [b.l for b in sel], "c": [b.c for b in sel], "v": [b.v for b in sel]}


def build_window(res: dict, t_from: int, t_to: int, moments: list[int]) -> dict:
    obs = res["obs"]
    conv = obs["conv"]
    inp, bar, day = conv.input_start, conv.bar_ms, conv.day_ms
    recs, recs1d = obs["observed"]["45m"], obs["observed"]["1D"]
    end_index = len(obs["bars45"]) - 1
    lo = max(0, (t_from - inp) // bar - WINDOW_BEFORE_BARS)
    hi = min(end_index, (t_to - inp) // bar + WINDOW_AFTER_BARS)
    dlo = max(0, (t_from - inp) // day - DAYS_BEFORE)
    dhi = min(len(obs["bars1d"]) - 1, (t_to - inp) // day + 1)
    t_lo, t_hi = inp + lo * bar, inp + (hi + 1) * bar
    pivots = [{k: e[k] for k in ("kind", "price", "candidateOpen", "eventTime", "availableAt")}
              for e in obs["observed"]["events"]["45m"] if e["type"] == "PIVOT_CONFIRMED" and t_lo <= e["candidateOpen"] < t_hi]
    snaps = {}
    for t in sorted(set(moments)):
        k = (t - inp) // bar - 1
        if 0 <= k <= end_index:
            kd = (t - t % day - inp) // day - 1
            snaps[str(t)] = _compact_record(recs[k], recs1d[kd] if 0 <= kd < len(recs1d) else None, t)
    return {
        "bars45": _bars(obs["bars45"], lo, hi), "bars1d": _bars(obs["bars1d"], dlo, dhi),
        "sma20": [recs[k]["avg"]["sma20"]["v"] for k in range(lo, hi + 1)], "sma50": [recs[k]["avg"]["sma50"]["v"] for k in range(lo, hi + 1)],
        "pivots": pivots, "snapshots": snaps,
    }


def _episode(e, trade_by_ep: dict, request_by_ep: dict) -> dict:
    return {
        "id": e.id, "legId": e.leg_id, "side": e.side, "d": e.d, "P0": e.p0, "P1": e.p1, "A0": e.a0, "L": e.length, "t0": e.t0,
        "p1BarOpen": e.p1["candidateOpen"], "status": e.status, "states": e.states, "plan": e.plan, "call": e.call,
        "termination": e.termination, "context0": e.context0,
        "tradeId": trade_by_ep.get(e.id, {}).get("id"), "request": request_by_ep.get(e.id),
    }


def build_bundle(cand, res: dict, summary: dict, quality: dict, run_ref: dict, phase: str) -> dict:
    eng, led = res["engine"], res["ledger"]
    src = cand.raw["data"]
    trade_by_ep = {t["episodeId"]: t for t in led.trades}
    req_by_ep = {r["episodeId"]: r for r in led.requests}
    episodes = [_episode(e, trade_by_ep, req_by_ep) for e in eng.episodes]
    windows = {}
    wanted = {e.id for e in eng.episodes if e.plan is not None}
    example_legs = {}
    for side in summary["examples"].values():
        for ref in side.values():
            if not ref:
                continue
            if ref["kind"] == "leg":
                example_legs[ref["id"]] = next(lg for lg in eng.legs if lg["id"] == ref["id"])
            else:
                wanted.add(ref.get("episodeId") or ref["id"])
    for e in eng.episodes:
        if e.id not in wanted:
            continue
        tr = trade_by_ep.get(e.id)
        end = (tr["exit"]["accountingTime"] if tr and tr.get("exit") else None) or (e.termination["t"] if e.termination else e.t0)
        moments = [s["t"] for s in e.states] + [e.t0]
        windows[e.id] = build_window(res, e.p0["candidateOpen"], end, moments)
    for leg_id, lg in example_legs.items():
        windows[leg_id] = build_window(res, lg["P0"]["candidateOpen"], lg["t"], [lg["t"]])
    # Curva per l'app a risoluzione 15 minuti più ogni chiusura d'operazione (il drawdown è calcolato a 1m).
    exits = {t["exit"]["accountingTime"] for t in led.trades if t.get("exit")}
    curve = [[t, v] for t, v in led.curve if t % (15 * 60_000) == 0 or t in exits or t == res["window"][0]]
    realized = [[t["exit"]["accountingTime"], t["net"]] for t in led.trades if t.get("exit")]
    return {
        "kind": "CAND001_BUNDLE", "schema": BUNDLE_SCHEMA, "engineVersion": ENGINE_VERSION,
        "candidate": {"id": cand.raw["id"], "version": cand.raw["candidateVersion"], "hash": cand.hash, "config": cand.raw},
        "observationConventions": {"id": cand.raw["observations"]["conventions"], "hash": cand.raw["observations"]["conventionsHash"]},
        "phase": phase, "timeUnit": "ms epoch UTC",
        "window": {"start": res["window"][0], "end": res["window"][1], "inputStart": res["obs"]["conv"].input_start},
        "run": run_ref,
        "source": {"name": "Binance Vision", "attribution": src["attribution"], "symbol": src["symbol"], "segment": src["segment"],
                   "contractType": src["contractType"], "termsUrl": "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md",
                   "note": "Dati per uso personale di ricerca non produttiva; non redistribuire il bundle."},
        "economicsLabel": cand.econ["label"], "notionalUSDT": cand.econ["notionalUSDT"],
        "quality": quality, "summary": summary,
        "trades": led.trades, "requests": led.requests, "episodes": episodes, "exampleLegs": list(example_legs.values()),
        "windows": windows, "curve": curve, "realized": realized,
    }


# ------------------------------------------------------------------ Markdown


def _f(x, digits=2):
    return "—" if x is None else f"{x:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f}%".replace(".", ",")


def results_markdown(summary: dict, n0: float) -> str:
    L = []
    tables = summary["tables"]
    cols = summary["periods"]
    L.append("### Popolazione, opportunità e operazioni\n")
    L.append("| Voce | " + " | ".join(cols) + " |")
    L.append("|---|" + "---:|" * len(cols))

    def row(label, fn):
        L.append(f"| {label} | " + " | ".join(fn(tables[c]) for c in cols) + " |")

    row("Chiusure 45m (valide)", lambda t: f"{t['closes']} ({t['validCloses']})")
    row("Gambe considerate", lambda t: str(t["legs"]))
    row("Episodi riconosciuti", lambda t: str(t["episodes"]))
    row("Call (LONG/SHORT)", lambda t: f"{t['calls']} ({t['callsLong']}/{t['callsShort']})")
    row("Ingressi eseguiti / rifiutati prezzo / senza quotazione", lambda t: f"{t['requests']['FILLED']} / {t['requests']['REJECTED_PRICE']} / {t['requests']['CANCELLED_NO_QUOTE']}")
    row("Operazioni (LONG/SHORT)", lambda t: f"{t['trades']['n']} ({t['trades']['long']}/{t['trades']['short']})")
    row("Uscite STOP / TARGET / STRUTTURA / 24h / FINE", lambda t: " / ".join(str(t["trades"]["exits"][r]) for r in ("STOP", "TARGET", "EXIT_STRUCTURE", "TIME_EXIT", "END_OF_SEGMENT")))
    row("Protezioni aggiornate (operazioni)", lambda t: f"{t['trades']['protectionUpdates']} ({t['trades']['tradesWithProtectionUpdate']})")
    row("Stop e target nello stesso minuto", lambda t: str(t["trades"]["bothTouched"]))
    row("Uscite in gap all'apertura", lambda t: str(t["trades"]["gapExits"]))
    L.append("\n### Risultato modellato (USDT per operazioni da N0 = 1.000 USDT; somme, non rendimento composto)\n")
    L.append("| Voce | " + " | ".join(cols) + " |")
    L.append("|---|" + "---:|" * len(cols))
    row("PnL prezzi ai riferimenti", lambda t: _f(t["trades"]["pricePnLRef"]))
    row("Slippage attribuito", lambda t: _f(t["trades"]["slippage"]))
    row("Fee", lambda t: _f(-t["trades"]["fees"] if t["trades"]["fees"] is not None else None))
    row("Funding", lambda t: _f(t["trades"]["funding"]))
    row("**Netto modellato**", lambda t: f"**{_f(t['trades']['net'])}**")
    row("Netto in punti base di N0", lambda t: _f(t["trades"]["netBps"], 0))
    row("Intervallo ambiguità funding", lambda t: f"{_f(t['trades']['ambiguityLow'], 3)} / +{_f(t['trades']['ambiguityHigh'], 3)}")
    row("Sensibilità target-first (stesso minuto)", lambda t: _f(t["trades"]["targetFirstDelta"]))
    row("Netto stress (fee 10 bp, slippage 10 bp)", lambda t: _f(t["trades"]["stressNet"]))
    row("Quota operazioni nette positive", lambda t: _pct(t["trades"]["positiveShare"]))
    row("Payoff medio (vincita/perdita)", lambda t: _f(t["trades"]["payoff"]))
    row("Profit factor", lambda t: _f(t["trades"]["profitFactor"]))
    row("Netto per operazione: mediana (P25 / P75)", lambda t: f"{_f(t['trades']['perTrade']['net']['p50'])} ({_f(t['trades']['perTrade']['net']['p25'])} / {_f(t['trades']['perTrade']['net']['p75'])})")
    row("Netto per operazione: P10 / P90", lambda t: f"{_f(t['trades']['perTrade']['net']['p10'])} / {_f(t['trades']['perTrade']['net']['p90'])}")
    row("Durata mediana (minuti)", lambda t: _f(t["trades"]["perTrade"]["durationMin"]["p50"], 0))
    row("Rischio iniziale q·R0 / N0, mediana", lambda t: _pct(t["trades"]["perTrade"]["riskInitialOverN0"]["p50"]))
    row("Netto / rischio iniziale, mediana", lambda t: _f(t["trades"]["perTrade"]["netOverRisk"]["p50"]))
    row("Sequenza massima di perdite", lambda t: str(t["trades"]["maxLosingStreak"]))
    row("Drawdown massimo (chiusure 1m)", lambda t: _f(t["drawdown"]["maxDrawdown"]))
    row("Esposizione (quota del tempo in posizione)", lambda t: _pct(t["trades"]["exposureShare"]))
    row("Concentrazione top5 |netto|", lambda t: _pct(t["trades"]["concentration"]["top5AbsShare"]))
    row("Migliori 5 / somma positivi", lambda t: _pct(t["trades"]["concentration"]["best5PositiveShare"]))
    row("Peggiori 5 / somma negativi", lambda t: _pct(t["trades"]["concentration"]["worst5NegativeShare"]))
    row("Operazioni con funding ambiguo / mancante", lambda t: f"{t['trades']['fundingAmbiguousTrades']} / {t['trades']['fundingMissingTrades']}")
    L.append("\n### Mesi (operazioni per mese d'ingresso; cashflow per data effettiva)\n")
    L.append("| Mese | Chiusure valide | Episodi | Call | Operazioni | Netto per ingresso | Cashflow netto per data | Uscite S/T/Str/24h/Fine |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for m, t in summary["months"].items():
        ex = t["trades"]["exits"]
        L.append(f"| {m} | {t['validCloses']}/{t['closes']} | {t['episodes']} | {t['calls']} | {t['trades']['n']} | {_f(t['trades']['net'])} | "
                 f"{_f(t['cashflowByTimestamp']['net'])} | {ex['STOP']}/{ex['TARGET']}/{ex['EXIT_STRUCTURE']}/{ex['TIME_EXIT']}/{ex['END_OF_SEGMENT']} |")
    L.append("\n### Motivi delle gambe e degli episodi (totale)\n")
    tot = tables[cols[-1]]
    L.append("| Esito della gamba | Numero |")
    L.append("|---|---:|")
    for k, v in sorted(tot["legsByOutcome"].items(), key=lambda x: -x[1]):
        L.append(f"| {k} | {v} |")
    L.append("\n| Conclusione dell'episodio | Numero |")
    L.append("|---|---:|")
    for k, v in sorted(tot["episodesByTermination"].items(), key=lambda x: -x[1]):
        L.append(f"| {k} | {v} |")
    L.append("\n### Esempi (regola cronologica registrata prima degli esiti)\n")
    L.append("| Verso | Categoria | Riferimento | Momento UTC |")
    L.append("|---|---|---|---|")
    for side, cats in summary["examples"].items():
        for cat, ref in cats.items():
            L.append(f"| {side} | {cat} | {ref['id'] if ref else 'categoria vuota'} | {iso(ref['t']) if ref else '—'} |")
    return "\n".join(L) + "\n"
