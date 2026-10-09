"""Adviser pins inside an observation-replay engine document and the explicit, checksummed runtime state codec used by
checkpoints, restore points and the professional finish.

The engine document pins ONE packaged method release (``methods``): v0.2 (MP-001, engine ``observe.stream.v3``,
runtime ``algotrader.adviser-runtime.v2``), v0.3 (MP-002, engine ``observe.stream.v4``, runtime
``algotrader.adviser-runtime.v3``), v0.4 (MP-003, engine ``observe.stream.v5``, runtime
``algotrader.adviser-runtime.v4``), v0.5 (MP-004, engine ``observe.stream.v6``, runtime
``algotrader.adviser-runtime.v5``) or v0.6 (MP-005, engine ``observe.stream.v7``, runtime
``algotrader.adviser-runtime.v6``). An absent ``method`` key is v0.2 (every WP-009 run). A run never continues under
another release; existing ``observe.stream.v1/v2`` runs keep their engines, validators and claims unchanged.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..feed.contracts import Family
from ..feed.ordering import canonical
from ..temporal.contracts import ClockPolicy
from . import contracts as sc
from . import methods
from .core import AdviserConfig, AdviserCore
from .evaluator import Evaluator
from .harness import mp001_dependencies
from .identity import (
    IMPLEMENTATION_ID,
    MODEL_ID,
    RULES_VERSION,
    CapabilityProfile,
    composite_identity,
    historical_profile,
    register_sha256,
    rules_sha256,
)
from .params import load
from .runtime import RUNTIME_FORMAT, AdviserRuntime

ENGINE_FORMAT_V3 = "observe.stream.v3"  # factual + temporal + algotrader.adviser-runtime.v2 (v0.2)
ENGINE_FORMAT_V4 = "observe.stream.v4"  # factual + temporal + algotrader.adviser-runtime.v3 (MP-002 v0.3)
ENGINE_FORMAT_V5 = "observe.stream.v5"  # factual + temporal + algotrader.adviser-runtime.v4 (MP-003 v0.4)
ENGINE_FORMAT_V6 = "observe.stream.v6"  # factual + temporal + algotrader.adviser-runtime.v5 (MP-004 v0.5)
ENGINE_FORMAT_V7 = "observe.stream.v7"  # factual + temporal + algotrader.adviser-runtime.v6 (MP-005 v0.6)


class AdviserStateError(Exception):
    """An adviser restore state is missing, incompatible or corrupt."""


def channel_ids(feed_manifest) -> dict[str, str]:
    out = {}
    for c in feed_manifest.coverage:
        fam = c.channel.family
        key = {Family.TRADE_BAR_1M: "trade", Family.MARK_BAR_1M: "mark", Family.INDEX_BAR_1M: "index",
               Family.FUNDING_SETTLEMENT: "funding"}[fam]
        out[key] = c.channel.channel_id
    return dict(sorted(out.items()))


def engine_config(feed_manifest, pack: dict, build: str | None, method: str | None = None) -> dict[str, Any]:
    """Pinned adviser configuration of a new pack adviser evaluation (method release, identity, profile, windows,
    tick, channels). ``method`` absent = the existing v0.2 default."""
    rel = methods.get(method)
    chans = channel_ids(feed_manifest)
    caps = {x["capability"]: x["status"] for x in pack.get("capabilities", [])}
    funding_covered = caps.get("funding_settlements") in ("AUTHORITATIVE_COMPLETE",)
    profile = historical_profile(dislocation="mark" in chans and "index" in chans, funding_covered=funding_covered)
    w = pack["windows"]
    tick = str(Decimal(pack["instrument"]["definition"]["tick_sz"]))
    pins = {"pack_id": pack["pack_id"], "instrument": feed_manifest.inst_id,
            "feed_content_identity": feed_manifest.content_identity,
            "availability_policy_id": feed_manifest.availability_policy.policy_id,
            "clock_policy": ClockPolicy.MODELED_COMPLETE_PREFIX.value, "tick": tick, "channels": chans,
            "evaluation": [w["evaluation"]["start"], w["evaluation"]["end"]], "clock_end": str(pack["clock_end"])}
    ident = rel.composite_identity(profile, pins, build)
    ev = _evaluator_cls(rel)(rel.params(), Decimal(tick), eval_start=None, eval_end=None,
                             funding_mode=profile.funding_outcomes.value)
    out = {"format": rel.runtime_format, "method": rel.key, "engine_format": rel.engine_format,
           "identity": ident, "profile": profile.model_dump(mode="json"), "tick": tick,
           "channels": chans, "eval_start": w["evaluation"]["start"], "eval_end": w["evaluation"]["end"],
           "warmup_start": w["warmup"]["start"], "tail_end": w["tail"]["end"], "clock_end": str(pack["clock_end"]),
           "clock_policy": ClockPolicy.MODELED_COMPLETE_PREFIX.value, "evaluator": ev.identity(),
           "origin": sc.Origin.HISTORICAL_MODELED.value, "build": build,
           "funding_completeness": caps.get("funding_settlements"),
           "labels": ["ADVISER_EVALUATION", "HYPOTHETICAL_OUTCOMES_SEPARATE", "NO_ORDERS_NO_SIZING"]}
    init = initialization_pin(pack)
    if init is not None:  # WP-013 explicit initialization only; earlier engine documents are unchanged
        out["initialization"] = init
    return out


def initialization_pin(pack: dict) -> dict[str, Any] | None:
    """Launch-time facts of a registered explicit initialization (WP-013): window, preset identity and the pack's own
    initialization coverage rows. Context only: the method, its parameters and the kernel are unchanged, and the
    single WARMUP->EVALUATION transition stays at the evaluation start (no monthly reset)."""
    preset = pack.get("preset") or {}
    if not preset.get("initialization"):
        return None
    w = pack["windows"]
    start, end = _dt(w["warmup"]["start"]), _dt(w["warmup"]["end"])
    return {"policy": preset["initialization"], "preset_id": preset.get("preset_id"),
            "preset_sha256": pack.get("preset_sha256"), "start": w["warmup"]["start"], "end": w["warmup"]["end"],
            "hours": int((end - start).total_seconds() // 3600), "evaluated": False,
            "coverage": [c for c in pack.get("coverage", []) if c.get("window") == "warmup"],
            "continuity": "ONE_RUN_ONE_EVALUATION_START_TRANSITION_NO_MONTHLY_RESET_OR_FINISH"}


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def release(engine: dict[str, Any]) -> methods.Release:
    """The packaged release pinned by this engine document; an unknown method fails explicitly."""
    try:
        return methods.for_engine(engine["adviser"])
    except methods.UnknownMethod as exc:
        raise AdviserStateError(str(exc)) from None


def _evaluator_cls(rel: methods.Release):
    if rel.key == "v0.2":
        return Evaluator
    from .evaluator3 import EvaluatorV3

    return EvaluatorV3


def config_from_engine(engine: dict[str, Any]) -> AdviserConfig:
    adv = engine["adviser"]
    rel = release(engine)
    profile = CapabilityProfile.model_validate(adv["profile"])
    ident = adv["identity"]
    if (ident["rules_sha256"] != rel.rules_sha256() or ident["register_sha256"] != rel.register_sha256()
            or ident["implementation"] != rel.implementation or ident["model"] != rel.model
            or ident["rules_version"] != rel.rules_version or adv["format"] != rel.runtime_format):
        raise AdviserStateError("the packaged method release differs from the identity pinned at preparation; the "
                                "run cannot continue under a different method")
    if rel.key == "v0.2":  # exact WP-009 construction
        method = sc.MethodRef(model=MODEL_ID, rules_version=RULES_VERSION, rules_sha256=rules_sha256(),
                              register_sha256=register_sha256(), profile_sha256=profile.sha256(),
                              implementation=IMPLEMENTATION_ID, build=adv.get("build"))
        params = load()
    else:
        method, params = rel.method_ref(profile, adv.get("build")), rel.params()
    return AdviserConfig(instrument=ident["pins"]["instrument"], tick=Decimal(adv["tick"]),
                         profile=profile, method=method, clock_policy=adv["clock_policy"], params=params,
                         eval_start=_dt(adv["eval_start"]), eval_end=_dt(adv["eval_end"]), origin=adv["origin"],
                         channel_ids={k: v for k, v in adv["channels"].items() if k in ("trade", "mark", "index")})


def new_evaluator(engine: dict[str, Any]) -> Evaluator:
    adv = engine["adviser"]
    rel = release(engine)
    ev = _evaluator_cls(rel)(rel.params(), Decimal(adv["tick"]), eval_start=_dt(adv["eval_start"]),
                             eval_end=_dt(adv["eval_end"]), funding_mode=adv["profile"]["funding_outcomes"])
    if ev.identity()["sha256"] != adv["evaluator"]["sha256"]:
        raise AdviserStateError("evaluator profile identity differs from the one pinned at preparation")
    return ev


def _runtime_cls(rel: methods.Release):
    if rel.key == "v0.2":
        return AdviserRuntime, AdviserCore
    if rel.key == "v0.4":
        from .runtime4 import AdviserRuntimeV4

        return AdviserRuntimeV4, AdviserRuntimeV4.CORE_CLS
    if rel.key == "v0.5":
        from .runtime5 import AdviserRuntimeV5

        return AdviserRuntimeV5, AdviserRuntimeV5.CORE_CLS
    if rel.key == "v0.6":
        from .runtime6 import AdviserRuntimeV6

        return AdviserRuntimeV6, AdviserRuntimeV6.CORE_CLS
    from .core3 import AdviserCoreV3
    from .runtime3 import AdviserRuntimeV3

    return AdviserRuntimeV3, AdviserCoreV3


def new_runtime(engine: dict[str, Any]) -> AdviserRuntime:
    rt_cls, core_cls = _runtime_cls(release(engine))
    return rt_cls(core_cls(config_from_engine(engine)), new_evaluator(engine))


def pack_runtime(rt: AdviserRuntime) -> tuple[bytes, str]:
    raw = canonical(rt.encode())
    return zlib.compress(raw, 6), hashlib.sha256(raw).hexdigest()


def unpack_runtime(blob: bytes, sha256: str, engine: dict[str, Any]) -> AdviserRuntime:
    try:
        raw = zlib.decompress(blob)
    except zlib.error as exc:
        raise AdviserStateError(f"adviser state not decompressible: {exc}") from None
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise AdviserStateError("adviser state SHA-256 mismatch (corrupt)")
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise AdviserStateError(f"adviser state JSON unreadable: {exc}") from None
    try:
        rt = _runtime_cls(release(engine))[0].decode(doc, config_from_engine(engine), new_evaluator(engine))
    except (KeyError, ValueError, TypeError) as exc:
        raise AdviserStateError(f"adviser state does not decode: {exc}") from None
    if canonical(rt.encode()) != raw:
        raise AdviserStateError("adviser state does not round-trip exactly")
    return rt
