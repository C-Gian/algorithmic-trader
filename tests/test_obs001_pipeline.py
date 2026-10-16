"""OBS-001: parsing, aggregazione, causalità degli snapshot, esiti 24h e riepiloghi."""

import json
import unittest

from obs001.aggregate import aggregate
from obs001.conventions import DAY_MS, MINUTE_MS, canonical_json
from obs001.minutes import INVALID, MISSING, VALID, MinuteStore, SchemaError, parse_csv_text
from obs001.observe import observe, snapshot_at
from obs001.outcomes import outcome_for
from obs001.pipeline import run_chain
from obs001.summary import describe, quantile

from obs001_helpers import BAR, CONV, fill_random_walk, full_store

HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
T0 = CONV.input_start


def row(t, o=10, h=11, l=9, c=10, v=1, close=None, n=3):
    close = t + 59_999 if close is None else close
    return f"{t},{o},{h},{l},{c},{v},{close},{v * c},{n},0.5,5,0\n"


class Parsing(unittest.TestCase):
    def store(self):
        return MinuteStore(T0, T0 + DAY_MS)

    def test_header_and_first_numeric_row_kept(self):
        s = self.store()
        st = parse_csv_text(HEADER + row(T0) + row(T0 + MINUTE_MS), s, T0, T0 + DAY_MS, "x")
        self.assertTrue(st.header)
        self.assertEqual(s.counts()["valid"], 2)
        s2 = self.store()
        parse_csv_text(row(T0) + row(T0 + MINUTE_MS), s2, T0, T0 + DAY_MS, "x")
        self.assertEqual(s2.status[0], VALID)

    def test_duplicates_and_corruption(self):
        s = self.store()
        text = row(T0) + row(T0) + row(T0 + MINUTE_MS) + row(T0 + MINUTE_MS, c=10.5) + row(T0 + 2 * MINUTE_MS, h=8) + row(T0 + 3 * MINUTE_MS, close=T0)
        st = parse_csv_text(text, s, T0, T0 + DAY_MS, "x")
        self.assertEqual(st.duplicates_identical, 1)
        self.assertEqual(st.duplicates_discordant_minutes, 1)
        self.assertEqual(list(s.status[:5]), [VALID, INVALID, INVALID, MISSING, MISSING])
        self.assertEqual(st.corrupt_rows, 2)

    def test_microseconds_and_unknown_header_are_errors(self):
        with self.assertRaises(SchemaError):
            parse_csv_text(row(T0 * 1000, close=T0 * 1000 + 59_999_999), self.store(), T0, T0 + DAY_MS, "x")
        with self.assertRaises(SchemaError):
            parse_csv_text("a,b,c\n" + row(T0), self.store(), T0, T0 + DAY_MS, "x")

    def test_rows_outside_month_are_not_used(self):
        s = self.store()
        st = parse_csv_text(row(T0 + DAY_MS), MinuteStore(T0, T0 + 2 * DAY_MS), T0, T0 + DAY_MS, "x")
        self.assertEqual(st.outside_month, 1)
        self.assertEqual(s.counts()["valid"], 0)


class Aggregation(unittest.TestCase):
    def test_45_minutes_exact_and_utc_day(self):
        s = MinuteStore(T0, T0 + 2 * DAY_MS)
        fill_random_walk(s, T0, T0 + 2 * DAY_MS)
        s.status[s.index(T0 + BAR + 44 * MINUTE_MS)] = MISSING  # ultimo minuto della seconda barra
        b45 = aggregate(s, BAR)
        d = aggregate(s, DAY_MS)
        self.assertEqual(len(b45), 64)
        self.assertEqual(b45[0].valid, 45)
        self.assertEqual((b45[1].status, b45[1].valid, b45[1].missing), ("INCOMPLETE", 44, 1))
        self.assertIsNone(b45[1].c)
        self.assertEqual(b45[32].start, T0 + DAY_MS)  # la 33ª barra apre a mezzanotte UTC
        self.assertEqual(d[0].status, "INCOMPLETE")
        day2 = b45[32:64]
        self.assertEqual(d[1].h, max(b.h for b in day2))
        self.assertEqual(d[1].l, min(b.l for b in day2))
        self.assertEqual((d[1].o, d[1].c), (day2[0].o, day2[-1].c))


class Causality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Trenta giorni sintetici e due futuri diversi dopo il cutoff, uno con una lacuna.
        cls.end = T0 + 30 * DAY_MS
        cls.cutoff = T0 + 20 * DAY_MS  # mezzanotte
        base = MinuteStore(T0, cls.end)
        fill_random_walk(base, T0, cls.end, seed=11)
        other = base.truncated(cls.cutoff)
        fill_random_walk(other, cls.cutoff, cls.end, seed=99, price=base.c[base.index(cls.cutoff) - 1])
        other.status[other.index(cls.cutoff + 3 * BAR)] = MISSING
        cls.stores = {"base": base, "other": other, "prefix": base.truncated(cls.cutoff)}

    def snap(self, store, t):
        bars45, bars1d = aggregate(store, BAR), aggregate(store, DAY_MS)
        return canonical_json(snapshot_at(observe(bars45, bars1d, CONV), CONV, t))

    def test_same_prefix_identical_snapshots(self):
        for t in (self.cutoff, self.cutoff - BAR, self.cutoff - 5 * BAR, self.cutoff - DAY_MS + 7 * BAR):
            snaps = {k: self.snap(s, t) for k, s in self.stores.items()}
            self.assertEqual(snaps["base"], snaps["other"], t)
            self.assertEqual(snaps["base"], snaps["prefix"], t)

    def test_future_pivots_not_visible_before_availability(self):
        bars45, bars1d = aggregate(self.stores["base"], BAR), aggregate(self.stores["base"], DAY_MS)
        res = observe(bars45, bars1d, CONV)
        pivot = next(e for e in res["events"]["45m"] if e["type"] == "PIVOT_CONFIRMED" and e["eventTime"] > T0 + 10 * DAY_MS)
        between = pivot["eventTime"] + BAR  # candidata chiusa, conferma non ancora avvenuta
        self.assertLess(between, pivot["availableAt"])
        self.assertNotIn(pivot["pivotId"], json.dumps(snapshot_at(res, CONV, between)))
        self.assertIn(pivot["pivotId"], json.dumps(snapshot_at(res, CONV, pivot["availableAt"])))
        # Lo stesso snapshot intermedio si ottiene da un input che termina a quel cutoff.
        self.assertEqual(self.snap(self.stores["base"], between), self.snap(self.stores["base"].truncated(between), between))
        snap = snapshot_at(res, CONV, self.cutoff)
        self.assertEqual(snap["1D"]["end"], self.cutoff)  # a mezzanotte il giorno appena chiuso è incluso
        self.assertTrue(all(e["availableAt"] <= self.cutoff for e in snap["events"]["45m"]))


