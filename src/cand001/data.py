"""Dati CAND-001: klines negoziate, fundingRate e markPriceKlines Binance Vision (solo fasi autorizzate).

Download seriali con checksum del fornitore e file temporaneo (funzioni OBS-001); cache verificata
riusata; versioni precedenti conservate. Manifest distinti per tipo. Funding e mark servono solo ai
costi: non sono input delle decisioni. Nessun rate o mark mancante diventa zero.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import zipfile
from pathlib import Path

from obs001.acquire import AcquisitionError, _sha256_file, http_get, now_utc, parse_checksum
from obs001.conventions import canonical_json, parse_utc, sha256_bytes
from obs001.inputs import month_bounds
from obs001.minutes import VALID, MinuteStore, SchemaError, parse_csv_text, read_month_zip

from .config import Candidate, months_between

KINDS = {"trade": "trade", "funding": "fundingRate", "mark": "markPrice"}
FUNDING_COLUMNS = ["calc_time", "funding_interval_hours", "last_funding_rate"]
MS_MIN = 60_000


def dirs(data_dir: Path) -> dict[str, Path]:
    d = {"raw": data_dir / "raw", "partial": data_dir / "raw" / ".partial", "superseded": data_dir / "raw" / "superseded",
         "meta": data_dir / "meta", "manifests": data_dir / "manifests", "runs": data_dir / "runs"}
    for kind in KINDS:
        d[kind] = data_dir / "raw" / kind
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


def phase_months(cand: Candidate, phase: str) -> dict[str, list[str]]:
    """Mesi necessari a una fase. DEV: trade dall'inizializzazione a fine 2024; funding/mark solo 2023-2024."""
    start, end = cand.window(phase)
    trade = months_between(cand.input_start, end)
    if phase == "ADDITIONAL_2025":
        trade = months_between(start, end)
    costs = months_between(start, end)
    return {"trade": trade, "funding": costs, "mark": costs}


def url_for(cand: Candidate, kind: str, month: str) -> str:
    return cand.raw["data"][KINDS[kind]]["urlTemplate"].format(month=month)


def acquire_file(url: str, target_dir: Path, d: dict[str, Path], previous: dict) -> dict:
    name = url.rsplit("/", 1)[1]
    entry = {"url": url, "checksumUrl": url + ".CHECKSUM", "file": name}
    body, meta = http_get(entry["checksumUrl"])
    provider = parse_checksum(body.decode("utf-8"), name)
    (target_dir / (name + ".CHECKSUM")).write_bytes(body)
    entry.update(providerChecksum=provider, checksumFetchedAt=now_utc(), checksumHttp=meta)
    target = target_dir / name
    if target.exists():
        local = _sha256_file(target)
        if local == provider:
            entry.update(sha256=local, size=target.stat().st_size, checksumOk=True, cache="REUSED", downloadedAt=previous.get(local))
            return entry
        keep = d["superseded"] / f"{target_dir.name}-{name}.{local[:12]}"
        os.replace(target, keep)
        entry["supersededLocal"] = {"path": str(keep), "sha256": local}
    data, meta = http_get(url)
    tmp = d["partial"] / (name + ".part")
    tmp.write_bytes(data)
    local = _sha256_file(tmp)
    entry.update(downloadedAt=now_utc(), http=meta, size=len(data), sha256=local)
    if local != provider:
        entry["checksumOk"] = False
        raise AcquisitionError(f"{name}: SHA256 locale {local} diverso dal checksum del fornitore {provider}")
    os.replace(tmp, target)
    entry.update(checksumOk=True, cache="DOWNLOADED")
    return entry


def write_manifest(folder: Path, stem: str, data: dict) -> None:
    stamp = now_utc().replace("-", "").replace(":", "")
    body = json.dumps(data, indent=2, ensure_ascii=False)
    (folder / f"{stem}-{stamp}.json").write_text(body, encoding="utf-8")
    (folder / f"{stem}.json").write_text(body, encoding="utf-8")


def acquire(cand: Candidate, data_dir: Path, phase: str) -> dict:
    d = dirs(data_dir)
    out = {}
    for kind, months in phase_months(cand, phase).items():
        prev_path = d["manifests"] / f"acquisition-{kind}.json"
        prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
        downloaded = {f["sha256"]: f.get("downloadedAt") for f in prev.get("files", []) if f.get("sha256")}
        files = {f["month"]: f for f in prev.get("files", [])}
        errors = []
        for month in months:
            try:
                entry = acquire_file(url_for(cand, kind, month), d[kind], d, downloaded)
                files[month] = {"month": month, "kind": kind, **entry}
            except AcquisitionError as e:
                errors.append({"month": month, "error": str(e)})
        manifest = {"kind": f"CAND001_ACQUISITION_{kind.upper()}", "candidate": cand.raw["id"], "configHash": cand.hash,
                    "phase": phase, "finishedAt": now_utc(), "files": [files[m] for m in sorted(files)], "errors": errors,
                    "blocked": bool(errors)}
        write_manifest(d["manifests"], f"acquisition-{kind}", manifest)
        out[kind] = manifest
    return out


