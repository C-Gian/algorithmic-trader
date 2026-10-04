"""WP-009 durable integration (DB): adviser evaluation over a real receipt-pinned pack prepared offline from hand
fixtures, through the observation worker (engine observe.stream.v3). Engineering checks only."""

from __future__ import annotations

import pytest
from adviser_db import (
    EV_END,
    EV_START,
    fake_from,
    journal,
    prepare_pack,
    records,
    replay,
    run_all,
    worker,
    write_presets,
)
from adviser_fixtures import DAY1, a_fixture
from pack_fixtures import connect

from algotrader.adviser.harness import run_pure
from algotrader.observe import control
from algotrader.observe.contracts import SourceKind

pytestmark = pytest.mark.db


def _launch(database_url, root, pack, paused=False, speed=0):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], speed, paused,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation")


def _decisions(entries):
    out = []
    for e in entries:
        r = e["record"]
        if e["kind"] == "call":
            out.append(("call", r["call_id"], r["invalidation"], r["target"], tuple(r["structural_area"])))
        elif e["kind"] == "call_revision":
            out.append(("rev", r["call_id"], r["revision"], r["entry_status"], r["thesis_status"]))
        elif e["kind"] == "candidate":
            out.append(("cand", r["attempt_id"], r["transition"], r["reason"]))
    return out


def test_adviser_evaluation_over_a_pack_matches_the_pure_fold(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    mins = a_fixture()
    pack = prepare_pack(database_url, root, fake_from(mins))
    rid = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed", row["error"]
    assert row["engine_format"] == "observe.stream.v3"
    assert row["assurance"]["state"] == "passed", [c for c in row["manifest"]["validation"]["checks"] if not c["passed"]]
    j = journal(database_url, rid)
    pure = run_pure(DAY1, mins[:int((EV_END - DAY1).total_seconds() // 60) + 365],
                    eval_start=EV_START, eval_end=EV_END)
    assert _decisions(j) == _decisions(pure.journal)
    assert [r["record"] for r in records(database_url, rid) if r["kind"] == "path"] == pure.paths()
    calls = [e["record"] for e in j if e["kind"] == "call"]
    assert len(calls) == 1 and calls[0]["target"] == "100798.5"
    names = {c["name"]: c["passed"] for c in row["manifest"]["validation"]["checks"]}
    assert names["adviser_journal_chain"] and names["adviser_finish_rederived"] and names["adviser_lineage_immutability"]
