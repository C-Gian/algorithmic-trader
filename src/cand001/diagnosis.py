"""CAND-001/D1: diagnosi offline della politica v1 dagli artefatti DEV conservati.

Legge il bundle DEV accettato (mai modificato) e, per i percorsi, i soli minuti negoziati DEV già
verificati. Non usa il motore decisionale né il ledger: nessuna decisione viene ricalcolata o
cambiata. Due passi separati, nell'ordine prescritto dal task:
    select   elenco deterministico degli esempi, dal solo bundle (prima di leggere i percorsi)
    extract  un record per operazione, timeline degli esempi, riepilogo e riconciliazione

PowerShell, dalla radice del checkout:
    $env:PYTHONPATH = "src"; python3.12 -m cand001.diagnosis select
    $env:PYTHONPATH = "src"; python3.12 -m cand001.diagnosis extract
Output fuori Git in <data-dir>/diagnosis/D1.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path

from obs001.acquire import _sha256_file, now_utc
from obs001.aggregate import aggregate
from obs001.cli import software_ref
from obs001.conventions import REPO_ROOT, canonical_json, iso, sha256_bytes
from obs001.minutes import VALID, MinuteStore
from obs001.summary import describe

from .config import CONFIG_PATH, load_candidate
from .data import dirs, load_trade

DEFAULT_DATA_DIR = REPO_ROOT.parent / "algorithmic-trader-data" / "CAND-001"
RUN_ID = "CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62"
BUNDLE_SHA256 = "b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a"
CONFIG_SHA256 = "aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf"
MAX_CASES = 14

# Regola registrata nel task D1 (sezione 2). Tempo pertinente per categoria, poi ID; categorie di
# risultato (netto positivo/negativo, motivo d'uscita) a posteriori, ordine solo cronologico.
SIDE_CATEGORIES = ("FIRST_POSITIVE_TRADE", "FIRST_NEGATIVE_TRADE", "FIRST_STOP_UPDATED_TRADE",
                   "FIRST_ABSTAIN_REWARD_RISK", "FIRST_INVALIDATED_DEPTH", "FIRST_REJECTED_PRICE")
GLOBAL_CATEGORIES = ("FIRST_EXIT_STRUCTURE", "FIRST_TIME_EXIT")
RULE = {
    "FIRST_POSITIVE_TRADE": "operazione conclusa con netto > 0; tempo = ingresso modellato",
    "FIRST_NEGATIVE_TRADE": "operazione conclusa con netto < 0; tempo = ingresso modellato",
    "FIRST_STOP_UPDATED_TRADE": "operazione con almeno un aggiornamento dello stop attivato; tempo = prima attivazione",
    "FIRST_ABSTAIN_REWARD_RISK": "episodio concluso ABSTAIN_REWARD_RISK; tempo = conclusione",
    "FIRST_INVALIDATED_DEPTH": "episodio concluso INVALIDATED_DEPTH; tempo = conclusione",
    "FIRST_REJECTED_PRICE": "richiesta d'ingresso REJECTED_PRICE; tempo = tentativo (executeAt)",
    "FIRST_EXIT_STRUCTURE": "operazione uscita EXIT_STRUCTURE, LONG e SHORT insieme; tempo = uscita contabile",
    "FIRST_TIME_EXIT": "operazione uscita TIME_EXIT, LONG e SHORT insieme; tempo = uscita contabile",
}


class InputMismatch(RuntimeError):
    """Artefatto diverso da quello accettato: la diagnosi non procede."""


def paths(data_dir: Path) -> dict[str, Path]:
    run = data_dir / "runs" / RUN_ID
    return {"run": run, "bundle": run / "cand001-bundle.json", "runManifest": run / "run-manifest.json",
            "out": data_dir / "diagnosis" / "D1"}


def load_bundle(data_dir: Path) -> tuple[dict, str]:
    """Bundle DEV accettato, con identità verificata prima di qualsiasi lettura dei contenuti."""
    p = paths(data_dir)
    sha = _sha256_file(p["bundle"])
    if sha != BUNDLE_SHA256:
        raise InputMismatch(f"bundle {p['bundle']}: SHA256 {sha} diverso da {BUNDLE_SHA256}")
    cand = load_candidate()
    if cand.hash != CONFIG_SHA256:
        raise InputMismatch(f"config v1 SHA256 {cand.hash} diverso da {CONFIG_SHA256}")
    bundle = json.loads(p["bundle"].read_text(encoding="utf-8"))
    if bundle["run"]["runId"] != RUN_ID or bundle["candidate"]["hash"] != CONFIG_SHA256 or bundle["phase"] != "DEV":
        raise InputMismatch("identità del bundle (run, config, fase) diversa da quella accettata")
    return bundle, sha


# ------------------------------------------------------------------ selezione


def _first(items: list[tuple[int, str, dict]]) -> tuple[int, str, dict] | None:
    return min(items, key=lambda x: (x[0], x[1])) if items else None


def select_examples(trades: list[dict], requests: list[dict], episodes: list[dict]) -> dict:
    """Elenco deterministico dei casi: per ogni categoria il primo per (tempo pertinente, ID).
    Il caso è l'episodio (un'operazione o una richiesta appartengono al loro episodio): un caso
    selezionato da più categorie compare una volta sola con tutte le sue categorie."""
    closed = [t for t in trades if t.get("exit")]
    hits: list[dict] = []

    def add(category: str, side: str | None, found: tuple[int, str, dict] | None) -> None:
        if found is None:
            hits.append({"category": category, "side": side, "empty": True})
            return
        t, _, obj = found
        hits.append({"category": category, "side": side, "t": t, "episodeId": obj["episodeId"] if "episodeId" in obj else obj["id"]})

    for side in ("LONG", "SHORT"):
        tr = [t for t in closed if t["side"] == side]
        add("FIRST_POSITIVE_TRADE", side, _first([(t["entryTime"], t["id"], t) for t in tr if t["net"] is not None and t["net"] > 0]))
        add("FIRST_NEGATIVE_TRADE", side, _first([(t["entryTime"], t["id"], t) for t in tr if t["net"] is not None and t["net"] < 0]))
        add("FIRST_STOP_UPDATED_TRADE", side, _first([(t["stops"][0]["effectiveAt"], t["id"], t) for t in tr if t["stops"]]))
        eps = [e for e in episodes if e["side"] == side and e.get("termination")]
        add("FIRST_ABSTAIN_REWARD_RISK", side, _first([(e["termination"]["t"], e["id"], e) for e in eps
                                                       if e["termination"]["code"] == "ABSTAIN_REWARD_RISK"]))
        add("FIRST_INVALIDATED_DEPTH", side, _first([(e["termination"]["t"], e["id"], e) for e in eps
                                                     if e["termination"]["code"] == "INVALIDATED_DEPTH"]))
        add("FIRST_REJECTED_PRICE", side, _first([(r["executeAt"], r["episodeId"], r) for r in requests
                                                  if r["side"] == side and r["outcome"] == "REJECTED_PRICE"]))
    for category, reason in (("FIRST_EXIT_STRUCTURE", "EXIT_STRUCTURE"), ("FIRST_TIME_EXIT", "TIME_EXIT")):
        add(category, None, _first([(t["exit"]["accountingTime"], t["id"], t) for t in closed if t["exit"]["reason"] == reason]))

    by_case: dict[str, dict] = {}
    for h in hits:
        if h.get("empty"):
            continue
        case = by_case.setdefault(h["episodeId"], {"episodeId": h["episodeId"], "categories": []})
        case["categories"].append({"category": h["category"], "side": h["side"], "t": h["t"], "tIso": iso(h["t"])})
    ep_by_id = {e["id"]: e for e in episodes}
    tr_by_ep = {t["episodeId"]: t for t in trades}
    req_by_ep = {r["episodeId"]: r for r in requests}
    cases = []
    for case in by_case.values():
        e, t, r = ep_by_id[case["episodeId"]], tr_by_ep.get(case["episodeId"]), req_by_ep.get(case["episodeId"])
        first_t = min(c["t"] for c in case["categories"])
        times = {"t0": e["t0"], "callTime": e["call"]["t"] if e.get("call") else None,
                 "requestAt": r["executeAt"] if r else None, "entryTime": t["entryTime"] if t else None,
                 "exitAccountingTime": t["exit"]["accountingTime"] if t and t.get("exit") else None,
                 "terminationTime": e["termination"]["t"] if e.get("termination") else None}
        cases.append({"episodeId": case["episodeId"], "tradeId": t["id"] if t else None, "side": e["side"],
                      "sortKey": [first_t, case["episodeId"]], "categories": sorted(case["categories"], key=lambda c: (c["t"], c["category"])),
                      "times": times, "timesIso": {k: (iso(v) if v is not None else None) for k, v in times.items()}})
    cases.sort(key=lambda c: (c["sortKey"][0], c["sortKey"][1]))
    if len(cases) > MAX_CASES:
        raise AssertionError(f"{len(cases)} casi > {MAX_CASES}")
    empty = [{"category": h["category"], "side": h["side"]} for h in hits if h.get("empty")]
    return {"cases": cases, "emptyCategories": empty, "categoryHits": len(hits) - len(empty)}


def cmd_select(data_dir: Path) -> int:
    bundle, sha = load_bundle(data_dir)
    sel = select_examples(bundle["trades"], bundle["requests"], bundle["episodes"])
    body = {"kind": "CAND001_D1_EXAMPLES", "runId": RUN_ID, "bundleSha256": sha, "configSha256": CONFIG_SHA256,
            "inputHash": bundle["run"]["inputHash"], "rule": RULE, "maxCases": MAX_CASES,
            "cases": sel["cases"], "emptyCategories": sel["emptyCategories"], "categoryHits": sel["categoryHits"]}
    list_sha = sha256_bytes(canonical_json({"cases": sel["cases"], "emptyCategories": sel["emptyCategories"]}))
    body["listSha256"] = list_sha
    body["createdAt"] = now_utc()
    out = paths(data_dir)["out"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "examples-selection.json").write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"bundle {sha} | casi {len(sel['cases'])} | categorie vuote {len(sel['emptyCategories'])} | listSha256 {list_sha}")
    for c in sel["cases"]:
        cats = ", ".join(f"{x['category']}{'/' + x['side'] if x['side'] else ''}" for x in c["categories"])
        print(f"  {c['timesIso']['t0']} {c['episodeId']} {c['tradeId'] or '-'} [{cats}]")
    for e in sel["emptyCategories"]:
        print(f"  categoria vuota: {e['category']} {e['side'] or ''}")
    return 0


# ------------------------------------------------------------------ percorsi

MS_MIN = 60_000
BAR_MS = 45 * MS_MIN
DAY_MIN = 24 * 60
Q3 = [0.1, 0.5, 0.9]


def _z(d: int, eref: float, r0: float, p: float) -> float:
    """z(p) = d*(p - entryReference)/R0, R0 geometrico v1 basato sulla fill."""
    return d * (p - eref) / r0


def _minute(store: MinuteStore, u: int) -> int | None:
    i = store.index(u)
    return i if 0 <= i < store.n and store.status[i] == VALID else None


def active_stop(trade: dict, u: int) -> float:
    """Stop attivo nel minuto [u, u+60s): l'ultimo attivato con effectiveAt <= u, altrimenti S0."""
    stop = trade["S0"]
    for s in trade["stops"]:
        if s["effectiveAt"] <= u:
            stop = s["to"]
    return stop


