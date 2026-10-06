"""WP-012 v0.4 packaging, identity matrix, contract revision, old-method preservation and production codec (pure).

``fixtures/wp012_v02_v03_base_pins.json`` was computed on the UNCHANGED base 68f26da (product source identical to the
accepted 3fcbfc5) over 11 v0.2 and 8 v0.3 fixed synthetic fixtures for both methods (journal/evaluation sequence +
chain + calls). The current code must reproduce every pin byte for byte: the v0.3 fold hooks introduced for v0.4 are
behaviour-neutral and no v0.2/v0.3 record, state or reader changed."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import zlib
from datetime import timedelta
from pathlib import Path

import adviser3_fixtures as f3
import adviser4_fixtures as fx
import pytest
from adviser_fixtures import DAY1, DAY2, a_fixture, box_fixture, mirror

from algotrader.adviser import contracts as sc
from algotrader.adviser import engine, methods
from algotrader.adviser.harness import build_events, make_runtime, run_pure, temporal_for
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((Path(__file__).parent / "fixtures" / "wp012_v02_v03_base_pins.json").read_text(encoding="utf-8"))
FIX = {
    "a_rally": lambda: a_fixture(), "a_stop": lambda: a_fixture(after_issue="stop"),
    "a_stall": lambda: a_fixture(after_issue="stall"), "a_progress": lambda: a_fixture(after_issue="progress"),
    "a_fade": lambda: a_fixture(after_arm="fade"), "a_short": lambda: mirror(a_fixture()),
    "box_b": lambda: box_fixture("B"), "box_c": lambda: box_fixture("C"), "box_b_return": lambda: box_fixture("B_RETURN"),
    "box_b_opposite": lambda: box_fixture("B_OPPOSITE"), "box_c_short": lambda: mirror(box_fixture("C")),
    "a3_return_long": f3.a3_return_long, "a3_return_short": lambda: f3.mirror(f3.a3_return_long()),
    "a3_cap_then_return": f3.a3_cap_then_return, "a3_cap_activation_contact": f3.a3_cap_activation_contact,
    "a3_cap_not_ahead": f3.a3_cap_not_ahead, "a3_expiry_at_return": f3.a3_expiry_at_return,
    "a3_stall_after_return": f3.a3_stall_after_return, "a3_outside_then": f3.a3_outside_then,
}
V04 = methods.get("v0.4")


# -- old methods preserved ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(PINS))
def test_v02_and_v03_outputs_are_byte_identical_to_the_unchanged_base(key):
    method, name = key.split(":")
    res = run_pure(DAY1, FIX[name](), eval_start=DAY2, method=method)
    core, ev = res.runtime.core, res.runtime.ev
    assert [core.journal_seq, core.journal_chain, ev.record_seq, ev.record_chain, len(res.calls())] == PINS[key]
    assert not any("anchor_epoch" in e["record"] for e in res.journal)  # never a v0.4 variant


# -- packaging and identities ----------------------------------------------------------------------------------------

def test_packaged_mp003_documents_are_the_director_documents_byte_for_byte():
    for name in ("MP-003-A-REACTION-ANCHOR-DISPOSITION.md", "MP-003-PARAMETERS.json", "MP-002-DIRECTOR-DISPOSITION.md",
                 "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md", "MP-001-INTEGRATED-METHOD-PROPOSAL.md"):
        packaged = (ROOT / "src/algotrader/adviser/method" / name).read_bytes().replace(b"\r\n", b"\n")
        assert packaged == (ROOT / "delivery" / name).read_bytes().replace(b"\r\n", b"\n"), name


def test_v04_rules_identity_is_a_manifest_of_every_authoritative_text():
    man = V04.rules_manifest()
    assert [(m["role"], m["file"]) for m in man] == [
        ("DELTA", "MP-003-A-REACTION-ANCHOR-DISPOSITION.md"),
        ("INHERITED_MP002_RULES", "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md"),
        ("INHERITED_MP002_DISPOSITION", "MP-002-DIRECTOR-DISPOSITION.md"),
        ("INHERITED_MP001_RULES", "MP-001-INTEGRATED-METHOD-PROPOSAL.md")]
    assert V04.rules_sha256() == hashlib.sha256(canonical(man)).hexdigest()
    # inherited texts are pinned too: the v0.3 rules hash equals the inherited MP-002 entry, v0.2 the MP-001 one
    assert man[1]["sha256_lf"] == methods.get("v0.3").rules_sha256()
    assert man[3]["sha256_lf"] == methods.get("v0.2").rules_sha256()


def test_a_changed_inherited_text_changes_the_v04_behaviour_identity(tmp_path):
    changed = tmp_path / "MP-002-DIRECTOR-DISPOSITION.md"
    changed.write_bytes((ROOT / "src/algotrader/adviser/method/MP-002-DIRECTOR-DISPOSITION.md").read_bytes() + b"\nx\n")
    other = dataclasses.replace(V04, inherited=(V04.inherited[0], ("INHERITED_MP002_DISPOSITION", changed),
                                                V04.inherited[2]))
    assert other.rules_manifest()[0] == V04.rules_manifest()[0]  # same delta file
    assert other.rules_sha256() != V04.rules_sha256()


def test_identity_matrix_and_numerical_register_preservation():
    v2, v3, v4 = methods.get("v0.2"), methods.get("v0.3"), V04
    assert methods.DEFAULT == "v0.2" and methods.get(None) is v2  # absent selection keeps the existing default
    assert (v4.model, v4.rules_version, v4.implementation, v4.evaluator_implementation, v4.core_state_format,
            v4.runtime_format, v4.evaluator_state_format, v4.engine_format, v4.report_version,
            v4.reconciliation_version, v4.deep_version) == (
        "btc.context-action.v0.4", "mp003.rules.v0.4", "adviser.core.v4", "adviser.evaluator.v3",
        "algotrader.adviser-state.v4", "algotrader.adviser-runtime.v4", "algotrader.adviser-evaluation-state.v2",
        "observe.stream.v5", "adviser.report.v4", "7", "8")
    assert (v2.status, v3.status, v4.status) == ("ACCEPTED_BASELINE", "TECHNICALLY_ACCEPTED",
                                                 "ENGINEERING_REVIEW_PENDING")
    assert all(r["economic_usefulness"] == "UNVALIDATED" for r in methods.selectable())
    p3 = {k: v for k, v in v3.params().__dict__.items() if k != "raw"}
    p4 = {k: v for k, v in v4.params().__dict__.items() if k != "raw"}
    assert p3 == p4  # MP-003 changes no numerical trading value
    assert v4.register()["continuation"]["reanchoring"].startswith("PRE_CONFIRMATION_LOCAL_ANCHOR_EPOCHS_ONLY_MP003")
    assert len({v2.register_sha256(), v3.register_sha256(), v4.register_sha256()}) == 3


def test_semantic_revision_3_records_validate_and_old_kinds_are_unchanged():
    res = run_pure(DAY1, fx.contact_then_rearm(), eval_start=DAY2, method="v0.4")
    for e in res.journal:
        sc.KIND_CONTRACTS_V4[e["kind"]].model_validate(e["record"])
    scen = [e["record"] for e in res.journal if e["kind"] == "scenario"]
    assert scen and all("anchor_epoch" in r for r in scen)
    assert sc.KIND_CONTRACTS_V4["entry_attempt"] is sc.KIND_CONTRACTS_V3["entry_attempt"]
    assert sc.KIND_CONTRACTS_V3["scenario"] is sc.ScenarioState  # v0.3 records keep their revision-2 contract
    banned = {"K_cost", "economic", "margin", "call_id", "price"}
    assert not [k for r in scen for k in r if any(b in k for b in banned)]  # structural: no economic field


# -- production codec ------------------------------------------------------------------------------------------------

MINS = fx.contact_then_rearm()
EVENTS, COV = build_events(DAY1, MINS)
END = DAY1 + len(MINS) * timedelta(minutes=1)


def _rt(method="v0.4", params=None):
    return make_runtime(eval_start=DAY2, eval_end=END, method=method, params=params)


def _engine_doc(rt, method="v0.4"):
    cfg, rel = rt.core.cfg, methods.get(method)
    return {"format": rel.engine_format, "adviser": {
        "method": rel.key, "format": rel.runtime_format,
        "identity": rel.composite_identity(cfg.profile, {"instrument": cfg.instrument}, None),
        "profile": cfg.profile.model_dump(mode="json"), "tick": str(cfg.tick), "clock_policy": cfg.clock_policy,
        "eval_start": DAY2.isoformat(), "eval_end": END.isoformat(), "origin": cfg.origin,
        "channels": cfg.channel_ids, "evaluator": rt.ev.identity(), "build": None}}


def _fold(cut_times=(), method="v0.4"):
    """Uninterrupted fold; at each cut time (before the first event available after it) the production
    pack -> unpack round trip replaces the runtime (direct restore, no prefix reconstruction)."""
    rt, temporal = _rt(method), temporal_for(COV)
    rt.attach(temporal)
    eng = _engine_doc(rt, method)
    journal, records, cuts, states = [], [], sorted(cut_times), {}
    for i, e in enumerate(EVENTS):
        while cuts and e.available_time > cuts[0]:
            j, r = rt.take()
            journal += j
            records += r
            blob, sha = engine.pack_runtime(rt)
            states[cuts[0]] = rt.core.inspect()
            temporal = te.unpack(*te.pack(temporal))
            rt = engine.unpack_runtime(blob, sha, eng)
            assert canonical(rt.encode()) == zlib.decompress(blob)
            rt.attach(temporal)
            cuts.pop(0)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    temporal.finish(END)
    rt.finish(END)
    j, r = rt.take()
    return journal + j, records + r, states


CUTS = (f3.T(3, 40), f3.T(3, 47), f3.T(3, 52), f3.T(4, 0, ), f3.T(4, 5), f3.T(4, 9), f3.T(5, 40))


def test_production_pack_unpack_at_every_anchor_stage_reproduces_the_uninterrupted_outputs():
    """Cuts before first arm, armed, after the contact (WATCH, lost anchor), at the same-dispatch replacement
    boundary, armed epoch 2, at confirmation and after the owner release: identical journal/evaluation bytes."""
    base_j, base_r, _ = _fold()
    j, r, states = _fold(CUTS)
    assert [e["digest"] for e in j] == [e["digest"] for e in base_j]
    assert [x["digest"] for x in r] == [x["digest"] for x in base_r]
    anchors = {t.strftime("%H:%M"): next(iter(s["anchors"].values()), None) for t, s in states.items()}
    assert anchors["03:47"]["epoch"] == 1 and anchors["03:47"]["status"] == "ACTIVE"
    assert anchors["03:52"]["status"] == "INVALIDATED" and anchors["03:52"]["ever_armed"] is True
    assert anchors["04:05"]["epoch"] == 2 and anchors["04:05"]["destination_monitoring_from"].startswith(
        "2025-09-01T03:45")


def _state_at(t, method="v0.4"):
    rt, temporal = _rt(method), temporal_for(COV)
    rt.attach(temporal)
    for i, e in enumerate(EVENTS):
        if e.available_time > t:
            break
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    rt.take()
    return rt


def test_a_v04_state_never_decodes_under_another_release_and_vice_versa():
    rt4, rt3 = _state_at(f3.T(3, 52)), _state_at(f3.T(3, 52), "v0.3")
    b4, s4 = engine.pack_runtime(rt4)
    b3, s3 = engine.pack_runtime(rt3)
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b4, s4, _engine_doc(rt3, "v0.3"))
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b3, s3, _engine_doc(rt4, "v0.4"))
    raw = json.loads(zlib.decompress(b4))
    assert raw["format"] == "algotrader.adviser-runtime.v4" and raw["core"]["format"] == "algotrader.adviser-state.v4"
    scen = [s for s in raw["core"]["v3"]["scen"] if s["family"] == "A"]
    assert scen and {"epoch", "anchor_status", "ever_armed", "first_arm_at", "lost_r_t", "lost_cutoff"} <= set(scen[0])
    # corrupt / tampered state fails explicitly (exact round-trip and SHA guards intact)
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b4, "0" * 64, _engine_doc(rt4))
    doc = json.loads(zlib.decompress(b4))
    doc["core"]["v3"]["scen"][0]["unknown_field"] = 1
    bad = canonical(doc)
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(zlib.compress(bad), hashlib.sha256(bad).hexdigest(), _engine_doc(rt4))


def test_active_state_is_bounded_anchor_history_lives_in_the_journal():
    rt = _state_at(f3.T(5, 0))
    doc = rt.encode()
    for s in doc["core"]["v3"]["scen"]:
        assert len(s["v_hist"]) <= 16


# -- B/C and post-confirmation A parity with v0.3 on fixed tapes --------------------------------------------------------

def _ids(journal) -> dict[str, str]:
    ids: dict[str, str] = {}
    for e in journal:
        r = e["record"]
        for k in ("scenario_id", "call_id", "landmark_id"):
            if e["kind"] in ("scenario", "call", "landmark") and isinstance(r.get(k), str):
                ids.setdefault(r[k], f"<{k}{len(ids)}>")
    return ids


def _sub(s: str, ids: dict[str, str]) -> str:
    for raw in sorted(ids, key=len, reverse=True):
        s = s.replace(raw, ids[raw])
    return s


def _norm(journal, kinds):
    """Records without envelopes; scenario and call identifiers (which hash the release's rules identity by design)
    replaced by order-of-appearance tokens everywhere in the record; v0.4-only anchor fields removed."""
    ids = _ids(journal)
    out = []
    for e in journal:
        if e["kind"] not in kinds:
            continue
        r = {k: v for k, v in e["record"].items() if k != "env" and not k.startswith(
            ("anchor_", "destination_monitoring")) and k not in ("ever_armed", "previous_anchor")}
        s = _sub(json.dumps(r, sort_keys=True, default=str), ids)
        out.append((e["kind"], e["record"]["env"]["clock_time"], s))
    return out


@pytest.mark.parametrize("name", ["a3_return_long", "a3_return_short", "a3_cap_then_return", "a3_stall_after_return",
                                  "a3_expiry_at_return", "box_b", "box_c", "box_b_return", "box_c_short"])
def test_bc_and_post_confirmation_outputs_match_v03_where_no_preconfirmation_contact_occurs(name):
    r3 = run_pure(DAY1, FIX[name](), eval_start=DAY2, method="v0.3")
    r4 = run_pure(DAY1, FIX[name](), eval_start=DAY2, method="v0.4")
    kinds = ("entry_attempt", "call_revision", "material_change")
    assert _norm(r4.journal, kinds) == _norm(r3.journal, kinds)
    assert [c["entry_mode"] for c in r4.calls()] == [c["entry_mode"] for c in r3.calls()]
    i3, i4 = _ids(r3.journal), _ids(r4.journal)
    got = [_sub(json.dumps(p, sort_keys=True), i4) for p in r4.paths()]
    assert got == [_sub(json.dumps(p, sort_keys=True), i3) for p in r3.paths()]
    t3 = [(s["env"]["clock_time"], s["transition"], s["reason"]) for s in r3.scenarios()]
    t4 = [(s["env"]["clock_time"], s["transition"], s["reason"]) for s in r4.scenarios()]
    assert t4 == t3
