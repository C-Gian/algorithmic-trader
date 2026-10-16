"""Acquisizione pubblica autorizzata: sette ZIP mensili Binance Vision, metadati e termini.

Download seriali con timeout e pochi tentativi su errori transitori; ZIP scritto prima in un
file temporaneo e promosso solo se lo SHA256 coincide col .CHECKSUM del fornitore. Una cache
locale coerente viene riusata; se il checksum remoto cambia, la versione precedente è
conservata a parte. Nessun login, chiave, scansione di simboli o altro dataset.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from .conventions import Conventions, canonical_json, sha256_bytes

USER_AGENT = "algorithmic-trader-OBS-001/1 (studio osservativo personale)"
TIMEOUT_S = 60
ATTEMPTS = 3
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}


class AcquisitionError(RuntimeError):
    """Blocco preciso dell'acquisizione affidabile."""


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url: str) -> tuple[bytes, dict]:
    last = None
    for attempt in range(1, ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.read(), {"status": resp.status, "headers": {k: v for k, v in resp.headers.items() if k.lower() in ("content-length", "last-modified", "etag", "date")}}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.reason}"
            if e.code not in TRANSIENT_HTTP:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = f"{type(e).__name__}: {getattr(e, 'reason', e)}"
        if attempt < ATTEMPTS:
            time.sleep(2 * attempt)
    raise AcquisitionError(f"{url}: {last}")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_checksum(text: str, expected_name: str) -> str:
    parts = text.split()
    if len(parts) != 2 or parts[1] != expected_name or len(parts[0]) != 64:
        raise AcquisitionError(f"file .CHECKSUM inatteso per {expected_name}: {text.strip()!r}")
    return parts[0].lower()


def paths(data_dir: Path) -> dict[str, Path]:
    p = {"raw": data_dir / "raw", "partial": data_dir / "raw" / ".partial", "superseded": data_dir / "raw" / "superseded",
         "meta": data_dir / "meta", "manifests": data_dir / "manifests", "runs": data_dir / "runs"}
    for d in p.values():
        d.mkdir(parents=True, exist_ok=True)
    return p


def acquire_month(conv: Conventions, month: str, dirs: dict[str, Path]) -> dict:
    src = conv.section("source")
    url = src["urlTemplate"].format(month=month)
    name = url.rsplit("/", 1)[1]
    entry = {"month": month, "url": url, "checksumUrl": url + src["checksumSuffix"], "file": name}
    checksum_bytes, meta = http_get(entry["checksumUrl"])
    provider = parse_checksum(checksum_bytes.decode("utf-8"), name)
    (dirs["raw"] / (name + ".CHECKSUM")).write_bytes(checksum_bytes)
    entry.update(providerChecksum=provider, checksumFetchedAt=now_utc(), checksumHttp=meta)
    target = dirs["raw"] / name
    if target.exists():
        local = _sha256_file(target)
        if local == provider:
            entry.update(sha256=local, size=target.stat().st_size, checksumOk=True, cache="REUSED")
            return entry
        keep = dirs["superseded"] / f"{name}.{local[:12]}"
        os.replace(target, keep)
        entry["supersededLocal"] = {"path": str(keep), "sha256": local}
    tmp = dirs["partial"] / (name + ".part")
    data, meta = http_get(url)
    tmp.write_bytes(data)
    local = _sha256_file(tmp)
    entry.update(downloadedAt=now_utc(), http=meta, size=len(data), sha256=local)
    if local != provider:
        entry["checksumOk"] = False
        raise AcquisitionError(f"{name}: SHA256 locale {local} diverso dal checksum del fornitore {provider}")
    os.replace(tmp, target)
    entry.update(checksumOk=True, cache="DOWNLOADED")
    return entry


