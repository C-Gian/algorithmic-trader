"""WP-015 v0.6 packaging, identity matrix, contract revision, old-method preservation and production codec (pure).

``fixtures/wp015_v05_base_pins.json`` was computed on the UNCHANGED base 3c6af11 (``delivery/evidence/
WP-015-V05-BASE-PINS.py`` run from a detached worktree of that commit) over 68 fixed synthetic fixtures under v0.5
(journal/evaluation sequence + chain + calls): the 53 WP-014 fixtures, five more MP-004 tapes and the ten MP-005 tapes
(LONG/SHORT). The current code must reproduce every pin byte for byte (the v0.4 pins of WP-014 and the v0.2/v0.3 pins
of WP-012 are re-checked by their own suites): the v0.6 code leaves v0.5 and earlier releases untouched."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import zlib
from datetime import timedelta
from pathlib import Path

import adviser6_fixtures as fx
import pytest
from test_mp004_versions import _engine_doc, _fold

from algotrader.adviser import contracts as sc
from algotrader.adviser import engine, methods
from algotrader.adviser.core6 import REASON
from algotrader.adviser.harness import build_events, make_runtime, run_pure, temporal_for
from algotrader.feed.ordering import canonical

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((Path(__file__).parent / "fixtures" / "wp015_v05_base_pins.json").read_text(encoding="utf-8"))
_spec = importlib.util.spec_from_file_location("wp015_pins", ROOT / "delivery/evidence/WP-015-V05-BASE-PINS.py")
_pins_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pins_mod)
FIX = _pins_mod.FIX
V06, V05 = methods.get("v0.6"), methods.get("v0.5")
DAY1, DAY2, T = fx.DAY1, fx.DAY2, fx.T


# -- old methods preserved ---------------------------------------------------------------------------------------------

def test_the_pinned_fixture_set_is_complete():
    assert len(PINS) == len(FIX) == 68 and set(PINS) == {f"v0.5:{k}" for k in FIX}


@pytest.mark.parametrize("key", sorted(PINS))
def test_v05_outputs_are_byte_identical_to_the_unchanged_base(key):
    res = run_pure(DAY1, FIX[key.split(":", 1)[1]](), eval_start=DAY2, method="v0.5")
    core, ev = res.runtime.core, res.runtime.ev
    assert [core.journal_seq, core.journal_chain, ev.record_seq, ev.record_chain, len(res.calls())] == PINS[key]
    assert not any(str(e["record"].get("reason") or "").startswith(REASON) for e in res.journal)


# -- packaging and identities ----------------------------------------------------------------------------------------

def test_packaged_mp005_documents_are_the_registered_documents_byte_for_byte():
    for name in ("MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md", "MP-005-DIRECTOR-CLOSURE.md",
                 "MP-005-PARAMETERS.json"):
        packaged = (ROOT / "src/algotrader/adviser/method" / name).read_bytes().replace(b"\r\n", b"\n")
        assert packaged == (ROOT / "delivery" / name).read_bytes().replace(b"\r\n", b"\n"), name
    # the specification and the Director closure are separate documents (the closure is not inside the delta)
    spec = (ROOT / "delivery/MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md").read_text(encoding="utf-8")
    closure = (ROOT / "delivery/MP-005-DIRECTOR-CLOSURE.md").read_text(encoding="utf-8")
    assert "Chiusura metodologica del Director" not in spec and closure.startswith("# MP-005 — Chiusura metodologica")
    assert "## 10. Esito della verifica semantica" in spec and "INITIAL_RESPONSE_INCOMPATIBLE" in closure


def test_v06_rules_identity_is_a_manifest_of_every_authoritative_text():
    man = V06.rules_manifest()
    assert [(m["role"], m["file"]) for m in man] == [
        ("DELTA", "MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md"),
        ("DELTA_DIRECTOR_CLOSURE", "MP-005-DIRECTOR-CLOSURE.md"),
        ("INHERITED_MP004_RULES", "MP-004-V05-RETURN-RESPONSE.md"),
        ("INHERITED_MP004_CLOSURE", "MP-004-DIRECTOR-CLOSURE.md"),
        ("INHERITED_MP003_RULES", "MP-003-A-REACTION-ANCHOR-DISPOSITION.md"),
        ("INHERITED_MP002_RULES", "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md"),
        ("INHERITED_MP002_DISPOSITION", "MP-002-DIRECTOR-DISPOSITION.md"),
        ("INHERITED_MP001_RULES", "MP-001-INTEGRATED-METHOD-PROPOSAL.md")]
    assert V06.rules_sha256() == hashlib.sha256(canonical(man)).hexdigest()
    # every v0.5 authoritative text is inherited unchanged, file by file and hash by hash
    assert [(m["file"], m["sha256_lf"]) for m in man[2:]] == [(m["file"], m["sha256_lf"]) for m in V05.rules_manifest()]
    v5_spec = (ROOT / "delivery/MP-004-V05-RETURN-RESPONSE.md").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(v5_spec).hexdigest() == "ddb09102cf31e31336dcfb440aea20dad01381b0e0dd769c206b212e39103c51"


def test_a_changed_closure_or_inherited_text_changes_the_v06_behaviour_identity(tmp_path):
    for i, role in ((0, "DELTA_DIRECTOR_CLOSURE"), (1, "INHERITED_MP004_RULES")):
        src = V06.inherited[i][1]
        changed = tmp_path / src.name
        changed.write_bytes(src.read_bytes() + b"\nx\n")
        inh = list(V06.inherited)
        inh[i] = (role, changed)
        other = dataclasses.replace(V06, inherited=tuple(inh))
        assert other.rules_manifest()[0] == V06.rules_manifest()[0] and other.rules_sha256() != V06.rules_sha256()


def test_identity_matrix_and_numerical_register_preservation():
    v6 = V06
    assert methods.DEFAULT == "v0.2"
    assert [r["method"] for r in methods.selectable()] == ["v0.2", "v0.3", "v0.4", "v0.5", "v0.6"]
    assert (v6.model, v6.rules_version, v6.implementation, v6.evaluator_implementation, v6.core_state_format,
            v6.runtime_format, v6.evaluator_state_format, v6.engine_format, v6.report_version,
            v6.reconciliation_version, v6.deep_version, v6.status) == (
        "btc.context-action.v0.6", "mp005.rules.v0.6", "adviser.core.v6", "adviser.evaluator.v3",
        "algotrader.adviser-state.v6", "algotrader.adviser-runtime.v6", "algotrader.adviser-evaluation-state.v2",
        "observe.stream.v7", "adviser.report.v6", "9", "10", "ENGINEERING_REVIEW_PENDING")
    # earlier releases keep every identity and status
    assert (V05.implementation, V05.engine_format, V05.report_version, V05.reconciliation_version, V05.deep_version,
            V05.status, V05.rules_sha256(), V05.register_sha256()) == (
        "adviser.core.v5", "observe.stream.v6", "adviser.report.v5", "8", "9", "ENGINEERING_REVIEW_PENDING",
        "0e34059a17f6655b72d003261ceaa7283dda7906078b8cb6e264bbf3387334ac",
        "255ab5b7cc591b9ea32cb6978d4b0e929063b68f4b19d2f2ae22a0d38dc280cc")
    assert all(r["economic_usefulness"] == "UNVALIDATED" for r in methods.selectable())
    p5 = {k: v for k, v in V05.params().__dict__.items() if k != "raw"}
    p6 = {k: v for k, v in v6.params().__dict__.items() if k != "raw"}
    assert p5 == p6  # MP-005 adds no numerical threshold, tolerance or live minimum cost
    r5, r6 = V05.register(), v6.register()
    assert {k: r6[k] for k in r5 if k not in ("model", "rules_version", "identity")} == \
        {k: r5[k] for k in r5 if k not in ("model", "rules_version", "identity")}
    assert set(r6) - set(r5) == {"mp005_policy"}
    pol = r6["mp005_policy"]
    assert pol["numerical_parameters"].startswith("UNCHANGED") and pol["new_categorical_elements"] == {
        "terminal_reason": "INITIAL_RESPONSE_INCOMPATIBLE", "terminal_bases": ["CORRIDOR", "HISTORICAL_ECONOMICS"],
        "primary_base_when_concurrent": "CORRIDOR_OTHER_ANNOTATED_ONE_TERMINAL",
        "response_outcome": "INITIAL_RESPONSE_INCOMPATIBLE"}
    assert len({methods.get(k).register_sha256() for k in methods.RELEASES}) == 5
    assert methods.RESPONSE_METHODS == {"v0.5", "v0.6"} and methods.INITIAL_COMPATIBILITY_METHODS == {"v0.6"}


def test_semantic_revision_5_values_validate_with_the_revision_4_contracts():
    res = run_pure(DAY1, fx.h1_economics(), eval_start=DAY2, method="v0.6")
    for e in res.journal:
        sc.KIND_CONTRACTS_V6[e["kind"]].model_validate(e["record"])
    assert sc.KIND_CONTRACTS_V6 == sc.KIND_CONTRACTS_V5 and sc.KIND_CONTRACTS_V6 is not sc.KIND_CONTRACTS_V5
    assert sc.SEMANTIC_V2_REVISION == 5 and sc.SEMANTIC_V2_EMITTED_REVISION["btc.context-action.v0.6"] == 5
    assert sc.SEMANTIC_V2_EMITTED_REVISION["btc.context-action.v0.5"] == 4
    assert any(str(e["record"].get("reason") or "").startswith(REASON) for e in res.journal)


# -- production codec: durable restore around the P -> X dispatch ------------------------------------------------------

def _same(ms, cuts, method="v0.6"):
    base_j, base_r, _ = _fold(ms, method=method)
    j, r, states = _fold(ms, cuts, method=method)
    assert [e["digest"] for e in j] == [e["digest"] for e in base_j]
    assert [x["digest"] for x in r] == [x["digest"] for x in base_r]
    return base_j, states


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("fixture", ["h1_economics", "h2_corridor", "h5_persistence"])
def test_restore_before_and_after_the_initial_terminal_never_reopens(side, fixture):
    ms = getattr(fx, fixture)()
    ms = ms if side == "L" else fx.mirror(ms)
    # a cut at t + 30 s holds the state after the dispatch at t - 1 min: 04:02:30 = WAIT_RETURN (after 04:01);
    # 04:03:30 = right after the P -> X dispatch at 04:02 (the next bar's dispatch still pending); later cuts
    cuts = tuple(T(4, m) + timedelta(seconds=30) for m in (2, 3, 4, 5))
    journal, states = _same(ms, cuts)
    assert next(iter(states[cuts[0]][0]["responses"].values()))["phase"] == "WAIT_RETURN"
    for c in cuts[1:]:
        assert states[c][0]["responses"] == {}  # the ended child never reopens, nothing is re-prepared
    raw = states[cuts[1]][1]
    assert raw["format"] == "algotrader.adviser-runtime.v6" and raw["core"]["format"] == "algotrader.adviser-state.v6"
    assert raw["core"]["v3"]["waits"] == [] and raw["core"]["counters"]["v6"]["initial_incompatible"] == 1
    scen = next(s for s in raw["core"]["v3"]["scen"] if s["family"] == "A")
    assert scen["entry"] == "TERMINAL" and scen["entry_ended"]["reason"] == REASON
    ents = [e["record"] for e in journal if e["kind"] == "entry_attempt" and e["record"]["scenario_id"][:2] in ("AL", "AS")]
    assert [r["transition"] for r in ents].count("RESPONSE_REFERENCE") == 1
    assert [str(r["reason"]).startswith(REASON) for r in ents].count(True) == 1
    assert not [e for e in journal if e["kind"] == "call"]


@pytest.mark.parametrize("side", ["L", "S"])
def test_restore_inside_a_compatible_single_tick_wait_then_issue(side):
    ms = fx.h3_single_tick() if side == "L" else fx.mirror(fx.h3_single_tick())
    cuts = tuple(T(4, m) + timedelta(seconds=30) for m in (3, 4))  # after the 04:02 preparation / the 04:03 issue
    journal, states = _same(ms, cuts)
    assert next(iter(states[cuts[0]][0]["responses"].values()))["phase"] == "WAIT_RESPONSE"
    assert states[cuts[1]][0]["responses"] == {} and sum(1 for e in journal if e["kind"] == "call") == 1


def test_a_v06_state_never_decodes_under_another_release_and_vice_versa():
    end = DAY1 + len(fx.h1_economics()) * timedelta(minutes=1)

    def at(method, t):
        evs, cov = build_events(DAY1, fx.h1_economics())
        rt, temporal = make_runtime(eval_start=DAY2, eval_end=end, method=method), temporal_for(cov)
        rt.attach(temporal)
        for i, e in enumerate(evs):
            if e.available_time > t:
                break
            temporal.on_event(e, i)
            rt.before_admit(e)
            rt.admit(e, i)
        rt.take()
        return rt

    rt6, rt5 = at("v0.6", T(4, 2) + timedelta(seconds=30)), at("v0.5", T(4, 2) + timedelta(seconds=30))
    b6, s6 = engine.pack_runtime(rt6)
    b5, s5 = engine.pack_runtime(rt5)
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b6, s6, _engine_doc(rt5, "v0.5", end))
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b5, s5, _engine_doc(rt6, "v0.6", end))
    ok = engine.unpack_runtime(b6, s6, _engine_doc(rt6, "v0.6", end))
    assert canonical(ok.encode()) == zlib.decompress(b6)
    # the v0.5 state has no v0.6 field at all (absent, not empty)
    s5doc = json.loads(zlib.decompress(b5))
    assert "v6" not in s5doc["core"]["counters"]
    assert not [s for s in s5doc["core"]["v3"]["scen"] if "entry_ended" in s]
