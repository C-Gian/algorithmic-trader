"""Two-run adviser comparison (WP-011 §6): an honest, copyable side-by-side of two ALREADY EXISTING adviser evaluation
reports (typically Original v0.2 then Revised v0.3 on the same prepared pack). It never launches, resumes or replays
anything; selecting or refreshing a comparison only reads committed reports.

Comparable only when the material inputs are identical: pack id and pack manifest, feed content identity, availability
and clock policy, instrument tick and channels, evaluation window and clock end, capability profile and the
evaluator's declared delays/costs/funding treatment. Method rules/register/implementation identities are EXPECTED to
differ. Any other difference is listed by field and the pair is labelled NONCOMPARABLE; an incomplete or failed run
or failed runtime assurance makes the pair INCOMPLETE. No winner is chosen: the total change mixes every MP-002 policy
change (structural lifecycle, clocks, RETURN) and, for a v0.2/v0.3 pair, the dislocation correction (the frozen v0.2
baseline keeps its acknowledged never-active dislocation veto; v0.3 applies the retained once-per-slot rule), so it does
not identify the RETURN effect alone.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

COMPARISON_VERSION = "adviser.comparison.v1"
DISLOCATION_LIMITATION = {
    "id": "V02_DISLOCATION_BASELINE_DEFECT_CORRECTED_IN_V03",
    "text": ("Additional version difference: the frozen v0.2 baseline keeps its acknowledged dislocation-baseline defect "
             "(the trade/mark dislocation veto is never active), unchanged by design; v0.3 applies the retained "
             "once-per-slot dislocation rule. The integrated comparison therefore also includes this correction and "
             "cannot attribute any difference to RETURN alone.")}
PIN_FIELDS = ("pack_id", "instrument", "feed_content_identity", "availability_policy_id", "clock_policy", "tick",
              "channels", "evaluation", "clock_end")
EVALUATOR_FIELDS = ("entry_delay_seconds", "exit_delay_seconds", "boundary_alignment", "opening_condition",
                    "fee_per_leg", "allowance_per_leg", "adequacy_envelope_bps", "funding", "notional_unit")


def _evaluator_terms(engine: dict) -> dict[str, Any]:
    prof = ((engine.get("adviser") or {}).get("evaluator") or {}).get("profiles") or {}
    return {v: {k: p.get(k) for k in EVALUATOR_FIELDS} for v, p in sorted(prof.items())}


def run_facts(ev: dict, replay: dict, report: dict) -> dict[str, Any]:
    eng = replay.get("engine") or {}
    adv = eng.get("adviser") or {}
    a = report.get("adviser") or {}
    ident = adv.get("identity") or {}
    val = report.get("validation") or {}
    return {
        "evaluation_id": ev["evaluation_id"], "replay_id": replay["replay_id"], "status": replay["status"],
        "method": adv.get("method") or ("v0.2" if adv else None), "model": ident.get("model"),
        "rules_version": ident.get("rules_version"), "rules_sha256": ident.get("rules_sha256"),
        "register_sha256": ident.get("register_sha256"), "implementation": ident.get("implementation"),
        "identity_sha256": ident.get("identity_sha256"),
        "capability_profile_sha256": ident.get("capability_profile_sha256"),
        "pins": {k: (ident.get("pins") or {}).get(k) for k in PIN_FIELDS},
        "pack_manifest_sha256": (eng.get("pack") or {}).get("pack_manifest_sha256"),
        "evaluator_terms": _evaluator_terms(eng), "evaluator_sha256": (adv.get("evaluator") or {}).get("sha256"),
        "assurance": _assurance_state((report.get("operation") or {}).get("assurance")),
        "validation_outcome": val.get("outcome"),
        "adviser": a,
    }


def _assurance_state(x: Any) -> str:
    """Operational assurance as one plain state (``ops`` reports an object with state and details)."""
    if isinstance(x, dict):
        return str(x.get("state") or "UNKNOWN").upper()
    return str(x or "UNKNOWN").upper()


def comparability(a: dict, b: dict) -> dict[str, Any]:
    diffs = []
    for k in PIN_FIELDS:
        if a["pins"].get(k) != b["pins"].get(k):
            diffs.append({"field": f"pins.{k}", "a": a["pins"].get(k), "b": b["pins"].get(k)})
    for k in ("pack_manifest_sha256", "capability_profile_sha256", "evaluator_terms"):
        if a.get(k) != b.get(k):
            diffs.append({"field": k, "a": a.get(k), "b": b.get(k)})
    incomplete = [f"{x['evaluation_id']} is {x['status']}" for x in (a, b) if x["status"] != "completed"]
    incomplete += [f"{x['evaluation_id']} runtime validation {x['validation_outcome']}" for x in (a, b)
                   if x["status"] == "completed" and x["validation_outcome"] != "passed"]
    not_adviser = [x["evaluation_id"] for x in (a, b) if not x["adviser"] or x["adviser"].get("pending")]
    verdict = ("NOT_ADVISER_RUNS" if not_adviser else "NONCOMPARABLE" if diffs else
               "INCOMPLETE" if incomplete else "COMPARABLE")
    return {"verdict": verdict, "differences": diffs, "incomplete": incomplete, "not_adviser_runs": not_adviser,
            "expected_differences": ["method model/rules/register/implementation identity",
                                     "evaluator implementation/profile ids (v2 vs v3)"],
            "same_method": a["method"] == b["method"]}


def _summary(x: dict) -> dict[str, Any]:
    a = x["adviser"] or {}
    calls = a.get("calls") or {}
    cov = a.get("coverage") or {}
    prim = ((a.get("outcomes") or {}).get("variants") or {}).get("PRIMARY") or {}
    f = a.get("funnel") or {}
    vs = a.get("view_samples") or {}
    out = {
        "evaluation_id": x["evaluation_id"], "method": x["method"], "model": x["model"],
        "implementation": x["implementation"], "status": x["status"], "assurance": x["assurance"],
        "report_version": a.get("report_version"),
        "coverage": {"evaluation_minutes": cov.get("evaluation_minutes"),
                     "assessable_minutes": cov.get("assessable_minutes"),
                     "unavailable_minutes": cov.get("unavailable_minutes")},
        "calls": calls.get("count"), "calls_per_evaluated_week": calls.get("per_evaluated_week"),
        "calls_by_family": calls.get("by_family"), "calls_by_family_mode": calls.get("by_family_mode"),
        "entry_available_minutes_median": (calls.get("entry_available_minutes") or {}).get("median"),
        "longest_no_call_interval_hours": calls.get("longest_no_call_interval_hours"),
        "thesis_terminals": calls.get("terminal"),
        "primary": {k: prim.get(k) for k in ("paths", "no_entry", "target_exits", "stop_exits", "guidance_exits",
                                             "ambiguous", "censored", "unresolved", "sum_price_net",
                                             "sum_stress_price_net", "total_net")},
        "view_1h": vs.get("1h"), "view_4h": vs.get("4h"),
    }
    if x["method"] == "v0.3":
        out["registered"] = {"a_confirmations": f.get("a_confirmations"), "a_denominators": f.get("a_denominators"),
                             "a_routing": f.get("a_routing"), "waiting": f.get("waiting"),
                             "issued_by_family_mode": f.get("issued_by_family_mode"),
                             "a_return_owners_entered_primary_60s": f.get("a_return_owners_entered_primary_60s"),
                             "evidence_threshold": f.get("evidence_threshold"),
                             "a_destination_before_confirmation":
                                 (f.get("a_destination_before_confirmation") or {}).get("count")}
    else:
        out["registered"] = {"births": f.get("births"), "arms": f.get("arms"),
                             "trigger_evaluations": f.get("trigger_evaluations"),
                             "rejection_blockers": f.get("rejection_blockers")}
    return out


def _delta(a, b) -> str | None:
    try:
        return str(Decimal(str(b)) - Decimal(str(a)))
    except Exception:  # noqa: BLE001 - absent/non-numeric fields have no delta
        return None


def build(a: dict, b: dict) -> dict[str, Any]:
    comp = comparability(a, b)
    sa, sb = _summary(a), _summary(b)
    deltas = None
    if comp["verdict"] == "COMPARABLE":
        deltas = {"calls": _delta(sa["calls"], sb["calls"]),
                  "primary_entries": _delta((sa["primary"]["paths"] or 0) - (sa["primary"]["no_entry"] or 0),
                                            (sb["primary"]["paths"] or 0) - (sb["primary"]["no_entry"] or 0)),
                  "primary_sum_price_net": _delta(sa["primary"]["sum_price_net"], sb["primary"]["sum_price_net"]),
                  "primary_sum_stress_price_net": _delta(sa["primary"]["sum_stress_price_net"],
                                                         sb["primary"]["sum_stress_price_net"])}
    ev = (sb.get("registered") or {}).get("evidence_threshold") if b["method"] == "v0.3" else \
        (sa.get("registered") or {}).get("evidence_threshold")
    if comp["verdict"] != "COMPARABLE":
        conclusion = {"verdict": comp["verdict"],
                      "text": "Not compared: " + ("; ".join(d["field"] for d in comp["differences"]) or
                                                  "; ".join(comp["incomplete"] + comp["not_adviser_runs"]))}
    elif ev and ev.get("status") == "MINIMUM_REPORTING_COUNT_REACHED":
        conclusion = {"verdict": "REPORTED_FOR_DIRECTOR_REVIEW",
                      "text": "Integrated version comparison on identical inputs; the Director diagnoses it. No "
                              "automatic improvement claim, ranking or variant choice."}
    else:
        conclusion = {"verdict": "INSUFFICIENT_EVIDENCE",
                      "text": "Integrated version comparison on identical inputs, below the registered minimum of "
                              "distinct A RETURN owners entered at 60 s (or none): frequency/practicality not "
                              "validated. More calls are not improvement by themselves."}
    methods = {a["method"], b["method"]}
    limitations = [DISLOCATION_LIMITATION] if methods == {"v0.2", "v0.3"} else []
    return {"comparison_version": COMPARISON_VERSION, "a": sa, "b": sb, "comparability": comp,
            "limitations": limitations,
            "pins": {"a": {**a["pins"], "pack_manifest_sha256": a["pack_manifest_sha256"],
                           "capability_profile_sha256": a["capability_profile_sha256"]},
                     "b": {**b["pins"], "pack_manifest_sha256": b["pack_manifest_sha256"],
                           "capability_profile_sha256": b["capability_profile_sha256"]}},
            "identities": {"a": {k: a[k] for k in ("model", "rules_version", "rules_sha256", "register_sha256",
                                                   "implementation", "identity_sha256", "evaluator_sha256")},
                           "b": {k: b[k] for k in ("model", "rules_version", "rules_sha256", "register_sha256",
                                                   "implementation", "identity_sha256", "evaluator_sha256")}},
            "deltas_b_minus_a": deltas, "conclusion": conclusion,
            "scope": ("Integrated VERSION comparison on the same prepared pack and profile: structural lifecycle, "
                      "clocks, the RETURN entry and (v0.2 vs v0.3) the dislocation-veto correction all changed "
                      "together, so the difference does not identify the RETURN effect alone. Hypothetical "
                      "normalized one-unit paths; no orders, sizing or account.")}


def render_markdown(c: dict[str, Any]) -> str:
    a, b, comp = c["a"], c["b"], c["comparability"]
    lines = ["# Adviser comparison — " + f"{a['method']} vs {b['method']}", "",
             f"> {c['scope']}", "",
             f"**Comparability: {comp['verdict']}**"]
    for d in comp["differences"]:
        lines.append(f"- differs: `{d['field']}` — A `{d['a']}` · B `{d['b']}`")
    for x in comp["incomplete"]:
        lines.append(f"- incomplete: {x}")
    if c.get("limitations"):
        lines += ["", "## Comparison limitations", *(f"- **{x['id']}** — {x['text']}" for x in c["limitations"])]
    p = c["pins"]["a"]
    lines += ["", "## Same inputs (pins)",
              f"- Pack `{p.get('pack_id')}` · manifest `{str(p.get('pack_manifest_sha256'))[:16]}` · feed "
              f"`{str(p.get('feed_content_identity'))[:16]}` · clock `{p.get('clock_policy')}` · tick {p.get('tick')}",
              f"- Evaluation {p.get('evaluation')} · clock end {p.get('clock_end')} · capability profile "
              f"`{str(p.get('capability_profile_sha256'))[:16]}`", "", "## Runs"]
    for tag, s in (("A", a), ("B", b)):
        pr = s["primary"]
        lines += [f"### {tag}: {s['method']} — `{s['evaluation_id']}` ({s['status']}, assurance {s['assurance']})",
                  f"- Method `{s['model']}` · implementation `{s['implementation']}` · report `{s['report_version']}`",
                  f"- Coverage: {s['coverage']['assessable_minutes']} of {s['coverage']['evaluation_minutes']} "
                  f"evaluation minutes assessable",
                  f"- Calls {s['calls']} ({s['calls_per_evaluated_week']}/week) · by family {s['calls_by_family']}"
                  + (f" · by family/mode {s['calls_by_family_mode']}" if s.get("calls_by_family_mode") else "")
                  + f" · entry available median {s['entry_available_minutes_median']} min · longest no-call "
                  f"{s['longest_no_call_interval_hours']} h",
                  f"- PRIMARY 60 s: paths {pr['paths']} · no entry {pr['no_entry']} · target {pr['target_exits']} · "
                  f"stop {pr['stop_exits']} · guidance {pr['guidance_exits']} · ambiguous {pr['ambiguous']} · "
                  f"censored {pr['censored']} · unresolved {pr['unresolved']} · price-net sum {pr['sum_price_net']} · "
                  f"stress {pr['sum_stress_price_net']} · total net {pr['total_net']}",
                  f"- Registered funnel: {s['registered']}"]
    if c["deltas_b_minus_a"]:
        lines += ["", "## B − A (integrated, not causal for RETURN alone)",
                  *(f"- {k}: {v}" for k, v in c["deltas_b_minus_a"].items())]
    lines += ["", f"**Conclusion: {c['conclusion']['verdict']}** — {c['conclusion']['text']}"]
    return "\n".join(lines) + "\n"
