"""WP-011 compatibility follow-up (correction review F3): v0.3 states written by the reviewed codec (f1a8023 / ed64d05,
no ``core.v3.deps``) restore through the PRODUCTION ``engine.unpack_runtime`` with its exact round-trip guard intact.

The legacy fixture ``tests/fixtures/mp002_legacy_v3_states.json.gz`` was encoded by the reviewed codec itself
(generator: ``delivery/evidence/WP-011-COMPAT-LEGACY-FIXTURE-GEN.py``). Absent and present-empty snapshots are distinct
shapes; a legacy state keeps its exact shape until a genuine dispatch recomputes the snapshot. A snapshot missing from a
legacy state is never invented: records emitted before that first recomputation carry no dependencies (disclosed)."""

from __future__ import annotations

import gzip
import hashlib
import json
import zlib
from datetime import datetime, timedelta
from pathlib import Path

import adviser3_fixtures as fx
import pytest
from adviser3_fixtures import DAY1, T

from algotrader.adviser import engine, methods
from algotrader.adviser.harness import build_events, make_runtime, temporal_for
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

LEGACY = json.loads(gzip.decompress((Path(__file__).parent / "fixtures" / "mp002_legacy_v3_states.json.gz")
                                    .read_bytes()))
ES, EE = datetime.fromisoformat(LEGACY["eval_start"]), datetime.fromisoformat(LEGACY["eval_end"])
MINS = fx.a3_stall_after_return()
EVENTS, COV = build_events(DAY1, MINS)
END = DAY1 + len(MINS) * timedelta(minutes=1)


def new_runtime(method="v0.3"):
    return make_runtime(eval_start=ES, eval_end=EE, method=method)


def engine_doc(rt, method="v0.3"):
    """Complete pinned engine document for the synthetic configuration (keys of ``adviser.engine.engine_config``)."""
    cfg, rel = rt.core.cfg, methods.get(method)
    return {"format": rel.engine_format, "adviser": {
        "method": rel.key, "format": rel.runtime_format,
        "identity": rel.composite_identity(cfg.profile, {"instrument": cfg.instrument}, None),
        "profile": cfg.profile.model_dump(mode="json"), "tick": str(cfg.tick), "clock_policy": cfg.clock_policy,
        "eval_start": ES.isoformat(), "eval_end": EE.isoformat(), "origin": cfg.origin, "channels": cfg.channel_ids,
        "evaluator": rt.ev.identity(), "build": None}}


ENGINE = engine_doc(new_runtime())


def blob(raw: bytes) -> tuple[bytes, str]:
    return zlib.compress(raw, 6), hashlib.sha256(raw).hexdigest()


def unpack(raw: bytes):
    return engine.unpack_runtime(*blob(raw), ENGINE)


def legacy_raw(name: str) -> bytes:
    st = LEGACY["states"][name]
    raw = st["state"].encode()
    assert hashlib.sha256(raw).hexdigest() == st["sha256"]
    return raw


def reference(stop_at: dict[int, str] | None = None):
    """Uninterrupted fold with the current codec; returns outputs, states and temporal packs captured before the given
    event indexes, and the event index at which each output was drained."""
    rt, temporal = new_runtime(), temporal_for(COV)
    rt.attach(temporal)
    journal, records, states = [], [], {}
    for i, e in enumerate(EVENTS):
        if stop_at and i in stop_at:
            j, r = rt.take()
            journal += j
            records += r
            states[stop_at[i]] = {"raw": canonical(rt.encode()), "temporal": te.pack(temporal),
                                  "journal": len(journal), "records": len(records)}
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    temporal.finish(END)
    rt.finish(END)
    j, r = rt.take()
    return journal + j, records + r, states


CUTS = {LEGACY["states"][k]["event_index"]: k for k in LEGACY["states"]}
REF_J, REF_R, REF_STATES = reference(CUTS)


