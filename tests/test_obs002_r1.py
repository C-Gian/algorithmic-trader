"""OBS-002/R1: proiezione causale delle timeline (R1-A) e riepilogo aritmetico dei contatti (R1-C).

R1-A è una regressione scritta prima della correzione: fallisce sulla consegna c8ac744, dove i fatti
di un ritiro futuro (replacedBy, sameGroup) comparivano in knownAtT.
"""

import copy
import unittest

from obs002.cli import population_body, timeline
from obs002.tables import contact_breakdown
from obs002.timelines import migrate_examples

from obs002_helpers import long_case, piv


def with_future(kind: str):
    """Stesso prefisso di long_case(90); futuro diverso dopo il secondo tentativo (barra 27)."""
    mk = long_case(90)
    if kind == "END":  # nessuna sostituzione: ritiro amministrativo a fine studio
        return mk
    p1_bar = 30 if kind == "REPLACE_30" else 31
    mk.set_bar(p1_bar, 109.8, 115, 109.7, 114)
    mk.set_bar(p1_bar + 1, 114, 114.2, 112, 112.5)
    mk.set_bar(p1_bar + 2, 112.5, 112.6, 111, 111.5)
    mk.set_bar(p1_bar + 3, 111.5, 113.5, 111.4, 113)
    mk.leg(piv("LOW", 100, 10), piv("HIGH", 115, p1_bar), p1_bar + 2, action="REPLACE")
    return mk


def known(mk, n):
    pop = mk.run()
    a = pop.attempts[n]
    return timeline({"categories": ["TEST"]}, a, {"label": "a posteriori"}, pop, {"bars45": mk.bars})["knownAtT"], pop


class CausalTimeline(unittest.TestCase):
    def test_future_retirement_facts_never_known_before_effect(self):
        views = [known(with_future(k), 0)[0] for k in ("END", "REPLACE_30", "REPLACE_31")]
        self.assertEqual(views[0], views[1])
        self.assertEqual(views[0], views[2])
        v = views[1]["groupVersionsSoFar"][0]
        for key in ("replacedBy", "sameGroup"):
            self.assertNotIn(key, v)
        self.assertIsNone(v["retiredAt"])
        self.assertIsNone(v["retireReason"])
        self.assertEqual(v["attempts"], [views[1]["attempt"]["attemptId"]])  # i tentativi successivi non sono noti

    def test_retirement_facts_kept_once_effective(self):
        kn, pop = known(with_future("REPLACE_30"), 2)  # tentativo sulla nuova versione, dopo il REPLACE
        old = kn["groupVersionsSoFar"][0]
        self.assertEqual(old["retireReason"], "NEW_VERSION_SAME_DIRECTION")
        self.assertEqual(old["replacedBy"], pop.versions[1].id)
        self.assertTrue(old["sameGroup"])
        self.assertEqual(len(old["attempts"]), 2)
        new = kn["groupVersionsSoFar"][1]
        self.assertIsNone(new["retiredAt"])  # il ritiro a fine studio è futuro anche qui
        self.assertNotIn("replacedBy", new)


class Migration(unittest.TestCase):
    def test_migrated_original_equals_corrected_generator(self):
        mk = with_future("REPLACE_30")
        pop = mk.run()
        a = pop.attempts[0]
        good = timeline({"categories": ["TEST"]}, a, {"label": "a posteriori"}, pop, {"bars45": mk.bars})
        leaked = copy.deepcopy(good)  # forma della consegna c8ac744: fatti del ritiro futuro presenti
        leaked["knownAtT"]["groupVersionsSoFar"][0].update(replacedBy=pop.versions[1].id, sameGroup=True)
        body = population_body(pop)
        original = {"cases": [{"attemptId": a["attemptId"]}], "emptyCategories": [], "listSha256": "x", "timelines": [leaked]}
        fixed = migrate_examples(original, body)
        self.assertEqual(fixed["timelines"][0], good)
        self.assertEqual({k: v for k, v in fixed.items() if k != "timelines"}, {k: v for k, v in original.items() if k != "timelines"})
        self.assertEqual(migrate_examples(fixed, body), fixed)  # ripetibile e idempotente

    def test_migration_refuses_a_different_population(self):
        mk = with_future("REPLACE_30")
        pop = mk.run()
        tl = timeline({"categories": ["TEST"]}, pop.attempts[2], {}, pop, {"bars45": mk.bars})
        other = population_body(with_future("END").run())
        with self.assertRaises(AssertionError):
            migrate_examples({"timelines": [tl]}, other)


class ContactArithmetic(unittest.TestCase):
    def test_at_least_one_is_not_both(self):
        # righe LONG e SHORT «Tutti» della tabella principale consegnata
        long = {"F_ONLY": 528, "A_ONLY": 436, "F_BEFORE_A": 614, "A_BEFORE_F": 624, "BOTH_UNORDERED": 3, "NEITHER": 22}
        short = {"F_ONLY": 428, "A_ONLY": 508, "F_BEFORE_A": 617, "A_BEFORE_F": 571, "BOTH_UNORDERED": 1, "NEITHER": 16}
        b = contact_breakdown({k: long[k] + short[k] for k in long})
        self.assertEqual((b["complete"], b["both"], b["oneOnly"], b["none"], b["atLeastOne"]), (4368, 2430, 1900, 38, 4330))
        self.assertAlmostEqual(b["shares"]["both"], 0.5563, places=4)
        self.assertAlmostEqual(b["shares"]["oneOnly"], 0.4350, places=4)
        self.assertAlmostEqual(b["shares"]["atLeastOne"], 0.9913, places=4)

    def test_empty_and_unknown_class(self):
        empty = contact_breakdown({c: 0 for c in ("F_ONLY", "A_ONLY", "F_BEFORE_A", "A_BEFORE_F", "BOTH_UNORDERED", "NEITHER")})
        self.assertIsNone(empty["shares"]["both"])
        with self.assertRaises(AssertionError):
            contact_breakdown({"F_ONLY": 1, "A_ONLY": 0, "F_BEFORE_A": 0, "A_BEFORE_F": 0, "BOTH_UNORDERED": 0, "NEITHER": 0, "ALTRO": 2})


if __name__ == "__main__":
    unittest.main()
