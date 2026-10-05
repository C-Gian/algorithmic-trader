"""v0.3 runtime state codec (``algotrader.adviser-runtime.v3``): the unchanged professional clock/frontier of
``runtime.AdviserRuntime`` around the v0.3 core and evaluator. Only the pinned formats differ; a v0.2 runtime
document never decodes here and vice versa (no silent cross-method continuation)."""

from __future__ import annotations

from datetime import datetime

from ..feed.contracts import FeedEvent
from .core import AdviserConfig, EventInput, Quote
from .core3 import STATE_FORMAT as CORE_FORMAT, AdviserCoreV3
from .evaluator3 import EvaluatorV3
from .runtime import AdviserRuntime

RUNTIME_FORMAT = "algotrader.adviser-runtime.v3"


class AdviserRuntimeV3(AdviserRuntime):
    def encode(self) -> dict:
        doc = super().encode()
        doc["format"], doc["core_format"] = RUNTIME_FORMAT, CORE_FORMAT
        return doc

    @classmethod
    def decode(cls, doc: dict, cfg: AdviserConfig, evaluator: EvaluatorV3 | None) -> AdviserRuntimeV3:
        if doc.get("format") != RUNTIME_FORMAT:
            raise ValueError(f"adviser runtime format {doc.get('format')!r} is not {RUNTIME_FORMAT}")
        core = AdviserCoreV3.decode(doc["core"], cfg)
        if (doc["evaluator"] is None) != (evaluator is None):
            raise ValueError("evaluator presence differs from the pinned configuration")
        if evaluator is not None:
            evaluator.restore(doc["evaluator"])
        rt = cls(core, evaluator)
        for t, order, kind, payload in doc["pending"]:
            tt = datetime.fromisoformat(t)
            if kind == "event":
                payload = (FeedEvent.model_validate(payload["event"]), payload["cursor"])
            elif kind == "quote":
                payload = Quote.decode(payload)
            elif kind == "capability":
                payload = EventInput.decode(payload)
            rt.pending.append((tt, order, kind, payload))
        rt._order, rt.dispatches, rt.finished = doc["order"], doc["dispatches"], doc["finished"]
        rt.admitted = doc["admitted"]
        return rt
