"""WP-011 method packaging, explicit dispatch, contract revisions and v0.2 baseline preservation (pure).

The v0.2 pins below were computed with the UNCHANGED base commit 7bf0f3c (product src identical to 6f95273) on the
same fixed synthetic fixtures (journal/evaluation sequence + chain); the current code must reproduce them byte for
byte: the baseline reducer/evaluator, record shapes and state formats are untouched."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from adviser_fixtures import DAY1, DAY2, a_fixture, box_fixture, mirror

from algotrader.adviser import contracts as sc
from algotrader.adviser import evaluation_contracts as ec
from algotrader.adviser import identity as idn
from algotrader.adviser import methods
from algotrader.adviser.harness import run_pure
from algotrader.feed.ordering import canonical
from algotrader.observe import contracts as oc

ROOT = Path(__file__).resolve().parents[1]

V02_PINS = {  # name: (journal_seq, journal_chain, evaluation_seq, evaluation_chain, calls)
    "a_fade": (64, "145df287ec8d9d688e6f1effafb1497f7392370e345d60153f6afc971aa5bbf1", 19,
               "4014186e62960e6ef051e1fd082122b711ccca400626d90bb2a437a70e1df916", 0),
    "a_progress": (83, "0e9acbf5e1c19b58e4776f4574c0201bee3304b4c9ccffa267d287018a0dfb5e", 25,
                   "bb18888e7f9fbf87a3b1d9c1dc5b950dc6385265a1b49da5bdc26c38c80ff203", 1),
    "a_rally": (81, "a30074a0b6dbe07737a4e2c2e20f57630e99d8ace4c647c1db9ec3d0496048e1", 21,
                "147029ecae38dc828088c8d5988802f705b95be9aea76f8296cadc49aa994703", 1),
    "a_short": (81, "147b68f6a5deff7da6f3085ce7a0c48ca08237d3ead8885a4e3351dda69495f8", 21,
                "5581b2fe4c8d41afa85da45301123b7b5b86eeab2ac48128ea90bc64ced538d7", 1),
    "a_stall": (76, "1b0f629cdad2a6d6c2578331c3ed58e81397ee2255d6815801a49f1ce323887c", 25,
                "8c29ec4f74b5364359f1944d29f81d3bf1e7b27b6999a4ce01f72618bb1301e2", 1),
    "a_stop": (70, "793707ab228d0b46a6af2d0316bb33aba2709974b73a631e3c061c8b987ee8df", 18,
               "b5db615ad095265b232cf6d6bd82dbcb8d89dc43fea2f70655cf932317476504", 1),
    "box_b": (73, "4cccdfb0ad1536243f3433bd0a359fa31596dc9362c24a707fa9dc5784912115", 20,
              "87829c48b33d1f39ab3cd4ca5cc93993efb2b5e2388b4fb27ba5f3a36642b61c", 1),
    "box_b_opposite": (46, "17294268375df471f4022aa6bc96e2852c2cc2a9fc01ceb6df53cfd3267d1096", 12,
                       "8d63c5354841f94b04c8325d32098ddcd11f62f1ce4e6de5fc9654c7373ec288", 0),
    "box_b_return": (68, "4e404d1011bfd3a3cd20392b2f9bf8d5c1a642ff97c1ed560f257d0ffd0b16ff", 17,
                     "73d1b599bdd729afa088a6d48220b2ef79cf3b25150691d8195bce97af9ce4c8", 1),
    "box_c": (64, "3a97fb61c3909fb785c0c97ebb5a60f13c01c0d4dad5026f487260c8199d7ebb", 18,
              "c19d4e26eaf804d7e78a07f531295f47c9c187bf5b36e1351ccbf66fb7df1561", 1),
    "box_c_short": (64, "a03d6868650519d24ed83135eac7a7ef258865e267028a611f60ce257fba3879", 18,
                    "f841196427ffa71a873ee36bbb026f6127ade90edcc29bd194668b1f09441593", 1),
}
FIX = {
    "a_rally": lambda: a_fixture(), "a_stop": lambda: a_fixture(after_issue="stop"),
    "a_stall": lambda: a_fixture(after_issue="stall"), "a_progress": lambda: a_fixture(after_issue="progress"),
    "a_fade": lambda: a_fixture(after_arm="fade"), "a_short": lambda: mirror(a_fixture()),
    "box_b": lambda: box_fixture("B"), "box_c": lambda: box_fixture("C"), "box_b_return": lambda: box_fixture("B_RETURN"),
    "box_b_opposite": lambda: box_fixture("B_OPPOSITE"), "box_c_short": lambda: mirror(box_fixture("C")),
}


@pytest.mark.parametrize("name", sorted(V02_PINS))
def test_v02_baseline_outputs_are_byte_identical_to_the_unchanged_base(name):
    res = run_pure(DAY1, FIX[name](), eval_start=DAY2)  # default method: v0.2
    core, ev = res.runtime.core, res.runtime.ev
    got = (core.journal_seq, core.journal_chain, ev.record_seq, ev.record_chain, len(res.calls()))
    assert got == V02_PINS[name]
    assert {e["kind"] for e in res.journal} <= set(sc.KIND_CONTRACTS)  # never a v0.3 kind or variant
    assert all("scenario_id" not in e["record"] for e in res.journal if e["kind"] == "call")


def test_packaged_mp002_rules_and_register_are_the_director_documents_byte_for_byte():
    for name in ("MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md", "MP-002-PARAMETERS.json",
                 "MP-001-INTEGRATED-METHOD-PROPOSAL.md", "MP-001-PARAMETERS.json"):
        packaged = (ROOT / "src/algotrader/adviser/method" / name).read_bytes().replace(b"\r\n", b"\n")
        director = (ROOT / "delivery" / name).read_bytes().replace(b"\r\n", b"\n")
        assert packaged == director, name
    v3 = methods.get("v0.3")
    assert v3.rules_sha256() == hashlib.sha256((ROOT / "delivery/MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md")
                                               .read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    reg = v3.register()
    assert (reg["model"], reg["rules_version"]) == ("btc.context-action.v0.3", "mp002.rules.v0.3")
    assert v3.register_sha256() == hashlib.sha256(canonical(reg)).hexdigest() != idn.register_sha256()


def _leaves(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _leaves(v, path + (k,))
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield path, x
    elif isinstance(x, list) and x and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x):
        yield path, x


def test_every_numerical_mp001_value_is_kept_at_its_path_in_the_mp002_register():
    old = json.loads((ROOT / "delivery/MP-001-PARAMETERS.json").read_text(encoding="utf-8"))
    new = json.loads((ROOT / "delivery/MP-002-PARAMETERS.json").read_text(encoding="utf-8"))
    missing = []
    for path, v in _leaves(old):
        cur = new
        for k in path:
            cur = cur.get(k) if isinstance(cur, dict) else None
        if cur != v:
            missing.append((path, v, cur))
    assert missing == []
    assert methods.get("v0.3").params() == methods.get("v0.3").params()  # typed view loads (no numeric drift)
    p2, p3 = methods.get("v0.2").params(), methods.get("v0.3").params()
    assert {k: v for k, v in p2.__dict__.items() if k != "raw"} == {k: v for k, v in p3.__dict__.items() if k != "raw"}


def test_method_dispatch_identities_and_defaults():
    v2, v3 = methods.get(None), methods.get("v0.3")
    assert v2.key == methods.DEFAULT == "v0.2" and v2 is methods.for_engine({})  # absent pin = WP-009 v0.2
    assert (v2.implementation, v2.runtime_format, v2.engine_format) == \
        ("adviser.core.v2", "algotrader.adviser-runtime.v2", "observe.stream.v3")
    assert (v2.model, v2.rules_version, v2.rules_sha256(), v2.register_sha256()) == \
        (idn.MODEL_ID, idn.RULES_VERSION, idn.rules_sha256(), idn.register_sha256())
    assert (v3.implementation, v3.evaluator_implementation, v3.core_state_format, v3.runtime_format,
            v3.evaluator_state_format, v3.report_version, v3.engine_format, v3.reconciliation_version,
            v3.deep_version) == ("adviser.core.v3", "adviser.evaluator.v3", "algotrader.adviser-state.v3",
                                 "algotrader.adviser-runtime.v3", "algotrader.adviser-evaluation-state.v2",
                                 "adviser.report.v3", "observe.stream.v4", "6", "7")
    assert v3.status == "TECHNICALLY_ACCEPTED" and v3.label.startswith("Revised v0.3")  # WP-012 status correction
    with pytest.raises(methods.UnknownMethod):
        methods.get("v0.9")  # WP-012: v0.4 is now a packaged release
    p = idn.historical_profile()
    a, b = v2.composite_identity(p, {"pack": "x"}, "b"), v3.composite_identity(p, {"pack": "x"}, "b")
    assert a == idn.composite_identity(p, {"pack": "x"}, "b") and a["identity_sha256"] != b["identity_sha256"]


def test_provisional_contract_revisions_and_per_method_emission():
    # WP-012 bumped semantic.v2 to r3 (ScenarioStateV4) and observe.v1 to r7 (method value v0.4); WP-014 to r4
    # (EntryAttemptV5) and r8 (method value v0.5); WP-015 to r5 (v0.6 values only) and r9 (method value v0.6); the
    # evaluation contract stays r3 (v0.4-v0.6 reuse the v0.3 evaluator)
    assert (sc.SEMANTIC_V2_REVISION, ec.EVALUATION_REVISION, oc.OBSERVE_SCHEMA_REVISION) == (5, 3, 9)
    assert [r for r, _, _ in sc.SEMANTIC_V2_CHANGELOG] == [1, 2, 3, 4, 5]
    assert [r for r, _, _ in ec.EVALUATION_CHANGELOG] == [1, 2, 3]
    assert [r for r, _, _ in oc.OBSERVE_CHANGELOG][-1] == 9  # WP-015
    assert sc.SEMANTIC_V2_EMITTED_REVISION == {"btc.context-action.v0.2": 1, "btc.context-action.v0.3": 2,
                                               "btc.context-action.v0.4": 3, "btc.context-action.v0.5": 4,
                                               "btc.context-action.v0.6": 5}  # WP-015
    assert "candidate" in sc.KIND_CONTRACTS and "candidate" not in sc.KIND_CONTRACTS_V3
    assert {"scenario", "entry_attempt"} <= set(sc.KIND_CONTRACTS_V3) and "scenario" not in sc.KIND_CONTRACTS
    # a revision-1 (v0.2) record still validates with the revision-1 contract after the revision bump
    res = run_pure(DAY1, a_fixture(), eval_start=DAY2)
    for e in res.journal:
        sc.KIND_CONTRACTS[e["kind"]].model_validate(e["record"])
    launch = oc.ObservationLaunch.model_validate({
        "schema_version": "algotrader.observe.v1", "replay_id": "r", "source_kind": "pack", "source_id": "p",
        "requested_at": "2026-10-05T00:00:00Z", "speed": 0, "paused": False, "evaluation_id": None,
        "expected_manifest_sha256": None, "code_version": None, "run_type": "adviser_evaluation"})
    assert launch.adviser_method is None  # revision-5 launch envelopes keep the v0.2 default


def test_v03_records_validate_and_the_scenario_kind_carries_no_economic_field():
    from adviser3_fixtures import a3_return_long

    res = run_pure(DAY1, a3_return_long(), eval_start=DAY2, method="v0.3")
    kinds = {e["kind"] for e in res.journal}
    assert kinds <= set(sc.KIND_CONTRACTS_V3) and {"scenario", "entry_attempt"} <= kinds
    for e in res.journal:
        sc.KIND_CONTRACTS_V3[e["kind"]].model_validate(e["record"])
    for e in res.journal:
        if e["kind"] == "scenario":
            flat = json.dumps({k: v for k, v in e["record"].items() if k != "env"}).lower()
            for word in ("cost", "k_cost", "admissible", "call_id", "economic", "mode"):
                assert word not in flat, word
