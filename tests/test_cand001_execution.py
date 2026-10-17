"""CAND-001/v1: ledger di esecuzione modellata, precedenze intraminuto e costi (sezioni 6, 8, 9, 11, 13)."""

import unittest

from obs001.minutes import MISSING

from cand001.execution import Ledger

from cand001_helpers import CAND, DAY, MIN, T0, flat_store, set_minute

END = T0 + 3 * DAY
U0 = T0 + 10 * MIN  # minuto d'ingresso


def entry(d=1, s0=105.8, t=112.0, at=U0):
    return {"type": "ENTRY", "episodeId": "EP:test", "d": d, "executeAt": at, "S0": s0, "T": t, "A0": 2.0, "callTime": at - MIN}


def ledger(store=None, funding=(), mark=None, price=108.0):
    st = store or flat_store(T0, END, price)
    return Ledger(CAND, st, (T0, END), list(funding), mark or {})


class Entry(unittest.TestCase):
    def test_fill_at_future_open_with_guard(self):
        lg = ledger()
        lg.accept([entry()])
        lg.advance(U0 + MIN)
        pos = lg.position
        self.assertEqual(pos.entry_time, U0)
        self.assertAlmostEqual(pos.e, 108 * 1.0003)
        self.assertAlmostEqual(pos.q, 1000 / (108 * 1.0003))
        self.assertEqual(lg.requests[0]["outcome"], "FILLED")

    def test_rejection_by_quote_and_missing_minute_have_no_cost(self):
        lg = ledger(price=110.0)  # E=110,033: rapporto (112-E)/(E-105,8) < 1,5
        lg.accept([entry()])
        lg.advance(U0 + 5 * MIN)
        self.assertIsNone(lg.position)
        self.assertEqual((lg.requests[0]["outcome"], lg.trades), ("REJECTED_PRICE", []))
        st = flat_store(T0, END, 108)
        st.status[st.index(U0)] = MISSING
        lg2 = ledger(st)
        lg2.accept([entry()])
        lg2.advance(U0 + 5 * MIN)
        self.assertEqual((lg2.requests[0]["outcome"], lg2.trades), ("CANCELLED_NO_QUOTE", []))


class Exits(unittest.TestCase):
    def open_ledger(self, store):
        lg = ledger(store)
        lg.accept([entry()])
        return lg

    def test_intraminute_stop_and_gap(self):
        st = flat_store(T0, END, 108)
        set_minute(st, U0 + 5 * MIN, 108, 108.1, 105.7, 106)
        lg = self.open_ledger(st)
        lg.advance(U0 + DAY)
        (tr,) = lg.trades
        self.assertEqual((tr["exit"]["reason"], tr["exit"]["Xref"], tr["exit"]["accountingTime"]), ("STOP", 105.8, U0 + 6 * MIN))
        self.assertAlmostEqual(tr["exit"]["X"], 105.8 * (1 - 0.0003))
        st2 = flat_store(T0, END, 108)
        set_minute(st2, U0 + 5 * MIN, 105.0, 105.2, 104.9, 105.1)  # gap oltre lo stop: riferimento open peggiore
        lg2 = self.open_ledger(st2)
        lg2.advance(U0 + DAY)
        ex = lg2.trades[0]["exit"]
        self.assertEqual((ex["reason"], ex["Xref"], ex["gap"], ex["accountingTime"]), ("STOP", 105.0, True, U0 + 5 * MIN))

    def test_both_touched_stop_first_with_alternative(self):
        st = flat_store(T0, END, 108)
        set_minute(st, U0 + 3 * MIN, 108, 112.5, 105.5, 109)
        lg = self.open_ledger(st)
        lg.advance(U0 + DAY)
        tr = lg.trades[0]
        self.assertEqual((tr["exit"]["reason"], tr["exit"]["bothTouched"]), ("STOP", True))
        self.assertEqual(tr["targetFirst"]["Xref"], 112.0)
        self.assertGreater(tr["targetFirst"]["delta"], 0)

    def test_entry_and_exit_same_minute_pay_both_fees(self):
        st = flat_store(T0, END, 108)
        set_minute(st, U0, 108, 108.2, 105.6, 106)
        lg = self.open_ledger(st)
        lg.advance(U0 + DAY)
        tr = lg.trades[0]
        self.assertEqual((tr["entryTime"], tr["exit"]["minute"]), (U0, U0))
        self.assertAlmostEqual(tr["feeEntry"], 0.0005 * tr["q"] * tr["E"])
        self.assertAlmostEqual(tr["feeExit"], 0.0005 * tr["q"] * tr["exit"]["X"])

    def test_stop_update_latency_and_activation_gap(self):
        st = flat_store(T0, END, 108)
        eff = U0 + 30 * MIN
        set_minute(st, eff - MIN, 108, 108.1, 107.0, 107.5)  # sotto il nuovo stop ma prima dell'efficacia: resta il vecchio
        set_minute(st, eff, 107.6, 107.8, 107.25, 107.5)
        lg = self.open_ledger(st)
        lg.advance(U0 + MIN)
        lg.accept([{"type": "STOP_UPDATE", "stop": 107.3, "decidedAt": eff - MIN, "effectiveAt": eff, "pivot": 107.5,
                    "pivotCandidateOpen": U0, "previous": 105.8}])
        lg.advance(U0 + DAY)
        tr = lg.trades[0]
        self.assertEqual(tr["stops"][0]["effectiveAt"], eff)
        self.assertEqual((tr["exit"]["reason"], tr["exit"]["Xref"], tr["exit"]["minute"]), ("STOP", 107.3, eff))
        st2 = flat_store(T0, END, 108)
        set_minute(st2, eff, 107.0, 107.1, 106.9, 107.0)  # open già oltre il nuovo stop all'attivazione
        lg2 = self.open_ledger(st2)
        lg2.advance(U0 + MIN)
        lg2.accept([{"type": "STOP_UPDATE", "stop": 107.3, "decidedAt": eff - MIN, "effectiveAt": eff, "pivot": 107.5,
                     "pivotCandidateOpen": U0, "previous": 105.8}])
        lg2.advance(U0 + DAY)
        ex = lg2.trades[0]["exit"]
        self.assertEqual((ex["Xref"], ex["atStopActivation"]), (107.0, True))

    def test_time_exit_end_of_window_and_data_gap(self):
        lg = self.open_ledger(flat_store(T0, END, 108))
        lg.advance(END)
        ex = lg.trades[0]["exit"]
        self.assertEqual((ex["reason"], ex["minute"]), ("TIME_EXIT", U0 + DAY))
        late = END - 30 * MIN
        lg2 = ledger()
        lg2.accept([entry(at=late)])
        lg2.advance(END)
        ex2 = lg2.trades[0]["exit"]
        self.assertEqual((ex2["reason"], ex2["minute"]), ("END_OF_SEGMENT", END - MIN))
        st = flat_store(T0, END, 108)
        st.status[st.index(U0 + 50 * MIN)] = MISSING
        lg3 = self.open_ledger(st)
        lg3.advance(END)
        self.assertEqual(lg3.halted["at"], U0 + 50 * MIN)
        self.assertEqual(lg3.trades[0]["status"], "UNRESOLVED_DATA_GAP")
        self.assertIsNone(lg3.trades[0]["net"])


