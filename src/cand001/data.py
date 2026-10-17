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


def obs_dir(data_dir: Path) -> Path:
    """Cartella dati OBS-001 accanto a quella CAND-001 (archivi trade 2025-06..12 già verificati)."""
    return data_dir.parent / "OBS-001"


def phase_inputs(cand: Candidate, phase: str, window: tuple[int, int] | None = None) -> dict[str, list[str]]:
    """Piano degli input di una fase, in insiemi distinti (motore 1.0.2):
    - observe: mesi trade da caricare per osservare, sempre dall'inizio dell'input (2022-10-01) alla fine
      della finestra, così le osservazioni al confine usano tutto il prefisso continuo;
    - reuseObs: mesi trade letti dagli archivi OBS-001 verificati (elenco della config congelata), mai riscaricati;
    - trade/funding/mark: mesi da acquisire nella cartella CAND-001. Funding e mark solo nella finestra
      valutata: la finestra parte FLAT e il prefisso non genera costi.
    Nessun mese oltre la fine della finestra (per ADDITIONAL_2025: nessun dato 2026).
    window sostituisce la finestra della fase (profili applicativi APP-001 come la prova di gennaio 2025)."""
    start, end = window or cand.window(phase)
    observe = months_between(cand.input_start, end)
    reuse = [m for m in observe if m in cand.raw["data"].get("reuseObsTradeMonths", [])]
    costs = months_between(start, end)
    return {"observe": observe, "reuseObs": reuse, "trade": [m for m in observe if m not in reuse], "funding": costs, "mark": costs}


def phase_months(cand: Candidate, phase: str, window: tuple[int, int] | None = None) -> dict[str, list[str]]:
    """Mesi da acquisire nella cartella CAND-001, per tipo."""
    plan = phase_inputs(cand, phase, window)
    return {"trade": plan["trade"], "funding": plan["funding"], "mark": plan["mark"]}


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


def _locally_verified(target_dir: Path, entry: dict | None) -> bool:
    """File già acquisito con checksum del fornitore registrato e hash locale ancora coincidente."""
    if not entry or not entry.get("checksumOk") or not entry.get("sha256") or entry.get("sha256") != entry.get("providerChecksum"):
        return False
    path = target_dir / entry["file"]
    return path.exists() and _sha256_file(path) == entry["sha256"]


def acquire(cand: Candidate, data_dir: Path, phase: str) -> dict:
    """Acquisisce solo i mesi mancanti. Un file già verificato (hash locale = checksum del fornitore
    registrato) è riusato senza richieste di rete, con la sua voce di manifest invariata.
    I mesi trade di OBS-001 sono riusati dalla loro cartella dopo verifica, mai riscaricati."""
    d = dirs(data_dir)
    out = {}
    for kind, months in phase_months(cand, phase).items():
        prev_path = d["manifests"] / f"acquisition-{kind}.json"
        prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
        downloaded = {f["sha256"]: f.get("downloadedAt") for f in prev.get("files", []) if f.get("sha256")}
        files = {f["month"]: f for f in prev.get("files", [])}
        errors, this_run = [], {}
        for month in months:
            if _locally_verified(d[kind], files.get(month)):
                this_run[month] = "VERIFIED_LOCAL"
                continue
            try:
                entry = acquire_file(url_for(cand, kind, month), d[kind], d, downloaded)
                files[month] = {"month": month, "kind": kind, **entry}
                this_run[month] = entry["cache"]
            except AcquisitionError as e:
                errors.append({"month": month, "error": str(e)})
        manifest = {"kind": f"CAND001_ACQUISITION_{kind.upper()}", "candidate": cand.raw["id"], "configHash": cand.hash,
                    "phase": phase, "finishedAt": now_utc(), "files": [files[m] for m in sorted(files)], "thisRun": this_run,
                    "errors": errors, "blocked": bool(errors)}
        write_manifest(d["manifests"], f"acquisition-{kind}", manifest)
        out[kind] = manifest
    reuse = phase_inputs(cand, phase)["reuseObs"]
    if reuse:
        out["reuseObs"] = verify_obs_reuse(data_dir, reuse, write=True)
    return out


