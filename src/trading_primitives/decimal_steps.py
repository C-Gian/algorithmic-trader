"""Exact multiples of a caller-provided step, extracted from measures.py.

No tick/lot size, side-dependent policy, risk budget, fees or limits are chosen
here. This is mathematical rounding, NOT validation of exchange order rules.
Inputs must be finite Decimals; floats are rejected. Integers/rational arithmetic
avoid silently crossing a step when the ambient Decimal precision is small.
The caller decides whether floor or ceil is appropriate for the intended action.
"""

from decimal import Decimal


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be Decimal, not a float or coerced value")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")


def _multiple(value: Decimal, step: Decimal, *, ceiling: bool) -> Decimal:
    _finite(value, "value")
    _finite(step, "step")
    if step <= 0:
        raise ValueError("step must be positive")
    vn, vd = value.as_integer_ratio()
    sn, sd = step.as_integer_ratio()
    numerator, denominator = vn * sd, vd * sn
    units = -((-numerator) // denominator) if ceiling else numerator // denominator
    parts = step.as_tuple()
    coefficient = 0
    for digit in parts.digits:
        coefficient = coefficient * 10 + digit
    product = units * coefficient
    # Decimal(tuple) is exact and ignores the ambient arithmetic precision.
    digits = Decimal(abs(product)).as_tuple().digits
    return Decimal((int(product < 0), digits, parts.exponent))


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Greatest multiple of step <= value (also for negative values)."""
    return _multiple(value, step, ceiling=False)


def ceil_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Least multiple of step >= value (also for negative values)."""
    return _multiple(value, step, ceiling=True)
