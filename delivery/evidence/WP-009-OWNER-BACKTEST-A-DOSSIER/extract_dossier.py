"""One-time read-only causal dossier for Owner Backtest A (eval-20261005T120047-e6cc50 / obs-20261005T120047-bc6947).

Not product code and not a reusable analytics framework. Inputs (produced by read-only access, never committed):
  <export>/snapshot.jsonl  - one REPEATABLE READ READ ONLY psql transaction: meta, evaluation, replay (config/engine/
                             manifest/assurance), checkpoint, professional finish, evaluation-record kinds and the
                             complete committed adviser journal of the run (seq order)
  <export>/<cache_id>/     - byte copy of the run's pinned canonical feed cache (manifest + gzip partitions)

Nothing replays the professional runtime/reducer. Facts are joins of committed journal records (ORIGINAL); exact
algebra on them is DERIVED; the pinned 1m trade bars are read only to aggregate the bounded 15m bars needed for S15 at
a trigger cutoff, the impulse/box break flags and the 45 spent-before-reaction terminal bars (DERIVED_PINNED_BAR).
No bar after a case's own cutoff is used for that case; no outcome/evaluation path record is read.

usage: uv run python extract_dossier.py <export_dir> <out_dir>
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.adviser import geometry as geo
from algotrader.adviser import params as params_mod
from algotrader.adviser.core import INITIAL_JOURNAL
from algotrader.adviser.measures import Bar, div, round_down, round_up, scale
from algotrader.adviser.report import _q
from algotrader.feed.ordering import canonical

EVAL_ID = "eval-20261005T120047-e6cc50"
RUN_ID = "obs-20261005T120047-bc6947"
REPO = Path(__file__).resolve().parents[3]
ORIGINAL_REPORT = REPO / "delivery" / "evidence" / "WP-009-OWNER-BACKTEST-A.json"
M15 = timedelta(minutes=15)
MIN = timedelta(minutes=1)
D0 = Decimal(0)


def dt(s):
    if s is None:
        return None
    return s if isinstance(s, datetime) else datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def iso(t):
    return None if t is None else t.isoformat().replace("+00:00", "Z")


def dec(x):
    return None if x is None else Decimal(str(x))


def s(x):
    return None if x is None else (format(x, "f") if isinstance(x, Decimal) else str(x))


def q4(x):
    return None if x is None else format(Decimal(x).quantize(Decimal("0.0001")), "f")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ----------------------------------------------------------------------------------------------------------------------
# inputs and provenance
# ----------------------------------------------------------------------------------------------------------------------

def load_snapshot(export: Path):
    rows = [json.loads(line) for line in (export / "snapshot.jsonl").open(encoding="utf-8") if line.startswith("{")]
    one = {k: r[k] for r in rows for k in r if k != "j"}
    journal = sorted((r["j"] for r in rows if "j" in r), key=lambda e: e["seq"])
    return one, journal


def verify_journal(journal, finish):
    h, bad_digest, bad_chain, gaps = INITIAL_JOURNAL, [], [], []
    for i, e in enumerate(journal, start=1):
        if e["seq"] != i:
            gaps.append(e["seq"])
        d = hashlib.sha256(canonical(e["record"])).hexdigest()
        if d != e["digest"]:
            bad_digest.append(e["seq"])
        h = hashlib.sha256(bytes.fromhex(h) + bytes.fromhex(d)).hexdigest()
        if h != e["chain"]:
            bad_chain.append(e["seq"])
    com = finish["commitment"]
    return {"rows": len(journal), "sequence_gaps": gaps[:10], "digest_mismatches": bad_digest[:10],
            "chain_mismatches": bad_chain[:10], "recomputed_chain_head": h,
            "finish_commitment_journal_seq": com["journal_seq"], "finish_commitment_journal_chain": com["journal_chain"],
            "matches_finish_commitment": (not gaps and not bad_digest and not bad_chain and h == com["journal_chain"]
                                          and len(journal) == com["journal_seq"])}


def load_cache(export: Path, cache_id: str, pinned_sha: str):
    root = export / cache_id
    msha = sha256_file(root / "manifest.json")
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bad, bars = [], {}
    for p in man["partitions"]:
        blob = (root / p["file"]).read_bytes()
        if hashlib.sha256(blob).hexdigest() != p["sha256"]:
            bad.append(p["file"])
            continue
        for line in gzip.decompress(blob).splitlines():
            ev = json.loads(line)
            ch = ev["channel"]
            if ch["family"] != "trade_bar_1m" or ev["kind"] != "bar_observation":
                continue
            pl = ev["payload"]
            bars[dt(ev["event_time"])] = (dec(pl["open"]), dec(pl["high"]), dec(pl["low"]), dec(pl["close"]),
                                          dec(pl.get("volume")) if pl.get("volume") is not None else None)
    prov = {"cache_id": cache_id, "manifest_sha256": msha, "pinned_manifest_sha256": pinned_sha,
            "manifest_matches_pin": msha == pinned_sha, "partitions": len(man["partitions"]),
            "partition_sha256_failures": bad, "trade_1m_bars_loaded": len(bars)}
    return bars, prov


class Bars15:
    """15m trade bars aggregated from the pinned complete 1m trade bars (UTC slots); DERIVED_PINNED_BAR."""

    def __init__(self, m1):
        slots = defaultdict(list)
        for t, b in m1.items():
            st = t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)
            slots[st].append((t, b))
        self.bars = {}
        for st, xs in slots.items():
            if len(xs) != 15:
                continue
            xs.sort()
            o = xs[0][1][0]
            c = xs[-1][1][3]
            self.bars[st] = Bar(st, st + M15, o, max(x[1][1] for x in xs), min(x[1][2] for x in xs), c, None,
                                st + M15, f"okx/BTC-USDT-SWAP/trade_bar_1m/15m/{iso(st).replace('Z', '+00:00')}")
        self.starts = sorted(self.bars)

    def ending_by(self, t, n):
        """The last n complete 15m bars whose end <= t (end == t is known at t under the modeled policy)."""
        i = bisect_right(self.starts, t - M15)
        return [self.bars[x] for x in self.starts[max(0, i - n):i]]

    def ending_in(self, a, b):
        """Bars with a < end <= b."""
        return [self.bars[x] for x in self.starts if a < x + M15 <= b]


# ----------------------------------------------------------------------------------------------------------------------
# journal indices and cutoff reconstruction
# ----------------------------------------------------------------------------------------------------------------------

class Index:
    def __init__(self, journal):
        self.j = journal
        self.cand = defaultdict(list)
        self.lm = defaultdict(list)          # lid -> [(seq, record)]
        self.boxes = {}                      # bid -> {"born": (seq, values, t), "retired": (seq, values, t)}
        self.acts = []
        self.views = []
        for e in journal:
            r, k = e["record"], e["kind"]
            if k == "candidate":
                self.cand[r["attempt_id"]].append((e["seq"], r))
            elif k == "landmark":
                self.lm[r["landmark_id"]].append((e["seq"], r))
            elif k == "observation" and r.get("name") == "compression_box":
                v = r["values"]
                self.boxes.setdefault(v["box_id"], {})["born" if r["category"] == "BOX_BORN" else "retired"] = (
                    e["seq"], v, dt(e["clock_time"]))
            elif k == "actionability":
                self.acts.append(e)
            elif k == "market_view":
                self.views.append(e)

    def attempt_alive(self, aid, seq):
        recs = self.cand[aid]
        born = recs[0][0] < seq
        ended = any(r["transition"] in ("EXPIRE", "WITHDRAW", "REJECT", "ISSUE", "CLEARED") and sq < seq
                    for sq, r in recs)
        return born and not ended

    def landmarks_at(self, seq):
        """Latest journaled version of every landmark published before ``seq`` (created/broken/retired)."""
        out = {}
        for lid, vs in self.lm.items():
            cur = None
            for sq, r in vs:
                if sq < seq:
                    cur = (sq, r)
            if cur is not None:
                out[lid] = cur
        return out

    def box_at(self, seq):
        for bid, b in self.boxes.items():
            if "born" in b and b["born"][0] < seq and not ("retired" in b and b["retired"][0] < seq):
                return bid, b
        return None, None


def zone_set(ix, b15, d, seq, t):
    """Opposing zones (transformed near/far) eligible at journal cutoff ``seq`` / clock ``t`` for direction d, built
    only from records published before the cutoff: ACTIVE opposing landmarks, A impulse-B owner zones of pending
    same-direction A attempts, and the live box edge. Impulse/box break flags are not journaled and are DERIVED from
    pinned 15m closes known by t."""
    zones = []
    for lid, (sq, r) in sorted(ix.landmarks_at(seq).items()):
        if r["status"] != "ACTIVE":
            continue
        if (r["side"] == "HIGH") != (d > 0):
            continue
        p, z = dec(r["price"]), dec(r["zone_halfwidth"])
        pt = p * d
        zones.append({"id": lid, "type": r["landmark_type"], "price": s(p), "zone_halfwidth": s(z),
                      "near_t": pt - z, "far_t": pt + z, "created_at": r["env"]["published_at"],
                      "source": "landmark record seq %d" % sq, "kind": "LANDMARK", "basis": "ORIGINAL",
                      "extremum_time": r.get("extremum_time"), "horizon": r.get("horizon"),
                      "source_ids": r.get("source_ids")})
    for aid, recs in ix.cand.items():
        r0 = recs[0][1]
        if r0["family"] != "A" or (1 if r0["direction"] == "LONG" else -1) != d or not ix.attempt_alive(aid, seq):
            continue
        b, z = dec(r0["setup"]["impulse_B"]), dec(r0["setup"]["zone_halfwidth"])
        born = dt(r0["env"]["published_at"])
        broken = [x for x in b15.ending_in(born, t) if x.c * d > b * d + z]
        # the attempt processes closes only while alive; any close before t during its life breaks the zone
        if broken:
            continue
        zones.append({"id": f"{aid}#B", "type": "IMPULSE_B", "price": s(b), "zone_halfwidth": s(z),
                      "near_t": b * d - z, "far_t": b * d + z, "created_at": r0["env"]["published_at"],
                      "source": "candidate BIRTH seq %d setup.impulse_B" % recs[0][0], "kind": "OWNER_A",
                      "basis": "ORIGINAL_PRICE_DERIVED_NOT_BROKEN"})
    bid, bx = ix.box_at(seq)
    if bid is not None:
        v = bx["born"][1]
        lo, up, z = dec(v["low"]), dec(v["up"]), dec(v["zone_halfwidth"])
        created = bx["born"][2]
        edge = up if d > 0 else lo
        broken = [x for x in b15.ending_in(created, t) if (x.c > up + z if d > 0 else x.c < lo - z)]
        if not broken:
            zones.append({"id": f"{bid}#{'U' if d > 0 else 'L'}", "type": "BOX_UPPER" if d > 0 else "BOX_LOWER",
                          "price": s(edge), "zone_halfwidth": s(z), "near_t": edge * d - z, "far_t": edge * d + z,
                          "created_at": iso(created), "source": "BOX_BORN observation seq %d" % bx["born"][0],
                          "kind": "OWNER_BOX", "basis": "ORIGINAL_PRICE_DERIVED_NOT_BROKEN"})
    return zones, (bid, bx)


def resolve_target(fam, d, tc, zones, box):
    """Mirror of MP-001 v0.2 target selection on the reconstructed zone set (algebra, not a runtime replay)."""
    tc_t = tc * d
    inside = [z for z in zones if z["near_t"] <= tc_t <= z["far_t"]]
    if inside:
        return {"blocked": True, "containing": inside}
    ahead = sorted((z for z in zones if z["near_t"] > tc_t), key=lambda z: (z["near_t"], z["created_at"], z["id"]))
    best = ahead[0] if ahead else None
    if fam == "A":
        if best is None:
            return {"blocked": False, "t_t": None, "type": "NONE", "limiting": None}
        return {"blocked": False, "t_t": best["near_t"], "type": "LANDMARK", "limiting": best}
    v = box[1]["born"][1]
    lo, up, mid = dec(v["low"]), dec(v["up"]), dec(v["mid"])
    l_t, u_t, m_t = (lo, up, mid) if d > 0 else (-up, -lo, -mid)
    if fam == "B":
        proj = u_t + (u_t - l_t)
        if best is not None and best["near_t"] <= proj:
            return {"blocked": False, "t_t": best["near_t"], "type": "LANDMARK", "limiting": best}
        return {"blocked": False, "t_t": proj, "type": "PROJECTED_BOX_WIDTH", "limiting": None}
    if best is not None and best["near_t"] < m_t:
        return {"blocked": False, "t_t": best["near_t"], "type": "LANDMARK", "limiting": best}
    return {"blocked": False, "t_t": m_t, "type": "MIDPOINT", "limiting": None}


def real(x_t, d, tick):
    """Price of a transformed level, rounded like the runtime (LONG floor, SHORT ceil of the market price)."""
    return round_down(x_t, tick) * d if d > 0 else -round_down(x_t, tick)


def bound(d, v, t, k, r, tick):
    """Extreme admissible price (unrounded formula, inward tick rounded, endpoint verified with the predicate)."""
    raw = div(t + r * v, (1 + r) * (1 + div(k, Decimal(10000)))) if d > 0 else div(t + r * v, (1 + r) * (1 - div(k, Decimal(10000))))
    p = round_down(raw, tick) if d > 0 else round_up(raw, tick)
    steps = 0
    while steps < 100000 and not geo.predicate(d, p, v, t, k, r).ok:
        p = p - tick if d > 0 else p + tick
        steps += 1
        if (d > 0 and p <= v) or (d < 0 and p >= v):
            return raw, None
    return raw, p


def feasibility(d, cmin, p_actual, v, t, k, r, tick):
    raw, pb = bound(d, v, t, k, r, tick)
    if pb is None:
        cls = "INCOMPATIBLE_NO_ADMISSIBLE_PRICE"
        region = None
    elif (d > 0 and pb < cmin) or (d < 0 and pb > cmin):
        cls = "INCOMPATIBLE_AT_MINIMUM_CONFIRMATION"
        region = None
    elif (d > 0 and p_actual > pb) or (d < 0 and p_actual < pb):
        cls = "OVERSHOOT"
        region = [s(cmin), s(pb)] if d > 0 else [s(pb), s(cmin)]
    else:
        cls = "ACTUAL_PRICE_ADMISSIBLE"
        region = [s(cmin), s(pb)] if d > 0 else [s(pb), s(cmin)]
    span = 10000 * d * (t - v) / v
    return {"bound_formula_unrounded": s(raw), "bound_inward_verified": s(pb), "min_confirmation_price": s(cmin),
            "region_min_confirmation_to_bound": region, "class": cls,
            "min_confirmation_beyond_bound_bps": None if pb is None else q4(10000 * d * (cmin - pb) / cmin),
            "actual_beyond_min_confirmation_bps": q4(10000 * d * (p_actual - cmin) / cmin),
            "T_minus_V_span_bps_at_V": q4(span),
            "note": "positive min_confirmation_beyond_bound = the confirmation threshold itself lies beyond every "
                    "admissible price; no admissible price at all when the T-V span is below about (1+r)K"}


# ----------------------------------------------------------------------------------------------------------------------
# main extraction
# ----------------------------------------------------------------------------------------------------------------------

def main(export: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    one, journal = load_snapshot(export)
    meta, rp, fin, ev = one["meta"], one["replay"], one["finish"], one["evaluation"]
    eng = rp["engine"]
    adv = eng["adviser"]
    tick = dec(adv["tick"])
    P = params_mod.load()
    r_min, k_hist, n_trig = P.rr_min, P.hist_k_bps, P.trigger_ticks
    es, ee = dt(adv["eval_start"]), dt(adv["eval_end"])
    in_eval = lambda t: es <= t < ee  # noqa: E731 - same predicate as adviser.report.build
    orig_bytes = ORIGINAL_REPORT.read_bytes()
    orig = json.loads(orig_bytes)
    jver = verify_journal(journal, fin)
    m1, cprov = load_cache(export, eng["cache_id"], eng["cache_manifest_sha256"])
    b15 = Bars15(m1)
    ix = Index(journal)
    by_seq = {e["seq"]: e for e in journal}

    # 15m aggregation check against journaled 15m pivot prices
    piv_ok = piv_bad = 0
    for lid, vs in ix.lm.items():
        r = vs[0][1]
        if not r["landmark_type"].endswith("_15M"):
            continue
        st = dt(r["source_ids"][0].rsplit("/", 1)[1])
        b = b15.bars.get(st)
        want = dec(r["price"])
        got = None if b is None else (b.h if r["side"] == "HIGH" else b.lo)
        piv_ok += got == want
        piv_bad += got != want

    provenance = {
        "evaluation_id": EVAL_ID, "replay_id": RUN_ID, "evaluation_row": {k: ev.get(k) for k in (
            "evaluation_id", "replay_id", "run_type", "preset", "chunk_id", "dataset_id", "pack_id")},
        "db_snapshot": meta, "replay_status": rp["status"], "total_events": rp["total_events"],
        "engine_format": rp["engine_format"], "code_build": adv["build"], "identity": adv["identity"],
        "checkpoint": one.get("checkpoint"), "finish_commitment": fin["commitment"], "journal_verification": jver,
        "evaluation_record_kinds_not_read": one.get("eval_kinds"),
        "feed_cache": cprov, "pivot_15m_price_check": {"matched": piv_ok, "mismatched": piv_bad},
        "original_report": {"path": str(ORIGINAL_REPORT.relative_to(REPO)).replace("\\", "/"),
                            "sha256": hashlib.sha256(orig_bytes).hexdigest()},
        "parameters_used": {"tick": s(tick), "trigger_offset_ticks": n_trig, "net_reward_risk_min": s(r_min),
                            "historical_adequacy_nominal_roundtrip_bps": s(k_hist), "area_each_side_scale": s(P.area_scale),
                            "median_tr_bars": P.median_tr, "reaction_min_scale": s(P.a_reaction_min),
                            "reaction_max_15m_bars": P.a_reaction_max_bars, "register_file_sha256":
                                sha256_file(params_mod.REGISTER_FILE)},
        "windows": {"evaluation": [iso(es), iso(ee)], "warmup_start": adv["warmup_start"], "tail_end": adv["tail_end"]},
    }

    # ---------------------------------------------------------------------------------------------------- triggers
    acts = [e for e in ix.acts if in_eval(dt(e["record"]["env"]["published_at"]))]
    disp_first = {}
    for e in ix.acts:
        disp_first.setdefault(e["clock_time"], e["seq"])
    trig_rows = []
    for e in acts:
        a = e["record"]
        aid = a["subject_id"]
        recs = ix.cand[aid]
        birth = recs[0][1]
        fam, d = birth["family"], (1 if birth["direction"] == "LONG" else -1)
        cut = disp_first[e["clock_time"]]
        t = dt(e["clock_time"])
        versions = [(sq, r) for sq, r in recs if r["transition"] in ("ARM", "REVISE") and sq < cut]
        arm_sq, arm = versions[-1]
        first_arm_sq, first_arm = versions[0]
        term = next((r for sq, r in recs if r["transition"] in ("REJECT", "ISSUE")), None)
        p = dec(a["side_price"])
        kc = dec(a["cost_envelope_bps"])
        g, qq = dec(a["gain_bps"]), dec(a["risk_bps"])
        k_trig, v_level = dec(arm["trigger_level"]), dec(arm["invalidation_level"])
        v_real = real(v_level * d, d, tick)
        cmin = k_trig + d * n_trig * tick
        row = {
            "attempt_id": aid, "family": fam, "direction": birth["direction"], "owner_id": birth["owner_id"],
            "actionability_seq": e["seq"], "actionability_record_id": e["record_id"], "dispatch_cutoff_seq": cut,
            "factual_cursor": e["factual_cursor"], "trigger_published_at": a["env"]["published_at"],
            "birth_published_at": birth["env"]["published_at"], "birth_seq": recs[0][0],
            "first_arm_published_at": first_arm["env"]["published_at"], "first_arm_seq": first_arm_sq,
            "latest_arm_or_revise": arm["transition"], "latest_arm_or_revise_seq": arm_sq,
            "latest_arm_published_at": arm["env"]["published_at"], "revisions_before_trigger": len(versions) - 1,
            "deadline": birth["expires_at"],
            "minutes_birth_to_arm": int((dt(first_arm["env"]["published_at"]) - dt(birth["env"]["published_at"])) / MIN),
            "minutes_latest_arm_to_trigger": int((t - dt(arm["env"]["published_at"])) / MIN),
            "frozen_s15": birth["setup"]["s15"], "frozen_zone_halfwidth": birth["setup"]["zone_halfwidth"],
            "impulse_A": birth["setup"].get("impulse_A"), "impulse_B": birth["setup"].get("impulse_B"),
            "reaction_at_latest_arm": arm["setup"].get("reaction"), "anchor_at_latest_arm": arm["setup"].get("anchor"),
            "box_low": birth["setup"].get("box_low"), "box_up": birth["setup"].get("box_up"),
            "box_mid": birth["setup"].get("box_mid"),
            "K_trigger_level": s(k_trig), "first_arm_K_trigger_level": first_arm["trigger_level"],
            "first_arm_invalidation_level": first_arm["invalidation_level"],
            "confirmation_rule": f"complete 1m close {'>=' if d > 0 else '<='} K {'+' if d > 0 else '-'} {n_trig} tick",
            "min_confirmation_price_DERIVED": s(cmin),
            "invalidation_level_unrounded": s(v_level), "V_from_candidate_DERIVED": s(v_real),
            "evaluated_side_price": s(p), "side_price_source": a["side_price_source"], "K_cost_bps": s(kc),
            "G_bps": a["gain_bps"], "Q_bps": a["risk_bps"], "margin_bps": a["reward_risk_margin"],
            "structural_area": a["structural_area"], "admissible_bounds": a["admissible_bounds"],
            "blockers": a["blockers"], "terminal_reason": term["reason"] if term else None,
            "limiting_landmark_recorded": a["limiting_landmark"],
            "basis": {"ORIGINAL": "candidate/actionability/landmark journal fields", "DERIVED": "fields suffixed "
                      "_DERIVED and the feasibility/zone reconstructions"},
        }
        zt, box = zone_set(ix, b15, d, cut, t)
        za, _ = zone_set(ix, b15, d, arm_sq, dt(arm["env"]["published_at"]))
        row["zones_at_trigger"] = [{k: (s(v) if isinstance(v, Decimal) else v) for k, v in z.items()} for z in zt]
        row["zones_at_latest_arm"] = [{k: (s(v) if isinstance(v, Decimal) else v) for k, v in z.items()} for z in za]
        ids_t, ids_a = {z["id"] for z in zt}, {z["id"] for z in za}
        row["zone_changes_arm_to_trigger"] = {"added": sorted(ids_t - ids_a), "removed_or_broken": sorted(ids_a - ids_t)}
        # S15 at the trigger cutoff (not journaled per close): DERIVED from the pinned 15m bars known by t
        s15 = scale(b15.ending_by(t, P.median_tr + 1), P.median_tr)
        row["S15_at_trigger_DERIVED_PINNED_BAR"] = s(s15)
        res = resolve_target(fam, d, p, zt, box)
        if g is None:  # inside-zone refusal: no geometry, retain the refusal and every containing zone
            row["T_DERIVED"] = row["V_DERIVED"] = None
            row["containing_zones_at_trigger"] = [z["id"] for z in res.get("containing", [])]
            row["containing_zone_types"] = [z["type"] for z in res.get("containing", [])]
            row["reconstruction_consistent"] = bool(res["blocked"]) and "AT_OPPOSING_AREA" in a["blockers"]
            row["original_blocking_zone_identity"] = ("UNIQUE_RECOVERED" if len(res.get("containing", [])) == 1 else
                                                      "AMBIGUOUS_MULTIPLE_CONTAINING_ORIGINAL_CHOICE_LOST"
                                                      if res.get("containing") else "NOT_RECOVERED")
            row["classification"] = "INSIDE_OPPOSING_ZONE_REFUSAL"
            row["feasibility_at_trigger"] = None
            row["T_at_min_confirmation_same_zone_set_DERIVED"] = None
            row["feasibility_at_latest_arm"] = None
            trig_rows.append(row)
            continue
        T = ((p + d * g * p / 10000) / tick).quantize(Decimal(1)) * tick
        V = ((p - d * qq * p / 10000) / tick).quantize(Decimal(1)) * tick
        chk = geo.predicate(d, p, V, T, kc, r_min)
        row["T_DERIVED"], row["V_DERIVED"] = s(T), s(V)
        row["G_Q_margin_regenerated_exactly"] = (str(chk.g) == a["gain_bps"] and str(chk.q) == a["risk_bps"]
                                                 and str(chk.margin) == a["reward_risk_margin"]
                                                 and chk.reason in a["blockers"])
        row["V_matches_candidate_invalidation_rounding"] = V == v_real
        rec_t = None if res.get("blocked") or res.get("t_t") is None else real(res["t_t"], d, tick)
        row["T_reconstructed_from_zone_set_DERIVED"] = s(rec_t)
        row["target_type_reconstructed"] = res.get("type")
        lim = res.get("limiting")
        row["limiting_reconstructed_id"] = lim["id"] if lim else None
        rec_lim = a["limiting_landmark"]
        row["reconstruction_consistent"] = (rec_t == T and ((lim is None and rec_lim is None) or
                                            (lim is not None and rec_lim is not None and lim["id"] == rec_lim["landmark_id"])))
        if s15 is not None:
            area = geo.structural_area(d, p, V, T, s15, P.area_scale, tick)
            row["structural_area_regenerated_matches"] = area is not None and [s(area[0]), s(area[1])] == a["structural_area"]
        a_bounds = geo.admissible_bounds(d, (dec(a["structural_area"][0]), dec(a["structural_area"][1])), V, T, kc,
                                         r_min, tick) if a["structural_area"] else None
        row["admissible_bounds_regenerated"] = None if a_bounds is None else [s(a_bounds[0]), s(a_bounds[1])]
        # gross target room versus the zero-risk floor G >= r*Q + (1+r)*K
        row["zero_risk_floor_bps"] = s((1 + r_min) * kc)
        row["G_below_zero_risk_floor"] = g < (1 + r_min) * kc
        row["feasibility_at_trigger"] = feasibility(d, cmin, p, V, T, kc, r_min, tick)
        # same zone set, hypothetical minimum-confirmation close: does the target (or a block) differ?
        rc = resolve_target(fam, d, cmin, zt, box)
        row["T_at_min_confirmation_same_zone_set_DERIVED"] = (
            "BLOCKED_INSIDE:" + ",".join(z["id"] for z in rc["containing"]) if rc["blocked"] else
            s(real(rc["t_t"], d, tick)) if rc.get("t_t") is not None else "NO_TARGET")
        # latest arm/revise cutoff: target then known for the minimum confirmation, stop then in force
        ra = resolve_target(fam, d, cmin, za, box if fam != "A" else (None, None)) if (fam == "A" or box[0]) else None
        if ra is None:
            row["feasibility_at_latest_arm"] = {"class": "INSUFFICIENT_DATA", "detail": "owner box not reconstructed"}
        elif ra["blocked"]:
            row["feasibility_at_latest_arm"] = {"class": "MIN_CONFIRMATION_INSIDE_OPPOSING_ZONE_AT_ARM",
                                                "containing": [z["id"] for z in ra["containing"]]}
        elif ra.get("t_t") is None:
            row["feasibility_at_latest_arm"] = {"class": "NO_TARGET_AT_ARM"}
        else:
            ta = real(ra["t_t"], d, tick)
            fa = feasibility(d, cmin, cmin, v_real, ta, k_hist, r_min, tick)
            fa["T_known_at_arm_DERIVED"] = s(ta)
            fa["target_type_at_arm"] = ra["type"]
            fa["limiting_at_arm"] = ra["limiting"]["id"] if ra.get("limiting") else None
            fa["target_changed_by_trigger"] = ta != T
            if fa["class"] == "ACTUAL_PRICE_ADMISSIBLE":
                fa["class"] = "MIN_CONFIRMATION_ADMISSIBLE_AT_ARM"
            fa.pop("region_min_confirmation_to_bound", None) if fa["class"] != "MIN_CONFIRMATION_ADMISSIBLE_AT_ARM" else None
            row["feasibility_at_latest_arm"] = fa
        f = row["feasibility_at_trigger"]["class"]
        if not row["reconstruction_consistent"] or not row["G_Q_margin_regenerated_exactly"]:
            row["classification"] = "OBJECT_OR_RULE_DIVERGENCE_OR_INSUFFICIENT_DATA"
        elif f == "ACTUAL_PRICE_ADMISSIBLE":
            row["classification"] = "OBJECT_OR_RULE_DIVERGENCE_OR_INSUFFICIENT_DATA"
        else:
            row["classification"] = f
        if fam == "A":
            for name, key in (("impulse_B", "impulse_B"), ("reaction", "reaction_at_latest_arm")):
                x = dec(row[key])
                row[f"room_from_{name}_to_trigger_T_bps_DERIVED"] = q4(10000 * d * (T - x) / x) if x else None
            if row["impulse_B"]:
                row["T_before_impulse_B_in_trade_direction"] = (T - dec(row["impulse_B"])) * d < 0
                row["T_is_own_impulse_B_near_edge"] = bool(lim) and lim["id"] == f"{aid}#B"
        trig_rows.append(row)

    # --------------------------------------------------------------------------------------------- candidate ledger
    ledger = []
    births_eval = [aid for aid, recs in ix.cand.items() if recs[0][1]["transition"] == "BIRTH"
                   and in_eval(dt(recs[0][1]["env"]["published_at"]))]
    for aid in births_eval:
        recs = ix.cand[aid]
        b = recs[0][1]
        bt = dt(b["env"]["published_at"])
        arms = [(sq, r) for sq, r in recs if r["transition"] == "ARM"]
        revs = [(sq, r) for sq, r in recs if r["transition"] == "REVISE"]
        end = next(((sq, r) for sq, r in recs if r["transition"] in ("EXPIRE", "WITHDRAW", "REJECT", "ISSUE", "CLEARED")),
                   None)
        et = dt(end[1]["env"]["published_at"]) if end else None
        at = dt(arms[0][1]["env"]["published_at"]) if arms else None
        ledger.append({
            "attempt_id": aid, "family": b["family"], "direction": b["direction"], "owner_id": b["owner_id"],
            "birth_at": iso(bt), "birth_seq": recs[0][0], "renewal": b["setup"].get("renewal"),
            "latch_long_at_birth": b["setup"].get("latch_long"), "latch_short_at_birth": b["setup"].get("latch_short"),
            "deadline": b["expires_at"], "armed": bool(arms), "arm_at": iso(at), "revisions": len(revs),
            "terminal": end[1]["transition"] if end else "OPEN_AT_SNAPSHOT", "terminal_status": end[1]["status"] if end else None,
            "terminal_reason": end[1]["reason"] if end else None, "terminal_at": iso(et),
            "terminal_in_evaluation_window": bool(et and in_eval(et)),
            "minutes_birth_to_arm": int((at - bt) / MIN) if at else None,
            "minutes_birth_to_terminal": int((et - bt) / MIN) if et else None,
            "minutes_arm_to_terminal": int((et - at) / MIN) if (et and at) else None,
            "impulse_A": b["setup"].get("impulse_A"), "impulse_B": b["setup"].get("impulse_B"),
            "frozen_s15": b["setup"]["s15"], "zone_halfwidth": b["setup"]["zone_halfwidth"],
            "transitions": [{"seq": sq, "transition": r["transition"], "at": r["env"]["published_at"],
                             "status": r["status"], "reason": r["reason"], "trigger_level": r["trigger_level"],
                             "invalidation_level": r["invalidation_level"], "reaction": r["setup"].get("reaction"),
                             "bars_seen": r["setup"].get("bars_seen")} for sq, r in recs],
        })

    # ---------------------------------------------------------------------------------- 45 spent-before-reaction cases
    spent = []
    for L in ledger:
        if not (L["family"] == "A" and (L["terminal_reason"] or "").startswith("SPENT_HIGH_BEYOND_B")
                and L["terminal_in_evaluation_window"]):
            continue
        d = 1 if L["direction"] == "LONG" else -1
        bt, et = dt(L["birth_at"]), dt(L["terminal_at"])
        A, B, z = dec(L["impulse_A"]), dec(L["impulse_B"]), dec(L["zone_halfwidth"])
        s15a = dec(L["frozen_s15"])
        src_close = None
        closes = []
        seen = b15.ending_in(bt, et)  # bars processed by the attempt: end in (birth, terminal]
        birth_bar = b15.ending_by(bt, 1)
        prev = birth_bar[-1].c * d if birth_bar else None
        lower = False
        r_min_t = None
        for x in seen[:-1]:
            ct = x.c * d
            if prev is not None and ct < prev:
                lower = True
            prev = ct
            lt = (x.lo if d > 0 else -x.h)
            r_min_t = lt if r_min_t is None or lt <= r_min_t else r_min_t
        term = seen[-1] if seen else None
        row = {"attempt_id": L["attempt_id"], "direction": L["direction"], "birth_at": L["birth_at"],
               "terminal_at": L["terminal_at"], "minutes_birth_to_terminal": L["minutes_birth_to_terminal"],
               "bars_processed_DERIVED": len(seen), "bars_seen_recorded_before_terminal": L["transitions"][-1]["bars_seen"],
               "impulse_A": s(A), "impulse_B": s(B), "zone_halfwidth": s(z)}
        if term is None or term.end != et:
            row["terminal_bar"] = "MISSING_OR_NOT_ENDING_AT_TERMINAL_DISPATCH"
        else:
            o_t, h_t, l_t, c_t = (term.o, term.h, term.lo, term.c) if d > 0 else (-term.o, -term.lo, -term.h, -term.c)
            lower_incl = lower or (prev is not None and c_t < prev)
            r_incl = l_t if r_min_t is None or l_t <= r_min_t else r_min_t
            reaction_same_bar = (lower_incl and r_incl < B * d - P.a_reaction_min * s15a and r_incl > A * d + z)
            row.update({
                "terminal_bar_DERIVED_PINNED_BAR": {"start": iso(term.start), "open": s(term.o), "high": s(term.h),
                                                     "low": s(term.lo), "close": s(term.c)},
                "spend_condition_verified": h_t > B * d + z,
                "reaction_conditions_also_true_in_terminal_bar_DERIVED": reaction_same_bar,
                "lower_close_before_terminal_bar_DERIVED": lower,
                "intrabar_order": "UNKNOWN (OHLC only); the runtime checks the spend first by declared precedence",
            })
        nxt = sorted((x for x in ledger if x["family"] == "A" and x["direction"] == L["direction"]
                      and dt(x["birth_at"]) > et), key=lambda x: x["birth_at"])
        row["latch_at_terminal_recorded"] = {"latch_long": None, "latch_short": None}
        last = ix.cand[L["attempt_id"]][-1][1]["setup"]
        row["latch_at_terminal_recorded"] = {"latch_long": last.get("latch_long"), "latch_short": last.get("latch_short")}
        row["next_same_direction_A_birth"] = (
            {"attempt_id": nxt[0]["attempt_id"], "birth_at": nxt[0]["birth_at"], "renewal": nxt[0]["renewal"],
             "minutes_after_spend": int((dt(nxt[0]["birth_at"]) - et) / MIN)} if nxt else None)
        row["qualification_or_latch_between"] = "NOT_JOURNALED (Q_A is not published per close; only latches at candidate records)"
        spent.append(row)

    # ----------------------------------------------------------------------------------------------- box owners
    boxes = []
    for bid, b in sorted(ix.boxes.items(), key=lambda kv: kv[1].get("born", (0,))[0]):
        if "born" not in b:
            continue
        ct = b["born"][2]
        rt = b["retired"][2] if "retired" in b else None
        if not (in_eval(ct) or (rt and in_eval(rt))):
            continue
        att = [L for L in ledger if L["owner_id"] == bid]
        boxes.append({"box_id": bid, "born_at": iso(ct), "retired_at": iso(rt),
                      "retire_reason": b["retired"][1].get("reason") if "retired" in b else None,
                      "minutes_alive": int((rt - ct) / MIN) if rt else None, "low": b["born"][1]["low"],
                      "up": b["born"][1]["up"], "mid": b["born"][1]["mid"],
                      "attempts_born_in_eval": len(att),
                      "attempts_by_key": dict(Counter(f"{x['family']}{'+' if x['direction'] == 'LONG' else '-'}" for x in att)),
                      "attempt_budget_note": "one B+/B-/C+/C- birth per box (used flags not journaled; births shown)",
                      "attempts": [{"attempt_id": x["attempt_id"], "armed": x["armed"], "terminal": x["terminal"],
                                    "terminal_reason": x["terminal_reason"]} for x in att]})

    # --------------------------------------------------------------------- view rows x context x phase, WATCH presence
    lives = []
    for aid, recs in ix.cand.items():
        b0 = dt(recs[0][1]["env"]["published_at"])
        arm = next((dt(r["env"]["published_at"]) for sq, r in recs if r["transition"] == "ARM"), None)
        end = next((dt(r["env"]["published_at"]) for sq, r in recs
                    if r["transition"] in ("EXPIRE", "WITHDRAW", "REJECT", "ISSUE", "CLEARED")), None)
        wend = min(x for x in (arm, end) if x is not None) if (arm or end) else None
        lives.append((b0, wend or ee))
    view_minutes = Counter()
    watch_minutes = Counter()
    vs = [(dt(e["clock_time"]), e["record"]) for e in ix.views]
    last_t = dt(journal[-1]["clock_time"])
    for (t0, r), nxt in zip(vs, vs[1:] + [(min(ee, last_t), None)]):
        a0, b0 = max(t0, es), min(nxt[0], ee)
        if b0 <= a0:
            continue
        key = (r["table_row"], r["observed_context"], r["phase"])
        mins = int((b0 - a0) / MIN)
        view_minutes[key] += mins
        cur = a0
        while cur < b0:  # minute-resolution WATCH presence (DERIVED from candidate intervals)
            w = any(x <= cur < y for x, y in lives)
            watch_minutes[key + ("WATCH_PRESENT" if w else "NO_WATCH",)] += 1
            cur += MIN
    view_table = [{"table_row": k[0], "observed_context": k[1], "phase": k[2], "minutes": v,
                   "minutes_with_watch": watch_minutes.get(k + ("WATCH_PRESENT",), 0),
                   "minutes_without_watch": watch_minutes.get(k + ("NO_WATCH",), 0)}
                  for k, v in sorted(view_minutes.items(), key=lambda kv: -kv[1])]

    # ------------------------------------------------------------------------------------------ reconciliation
    of = orig["adviser"]["funnel"]
    births = Counter(f"{L['family']}_{L['direction']}" for L in ledger)
    arms_c = Counter()
    ends = Counter()
    reasons = Counter()
    for aid, recs in ix.cand.items():
        for sq, c in recs:
            if not in_eval(dt(c["env"]["published_at"])):
                continue
            key = f"{c['family']}_{c['direction']}"
            if c["transition"] == "ARM":
                arms_c[key] += 1
            elif c["transition"] in ("EXPIRE", "WITHDRAW", "REJECT", "ISSUE", "CLEARED"):
                ends[f"{key}:{c['transition']}"] += 1
                if c["transition"] != "ISSUE":
                    for rr in str(c.get("reason") or "").split(","):
                        if rr:
                            reasons[f"{c['transition']}:{rr.split(':')[0]}"] += 1
    blockers = Counter(b.split(":")[0] for r in trig_rows for b in r["blockers"])
    limiting = Counter(((r["limiting_landmark_recorded"] or {}).get("type") or "NONE") for r in trig_rows)
    gq = defaultdict(lambda: defaultdict(list))
    for r in trig_rows:
        if r["G_bps"] is not None:
            for k_, col in (("G", "G_bps"), ("Q", "Q_bps"), ("K", "K_cost_bps"), ("margin", "margin_bps")):
                gq[r["family"]][k_].append(dec(r[col]))
    gates = {f: {k_: _q(v) for k_, v in x.items()} for f, x in sorted(gq.items())}
    staged = {x["attempt_id"]: x for x in orig["adviser"]["room_erosion_staged"]["list"]}
    staged_ok = sum(1 for r in trig_rows if r["family"] == "A" and r["G_bps"] is not None and staged.get(
        r["attempt_id"], {}).get("room_reaction_bps") == (None if r.get("room_from_reaction_to_trigger_T_bps_DERIVED") is None
                                                           else format(Decimal(r["room_from_reaction_to_trigger_T_bps_DERIVED"]).quantize(Decimal("0.01")), "f")))
    recon = {
        "births": [dict(sorted(births.items())), of["births"]], "arms": [dict(sorted(arms_c.items())), of["arms"]],
        "ends": [dict(sorted(ends.items())), of["ends"]], "end_reasons": [dict(sorted(reasons.items())), of["end_reasons"]],
        "trigger_evaluations": [len(trig_rows), of["trigger_evaluations"]],
        "rejection_blockers": [dict(sorted(blockers.items())), of["rejection_blockers"]],
        "limiting_landmarks": [dict(sorted(limiting.items())), orig["adviser"]["limiting_landmarks"]],
        "gates": [gates, orig["adviser"]["gates"]],
        "staged_A_reaction_room_rows_matching_original": [staged_ok, sum(1 for x in staged.values() if x["family"] == "A")],
    }
    recon_ok = {k: v[0] == v[1] for k, v in recon.items()}

    # ------------------------------------------------------------------------------------------ timelines (<= 5)
    geomA = [r for r in trig_rows if r["family"] == "A" and r["G_bps"] is not None]
    pick = {}
    if geomA:
        pick["A_least_negative_margin"] = max(geomA, key=lambda r: dec(r["margin_bps"]))["attempt_id"]
        er = [(Decimal(x["room_reaction_bps"]) - Decimal(x["room_trigger_bps"]), x["attempt_id"])
              for x in orig["adviser"]["room_erosion_staged"]["list"]
              if x["family"] == "A" and x["room_reaction_bps"] not in (None, "NOT_APPLICABLE")]
        pick["A_largest_reported_erosion"] = max(er)[1]
    inside = sorted((r for r in trig_rows if r["G_bps"] is None), key=lambda r: r["actionability_seq"])
    if inside:
        pick["first_AT_OPPOSING_AREA"] = inside[0]["attempt_id"]
    bs = [r for r in trig_rows if r["family"] == "B"]
    if bs:
        pick["only_B"] = bs[0]["attempt_id"]
    cs = [r for r in trig_rows if r["family"] == "C" and r["G_bps"] is not None]
    if cs:
        pick["C_largest_G"] = max(cs, key=lambda r: dec(r["G_bps"]))["attempt_id"]
    timelines = {}
    for why, aid in pick.items():
        recs = ix.cand[aid]
        lo_seq = recs[0][0]
        hi_seq = next(sq for sq, r in recs if r["transition"] in ("REJECT", "ISSUE", "EXPIRE", "WITHDRAW"))
        tr = next(r for r in trig_rows if r["attempt_id"] == aid)
        lims = {z["id"] for z in tr["zones_at_trigger"]} | {z["id"] for z in tr["zones_at_latest_arm"]}
        items = []
        for sq in range(lo_seq, hi_seq + 1):
            e = by_seq[sq]
            r = e["record"]
            rel = (e["kind"] == "candidate" and r["attempt_id"] == aid) or (e["kind"] == "actionability" and r["subject_id"] == aid)
            rel = rel or (e["kind"] == "landmark" and r["landmark_id"] in lims)
            rel = rel or (e["kind"] == "market_view") or (e["kind"] == "observation" and r.get("name") in ("context", "phase", "compression_box"))
            if not rel:
                continue
            brief = {"seq": sq, "at": e["clock_time"], "kind": e["kind"]}
            if e["kind"] == "candidate":
                brief.update(transition=r["transition"], reason=r["reason"], K=r["trigger_level"], V=r["invalidation_level"],
                             reaction=r["setup"].get("reaction"))
            elif e["kind"] == "actionability":
                brief.update(blockers=r["blockers"], price=r["side_price"], G=q4(r["gain_bps"]), Q=q4(r["risk_bps"]),
                             margin=q4(r["reward_risk_margin"]), area=r["structural_area"])
            elif e["kind"] == "landmark":
                brief.update(id=r["landmark_id"], type=r["landmark_type"], price=r["price"], status=r["status"],
                             reason=r["status_reason"])
            elif e["kind"] == "market_view":
                brief.update(row=r["table_row"], expected=r["expected_direction"], context=r["observed_context"],
                             phase=r["phase"])
            else:
                brief.update(name=r["name"], category=r["category"])
            items.append(brief)
        timelines[why] = {"attempt_id": aid, "selection_criterion": why, "outcome_free": "stops at the attempt's terminal "
                          "record; no later bar or evaluation record", "events": items}

    # ------------------------------------------------------------------------------------------ algebra self-tests
    def astra(d, Tm, Vm, thr, close):
        cm = Decimal(thr)
        return feasibility(d, cm, Decimal(close), Decimal(Vm), Decimal(Tm), Decimal(14), Decimal("1.2"), Decimal("0.1"))
    tests = {
        "LONG_incompatible": astra(1, "100700", "99700", "100050", "100050"),
        "LONG_overshoot": astra(1, "100700", "99700", "100000", "100100"),
        "SHORT_incompatible_mirror": astra(-1, "99300", "100300", "99950", "99950"),
        "SHORT_overshoot_mirror": astra(-1, "99300", "100300", "100000", "99900"),
    }
    tests_ok = (tests["LONG_incompatible"]["class"] == "INCOMPATIBLE_AT_MINIMUM_CONFIRMATION"
                and tests["LONG_overshoot"]["class"] == "OVERSHOOT"
                and tests["SHORT_incompatible_mirror"]["class"] == "INCOMPATIBLE_AT_MINIMUM_CONFIRMATION"
                and tests["SHORT_overshoot_mirror"]["class"] == "OVERSHOOT"
                and Decimal(tests["LONG_overshoot"]["bound_formula_unrounded"]).quantize(Decimal("0.001")) == Decimal("100014.525"))

    # ------------------------------------------------------------------------------------------ write
    summary_counts = {
        "trigger_rows": len(trig_rows), "classification": dict(Counter(r["classification"] for r in trig_rows)),
        "classification_by_family": {f: dict(Counter(r["classification"] for r in trig_rows if r["family"] == f))
                                     for f in "ABC"},
        "arm_cutoff_classification": dict(Counter((r["feasibility_at_latest_arm"] or {}).get("class") for r in trig_rows
                                                  if r["G_bps"] is not None)),
        "G_below_zero_risk_floor": sum(1 for r in trig_rows if r.get("G_below_zero_risk_floor")),
        "reconstruction_consistent": sum(1 for r in trig_rows if r["reconstruction_consistent"]),
        "regenerated_exact": sum(1 for r in trig_rows if r.get("G_Q_margin_regenerated_exactly")),
        "structural_area_regenerated": sum(1 for r in trig_rows if r.get("structural_area_regenerated_matches")),
        "candidates": len(ledger), "spent_cases": len(spent),
        "spent_with_reaction_conditions_also_true": sum(1 for x in spent if x.get(
            "reaction_conditions_also_true_in_terminal_bar_DERIVED")),
        "spent_condition_verified": sum(1 for x in spent if x.get("spend_condition_verified")),
        "boxes": len(boxes), "reconciliation": recon_ok, "algebra_self_tests_ok": tests_ok,
    }
    doc = {"dossier": "WP-009 Owner Backtest A causal dossier (read-only, one-time)", "provenance": provenance,
           "summary_counts": summary_counts, "reconciliation": recon, "triggers": trig_rows, "candidates": ledger,
           "spent_before_reaction": spent, "boxes": boxes, "view_rows_by_context_phase": view_table,
           "timelines": timelines, "algebra_self_tests": tests,
           "missing_fields": [
               "S15 at each trigger dispatch: not journaled per 15m close; DERIVED from pinned 15m bars (verified by "
               "regenerating the recorded structural area)",
               "T and V at trigger: not journaled in actionability; DERIVED exactly from side price and G/Q and checked "
               "against the predicate, candidate invalidation rounding and the reconstructed zone set",
               "Blocking-zone identity for AT_OPPOSING_AREA rows: lost by the runtime (geom=None); all containing zones "
               "at the cutoff are listed; the original choice is unrecoverable when several contain the price",
               "Impulse-B and box break flags: not journaled; DERIVED from pinned 15m closes",
               "Q_A qualification per close and latch transitions between candidate records: not journaled",
               "Box used/broken flags and B retest counts: not journaled (births per box shown)",
               "Trigger minute close vs side price: identical by construction only when the trigger minute is the "
               "dispatch's last minute; verified indirectly through the regenerated structural area"]}

    def enc(o):
        if isinstance(o, Decimal):
            return format(o, "f")
        raise TypeError(type(o))

    (out / "dossier.json").write_text(json.dumps(doc, indent=1, default=enc, ensure_ascii=False) + "\n",
                                      encoding="utf-8", newline="\n")
    cols = ["attempt_id", "family", "direction", "owner_id", "birth_published_at", "first_arm_published_at",
            "latest_arm_or_revise", "latest_arm_published_at", "revisions_before_trigger", "trigger_published_at",
            "actionability_seq", "factual_cursor", "deadline", "minutes_birth_to_arm", "minutes_latest_arm_to_trigger",
            "frozen_s15", "S15_at_trigger_DERIVED_PINNED_BAR", "frozen_zone_halfwidth", "impulse_A", "impulse_B",
            "reaction_at_latest_arm", "box_low", "box_up", "box_mid", "K_trigger_level", "min_confirmation_price_DERIVED",
            "evaluated_side_price", "V_DERIVED", "T_DERIVED", "K_cost_bps", "G_bps", "Q_bps", "margin_bps",
            "zero_risk_floor_bps", "G_below_zero_risk_floor", "structural_area", "admissible_bounds", "blockers",
            "limiting_type", "limiting_id", "target_type_reconstructed", "containing_zones_at_trigger",
            "original_blocking_zone_identity", "T_at_min_confirmation_same_zone_set_DERIVED", "trigger_bound",
            "trigger_class", "min_confirmation_beyond_bound_bps", "actual_beyond_min_confirmation_bps",
            "T_minus_V_span_bps_at_V", "arm_T_DERIVED", "arm_bound", "arm_class", "zones_added_arm_to_trigger",
            "zones_removed_arm_to_trigger", "room_from_impulse_B_to_trigger_T_bps_DERIVED",
            "room_from_reaction_to_trigger_T_bps_DERIVED", "T_is_own_impulse_B_near_edge", "reconstruction_consistent",
            "G_Q_margin_regenerated_exactly", "structural_area_regenerated_matches", "classification"]
    with (out / "triggers.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in trig_rows:
            lim = r["limiting_landmark_recorded"] or {}
            ft, fa = r["feasibility_at_trigger"] or {}, r["feasibility_at_latest_arm"] or {}
            flat = dict(r, limiting_type=lim.get("type"), limiting_id=lim.get("landmark_id"),
                        trigger_bound=ft.get("bound_inward_verified"), trigger_class=ft.get("class"),
                        min_confirmation_beyond_bound_bps=ft.get("min_confirmation_beyond_bound_bps"),
                        actual_beyond_min_confirmation_bps=ft.get("actual_beyond_min_confirmation_bps"),
                        T_minus_V_span_bps_at_V=ft.get("T_minus_V_span_bps_at_V"),
                        arm_T_DERIVED=fa.get("T_known_at_arm_DERIVED"), arm_bound=fa.get("bound_inward_verified"),
                        arm_class=fa.get("class"), zones_added_arm_to_trigger=r["zone_changes_arm_to_trigger"]["added"],
                        zones_removed_arm_to_trigger=r["zone_changes_arm_to_trigger"]["removed_or_broken"])
            w.writerow([";".join(map(str, flat.get(c))) if isinstance(flat.get(c), list) else
                        ("" if flat.get(c) is None else flat.get(c)) for c in cols])
    ccols = ["attempt_id", "family", "direction", "owner_id", "birth_at", "renewal", "latch_long_at_birth",
             "latch_short_at_birth", "deadline", "armed", "arm_at", "revisions", "terminal", "terminal_status",
             "terminal_reason", "terminal_at", "terminal_in_evaluation_window", "minutes_birth_to_arm",
             "minutes_birth_to_terminal", "minutes_arm_to_terminal", "impulse_A", "impulse_B", "frozen_s15",
             "zone_halfwidth"]
    with (out / "candidates.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ccols)
        for L in ledger:
            w.writerow(["" if L.get(c) is None else L.get(c) for c in ccols])
    print(json.dumps(summary_counts, indent=1, default=enc))
    print("original report sha256 unchanged:", hashlib.sha256(ORIGINAL_REPORT.read_bytes()).hexdigest()
          == provenance["original_report"]["sha256"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
