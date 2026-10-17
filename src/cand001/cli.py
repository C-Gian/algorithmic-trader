"""Comandi CAND-001: acquire, check, run, report, all. Fase predefinita DEV (2023-2024).

PowerShell, dalla radice del checkout:
    $env:PYTHONPATH = "src"; python3.12 -m cand001 all
    $env:PYTHONPATH = "src"; python3.12 -m cand001 all --phase additional2025
    $env:PYTHONPATH = "src"; python3.12 -m cand001 run --phase app-check-2025-01
ADDITIONAL_2025 (confronto aggiuntivo già esposto, checkpoint Director registrato il 17 ottobre 2026):
osservazioni su tutto il prefisso dal 2022-10-01, valutazione [2025-01-01, 2026-01-01) da FLAT.
app-check-2025-01 (APP-001): profilo di collaudo [2025-01-01, 2025-02-01), solo dati già presenti;
check/run usano lo stesso percorso del servizio locale dell'app (pipeline.py).
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

from obs001.acquire import AcquisitionError, now_utc
from obs001.conventions import REPO_ROOT
from obs001.minutes import SchemaError
from trading_primitives.file_lock import FileLock

from . import ENGINE_VERSION
from .bundle import results_markdown
from .config import load_candidate
from .data import FundingNotCertified, acquire, dirs
from .pipeline import Events, check_inputs, execute
from .profiles import load_profiles

DEFAULT_DATA_DIR = REPO_ROOT.parent / "algorithmic-trader-data" / "CAND-001"
PHASES = {"dev": "DEV", "additional2025": "ADDITIONAL_2025", "app-check-2025-01": "APP_CHECK_2025_01"}
ACQUIRABLE = {"DEV", "ADDITIONAL_2025"}


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


class LogEvents(Events):
    """Il comando diretto non mostra l'avanzamento fine: solo i messaggi di sempre."""

    def log(self, message: str) -> None:
        log(message)


def cmd_acquire(cand, data_dir: Path, phase: str) -> int:
    log(f"acquisizione {phase} in {data_dir}")
    res = acquire(cand, data_dir, phase)
    code = 0
    for kind, man in res.items():
        counts = {}
        for status in (man["thisRun"].values() if "thisRun" in man else ["REUSED_OBS-001"] * len(man["files"])):
            counts[status] = counts.get(status, 0) + 1
        log(f"  {kind}: {len(man['files'])} file nel manifest, in questa fase {counts} | errori {len(man['errors'])}")
        for e in man["errors"]:
            log(f"    ERRORE {e['month']}: {e['error']}")
            code = 2
    return code


def cmd_check(cand, data_dir: Path, profile, economic: bool = False):
    log(f"controllo input {profile.id}")
    store, funding, mark, quality = check_inputs(cand, data_dir, profile, LogEvents(), economic)
    log(f"  trade: minuti {quality['trade']['totals']}")
    for r in quality["trade"]["months"]:
        anomalies = {k: r[k] for k in ("duplicatesIdentical", "duplicatesDiscordantMinutes", "outOfOrder", "outsideMonth", "corruptRows") if r[k]}
        if anomalies or r["coverage"]["valid"] != r["coverage"]["expected"]:
            log(f"    {r['month']}: validi {r['coverage']['valid']}/{r['coverage']['expected']} anomalie {anomalies}")
    s = quality["costs"]["funding"]["series"]
    log(f"  funding: {s['events']} eventi, intervalli {s['intervalsHours']} h, jitter max {s['jitterMaxMs']} ms, anomalie {len(s['anomalies'])}, "
        f"{'certificata' if s['certified'] else 'NON CERTIFICATA'}")
    for a in s["anomalies"][:10]:
        log(f"    funding: {a}")
    log(f"  mark: punti necessari {quality['costs']['mark']['pointsNeeded']}, disponibili {quality['costs']['mark']['pointsAvailable']}")
    return store, funding, mark, quality


def cmd_run(cand, data_dir: Path, profile, argv) -> Path | None:
    command = " ".join(["python -m cand001", *(argv or [])]) if argv is not None else ""
    # Stesso lock del worker del servizio APP-001: mai due calcoli sulla stessa cartella dati.
    (data_dir / "jobs").mkdir(parents=True, exist_ok=True)
    lock = FileLock(data_dir / "jobs" / "worker.lock")
    if not lock.acquire():
        log("BLOCCO: un altro backtest usa la stessa cartella dati (servizio dell'app o altro comando); riprova quando è concluso")
        return None
    try:
        out = execute(cand, data_dir, profile, LogEvents(), command=command)
    finally:
        lock.release()
    if out["status"] != "PUBLISHED":
        return None
    log(f"  risultato {out['runId']} | bundle sha256 {out['bundleSha256']} | inputHash {out['inputHash']} | configHash {out['configHash']}")
    return Path(out["runDir"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cand001", description="CAND-001: acquisizione, controllo, backtest e report.")
    parser.add_argument("command", choices=["acquire", "check", "run", "report", "all"])
    parser.add_argument("--phase", choices=list(PHASES), default="dev")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--run", help="ID del run per 'report' (predefinito: il più recente)")
    args = parser.parse_args(argv)
    phase = PHASES[args.phase]
    cand = load_candidate()
    profile = load_profiles(cand)[phase]
    data_dir = args.data_dir.resolve()
    log(f"CAND-001 | candidato {cand.raw['id']} {cand.raw['candidateVersion']} hash {cand.hash} | motore {ENGINE_VERSION} | "
        f"profilo {profile.id} | Python {platform.python_version()}")
    try:
        if args.command in ("acquire", "all") and phase not in ACQUIRABLE:
            log(f"BLOCCO: il profilo {profile.id} usa solo dati già presenti; nessuna acquisizione per questo profilo")
            return 2
        if args.command == "acquire":
            return cmd_acquire(cand, data_dir, phase)
        if args.command == "check":
            try:
                cmd_check(cand, data_dir, profile)
            except FundingNotCertified as e:
                log(f"BLOCCO: {e}")
                return 2
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
        return 0 if cmd_run(cand, data_dir, profile, argv) else 2
    except (AcquisitionError, SchemaError) as e:
        log(f"BLOCCO: {e}")
        return 2
