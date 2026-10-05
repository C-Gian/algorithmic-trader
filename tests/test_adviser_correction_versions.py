"""WP-009 correction, version discipline (DB): an unfinished adviser evaluation pinned to the pre-correction
implementation identity cannot resume under the corrected semantics - it is surfaced as an explicit failure, never
silently continued or restarted; its committed outputs are preserved and remain readable."""

from __future__ import annotations

import pytest
from adviser_db import fake_from, journal, prepare_pack, replay, run_all, worker, write_presets
from adviser_fixtures import a_fixture
from pack_fixtures import connect
from psycopg.types.json import Jsonb

from algotrader.adviser.identity import IMPLEMENTATION_ID
from algotrader.observe import control
from algotrader.observe.contracts import SourceKind

pytestmark = pytest.mark.db


def test_unfinished_run_with_the_old_implementation_identity_fails_explicitly(database_url, tmp_path, monkeypatch):
    assert IMPLEMENTATION_ID == "adviser.core.v2"
    write_presets(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    pack = prepare_pack(database_url, root, fake_from(a_fixture()))
    with connect(database_url) as c:
        rid = control.create_replay(c, root, SourceKind.PACK, pack["pack_id"], 0, False,
                                    expected_manifest_sha256=pack["manifest_sha256"], run_type="adviser_evaluation")

    def pause_at(replay_id, cursor):
        if cursor >= 1500:
            with connect(database_url) as c:
                control.pause(c, replay_id)

    run_all(worker(database_url, root, art, "observe:v1", checkpoint_events=500, after_commit=pause_at))
    assert replay(database_url, rid)["status"] == "paused"
    before = [e["digest"] for e in journal(database_url, rid)]
    with connect(database_url) as c:  # simulate a run prepared by the pre-correction release
        eng = c.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
        eng["adviser"]["identity"]["implementation"] = "adviser.core.v1"
        c.execute("UPDATE observation_replays SET engine = %s WHERE replay_id = %s", (Jsonb(eng), rid))
        c.commit()
        control.resume(c, rid)
    run_all(worker(database_url, root, art, "observe:v2", checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "failed", (row["status"], row["error"])
    assert "INCOMPATIBLE_ADVISER_IDENTITY" in (row["error"] or "") and "adviser.core.v1" in row["error"]
    assert [e["digest"] for e in journal(database_url, rid)] == before  # committed outputs preserved, nothing added
