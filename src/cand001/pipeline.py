"""Percorso applicativo unico di un backtest CAND-001: controllo input → aggregati/osservazioni →
run_window → riepilogo/bundle → pubblicazione. Lo usano sia il comando diretto (cli.py) sia il
servizio locale APP-001: stessi dati, stesse funzioni, stesso bundle.

Gli eventi di avanzamento (Events) sono facoltativi e separati dai dati: senza eventi il percorso è
quello diretto di sempre. Un evento può interrompere il lavoro sollevando Cancelled; fino a
publishing() nessun file compare in runs/. La pubblicazione scrive prima in una cartella di staging
fuori da runs/ e poi sposta i file con os.replace, run-manifest per ultimo: un risultato è valido
solo se il suo run-manifest esiste. Date, ID d'esecuzione e progresso restano fuori dal bundle.
"""

from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import sys
import time
from pathlib import Path

from obs001.acquire import now_utc
from obs001.cli import software_ref
from obs001.conventions import sha256_bytes

from . import BUNDLE_SCHEMA, ENGINE_VERSION
from .backtest import observe_store, run_window
from .bundle import build_bundle, results_markdown
from .config import Candidate
from .data import FundingNotCertified, dirs, economic_inputs, input_hash, load_costs, load_trade, phase_inputs, reused_identity
from .metrics import summarize
from .profiles import Profile

BUNDLE_FILE = "cand001-bundle.json"
RUN_MANIFEST = "run-manifest.json"


class Cancelled(Exception):
    """Annullamento cooperativo richiesto: il lavoro si ferma al punto di controllo successivo."""


class Events:
    """Avanzamento facoltativo. stage() all'inizio di ogni fase, tick() durante i loop (può sollevare
    Cancelled), publishing() subito prima della pubblicazione: dopo, il risultato viene pubblicato."""

    def stage(self, name: str, **info) -> None:  # noqa: D401 - interfaccia vuota
        pass

    def tick(self, name: str, **info) -> None:
        pass

    def log(self, message: str) -> None:
        pass

    def publishing(self) -> None:
        pass


def peak_memory_mb() -> float | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p  # handle a 64 bit: senza restype viene troncato
        k32.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
        if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.PeakWorkingSetSize / 1e6, 1)
    except Exception:  # noqa: BLE001 - misura facoltativa
        return None


def input_plan(cand: Candidate, profile: Profile) -> dict:
    """File richiesti dal profilo, per tipo: trade dal 2022-10-01 alla fine della finestra (prefisso
    osservativo), funding e mark della sola finestra valutata."""
    plan = phase_inputs(cand, profile.phase, profile.window)
    return {"trade": plan["observe"], "reuseObs": plan["reuseObs"], "funding": plan["funding"], "mark": plan["mark"]}


def check_inputs(cand: Candidate, data_dir: Path, profile: Profile, events: Events | None = None, economic: bool = False):
    """Controllo e caricamento degli input del profilo. Con economic=True funding non certificato
    solleva FundingNotCertified dopo aver scritto il rapporto di qualità."""
    ev = events or Events()
    t0 = time.perf_counter()
    plan = input_plan(cand, profile)
    files = [{"kind": k, "month": m} for k in ("trade", "funding", "mark") for m in plan[k]]
    ev.stage("check", filesExpected=len(files), files=files, reuseObs=plan["reuseObs"])
    ev.log(f"  piano: osservazione {len(plan['trade'])} mesi trade {plan['trade'][0]}..{plan['trade'][-1]} "
           f"(di cui {len(plan['reuseObs'])} da OBS-001), funding/mark {len(plan['funding'])} mesi della finestra")

    def tick(event: str, **info) -> None:
        ev.tick("check", event=event, **info)

    store, trade = load_trade(cand, data_dir, profile.phase, profile.window, tick=tick)
    blocked = None
    try:
        loader = economic_inputs if economic else load_costs
        funding, mark, costs = loader(cand, data_dir, profile.phase, window=profile.window, tick=tick)
    except FundingNotCertified as e:
        blocked, costs = e, e.report
        funding, mark = [], {}
    totals = store.counts()
    quality = {"trade": {"months": trade, "totals": totals, "initialization": store.counts(store.start, profile.window[0])},
               "costs": costs, "identity": reused_identity(data_dir), "checkSeconds": round(time.perf_counter() - t0, 2)}
    (dirs(data_dir)["manifests"] / f"input-{profile.id}.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    if blocked is not None:
        raise blocked
    return store, funding, mark, quality


def slim_quality(q: dict) -> dict:
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


def run_id_for(cand: Candidate, profile: Profile, ih: str) -> str:
    return f"CAND-001-v{cand.raw['candidateVersion']}-e{ENGINE_VERSION}-{profile.id}-{ih[:10]}-{cand.hash[:10]}"


def _write_staged(folder: Path, name: str, body: bytes) -> Path:
    path = folder / name
    path.write_bytes(body)
    return path


def _replace(src: Path, dst: Path) -> None:
    """os.replace con pochi tentativi: su Windows un lettore esterno può tenere il file per un attimo."""
    for attempt in range(10):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.05)


