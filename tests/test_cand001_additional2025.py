"""Supporto ADDITIONAL_2025 (motore 1.0.2), controlli sintetici prima di qualunque esito 2025.

- piano degli input: prefisso osservativo intero dal 2022-10-01, riuso dei 7 mesi OBS-001, solo
  5 trade + 12 funding + 12 mark da acquisire, nessun mese 2026;
- acquisizione con rete simulata: file già verificati senza richieste, OBS mai riscaricati;
- caricamento: store dal 2022-10-01 al 2026-01-01, fonti miste, nessun minuto 2026 accettato;
- osservazioni al confine uguali a quelle del prefisso continuo, diverse da uno store che parte al confine;
- finestra che parte FLAT, senza episodi, richieste o posizioni precedenti.
Prezzi e archivi inventati; nessun dato reale letto.
"""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from obs001.conventions import parse_utc
from obs001.inputs import month_bounds

from cand001 import data as D
from cand001.backtest import observe_store, run_window
from cand001.fixture import synthetic_store

from cand001_helpers import BAR, CAND, DAY, MIN, T0

PHASE = "ADDITIONAL_2025"
OBS_MONTHS = [f"2025-{m:02d}" for m in range(6, 13)]
NEW_TRADE = [f"2025-{m:02d}" for m in range(1, 6)]
Y2025 = [f"2025-{m:02d}" for m in range(1, 13)]
HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"


def kline(t: int) -> str:
    return f"{t},100,100.1,99.9,100,1,{t + 59_999},100,3,0,0,0"


def zip_bytes(csv_name: str, text: str) -> bytes:
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(csv_name, text)
    return buf.getvalue()


def month_zip(kind: str, month: str, extra: list[str] | None = None) -> tuple[str, bytes]:
    if kind == "funding":
        name = f"BTCUSDT-fundingRate-{month}"
        lo, _ = month_bounds(month)
        return name + ".zip", zip_bytes(name + ".csv", "calc_time,funding_interval_hours,last_funding_rate\n" + f"{lo},8,0.0001\n")
    name = f"BTCUSDT-1m-{month}"
    lo, _ = month_bounds(month)
    rows = [HEADER, kline(lo), kline(lo + MIN)] + (extra or [])
    return name + ".zip", zip_bytes(name + ".csv", "\n".join(rows) + "\n")


def entry(kind: str, month: str, folder: Path, extra=None) -> dict:
    name, body = month_zip(kind, month, extra)
    (folder / name).write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    return {"month": month, "kind": kind, "file": name, "url": f"https://example.invalid/{name}", "providerChecksum": sha,
            "sha256": sha, "checksumOk": True, "cache": "DOWNLOADED", "downloadedAt": "2026-10-17T00:00:00Z"}


def data_root(tmp: Path, dev_only: bool = True) -> Path:
    """Cartella CAND con i 27/24/24 file DEV già verificati e cartella OBS con i 7 mesi 2025-06..12."""
    root = tmp / "CAND-001"
    d = D.dirs(root)
    dev = D.phase_inputs(CAND, "DEV")
    for kind, months in (("trade", dev["trade"]), ("funding", dev["funding"]), ("mark", dev["mark"])):
        files = [entry(kind, m, d[kind]) for m in months]
        (d["manifests"] / f"acquisition-{kind}.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    obs_raw = tmp / "OBS-001" / "raw"
    obs_raw.mkdir(parents=True)
    (tmp / "OBS-001" / "manifests").mkdir()
    last = [kline(parse_utc("2026-01-01T00:00:00Z"))]  # riga 2026 dentro il file di dicembre: va scartata
    obs = [entry("trade", m, obs_raw, last if m == "2025-12" else None) for m in OBS_MONTHS]
    (tmp / "OBS-001" / "manifests" / "acquisition.json").write_text(json.dumps({"files": obs}), encoding="utf-8")
    return root


class FakeNetwork:
    """Sostituisce http_get: serve archivi e .CHECKSUM sintetici e registra ogni URL richiesto."""

    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, url: str):
        self.urls.append(url)
        name = url.rsplit("/", 1)[1]
        zname = name.removesuffix(".CHECKSUM")
        month = zname.removesuffix(".zip")[-7:]
        kind = "funding" if "fundingRate" in url else "trade"
        body = month_zip(kind, month)[1]
        if name.endswith(".CHECKSUM"):
            return f"{hashlib.sha256(body).hexdigest()}  {zname}\n".encode(), {"status": 200}
        return body, {"status": 200}


