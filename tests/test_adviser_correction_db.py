"""WP-009 correction, findings 6-7 (DB, offline hand fixtures through the durable worker; engineering checks only).

6. Historical inspection never exposes the uncommitted suffix: the price window is clamped to the run's committed
   factual frontier (running, paused, failed, completed), rejects future cursors, verifies the pinned cache, and
   call/revision/outcome inspection honours a requested cutoff (no later record under an earlier cutoff).
7. Deep v5 re-hashes the STORED professional record bytes: record-only alteration with an unchanged digest, a
   consistently rewritten digest/chain, missing and extra rows (journal and evaluation tables), a resumed validation
   and an incompatible implementation identity all fail/mismatch; never MATCH on unverified bytes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import pytest
from adviser_db import fake_from, journal, prepare_pack, records, replay, run_all, worker, write_presets
from adviser_fixtures import a_fixture
from fastapi.testclient import TestClient
from pack_fixtures import connect
from psycopg.types.json import Jsonb

from algotrader.api import create_app
from algotrader.feed.ordering import canonical
from algotrader.observe import control, deep
from algotrader.observe.contracts import SourceKind

pytestmark = pytest.mark.db


def _prepared(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    pack = prepare_pack(database_url, root, fake_from(a_fixture()))
    return root, art, pack


def _launch(database_url, root, pack):
    with connect(database_url) as c:
        return control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], 0, False,
                                     expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation")


def _committed(database_url, rid):
    with connect(database_url) as c:
        row = c.execute("SELECT cursor FROM observation_checkpoints WHERE replay_id = %s", (rid,)).fetchone()
    return row["cursor"] if row else 0


def _api(database_url, art, root, tmp_path):
    return TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))


# -- finding 6 -------------------------------------------------------------------------------------------------------

def test_window_is_clamped_to_the_committed_frontier_while_running_paused_and_completed(database_url, tmp_path,
                                                                                         monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    api = _api(database_url, art, root, tmp_path)
    seen = {}

    def during(replay_id, cursor):  # RUNNING: inspected right after a commit, before any later work
        if "running" not in seen and cursor >= 1000:
            committed = _committed(database_url, replay_id)
            r = api.get(f"/api/adviser/runs/{replay_id}/window", params={"cursor": committed, "before": 5,
                                                                          "after": 500}).json()
            seen["running"] = (committed, r)
            assert api.get(f"/api/adviser/runs/{replay_id}/window",
                           params={"cursor": committed + 1}).status_code == 409
        if cursor >= 2000:
            with connect(database_url) as c:
                control.pause(c, replay_id)

    run_all(worker(database_url, root, art, "observe:w1", checkpoint_events=500, after_commit=during))
    committed, r = seen["running"]
    assert r["range"] == [committed - 5, committed] and r["committed_cursor"] == committed
    assert len(r["bars"]) <= 5
    # PAUSED
    assert replay(database_url, rid)["status"] == "paused"
    pc = _committed(database_url, rid)
    r = api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": pc, "before": 0, "after": 50}).json()
    assert r["bars"] == [] and r["range"] == [pc, pc]  # Director probe shape: nothing uncommitted
    assert api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": pc + 1}).status_code == 409
    assert api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": -1}).status_code == 422
    assert api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": 5, "after": -1}).status_code == 422
    # COMPLETED: the exact end boundary is the committed total
    with connect(database_url) as c:
        control.resume(c, rid)
    run_all(worker(database_url, root, art, "observe:w2", checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed"
    total = _committed(database_url, rid)
    r = api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": total, "before": 3, "after": 6000}).json()
    assert r["range"] == [total - 3, total]
    assert api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": total + 1}).status_code == 409
    # source tamper: an altered pinned cache partition is refused, never served
    from algotrader.observe.feedcache import open_cache

    eng = row["engine"]
    cache = open_cache(root, eng["cache_id"], expected_manifest_sha256=eng["cache_manifest_sha256"])
    part = cache.path / cache.partitions[-1]["file"]
    blob = bytearray(part.read_bytes())
    blob[-5] ^= 0xFF
    part.write_bytes(bytes(blob))
    assert api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": total, "before": 3}).status_code == 409


def test_failed_run_window_stays_within_its_committed_prefix(database_url, tmp_path, monkeypatch):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)

    def boom(replay_id, cursor):
        if cursor >= 1500:
            raise RuntimeError("fixture failure after a commit")

    w = worker(database_url, root, art, "observe:w3", checkpoint_events=500, after_commit=boom)
    try:
        run_all(w)
    except RuntimeError:
        pass
    row = replay(database_url, rid)
    if row["status"] != "failed":
        with connect(database_url) as c:  # a worker that propagates the error leaves the lease; mark explicitly
            c.execute("UPDATE observation_replays SET status = 'failed', error = 'fixture' WHERE replay_id = %s", (rid,))
            c.commit()
    api = _api(database_url, art, root, tmp_path)
    fc = _committed(database_url, rid)
    assert fc >= 1500
    r = api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": fc, "before": 10, "after": 1000}).json()
    assert r["range"] == [fc - 10, fc]
    assert api.get(f"/api/adviser/runs/{rid}/window", params={"cursor": fc + 1}).status_code == 409


def _completed(database_url, tmp_path, monkeypatch, wid="observe:c"):
    root, art, pack = _prepared(database_url, tmp_path, monkeypatch)
    rid = _launch(database_url, root, pack)
    w = worker(database_url, root, art, wid, checkpoint_events=700)
    run_all(w)
    assert replay(database_url, rid)["status"] == "completed"
    return root, art, rid, w


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_call_journal_and_outcome_inspection_honour_a_requested_cutoff(database_url, tmp_path, monkeypatch):
    root, art, rid, _ = _completed(database_url, tmp_path, monkeypatch)
    api = _api(database_url, art, root, tmp_path)
    full = api.get(f"/api/adviser/runs/{rid}/calls").json()
    [c] = full["calls"]
    issued = _ts(c["call"]["issued_at"])
    cid = c["call"]["call_id"]
    paths = c["hypothetical_paths"]
    assert paths and all(p["resolved_at"] for p in paths)
    before = api.get(f"/api/adviser/runs/{rid}/calls", params={"cutoff": (issued - timedelta(seconds=1)).isoformat()})
    assert before.json()["calls"] == []
    assert api.get(f"/api/adviser/runs/{rid}/calls/{cid}",
                   params={"cutoff": (issued - timedelta(seconds=1)).isoformat()}).status_code == 404
    at = api.get(f"/api/adviser/runs/{rid}/calls/{cid}", params={"cutoff": issued.isoformat()}).json()
    assert at["call"]["call_id"] == cid
    assert all(_ts(r["env"]["published_at"]) <= issued for r in at["revisions"])
    assert at["hypothetical_paths"] == [] and at["hypothetical_paths_withheld_at_cutoff"] == len(paths)
    last = max(_ts(p["resolved_at"]) for p in paths)
    after = api.get(f"/api/adviser/runs/{rid}/calls/{cid}", params={"cutoff": last.isoformat()}).json()
    assert len(after["hypothetical_paths"]) == len(paths) and after["hypothetical_paths_withheld_at_cutoff"] == 0
    assert len(after["revisions"]) >= len(at["revisions"])
    page = api.get(f"/api/adviser/journal/{rid}", params={"cutoff": issued.isoformat(), "limit": 2000}).json()
    assert page["records"] and all(_ts(x["clock_time"]) <= issued for x in page["records"])


# -- finding 7 -------------------------------------------------------------------------------------------------------

def _deep(database_url, w, rid, pause_first=False):
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, rid)
        if pause_first:
            deep.control(c, vid, "pause")
    run_all(w)
    if pause_first:
        with connect(database_url) as c:
            st = c.execute("SELECT status FROM observation_deep_validations WHERE validation_id = %s",
                           (vid,)).fetchone()["status"]
            assert st == "paused"
            deep.control(c, vid, "resume")
        run_all(w)
    with connect(database_url) as c:
        return c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()


def _kinds(v):
    return {m["kind"] for m in (v["result"] or {}).get("mismatches", [])}


def _set_record(database_url, table, rid, seq, record, digest=None, chain=None):
    with connect(database_url) as c:
        c.execute(f"UPDATE {table} SET record = %s" + (", digest = %s, chain = %s" if digest else "")
                  + " WHERE run_id = %s AND seq = %s",
                  (Jsonb(record), *((digest, chain) if digest else ()), rid, seq))
        c.commit()


def test_deep_v5_rehashes_stored_bytes_and_detects_every_alteration(database_url, tmp_path, monkeypatch):
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:d")
    v = _deep(database_url, w, rid)
    assert v["status"] == "completed" and v["result"]["outcome"] == "match", v["result"]["mismatches"]
    assert v["result"]["validator_version"] == "6"
    j = journal(database_url, rid)
    ev = records(database_url, rid)
    # (a) record-only alteration, stored digest/chain unchanged (Director probe) - journal and evaluation tables
    for table, rows in (("adviser_journal", j), ("adviser_evaluation_records", ev)):
        orig = rows[2]
        _set_record(database_url, table, rid, orig["seq"], {**orig["record"], "tampered": True})
        v = _deep(database_url, w, rid)
        assert v["result"]["outcome"] == "mismatch", table
        assert {f"{table}_stored_bytes", f"{table}_record"} <= _kinds(v), _kinds(v)
        _set_record(database_url, table, rid, orig["seq"], orig["record"])
    # (b) the last journal record rewritten with a CONSISTENT digest and chain: storage checks pass, the regenerated
    # record still differs
    last, prev = j[-1], j[-2]
    altered = {**last["record"], "tampered": True}
    d = hashlib.sha256(canonical(altered)).hexdigest()
    ch = hashlib.sha256(bytes.fromhex(prev["chain"]) + bytes.fromhex(d)).hexdigest()
    _set_record(database_url, "adviser_journal", rid, last["seq"], altered, d, ch)
    v = _deep(database_url, w, rid)
    assert "adviser_journal_record" in _kinds(v) and "adviser_journal_stored_bytes" not in _kinds(v)
    _set_record(database_url, "adviser_journal", rid, last["seq"], last["record"], last["digest"], last["chain"])
    # (c) a missing stored row and (d) an extra stored row
    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_journal WHERE run_id = %s AND seq = %s", (rid, last["seq"]))
        c.commit()
    v = _deep(database_url, w, rid)
    assert v["result"]["outcome"] == "mismatch" and "adviser_journal_record" in _kinds(v)
    with connect(database_url) as c:
        cols = [k for k in last if k not in ("committed_at",)]
        c.execute(f"INSERT INTO adviser_journal ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                  [Jsonb(last[k]) if k == "record" else last[k] for k in cols])
        extra = {**last, "seq": last["seq"] + 1, "record_id": "extra"}
        ed = last["digest"]
        extra["chain"] = hashlib.sha256(bytes.fromhex(last["chain"]) + bytes.fromhex(ed)).hexdigest()
        c.execute(f"INSERT INTO adviser_journal ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                  [Jsonb(extra[k]) if k == "record" else extra[k] for k in cols])
        c.commit()
    v = _deep(database_url, w, rid)
    assert "adviser_journal_extra_stored" in _kinds(v)
    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_journal WHERE run_id = %s AND seq = %s", (rid, extra["seq"]))
        c.commit()
    v = _deep(database_url, w, rid)
    assert v["result"]["outcome"] == "match", v["result"]["mismatches"]  # restored bytes match again


def test_deep_v5_keeps_stored_byte_mismatches_across_a_paused_and_resumed_validation(database_url, tmp_path,
                                                                                      monkeypatch):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 400)
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:e")
    orig = journal(database_url, rid)[4]
    _set_record(database_url, "adviser_journal", rid, orig["seq"], {**orig["record"], "tampered": 1})
    v = _deep(database_url, w, rid, pause_first=True)
    assert v["status"] == "completed" and v["result"]["outcome"] == "mismatch"
    assert "adviser_journal_stored_bytes" in _kinds(v)


# -- finding 7 follow-up: storage changed while a CLEAN validation is paused ------------------------------------------

def _paused_clean(database_url, w, rid):
    """Launch, park at the first save boundary (nonzero cursor) with no mismatch saved, return the validation id."""
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, rid)
        deep.control(c, vid, "pause")
    run_all(w)
    with connect(database_url) as c:
        v = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    assert v["status"] == "paused" and 0 < v["resume_cursor"] < v["plan"]["committed_cursor"], v["resume_cursor"]
    assert v["comparisons"]["mismatches"] == [] and v["comparisons"]["compared"] > 0
    return vid


def _resume(database_url, w, vid):
    with connect(database_url) as c:
        deep.control(c, vid, "resume")
    run_all(w)
    with connect(database_url) as c:
        return c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()


def _set_meta(database_url, table, rid, seq, **cols):
    with connect(database_url) as c:
        c.execute(f"UPDATE {table} SET " + ", ".join(f"{k} = %s" for k in cols) + " WHERE run_id = %s AND seq = %s",
                  (*cols.values(), rid, seq))
        c.commit()


@pytest.mark.parametrize("table", ["adviser_journal", "adviser_evaluation_records"])
def test_resumed_deep_keeps_a_digest_only_alteration_made_while_a_clean_validation_was_paused(
        database_url, tmp_path, monkeypatch, table):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 400)
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:g")
    rows = journal(database_url, rid) if table == "adviser_journal" else records(database_url, rid)
    orig = rows[1]
    vid = _paused_clean(database_url, w, rid)
    # digest column only: record bytes and chain unchanged, so the regenerated record still equals the recomputation
    _set_meta(database_url, table, rid, orig["seq"], digest="f" * 64)
    v = _resume(database_url, w, vid)
    assert v["status"] == "completed" and v["result"]["outcome"] == "mismatch", v["result"]
    bad = [m for m in v["result"]["mismatches"] if m["kind"] == f"{table}_stored_bytes"]
    assert len(bad) == 1 and bad[0]["at"] == f"seq {orig['seq']}" and bad[0]["expected"] == "f" * 64
    notes = [n for n in v["diagnostic_log"] if n.get("event") == "deep_resume_stored_recheck"]
    assert notes and notes[-1]["new_problems"] == 1, v["diagnostic_log"]


def test_resumed_deep_keeps_a_last_row_chain_only_alteration_made_while_paused(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 400)
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:h")
    for table, rows in (("adviser_journal", journal(database_url, rid)),
                        ("adviser_evaluation_records", records(database_url, rid))):
        last = rows[-1]
        vid = _paused_clean(database_url, w, rid)
        _set_meta(database_url, table, rid, last["seq"], chain="e" * 64)
        v = _resume(database_url, w, vid)
        assert v["status"] == "completed" and v["result"]["outcome"] == "mismatch", (table, v["result"])
        assert [m["at"] for m in v["result"]["mismatches"] if m["kind"] == f"{table}_stored_chain"] ==             [f"seq {last['seq']}"]
        _set_meta(database_url, table, rid, last["seq"], chain=last["chain"])
    v = _deep(database_url, w, rid)
    assert v["result"]["outcome"] == "match", v["result"]["mismatches"]  # restored storage matches again


def test_repeated_resumes_over_altered_storage_record_each_problem_once(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 300)
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:i")
    orig = journal(database_url, rid)[1]
    vid = _paused_clean(database_url, w, rid)
    _set_meta(database_url, "adviser_journal", rid, orig["seq"], digest="f" * 64)
    parks = 0
    for _ in range(3):  # resume and immediately park again at the next save boundary
        with connect(database_url) as c:
            deep.control(c, vid, "resume")
            deep.control(c, vid, "pause")
        run_all(w)
        with connect(database_url) as c:
            v = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
        if v["status"] != "paused":
            break
        parks += 1
        assert [m["kind"] for m in v["comparisons"]["mismatches"]] == ["adviser_journal_stored_bytes"]
    assert parks >= 2
    v = _resume(database_url, w, vid) if v["status"] == "paused" else v
    assert v["result"]["outcome"] == "mismatch"
    assert [m["kind"] for m in v["result"]["mismatches"]] == ["adviser_journal_stored_bytes"]


def test_clean_paused_and_resumed_deep_reports_the_uninterrupted_result(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(deep, "SAVE_EVENTS", 300)
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:j")
    straight = _deep(database_url, w, rid)["result"]
    vid = _paused_clean(database_url, w, rid)
    v = _resume(database_url, w, vid)
    assert straight["outcome"] == v["result"]["outcome"] == "match", v["result"]["mismatches"]
    keys = ("validator_version", "scope", "covered_events", "target_events", "comparison_cursors", "mismatches")
    assert {k: straight[k] for k in keys} == {k: v["result"][k] for k in keys}


def test_deep_refuses_a_run_pinned_to_a_different_implementation_identity(database_url, tmp_path, monkeypatch):
    root, art, rid, w = _completed(database_url, tmp_path, monkeypatch, "observe:f")
    with connect(database_url) as c:
        eng = c.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
        eng["adviser"]["identity"]["implementation"] = "adviser.core.v1"
        c.execute("UPDATE observation_replays SET engine = %s WHERE replay_id = %s", (Jsonb(eng), rid))
        c.commit()
    v = _deep(database_url, w, rid)
    assert v["status"] == "failed" and "different method implementation identity" in v["error"]
    assert v["result"] is None or v["result"].get("outcome") != "match"


_ = json
