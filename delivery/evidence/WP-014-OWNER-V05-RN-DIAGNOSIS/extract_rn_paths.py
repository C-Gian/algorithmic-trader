"""Read-only diagnosis of the four R->N paths (first recovery observed, not issuable) of the Owner v0.5 run.

  evaluation eval-20261009T155751-be8b2b  replay obs-20261009T155751-0f255b  build eab7d23
  method btc.context-action.v0.5 / mp004.rules.v0.5 (rules 0e34059a17f6, register 255ab5b7cc59)

Not product code. Input: raw responses of the app's own read-only GET surfaces, kept OUTSIDE Git (no DB extraction):
  <export>/evaluation.json, report.json   GET /api/evaluations/<id>, /report.json
  <export>/ea_*.json                      GET /api/adviser/journal/<replay>?kind=entry_attempt (all pages)
  <export>/sc_*.json                      GET /api/adviser/journal/<replay>?kind=scenario (all pages)
  <export>/win_<cursor>.json              GET /api/adviser/runs/<replay>/window?cursor=<recovery decision cursor>&
                                          before=40&after=0 (pinned SHA-verified cache, events strictly before the
                                          cursor of the recovery dispatch: no later bar is read)

Nothing replays the runtime or evaluates an alternative rule. Formulas are the pinned ones imported from the build
(geometry.predicate / admissible_bounds, core5.local_verdict / primary_reason) with the run's register values.
Labels: STORED (a committed journal/report field or a pinned-cache bar), DERIVED (exact arithmetic on STORED inputs
available at the stated record's cutoff), UNAVAILABLE (not recorded by the surfaces used).

Definitions (Director): E0 = prices admitted by corridor and economics at the preparation; E1 = the same at the first
recovery; F = prices satisfying the local recovery close (LONG >= H0 + tick, SHORT <= L0 - tick).

usage: uv run python extract_rn_paths.py <export_dir> <out_dir>
"""

from __future__ import annotations

import glob
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

from algotrader.adviser import geometry as geo
from algotrader.adviser import methods
from algotrader.adviser.core5 import local_verdict, primary_reason, reason_class
from algotrader.adviser.measures import round_down, round_up

EVAL_ID = "eval-20261009T155751-be8b2b"
RID = "obs-20261009T155751-0f255b"
BUILD = "eab7d23438d7188118600dbb358f9136f96bd32b"
RULES = "0e34059a17f6655b72d003261ceaa7283dda7906078b8cb6e264bbf3387334ac"
REGISTER = "255ab5b7cc591b9ea32cb6978d4b0e929063b68f4b19d2f2ae22a0d38dc280cc"
# Director-quoted reconciliation (Owner report): R=4, N=4, I=0; incidence RR 4, corridor 1; primary RR 3, corridor 1
EXPECTED = {"R": 4, "N": 4, "I": 0, "incidence": {"REWARD_RISK_BELOW_MINIMUM": 4, "CLOSE_OUTSIDE_RETURN_CORRIDOR": 1},
            "primary": {"REWARD_RISK_BELOW_MINIMUM": 3, "CLOSE_OUTSIDE_RETURN_CORRIDOR": 1},
            "cohorts": {"2025-09": 1, "2025-11": 1, "2025-12": 2}, "directions": {"LONG": 1, "SHORT": 3}}
DNAME = {1: "LONG", -1: "SHORT"}


def D(x):
    return None if x is None else Decimal(str(x))


def s(x):
    return None if x is None else format(x, "f") if isinstance(x, Decimal) else str(x)


def rng(x):
    if x is None:
        return None
    a, b = x.split("..")
    return Decimal(a), Decimal(b)


def srng(x):
    return None if x is None else f"{x[0]}..{x[1]}"


def ratio(g, q, k):
    return None if g is None or q is None else (g - k) / (q + k)


def f4(x):
    return None if x is None else format(x.quantize(Decimal("0.0001")), "f")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pages(export: Path, prefix: str) -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(export / f"{prefix}_*.json")), key=lambda x: int(Path(x).stem.split("_")[1])):
        out += json.loads(Path(f).read_text(encoding="utf-8"))["records"]
    seqs = [r["seq"] for r in out]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs), f"{prefix}: pages not contiguous/ordered"
    return out


