"""Cartella dati sintetica per i test APP-001: archivi ZIP inventati (non BTC) con manifest coerenti.

Profilo di prova [2022-11-01, 2022-12-01) con prefisso osservativo da ottobre 2022: due mesi di minuti
a tratti di tendenza (stesso generatore della fixture CAND-001), funding ogni 8 ore e mark uguale al
prezzo negoziato. Basta al percorso reale del motore per produrre episodi, richieste e operazioni.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

from obs001.conventions import parse_utc
from obs001.inputs import month_bounds

from cand001 import data as D
from cand001.config import load_candidate
from cand001.fixture import synthetic_store
from cand001.profiles import Profile

CAND = load_candidate()
MIN = 60_000
WINDOW = (parse_utc("2022-11-01T00:00:00Z"), parse_utc("2022-12-01T00:00:00Z"))
PROFILE = Profile("TEST_2022_11", "Prova sintetica novembre 2022", "PRODUCT_CHECK", WINDOW, "DEV", "solo test", "test")
PROFILES = {PROFILE.id: PROFILE}
HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"


def _zip(csv_name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_name, text)
    return buf.getvalue()


def _klines(store, month: str, drop: int | None = None) -> str:
    lo, hi = month_bounds(month)
    rows = [HEADER]
    for t in range(lo, hi, MIN):
        if t == drop:
            continue
        i = store.index(t)
        rows.append(f"{t},{store.o[i]!r},{store.h[i]!r},{store.l[i]!r},{store.c[i]!r},{store.v[i]!r},{t + MIN - 1},0,3,0,0,0")
    return "\n".join(rows) + "\n"


def _funding(month: str, skip_one: bool = False, offset: int | None = None) -> str:
    """offset: prima scadenza a lo+offset (griglia regolare di 8 ore spostata, serie sempre certificabile)."""
    lo, hi = month_bounds(month)
    taus = list(range(lo + (8 * 3_600_000 if offset is None else offset), hi, 8 * 3_600_000))  # il mark del minuto precedente esiste nella finestra
    if skip_one:
        del taus[len(taus) // 2]  # un evento mancante: serie non certificabile
    return "calc_time,funding_interval_hours,last_funding_rate\n" + "".join(f"{t + 5},8,0.0001\n" for t in taus)


_CACHE: dict[tuple, dict[str, bytes]] = {}


def _archives(bad_funding: bool, funding_offset: int | None = None, drop_mark: int | None = None,
              drop_trade: int | None = None) -> dict[str, bytes]:
    key = (bad_funding, funding_offset, drop_mark, drop_trade)
    if key not in _CACHE:
        store = synthetic_store(CAND.input_start, WINDOW[1], seed=11)
        out = {}
        for month in ("2022-10", "2022-11"):
            out[f"trade/BTCUSDT-1m-{month}.zip"] = _zip(f"BTCUSDT-1m-{month}.csv", _klines(store, month, drop=drop_trade))
        out["mark/BTCUSDT-1m-2022-11.zip"] = _zip("BTCUSDT-1m-2022-11.csv", _klines(store, "2022-11", drop=drop_mark))
        name = "BTCUSDT-fundingRate-2022-11"
        out[f"funding/{name}.zip"] = _zip(name + ".csv", _funding("2022-11", skip_one=bad_funding, offset=funding_offset))
        _CACHE[key] = out
    return _CACHE[key]


def make_data_dir(tmp: Path, bad_funding: bool = False, missing: str | None = None, funding_offset: int | None = None,
                  drop_mark: int | None = None, drop_trade: int | None = None) -> Path:
    """Cartella CAND-001 sintetica. missing='trade/2022-10' toglie quel file dal disco (manifest invariato).
    funding_offset sposta la griglia regolare di 8 ore; drop_mark toglie un solo minuto dal file mark
    (ZIP, hash e manifest coerenti): il prezzo di riferimento di quel pagamento periodico manca."""
    root = tmp / "CAND-001"
    d = D.dirs(root)
    manifests: dict[str, list] = {"trade": [], "funding": [], "mark": []}
    for rel, body in _archives(bad_funding, funding_offset, drop_mark, drop_trade).items():
        kind, name = rel.split("/")
        month = name[-11:-4]
        sha = hashlib.sha256(body).hexdigest()
        if missing != f"{kind}/{month}":
            (d[kind] / name).write_bytes(body)
        manifests[kind].append({"month": month, "kind": kind, "file": name, "url": f"https://example.invalid/{name}", "providerChecksum": sha,
                                "sha256": sha, "size": len(body), "checksumOk": True, "cache": "DOWNLOADED", "downloadedAt": "2026-10-17T00:00:00Z"})
    for kind, files in manifests.items():
        (d["manifests"] / f"acquisition-{kind}.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    return root


def clean(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