def path_facts(trade: dict, store: MinuteStore) -> dict:
    """Percorso campionato alle chiusure 1m effettivamente detenute.

    Detenuti sono i minuti [entryTime, exit.minute): la loro chiusura è osservata a posizione aperta.
    Il minuto d'uscita è escluso in entrambi i casi: uscita intraminuto (il contatto non ordina gli
    altri prezzi del minuto) e uscita all'apertura (nessun prezzo successivo). Origine z=0 al
    riferimento d'ingresso; il riferimento d'uscita modellato è un punto finale separato, non una
    chiusura osservata. Nessun minuto dopo l'uscita viene letto."""
    d, eref, r0 = trade["d"], trade["Eref"], trade["R0"]
    ex = trade["exit"]
    entry, m_exit = trade["entryTime"], ex["minute"]
    closes, missing, violations = [], [], []
    for u in range(entry, m_exit, MS_MIN):
        i = _minute(store, u)
        if i is None:
            missing.append(u)
            continue
        closes.append((u + MS_MIN, _z(d, eref, r0, store.c[i])))
        # Coerenza con il ledger: in un minuto detenuto e non d'uscita né stop né target sono toccati.
        stop = active_stop(trade, u)
        lo, hi = (store.l[i], store.h[i]) if d == 1 else (-store.h[i], -store.l[i])
        if lo <= d * stop or hi >= d * trade["T"]:
            violations.append(u)
    z_exit = _z(d, eref, r0, ex["Xref"])
    zmax, t_max, zmin, t_min = 0.0, entry, 0.0, entry  # origine inclusa; a parità il primo istante
    for t, z in closes:
        if z > zmax:
            zmax, t_max = z, t
        if z < zmin:
            zmin, t_min = z, t
    tc = (entry // BAR_MS + 1) * BAR_MS  # prima chiusura 45m strettamente dopo l'ingresso
    first45 = {"t": tc, "status": "CLOSED_BEFORE", "C": None, "move": None, "z": None}
    if m_exit >= tc:  # posizione ancora aperta dopo il processo di esecuzione di quella chiusura
        i = _minute(store, tc - MS_MIN)
        if i is None:
            first45.update(status="MISSING_MINUTE")
        else:
            first45.update(status="HELD", C=store.c[i], move=d * (store.c[i] - eref), z=_z(d, eref, r0, store.c[i]))
    return {
        "heldCloses": len(closes), "missingMinutes": missing, "ledgerViolations": violations,
        "zMaxObserved": zmax, "tMaxObserved": t_max, "minutesToMaxObserved": (t_max - entry) / MS_MIN,
        "zMinObserved": zmin, "tMinObserved": t_min, "minutesToMinObserved": (t_min - entry) / MS_MIN,
        "zExitReference": z_exit, "givebackFromMaxObserved": zmax - z_exit,
        "zTargetInitial": _z(d, eref, r0, trade["T"]), "zStopInitial": _z(d, eref, r0, trade["S0"]),
        "first45m": first45, "series": closes,
    }


def management_facts(trade: dict, episode: dict) -> dict:
    """Decisioni di gestione (chiusure 45m) e loro esito di esecuzione, con latenza di 60 s."""
    ex = trade["exit"]
    acts = {s["decidedAt"]: s for s in trade["stops"]}
    updates, rejected, before_entry, exit_requests = [], [], 0, []
    for s in episode["states"]:
        if s["state"] == "PROTECTION_UPDATE":
            a = acts.get(s["t"])
            if a is not None:
                outcome = "ACTIVATED"
            elif ex["minute"] < s["effectiveAt"]:
                outcome = "NOT_ACTIVATED_EXIT_DURING_LATENCY"
            else:
                outcome = "NOT_ACTIVATED_EXIT_AT_ACTIVATION_OPEN"
            updates.append({"decidedAt": s["t"], "effectiveAtPlanned": s["effectiveAt"], "activatedAt": a["effectiveAt"] if a else None,
                            "from": s["current"], "to": s["proposal"], "pivot": s["pivot"], "pivotCandidateOpen": s["pivotCandidateOpen"],
                            "pivotAvailableAt": s["pivotAvailableAt"], "outcome": outcome})
        elif s["state"] == "PROTECTION_REJECTED":
            rejected.append({"t": s["t"], "proposal": s["proposal"], "failed": sorted(k for k, v in s["checks"].items() if not v)})
        elif s["state"] == "PROTECTION_PIVOT_BEFORE_ENTRY":
            before_entry += 1
        elif s["state"] == "EXIT_STRUCTURE_REQUESTED":
            done = ex["reason"] == "EXIT_STRUCTURE" and ex["minute"] == s["executeAt"]
            exit_requests.append({"decidedAt": s["t"], "executeAt": s["executeAt"],
                                  "outcome": "EXECUTED" if done else f"PRECEDED_BY_{ex['reason']}"})
    return {"updatesDecided": updates, "updatesActivated": len(trade["stops"]), "updatesRejected": rejected,
            "pivotsBeforeEntry": before_entry, "exitStructureRequests": exit_requests,
            "stopAtExit": trade["finalStop"], "stopAtExitOrigin": "UPDATED" if trade["stops"] else "INITIAL"}


def economics_facts(trade: dict) -> dict:
    """Componenti economiche. Lo slippage è già nei prezzi fill: qui come costo positivo
    slippage = pricePnLRef - pricePnL (nel bundle slippageCost ha segno opposto), mai sottratto due volte."""
    slip = trade["pricePnLRef"] - trade["pricePnL"]
    fund = trade["funding"]["total"]
    rebuilt = None if fund is None else trade["pricePnLRef"] - slip - trade["feeEntry"] - trade["feeExit"] + fund
    return {"pricePnLRef": trade["pricePnLRef"], "slippage": slip, "pricePnL": trade["pricePnL"], "feeEntry": trade["feeEntry"],
            "feeExit": trade["feeExit"], "funding": fund, "net": trade["net"], "riskInitial": trade["riskInitial"],
            "netOverRisk": trade["netOverRisk"], "stressNet": trade["stress"]["net"],
            "fundingAmbiguous": trade["funding"]["ambiguous"], "fundingMissing": trade["funding"]["missing"],
            "identityResidual": None if rebuilt is None or trade["net"] is None else trade["net"] - rebuilt}


def trade_record(trade: dict, episode: dict, request: dict, store: MinuteStore, refs: dict) -> dict:
    plan, call = episode["plan"], episode["call"]
    rec = next(s for s in episode["states"] if s["state"] == "RECOGNIZED")
    d = trade["d"]
    ex = trade["exit"]
    trigger_prev = plan["Hprev"] if d == 1 else plan["Lprev"]
    path = path_facts(trade, store)
    return {
        "tradeId": trade["id"], "episodeId": episode["id"], "requestRef": f"{episode['id']}@{request['executeAt']}", "side": trade["side"], "d": d,
        "t0": episode["t0"], "callTime": trade["callTime"], "entryTime": trade["entryTime"],
        "P0": episode["P0"]["price"], "P0candidateOpen": episode["P0"]["candidateOpen"], "P1": episode["P1"]["price"],
        "P1candidateOpen": episode["P1"]["candidateOpen"], "P1availableAt": episode["P1"]["availableAt"], "A0": episode["A0"],
        "legAmplitude": episode["L"], "legAmplitudeOverA0": episode["L"] / episode["A0"], "legBars": rec["legBars"],
        "legMinutes": (episode["P1"]["candidateOpen"] - episode["P0"]["candidateOpen"]) / MS_MIN,
        "depthAtTrigger": plan["depth"], "Rext": plan["Rext"], "counterCloses": plan["counterCloses"], "barsSinceP1AtTrigger": plan["barsSinceP1"],
        "waitClosesFromT0": (trade["callTime"] - episode["t0"]) // BAR_MS,
        "trigger": {"Ck": plan["Ck"], "Ok": plan["Ok"], "prevExtreme": trigger_prev, "beyondPrevExtreme": d * (plan["Ck"] - trigger_prev),
                    "bodyDirectional": d * (plan["Ck"] - plan["Ok"])},
        "structure45mAtT0": episode["context0"]["structure45m"]["v"], "structure45mAtCall": call["context"]["structure45m"]["v"],
        "structure1DAtCall": call["context"]["structure1D"]["v"],
        "S0": trade["S0"], "T": trade["T"], "Estar": plan["Estar"], "indicativeRatio": plan["ratio"], "entryBound": call["entryBound"],
        "Eref": trade["Eref"], "E": trade["E"], "R0": trade["R0"], "G0": trade["G0"], "fillRatio": trade["G0"] / trade["R0"],
        "R0OverE": trade["R0"] / trade["E"], "q": trade["q"],
        "exit": {"reason": ex["reason"], "minute": ex["minute"], "accountingTime": ex["accountingTime"], "Xref": ex["Xref"], "X": ex["X"],
                 "intrabar": ex["intrabar"], "gap": ex["gap"], "due": ex["due"], "atStopActivation": ex["atStopActivation"],
                 "bothTouched": ex["bothTouched"]},
        "durationMin": trade["durationMin"], "durationOver24h": trade["durationMin"] / DAY_MIN,
        "management": management_facts(trade, episode), "path": {k: v for k, v in path.items() if k != "series"},
        "economics": economics_facts(trade), "sourceRefs": refs,
    }


# ------------------------------------------------------------------ timeline degli esempi


def _bars_until(bars45: list, start: int, end: int) -> list[dict]:
    """Barre 45m complete aperte da start e terminate entro end (nessuna barra che si chiude dopo)."""
    return [{"open": b.start, "o": b.o, "h": b.h, "l": b.l, "c": b.c, "status": b.status} for b in bars45 if b.start >= start and b.end <= end]


def example_timeline(case: dict, bundle: dict, records: dict, store: MinuteStore, bars45: list, series: dict) -> dict:
    """Fatti noti a ciascun t (stati del candidato, osservazioni del bundle a quei momenti) separati da
    ciò che accade dopo (esecuzione modellata), fino alla conclusione dell'episodio e mai oltre."""
    ep = next(e for e in bundle["episodes"] if e["id"] == case["episodeId"])
    tr = next((t for t in bundle["trades"] if t["episodeId"] == ep["id"]), None)
    end = tr["exit"]["minute"] if tr else ep["termination"]["t"]
    win = bundle["windows"].get(ep["id"])
    snaps = win["snapshots"] if win else {}
    decisions = []
    for s in ep["states"]:
        snap = snaps.get(str(s["t"]))
        known = {"structure45m": snap["structure45m"]["v"], "structure1D": snap["structure1D"]["v"], "A": snap["A"]["v"], "C": snap["C"]} if snap else None
        decisions.append({"t": s["t"], "tIso": iso(s["t"]), "state": s["state"], "facts": {k: v for k, v in s.items() if k not in ("t", "state")},
                          "observationsAtT": known})
    pivots = [p for p in (win["pivots"] if win else []) if p["availableAt"] <= end]
    out = {"episodeId": ep["id"], "tradeId": tr["id"] if tr else None, "side": ep["side"], "categories": case["categories"],
           "leg": {"P0": ep["P0"], "P1": ep["P1"], "A0": ep["A0"], "L": ep["L"], "note": "P1 è confermato (availableAt) due barre dopo la propria candela"},
           "bars45": _bars_until(bars45, ep["P0"]["candidateOpen"], end), "pivotsConfirmedUntilEnd": pivots,
           "decisions": decisions, "termination": ep["termination"], "request": ep.get("request"), "windowInBundle": win is not None}
    if tr:
        out["trade"] = records[tr["id"]]
        out["pathSeries"] = [{"t": t, "z": z} for t, z in series[tr["id"]]]
    return out


# ------------------------------------------------------------------ riepilogo


def _q(values: list[float]) -> dict:
    s = describe(values, Q3)
    return {"n": s["n"], "p10": s["p10"], "p50": s["p50"], "p90": s["p90"]}


def _contrib(rows: list[dict]) -> dict:
    e = [r["economics"] for r in rows]
    return {"n": len(rows), **{k: math.fsum(x[k] for x in e) for k in ("pricePnLRef", "slippage", "feeEntry", "feeExit", "funding", "net")}}


def summarize_records(records: list[dict], bundle: dict) -> dict:
    s = bundle["summary"]
    path = [r["path"] for r in records]
    held45 = [p["first45m"]["z"] for p in path if p["first45m"]["status"] == "HELD"]
    first45_status: dict[str, int] = {}
    for p in path:
        first45_status[p["first45m"]["status"]] = first45_status.get(p["first45m"]["status"], 0) + 1
    by_exit: dict[str, list] = {}
    by_stop: dict[str, list] = {}
    for r in records:
        by_exit.setdefault(r["exit"]["reason"], []).append(r)
        by_stop.setdefault(r["management"]["stopAtExitOrigin"], []).append(r)
    upd = [u for r in records for u in r["management"]["updatesDecided"]]
    upd_out: dict[str, int] = {}
    for u in upd:
        upd_out[u["outcome"]] = upd_out.get(u["outcome"], 0) + 1
    xs = [x for r in records for x in r["management"]["exitStructureRequests"]]
    eps = bundle["episodes"]
    at_t0: dict[str, int] = {}
    for e in eps:
        if e["termination"]["t"] == e["t0"]:
            at_t0[e["termination"]["code"]] = at_t0.get(e["termination"]["code"], 0) + 1
    rr = [e["plan"] for e in eps if e["termination"]["code"] == "ABSTAIN_REWARD_RISK"]
    ep_by_id = {e["id"]: e for e in eps}
    rejected = []
    for r in bundle["requests"]:
        if r["outcome"] != "REJECTED_PRICE":
            continue
        e = ep_by_id[r["episodeId"]]
        rejected.append({"episodeId": e["id"], "side": e["side"], "executeAt": r["executeAt"], "indicativeRatio": e["plan"]["ratio"],
                         "ratioAtOpen": r["ratio"], "openMoveOverA0": e["d"] * (r["Oref"] - e["plan"]["Ck"]) / e["A0"]})

    def period(t: dict) -> dict:
        tt = t["trades"]
        return {"trades": tt["n"], "net": tt["net"], "maxDrawdown": t["drawdown"]["maxDrawdown"], "concentration": tt["concentration"],
                "pricePnLRef": tt["pricePnLRef"], "stressNet": tt["stressNet"]}

    dev = s["tables"]["DEV"]
    return {
        "periods": {k: period(s["tables"][k]) for k in ("DEV", "2023", "2024")},
        "months": {m: period(t) for m, t in s["months"].items()},
        "distributions": {
            "first45mZ": {**_q(held45), "status": first45_status},
            "zMaxObserved": _q([p["zMaxObserved"] for p in path]), "zMinObserved": _q([p["zMinObserved"] for p in path]),
            "zExitReference": _q([p["zExitReference"] for p in path]), "givebackFromMaxObserved": _q([p["givebackFromMaxObserved"] for p in path]),
            "zTargetInitial": _q([p["zTargetInitial"] for p in path]), "minutesToMaxObserved": _q([p["minutesToMaxObserved"] for p in path]),
            "durationOver24h": _q([r["durationOver24h"] for r in records]), "R0OverE": _q([r["R0OverE"] for r in records]),
            "heldCloses": _q([p["heldCloses"] for p in path]),
            "zeroFavourableObserved": sum(1 for p in path if p["zMaxObserved"] == 0.0),
            "zMaxObservedAtLeast1": sum(1 for p in path if p["zMaxObserved"] >= 1.0),
            "zMaxObservedByExitReason": {k: _q([r["path"]["zMaxObserved"] for r in v]) for k, v in sorted(by_exit.items())},
            "costOverRisk": _q([(r["economics"]["slippage"] + r["economics"]["feeEntry"] + r["economics"]["feeExit"]) / r["economics"]["riskInitial"]
                                for r in records]),
        },
        "entry": {
            "triggerBeyondPrevOverA0": _q([r["trigger"]["beyondPrevExtreme"] / r["A0"] for r in records]),
            "triggerBodyOverA0": _q([r["trigger"]["bodyDirectional"] / r["A0"] for r in records]),
            "waitClosesFromT0": _q([r["waitClosesFromT0"] for r in records]), "depthAtTrigger": _q([r["depthAtTrigger"] for r in records]),
            "legAmplitudeOverA0": _q([r["legAmplitudeOverA0"] for r in records]), "indicativeRatio": _q([r["indicativeRatio"] for r in records]),
            "fillRatio": _q([r["fillRatio"] for r in records]),
            "structure45mAtCall": {v: sum(1 for r in records if str(r["structure45mAtCall"]) == v) for v in sorted({str(r["structure45mAtCall"]) for r in records})},
        },
        "abstentions": {
            "terminatedAtRecognitionClose": at_t0,
            "rewardRiskIndicativeRatio": {**_q([p["ratio"] for p in rr if p["ratio"] is not None]), "gainNotPositive": sum(1 for p in rr if p["gain"] <= 0)},
            "rejectedPrice": rejected,
        },
        "byExitReason": {k: _contrib(v) for k, v in sorted(by_exit.items())},
        "byStopAtExit": {k: _contrib(v) for k, v in sorted(by_stop.items())},
        "management": {"updatesDecided": len(upd), "updateOutcomes": upd_out,
                       "tradesWithDecidedUpdate": sum(1 for r in records if r["management"]["updatesDecided"]),
                       "tradesWithActivatedUpdate": sum(1 for r in records if r["management"]["updatesActivated"]),
                       "updatesRejected": sum(len(r["management"]["updatesRejected"]) for r in records),
                       "pivotsBeforeEntry": sum(r["management"]["pivotsBeforeEntry"] for r in records),
                       "exitStructureRequests": len(xs), "exitStructureOutcomes": {o: sum(1 for x in xs if x["outcome"] == o) for o in sorted({x["outcome"] for x in xs})}},
        "population": {"legs": dev["legs"], "legsByOutcome": dev["legsByOutcome"], "episodes": dev["episodes"],
                       "episodesByTermination": dev["episodesByTermination"], "calls": dev["calls"], "requests": dev["requests"],
                       "trades": dev["trades"]["n"]},
    }


def reconcile_records(records: list[dict], bundle: dict) -> dict:
    """Riconciliazione su tutti i record: ogni discrepanza è un errore, non una nota."""
    s = bundle["summary"]
    problems = []
    if (len(records), len(bundle["requests"]), len(bundle["episodes"])) != (78, 87, 814):
        problems.append(f"popolazione {len(records)}/{len(bundle['requests'])}/{len(bundle['episodes'])} != 78/87/814")
    net = math.fsum(r["economics"]["net"] for r in records)
    if net != s["reconciliation"]["net"] and abs(net - s["reconciliation"]["net"]) > 1e-9:
        problems.append(f"netto {net!r} != {s['reconciliation']['net']!r}")
    worst = max(abs(r["economics"]["identityResidual"]) for r in records)
    if worst > 1e-9:
        problems.append(f"identità dei costi: residuo {worst}")
    viol = [r["tradeId"] for r in records if r["path"]["ledgerViolations"] or r["path"]["missingMinutes"]]
    if viol:
        problems.append(f"percorso incoerente col ledger o minuti mancanti: {viol}")
    ordered = sorted(records, key=lambda r: r["entryTime"])
    overlap = [b["tradeId"] for a, b in zip(ordered, ordered[1:]) if b["entryTime"] < a["exit"]["accountingTime"]]
    if overlap:
        problems.append(f"operazioni sovrapposte: {overlap}")
    exits = s["tables"]["DEV"]["trades"]["exits"]
    mine = {k: sum(1 for r in records if r["exit"]["reason"] == k) for k in exits}
    if mine != exits:
        problems.append(f"motivi d'uscita {mine} != {exits}")
    if problems:
        raise AssertionError("; ".join(problems))
    return {"trades": len(records), "requests": len(bundle["requests"]), "episodes": len(bundle["episodes"]), "net": net,
            "netBundle": s["reconciliation"]["net"], "netEqualExact": net == s["reconciliation"]["net"], "identityMaxResidual": worst,
            "exits": mine, "noOverlap": True, "pathConsistentWithLedger": True}


def _csv(records: list[dict]) -> str:
    cols = ["tradeId", "episodeId", "side", "t0", "callTime", "entryTime", "P0", "P1", "A0", "legAmplitude", "legAmplitudeOverA0", "legBars",
            "depthAtTrigger", "barsSinceP1AtTrigger", "waitClosesFromT0", "structure45mAtCall", "structure1DAtCall", "S0", "T", "Estar",
            "indicativeRatio", "Eref", "E", "R0", "G0", "fillRatio", "R0OverE"]
    extra = {"exitReason": lambda r: r["exit"]["reason"], "exitMinute": lambda r: r["exit"]["minute"], "exitAccountingTime": lambda r: r["exit"]["accountingTime"],
             "Xref": lambda r: r["exit"]["Xref"], "intrabar": lambda r: r["exit"]["intrabar"], "durationMin": lambda r: r["durationMin"],
             "stopAtExitOrigin": lambda r: r["management"]["stopAtExitOrigin"], "stopAtExit": lambda r: r["management"]["stopAtExit"],
             "updatesDecided": lambda r: len(r["management"]["updatesDecided"]), "updatesActivated": lambda r: r["management"]["updatesActivated"],
             "first45mStatus": lambda r: r["path"]["first45m"]["status"], "first45mZ": lambda r: r["path"]["first45m"]["z"],
             "zMaxObserved": lambda r: r["path"]["zMaxObserved"], "minutesToMaxObserved": lambda r: r["path"]["minutesToMaxObserved"],
             "zMinObserved": lambda r: r["path"]["zMinObserved"], "zExitReference": lambda r: r["path"]["zExitReference"],
             "givebackFromMaxObserved": lambda r: r["path"]["givebackFromMaxObserved"], "zTargetInitial": lambda r: r["path"]["zTargetInitial"],
             "heldCloses": lambda r: r["path"]["heldCloses"]}
    econ = ["pricePnLRef", "slippage", "feeEntry", "feeExit", "funding", "net", "riskInitial", "stressNet"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols + list(extra) + econ)
    for r in records:
        w.writerow([("" if r[c] is None else r[c]) for c in cols] + [("" if f(r) is None else f(r)) for f in extra.values()]
                   + [r["economics"][k] for k in econ])
    return buf.getvalue()


def cmd_extract(data_dir: Path, argv: list[str] | None) -> int:
    bundle, sha_before = load_bundle(data_dir)
    out = paths(data_dir)["out"]
    sel_path = out / "examples-selection.json"
    sel = json.loads(sel_path.read_text(encoding="utf-8"))
    sel_sha = _sha256_file(sel_path)
    if sel["listSha256"] != sha256_bytes(canonical_json({"cases": sel["cases"], "emptyCategories": sel["emptyCategories"]})) or sel["bundleSha256"] != sha_before:
        raise InputMismatch("lista degli esempi non coerente con il bundle o con il proprio hash")
    cand = load_candidate()
    config_sha_before = _sha256_file(CONFIG_PATH)
    store, trade_report = load_trade(cand, data_dir, "DEV")  # zip verificati con manifest e fornitore; nessun mese oltre il DEV
    if store.end != cand.window("DEV")[1] or any(r["month"] >= "2025-01" for r in trade_report):
        raise InputMismatch("lo store supera la fine del DEV")
    bundle_months = {m["month"]: m["sha256"] for m in bundle["quality"]["trade"]["months"]}
    if {r["month"]: r["sha256"] for r in trade_report} != bundle_months:
        raise InputMismatch("archivi trade diversi da quelli registrati nel bundle")
    ep_idx = {e["id"]: i for i, e in enumerate(bundle["episodes"])}
    rq_idx = {r["episodeId"]: i for i, r in enumerate(bundle["requests"])}
    records, series = [], {}
    for i, t in enumerate(bundle["trades"]):
        e, r = bundle["episodes"][ep_idx[t["episodeId"]]], bundle["requests"][rq_idx[t["episodeId"]]]
        refs = {"bundle": f"trades[{i}]", "episode": f"episodes[{ep_idx[t['episodeId']]}]", "request": f"requests[{rq_idx[t['episodeId']]}]",
                "minutes": "raw/trade BTCUSDT-1m (minuti [entryTime, exit.minute))"}
        rec = trade_record(t, e, r, store, refs)
        records.append(rec)
        series[t["id"]] = path_facts(t, store)["series"]
    recon = reconcile_records(records, bundle)
    summary = summarize_records(records, bundle)
    by_id = {r["tradeId"]: r for r in records}
    bars45 = aggregate(store, BAR_MS)  # dal 2022-10-01: P0 del primo episodio è del 31 dicembre 2022
    timelines = [example_timeline(c, bundle, by_id, store, bars45, series) for c in sel["cases"]]
    files = {"trades.json": json.dumps(records, indent=1, ensure_ascii=False).encode("utf-8"), "trades.csv": _csv(records).encode("utf-8"),
             "examples-timelines.json": json.dumps(timelines, indent=1, ensure_ascii=False).encode("utf-8"),
             "summary.json": json.dumps({"reconciliation": recon, **summary}, indent=1, ensure_ascii=False).encode("utf-8")}
    for name, body in files.items():
        (out / name).write_bytes(body)
    trade_after = {r["month"]: _sha256_file(dirs(data_dir)["trade"] / r["file"]) for r in trade_report}
    sha_after = _sha256_file(paths(data_dir)["bundle"])
    unchanged = sha_after == sha_before and trade_after == bundle_months and _sha256_file(CONFIG_PATH) == config_sha_before \
        and _sha256_file(sel_path) == sel_sha
    prov = {"kind": "CAND001_D1_PROVENANCE", "command": " ".join(["python -m cand001.diagnosis", *(argv or ["extract"])]),
            "software": software_ref(), "createdAt": now_utc(), "runId": RUN_ID, "inputHash": bundle["run"]["inputHash"],
            "inputs": {"bundle": {"path": str(paths(data_dir)["bundle"]), "sha256Before": sha_before, "sha256After": sha_after},
                       "config": {"sha256Canonical": cand.hash, "fileSha256": config_sha_before},
                       "examplesSelection": {"sha256": sel_sha, "listSha256": sel["listSha256"]},
                       "tradeZips": {m: {"before": bundle_months[m], "after": trade_after[m]} for m in sorted(bundle_months)}},
            "inputsUnchanged": unchanged, "outputs": {n: sha256_bytes(b) for n, b in files.items()},
            "minutesRead": {"start": store.start, "end": store.end, "months": sorted(bundle_months)}}
    (out / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    if not unchanged:
        raise AssertionError("un input è cambiato durante l'estrazione")
    print(f"record {len(records)} | netto {recon['net']!r} | identità max residuo {recon['identityMaxResidual']:.2e} | casi {len(timelines)}")
    for n, h in prov["outputs"].items():
        print(f"  {n} {h}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cand001.diagnosis", description="CAND-001/D1: diagnosi offline della v1 sul DEV conservato.")
    parser.add_argument("command", choices=["select", "extract"])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)
    data_dir = args.data_dir.resolve()
    if args.command == "select":
        return cmd_select(data_dir)
    return cmd_extract(data_dir, argv)


if __name__ == "__main__":
    raise SystemExit(main())