def corridor_market(d: int, r: Decimal, k: Decimal, v_op: Decimal, t: Decimal, cap: Decimal, tick: Decimal):
    """core3._corridor + Wait.corridor (transformed axis, inward ticks), returned in market prices (ascending)."""
    r_t, k_t = r * d, k * d
    lo_t = max(round_up(r_t, tick), v_op * d + tick)
    hi_t = min(round_down(k_t, tick), t * d - tick)
    hi_t = min(hi_t, cap * d - tick)
    if hi_t < lo_t:
        return None
    return (lo_t, hi_t) if d > 0 else (-hi_t, -lo_t)


def intersect(a, b):
    if a is None or b is None:
        return None
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo <= hi else None


def f_with(d: int, region, thr: Decimal):
    """region ∩ F with F = [thr, +inf) LONG or (-inf, thr] SHORT; also the signed gap (>0 = empty by that much)."""
    if region is None:
        return None, None
    lo, hi = region
    if d > 0:
        return ((max(lo, thr), hi) if max(lo, thr) <= hi else None), thr - hi
    return ((lo, min(hi, thr)) if lo <= min(hi, thr) else None), lo - thr


def path(child: str, ea: list[dict], sc: list[dict], export: Path, p, tick_reg: str) -> dict:
    recs = [r for r in ea if r["subject"] == child]
    wo = next(r for r in recs if r["record"]["transition"] == "WAIT_OPEN")
    prep = next(r for r in recs if r["record"]["transition"] == "RESPONSE_REFERENCE")
    term = next(r for r in recs if (r["record"].get("reason") or "").startswith("RESPONSE_NOT_ISSUABLE"))
    between = [r for r in recs if prep["seq"] < r["seq"] < term["seq"]]
    W, P, T = wo["record"], prep["record"], term["record"]
    d = 1 if T["direction"] == "LONG" else -1
    sid = T["scenario_id"]
    scen = [r for r in sc if r["subject"] == sid]
    conf = next(r for r in scen if r["record"]["status"] == "CONFIRMED")
    scen_between = [r["seq"] for r in scen if prep["seq"] < r["seq"] < term["seq"]]
    gp, gt = P["geometry"], T["geometry"]
    ref, resp = P["response"], T["response"]
    tick = D(gp["tick"])
    assert s(tick) == tick_reg or tick == D(tick_reg)
    k_cost, rr = D(gp["K_cost"]), p.rr_min
    v_op, v_struct = D(gp["V"]), D(conf["record"]["invalidation_level"])
    h0, l0 = D(ref["H0"]), D(ref["L0"])

    # ---- reference bar (journal) + its open (pinned cache, read-only window clamped before the recovery cursor)
    win = json.loads((export / f"win_{T['env']['factual_cursor']}.json").read_text(encoding="utf-8"))
    assert win["replay_id"] == RID and win["range"][1] == T["env"]["factual_cursor"]
    bars = {b["t"]: b for b in win["bars"]}
    rb = bars[ref["reference_start"]]
    assert (D(rb["h"]), D(rb["l"]), D(rb["c"])) == (h0, l0, D(ref["reference_close"])), "cache/journal reference bar"

    # ---- E0 at the preparation (STORED) and its re-derivation from the preparation record only (DERIVED)
    cor0_st, e0_st = rng(gp["corridor_effective"]), rng(gp["economic_current"])
    cap0 = D(gp["T_current"])
    cor0 = corridor_market(d, D(gp["R"]), D(gp["K_trigger"]), v_op, D(gp["T_confirm"]), cap0, tick)
    e0 = geo.admissible_bounds(d, cor0, v_op, cap0, k_cost, rr, tick) if cor0 else None
    assert cor0 == cor0_st and e0 == e0_st, (child, cor0, cor0_st, e0, e0_st)
    # ---- E1 at the first recovery (STORED) and re-derivation from the terminal record only (DERIVED)
    cor1_st, e1_st, cap1 = rng(gt["corridor_effective"]), rng(gt["economic_current"]), D(gt["T_current"])
    cor1 = corridor_market(d, D(gt["R"]), D(gt["K_trigger"]), D(gt["V"]), D(gt["T_confirm"]), cap1, tick)
    e1 = geo.admissible_bounds(d, cor1, D(gt["V"]), cap1, D(gt["K_cost"]), rr, tick) if cor1 else None
    assert cor1 == cor1_st and e1 == e1_st

    # ---- F and the intersections
    thr = h0 + tick if d > 0 else l0 - tick
    e0f, gap_e0 = f_with(d, e0, thr)
    c0f, gap_c0 = f_with(d, cor0, thr)
    e1f, gap_e1 = f_with(d, e1, thr)
    # best ratio over F inside the corridor (the pinned predicate is monotone in price; evaluated at the F edge)
    edge = thr if c0f is not None else None
    chk_edge = geo.predicate(d, edge, v_op, cap0, k_cost, rr) if edge is not None else None

    # ---- the local sequence actually checked (pinned predicate on cache bars inside the domain)
    p0 = ref["published_at"]
    dom = sorted(t for t in bars if t >= p0 and t <= resp["response_bar"].split("#obs@")[1].replace("Z", "+00:00"))
    checked = [{"bar_start": t, "o": bars[t]["o"], "h": bars[t]["h"], "l": bars[t]["l"], "c": bars[t]["c"],
                "verdict": local_verdict(d, h0, l0, tick, D(bars[t]["l"]), D(bars[t]["h"]), D(bars[t]["c"]))}
               for t in dom]
    assert len(checked) == int(resp["bars_checked"]) and checked[-1]["verdict"] == "RECOVERY"
    assert all(c["verdict"] == "NONE" for c in checked[:-1])
    last = checked[-1]
    assert (last["h"], last["l"], last["c"]) == (resp["response_high"], resp["response_low"], resp["response_close"])

    # ---- the recovery evaluation (pinned predicate at the stored evaluation price)
    price = D(gt["price"])
    chk = geo.predicate(d, price, D(gt["V"]), cap1, D(gt["K_cost"]), rr)
    assert s(chk.g) == gt["G"] and s(chk.q) == gt["Q"] and s(chk.margin) == gt["margin"]
    blockers = list(T["blockers"])
    rederived = []
    if not cor1[0] <= price <= cor1[1]:
        rederived.append("CLOSE_OUTSIDE_RETURN_CORRIDOR")
    if not chk.ok:
        rederived.append(chk.reason)
    assert sorted(rederived) == sorted(blockers) and primary_reason(blockers) == resp["primary_reason"]
    chk_prep = geo.predicate(d, D(gp["price"]), v_op, cap0, k_cost, rr)
    assert chk_prep.ok and s(chk_prep.g) == gp["G"]

    # ---- preparation -> recovery, three distinct facts:
    # (a) intermediate records of the child/scenario between the preparation and terminal journal sequences,
    #     endpoints excluded (`between`, `scen_between` above);
    # (b) comparison of the geometric fields of the two snapshots (preparation and terminal records);
    # (c) cap history check and recomputation of E0/E1 from their own records (asserted equal to the stored values).
    keys = ("R", "K_trigger", "V", "T_confirm", "T_current", "corridor_effective", "economic_current", "K_cost")
    changed = {k: [gp[k], gt[k]] for k in keys if gp[k] != gt[k]}
    caps_after_prep = [c for c in T["cap_history"] if c["since"] > p0]
    caps_same = P["cap_history"] == T["cap_history"]

    cls1 = e0f is None
    return {
        "child": child, "scenario_id": sid, "direction": DNAME[d],
        "wait_open": {"published_at": W["env"]["published_at"], "cursor": W["env"]["factual_cursor"],
                      "journal_seq": wo["seq"], "cohort_month": W["env"]["published_at"][:7], "label": "STORED"},
        "reference_bar": {
            "id": ref["reference_bar"], "interval": [ref["reference_start"], ref["reference_end"]],
            "open": rb["o"], "high_H0": ref["H0"], "low_L0": ref["L0"], "close": ref["reference_close"],
            "p0_published_at": p0, "c0_cursor": ref["published_cursor"], "tick": s(tick), "journal_seq": prep["seq"],
            "labels": {"open": "STORED (pinned cache via read-only window)", "others": "STORED (journal)"}},
        "geometry_at_preparation": {
            "R": gp["R"], "K_trigger": gp["K_trigger"], "V_structural": s(v_struct), "V_operational": gp["V"],
            "T_confirm": gp["T_confirm"], "T_cap_current": gp["T_current"], "cap_history_at_preparation": P["cap_history"],
            "corridor_structural": gp["corridor_structural"], "corridor_effective": gp["corridor_effective"],
            "economic_region_E0": gp["economic_current"], "K_cost_bps": gp["K_cost"], "rr_min": s(rr),
            "price_reference_close": gp["price"], "G": gp["G"], "Q": gp["Q"], "margin": gp["margin"],
            "ratio_at_reference_close": f4(ratio(D(gp["G"]), D(gp["Q"]), k_cost)),
            "labels": {"V_structural": "STORED (scenario CONFIRMED record seq %d)" % conf["seq"],
                       "ratio_at_reference_close": "DERIVED (G-K)/(Q+K)", "rr_min": "STORED (register %s)" % REGISTER[:12],
                       "corridor/E0": "STORED; re-derived from the preparation record with the pinned formulas: equal",
                       "others": "STORED (journal, preparation record)"}},
        "first_recovery": {
            "bar": resp["response_bar"], "published_at": T["env"]["published_at"], "cursor": T["env"]["factual_cursor"],
            "known_at": T["env"]["known_at"], "response_current": resp["response_current"],
            "bars_checked": resp["bars_checked"], "local_sequence": checked,
            "evaluated_price": gt["price"], "price_source": "historical close of the current recovery bar",
            "G": gt["G"], "Q": gt["Q"], "margin": gt["margin"],
            "ratio": f4(ratio(chk.g, chk.q, D(gt["K_cost"]))), "blockers": blockers,
            "primary_reason": resp["primary_reason"], "primary_class": resp["primary_class"],
            "dependencies": T["env"]["dependencies"], "limitations": T["env"]["limitations"],
            "labels": {"local_sequence": "bars STORED (pinned cache); verdicts DERIVED with core5.local_verdict",
                       "ratio": "DERIVED (G-K)/(Q+K) from STORED G/Q/K", "blockers": "STORED; re-derived: equal",
                       "per-bar admission cursor of checked bars": "UNAVAILABLE (not returned by the surfaces used)",
                       "intrabar order": "UNAVAILABLE (never inferred)"}},
        "sets": {
            "F": ("[%s, +inf)" if d > 0 else "(-inf, %s]") % s(thr),
            "E0": srng(e0), "E1": srng(e1), "corridor0": srng(cor0),
            "E0_cap_F": srng(e0f), "E0_F_gap_price": s(gap_e0), "E0_F_gap_ticks": s(gap_e0 / tick),
            "corridor0_cap_F": srng(c0f), "corridor0_F_gap_price": s(gap_c0),
            "E1_cap_F": srng(e1f), "E1_F_gap_price": s(gap_e1),
            "reference_extreme_vs_E0": {"favourable_extreme": ref["H0"] if d > 0 else ref["L0"],
                                        "E0_near_edge": s(e0[1] if d > 0 else e0[0]),
                                        "beyond_E0_by": s((h0 - e0[1]) if d > 0 else (e0[0] - l0))},
            "best_ratio_over_F_in_corridor": f4(ratio(chk_edge.g, chk_edge.q, k_cost)) if chk_edge else None,
            "best_ratio_price": s(edge),
            "labels": "DERIVED from STORED H0/L0/tick and the STORED (re-derived) corridor/E0/E1"},
        "checks": {
            "1_E0_cap_F_empty_at_preparation": cls1,
            "2_E0_cap_F_nonempty_but_close_outside_usable_region": "NOT_APPLICABLE (E0 ∩ F empty)" if cls1 else
            (not (e1[0] <= price <= e1[1]) if e1 else True),
            "3_later_documented_restriction_E0_to_E1": bool(changed or caps_after_prep),
            "close_in_F": True, "close_in_E1": bool(e1 and e1[0] <= price <= e1[1]),
            "geometry_unchanged": not changed},
        "between_preparation_and_recovery": {
            "intermediate_records": {
                "preparation_seq": prep["seq"], "terminal_seq": term["seq"],
                "entry_attempt_seqs": [r["seq"] for r in between], "scenario_seqs": scen_between,
                "label": "STORED: journal records of the child/scenario with preparation seq < seq < terminal seq "
                         "(endpoints excluded)"},
            "geometry_snapshot_comparison": {
                "fields": list(keys), "changes": changed,
                "label": "STORED: geometric fields of the preparation record vs the terminal record"},
            "cap_history_and_region_recompute": {
                "cap_history_identical": caps_same, "cap_revisions_after_p0": caps_after_prep,
                "cap_revisions_before_p0_after_wait_open":
                    [c for c in P["cap_history"] if c["since"] > W["env"]["published_at"]],
                "E0_recomputed_equals_stored": True, "E1_recomputed_equals_stored": True,
                "label": "STORED cap history of both records; E0/E1 DERIVED from each record with the pinned "
                         "formulas (asserted equal to the stored regions)"},
            "scope": "E1 = E0 holds for the geometric quantities considered; it does not imply that the market "
                     "or context was generally unchanged"},
    }


