"""Comando MOVE-001: un'applicazione descrittiva sui dati locali già verificati.

PowerShell, dalla radice del checkout:
    $env:PYTHONPATH = "src"; python3.12 -m move001 run
Output fuori Git in <data-root>/MOVE-001/runs/<runId>. Gli output numerici non contengono orari né
commit (deterministici); provenienza, commit e orari stanno in provenance.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import time
from pathlib import Path

from obs001.acquire import _sha256_file, now_utc
from obs001.aggregate import aggregate
from obs001.cli import software_ref
from obs001.conventions import REPO_ROOT, sha256_bytes
from obs001.observe import observe

from . import ENGINE_VERSION
from .config import CONFIG_PATH, MONTHS, load_study, observation_conventions
from .consult import package
from .cycle import Cycle
from .data import input_hash, load_minutes
from .examples import select
from .summary import summarize
from .verify import verify

DEFAULT_ROOT = REPO_ROOT.parent / "algorithmic-trader-data"


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def dump(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def to_csv(rows: list[dict]) -> bytes:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if v is None else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
    return buf.getvalue().encode("utf-8")


def cmd_run(study, root: Path) -> Path:
    t0 = time.perf_counter()
    store, report = load_minutes(study, root)
    conv = observation_conventions(study)
    bars45, bars1d = aggregate(store, conv.bar_ms), aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    cy = Cycle(bars45, observed["45m"], observed["events"]["45m"], study.input_start, conv.bar_ms, study.end).run()
    summary = summarize(cy, study.study_start, study.end, conv.bar_ms)
    sel = select(cy.ledger, cy.refs, study.study_start, study.end)
    ih = input_hash(report)
    out = root / "MOVE-001" / "runs" / f"MOVE-001-v{study.raw['version']}-e{ENGINE_VERSION}-{ih[:10]}-{study.hash[:10]}"
    (out / "cases").mkdir(parents=True, exist_ok=True)
    identity = {"study": study.raw["id"], "version": study.raw["version"], "configHash": study.hash, "observationConventions": conv.hash,
                "engineVersion": ENGINE_VERSION, "inputHash": ih, "months": MONTHS, "minutes": store.counts(),
                "inputFiles": [{k: r[k] for k in ("month", "file", "sha256", "rows", "coverage")} for r in report]}
    files = {
        "identity.json": dump(identity),
        "ledger.json": dump(cy.ledger), "references.json": dump([r.as_dict() for r in cy.refs]), "structures.json": dump(cy.structures),
        "triples.json": dump(cy.triples), "closes.csv": to_csv(cy.closes), "summary.json": dump(summary),
        "references.csv": to_csv([{**{k: v for k, v in r.as_dict().items() if k not in ("Q", "B", "P0", "P1", "suspension", "archive", "closesByCondition")},
                                   "Q": r.Q["price"], "B": r.B["price"], "P0": r.P0["price"], "P1": r.P1["price"] if r.P1 else None,
                                   "suspensionReason": r.suspended["reason"] if r.suspended else None, "suspendedAt": r.suspended["t"] if r.suspended else None,
                                   "archiveReason": r.archived["reason"] if r.archived else "FINE_COPERTURA", "archivedAt": r.archived["t"] if r.archived else None,
                                   **{f"closes_{k}": v for k, v in r.closes.items()}} for r in cy.refs]),
    }
    sel["listSha256"] = sha256_bytes(dump({"cases": sel["cases"], "emptyCategories": sel["emptyCategories"]}))
    files["examples.json"] = dump(sel)
    run_ref = {"runId": out.name, "inputHash": ih, "engineVersion": ENGINE_VERSION}
    by_id = {r.id: r for r in cy.refs}
    chain = {"bars45": bars45, "bars1d": bars1d, "observed": observed}
    for n, c in enumerate(sel["cases"], 1):
        r = by_id[c["refId"]]
        files[f"cases/{n:02d}-{r.side}-{r.birth_t}.json"] = dump(package(c, r, cy.ledger, cy.structures, chain, store, conv, study, run_ref, report))
    for name, body in files.items():
        (out / name).write_bytes(body)
    outputs = {n: sha256_bytes(b) for n, b in files.items()}
    (out / "outputs.json").write_bytes(dump({"outputs": outputs}))
    prov = {"software": software_ref(), "python": platform.python_version(), "platform": platform.platform(), "finishedAt": now_utc(),
            "configFileSha256": _sha256_file(CONFIG_PATH), "command": "python -m move001 run", "seconds": round(time.perf_counter() - t0, 2)}
    (out / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    dev = summary["tables"]["DEV"]
    log(f"MOVE-001 {out.name} | nascite DEV {dev['births']['total']} | strutture {dev['structures']['byOutcome']} | casi {len(sel['cases'])} | vuote {sel['emptyCategories']}")
    log(f"  outputs.json {sha256_bytes((out / 'outputs.json').read_bytes())}")
    return out


def cmd_verify(study, root: Path) -> dict:
    """Riscontro degli invarianti su tutti i riferimenti: ricalcola la catena, confronta gli output con
    quelli registrati e scrive solo verify.json (fuori da outputs.json, che resta invariato)."""
    store, report = load_minutes(study, root)
    conv = observation_conventions(study)
    bars45, bars1d = aggregate(store, conv.bar_ms), aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    cy = Cycle(bars45, observed["45m"], observed["events"]["45m"], study.input_start, conv.bar_ms, study.end).run()
    out = root / "MOVE-001" / "runs" / f"MOVE-001-v{study.raw['version']}-e{ENGINE_VERSION}-{input_hash(report)[:10]}-{study.hash[:10]}"
    reg = json.loads((out / "outputs.json").read_text(encoding="utf-8"))["outputs"]
    if sha256_bytes(dump(cy.ledger)) != reg["ledger.json"] or sha256_bytes(dump([r.as_dict() for r in cy.refs])) != reg["references.json"]:
        raise AssertionError("ledger o riferimenti ricalcolati diversi da quelli registrati")
    res = {**verify(cy), "ledgerSha256": reg["ledger.json"], "referencesSha256": reg["references.json"], "software": software_ref(), "finishedAt": now_utc()}
    (out / "verify.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    log(f"verifica invarianti: {res['references']} riferimenti, {res['closes']} chiusure, violazioni {res['violations']}")
    return res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="move001", description="MOVE-001: applicazione descrittiva del ciclo sul DEV locale.")
    parser.add_argument("command", choices=["run", "verify"])
    parser.add_argument("--data-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    study = load_study()
    log(f"MOVE-001 | config {study.hash} | motore {ENGINE_VERSION} | mesi {MONTHS[0]}..{MONTHS[-1]} | Python {platform.python_version()}")
    if args.command == "run":
        cmd_run(study, args.data_root.resolve())
    else:
        cmd_verify(study, args.data_root.resolve())
    return 0
