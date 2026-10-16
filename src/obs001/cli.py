"""Comandi espliciti OBS-001: acquire, check, process, summarize, all.

Esempio (PowerShell, dalla radice del checkout):
    $env:PYTHONPATH = "src"; python3.12 -m obs001 all
La cartella dati predefinita è la sorella del checkout: ..\\algorithmic-trader-data\\OBS-001.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from . import BUNDLE_SCHEMA, ENGINE_VERSION
from .acquire import AcquisitionError, acquire_all, now_utc, paths
from .bundle import build_bundle, summary_markdown
from .conventions import REPO_ROOT, canonical_json, load_conventions, sha256_bytes
from .inputs import InputBlocked, check_inputs
from .pipeline import run_chain

DEFAULT_DATA_DIR = REPO_ROOT.parent / "algorithmic-trader-data" / "OBS-001"


def software_ref() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    dirty = git("status", "--porcelain", "--", "src", "config")
    return {"commit": git("rev-parse", "HEAD") or None, "dirty": bool(dirty)}


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def cmd_acquire(conv, data_dir: Path) -> int:
    log(f"acquisizione in {data_dir}")
    manifest = acquire_all(conv, data_dir)
    for f in manifest["files"]:
        log(f"  {f['file']}: {f['cache']} | {f['size']} byte | sha256 {f['sha256'][:16]}... | checksum OK")
    for e in manifest["errors"]:
        log(f"  ERRORE {e['month']}: {e['error']}")
    meta = manifest["instrumentMetadata"]
    log(f"  metadati strumento: {'OK' if meta.get('ok') else 'NON VERIFICATI'} {meta.get('error') or ''}")
    log(f"  termini: {'salvati' if manifest['terms'].get('ok') else manifest['terms'].get('error')}")
    if manifest["blocked"]:
        log("BLOCCO: acquisizione non affidabile (vedi manifests/acquisition.json)")
        return 2
    return 0


def cmd_check(conv, data_dir: Path):
    log("controllo input")
    try:
        store, manifest = check_inputs(conv, data_dir)
    except InputBlocked as e:
        log(f"BLOCCO: {e}")
        if e.manifest:
            (paths(data_dir)["manifests"] / "input-blocked.json").write_text(json.dumps(e.manifest, indent=2), encoding="utf-8")
        return None, None
    (paths(data_dir)["manifests"] / "input.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    t = manifest["totals"]
    log(f"  minuti input {t['input']} | inizializzazione {t['initialization']} | studio {t['study']}")
    for f in manifest["files"]:
        a = [k for k in ("duplicatesIdentical", "duplicatesDiscordantMinutes", "outOfOrder", "outsideMonth", "corruptRows") if f[k]]
        log(f"  {f['month']}: righe {f['rows']} | validi {f['coverage']['valid']}/{f['coverage']['expected']} | anomalie {', '.join(f'{k}={f[k]}' for k in a) or 'nessuna'}")
    log(f"  inputHash {manifest['inputHash']}")
    return store, manifest


def cmd_process(conv, data_dir: Path, store=None, manifest=None, argv=None) -> Path | None:
    started = now_utc()
    timings = {}
    t0 = time.perf_counter()
    if store is None:
        store, manifest = cmd_check(conv, data_dir)
        if store is None:
            return None
    timings["check_s"] = round(time.perf_counter() - t0, 3)
    sw = software_ref()
    run_id = f"OBS-001-v1-e{ENGINE_VERSION}-{manifest['inputHash'][:10]}-{conv.hash[:10]}"
    run_ref = {"runId": run_id, "inputHash": manifest["inputHash"], "softwareCommit": sw["commit"], "softwareDirty": sw["dirty"]}
    log(f"elaborazione {run_id} (commit {sw['commit']}{' con modifiche locali' if sw['dirty'] else ''})")
    t1 = time.perf_counter()
    chain = run_chain(store, conv)
    timings["chain_s"] = round(time.perf_counter() - t1, 3)
    bundle = build_bundle(conv, chain, manifest, run_ref)
    body = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    out_hash = sha256_bytes(body)
    run_dir = paths(data_dir)["runs"] / run_id
    bundle_path = run_dir / "obs001-bundle.json"
    if bundle_path.exists():
        existing = sha256_bytes(bundle_path.read_bytes())
        if existing == out_hash:
            log(f"  bundle già presente e identico ({out_hash[:16]}...): nessuna sovrascrittura")
        else:
            k = 2
            while (paths(data_dir)["runs"] / f"{run_id}-r{k}").exists():
                k += 1
            log(f"  ATTENZIONE: bundle esistente diverso con lo stesso ID; nuovo run separato -r{k}")
            run_dir = paths(data_dir)["runs"] / f"{run_id}-r{k}"
            bundle_path = run_dir / "obs001-bundle.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    if not bundle_path.exists():
        bundle_path.write_bytes(body)
    (run_dir / "summary.md").write_text(summary_markdown(chain["summary"]), encoding="utf-8")
    (run_dir / "input-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    timings["total_s"] = round(time.perf_counter() - t0, 3)
    run_manifest = {
        "kind": "OBS001_RUN", "runId": run_dir.name, "schema": BUNDLE_SCHEMA, "conventions": {"id": conv.raw["id"], "hash": conv.hash},
        "engineVersion": ENGINE_VERSION, "software": sw, "python": platform.python_version(), "platform": platform.platform(),
        "inputHash": manifest["inputHash"], "inputManifest": "input-manifest.json",
        "outputs": {"bundle": {"file": bundle_path.name, "sha256": out_hash, "bytes": len(body)}},
        "counts": {"bars45m": len(chain["bars45"]), "bars1D": len(chain["bars1d"]), "origins": len(chain["rows"]),
                   "events45m": len(chain["observed"]["events"]["45m"]), "events1D": len(chain["observed"]["events"]["1D"])},
        "checks": chain["summary"]["checks"], "timings": timings, "startedAt": started, "finishedAt": now_utc(),
        "command": " ".join(argv or sys.argv),
    }
    (run_dir / "run-manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    log(f"  bundle {bundle_path} | {len(body) / 1e6:.1f} MB | sha256 {out_hash[:16]}... | {timings}")
    return run_dir


def cmd_summarize(data_dir: Path, run: str | None) -> int:
    runs = paths(data_dir)["runs"]
    run_dir = runs / run if run else max((d for d in runs.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime, default=None)
    if run_dir is None or not (run_dir / "obs001-bundle.json").exists():
        log("nessun run con bundle trovato")
        return 1
    bundle = json.loads((run_dir / "obs001-bundle.json").read_text(encoding="utf-8"))
    md = summary_markdown(bundle["retrospective"]["summary"])
    (run_dir / "summary.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="obs001", description="OBS-001: acquisizione, controllo, elaborazione e riepilogo.")
    parser.add_argument("command", choices=["acquire", "check", "process", "summarize", "all"])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--run", help="ID del run per 'summarize' (predefinito: il più recente)")
    args = parser.parse_args(argv)
    conv = load_conventions()
    data_dir = args.data_dir.resolve()
    log(f"OBS-001 | convenzioni {conv.raw['id']} hash {conv.hash} | motore {ENGINE_VERSION} | Python {platform.python_version()}")
    try:
        if args.command == "acquire":
            return cmd_acquire(conv, data_dir)
        if args.command == "check":
            return 0 if cmd_check(conv, data_dir)[0] is not None else 2
        if args.command == "process":
            return 0 if cmd_process(conv, data_dir, argv=argv) else 2
        if args.command == "summarize":
            return cmd_summarize(data_dir, args.run)
        code = cmd_acquire(conv, data_dir)
        if code:
            return code
        store, manifest = cmd_check(conv, data_dir)
        if store is None:
            return 2
        return 0 if cmd_process(conv, data_dir, store, manifest, argv=argv) else 2
    except AcquisitionError as e:
        log(f"BLOCCO: {e}")
        return 2
