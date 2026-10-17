"""Comandi CAND-001: acquire, check, run, report, all. Fase predefinita DEV (2023-2024).

PowerShell, dalla radice del checkout:
    $env:PYTHONPATH = "src"; python3.12 -m cand001 all
La fase ADDITIONAL_2025 non si esegue da qui finché il Director non registra il congelamento.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import platform
import sys
import time
from pathlib import Path

from obs001.acquire import AcquisitionError, now_utc
from obs001.cli import software_ref
from obs001.conventions import REPO_ROOT, sha256_bytes
from obs001.minutes import SchemaError

from . import BUNDLE_SCHEMA, ENGINE_VERSION
from .backtest import run_window
from .bundle import build_bundle, results_markdown
from .config import load_candidate
from .data import acquire, dirs, input_hash, load_costs, load_trade, reused_identity
from .metrics import summarize

DEFAULT_DATA_DIR = REPO_ROOT.parent / "algorithmic-trader-data" / "CAND-001"
PHASES = {"dev": "DEV", "additional2025": "ADDITIONAL_2025"}


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def peak_memory_mb() -> float | None:
    if sys.platform != "win32":
        return None
    try:
        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return round(pmc.PeakWorkingSetSize / 1e6, 1)
    except Exception:  # noqa: BLE001 - misura facoltativa
        return None


def cmd_acquire(cand, data_dir: Path, phase: str) -> int:
    log(f"acquisizione {phase} in {data_dir}")
    res = acquire(cand, data_dir, phase)
    code = 0
    for kind, man in res.items():
        counts = {}
        for f in man["files"]:
            counts[f["cache"]] = counts.get(f["cache"], 0) + 1
        log(f"  {kind}: {len(man['files'])} file ({counts}) | errori {len(man['errors'])}")
        for e in man["errors"]:
            log(f"    ERRORE {e['month']}: {e['error']}")
            code = 2
    return code


def cmd_check(cand, data_dir: Path, phase: str):
    log(f"controllo input {phase}")
    t0 = time.perf_counter()
    store, trade = load_trade(cand, data_dir, phase)
    funding, mark, costs = load_costs(cand, data_dir, phase)
    totals = store.counts()
    log(f"  trade: minuti {totals}")
    for r in trade:
        anomalies = {k: r[k] for k in ("duplicatesIdentical", "duplicatesDiscordantMinutes", "outOfOrder", "outsideMonth", "corruptRows") if r[k]}
        if anomalies or r["coverage"]["valid"] != r["coverage"]["expected"]:
            log(f"    {r['month']}: validi {r['coverage']['valid']}/{r['coverage']['expected']} anomalie {anomalies}")
    s = costs["funding"]["series"]
    log(f"  funding: {s['events']} eventi, intervalli {s['intervalsHours']} h, jitter max {s['jitterMaxMs']} ms, anomalie {len(s['anomalies'])}")
    log(f"  mark: punti necessari {costs['mark']['pointsNeeded']}, disponibili {costs['mark']['pointsAvailable']}")
    quality = {"trade": {"months": trade, "totals": totals,
                         "initialization": store.counts(store.start, cand.window("DEV")[0]) if phase == "DEV" else None},
               "costs": costs, "identity": reused_identity(data_dir), "checkSeconds": round(time.perf_counter() - t0, 2)}
    (dirs(data_dir)["manifests"] / f"input-{phase}.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    return store, funding, mark, quality


def _slim_quality(q: dict) -> dict:
    trade = [{k: r[k] for k in ("month", "file", "sha256", "rows", "coverage", "duplicatesIdentical", "duplicatesDiscordantMinutes",
                               "outOfOrder", "outsideMonth", "corruptRows")} for r in q["trade"]["months"]]
    costs = q["costs"]
    return {"trade": {"months": trade, "totals": q["trade"]["totals"], "initialization": q["trade"]["initialization"]},
            "funding": {"files": [{k: f[k] for k in ("month", "file", "sha256", "rows", "corrupt", "outsideMonth")} for f in costs["funding"]["files"]],
                        "series": {k: v for k, v in costs["funding"]["series"].items()}},
            "mark": {"files": [{k: f[k] for k in ("month", "file", "sha256", "rows", "coverage")} for f in costs["mark"]["files"]],
                     "pointsNeeded": costs["mark"]["pointsNeeded"], "pointsAvailable": costs["mark"]["pointsAvailable"],
                     "missingForTau": costs["mark"]["missingForTau"]},
            "identity": q["identity"]}


def cmd_run(cand, data_dir: Path, phase: str, argv) -> Path | None:
    started = now_utc()
    t0 = time.perf_counter()
    store, funding, mark, quality = cmd_check(cand, data_dir, phase)
    t_check = time.perf_counter() - t0
    ih = input_hash(quality["trade"]["months"], quality["costs"])
    sw = software_ref()
    run_id = f"CAND-001-v{cand.raw['candidateVersion']}-e{ENGINE_VERSION}-{phase}-{ih[:10]}-{cand.hash[:10]}"
    log(f"backtest {run_id} (commit {sw['commit']}{' con modifiche locali' if sw['dirty'] else ''})")
    t1 = time.perf_counter()
    res = run_window(cand, store, cand.window(phase), funding, mark)
    t_run = time.perf_counter() - t1
    summary = summarize(res, cand, phase)
    run_ref = {"runId": run_id, "inputHash": ih, "engineVersion": ENGINE_VERSION, "candidateVersion": cand.raw["candidateVersion"],
               "configHash": cand.hash}
    bundle = build_bundle(cand, res, summary, _slim_quality(quality), run_ref, phase)
    body = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    out_hash = sha256_bytes(body)
    runs = dirs(data_dir)["runs"]
    run_dir = runs / run_id
    path = run_dir / "cand001-bundle.json"
    if path.exists() and sha256_bytes(path.read_bytes()) != out_hash:
        k = 2
        while (runs / f"{run_id}-r{k}").exists():
            k += 1
        log(f"  ATTENZIONE: bundle esistente diverso con lo stesso ID; nuovo run separato -r{k}")
        run_dir = runs / f"{run_id}-r{k}"
        path = run_dir / "cand001-bundle.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    if path.exists():
        log(f"  bundle già presente e identico ({out_hash[:16]}...): nessuna sovrascrittura")
    else:
        path.write_bytes(body)
    (run_dir / "results.md").write_text(results_markdown(summary, cand.econ["notionalUSDT"]), encoding="utf-8")
    (run_dir / "input-manifest.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    manifest = {
        "kind": "CAND001_RUN", "runId": run_dir.name, "phase": phase, "schema": BUNDLE_SCHEMA, "engineVersion": ENGINE_VERSION,
        "candidate": {"id": cand.raw["id"], "version": cand.raw["candidateVersion"], "configHash": cand.hash},
        "observationConventions": cand.raw["observations"]["conventionsHash"], "software": sw, "python": platform.python_version(),
        "platform": platform.platform(), "inputHash": ih, "outputs": {"bundle": {"file": path.name, "sha256": out_hash, "bytes": len(body)}},
        "counts": {"trades": len(res["ledger"].trades), "episodes": len(res["engine"].episodes), "legs": len(res["engine"].legs),
                   "decisions": len(res["engine"].decisions), "windows": len(bundle["windows"])},
        "reconciliation": summary["reconciliation"], "halted": summary["halted"],
        "timings": {"check_s": round(t_check, 2), "backtest_s": round(t_run, 2), "total_s": round(time.perf_counter() - t0, 2)},
        "peakMemoryMB": peak_memory_mb(), "startedAt": started, "finishedAt": now_utc(), "command": " ".join(argv or sys.argv),
    }
    stamp = manifest["finishedAt"].replace("-", "").replace(":", "")
    for name in (f"run-manifest-{stamp}.json", "run-manifest.json"):
        (run_dir / name).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"  bundle {path} | {len(body) / 1e6:.1f} MB | sha256 {out_hash[:16]}... | {manifest['timings']} | picco memoria {manifest['peakMemoryMB']} MB")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cand001", description="CAND-001: acquisizione, controllo, backtest e report.")
    parser.add_argument("command", choices=["acquire", "check", "run", "report", "all"])
    parser.add_argument("--phase", choices=list(PHASES), default="dev")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--run", help="ID del run per 'report' (predefinito: il più recente)")
    args = parser.parse_args(argv)
    phase = PHASES[args.phase]
    cand = load_candidate()
    data_dir = args.data_dir.resolve()
    log(f"CAND-001 | candidato {cand.raw['id']} {cand.raw['candidateVersion']} hash {cand.hash} | motore {ENGINE_VERSION} | Python {platform.python_version()}")
    if phase == "ADDITIONAL_2025":
        log("FASE NON ESEGUITA: ADDITIONAL_2025 richiede il checkpoint del Director dopo la diagnosi DEV e la registrazione del congelamento.")
        return 3
    try:
        if args.command == "acquire":
            return cmd_acquire(cand, data_dir, phase)
        if args.command == "check":
            cmd_check(cand, data_dir, phase)
            return 0
        if args.command == "report":
            runs = dirs(data_dir)["runs"]
            run_dir = runs / args.run if args.run else max((d for d in runs.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime, default=None)
            if run_dir is None:
                log("nessun run trovato")
                return 1
            bundle = json.loads((run_dir / "cand001-bundle.json").read_text(encoding="utf-8"))
            md = results_markdown(bundle["summary"], bundle["notionalUSDT"])
            (run_dir / "results.md").write_text(md, encoding="utf-8")
            print(md)
            return 0
        if args.command == "all":
            code = cmd_acquire(cand, data_dir, phase)
            if code:
                return code
        return 0 if cmd_run(cand, data_dir, phase, argv) else 2
    except (AcquisitionError, SchemaError) as e:
        log(f"BLOCCO: {e}")
        return 2