def _obs_manifest(data_dir: Path) -> tuple[Path, dict]:
    path = obs_dir(data_dir) / "manifests" / "acquisition.json"
    if not path.exists():
        raise AcquisitionError(f"manifest OBS-001 non trovato: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def verify_obs_reuse(data_dir: Path, months: list[str], write: bool = False) -> dict:
    """Riuso degli archivi trade OBS-001: file letti dove si trovano (nessuna copia né modifica),
    hash locale confrontato con il manifest OBS e con il checksum del fornitore registrato."""
    mpath, man = _obs_manifest(data_dir)
    raw = obs_dir(data_dir) / "raw"
    files, errors = [], []
    for month in months:
        try:
            path = _verified_zip_at(raw, "trade OBS-001", man, month)
            f = next(x for x in man["files"] if x["month"] == month)
            files.append({"month": month, "kind": "trade", "source": "OBS-001", "path": str(path), "file": f["file"], "url": f["url"],
                          "providerChecksum": f["providerChecksum"], "checksumFetchedAt": f.get("checksumFetchedAt"),
                          "downloadedAt": f.get("downloadedAt"), "sha256": f["sha256"], "size": f.get("size"), "localCheck": "VERIFIED"})
        except AcquisitionError as e:
            errors.append({"month": month, "error": str(e)})
    manifest = {"kind": "CAND001_REUSE_TRADE_OBS001", "obsManifest": str(mpath), "obsManifestSha256": _sha256_file(mpath),
                "verifiedAt": now_utc(), "files": files, "errors": errors, "blocked": bool(errors)}
    if write:
        write_manifest(dirs(data_dir)["manifests"], "reuse-trade-obs", manifest)
    return manifest


# ------------------------------------------------------------------- controllo


def _verified_zip(d: dict[str, Path], kind: str, manifest: dict, month: str) -> Path:
    return _verified_zip_at(d[kind], kind, manifest, month)


def _verified_zip_at(folder: Path, kind: str, manifest: dict, month: str) -> Path:
    f = next((x for x in manifest.get("files", []) if x["month"] == month), None)
    if f is None:
        raise AcquisitionError(f"{kind} {month}: file non acquisito")
    path = folder / f["file"]
    if not path.exists():
        raise AcquisitionError(f"{kind} {month}: {path} assente")
    local = _sha256_file(path)
    if local != f["sha256"] or local != f["providerChecksum"]:
        raise AcquisitionError(f"{kind} {month}: SHA256 {local} non coerente con manifest/fornitore")
    return path


def _ticker(tick, kind: str, month: str):
    """Avanzamento per righe di un file; None se non richiesto (percorso diretto invariato)."""
    if tick is None:
        return None
    return lambda rows: tick("rows", kind=kind, month=month, rows=rows)


def load_trade(cand: Candidate, data_dir: Path, phase: str, window: tuple[int, int] | None = None,
               tick=None) -> tuple[MinuteStore, list[dict]]:
    """Minuti negoziati dall'inizio dell'input (2022-10-01) alla fine della finestra, in ogni fase: il
    prefisso osservativo è sempre completo e continuo (motore 1.0.2). Mesi OBS-001 letti dalla loro
    cartella dopo verifica; righe fuori dal mese del file scartate e contate; nessun minuto oltre la fine.
    tick(event, **info) facoltativo: inizio/fine di ogni file e righe lette (solo avanzamento/annullamento)."""
    d = dirs(data_dir)
    manifest = json.loads((d["manifests"] / "acquisition-trade.json").read_text(encoding="utf-8"))
    plan = phase_inputs(cand, phase, window)
    obs_man = _obs_manifest(data_dir)[1] if plan["reuseObs"] else None
    _, end = window or cand.window(phase)
    store = MinuteStore(cand.input_start, end)
    report = []
    for month in plan["observe"]:
        if tick is not None:
            tick("file", kind="trade", month=month)
        if month in plan["reuseObs"]:
            source, man = "OBS-001", obs_man
            path = _verified_zip_at(obs_dir(data_dir) / "raw", "trade OBS-001", man, month)
        else:
            source, man = "CAND-001", manifest
            path = _verified_zip(d, "trade", manifest, month)
        lo, hi = month_bounds(month)
        stats = parse_csv_text(read_month_zip(path, path.name.replace(".zip", ".csv")), store, lo, hi, path.name,
                               tick=_ticker(tick, "trade", month))
        f = next(x for x in man["files"] if x["month"] == month)
        report.append({"month": month, "file": path.name, "source": source, "url": f["url"], "sha256": f["sha256"],
                       "downloadedAt": f.get("downloadedAt"), "cache": f.get("cache"), "timeUnit": "ms", **stats.as_dict(),
                       "coverage": store.counts(lo, hi)})
        if tick is not None:
            tick("done", kind="trade", month=month)
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


class FundingNotCertified(RuntimeError):
    """Serie funding non certificabile: il run economico si ferma prima del ledger (review CAND-001/R1-A)."""

    def __init__(self, message: str, report: dict):
        super().__init__(message)
        self.report = report


def check_funding_series(events: list[dict], start: int, end: int, file_stats: list[dict] | None = None) -> dict:
    """Certificazione della serie funding sulla finestra [start, end).

    Non certificata se: vuota; righe corrotte/non finite o eventi fuori mese nei file; timestamp
    duplicati (identici o discordanti); distanze fra eventi consecutivi diverse dall'intervallo
    dichiarato oltre la tolleranza di 60 s; copertura ai confini più lunga di un intervallo dichiarato.
    Nessun calendario, tasso o prezzo viene inventato: un tratto non certificabile blocca il netto.
    """
    anomalies = []
    for st in file_stats or []:
        if st.get("corrupt"):
            anomalies.append({"kind": "CORRUPT_ROWS", "file": st.get("name"), "count": st["corrupt"]})
        if st.get("outsideMonth"):
            anomalies.append({"kind": "OUTSIDE_MONTH", "file": st.get("name"), "count": st["outsideMonth"]})
    if not events:
        anomalies.append({"kind": "EMPTY", "start": start, "end": end})
    taus = [e["tau"] for e in events]
    if taus != sorted(taus):
        anomalies.append({"kind": "NOT_ORDERED"})
    by_tau: dict[int, list[dict]] = {}
    for e in events:
        by_tau.setdefault(e["tau"], []).append(e)
    for tau, group in sorted(by_tau.items()):
        if len(group) > 1:
            same = all((g["rate"], g["intervalHours"]) == (group[0]["rate"], group[0]["intervalHours"]) for g in group)
            anomalies.append({"kind": "DUPLICATE_TIMESTAMP" if same else "CONFLICTING_DUPLICATE", "tau": tau, "count": len(group)})
    ev = [group[0] for _, group in sorted(by_tau.items())]
    for a, b in zip(ev, ev[1:]):
        expected = a["intervalHours"] * 3_600_000
        delta = b["tau"] - a["tau"]
        if abs(delta - expected) > MS_MIN:
            anomalies.append({"kind": "INTERVAL_MISMATCH", "from": a["tau"], "to": b["tau"], "deltaMs": delta, "declaredHours": a["intervalHours"]})
    if ev:
        if ev[0]["tau"] - start > ev[0]["intervalHours"] * 3_600_000 + MS_MIN:
            anomalies.append({"kind": "START_COVERAGE", "start": start, "firstTau": ev[0]["tau"], "declaredHours": ev[0]["intervalHours"]})
        if end - ev[-1]["tau"] > ev[-1]["intervalHours"] * 3_600_000 + MS_MIN:
            anomalies.append({"kind": "END_COVERAGE", "end": end, "lastTau": ev[-1]["tau"], "declaredHours": ev[-1]["intervalHours"]})
    first_gap = ev[0]["tau"] - start if ev else None
    last_gap = end - ev[-1]["tau"] if ev else None
    intervals = sorted({e["intervalHours"] for e in ev})
    return {"events": len(ev), "intervalsHours": intervals, "jitterMaxMs": max(e["tau"] % MS_MIN for e in ev) if ev else None,
            "firstTau": ev[0]["tau"] if ev else None, "lastTau": ev[-1]["tau"] if ev else None, "startGapMs": first_gap, "endGapMs": last_gap,
            "window": [start, end], "toleranceMs": MS_MIN, "anomalies": anomalies, "certified": not anomalies}


def load_costs(cand: Candidate, data_dir: Path, phase: str, months: list[str] | None = None,
               window: tuple[int, int] | None = None, tick=None) -> tuple[list[dict], dict[int, float], dict]:
    """Funding e mark della fase o della finestra del profilo. months restringe il caricamento (solo
    test sintetici). tick(event, **info) facoltativo come in load_trade."""
    d = dirs(data_dir)
    start, end = window or cand.window(phase)
    months = {"funding": months, "mark": months} if months else phase_months(cand, phase, window)
    fman = json.loads((d["manifests"] / "acquisition-funding.json").read_text(encoding="utf-8"))
    mman = json.loads((d["manifests"] / "acquisition-mark.json").read_text(encoding="utf-8"))
    funding, freport = [], []
    for month in months["funding"]:
        if tick is not None:
            tick("file", kind="funding", month=month)
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
        funding.extend(e for e in events if lo <= e["tau"] < hi and start <= e["tau"] < end)
        f = next(x for x in fman["files"] if x["month"] == month)
        freport.append({"month": month, "file": path.name, "sha256": f["sha256"], "downloadedAt": f.get("downloadedAt"), **stats})
        if tick is not None:
            tick("done", kind="funding", month=month)
    series = check_funding_series(funding, start, end, file_stats=freport)
    # Mark: stessi controlli di schema/tempi/OHLC dei minuti; si conservano solo i close necessari.
    mstore = MinuteStore(start, end)
    mreport = []
    for month in months["mark"]:
        if tick is not None:
            tick("file", kind="mark", month=month)
        path = _verified_zip(d, "mark", mman, month)
        lo, hi = month_bounds(month)
        stats = parse_csv_text(read_month_zip(path, path.name.replace(".zip", ".csv")), mstore, lo, hi, path.name,
                               tick=_ticker(tick, "mark", month))
        f = next(x for x in mman["files"] if x["month"] == month)
        mreport.append({"month": month, "file": path.name, "sha256": f["sha256"], "downloadedAt": f.get("downloadedAt"), **stats.as_dict(),
                        "coverage": mstore.counts(lo, hi)})
        if tick is not None:
            tick("done", kind="mark", month=month)
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


def economic_inputs(cand: Candidate, data_dir: Path, phase: str, months: list[str] | None = None,
                    window: tuple[int, int] | None = None, tick=None) -> tuple[list[dict], dict[int, float], dict]:
    """Costi per il ledger, solo se la serie funding è certificata; altrimenti FundingNotCertified."""
    funding, mark, report = load_costs(cand, data_dir, phase, months, window, tick=tick)
    series = report["funding"]["series"]
    if not series["certified"]:
        kinds = ", ".join(sorted({a["kind"] for a in series["anomalies"]}))
        first = series["anomalies"][0]
        raise FundingNotCertified(
            f"serie funding non certificata per [{series['window'][0]}, {series['window'][1]}): {kinds}; primo problema {first}. "
            "Run economico fermato prima del ledger: nessun netto completo.", report)
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


__all__ = ["acquire", "verify_obs_reuse", "phase_inputs", "obs_dir", "load_trade", "load_costs", "input_hash", "reused_identity", "phase_months", "parse_funding", "check_funding_series", "parse_utc"]
