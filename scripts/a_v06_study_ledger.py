"""A v0.6 operational evaluation — study ledger (offline accounting of one completed adviser evaluation).

Not product code and not an engine: it reads the run's existing read-only exports and arranges the results the
design asks for, without recomputing any decision or outcome.

  export  GET-only copy of one evaluation from a running local app (report, calls with hypothetical paths, scenario
          and entry-attempt journal pages) into a NEW directory, with the SHA-256 of every file.
  ledger  offline, from such an export: identities checked against the registered b47b997 identities; the primary
          population (every A call issued in the evaluation window), B/C and out-of-window calls kept apart; per-call
          PRIMARY results (price_net, or total_net only when the run's funding is certified); the UTC issue-hour series;
          weekly issue/entry counts; the A owner register; a balance that is never completed by assumption.

Fixed by the design (§2-§7) and applied here: result = the PRIMARY path; NO_ENTRY is no modeled operation; hours without
an A call are 0; an hour holding an included path without a determinable result (CENSORED / UNRESOLVED / AMBIGUOUS /
missing terminal record / missing value) is NOT zero, it stays undetermined; B/C calls never enter the primary result.
The moving-block bootstrap is NOT computed: its draw procedure and the representation of undetermined paths are still
to be registered (design §3-§6; see delivery/A-V06-OPERATIONAL-EVALUATION-REFERENCES.md). No HDP-001 convention is
used. Sums are normalized one-unit results, never an account return.

Usage (only under the separate executive assignment; the study is INACTIVE):
  uv run python scripts/a_v06_study_ledger.py export --api http://127.0.0.1:8000 --evaluation <id> --out <new dir>
  uv run python scripts/a_v06_study_ledger.py ledger --export <export dir> --out <new dir> --assignment "<ref>"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from algotrader.adviser.report_periods import exact_sum

LEDGER_ID = "a-v06.study-ledger.v1"
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_COMMIT = "b47b997ee93513c7a358b49e961020705e4fbb85"
REGISTERED_IDENTITIES = ROOT / "delivery" / "evidence" / "A-V06-REFERENCES" / "identities-b47b997.json"
HOUR = timedelta(hours=1)
UNDETERMINED_STATUSES = ("CENSORED", "UNRESOLVED", "AMBIGUOUS")
OPEN_REQUIREMENTS = (
    "bootstrap draw procedure: order and method of the random.Random(0) draws (design §6 fixes blocks, B, seed, "
    "uniform starts, no wrap, truncation and type-7 percentiles only)",
    "representation, in the bootstrap and in the reported balance, of included entered paths without a determinable "
    "result (design §3-§4 forbid imputing zero or deleting them)",
)


def _dt(s: str | None) -> datetime | None:
    return None if s is None else datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def iso(t: datetime | None) -> str | None:
    return None if t is None else t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _new_dir(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} exists and is not empty; earlier outputs are never overwritten")
    out.mkdir(parents=True, exist_ok=True)


# -- export (GET only) -----------------------------------------------------------------------------------------------

def export(get, evaluation_id: str, out: Path) -> dict:
    """``get(path, params) -> dict`` is a read-only GET (urllib against the local app, or a test client)."""
    _new_dir(out)
    ev = get(f"/api/evaluations/{evaluation_id}", None)
    rid = ev["replay"]["replay_id"]
    docs = {"evaluation.json": ev, "report.json": get(f"/api/evaluations/{evaluation_id}/report.json", None),
            "calls.json": get(f"/api/adviser/runs/{rid}/calls", None)}
    for kind in ("scenario", "entry_attempt"):
        recs, after = [], 0
        while True:
            page = get(f"/api/adviser/journal/{rid}", {"kind": kind, "after_seq": after, "limit": 200})
            recs += page["records"]
            if not page["records"]:
                break
            after = page["next_after_seq"]
        docs[f"journal-{kind}.json"] = {"run_id": rid, "kind": kind, "records": recs}
    files = {}
    for name, doc in docs.items():
        data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode()
        (out / name).write_bytes(data)
        files[name] = hashlib.sha256(data).hexdigest()
    man = {"ledger_tool": LEDGER_ID, "evaluation_id": evaluation_id, "replay_id": rid, "access": "GET only",
           "files": files}
    (out / "export_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return man


def http_get(base: str):
    def get(path: str, params: dict | None) -> dict:
        url = base.rstrip("/") + path + ("?" + urllib.parse.urlencode(params) if params else "")
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=60) as r:
            return json.loads(r.read())
    return get


# -- ledger (offline) ------------------------------------------------------------------------------------------------

def _primary_path(paths: list[dict]) -> dict | None:
    prim = [p for p in paths if p.get("variant") == "PRIMARY"]
    return prim[-1] if prim else None


def _call_row(entry: dict, es: datetime, ee: datetime, measure: str) -> dict:
    c = entry["call"]
    issued = _dt(c["issued_at"])
    in_window = es <= issued < ee
    p = _primary_path(entry.get("hypothetical_paths", []))
    status = p["status"] if p else None
    value = p.get(measure) if p else None
    if p is None:
        cls, reason = "UNDETERMINED", "PRIMARY_TERMINAL_RECORD_MISSING"
    elif status == "NO_ENTRY":
        cls, reason = "NO_OPERATION", "NO_ENTRY"
    elif status == "CLOSED" and value is not None:
        cls, reason = "DETERMINED", None
    elif status == "CLOSED":
        cls, reason = "UNDETERMINED", f"{measure.upper()}_UNAVAILABLE"
    else:
        cls, reason = "UNDETERMINED", status
    resolved = _dt(p.get("resolved_at")) if p else None
    return {"call_id": c["call_id"], "family": c["family"], "direction": c["direction"],
            "entry_mode": c.get("entry_mode"), "scenario_id": c.get("scenario_id"), "issued_at": iso(issued),
            "issue_hour": iso(issued.replace(minute=0, second=0, microsecond=0)), "in_window": in_window,
            "primary": c["family"] == "A" and in_window, "primary_status": status,
            "entered": bool(p and p.get("entry")), "exit_class": p.get("exit_class") if p else None,
            "measure": measure, "value": value, "class": cls, "undetermined_reason": reason,
            "bounds": p.get("bounds") if p and cls == "UNDETERMINED" else None,
            "resolved_at": iso(resolved), "resolved_in_tail": bool(resolved and resolved >= ee),
            "funding_status": p.get("funding_status") if p else None}


def _owner_register(scen: list[dict], ents: list[dict], calls: list[dict], es: datetime, ee: datetime) -> list[dict]:
    by_owner: dict[str, list[dict]] = defaultdict(list)
    for x in scen:
        r = x["record"]
        if r["family"] == "A":
            by_owner[r["scenario_id"]].append(r)
    ent_by: dict[str, list[dict]] = defaultdict(list)
    for x in ents:
        ent_by[x["record"]["scenario_id"]].append(x["record"])
    calls_by: dict[str, list[dict]] = defaultdict(list)
    for c in calls:
        if c["scenario_id"]:
            calls_by[c["scenario_id"]].append(c)
    out = []
    for sid, recs in sorted(by_owner.items(), key=lambda kv: kv[1][0]["env"]["published_at"]):
        t = lambda r: _dt(r["env"]["published_at"])  # noqa: E731
        born = next((t(r) for r in recs if r["transition"] == "BIRTH"), t(recs[0]))
        term = next((r for r in recs if r["transition"] == "TERMINAL"), None)
        before = [r for r in recs if t(r) < es]
        status_at_start = before[-1]["status"] if before else None
        pre = born < es and not (term is not None and t(term) < es)
        confs = [r for r in recs if r["transition"] == "CONFIRM"]
        e = ent_by.get(sid, [])
        issued = calls_by.get(sid, [])
        last_e = next((r for r in reversed(e) if r["transition"] in ("TERMINAL", "REJECT")), None)
        blockers = next((r["blockers"] for r in reversed(e) if r["transition"] == "BLOCKERS"), None)
        not_confirmed = None if confs else (
            f"{term['terminal_state']}:{term['reason']}" if term is not None and t(term) < ee
            else "OPEN_WITHOUT_CONFIRMATION_AT_WINDOW_END")
        not_issued = None
        if confs and not issued:
            not_issued = (f"{last_e['transition']}:{last_e['reason']}" if last_e is not None
                          else f"BLOCKERS:{'|'.join(blockers)}" if blockers else "NO_TERMINAL_ENTRY_RECORD")
        out.append({
            "owner_id": sid, "direction": recs[0]["direction"], "born_at": iso(born),
            "class": ("PRE_EXISTING_AT_START" if pre else "BORN_IN_WINDOW" if es <= born < ee
                      else "BORN_IN_WARMUP_ENDED_BEFORE_START" if born < es else "BORN_AFTER_WINDOW"),
            "status_at_start": status_at_start if pre else None,
            "confirmations": [{"at": iso(t(r)), "in_window": es <= t(r) < ee} for r in confs],
            "transitions": dict(sorted(Counter(r["transition"] for r in recs).items())),
            "entry_transitions": dict(sorted(Counter(r["transition"] for r in e).items())),
            "calls": [{"call_id": c["call_id"], "issued_at": c["issued_at"], "primary": c["primary"]} for c in issued],
            "terminal": ({"at": iso(t(term)), "state": term["terminal_state"], "reason": term["reason"]}
                         if term is not None else None),
            "open_at_window_end": term is None or t(term) >= ee,
            "not_confirmed_reason": not_confirmed, "not_issued_reason": not_issued,
        })
    return out


def _check_identities(pins: dict) -> dict:
    reg = json.loads(REGISTERED_IDENTITIES.read_text(encoding="utf-8"))
    funding = pins["capability_profile"]["funding_outcomes"]
    prof = {v["sha256"] for v in reg["historical_profiles"].values()}
    checks = {
        "rules_sha256": pins.get("rules_sha256") == reg["rules_sha256"],
        "register_sha256": pins.get("register_sha256") == reg["register_canonical_sha256"],
        "implementation": pins.get("implementation") == reg["release"]["implementation"],
        "model": pins.get("model") == reg["release"]["model"],
        "evaluator_sha256": pins.get("evaluator_sha256") == reg["evaluator_identity"][funding]["sha256"],
        "capability_profile_sha256_is_a_registered_row": pins.get("capability_profile_sha256") in prof,
        "primary_entry_delay_60s": pins.get("primary_entry_delay_seconds") == 60,
    }
    return {"reference_commit": REFERENCE_COMMIT, "registered_identities_file": str(
        REGISTERED_IDENTITIES.relative_to(ROOT)).replace("\\", "/"),
            "registered_identities_sha256_lf": sha_lf(REGISTERED_IDENTITIES), "checks": checks,
            "all_match": all(checks.values()),
            "note": ("identity names and hashes only; behavioural equivalence of the executive build with b47b997 is a "
                     "separate check (references §8)")}


def build_ledger(report: dict, calls_doc: dict, scen: list[dict], ents: list[dict], *, mode: str,
                 assignment: str | None = None) -> dict:
    adv = report["adviser"]
    w = adv["windows"]
    es, ee = _dt(w["evaluation"][0]), _dt(w["evaluation"][1])
    pins = adv["launch_pins"]
    funding = pins["capability_profile"]["funding_outcomes"]
    measure = "total_net" if funding == "AUTHORITATIVE_IF_COVERED" else "price_net"
    rows = [_call_row(e, es, ee, measure) for e in calls_doc["calls"]]
    prim = [r for r in rows if r["primary"]]
    hours, t = [], es
    by_hour: dict[str, list[dict]] = defaultdict(list)
    for r in prim:
        by_hour[r["issue_hour"]].append(r)
    while t < ee:
        rs = by_hour.get(iso(t), [])
        det = [r["value"] for r in rs if r["class"] == "DETERMINED"]
        und = [r for r in rs if r["class"] == "UNDETERMINED"]
        value = None if und else str(exact_sum(det))
        hours.append({"hour": iso(t), "a_calls": len(rs), "determined": len(det),
                      "no_operation": sum(1 for r in rs if r["class"] == "NO_OPERATION"), "undetermined": len(und),
                      "value": value, "status": ("NO_CALL_ZERO" if not rs else "CONTAINS_UNDETERMINED" if und
                                                  else "DETERMINED")})
        t += HOUR
    det_all = [r["value"] for r in prim if r["class"] == "DETERMINED"]
    und_all = [r for r in prim if r["class"] == "UNDETERMINED"]
    weeks = []
    for b in range(0, len(hours), 168):
        block = {h["hour"] for h in hours[b:b + 168]}
        weeks.append({"block": b // 168, "from": hours[b]["hour"], "hours": len(block),
                      "a_calls_issued": sum(1 for r in prim if r["issue_hour"] in block),
                      "a_paths_entered": sum(1 for r in prim if r["issue_hour"] in block and r["entered"])})
    determined_sum = str(exact_sum(det_all))
    return {
        "ledger_tool": LEDGER_ID, "mode": mode, "assignment": assignment,
        "label": ("SYNTHETIC EXECUTION — engineering check of the study path; not the A v0.6 evaluation"
                  if mode == "SYNTHETIC" else "A v0.6 OPERATIONAL EVALUATION — ledger of the run below"),
        "evaluation_id": report["evaluation_id"], "replay_id": report["replay_id"],
        "run_status": report["status"], "completion": report.get("completion"),
        "windows": {"evaluation": [iso(es), iso(ee)], "warmup_start": iso(_dt(w["warmup_start"])),
                    "tail_end": iso(_dt(w["tail_end"])), "hours": len(hours)},
        "build": pins.get("build"), "pack_id": pins.get("pack_id"), "feed_content_identity": pins.get(
            "feed_content_identity"), "identity_sha256": pins.get("identity_sha256"),
        "identities": _check_identities(pins), "funding_outcomes": funding, "measure": measure,
        "population": {
            "primary_a_calls": len(prim), "determined": len(det_all),
            "no_operation_no_entry": sum(1 for r in prim if r["class"] == "NO_OPERATION"),
            "undetermined": len(und_all),
            "undetermined_by_reason": dict(sorted(Counter(r["undetermined_reason"] for r in und_all).items())),
            "entered": sum(1 for r in prim if r["entered"]),
            "resolved_in_tail": sum(1 for r in prim if r["resolved_in_tail"]),
            "bc_calls_reported_separately": sum(1 for r in rows if r["family"] != "A"),
            "a_calls_outside_window": sum(1 for r in rows if r["family"] == "A" and not r["in_window"])},
        "balance": {"determined_sum": determined_sum,
                    "complete_balance": determined_sum if not und_all else None,
                    "status": "COMPLETE" if not und_all else "INCOMPLETE_UNDETERMINED_PATHS",
                    "meaning": ("sum of normalized one-unit PRIMARY results of the included A calls, net of the "
                                "included costs; abstention = 0; not an account return, not compounded"),
                    "note": None if not und_all else ("the determined sum excludes undetermined included paths; it "
                                                      "is not a complete balance and nothing was imputed")},
        "weekly": weeks,
        "bootstrap": {"status": "NOT_COMPUTED_CONVENTIONS_OPEN", "open_requirements": list(OPEN_REQUIREMENTS),
                      "fixed_by_design": "168 h moving blocks on the full window grid, 10,000 resamples, "
                                         "random.Random(0), no wrap, truncated last block, type-7 95% interval"},
        "calls": rows, "hours": hours, "owners": _owner_register(scen, ents, rows, es, ee),
    }


def run_ledger(export_dir: Path, out: Path, mode: str = "SYNTHETIC", assignment: str | None = None) -> dict:
    if mode == "STUDY" and not assignment:
        raise SystemExit("a STUDY ledger needs --assignment: the separate executive assignment that authorizes it")
    _new_dir(out)
    man = json.loads((export_dir / "export_manifest.json").read_text(encoding="utf-8"))
    for name, h in man["files"].items():
        if hashlib.sha256((export_dir / name).read_bytes()).hexdigest() != h:
            raise SystemExit(f"export file {name} differs from its recorded SHA-256")
    load = lambda n: json.loads((export_dir / n).read_text(encoding="utf-8"))  # noqa: E731
    doc = build_ledger(load("report.json"), load("calls.json"), load("journal-scenario.json")["records"],
                       load("journal-entry_attempt.json")["records"], mode=mode, assignment=assignment)
    doc["export"] = man
    doc["ledger_script_sha256_lf"] = sha_lf(Path(__file__))
    for name, rows, cols in (("calls.csv", doc["calls"], ["call_id", "family", "direction", "issued_at", "issue_hour",
                                                          "in_window", "primary", "primary_status", "entered",
                                                          "measure", "value", "class", "undetermined_reason",
                                                          "resolved_at", "resolved_in_tail"]),
                             ("hours.csv", doc["hours"], ["hour", "a_calls", "determined", "no_operation",
                                                          "undetermined", "value", "status"])):
        buf = io.StringIO()
        wr = csv.writer(buf, lineterminator="\n")
        wr.writerow(cols)
        for r in rows:
            wr.writerow(["" if r[c] is None else r[c] for c in cols])
        (out / name).write_bytes(buf.getvalue().encode())
    (out / "ledger.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A v0.6 study ledger (GET-only export; offline ledger)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--api", required=True)
    e.add_argument("--evaluation", required=True)
    e.add_argument("--out", required=True, type=Path)
    lg = sub.add_parser("ledger")
    lg.add_argument("--export", required=True, type=Path)
    lg.add_argument("--out", required=True, type=Path)
    lg.add_argument("--assignment", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "export":
        print(json.dumps(export(http_get(a.api), a.evaluation, a.out)))
    else:
        doc = run_ledger(a.export, a.out, mode="STUDY", assignment=a.assignment)
        print(json.dumps({"balance": doc["balance"]["status"], "out": str(a.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