class Outcomes(unittest.TestCase):
    def test_prefixed_example_and_intraminute_extremes(self):
        t = CONV.study_start
        s = MinuteStore(T0, CONV.end)
        for k in range(1440):
            m = t + k * MINUTE_MS
            s.set_minute(s.index(m), (100, 101, 99, 100, 1, 0, 1, 0, 0))
        s.set_minute(s.index(t + 100 * MINUTE_MS), (100, 106, 99, 100, 1, 0, 1, 0, 0))
        s.set_minute(s.index(t + 700 * MINUTE_MS), (100, 101, 97, 100, 1, 0, 1, 0, 0))
        s.set_minute(s.index(t + 1439 * MINUTE_MS), (100, 102, 99, 102, 1, 0, 1, 0, 0))
        o = outcome_for(s, CONV, t, 100.0, 2.0, None)
        self.assertEqual((o["final"], o["up"], o["down"]), (1.0, 3.0, 1.5))
        self.assertEqual(o["futureStatus"], "COMPLETE")
        z = outcome_for(s, CONV, t, 100.0, 0.0, None)
        self.assertEqual((z["aStatus"], z["final"]), ("A_NOT_POSITIVE", None))

    def test_gap_and_right_censoring(self):
        t = CONV.end - 2 * BAR
        s = MinuteStore(T0, CONV.end)
        fill_random_walk(s, t, CONV.end)
        o = outcome_for(s, CONV, t, 100.0, 2.0, None)
        self.assertEqual(o["futureFlags"], ["RIGHT_CENSORED"])
        self.assertIsNone(o["final"])
        self.assertEqual(o["futureMinutesInRange"], 90)
        s.status[s.index(t + 10 * MINUTE_MS)] = MISSING
        o = outcome_for(s, CONV, t, 100.0, 2.0, None)
        self.assertEqual((o["futureFlags"], o["futureMinutesContiguous"]), (["RIGHT_CENSORED", "GAP"], 10))

    def test_last_2025_minute_closes_the_last_complete_horizon(self):
        t = CONV.end - DAY_MS
        s = MinuteStore(T0, CONV.end)
        fill_random_walk(s, t, CONV.end)
        o = outcome_for(s, CONV, t, 100.0, 2.0, None)
        self.assertEqual(o["futureStatus"], "COMPLETE")
        self.assertEqual(o["close24h"], s.c[s.n - 1])


class FullGrid(unittest.TestCase):
    """Griglia teorica intera su dati sintetici: popolazione, censure e partizioni."""

    @classmethod
    def setUpClass(cls):
        store = full_store(seed=3)
        store.status[store.index(CONV.study_start + 40 * DAY_MS + 5 * MINUTE_MS)] = MISSING
        cls.chain = run_chain(store, CONV)

    def test_population_and_censoring(self):
        rows = self.chain["rows"]
        self.assertEqual(len(rows), 3904)
        self.assertEqual(sum("RIGHT_CENSORED" in r["futureFlags"] for r in rows), 31)
        self.assertTrue(self.chain["summary"]["checks"]["partitionsReconciled"])
        gap_rows = [r for r in rows if "GAP" in r["futureFlags"]]
        self.assertGreater(len(gap_rows), 0)
        self.assertTrue(all(r["final"] is None for r in gap_rows))
        incomplete = [r for r in rows if r["originStatus"] != "VALID"]
        self.assertEqual(len(incomplete), 1)  # l'origine sulla barra con il minuto mancante resta nella popolazione

    def test_relation_only_for_directional_s45(self):
        for r in self.chain["rows"]:
            if r["s45"] in ("MIXED", "UNAVAILABLE"):
                self.assertEqual(r["dailyRelation"], "NOT_APPLICABLE")


class Quantiles(unittest.TestCase):
    def test_linear_interpolation(self):
        self.assertEqual(quantile([1, 2, 3, 4], 0.25), 1.75)
        self.assertEqual(quantile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(quantile([7], 0.9), 7)
        self.assertIsNone(quantile([], 0.5))
        d = describe([4, 1, 3, 2], [0.1, 0.9])
        self.assertEqual((d["mean"], d["min"], d["max"]), (2.5, 1, 4))
        self.assertAlmostEqual(d["p10"], 1.3)
        self.assertAlmostEqual(d["p90"], 3.7)


if __name__ == "__main__":
    unittest.main()
