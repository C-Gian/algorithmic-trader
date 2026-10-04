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
from algotrader.observe.job import SimulatedCrash

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


def _signature(database_url, rid):
    """Every committed professional output + the finish commitment (identity of the semantic outcome)."""
    with connect(database_url) as c:
        fin = c.execute("SELECT commitment FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
    return ([e["digest"] for e in journal(database_url, rid)], [r["digest"] for r in records(database_url, rid)],
            {k: v for k, v in (fin or {}).get("commitment", {}).items()})


def _prepared(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    pack = prepare_pack(database_url, root, fake_from(a_fixture()))
    return root, art, pack


def crash_once_after(rid, at):
    fired = {"done": False}

    def hook(replay_id, cursor):
        if replay_id == rid and cursor >= at and not fired["done"]:
            fired["done"] = True
            raise SimulatedCrash()
    return hook


def test_checkpoint_cadence_step_paced_and_crash_recovery_give_identical_outputs(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    base = _launch(database_url, root, pack)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    assert replay(database_url, base)["status"] == "completed"
    want = _signature(database_url, base)
    assert want[0] and want[1] and want[2]
    # cadence 7 with a hard crash right after a commit in the middle of the run, then reclaim by another worker
    rid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:b", checkpoint_events=7,
                       after_commit=crash_once_after(rid, 3500)))
    with connect(database_url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))
    run_all(worker(database_url, root, art, "observe:c", checkpoint_events=7))
    r = replay(database_url, rid)
    assert r["status"] == "completed" and r["assurance"]["state"] == "passed", r["error"]
    assert _signature(database_url, rid) == want
    # single-event STEP commits (cadence 1) over a prefix, then paced resume (pacing sleeps are no-ops here)
    sid = _launch(database_url, root, pack, paused=True, speed=400)
    w = worker(database_url, root, art, "observe:d", checkpoint_events=13)
    run_all(w)
    with connect(database_url) as c:
        for _ in range(40):
            control.step(c, sid)
            run_all(w)
        assert c.execute("SELECT cursor FROM observation_checkpoints WHERE replay_id = %s", (sid,)).fetchone()[
            "cursor"] == 40
        control.resume(c, sid)
    run_all(w)
    assert replay(database_url, sid)["status"] == "completed"
    assert _signature(database_url, sid) == want


def test_restore_fallback_verifies_regenerated_journal_without_duplicates(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    with pytest.raises(SimulatedCrash):
        run_all(worker(database_url, root, art, "observe:e", checkpoint_events=500,
                       after_commit=crash_once_after(rid, 5000)))
    with connect(database_url) as c:
        # corrupt the newest restore point's professional state: restore must fall back and reprocess the suffix
        c.execute("UPDATE observation_restore_points SET adviser_blob = 'x'::bytea WHERE replay_id = %s AND cursor = "
                  "(SELECT max(cursor) FROM observation_restore_points WHERE replay_id = %s)", (rid, rid))
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))
    run_all(worker(database_url, root, art, "observe:f", checkpoint_events=500))
    r = replay(database_url, rid)
    assert r["status"] == "completed", r["error"]
    assert any(e["event"] == "restore_fallback" for e in r["diagnostic_log"])
    m = r["metrics"]
    assert any(v.get("adviser_records_verified", 0) > 0 or v.get("restore_suffix_events", 0) > 0 for v in m.values())
    seqs = [e["seq"] for e in journal(database_url, rid)]
    assert seqs == list(range(1, len(seqs) + 1))  # no duplicates, no gaps
    assert r["assurance"]["state"] == "passed"


def test_cancel_during_replay_is_incomplete_and_the_report_is_copyable(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)

    def cancel_at(replay_id, cursor):
        if cursor >= 2000:
            with connect(database_url) as c:
                c.execute("UPDATE observation_replays SET cancel_requested = true WHERE replay_id = %s", (replay_id,))
    run_all(worker(database_url, root, art, "observe:g", checkpoint_events=500, after_commit=cancel_at))
    r = replay(database_url, rid)
    assert r["status"] == "cancelled" and r["assurance"]["state"] == "incomplete"
    with connect(database_url) as c:
        assert c.execute("SELECT 1 FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone() is None


def test_deep_v4_matches_a_completed_adviser_run_and_detects_journal_tamper(database_url, tmp_path, monkeypatch):
    from algotrader.observe import deep

    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    w = worker(database_url, root, art, "observe:h", checkpoint_events=700)
    run_all(w)
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, rid)
    run_all(w)
    with connect(database_url) as c:
        v = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    assert v["status"] == "completed", v["error"]
    res = v["result"]
    assert res["outcome"] == "match" and res["validator_version"] == "4", res["mismatches"]
    assert res["temporal"]["terminal"]["adviser"]["compared"] is True
    with connect(database_url) as c:
        c.execute("UPDATE adviser_journal SET digest = repeat('0', 64) WHERE run_id = %s AND seq = 3", (rid,))
        vid2 = deep.create_deep_validation(c, rid)
    run_all(w)
    with connect(database_url) as c:
        v2 = c.execute("SELECT result FROM observation_deep_validations WHERE validation_id = %s", (vid2,)).fetchone()
    assert v2["result"]["outcome"] == "mismatch"
    assert any(m["kind"] == "adviser_journal_record" for m in v2["result"]["mismatches"])
