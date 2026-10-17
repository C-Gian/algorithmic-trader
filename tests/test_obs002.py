"""OBS-002: popolazione causale, snapshot, seguito 24h, riconciliazioni ed esempi (dati sintetici)."""

import copy
import unittest

from obs001.aggregate import Bar
from obs001.observe import observe

from obs002.config import load_study, observation_conventions
from obs002.examples import select
from obs002.outcomes import outcome
from obs002.population import Population, joint_profile
from obs002.summary import cell, design

from obs002_helpers import BAR, DAY, MIN, T0, Mk, daily, long_case, m, minute_store, piv, set_minute, walk_bars

STUDY = load_study()
H = STUDY.horizon_ms


class Attempts(unittest.TestCase):
    def test_first_attempt_continuation_and_rearm(self):
        pop = long_case().run()
        atts = pop.attempts
        self.assertEqual([(a["t"], a["ordinal"]) for a in atts], [(T0 + 25 * BAR, 1), (T0 + 28 * BAR, 2)])
        # barra 25: nuova chiusura oltre il massimo precedente ma senza arretramento -> continuazione, nessuna riga
        first = atts[0]
        self.assertAlmostEqual(first["reaction"]["depth"], 0.5)
        self.assertEqual(first["reaction"]["Rext"], 106)
        self.assertEqual(atts[1]["reaction"]["counterClosesSinceRearmStart"], 1)
        self.assertEqual(atts[1]["groupId"], first["groupId"])

    def test_long_short_mirror(self):
        lo, sh = long_case().run(), long_case().mirror().run()
        self.assertEqual([(a["t"], a["ordinal"]) for a in lo.attempts], [(a["t"], a["ordinal"]) for a in sh.attempts])
        for a, b in zip(lo.attempts, sh.attempts):
            self.assertEqual((a["side"], b["side"]), ("LONG", "SHORT"))
            self.assertAlmostEqual(a["reaction"]["depth"], b["reaction"]["depth"])
            self.assertAlmostEqual(a["trigger"]["beyondPrev"], b["trigger"]["beyondPrev"])
            self.assertEqual(a["snapshot"]["profile"]["profile"], b["snapshot"]["profile"]["profile"])

    def test_attempt_allowed_at_t0_but_never_before_availability(self):
        mk = Mk(60)
        mk.set_bar(20, 110, 112, 109.5, 111)
        mk.set_bar(21, 111, 111.5, 108, 108.5)
        mk.set_bar(22, 108.5, 111.9, 108.4, 111.8)  # riprende già sulla barra di conferma
        for k in range(23, 60):
            mk.set_bar(k, 111.8, 111.85, 111.75, 111.8)
        at_t0 = copy.deepcopy(mk)
        at_t0.leg(piv("LOW", 100, 10), piv("HIGH", 112, 20), 22)
        self.assertEqual([a["t"] for a in at_t0.run().attempts], [mk.t(22)])  # t >= t0 incluso
        late = copy.deepcopy(mk)
        late.leg(piv("LOW", 100, 10), piv("HIGH", 112, 20), 23)  # disponibile solo alla barra 23
        self.assertEqual(late.run().attempts, [])  # nessun tentativo retroattivo alla barra 22

    def test_replace_keeps_group_new_p0_new_group(self):
        mk = long_case(90)
        # REPLACE: P1 più alto (barra 30) con lo stesso P0, disponibile alla barra 32
        mk.set_bar(30, 109.8, 115, 109.7, 114)
        mk.set_bar(31, 114, 114.2, 112, 112.5)
        mk.set_bar(32, 112.5, 112.6, 111, 111.5)
        mk.set_bar(33, 111.5, 113.5, 111.4, 113)
        for k in range(34, 90):
            mk.set_bar(k, 113, 113.1, 112.9, 113)
        mk.leg(piv("LOW", 100, 10), piv("HIGH", 115, 30), 32, action="REPLACE")
        pop = mk.run()
        self.assertEqual([(a["t"], a["ordinal"]) for a in pop.attempts][-1], (mk.t(33), 3))
        self.assertEqual(len(pop.groups), 1)
        old, new = pop.versions
        self.assertEqual((old.retire_reason, old.retire_facts["sameGroup"]), ("NEW_VERSION_SAME_DIRECTION", True))
        self.assertEqual(new.group_id, old.group_id)
        # nuova gamba con P0 diverso: nuovo gruppo e contatore da 1
        mk2 = long_case(90)
        mk2.set_bar(30, 109.8, 115, 109.7, 114)
        mk2.set_bar(31, 114, 114.2, 112, 112.5)
        mk2.set_bar(32, 112.5, 112.6, 111, 111.5)
        mk2.set_bar(33, 111.5, 113.5, 111.4, 113)
        mk2.leg(piv("LOW", 108, 26), piv("HIGH", 115, 30), 32)
        pop2 = mk2.run()
        self.assertEqual(len(pop2.groups), 2)
        self.assertEqual(pop2.attempts[-1]["ordinal"], 1)
        self.assertEqual(pop2.versions[0].retire_facts["sameGroup"], False)

    def test_opposite_direction_coexists_and_reset_retires_both(self):
        mk = long_case(90)
        mk.leg(piv("HIGH", 112, 20), piv("LOW", 106, 22), 24)  # SHORT: non ritira il LONG
        mk.gap(40)
        pop = mk.run()
        lv = [v for v in pop.versions if v.d == 1][0]
        sv = [v for v in pop.versions if v.d == -1][0]
        self.assertEqual((lv.retire_reason, lv.retired_at), ("SEGMENT_RESET", mk.t(40)))
        self.assertEqual((sv.retire_reason, sv.retired_at), ("SEGMENT_RESET", mk.t(40)))
        self.assertTrue(all(a["t"] < mk.t(40) for a in pop.attempts))

    def test_initialization_ordinal_and_end_of_study(self):
        mk = long_case()
        pop = mk.run(study_start=mk.t(26))  # primo tentativo (barra 24) nel prefisso
        dev = [a for a in pop.attempts if a["inStudy"]]
        self.assertEqual([(a["ordinal"], a["priorAttemptsInInitialization"]) for a in dev], [(2, 1)])
        self.assertEqual(pop.versions[0].retire_reason, "END_OF_STUDY")  # amministrativo, non fallimento

    def test_no_cand_guards(self):
        # struttura opposta, reazione oltre P0 (profondità > 1) e P1 lontanissimo: il tentativo resta
        mk = Mk(60, structure="DOWN", dist=-1.0, slope=-1.0)
        mk.set_bar(20, 110, 112, 109.5, 111)
        mk.set_bar(21, 111, 111.5, 95, 96)
        mk.set_bar(22, 96, 96.5, 94, 94.5)
        mk.set_bar(23, 94.5, 97, 94.4, 96.8)
        mk.leg(piv("LOW", 100, 10), piv("HIGH", 112, 20), 22)
        a = mk.run().attempts[0]
        self.assertGreater(a["reaction"]["depth"], 1)
        self.assertEqual(a["snapshot"]["profile"]["profile"], "OPPOSITE")

    def test_degenerate_and_missing_anchor_events_recorded(self):
        mk = long_case()
        mk.events.append({"id": "X1", "type": "FIB_SEQUENCE", "action": "APPEND", "availableAt": mk.t(30), "version": 9, "anchors": None})
        mk.leg(piv("LOW", 115, 28), piv("HIGH", 113, 29), 31)
        pop = mk.run()
        self.assertEqual([e["outcome"] for e in pop.events], ["VERSION", "ANCHORS_MISSING", "L_NOT_POSITIVE"])
        self.assertEqual(len(pop.versions), 1)

    def test_future_changes_do_not_alter_population_until_cutoff(self):
        study = load_study()
        conv = observation_conventions(study)
        bars = walk_bars(32 * 25, seed=5)
        ref = observe(bars, daily(bars), conv)
        cut = 32 * 18
        altered = bars[:cut] + [Bar(b.start, b.end, b.status, b.valid, b.missing, b.invalid, o=b.o * 1.3, h=b.h * 1.4, l=b.l * 0.9, c=b.c * 1.2,
                                    v=b.v, q=b.q, trades=b.trades, tb=b.tb, tq=b.tq) for b in bars[cut:]]
        alt = observe(altered, daily(altered), conv)
        end = T0 + 32 * 25 * BAR
        p1 = Population(bars, ref["45m"], ref["1D"], ref["events"]["45m"], T0, BAR, DAY, T0 + 5 * DAY, end).run()
        p2 = Population(altered, alt["45m"], alt["1D"], alt["events"]["45m"], T0, BAR, DAY, T0 + 5 * DAY, end).run()
        tc = bars[cut - 1].end
        before = lambda p: [a for a in p.attempts if a["t"] <= tc]  # noqa: E731
        self.assertGreater(len(before(p1)), 3)  # il percorso casuale produce davvero tentativi con l'osservatore reale
        self.assertEqual(before(p1), before(p2))
        self.assertTrue(any(v.action == "REPLACE" for v in p1.versions))