# ------------------------------------------------------------------- controllo


def _verified_zip(d: dict[str, Path], kind: str, manifest: dict, month: str) -> Path:
    f = next((x for x in manifest.get("files", []) if x["month"] == month), None)
    if f is None:
        raise AcquisitionError(f"{kind} {month}: file non acquisito")
    path = d[kind] / f["file"]
    if not path.exists():
        raise AcquisitionError(f"{kind} {month}: {path} assente")
    local = _sha256_file(path)
    if local != f["sha256"] or local != f["providerChecksum"]:
        raise AcquisitionError(f"{kind} {month}: SHA256 {local} non coerente con manifest/fornitore")
    return path


def load_trade(cand: Candidate, data_dir: Path, phase: str) -> tuple[MinuteStore, list[dict]]:
    d = dirs(data_dir)
    manifest = json.loads((d["manifests"] / "acquisition-trade.json").read_text(encoding="utf-8"))
    _, end = cand.window(phase)
    start = cand.input_start if phase == "DEV" else cand.window(phase)[0]
    store = MinuteStore(start, end)
    report = []
    for month in phase_months(cand, phase)["trade"]:
        path = _verified_zip(d, "trade", manifest, month)
        lo, hi = month_bounds(month)
        stats = parse_csv_text(read_month_zip(path, path.name.replace(".zip", ".csv")), store, lo, hi, path.name)
        f = next(x for x in manifest["files"] if x["month"] == month)
        report.append({"month": month, "file": path.name, "url": f["url"], "sha256": f["sha256"], "downloadedAt": f.get("downloadedAt"),
                       "cache": f.get("cache"), "timeUnit": "ms", **stats.as_dict(), "coverage": store.counts(lo, hi)})
    return store, report


def parse_funding(text: str, name: str) -> tuple[list[dict], dict]:
    rows = list(csv.reader(io.StringIO(text)))
    stats = {"name": name, "header": False, "rows": 0, "corrupt": 0, "anomalies": []}
    out = []
    for n, fields in enumerate(rows, start=1):
        if not fields or (len(fields) == 1 and not fields[0].strip()):
            continue
        if n == 1 and not fields[0].strip().isdigit():
            if [x.strip() for x in fields] != FUNDING_COLUMNS:
                raise SchemaError(f"{name}: intestazione funding non riconosciuta {fields}")
            stats["header"] = True
            continue
        stats["rows"] += 1
        try:
            tau, hours, rate = int(fields[0]), float(fields[1]), float(fields[2])
        except (ValueError, IndexError):
            stats["corrupt"] += 1
            stats["anomalies"].append({"kind": "ROW_NOT_PARSABLE", "line": n})
            continue
        if tau >= 10**13:
            raise SchemaError(f"{name}: calc_time {tau} non in millisecondi")
        if not (math.isfinite(hours) and hours > 0) or not math.isfinite(rate):
            stats["corrupt"] += 1
            stats["anomalies"].append({"kind": "VALUE_NOT_FINITE", "line": n, "tau": tau})
            continue
        out.append({"tau": tau, "intervalHours": hours, "rate": rate})
    return out, stats


def check_funding_series(events: list[dict], start: int, end: int) -> dict:
    """Ordine, unicità e distanze coerenti con l'intervallo dichiarato (jitter fino a 60s)."""
    anomalies = []
    taus = [e["tau"] for e in events]
    if taus != sorted(taus):
        anomalies.append({"kind": "NOT_ORDERED"})
    if len(set(taus)) != len(taus):
        anomalies.append({"kind": "DUPLICATE_TIMESTAMP", "count": len(taus) - len(set(taus))})
    ev = sorted(events, key=lambda e: e["tau"])
    for a, b in zip(ev, ev[1:]):
        expected = a["intervalHours"] * 3_600_000
        delta = b["tau"] - a["tau"]
        if abs(delta - expected) > MS_MIN:
            anomalies.append({"kind": "INTERVAL_MISMATCH", "from": a["tau"], "to": b["tau"], "deltaMs": delta, "declaredHours": a["intervalHours"]})
    first_gap = ev[0]["tau"] - start if ev else None
    last_gap = end - ev[-1]["tau"] if ev else None
    intervals = sorted({e["intervalHours"] for e in ev})
    return {"events": len(ev), "intervalsHours": intervals, "jitterMaxMs": max(e["tau"] % MS_MIN for e in ev) if ev else None,
            "firstTau": ev[0]["tau"] if ev else None, "lastTau": ev[-1]["tau"] if ev else None, "startGapMs": first_gap, "endGapMs": last_gap,
            "anomalies": anomalies, "certified": not anomalies}


