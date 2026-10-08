"""v0.5 adviser evaluation report section (``adviser.report.v5``), built from COMMITTED records only.

It is the v0.4 report (structural scenarios, D/N, routing, waits, anchors, the entered-primary-60s RETURN owner
criterion, call outcomes, coverage and the WP-013 continuous-run sections) plus the MP-004 §7 A RETURN response
accounting:

* unit = one A RETURN child (entry attempt id), separated by direction and by window (warmup clearings apart, never
  evaluation references); no per-bar counting;
* W children routed to WAIT_RETURN in the window, P references prepared, C ended by a local contradiction before any
  recovery, R first decisive recoveries observed, N first recoveries not issuable, I calls issued, X other endings
  after the reference (expiry, scenario terminal, contacts, caps, coverage/ambiguity, clearing, window end) and A
  waits still open at the report cutoff (the last committed record);
* identities ``P = C + R + X + A``, ``R = N + I`` and ``W = P + endings before a reference + WAIT_RETURN still open``,
  checked on the same perimeter; ratios P/W, C/P, R/P, N/R, I/R, I/P with a zero denominator reported as undefined;
* N keeps every blocker and one deterministic primary reason (economics/geometry, other gates, selection; smallest
  code inside the class; a late first recovery is its own class); incidences are never summed. X uses the lifecycle's
  priority cause. Ambiguity and coverage are never counted as proven contradictions.

Months (continuous runs): a child belongs to the calendar month in which its WAIT opened and is followed to its
ending wherever it falls (the WP-013 WAIT attribution), so every identity holds per month and the months sum to the
total. Outcomes and later entries belong to the separate economic report, not to these denominators. Nothing here is a
frequency or profit quota, and C/P or R/P do not measure deterioration or continuation quality.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from . import methods
from . import report as r2
from . import report4 as r4
from . import report_periods as rp
from .core5 import LATE, reason_class

REPORT_VERSION = "adviser.report.v5"
KEYS = ("W", "P", "C", "R", "N", "I", "X", "A")
RATIOS = (("P/W", "P", "W"), ("C/P", "C", "P"), ("R/P", "R", "P"), ("N/R", "N", "R"), ("I/R", "I", "R"),
          ("I/P", "I", "P"))
ENDINGS = ("TERMINAL", "REJECT", "ISSUE", "CLEARED")
MEANING = {
    "W": "A RETURN children routed to WAIT_RETURN", "P": "local references prepared",
    "C": "ended by a local contradiction before any recovery", "R": "first decisive recoveries observed",
    "N": "first recoveries not issuable", "I": "calls issued", "X": "other endings after the reference",
    "A": "still waiting for the response at the report cutoff"}


def child_fates(journal: list[dict]) -> dict[str, dict[str, Any]]:
    """One fate per A RETURN child (WAIT_OPEN record), from its own committed entry-attempt records only."""
    out: dict[str, dict[str, Any]] = {}
    for e in journal:
        if e["kind"] != "entry_attempt":
            continue
        rec = e["record"]
        eid = rec["entry_attempt_id"]
        if rec["transition"] == "WAIT_OPEN" and rec["family"] == "A" and eid not in out:
            out[eid] = {"id": eid, "direction": rec["direction"], "opened_at": rec["env"]["published_at"],
                        "reference": None, "end": None}
            continue
        f = out.get(eid)
        if f is None or f["end"] is not None:
            continue
        if rec["transition"] == "RESPONSE_REFERENCE":
            f["reference"] = rec
        elif rec["transition"] in ENDINGS and rec["state"] in ("TERMINAL", "ISSUED", "CLEARED"):
            f["end"] = rec
    for f in out.values():
        f["class"], f["detail"] = _classify(f)
    return out


def _classify(f: dict) -> tuple[str, dict[str, Any]]:
    end, ref = f["end"], f["reference"]
    if ref is None:
        if end is None:
            return "WAIT_RETURN_OPEN", {}
        return "ENDED_BEFORE_REFERENCE", {"reason": str(end["reason"]).split(":")[0].split(",")[0]}
    if end is None:
        return "A", {}
    resp = end.get("response") or {}
    reason = str(end["reason"] or "")
    if end["transition"] == "ISSUE":
        return "I", {"call_id": end.get("call_id")}
    if reason.startswith("RESPONSE_NOT_ISSUABLE"):
        prim = resp.get("primary_reason") or reason.split(":", 1)[1]
        return "N", {"primary": prim, "class": resp.get("primary_class") or reason_class(prim),
                     "blockers": list(end.get("blockers") or [prim]), "late": prim == LATE}
    if reason.startswith("LOCAL_RESPONSE_CONTRADICTED"):
        return "C", {"recovery_before_contradiction": resp.get("recovery_close_observed_before_priority")}
    cause = reason.split(":")[0].split(",")[0] if end["transition"] != "CLEARED" else "CLEARED"
    if cause == "SCENARIO_TERMINAL":
        cause = ":".join(reason.split(":")[:3])
    return "X", {"cause": cause, "observed": resp.get("observed_in_priority_dispatch")}


def _ratio(n: int, d: int) -> str | None:
    return None if d == 0 else str((Decimal(n) / Decimal(d)).quantize(Decimal("0.0001")))


def tally(fates: list[dict]) -> dict[str, Any]:
    c = Counter()
    by_dir: dict[str, Counter] = {"LONG": Counter(), "SHORT": Counter()}
    pre_ref, n_primary, n_class, n_incidence, x_cause = Counter(), Counter(), Counter(), Counter(), Counter()
    late = 0
    observed_in_priority = Counter()
    for f in fates:
        k, det = f["class"], f["detail"]
        keys = ["W"] + (["P"] if f["reference"] is not None else []) + (
            [k] if k in ("C", "X", "A") else ["R", k] if k in ("N", "I") else [])
        for x in keys:
            c[x] += 1
            by_dir[f["direction"]][x] += 1
        if k == "ENDED_BEFORE_REFERENCE":
            pre_ref[det["reason"]] += 1
        elif k == "WAIT_RETURN_OPEN":
            c["wait_return_open"] += 1
        elif k == "N":
            n_primary[det["primary"]] += 1
            n_class[det["class"]] += 1
            late += det["late"]
            for b in det["blockers"]:
                n_incidence[b.split(":")[0]] += 1
        elif k == "X":
            x_cause[det["cause"]] += 1
            if det.get("observed"):
                observed_in_priority[det["observed"].split(":")[0]] += 1
    counts = {x: c.get(x, 0) for x in KEYS}
    checks = {
        "P_eq_C_plus_R_plus_X_plus_A": counts["P"] == counts["C"] + counts["R"] + counts["X"] + counts["A"],
        "R_eq_N_plus_I": counts["R"] == counts["N"] + counts["I"],
        "W_eq_P_plus_ended_before_reference_plus_wait_return_open":
            counts["W"] == counts["P"] + sum(pre_ref.values()) + c.get("wait_return_open", 0),
        "N_primary_partition": sum(n_primary.values()) == counts["N"],
        "X_cause_partition": sum(x_cause.values()) == counts["X"],
    }
    return {
        "counts": counts,
        "ratios": {name: _ratio(counts[a], counts[b]) for name, a, b in RATIOS},
        "by_direction": {d: {x: v.get(x, 0) for x in KEYS} for d, v in by_dir.items()},
        "ended_before_reference": dict(sorted(pre_ref.items())),
        "wait_return_open": c.get("wait_return_open", 0),
        "not_issuable": {"primary_reason": dict(sorted(n_primary.items())),
                         "primary_class": dict(sorted(n_class.items())),
                         "blocker_incidence_not_summable": dict(sorted(n_incidence.items())),
                         "late_first_recovery": late},
        "other_endings_by_priority_cause": dict(sorted(x_cause.items())),
        "local_conditions_annotated_in_priority_dispatches": dict(sorted(observed_in_priority.items())),
        "identities": checks, "identities_hold": all(checks.values()),
    }


def response_accounting(*, engine: dict, journal: list[dict], status: str) -> dict[str, Any]:
    adv = engine["adviser"]
    es, ee = r2._dt(adv["eval_start"]), r2._dt(adv["eval_end"])
    fates = list(child_fates(journal).values())
    ev = [f for f in fates if es <= r2._dt(f["opened_at"]) < ee]
    warm = [f for f in fates if r2._dt(f["opened_at"]) < es]
    cutoff = journal[-1]["clock_time"] if journal else None
    total = tally(ev)
    out: dict[str, Any] = {
        "unit": "A RETURN child (entry attempt), by direction; evaluation window only (warmup clearings apart)",
        "meaning": MEANING, "cutoff": cutoff,
        "cutoff_meaning": ("A = waits still open at the last committed record" + (
            "" if status == "completed" else "; the run is not complete, so A and the counts cover the committed "
                                             "prefix only")),
        "total": total,
        "warmup": {"children": len(warm), "cleared_at_evaluation_start": dict(sorted(Counter(
            ("WAIT_RESPONSE" if f["reference"] is not None else "WAIT_RETURN") for f in warm
            if f["end"] is not None and f["end"]["transition"] == "CLEARED").items())),
                   "other_warmup_endings": sum(1 for f in warm if f["end"] is not None
                                               and f["end"]["transition"] != "CLEARED"),
                   "note": "warmup references are cleared at the evaluation start and never become evaluation "
                           "references; the structural scenarios stay labelled warmup context"},
        "note": ("C/P does not measure real deterioration and R/P does not measure continuation quality; outcomes "
                 "and later entries belong to the separate economic report. No frequency or profit quota."),
    }
    months = rp.month_bounds(es, ee)
    if len(months) > 1:
        sections = {m: tally([f for f in ev if lo <= r2._dt(f["opened_at"]) < hi]) for m, lo, hi in months}
        sums = {x: sum(s["counts"][x] for s in sections.values()) for x in KEYS}
        out["months"] = sections
        out["months_attribution"] = ("child -> calendar month in which its WAIT opened, followed to its ending "
                                     "wherever it falls (never counted twice); no reset at a month boundary")
        out["months_reconcile"] = {"months_sum_to_total": sums == total["counts"],
                                   "every_month_identities_hold": all(s["identities_hold"] for s in sections.values())}
    return out


def build(*, engine: dict, journal: list[dict], records: list[dict], view: dict | None, status: str,
          clock_end_reached: bool) -> dict[str, Any]:
    out = r4.build(engine=engine, journal=journal, records=records, view=view, status=status,
                   clock_end_reached=clock_end_reached)
    rel = methods.get("v0.5")
    resp = response_accounting(engine=engine, journal=journal, status=status)
    t = resp["total"]["counts"]
    f = out.get("funnel") or {}
    w = f.get("waiting") or {}
    # v0.5 emits RESPONSE_REFERENCE (the bar a v0.4 RETURN would have used), never RETURN_USABLE
    w["observed_usable_return"] = t["P"]
    w["usable_return_meaning"] = "v0.5: the usable return bar prepares the local reference (P); it never issues"
    checks = {"W_equals_waits_opened": t["W"] == w.get("opened"),
              "I_equals_A_RETURN_calls_in_window": t["I"] == f.get("a_return_calls")}
    resp["report_cross_checks"] = checks
    out.update(report_version=REPORT_VERSION,
               method={"method": "v0.5", "model": engine["adviser"]["identity"]["model"], "status": rel.status,
                       "status_label": rel.status_label, "economic_usefulness": "UNVALIDATED"},
               responses=resp,
               gates_note="v0.5 gate statistics are in the entry_attempt records (G/Q/K per routing, return sample "
                          "and decisive recovery)")
    pr = out.get("periods")
    if pr is not None:
        for m, sec in pr["months"].items():
            ms = (resp.get("months") or {}).get(m)
            if ms is not None:
                sec["waits"]["observed_usable_return"] = ms["counts"]["P"]
        pr["total"]["waits"]["observed_usable_return"] = t["P"]
    if status == "completed":
        out["conclusion"] = {
            "verdict": out["conclusion"]["verdict"],
            "text": ("v0.5 results are reported for Director diagnosis. More or fewer calls are not improvement by "
                     "themselves; compare against the v0.4 baseline on the same pack with the comparison report (the "
                     "integrated MP-004 RETURN delta, not a proof that any particular call would be avoided or "
                     "recovered).")}
    if t["W"] and not t["P"]:
        out["diagnosis"] = list(out.get("diagnosis") or []) + [
            f"NO_RETURN_REFERENCE_PREPARED: {t['W']} A RETURN wait(s) opened and none reached a usable return bar"]
    if t["P"] and not t["R"]:
        out["diagnosis"] = list(out.get("diagnosis") or []) + [
            f"NO_LOCAL_RECOVERY_OBSERVED: {t['P']} reference(s) prepared, {t['C']} contradicted, {t['X']} ended by "
            f"another cause, {t['A']} still waiting"]
    return out


def render_markdown(a: dict[str, Any]) -> list[str]:
    lines = r4.render_markdown(a)
    status_label = a["method"].get("status_label") or "engineering review pending"
    lines[1] = f"## Adviser evaluation — Candidate v0.5 (MP-004; {status_label}; hypothetical, no orders)"
    return lines + response_markdown(a.get("responses") or {})


def _row(label: str, s: dict) -> str:
    c, r = s["counts"], s["ratios"]
    return (f"| {label} | " + " | ".join(str(c[k]) for k in KEYS) + " | "
            + " | ".join(r[n] if r[n] is not None else "undef." for n, _, _ in RATIOS)
            + f" | {'yes' if s['identities_hold'] else '**NO**'} |")


def response_markdown(x: dict) -> list[str]:
    if not x:
        return []
    t = x["total"]
    hdr = ("| Period | " + " | ".join(KEYS) + " | " + " | ".join(n for n, _, _ in RATIOS) + " | Identities |")
    out = ["", "### A RETURN response (MP-004 §7; unit = A RETURN child)",
           "- " + " · ".join(f"{k} {MEANING[k]}" for k in KEYS),
           f"- Cutoff {x.get('cutoff') or '—'}: {x['cutoff_meaning']}",
           "- Identities P = C + R + X + A, R = N + I, W = P + endings before a reference + WAIT_RETURN open; "
           "a zero denominator is undefined.", "", hdr, "|" + "---|" * (2 + len(KEYS) + len(RATIOS)), _row("Total", t)]
    for m, s in (x.get("months") or {}).items():
        out.append(_row(m, s))
    for d, v in t["by_direction"].items():
        out.append(f"- {d}: " + " · ".join(f"{k} {v[k]}" for k in KEYS))
    n = t["not_issuable"]
    out += [f"- Ended before a reference: {t['ended_before_reference'] or '{}'} · WAIT_RETURN still open "
            f"{t['wait_return_open']}",
            f"- N primary reason: {n['primary_reason'] or '{}'} · by class {n['primary_class'] or '{}'} · late first "
            f"recovery {n['late_first_recovery']} · blocker incidence (not summable) "
            f"{n['blocker_incidence_not_summable'] or '{}'}",
            f"- X by priority cause: {t['other_endings_by_priority_cause'] or '{}'}"
            + (f" · local conditions annotated in those dispatches "
               f"{t['local_conditions_annotated_in_priority_dispatches']}"
               if t["local_conditions_annotated_in_priority_dispatches"] else "")]
    if x.get("months_reconcile"):
        mr = x["months_reconcile"]
        out.append(f"- Months ({x['months_attribution']}): sum to total {'yes' if mr['months_sum_to_total'] else '**NO**'}"
                   f" · identities in every month {'yes' if mr['every_month_identities_hold'] else '**NO**'}")
    wu = x["warmup"]
    out.append(f"- Warmup (not evaluated): {wu['children']} child(ren); cleared at the evaluation start "
               f"{wu['cleared_at_evaluation_start'] or '{}'}; other warmup endings {wu['other_warmup_endings']}")
    cc = x.get("report_cross_checks") or {}
    if cc:
        out.append("- Cross-checks with the report funnel: " + " · ".join(
            f"{k} {'yes' if v else '**NO**'}" for k, v in cc.items()))
    out.append(f"- {x['note']}")
    return out
