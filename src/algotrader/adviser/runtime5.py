"""v0.5 runtime state codec (``algotrader.adviser-runtime.v5``): the v0.3 runtime frontier/clock codec around the MP-004
core (``algotrader.adviser-state.v5``: v0.4 state plus the A RETURN phase and its prepared local reference) and the
unchanged v0.3 evaluator. A v0.2/v0.3/v0.4 runtime document never decodes here and vice versa (no silent cross-method
continuation)."""

from __future__ import annotations

from .core5 import STATE_FORMAT as CORE_FORMAT, AdviserCoreV5
from .runtime3 import AdviserRuntimeV3

RUNTIME_FORMAT = "algotrader.adviser-runtime.v5"


class AdviserRuntimeV5(AdviserRuntimeV3):
    RUNTIME_FMT, CORE_FMT, CORE_CLS = RUNTIME_FORMAT, CORE_FORMAT, AdviserCoreV5
