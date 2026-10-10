"""Descriptive tabulation: MarketView +1h sign versus last-hour persistence, run eval-20261009T155751-be8b2b (v0.5).

Not product code. Offline only, from raw exports kept OUTSIDE Git:
  <vs_export>/view_samples.jsonl  output of export.sql (one REPEATABLE READ READ ONLY transaction, view_sample rows only)
  <journal_export>/sc_*.json      GET /api/adviser/journal/<replay>?kind=scenario (all pages; R->N diagnosis exports)
  <journal_export>/report.json    GET /api/evaluations/<id>/report.json (aggregates used as cross-checks only)

Usage: uv run python tabulate_view_persistence.py <vs_export> <journal_export> <out_dir>
Writes <out_dir>/tabulation.json and <out_dir>/samples.csv. No thresholds, significance tests or subgroup search; hours
are not treated as independent observations. Later activation and scenario terminals are annotations only.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

EVALUATION_ID = "eval-20261009T155751-be8b2b"
REPLAY_ID = "obs-20261009T155751-0f255b"
GRID_START = datetime(2025, 9, 1, tzinfo=timezone.utc)
GRID_END = datetime(2026, 1, 1, tzinfo=timezone.utc)  # exclusive
INITIAL_RECORDS = hashlib.sha256(b"algotrader.adviser-evaluation.records.v1\x00").hexdigest()  # evaluator.py
DIRECTIONAL = ("UP", "DOWN")


def canonical(obj) -> bytes:  # identical to algotrader.feed.ordering.canonical
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()


def dt(s: str | None) -> datetime | None:
    return None if s is None else datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(d: datetime | None) -> str | None:
    return None if d is None else d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_samples(vs_export: Path) -> tuple[dict, dict, list[dict]]:
    meta = count = None
    rows = []
    for line in (vs_export / "view_samples.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if "meta" in d:
            meta = d["meta"]
        elif "count" in d:
            count = d["count"]
        else:
            rows.append(d["vs"])
    return meta, count, rows


def load_scenarios(journal_export: Path) -> dict[str, dict]:
    recs = []
    for f in sorted(glob.glob(str(journal_export / "sc_*.json")), key=lambda x: int(Path(x).stem.split("_")[1])):
        recs += json.loads(Path(f).read_text(encoding="utf-8"))["records"]
    sc: dict[str, dict] = {}
    for r in recs:
        x = r["record"]
        s = sc.setdefault(x["scenario_id"], {"owners": [], "confirms": [], "terminal": None, "birth": None})
        if x.get("owner_id") and x["owner_id"] not in s["owners"]:
            s["owners"].append(x["owner_id"])
        pub = x["env"]["published_at"]
        if x["transition"] == "BIRTH":
            s["birth"] = pub
        elif x["transition"] == "CONFIRM":
            s["confirms"].append(pub)
        elif x["transition"] == "TERMINAL":
            s["terminal"] = {"state": x.get("terminal_state"), "published_at": pub, "reason": x.get("reason")}
    return sc, {"records": len(recs), "births": sum(1 for r in recs if r["record"]["transition"] == "BIRTH"),
                "terminals": sum(1 for r in recs if r["record"]["transition"] == "TERMINAL"),
                "confirms": sum(1 for r in recs if r["record"]["transition"] == "CONFIRM"),
                "seq_first": recs[0]["seq"], "seq_last": recs[-1]["seq"]}


def integrity(meta: dict, count: dict, rows: list[dict]) -> dict:
    out: dict = {"transaction": meta, "server_count": count}
    seqs = [r["seq"] for r in rows]
    times = [r["record"]["sample_time"] for r in rows]
    grid = []
    t = GRID_START
    while t < GRID_END:
        grid.append(iso(t))
        t += timedelta(hours=1)
    by_seq = {r["seq"]: r for r in rows}
    digest_ok = sum(1 for r in rows if hashlib.sha256(canonical(r["record"])).hexdigest() == r["digest"])
    # chain checks possible inside the extracted subset only: seq 1 from the initial seed, and the link into seq s whose
    # predecessor s-1 is also a view_sample. A link after a non-extracted record (path rows) is NOT verifiable.
    links_ok = links_bad = 0
    unverifiable = []
    for r in rows:
        prev = INITIAL_RECORDS if r["seq"] == 1 else (by_seq.get(r["seq"] - 1) or {}).get("chain")
        if prev is None:
            unverifiable.append(r["seq"])
            continue
        if hashlib.sha256(bytes.fromhex(prev) + bytes.fromhex(r["digest"])).hexdigest() == r["chain"]:
            links_ok += 1
        else:
            links_bad += 1
    missing = sorted(set(range(1, max(seqs) + 1)) - set(seqs))
    # cross-record consistency from stored values only (no price cache): the +1h endpoint of h is the latest complete
    # 1m close known at h+1h, i.e. the anchor of the h+1h sample, and the persistence of h+1h is the last completed
    # hour, i.e. the same move.
    by_time = {r["record"]["sample_time"]: r["record"] for r in rows}
    cons = Counter()
    for r in rows:
        s = r["record"]
        n = by_time.get(iso(dt(s["sample_time"]) + timedelta(hours=1)))
        if n is None or s["anchor_price"] is None or n["anchor_price"] is None or s["outcome_1h"] is None:
            cons["not_checkable"] += 1
            continue
        a0, a1 = float(s["anchor_price"]), float(n["anchor_price"])
        sign = "UP" if a1 > a0 else "DOWN" if a1 < a0 else "FLAT"
        cons["outcome_equals_next_anchor_sign" if sign == s["outcome_1h"] else "outcome_differs_next_anchor_sign"] += 1
        cons["next_persistence_equals_outcome" if n["persistence"] == s["outcome_1h"] else
             "next_persistence_differs_outcome"] += 1
    out.update({
        "rows": len(rows), "expected_rows": len(grid),
        "all_kind_view_sample": all(r["kind"] == "view_sample" for r in rows),
        "all_run_id": all(r["run_id"] == REPLAY_ID for r in rows),
        "unique_seq": len(set(seqs)) == len(seqs), "unique_record_id": len({r["record_id"] for r in rows}) == len(rows),
        "unique_sample_time": len(set(times)) == len(times),
        "record_id_equals_sample_prefix_time": all(r["record_id"] == f"sample-{r['record']['sample_time']}" for r in rows),
        "sample_times_equal_hourly_grid": sorted(times) == grid,
        "seq_order_equals_time_order": [r["record"]["sample_time"] for r in sorted(rows, key=lambda r: r["seq"])] == grid,
        "generations": dict(Counter(str(r["generation"]) for r in rows)),
        "digest_recomputed_equal": f"{digest_ok}/{len(rows)}",
        "seq_range": [min(seqs), max(seqs)], "seq_not_extracted_other_kinds": missing,
        "chain_links_verified_within_subset": links_ok, "chain_links_failed": links_bad,
        "chain_links_not_verifiable": unverifiable,
        "chain_scope": ("partial: per-record digests are recomputed; chain_links_verified_within_subset counts the "
                        "successful checks, i.e. the check of seq 1 from the initial seed plus the links between "
                        "consecutive extracted records; chain_links_not_verifiable lists the links that follow a "
                        "non-extracted record; the full chain and its final commitment are NOT verified by this "
                        "extraction (non-view_sample records and the finish commitment were outside the authorized "
                        "access)"),
        "stored_value_consistency": dict(cons),
    })
    return out


def tabulate(rows: list[dict], sc: dict[str, dict]) -> tuple[dict, list[dict]]:
    S = [r["record"] for r in sorted(rows, key=lambda r: r["seq"])]
    seq_of = {r["record"]["sample_time"]: r["seq"] for r in rows}
    dig_of = {r["record"]["sample_time"]: r["digest"] for r in rows}

    def month(s):
        return s["sample_time"][:7]

    # 1. reconciliation of every sample
    recon = {"samples": len(S), "by_view": dict(sorted(Counter(s["view"] for s in S).items())),
             "outcome_1h": dict(sorted(Counter(str(s["outcome_1h"]) for s in S).items())),
             "persistence": dict(sorted(Counter(str(s["persistence"]) for s in S).items())),
             "anchor_missing": sum(1 for s in S if s["anchor_price"] is None),
             "by_month_view": {m: dict(sorted(Counter(s["view"] for s in S if month(s) == m).items()))
                               for m in sorted({month(s) for s in S})}}
    D = [s for s in S if s["view"] in DIRECTIONAL]
    recon["directional"] = len(D)
    recon["directional_endpoint_missing"] = sum(1 for s in D if s["outcome_1h"] is None)
    recon["directional_endpoint_flat"] = sum(1 for s in D if s["outcome_1h"] == "FLAT")
    recon["directional_persistence_missing"] = sum(1 for s in D if s["persistence"] is None)
    recon["directional_persistence_flat"] = sum(1 for s in D if s["persistence"] == "FLAT")

    # 3. MarketView on the whole evaluable directional population (endpoint available; FLAT outcome kept apart)
    ev = [s for s in D if s["outcome_1h"] is not None]
    mv_full = {"population": "view UP/DOWN with +1h endpoint available", "n": len(ev),
               "coverage_directional_over_all_samples": f"{len(D)}/{len(S)}",
               "matching_sign": sum(1 for s in ev if s["outcome_1h"] == s["view"]),
               "opposite_sign": sum(1 for s in ev if s["outcome_1h"] in DIRECTIONAL and s["outcome_1h"] != s["view"]),
               "outcome_flat": sum(1 for s in ev if s["outcome_1h"] == "FLAT"),
               "by_direction": {}, "by_month": {}}
    for k, sel in (("by_direction", lambda s: s["view"]), ("by_month", month)):
        for g in sorted({sel(s) for s in ev}):
            x = [s for s in ev if sel(s) == g]
            mv_full[k][g] = {"n": len(x), "matching_sign": sum(1 for s in x if s["outcome_1h"] == s["view"]),
                             "outcome_flat": sum(1 for s in x if s["outcome_1h"] == "FLAT")}

    # 2. paired comparison: endpoint and persistence both available with a sign (FLAT counted explicitly outside)
    paired = [s for s in ev if s["outcome_1h"] in DIRECTIONAL and s["persistence"] in DIRECTIONAL]

    def cell(s):
        mv, pe = s["view"] == s["outcome_1h"], s["persistence"] == s["outcome_1h"]
        return "BOTH" if mv and pe else "MV_ONLY" if mv else "PERSISTENCE_ONLY" if pe else "NEITHER"

    cells = ("BOTH", "MV_ONLY", "PERSISTENCE_ONLY", "NEITHER")

    def scen_count(xs):
        return len({s["scenario_id"] for s in xs if s["scenario_id"]})

    def owner_count(xs):
        return len({own(s) for s in xs if own(s)})

    def own(s):
        o = (sc.get(s["scenario_id"]) or {}).get("owners") if s["scenario_id"] else None
        return o[0] if o else None

    pt = {"population": "view UP/DOWN, +1h endpoint UP/DOWN, persistence UP/DOWN (same sample)", "n": len(paired),
          "excluded_from_ev": {"outcome_flat": sum(1 for s in ev if s["outcome_1h"] == "FLAT"),
                               "persistence_flat": sum(1 for s in ev if s["persistence"] == "FLAT"),
                               "persistence_missing": sum(1 for s in ev if s["persistence"] is None)},
          "cells": {}, "by_direction": {}, "by_month": {},
          "mv_matching": sum(1 for s in paired if s["view"] == s["outcome_1h"]),
          "persistence_matching": sum(1 for s in paired if s["persistence"] == s["outcome_1h"]),
          "view_persistence_same_sign": sum(1 for s in paired if s["view"] == s["persistence"]),
          "view_persistence_opposite_sign": sum(1 for s in paired if s["view"] != s["persistence"])}
    for c in cells:
        x = [s for s in paired if cell(s) == c]
        pt["cells"][c] = {"samples": len(x), "distinct_scenarios": scen_count(x), "distinct_owners": owner_count(x)}
    for k, sel in (("by_direction", lambda s: s["view"]), ("by_month", month)):
        for g in sorted({sel(s) for s in paired}):
            x = [s for s in paired if sel(s) == g]
            pt[k][g] = {c: sum(1 for s in x if cell(s) == c) for c in cells} | {"n": len(x)}
    pt["by_view_persistence_agreement"] = {
        a: {c: sum(1 for s in paired if (s["view"] == s["persistence"]) == (a == "SAME_SIGN") and cell(s) == c)
            for c in cells} for a in ("SAME_SIGN", "OPPOSITE_SIGN")}

    # 4. scenarios / owners supporting the directional samples
    per_scen = Counter(s["scenario_id"] for s in D)
    per_owner = Counter(own(s) for s in D)
    sizes = sorted(per_scen.values(), reverse=True)
    support = {"directional_samples": len(D), "with_scenario_id": sum(1 for s in D if s["scenario_id"]),
               "scenario_found_in_journal": sum(1 for s in D if s["scenario_id"] in sc),
               "distinct_scenarios": len(per_scen), "distinct_owners": len(per_owner),
               "scenarios_with_multiple_owner_ids": sorted(k for k in per_scen if len((sc.get(k) or {}).get("owners", [])) > 1),
               "samples_per_scenario": {"max": sizes[0], "median": statistics.median(sizes), "min": sizes[-1],
                                        "distribution": dict(sorted(Counter(sizes).items()))},
               "largest_scenario_shares": [{"scenario_id": k, "samples": v} for k, v in per_scen.most_common(5)],
               "samples_per_owner_max": max(per_owner.values()),
               "by_month_direction": {}}
    for m in sorted({month(s) for s in D}):
        for d in DIRECTIONAL:
            x = [s for s in D if month(s) == m and s["view"] == d]
            if not x:
                support["by_month_direction"][f"{m} {d}"] = {"samples": 0}
                continue
            c = Counter(s["scenario_id"] for s in x)
            support["by_month_direction"][f"{m} {d}"] = {
                "samples": len(x), "distinct_scenarios": len(c), "distinct_owners": owner_count(x),
                "max_samples_one_scenario": max(c.values())}
    support["paired_distinct_scenarios"] = scen_count(paired)
    support["paired_distinct_owners"] = owner_count(paired)

    # 5. antecedent class at +1h from the scenario journal (CONFIRM published_at); annotations never select
    def ante(s):
        h = dt(s["sample_time"])
        if not s["scenario_id"] or s["scenario_id"] not in sc:
            return "NOT_ASSESSABLE", None
        conf = [dt(c) for c in sc[s["scenario_id"]]["confirms"]]
        first = min(conf) if conf else None
        if first is not None and first <= h:
            return "ALREADY_ACTIVE_AT_CUTOFF", first
        if first is not None and first <= h + timedelta(hours=1):
            return "ACTIVATED_WITHIN_1H", first
        return "NOT_ACTIVATED_AT_1H", first

    ac = Counter()
    ac_dir = defaultdict(Counter)
    flag_mismatch = []
    table = []
    ordinal = Counter()
    for s in S:
        cls, first = ante(s) if s["view"] in DIRECTIONAL else (("NOT_ASSESSABLE", None) if not s["scenario_id"]
                                                                else ante(s))
        if s["view"] in DIRECTIONAL:
            ac[cls] += 1
            ac_dir[s["view"]][cls] += 1
            stored = s.get("antecedent_activated_1h")
            if cls != "NOT_ASSESSABLE" and stored is not None and stored != (cls != "NOT_ACTIVATED_AT_1H"):
                flag_mismatch.append(s["sample_time"])
        h = dt(s["sample_time"])
        later = first if (first is not None and first > h + timedelta(hours=1)) else None
        term = (sc.get(s["scenario_id"]) or {}).get("terminal") if s["scenario_id"] else None
        if s["scenario_id"]:
            ordinal[s["scenario_id"]] += 1
        directional_ev = s["view"] in DIRECTIONAL and s["outcome_1h"] is not None
        table.append({
            "s_seq": seq_of[s["sample_time"]], "s_digest": dig_of[s["sample_time"]], "s_sample_time": s["sample_time"],
            "s_view": s["view"], "s_conditional": s["conditional"], "s_scenario_id": s["scenario_id"] or "",
            "s_anchor_price": s["anchor_price"] or "", "s_persistence": s["persistence"] or "",
            "s_outcome_1h": s["outcome_1h"] or "", "s_return_1h": s["return_1h"] or "",
            "s_antecedent_activated_1h": "" if s.get("antecedent_activated_1h") is None else s["antecedent_activated_1h"],
            "d_month": month(s),
            "d_population": ("PAIRED" if s in paired else "DIRECTIONAL_EVALUABLE" if directional_ev else
                             "DIRECTIONAL_NO_ENDPOINT" if s["view"] in DIRECTIONAL else
                             "ABSTENTION" if s["view"] in ("BALANCED", "UNCERTAIN") else "UNAVAILABLE"),
            "d_mv_matches_1h": "" if not directional_ev else s["view"] == s["outcome_1h"],
            "d_persistence_matches_1h": ("" if not directional_ev or s["persistence"] not in DIRECTIONAL else
                                         s["persistence"] == s["outcome_1h"]),
            "d_paired_cell": cell(s) if s in paired else "",
            "d_owner_id": own(s) or "",
            "d_scenario_sample_ordinal": ordinal[s["scenario_id"]] if s["scenario_id"] else "",
            "d_antecedent_class_1h": cls if s["view"] in DIRECTIONAL else "",
            "d_first_confirm_published_at": iso(first) or "",
            "a_activation_after_1h_at": iso(later) or "",
            "a_scenario_terminal_state": (term or {}).get("state") or "",
            "a_scenario_terminal_published_at": (term or {}).get("published_at") or "",
        })
    antecedent = {"population": "directional samples (all, not only evaluable)", "classes": dict(sorted(ac.items())),
                  "by_direction": {d: dict(sorted(c.items())) for d, c in sorted(ac_dir.items())},
                  "stored_flag_1h_vs_journal_class_mismatches": flag_mismatch,
                  "annotation_activation_after_1h": sum(1 for t in table if t["s_view"] in DIRECTIONAL
                                                        and t["a_activation_after_1h_at"]),
                  "annotation_terminal_states": dict(sorted(Counter(t["a_scenario_terminal_state"] or "NONE"
                                                                    for t in table if t["s_view"] in DIRECTIONAL).items())),
                  "note": "class from the first CONFIRM published_at; activation after +1h and terminals are annotations "
                          "and select nothing; no accuracy is computed by class"}
    return {"reconciliation": recon, "marketview_full_directional": mv_full, "paired": pt,
            "scenario_owner_support": support, "antecedent": antecedent}, table


def cross_check(report: dict, recon: dict, mv: dict) -> dict:
    t = report["adviser"]["view_samples"]["1h"]
    tot = report["adviser"]["periods"]["total"]["market_view_samples"]
    return {"by_view": tot["by_view"] == recon["by_view"], "samples": tot["samples"] == recon["samples"],
            "directional_scored": t["directional_scored"] == mv["n"],
            "directional_matching_sign": t["directional_matching_sign"] == mv["matching_sign"],
            "endpoint_unavailable": t["endpoint_unavailable"] == int(recon["outcome_1h"].get("None", 0))}


def main(vs_export: Path, journal_export: Path, out: Path) -> None:
    meta, count, rows = load_samples(vs_export)
    sc, sc_meta = load_scenarios(journal_export)
    report = json.loads((journal_export / "report.json").read_text(encoding="utf-8"))
    integ = integrity(meta, count, rows)
    tab, table = tabulate(rows, sc)
    doc = {"evaluation_id": EVALUATION_ID, "replay_id": REPLAY_ID, "method": "btc.context-action.v0.5 (no v0.6 identity)",
           "inputs_sha256": {"view_samples.jsonl": sha(vs_export / "view_samples.jsonl"),
                             **{Path(f).name: sha(Path(f)) for f in sorted(glob.glob(str(journal_export / "sc_*.json")))},
                             "report.json": sha(journal_export / "report.json")},
           "scenario_journal": sc_meta, "integrity": integ,
           "report_cross_check": cross_check(report, tab["reconciliation"], tab["marketview_full_directional"]),
           "reused_commitment": ("app terminal validation of this run: assurance 21/21 PASSED (evaluation.json / report.json "
                                 "local GET exports, R->N diagnosis); per code its adviser checks include "
                                 "adviser_evaluation_chain (observe/reconcile.py -> adviser/reconcile.py). Not re-executed "
                                 "here; check names are not enumerated in those exports."),
           **tab}
    out.mkdir(parents=True, exist_ok=True)
    (out / "tabulation.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with open(out / "samples.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(table)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
