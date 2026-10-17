"""CAND-001/D1: selezione deterministica degli esempi e fatti di percorso/costi (dati sintetici, non BTC)."""

import unittest

from obs001.minutes import MinuteStore

from cand001.diagnosis import BAR_MS, economics_facts, management_facts, path_facts, select_examples

MIN = 60_000
B0 = 1_672_531_200_000  # 2023-01-01T00:00Z, chiusura 45m; solo origine sintetica


def store_from(bars, start=B0):
    """bars: lista (o, h, l, c) per minuto da start."""
    st = MinuteStore(start, start + max(len(bars), 1) * MIN)
    for i, (o, h, l, c) in enumerate(bars):
        st.set_minute(i, (o, h, l, c, 1.0, 1.0, 1, 0.5, 0.5))
    return st


def mirror(bars):
    return [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in bars]


def ptrade(d, entry_min, exit_min, xref, stops=(), s0=None, t=None, eref=100.0, r0=2.0):
    s0 = s0 if s0 is not None else eref - d * 2.0
    t = t if t is not None else eref + d * 6.0
    return {"d": d, "Eref": eref, "R0": r0, "S0": s0, "T": t, "entryTime": B0 + entry_min * MIN, "stops": list(stops),
            "exit": {"minute": B0 + exit_min * MIN, "Xref": xref}}


def trade(i, side, entry, net, stops=(), reason="STOP"):
    ep = f"EP:{side}:{i}"
    return {"id": f"TR:{side}:{i}", "episodeId": ep, "side": side, "d": 1 if side == "LONG" else -1, "entryTime": entry, "net": net,
            "stops": [{"effectiveAt": s} for s in stops], "exit": {"reason": reason, "accountingTime": entry + 600_000}}


def episode(i, side, t0, code=None, t_end=None, call=False):
    return {"id": f"EP:{side}:{i}", "side": side, "t0": t0, "call": {"t": t0 + 1} if call else None,
            "termination": {"t": t_end, "code": code} if code else None}


class Selection(unittest.TestCase):
    def test_order_time_then_id_and_dedup_keeps_all_categories(self):
        trades = [trade("b", "LONG", 1_000, -1.0, stops=[1_100]), trade("a", "LONG", 1_000, 2.0), trade("c", "LONG", 5_000, 3.0, reason="TIME_EXIT")]
        episodes = [episode("a", "LONG", 10, call=True), episode("b", "LONG", 10, call=True), episode("c", "LONG", 20, call=True)]
        sel = select_examples(trades, [], episodes)
        ids = [c["episodeId"] for c in sel["cases"]]
        # stesso istante d'ingresso: precede l'ID minore; il primo positivo è "a" anche se "b" ha un netto più estremo
        self.assertEqual(ids, ["EP:LONG:a", "EP:LONG:b", "EP:LONG:c"])
        cats_b = [c["category"] for c in sel["cases"][1]["categories"]]
        self.assertEqual(sorted(cats_b), ["FIRST_NEGATIVE_TRADE", "FIRST_STOP_UPDATED_TRADE"])
        self.assertEqual([c["category"] for c in sel["cases"][2]["categories"]], ["FIRST_TIME_EXIT"])

    def test_empty_category_declared_not_replaced(self):
        trades = [trade("a", "SHORT", 1_000, -1.0)]
        episodes = [episode("a", "SHORT", 10, call=True), episode("z", "SHORT", 5, "INVALIDATED_STRUCTURE", 50)]
        sel = select_examples(trades, [], episodes)
        empty = {(e["category"], e["side"]) for e in sel["emptyCategories"]}
        self.assertIn(("FIRST_POSITIVE_TRADE", "SHORT"), empty)
        self.assertIn(("FIRST_INVALIDATED_DEPTH", "SHORT"), empty)  # un'altra invalidazione non la sostituisce
        self.assertIn(("FIRST_EXIT_STRUCTURE", None), empty)
        self.assertEqual([c["episodeId"] for c in sel["cases"]], ["EP:SHORT:a"])

    def test_abstentions_and_rejected_by_their_own_time(self):
        episodes = [episode("late", "LONG", 1, "ABSTAIN_REWARD_RISK", 900), episode("early", "LONG", 50, "ABSTAIN_REWARD_RISK", 100),
                    episode("r", "SHORT", 30, "REJECTED_PRICE", 61, call=True)]
        reqs = [{"episodeId": "EP:SHORT:r", "side": "SHORT", "executeAt": 61, "outcome": "REJECTED_PRICE"}]
        sel = select_examples([], reqs, episodes)
        ids = [c["episodeId"] for c in sel["cases"]]
        self.assertEqual(ids, ["EP:SHORT:r", "EP:LONG:early"])  # conclusione, non nascita dell'episodio