def instrument_metadata(conv: Conventions, dirs: dict[str, Path]) -> dict:
    """Metadati pubblici correnti dello strumento: identità, non condizioni storiche."""
    src = conv.section("source")
    fetched = now_utc()
    try:
        body, meta = http_get(src["metadataUrl"])
    except AcquisitionError as e:
        return {"url": src["metadataUrl"], "fetchedAt": fetched, "ok": False, "error": str(e),
                "alternative": "https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data"}
    raw_path = dirs["meta"] / f"exchangeInfo-{fetched[:10]}.json"
    raw_path.write_bytes(body)
    info = json.loads(body)
    sym = next((s for s in info.get("symbols", []) if s.get("symbol") == src["symbol"]), None)
    checks = {}
    if sym is not None:
        for key, expected in (("contractType", src["contractType"]), ("baseAsset", src["baseAsset"]),
                              ("quoteAsset", src["quoteAsset"]), ("marginAsset", src["marginAsset"])):
            checks[key] = {"expected": expected, "observed": sym.get(key), "ok": sym.get(key) == expected}
    pertinent = {k: sym.get(k) for k in ("symbol", "pair", "contractType", "status", "baseAsset", "quoteAsset", "marginAsset",
                                          "underlyingType", "onboardDate", "pricePrecision", "quantityPrecision")} if sym else None
    (dirs["meta"] / f"instrument-{src['symbol']}-{fetched[:10]}.json").write_text(json.dumps(pertinent, indent=2), encoding="utf-8")
    return {"url": src["metadataUrl"], "fetchedAt": fetched, "http": meta, "ok": sym is not None and all(c["ok"] for c in checks.values()),
            "responseSha256": sha256_bytes(body), "responseFile": str(raw_path), "instrument": pertinent, "checks": checks,
            "note": "Metadati correnti: confermano l'identità dello strumento, non certificano condizioni storiche di esecuzione."}


def terms(conv: Conventions, dirs: dict[str, Path]) -> dict:
    url = conv.section("source")["termsUrl"]
    fetched = now_utc()
    try:
        body, meta = http_get(url)
    except AcquisitionError as e:
        return {"url": url, "fetchedAt": fetched, "ok": False, "error": str(e)}
    path = dirs["meta"] / f"binance-public-data-TERMS-{fetched[:10]}.md"
    path.write_bytes(body)
    return {"url": url, "fetchedAt": fetched, "ok": True, "sha256": sha256_bytes(body), "file": str(path), "http": meta}


def acquire_all(conv: Conventions, data_dir: Path) -> dict:
    dirs = paths(data_dir)
    manifest = {"kind": "OBS001_ACQUISITION", "conventions": {"id": conv.raw["id"], "hash": conv.hash}, "startedAt": now_utc()}
    manifest["instrumentMetadata"] = instrument_metadata(conv, dirs)
    manifest["terms"] = terms(conv, dirs)
    previous_path = dirs["manifests"] / "acquisition.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    downloaded = {f["sha256"]: f.get("downloadedAt") for f in previous.get("files", []) if f.get("sha256")}
    files, errors = [], []
    for month in conv.months:
        try:
            entry = acquire_month(conv, month, dirs)
        except AcquisitionError as e:
            errors.append({"month": month, "error": str(e)})
            continue
        if entry["cache"] == "REUSED":
            entry["downloadedAt"] = downloaded.get(entry["sha256"])  # orario del download originale, se registrato
        files.append(entry)
    manifest.update(files=files, errors=errors, finishedAt=now_utc())
    manifest["blocked"] = bool(errors) or not manifest["instrumentMetadata"].get("ok", False)
    _write_versioned(dirs["manifests"], "acquisition", manifest)
    return manifest


def _write_versioned(folder: Path, stem: str, data: dict) -> Path:
    """Scrive <stem>.json (ultimo) e conserva una copia datata: nessuna sovrascrittura della storia."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    body = json.dumps(data, indent=2, ensure_ascii=False)
    (folder / f"{stem}-{stamp}.json").write_text(body, encoding="utf-8")
    latest = folder / f"{stem}.json"
    latest.write_text(body, encoding="utf-8")
    return latest


def input_identity(files: list[dict]) -> str:
    """Hash degli input: URL, file e SHA256, senza orari di download (metadati di run)."""
    stable = sorted(({"url": f["url"], "file": f["file"], "sha256": f["sha256"]} for f in files), key=lambda x: x["file"])
    return sha256_bytes(canonical_json(stable))
