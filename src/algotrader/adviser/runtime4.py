"""v0.4 runtime state codec (``algotrader.adviser-runtime.v4``): the v0.3 runtime frontier/clock codec around the MP-003
core (``algotrader.adviser-state.v4``) and the unchanged v0.3 evaluator. A v0.2/v0.3 runtime document never decodes
here and vice versa (no silent cross-method continuation)."""

from __future__ import annotations

from .core4 import STATE_FORMAT as CORE_FORMAT, AdviserCoreV4
from .runtime3 import AdviserRuntimeV3

RUNTIME_FORMAT = "algotrader.adviser-runtime.v4"


class AdviserRuntimeV4(AdviserRuntimeV3):
    RUNTIME_FMT, CORE_FMT, CORE_CLS = RUNTIME_FORMAT, CORE_FORMAT, AdviserCoreV4
