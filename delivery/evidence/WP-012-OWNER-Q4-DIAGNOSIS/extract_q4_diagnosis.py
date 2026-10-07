"""One-time read-only cross-month diagnosis of the Owner v0.4 October-December 2025 evaluations (build c525941).

  v0.4  Oct eval-20261007T094006-67272e  Nov eval-20261007T102821-ae14be  Dec eval-20261007T105636-6d9276
  v0.3  Oct eval-20261006T175135-9ddf6d  Nov eval-20261007T101912-087dd1  Dec eval-20261007T105343-eb536a (comparison)

Not product code and not a reusable analytics framework (it extends the WP-011 October dossier extraction). Inputs,
produced by read-only access and never committed:
  <export>/snapshot.jsonl  one REPEATABLE READ READ ONLY psql transaction (export.sql in this folder): meta, the six
                           evaluation/replay/checkpoint/finish rows (adviser blob excluded), the three pack and cache
                           rows, the complete committed adviser journals and evaluation records of the six runs
  <export>/<cache_id>/     byte copies of the three pinned canonical feed caches

Nothing replays the professional runtime, the evaluator or a counterfactual. Labels:
  STORED    a committed journal/evaluation field (or a count of such fields through the product's own report builder)
  DERIVED   exact Decimal arithmetic on STORED fields, or on pinned 1m trade bars no later than the row's stated cutoff;
            the economic predicate/bounds are the product's pure functions (algotrader.adviser.geometry)
  UNAVAILABLE  not recorded and not derivable without a replay/counterfactual (named per field)

usage: uv run python extract_q4_diagnosis.py <export_dir> <out_dir>
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.adviser import compare as cmp
from algotrader.adviser import geometry as geo
from algotrader.adviser import report3 as r3
from algotrader.adviser import report4 as r4
from algotrader.adviser.core import INITIAL_JOURNAL
from algotrader.adviser.evaluator import INITIAL_RECORDS
from algotrader.feed.ordering import canonical

MONTHS = ("2025-10", "2025-11", "2025-12")
V4 = {"2025-10": "obs-20261007T094006-0f9af7", "2025-11": "obs-20261007T102821-68ca1a",
      "2025-12": "obs-20261007T105636-dba49c"}
V3 = {"2025-10": "obs-20261006T175135-e8267a", "2025-11": "obs-20261007T101912-503fbd",
      "2025-12": "obs-20261007T105343-ae0dcb"}
EVAL = {"obs-20261007T094006-0f9af7": "eval-20261007T094006-67272e",
        "obs-20261007T102821-68ca1a": "eval-20261007T102821-ae14be",
        "obs-20261007T105636-dba49c": "eval-20261007T105636-6d9276",
        "obs-20261006T175135-e8267a": "eval-20261006T175135-9ddf6d",
        "obs-20261007T101912-503fbd": "eval-20261007T101912-087dd1",
        "obs-20261007T105343-ae0dcb": "eval-20261007T105343-eb536a"}
CACHE = {"2025-10": "fc-de5aa4a9d5260d3cfdb135be2d0a90001d6c835f",
         "2025-11": "fc-83bba3018d80145ce65be63d7168efb104d16a49",
         "2025-12": "fc-29ae65c99d81b1d1307c642d14a75cd5fce5d0ef"}
# the adjacent (earlier) pinned cache that holds bars from before a month's 96 h warmup, when copied here
PREV_CACHE = {"2025-11": "2025-10", "2025-12": "2025-11"}
BUILD = "c525941abcf3c127bb070983b436ef8acde1d022"
EXPECTED = {"2025-10": {"a_confirmations": 19, "waits": 14, "calls": 4, "return_calls": 3, "immediate_calls": 1},
            "2025-11": {"a_confirmations": 20, "waits": 16, "calls": 2, "return_calls": 2, "immediate_calls": 0},
            "2025-12": {"a_confirmations": 25, "waits": 16, "calls": 4, "return_calls": 4, "immediate_calls": 0}}
TICK, K_HIST, RR = Decimal("0.1"), Decimal(14), Decimal("1.2")
AGE_1H = timedelta(hours=168)  # MP-001/002/003 register levels.age_1h_hours
MIN = timedelta(minutes=1)
PRICE_BLOCKERS = ("CLOSE_OUTSIDE_RETURN_CORRIDOR", "NO_ROOM_AFTER_COSTS", "AT_OR_BEYOND_INVALIDATION",
                  "REWARD_RISK_BELOW_MINIMUM")
LANDMARK_HORIZONS = ("PIVOT_HIGH_15M", "PIVOT_LOW_15M", "PIVOT_HIGH_1H", "PIVOT_LOW_1H", "PREV_1D_HIGH", "PREV_1D_LOW",
                     "PREV_1W_HIGH", "PREV_1W_LOW", "PREV_1MO_HIGH", "PREV_1MO_LOW")


def dt(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def iso(t):
    return None if t is None else t.isoformat().replace("+00:00", "Z")


def z19(s):
    return None if s is None else str(s)[:19] + "Z"


def dec(x):
    return None if x is None else Decimal(str(x))


def s(x):
    return None if x is None else format(x, "f") if isinstance(x, Decimal) else str(x)


def fx2(x):
    return None if x is None else format(Decimal(x).quantize(Decimal("0.01")), "f")


def pct(x):
    """fraction -> percent, 3 decimals"""
    return None if x is None else format((Decimal(x) * 100).quantize(Decimal("0.001")), "f")


def bps(a, b):
    return fx2(Decimal(10000) * (a - b) / b)


def minutes(a, b):
    return None if a is None or b is None else int((b - a).total_seconds() // 60)


def first(xs, pred=lambda _: True):
    return next((x for x in xs if pred(x)), None)


# ----------------------------------------------------------------------------------------------------------------------
# inputs and provenance
# ----------------------------------------------------------------------------------------------------------------------

def load(export: Path):
    one = defaultdict(dict)
    journal, records, meta = defaultdict(list), defaultdict(list), None
    for line in (export / "snapshot.jsonl").open(encoding="utf-8"):
        if not line.startswith("{"):
            continue
        o = json.loads(line)
        k, v = next(iter(o.items()))
        if k == "meta":
            meta = v
        elif k == "j":
            journal[v["run_id"]].append(v)
        elif k == "er":
            records[v["run_id"]].append(v)
        else:
            one[k][v.get("evaluation_id") if k == "evaluation" else v.get("pack_id") if k == "pack" else
                   v.get("cache_id") if k == "cache" else v.get("replay_id") or v.get("run_id")] = v
    for rid in journal:
        journal[rid].sort(key=lambda e: e["seq"])
        records[rid].sort(key=lambda e: e["seq"])
    return meta, one, journal, records


def verify_chain(rows, finish, key_seq, key_chain, seed):
    h, bad_d, bad_c, gaps = seed, [], [], []
    for i, e in enumerate(rows, start=1):
        if e["seq"] != i:
            gaps.append(e["seq"])
        d = hashlib.sha256(canonical(e["record"])).hexdigest()
        if d != e["digest"]:
            bad_d.append(e["seq"])
        h = hashlib.sha256(bytes.fromhex(h) + bytes.fromhex(d)).hexdigest()
        if h != e["chain"]:
            bad_c.append(e["seq"])
    com = finish["commitment"]
    return {"rows": len(rows), "sequence_gaps": gaps[:10], "digest_mismatches": bad_d[:10],
            "chain_mismatches": bad_c[:10], "recomputed_head": h, "finish_seq": com[key_seq],
            "finish_chain": com[key_chain],
            "matches_finish_commitment": (not gaps and not bad_d and not bad_c and h == com[key_chain]
                                          and len(rows) == com[key_seq])}


def load_cache(export: Path, cid: str, pinned_sha: str):
    root = export / cid
    msha = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bad, bars, fam = [], {}, Counter()
    for p in man["partitions"]:
        blob = (root / p["file"]).read_bytes()
        if hashlib.sha256(blob).hexdigest() != p["sha256"]:
            bad.append(p["file"])
            continue
        for line in gzip.decompress(blob).splitlines():
            ev = json.loads(line)
            t = dt(ev["event_time"])
            fam[(ev["channel"]["family"], ev["kind"], t >= datetime(2026, 1, 1, tzinfo=t.tzinfo))] += 1
            if ev["channel"]["family"] != "trade_bar_1m" or ev["kind"] != "bar_observation":
                continue
            pl = ev["payload"]
            bars[t] = tuple(dec(pl[k]) for k in ("open", "high", "low", "close"))
    info = {"cache_id": cid, "manifest_sha256": msha, "pinned_manifest_sha256": pinned_sha,
            "manifest_matches_pin": msha == pinned_sha, "partitions": len(man["partitions"]),
            "partitions_failing_sha256": bad, "trade_minutes": len(bars),
            "first_trade_minute": iso(min(bars)), "last_trade_minute": iso(max(bars)),
            "events_on_or_after_2026_01_01": {f"{f}/{k}": n for (f, k, tail), n in sorted(fam.items()) if tail}}
    return info, bars


def bar(bars, start, cutoff):
    """A pinned 1m trade bar [start, start+1m) used only when start+1m <= cutoff (admitted at its close)."""
    if start + MIN > cutoff:
        raise RuntimeError(f"bar {iso(start)} is after cutoff {iso(cutoff)}")
    return bars[start]


def build_report(rid, one, journal, records):
    rep = one["replay"][rid]
    eng = rep["engine"]
    b = r4 if eng["adviser"]["method"] == "v0.4" else r3
    return b.build(engine=eng, journal=journal[rid], records=records[rid],
                   view=(one["checkpoint"].get(rid) or {}).get("adviser_view"), status=rep["status"],
                   clock_end_reached=rid in one["finish"])


def provenance(meta, one, journal, records, caches, export):
    runs = {}
    for rid, ev_id in EVAL.items():
        ev, rep = one["evaluation"][ev_id], one["replay"][rid]
        runs[rid] = {
            "evaluation_id": ev_id, "status": rep["status"], "code_version": rep["config"]["code_version"],
            "engine_method": rep["engine"]["adviser"]["method"],
            "model": rep["engine"]["adviser"]["identity"]["model"],
            "rules_version": rep["engine"]["adviser"]["identity"]["rules_version"],
            "identity_sha256": rep["engine"]["adviser"]["identity"]["identity_sha256"],
            "dataset_id": ev["dataset_id"], "preset_id": ev["preset_id"],
            "pinned_cache_manifest_sha256": ev["corpus"]["pack"]["feed"]["cache_manifest_sha256"],
            "pack_manifest_sha256": ev["corpus"]["pack"].get("manifest_sha256")
            or one["pack"][ev["dataset_id"]]["manifest_sha256"],
            "windows": {k: rep["engine"]["adviser"][k] for k in ("warmup_start", "eval_start", "eval_end", "tail_end",
                                                                  "clock_end")},
            "assurance": {k: rep["assurance"][k] for k in ("state", "validator", "validator_version",
                                                          "checks_passed", "checks_total")},
            "adviser_format": one["finish"][rid]["adviser_format"],
            "checkpoint": {k: one["checkpoint"][rid][k] for k in ("cursor", "info_time")},
            "journal": verify_chain(journal[rid], one["finish"][rid], "journal_seq", "journal_chain", INITIAL_JOURNAL),
            "evaluation_records": verify_chain(records[rid], one["finish"][rid], "evaluation_seq", "evaluation_chain",
                                               INITIAL_RECORDS),
            "journal_kinds": dict(Counter(e["kind"] for e in journal[rid]))}
    packs = {}
    for m in MONTHS:
        ev = one["evaluation"][EVAL[V4[m]]]
        p = one["pack"][ev["dataset_id"]]
        c = one["cache"][p["cache_id"]]
        packs[m] = {"pack_id": p["pack_id"], "pack_manifest_sha256": p["manifest_sha256"],
                    "cache_id": p["cache_id"], "cache_row_manifest_sha256": c["cache_manifest_sha256"],
                    "pack_row_cache_manifest_sha256": p["cache_manifest_sha256"],
                    "content_identity": p["content_identity"], "event_count": p["event_count"],
                    "cache_row_event_count": c["event_count"],
                    "windows": ev["corpus"]["pack"]["preset"] | {"pack_windows": ev["corpus"]["pack"].get("windows")},
                    "coverage_trade": [x for x in ev["corpus"]["pack"].get("coverage") or []
                                       if x["family"] == "trade_bar_1m"],
                    "sources": ev["corpus"]["pack"]["sources"],
                    "both_runs_pin_this_cache": all(one["evaluation"][EVAL[r]]["corpus"]["pack"]["feed"]["cache_id"]
                                                    == p["cache_id"] for r in (V4[m], V3[m]))}
    sha = hashlib.sha256((export / "snapshot.jsonl").read_bytes()).hexdigest()
    return {"db_snapshot": meta, "snapshot_jsonl_sha256_not_committed": sha, "build": BUILD, "runs": runs,
            "packs": packs, "caches": caches}


def comparability(one, reports):
    out = {}
    for m in MONTHS:
        facts = []
        for rid in (V3[m], V4[m]):
            rep = one["replay"][rid]
            ev = one["evaluation"][EVAL[rid]]
            st = rep["assurance"]["state"]
            facts.append(cmp.run_facts(ev, rep, {"adviser": reports[rid], "operation": {"assurance": {"state": st}},
                                                 "validation": {"outcome": st}}))
        c = cmp.comparability(facts[0], facts[1])
        out[m] = {"baseline": EVAL[V3[m]], "candidate": EVAL[V4[m]], "verdict_recomputed": c["verdict"],
                  "differences": c["differences"], "incomplete": c["incomplete"],
                  "baseline_build": one["replay"][V3[m]]["config"]["code_version"],
                  "note": "product compare.comparability on stored rows; validation outcome taken from replay "
                          "assurance state (the API's validation summary is not stored as a row)"}
    return out


# ----------------------------------------------------------------------------------------------------------------------
# indexes over one run
# ----------------------------------------------------------------------------------------------------------------------

class Run:
    def __init__(self, rid, one, journal, records):
        self.rid = rid
        adv = one["replay"][rid]["engine"]["adviser"]
        self.es, self.ee = dt(adv["eval_start"]), dt(adv["eval_end"])
        self.warmup_start, self.clock_end = dt(adv["warmup_start"]), dt(adv["clock_end"])
        self.j = journal[rid]
        self.scen = defaultdict(list)
        self.ent = defaultdict(list)
        self.rev = defaultdict(list)
        self.obs = defaultdict(list)
        self.mv = []
        self.calls = {}
        self.lm = []
        for e in self.j:
            r, k = e["record"], e["kind"]
            if k == "scenario":
                self.scen[r["scenario_id"]].append(e)
            elif k == "entry_attempt":
                self.ent[r["entry_attempt_id"]].append(e)
            elif k == "call_revision":
                self.rev[r["call_id"]].append(e)
            elif k == "observation":
                self.obs[r["name"]].append(e)
            elif k == "market_view":
                self.mv.append(e)
            elif k == "call":
                self.calls[r["call_id"]] = e
            elif k == "landmark":
                self.lm.append(e)
        self.paths = defaultdict(dict)
        self.view_samples = []
        for x in records[rid]:
            if x["kind"] == "path":
                self.paths[x["record"]["call_id"]][x["record"]["variant"]] = x["record"]
            elif x["kind"] == "view_sample":
                self.view_samples.append(x["record"])
        self.by_prefix = defaultdict(list)
        for sid in self.scen:
            self.by_prefix[sid.rsplit("-", 1)[0]].append(sid)

    def in_eval(self, rec):
        return self.es <= dt(rec["env"]["published_at"]) < self.ee

    def routed_a(self):
        """First routing record per A child in the evaluation window (exactly as report3)."""
        seen = {}
        for eid, recs in self.ent.items():
            for e in recs:
                r = e["record"]
                if r["family"] == "A" and self.in_eval(r) and (r.get("diagnostic") or {}).get("in_D") is not None:
                    seen[eid] = e
                    break
        return sorted(seen.values(), key=lambda e: e["seq"])

    def context_at(self, t):
        """STORED: latest published observation/view at or before cutoff t (published on change only)."""
        out = {}
        for n in ("context", "phase", "dislocation", "readiness"):
            x = None
            for e in self.obs[n]:
                if dt(e["clock_time"]) <= t:
                    x = e
                else:
                    break
            out[n] = None if x is None else {"category": x["record"]["category"], "since": z19(x["clock_time"])}
        m = None
        for e in self.mv:
            if dt(e["clock_time"]) <= t:
                m = e
            else:
                break
        out["market_view"] = None if m is None else {
            "since": z19(m["clock_time"]), "table_row": m["record"]["table_row"],
            "expected_direction": m["record"]["expected_direction"], "phase": m["record"]["phase"],
            "observed_context": m["record"]["observed_context"], "blockers": m["record"]["blockers"]}
        return out


def ctx_short(c):
    mv = c.get("market_view") or {}
    return (f"ctx {(c.get('context') or {}).get('category')} / phase {(c.get('phase') or {}).get('category')} / "
            f"MV {mv.get('table_row')} {mv.get('expected_direction')}")


# ----------------------------------------------------------------------------------------------------------------------
# per owner (structural scenario) lineage
# ----------------------------------------------------------------------------------------------------------------------

def anchors_of(run, sid):
    out = []
    for e in run.scen[sid]:
        r = e["record"]
        if r["transition"] in ("ARM", "REVISE", "REARM", "ANCHOR_LOST"):
            pa = r.get("previous_anchor") or {}
            out.append({"at": z19(e["clock_time"]), "transition": r["transition"], "epoch": r.get("anchor_epoch"),
                        "R": r.get("reaction_level"), "K": r.get("trigger_level"), "V": r.get("invalidation_level"),
                        "source": r.get("anchor_source"), "published_at": r.get("anchor_published_at"),
                        "published_cursor": r.get("anchor_published_cursor"), "status": r.get("anchor_status"),
                        "reason": r.get("reason"),
                        "lost_anchor": ({k: pa.get(k) for k in ("epoch", "R", "K", "V", "source", "status", "interval",
                                                                 "interval_end", "published_at")}
                                        if r["transition"] == "ANCHOR_LOST" else None)})
    return out


def scenario_summary(run, sid):
    recs = run.scen[sid]
    by = defaultdict(list)
    for e in recs:
        by[e["record"]["transition"]].append(e)
    birth = by["BIRTH"][0]
    conf = by["CONFIRM"][0] if by["CONFIRM"] else None
    term = by["TERMINAL"][-1] if by["TERMINAL"] else None
    st = birth["record"]["setup"]
    return {
        "scenario_id": sid, "direction": birth["record"]["direction"], "family": birth["record"]["family"],
        "birth_published": z19(birth["clock_time"]), "impulse_A": st["impulse_A"], "impulse_B": st["impulse_B"],
        "birth_s15": st["s15"], "z": st["zone_halfwidth"], "original_expiry": birth["record"]["original_expiry"],
        "first_arm_at": z19(by["ARM"][0]["clock_time"]) if by["ARM"] else None,
        "destination_monitoring_from": (conf or term or birth)["record"].get("destination_monitoring_from"),
        "anchor_losses_before_confirmation": sum(1 for e in by["ANCHOR_LOST"]
                                                 if conf is None or e["seq"] < conf["seq"]),
        "rearms_before_confirmation": sum(1 for e in by["REARM"] if conf is None or e["seq"] < conf["seq"]),
        "revisions_before_confirmation": sum(1 for e in by["REVISE"] if conf is None or e["seq"] < conf["seq"]),
        "anchor_epoch_at_confirmation": conf["record"].get("anchor_epoch") if conf else None,
        "confirmed_at": conf["record"]["confirmed_at"] if conf else None,
        "confirmation_close": conf["record"].get("confirmation_close") if conf else None,
        "confirmation_scale": conf["record"].get("confirmation_scale") if conf else None,
        "confirmed_deadline": conf["record"].get("confirmed_deadline") if conf else None,
        "scenario_progress_check_at": conf["record"].get("progress_check_at") if conf else None,
        "scenario_terminal": (f"{term['record']['terminal_state']}:{str(term['record']['reason']).split(':')[0]}"
                              if term else None),
        "scenario_terminal_reason": term["record"]["reason"] if term else None,
        "scenario_terminal_at": z19(term["clock_time"]) if term else None,
        "owner_releases": len(by["OWNER_RELEASE"]),
    }


def v3_same_boundary(v3run, sid):
    """STORED: the v0.3 baseline scenario born at the same 15m boundary, family and direction (ids differ by hash)."""
    out = []
    for vsid in v3run.by_prefix.get(sid.rsplit("-", 1)[0], []):
        ss = scenario_summary(v3run, vsid)
        ent = [e["record"] for e in v3run.ent.get(f"{vsid}#entry", [])]
        call = first(v3run.calls.values(), lambda c: c["record"]["scenario_id"] == vsid)
        out.append(f"{vsid}: confirmed {ss['confirmed_at'] or 'no'}; terminal {ss['scenario_terminal']} at "
                   f"{ss['scenario_terminal_at']}; entry {ent[-1]['transition'] + ':' + str(ent[-1]['reason'])[:60] if ent else 'none'}"
                   f"; call {call['record']['call_id'] if call else 'none'}")
    return out or ["no v0.3 scenario at the same boundary/direction"]


# ----------------------------------------------------------------------------------------------------------------------
# the WAITs: minute reconstruction (validated against STORED blocker changes), as in the October dossier
# ----------------------------------------------------------------------------------------------------------------------

def wait_minutes(run, first_rec, bars):
    eid = first_rec["record"]["entry_attempt_id"]
    recs = run.ent[eid]
    r0 = first_rec["record"]
    g0 = r0["geometry"]
    d = 1 if r0["direction"] == "LONG" else -1
    sid = r0["scenario_id"]
    dest = Decimal(run.scen[sid][0]["record"]["destination"])
    conf_at = dt(r0["clocks"]["confirmed_at"])
    end_rec = recs[-1]
    end_t = dt(end_rec["clock_time"])
    v = Decimal(g0["V"])
    lo_s, hi_s = (Decimal(x) for x in g0["corridor"].split(".."))
    caps = end_rec["record"]["cap_history"]
    stored = [(dt(x["clock_time"]), x["record"]["blockers"]) for x in recs if x["record"]["transition"] != "CAP_REVISION"]
    rows = []
    t = conf_at
    while t + MIN <= end_t:
        o, h, lo, c = bar(bars, t, end_t)
        disp = t + MIN
        cap = Decimal(next(x["cap"] for x in reversed(caps) if dt(x["since"]) <= t))
        cap_d = Decimal(next(x["cap"] for x in reversed(caps) if dt(x["since"]) <= disp))
        cor = (lo_s, min(hi_s, cap_d - TICK)) if d > 0 else (max(lo_s, cap_d + TICK), hi_s)
        econ = geo.admissible_bounds(d, cor, v, cap_d, K_HIST, RR, TICK) if cor[0] <= cor[1] else None
        chk = geo.predicate(d, c, v, cap_d, K_HIST, RR)
        derived = sorted(set((["CLOSE_OUTSIDE_RETURN_CORRIDOR"] if not cor[0] <= c <= cor[1] else [])
                             + ([chk.reason] if not chk.ok else [])))
        in_force_all = [bl for (ct, bl) in stored if ct <= disp][-1]
        in_force = [b for b in in_force_all if b in PRICE_BLOCKERS]
        non_price = sorted(b for b in in_force_all if b not in PRICE_BLOCKERS)
        v_c = lo <= v if d > 0 else h >= v
        cap_c = h >= cap if d > 0 else lo <= cap
        dest_c = h >= dest if d > 0 else lo <= dest
        # a terminal at this dispatch (context/expiry/contact) is processed before the return gate: not a sample
        terminal_here = disp == end_t and end_rec["record"]["transition"] == "TERMINAL"
        sampled = disp < dt(r0["clocks"]["setup_expiry"]) and not (v_c or cap_c or dest_c or terminal_here)
        rows.append({"close": c, "high": h, "low": lo, "econ": econ, "in_cor": cor[0] <= c <= cor[1],
                     "in_econ": bool(econ and econ[0] <= c <= econ[1]),
                     "touch_econ": bool(econ and (lo <= econ[1] if d > 0 else h >= econ[0])),
                     "sampled": sampled, "equal": (derived == sorted(in_force)) if sampled else None,
                     "non_price": non_price if sampled else [],
                     "margin": chk.margin})
        t += MIN
    samp = [x for x in rows if x["sampled"]]
    best = (min(x["close"] for x in samp) if d > 0 else max(x["close"] for x in samp)) if samp else None
    edge = None
    if samp and samp[-1]["econ"]:
        edge = samp[-1]["econ"][1] if d > 0 else samp[-1]["econ"][0]
    eq = [x["equal"] for x in rows if x["equal"] is not None]
    return {"cutoff": iso(end_t), "minutes_after_confirmation": len(rows), "return_samples": len(samp),
            "closes_in_corridor": sum(1 for x in samp if x["in_cor"]),
            "closes_in_economic_region": sum(1 for x in samp if x["in_econ"]),
            "intrabar_touches_of_economic_region": sum(1 for x in rows if x["touch_econ"]),
            "best_sampled_close_toward_region": s(best), "economic_edge_last": s(edge),
            "best_close_distance_to_region_bps": ((bps(best, edge) if d > 0 else bps(edge, best))
                                                  if best is not None and edge is not None else None),
            "derived_blockers_equal_stored": f"{sum(eq)}/{len(eq)}",
            "sampled_minutes_with_non_price_blockers_STORED": dict(Counter(b for x in rows for b in x["non_price"]))}


# ----------------------------------------------------------------------------------------------------------------------
# classification of every A confirmation (DERIVED from STORED routing/ending reasons)
# ----------------------------------------------------------------------------------------------------------------------

def classify(route_tr, route_reason, end_tr, end_reason, call_id):
    if call_id:
        return "CALL"
    rr = str(route_reason).split(":")[0]
    if route_tr != "WAIT_OPEN":
        return {"NO_ECONOMIC_RETURN_REGION": "GEOMETRY_AT_CONFIRMATION:NO_ECONOMIC_RETURN_REGION",
                "AT_OPPOSING_AREA": "CAP_OR_OBSTACLE_AT_CONFIRMATION:AT_OPPOSING_AREA",
                "PRE_ENTRY_TARGET_CONTACT": "CAP_OR_OBSTACLE_AT_CONFIRMATION:PRE_ENTRY_TARGET_CONTACT"}.get(
            rr, f"OTHER_AT_CONFIRMATION:{rr}")
    er = str(end_reason)
    if end_tr == "REJECT" or er.split(":")[0] in ("SLOT_OCCUPIED", "PRIORITY", "CONFLICTED"):
        return f"SELECTION:{er.split(':')[0]}"
    if er.startswith("ORIGINAL_SETUP_DEADLINE"):
        return "NO_RETURN:ORIGINAL_SETUP_DEADLINE"
    if er.startswith("PRE_ENTRY_TARGET_CONTACT"):
        return "CAP_OR_OBSTACLE_DURING_WAIT:PRE_ENTRY_TARGET_CONTACT"
    if er.startswith("SCENARIO_TERMINAL"):
        return "TERMINAL_DURING_WAIT:" + ":".join(er.split(":")[1:3])
    if er.startswith("CONTEXT_FORBIDDEN") or "DISLOCATION" in er or "EXECUTION" in er:
        return f"CONTEXT_OR_EXECUTION_RESTRICTION:{er.split(':')[0]}"
    return f"OTHER_DURING_WAIT:{er.split(':')[0]}"


def confirmations(run, v3run, month, bars, prev_bars):
    rows = []
    for e in run.routed_a():
        r = e["record"]
        eid, sid = r["entry_attempt_id"], r["scenario_id"]
        g = r["geometry"]
        recs = run.ent[eid]
        end = recs[-1]["record"]
        call_id = end.get("call_id") if end["transition"] == "ISSUE" else None
        usable = first(recs, lambda x: x["record"]["transition"] == "RETURN_USABLE")
        ss = scenario_summary(run, sid)
        conf_at = dt(r["clocks"]["confirmed_at"])
        ctx = run.context_at(conf_at)
        lm = r.get("limiting_landmark") or {}
        row = {
            "month": month, "run": run.rid, "entry_attempt_id": eid, "scenario_id": sid, "direction": r["direction"],
            "birth_published": ss["birth_published"], "first_arm_at": ss["first_arm_at"],
            "anchor_losses_before_confirmation": ss["anchor_losses_before_confirmation"],
            "rearms_before_confirmation": ss["rearms_before_confirmation"],
            "anchor_epoch_at_confirmation": ss["anchor_epoch_at_confirmation"],
            "confirmed_after_replacement": ss["rearms_before_confirmation"] > 0,
            "confirmed_at": iso(conf_at), "setup_expiry": r["clocks"].get("setup_expiry"),
            "hard_deadline": r["clocks"].get("hard_deadline"),
            "R": g.get("R"), "K_trigger": g.get("K_trigger"), "V": g.get("V"),
            "confirmation_close": g.get("confirmation_close"), "S15": g.get("S15"), "T_confirm": g.get("T_confirm"),
            "target_type": g.get("target_type"), "limiting_landmark": lm.get("type"),
            "limiting_is_own_impulse_B": lm.get("landmark_id") == f"{sid}#B" if lm else None,
            "destination_B": ss["impulse_B"],
            "G_bps": fx2(g.get("G")), "Q_bps": fx2(g.get("Q")), "margin_bps": fx2(g.get("margin")),
            "I0": g.get("I0"), "corridor": g.get("corridor"), "economic_fixed_k": g.get("economic_fixed_k"),
            "in_D": r["diagnostic"]["in_D"], "in_N": r["diagnostic"].get("in_N"),
            "exclusion": r["diagnostic"].get("exclusion"), "blockers_at_confirmation": r["blockers"],
            "routing": r["transition"], "routing_reason": r["reason"],
            "wait_end_transition": end["transition"] if r["transition"] == "WAIT_OPEN" else None,
            "wait_end_reason": end["reason"] if r["transition"] == "WAIT_OPEN" else None,
            "wait_end_at": z19(recs[-1]["clock_time"]) if r["transition"] == "WAIT_OPEN" else None,
            "usable_return_at": z19(usable["clock_time"]) if usable else None,
            "usable_return_price": usable["record"]["geometry"].get("price") if usable else None,
            "cap_revisions": sum(1 for x in recs if x["record"]["transition"] == "CAP_REVISION"),
            "call_id": call_id,
            "scenario_terminal": ss["scenario_terminal"], "scenario_terminal_at": ss["scenario_terminal_at"],
            "minutes_confirmation_to_scenario_terminal": minutes(conf_at, dt(ss["scenario_terminal_at"]))
            if ss["scenario_terminal_at"] else None,
            "context_at_confirmation": (ctx.get("context") or {}).get("category"),
            "phase_at_confirmation": (ctx.get("phase") or {}).get("category"),
            "market_view_at_confirmation": ((ctx.get("market_view") or {}).get("table_row")),
            "v03_same_boundary": v3_same_boundary(v3run, sid),
        }
        row["classification"] = classify(r["transition"], r["reason"], row["wait_end_transition"],
                                         row["wait_end_reason"], call_id)
        row["DERIVED_wait"] = wait_minutes(run, e, bars) if r["transition"] == "WAIT_OPEN" else None
        row["DERIVED_target_distance_bps_from_close"] = (
            (bps(Decimal(g["T_confirm"]), Decimal(g["confirmation_close"])) if r["direction"] == "LONG" else
             bps(Decimal(g["confirmation_close"]), Decimal(g["T_confirm"]))) if g.get("T_confirm") else None)
        row["DERIVED_V_distance_bps_from_close"] = (
            (bps(Decimal(g["confirmation_close"]), Decimal(g["V"])) if r["direction"] == "LONG" else
             bps(Decimal(g["V"]), Decimal(g["confirmation_close"]))) if g.get("V") else None)
        row["warmup_limits"] = warmup_flags(run, conf_at)
        rows.append(row)
    return rows


# ----------------------------------------------------------------------------------------------------------------------
# the calls
# ----------------------------------------------------------------------------------------------------------------------

def median_range_bps(bars, t, n=60):
    """DERIVED: median (high-low)/close in bps of the n complete 1m trade bars ending at cutoff t."""
    xs = []
    for i in range(n, 0, -1):
        st = t - i * MIN
        if st in bars:
            o, h, lo, c = bar(bars, st, t)
            xs.append(Decimal(10000) * (h - lo) / c)
    return fx2(statistics.median(xs)) if xs else None


def cap_at(cap_history, t):
    x = [c for c in cap_history if dt(c["since"]) <= t]
    return Decimal(x[-1]["cap"]) if x else None


def call_rows(run, v3run, month, bars):
    out = []
    for cid, ce in sorted(run.calls.items(), key=lambda kv: kv[1]["seq"]):
        c = ce["record"]
        if not run.es <= dt(c["issued_at"]) < run.ee:
            continue
        sid, eid = c["scenario_id"], c["attempt_id"]
        d = 1 if c["direction"] == "LONG" else -1
        ss = scenario_summary(run, sid)
        recs = run.ent[eid]
        first_route = first(recs, lambda x: (x["record"].get("diagnostic") or {}).get("in_D") is not None)
        fr = first_route["record"]
        g0 = fr["geometry"]
        usable = first(recs, lambda x: x["record"]["transition"] == "RETURN_USABLE")
        conf_at, iss_at = dt(c["confirmed_at"]), dt(c["issued_at"])
        p = run.paths.get(cid, {})
        prim = p.get("PRIMARY") or {}
        ent_t = dt(prim["entry"]["time_end"]) if prim.get("entry") else None
        ent_p = Decimal(prim["entry"]["price"]) if prim.get("entry") else None
        v = Decimal(c["invalidation"])
        t_issue = Decimal(c["target"])
        # an IMMEDIATE call has no cap history: its target at issue is the active cap
        cap_e = (cap_at(c["cap_history"], ent_t) or t_issue) if ent_t else None
        revs = run.rev.get(cid, [])
        closed = first(revs, lambda x: x["record"]["entry_status"] != "AVAILABLE")
        reopen = sum(1 for a, b in zip(revs, revs[1:]) if a["record"]["entry_status"] != "AVAILABLE"
                     and b["record"]["entry_status"] == "AVAILABLE")
        term = first(revs, lambda x: x["record"]["thesis_status"] != "ONGOING")
        hd = dt(c["hard_deadline"])
        chk_e = geo.predicate(d, ent_p, v, cap_e, K_HIST, RR) if ent_p is not None and cap_e is not None else None
        act = c["actionability"]
        mrb = median_range_bps(bars, iss_at)
        risk_iss = Decimal(act["risk_bps"])
        risk_ent = Decimal(10000) * d * (ent_p - v) / ent_p if ent_p is not None else None
        scale_bps = Decimal(10000) * Decimal(c["frozen_scale"]) / Decimal(c["issue_reference"])
        ctx = {k: run.context_at(t) for k, t in (("confirmation", conf_at),
                                                 ("wait_open", conf_at if fr["transition"] == "WAIT_OPEN" else None),
                                                 ("issue", iss_at), ("primary_entry", ent_t),
                                                 ("primary_exit", dt(prim["exit"]["time_end"]) if prim.get("exit")
                                                  else None)) if t is not None}
        row = {
            "month": month, "run": run.rid, "evaluation_id": EVAL[run.rid], "call_id": cid, "owner": sid,
            "direction": c["direction"], "family": c["family"], "entry_mode": c["entry_mode"],
            "owner_STORED": {k: ss[k] for k in ("birth_published", "impulse_A", "impulse_B", "birth_s15", "z",
                                                "original_expiry", "first_arm_at", "destination_monitoring_from",
                                                "owner_releases")},
            "anchors_STORED": anchors_of(run, sid),
            "anchor_epoch_at_confirmation": ss["anchor_epoch_at_confirmation"],
            "anchor_losses_before_confirmation": ss["anchor_losses_before_confirmation"],
            "confirmed_after_replacement": ss["rearms_before_confirmation"] > 0,
            "sequence_STORED": {
                "confirmed_at": iso(conf_at), "confirmation_close": ss["confirmation_close"],
                "routing": fr["transition"], "routing_reason": fr["reason"], "blockers_at_confirmation": fr["blockers"],
                "wait_open_at": iso(conf_at) if fr["transition"] == "WAIT_OPEN" else None,
                "wait_blocker_changes": sum(1 for x in recs if x["record"]["transition"] == "BLOCKERS"),
                "usable_return_at": z19(usable["clock_time"]) if usable else None,
                "usable_return_minute": usable["record"]["reason"] if usable else None,
                "issued_at": c["issued_at"], "issue_reference_price": c["issue_reference"],
                "primary_entry_at": iso(ent_t), "primary_entry_price": s(ent_p),
                "primary_exit_at": prim.get("exit", {}).get("time_end"), "primary_exit_price": prim.get("exit", {}).get("price"),
                "primary_exit_reason": prim.get("exit", {}).get("reason")},
            "geometry_STORED": {
                "R": g0.get("R"), "K_trigger": g0.get("K_trigger"), "V_rounded": g0.get("V"), "stop_guidance": c["invalidation"],
                "T_confirm": g0.get("T_confirm"), "T_at_issue": c["target"], "target_type": c["target_type"],
                "target_origin": (c["cap_history"][-1]["zone_id"] if c["cap_history"] else None),
                "limiting_landmark_at_confirmation": {k: (fr.get("limiting_landmark") or {}).get(k)
                                                      for k in ("type", "price", "landmark_id", "age_minutes")},
                "scenario_destination_B": ss["impulse_B"], "scale_S15_at_confirmation": g0.get("S15"),
                "issue_scale": c["issue_scale"], "frozen_scale": c["frozen_scale"], "z": ss["z"],
                "cap_history": c["cap_history"], "cap_revisions_during_wait":
                    sum(1 for x in recs if x["record"]["transition"] == "CAP_REVISION"),
                "I0": g0.get("I0"), "corridor": g0.get("corridor"), "economic_at_confirmation": g0.get("economic_fixed_k"),
                "structural_area_at_issue": c["structural_area"], "admissible_bounds_at_issue": act["admissible_bounds"]},
            "economics": {
                "confirmation_STORED": {"G_bps": fx2(g0.get("G")), "Q_bps": fx2(g0.get("Q")),
                                        "margin_bps": fx2(g0.get("margin"))},
                "issue_STORED": {"gain_bps": fx2(act["gain_bps"]), "risk_bps": fx2(act["risk_bps"]),
                                 "margin_bps": fx2(act["reward_risk_margin"]), "cost_envelope_bps": act["cost_envelope_bps"]},
                "primary_entry_DERIVED": ({"cutoff": iso(ent_t), "price_STORED": s(ent_p), "cap_active": s(cap_e),
                                           "G_bps": fx2(chk_e.g), "Q_bps": fx2(chk_e.q), "margin_bps": fx2(chk_e.margin),
                                           "predicate": chk_e.reason or "PASS"} if chk_e else "UNAVAILABLE"),
                "residual_minutes_DERIVED": {
                    "at_confirmation_to_setup_expiry": minutes(conf_at, dt(fr["clocks"]["setup_expiry"]))
                    if fr["clocks"].get("setup_expiry") else None,
                    "at_confirmation_to_hard_deadline": minutes(conf_at, hd),
                    "at_issue_to_hard_deadline": minutes(iss_at, hd),
                    "at_primary_entry_to_hard_deadline": minutes(ent_t, hd) if ent_t else None},
                "stop_distance_DERIVED": {
                    "risk_bps_at_issue_STORED": fx2(risk_iss), "risk_bps_at_primary_entry": fx2(risk_ent),
                    "risk_in_scale_units_at_issue": fx2(risk_iss / scale_bps),
                    "scale_bps_at_issue": fx2(scale_bps),
                    "median_1m_range_bps_60min_before_issue": mrb,
                    "risk_at_issue_over_median_1m_range": fx2(risk_iss / Decimal(mrb)) if mrb else None,
                    "gain_in_scale_units_at_issue": fx2(Decimal(act["gain_bps"]) / scale_bps)}},
            "entry_window_STORED": {
                "issued_at": c["issued_at"], "first_closed_at": z19(closed["clock_time"]) if closed else None,
                "first_closed_reasons": closed["record"]["entry_reasons"] if closed else None,
                "available_minutes_DERIVED": minutes(iss_at, dt(closed["clock_time"])) if closed else None,
                "reopenings": reopen, "setup_expiry": fr["clocks"].get("setup_expiry"),
                "hard_deadline": c["hard_deadline"], "hard_deadline_origin": c["hard_deadline_origin"],
                "call_progress_check_at": c["progress_check_at"], "scenario_progress_check_at": ss["scenario_progress_check_at"],
                "expected_minutes": c["expected_minutes"], "minimum_residual_minutes": c["minimum_residual_minutes"],
                "progress_check_reached_before_guidance_end": (dt(c["progress_check_at"]) <= dt(term["clock_time"]))
                if term else None},
            "revisions_STORED": [{"at": z19(x["clock_time"]), "rev": x["record"]["revision"], "changed": x["record"]["changed"],
                                  "entry_status": x["record"]["entry_status"], "entry_reasons": x["record"]["entry_reasons"],
                                  "thesis_status": x["record"]["thesis_status"],
                                  "terminal_reason": x["record"]["terminal_reason"],
                                  "remaining_minutes": x["record"]["remaining_minutes"],
                                  "progress_max_favorable_scale": fx2(x["record"].get("progress_max_favorable_scale"))}
                                 for x in revs],
            "outcomes_STORED": {
                "scenario": {"terminal": ss["scenario_terminal"], "reason": ss["scenario_terminal_reason"],
                             "at": ss["scenario_terminal_at"]},
                "guidance": {"thesis_status": term["record"]["thesis_status"] if term else None,
                             "terminal_reason": term["record"]["terminal_reason"] if term else None,
                             "at": z19(term["clock_time"]) if term else None},
                "paths": {k: {"status": x.get("status"), "exit_class": x.get("exit_class"),
                              "entry": (x.get("entry") or {}).get("price"), "entry_at": (x.get("entry") or {}).get("time_end"),
                              "exit": (x.get("exit") or {}).get("price"), "exit_at": (x.get("exit") or {}).get("time_end"),
                              "price_net_pct": pct(x.get("price_net")), "stress_price_net_pct": pct(x.get("stress_price_net")),
                              "gross_pct": pct(x.get("gross")), "mfe_pct": pct(x.get("mfe")), "mae_pct": pct(x.get("mae")),
                              "held_minutes": x.get("held_minutes"), "funding_status": x.get("funding_status"),
                              "entry_attempts": x.get("entry_attempts"), "rejected_opens": x.get("rejected_opens")}
                          for k, x in sorted(p.items())}},
            "context_STORED": {k: v for k, v in ctx.items()},
            "v03_same_boundary_STORED": v3_same_boundary(v3run, sid),
            "warmup_limits": warmup_flags(run, conf_at),
        }
        out.append(row)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# warmup and tail boundaries
# ----------------------------------------------------------------------------------------------------------------------

_LM_FIRST: dict[str, dict] = {}


def landmark_first(run):
    if run.rid not in _LM_FIRST:
        f = {}
        for e in run.lm:
            f.setdefault(e["record"]["landmark_type"], z19(e["clock_time"]))
        _LM_FIRST[run.rid] = f
    return _LM_FIRST[run.rid]


def warmup_flags(run, t):
    """STORED/DERIVED: which landmark horizons could not yet hold their full registered memory at cutoff t."""
    f = landmark_first(run)
    return {"pivot_1h_memory_truncated": t < run.warmup_start + AGE_1H,
            "prev_1w_not_yet_published": f.get("PREV_1W_HIGH") is None or t < dt(f["PREV_1W_HIGH"]),
            "prev_1mo_not_yet_published": f.get("PREV_1MO_HIGH") is None or t < dt(f["PREV_1MO_HIGH"])}


def pre_warmup_bound(row, run, prev_bars):
    """DERIVED, descriptive: did any complete 1m trade bar in [cutoff-168h, warmup_start) - real history the run never
    admitted, but known before the cutoff - trade inside the call's issue-to-target range? Zero means no 1h pivot from
    that interval could lie between entry and target. It is NOT a reconstruction of the landmark logic or of a call."""
    if prev_bars is None:
        return "UNAVAILABLE (the earlier pinned source cache was not copied for this month)"
    t = dt(row["sequence_STORED"]["issued_at"])
    lo_t, hi_t = t - AGE_1H, run.warmup_start
    ref, tgt = Decimal(row["sequence_STORED"]["issue_reference_price"]), Decimal(row["geometry_STORED"]["T_at_issue"])
    a, b = min(ref, tgt), max(ref, tgt)
    n = inside = 0
    hi = lo = None
    st = lo_t.replace(second=0, microsecond=0)
    while st + MIN <= hi_t:
        if st in prev_bars:
            _o, h, l_, _c = prev_bars[st]
            n += 1
            hi = h if hi is None or h > hi else hi
            lo = l_ if lo is None or l_ < lo else lo
            if l_ <= b and h >= a:
                inside += 1
        st += MIN
    return {"interval": [iso(lo_t), iso(hi_t)], "bars": n, "high": s(hi), "low": s(lo),
            "issue_to_target_range": [s(a), s(b)], "bars_trading_inside_range": inside}


def prev_week_extremes(run, t, prev_bars, bars):
    """DERIVED, descriptive: the complete previous UTC Monday-week high/low known before cutoff t, from pinned bars."""
    monday = (t - timedelta(days=t.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    a, b = monday - timedelta(days=7), monday
    hi = lo = None
    n = 0
    st = a
    while st + MIN <= b:
        x = (bars.get(st) if st >= run.warmup_start else None) or (prev_bars or {}).get(st)
        if x:
            n += 1
            hi = x[1] if hi is None or x[1] > hi else hi
            lo = x[2] if lo is None or x[2] < lo else lo
        st += MIN
    return {"week": [iso(a), iso(b)], "bars": n, "expected_bars": 10080, "high": s(hi), "low": s(lo)}


def warmup_section(runs, rows_by_month, calls, prev):
    out = {}
    for m in MONTHS:
        run = runs[m]
        rd = [{"at": z19(e["clock_time"]), "category": e["record"]["category"]} for e in run.obs["readiness"]]
        fctx = first(run.obs["context"], lambda e: e["record"]["category"] != "UNAVAILABLE")
        f = landmark_first(run)
        conf = rows_by_month[m]
        out[m] = {
            "warmup": [iso(run.warmup_start), iso(run.es)], "warmup_hours": (run.es - run.warmup_start).total_seconds() / 3600,
            "readiness_STORED": rd, "first_context_label_STORED": z19(fctx["clock_time"]) if fctx else None,
            "landmark_first_publication_STORED": {k: f.get(k) for k in LANDMARK_HORIZONS},
            "registered_memory": {"pivot_15m_hours": 24, "pivot_1h_hours": 168,
                                  "prev_1d/1w/1mo": "previous complete UTC period, published at the period close"},
            "DERIVED_truncation_windows": {
                "pivot_1h_memory_truncated_until": iso(run.warmup_start + AGE_1H),
                "prev_1w_absent_until": f.get("PREV_1W_HIGH"),
                "prev_1mo_absent_until": f.get("PREV_1MO_HIGH"),
                "prev_1mo_available_inside_evaluation_window": bool(f.get("PREV_1MO_HIGH") and dt(f["PREV_1MO_HIGH"]) < run.ee)},
            "A_confirmations_affected": {
                "pivot_1h_memory_truncated": sum(1 for r in conf if r["warmup_limits"]["pivot_1h_memory_truncated"]),
                "prev_1w_not_yet_published": sum(1 for r in conf if r["warmup_limits"]["prev_1w_not_yet_published"]),
                "prev_1mo_not_yet_published": sum(1 for r in conf if r["warmup_limits"]["prev_1mo_not_yet_published"]),
                "of": len(conf)},
            "calls_affected": [{"call_id": c["call_id"], **c["warmup_limits"],
                                "DERIVED_pre_warmup_bars_in_issue_to_target_range":
                                    pre_warmup_bound(c, run, prev.get(m)) if c["warmup_limits"]["pivot_1h_memory_truncated"] else None,
                                "DERIVED_previous_week_extremes":
                                    prev_week_extremes(run, dt(c["sequence_STORED"]["issued_at"]), prev.get(m), run_bars[m])
                                    if c["warmup_limits"]["prev_1w_not_yet_published"] else None,
                                "issue_reference": c["sequence_STORED"]["issue_reference_price"],
                                "target": c["geometry_STORED"]["T_at_issue"], "stop": c["geometry_STORED"]["stop_guidance"],
                                "direction": c["direction"]}
                               for c in calls if c["month"] == m and any(c["warmup_limits"].values())],
        }
    return out


def tail_section(runs, v3runs, caches, one):
    out = {}
    for m in MONTHS:
        res = {}
        for label, run in (("v0.4", runs[m]), ("v0.3", v3runs[m])):
            tail = [e for e in run.j if dt(e["clock_time"]) >= run.ee]
            decisions = [e for e in tail if e["kind"] in ("scenario", "entry_attempt", "call", "call_revision",
                                                          "material_change")]
            paths_tail = [f"{k}#{v}" for k, vs in run.paths.items() for v, x in vs.items()
                          if dt(run.calls[k]["record"]["issued_at"]) < run.ee and x.get("exit")
                          and dt(x["exit"]["time_end"]) > run.ee]
            vs_tail = [{k: x[k] for k in ("sample_time", "view", "conditional", "outcome_4h", "persistence")}
                       for x in run.view_samples
                       if run.es <= dt(x["sample_time"]) < run.ee and dt(x["sample_time"]) + timedelta(hours=4) > run.ee]
            vs_tail1 = [x["sample_time"] for x in run.view_samples
                        if run.es <= dt(x["sample_time"]) < run.ee and dt(x["sample_time"]) + timedelta(hours=1) > run.ee]
            lm_tail = Counter(e["record"]["landmark_type"] for e in tail if e["kind"] == "landmark")
            res[label] = {
                "tail": [iso(run.ee), iso(run.clock_end)],
                "checkpoint_info_time_STORED": one["checkpoint"][run.rid]["info_time"],
                "journal_records_in_tail_by_kind": dict(Counter(e["kind"] for e in tail)),
                "decision_records_in_tail": len(decisions),
                "evaluation_window_paths_resolved_in_tail": paths_tail,
                "view_samples_with_4h_endpoint_in_tail": vs_tail, "view_samples_with_1h_endpoint_in_tail": vs_tail1,
                "landmarks_published_in_tail": dict(lm_tail),
                "evaluation_window_scenarios_ending_in_tail": sorted({e["record"]["scenario_id"] for e in tail
                                                                      if e["kind"] == "scenario"}),
            }
        res["cache_events_on_or_after_2026_01_01"] = caches[m]["events_on_or_after_2026_01_01"]
        out[m] = res
    return out


# ----------------------------------------------------------------------------------------------------------------------
# summaries
# ----------------------------------------------------------------------------------------------------------------------

def funnel_section(reports, runs, v3runs):
    out = {}
    for m in MONTHS:
        mo = {}
        for label, rid in (("v0.4", V4[m]), ("v0.3", V3[m])):
            rep = reports[rid]
            f = rep["funnel"]
            bc = {k: v for k, v in f["scenario_transitions"].items() if k[0] in "BC"}
            bct = {k: v for k, v in f["scenario_terminals"].items() if k[0] in "BC"}
            cov = rep["coverage"]
            vs = rep["view_samples"]
            cd = rep.get("condition_durations") or {}
            mo[label] = {
                "B_C_scenario_transitions": bc, "B_C_terminals": bct,
                "B_C_confirmations": sum(v for k, v in bc.items() if k.endswith(":CONFIRM")),
                "B_C_calls": sum(v for k, v in (f.get("issued_by_family_mode") or {}).items() if k[0] in "BC"),
                "A_births": {k: v for k, v in f["births"].items() if k[0] == "A"},
                "A_terminals": {k: v for k, v in f["scenario_terminals"].items() if k[0] == "A"},
                "anchors": rep.get("anchors"),
                "coverage": {k: cov[k] for k in ("evaluation_minutes", "covered_minutes", "assessable_minutes",
                                                 "unavailable_minutes", "view_row_minutes", "assessable_weeks")},
                "calls_per_evaluated_week": rep["calls"]["per_evaluated_week"],
                "longest_no_call_interval_hours": rep["calls"]["longest_no_call_interval_hours"],
                "entry_available_minutes": rep["calls"]["entry_available_minutes"],
                "view_samples": vs,
                "condition_durations_top": (sorted(((k, v["minutes"]) for k, v in (cd.get("conditions") or {}).items()),
                                                   key=lambda kv: -Decimal(kv[1]))[:8] if cd.get("available") else None),
                "diagnosis": rep.get("diagnosis"),
            }
        out[m] = mo
    return out


def reconcile(reports, calls, confs):
    rec = {}
    for m in MONTHS:
        f = reports[V4[m]]["funnel"]
        bfm = reports[V4[m]]["by_family_mode"]
        got = {"a_confirmations": f["a_confirmations"], "waits": f["waiting"]["opened"], "calls": f["issued"],
               "return_calls": f["a_return_calls"],
               "immediate_calls": sum(v for k, v in f["issued_by_family_mode"].items() if k.endswith("IMMEDIATE"))}
        rec[m] = {"expected_from_owner": EXPECTED[m], "report_builder_STORED": got,
                  "matches": got == EXPECTED[m],
                  "rows_in_this_dossier": {"confirmations": sum(1 for r in confs if r["month"] == m),
                                           "waits": sum(1 for r in confs if r["month"] == m and r["routing"] == "WAIT_OPEN"),
                                           "calls": sum(1 for c in calls if c["month"] == m)},
                  "a_routing": f["a_routing"], "wait_endings": f["waiting"]["endings"],
                  "D_N": f["a_denominators"], "by_family_mode_PRIMARY": bfm,
                  "a_return_owners_entered_primary_60s": f["a_return_owners_entered_primary_60s"]}
    tot = {k: sum(rec[m]["report_builder_STORED"][k] for m in MONTHS) for k in EXPECTED["2025-10"]}
    entered = sum(rec[m]["a_return_owners_entered_primary_60s"] for m in MONTHS)
    pn = sum(Decimal(v["sum_price_net"]) for m in MONTHS for v in rec[m]["by_family_mode_PRIMARY"].values())
    rec["total"] = {**tot, "return_owners_entered_primary": entered, "primary_price_net_sum_pct": pct(pn),
                    "expected": {"a_confirmations": 64, "waits": 46, "calls": 10, "return_entered": 9},
                    "matches": tot["a_confirmations"] == 64 and tot["waits"] == 46 and tot["calls"] == 10 and entered == 9,
                    "funding": "PRICE_NET_ONLY_TOTAL_NET_UNAVAILABLE on every path (funding not covered)"}
    return rec


def tabulations(confs, calls):
    """DERIVED counts over STORED fields (every confirmation; no selection of examples)."""
    t = {}
    t["classification"] = dict(Counter(r["classification"] for r in confs).most_common())
    t["classification_by_month"] = {m: dict(Counter(r["classification"] for r in confs if r["month"] == m).most_common())
                                    for m in MONTHS}
    # scenario fate after confirmation, split by what happened to the entry
    def grp(r):
        if r["call_id"]:
            return "CALL_ENTERED" if any(c["call_id"] == r["call_id"] and c["outcomes_STORED"]["paths"].get("PRIMARY", {}).get("entry")
                                        for c in calls) else "CALL_NOT_ENTERED"
        if r["routing"] == "WAIT_OPEN":
            return "WAIT_NO_CALL"
        return "TERMINAL_AT_CONFIRMATION"
    fate = defaultdict(Counter)
    for r in confs:
        fate[grp(r)][r["scenario_terminal"]] += 1
    t["scenario_terminal_by_entry_group"] = {k: dict(v.most_common()) for k, v in sorted(fate.items())}
    usable = defaultdict(Counter)
    for r in confs:
        if r["routing"] == "WAIT_OPEN":
            usable["usable_return" if r["usable_return_at"] else "no_usable_return"][r["scenario_terminal"]] += 1
    t["waits_scenario_terminal_by_usable_return"] = {k: dict(v.most_common()) for k, v in sorted(usable.items())}
    epoch = defaultdict(Counter)
    for r in confs:
        epoch["confirmed_after_replacement" if r["confirmed_after_replacement"] else "confirmed_on_first_anchor_or_revision"][
            r["classification"].split(":")[0]] += 1
    t["classification_by_anchor_history"] = {k: dict(v) for k, v in sorted(epoch.items())}
    epoch_fate = defaultdict(Counter)
    for r in confs:
        epoch_fate["confirmed_after_replacement" if r["confirmed_after_replacement"] else
                   "confirmed_on_first_anchor_or_revision"][r["scenario_terminal"]] += 1
    t["scenario_terminal_by_anchor_history"] = {k: dict(v.most_common()) for k, v in sorted(epoch_fate.items())}
    t["direction_by_classification"] = {k: dict(Counter(r["direction"] for r in confs if r["classification"] == k))
                                        for k in sorted({r["classification"] for r in confs})}
    t["context_at_confirmation"] = dict(Counter(f"{r['context_at_confirmation']}/{r['phase_at_confirmation']}"
                                                for r in confs).most_common())
    waits = [r for r in confs if r["routing"] == "WAIT_OPEN"]
    t["waits_derived"] = {
        "waits": len(waits),
        "with_any_close_in_economic_region": sum(1 for r in waits if r["DERIVED_wait"]["closes_in_economic_region"]),
        "derived_vs_stored_blockers": f"{sum(int(r['DERIVED_wait']['derived_blockers_equal_stored'].split('/')[0]) for r in waits)}/"
                                      f"{sum(int(r['DERIVED_wait']['derived_blockers_equal_stored'].split('/')[1]) for r in waits)}",
        "required_retrace_bps_from_close_to_economic_edge": [
            (r["entry_attempt_id"], (bps(Decimal(r["confirmation_close"]), Decimal(r["economic_fixed_k"].split("..")[1]))
                                     if r["direction"] == "LONG" else
                                     bps(Decimal(r["economic_fixed_k"].split("..")[0]), Decimal(r["confirmation_close"])))
             if r["economic_fixed_k"] else None) for r in waits]}
    t["waits_non_price_blockers_STORED"] = dict(sum((Counter(r["DERIVED_wait"]["sampled_minutes_with_non_price_blockers_STORED"])
                                                     for r in waits), Counter()))
    t["minutes_confirmation_to_usable_return"] = [
        (r["entry_attempt_id"], minutes(dt(r["confirmed_at"]), dt(r["usable_return_at"]))) for r in waits if r["usable_return_at"]]
    t["minutes_confirmation_to_scenario_terminal_by_group"] = {
        k: sorted(r["minutes_confirmation_to_scenario_terminal"] for r in confs if grp(r) == k)
        for k in sorted({grp(r) for r in confs})}
    t["calls"] = [{"call_id": c["call_id"], "dir": c["direction"], "mode": c["entry_mode"],
                   "epoch": c["anchor_epoch_at_confirmation"], "after_replacement": c["confirmed_after_replacement"],
                   "risk_bps_issue": c["economics"]["stop_distance_DERIVED"]["risk_bps_at_issue_STORED"],
                   "risk_over_median_1m_range": c["economics"]["stop_distance_DERIVED"]["risk_at_issue_over_median_1m_range"],
                   "gain_bps_issue": c["economics"]["issue_STORED"]["gain_bps"],
                   "primary": c["outcomes_STORED"]["paths"].get("PRIMARY", {}).get("exit_class"),
                   "held": c["outcomes_STORED"]["paths"].get("PRIMARY", {}).get("held_minutes"),
                   "price_net_pct": c["outcomes_STORED"]["paths"].get("PRIMARY", {}).get("price_net_pct"),
                   "mfe_pct": c["outcomes_STORED"]["paths"].get("PRIMARY", {}).get("mfe_pct"),
                   "delay0_pct": c["outcomes_STORED"]["paths"].get("ENTRY_DELAY_0", {}).get("price_net_pct"),
                   "delay120_pct": c["outcomes_STORED"]["paths"].get("ENTRY_DELAY_120", {}).get("price_net_pct"),
                   "horizon_only_pct": c["outcomes_STORED"]["paths"].get("HORIZON_ONLY", {}).get("price_net_pct"),
                   "horizon_only_exit": c["outcomes_STORED"]["paths"].get("HORIZON_ONLY", {}).get("exit_class"),
                   "scenario": c["outcomes_STORED"]["scenario"]["terminal"],
                   "guidance": c["outcomes_STORED"]["guidance"]["thesis_status"]} for c in calls]
    sums = {}
    for v in ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY"):
        xs = [Decimal(c["outcomes_STORED"]["paths"][v]["price_net_pct"]) for c in calls
              if c["outcomes_STORED"]["paths"].get(v, {}).get("price_net_pct") is not None]
        sums[v] = {"paths": len(xs), "sum_price_net_pct": s(sum(xs)) if xs else None,
                   "positive": sum(1 for x in xs if x > 0)}
    t["path_variant_sums_pct"] = sums
    return t


# ----------------------------------------------------------------------------------------------------------------------

run_bars: dict[str, dict] = {}


def main(export: Path, out: Path):
    meta, one, journal, records = load(export)
    caches, bars = {}, {}
    for m in MONTHS:
        pin = one["evaluation"][EVAL[V4[m]]]["corpus"]["pack"]["feed"]["cache_manifest_sha256"]
        caches[m], bars[m] = load_cache(export, CACHE[m], pin)
        run_bars[m] = bars[m]
    prev = {m: bars[PREV_CACHE[m]] for m in MONTHS if m in PREV_CACHE}
    reports = {rid: build_report(rid, one, journal, records) for rid in EVAL}
    runs = {m: Run(V4[m], one, journal, records) for m in MONTHS}
    v3runs = {m: Run(V3[m], one, journal, records) for m in MONTHS}
    confs, calls = [], []
    for m in MONTHS:
        confs += confirmations(runs[m], v3runs[m], m, bars[m], prev.get(m))
        calls += call_rows(runs[m], v3runs[m], m, bars[m])
    by_month = {m: [r for r in confs if r["month"] == m] for m in MONTHS}
    warm_calls = {m: [{"call_id": cid, "issued_at": e["record"]["issued_at"],
                       "note": "issued inside this run's warmup; not scored; identical id in the previous month's run"
                       if any(cid in runs[p].calls for p in MONTHS if p != m) else "issued inside warmup; not scored"}
                      for cid, e in runs[m].calls.items() if dt(e["record"]["issued_at"]) < runs[m].es]
                  for m in MONTHS}
    dossier = {
        "scope": "read-only cross-month diagnosis of the Owner v0.4 Oct-Dec 2025 evaluations; no replay, backtest, "
                 "Deep validation, counterfactual, download or product/data change",
        "labels": {"STORED": "committed journal/evaluation field or product-builder count",
                   "DERIVED": "exact arithmetic on STORED fields or on pinned 1m trade bars no later than the stated cutoff",
                   "UNAVAILABLE": "not recorded; not derivable without replay/counterfactual"},
        "provenance": provenance(meta, one, journal, records, caches, export),
        "comparability": comparability(one, reports),
        "reconciliation": reconcile(reports, calls, confs),
        "warmup_calls_not_scored": warm_calls,
        "calls": calls,
        "confirmations": confs,
        "tabulations": tabulations(confs, calls),
        "funnel_and_marketview": funnel_section(reports, runs, v3runs),
        "warmup_limits": warmup_section(runs, by_month, calls, prev),
        "tail_2026_01_01": tail_section(runs, v3runs, caches, one),
        "unavailable": [
            "whether any confirmation without a call would have produced a profitable call under another rule "
            "(counterfactual replay not authorized)",
            "intrabar order inside 1m bars (no sub-minute evidence)",
            "landmarks the run would have published from pre-warmup history (only a descriptive price-range bound "
            "is given; the landmark logic is not re-run)",
            "October pre-warmup bars (the September source cache was not copied; bound UNAVAILABLE for October)",
            "funding (PRICE_NET_ONLY; total net unavailable)",
            "per-minute STORED return samples (blockers are journaled only on change; minutes are DERIVED and "
            "validated against stored blocker changes)",
            "news/calendar coverage (capability profile NONE_UNKNOWN)"],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "dossier.json").write_text(json.dumps(dossier, indent=1, default=str) + "\n", encoding="utf-8")
    ccols = [("month", lambda c: c["month"]), ("call_id", lambda c: c["call_id"]), ("owner", lambda c: c["owner"]),
             ("direction", lambda c: c["direction"]), ("entry_mode", lambda c: c["entry_mode"]),
             ("birth", lambda c: c["owner_STORED"]["birth_published"]),
             ("impulse_A", lambda c: c["owner_STORED"]["impulse_A"]), ("impulse_B", lambda c: c["owner_STORED"]["impulse_B"]),
             ("first_anchor", lambda c: _anch(c["anchors_STORED"], first=True)),
             ("confirming_anchor", lambda c: _anch(c["anchors_STORED"], first=False)),
             ("anchor_epoch_at_confirmation", lambda c: c["anchor_epoch_at_confirmation"]),
             ("anchor_losses_before_confirmation", lambda c: c["anchor_losses_before_confirmation"]),
             ("confirmed_at", lambda c: c["sequence_STORED"]["confirmed_at"]),
             ("routing", lambda c: c["sequence_STORED"]["routing"]),
             ("usable_return_at", lambda c: c["sequence_STORED"]["usable_return_at"]),
             ("issued_at", lambda c: c["sequence_STORED"]["issued_at"]),
             ("primary_entry_at", lambda c: c["sequence_STORED"]["primary_entry_at"]),
             ("primary_entry_price", lambda c: c["sequence_STORED"]["primary_entry_price"]),
             ("primary_exit_at", lambda c: c["sequence_STORED"]["primary_exit_at"]),
             ("primary_exit_price", lambda c: c["sequence_STORED"]["primary_exit_price"]),
             ("R", lambda c: c["geometry_STORED"]["R"]), ("K", lambda c: c["geometry_STORED"]["K_trigger"]),
             ("V_stop", lambda c: c["geometry_STORED"]["stop_guidance"]),
             ("T_confirm", lambda c: c["geometry_STORED"]["T_confirm"]), ("T_issue", lambda c: c["geometry_STORED"]["T_at_issue"]),
             ("target_origin", lambda c: c["geometry_STORED"]["target_origin"]),
             ("limiting_landmark", lambda c: c["geometry_STORED"]["limiting_landmark_at_confirmation"]["type"]),
             ("scale_S15", lambda c: c["geometry_STORED"]["scale_S15_at_confirmation"]),
             ("cap_revisions", lambda c: len(c["geometry_STORED"]["cap_history"]) - 1),
             ("margin_conf_bps", lambda c: c["economics"]["confirmation_STORED"]["margin_bps"]),
             ("margin_issue_bps", lambda c: c["economics"]["issue_STORED"]["margin_bps"]),
             ("margin_entry_bps_DERIVED", lambda c: c["economics"]["primary_entry_DERIVED"]["margin_bps"]
              if isinstance(c["economics"]["primary_entry_DERIVED"], dict) else "UNAVAILABLE"),
             ("residual_min_conf_DERIVED", lambda c: c["economics"]["residual_minutes_DERIVED"]["at_confirmation_to_hard_deadline"]),
             ("residual_min_issue_DERIVED", lambda c: c["economics"]["residual_minutes_DERIVED"]["at_issue_to_hard_deadline"]),
             ("residual_min_entry_DERIVED", lambda c: c["economics"]["residual_minutes_DERIVED"]["at_primary_entry_to_hard_deadline"]),
             ("gain_bps_issue", lambda c: c["economics"]["issue_STORED"]["gain_bps"]),
             ("risk_bps_issue", lambda c: c["economics"]["issue_STORED"]["risk_bps"]),
             ("risk_bps_entry_DERIVED", lambda c: c["economics"]["stop_distance_DERIVED"]["risk_bps_at_primary_entry"]),
             ("median_1m_range_bps_DERIVED", lambda c: c["economics"]["stop_distance_DERIVED"]["median_1m_range_bps_60min_before_issue"]),
             ("entry_available_min", lambda c: c["entry_window_STORED"]["available_minutes_DERIVED"]),
             ("entry_first_closed_reasons", lambda c: c["entry_window_STORED"]["first_closed_reasons"]),
             ("hard_deadline", lambda c: c["entry_window_STORED"]["hard_deadline"]),
             ("call_progress_check_at", lambda c: c["entry_window_STORED"]["call_progress_check_at"]),
             ("context_at_confirmation", lambda c: ctx_short(c["context_STORED"]["confirmation"])),
             ("context_at_issue", lambda c: ctx_short(c["context_STORED"]["issue"])),
             ("scenario_outcome", lambda c: c["outcomes_STORED"]["scenario"]["terminal"]),
             ("scenario_outcome_at", lambda c: c["outcomes_STORED"]["scenario"]["at"]),
             ("guidance_outcome", lambda c: c["outcomes_STORED"]["guidance"]["thesis_status"]),
             ("guidance_outcome_at", lambda c: c["outcomes_STORED"]["guidance"]["at"]),
             ("primary_exit_class", lambda c: c["outcomes_STORED"]["paths"]["PRIMARY"]["exit_class"]),
             ("primary_price_net_pct", lambda c: c["outcomes_STORED"]["paths"]["PRIMARY"]["price_net_pct"]),
             ("primary_held_min", lambda c: c["outcomes_STORED"]["paths"]["PRIMARY"]["held_minutes"]),
             ("primary_mfe_pct", lambda c: c["outcomes_STORED"]["paths"]["PRIMARY"]["mfe_pct"]),
             ("primary_mae_pct", lambda c: c["outcomes_STORED"]["paths"]["PRIMARY"]["mae_pct"]),
             ("delay0_price_net_pct", lambda c: c["outcomes_STORED"]["paths"]["ENTRY_DELAY_0"]["price_net_pct"]),
             ("delay120_price_net_pct", lambda c: c["outcomes_STORED"]["paths"]["ENTRY_DELAY_120"]["price_net_pct"]),
             ("horizon_only_exit", lambda c: c["outcomes_STORED"]["paths"]["HORIZON_ONLY"]["exit_class"]),
             ("horizon_only_price_net_pct", lambda c: c["outcomes_STORED"]["paths"]["HORIZON_ONLY"]["price_net_pct"]),
             ("v03_same_boundary", lambda c: c["v03_same_boundary_STORED"])]
    _csv(out / "calls.csv", calls, ccols)
    fcols = ["month", "entry_attempt_id", "direction", "birth_published", "anchor_losses_before_confirmation",
             "anchor_epoch_at_confirmation", "confirmed_after_replacement", "confirmed_at", "R", "K_trigger", "V",
             "confirmation_close", "S15", "T_confirm", "target_type", "limiting_landmark", "limiting_is_own_impulse_B",
             "destination_B", "DERIVED_target_distance_bps_from_close", "DERIVED_V_distance_bps_from_close",
             "G_bps", "Q_bps", "margin_bps", "corridor", "economic_fixed_k", "in_D", "in_N", "exclusion",
             "blockers_at_confirmation", "routing", "routing_reason", "wait_end_transition", "wait_end_reason",
             "wait_end_at", "usable_return_at", "cap_revisions", "call_id", "classification", "scenario_terminal",
             "scenario_terminal_at", "minutes_confirmation_to_scenario_terminal", "context_at_confirmation",
             "phase_at_confirmation", "market_view_at_confirmation", "v03_same_boundary"]
    wcols = [("wait_return_samples_DERIVED", "return_samples"), ("wait_closes_in_economic_DERIVED", "closes_in_economic_region"),
             ("wait_best_close_distance_bps_DERIVED", "best_close_distance_to_region_bps"),
             ("wait_blockers_equal_stored_DERIVED", "derived_blockers_equal_stored")]
    _csv(out / "confirmations.csv", confs,
         [(k, (lambda k: lambda r: r[k])(k)) for k in fcols]
         + [(n, (lambda k: lambda r: (r["DERIVED_wait"] or {}).get(k))(k)) for n, k in wcols]
         + [("pivot_1h_memory_truncated", lambda r: r["warmup_limits"]["pivot_1h_memory_truncated"]),
            ("prev_1w_not_yet_published", lambda r: r["warmup_limits"]["prev_1w_not_yet_published"])])
    print(json.dumps({"reconciliation": {m: dossier["reconciliation"][m]["matches"] for m in (*MONTHS, "total")},
                      "chains": {rid: [v["journal"]["matches_finish_commitment"], v["evaluation_records"]["matches_finish_commitment"]]
                                 for rid, v in dossier["provenance"]["runs"].items()},
                      "caches": {m: [c["manifest_matches_pin"], c["partitions_failing_sha256"]] for m, c in caches.items()},
                      "comparability": {m: v["verdict_recomputed"] for m, v in dossier["comparability"].items()}}, indent=1))


def _anch(anchors, first):
    xs = [a for a in anchors if a["transition"] in ("ARM", "REARM", "REVISE")]
    if not xs:
        return None
    a = xs[0] if first else xs[-1]
    return f"e{a['epoch']} R {a['R']} K {a['K']} V {a['V']} src {str(a['source']).rsplit('/', 1)[-1]} pub {a['published_at']}"


def _csv(path, rows, cols):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow([c for c, _ in cols])
        for r in rows:
            vals = []
            for _, fn in cols:
                v = fn(r)
                vals.append(" | ".join(map(str, v)) if isinstance(v, list) else v)
            w.writerow(vals)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
