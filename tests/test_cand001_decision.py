"""CAND-001/v1: riconoscimento, reazione, contraddizioni, trigger e gestione su dati costruiti a mano."""

import unittest

from cand001 import decision as D
from cand001.decision import PositionView

from cand001_helpers import BAR, Market, T0, long_example, piv, run_closes, short_example


def states(engine):
    return [(round((d["t"] - T0) / BAR) - 1, d["state"]) for d in engine.decisions if d["state"] not in ("NO_NEW_SETUP",)]


class ProtocolExamples(unittest.TestCase):
    def test_long_example_plan(self):
        mk = long_example()
        e = mk.engine()
        actions = run_closes(e, 22, 24)
        self.assertEqual(states(e), [(22, "RECOGNIZED"), (22, "WAIT_RESUMPTION"), (23, "WAIT_RESUMPTION"), (24, "CALL")])
        (req,) = actions
        ep = e.episodes[0]
        self.assertEqual((ep.side, ep.length, ep.a0), ("LONG", 12, 2.0))
        self.assertAlmostEqual(ep.plan["Rext"], 106)
        self.assertAlmostEqual(ep.plan["depth"], 0.5)
        self.assertAlmostEqual(req["S0"], 105.8)
        self.assertEqual(req["T"], 112)
        self.assertAlmostEqual(ep.plan["Estar"], 108.0324)
        self.assertAlmostEqual(ep.plan["risk"], 2.2324)
        self.assertAlmostEqual(ep.plan["gain"], 3.9676)
        self.assertGreaterEqual(ep.plan["ratio"], 1.5)
        self.assertEqual(req["executeAt"], mk.t(24) + 60_000)  # mai alla chiusura del segnale
        self.assertAlmostEqual(ep.call["entryBound"], (112 + 1.5 * 105.8) / 2.5)

    def test_short_mirror(self):
        mk = short_example()
        e = mk.engine()
        (req,) = run_closes(e, 22, 24)
        ep = e.episodes[0]
        self.assertEqual(ep.side, "SHORT")
        self.assertAlmostEqual(ep.plan["Rext"], 106)
        self.assertAlmostEqual(req["S0"], 106.2)
        self.assertEqual(req["T"], 100)
        self.assertAlmostEqual(ep.plan["Estar"], 103.9688)
        self.assertEqual(req["d"], -1)


class Causality(unittest.TestCase):
    def test_no_retroactive_call_on_confirmation_bars(self):
        mk = long_example()
        mk.set_bar(22, 108.5, 109, 106, 109.6)  # alla chiusura di conferma il trigger sarebbe vero
        e = mk.engine()
        self.assertEqual(run_closes(e, 22, 22), [])
        self.assertEqual(states(e)[-1], (22, "WAIT_RESUMPTION"))

    def test_leg_only_when_available(self):
        mk = long_example()
        e = mk.engine()
        run_closes(e, 15, 21)
        self.assertEqual(e.episodes, [])  # P1 (barra 20) non è noto prima della chiusura della barra 22

    def test_daily_structure_is_context_only(self):
        mk = long_example()
        e = mk.engine()  # nessun giorno chiuso: 1D indisponibile non blocca
        self.assertEqual(len(run_closes(e, 22, 24)), 1)
        self.assertEqual(e.episodes[0].context0["structure1D"]["r"], "INSUFFICIENT_HISTORY")
        mk2 = long_example(offset=32)
        e2 = mk2.engine()  # 1D chiuso DOWN, contrario al LONG: solo contesto
        self.assertEqual(len(run_closes(e2, 54, 56)), 1)
        self.assertEqual(e2.episodes[0].context0["structure1D"]["v"], "DOWN")


class Recognition(unittest.TestCase):
    def test_amplitude_threshold(self):
        mk = long_example()
        mk.recs[22]["vol"]["A"] = {"v": 4.0, "r": None}  # 3A=12=L: ammesso (>=)
        e = mk.engine()
        run_closes(e, 22, 22)
        self.assertEqual(len(e.episodes), 1)
        mk2 = long_example()
        mk2.recs[22]["vol"]["A"] = {"v": 4.01, "r": None}
        e2 = mk2.engine()
        run_closes(e2, 22, 22)
        self.assertEqual(e2.legs[0]["outcome"], D.ABSTAIN_AMPLITUDE)
        self.assertEqual(e2.episodes, [])

    def test_structure_and_duration(self):
        mk = long_example()
        mk.structure(22, "MIXED")
        e = mk.engine()
        run_closes(e, 22, 30)
        self.assertEqual(e.legs[0]["outcome"], D.ABSTAIN_STRUCTURE)
        self.assertEqual(e.episodes, [])  # gamba consumata, mai riesaminata
        mk2 = Market(n=80)
        mk2.leg(piv("LOW", 100, 2), piv("HIGH", 112, 40), 42)
        e2 = mk2.engine()
        run_closes(e2, 42, 42)
        self.assertEqual(e2.legs[0]["outcome"], D.ABSTAIN_DURATION)  # 38 barre > 32

    def test_busy_skips_new_leg(self):
        mk = long_example()
        mk.leg(piv("HIGH", 112, 20), piv("LOW", 106, 22), 23)  # nuova gamba nota a 23, durante l'episodio
        e = mk.engine()
        run_closes(e, 22, 23)
        self.assertEqual([lg["outcome"] for lg in e.legs], ["RECOGNIZED", D.SKIPPED_BUSY])