class Profiles(unittest.TestCase):
    def rec(self, s, dist, slope):
        return {"piv": {"structure": m(s, "NO_CONFIRMED_PIVOTS")}, "avg": {"dist": m(dist), "slope": m(slope)}}

    def test_four_profiles(self):
        self.assertEqual(joint_profile(self.rec("UP", 0.5, 0.1), 1)["profile"], "CONCORDANT")
        self.assertEqual(joint_profile(self.rec("UP", 0.5, 0.1), -1)["profile"], "OPPOSITE")
        self.assertEqual(joint_profile(self.rec("MIXED", 0.5, 0.1), 1)["profile"], "DISCORDANT")
        self.assertEqual(joint_profile(self.rec("UP", 0.0, 0.1), 1)["profile"], "DISCORDANT")  # zero: non concorde
        self.assertEqual(joint_profile(self.rec(None, 0.5, 0.1), 1)["profile"], "UNAVAILABLE")
        self.assertEqual(joint_profile(self.rec("UP", 0.5, None), 1)["profile"], "UNAVAILABLE")


class Outcomes(unittest.TestCase):
    def setUp(self):
        self.t = T0 + 45 * MIN
        self.end = T0 + 4 * DAY
        self.st = minute_store(T0, 4 * DAY // MIN)

    def out(self, d=1, a=1.0, t=None, end=None):
        return outcome(self.st, t or self.t, 100.0, m(a), d, H, end or self.end)

    def test_window_first_included_last_included_next_excluded(self):
        set_minute(self.st, self.t + H, 100, 105, 100, 100)  # primo minuto dopo la finestra: escluso
        self.assertEqual(self.out()["class"], "NEITHER")
        set_minute(self.st, self.t + H - MIN, 100, 101, 99.95, 100.4)  # ultimo minuto: incluso
        o = self.out()
        self.assertEqual((o["class"], o["contactF"]["minute"]), ("F_ONLY", self.t + H - MIN))
        self.assertAlmostEqual(o["final"], 0.4)
        self.assertEqual(o["Cend"], 100.4)
        set_minute(self.st, self.t, 100, 100.05, 98.9, 100)  # primo minuto (t): incluso
        o = self.out()
        self.assertEqual((o["class"], o["contactA"]["minute"]), ("A_BEFORE_F", self.t))

    def test_same_minute_with_and_without_ordering_open(self):
        u = self.t + 10 * MIN
        set_minute(self.st, u, 100, 101.2, 98.8, 100)
        self.assertEqual(self.out()["class"], "BOTH_UNORDERED")
        set_minute(self.st, u, 101.0, 101.2, 98.8, 100)  # apertura già sul riferimento favorevole (uguaglianza = contatto)
        o = self.out()
        self.assertEqual((o["class"], o["contactF"]["atOpen"], o["contactF"]["interval"]), ("F_BEFORE_A", True, [u, u]))
        set_minute(self.st, u, 98.9, 101.2, 98.8, 100)
        self.assertEqual(self.out()["class"], "A_BEFORE_F")
        sh = self.out(d=-1)  # SHORT: lo stesso minuto, apertura sotto il riferimento contrario del LONG = favorevole SHORT
        self.assertEqual(sh["class"], "F_BEFORE_A")

    def test_long_short_measures(self):
        set_minute(self.st, self.t + 5 * MIN, 100, 103, 99.5, 101)
        lo, sh = self.out(d=1, a=2.0), self.out(d=-1, a=2.0)
        self.assertAlmostEqual(lo["favourable"], 1.5)
        self.assertAlmostEqual(lo["adverse"], 0.25)
        self.assertAlmostEqual(sh["favourable"], 0.25)
        self.assertAlmostEqual(sh["adverse"], 1.5)
        self.assertAlmostEqual(lo["final"], -sh["final"])
        self.assertEqual(lo["maxHighFirstMinute"], self.t + 5 * MIN)

    def test_censoring_gap_missing_and_zero_a(self):
        late = self.end - 600 * MIN
        set_minute(self.st, late + 5 * MIN, 100, 101.5, 99.9, 100)
        c = self.out(t=late)
        self.assertEqual((c["flags"], c["class"], c["final"]), (["RIGHT_CENSORED"], None, None))
        self.assertEqual(c["partial"]["minutes"], 600)
        self.assertEqual(c["partial"]["contactF"]["minute"], late + 5 * MIN)  # contatto noto, esito non completo
        self.st.status[self.st.index(self.t + 30 * MIN)] = 0  # minuto mancante
        g = self.out()
        self.assertEqual((g["flags"], g["class"], g["partial"]["minutes"]), (["GAP"], None, 30))
        self.assertEqual(self.out(a=None)["flags"][-1], "MISSING_A")
        z = self.out(a=0.0)
        self.assertIn("ZERO_A", z["flags"])
        self.assertIsNone(z["markers"])


class Tables(unittest.TestCase):
    def fake(self, n, side, profile, ordinal=1, t0=0):
        return {"attemptId": f"A{side}{profile}{n}{ordinal}", "groupId": f"G{side}{n}", "side": side, "t": T0 + t0 + n * BAR, "ordinal": ordinal,
                "reaction": {"depth": 0.4},
                "snapshot": {"profile": {"profile": profile}, "levels": {"nearestAhead": None, "nearestBehind": None, "atC": []},
                             "volatility": {k: m(1.0) for k in ("LoverA", "toP1", "toRext", "AoverC")},
                             "averages": {"dDist": m(0.1), "dSlope": m(None), "dPos": m(0.2), "crossRelative": m("NONE")},
                             "volume": {"ratio": m(1.2)}, "fibonacci": {"available": False, "reason": "NO_CONFIRMED_PIVOTS"},
                             "structure": {"s1D": m("UP")}}}

    def test_cells_reconcile_and_empty_categories(self):
        atts = [self.fake(1, "LONG", "CONCORDANT"), self.fake(2, "LONG", "OPPOSITE"), self.fake(3, "SHORT", "DISCORDANT"),
                self.fake(4, "LONG", "CONCORDANT", ordinal=2)]
        outs = {a["attemptId"]: {"complete": i != 1, "flags": [] if i != 1 else ["GAP"], "class": None if i == 1 else "NEITHER",
                                 "final": 0.5 if i != 1 else None, "favourable": 0.5, "adverse": 0.1} for i, a in enumerate(atts)}
        des = design(atts, outs)
        self.assertEqual(des["LONG"]["ALL"]["attempts"], 3)
        self.assertEqual(sum(des["LONG"][p]["attempts"] for p in ("CONCORDANT", "OPPOSITE", "DISCORDANT", "UNAVAILABLE")), 3)
        c = cell(atts[:2], outs)
        self.assertEqual((c["complete"], c["incomplete"], c["missingFlags"]["GAP"], sum(c["classes"].values())), (1, 1, 1, 1))
        self.assertEqual(c["coordinates"]["dSmaSlope"]["missing"], {"INSUFFICIENT_HISTORY": 2})
        sel = select(atts, outs)
        self.assertIn("FIRST_SHORT_CONCORDANT", sel["emptyCategories"])  # dichiarata, non sostituita
        self.assertIn("FIRST_CONCORDANT_FINAL_LE_0", sel["emptyCategories"])
        cats = {c["attemptId"]: c["categories"] for c in sel["cases"]}
        self.assertEqual(cats[atts[3]["attemptId"]], ["FIRST_REPEATED_ATTEMPT"])
        self.assertEqual([c["t"] for c in sel["cases"]], sorted(c["t"] for c in sel["cases"]))


if __name__ == "__main__":
    unittest.main()
