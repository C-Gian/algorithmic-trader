"""Controllo degli input acquisiti: hash, schema, unità, copertura e manifest per file."""

from __future__ import annotations

import json
from pathlib import Path

from .acquire import _sha256_file, input_identity, paths
from .conventions import Conventions, parse_utc
from .minutes import EXPECTED_COLUMNS, MinuteStore, SchemaError, parse_csv_text, read_month_zip


class InputBlocked(RuntimeError):
    def __init__(self, message: str, manifest: dict | None = None):
        super().__init__(message)
        self.manifest = manifest


def month_bounds(month: str) -> tuple[int, int]:
    y, m = (int(x) for x in month.split("-"))
    start = parse_utc(f"{y:04d}-{m:02d}-01T00:00:00Z")
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return start, parse_utc(f"{ny:04d}-{nm:02d}-01T00:00:00Z")


def check_inputs(conv: Conventions, data_dir: Path) -> tuple[MinuteStore, dict]:
    dirs = paths(data_dir)
    acq_path = dirs["manifests"] / "acquisition.json"
    if not acq_path.exists():
        raise InputBlocked(f"manifest di acquisizione assente: {acq_path} (eseguire prima 'acquire')")
    acq = json.loads(acq_path.read_text(encoding="utf-8"))
    by_month = {f["month"]: f for f in acq.get("files", [])}
    src = conv.section("source")
    store = MinuteStore(conv.input_start, conv.end)
    files, problems = [], []
    for month in conv.months:
        f = by_month.get(month)
        if f is None:
            problems.append(f"{month}: file non acquisito")
            continue
        path = dirs["raw"] / f["file"]
        if not path.exists():
            problems.append(f"{month}: {path} assente")
            continue
        local = _sha256_file(path)
        if local != f["sha256"] or local != f["providerChecksum"]:
            problems.append(f"{month}: SHA256 {local} non coerente con manifest/fornitore")
            continue
        lo, hi = month_bounds(month)
        try:
            stats = parse_csv_text(read_month_zip(path, f["file"].replace(".zip", ".csv")), store, lo, hi, f["file"])
        except SchemaError as e:
            problems.append(f"{month}: {e}")
            continue
        files.append({
            "month": month, "url": f["url"], "file": f["file"], "downloadedAt": f.get("downloadedAt"), "cache": f.get("cache"),
            "size": path.stat().st_size, "sha256": local, "providerChecksum": f["providerChecksum"], "checksumOk": True,
            "symbol": src["symbol"], "market": src["segment"], "contractType": src["contractType"], "priceType": src["priceType"],
            "columns": EXPECTED_COLUMNS, "timeUnit": "ms", **stats.as_dict(), "coverage": store.counts(lo, hi),
        })
    meta = acq.get("instrumentMetadata", {})
    if not meta.get("ok"):
        problems.append(f"identità dello strumento non verificata: {meta.get('error') or meta.get('checks')}")
    totals = {
        "input": store.counts(),
        "initialization": store.counts(conv.input_start, conv.study_start),
        "study": store.counts(conv.study_start, conv.end),
    }
    manifest = {
        "kind": "OBS001_INPUT", "conventions": {"id": conv.raw["id"], "hash": conv.hash},
        "acquisition": {"startedAt": acq.get("startedAt"), "finishedAt": acq.get("finishedAt")},
        "instrumentMetadata": meta, "terms": acq.get("terms"), "files": files, "totals": totals, "problems": problems,
        "inputHash": input_identity(files) if len(files) == len(conv.months) else None,
    }
    if problems:
        raise InputBlocked("; ".join(problems), manifest)
    return store, manifest
