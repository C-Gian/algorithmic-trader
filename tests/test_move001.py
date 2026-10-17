"""MOVE-001: ciclo causale, precedenze, posto principale, interruzioni, conteggi ed esempi (dati sintetici)."""

import unittest

from obs001.aggregate import Bar
from obs001.observe import observe

from move001.config import load_study, observation_conventions
from move001.cycle import Cycle
from move001.examples import select
from move001.summary import summarize

from move001_helpers import BAR, T0, Mv, base, kinds, types, with_p1
from obs002_helpers import daily, walk_bars

t = Mv.t


class Lifecycle(unittest.TestCase):
    def test_birth_formation_usable_completion(self):
        mv = with_p1(base())
        mv.bar(14, 113, 108, 110).bar(15, 115, 109, 114).bar(16, 116.4, 113, 115.7)
        cy = mv.run()
        self.assertEqual(kinds(cy), [("BIRTH", None, t(10)), ("P1_PUBLISHED", None, t(13)), ("USABLE", None, t(13)),
                                     ("ARCHIVE", "ESTREMO_RAGGIUNTO", t(16))])
        r = cy.refs[0]
        self.assertEqual((r.archived["judgement"], r.P1["price"]), ("UTILIZZABILE", 116))
        self.assertEqual(r.closes, {"FORMAZIONE": 3, "SOSPESO_CON_P1": 0, "SOSPESO_SENZA_P1": 0, "UTILIZZABILE": 3})

    def test_long_short_mirror(self):
        mv = with_p1(base())
        mv.bar(14, 113, 108, 110).bar(15, 115, 109, 114).bar(16, 116.4, 113, 115.7)
        lo, sh = mv.run(), mv.mirror().run()
        self.assertEqual(kinds(lo), kinds(sh))
        self.assertEqual([r.side for r in sh.refs], ["SHORT"])
        self.assertEqual((sh.refs[0].P0["price"], sh.refs[0].B["price"], sh.refs[0].P1["price"]), (116, 110, 104))

    def test_p1_candle_and_publication_bar_never_complete(self):
        mv = with_p1(base())
        mv.bar(13, 116.5, 109, 111)  # anche se la barra di pubblicazione arrivasse a P1, non è un contatto successivo
        cy = mv.run()
        self.assertEqual(types(cy), ["BIRTH", "P1_PUBLISHED", "USABLE"])

    def test_close_beyond_base_loses_and_recovery_does_not_restore(self):
        mv = with_p1(base())
        mv.bar(14, 109, 103, 103.5).bar(15, 109, 107, 108)
        cy = mv.run()
        self.assertEqual(kinds(cy)[-1], ("ARCHIVE", "ORIGINE_IN_CHIUSURA", t(14)))
        self.assertEqual(cy.refs[0].archived["conditionBefore"], "UTILIZZABILE")
        self.assertEqual(len(cy.refs), 1)

    def test_loss_during_formation_keeps_p1_missing(self):
        mv = base()
        mv.bar(11, 111, 103, 103.9)
        cy = mv.run()
        r = cy.refs[0]
        self.assertEqual((r.archived["reason"], r.archived["conditionBefore"], r.P1), ("ORIGINE_IN_CHIUSURA", "FORMAZIONE", None))

    def test_double_test_unordered_and_suspension_not_reactivated(self):
        mv = with_p1(base())
        mv.bar(14, 117, 103.8, 112).bar(15, 115, 109, 113).bar(16, 116.5, 110, 112)
        cy = mv.run()
        self.assertEqual(kinds(cy)[3:], [("SUSPENSION", "TEST_ORIGINE", t(14)), ("FACT", "P1_TOCCATO_DA_SOSPESO", t(16))])
        self.assertEqual(cy.ledger[3]["flags"], ["DOPPIO_TEST_ORDINE_IGNOTO"])
        self.assertIsNone(cy.refs[0].archived)
        self.assertEqual(cy.refs[0].condition(), "SOSPESO_CON_P1")

    def test_opposite_structure_at_birth_and_later(self):
        at_birth = with_p1(base().structure(10, "DOWN", 10))
        cy = at_birth.run()
        self.assertEqual(kinds(cy)[:2], [("BIRTH", None, t(10)), ("SUSPENSION", "STRUTTURA_OPPOSTA_ALLA_NASCITA", t(10))])
        self.assertTrue(cy.ledger[2]["whileSuspended"])  # P1 noto ma nessun passaggio a UTILIZZABILE
        self.assertNotIn("USABLE", types(cy))
        self.assertEqual(types(base().structure(10, "MIXED", 10).run()), ["BIRTH"])  # MIXED non sospende
        later = with_p1(base().structure(15, "DOWN"))
        self.assertEqual(kinds(later.run())[-1], ("SUSPENSION", "STRUTTURA_OPPOSTA", t(15)))
        same_bar = with_p1(base().structure(16, "DOWN"))
        same_bar.bar(16, 116.4, 113, 115.7)
        self.assertEqual(kinds(same_bar.run())[-1], ("ARCHIVE", "ESTREMO_RAGGIUNTO", t(16)))  # completamento prima della struttura

    def test_base_tested_in_birth_bar_or_crossing_before_availability_no_birth(self):
        mv = base()
        mv.bar(10, 111.5, 103.9, 111, o=109)
        self.assertEqual(mv.run().refs, [])
        early = base()
        early.bar(8, 111, 107.9, 110.8).bar(9, 112, 110.2, 111.5).bar(10, 112, 110.5, 111.8)  # rottura alla barra 8, P0 noto solo alla 9
        self.assertEqual(early.run().refs, [])

    def test_p1_fixed_and_keep_not_accepted(self):
        mv = with_p1(base())
        mv.pivot("HIGH", 118, 14, action="REPLACE")
        mv.bar(18, 116.2, 112, 113)
        cy = mv.run()
        self.assertEqual(cy.refs[0].P1["price"], 116)
        self.assertEqual(kinds(cy)[-1], ("ARCHIVE", "ESTREMO_RAGGIUNTO", t(18)))
        keep = base()
        keep.pivot("HIGH", 116, 11, action="KEEP")
        self.assertIsNone(keep.run().refs[0].P1)


