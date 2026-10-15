import unittest
from decimal import Decimal, Inexact, Rounded, localcontext
from fractions import Fraction

from trading_primitives.decimal_steps import ceil_to_step, floor_to_step

D = Decimal


class DecimalStepTests(unittest.TestCase):
    def test_known_boundaries_non_decimal_power_step(self):
        for value, step, low, high in [
            ("100.12", "0.05", "100.10", "100.15"),
            ("100.10", "0.05", "100.10", "100.10"),
            ("0.000019", "0.00001", "0.00001", "0.00002"),
            ("-1.01", "0.1", "-1.1", "-1.0"),
            ("0", "0.05", "0", "0"),
            ("123", "1E+1", "120", "130"),
        ]:
            with self.subTest(value=value, step=step):
                self.assertEqual(floor_to_step(D(value), D(step)), D(low))
                self.assertEqual(ceil_to_step(D(value), D(step)), D(high))

    def test_low_decimal_precision_cannot_move_boundary(self):
        with localcontext() as ctx:
            ctx.prec = 3
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            self.assertEqual(floor_to_step(D("100000.00001"), D("0.0001")), D("100000.0000"))
            self.assertEqual(ceil_to_step(D("100000.00001"), D("0.0001")), D("100000.0001"))

    def test_invalid_input_never_coerced(self):
        for func in (floor_to_step, ceil_to_step):
            for value in (float("nan"), 1.25, "1.25", 1):
                with self.subTest(func=func.__name__, value=value), self.assertRaises(TypeError):
                    func(value, D("0.1"))
            for value in ("NaN", "Infinity", "-Infinity", "sNaN"):
                with self.subTest(func=func.__name__, value=value), self.assertRaises(ValueError):
                    func(D(value), D("0.1"))
            for step in ("0", "-0.1", "NaN", "Infinity"):
                with self.subTest(func=func.__name__, step=step), self.assertRaises(ValueError):
                    func(D("1"), D(step))
            with self.assertRaises(TypeError):
                func(D("1"), 0.1)

    def test_order_exact_multiple_and_idempotence_with_rational_oracle(self):
        for value in ("-12.4567", "0", "0.00000001", "12.4567", "100000000000000000.01"):
            for step in ("0.05", "0.0003", "2.5"):
                v, s = D(value), D(step)
                low, high = floor_to_step(v, s), ceil_to_step(v, s)
                vf, sf, lf, hf = map(Fraction, (v, s, low, high))
                self.assertLessEqual(lf, vf)
                self.assertLessEqual(vf, hf)
                self.assertEqual((lf/sf).denominator, 1)
                self.assertEqual((hf/sf).denominator, 1)
                self.assertLess(vf-lf, sf)
                self.assertLess(hf-vf, sf)
                self.assertEqual(floor_to_step(low, s), low)
                self.assertEqual(ceil_to_step(high, s), high)
