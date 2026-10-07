"""One-time read-only diagnosis of the continuous v0.4 September-December 2025 run (build 97a2a8c).

  evaluation eval-20261007T182934-3f41ad  replay obs-20261007T182934-f8c3d4
  pack pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e

Not product code and not a reusable analytics framework. Input, produced by ONE read-only access and never committed:
  <export>/snapshot.jsonl  one REPEATABLE READ READ ONLY psql transaction (export.sql in this folder): meta, the
                           evaluation/replay/checkpoint/finish rows (adviser blob excluded), the pack and cache rows,
                           the complete committed adviser journal and evaluation records of this run
Optional: <export>/report.json, the app's own report export of the evaluation (read-only GET), compared if present.

Nothing replays the professional runtime, the evaluator or a counterfactual; no feed cache is read (every distance
is computed from closes the journal itself stores). Labels:
  STORED       a committed journal/evaluation field (or a count of such fields through the product's report builder)
  DERIVED      exact Decimal arithmetic on STORED fields known at the stated cutoff
  UNAVAILABLE  not recorded and not derivable without a replay/counterfactual (named per field)

The structural evidence (DEFINITIONS.md, registered before the outcome analysis) is computed by ``evidence`` and
``classify``, which receive journal records only - never a path, a guidance terminal or a scenario terminal. Outcomes
are joined afterwards for presentation.

usage: uv run python extract_continuous_diagnosis.py <export_dir> <out_dir>
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path

from algotrader.adviser import report4 as r4
from algotrader.adviser.core import INITIAL_JOURNAL
from algotrader.adviser.evaluator import INITIAL_RECORDS
from algotrader.feed.ordering import canonical

EVAL_ID = "eval-20261007T182934-3f41ad"
RID = "obs-20261007T182934-f8c3d4"
PACK = "pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e"
BUILD = "97a2a8ceb81a42a72f5b1fd84c98b040147dd159"
# Director-quoted reconciliation targets (from the Owner's copied report)
EXPECTED = {"a_confirmations": 89, "waits": 57, "calls": 13, "return_calls": 12, "return_entered_primary": 11,
            "terminal_path_records": 52}
VARIANTS = ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY")
MIN = timedelta(minutes=1)
OPP = {"LONG": "SHORT", "SHORT": "LONG"}
ALIGNED = {"LONG": "UP", "SHORT": "DOWN"}
ADVERSE_SIDE = {"LONG": "LOW", "SHORT": "HIGH"}  # a broken support hurts a LONG, a broken resistance a SHORT
EXP_DIR = {"LONG": "UP", "SHORT": "DOWN"}
H1_CODES = ("S1", "S2", "S3", "S5", "S6")
CODES = ("S1", "S2", "S3", "S4", "S5", "S6")


def dt(s):
    return None if s is None else datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def iso(t):
    return None if t is None else t.isoformat().replace("+00:00", "Z")


def dec(x):
    return None if x is None else Decimal(str(x))


def s(x):
    return None if x is None else format(x, "f") if isinstance(x, Decimal) else str(x)


def fx2(x):
    return None if x is None else format(Decimal(x).quantize(Decimal("0.01")), "f")


def bps(d, ref, x):
    """Signed distance from reference close ``ref`` to ``x`` in the call direction, in bps of ``ref``."""
    if ref is None or x is None:
        return None
    return fx2(Decimal(10000) * d * (dec(x) - dec(ref)) / dec(ref))


def exact_sum(xs):
    with localcontext() as ctx:
        ctx.prec = 400
        return +sum((Decimal(x) for x in xs), Decimal(0))


def minutes(a, b):
    return None if a is None or b is None else int((b - a).total_seconds() // 60)


def pub(e):
    return dt(e["record"]["env"]["published_at"])


def contact_bar(prefix, reason):
    """The 1m bar of a certified contact named in a terminal reason (``...#obs@<bar start>``): bar interval
    [start, start+1m). The instant inside the bar is UNAVAILABLE (no intrabar order is recorded)."""
    start = None
    if reason and "#obs@" in str(reason):
        start = dt(str(reason).split("#obs@")[1])
    return {f"{prefix}_bar_start": iso(start), f"{prefix}_bar_end": iso(start + MIN) if start else None,
            f"{prefix}_intrabar_instant": "UNAVAILABLE" if start else None}


def ceil_minute(t):
    f = t.replace(second=0, microsecond=0)
    return f if f == t else f + MIN


# ----------------------------------------------------------------------------------------------------------------------
# inputs and provenance
# ----------------------------------------------------------------------------------------------------------------------

def load(export: Path):
    one, journal, records, meta = {}, [], [], None
    for line in (export / "snapshot.jsonl").open(encoding="utf-8"):
        if not line.startswith("{"):
            continue
        k, v = next(iter(json.loads(line).items()))
        if k == "meta":
            meta = v
        elif k == "j":
            journal.append(v)
        elif k == "er":
            records.append(v)
        else:
            one[k] = v
    journal.sort(key=lambda e: e["seq"])
    records.sort(key=lambda e: e["seq"])
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


def provenance(meta, one, journal, records, export):
    ev, rep, fin, pk, cache = one["evaluation"], one["replay"], one["finish"], one["pack"], one.get("cache")
    adv = rep["engine"]["adviser"]
    ident = adv["identity"]
    builds = Counter(e["record"]["env"]["method"]["build"] for e in journal if "method" in e["record"].get("env", {}))
    return {
        "db_snapshot": meta,
        "snapshot_jsonl_sha256_not_committed": hashlib.sha256((export / "snapshot.jsonl").read_bytes()).hexdigest(),
        "evaluation_id": ev["evaluation_id"], "replay_id": rep["replay_id"], "status": rep["status"],
        "code_version": rep["config"].get("code_version"), "expected_build": BUILD,
        "record_builds": dict(builds), "build_matches": set(builds) == {BUILD + "+image"},
        "method": adv["method"], "model": ident["model"], "rules_version": ident["rules_version"],
        "rules_sha256": ident["rules_sha256"], "register_sha256": ident["register_sha256"],
        "implementation": ident["implementation"], "identity_sha256": ident["identity_sha256"],
        "capability_profile_sha256": ident.get("capability_profile_sha256"),
        "evaluator": {k: adv["evaluator"].get(k) for k in ("format", "implementation", "sha256")},
        "evaluator_primary_entry_delay_seconds": adv["evaluator"]["profiles"]["PRIMARY"]["entry_delay_seconds"],
        "windows": {k: adv.get(k) for k in ("warmup_start", "eval_start", "eval_end", "tail_end", "clock_end")},
        "initialization": {k: (adv.get("initialization") or {}).get(k) for k in ("policy", "preset_id", "start", "end",
                                                                                 "hours", "evaluated")},
        "pins": ident.get("pins"),
        "pack": {"pack_id": pk["pack_id"], "manifest_sha256": pk["manifest_sha256"], "cache_id": pk["cache_id"],
                 "pack_row_cache_manifest_sha256": pk["cache_manifest_sha256"],
                 "content_identity": pk["content_identity"], "event_count": pk["event_count"]},
        "cache": None if cache is None else {"cache_id": cache["cache_id"],
                                             "cache_manifest_sha256": cache["cache_manifest_sha256"],
                                             "event_count": cache["event_count"]},
        "evaluation_pins_cache": ev["corpus"]["pack"]["feed"]["cache_id"] == pk["cache_id"],
        "evaluation_cache_manifest_matches_pack": ev["corpus"]["pack"]["feed"]["cache_manifest_sha256"]
        == pk["cache_manifest_sha256"],
        "assurance": {k: rep["assurance"].get(k) for k in ("state", "validator", "validator_version", "checks_passed",
                                                          "checks_total")},
        "checkpoint": {k: one["checkpoint"][k] for k in ("cursor", "info_time")},
        "finish": {"adviser_format": fin.get("adviser_format"), "commitment": fin.get("commitment")},
        "journal": verify_chain(journal, fin, "journal_seq", "journal_chain", INITIAL_JOURNAL),
        "evaluation_records": verify_chain(records, fin, "evaluation_seq", "evaluation_chain", INITIAL_RECORDS),
        "journal_kinds": dict(Counter(e["kind"] for e in journal)),
        "record_kinds": dict(Counter(e["kind"] for e in records)),
        "feed_cache_copied": False,
        "feed_cache_note": "not needed: every distance uses closes stored in the journal; outcomes use stored paths",
    }


# ----------------------------------------------------------------------------------------------------------------------
# structural evidence (DEFINITIONS.md) - journal records only, no outcome data
# ----------------------------------------------------------------------------------------------------------------------

def same_dispatch_observations(journal, hi_seq):
    """Observation records journaled AFTER the record ``hi_seq`` in the same dispatch (same clock time). The method
    computes context/phase first and journals them last (dispatch write order: landmark, scenario, entry_attempt,
    call, market_view, material_change, observation), so they were known before that decision (DEFINITIONS erratum)."""
    if hi_seq > len(journal):
        return []
    t = journal[hi_seq - 1]["clock_time"]
    out = []
    for e in journal[hi_seq:]:
        if e["clock_time"] != t:
            break
        if e["kind"] == "observation":
            out.append(e)
    return out


def evidence(journal, lo_seq, hi_seq, d_name, attempt_id, *, inclusive_hi=False, dispatch=True):
    """S1-S6 records with lo_seq < seq < hi_seq (or <= hi_seq), plus (dispatch=True) the observation records of the
    dispatch of ``hi_seq`` (see ``same_dispatch_observations``). journal[i] has seq i+1."""
    end = hi_seq if inclusive_hi else hi_seq - 1
    hits = {c: [] for c in CODES}
    unavailable = []
    rows = journal[lo_seq:max(lo_seq, end)] + (same_dispatch_observations(journal, hi_seq) if dispatch else [])
    for e in rows:
        k, r = e["kind"], e["record"]
        t = r["env"]["published_at"] if "env" in r else e["clock_time"]
        if k == "landmark" and r.get("status") == "BROKEN" and r.get("side") == ADVERSE_SIDE[d_name]:
            hits["S1"].append({"seq": e["seq"], "at": t, "what": f"{r['landmark_type']} {r['price']} BROKEN",
                               "reason": str(r.get("status_reason"))[:60]})
        elif k == "scenario" and r.get("direction") == OPP[d_name] and r.get("transition") in (
                "ARM", "REARM", "REVISE", "CONFIRM"):
            hits["S2"].append({"seq": e["seq"], "at": t, "what": f"{r['family']} {r['direction']} {r['transition']}",
                               "scenario_id": r["scenario_id"]})
        elif k == "market_view" and (r.get("counterevidence") or r.get("expected_direction") == EXP_DIR[OPP[d_name]]):
            hits["S3"].append({"seq": e["seq"], "at": t, "what": "; ".join(r.get("counterevidence") or [])
                               or f"expected_direction {r.get('expected_direction')}",
                               "table_row": r.get("table_row")})
        elif k == "entry_attempt" and r.get("entry_attempt_id") == attempt_id and r.get("transition") == "CAP_REVISION":
            hits["S4"].append({"seq": e["seq"], "at": t, "what": f"cap -> {(r.get('cap_history') or [{}])[-1].get('cap')}",
                               "reason": r.get("reason")})
        elif k == "observation" and r.get("name") == "phase":
            if r.get("category") == "UNAVAILABLE":
                unavailable.append({"seq": e["seq"], "at": t, "what": "phase UNAVAILABLE"})
            elif r.get("category") == "EXPANSION" and (r.get("values") or {}).get("expansion_direction") == \
                    EXP_DIR[OPP[d_name]]:
                hits["S5"].append({"seq": e["seq"], "at": t, "what": f"EXPANSION {r['values']['expansion_direction']}"})
        elif k == "observation" and r.get("name") == "context":
            if r.get("category") == "UNAVAILABLE":
                unavailable.append({"seq": e["seq"], "at": t, "what": "context UNAVAILABLE"})
            elif r.get("category") != ALIGNED[d_name]:
                hits["S6"].append({"seq": e["seq"], "at": t, "what": f"context {r['category']}"})
    return hits, unavailable


def last_obs(journal, hi_seq, name, *, dispatch=True):
    """Latest PUBLISHED observation known at the decision ``hi_seq`` (same-dispatch observations included unless
    ``dispatch`` is False). Observations are publications: the category persists until the next record, but the
    publisher may not emit a new record when only a value changes, so ``values_as_published`` are the values attached
    to that publication at ``published_at`` - not a numeric snapshot certainly current at the decision."""
    rows = journal[:hi_seq - 1] + (same_dispatch_observations(journal, hi_seq) if dispatch else [])
    for e in reversed(rows):
        if e["kind"] == "observation" and e["record"].get("name") == name:
            return {"seq": e["seq"], "published_at": e["record"]["env"]["published_at"],
                    "category": e["record"]["category"], "values_as_published": e["record"].get("values")}
    return None


def observations_known(ctx, phase):
    """Context and phase categories are both known (published and not UNAVAILABLE) at the decision."""
    return all(o is not None and o["category"] != "UNAVAILABLE" for o in (ctx, phase))


def classify(hits, unavailable, *, immediate, returned, known=True):
    """DEFINITIONS classes. Missing required observations (an UNAVAILABLE publication inside the window, or no known
    context/phase category at the decision) give INDETERMINATE - never H2."""
    if immediate:
        return "NOT_APPLICABLE_IMMEDIATE"
    if unavailable or not known:
        return "INDETERMINATE"
    if any(hits[c] for c in H1_CODES):
        return "H1_RECORDED"
    if hits["S4"]:
        return "OBSTACLE_ONLY"
    return "NONE_RECORDED_H2_CONSISTENT" if returned else "NONE_RECORDED"


def counts(hits):
    return {c: len(hits[c]) for c in CODES}


# ----------------------------------------------------------------------------------------------------------------------
# run model
# ----------------------------------------------------------------------------------------------------------------------

class Run:
    def __init__(self, one, journal, records):
        adv = one["replay"]["engine"]["adviser"]
        self.es, self.ee = dt(adv["eval_start"]), dt(adv["eval_end"])
        self.journal, self.records = journal, records
        self.scen = defaultdict(list)
        self.ent = defaultdict(list)
        self.rev = defaultdict(list)
        self.calls = []
        for e in journal:
            r = e["record"]
            if e["kind"] == "scenario":
                self.scen[r["scenario_id"]].append(e)
            elif e["kind"] == "entry_attempt":
                self.ent[r["entry_attempt_id"]].append(e)
            elif e["kind"] == "call_revision":
                self.rev[r["call_id"]].append(e)
            elif e["kind"] == "call":
                self.calls.append(e)
        self.paths = {(x["record"]["call_id"], x["record"]["variant"]): x for x in records if x["kind"] == "path"}

    def in_eval(self, t):
        return self.es <= t < self.ee

    def eval_calls(self):
        return [c for c in self.calls if self.in_eval(dt(c["record"]["issued_at"]))
                and c["record"]["env"]["origin"] == "HISTORICAL_MODELED"]

    def eval_waits(self):
        return [e for es in self.ent.values() for e in es
                if e["record"]["transition"] == "WAIT_OPEN" and self.in_eval(pub(e))]


def scenario_digest(run, sid):
    """Owner/anchor history of the structural scenario up to confirmation (STORED)."""
    rs = run.scen[sid]
    tr = Counter(e["record"]["transition"] for e in rs)
    conf = next((e for e in rs if e["record"]["transition"] == "CONFIRM"), None)
    term = next((e for e in rs if e["record"]["transition"] == "TERMINAL"), None)
    birth = rs[0]["record"] if rs else {}
    pre = [e for e in rs if conf is None or e["seq"] < conf["seq"]]
    return {
        "scenario_id": sid, "owner_id": birth.get("owner_id"), "family": birth.get("family"),
        "direction": birth.get("direction"), "born_at": rs[0]["record"]["env"]["published_at"] if rs else None,
        "warmup_origin": birth.get("warmup_origin"), "destination_B": birth.get("destination"),
        "destination_type": birth.get("destination_type"),
        "pre_confirmation_transitions": dict(Counter(e["record"]["transition"] for e in pre)),
        "anchor_epoch_at_confirmation": conf["record"].get("anchor_epoch") if conf else None,
        "transitions": dict(tr), "confirm_seq": conf["seq"] if conf else None,
        "confirm": None if conf is None else {k: conf["record"].get(k) for k in (
            "confirmed_at", "confirmation_close", "confirmation_scale", "invalidation_level", "trigger_level",
            "reaction_level", "destination", "confirmed_deadline", "progress_check_at", "anchor_status")}
        | {"published_at": conf["record"]["env"]["published_at"]},
        "owner_release": [{"at": e["record"]["env"]["published_at"], "reason": e["record"].get("reason")}
                          for e in rs if e["record"]["transition"] == "OWNER_RELEASE"],
        "terminal": None if term is None else {"seq": term["seq"], "at": term["record"]["env"]["published_at"],
                                               "state": term["record"].get("terminal_state"),
                                               "reason": str(term["record"].get("reason"))[:90]},
    }


def attempt_records(run, aid):
    return [{"seq": e["seq"], "at": e["record"]["env"]["published_at"], "transition": e["record"]["transition"],
             "state": e["record"].get("state"), "reason": None if e["record"].get("reason") is None
             else str(e["record"]["reason"])[:90], "blockers": e["record"].get("blockers"),
             "cap": (e["record"].get("cap_history") or [{}])[-1].get("cap"),
             "price": (e["record"].get("geometry") or {}).get("price")} for e in run.ent[aid]]


def geometry_at_open(run, aid):
    w = next((e for e in run.ent[aid] if e["record"]["transition"] in ("WAIT_OPEN", "ISSUE")), None)
    g = (w or {}).get("record", {}).get("geometry") or {}
    c = (w or {}).get("record", {}).get("clocks") or {}
    return w, {k: g.get(k) for k in ("confirmation_close", "R", "K_trigger", "V", "T_confirm", "T_current", "S15",
                                     "corridor", "economic_current", "economic_fixed_k", "I0", "G", "Q", "margin",
                                     "price_source")}, c


# ----------------------------------------------------------------------------------------------------------------------
# calls (evidence first, outcomes joined afterwards)
# ----------------------------------------------------------------------------------------------------------------------

def call_evidence(run, c):
    r = c["record"]
    d_name, aid, sid = r["direction"], r["attempt_id"], r["scenario_id"]
    sd = scenario_digest(run, sid)
    issue = next(e for e in run.ent[aid] if e["record"]["transition"] == "ISSUE")
    immediate = r.get("entry_mode") == "IMMEDIATE"
    returned = any(e["record"]["transition"] == "RETURN_USABLE" and e["seq"] < issue["seq"] for e in run.ent[aid])
    hits, unav = evidence(run.journal, sd["confirm_seq"], issue["seq"], d_name, aid)
    strict, strict_unav = evidence(run.journal, sd["confirm_seq"], issue["seq"], d_name, aid, dispatch=False)
    ctx, ph = last_obs(run.journal, issue["seq"], "context"), last_obs(run.journal, issue["seq"], "phase")
    known = observations_known(ctx, ph)
    known_strict = observations_known(last_obs(run.journal, issue["seq"], "context", dispatch=False),
                                      last_obs(run.journal, issue["seq"], "phase", dispatch=False))
    return {"strict_seq_counts": counts(strict), "observations_known_at_issue": known,
            "strict_seq_classification": classify(strict, strict_unav, immediate=immediate, returned=returned,
                                                  known=known_strict),"call_id": r["call_id"], "issue_seq": issue["seq"], "confirm_seq": sd["confirm_seq"],
            "window_records": issue["seq"] - sd["confirm_seq"] - 1, "evidence_counts": counts(hits),
            "evidence": hits, "unavailable": unav, "returned_before_issue": returned,
            "context_at_issue": ctx, "phase_at_issue": ph,
            "context_at_confirmation": last_obs(run.journal, sd["confirm_seq"], "context"),
            "classification": classify(hits, unav, immediate=immediate, returned=returned, known=known)}


def call_row(run, c, ev):
    r = c["record"]
    d = 1 if r["direction"] == "LONG" else -1
    aid, sid, cid = r["attempt_id"], r["scenario_id"], r["call_id"]
    sd = scenario_digest(run, sid)
    w, g, clocks = geometry_at_open(run, aid)
    ents = run.ent[aid]
    tc = dt(sd["confirm"]["published_at"])
    ti = dt(r["issued_at"])
    hard = dt(r["hard_deadline"])
    act = r.get("actionability") or {}
    usable = [e for e in ents if e["record"]["transition"] == "RETURN_USABLE"]
    blockers = Counter(b for e in ents if e["seq"] < ev["issue_seq"] for b in (e["record"].get("blockers") or []))
    revs = run.rev[cid]
    term = next((e for e in revs if e["record"]["thesis_status"] != "ONGOING"), None)
    p = {v: (run.paths.get((cid, v)) or {}).get("record") for v in VARIANTS}
    pr = p["PRIMARY"] or {}
    entry = (pr.get("entry") or {})
    t_entry = dt(entry.get("time_start"))
    # entry-status timeline up to the PRIMARY entry (or to the terminal when there is no entry)
    status_tl = [{"at": e["record"]["env"]["published_at"], "rev": e["record"]["revision"],
                  "entry_status": e["record"]["entry_status"], "reasons": e["record"].get("entry_reasons"),
                  "thesis": e["record"]["thesis_status"]} for e in revs
                 if "entry" in (e["record"].get("changed") or []) or e["record"]["thesis_status"] != "ONGOING"]
    first_boundary = ceil_minute(ti + timedelta(seconds=60))
    # post-issue evidence (descriptive only)
    entry_seq_hi = None
    if t_entry is not None:
        entry_seq_hi = max((e["seq"] for e in run.journal[ev["issue_seq"]:] if dt(e["clock_time"]) <= t_entry),
                           default=ev["issue_seq"])
    h_entry, _ = (evidence(run.journal, ev["issue_seq"], entry_seq_hi, r["direction"], aid, inclusive_hi=True)
                  if entry_seq_hi else ({c_: [] for c_ in CODES}, []))
    h_hold, _ = (evidence(run.journal, entry_seq_hi or ev["issue_seq"], term["seq"], r["direction"], aid,
                          inclusive_hi=True) if term else ({c_: [] for c_ in CODES}, []))
    conf = sd["confirm"]
    row = {
        "call_id": cid, "issue_month": f"{ti:%Y-%m}", "family": r["family"], "direction": r["direction"],
        "entry_mode": r.get("entry_mode"), "scenario_id": sid, "owner_id": sd["owner_id"],
        "scenario_born_at": sd["born_at"], "anchor_epoch_at_confirmation": sd["anchor_epoch_at_confirmation"],
        "pre_confirmation_transitions": sd["pre_confirmation_transitions"],
        "confirmed_at": conf["published_at"], "wait_open_at": w["record"]["env"]["published_at"]
        if w and w["record"]["transition"] == "WAIT_OPEN" else None,
        "first_return_usable_at": usable[0]["record"]["env"]["published_at"] if usable else None,
        "issued_at": r["issued_at"], "confirmation_to_issue_min": minutes(tc, ti),
        "setup_expiry": clocks.get("setup_expiry"), "hard_deadline": r["hard_deadline"],
        "residual_at_issue_min": minutes(ti, hard),
        # at confirmation (STORED geometry of the WAIT_OPEN/ISSUE record; DERIVED distances)
        "conf_close": conf["confirmation_close"], "R": g["R"], "K_trigger": g["K_trigger"], "V": g["V"],
        "V_structural_scenario": conf["invalidation_level"], "V_operational_tick": r["invalidation"],
        "T_confirm": g["T_confirm"], "S15_conf": g["S15"] or conf["confirmation_scale"], "corridor": g["corridor"],
        "economic_initial": g["economic_current"], "I0": g["I0"],
        "conf_close_to_V_bps": bps(d, conf["confirmation_close"], g["V"] or r["invalidation"]),
        "conf_close_to_T_bps": bps(d, conf["confirmation_close"], g["T_confirm"] or r["target_at_confirmation"]),
        # at issue
        "issue_close": r.get("issue_reference"), "issue_side_price_source": act.get("side_price_source"),
        "issue_V": r["invalidation"], "issue_T": r["target"], "target_type": r.get("target_type"),
        "structural_area": r.get("structural_area"), "admissible_bounds": act.get("admissible_bounds"),
        "issue_close_to_V_bps": bps(d, r.get("issue_reference"), r["invalidation"]),
        "issue_close_to_T_bps": bps(d, r.get("issue_reference"), r["target"]),
        "stored_gain_bps": fx2(act.get("gain_bps")), "stored_risk_bps": fx2(act.get("risk_bps")),
        "stored_reward_risk_margin": fx2(act.get("reward_risk_margin")), "cap_history": r.get("cap_history"),
        "S15_issue": r.get("issue_scale"),
        "issue_close_minus_conf_close_in_S15_conf": None if not r.get("issue_reference") else fx2(
            d * (dec(r["issue_reference"]) - dec(conf["confirmation_close"])) / dec(conf["confirmation_scale"])),
        "wait_records_before_issue": sum(1 for e in ents if e["seq"] < ev["issue_seq"]),
        "blockers_seen_before_issue": dict(blockers),
        # evidence (pre-issue; DEFINITIONS.md)
        "pre_issue_window_records": ev["window_records"], "classification": ev["classification"],
        **{f"pre_{k}": v for k, v in ev["evidence_counts"].items()},
        "classification_strict_seq": ev["strict_seq_classification"],
        "strict_seq_differs": ev["strict_seq_counts"] != ev["evidence_counts"],
        "observations_known_at_issue": ev["observations_known_at_issue"],
        "context_at_confirmation": (ev["context_at_confirmation"] or {}).get("category"),
        "context_at_confirmation_published_at": (ev["context_at_confirmation"] or {}).get("published_at"),
        "context_at_issue": (ev["context_at_issue"] or {}).get("category"),
        "context_at_issue_published_at": (ev["context_at_issue"] or {}).get("published_at"),
        "phase_at_issue": (ev["phase_at_issue"] or {}).get("category"),
        "phase_at_issue_published_at": (ev["phase_at_issue"] or {}).get("published_at"),
        # entry
        "first_candidate_boundary_primary": iso(first_boundary), "entry_status_timeline": status_tl,
        "primary_entry_at": entry.get("time_start"), "primary_entry_price": entry.get("price"),
        "primary_entry_after_issue_min": minutes(ti, t_entry), "primary_entry_attempts": pr.get("entry_attempts"),
        "primary_rejected_opens": pr.get("rejected_opens"),
        "primary_no_entry_class": pr.get("exit_class") if pr.get("status") == "NO_ENTRY" else None,
        "primary_entry_open_to_V_operational_bps": bps(d, entry.get("price"), r["invalidation"]),
        "primary_entry_open_to_T_bps": bps(d, entry.get("price"), r["target"]),
        **{f"entry_window_{k}": len(v) for k, v in h_entry.items()},
        # outcomes (joined after the evidence; STORED)
        "guidance_terminal": term["record"]["thesis_status"] if term else "ONGOING_AT_END",
        "guidance_terminal_reason": None if not term else str(term["record"].get("terminal_reason"))[:80],
        "guidance_terminal_published_at": term["record"]["env"]["published_at"] if term else None,
        **contact_bar("guidance_contact", None if not term else term["record"].get("terminal_reason")),
        "scenario_terminal": (sd["terminal"] or {}).get("state"),
        "scenario_terminal_reason": (sd["terminal"] or {}).get("reason"),
        "scenario_terminal_published_at": (sd["terminal"] or {}).get("at"), "destination_B": sd["destination_B"],
        "primary_status": pr.get("status"), "primary_exit_class": pr.get("exit_class"),
        "primary_exit_fill_start": (pr.get("exit") or {}).get("time_start"),
        "primary_exit_fill_end": (pr.get("exit") or {}).get("time_end"),
        "primary_exit_reason": (pr.get("exit") or {}).get("reason"),
        "primary_exit_price": (pr.get("exit") or {}).get("price"), "primary_held_min": pr.get("held_minutes"), "primary_price_net": pr.get("price_net"),
        "primary_mfe": pr.get("mfe"), "primary_mae": pr.get("mae"),
        **{f"{v.lower()}_status": (p[v] or {}).get("status") for v in VARIANTS[1:]},
        **{f"{v.lower()}_price_net": (p[v] or {}).get("price_net") for v in VARIANTS[1:]},
        **{f"{v.lower()}_entry_open_at": ((p[v] or {}).get("entry") or {}).get("time_start") for v in VARIANTS[1:]},
        **{f"{v.lower()}_exit_fill_start": ((p[v] or {}).get("exit") or {}).get("time_start") for v in VARIANTS[1:]},
        **{f"hold_window_{k}": len(v) for k, v in h_hold.items()},
    }
    return row


def call_timeline(run, c, ev):
    """Chronological STORED records linking scenario, attempt, call, revisions and paths."""
    r = c["record"]
    cid, sid, aid = r["call_id"], r["scenario_id"], r["attempt_id"]
    out = []
    for e in run.scen[sid]:
        x = e["record"]
        out.append((e["seq"], x["env"]["published_at"], "scenario", x["transition"],
                    f"status {x.get('status')} anchor {x.get('anchor_epoch')} R {x.get('reaction_level')} "
                    f"K {x.get('trigger_level')} V {x.get('invalidation_level')} B {x.get('destination')}"
                    + (f" term {x.get('terminal_state')}" if x.get("terminal_state") else "")
                    + (f" reason {str(x.get('reason'))[:70]}" if x.get("reason") else "")))
    for e in run.ent[aid]:
        x = e["record"]
        out.append((e["seq"], x["env"]["published_at"], "entry_attempt", x["transition"],
                    f"state {x.get('state')} blockers {','.join(x.get('blockers') or []) or '-'} price "
                    f"{(x.get('geometry') or {}).get('price')} cap {(x.get('cap_history') or [{}])[-1].get('cap')}"
                    + (f" reason {str(x.get('reason'))[:70]}" if x.get("reason") else "")))
    out.append((c["seq"], r["issued_at"], "call", "NEW_CALL",
                f"{r['direction']} {r.get('entry_mode')} ref {r.get('issue_reference')} V {r['invalidation']} "
                f"T {r['target']} area {r.get('structural_area')}"))
    for e in run.rev[cid]:
        x = e["record"]
        out.append((e["seq"], x["env"]["published_at"], "call_revision", x["thesis_status"],
                    f"r{x['revision']} entry {x['entry_status']} {','.join(x.get('entry_reasons') or [])} changed "
                    f"{','.join(x.get('changed') or [])}"
                    + (f" terminal {str(x.get('terminal_reason'))[:70]}" if x.get("terminal_reason") else "")))
    for code, hs in ev["evidence"].items():
        for h in hs:
            out.append((h["seq"], h["at"], f"evidence_{code}", "PRE_ISSUE", h["what"][:100]))
    for v in VARIANTS:
        p = (run.paths.get((cid, v)) or {}).get("record")
        if not p:
            continue
        if p.get("entry"):
            out.append((None, p["entry"]["time_start"], f"path_{v}", "ENTRY", f"open {p['entry']['price']}"))
        out.append((None, (p.get("exit") or {}).get("time_start") or p.get("resolved_at"), f"path_{v}", p["status"],
                    f"{p.get('exit_class')} exit {(p.get('exit') or {}).get('price')} price_net {p.get('price_net')}"))
    out.sort(key=lambda x: (dt(x[1]), x[0] if x[0] is not None else 10**12))
    return [{"call_id": cid, "seq": a, "at": b, "object": k, "event": t, "detail": dd} for a, b, k, t, dd in out]


# ----------------------------------------------------------------------------------------------------------------------
# WAITs
# ----------------------------------------------------------------------------------------------------------------------

def wait_row(run, w):
    r = w["record"]
    aid, sid, d_name = r["entry_attempt_id"], r["scenario_id"], r["direction"]
    d = 1 if d_name == "LONG" else -1
    ents = run.ent[aid]
    sd = scenario_digest(run, sid)
    g = r.get("geometry") or {}
    end = next((e for e in ents if e["record"]["transition"] in ("ISSUE", "TERMINAL", "REJECT")), None)
    issued = end is not None and end["record"]["transition"] == "ISSUE"
    usable = [e for e in ents if e["record"]["transition"] == "RETURN_USABLE"]
    hi = end["seq"] if end else len(run.journal) + 1
    hits, unav = evidence(run.journal, sd["confirm_seq"], hi, d_name, aid, inclusive_hi=not issued)
    strict, strict_unav = evidence(run.journal, sd["confirm_seq"], hi, d_name, aid, inclusive_hi=not issued,
                                   dispatch=False)
    hi_obs = min(hi, len(run.journal))
    known = observations_known(last_obs(run.journal, hi_obs, "context"), last_obs(run.journal, hi_obs, "phase"))
    known_strict = observations_known(last_obs(run.journal, hi_obs, "context", dispatch=False),
                                      last_obs(run.journal, hi_obs, "phase", dispatch=False))
    blockers = Counter(b for e in ents if e["record"]["transition"] == "BLOCKERS" for b in e["record"]["blockers"])
    caps = [{"at": e["record"]["env"]["published_at"], "cap": (e["record"].get("cap_history") or [{}])[-1].get("cap"),
             "reason": e["record"].get("reason")} for e in ents if e["record"]["transition"] == "CAP_REVISION"]
    st = sd["terminal"]
    end_at = end["record"]["env"]["published_at"] if end else None
    return {
        "attempt_id": aid, "scenario_id": sid, "open_month": f"{pub(w):%Y-%m}", "direction": d_name,
        "owner_id": sd["owner_id"], "anchor_epoch_at_confirmation": sd["anchor_epoch_at_confirmation"],
        "wait_open_at": r["env"]["published_at"], "setup_expiry": (r.get("clocks") or {}).get("setup_expiry"),
        "hard_deadline": (r.get("clocks") or {}).get("hard_deadline"),
        "open_reason": r.get("reason"), "open_blockers": r.get("blockers"),
        "conf_close": g.get("confirmation_close"), "R": g.get("R"), "K_trigger": g.get("K_trigger"), "V": g.get("V"),
        "T_confirm": g.get("T_confirm"), "S15": g.get("S15"), "corridor": g.get("corridor"),
        "economic_initial": g.get("economic_current"),
        "conf_close_to_V_bps": bps(d, g.get("confirmation_close"), g.get("V")),
        "conf_close_to_T_bps": bps(d, g.get("confirmation_close"), g.get("T_confirm")),
        "n_records": len(ents), "n_blocker_updates": sum(1 for e in ents if e["record"]["transition"] == "BLOCKERS"),
        "blockers_seen": dict(blockers), "cap_revisions": caps,
        "return_usable_at": [e["record"]["env"]["published_at"] for e in usable],
        "end_transition": end["record"]["transition"] if end else "OPEN_AT_END",
        "end_reason": None if not end else str(end["record"].get("reason"))[:90], "end_at": end_at,
        "minutes_open": minutes(pub(w), dt(end_at)) if end_at else None,
        "issued_call_id": end["record"].get("call_id") if issued else None,
        "class": "ISSUED" if issued else ("RETURN_USABLE_NOT_ISSUED" if usable else "ENDED_WITHOUT_USABLE_RETURN"),
        "scenario_terminal": (st or {}).get("state"), "scenario_terminal_reason": (st or {}).get("reason"),
        "scenario_terminal_published_at": (st or {}).get("at"),
        "scenario_terminal_same_dispatch_as_entry_end": bool(st and end_at and st["at"] == end_at),
        "scenario_terminal_before_entry_end": bool(st and end and st["seq"] < end["seq"]),
        "owner_release_during_wait": [x for x in sd["owner_release"] if end_at and r["env"]["published_at"]
                                      <= x["at"] <= end_at],
        "window_class": classify(hits, unav, immediate=False, returned=bool(usable), known=known),
        "observations_known_at_end": known,
        **{f"win_{k}": v for k, v in counts(hits).items()}, "window_unavailable": len(unav),
        "window_class_strict_seq": classify(strict, strict_unav, immediate=False, returned=bool(usable),
                                           known=known_strict),
    }


# ----------------------------------------------------------------------------------------------------------------------
# reconciliation, totals and tabulations
# ----------------------------------------------------------------------------------------------------------------------

def reconcile(rep, run, calls, waits, export):
    f = rep["funnel"]
    ret = [c for c in calls if c["entry_mode"] == "RETURN"]
    got = {"a_confirmations": f["a_confirmations"], "waits": len(waits), "calls": len(calls),
           "return_calls": len(ret), "return_entered_primary": sum(1 for c in ret if c["primary_entry_at"]),
           "terminal_path_records": sum(1 for x in run.records if x["kind"] == "path")}
    out = {"expected": EXPECTED, "extracted": got, "report_funnel": {
        "issued": f.get("issued"), "a_confirmations": f.get("a_confirmations"),
        "waits_opened": (f.get("waiting") or {}).get("opened")},
        "matches": {k: got[k] == EXPECTED[k] for k in EXPECTED},
        "report_issued_equals_calls": f.get("issued") == len(calls),
        "report_waits_equals_waits": (f.get("waiting") or {}).get("opened") == len(waits)}
    inv = [c for c in ret if c["guidance_terminal"] == "INVALIDATED"]
    tgt = [c for c in ret if c["guidance_terminal"] == "TARGET_REACHED"]
    out["return_outcome_identities"] = {
        "return": len(ret), "invalidated": len(inv), "target_reached": len(tgt),
        "invalidated_entered_primary_stopped": sum(1 for c in inv if c["primary_status"] == "CLOSED"
                                                   and c["primary_exit_class"] == "STOP"),
        "invalidated_primary_no_entry": sum(1 for c in inv if c["primary_status"] == "NO_ENTRY"),
        "return_eq_invalidated_plus_target": len(ret) == len(inv) + len(tgt),
        "invalidated_eq_stopped_plus_no_entry": len(inv) == sum(
            1 for c in inv if (c["primary_status"] == "CLOSED" and c["primary_exit_class"] == "STOP")
            or c["primary_status"] == "NO_ENTRY")}
    periods = rep.get("periods") or {}
    out["periods_reconciliation_all_passed"] = (periods.get("reconciliation") or {}).get("all_passed")
    out["periods_outcome_completeness"] = (periods.get("outcome_completeness") or {}).get("state")
    out["periods_path_records"] = {k: v for k, v in (periods.get("path_records") or {}).items()
                                   if k in ("available", "admitted", "extraneous", "duplicates", "expected_missing")}
    app = export / "report.json"
    if app.exists():
        a = json.loads(app.read_text(encoding="utf-8"))["adviser"]
        out["app_report_export"] = {
            "sha256_not_committed": hashlib.sha256(app.read_bytes()).hexdigest(),
            "funnel_equal": a["funnel"] == rep["funnel"], "outcomes_equal": a.get("outcomes") == rep.get("outcomes"),
            "periods_equal": a.get("periods") == rep.get("periods")}
    return out


def totals(run, calls):
    out = {}
    for v in VARIANTS:
        ps = [run.paths[(c["call_id"], v)]["record"] for c in calls if (c["call_id"], v) in run.paths]
        nets = [p["price_net"] for p in ps if p["status"] == "CLOSED" and p.get("price_net") is not None]
        out[v] = {"records": len(ps), "status": dict(Counter(p["status"] for p in ps)),
                  "closed_with_price_net": len(nets), "sum_price_net_exact": s(exact_sum(nets)) if nets else None,
                  "exit_class": dict(Counter(p.get("exit_class") for p in ps))}
    out["meaning"] = ("exact sums of the STORED normalized one-unit price-net values (N0=1, q=1/E); not an account "
                      "return, not compounded; funding not covered (PRICE_NET_ONLY)")
    return out


def tabulate(calls, waits):
    by = defaultdict(list)
    for c in calls:
        by[c["classification"]].append(c["call_id"])
    xt = Counter((c["classification"], c["guidance_terminal"]) for c in calls)
    ev_by_outcome = defaultdict(lambda: Counter())
    for c in calls:
        grp = "TARGET_REACHED" if c["guidance_terminal"] == "TARGET_REACHED" else "OTHER_TERMINAL"
        for k in CODES:
            ev_by_outcome[grp][k] += 1 if c[f"pre_{k}"] else 0
        ev_by_outcome[grp]["calls"] += 1
    wc = Counter((w["class"], w["window_class"]) for w in waits)
    wev = defaultdict(Counter)
    for w in waits:
        for k in CODES:
            wev[w["class"]][k] += 1 if w[f"win_{k}"] else 0
        wev[w["class"]]["waits"] += 1
    return {"calls_by_classification": {k: v for k, v in sorted(by.items())},
            "classification_x_guidance_terminal": {f"{a} / {b}": n for (a, b), n in sorted(xt.items())},
            "calls_with_evidence_type_by_outcome_group": {k: dict(v) for k, v in ev_by_outcome.items()},
            "waits_class_x_window_class": {f"{a} / {b}": n for (a, b), n in sorted(wc.items())},
            "waits_with_evidence_type_by_class": {k: dict(v) for k, v in wev.items()},
            "note": ("counts of calls/WAITs with at least one record of each type in their window; WAITs that never "
                     "returned are not controls for entered calls (different windows, no entry, no outcome)")}


# ----------------------------------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------------------------------

def _csv(path, rows, cols):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v) for k, v in r.items()})


def main(export: Path, out: Path):
    meta, one, journal, records = load(export)
    run = Run(one, journal, records)
    rep_row = one["replay"]
    rep = r4.build(engine=rep_row["engine"], journal=[{"seq": e["seq"], "kind": e["kind"], "clock_time": e["clock_time"],
                                                       "record": e["record"]} for e in journal],
                   records=[{"seq": e["seq"], "kind": e["kind"], "record": e["record"]} for e in records],
                   view=(one["checkpoint"] or {}).get("adviser_view"), status=rep_row["status"],
                   clock_end_reached=bool(one.get("finish")))
    # 1. evidence (no outcome data), 2. rows with outcomes joined
    calls_raw = run.eval_calls()
    evs = {c["record"]["call_id"]: call_evidence(run, c) for c in calls_raw}
    calls = [call_row(run, c, evs[c["record"]["call_id"]]) for c in calls_raw]
    timeline = [x for c in calls_raw for x in call_timeline(run, c, evs[c["record"]["call_id"]])]
    waits = [wait_row(run, w) for w in sorted(run.eval_waits(), key=lambda e: e["seq"])]
    defs = (Path(__file__).parent / "DEFINITIONS.md").read_bytes()
    dossier = {
        "title": "Continuous v0.4 September-December 2025 - confirmation -> WAIT -> issue -> entry -> outcome",
        "director_acceptance_recorded": ("Prova continua accettata come evidenza descrittiva di sviluppo; risultato "
                                         "negativo; causa non identificata; nessuna modifica metodologica "
                                         "autorizzata."),
        "definitions_file_sha256": hashlib.sha256(defs).hexdigest(),
        "provenance": provenance(meta, one, journal, records, export),
        "reconciliation": reconcile(rep, run, calls, waits, export),
        "totals": totals(run, [c["record"] for c in calls_raw]),
        "tabulations": tabulate(calls, waits),
        "calls": calls,
        "call_evidence": {k: {"evidence": v["evidence"], "unavailable": v["unavailable"],
                              "context_at_issue": v["context_at_issue"], "phase_at_issue": v["phase_at_issue"]}
                          for k, v in evs.items()},
        "waits": waits,
        "levels_and_times": {
            "V_structural_scenario": "the confirmed scenario's frozen V (scenario CONFIRM invalidation_level, unrounded)",
            "V_operational_tick": ("the call/guidance V: derived from the structural V and tick-rounded away from the "
                                   "entry (call invalidation; also the WAIT geometry V)"),
            "distances": ("every *_to_V_* distance uses V_operational_tick; conf_close_* use the stored confirmation "
                          "close, issue_close_* the stored issue reference close, primary_entry_open_* the stored "
                          "modeled PRIMARY entry OPEN; the denominator is always that reference price"),
            "terminal_times": ("*_published_at = journal publication of the terminal record; *_contact_bar_start/"
                               "end = the certified 1m contact bar named in the reason; the instant inside the bar is "
                               "UNAVAILABLE"),
            "path_times": "entry/exit fills are the evaluator's modeled fills (time_start/time_end of the fill)"},
        "observation_limits": (
            "S1-S6 count PUBLISHED occurrences, not every possible state change. Observation categories persist until "
            "the next publication; values attached to the last publication are as of its published_at and the "
            "publisher may not emit when only a value changes, so they are not a certainly-current numeric snapshot. "
            "S1 is a landmark break, S2 an opposite-direction scenario transition, S3 counterevidence of the "
            "aggregate view - none is automatically specific to the call. The absence of S5/S6 at issue is expected "
            "from the method's gates (A withdrawal on forbidden context / opposite expansion) and is not an "
            "independent check of selection quality."),
        "unavailable": {
            "intrabar_order": "order of high/low inside a minute is not recorded (stored contacts only)",
            "quotes": "historical bid/ask were not recorded; the modeled side price is the complete-minute close",
            "news_calendar": "calendar/news coverage UNKNOWN for the whole run",
            "unrecorded_structure": ("structure the method does not journal (e.g. lower-timeframe swings, order flow) "
                                     "cannot be reconstructed without a replay; absence of a record is not absence"),
            "post_confirmation_anchor_revisions": "none exist by rule (MP-002 §3: frozen at confirmation)"},
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "dossier.json").write_text(json.dumps(dossier, indent=1, sort_keys=False, default=str) + "\n",
                                      encoding="utf-8")
    _csv(out / "calls.csv", calls, list(calls[0]))
    _csv(out / "waits.csv", waits, list(waits[0]))
    _csv(out / "call_timeline.csv", timeline, ["call_id", "seq", "at", "object", "event", "detail"])
    print(json.dumps({"reconciliation": dossier["reconciliation"]["matches"],
                      "chains": [dossier["provenance"]["journal"]["matches_finish_commitment"],
                                 dossier["provenance"]["evaluation_records"]["matches_finish_commitment"]],
                      "build_matches": dossier["provenance"]["build_matches"],
                      "classification": dossier["tabulations"]["calls_by_classification"]}, indent=1))


def selfcheck():
    """Synthetic probes of classify()/evidence() (no export needed)."""
    def obs(seq, t, name, cat, **values):
        return {"seq": seq, "kind": "observation", "clock_time": t,
                "record": {"name": name, "category": cat, "values": values, "env": {"published_at": t}}}

    def ent(seq, t, tr):
        return {"seq": seq, "kind": "entry_attempt", "clock_time": t,
                "record": {"entry_attempt_id": "a", "transition": tr, "env": {"published_at": t}}}
    t0, t1 = "2025-09-01T00:00:00Z", "2025-09-01T00:10:00Z"
    full = [obs(1, t0, "context", "UP"), obs(2, t0, "phase", "REACTION"), ent(3, t0, "WAIT_OPEN"),
            ent(4, t1, "ISSUE")]
    missing_phase = [obs(1, t0, "context", "UP"), ent(2, t0, "WAIT_OPEN"), ent(3, t1, "ISSUE")]
    none = [ent(1, t0, "WAIT_OPEN"), ent(2, t1, "ISSUE")]
    unavailable_ctx = [obs(1, t0, "context", "UNAVAILABLE"), obs(2, t0, "phase", "REACTION"), ent(3, t0, "WAIT_OPEN"),
                       ent(4, t1, "ISSUE")]
    out = {}
    for name, j in (("full", full), ("missing_phase", missing_phase), ("no_observations", none),
                    ("context_unavailable", unavailable_ctx)):
        issue = j[-1]["seq"]
        h, u = evidence(j, issue - 2, issue, "LONG", "a")
        known = observations_known(last_obs(j, issue, "context"), last_obs(j, issue, "phase"))
        out[name] = classify(h, u, immediate=False, returned=True, known=known)
    expected = {"full": "NONE_RECORDED_H2_CONSISTENT", "missing_phase": "INDETERMINATE",
                "no_observations": "INDETERMINATE", "context_unavailable": "INDETERMINATE"}
    assert out == expected, out
    print(json.dumps({"selfcheck": out, "passed": True}))


if __name__ == "__main__":
    if sys.argv[1:] == ["--selfcheck"]:
        selfcheck()
    else:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
