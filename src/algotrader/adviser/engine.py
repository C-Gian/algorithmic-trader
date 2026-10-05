"""Adviser pins inside an observation-replay engine document (engine ``observe.stream.v3``) and the explicit,
checksummed runtime state codec used by checkpoints, restore points and the professional finish.

Only NEW adviser evaluation launches use ``observe.stream.v3``; existing ``observe.stream.v1/v2`` runs keep their
engines, validators and claims unchanged.
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

ENGINE_FORMAT_V3 = "observe.stream.v3"  # factual + temporal + algotrader.adviser-runtime.v2


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


def engine_config(feed_manifest, pack: dict, build: str | None) -> dict[str, Any]:
    """Pinned adviser configuration of a new pack adviser evaluation (identity, profile, windows, tick, channels)."""
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
    ident = composite_identity(profile, pins, build)
    ev = Evaluator(load(), Decimal(tick), eval_start=None, eval_end=None, funding_mode=profile.funding_outcomes.value)
    return {"format": RUNTIME_FORMAT, "identity": ident, "profile": profile.model_dump(mode="json"), "tick": tick,
            "channels": chans, "eval_start": w["evaluation"]["start"], "eval_end": w["evaluation"]["end"],
            "warmup_start": w["warmup"]["start"], "tail_end": w["tail"]["end"], "clock_end": str(pack["clock_end"]),
            "clock_policy": ClockPolicy.MODELED_COMPLETE_PREFIX.value, "evaluator": ev.identity(),
            "origin": sc.Origin.HISTORICAL_MODELED.value, "build": build,
            "funding_completeness": caps.get("funding_settlements"),
            "labels": ["ADVISER_EVALUATION", "HYPOTHETICAL_OUTCOMES_SEPARATE", "NO_ORDERS_NO_SIZING"]}


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def config_from_engine(engine: dict[str, Any]) -> AdviserConfig:
    adv = engine["adviser"]
    profile = CapabilityProfile.model_validate(adv["profile"])
    ident = adv["identity"]
    if ident["rules_sha256"] != rules_sha256() or ident["register_sha256"] != register_sha256() \
            or ident["implementation"] != IMPLEMENTATION_ID or ident["model"] != MODEL_ID \
            or ident["rules_version"] != RULES_VERSION:
        raise AdviserStateError("the packaged method release differs from the identity pinned at preparation; the "
                                "run cannot continue under a different method")
    method = sc.MethodRef(model=MODEL_ID, rules_version=RULES_VERSION, rules_sha256=rules_sha256(),
                          register_sha256=register_sha256(), profile_sha256=profile.sha256(),
                          implementation=IMPLEMENTATION_ID, build=adv.get("build"))
    return AdviserConfig(instrument=ident["pins"]["instrument"], tick=Decimal(adv["tick"]),
                         profile=profile, method=method, clock_policy=adv["clock_policy"], params=load(),
                         eval_start=_dt(adv["eval_start"]), eval_end=_dt(adv["eval_end"]), origin=adv["origin"],
                         channel_ids={k: v for k, v in adv["channels"].items() if k in ("trade", "mark", "index")})


def new_evaluator(engine: dict[str, Any]) -> Evaluator:
    adv = engine["adviser"]
    ev = Evaluator(load(), Decimal(adv["tick"]), eval_start=_dt(adv["eval_start"]), eval_end=_dt(adv["eval_end"]),
                   funding_mode=adv["profile"]["funding_outcomes"])
    if ev.identity()["sha256"] != adv["evaluator"]["sha256"]:
        raise AdviserStateError("evaluator profile identity differs from the one pinned at preparation")
    return ev


def new_runtime(engine: dict[str, Any]) -> AdviserRuntime:
    return AdviserRuntime(AdviserCore(config_from_engine(engine)), new_evaluator(engine))


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
        rt = AdviserRuntime.decode(doc, config_from_engine(engine), new_evaluator(engine))
    except (KeyError, ValueError, TypeError) as exc:
        raise AdviserStateError(f"adviser state does not decode: {exc}") from None
    if canonical(rt.encode()) != raw:
        raise AdviserStateError("adviser state does not round-trip exactly")
    return rt
