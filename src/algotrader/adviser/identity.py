"""Immutable method release identity (MP-001 v0.2) and capability profiles.

The packaged ``method/MP-001-INTEGRATED-METHOD-PROPOSAL.md`` (normative rules prose) and
``method/MP-001-PARAMETERS.json`` (numerical/categorical register) are byte-identical copies of the Director
documents in ``delivery/`` (pinned by regression tests). Behaviour identity is

    rules_version + rules-document SHA-256 + register canonical SHA-256 + capability-profile SHA-256
    + input/clock/config pins + code build

so a prose change produces a different identity even when the JSON register is unchanged (MP-001 §12, B8).
The rules hash is taken over the LF-normalized bytes (the Git-canonical content), so a Windows CRLF checkout and a
Linux checkout of the same commit have the same identity.

Capability profiles name the evidence the run actually has. Different profiles have different hashes and never
claim call identity with each other (LIVE_QUOTED vs HISTORICAL_BASE).
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..feed.ordering import canonical

METHOD_DIR = Path(__file__).with_name("method")
RULES_FILE = METHOD_DIR / "MP-001-INTEGRATED-METHOD-PROPOSAL.md"
REGISTER_FILE = METHOD_DIR / "MP-001-PARAMETERS.json"
MODEL_ID = "btc.context-action.v0.2"
RULES_VERSION = "mp001.rules.v0.2"
# Implementation identity of this translation of the rules into code (bumped with any behavioural code change).
IMPLEMENTATION_ID = "adviser.core.v2"  # v2: WP-009 correction (timers, C withdrawal, live connection adequacy)


def _lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


@lru_cache(maxsize=1)
def rules_sha256() -> str:
    return hashlib.sha256(_lf(RULES_FILE.read_bytes())).hexdigest()


@lru_cache(maxsize=1)
def register() -> dict[str, Any]:
    doc = json.loads(REGISTER_FILE.read_text(encoding="utf-8"))
    if doc.get("model") != MODEL_ID or doc.get("rules_version") != RULES_VERSION:
        raise RuntimeError(f"packaged register is {doc.get('model')}/{doc.get('rules_version')}, expected "
                           f"{MODEL_ID}/{RULES_VERSION}")
    return doc


@lru_cache(maxsize=1)
def register_sha256() -> str:
    return hashlib.sha256(canonical(register())).hexdigest()


class Execution(StrEnum):
    LIVE_QUOTED = "LIVE_QUOTED"
    HISTORICAL_BASE = "HISTORICAL_BASE"


class Calendar(StrEnum):
    STRICT_AS_KNOWN_ALLOW_UNKNOWN = "STRICT_AS_KNOWN_ALLOW_UNKNOWN"
    NONE_UNKNOWN = "NONE_UNKNOWN"
    RECONSTRUCTED_SECONDARY = "RECONSTRUCTED_SECONDARY"


class Dislocation(StrEnum):
    ENABLE_WHERE_SUPPORTED = "ENABLE_WHERE_SUPPORTED"
    NOT_COVERED = "NOT_COVERED"


class IncidentTape(StrEnum):
    TYPED_TAPE = "TYPED_TAPE"
    NOT_COVERED = "NOT_COVERED"


class FundingOutcomes(StrEnum):
    AUTHORITATIVE_IF_COVERED = "AUTHORITATIVE_IF_COVERED"
    PRICE_NET_ONLY = "PRICE_NET_ONLY"


class CapabilityProfile(BaseModel):
    """MP-001 §12 profile fields. Hashed canonically; part of every behaviour identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution: Execution
    calendar: Calendar
    dislocation: Dislocation
    incident_tape: IncidentTape
    funding_outcomes: FundingOutcomes
    horizon_inputs: str = "R2_COMPLETE_MINUTE_DERIVED_UTC_HORIZONS"
    late_policy: str = "temporal.seal-no-revision.v1"
    origin: str = "HISTORICAL_MODELED"  # HISTORICAL_MODELED | LIVE (live sessions also journal RECONSTRUCTED spans)

    def sha256(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json"))).hexdigest()


def historical_profile(dislocation: bool = True, funding_covered: bool = False) -> CapabilityProfile:
    """Primary Owner historical profile for a receipt-pinned pack (calendar/incidents not covered)."""
    return CapabilityProfile(
        execution=Execution.HISTORICAL_BASE, calendar=Calendar.NONE_UNKNOWN,
        dislocation=Dislocation.ENABLE_WHERE_SUPPORTED if dislocation else Dislocation.NOT_COVERED,
        incident_tape=IncidentTape.NOT_COVERED,
        funding_outcomes=FundingOutcomes.AUTHORITATIVE_IF_COVERED if funding_covered else FundingOutcomes.PRICE_NET_ONLY)


def live_profile() -> CapabilityProfile:
    return CapabilityProfile(execution=Execution.LIVE_QUOTED, calendar=Calendar.NONE_UNKNOWN,
                             dislocation=Dislocation.ENABLE_WHERE_SUPPORTED, incident_tape=IncidentTape.NOT_COVERED,
                             funding_outcomes=FundingOutcomes.PRICE_NET_ONLY, origin="LIVE")


def composite_identity(profile: CapabilityProfile, pins: dict[str, Any], build: str | None) -> dict[str, Any]:
    """Full behaviour identity of one adviser run/session (stable JSON + its SHA-256)."""
    body = {
        "model": MODEL_ID, "rules_version": RULES_VERSION, "rules_sha256": rules_sha256(),
        "register_sha256": register_sha256(), "implementation": IMPLEMENTATION_ID,
        "capability_profile": profile.model_dump(mode="json"), "capability_profile_sha256": profile.sha256(),
        "pins": pins, "build": build,
    }
    return {**body, "identity_sha256": hashlib.sha256(canonical(body)).hexdigest()}


def D(x: Any) -> Decimal:
    """Exact Decimal from a register number (never via binary float text)."""
    if isinstance(x, float):
        return Decimal(repr(x))
    return Decimal(str(x))
