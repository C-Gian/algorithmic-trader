"""A v0.6 study path, durable and through the app API (DB; synthetic engineering inputs only, never market data or the
real study window). A tiny registered study window (``study_fixtures``: outside the fixture target, not on calendar
months, crossing the Aug/Sep 2025 month boundary) is prepared by the real pack job, launched as the only admitted run
(adviser v0.6), executed by the observation worker and exported GET-only into the study ledger.

Hand-expected facts of the tape (pure fold checked first): one A LONG RETURN call issued 04:03 on DAY2, inside the
window [DAY1 22:00, DAY2 04:30); its PRIMARY path closes at 06:03 (GUIDANCE_RETIRED, price_net -0.0014), inside the
tail [04:30, 10:35); the owner is born 03:30 and confirmed 04:01, both inside the window."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from datetime import timedelta
from pathlib import Path

import pytest
import study_fixtures as sf
from adviser_db import fake_from, journal, replay, run_all, worker
from fastapi.testclient import TestClient
from pack_fixtures import connect, corpus_worker, drain
from test_mp004_db import _expire_lease, _signature, _strip, crash_once_after

from algotrader.adviser.harness import run_pure
from algotrader.api import create_app
from algotrader.observe import control
from algotrader.observe.job import SimulatedCrash

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("a_v06_study_ledger", ROOT / "scripts" / "a_v06_study_ledger.py")
lg = importlib.util.module_from_spec(_spec)
sys.modules["a_v06_study_ledger"] = lg
_spec.loader.exec_module(lg)

EV_PER_MIN = 3  # trade + mark + index per minute (no funding rows in this tape)
CALL = "call-AL-2025-09-01T04:03:00+00:00-33d5d0d48b6a"


def _cursor(t) -> int:
    return EV_PER_MIN * int((t - sf.DAY1) / timedelta(minutes=1))


def _app(database_url, tmp_path, monkeypatch):
    sf.write_files(tmp_path, monkeypatch)
    root, art = tmp_path / "data", tmp_path / "art"
    return root, art, TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))


def _prepare(api, database_url, root) -> str:
    listed = {p["preset"]["preset_id"]: p for p in api.get("/api/corpus/presets").json()["presets"]}
    view = listed[sf.STUDY_PRESET_ID]
    assert view["classification"]["label"] == "REGISTERED_STUDY_WINDOW" and view["study"]["method"] == "v0.6"
    assert view["windows"]["initialization"]["evaluated"] is False
    r = api.post(f"/api/corpus/presets/{sf.STUDY_PRESET_ID}/prepare")
    assert r.status_code == 201, r.text
    drain(corpus_worker(database_url, root, fake_from(sf.tape(), start=sf.DAY1)))
    packs = [p for p in api.get("/api/corpus/packs").json() if p["preset_id"] == sf.STUDY_PRESET_ID]
    assert len(packs) == 1 and packs[0]["status"] == "READY", packs
    return packs[0]["pack_id"]


def _launch(api, pack_id: str) -> tuple[str, str]:
    r = api.post("/api/evaluations", json={"pack_id": pack_id, "run_type": "adviser_evaluation", "method": "v0.6"})
    assert r.status_code == 201, r.text
    return r.json()["evaluation_id"], r.json()["replay"]["replay_id"]


def test_study_window_end_to_end_prepared_launched_and_ledgered(database_url, tmp_path, monkeypatch):
    root, art, api = _app(database_url, tmp_path, monkeypatch)
    pure = run_pure(sf.DAY1, sf.tape(), eval_start=sf.EV_START, eval_end=sf.EV_END, method="v0.6")
    assert [e["record"]["call_id"] for e in pure.journal if e["kind"] == "call"] == [CALL]
    # a month-builder selection or an unregistered shift of the study window stays refused
    assert api.get("/api/corpus/selection", params={"months": "2025-08,2025-09"}).status_code == 422
    pack_id = _prepare(api, database_url, root)
    for body in ({"run_type": "observation_only"}, {"run_type": "adviser_evaluation"},
                 {"run_type": "adviser_evaluation", "method": "v0.5"}):
        r = api.post("/api/evaluations", json={"pack_id": pack_id, **body})
        assert r.status_code == 409 and "admits only an adviser evaluation with method v0.6" in r.text, body
    eid, rid = _launch(api, pack_id)
    run_all(worker(database_url, root, art, "observe:s", checkpoint_events=500))
    row = replay(database_url, rid)
    assert row["status"] == "completed" and row["assurance"]["state"] == "passed", row["error"]
    assert [(e["kind"], _strip(e["record"])) for e in journal(database_url, rid)] == \
        [(e["kind"], _strip(e["record"])) for e in pure.journal]  # one continuous fold: no monthly reset
    rep = api.get(f"/api/evaluations/{eid}/report.json").json()
    adv = rep["adviser"]
    assert adv["windows"]["evaluation"] == [sf.EV_START.isoformat(), sf.EV_END.isoformat()]
    assert adv["launch_pins"]["method"] == "v0.6" and adv["launch_pins"]["primary_is_60s"] is True
    assert rep["pack"]["evidence_classes"]["label"] == "REGISTERED_STUDY_WINDOW"
    months = adv["periods"]["months"]
    assert list(months) == ["2025-08", "2025-09"] and adv["periods"]["reconciliation"]["all_passed"]

    exp = tmp_path / "export"
    lg.export(lambda p, q: api.get(p, params=q).json(), eid, exp)
    doc = lg.run_ledger(exp, tmp_path / "ledger", mode="SYNTHETIC")
    assert doc["mode"] == "SYNTHETIC" and doc["identities"]["all_match"], doc["identities"]
    assert doc["measure"] == "price_net" and doc["funding_outcomes"] == "PRICE_NET_ONLY"
    (c,) = doc["calls"]
    assert (c["call_id"], c["primary"], c["class"], c["value"], c["primary_status"]) == (
        CALL, True, "DETERMINED", "-0.0014", "CLOSED")
    assert c["resolved_in_tail"] and c["resolved_at"] == "2025-09-01T06:03:00Z" and c["issue_hour"] == \
        "2025-09-01T04:00:00Z"
    assert doc["windows"]["hours"] == 7 == len(doc["hours"])  # [22:00, 04:30) -> 6.5 h -> 7 hourly grid points
    by_hour = {h["hour"]: h for h in doc["hours"]}
    assert by_hour["2025-09-01T04:00:00Z"]["value"] == "-0.0014"
    assert all(h["value"] == "0" and h["status"] == "NO_CALL_ZERO" for k, h in by_hour.items()
               if k != "2025-09-01T04:00:00Z")
    assert doc["balance"] == {**doc["balance"], "status": "COMPLETE", "complete_balance": "-0.0014"}
    assert doc["population"]["resolved_in_tail"] == 1 and doc["bootstrap"]["status"] == "NOT_COMPUTED_CONVENTIONS_OPEN"
    (o,) = doc["owners"]
    assert (o["class"], o["born_at"], o["calls"][0]["call_id"], o["open_at_window_end"]) == (
        "BORN_IN_WINDOW", "2025-09-01T03:30:00Z", CALL, True)
    assert o["confirmations"] == [{"at": "2025-09-01T04:01:00Z", "in_window": True}]
    if os.environ.get("ALGOTRADER_EVIDENCE_DIR"):  # optional synthetic artifacts for the delivery evidence
        ev = Path(os.environ["ALGOTRADER_EVIDENCE_DIR"])
        shutil.copytree(exp, ev / "synthetic-export", dirs_exist_ok=True)
        shutil.copytree(tmp_path / "ledger", ev / "synthetic-ledger", dirs_exist_ok=True)
    with pytest.raises(SystemExit):
        lg.run_ledger(exp, tmp_path / "ledger", mode="SYNTHETIC")  # never overwritten
    with pytest.raises(SystemExit):
        lg.run_ledger(exp, tmp_path / "ledger2", mode="STUDY")  # a study ledger needs an assignment reference


@pytest.mark.parametrize("cut", ["month_boundary", "pause_resume_around_issue"])
def test_interrupted_study_run_equals_the_uninterrupted_one(database_url, tmp_path, monkeypatch, cut):
    root, art, api = _app(database_url, tmp_path, monkeypatch)
    pack_id = _prepare(api, database_url, root)
    _, base = _launch(api, pack_id)
    run_all(worker(database_url, root, art, "observe:a", checkpoint_events=5000))
    want = _signature(database_url, base)
    _, rid = _launch(api, pack_id)
    if cut == "month_boundary":  # crash right after the first delivery of September (inside the evaluation window)
        with pytest.raises(SimulatedCrash):
            run_all(worker(database_url, root, art, "observe:b", checkpoint_events=7,
                           after_commit=crash_once_after(rid, _cursor(sf.DAY2) + 1)))
        _expire_lease(database_url, rid)
        run_all(worker(database_url, root, art, "observe:c", checkpoint_events=7))
    else:  # pause before the 04:02 reference, then step through the 04:03 issue and resume
        paused = {"done": False}

        def pause_before(replay_id, cursor):
            if replay_id == rid and cursor >= _cursor(sf.DAY2 + timedelta(hours=4, minutes=1)) and not paused["done"]:
                paused["done"] = True
                with connect(database_url) as c:
                    control.pause(c, replay_id)
        w = worker(database_url, root, art, "observe:d", checkpoint_events=13, after_commit=pause_before)
        run_all(w)
        assert replay(database_url, rid)["status"] == "paused"
        with connect(database_url) as c:
            for _ in range(EV_PER_MIN * 4):
                control.step(c, rid)
                run_all(w)
            control.resume(c, rid)
        run_all(w)
    r = replay(database_url, rid)
    assert r["status"] == "completed" and r["assurance"]["state"] == "passed", r["error"]
    assert _signature(database_url, rid) == want  # same journal, evaluation records and finish commitment
    calls = [e["record"]["call_id"] for e in journal(database_url, rid) if e["kind"] == "call"]
    assert calls == [CALL]