class Slot(unittest.TestCase):
    def test_formation_occupies_same_and_opposite_direction(self):
        same = base()
        same.pivot("HIGH", 109.5, 11).pivot("LOW", 106.5, 13).bar(16, 110, 107.9, 109.8, o=108)
        cy = same.run()
        self.assertEqual([s["outcome"] for s in cy.structures][-1], "NON_ADOTTATA_OCCUPATO_FORMAZIONE")
        self.assertEqual(types(cy)[-1], "CANDIDATE_REJECTED")
        opp = base()
        opp.pivot("HIGH", 109.5, 11).pivot("LOW", 107, 13).pivot("HIGH", 109, 15).bar(18, 107.5, 106.3, 106.5)
        s = opp.run().structures[-1]
        self.assertEqual((s["side"], s["outcome"], s["occupant"]["condition"]), ("SHORT", "NON_ADOTTATA_OCCUPATO_FORMAZIONE", "FORMAZIONE"))

    def test_usable_occupies_and_completion_frees_slot_same_close(self):
        rej = with_p1(base())
        rej.pivot("LOW", 108, 14).pivot("HIGH", 112, 16).bar(20, 107.8, 107.3, 107.5)
        s = rej.run().structures[-1]
        self.assertEqual((s["side"], s["outcome"]), ("SHORT", "NON_ADOTTATA_OCCUPATO_UTILIZZABILE"))
        free = with_p1(base())
        free.pivot("LOW", 106, 14).bar(17, 116.5, 110, 116.3, o=110)
        cy = free.run()
        self.assertEqual(kinds(cy)[-2:], [("ARCHIVE", "ESTREMO_RAGGIUNTO", t(17)), ("BIRTH", None, t(17))])
        self.assertIsNone(cy.refs[1].predecessor)  # posto liberato dal completamento, non una sostituzione

    def test_freshness_then_replacement_after_suspension(self):
        mv = with_p1(base())
        mv.bar(14, 112, 103.8, 109.5).bar(15, 110, 108.3, 108.5)           # test della base alla barra 14
        mv.pivot("LOW", 109, 12).pivot("HIGH", 113, 13)                    # SHORT con P0 candidato 13 <= barra del test
        mv.pivot("LOW", 107, 15).pivot("HIGH", 111, 17)                    # SHORT con P0 candidato 17 > barra del test
        mv.bar(21, 107.5, 106.3, 106.5)
        cy = mv.run()
        self.assertEqual([s["outcome"] for s in cy.structures], ["ADOTTATA", "NON_ADOTTATA_FRESCHEZZA", "ADOTTATA"])
        old, new = cy.refs
        self.assertEqual((old.archived["reason"], old.archived["judgementReason"], old.archived["replacedBy"]),
                         ("SOSTITUITO_DA_NUOVA_STRUTTURA", "TEST_ORIGINE", new.id))
        self.assertEqual((new.side, new.predecessor, new.birth_t), ("SHORT", old.id, t(21)))

    def test_rejected_candidate_never_recovered(self):
        mv = base()
        mv.pivot("HIGH", 109.5, 11).pivot("LOW", 106.5, 13).bar(16, 110, 107.9, 109.8, o=108)
        mv.bar(17, 109.8, 103, 103.5)                       # il principale perde la base: posto libero
        mv.bar(18, 109, 103.4, 109.2).bar(19, 110, 109, 109.9)  # riattraversa 109,5 con la stessa tripla
        cy = mv.run()
        self.assertEqual(len(cy.refs), 1)
        self.assertEqual(len(cy.structures), 2)

    def test_gap_archives_and_restarts_without_old_anchors(self):
        mv = with_p1(base())
        mv.gap(15)
        mv.bar(16, 108.5, 107.8, 108).bar(17, 117, 108, 116.8)  # dopo la lacuna: prezzo oltre P1 e B, ma nessuna nuova tripla
        cy = mv.run()
        r = cy.refs[0]
        self.assertEqual((r.archived["reason"], r.archived["judgement"], r.archived["judgementReason"]),
                         ("CONTINUITA_INTERROTTA", "INDETERMINATO", "DATI_INCOMPLETI"))
        self.assertEqual((r.archived["lastCompleteClose"], r.archived["firstIncompleteClose"]), (t(14), t(15)))
        self.assertEqual(len(cy.refs), 1)
        self.assertFalse(cy.closes[15]["complete"])

    def test_end_of_coverage_is_administrative(self):
        cy = with_p1(base()).run(end_k=20)
        self.assertEqual(kinds(cy, admin=True)[-1], ("OPEN_AT_END", "FINE_COPERTURA", t(20)))
        self.assertIsNone(cy.refs[0].archived)


