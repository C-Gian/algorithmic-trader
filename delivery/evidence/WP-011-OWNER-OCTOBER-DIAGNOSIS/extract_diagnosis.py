"""One-time read-only diagnosis of the Owner October 2025 paired comparison (WP-011, build bd5d81c).

  v0.2  eval-20261006T173330-4e7c36 / obs-20261006T173330-62d684
  v0.3  eval-20261006T175135-9ddf6d / obs-20261006T175135-e8267a
  pack  pack-30c0661ff5dc7b746f821ceb5efeda0702f33f30, cache fc-de5aa4a9d5260d3cfdb135be2d0a90001d6c835f

Not product code and not a reusable analytics framework. Inputs (produced by read-only access, never committed):
  <export>/snapshot.jsonl  one REPEATABLE READ READ ONLY psql transaction: meta, both evaluation/replay/checkpoint/
                           finish rows (adviser blob excluded) and the complete committed adviser journal and
                           evaluation records of both runs
  <export>/<cache_id>/     byte copy of the runs' common pinned canonical feed cache

Nothing replays the professional runtime. STORED = a committed journal/evaluation field. DERIVED = exact Decimal
arithmetic on STORED fields, or on pinned 1m trade bars no later than the case's own cutoff (stated per row). The
economic predicate and admissible bounds are the product's own pure functions (algotrader.adviser.geometry), called
on STORED levels; they do not change any saved result.

usage: uv run python extract_diagnosis.py <export_dir> <out_dir>
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.adviser import geometry as geo
from algotrader.adviser import report as r2
from algotrader.adviser import report3 as r3
from algotrader.adviser.core import INITIAL_JOURNAL
from algotrader.adviser.evaluator import INITIAL_RECORDS
from algotrader.adviser.measures import round_down, round_up
from algotrader.feed.ordering import canonical

V2 = "obs-20261006T173330-62d684"
V3 = "obs-20261006T175135-e8267a"
EVAL = {V2: "eval-20261006T173330-4e7c36", V3: "eval-20261006T175135-9ddf6d"}
PACK = "pack-30c0661ff5dc7b746f821ceb5efeda0702f33f30"
CACHE = "fc-de5aa4a9d5260d3cfdb135be2d0a90001d6c835f"
BUILD = "bd5d81c1060303a91d6ee38471a99afd09b6c8f2"
ES, EE = "2025-10-01T00:00:00Z", "2025-11-01T00:00:00Z"
TICK, K_HIST, RR = Decimal("0.1"), Decimal(14), Decimal("1.2")
MIN = timedelta(minutes=1)
EPISODE_V2 = "AL-2025-10-26T22:45:00+00:00-c846b443f534"
EPISODE_V3 = "AL-2025-10-26T22:45:00+00:00-3ae176455221"


def dt(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def dec(x):
    return None if x is None else Decimal(str(x))


def s(x):
    return None if x is None else format(x, "f") if isinstance(x, Decimal) else str(x)


def fx2(x):
    return None if x is None else format(Decimal(x).quantize(Decimal("0.01")), "f")


def bps(a, b):
    """10000*(a-b)/b, two decimals."""
    return fx2(Decimal(10000) * (a - b) / b)


# ----------------------------------------------------------------------------------------------------------------------
# inputs and provenance
# ----------------------------------------------------------------------------------------------------------------------

def load(export: Path):
    one = {"evaluation": {}, "replay": {}, "checkpoint": {}, "finish": {}}
    journal, records, meta = {V2: [], V3: []}, {V2: [], V3: []}, None
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
            one[k][v.get("replay_id") or v.get("run_id")] = v
    for rid in (V2, V3):
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


def load_cache(export: Path, pinned_sha: str):
    root = export / CACHE
    msha = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bad, bars = [], {}
    for p in man["partitions"]:
        blob = (root / p["file"]).read_bytes()
        if hashlib.sha256(blob).hexdigest() != p["sha256"]:
            bad.append(p["file"])
            continue
        for line in gzip.decompress(blob).splitlines():
            ev = json.loads(line)
            if ev["channel"]["family"] != "trade_bar_1m" or ev["kind"] != "bar_observation":
                continue
            pl = ev["payload"]
            bars[dt(ev["event_time"])] = tuple(dec(pl[k]) for k in ("open", "high", "low", "close"))
    return {"cache_id": CACHE, "manifest_sha256": msha, "pinned_manifest_sha256": pinned_sha,
            "manifest_matches_pin": msha == pinned_sha, "partitions": len(man["partitions"]),
            "partitions_failing_sha256": bad, "trade_minutes": len(bars)}, bars


def bar_row(bars, start: datetime, cutoff: datetime):
    """A pinned 1m trade bar [start, start+1m) used only when start+1m <= cutoff (admitted at its close)."""
    if start + MIN > cutoff:
        raise RuntimeError(f"bar {iso(start)} is after cutoff {iso(cutoff)}")
    o, h, lo, c = bars[start]
    return {"start": iso(start), "open": s(o), "high": s(h), "low": s(lo), "close": s(c)}


# ----------------------------------------------------------------------------------------------------------------------
# count reconciliation through the product's own report builders (committed records only)
# ----------------------------------------------------------------------------------------------------------------------

def report_counts(one, journal, records):
    out = {}
    for rid in (V2, V3):
        # exactly as algotrader.evaluation.api.adviser_section: the run's stored engine descriptor selects the builder
        engine = one["replay"][rid]["engine"]
        builder = r3.build if engine["adviser"].get("method") == "v0.3" else r2.build
        view = (one["checkpoint"].get(rid) or {}).get("adviser_view")
        rep = builder(engine=engine, journal=journal[rid], records=records[rid], view=view,
                      status=one["replay"][rid]["status"], clock_end_reached=rid in one["finish"])
        f = rep.get("funnel") or {}
        keep = {k: f.get(k) for k in ("births", "arms", "trigger_evaluations", "issued", "a_confirmations",
                                      "a_denominators", "a_routing", "waiting", "issued_by_family_mode",
                                      "a_return_owners_entered_primary_60s", "rejection_blockers",
                                      "a_destination_before_confirmation") if k in f}
        out[rid] = {"builder": builder.__module__, "funnel": keep}
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Q1 — the 26 October A LONG episode
# ----------------------------------------------------------------------------------------------------------------------

def compact(e):
    r = e["record"]
    keep = ("transition", "status", "reason", "trigger_level", "invalidation_level", "reaction_level", "destination",
            "expires_at", "original_expiry", "terminal_state", "discovery_owner", "call_id", "target",
            "invalidation", "entry_status", "issued_at")
    out = {"seq": e["seq"], "kind": e["kind"], "clock_time": e["clock_time"][:19] + "Z",
           "factual_cursor": e["factual_cursor"], **{k: r[k] for k in keep if k in r}}
    st = r.get("setup") or {}
    for k in ("impulse_A", "impulse_B", "s15", "zone_halfwidth", "reaction", "latch_long", "renewal"):
        if k in st:
            out[f"setup.{k}"] = st[k]
    return out


def q1(journal, records, bars):
    cutoff = dt("2025-10-26T23:34:00Z")  # the v0.2 issue dispatch; nothing later is used for the derivation
    v2 = [compact(e) for e in journal[V2] if e["kind"] in ("candidate", "call")
          and (e["record"].get("attempt_id") == EPISODE_V2)]
    v3 = [compact(e) for e in journal[V3] if e["kind"] in ("scenario", "entry_attempt")
          and e["record"].get("scenario_id") == EPISODE_V3]
    act = next(e["record"] for e in journal[V2] if e["kind"] == "actionability"
               and e["record"].get("subject_id", "").startswith("call-AL-2025-10-26T23:34"))
    act = {k: act[k] for k in ("side_price", "structural_area", "admissible_bounds", "gain_bps", "risk_bps",
                               "reward_risk_margin", "cost_envelope_bps", "blockers", "limiting_landmark")}
    # armed levels (STORED, identical in both runs) and per-minute DERIVED checks from the arm publication
    arm_t = dt("2025-10-26T23:15:00Z")
    a_t, z = Decimal("112835"), Decimal("19.92")
    k_arm, v_arm, r_arm = Decimal("114940.6"), Decimal("114343.28"), Decimal("114363.2")
    k_rev, v_rev = Decimal("114540.5"), Decimal("114309.58")
    rows = []
    t = arm_t
    while t + MIN <= cutoff:
        b = bar_row(bars, t, cutoff)
        lo, c = Decimal(b["low"]), Decimal(b["close"])
        active_v2_v = v_arm if t + MIN <= dt("2025-10-26T23:30:00Z") else v_rev
        active_v2_k = k_arm if t + MIN <= dt("2025-10-26T23:30:00Z") else k_rev
        rows.append({**b, "admitted_at_dispatch": iso(t + MIN),
                     "v3_active_V": s(v_arm) if t + MIN <= dt("2025-10-26T23:30:00Z") else None,
                     "v3_low_at_or_below_V": (lo <= v_arm) if t + MIN <= dt("2025-10-26T23:30:00Z") else None,
                     "v2_active_K_plus_tick": s(active_v2_k + TICK), "v2_active_V": s(active_v2_v),
                     "v2_confirming_close": c >= active_v2_k + TICK, "v2_low_at_or_below_active_V": lo <= active_v2_v})
        t += MIN
    m15 = [bars[dt("2025-10-26T23:15:00Z") + i * MIN] for i in range(15)]
    bar15 = {"start": "2025-10-26T23:15:00Z", "high": s(max(x[1] for x in m15)), "low": s(min(x[2] for x in m15)),
             "close": s(m15[-1][3]), "admitted_at_dispatch": "2025-10-26T23:30:00Z"}
    first_contact = next(r for r in rows if r["v3_low_at_or_below_V"])
    derived = {
        "armed_V_equals_R_minus_z": s(r_arm - z) == s(v_arm),
        "first_1m_low_at_or_below_armed_V": first_contact["start"],
        "v2_revision_15m_bar": bar15,
        "v2_revision_conditions": {
            "low_le_R": Decimal(bar15["low"]) <= r_arm, "low_gt_A_plus_z": Decimal(bar15["low"]) > a_t + z,
            "new_R": bar15["low"], "new_K_is_15m_high": bar15["high"] == s(k_rev),
            "new_V_equals_low_minus_z": s(Decimal(bar15["low"]) - z) == s(v_rev)},
        "v2_trigger_minute": next(r for r in rows if r["v2_confirming_close"]
                                  and dt(r["admitted_at_dispatch"]) > dt("2025-10-26T23:30:00Z")),
        "v2_trigger_low_above_revised_V": True,
    }
    derived["v2_trigger_low_above_revised_V"] = Decimal(derived["v2_trigger_minute"]["low"]) > v_rev
    disl = [{"clock_time": e["clock_time"][:19] + "Z", "category": e["record"]["category"]}
            for e in journal[V3] if e["kind"] == "observation" and e["record"]["name"] == "dislocation"
            and dt(e["clock_time"]) <= cutoff]
    paths = [{k: x["record"].get(k) for k in ("variant", "status", "exit_class", "entry", "exit", "price_net")}
             for x in records[V2] if x["kind"] == "path"]
    return {"cutoff": iso(cutoff), "v2_records": v2, "v2_issue_actionability": act, "v3_records": v3,
            "minutes_from_arm": rows, "derived": derived,
            "v3_dislocation_observations_up_to_cutoff_last3": disl[-3:],
            "v2_call_paths_STORED": paths}


def q1_scope(journal):
    """STORED-only scope of the rule difference in the evaluation window: v0.2 A revisions whose new reaction low is
    at/beyond the V armed before it (a path on which every complete 1m minute is wholly after arm, so a v0.3-style
    1m V contact necessarily occurred first), the end of those v0.2 attempts, and v0.3 pre-confirmation V contacts."""
    last, through, rev = {}, [], 0
    for e in journal[V2]:
        r = e["record"]
        if e["kind"] != "candidate" or r["family"] != "A":
            continue
        a = r["attempt_id"]
        if r["transition"] == "REVISE" and ES <= e["clock_time"][:19] + "Z" < EE:
            rev += 1
            d = 1 if r["direction"] == "LONG" else -1
            pv = last.get(a)
            if pv is not None and d * Decimal(r["setup"]["reaction"]) <= d * Decimal(pv):
                through.append({"at": e["clock_time"][:19] + "Z", "attempt_id": a, "previous_V": pv,
                                "new_reaction": r["setup"]["reaction"]})
        if r.get("invalidation_level"):
            last[a] = r["invalidation_level"]
    ends = {}
    for x in through:
        a = x["attempt_id"]
        last_rec = [e["record"] for e in journal[V2] if e["kind"] == "candidate" and e["record"]["attempt_id"] == a][-1]
        ends[a] = ("ISSUE (call)" if last_rec["transition"] == "ISSUE" else
                   f"{last_rec['transition']}:{str(last_rec.get('reason')).split(':')[0]}")
    vc = [e["record"] for e in journal[V3] if e["kind"] == "scenario" and e["record"]["transition"] == "TERMINAL"
          and str(e["record"]["reason"]).startswith("V_CONTACT") and ES <= e["clock_time"][:19] + "Z" < EE]
    return {"v2_A_revisions_in_window": rev, "v2_A_revisions_at_or_through_armed_V": len(through),
            "v2_distinct_attempts_with_such_revision": len(ends),
            "v2_end_of_those_attempts": dict(Counter(ends.values())),
            "v3_pre_confirmation_V_contact_terminals_A": sum(1 for r in vc if r["family"] == "A" and r["confirmed_at"] is None),
            "v3_V_contact_terminals_other": sum(1 for r in vc if not (r["family"] == "A" and r["confirmed_at"] is None)),
            "v3_A_revisions_in_window": sum(1 for e in journal[V3] if e["kind"] == "scenario"
                                            and e["record"]["transition"] == "REVISE"
                                            and ES <= e["clock_time"][:19] + "Z" < EE),
            "rows": through,
            "limit": "Counts only. Whether any of these v0.2 attempts would have produced a different v0.3 call is "
                     "NOT DEMONSTRABLE without a counterfactual replay, which is not authorized."}


# ----------------------------------------------------------------------------------------------------------------------
# Q2 — the six routed A confirmations of v0.3
# ----------------------------------------------------------------------------------------------------------------------

def routed_rows(journal):
    routed = {}
    for e in journal[V3]:
        r = e["record"]
        if (e["kind"] == "entry_attempt" and r["family"] == "A" and ES <= r["env"]["published_at"] < EE
                and r["entry_attempt_id"] not in routed and (r.get("diagnostic") or {}).get("in_D") is not None):
            routed[r["entry_attempt_id"]] = e
    return list(routed.values())


def econ_bound(d, t, v):
    raw = (t + RR * v) / ((1 + RR) * ((1 + K_HIST / 10000) if d > 0 else (1 - K_HIST / 10000)))
    return round_down(raw, TICK) if d > 0 else round_up(raw, TICK)


def q2(journal, bars):
    v2_by_prefix = {}
    for e in journal[V2]:
        if e["kind"] == "candidate":
            v2_by_prefix.setdefault(e["record"]["attempt_id"].rsplit("-", 1)[0], []).append(e)
    out = []
    for e in routed_rows(journal):
        r = e["record"]
        g, sid = r["geometry"], r["scenario_id"]
        sc = [x for x in journal[V3] if x["kind"] == "scenario" and x["record"]["scenario_id"] == sid]
        by = {x["record"]["transition"]: x for x in sc}
        conf, arm, term = by["CONFIRM"]["record"], by["ARM"]["record"], by["TERMINAL"]
        d = 1 if r["direction"] == "LONG" else -1
        conf_at = dt(r["clocks"]["confirmed_at"])
        cbar = bar_row(bars, conf_at - MIN, conf_at)
        v, t = Decimal(g["V"]), Decimal(g["T_confirm"])
        cor = [Decimal(x) for x in g["corridor"].split("..")] if g.get("corridor") else None
        bound = econ_bound(d, t, v)
        econ_d = geo.admissible_bounds(d, tuple(cor), v, t, K_HIST, RR, TICK) if cor else None
        chk = geo.predicate(d, Decimal(g["price"]), v, t, K_HIST, RR)
        ends = [x for x in journal[V3] if x["kind"] == "entry_attempt" and x["record"]["entry_attempt_id"]
                == r["entry_attempt_id"] and x["record"]["state"] == "TERMINAL"]
        final = ends[-1]["record"]["reason"] if ends else None
        # STORED: the scenario's own terminal and the v0.2 attempt born at the same 15m boundary/direction
        tminute = term["record"]["reason"].split("@")[-1] if "@" in term["record"]["reason"] else None
        tbar = bar_row(bars, dt(tminute), dt(term["clock_time"])) if tminute else None
        v2e = v2_by_prefix.get(sid.rsplit("-", 1)[0], [])
        v2_last = v2e[-1]["record"] if v2e else None
        row = {
            "entry_attempt_id": r["entry_attempt_id"], "direction": r["direction"],
            "birth_published": by["BIRTH"]["clock_time"][:19] + "Z", "armed_at": arm["activated_at"],
            "confirmed_at": iso(conf_at), "confirmation_minute": cbar["start"],
            "original_setup_expiry": r["clocks"]["setup_expiry"], "hard_deadline": r["clocks"]["hard_deadline"],
            "impulse_A": arm["setup"]["impulse_A"], "destination_impulse_B": conf["destination"],
            "R": g["R"], "K_trigger": g["K_trigger"], "V_rounded": g["V"], "V_raw": conf["invalidation_level"],
            "S15_at_confirmation": g["S15"], "setup_s15": conf["setup"]["s15"],
            "confirmation_close": g["confirmation_close"], "T_confirm": g["T_confirm"],
            "target_type": g["target_type"], "limiting_landmark": (r.get("limiting_landmark") or {}).get("type"),
            "limiting_landmark_id": (r.get("limiting_landmark") or {}).get("landmark_id"),
            "limiting_is_own_impulse_B": (r.get("limiting_landmark") or {}).get("landmark_id") == f"{sid}#B",
            "I0": g.get("I0"), "corridor": g.get("corridor"), "economic_fixed_k_STORED": g.get("economic_fixed_k"),
            "G_bps": fx2(g["G"]), "Q_bps": fx2(g["Q"]), "margin_bps": fx2(g["margin"]),
            "blockers_STORED": r["blockers"], "routing": r["transition"] if r["transition"] == "WAIT_OPEN" else "TERMINAL",
            "routing_reason": r["reason"], "final_entry_reason": final,
            "in_D": r["diagnostic"]["in_D"], "in_N": r["diagnostic"]["in_N"],
            "scenario_terminal_STORED": f"{term['record']['terminal_state']}:{term['record']['reason']}",
            "scenario_terminal_at": term["clock_time"][:19] + "Z",
            "v2_same_boundary_attempt_STORED": (f"{v2_last['attempt_id']} {v2_last['transition']} "
                                                f"{v2_last['status']} {v2_last.get('reason')}") if v2_last else None,
            "DERIVED": {
                "confirmation_bar": cbar,
                "confirmation_bar_cutoff": iso(conf_at),
                "T_confirm_minus_close_bps_toward_target": bps(t, Decimal(g["confirmation_close"])) if d > 0
                else bps(Decimal(g["confirmation_close"]), t),
                "T_confirm_vs_destination": (f"T_confirm = B {'-' if d > 0 else '+'} z rounded inward"
                                             if g.get("target_type") == "LANDMARK" else None),
                "predicate_at_close_reproduced": (chk.reason or "PASS") in r["blockers"] or chk.ok,
                "fixed_k_bound": s(bound),
                "fixed_k_economic_reproduced": s(econ_d[0]) + ".." + s(econ_d[1]) if econ_d else None,
                "economic_matches_STORED": ((s(econ_d[0]) + ".." + s(econ_d[1])) if econ_d else None)
                == g.get("economic_fixed_k"),
                "confirmation_bar_extreme_vs_T": (f"high {cbar['high']} >= T {g['T_confirm']}" if d > 0 and
                                                  Decimal(cbar["high"]) >= t else
                                                  f"low {cbar['low']} <= T {g['T_confirm']}" if d < 0 and
                                                  Decimal(cbar["low"]) <= t else "no target contact"),
                "scenario_terminal_bar": tbar,
            },
        }
        out.append(row)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Q3 — the three RETURN waits, minute by minute
# ----------------------------------------------------------------------------------------------------------------------

def q3(journal, bars):
    waits = []
    for e in routed_rows(journal):
        if e["record"]["transition"] != "WAIT_OPEN":
            continue
        eid = e["record"]["entry_attempt_id"]
        recs = [x for x in journal[V3] if x["kind"] == "entry_attempt" and x["record"]["entry_attempt_id"] == eid]
        sid = e["record"]["scenario_id"]
        scen = [x for x in journal[V3] if x["kind"] == "scenario" and x["record"]["scenario_id"] == sid]
        dest = Decimal(scen[-1]["record"]["destination"])
        r0 = e["record"]
        g0 = r0["geometry"]
        d = 1 if r0["direction"] == "LONG" else -1
        conf_at = dt(r0["clocks"]["confirmed_at"])
        end_rec = recs[-1]
        end_t = dt(end_rec["clock_time"])
        v = Decimal(g0["V"])
        lo_s, hi_s = (Decimal(x) for x in g0["corridor"].split(".."))
        caps = end_rec["record"]["cap_history"]
        stored_blockers = [(dt(x["clock_time"]), x["record"]["blockers"]) for x in recs]
        minutes = []
        t = conf_at
        while t + MIN <= end_t:
            b = bar_row(bars, t, end_t)
            o, h, lo, c = (Decimal(b[k]) for k in ("open", "high", "low", "close"))
            cap = Decimal(next(x["cap"] for x in reversed(caps) if dt(x["since"]) <= t))
            # effective corridor with the cap active at this sample's dispatch (cap published at that dispatch counts)
            cap_disp = Decimal(next(x["cap"] for x in reversed(caps) if dt(x["since"]) <= t + MIN))
            if d > 0:
                cor = (lo_s, min(hi_s, cap_disp - TICK))
            else:
                cor = (max(lo_s, cap_disp + TICK), hi_s)
            econ = geo.admissible_bounds(d, cor, v, cap_disp, K_HIST, RR, TICK) if cor[0] <= cor[1] else None
            chk = geo.predicate(d, c, v, cap_disp, K_HIST, RR)
            derived_price_blockers = sorted(set((["CLOSE_OUTSIDE_RETURN_CORRIDOR"] if not cor[0] <= c <= cor[1] else [])
                                                + ([chk.reason] if not chk.ok else [])))
            disp = t + MIN
            in_force = [bl for (ct, bl) in stored_blockers if ct <= disp][-1]
            v_contact = lo <= v if d > 0 else h >= v
            cap_contact = h >= cap if d > 0 else lo <= cap
            dest_contact = h >= dest if d > 0 else lo <= dest
            sampled = disp < dt(r0["clocks"]["setup_expiry"]) and not (v_contact or cap_contact or dest_contact)
            minutes.append({
                "wait": eid, **b, "admitted_at_dispatch": iso(disp), "cap_active_at_start": s(cap),
                "cap_at_dispatch": s(cap_disp), "corridor_effective": f"{cor[0]}..{cor[1]}",
                "economic_fixed_k": f"{econ[0]}..{econ[1]}" if econ else None,
                "close_in_corridor": cor[0] <= c <= cor[1], "close_in_economic": bool(econ and econ[0] <= c <= econ[1]),
                "extreme_in_economic_intrabar": bool(econ and (lo <= econ[1] if d > 0 else h >= econ[0])),
                "V_contact": v_contact, "cap_contact": cap_contact, "destination_contact": dest_contact,
                "G_at_close": fx2(chk.g), "Q_at_close": fx2(chk.q), "margin_at_close": fx2(chk.margin),
                "derived_price_blockers": derived_price_blockers, "stored_blockers_in_force": in_force,
                "derived_equals_stored": derived_price_blockers == sorted(in_force) if sampled else None,
                "return_gate_sampled": sampled})
            t += MIN
        closes = [Decimal(m["close"]) for m in minutes if m["return_gate_sampled"]]
        econs = [m["economic_fixed_k"] for m in minutes if m["return_gate_sampled"]]
        best = (min(closes) if d > 0 else max(closes)) if closes else None
        edge = None
        if econs and econs[-1]:
            lo_e, hi_e = (Decimal(x) for x in econs[-1].split(".."))
            edge = hi_e if d > 0 else lo_e
        extreme = (min(Decimal(m["low"]) for m in minutes) if d > 0 else max(Decimal(m["high"]) for m in minutes))
        waits.append({
            "entry_attempt_id": eid, "direction": r0["direction"], "confirmed_at": iso(conf_at),
            "setup_expiry": r0["clocks"]["setup_expiry"], "hard_deadline": r0["clocks"]["hard_deadline"],
            "V": g0["V"], "R": g0["R"], "K_trigger": g0["K_trigger"], "corridor_structural": g0["corridor"],
            "T_confirm": g0["T_confirm"], "destination": s(dest), "economic_at_open": g0["economic_fixed_k"],
            "cap_history_STORED": caps,
            "records_STORED": [{"seq": x["seq"], "clock_time": x["clock_time"][:19] + "Z",
                                "transition": x["record"]["transition"], "reason": x["record"].get("reason"),
                                "blockers": x["record"]["blockers"], "price": x["record"]["geometry"].get("price"),
                                "T_current": x["record"]["geometry"].get("T_current")} for x in recs],
            "scenario_records_STORED": [compact(x) for x in scen],
            "final_reason_STORED": end_rec["record"]["reason"], "ended_at": iso(end_t),
            "DERIVED_summary": {
                "cutoff": iso(end_t), "minutes_after_confirmation": len(minutes),
                "return_samples": len(closes),
                "closes_in_corridor": sum(1 for m in minutes if m["return_gate_sampled"] and m["close_in_corridor"]),
                "closes_in_economic_region": sum(1 for m in minutes if m["return_gate_sampled"] and m["close_in_economic"]),
                "intrabar_touches_of_economic_region": sum(1 for m in minutes if m["extreme_in_economic_intrabar"]),
                "best_sampled_close_toward_region": s(best), "economic_edge_last": s(edge),
                "best_close_distance_to_region_bps": (bps(best, edge) if d > 0 else bps(edge, best))
                if best is not None and edge is not None else None,
                "extreme_price_during_wait": s(extreme),
                "derived_vs_stored_blockers_all_equal": all(m["derived_equals_stored"] for m in minutes
                                                           if m["derived_equals_stored"] is not None)},
            "minutes": minutes})
    return waits


def main(export: Path, out: Path):
    meta, one, journal, records = load(export)
    pinned = one["evaluation"][V3]["corpus"]["pack"]["feed"]["cache_manifest_sha256"]
    cache, bars = load_cache(export, pinned)
    prov = {
        "db_snapshot": meta, "build": BUILD, "pack": PACK,
        "runs": {rid: {"evaluation_id": EVAL[rid], "status": one["replay"][rid]["status"],
                       "code_version": one["replay"][rid]["config"]["code_version"],
                       "dataset_id": one["evaluation"][rid]["dataset_id"],
                       "pinned_cache_manifest_sha256": one["evaluation"][rid]["corpus"]["pack"]["feed"]["cache_manifest_sha256"],
                       "engine_method": one["replay"][rid]["engine"]["adviser"]["method"],
                       "launch_adviser_method": (one["replay"][rid].get("launch") or {}).get("adviser_method"),
                       "pack_preset_file_method_label": one["evaluation"][rid]["corpus"]["pack"].get("method"),
                       "assurance": {k: one["replay"][rid]["assurance"][k] for k in
                                     ("state", "validator", "validator_version", "checks_passed", "checks_total")},
                       "adviser_format": one["finish"][rid]["adviser_format"],
                       "journal": verify_chain(journal[rid], one["finish"][rid], "journal_seq", "journal_chain", INITIAL_JOURNAL),
                       "evaluation_records": verify_chain(records[rid], one["finish"][rid], "evaluation_seq",
                                                          "evaluation_chain", INITIAL_RECORDS),
                       "journal_kinds": dict(Counter(e["kind"] for e in journal[rid]))} for rid in (V2, V3)},
        "cache": cache,
    }
    dossier = {"provenance": prov, "report_reconciliation": report_counts(one, journal, records),
               "q1_episode_2025_10_26": q1(journal, records, bars), "q1_rule_scope": q1_scope(journal), "q2_confirmations": q2(journal, bars),
               "q3_waits": q3(journal, bars)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "dossier.json").write_text(json.dumps(dossier, indent=1, default=str) + "\n", encoding="utf-8")
    cols = ["entry_attempt_id", "direction", "confirmed_at", "original_setup_expiry", "hard_deadline", "R", "K_trigger",
            "V_rounded", "confirmation_close", "T_confirm", "destination_impulse_B", "limiting_landmark",
            "limiting_is_own_impulse_B", "S15_at_confirmation", "I0", "corridor", "economic_fixed_k_STORED", "G_bps",
            "Q_bps", "margin_bps", "blockers_STORED", "routing", "routing_reason", "final_entry_reason", "in_N",
            "scenario_terminal_STORED", "scenario_terminal_at", "v2_same_boundary_attempt_STORED"]
    with (out / "confirmations.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in dossier["q2_confirmations"]:
            w.writerow(["|".join(r[c]) if isinstance(r[c], list) else r[c] for c in cols])
    mcols = ["wait", "start", "admitted_at_dispatch", "open", "high", "low", "close", "cap_active_at_start",
             "cap_at_dispatch", "corridor_effective", "economic_fixed_k", "close_in_corridor", "close_in_economic",
             "extreme_in_economic_intrabar", "V_contact", "cap_contact", "destination_contact", "G_at_close",
             "Q_at_close", "margin_at_close", "derived_price_blockers", "stored_blockers_in_force",
             "derived_equals_stored", "return_gate_sampled"]
    with (out / "wait_minutes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(mcols)
        for wt in dossier["q3_waits"]:
            for m in wt["minutes"]:
                w.writerow(["|".join(m[c]) if isinstance(m[c], list) else m[c] for c in mcols])
    print(json.dumps({"provenance": {rid: {k: v[k]["matches_finish_commitment"] for k in ("journal", "evaluation_records")}
                                     for rid, v in prov["runs"].items()}, "cache": cache}, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
