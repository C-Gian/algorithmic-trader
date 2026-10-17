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
import json
from pathlib import Path

from obs001.acquire import _sha256_file, now_utc
from obs001.conventions import REPO_ROOT, canonical_json, iso, sha256_bytes

from .config import load_candidate

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cand001.diagnosis", description="CAND-001/D1: diagnosi offline della v1 sul DEV conservato.")
    parser.add_argument("command", choices=["select"])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)
    data_dir = args.data_dir.resolve()
    if args.command == "select":
        return cmd_select(data_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
