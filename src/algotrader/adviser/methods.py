"""Explicit adviser method selection (WP-011): the fixed MP-001 v0.2 baseline and the closed MP-002 v0.3 revision.

A small dispatch table, not a trading DSL. Each release names its immutable packaged rules document and complete
parameter register (byte-identical copies of the Director documents in ``delivery/``) and every implementation,
state, runtime, report and validator identity its runs pin. The v0.2 entries are exactly the identities of the
accepted WP-009 product (commit 6f95273): its reducer, evaluator, state formats and readers are unchanged and are
never handed v0.3 scenarios or clocks.

Behaviour identity = rules_version + LF-normalized rules-document SHA-256 + register canonical SHA-256 + capability
profile SHA-256 + input/clock/config pins + implementation + build (MP-001 §12). Stored results always show their
pinned release, never the current default.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..feed.ordering import canonical
from . import contracts as sc
from . import identity as idn
from .params import Params, load, load_register

DEFAULT = "v0.2"  # absent selection continues the existing default (WP-011 §2)


@dataclass(frozen=True)
class Release:
    key: str
    label: str
    purpose: str
    status: str
    model: str
    rules_version: str
    rules_file: Path
    register_file: Path
    implementation: str
    evaluator_implementation: str
    core_state_format: str
    runtime_format: str
    evaluator_state_format: str
    engine_format: str
    report_version: str
    reconciliation_version: str
    deep_version: str

    # -- immutable method documents --------------------------------------------------------------------------------

    def rules_sha256(self) -> str:
        if self.key == "v0.2":
            return idn.rules_sha256()
        return _sha_lf(self.rules_file)

    def register(self) -> dict[str, Any]:
        if self.key == "v0.2":
            return idn.register()
        return _register(self.register_file, self.model, self.rules_version)

    def register_sha256(self) -> str:
        if self.key == "v0.2":
            return idn.register_sha256()
        return hashlib.sha256(canonical(self.register())).hexdigest()

    def params(self) -> Params:
        return load() if self.key == "v0.2" else load_register(self.register_file)

    # -- identities --------------------------------------------------------------------------------------------------

    def method_ref(self, profile: idn.CapabilityProfile, build: str | None) -> sc.MethodRef:
        return sc.MethodRef(model=self.model, rules_version=self.rules_version, rules_sha256=self.rules_sha256(),
                            register_sha256=self.register_sha256(), profile_sha256=profile.sha256(),
                            implementation=self.implementation, build=build)

    def composite_identity(self, profile: idn.CapabilityProfile, pins: dict[str, Any], build: str | None) -> dict:
        if self.key == "v0.2":
            return idn.composite_identity(profile, pins, build)  # unchanged WP-009 identity body
        body = {
            "model": self.model, "rules_version": self.rules_version, "rules_sha256": self.rules_sha256(),
            "register_sha256": self.register_sha256(), "implementation": self.implementation,
            "capability_profile": profile.model_dump(mode="json"), "capability_profile_sha256": profile.sha256(),
            "pins": pins, "build": build,
        }
        return {**body, "identity_sha256": hashlib.sha256(canonical(body)).hexdigest()}

    def summary(self) -> dict[str, Any]:
        return {"method": self.key, "label": self.label, "purpose": self.purpose, "status": self.status,
                "model": self.model, "rules_version": self.rules_version, "rules_sha256": self.rules_sha256(),
                "register_sha256": self.register_sha256(), "implementation": self.implementation,
                "evaluator_implementation": self.evaluator_implementation, "engine_format": self.engine_format,
                "report_version": self.report_version}


def _sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@lru_cache(maxsize=4)
def _register(path: Path, model: str, rules_version: str) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("model") != model or doc.get("rules_version") != rules_version:
        raise RuntimeError(f"packaged register is {doc.get('model')}/{doc.get('rules_version')}, expected "
                           f"{model}/{rules_version}")
    return doc


V02 = Release(
    key="v0.2", label="Original v0.2", status="ACCEPTED_BASELINE",
    purpose="The accepted MP-001 adviser exactly as evaluated so far (fixed comparison baseline).",
    model=idn.MODEL_ID, rules_version=idn.RULES_VERSION, rules_file=idn.RULES_FILE, register_file=idn.REGISTER_FILE,
    implementation=idn.IMPLEMENTATION_ID, evaluator_implementation="adviser.evaluator.v2",
    core_state_format="algotrader.adviser-state.v2", runtime_format="algotrader.adviser-runtime.v2",
    evaluator_state_format="algotrader.adviser-evaluation-state.v1", engine_format="observe.stream.v3",
    report_version="adviser.report.v2", reconciliation_version="5", deep_version="6")

V03 = Release(
    key="v0.3", label="Revised v0.3 — confirmation then usable entry",
    status="ENGINEERING_REVIEW_PENDING",
    purpose=("MP-002: scenarios persist independently of entry; after an A confirmation the adviser may wait for a "
             "later usable price inside the reaction corridor instead of rejecting at once."),
    model="btc.context-action.v0.3", rules_version="mp002.rules.v0.3",
    rules_file=idn.METHOD_DIR / "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md",
    register_file=idn.METHOD_DIR / "MP-002-PARAMETERS.json",
    implementation="adviser.core.v3", evaluator_implementation="adviser.evaluator.v3",
    core_state_format="algotrader.adviser-state.v3", runtime_format="algotrader.adviser-runtime.v3",
    evaluator_state_format="algotrader.adviser-evaluation-state.v2", engine_format="observe.stream.v4",
    report_version="adviser.report.v3", reconciliation_version="6", deep_version="7")

RELEASES: dict[str, Release] = {r.key: r for r in (V02, V03)}
BY_MODEL: dict[str, Release] = {r.model: r for r in RELEASES.values()}


class UnknownMethod(ValueError):
    """A requested or pinned method is not a packaged release."""


def get(key: str | None) -> Release:
    k = key or DEFAULT
    if k not in RELEASES:
        raise UnknownMethod(f"unknown adviser method {k!r} (available: {', '.join(RELEASES)})")
    return RELEASES[k]


def for_model(model: str) -> Release:
    if model not in BY_MODEL:
        raise UnknownMethod(f"no packaged release for model {model!r}")
    return BY_MODEL[model]


def for_engine(adviser: dict[str, Any]) -> Release:
    """Release pinned by an engine/state document (absent ``method`` = v0.2: every WP-009 run)."""
    return get(adviser.get("method") or "v0.2")


def selectable() -> list[dict[str, Any]]:
    return [r.summary() for r in RELEASES.values()]