class Accounting(unittest.TestCase):
    def trade(self, d, x):
        return {"d": d, "q": 10.0, "E": 100.0, "Eref": 100.0, "entryTime": T0, "exit": {"Xref": x, "accountingTime": T0 + DAY, "intrabar": False, "minute": T0 + DAY}}

    def test_protocol_examples(self):
        tau = T0 + 8 * 3_600_000
        lg = ledger(funding=[{"tau": tau, "rate": 0.0001, "intervalHours": 8}], mark={tau: 101.0})
        long = lg.economics(self.trade(1, 102), 0.0005, 0.0, 102.0)
        self.assertAlmostEqual(long["pricePnL"], 20)
        self.assertAlmostEqual(long["feeEntry"] + long["feeExit"], 1.01)
        self.assertAlmostEqual(long["funding"]["total"], -0.101)
        self.assertAlmostEqual(long["net"], 18.889)
        short = lg.economics(self.trade(-1, 98), 0.0005, 0.0, 98.0)
        self.assertAlmostEqual(short["pricePnL"], 20)
        self.assertAlmostEqual(short["feeEntry"] + short["feeExit"], 0.99)
        self.assertAlmostEqual(short["funding"]["total"], 0.101)
        self.assertAlmostEqual(short["net"], 19.111)

    def test_missing_mark_and_boundary_ambiguity(self):
        tau = T0 + 8 * 3_600_000
        lg = ledger(funding=[{"tau": tau, "rate": 0.0001, "intervalHours": 8}], mark={})
        res = lg.economics(self.trade(1, 102), 0.0005, 0.0, 102.0)
        self.assertIsNone(res["net"])  # mai zero
        self.assertTrue(res["funding"]["missing"])
        near = T0 + 8  # 8 ms dopo l'ingresso: contato ma ambiguo
        lg2 = ledger(funding=[{"tau": near, "rate": 0.0001, "intervalHours": 8}], mark={T0: 101.0})
        r2 = lg2.economics(self.trade(1, 102), 0.0005, 0.0, 102.0)
        ev = r2["funding"]["events"][0]
        self.assertTrue(ev["counted"] and ev["ambiguous"])
        self.assertEqual(ev["markMinute"], T0 - MIN)  # mark del minuto precedente
        self.assertAlmostEqual(r2["netRange"][1] - r2["net"], 0.101)  # alternativa: escluso

    def test_slippage_not_subtracted_twice_and_stress_repricing(self):
        st = flat_store(T0, END, 108)
        set_minute(st, U0 + 5 * MIN, 108, 112.2, 107.9, 111)
        lg = ledger(st)
        lg.accept([entry()])
        lg.advance(END)
        tr = lg.trades[0]
        self.assertAlmostEqual(tr["pricePnL"], tr["q"] * (tr["exit"]["X"] - tr["E"]))
        self.assertAlmostEqual(tr["pricePnLRef"], tr["q"] * (112 - 108))
        self.assertLess(tr["slippageCost"], 0)
        self.assertAlmostEqual(tr["net"], tr["pricePnL"] - tr["feeEntry"] - tr["feeExit"])
        s = tr["stress"]
        self.assertAlmostEqual(s["pricePnL"], tr["q"] * (112 * 0.999 - 108 * 1.001))  # stessa quantità e riferimenti
        self.assertAlmostEqual(s["feeEntry"], 0.001 * tr["q"] * 108 * 1.001)
        self.assertLess(s["net"], tr["net"])


if __name__ == "__main__":
    unittest.main()