class Reaction(unittest.TestCase):
    def test_depth_bounds_and_wait_reaction(self):
        mk = long_example()
        mk.set_bar(21, 111, 111.5, 109.3, 110)
        mk.set_bar(22, 109.5, 109.6, 109.2, 109.4)  # Rext=109,2: profondità 0,233 < 1/4
        e = mk.engine()
        run_closes(e, 22, 22)
        self.assertEqual(states(e)[-1], (22, "WAIT_REACTION"))
        mk2 = long_example()
        mk2.set_bar(23, 106.5, 107.5, 103, 107)  # Rext=103: profondità 0,75 esatta, ammessa
        mk2.set_bar(24, 107, 108.2, 106.8, 108)
        e2 = mk2.engine()
        run_closes(e2, 22, 24)
        # 0,75 non invalida: si arriva al trigger; qui lo stop lontano porta il rapporto sotto 1,5.
        self.assertEqual(states(e2)[-2:], [(23, "WAIT_RESUMPTION"), (24, "ABSTAIN_REWARD_RISK")])
        self.assertAlmostEqual(e2.episodes[0].plan["depth"], 0.75)
        mk3 = long_example()
        mk3.set_bar(23, 106.5, 107.5, 102.9, 107)  # 0,758 > 3/4
        e3 = mk3.engine()
        run_closes(e3, 22, 24)
        self.assertEqual(e3.episodes[0].status, D.INVALIDATED_DEPTH)

    def test_contradiction_precedes_trigger(self):
        mk = long_example()
        mk.structure(24, "DOWN")  # alla barra di trigger la struttura diventa opposta
        e = mk.engine()
        self.assertEqual(run_closes(e, 22, 24), [])
        self.assertEqual(e.episodes[0].status, D.INVALIDATED_STRUCTURE)
        mk2 = long_example()
        mk2.set_bar(23, 106.5, 112, 106.2, 107)  # obiettivo P1 già toccato
        e2 = mk2.engine()
        run_closes(e2, 22, 24)
        self.assertEqual(e2.episodes[0].status, D.INVALIDATED_TARGET_REACHED)

    def test_expiry_at_bar_12(self):
        mk = long_example()
        for k in range(23, 33):
            mk.set_bar(k, 107, 107.5, 106.5, 106.9)  # nessun trigger
        mk.set_bar(32, 106.9, 107.6, 106.5, 107.55)  # k-i=12: trigger ancora ammesso
        e = mk.engine()
        run_closes(e, 22, 32)
        self.assertEqual(states(e)[-1], (32, "CALL"))
        mk2 = long_example()
        for k in range(23, 34):
            mk2.set_bar(k, 107, 107.5, 106.5, 106.9)
        e2 = mk2.engine()
        run_closes(e2, 22, 33)
        self.assertEqual(e2.episodes[0].status, D.EXPIRED)

    def test_reward_risk_abstention(self):
        mk = long_example()
        mk.set_bar(24, 107, 110.5, 106.8, 110.4)  # ripresa troppo vicina al target: rapporto < 1,5
        e = mk.engine()
        self.assertEqual(run_closes(e, 22, 24), [])
        self.assertEqual(e.episodes[0].status, D.ABSTAIN_REWARD_RISK)


class Management(unittest.TestCase):
    def pos(self, entry_k=25, stop=105.8):
        return PositionView("EP:x", 1, T0 + entry_k * BAR + 60_000, stop, 112.0, 2.0)

    def test_protection_only_after_entry_and_monotone(self):
        mk = long_example()
        e = mk.engine()
        run_closes(e, 22, 24)
        before = piv("LOW", 107, 24)  # candela iniziata prima dell'ingresso
        after = piv("LOW", 107.5, 27)
        mk.events.append({"type": "PIVOT_CONFIRMED", "kind": "LOW", "price": 107, "candidateOpen": before["candidateOpen"], "availableAt": mk.t(26)})
        mk.events.append({"type": "PIVOT_CONFIRMED", "kind": "LOW", "price": 107.5, "candidateOpen": after["candidateOpen"], "availableAt": mk.t(29)})
        mk.set_bar(29, 108, 109, 108, 108.6)
        e2 = mk.engine()
        e2.episode = e.episodes[0]
        self.assertEqual(run_closes(e2, 26, 26, self.pos()), [])
        (upd,) = run_closes(e2, 29, 29, self.pos())
        self.assertAlmostEqual(upd["stop"], 107.3)
        self.assertEqual(upd["effectiveAt"], mk.t(29) + 60_000)
        # Proposta non migliorativa rispetto a uno stop già più alto: scartata.
        self.assertEqual(run_closes(e2, 29, 29, self.pos(stop=107.4)), [])

    def test_exit_on_opposite_structure(self):
        mk = long_example()
        mk.structure(30, "DOWN")
        e = mk.engine()
        run_closes(e, 22, 24)
        (ex,) = run_closes(e, 30, 30, self.pos())
        self.assertEqual((ex["type"], ex["reason"], ex["executeAt"]), ("EXIT", "EXIT_STRUCTURE", mk.t(30) + 60_000))


if __name__ == "__main__":
    unittest.main()
