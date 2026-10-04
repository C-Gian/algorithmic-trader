"""Adviser evaluation report section (operational report; built from COMMITTED records only).

Works at every job state (running snapshot, paused, cancelled, failed, zero-call, completed): it reads the committed
semantic journal, the committed evaluation records and the latest committed adviser inspection view. Sections keep
operational status, runtime integrity, coverage, adviser behaviour and hypothetical economics apart. Hypothetical
outcomes are normalized one-unit paths, never a human account result; win rate is never reported alone.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

MIN = timedelta(minutes=1)


def _dt(s: Any) -> datetime | None:
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def _q(xs: list[Decimal]) -> dict[str, str | None]:
    if not xs:
        return {"n": "0", "min": None, "p25": None, "median": None, "p75": None, "max": None}
    s = sorted(xs)

    def pct(p: float) -> str:
        i = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
        return format(s[i].quantize(Decimal("0.0001")), "f")
    return {"n": str(len(s)), "min": pct(0), "p25": pct(0.25), "median": pct(0.5), "p75": pct(0.75), "max": pct(1)}


def _bps(x: Any) -> Decimal | None:
    return None if x is None else Decimal(str(x)) * 10000


def build(*, engine: dict, journal: list[dict], records: list[dict], view: dict | None, status: str,
          clock_end_reached: bool) -> dict[str, Any]:
    adv = engine["adviser"]
    es, ee = _dt(adv["eval_start"]), _dt(adv["eval_end"])
    weeks = Decimal(int((ee - es).total_seconds())) / Decimal(7 * 86400)
    in_eval = lambda t: es <= t < ee  # noqa: E731
    calls = [e["record"] for e in journal if e["kind"] == "call"]
    revs = defaultdict(list)
    for e in journal:
        if e["kind"] == "call_revision":
            revs[e["record"]["call_id"]].append(e["record"])
    cands = [e["record"] for e in journal if e["kind"] == "candidate"]
    views = [(e["clock_time"], e["record"]) for e in journal if e["kind"] == "market_view"]
    acts = [e["record"] for e in journal if e["kind"] == "actionability"]
    eval_calls = [c for c in calls if in_eval(_dt(c["issued_at"]))]
    warm_calls = [c for c in calls if _dt(c["issued_at"]) < es]
    last_t = _dt(journal[-1]["clock_time"]) if journal else None
    covered_to = min(ee, last_t) if last_t else es

    # -- coverage: view rows over the evaluation window ------------------------------------------------------
    row_minutes: Counter = Counter()
    prev_t, prev_row = None, None
    for t, rec in views:
        t = _dt(t)
        if prev_t is not None:
            a, b = max(prev_t, es), min(t, ee)
            if b > a:
                row_minutes[prev_row] += int((b - a) / MIN)
        prev_t, prev_row = t, rec["table_row"]
    if prev_t is not None and covered_to > max(prev_t, es):
        row_minutes[prev_row] += int((covered_to - max(prev_t, es)) / MIN)
    eval_minutes = int((ee - es) / MIN)
    unavailable = row_minutes.get("REQUIRED_CONTEXT_UNAVAILABLE", 0)
    assessable_minutes = sum(row_minutes.values()) - unavailable
    assessable_weeks = Decimal(assessable_minutes) / Decimal(7 * 24 * 60)

    # -- calls, entry windows ---------------------------------------------------------------------------------
    call_rows = []
    entry_minutes_all: list[Decimal] = []
    reopens_all = 0
    for c in eval_calls:
        rs = revs.get(c["call_id"], [])
        timeline = [(_dt(c["issued_at"]), "AVAILABLE")] + [(_dt(r["env"]["published_at"]), r["entry_status"]) for r in rs]
        end = next((_dt(r["env"]["published_at"]) for r in rs if r["thesis_status"] != "ONGOING"), None)
        avail = Decimal(0)
        reopens = 0
        for (t0, st), nxt in zip(timeline, timeline[1:] + [(end or covered_to, None)]):
            if st == "AVAILABLE":
                avail += Decimal(int((nxt[0] - t0).total_seconds())) / 60
        for (t0, a), (t1, b) in zip(timeline, timeline[1:]):
            if a != "AVAILABLE" and b == "AVAILABLE":
                reopens += 1
        entry_minutes_all.append(avail)
        reopens_all += reopens
        term = next((r for r in rs if r["thesis_status"] != "ONGOING"), None)
        call_rows.append({
            "call_id": c["call_id"], "family": c["family"], "direction": c["direction"], "issued_at": c["issued_at"],
            "issue_reference": c["issue_reference"], "stop": c["invalidation"], "target": c["target"],
            "target_type": c["target_type"], "structural_area": c["structural_area"],
            "hard_deadline": c["hard_deadline"], "entry_available_minutes": str(avail), "entry_reopens": reopens,
            "terminal": term["thesis_status"] if term else "ONGOING", "terminal_reason": term["terminal_reason"] if term
            else None, "terminal_at": term["env"]["published_at"] if term else None,
            "limiting_landmark": (c.get("limiting_landmark") or {}).get("type"),
            "limiting_age_minutes": (c.get("limiting_landmark") or {}).get("age_minutes"),
            "gain_bps": c["actionability"]["gain_bps"], "risk_bps": c["actionability"]["risk_bps"]})
    issue_times = sorted(_dt(c["issued_at"]) for c in eval_calls)
    bounds = [es] + issue_times + [covered_to]
    longest = max(((b - a) for a, b in zip(bounds, bounds[1:])), default=timedelta(0))

    # -- funnel ------------------------------------------------------------------------------------------------
    births = Counter()
    arms = Counter()
    ends = Counter()
    reasons = Counter()
    for c in cands:
        if not in_eval(_dt(c["env"]["published_at"])):
            continue
        key = f"{c['family']}_{c['direction']}"
        if c["transition"] == "BIRTH":
            births[key] += 1
        elif c["transition"] == "ARM":
            arms[key] += 1
        elif c["transition"] in ("EXPIRE", "WITHDRAW", "REJECT", "ISSUE", "CLEARED"):
            ends[(key, c["transition"])] += 1
            if c["transition"] != "ISSUE":
                for r in str(c.get("reason") or "").split(","):
                    if r:
                        reasons[f"{c['transition']}:{r.split(':')[0]}"] += 1
    rejected_acts = [a for a in acts if not a["actionable"] and in_eval(_dt(a["env"]["published_at"]))]
    blockers = Counter(b.split(":")[0] for a in rejected_acts for b in a["blockers"])
    triggers = len([a for a in acts if in_eval(_dt(a["env"]["published_at"]))])
    gstats = defaultdict(lambda: {"G": [], "Q": [], "K": [], "margin": []})
    for a in acts:
        if a.get("gain_bps") is None or not in_eval(_dt(a["env"]["published_at"])):
            continue
        fam = a["subject_id"].split("-")[0][0] if not a["subject_id"].startswith("call-") else a["subject_id"][5]
        gstats[fam]["G"].append(Decimal(a["gain_bps"]))
        gstats[fam]["Q"].append(Decimal(a["risk_bps"]))
        gstats[fam]["K"].append(Decimal(a["cost_envelope_bps"]))
        gstats[fam]["margin"].append(Decimal(a["reward_risk_margin"]))
    limiting = Counter((a.get("limiting_landmark") or {}).get("type") or "NONE" for a in acts
                       if in_eval(_dt(a["env"]["published_at"])))

    # -- outcomes ----------------------------------------------------------------------------------------------
    paths = [r["record"] for r in records if r["kind"] == "path"]
    by_variant: dict[str, dict[str, Any]] = {}
    for v in ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY"):
        ps = [p for p in paths if p["variant"] == v]
        st = Counter(p["status"] for p in ps)
        ex = Counter(p["exit_class"] for p in ps if p["status"] == "CLOSED")
        closed = [p for p in ps if p["status"] == "CLOSED" and p["price_net"] is not None]
        nets = [Decimal(p["price_net"]) for p in closed]
        gross = [Decimal(p["gross"]) for p in closed]
        stress = [Decimal(p["stress_price_net"]) for p in closed if p.get("stress_price_net") is not None]
        held = [Decimal(p["held_minutes"]) for p in closed if p.get("held_minutes") is not None]
        by_variant[v] = {
            "paths": len(ps), "status": dict(sorted(st.items())), "exit_class": dict(sorted(ex.items())),
            "target_exits": ex.get("TARGET", 0) + ex.get("TARGET_GAP", 0),
            "stop_exits": ex.get("STOP", 0) + ex.get("STOP_GAP", 0),
            "guidance_exits": sum(n for k, n in ex.items() if k.startswith("GUIDANCE")),
            "no_entry": st.get("NO_ENTRY", 0), "ambiguous": st.get("AMBIGUOUS", 0),
            "censored": st.get("CENSORED", 0), "unresolved": st.get("UNRESOLVED", 0),
            "sum_gross": str(sum(gross, Decimal(0))), "sum_price_net": str(sum(nets, Decimal(0))),
            "mean_price_net": str(sum(nets, Decimal(0)) / len(nets)) if nets else None,
            "sum_stress_price_net": str(sum(stress, Decimal(0))) if v == "PRIMARY" else None,
            "price_net_bps_distribution": _q([x * 10000 for x in nets]),
            "held_minutes_distribution": _q(held),
            "positive_price_net": sum(1 for x in nets if x > 0), "nonpositive_price_net": sum(1 for x in nets if x <= 0),
            "total_net": "UNAVAILABLE (PRICE_NET_ONLY: funding completeness unproven)"
            if all(p["total_net"] is None for p in ps) else "PARTIAL",
            "ambiguous_bounds": [p["bounds"] for p in ps if p["status"] == "AMBIGUOUS"][:20],
        }
    room = []
    for c in eval_calls:
        p = next((x for x in paths if x["call_id"] == c["call_id"] and x["variant"] == "PRIMARY"), None)
        tc, t = Decimal(c["issue_reference"]), Decimal(c["target"])
        d = 1 if c["direction"] == "LONG" else -1
        r = {"call_id": c["call_id"], "room_at_trigger_bps": str((d * (t - tc) / tc * 10000).quantize(Decimal("0.01")))}
        if p and p.get("entry"):
            e = Decimal(p["entry"]["price"])
            r["room_at_primary_open_bps"] = str((d * (t - e) / e * 10000).quantize(Decimal("0.01")))
            r["erosion_bps"] = str((Decimal(r["room_at_trigger_bps"]) - Decimal(r["room_at_primary_open_bps"])))
        room.append(r)

    # -- view samples -------------------------------------------------------------------------------------------
    samples = [r["record"] for r in records if r["kind"] == "view_sample"]
    vs: dict[str, Any] = {"samples": len(samples), "by_view": dict(sorted(Counter(s["view"] for s in samples).items()))}
    for h in (1, 4):
        key = f"outcome_{h}h"
        directional = [s for s in samples if s["view"] in ("UP", "DOWN") and s[key] is not None]
        hits = sum(1 for s in directional if s[key] == s["view"])
        pers = [s for s in samples if s["persistence"] in ("UP", "DOWN") and s[key] is not None]
        phits = sum(1 for s in pers if s[key] == s["persistence"])
        cond = [s for s in samples if s.get("scenario_id")]
        act = sum(1 for s in cond if s.get(f"antecedent_activated_{h}h"))
        vs[f"{h}h"] = {
            "directional_scored": len(directional), "directional_matching_sign": hits,
            "abstentions_balanced_uncertain": sum(1 for s in samples if s["view"] in ("BALANCED", "UNCERTAIN")),
            "unavailable_view": sum(1 for s in samples if s["view"] == "UNAVAILABLE"),
            "endpoint_unavailable": sum(1 for s in samples if s[key] is None),
            "persistence_scored": len(pers), "persistence_matching_sign": phits,
            "conditional_samples": len(cond), "antecedent_activated": act,
            "note": "conditional labels; not calibrated probabilities; abstentions are not hits"}

    # -- diagnosis ------------------------------------------------------------------------------------------------
    total_births = sum(births.values())
    diag = []
    if not eval_calls:
        if assessable_minutes == 0:
            diag.append("NO_ASSESSABLE_TIME: required 15m/1h trade context never ready in the evaluation window "
                        "(warmup/data gaps)")
        if total_births == 0:
            diag.append("NO_CANDIDATE_BIRTHS: A needs a 1h UP/DOWN context with a 15m impulse; B/C need a "
                        "compression-qualified box")
        if total_births and not sum(arms.values()):
            diag.append("NO_ARMS: episodes/attempts were born but never armed (reaction/retest/context gates)")
        if sum(arms.values()) and not triggers:
            diag.append("NO_TRIGGERS: armed scenarios expired/withdrew before an eligible trigger minute")
        if blockers:
            diag.append("TRIGGERS_REJECTED: " + ", ".join(f"{k} {n}" for k, n in blockers.most_common(6)))
    conclusion = ("INSUFFICIENT_EVIDENCE" if status == "completed" else "INCOMPLETE")
    return {
        "section": "ADVISER_EVALUATION", "identity": {k: adv["identity"][k] for k in (
            "model", "rules_version", "rules_sha256", "register_sha256", "implementation", "capability_profile_sha256",
            "identity_sha256")} | {"capability_profile": adv["profile"], "evaluator_sha256": adv["evaluator"]["sha256"]},
        "windows": {"warmup_start": adv["warmup_start"], "evaluation": [adv["eval_start"], adv["eval_end"]],
                    "tail_end": adv["tail_end"], "clock_end": adv["clock_end"], "clock_end_reached": clock_end_reached},
        "boundary_effect": ((view or {}).get("boundary") or {}),
        "coverage": {"evaluation_minutes": eval_minutes, "covered_minutes": int((covered_to - es) / MIN)
                     if covered_to > es else 0, "assessable_minutes": assessable_minutes,
                     "unavailable_minutes": unavailable, "view_row_minutes": dict(sorted(row_minutes.items())),
                     "assessable_weeks": str(assessable_weeks.quantize(Decimal("0.001"))),
                     "capabilities": {"calendar": adv["profile"]["calendar"], "incidents": adv["profile"]["incident_tape"],
                                      "dislocation": adv["profile"]["dislocation"],
                                      "funding_outcomes": adv["profile"]["funding_outcomes"],
                                      "execution": adv["profile"]["execution"], "quotes": "NOT_COVERED (historical)",
                                      "predictive_cycles": "NOT_COVERED (observed phase only)",
                                      "oi_liquidations_depth_flow": "NOT_COVERED"}},
        "calls": {"count": len(eval_calls), "warmup_calls_not_scored": len(warm_calls),
                  "per_evaluated_week": str((Decimal(len(eval_calls)) / weeks).quantize(Decimal("0.01"))),
                  "per_assessable_week": (str((Decimal(len(eval_calls)) / assessable_weeks).quantize(Decimal("0.01")))
                                          if assessable_weeks > 0 else None),
                  "by_family": dict(sorted(Counter(f"{c['family']}_{c['direction']}" for c in eval_calls).items())),
                  "entry_available_minutes": _q(entry_minutes_all), "entry_reopens": reopens_all,
                  "longest_no_call_interval_hours": str(Decimal(int(longest.total_seconds())) / 3600),
                  "terminal": dict(sorted(Counter(r["terminal"] for r in call_rows).items())),
                  "list": call_rows},
        "funnel": {"births": dict(sorted(births.items())), "arms": dict(sorted(arms.items())),
                   "trigger_evaluations": triggers, "issued": len(eval_calls),
                   "ends": {f"{k[0]}:{k[1]}": n for k, n in sorted(ends.items())},
                   "end_reasons": dict(reasons.most_common()), "rejection_blockers": dict(blockers.most_common()),
                   "slot_occupied": blockers.get("SLOT_OCCUPIED", 0), "priority": blockers.get("PRIORITY", 0),
                   "conflicted": blockers.get("CONFLICTED", 0)},
        "gates": {f: {k: _q(v) for k, v in g.items()} for f, g in sorted(gstats.items())},
        "limiting_landmarks": dict(sorted(limiting.items())), "room_erosion": room,
        "outcomes": {"note": "normalized one-unit hypothetical paths (N0=1, q=1/E); not a fill, account or size; "
                             "PRICE_NET_ONLY - total net with funding unavailable unless coverage is proven",
                     "variants": by_variant},
        "view_samples": vs, "diagnosis": diag,
        "conclusion": {"verdict": conclusion,
                       "text": ("First adviser evaluation on these data: no prior adviser baseline exists on the same "
                                "pack, so improvement cannot be judged. Calls, entry windows, funnel and hypothetical "
                                "outcomes are reported for Director diagnosis." if status == "completed" else
                                "Run not complete: sections cover the committed prefix only.")},
    }


def render_markdown(a: dict[str, Any]) -> list[str]:
    c, f, o, cov = a["calls"], a["funnel"], a["outcomes"]["variants"], a["coverage"]
    w = a["windows"]
    lines = ["", "## Adviser evaluation (hypothetical; no orders, sizing or account)",
             f"- Method `{a['identity']['model']}` / `{a['identity']['rules_version']}` · rules "
             f"`{a['identity']['rules_sha256'][:12]}` · register `{a['identity']['register_sha256'][:12]}` · profile "
             f"`{a['identity']['capability_profile_sha256'][:12]}` · identity `{a['identity']['identity_sha256'][:12]}`",
             f"- Evaluation {w['evaluation'][0]} → {w['evaluation'][1]} · clock end {w['clock_end']}"
             + ("" if w["clock_end_reached"] else " (not reached: committed prefix only)"),
             f"- Coverage: {cov['assessable_minutes']} of {cov['evaluation_minutes']} evaluation minutes assessable "
             f"({cov['unavailable_minutes']} unavailable) · calendar {cov['capabilities']['calendar']} · funding "
             f"{cov['capabilities']['funding_outcomes']} · quotes NOT_COVERED (historical, MODELED execution)",
             f"- **Calls: {c['count']}** · {c['per_evaluated_week']}/evaluated week · "
             f"{c['per_assessable_week'] or '—'}/assessable week · by family {c['by_family'] or '{}'} · warmup "
             f"calls not scored {c['warmup_calls_not_scored']}",
             f"- Entry available (minutes per call): median {c['entry_available_minutes']['median'] or '—'} · max "
             f"{c['entry_available_minutes']['max'] or '—'} · reopens {c['entry_reopens']} · longest no-call interval "
             f"{c['longest_no_call_interval_hours']} h",
             f"- Thesis outcomes (guidance): {c['terminal'] or '{}'}",
             f"- Funnel: births {f['births'] or '{}'} · arms {f['arms'] or '{}'} · trigger evaluations "
             f"{f['trigger_evaluations']} · issued {f['issued']} · slot-occupied {f['slot_occupied']} · priority "
             f"{f['priority']} · conflicted {f['conflicted']}"]
    if f["rejection_blockers"]:
        lines.append("- Trigger rejections: " + ", ".join(f"{k} {n}" for k, n in f["rejection_blockers"].items()))
    if f["end_reasons"]:
        lines.append("- Attempt endings: " + ", ".join(f"{k} {n}" for k, n in list(f["end_reasons"].items())[:12]))
    for fam, g in a["gates"].items():
        lines.append(f"- Gates {fam}: G median {g['G']['median']} bps · Q median {g['Q']['median']} · K "
                     f"{g['K']['median']} · margin G-1.2Q-2.2K median {g['margin']['median']} (n {g['G']['n']})")
    p = o["PRIMARY"]
    lines += [f"- Hypothetical PRIMARY (60 s entry delay): {p['paths']} paths · entries "
              f"{p['paths'] - p['no_entry']} · NO_ENTRY {p['no_entry']} · target {p['target_exits']} · stop "
              f"{p['stop_exits']} · guidance exits {p['guidance_exits']} · ambiguous {p['ambiguous']} · censored "
              f"{p['censored']} · unresolved {p['unresolved']}",
              f"  - price-net sum {p['sum_price_net']} (normalized units) · median "
              f"{p['price_net_bps_distribution']['median'] or '—'} bps · stress (5 bps/leg allowance) sum "
              f"{p['sum_stress_price_net']} · total net {p['total_net']}"]
    for v in ("ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY"):
        x = o[v]
        lines.append(f"- Sensitivity {v}: {x['paths']} paths · NO_ENTRY {x['no_entry']} · price-net sum "
                     f"{x['sum_price_net']}" + (" (no stop/target; exits at issue + hard horizon)" if v == "HORIZON_ONLY"
                                                else ""))
    vs = a["view_samples"]
    for h in ("1h", "4h"):
        s = vs.get(h)
        if s:
            lines.append(f"- View samples +{h}: {s['directional_scored']} directional scored, "
                         f"{s['directional_matching_sign']} matching sign · abstentions "
                         f"{s['abstentions_balanced_uncertain']} · unavailable {s['unavailable_view']} · persistence "
                         f"{s['persistence_matching_sign']}/{s['persistence_scored']} · antecedent activated "
                         f"{s['antecedent_activated']}/{s['conditional_samples']} (not calibrated)")
    if a["diagnosis"]:
        lines.append("- **Zero-call diagnosis:** " + " · ".join(a["diagnosis"]))
    for r in c["list"][:20]:
        lines.append(f"  - {r['issued_at']} {r['family']} {r['direction']} ref {r['issue_reference']} stop {r['stop']} "
                     f"target {r['target']} ({r['target_type']}) → {r['terminal']}"
                     + (f" ({r['terminal_reason']})" if r["terminal_reason"] else "")
                     + f" · entry available {r['entry_available_minutes']} min")
    if len(c["list"]) > 20:
        lines.append(f"  - … {len(c['list']) - 20} more calls in the JSON report")
    lines.append(f"- Adviser conclusion: **{a['conclusion']['verdict']}** — {a['conclusion']['text']}")
    return lines