class Causality(unittest.TestCase):
    def test_same_prefix_different_futures(self):
        study = load_study()
        conv = observation_conventions(study)
        bars = walk_bars(32 * 30, seed=9)
        cut = 32 * 20
        alt = bars[:cut] + [Bar(b.start, b.end, b.status, b.valid, b.missing, b.invalid, o=b.o * 0.8, h=b.h * 0.95, l=b.l * 0.7, c=b.c * 0.75,
                                v=b.v, q=b.q, trades=b.trades, tb=b.tb, tq=b.tq) for b in bars[cut:]]
        end = T0 + len(bars) * BAR
        runs = []
        for bb in (bars, alt):
            obs = observe(bb, daily(bb), conv)
            runs.append(Cycle(bb, obs["45m"], obs["events"]["45m"], T0, BAR, end).run())
        tc = bars[cut - 1].end
        a, b = runs
        self.assertGreater(sum(1 for e in a.ledger if e["type"] == "BIRTH" and e["t"] <= tc), 2)  # l'osservatore reale produce nascite
        self.assertEqual([e for e in a.ledger if e["t"] <= tc], [e for e in b.ledger if e["t"] <= tc])
        self.assertEqual([s for s in a.structures if s["t"] <= tc], [s for s in b.structures if s["t"] <= tc])
        self.assertEqual([c for c in a.closes if c["t"] <= tc], [c for c in b.closes if c["t"] <= tc])


class Reporting(unittest.TestCase):
    def test_counts_reconcile_and_empty_categories(self):
        mv = with_p1(base())
        mv.bar(14, 113, 108, 110).bar(15, 115, 109, 114).bar(16, 116.4, 113, 115.7)
        cy = mv.run()
        s = summarize(cy, T0, cy.end, BAR)
        dev = s["tables"]["DEV"]
        self.assertEqual(dev["stock"], {"start": 0, "births": 1, "archives": 1, "end": 0})
        self.assertEqual(sum(dev["closes"]["byCondition"].values()), dev["closes"]["complete"])
        d = s["durationsDev"]
        self.assertEqual((d["birthToP1"]["available"]["p50"], d["birthToArchiveOrEnd"]["available"]["max"]), (3, 6))
        self.assertEqual(d["birthToP1"]["censoredCount"], 0)
        sel = select(cy.ledger, cy.refs, T0, cy.end)
        self.assertEqual([c["categories"][0]["category"] for c in sel["cases"]], ["BIRTH_LONG"])
        self.assertIn("BASE_LOST", sel["emptyCategories"])
        self.assertIn("BIRTH_SHORT", sel["emptyCategories"])

    def test_open_reference_durations_censored(self):
        cy = base().run(end_k=20)
        d = summarize(cy, T0, cy.end, BAR)["durationsDev"]
        self.assertEqual((d["birthToP1"]["censoredCount"], d["birthToP1"]["available"]["n"]), (1, 0))  # mai zero
        self.assertEqual(d["birthToArchiveOrEnd"]["censored"]["max"], 10)


if __name__ == "__main__":
    unittest.main()
