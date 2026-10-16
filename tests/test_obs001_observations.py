"""OBS-001: formule, disponibilità per misura, pivot, livelli e Fibonacci su barre sintetiche."""

import unittest

from obs001.aggregate import INCOMPLETE, Bar
from obs001.observe import ScaleObserver

from obs001_helpers import CONV, bar, hl_bars, linear_bars


def run(bars, prev_day=None):
    obs = ScaleObserver("45m", CONV)
    return obs, [obs.step(b, prev_day) for b in bars]


class PrefixedExample(unittest.TestCase):
    """Esempio numerico prefissato nella sezione 8 del task."""

    def setUp(self):
        self.obs, self.recs = run(linear_bars(51))

    def r(self, i):
        return self.recs[i - 1]

    def test_true_range_and_a(self):
        self.assertEqual(self.r(1)["vol"]["tr"], {"v": None, "r": "INSUFFICIENT_HISTORY"})
        self.assertEqual(self.r(2)["vol"]["tr"]["v"], 2)
        self.assertIsNone(self.r(20)["vol"]["A"]["v"])
        self.assertEqual(self.r(21)["vol"]["A"]["v"], 2)

    def test_averages(self):
        self.assertEqual(self.r(20)["avg"]["sma20"]["v"], 110.5)
        self.assertIsNone(self.r(19)["avg"]["sma20"]["v"])
        self.assertEqual(self.r(24)["avg"]["sma20"]["v"], 114.5)
        self.assertEqual(self.r(24)["avg"]["slope"]["v"], 2)
        self.assertIsNone(self.r(23)["avg"]["slope"]["v"])
        self.assertEqual(self.r(50)["avg"]["sma50"]["v"], 125.5)
        self.assertEqual(self.r(50)["avg"]["sma20"]["v"], 140.5)
        self.assertEqual(self.r(50)["avg"]["dist"]["v"], 7.5)
        self.assertIsNone(self.r(49)["avg"]["dist"]["v"])
        self.assertEqual(self.r(21)["avg"]["pos"]["v"], 4.75)
        self.assertIsNone(self.r(20)["avg"]["pos"]["v"])

    def test_cross_needs_51_bars(self):
        self.assertEqual(self.r(50)["avg"]["cross"]["r"], "INSUFFICIENT_HISTORY")
        self.assertEqual(self.r(51)["avg"]["cross"], {"v": "NONE", "r": None})

    def test_volume_ratio_excludes_current(self):
        self.assertIsNone(self.r(20)["volu"]["ratio"]["v"])
        self.assertEqual(self.r(21)["volu"]["ratio"]["v"], 2)
        self.assertEqual(self.r(21)["volu"]["median"]["v"], 10.5)

    def test_independent_of_pivots(self):
        # Rialzo lineare: nessun pivot confermato, struttura indisponibile ma medie calcolate.
        self.assertEqual(self.r(51)["piv"]["structure"], {"v": None, "r": "NO_CONFIRMED_PIVOTS"})
        self.assertIsNotNone(self.r(51)["avg"]["dist"]["v"])
        self.assertEqual(self.r(51)["fib"]["anchors"]["r"], "NO_CONFIRMED_PIVOTS")


class ZeroDenominators(unittest.TestCase):
    def test_zero_a_is_known_zero_and_ratios_are_null(self):
        bars = [bar(i, 100, 100, 100, 100, v=1.0) for i in range(51)]
        _, recs = run(bars)
        last = recs[-1]
        self.assertEqual(last["vol"]["A"], {"v": 0.0, "r": None})
        self.assertEqual(last["vol"]["AoverC"], {"v": 0.0, "r": None})
        for key in ("dist", "slope", "pos"):
            self.assertEqual(last["avg"][key], {"v": None, "r": "ZERO_DENOMINATOR"}, key)
        self.assertEqual(last["avg"]["cross"]["r"], "ZERO_DENOMINATOR")

    def test_volume_zero_median_vs_zero_current(self):
        zero = [bar(i, 100, 101, 99, 100, v=0.0) for i in range(21)]
        _, recs = run(zero)
        self.assertEqual(recs[-1]["volu"]["ratio"], {"v": None, "r": "ZERO_DENOMINATOR"})
        current_zero = [bar(i, 100, 101, 99, 100, v=5.0) for i in range(20)] + [bar(20, 100, 101, 99, 100, v=0.0)]
        _, recs = run(current_zero)
        self.assertEqual(recs[-1]["volu"]["ratio"], {"v": 0.0, "r": None})


