"""CAND-001/v1 sulla catena completa (osservatore OBS-001 + decisioni + ledger) con minuti sintetici."""

import json
import unittest

from cand001.backtest import run_window
from cand001.metrics import summarize

from cand001_helpers import BAR, CAND, DAY, MIN, T0, trend_store

START, END = T0 - 10 * DAY, T0 + 20 * DAY
WINDOW = (T0, END)


def canon(x):
    return json.dumps(x, sort_keys=True, default=str)


class Causality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = run_window(CAND, trend_store(START, END, 7), WINDOW, [], {})
        trades = cls.base["ledger"].trades
        second = trades[1]
        # Cutoff a posizione aperta: 3 ore dopo l'ingresso del secondo trade, sulla griglia 45m.
        t = second["entryTime"] + 3 * 3_600_000
        cls.cutoff = t - (t - START) % BAR
        other = trend_store(START, END, 7)
        st = other.truncated(cls.cutoff)
        last = other.c[other.index(cls.cutoff) - 1]
        trend_store(START, END, 99, store=st, price=last, from_t=cls.cutoff)
        cls.other = run_window(CAND, st, WINDOW, [], {})

    def test_setup_has_trades(self):
        self.assertGreaterEqual(len(self.base["ledger"].trades), 3)
        self.assertLess(self.base["ledger"].trades[1]["entryTime"], self.cutoff)  # posizione già aperta prima del cutoff

    def test_same_prefix_same_decisions_requests_and_protections(self):
        def upto(res):
            dec = [d for d in res["engine"].decisions if d["t"] <= self.cutoff]
            req = [r for r in res["ledger"].requests if r["executeAt"] <= self.cutoff]
            done = [t for t in res["ledger"].trades if t["exit"]["accountingTime"] <= self.cutoff]
            return canon(dec), canon(req), canon(done)

        a, b = upto(self.base), upto(self.other)
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[1], b[1])
        self.assertEqual(a[2], b[2])
        self.assertGreater(len(json.loads(a[0])), 100)


class Reconciliation(unittest.TestCase):
    def test_counts_and_ledger_reconcile(self):
        res = run_window(CAND, trend_store(START, END, 5), WINDOW, [], {})
        summ = summarize(res, CAND, "DEV")
        rec = summ["reconciliation"]
        self.assertTrue(rec["reconciled"])
        total = summ["tables"]["DEV"]
        self.assertEqual(total["closes"], 20 * 32)
        self.assertEqual(sum(total["requests"].values()), total["calls"])
        self.assertEqual(sum(total["trades"]["exits"].values()), total["trades"]["closed"])
        # I mesi non azzerano il percorso: la somma dei netti mensili per ingresso è il totale.
        months = [m["trades"]["net"] for m in summ["months"].values()]
        self.assertAlmostEqual(sum(months), total["trades"]["net"])
        self.assertTrue(any(t["stops"] for t in res["ledger"].trades))  # seed con protezione aggiornata

    def test_no_minute_after_window_end(self):
        res = run_window(CAND, trend_store(START, END, 7), WINDOW, [], {})
        led = res["ledger"]
        self.assertLessEqual(led.cursor, END)
        for t in led.trades:
            self.assertLessEqual(t["exit"]["accountingTime"], END)
            self.assertLess(t["exit"]["minute"], END)


if __name__ == "__main__":
    unittest.main()