def continue_from(rt, name):
    """Continue ``rt`` (restored at the cut ``name``) with the reference temporal state to the end."""
    st = REF_STATES[name]
    temporal = te.unpack(*st["temporal"])
    rt.attach(temporal)
    journal, records = list(REF_J[:st["journal"]]), list(REF_R[:st["records"]])
    first = LEGACY["states"][name]["event_index"]
    after_first_dispatch = None
    seq0 = rt.core.seq
    for i in range(first, len(EVENTS)):
        e = EVENTS[i]
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
        if after_first_dispatch is None and rt.core.seq > seq0:
            j, r = rt.take()
            journal += j
            records += r
            after_first_dispatch = (i, json.loads(canonical(rt.encode())))
    temporal.finish(END)
    rt.finish(END)
    j, r = rt.take()
    return journal + j, records + r, after_first_dispatch


# -- the fixture really is the reviewed codec's shape of the same state ---------------------------------------------


@pytest.mark.parametrize("name", sorted(LEGACY["states"]))
def test_legacy_fixture_equals_the_current_state_without_the_snapshot(name):
    new = json.loads(REF_STATES[name]["raw"])
    assert new["core"]["v3"]["deps"], "the current codec writes a non-empty snapshot at this cut"
    del new["core"]["v3"]["deps"]
    assert canonical(new) == legacy_raw(name)


# -- production codec: exact byte/hash round trip for absent, present-empty and present-nonempty ----------------------


@pytest.mark.parametrize("name", sorted(LEGACY["states"]))
def test_absent_snapshot_round_trips_exactly_through_unpack_runtime(name):
    raw = legacy_raw(name)
    rt = unpack(raw)
    assert rt.core._deps_known is False and rt.core._deps == ()
    assert canonical(rt.encode()) == raw
    assert engine.pack_runtime(rt)[1] == LEGACY["states"][name]["sha256"]
    assert "deps" not in json.loads(canonical(rt.encode()))["core"]["v3"]


def test_present_empty_and_present_nonempty_snapshots_round_trip_and_differ_from_absent():
    rt = new_runtime()
    empty = canonical(rt.encode())
    assert json.loads(empty)["core"]["v3"]["deps"] == []
    absent = json.loads(empty)
    del absent["core"]["v3"]["deps"]
    absent = canonical(absent)
    for raw in (empty, absent, REF_STATES["before_0400"]["raw"], REF_STATES["before_0500"]["raw"]):
        out = unpack(raw)
        assert canonical(out.encode()) == raw and engine.pack_runtime(out)[1] == hashlib.sha256(raw).hexdigest()
    assert hashlib.sha256(empty).digest() != hashlib.sha256(absent).digest()
    assert unpack(empty).core._deps_known is True and unpack(absent).core._deps_known is False


# -- continuation: honest new snapshot, no invented metadata ----------------------------------------------------------


@pytest.mark.parametrize("name", ["before_0400", "before_0500"])
def test_legacy_restore_continues_identically_and_then_writes_the_recomputed_snapshot(name):
    journal, records, (i, doc) = continue_from(unpack(legacy_raw(name)), name)
    assert [e["digest"] for e in journal] == [e["digest"] for e in REF_J]
    assert [x["digest"] for x in records] == [x["digest"] for x in REF_R]
    # after the first genuine dispatch the state carries the recomputed snapshot: equal to the uninterrupted fold's
    ref = reference({i + 1: "x"})[2]["x"]
    assert doc["core"]["v3"]["deps"] and canonical(doc) == ref["raw"]