def main(export: Path, out: Path) -> None:
    ev = json.loads((export / "evaluation.json").read_text(encoding="utf-8"))
    rep = json.loads((export / "report.json").read_text(encoding="utf-8"))
    assert rep["evaluation_id"] == EVAL_ID and rep["replay_id"] == RID
    m = methods.get("v0.5")
    assert m.register_sha256() == REGISTER and m.rules_sha256() == RULES
    p = m.params()
    ea, sc = pages(export, "ea"), pages(export, "sc")
    env0 = next(r for r in ea)["record"]["env"]["method"]
    assert env0["build"].startswith(BUILD) and env0["register_sha256"] == REGISTER and env0["rules_sha256"] == RULES
    children = [r["subject"] for r in ea if (r["record"].get("reason") or "").startswith("RESPONSE_NOT_ISSUABLE")]
    paths = [path(c, ea, sc, export, p, "0.1") for c in children]

    resp = rep["adviser"]["responses"]
    tot = resp["total"]["counts"] if "total" in resp else None
    ni = resp["total"]["not_issuable"] if "total" in resp else None
    inc, prim = {}, {}
    for x in paths:
        for b in x["first_recovery"]["blockers"]:
            inc[b] = inc.get(b, 0) + 1
        prim[x["first_recovery"]["primary_reason"]] = prim.get(x["first_recovery"]["primary_reason"], 0) + 1
    cohorts, dirs = {}, {}
    for x in paths:
        cohorts[x["wait_open"]["cohort_month"]] = cohorts.get(x["wait_open"]["cohort_month"], 0) + 1
        dirs[x["direction"]] = dirs.get(x["direction"], 0) + 1
    recon = {
        "report_total": {k: tot[k] for k in ("R", "N", "I")} if tot else None,
        "report_not_issuable": ni,
        "paths": len(paths), "blocker_incidence": dict(sorted(inc.items())), "primary": dict(sorted(prim.items())),
        "primary_class": sorted({reason_class(x["first_recovery"]["primary_reason"]) for x in paths}),
        "cohorts": dict(sorted(cohorts.items())), "directions": dict(sorted(dirs.items())),
    }
    ok = (tot is not None and {k: tot[k] for k in ("R", "N", "I")} == {k: EXPECTED[k] for k in ("R", "N", "I")}
          and len(paths) == EXPECTED["N"] and inc == EXPECTED["incidence"] and prim == EXPECTED["primary"]
          and cohorts == EXPECTED["cohorts"] and dirs == EXPECTED["directions"]
          and ni["blocker_incidence_not_summable"] == EXPECTED["incidence"] and ni["primary_reason"] == EXPECTED["primary"])
    recon["matches_director_quote_and_report"] = ok
    assert ok, recon
    inputs = {Path(f).name: sha(Path(f)) for f in sorted(glob.glob(str(export / "*.json")))}
    doc = {"evaluation_id": EVAL_ID, "replay_id": RID, "build": BUILD, "rules_sha256": RULES, "register_sha256": REGISTER,
           "run_status": ev.get("status"), "access": "app read-only GET surfaces only; no DB extraction",
           "definitions": {"E0": "corridor ∩ economic region at the preparation record (stored; re-derived)",
                           "E1": "the same at the first-recovery record", "F": "LONG close >= H0+tick; SHORT close <= L0-tick"},
           "reconciliation": recon, "paths": paths, "input_sha256": inputs}
    out.mkdir(parents=True, exist_ok=True)
    (out / "paths.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8",
                                    newline="\n")
    print(json.dumps(recon, sort_keys=True))
    for x in paths:
        print(x["child"], x["direction"], x["sets"]["E0"], x["sets"]["F"], "E0&F", x["sets"]["E0_cap_F"],
              "gap", x["sets"]["E0_F_gap_price"], "checks", json.dumps(x["checks"]))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
