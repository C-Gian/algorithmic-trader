"""WP-014 v0.5 packaging, identity matrix, contract revision, old-method preservation and production codec (pure).

``fixtures/wp014_v04_base_pins.json`` was computed on the UNCHANGED base 776752e (``delivery/evidence/
WP-014-V04-BASE-PINS.py`` run from a detached worktree of that commit) over 53 fixed synthetic fixtures under v0.4
(journal/evaluation sequence + chain + calls), including the MP-003 anchor tapes and every new MP-004 tape. The current
code must reproduce every pin byte for byte (the v0.2/v0.3 pins of WP-012 are re-checked by ``test_mp003_versions``):
the fold hooks introduced for v0.5 are behaviour-neutral and no v0.2/v0.3/v0.4 record, state or reader changed."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import zlib
from datetime import timedelta
from pathlib import Path

import adviser3_fixtures as f3
import adviser5_fixtures as fx
import pytest

from algotrader.adviser import contracts as sc
from algotrader.adviser import engine, methods
from algotrader.adviser.harness import build_events, make_runtime, run_pure, temporal_for
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((Path(__file__).parent / "fixtures" / "wp014_v04_base_pins.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "delivery" / "evidence"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("wp014_pins", ROOT / "delivery/evidence/WP-014-V04-BASE-PINS.py")
_pins_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pins_mod)
FIX = _pins_mod.FIX
V05, V04 = methods.get("v0.5"), methods.get("v0.4")
DAY1, DAY2, T = fx.DAY1, fx.DAY2, fx.T


# -- old methods preserved ---------------------------------------------------------------------------------------------

def test_the_pinned_fixture_set_is_complete():
    assert len(PINS) == len(FIX) == 53 and set(PINS) == {f"v0.4:{k}" for k in FIX}


@pytest.mark.parametrize("key", sorted(PINS))
def test_v04_outputs_are_byte_identical_to_the_unchanged_base(key):
    res = run_pure(DAY1, FIX[key.split(":", 1)[1]](), eval_start=DAY2, method="v0.4")
    core, ev = res.runtime.core, res.runtime.ev
    assert [core.journal_seq, core.journal_chain, ev.record_seq, ev.record_chain, len(res.calls())] == PINS[key]
    assert not any("response" in e["record"] for e in res.journal)  # never a v0.5 variant


# -- packaging and identities ----------------------------------------------------------------------------------------

def test_packaged_mp004_documents_are_the_registered_documents_byte_for_byte():
    for name in ("MP-004-V05-RETURN-RESPONSE.md", "MP-004-DIRECTOR-CLOSURE.md", "MP-004-PARAMETERS.json"):
        packaged = (ROOT / "src/algotrader/adviser/method" / name).read_bytes().replace(b"\r\n", b"\n")
        assert packaged == (ROOT / "delivery" / name).read_bytes().replace(b"\r\n", b"\n"), name
    spec = (ROOT / "delivery/MP-004-V05-RETURN-RESPONSE.md").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(spec).hexdigest() == "ddb09102cf31e31336dcfb440aea20dad01381b0e0dd769c206b212e39103c51"


def test_v05_rules_identity_is_a_manifest_of_every_authoritative_text():
    man = V05.rules_manifest()
    assert [(m["role"], m["file"]) for m in man] == [
        ("DELTA", "MP-004-V05-RETURN-RESPONSE.md"), ("DELTA_DIRECTOR_CLOSURE", "MP-004-DIRECTOR-CLOSURE.md"),
        ("INHERITED_MP003_RULES", "MP-003-A-REACTION-ANCHOR-DISPOSITION.md"),
        ("INHERITED_MP002_RULES", "MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md"),
        ("INHERITED_MP002_DISPOSITION", "MP-002-DIRECTOR-DISPOSITION.md"),
        ("INHERITED_MP001_RULES", "MP-001-INTEGRATED-METHOD-PROPOSAL.md")]
    assert V05.rules_sha256() == hashlib.sha256(canonical(man)).hexdigest()
    # the v0.4 manifest (its delta + inherited texts) is inherited unchanged, file by file and hash by hash
    assert [(m["file"], m["sha256_lf"]) for m in man[2:]] == [(m["file"], m["sha256_lf"]) for m in V04.rules_manifest()]


def test_a_changed_closure_or_inherited_text_changes_the_v05_behaviour_identity(tmp_path):
    for i, role in ((0, "DELTA_DIRECTOR_CLOSURE"), (1, "INHERITED_MP003_RULES")):
        src = V05.inherited[i][1]
        changed = tmp_path / src.name
        changed.write_bytes(src.read_bytes() + b"\nx\n")
        inh = list(V05.inherited)
        inh[i] = (role, changed)
        other = dataclasses.replace(V05, inherited=tuple(inh))
        assert other.rules_manifest()[0] == V05.rules_manifest()[0]  # same delta file
        assert other.rules_sha256() != V05.rules_sha256()


def test_identity_matrix_and_numerical_register_preservation():
    v5 = V05
    assert methods.DEFAULT == "v0.2" and [r["method"] for r in methods.selectable()][:4] == ["v0.2", "v0.3", "v0.4",
                                                                                              "v0.5"]  # + v0.6
    assert (v5.model, v5.rules_version, v5.implementation, v5.evaluator_implementation, v5.core_state_format,
            v5.runtime_format, v5.evaluator_state_format, v5.engine_format, v5.report_version,
            v5.reconciliation_version, v5.deep_version) == (
        "btc.context-action.v0.5", "mp004.rules.v0.5", "adviser.core.v5", "adviser.evaluator.v3",
        "algotrader.adviser-state.v5", "algotrader.adviser-runtime.v5", "algotrader.adviser-evaluation-state.v2",
        "observe.stream.v6", "adviser.report.v5", "8", "9")
    # earlier releases keep every identity and status
    assert (V04.implementation, V04.engine_format, V04.report_version, V04.reconciliation_version, V04.deep_version,
            V04.status) == ("adviser.core.v4", "observe.stream.v5", "adviser.report.v4", "7", "8",
                            "ENGINEERING_REVIEW_PENDING")
    assert v5.status == "ENGINEERING_REVIEW_PENDING"
    assert all(r["economic_usefulness"] == "UNVALIDATED" for r in methods.selectable())
    p4 = {k: v for k, v in V04.params().__dict__.items() if k != "raw"}
    p5 = {k: v for k, v in v5.params().__dict__.items() if k != "raw"}
    assert p4 == p5  # MP-004 adds no numerical threshold
    r4, r5 = V04.register(), v5.register()
    assert {k: r5[k] for k in r4 if k not in ("model", "rules_version", "identity")} == \
        {k: r4[k] for k in r4 if k not in ("model", "rules_version", "identity")}
    assert set(r5) - set(r4) == {"mp004_policy"} and r5["mp004_policy"]["numerical_parameters"].startswith("UNCHANGED")
    assert len({methods.get(k).register_sha256() for k in ("v0.2", "v0.3", "v0.4", "v0.5")}) == 4


def test_semantic_revision_4_records_validate_and_old_kinds_are_unchanged():
    res = run_pure(DAY1, fx.valid(), eval_start=DAY2, method="v0.5")
    for e in res.journal:
        sc.KIND_CONTRACTS_V5[e["kind"]].model_validate(e["record"])
    ents = [e["record"] for e in res.journal if e["kind"] == "entry_attempt"]
    assert ents and all("response" in r for r in ents)
    assert sc.KIND_CONTRACTS_V5["scenario"] is sc.ScenarioStateV4  # anchors inherited unchanged
    assert sc.KIND_CONTRACTS_V4["entry_attempt"] is sc.EntryAttempt  # v0.4 records keep their revision-2 contract
    # WP-015 bumps the revision to 5 (v0.6 values only); v0.5 still emits revision 4
    assert sc.SEMANTIC_V2_REVISION == 5 and sc.SEMANTIC_V2_EMITTED_REVISION["btc.context-action.v0.5"] == 4
    # the response provenance is never an economic or account field of the structural scenario records
    scen = [e["record"] for e in res.journal if e["kind"] == "scenario"]
    assert not [k for r in scen for k in r if k == "response"]


# -- v0.4 / v0.5 parity outside the A RETURN child ---------------------------------------------------------------------

STRUCTURAL = ("scenario", "market_view", "landmark", "observation", "phase", "event_context", "event_response")


def _ids(journal) -> dict[str, str]:
    ids: dict[str, str] = {}
    for e in journal:
        r = e["record"]
        vals = r.get("values") if isinstance(r.get("values"), dict) else {}
        for k, x in [(k, r.get(k)) for k in ("scenario_id", "call_id", "landmark_id", "entry_attempt_id", "owner_id")]                 + [("box_id", vals.get("box_id"))]:
            if isinstance(x, str) and x not in ids:  # one counter per id kind (order of appearance)
                ids[x] = f"<{k}{sum(1 for v in ids.values() if v.startswith(f'<{k}'))}>"
    return ids


def _sub(s: str, ids: dict[str, str]) -> str:
    for raw in sorted(ids, key=len, reverse=True):
        s = s.replace(raw, ids[raw])
    return s


def _norm(journal, kinds, upto: str | None = None):
    """Records without envelopes, identifiers (which hash the release's rules identity by design) replaced by
    order-of-appearance tokens; the v0.5-only ``response`` key removed when null."""
    ids = _ids(journal)
    out = []
    for e in journal:
        if e["kind"] not in kinds or (upto is not None and e["record"]["env"]["clock_time"] > upto):
            continue
        r = _drop_env({k: v for k, v in e["record"].items() if not (k == "response" and v is None)})
        out.append((e["kind"], e["record"]["env"]["clock_time"], _sub(json.dumps(r, sort_keys=True, default=str), ids)))
    return out


def _drop_env(x):
    """Envelopes (top-level and nested, e.g. a call's actionability) carry the release's method identity."""
    if isinstance(x, dict):
        return {k: _drop_env(v) for k, v in x.items() if k != "env"}
    if isinstance(x, list):
        return [_drop_env(v) for v in x]
    return x


@pytest.mark.parametrize("name", sorted(k for k in FIX if not k.startswith("mp004_")))
def test_v05_equals_v04_outside_the_a_return_child(name):
    """Every fixed tape: structural records (scenarios incl. anchors, views, landmarks, observations) are identical;
    without an A RETURN wait the WHOLE journal and every hypothetical path are identical (IMMEDIATE, B/C, geometry,
    costs, deadlines and post-issue lifecycle unchanged); with one, every record before the first usable return is."""
    r4 = run_pure(DAY1, FIX[name](), eval_start=DAY2, method="v0.4")
    r5 = run_pure(DAY1, FIX[name](), eval_start=DAY2, method="v0.5")
    waits = [e for e in r4.journal if e["kind"] == "entry_attempt" and e["record"]["transition"] == "WAIT_OPEN"]
    if not waits:
        everything = tuple(sorted({e["kind"] for e in r4.journal} | {e["kind"] for e in r5.journal}))
        assert _norm(r5.journal, everything) == _norm(r4.journal, everything)
        i4, i5 = _ids(r4.journal), _ids(r5.journal)
        assert [_sub(json.dumps(p, sort_keys=True), i5) for p in r5.paths()] == \
            [_sub(json.dumps(p, sort_keys=True), i4) for p in r4.paths()]
        return
    usable = [e for e in r4.journal if e["kind"] == "entry_attempt" and e["record"]["transition"] == "RETURN_USABLE"]
    cut = usable[0]["record"]["env"]["clock_time"] if usable else None
    if cut is not None:  # every record of every kind published before the usable-return dispatch is identical
        kinds = tuple({e["kind"] for e in r4.journal})
        assert [x for x in _norm(r5.journal, kinds) if x[1] < cut] == [x for x in _norm(r4.journal, kinds) if x[1] < cut]
    # structural lineage does not depend on the child
    assert _norm(r5.journal, ("scenario", "landmark")) == _norm(r4.journal, ("scenario", "landmark"))


# -- production codec: durable restore at every response stage ---------------------------------------------------------

def _engine_doc(rt, method, end):
    cfg, rel = rt.core.cfg, methods.get(method)
    return {"format": rel.engine_format, "adviser": {
        "method": rel.key, "format": rel.runtime_format,
        "identity": rel.composite_identity(cfg.profile, {"instrument": cfg.instrument}, None),
        "profile": cfg.profile.model_dump(mode="json"), "tick": str(cfg.tick), "clock_policy": cfg.clock_policy,
        "eval_start": DAY2.isoformat(), "eval_end": end.isoformat(), "origin": cfg.origin,
        "channels": cfg.channel_ids, "evaluator": rt.ev.identity(), "build": None}}


def _fold(ms, cut_times=(), method="v0.5", events=None):
    """Uninterrupted fold; at each cut time (before the first event available after it) the production
    pack -> unpack round trip replaces the runtime (direct restore, no prefix reconstruction)."""
    evs, cov = build_events(DAY1, ms)
    evs = events or evs
    end = DAY1 + len(ms) * timedelta(minutes=1)
    rt, temporal = make_runtime(eval_start=DAY2, eval_end=end, method=method), temporal_for(cov)
    rt.attach(temporal)
    eng = _engine_doc(rt, method, end)
    journal, records, cuts, states = [], [], sorted(cut_times), {}
    for i, e in enumerate(evs):
        while cuts and e.available_time > cuts[0]:
            j, r = rt.take()
            journal += j
            records += r
            blob, sha = engine.pack_runtime(rt)
            states[cuts[0]] = (rt.core.inspect(), json.loads(zlib.decompress(blob)))
            temporal = te.unpack(*te.pack(temporal))
            rt = engine.unpack_runtime(blob, sha, eng)
            assert canonical(rt.encode()) == zlib.decompress(blob)
            rt.attach(temporal)
            cuts.pop(0)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    temporal.finish(end)
    rt.finish(end)
    j, r = rt.take()
    return journal + j, records + r, states


def _same(ms, cuts, events=None):
    base_j, base_r, _ = _fold(ms, events=events)
    j, r, states = _fold(ms, cuts, events=events)
    assert [e["digest"] for e in j] == [e["digest"] for e in base_j]
    assert [x["digest"] for x in r] == [x["digest"] for x in base_r]
    return base_j, states


def _phase(states, t):
    resp = states[t][0]["responses"]
    return next(iter(resp.values()))["phase"] if resp else None


@pytest.mark.parametrize("side", ["L", "S"])
def test_restore_before_and_after_preparation_and_after_issue_reproduces_the_uninterrupted_run(side):
    ms = fx.valid() if side == "L" else fx.mirror(fx.valid())
    # a cut at t + 30 s holds the state after the dispatch at t - 1 min (the events available at t are admitted, their
    # dispatch is still pending): before the WAIT, in WAIT_RETURN, in WAIT_RESPONSE and after the issue
    cuts = tuple(T(4, m) + timedelta(seconds=30) for m in (1, 2, 3, 4))
    journal, states = _same(ms, cuts)
    assert _phase(states, cuts[0]) is None and _phase(states, cuts[1]) == "WAIT_RETURN"
    assert _phase(states, cuts[2]) == "WAIT_RESPONSE"
    raw = states[cuts[2]][1]
    w = raw["core"]["v3"]["waits"][0]
    assert raw["format"] == "algotrader.adviser-runtime.v5" and raw["core"]["format"] == "algotrader.adviser-state.v5"
    assert w["phase"] == "WAIT_RESPONSE" and w["ref"]["published_at"] == "2025-09-01T04:02:00+00:00"
    assert w["ref"]["cursor"] and w["checked"] == 0
    assert states[cuts[3]][0]["responses"] == {}  # consumed: the issued child never reopens
    assert sum(1 for e in journal if e["kind"] == "call") == 1


def test_restore_after_a_contradiction_and_mid_wait_never_repeats_or_reopens():
    ms = fx.intermediate_violation_then_valid()
    cuts = tuple(T(4, m) + timedelta(seconds=30) for m in (2, 3, 4, 5))
    journal, states = _same(ms, cuts)
    assert _phase(states, cuts[0]) == "WAIT_RETURN" and _phase(states, cuts[1]) == "WAIT_RESPONSE"
    assert states[cuts[2]][0]["responses"] == {} == states[cuts[3]][0]["responses"]
    ends = [e for e in journal if e["kind"] == "entry_attempt" and e["record"]["state"] == "TERMINAL"]
    assert len(ends) == 1 and not [e for e in journal if e["kind"] == "call"]


def test_restore_around_a_late_first_recovery_with_a_delayed_receipt():
    ms = fx.two_valid()
    evs = fx.delayed_events(ms, {fx.index_of(T(4, 2)): 60})
    cuts = (T(4, 3) + timedelta(seconds=30), T(4, 4) + timedelta(seconds=10), T(4, 5) + timedelta(seconds=30))
    journal, states = _same(ms, cuts, events=evs)
    assert _phase(states, cuts[0]) == "WAIT_RESPONSE"  # admitted-but-undispatched bars are not lost on restore
    assert _phase(states, cuts[1]) == "WAIT_RESPONSE" and states[cuts[2]][0]["responses"] == {}
    last = [e["record"] for e in journal if e["kind"] == "entry_attempt"][-1]
    assert last["reason"] == "RESPONSE_NOT_ISSUABLE:RESPONSE_OBSERVED_LATE_NOT_CURRENT"


def test_restore_inside_a_long_wait_preserves_the_checked_count_and_the_deadline_outcome():
    ms = fx.favourable_equality_only()
    journal, states = _same(ms, (T(5, 0),))
    w = states[T(5, 0)][1]["core"]["v3"]["waits"][0]
    assert w["phase"] == "WAIT_RESPONSE" and w["checked"] == 57  # bars [04:02, 04:59) dispatched before the cut
    last = [e["record"] for e in journal if e["kind"] == "entry_attempt"][-1]
    assert (last["reason"], last["response"]["bars_checked"]) == ("ORIGINAL_SETUP_DEADLINE", "87")


def test_a_v05_state_never_decodes_under_another_release_and_vice_versa():
    end = DAY1 + len(fx.valid()) * timedelta(minutes=1)

    def at(method, t):
        evs, cov = build_events(DAY1, fx.valid())
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

    rt5, rt4 = at("v0.5", T(4, 3) + timedelta(seconds=30)), at("v0.4", T(4, 2) + timedelta(seconds=30))
    b5, s5 = engine.pack_runtime(rt5)
    b4, s4 = engine.pack_runtime(rt4)
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b5, s5, _engine_doc(rt4, "v0.4", end))
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b4, s4, _engine_doc(rt5, "v0.5", end))
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(b5, "0" * 64, _engine_doc(rt5, "v0.5", end))
    doc = json.loads(zlib.decompress(b5))
    doc["core"]["v3"]["waits"][0]["unknown_field"] = 1
    bad = canonical(doc)
    with pytest.raises(engine.AdviserStateError):
        engine.unpack_runtime(zlib.compress(bad), hashlib.sha256(bad).hexdigest(), _engine_doc(rt5, "v0.5", end))
    # the v0.4 state has no MP-004 field at all (absent, not empty)
    w4 = json.loads(zlib.decompress(b4))["core"]["v3"]["waits"][0]
    assert not {"phase", "ref", "checked"} & set(w4)


_ = f3