def test_legacy_restore_inside_0400_only_lacks_the_unknowable_first_dispatch_metadata():
    """The 04:00 dispatch emits 1h landmarks during sealed ingestion, BEFORE it recomputes the snapshot; their envelope
    would carry the previous dispatch's snapshot, which the legacy state does not contain. They are emitted with no
    dependencies (not invented); everything else, every evaluator record and the later snapshot are exact."""
    journal, records, (_, doc) = continue_from(unpack(legacy_raw("inside_0400")), "inside_0400")
    assert [x["digest"] for x in records] == [x["digest"] for x in REF_R]
    assert len(journal) == len(REF_J)
    differ = [(a, b) for a, b in zip(journal, REF_J) if a["digest"] != b["digest"]]
    assert differ
    for a, b in differ:
        assert a["kind"] == "landmark" and a["clock_time"] == "2025-09-01T04:00:00Z"
        assert a["record"]["env"]["dependencies"] == [] and b["record"]["env"]["dependencies"]
        ra, rb = dict(a["record"]), dict(b["record"])
        ra["env"] = {k: v for k, v in ra["env"].items() if k != "dependencies"}
        rb["env"] = {k: v for k, v in rb["env"].items() if k != "dependencies"}
        assert ra == rb
    assert doc["core"]["v3"]["deps"]


# -- integrity guards unchanged ---------------------------------------------------------------------------------------


def _tamper(name, f):
    doc = json.loads(legacy_raw(name))
    f(doc)
    return canonical(doc)


@pytest.mark.parametrize("case,match", [
    ("wrong_sha", "SHA-256 mismatch"),
    ("corrupt_bytes", "not decompressible"),
    ("unknown_v3_key", "round-trip exactly"),
    ("deps_null", "does not decode"),
    ("deps_bad_entry", "does not decode"),
    ("deps_noncanonical_time", "round-trip exactly"),
    ("v02_state_under_v03", "does not decode"),
])
def test_corrupt_wrong_or_incompatible_states_still_fail(case, match):
    raw = legacy_raw("before_0500")
    b, sha = blob(raw)
    if case == "wrong_sha":
        sha = hashlib.sha256(raw + b" ").hexdigest()
    elif case == "corrupt_bytes":
        b = b[:-7] + b"garbage"
    else:
        dep = json.loads(REF_STATES["before_0500"]["raw"])["core"]["v3"]["deps"][0]
        bad = {
            "unknown_v3_key": lambda d: d["core"]["v3"].__setitem__("extra", 1),
            "deps_null": lambda d: d["core"]["v3"].__setitem__("deps", None),
            "deps_bad_entry": lambda d: d["core"]["v3"].__setitem__("deps", [{"name": "trade.15m"}]),
            "deps_noncanonical_time": lambda d: d["core"]["v3"].__setitem__(
                "deps", [{**dep, "known_at": dep["known_at"].replace("Z", "+00:00")}]),
        }
        if case == "v02_state_under_v03":
            raw = canonical(new_runtime("v0.2").encode())
        else:
            raw = _tamper("before_0500", bad[case])
        b, sha = blob(raw)
    with pytest.raises(engine.AdviserStateError, match=match):
        engine.unpack_runtime(b, sha, ENGINE)


# -- new snapshots: direct restore through the production codec around hourly boundaries -----------------------------


@pytest.mark.parametrize("window", [(T(3, 59), T(4, 2)), (T(4, 59), T(5, 2)), (T(5, 59), T(6, 2))],
                         ids=["around_04", "around_05", "around_06"])
def test_new_snapshot_production_restore_is_exact_around_hourly_boundaries(window):
    lo, hi = window
    cuts = {i for i, e in enumerate(EVENTS) if lo <= e.available_time <= hi}
    assert len(cuts) >= 3
    rt, temporal = new_runtime(), temporal_for(COV)
    rt.attach(temporal)
    journal, records = [], []
    for i, e in enumerate(EVENTS):
        if i in cuts:
            j, r = rt.take()
            journal += j
            records += r
            temporal = te.unpack(*te.pack(temporal))
            b, sha = engine.pack_runtime(rt)
            rt = engine.unpack_runtime(b, sha, ENGINE)
            assert "deps" in json.loads(canonical(rt.encode()))["core"]["v3"]
            rt.attach(temporal)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    temporal.finish(END)
    rt.finish(END)
    j, r = rt.take()
    assert [e["digest"] for e in journal + j] == [e["digest"] for e in REF_J]
    assert [x["digest"] for x in records + r] == [x["digest"] for x in REF_R]
