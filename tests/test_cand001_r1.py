"""CAND-001/R1: funding non certificato blocca l'economia (R1-A); percorsi irrisolti e aggregati (R1-B).

Regressioni scritte prima della patch: falliscono sul codice consegnato a ee7282f.
"""

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from obs001.minutes import MISSING

from cand001 import data as D
from cand001.backtest import run_window
from cand001.execution import Ledger
from cand001.metrics import summarize, trade_stats

from cand001_helpers import CAND, DAY, MIN, T0, flat_store, trend_store

H = 3_600_000


def series(taus, hours=8):
    return [{"tau": t, "rate": 0.0001, "intervalHours": hours} for t in taus]


class FundingSeries(unittest.TestCase):
    def test_valid_series_certified(self):
        rep = D.check_funding_series(series([T0 + k * 8 * H + 8 for k in range(6)]), T0, T0 + 2 * DAY)
        self.assertTrue(rep["certified"], rep["anomalies"])

    def test_empty_internal_gap_and_boundaries_not_certified(self):
        self.assertFalse(D.check_funding_series([], T0, T0 + DAY)["certified"])
        gap = D.check_funding_series(series([T0, T0 + 16 * H]), T0, T0 + DAY)
        self.assertIn("INTERVAL_MISMATCH", [a["kind"] for a in gap["anomalies"]])
        late_start = D.check_funding_series(series([T0 + 9 * H, T0 + 17 * H]), T0, T0 + DAY)
        self.assertIn("START_COVERAGE", [a["kind"] for a in late_start["anomalies"]])
        early_end = D.check_funding_series(series([T0, T0 + 8 * H]), T0, T0 + DAY)
        self.assertIn("END_COVERAGE", [a["kind"] for a in early_end["anomalies"]])
        self.assertFalse(early_end["certified"])

    def test_duplicates_and_file_problems(self):
        dup = series([T0, T0 + 8 * H, T0 + 16 * H]) + [{"tau": T0 + 8 * H, "rate": 0.0002, "intervalHours": 8}]
        rep = D.check_funding_series(dup, T0, T0 + DAY)
        self.assertIn("CONFLICTING_DUPLICATE", [a["kind"] for a in rep["anomalies"]])
        ok = series([T0, T0 + 8 * H, T0 + 16 * H])
        rep2 = D.check_funding_series(ok, T0, T0 + DAY, file_stats=[{"name": "x", "corrupt": 1, "outsideMonth": 0}])
        self.assertFalse(rep2["certified"])


def _zip(path: Path, member: str, text: str) -> dict:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, text)
    path.write_bytes(buf.getvalue())
    sha = hashlib.sha256(buf.getvalue()).hexdigest()
    return {"month": "2023-01", "file": path.name, "sha256": sha, "providerChecksum": sha}


def synthetic_cost_dir(root: Path, funding_rows: list[str]) -> Path:
    d = D.dirs(root)
    fund = _zip(d["funding"] / "BTCUSDT-fundingRate-2023-01.zip", "BTCUSDT-fundingRate-2023-01.csv",
                "calc_time,funding_interval_hours,last_funding_rate\n" + "\n".join(funding_rows) + "\n")
    rows = ["open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"]
    for t in range(T0, T0 + 3 * DAY, MIN):
        rows.append(f"{t},100,100.1,99.9,100,0,{t + 59_999},0,0,0,0,0")
    mark = _zip(d["mark"] / "BTCUSDT-1m-2023-01.zip", "BTCUSDT-1m-2023-01.csv", "\n".join(rows) + "\n")
    (d["manifests"] / "acquisition-funding.json").write_text(json.dumps({"files": [fund]}), encoding="utf-8")
    (d["manifests"] / "acquisition-mark.json").write_text(json.dumps({"files": [mark]}), encoding="utf-8")
    return root