class Pivots(unittest.TestCase):
    def test_revealed_exactly_at_i_plus_2(self):
        highs = [10, 11, 15, 12, 11, 10]
        lows = [5, 6, 7, 6, 5, 4]
        obs, recs = run(hl_bars(highs, lows))
        confirmed = [e for e in obs.events if e["type"] == "PIVOT_CONFIRMED"]
        self.assertEqual(len(confirmed), 1)
        ev = confirmed[0]
        self.assertEqual(ev["kind"], "HIGH")
        self.assertEqual(ev["eventTime"], recs[2]["end"])
        self.assertEqual(ev["availableAt"], recs[4]["end"])
        self.assertEqual(ev["candidateOpen"], recs[2]["open"])
        self.assertEqual(recs[3]["lvl"][0]["reason"], "NO_CONFIRMED_PIVOTS")  # non ancora noto a i+1
        self.assertEqual(recs[4]["lvl"][0]["price"], 15)

    def test_tie_and_dual(self):
        obs, recs = run(hl_bars([10, 11, 15, 15, 11], [5, 6, 7, 6, 5]))
        self.assertEqual(recs[4]["piv"]["check"]["v"]["high"], "TIE")
        self.assertEqual([e["reason"] for e in obs.events if e["type"] == "PIVOT_REJECTED"], ["TIE"])
        obs, recs = run(hl_bars([10, 11, 15, 12, 11], [5, 4, 1, 4, 5]))
        self.assertEqual(recs[4]["piv"]["check"]["v"]["high"], "DUAL_AMBIGUOUS")
        self.assertEqual([e["type"] for e in obs.events], ["PIVOT_DUAL_AMBIGUOUS"])
        self.assertEqual(recs[4]["lvl"][0]["reason"], "NO_CONFIRMED_PIVOTS")

    def _structure(self, h1, h2, l1, l2):
        # Alternanza: high h1, low l1, high h2, low l2; base 50, picchi isolati.
        highs = [50, 50, h1, 50, 50, 50, 50, 50, 50, h2, 50, 50, 50, 50, 50, 50]
        lows = [40, 40, 40, 40, 40, l1, 40, 40, 40, 40, 40, 40, l2, 40, 40, 40]
        _, recs = run(hl_bars(highs, lows))
        return recs[-1]["piv"]["structure"]

    def test_structure_states(self):
        self.assertEqual(self._structure(60, 62, 30, 32)["v"], "UP")
        self.assertEqual(self._structure(62, 60, 32, 30)["v"], "DOWN")
        self.assertEqual(self._structure(60, 62, 32, 30)["v"], "MIXED")
        self.assertEqual(self._structure(60, 60, 30, 32)["v"], "MIXED")  # parità = misto

    def test_structure_needs_two_of_each(self):
        highs = [50, 50, 60, 50, 50, 50, 50, 50, 50, 62, 50, 50]
        lows = [40] * 5 + [30] + [40] * 6
        _, recs = run(hl_bars(highs, lows))
        self.assertEqual(recs[-1]["piv"]["structure"], {"v": None, "r": "NO_CONFIRMED_PIVOTS"})


