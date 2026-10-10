"""Same synthetic input through one source tree (b47b997 or the executive build): engineering comparison only.

Run once per tree, with that tree's ``src`` first on the import path, against a disposable PostgreSQL server:

  PYTHONPATH=<tree>/src uv run python compare_builds.py --admin-url <disposable server> --out <tree>.json --label <tree>

1. Durable path, inside a window BOTH trees accept (the fixture presets file of ``tests/adviser_db.py``): the real pack
   job prepares a pack from the synthetic v0.6 A call tape (``tests/study_fixtures.tape``), a v0.6 adviser evaluation
   runs on the observation worker, and the script records the pack content identity, the journal / evaluation-record
   digests, the finish commitment and the report with volatile fields (ids, times, build) removed.
2. Pure fold with the study fixture windows (no presets involved, so the reference tree can compute it too): journal
   and record digests. The executive build's durable study-window run is separately asserted equal to this pure fold
   (tests/test_a_v06_study_db.py).

Synthetic engineering input only; no market data, Owner data, network, real window or economic result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(1, str(REPO / "tests"))

import psycopg  # noqa: E402
import study_fixtures as sf  # noqa: E402
from adviser_db import EV_END, EV_START, fake_from, prepare_pack, run_all, worker, write_presets  # noqa: E402
from pack_fixtures import connect  # noqa: E402
from psycopg import sql  # noqa: E402

import algotrader  # noqa: E402
from algotrader import db  # noqa: E402
from algotrader.adviser.harness import run_pure  # noqa: E402
from algotrader.api import create_app  # noqa: E402

VOLATILE = {"evaluation_id", "replay_id", "captured_at", "created_at", "started_at", "finished_at", "stopped_at",
            "code_version", "build", "identity_sha256", "elapsed_seconds", "runtime", "operation", "storage",
            "acquisition", "verified_at", "retrieved_at", "snapshot_retrieved_at", "progress", "lease_owner",
            "control_log", "recovery_log", "attempt", "published_at", "committed_at", "duration_seconds",
            "seconds", "wall_seconds", "events_per_second", "bytes", "phase_timing", "work_dir", "path", "checked_at",
            "manifest_file_sha256"}  # run manifest file: embeds replay id, launch time and build


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    return [strip(v) for v in x] if isinstance(x, list) else x


def h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


class _Env:
    def setenv(self, k, v):
        os.environ[k] = v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin-url", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--label", required=True, help="tree label recorded in the output, e.g. b47b997")
    a = ap.parse_args()
    name = f"cmp_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(a.admin_url, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = a.admin_url.rsplit("/", 1)[0] + "/" + name
    try:
        db.migrate(url)
        tmp = Path(tempfile.mkdtemp())
        write_presets(tmp, _Env())  # fixture window [DAY2, DAY2+6h), accepted by both trees
        os.environ.pop("ALGOTRADER_STUDY_PRESETS", None)
        root, art = tmp / "data", tmp / "art"
        tape = sf.tape(int((EV_END - sf.DAY1).total_seconds() // 60) + 365)
        pack = prepare_pack(url, root, fake_from(tape, start=sf.DAY1))
        from fastapi.testclient import TestClient

        api = TestClient(create_app(url, art, web_dist=tmp / "no-ui", data_root=root))
        r = api.post("/api/evaluations", json={"pack_id": pack["pack_id"], "run_type": "adviser_evaluation",
                                               "method": "v0.6", "acknowledge_limitations": True})
        assert r.status_code == 201, r.text
        eid, rid = r.json()["evaluation_id"], r.json()["replay"]["replay_id"]
        run_all(worker(url, root, art, "observe:cmp", checkpoint_events=500))
        rep = api.get(f"/api/evaluations/{eid}/report.json").json()
        with connect(url) as c:
            row = c.execute("SELECT status, assurance, engine FROM observation_replays WHERE replay_id = %s",
                            (rid,)).fetchone()
            jd = [r["digest"] for r in c.execute("SELECT digest FROM adviser_journal WHERE run_id = %s ORDER BY seq",
                                                 (rid,)).fetchall()]
            rd = [r["digest"] for r in c.execute("SELECT digest FROM adviser_evaluation_records WHERE run_id = %s "
                                                 "ORDER BY seq", (rid,)).fetchall()]
            fin = c.execute("SELECT commitment FROM adviser_finish WHERE run_id = %s", (rid,)).fetchone()
            calls = [r["record"] for r in c.execute("SELECT record FROM adviser_journal WHERE run_id = %s AND "
                                                    "kind = 'call' ORDER BY seq", (rid,)).fetchall()]
            paths = [r["record"] for r in c.execute("SELECT record FROM adviser_evaluation_records WHERE run_id = %s "
                                                    "AND kind = 'path' ORDER BY seq", (rid,)).fetchall()]
        adv = row["engine"]["adviser"]
        pure = run_pure(sf.DAY1, sf.tape(), eval_start=sf.EV_START, eval_end=sf.EV_END, method="v0.6")
        out = {
            "tree": a.label,
            "algotrader_imported_from_repo_src": Path(algotrader.__file__).resolve().is_relative_to(REPO / "src"),
            "durable": {
                "window": [EV_START.isoformat(), EV_END.isoformat()], "pack_id": pack["pack_id"],
                "status": row["status"], "assurance": row["assurance"]["state"],
                "identity_without_build": {k: v for k, v in adv["identity"].items()
                                           if k not in ("build", "identity_sha256")},
                "evaluator": adv["evaluator"]["sha256"], "journal_digests_sha256": h(jd), "journal_records": len(jd),
                "record_digests_sha256": h(rd), "records": len(rd), "finish_commitment": (fin or {}).get("commitment"),
                "calls": [(x["call_id"], x["issued_at"]) for x in calls],
                "primary_paths": [(p["call_id"], p["status"], p["price_net"], p.get("resolved_at")) for p in paths
                                  if p["variant"] == "PRIMARY"],
                "report_sha256_without_volatile": h(strip(rep)),
                "report_adviser_sha256_without_volatile": h(strip(rep.get("adviser"))),
            },
            "pure_study_windows": {
                "window": [sf.EV_START.isoformat(), sf.EV_END.isoformat()],
                "journal_digests_sha256": h([e["digest"] for e in pure.journal]) if pure.journal and "digest" in
                pure.journal[0] else h([e["record"] for e in pure.journal]),
                "records_sha256": h([x["record"] for x in pure.records]),
                "calls": [e["record"]["call_id"] for e in pure.journal if e["kind"] == "call"]},
        }
        a.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
        a.out.with_suffix(".report.json").write_text(json.dumps(strip(rep), indent=1, sort_keys=True, default=str)
                                                      + "\n", encoding="utf-8")
        print(json.dumps({"tree": a.label, "from_repo_src": out["algotrader_imported_from_repo_src"], "status": row["status"]}))
    finally:
        with psycopg.connect(a.admin_url, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    main()
