"""CAND-001/D1: selezione deterministica degli esempi (record sintetici, non BTC)."""

import unittest

from cand001.diagnosis import select_examples


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


if __name__ == "__main__":
    unittest.main()
