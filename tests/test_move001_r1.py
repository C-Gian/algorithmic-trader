"""MOVE-001/R1-B: l'ultima chiusura disponibile è selezionabile nel pacchetto di consultazione.

Regressione scritta prima della correzione: sulla consegna 1235e64 le origini finivano una barra prima
della fine copertura, quindi OPEN_AT_END non era raggiungibile. Nessun dato oltre la fine: le barre del
pacchetto coprono esattamente [inputStart, end).
"""

import unittest

from move001.fixture import build

BAR = 45 * 60_000


class FinalClose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = build(final=True)

    def test_open_at_end_reachable_without_data_beyond_end(self):
        p, c = self.pkg, self.pkg["case"]
        end_event = [e for e in c["ledger"] if e["type"] == "OPEN_AT_END"]
        self.assertEqual(len(end_event), 1)
        self.assertEqual(end_event[0]["t"], p["periods"]["end"])
        self.assertEqual(p["origins"][-1], p["periods"]["end"])  # ultima chiusura selezionabile
        bars = p["bars"]["45m"]["open"]
        self.assertEqual(bars[-1] + BAR, p["periods"]["end"])  # ultima barra completa termina alla fine, nessuna barra oltre
        self.assertEqual(len(bars) * BAR, p["periods"]["end"] - p["periods"]["inputStart"])
        self.assertEqual(p["observations"]["45m"][-1]["end"], p["periods"]["end"])

    def test_package_declares_consultation_version(self):
        self.assertEqual(self.pkg["consultVersion"], "move001.consult/2")

    def test_earlier_reference_origins_unchanged(self):
        p = build()
        last_fact = max(e["t"] for e in p["case"]["ledger"])
        self.assertEqual(p["origins"][-1], min(last_fact + 8 * BAR, p["periods"]["end"]))
        self.assertLess(p["origins"][-1], p["periods"]["end"])


if __name__ == "__main__":
    unittest.main()