class LoadingPath(unittest.TestCase):
    """Percorso di caricamento usato da 'run' (archivi ZIP, manifest, controlli), su una finestra breve."""

    WINDOW = (T0, T0 + 3 * DAY)

    def load(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_cost_dir(Path(tmp), rows)
            return D.economic_inputs(CAND, root, "DEV", months=["2023-01"], window=self.WINDOW)

    def test_valid_file_passes_and_gives_same_events(self):
        rows = [f"{T0 + k * 8 * H + 8},8,0.0001" for k in range(9)]
        funding, mark, report = self.load(rows)
        self.assertEqual(len(funding), 9)
        self.assertTrue(report["funding"]["series"]["certified"])
        self.assertEqual(len(mark), 9 - 1)  # il primo evento (00:00 del 1° gennaio) richiede un mark del 2022, assente: MISSING

    def test_gap_corrupt_and_duplicate_block_before_ledger(self):
        base = [f"{T0 + k * 8 * H},8,0.0001" for k in range(9)]
        cases = {
            "buco 08:00": base[:1] + base[2:],
            "riga corrotta": base[:4] + ["abc,8,0.0001"] + base[4:],
            "duplicato discordante": base + [f"{T0 + 8 * H},8,0.0005"],
            "fine scoperta": base[:-2],
        }
        for label, rows in cases.items():
            with self.subTest(label):
                with self.assertRaises(D.FundingNotCertified) as ctx:
                    self.load(rows)
                self.assertFalse(ctx.exception.report["funding"]["series"]["certified"])
                self.assertIn("funding", str(ctx.exception).lower())


def entry(at, d=1, s0=98.0, t=110.0):
    return {"type": "ENTRY", "episodeId": "EP:gap", "d": d, "executeAt": at, "S0": s0, "T": t, "A0": 2.0, "callTime": at - MIN}


class Unresolved(unittest.TestCase):
    def test_review_reproduction_net_is_missing_not_zero(self):
        st = flat_store(T0, T0 + DAY, 100)
        st.status[st.index(T0 + 11 * MIN)] = MISSING
        lg = Ledger(CAND, st, (T0, T0 + DAY), [], {})
        lg.accept([entry(T0 + 10 * MIN)])
        lg.advance(T0 + DAY)
        (tr,) = lg.trades
        self.assertEqual(tr["status"], "UNRESOLVED_DATA_GAP")
        self.assertIsNone(tr["exit"])
        self.assertAlmostEqual(tr["feeEntry"], 0.0005 * tr["q"] * tr["E"])  # quanto era noto resta
        self.assertEqual(tr["gap"]["at"], T0 + 11 * MIN)
        s = trade_stats(lg.trades, 1000)
        self.assertEqual((s["n"], s["closed"], s["unresolved"]), (1, 0, 1))
        for k in ("net", "netBps", "stressNet", "pricePnLRef", "fees"):
            self.assertIsNone(s[k], k)

    def chain(self, trade_index):
        base = run_window(CAND, trend_store(T0 - 10 * DAY, T0 + 20 * DAY, 7), (T0, T0 + 20 * DAY), [], {})
        target = base["ledger"].trades[trade_index]
        st = trend_store(T0 - 10 * DAY, T0 + 20 * DAY, 7)
        gap_at = target["entryTime"] + 5 * MIN
        st.status[st.index(gap_at)] = MISSING
        res = run_window(CAND, st, (T0, T0 + 20 * DAY), [], {})
        return base, res, gap_at

    def test_gap_on_first_position(self):
        _, res, gap_at = self.chain(0)
        summ = summarize(res, CAND, "DEV")
        dev = summ["tables"]["DEV"]
        self.assertEqual((dev["trades"]["n"], dev["trades"]["unresolved"]), (1, 1))
        self.assertIsNone(dev["trades"]["net"])
        self.assertFalse(dev["coverage"]["complete"])
        self.assertEqual(dev["coverage"]["haltedAt"], gap_at)
        self.assertIsNone(dev["drawdown"]["maxDrawdown"])
        self.assertLess(dev["evaluatedCloses"], dev["closes"])
        rec = summ["reconciliation"]
        self.assertTrue(rec["knownPartReconciled"])
        self.assertFalse(rec["windowComplete"])

    def test_gap_after_closed_positions(self):
        base, res, gap_at = self.chain(2)
        summ = summarize(res, CAND, "DEV")
        dev = summ["tables"]["DEV"]["trades"]
        closed = base["ledger"].trades[:2]
        self.assertEqual((dev["n"], dev["closed"], dev["unresolved"]), (3, 2, 1))
        self.assertIsNone(dev["net"])
        self.assertAlmostEqual(dev["closedSubset"]["net"], sum(t["net"] for t in closed))
        self.assertEqual(dev["closedSubset"]["trades"], 2)
        # I due trade precedenti alla lacuna sono identici al percorso senza lacuna.
        self.assertEqual(json.dumps(res["ledger"].trades[:2], sort_keys=True), json.dumps(closed, sort_keys=True))
        after = [m for m in summ["months"].values() if m["start"] >= gap_at]
        self.assertTrue(all(not m["coverage"]["evaluated"] and m["trades"]["net"] is None for m in after))


if __name__ == "__main__":
    unittest.main()
