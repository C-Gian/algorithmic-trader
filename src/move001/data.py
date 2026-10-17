"""Minuti negoziati 1m già conservati (cartella CAND-001), soli mesi 2022-10…2024-12 elencati.

Ogni ZIP è verificato contro il manifest di acquisizione CAND-001 (SHA256 locale = registrato =
checksum del fornitore) prima della lettura. Nessun download, nessun mese oltre il 2024.
"""

from __future__ import annotations

import json
from pathlib import Path

from obs001.acquire import AcquisitionError, _sha256_file
from obs001.conventions import canonical_json, sha256_bytes
from obs001.inputs import month_bounds
from obs001.minutes import MinuteStore, parse_csv_text, read_month_zip

from .config import MONTHS, Study


def load_minutes(study: Study, data_root: Path) -> tuple[MinuteStore, list[dict]]:
    man = json.loads((data_root / "CAND-001" / "manifests" / "acquisition-trade.json").read_text(encoding="utf-8"))
    store = MinuteStore(study.input_start, study.end)
    report = []
    for month in MONTHS:
        f = next((x for x in man["files"] if x["month"] == month), None)
        if f is None:
            raise AcquisitionError(f"trade {month}: assente dal manifest CAND-001")
        path = data_root / "CAND-001" / "raw" / "trade" / f["file"]
        if not path.exists():
            raise AcquisitionError(f"trade {month}: {path} assente")
        local = _sha256_file(path)
        if local != f["sha256"] or local != f["providerChecksum"]:
            raise AcquisitionError(f"trade {month}: SHA256 {local} non coerente con manifest/fornitore")
        lo, hi = month_bounds(month)
        s = parse_csv_text(read_month_zip(path, f["file"].replace(".zip", ".csv")), store, lo, hi, f["file"]).as_dict()
        report.append({"month": month, "file": f["file"], "sha256": local, "url": f["url"], "rows": s["rows"],
                       **{k: s[k] for k in ("duplicatesIdentical", "duplicatesDiscordantMinutes", "outOfOrder", "outsideMonth", "corruptRows")},
                       "coverage": store.counts(lo, hi)})
    return store, report


def input_hash(report: list[dict]) -> str:
    return sha256_bytes(canonical_json(sorted((r["month"], r["sha256"]) for r in report)))