class Paths(unittest.TestCase):
    # minuti 1..4 detenuti dopo l'ingresso a open del minuto 1; minuto 5 = uscita
    BARS = [(100, 100.5, 99.5, 100), (100, 101, 99.5, 100.8), (100.8, 102.9, 100.5, 102.6), (102.6, 102.7, 99.9, 100.4),
            (100.4, 101, 99.0, 99.4), (99.4, 99.5, 97.0, 97.5), (97.5, 130, 97, 130)]

    def test_long_short_mirror(self):
        lo = path_facts(ptrade(1, 1, 5, 98.0), store_from(self.BARS))
        sh = path_facts(ptrade(-1, 1, 5, 102.0, eref=100.0), store_from(mirror(self.BARS)))
        for k in ("zMaxObserved", "zMinObserved", "zExitReference", "givebackFromMaxObserved", "heldCloses", "minutesToMaxObserved"):
            self.assertAlmostEqual(lo[k], sh[k], places=12, msg=k)
        self.assertAlmostEqual(lo["zMaxObserved"], 1.3)  # close 102.6 del minuto 2, (102.6-100)/2
        self.assertEqual(lo["minutesToMaxObserved"], 2.0)  # chiusura del minuto 2 (B0+3m), ingresso all'open del minuto 1
        self.assertEqual(lo["ledgerViolations"], [])

    def test_intraminute_exit_excludes_exit_minute_and_later_prices(self):
        # Uscita intraminuto nel minuto 5 (low 97 <= stop 98): close 97.5 e minuto 6 a 130 non entrano.
        f = path_facts(ptrade(1, 1, 5, 98.0), store_from(self.BARS))
        self.assertEqual(f["heldCloses"], 4)
        self.assertAlmostEqual(f["zMinObserved"], -0.3)  # close 99.4 del minuto 4, non 97.5 del minuto d'uscita
        self.assertAlmostEqual(f["zExitReference"], -1.0)  # punto finale modellato, separato dalle chiusure

    def test_open_exit_has_no_later_price(self):
        f = path_facts(ptrade(1, 1, 3, 102.6), store_from(self.BARS))  # uscita all'apertura del minuto 3
        self.assertEqual(f["heldCloses"], 2)
        self.assertAlmostEqual(f["zMaxObserved"], 1.3)
        self.assertAlmostEqual(f["givebackFromMaxObserved"], 0.0)

    def test_first_45m_close_only_if_still_held(self):
        bars = [(100, 100.2, 99.9, 100.1)] * 100
        entry, tc_min = 1, BAR_MS // MIN  # ingresso 60 s dopo la chiusura B0; prima chiusura 45m dopo 44 minuti
        before = path_facts(ptrade(1, entry, 11, 100.1), store_from(bars))
        self.assertEqual(before["first45m"]["status"], "CLOSED_BEFORE")
        self.assertIsNone(before["first45m"]["z"])
        intrabar_last = path_facts(ptrade(1, entry, tc_min - 1, 100.1), store_from(bars))
        self.assertEqual(intrabar_last["first45m"]["status"], "CLOSED_BEFORE")  # contatto nel minuto che chiude la barra
        at_open = path_facts(ptrade(1, entry, tc_min, 100.1), store_from(bars))
        self.assertEqual(at_open["first45m"]["status"], "HELD")  # detenuta fino alla chiusura, uscita all'open successivo
        self.assertEqual(at_open["first45m"]["t"], B0 + BAR_MS)
        self.assertAlmostEqual(at_open["first45m"]["z"], 0.05)

    def test_stop_latency(self):
        # Decisione alla chiusura del minuto 2 (B0+3m), nuovo stop 99.6 efficace al minuto 3: nel minuto 2
        # il low 99.0 sta sotto il nuovo stop ma sopra il vecchio 98, quindi nessuna incoerenza.
        bars = [(100, 100.4, 99.8, 100.2), (100.2, 100.6, 99.9, 100.5), (100.5, 100.7, 99.0, 100.3), (100.3, 100.5, 99.5, 99.7)]
        upd = {"decidedAt": B0 + 2 * MIN, "effectiveAt": B0 + 3 * MIN, "from": 98.0, "to": 99.6, "pivot": 99.7, "pivotCandidateOpen": B0}
        activated = path_facts(ptrade(1, 0, 3, 99.6, stops=[upd], s0=98.0), store_from(bars))
        self.assertEqual(activated["ledgerViolations"], [])
        tr = {**ptrade(1, 0, 2, 98.0, s0=98.0), "finalStop": 98.0}
        tr["exit"]["reason"] = "STOP"
        episode = {"states": [{"t": B0 + 2 * MIN, "state": "PROTECTION_UPDATE", "effectiveAt": B0 + 3 * MIN, "current": 98.0, "proposal": 99.6,
                               "pivot": 99.7, "pivotCandidateOpen": B0, "pivotAvailableAt": B0 + 2 * MIN}]}
        m = management_facts(tr, episode)
        self.assertEqual(m["updatesDecided"][0]["outcome"], "NOT_ACTIVATED_EXIT_DURING_LATENCY")
        self.assertEqual((m["updatesActivated"], m["stopAtExitOrigin"]), (0, "INITIAL"))

    def test_cost_identity_slippage_not_subtracted_twice(self):
        # Numeri del protocollo §13 (LONG E100 X102 q10): lordo fill 20, fee 1,01, funding -0,101, netto 18,889.
        tr = {"pricePnLRef": 20.6, "pricePnL": 20.0, "slippageCost": -0.6, "feeEntry": 0.5, "feeExit": 0.51, "net": 18.889,
              "funding": {"total": -0.101, "ambiguous": False, "missing": False}, "riskInitial": 10.0, "netOverRisk": 1.8889,
              "stress": {"net": 15.0}}
        e = economics_facts(tr)
        self.assertAlmostEqual(e["slippage"], 0.6)
        self.assertAlmostEqual(e["identityResidual"], 0.0, places=12)
        self.assertAlmostEqual(e["net"] - (e["pricePnL"] - e["slippage"] - 1.01 - 0.101), 0.6, places=12)  # sottrazione doppia: errata


if __name__ == "__main__":
    unittest.main()