def execute(cand: Candidate, data_dir: Path, profile: Profile, events: Events | None = None, command: str = "",
            execution: dict | None = None, staging: Path | None = None) -> dict:
    """Esegue il profilo e pubblica il risultato. Ritorna l'esito; solleva Cancelled se annullato prima
    della pubblicazione e AcquisitionError/SchemaError per dati mancanti o non interpretabili."""
    ev = events or Events()
    started = now_utc()
    t0 = time.perf_counter()
    try:
        # R1-A: qualità funding vincolante, nessun ledger né netto se la serie non è certificata.
        store, funding, mark, quality = check_inputs(cand, data_dir, profile, ev, economic=True)
    except FundingNotCertified as e:
        ev.log(f"BLOCCO: {e} Rapporto di qualità in manifests/input-{profile.id}.json")
        return {"status": "BLOCKED_FUNDING", "message": str(e), "qualityReport": f"manifests/input-{profile.id}.json"}
    t_check = time.perf_counter() - t0
    ih = input_hash(quality["trade"]["months"], quality["costs"])
    sw = software_ref()
    run_id = run_id_for(cand, profile, ih)
    ev.log(f"backtest {run_id} (commit {sw['commit']}{' con modifiche locali' if sw['dirty'] else ''})")

    t1 = time.perf_counter()
    ev.stage("init", minutes=store.n, minutesValid=quality["trade"]["totals"]["valid"],
             prefixMinutes=store.index(profile.window[0]), windowMinutes=store.n - store.index(profile.window[0]))
    obs = observe_store(store, tick=lambda step, done, total: ev.tick("init", step=step, done=done, total=total))
    bars_window = (profile.window[1] - profile.window[0]) // obs["conv"].bar_ms
    ev.stage("simulate", closesTotal=bars_window, bars45=len(obs["bars45"]), bars1D=len(obs["bars1d"]))
    res = run_window(cand, store, profile.window, funding, mark, obs=obs, tick=lambda state: ev.tick("simulate", **state))
    t_run = time.perf_counter() - t1

    ev.stage("save")
    summary = summarize(res, cand, profile.id)
    ev.tick("save", step="summary")
    run_ref = {"runId": run_id, "inputHash": ih, "engineVersion": ENGINE_VERSION, "candidateVersion": cand.raw["candidateVersion"],
               "configHash": cand.hash}
    bundle = build_bundle(cand, res, summary, slim_quality(quality), run_ref, profile.id, profile.ref())
    body = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    out_hash = sha256_bytes(body)
    ev.tick("save", step="bundle", bytes=len(body))

    runs = dirs(data_dir)["runs"]
    run_dir = runs / run_id
    if (run_dir / BUNDLE_FILE).exists() and sha256_bytes((run_dir / BUNDLE_FILE).read_bytes()) != out_hash:
        k = 2
        while (runs / f"{run_id}-r{k}").exists():
            k += 1
        ev.log(f"  ATTENZIONE: bundle esistente diverso con lo stesso ID; nuovo run separato -r{k}")
        run_dir = runs / f"{run_id}-r{k}"
    reused = (run_dir / BUNDLE_FILE).exists()

    stage_dir = staging or (data_dir / "staging" / f"direct-{now_utc().replace('-', '').replace(':', '')}-{secrets.token_hex(3)}")
    stage_dir.mkdir(parents=True, exist_ok=True)
    try:
        if not reused:
            _write_staged(stage_dir, BUNDLE_FILE, body)
        _write_staged(stage_dir, "results.md", results_markdown(summary, cand.econ["notionalUSDT"]).encode("utf-8"))
        _write_staged(stage_dir, "input-manifest.json", json.dumps(quality, indent=2).encode("utf-8"))
        ev.tick("save", step="staged")
        manifest = {
            "kind": "CAND001_RUN", "runId": run_dir.name, "phase": profile.id, "profile": profile.ref(), "schema": BUNDLE_SCHEMA,
            "engineVersion": ENGINE_VERSION,
            "candidate": {"id": cand.raw["id"], "version": cand.raw["candidateVersion"], "configHash": cand.hash},
            "observationConventions": cand.raw["observations"]["conventionsHash"], "software": sw, "python": platform.python_version(),
            "platform": platform.platform(), "inputHash": ih, "outputs": {"bundle": {"file": BUNDLE_FILE, "sha256": out_hash, "bytes": len(body)}},
            "counts": {"trades": len(res["ledger"].trades), "episodes": len(res["engine"].episodes), "legs": len(res["engine"].legs),
                       "decisions": len(res["engine"].decisions), "windows": len(bundle["windows"]), "requests": len(res["ledger"].requests)},
            "reconciliation": summary["reconciliation"], "halted": summary["halted"],
            "timings": {"check_s": round(t_check, 2), "backtest_s": round(t_run, 2), "total_s": round(time.perf_counter() - t0, 2)},
            "peakMemoryMB": peak_memory_mb(), "startedAt": started, "command": command or " ".join(sys.argv),
            "execution": execution or {"via": "DIRECT"},
        }
        ev.publishing()  # da qui l'annullamento non si applica più: il risultato completo viene pubblicato
        manifest["finishedAt"] = now_utc()
        mbody = json.dumps(manifest, indent=2).encode("utf-8")
        stamp = manifest["finishedAt"].replace("-", "").replace(":", "")
        _write_staged(stage_dir, f"run-manifest-{stamp}.json", mbody)
        _write_staged(stage_dir, RUN_MANIFEST, mbody)
        run_dir.mkdir(parents=True, exist_ok=True)
        if reused:
            ev.log(f"  bundle già presente e identico ({out_hash[:16]}...): nessuna sovrascrittura")
        else:
            _replace(stage_dir / BUNDLE_FILE, run_dir / BUNDLE_FILE)
        for name in ("results.md", "input-manifest.json", f"run-manifest-{stamp}.json", RUN_MANIFEST):
            _replace(stage_dir / name, run_dir / name)
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)
    ev.log(f"  bundle {run_dir / BUNDLE_FILE} | {len(body) / 1e6:.1f} MB | sha256 {out_hash[:16]}... | {manifest['timings']} | "
           f"picco memoria {manifest['peakMemoryMB']} MB")
    return {"status": "PUBLISHED", "runId": run_dir.name, "runDir": str(run_dir), "bundleSha256": out_hash, "bundleBytes": len(body),
            "reusedIdenticalBundle": reused, "complete": bool(summary["reconciliation"]["windowComplete"]), "inputHash": ih,
            "configHash": cand.hash, "engineVersion": ENGINE_VERSION, "profile": profile.ref(), "counts": manifest["counts"],
            "halted": summary["halted"], "net": summary["reconciliation"]["net"], "timings": manifest["timings"]}