def load_costs(cand: Candidate, data_dir: Path, phase: str) -> tuple[list[dict], dict[int, float], dict]:
    d = dirs(data_dir)
    start, end = cand.window(phase)
    months = phase_months(cand, phase)
    fman = json.loads((d["manifests"] / "acquisition-funding.json").read_text(encoding="utf-8"))
    mman = json.loads((d["manifests"] / "acquisition-mark.json").read_text(encoding="utf-8"))
    funding, freport = [], []
    for month in months["funding"]:
        path = _verified_zip(d, "funding", fman, month)
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            expected = path.name.replace(".zip", ".csv")
            if names != [expected]:
                raise SchemaError(f"{path.name}: contenuto inatteso {names}")
            text = zf.read(expected).decode("utf-8")
        events, stats = parse_funding(text, path.name)
        lo, hi = month_bounds(month)
        outside = [e for e in events if not (lo <= e["tau"] < hi)]
        stats["outsideMonth"] = len(outside)
        funding.extend(e for e in events if lo <= e["tau"] < hi)
        f = next(x for x in fman["files"] if x["month"] == month)
        freport.append({"month": month, "file": path.name, "sha256": f["sha256"], "downloadedAt": f.get("downloadedAt"), **stats})
    series = check_funding_series(funding, start, end)
    # Mark: stessi controlli di schema/tempi/OHLC dei minuti; si conservano solo i close necessari.
    mstore = MinuteStore(start, end)
    mreport = []
    for month in months["mark"]:
        path = _verified_zip(d, "mark", mman, month)
        lo, hi = month_bounds(month)
        stats = parse_csv_text(read_month_zip(path, path.name.replace(".zip", ".csv")), mstore, lo, hi, path.name)
        f = next(x for x in mman["files"] if x["month"] == month)
        mreport.append({"month": month, "file": path.name, "sha256": f["sha256"], "downloadedAt": f.get("downloadedAt"), **stats.as_dict(),
                        "coverage": mstore.counts(lo, hi)})
    mark, missing = {}, []
    for e in funding:
        u = e["tau"] - e["tau"] % MS_MIN
        prev = u - MS_MIN
        i = mstore.index(prev)
        if 0 <= i < mstore.n and mstore.status[i] == VALID:
            mark[u] = mstore.c[i]
        else:
            missing.append(e["tau"])
    report = {"funding": {"files": freport, "series": series}, "mark": {"files": mreport, "pointsNeeded": len(funding),
              "pointsAvailable": len(mark), "missingForTau": missing}}
    return funding, mark, report


def input_hash(trade_report: list[dict], cost_report: dict) -> str:
    stable = {"trade": sorted((r["month"], r["sha256"]) for r in trade_report),
              "funding": sorted((r["month"], r["sha256"]) for r in cost_report["funding"]["files"]),
              "mark": sorted((r["month"], r["sha256"]) for r in cost_report["mark"]["files"])}
    return sha256_bytes(canonical_json(stable))


def reused_identity(data_dir: Path) -> dict:
    """Identità dello strumento e termini già verificati per OBS-001 sul PC Owner: riuso con provenienza."""
    path = data_dir.parent / "OBS-001" / "manifests" / "acquisition.json"
    if not path.exists():
        return {"ok": False, "reason": f"manifest OBS-001 non trovato: {path}"}
    acq = json.loads(path.read_text(encoding="utf-8"))
    meta, terms = acq.get("instrumentMetadata", {}), acq.get("terms", {})
    return {"ok": bool(meta.get("ok")), "reusedFrom": str(path), "fetchedAt": meta.get("fetchedAt"), "responseSha256": meta.get("responseSha256"),
            "instrument": meta.get("instrument"), "checks": meta.get("checks"), "terms": {k: terms.get(k) for k in ("url", "fetchedAt", "sha256")},
            "note": "Metadati correnti riusati con provenienza; non certificano condizioni storiche."}


__all__ = ["acquire", "load_trade", "load_costs", "input_hash", "reused_identity", "phase_months", "parse_funding", "check_funding_series", "parse_utc"]
