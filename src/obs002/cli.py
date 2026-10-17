"""Comandi OBS-002: population (prima degli esiti), outcomes, all. Solo dati locali già conservati.

PowerShell, dalla radice del checkout:
    $env:PYTHONPATH = "src"; python3.12 -m obs002 population
    $env:PYTHONPATH = "src"; python3.12 -m obs002 outcomes
Output fuori Git in <data-root>/OBS-002/runs/<runId>. Gli output numerici non contengono orari né
commit (deterministici); provenienza, commit e orari stanno in provenance-*.json separati.
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
from obs001.conventions import REPO_ROOT, canonical_json, iso, sha256_bytes
from obs001.observe import observe
from obs001.outcomes import outcome_for

from . import ENGINE_VERSION
from .config import CONFIG_PATH, MONTHS, load_study, observation_conventions
from .consult import check_against_obs001, package
from .data import input_hash, load_minutes
from .examples import select
from .outcomes import outcome
from .population import Population
from .summary import summarize
from .tables import report_tables

DEFAULT_ROOT = REPO_ROOT.parent / "algorithmic-trader-data"


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def dump(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def chain(study, root: Path) -> dict:
    t0 = time.perf_counter()
    store, report = load_minutes(study, root)
    conv = observation_conventions(study)
    bars45, bars1d = aggregate(store, conv.bar_ms), aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    pop = Population(bars45, observed["45m"], observed["1D"], observed["events"]["45m"], study.input_start, conv.bar_ms, conv.day_ms,
                     study.study_start, study.end).run()
    return {"store": store, "report": report, "conv": conv, "bars45": bars45, "bars1d": bars1d, "observed": observed, "pop": pop,
            "seconds": round(time.perf_counter() - t0, 2)}


def population_body(pop) -> dict:
    return {"kind": "OBS002_POPULATION", "versions": [v.as_dict() for v in pop.versions], "groups": [g.as_dict() for g in pop.groups.values()],
            "events": pop.events, "attempts": pop.attempts}


def run_dir(root: Path, study, ih: str) -> Path:
    return root / "OBS-002" / "runs" / f"OBS-002-v{study.raw['version']}-e{ENGINE_VERSION}-{ih[:10]}-{study.hash[:10]}"


def identity(study, c: dict) -> dict:
    ih = input_hash(c["report"])
    return {"study": study.raw["id"], "studyVersion": study.raw["version"], "configHash": study.hash, "observationConventions": c["conv"].hash,
            "engineVersion": ENGINE_VERSION, "inputHash": ih, "months": MONTHS,
            "inputFiles": [{k: r[k] for k in ("month", "file", "sha256", "rows", "coverage")} for r in c["report"]],
            "minutes": c["store"].counts()}


def provenance(out: Path, name: str, extra: dict) -> None:
    body = {"software": software_ref(), "python": platform.python_version(), "platform": platform.platform(), "finishedAt": now_utc(),
            "configFileSha256": _sha256_file(CONFIG_PATH), **extra}
    (out / f"provenance-{name}.json").write_text(json.dumps(body, indent=2), encoding="utf-8")


def cmd_population(study, root: Path) -> Path:
    c = chain(study, root)
    ident = identity(study, c)
    out = run_dir(root, study, ident["inputHash"])
    out.mkdir(parents=True, exist_ok=True)
    body = dump(population_body(c["pop"]))
    pop_sha = sha256_bytes(body)
    (out / "population.json").write_bytes(body)
    manifest = {**ident, "populationSha256": pop_sha, "counts": {"versions": len(c["pop"].versions), "groups": len(c["pop"].groups),
                                                                  "attempts": len(c["pop"].attempts),
                                                                  "devAttempts": sum(1 for a in c["pop"].attempts if a["inStudy"])}}
    (out / "population-manifest.json").write_bytes(dump(manifest))
    provenance(out, "population", {"command": "python -m obs002 population", "seconds": c["seconds"]})
    log(f"popolazione {out.name} | sha256 {pop_sha} | {manifest['counts']} | identità {sha256_bytes(canonical_json(ident))}")
    return out


def _flat(prefix: str, x, row: dict) -> None:
    if isinstance(x, dict) and set(x) == {"v", "r"}:
        row[prefix] = x["v"] if x["v"] is not None else ""
        row[prefix + ".reason"] = x["r"] or ""
    elif isinstance(x, dict):
        for k, v in x.items():
            _flat(f"{prefix}.{k}" if prefix else k, v, row)
    elif isinstance(x, list):
        return
    else:
        row[prefix] = "" if x is None else x


def to_csv(rows: list[dict]) -> bytes:
    cols: list[str] = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def timeline(case: dict, attempt: dict, outcome_row: dict, pop, c: dict) -> dict:
    """Noto a t (versioni, barre chiuse, snapshot) separato dal seguito retrospettivo."""
    g = pop.groups[attempt["groupId"]]
    versions = [v.as_dict() for v in pop.versions if v.group_id == g.id and v.t0 <= attempt["t"]]
    p0 = attempt["version"]["P0"]["candidateOpen"]
    bars = [{"open": b.start, "o": b.o, "h": b.h, "l": b.l, "c": b.c} for b in c["bars45"] if p0 <= b.start and b.end <= attempt["t"]]
    prior = [a for a in pop.attempts if a["groupId"] == g.id and a["t"] < attempt["t"]]
    return {"attemptId": attempt["attemptId"], "categories": case["categories"],
            "knownAtT": {"t": attempt["t"], "tIso": iso(attempt["t"]), "groupVersionsSoFar": [{**v, "retiredAt": v["retiredAt"] if v["retiredAt"] is not None and v["retiredAt"] <= attempt["t"] else None,
                                                                                               "retireReason": v["retireReason"] if v["retiredAt"] is not None and v["retiredAt"] <= attempt["t"] else None,
                                                                                               "attempts": [x for x in v["attempts"] if int(x.split(':')[-1]) <= attempt["t"]]} for v in versions],
                          "priorAttemptsOfGroup": [{"attemptId": a["attemptId"], "t": a["t"]} for a in prior], "bars45SinceP0": bars, "attempt": attempt},
            "afterT": {"label": "A POSTERIORI", "outcome": outcome_row}}


def cmd_outcomes(study, root: Path) -> Path:
    c = chain(study, root)
    ident = identity(study, c)
    out = run_dir(root, study, ident["inputHash"])
    man = json.loads((out / "population-manifest.json").read_text(encoding="utf-8"))
    body = dump(population_body(c["pop"]))
    if sha256_bytes(body) != man["populationSha256"] or sha256_bytes(canonical_json(ident)) != sha256_bytes(canonical_json({k: man[k] for k in ident})):
        raise AssertionError("popolazione o identità diverse da quelle registrate prima degli esiti")
    if _sha256_file(out / "population.json") != man["populationSha256"]:
        raise AssertionError("population.json modificato dopo la registrazione")
    pop, store = c["pop"], c["store"]
    t1 = time.perf_counter()
    outs = {a["attemptId"]: outcome(store, a["t"], a["C"], a["snapshot"]["volatility"]["A"], a["d"], study.horizon_ms, study.end, study.marker_a)
            for a in pop.attempts if a["inStudy"]}
    checked = cross_check(pop, outs, c)
    summary = summarize(pop, outs, study)
    summary["checks"]["obs001FollowUpCrossCheck"] = checked
    dev = [a for a in pop.attempts if a["inStudy"]]
    sel = select(dev, outs)
    by_id = {a["attemptId"]: a for a in dev}
    timelines = [timeline(cs, by_id[cs["attemptId"]], outs[cs["attemptId"]], pop, c) for cs in sel["cases"]]
    sel["listSha256"] = sha256_bytes(canonical_json({"cases": sel["cases"], "emptyCategories": sel["emptyCategories"]}))
    files = {
        "outcomes.json": dump(outs), "summary.json": dump(summary), "examples.json": dump({**sel, "timelines": timelines}),
        "results-tables.md": report_tables(summary, sel).encode("utf-8"),
        "attempts-register.csv": to_csv([_row_causal(a) for a in dev]), "outcomes.csv": to_csv([_row_outcome(a, outs[a["attemptId"]]) for a in dev]),
        "versions.csv": to_csv([{k: v for k, v in vv.as_dict().items() if k not in ("P0", "P1", "attempts")} | {"P0.price": vv.p0["price"], "P0.candidateOpen": vv.p0["candidateOpen"],
                                "P1.price": vv.p1["price"], "P1.candidateOpen": vv.p1["candidateOpen"], "attempts": len(vv.attempts)} for vv in pop.versions]),
    }
    run_ref = {"runId": out.name, "inputHash": ident["inputHash"], "engineVersion": ENGINE_VERSION}
    cases_dir = out / "cases"
    cases_dir.mkdir(exist_ok=True)
    for n, cs in enumerate(sel["cases"], 1):
        a = by_id[cs["attemptId"]]
        pk = package(cs, a, outs[a["attemptId"]], c, store, c["conv"], study, run_ref, c["report"])
        files[f"cases/{n:02d}-{a['side']}-{a['t']}.json"] = dump(pk)
    for name, b in files.items():
        (out / name).write_bytes(b)
    hashes = {n: sha256_bytes(b) for n, b in files.items()}
    (out / "outputs.json").write_bytes(dump({"populationSha256": man["populationSha256"], "outputs": hashes}))
    provenance(out, "outcomes", {"command": "python -m obs002 outcomes", "seconds": round(time.perf_counter() - t1, 2) + c["seconds"]})
    log(f"esiti {out.name} | tentativi DEV {len(dev)} | casi {len(sel['cases'])} | vuote {sel['emptyCategories']} | listSha {sel['listSha256']}")
    log(f"  outputs.json {sha256_bytes((out / 'outputs.json').read_bytes())}")
    return out


def cross_check(pop, outs: dict, c: dict) -> int:
    """Ogni esito DEV confrontato con il seguito 24h OBS-001 esistente allo stesso istante."""
    n = 0
    for a in pop.attempts:
        if not a["inStudy"]:
            continue
        a_m = a["snapshot"]["volatility"]["A"]
        row = outcome_for(c["store"], c["conv"], a["t"], a["C"], a_m["v"], a_m["r"])
        check_against_obs001(a, outs[a["attemptId"]], row)
        n += 1
    return n


def _row_causal(a: dict) -> dict:
    s = a["snapshot"]
    row = {k: a[k] for k in ("attemptId", "groupId", "versionId", "ordinal", "priorAttemptsInInitialization", "side", "t")}
    row["tIso"] = iso(a["t"])
    row["C"] = a["C"]
    row["profile"] = s["profile"]["profile"]
    for k in ("P0", "P1"):
        row[f"{k}.price"], row[f"{k}.candidateOpen"] = a["version"][k]["price"], a["version"][k]["candidateOpen"]
    row["versionAvailableAt"], row["versionAction"], row["L"] = a["version"]["availableAt"], a["version"]["action"], a["version"]["L"]
    _flat("reaction", a["reaction"], row)
    _flat("trigger", a["trigger"], row)
    _flat("s45m", s["structure"]["s45m"], row)
    _flat("s1D", s["structure"]["s1D"], row)
    for side in ("nearestAhead", "nearestBehind"):
        lv = s["levels"][side]
        row[f"{side}.kind"] = lv["kind"] if lv else ""
        row[f"{side}.price"] = lv["price"] if lv else ""
        _flat(f"{side}.distOverA", lv["dist"] if lv else {"v": None, "r": "NONE"}, row)
    row["levelsAtC"] = "|".join(s["levels"]["atC"])
    for lv in s["levels"]["all"]:
        row[f"level.{lv['kind']}.price"] = "" if lv["price"] is None else lv["price"]
        _flat(f"level.{lv['kind']}.distOverA", lv.get("dist") or {"v": None, "r": lv.get("reason")}, row)
    _flat("avg", {k: v for k, v in s["averages"].items()}, row)
    _flat("volume", s["volume"], row)
    _flat("volatility", s["volatility"], row)
    fib = s["fibonacci"]
    row["fib.version"], row["fib.available"] = fib["version"], fib["available"]
    if fib["available"]:
        row["fib.relation"], row["fib.sameAsContext"], row["fib.u"], row["fib.r"] = fib["relation"], fib["sameAsContext"], fib["u"], fib["r"]
        row["fib.P0.price"], row["fib.P1.price"] = fib["anchors"]["P0"]["price"], fib["anchors"]["P1"]["price"]
        for lv in fib["levels"]:
            _flat(f"fib.{lv['type'][:4]}.{lv['ratio']}.distOverA", lv["dist"], row)
    else:
        row["fib.reason"] = fib["reason"]
    return row


def _row_outcome(a: dict, o: dict) -> dict:
    row = {"attemptId": a["attemptId"], "t": a["t"], "complete": o["complete"], "flags": "|".join(o["flags"]), "class": o["class"] or ""}
    for k in ("final", "favourable", "adverse", "C", "A", "Cend", "maxHigh", "maxHighFirstMinute", "minLow", "minLowFirstMinute"):
        row[k] = "" if o[k] is None else o[k]
    for k in ("contactF", "contactA"):
        row[f"{k}.minute"] = o[k]["minute"] if o[k] else ""
        row[f"{k}.atOpen"] = o[k]["atOpen"] if o[k] else ""
    row["coverage.minutesValidContiguous"] = o["coverage"]["minutesValidContiguous"]
    row["partial"] = bool(o["partial"])
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="obs002", description="OBS-002: popolazione causale, seguito 24h, tabelle ed esempi sul DEV.")
    parser.add_argument("command", choices=["population", "outcomes", "all"])
    parser.add_argument("--data-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    study = load_study()
    root = args.data_root.resolve()
    log(f"OBS-002 | config {study.hash} | motore {ENGINE_VERSION} | mesi {MONTHS[0]}..{MONTHS[-1]} | Python {platform.python_version()}")
    if args.command in ("population", "all"):
        cmd_population(study, root)
    if args.command in ("outcomes", "all"):
        cmd_outcomes(study, root)
    return 0
