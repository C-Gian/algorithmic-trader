"""Explicit adviser method selection (WP-011/WP-012/WP-014): the fixed MP-001 v0.2 baseline, the accepted MP-002 v0.3
revision, the MP-003 v0.4 candidate (pre-confirmation A anchor epochs) and the MP-004 v0.5 candidate (A RETURN local
reference followed by a local recovery).

A small dispatch table, not a trading DSL. Each release names its immutable packaged rules document and complete
parameter register (byte-identical copies of the Director documents in ``delivery/``) and every implementation,
state, runtime, report and validator identity its runs pin. The v0.2 entries are exactly the identities of the
accepted WP-009 product (commit 6f95273): its reducer, evaluator, state formats and readers are unchanged and are
never handed v0.3 scenarios or clocks.

Behaviour identity = rules_version + LF-normalized rules-document SHA-256 + register canonical SHA-256 + capability
profile SHA-256 + input/clock/config pins + implementation + build (MP-001 §12). Stored results always show their
pinned release, never the current default.

A release that inherits other authoritative rule texts (v0.4: the MP-003 delta over MP-002 rules/disposition and the
MP-001 rules; v0.5: the MP-004 delta and its Director closure over the MP-003 disposition, the MP-002 rules/disposition
and the MP-001 rules) pins a rules MANIFEST: ``rules_sha256`` is the SHA-256 of the canonical list of every authoritative
document's role, file name and LF-normalized SHA-256, so a changed inherited text changes the behaviour identity even
though the delta file is unchanged (WP-012 §3). Single-document releases keep their existing single-file hash.
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
    inherited: tuple[tuple[str, Path], ...] = ()  # (role, file) authoritative inherited rule texts (rules manifest)
    status_label: str = ""

    # -- immutable method documents --------------------------------------------------------------------------------

    def rules_sha256(self) -> str:
        if self.key == "v0.2":
            return idn.rules_sha256()
        if not self.inherited:
            return _sha_lf(self.rules_file)
        return hashlib.sha256(canonical(self.rules_manifest())).hexdigest()

    def rules_manifest(self) -> list[dict[str, str]]:
        """Every authoritative rule text of this release: the delta first, then the inherited texts in their order."""
        docs = [("DELTA", self.rules_file)] + list(self.inherited)
        return [{"role": role, "file": f.name, "sha256_lf": _sha_lf(f)} for role, f in docs]

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
                "status_label": self.status_label, "economic_usefulness": "UNVALIDATED", "model": self.model, "rules_version": self.rules_version, "rules_sha256": self.rules_sha256(),
                "register_sha256": self.register_sha256(), "implementation": self.implementation,
                "evaluator_implementation": self.evaluator_implementation, "engine_format": self.engine_format,
                "report_version": self.report_version,
                "rules_manifest": self.rules_manifest() if self.inherited else None}


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
    key="v0.2", label="Original v0.2", status="ACCEPTED_BASELINE", status_label="accepted baseline",
    purpose="The accepted MP-001 adviser exactly as evaluated so far (fixed comparison baseline).",
    model=idn.MODEL_ID, rules_version=idn.RULES_VERSION, rules_file=idn.RULES_FILE, register_file=idn.REGISTER_FILE,
    implementation=idn.IMPLEMENTATION_ID, evaluator_implementation="adviser.evaluator.v2",
    core_state_format="algotrader.adviser-state.v2", runtime_format="algotrader.adviser-runtime.v2",
    evaluator_state_format="algotrader.adviser-evaluation-state.v1", engine_format="observe.stream.v3",
    report_version="adviser.report.v2", reconciliation_version="5", deep_version="6")

V03 = Release(
    key="v0.3", label="Revised v0.3 — confirmation then usable entry",
    status="TECHNICALLY_ACCEPTED", status_label="technically accepted (WP-011, 3fcbfc5)",
    purpose=("MP-002: scenarios persist independently of entry; after an A confirmation the adviser may wait for a "
             "later usable price inside the reaction corridor instead of rejecting at once."),
    model="btc.context-action.v0.3", rules_version="mp002.rules.v0.3",
    rules_file=idn.METHOD_DIR / "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md",
    register_file=idn.METHOD_DIR / "MP-002-PARAMETERS.json",
    implementation="adviser.core.v3", evaluator_implementation="adviser.evaluator.v3",
    core_state_format="algotrader.adviser-state.v3", runtime_format="algotrader.adviser-runtime.v3",
    evaluator_state_format="algotrader.adviser-evaluation-state.v2", engine_format="observe.stream.v4",
    report_version="adviser.report.v3", reconciliation_version="6", deep_version="7")

V04 = Release(
    key="v0.4", label="Candidate v0.4 — reaction anchor may be replaced before confirmation",
    status="ENGINEERING_REVIEW_PENDING", status_label="engineering review pending",
    purpose=("MP-003: before confirmation a touch of the A reaction stop V invalidates only that local anchor; the "
             "same scenario waits for a new, deeper completed 15m reaction. Confirmation, waiting entry, costs, "
             "targets and stops after confirmation are unchanged from v0.3."),
    model="btc.context-action.v0.4", rules_version="mp003.rules.v0.4",
    rules_file=idn.METHOD_DIR / "MP-003-A-REACTION-ANCHOR-DISPOSITION.md",
    register_file=idn.METHOD_DIR / "MP-003-PARAMETERS.json",
    implementation="adviser.core.v4", evaluator_implementation="adviser.evaluator.v3",
    core_state_format="algotrader.adviser-state.v4", runtime_format="algotrader.adviser-runtime.v4",
    evaluator_state_format="algotrader.adviser-evaluation-state.v2", engine_format="observe.stream.v5",
    report_version="adviser.report.v4", reconciliation_version="7", deep_version="8",
    inherited=(("INHERITED_MP002_RULES", idn.METHOD_DIR / "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md"),
               ("INHERITED_MP002_DISPOSITION", idn.METHOD_DIR / "MP-002-DIRECTOR-DISPOSITION.md"),
               ("INHERITED_MP001_RULES", idn.METHOD_DIR / "MP-001-INTEGRATED-METHOD-PROPOSAL.md")))

V05 = Release(
    key="v0.5", label="Candidate v0.5 — RETURN waits for a local recovery",
    status="ENGINEERING_REVIEW_PENDING", status_label="engineering review pending",
    purpose=("MP-004: in the A RETURN wait the first usable return no longer issues a call; it prepares one fixed local "
             "reference bar, and a call can only follow a later complete 1m close beyond that bar's favourable extreme "
             "without breaking its contrary extreme (one reference, first recovery evaluated once). Everything else is "
             "v0.4."),
    model="btc.context-action.v0.5", rules_version="mp004.rules.v0.5",
    rules_file=idn.METHOD_DIR / "MP-004-V05-RETURN-RESPONSE.md",
    register_file=idn.METHOD_DIR / "MP-004-PARAMETERS.json",
    implementation="adviser.core.v5", evaluator_implementation="adviser.evaluator.v3",
    core_state_format="algotrader.adviser-state.v5", runtime_format="algotrader.adviser-runtime.v5",
    evaluator_state_format="algotrader.adviser-evaluation-state.v2", engine_format="observe.stream.v6",
    report_version="adviser.report.v5", reconciliation_version="8", deep_version="9",
    inherited=(("DELTA_DIRECTOR_CLOSURE", idn.METHOD_DIR / "MP-004-DIRECTOR-CLOSURE.md"),
               ("INHERITED_MP003_RULES", idn.METHOD_DIR / "MP-003-A-REACTION-ANCHOR-DISPOSITION.md"),
               ("INHERITED_MP002_RULES", idn.METHOD_DIR / "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md"),
               ("INHERITED_MP002_DISPOSITION", idn.METHOD_DIR / "MP-002-DIRECTOR-DISPOSITION.md"),
               ("INHERITED_MP001_RULES", idn.METHOD_DIR / "MP-001-INTEGRATED-METHOD-PROPOSAL.md")))

RELEASES: dict[str, Release] = {r.key: r for r in (V02, V03, V04, V05)}
# MP-002 structural-scenario lineage (scenario/entry_attempt kinds); v0.5 inherits the v0.4 anchors
SCENARIO_METHODS = frozenset({"v0.3", "v0.4", "v0.5"})
ANCHOR_METHODS = frozenset({"v0.4", "v0.5"})  # MP-003 pre-confirmation A anchor epochs
RESPONSE_METHODS = frozenset({"v0.5"})  # MP-004 A RETURN local reference / recovery
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


def is_scenario_method(key: str | None) -> bool:
    """True for releases emitting MP-002 structural scenarios and child entry attempts (v0.3, v0.4, v0.5)."""
    return (key or DEFAULT) in SCENARIO_METHODS


def selectable() -> list[dict[str, Any]]:
    return [r.summary() for r in RELEASES.values()]