class Fibonacci(unittest.TestCase):
    def test_versions_keep_replace_append(self):
        highs = [50, 50, 60, 50, 50, 50, 58, 50, 50, 50, 65, 50, 50, 50, 50, 50, 50]
        lows = [40] * 13 + [30] + [40] * 3
        obs, recs = run(hl_bars(highs, lows))
        fib = [e for e in obs.events if e["type"] == "FIB_SEQUENCE"]
        self.assertEqual([(e["action"], e["version"]) for e in fib], [("APPEND", 1), ("KEEP", 1), ("REPLACE", 2), ("APPEND", 3)])
        self.assertEqual(fib[2]["before"]["price"], 60)
        self.assertEqual(fib[2]["after"]["price"], 65)
        anchors = recs[-1]["fib"]["anchors"]["v"]
        self.assertEqual((anchors["P0"]["price"], anchors["P1"]["price"]), (65, 30))
        # Uno snapshot precedente alla sostituzione conserva la vecchia versione.
        self.assertEqual(recs[9]["fib"]["version"], 1)

    def _anchored(self, p0, p1):
        obs = ScaleObserver("45m", CONV)
        obs.fib_seq = [
            {"kind": "LOW" if p0 < p1 else "HIGH", "price": p0, "candidateOpen": 0, "eventTime": 0, "availableAt": 0},
            {"kind": "HIGH" if p0 < p1 else "LOW", "price": p1, "candidateOpen": 1, "eventTime": 1, "availableAt": 1},
        ]
        return obs._fibonacci(110.0, {"v": 2.0, "r": None})

    def test_reference_prices_up_and_down_leg(self):
        up = self._anchored(100, 120)
        self.assertAlmostEqual(up["retracements"][0]["price"], 112.36, places=9)
        self.assertAlmostEqual(up["projections"][0]["price"], 125.44, places=9)
        self.assertEqual(up["retracements"][1]["price"], 110.0)
        self.assertAlmostEqual(up["u"], 0.5)
        down = self._anchored(120, 100)
        self.assertAlmostEqual(down["retracements"][0]["price"], 107.64, places=9)
        self.assertAlmostEqual(down["projections"][0]["price"], 94.56, places=9)
        self.assertAlmostEqual(down["r"], 0.5)

    def test_equal_anchors(self):
        self.assertEqual(self._anchored(100, 100)["anchors"]["r"], "ANCHORS_EQUAL")


class GapsAndLevels(unittest.TestCase):
    def test_incomplete_bar_resets_segment_and_keeps_history(self):
        bars = linear_bars(30)
        gap = Bar(bars[-1].end, bars[-1].end + CONV.bar_ms, INCOMPLETE, 44, 1, 0)
        after = [bar(31 + k, 200, 201, 199, 200) for k in range(3)]
        obs, recs = run(bars + [gap] + after)
        self.assertEqual(recs[30]["vol"]["A"], {"v": None, "r": "INCOMPLETE_INPUT"})
        self.assertEqual(recs[31]["vol"]["tr"]["r"], "INSUFFICIENT_HISTORY")  # nessun ponte sul gap
        self.assertEqual(recs[31]["segment"], {"id": 2, "bars": 1})
        self.assertEqual(recs[29]["vol"]["A"]["v"], 2)  # record precedente invariato
        self.assertEqual([e["type"] for e in obs.events], ["SEGMENT_RESET"])

    def test_crossing_only_against_previous_snapshot_level(self):
        # Pivot high 15 confermato alla barra 4; poi la chiusura lo supera.
        highs = [10, 11, 15, 12, 11, 16, 16]
        lows = [5, 6, 7, 6, 5, 14, 14]
        bars = hl_bars(highs, lows)
        bars[5] = bar(5, 14, 16, 14, 16)
        bars[6] = bar(6, 16, 16, 15.5, 15)  # ritorno esattamente sul livello: non è un nuovo attraversamento
        obs, recs = run(bars)
        crosses = [e for e in obs.events if e["type"] == "LEVEL_CROSS"]
        self.assertEqual([(e["levelKind"], e["direction"], e["price"]) for e in crosses], [("PIVOT_HIGH", "UP", 15)])
        self.assertEqual(recs[4]["crossings"], [])  # pubblicazione del livello: nessun falso attraversamento

    def test_previous_day_levels(self):
        day = Bar(CONV.input_start, CONV.input_start + CONV.day_ms, "COMPLETE", 1440, 0, 0, o=1, h=9, l=2, c=5, v=1, q=1, trades=1, tb=0, tq=0)
        obs = ScaleObserver("45m", CONV)
        rec = obs.step(bar(32, 5, 6, 4, 5), day)
        kinds = {lv["kind"]: lv for lv in rec["lvl"]}
        self.assertEqual((kinds["DAY_HIGH"]["price"], kinds["DAY_LOW"]["price"]), (9, 2))
        self.assertEqual(kinds["DAY_HIGH"]["availableAt"], day.end)
        self.assertEqual(kinds["DAY_HIGH"]["dist"]["r"], "INSUFFICIENT_HISTORY")  # livello visibile anche senza A
        missing = ScaleObserver("45m", CONV).step(bar(0, 5, 6, 4, 5), None)
        self.assertEqual({lv["kind"]: lv.get("reason") for lv in missing["lvl"]}["DAY_LOW"], "INSUFFICIENT_HISTORY")


if __name__ == "__main__":
    unittest.main()