class Plan(unittest.TestCase):
    def test_additional_2025_inputs(self):
        p = D.phase_inputs(CAND, PHASE)
        self.assertEqual((len(p["observe"]), p["observe"][0], p["observe"][-1]), (39, "2022-10", "2025-12"))
        self.assertEqual(p["reuseObs"], OBS_MONTHS)
        self.assertEqual(len(p["trade"]), 32)  # 27 già in CAND-001 + 5 nuovi; nessuno dei 7 OBS
        self.assertEqual(p["trade"][-5:], NEW_TRADE)
        self.assertEqual((p["funding"], p["mark"]), (Y2025, Y2025))
        self.assertFalse([m for v in p.values() for m in v if m >= "2026"])
        start, end = CAND.window(PHASE)
        self.assertEqual((end - CAND.input_start) // MIN, 1_710_720)
        self.assertEqual(((end - start) // MIN, (end - start) // BAR), (525_600, 11_680))

    def test_dev_plan_unchanged(self):
        p = D.phase_inputs(CAND, "DEV")
        self.assertEqual((len(p["observe"]), p["reuseObs"], len(p["funding"])), (27, [], 24))
        self.assertEqual(p["trade"], p["observe"])


class Acquisition(unittest.TestCase):
    def test_only_missing_files_downloaded_and_obs_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = data_root(Path(tmp))
            before = (root / "manifests" / "acquisition-trade.json").read_text(encoding="utf-8")
            net = FakeNetwork()
            with mock.patch.object(D, "http_get", net):
                out = D.acquire(CAND, root, PHASE)
            zips = sorted(u.rsplit("/", 1)[1] for u in net.urls if u.endswith(".zip"))
            sums = [u for u in net.urls if u.endswith(".CHECKSUM")]
            expected = sorted([f"BTCUSDT-1m-{m}.zip" for m in NEW_TRADE] * 1 + [f"BTCUSDT-fundingRate-{m}.zip" for m in Y2025]
                              + [f"BTCUSDT-1m-{m}.zip" for m in Y2025])
            self.assertEqual(zips, expected)  # 5 + 12 + 12 = 29 archivi nuovi
            self.assertEqual(len(zips), 29)
            self.assertEqual(len(sums), 29)
            self.assertFalse([u for u in net.urls if any(m in u for m in OBS_MONTHS) and "/klines/" in u])
            self.assertFalse([u for u in net.urls if "2026" in u or any(f"-{m}." in u for m in D.phase_inputs(CAND, "DEV")["trade"])])
            self.assertEqual(sum(v == "VERIFIED_LOCAL" for v in out["trade"]["thisRun"].values()), 27)
            self.assertEqual(sum(v == "DOWNLOADED" for v in out["trade"]["thisRun"].values()), 5)
            self.assertEqual([f["month"] for f in out["reuseObs"]["files"]], OBS_MONTHS)
            self.assertFalse(out["reuseObs"]["blocked"])
            # Voci DEV del manifest invariate (nessuna provenienza riscritta).
            old = {f["month"]: f for f in json.loads(before)["files"]}
            new = {f["month"]: f for f in out["trade"]["files"]}
            self.assertTrue(all(new[m] == old[m] for m in old))
            # Seconda esecuzione: tutto in cache, nessuna richiesta.
            net2 = FakeNetwork()
            with mock.patch.object(D, "http_get", net2):
                D.acquire(CAND, root, PHASE)
            self.assertEqual(net2.urls, [])

    def test_altered_obs_file_blocks_and_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = data_root(Path(tmp))
            f = Path(tmp) / "OBS-001" / "raw" / "BTCUSDT-1m-2025-07.zip"
            f.write_bytes(f.read_bytes() + b"x")
            rep = D.verify_obs_reuse(root, OBS_MONTHS)
            self.assertTrue(rep["blocked"])
            self.assertEqual([e["month"] for e in rep["errors"]], ["2025-07"])
            self.assertTrue(f.read_bytes().endswith(b"x"))


class Loading(unittest.TestCase):
    def test_store_spans_full_prefix_and_no_2026_minute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = data_root(Path(tmp))
            with mock.patch.object(D, "http_get", FakeNetwork()):
                D.acquire(CAND, root, PHASE)
            store, report = D.load_trade(CAND, root, PHASE)
            self.assertEqual((store.start, store.end), (CAND.input_start, parse_utc("2026-01-01T00:00:00Z")))
            self.assertEqual(len(report), 39)
            src = {r["month"]: r["source"] for r in report}
            self.assertEqual([m for m, s in src.items() if s == "OBS-001"], OBS_MONTHS)
            self.assertEqual(store.counts()["valid"], 2 * 39)
            dec = next(r for r in report if r["month"] == "2025-12")
            self.assertEqual(dec["outsideMonth"], 1)  # la riga del 2026 non entra nello store


class Boundary(unittest.TestCase):
    """Confine sintetico W0 = 2023-01-01 con 110 giorni di prefisso (stessa logica del 2025-01-01)."""

    S, W0, E = T0 - 110 * DAY, T0, T0 + 10 * DAY

    @classmethod
    def setUpClass(cls):
        cls.full = synthetic_store(cls.S, cls.E, 11)
        cls.obs_full = observe_store(cls.full)

    def test_boundary_observations_equal_continuous_prefix(self):
        # Stessa serie continua (stesso seme) che termina un giorno dopo il confine.
        cont = observe_store(synthetic_store(self.S, self.W0 + DAY, 11))
        k = (self.W0 - self.S) // BAR  # barra che chiude a W0 + BAR: la prima decisione della finestra è a W0
        a, b = self.obs_full["observed"]["45m"], cont["observed"]["45m"]
        for j in range(k - 40, k + 1):
            self.assertEqual(json.dumps(a[j], sort_keys=True, default=str), json.dumps(b[j], sort_keys=True, default=str))
        da, db = self.obs_full["observed"]["1D"], cont["observed"]["1D"]
        kd = (self.W0 - self.S) // DAY - 1
        self.assertEqual(json.dumps(da[kd], sort_keys=True, default=str), json.dumps(db[kd], sort_keys=True, default=str))

    def test_store_starting_at_boundary_would_differ(self):
        # Il difetto corretto: con lo store che parte al confine le medie non hanno storia.
        k = (self.W0 - self.S) // BAR  # prima barra della finestra, chiude a W0 + 45m
        short = observe_store(synthetic_store(self.W0, self.E, 11))["observed"]["45m"][0]
        self.assertIsNotNone(self.obs_full["observed"]["45m"][k]["avg"]["sma50"]["v"])
        self.assertIsNone(short["avg"]["sma50"]["v"])

    def test_window_starts_flat(self):
        early = run_window(CAND, self.full, (self.S + 60 * DAY, self.E), [], {}, obs=self.obs_full)
        late = run_window(CAND, self.full, (self.W0, self.E), [], {}, obs=self.obs_full)
        self.assertTrue(any(t["entryTime"] < self.W0 for t in early["ledger"].trades))  # il percorso lungo ha storia prima
        self.assertTrue(all(d["t"] >= self.W0 for d in late["engine"].decisions))
        self.assertTrue(all(e.t0 >= self.W0 for e in late["engine"].episodes))
        self.assertTrue(all(r["callTime"] >= self.W0 for r in late["ledger"].requests))
        self.assertTrue(all(t["entryTime"] > self.W0 for t in late["ledger"].trades))
        self.assertLessEqual(late["ledger"].cursor, self.E)

    def test_store_must_end_at_window_end(self):
        with self.assertRaises(ValueError):
            run_window(CAND, self.full, (self.W0, self.E - DAY), [], {})


if __name__ == "__main__":
    unittest.main()
