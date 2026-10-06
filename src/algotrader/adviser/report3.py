"""v0.3 adviser evaluation report section (``adviser.report.v3``), built from COMMITTED records only.

It reuses the v0.2 builder for the method-independent parts (coverage view rows, calls and entry windows, outcomes by
variant, view samples, condition durations) and replaces the funnel/diagnosis with the MP-002 registered structure:

* structural scenarios: births / arms / confirmations / terminal states per family-direction (cost-independent);
* A confirmations and the preregistered diagnostic denominators: D (geometrically evaluable confirmations, including
  IMMEDIATE), N (empty geometric corridor or empty fixed-K economics at confirmation), N/D, and the separate
  exclusions (no target, inside zone, missing geometry) - never assumed empty;
* routing (IMMEDIATE / WAIT_PRICE / terminal reasons), waiting outcomes (usable returns, selection rejections,
  expiry, cap terminals, temporary blockers), issued calls by family and mode;
* the evidence threshold: distinct A RETURN owners with a PRIMARY (60 s) path ENTERED - once per owner, never B/C,
  IMMEDIATE, other delays, reopenings or hourly samples. 0 / 1-19 / >=20 are reported as registered conventions,
  not a significance, quota or profitability test.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from . import report as r2

REPORT_VERSION = "adviser.report.v3"
EVIDENCE_MIN_OWNERS = 20


def build(*, engine: dict, journal: list[dict], records: list[dict], view: dict | None, status: str,
          clock_end_reached: bool) -> dict[str, Any]:
    base = r2.build(engine=engine, journal=journal, records=records, view=view, status=status,
                    clock_end_reached=clock_end_reached)
    adv = engine["adviser"]
    es, ee = r2._dt(adv["eval_start"]), r2._dt(adv["eval_end"])

    def in_eval(rec: dict) -> bool:
        t = r2._dt(rec["env"]["published_at"])
        return es <= t < ee

    scen = [e["record"] for e in journal if e["kind"] == "scenario"]
    ents = [e["record"] for e in journal if e["kind"] == "entry_attempt"]
    calls = {e["record"]["call_id"]: e["record"] for e in journal if e["kind"] == "call"}
    paths = [x["record"] for x in records if x["kind"] == "path"]

    # -- structural scenarios -------------------------------------------------------------------------------
    trans = Counter()
    terminal = Counter()
    for s in scen:
        if not in_eval(s):
            continue
        key = f"{s['family']}_{s['direction']}"
        trans[f"{key}:{s['transition']}"] += 1
        if s["transition"] == "TERMINAL":
            terminal[f"{s['family']}:{s['terminal_state']}:{str(s['reason']).split(':')[0]}"] += 1
    warmup_context = sorted({s["scenario_id"] for s in scen if s.get("warmup_origin")})
    # A narrative destination contacted while still ARMED (MP-002 §3 literal after-arm precedence, e.g. K >= frozen B):
    # the scenario ends, no confirmation and no call; reported so the domain loss is visible, never relaxed
    a_dest_first = [s for s in scen if in_eval(s) and s["family"] == "A" and s["transition"] == "TERMINAL"
                    and s["terminal_state"] == "DESTINATION_REACHED" and s.get("confirmed_at") is None]

    # -- A confirmations: registered denominators (first routing record per child) ----------------------------
    routed: dict[str, dict] = {}
    for e in ents:
        if e["family"] != "A" or not in_eval(e) or e["entry_attempt_id"] in routed:
            continue
        if e.get("diagnostic") and e["diagnostic"].get("in_D") is not None:
            routed[e["entry_attempt_id"]] = e
    d_rows = [e for e in routed.values() if e["diagnostic"].get("in_D") == "true"]
    n_rows = [e for e in d_rows if e["diagnostic"].get("in_N") == "true"]
    excluded = Counter(e["diagnostic"].get("exclusion") for e in routed.values()
                       if e["diagnostic"].get("in_D") != "true")
    route = Counter()
    for e in routed.values():
        if e["transition"] == "WAIT_OPEN":
            route["RETURN_WAIT"] += 1
        elif e["transition"] == "ISSUE":
            route["IMMEDIATE_ISSUED"] += 1
        elif e["transition"] == "REJECT":
            route["IMMEDIATE_SELECTION_REJECTED"] += 1
        else:
            route[f"TERMINAL:{str(e['reason']).split(':')[0]}"] += 1
    nd = (Decimal(len(n_rows)) / Decimal(len(d_rows))) if d_rows else None

    # -- waiting outcomes ------------------------------------------------------------------------------------------
    wait_ids = {e["entry_attempt_id"] for e in ents if e["transition"] == "WAIT_OPEN" and in_eval(e)}
    usable = {e["entry_attempt_id"] for e in ents if e["transition"] == "RETURN_USABLE" and e["entry_attempt_id"] in wait_ids}
    wait_end = Counter()
    blockers_seen = Counter()
    caps = Counter()
    for e in ents:
        if e["entry_attempt_id"] not in wait_ids:
            continue
        if e["transition"] == "BLOCKERS":
            for b in e["blockers"]:
                blockers_seen[b.split(":")[0]] += 1
            if len(e["blockers"]) > 1:
                blockers_seen["OVERLAPPING_BLOCKER_SETS"] += 1
        elif e["transition"] == "CAP_REVISION":
            caps["CAP_REVISIONS"] += 1
        elif e["transition"] in ("TERMINAL", "REJECT", "ISSUE"):
            wait_end[f"{e['transition']}:{str(e['reason']).split(':')[0].split(',')[0]}"] += 1

    # -- issued calls by mode and the RETURN evidence threshold ---------------------------------------------------
    eval_calls = [c for c in calls.values() if es <= r2._dt(c["issued_at"]) < ee]
    by_mode = Counter(f"{c['family']}_{c.get('entry_mode', 'IMMEDIATE')}" for c in eval_calls)
    primary = {p["call_id"]: p for p in paths if p["variant"] == "PRIMARY"}
    return_owners_entered = sorted({c["scenario_id"] for c in eval_calls if c["family"] == "A"
                                    and c.get("entry_mode") == "RETURN"
                                    and (primary.get(c["call_id"]) or {}).get("entry")})
    return_calls = [c for c in eval_calls if c["family"] == "A" and c.get("entry_mode") == "RETURN"]
    n_owners = len(return_owners_entered)
    if n_owners >= EVIDENCE_MIN_OWNERS:
        threshold = "MINIMUM_REPORTING_COUNT_REACHED"
    elif n_owners >= 1:
        threshold = "INSUFFICIENT_EVIDENCE"
    else:
        threshold = ("NO_ENTERED_RETURN_OWNER" if route.get("RETURN_WAIT") else
                     "NO_RETURN_ROUTING_UPSTREAM_OR_DOMAIN")
    retired_by_scenario = sum(
        1 for e in journal if e["kind"] == "call_revision" and e["record"]["call_id"] in calls
        and str(e["record"].get("terminal_reason") or "").startswith("SCENARIO_TERMINAL"))
    by_family_mode: dict[str, dict] = {}
    for c in eval_calls:
        k = f"{c['family']}_{c.get('entry_mode', 'IMMEDIATE')}"
        p = primary.get(c["call_id"]) or {}
        row = by_family_mode.setdefault(k, {"calls": 0, "entered": 0, "target": 0, "stop": 0, "other_closed": 0,
                                            "no_entry": 0, "unresolved_or_censored_or_ambiguous": 0,
                                            "sum_price_net": Decimal(0)})
        row["calls"] += 1
        if p.get("entry"):
            row["entered"] += 1
        st, ex = p.get("status"), p.get("exit_class") or ""
        if st == "CLOSED":
            if ex.startswith("TARGET"):
                row["target"] += 1
            elif ex.startswith("STOP"):
                row["stop"] += 1
            else:
                row["other_closed"] += 1
            if p.get("price_net") is not None:
                row["sum_price_net"] += Decimal(p["price_net"])
        elif st == "NO_ENTRY":
            row["no_entry"] += 1
        elif st:
            row["unresolved_or_censored_or_ambiguous"] += 1
    for v in by_family_mode.values():
        v["sum_price_net"] = str(v["sum_price_net"])

    # the v0.2-shaped keys are kept (same meaning, mapped to structural scenarios) so every reader of the earlier
    # report shape keeps working; the registered v0.3 keys follow
    births = {k.split(":")[0]: n for k, n in sorted(trans.items()) if k.endswith(":BIRTH")}
    arms = {k.split(":")[0]: n for k, n in sorted(trans.items()) if k.endswith(":ARM")}
    rejections = Counter()
    for e in ents:
        if in_eval(e) and e["transition"] in ("TERMINAL", "REJECT") and e["state"] == "TERMINAL":
            for b in e["blockers"] or [str(e["reason"])]:
                rejections[str(b).split(":")[0]] += 1
            if e["transition"] == "REJECT":
                for r in str(e["reason"]).split(","):
                    rejections[r.split(":")[0]] += 1
    durations = base.get("condition_durations") or {}
    funnel = {
        "births": births, "arms": arms,
        "trigger_evaluations": sum(n for k, n in trans.items() if k.endswith(":CONFIRM")),
        "issued": len(eval_calls), "ends": {}, "end_reasons": dict(terminal.most_common()),
        "rejection_blockers": dict(rejections.most_common()), "slot_occupied": rejections.get("SLOT_OCCUPIED", 0),
        "priority": rejections.get("PRIORITY", 0), "conflicted": rejections.get("CONFLICTED", 0),
        "slot_priority_minutes": {k: (durations.get("conditions") or {}).get(k, {}).get("minutes", "0.00")
                                  for k in r2.SLOT_KEYS} if durations.get("available") else None,
        "scenario_transitions": dict(sorted(trans.items())), "scenario_terminals": dict(terminal.most_common()),
        "warmup_context_scenarios": len(warmup_context),
        "a_confirmations": len(routed),
        "a_denominators": {
            "D_geometrically_evaluable": len(d_rows), "N_initially_empty_corridor_or_fixed_k_economics": len(n_rows),
            "N_over_D": str(nd.quantize(Decimal("0.0001"))) if nd is not None else None,
            "N_over_D_above_half": (nd > Decimal("0.5")) if nd is not None else None,
            "excluded": dict(sorted((k or "UNKNOWN", n) for k, n in excluded.items())),
            "note": ("D = distinct structurally confirmed A owners with valid R/K/V/T/scale/price at confirmation "
                     "(IMMEDIATE included); N = D rows with an empty R-K corridor or empty fixed-K (historical 14 bps) "
                     "economics at that cutoff. Exclusions are separate, never assumed empty. N/D>0.5 is a "
                     "preregistered selected-domain diagnostic for Director review, not proof about timeframes.")},
        "a_destination_before_confirmation": {
            "count": len(a_dest_first),
            "by_direction": dict(sorted(Counter(s["direction"] for s in a_dest_first).items())),
            "examples": [{"scenario_id": s["scenario_id"], "direction": s["direction"],
                          "at": s["env"]["clock_time"], "armed_at": s.get("activated_at"),
                          "trigger_level": s.get("trigger_level"), "destination": s.get("destination"),
                          "reason": s["reason"]} for s in a_dest_first[:3]],
            "note": ("A scenarios whose narrative destination was contacted after arm and before any confirmation "
                     "(MP-002 §3 literal after-arm destination precedence; reachable when K >= the frozen impulse B): "
                     "ended DESTINATION_REACHED with no confirmation or call. Diagnostic only; K and destination rules "
                     "are unchanged.")},
        "a_routing": dict(sorted(route.items())),
        "waiting": {"opened": len(wait_ids), "observed_usable_return": len(usable),
                    "endings": dict(sorted(wait_end.items())), "blocker_observations": dict(blockers_seen.most_common()),
                    **dict(caps)},
        "issued_by_family_mode": dict(sorted(by_mode.items())),
        "a_return_calls": len(return_calls),
        "a_return_owners_entered_primary_60s": n_owners,
        "evidence_threshold": {"registered_minimum_distinct_owners": EVIDENCE_MIN_OWNERS, "observed": n_owners,
                               "status": threshold,
                               "note": ("distinct A RETURN owner/confirmation ids with a PRIMARY 60 s path ENTERED, "
                                        "once per owner; not B/C, IMMEDIATE, sensitivities, reopenings or hourly "
                                        "samples. A reporting convention, not power analysis or a quota.")},
        "guidance_retired_by_scenario_terminal": retired_by_scenario,
    }
    diag: list[str] = []
    if not eval_calls:
        if not any(k.endswith(":BIRTH") for k in trans):
            diag.append("NO_SCENARIO_BIRTHS in the evaluation window")
        if not any(k.endswith(":CONFIRM") for k in trans):
            diag.append("NO_STRUCTURAL_CONFIRMATIONS")
        if routed and not route.get("RETURN_WAIT") and not route.get("IMMEDIATE_ISSUED"):
            diag.append("A_CONFIRMATIONS_NOT_ROUTABLE: " + ", ".join(f"{k} {n}" for k, n in route.most_common(5)))
        if terminal:
            diag.append("SCENARIO_TERMINALS: " + ", ".join(f"{k} {n}" for k, n in terminal.most_common(5)))
    if a_dest_first:
        diag.append(f"A_DESTINATION_BEFORE_CONFIRMATION: {len(a_dest_first)} armed A scenario(s) ended at the "
                    "narrative destination before confirmation (no call; closed rule, not relaxed)")
    if nd is not None and nd > Decimal("0.5"):
        diag.append(f"SELECTED_DOMAIN_INCOMPATIBILITY_FOR_DIRECTOR_REVIEW: N/D = {len(n_rows)}/{len(d_rows)}")
    out = {k: v for k, v in base.items() if k not in ("funnel", "room_erosion_staged", "diagnosis", "conclusion")}
    out.update(gates={}, limiting_landmarks={},
               gates_note="v0.3 gate statistics are in the entry_attempt records (G/Q/K per routing and return sample)")
    out.update(report_version=REPORT_VERSION, method={"method": "v0.3", "model": adv["identity"]["model"],
                                                      "status": "ENGINEERING_REVIEW_PENDING"},
               funnel=funnel, by_family_mode=by_family_mode, diagnosis=diag,
               conclusion={"verdict": "INCOMPLETE" if status != "completed" else "INSUFFICIENT_EVIDENCE"
                           if threshold != "MINIMUM_REPORTING_COUNT_REACHED" else "REPORTED_FOR_DIRECTOR_REVIEW",
                           "text": ("Run not complete: sections cover the committed prefix only." if status != "completed"
                                    else "v0.3 results are reported for Director diagnosis. More calls are not "
                                         "improvement by themselves; compare against the v0.2 baseline on the same "
                                         "pack with the comparison report (an integrated version comparison, not the "
                                         "RETURN effect alone).")})
    out["calls"]["by_family_mode"] = dict(sorted(by_mode.items()))
    return out


def render_markdown(a: dict[str, Any]) -> list[str]:
    lines = r2.render_markdown({**a, "room_erosion_staged": {}, "diagnosis": a.get("diagnosis") or [],
                                "conclusion": a["conclusion"]})
    lines[1] = "## Adviser evaluation — Revised v0.3 (MP-002; engineering review pending; hypothetical, no orders)"
    f = a["funnel"]
    dn = f["a_denominators"]
    w = f["waiting"]
    extra = [
        f"- Scenario transitions: {f['scenario_transitions'] or '{}'} · warmup-context scenarios "
        f"{f['warmup_context_scenarios']}",
        f"- A confirmations {f['a_confirmations']}: D {dn['D_geometrically_evaluable']} · N "
        f"{dn['N_initially_empty_corridor_or_fixed_k_economics']} · N/D {dn['N_over_D'] or '—'} · excluded "
        f"{dn['excluded'] or '{}'}",
        f"- A routing: {f['a_routing'] or '{}'}",
        _dest_first_line(f.get("a_destination_before_confirmation")),
        f"- Waiting for a usable price: opened {w['opened']} · usable return observed {w['observed_usable_return']} · "
        f"endings {w['endings'] or '{}'} · cap revisions {w.get('CAP_REVISIONS', 0)}",
        f"- Issued by family/mode: {f['issued_by_family_mode'] or '{}'} · guidance retired by scenario terminal "
        f"{f['guidance_retired_by_scenario_terminal']}",
        f"- **A RETURN owners entered at PRIMARY 60 s: {f['a_return_owners_entered_primary_60s']}** "
        f"(registered minimum for discussion {f['evidence_threshold']['registered_minimum_distinct_owners']}) → "
        f"{f['evidence_threshold']['status']}",
    ]
    for k, v in (a.get("by_family_mode") or {}).items():
        extra.append(f"  - {k}: calls {v['calls']} · entered {v['entered']} · target {v['target']} · stop {v['stop']} "
                     f"· other exits {v['other_closed']} · no entry {v['no_entry']} · price-net sum {v['sum_price_net']}")
    return lines[:3] + extra + lines[3:]


def _dest_first_line(x: dict | None) -> str:
    if x is None:  # report built before this diagnostic existed
        return "- A destination before confirmation: not reported by this report build"
    ex = "; ".join(f"{e['direction']} {e['scenario_id']} at {e['at']} (K {e['trigger_level']} · destination "
                   f"{e['destination']})" for e in x["examples"])
    return (f"- A destination contacted before confirmation (no call, rules unchanged): {x['count']}"
            + (f" — e.g. {ex}" if ex else ""))
