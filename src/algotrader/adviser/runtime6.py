"""v0.6 runtime state codec (``algotrader.adviser-runtime.v6``): the v0.3 runtime frontier/clock codec around the MP-005
core (``algotrader.adviser-state.v6``: v0.5 state plus the scenario's ended-entry presentation record) and the
unchanged v0.3 evaluator. A v0.2-v0.5 runtime document never decodes here and vice versa (no silent cross-method
continuation)."""

from __future__ import annotations

from .core6 import STATE_FORMAT as CORE_FORMAT, AdviserCoreV6
from .runtime3 import AdviserRuntimeV3

RUNTIME_FORMAT = "algotrader.adviser-runtime.v6"


class AdviserRuntimeV6(AdviserRuntimeV3):
    RUNTIME_FMT, CORE_FMT, CORE_CLS = RUNTIME_FORMAT, CORE_FORMAT, AdviserCoreV6
