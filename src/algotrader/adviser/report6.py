"""v0.6 adviser evaluation report section (``adviser.report.v6``), built from COMMITTED records only.

It is the v0.5 report (MP-004 §7 W/P/C/R/N/I/X/A accounting, total and monthly by WAIT-open cohort) plus the MP-005 §6
initial response incompatibility:

* a prepared reference counts in P; its INITIAL_RESPONSE_INCOMPATIBLE terminal counts in X (cause
  ``INITIAL_RESPONSE_INCOMPATIBLE``) and never in C, R, N, I or A, so ``P = C + R + X + A``, ``R = N + I`` and the W
  identity hold unchanged;
* the INITIAL_RESPONSE_INCOMPATIBLE count is a SUBSET of X (never added a second time), shown by base (CORRIDOR /
  HISTORICAL_ECONOMICS; a concurrent economic incompatibility is annotated, never a second terminal), by direction and
  per WAIT-open month, with its ratio over P (zero denominator = undefined) and the stored diagnostic bases;
* declared information loss: children ended at the preparation receive no later C/R classification that MP-004 might
  have produced; no counterfactual classification is reconstructed, and C/P or R/P changes between versions do not
  show a better local response.

The earlier 20-owner RETURN convention is NOT_APPLICABLE (no substitute). Nothing here is a frequency or profit quota.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from . import methods
from . import report as r2
from . import report5 as r5
from . import report_periods as rp
from .core6 import BASES, REASON

REPORT_VERSION = "adviser.report.v6"
LOSS_NOTE = ("Declared information loss (MP-005 §6): a child ended INITIAL_RESPONSE_INCOMPATIBLE at its preparation "
             "receives no later local classification (C or R) that it might have produced under MP-004 v0.5; no "
             "counterfactual classification is reconstructed. Changes of C/P or R/P between v0.5 and v0.6 therefore do "
             "not show a better local response.")
SUBSET_NOTE = ("INITIAL_RESPONSE_INCOMPATIBLE is a subset of X (never added a second time): P = C + R + X + A still "
               "holds; ratio over P, a zero denominator is undefined.")
ATTEMPT_NOTE = ("An INITIAL_RESPONSE_INCOMPATIBLE ending terminates the entry attempt only; the structural scenario is "
                "not invalidated and keeps its own lifecycle.")


def _incompatible(fates: list[dict]) -> dict[str, Any]:
    by_base, by_dir, annotated = Counter(), Counter(), Counter()
    examples: list[dict] = []
    for f in fates:
        if f["class"] != "X" or f["detail"].get("cause") != REASON:
            continue
        resp = f["end"].get("response") or {}
        base = resp.get("incompatibility_base") or str(f["end"]["reason"]).split(":", 1)[-1]
        by_base[base] += 1
        by_dir[f["direction"]] += 1
        for a in str(resp.get("incompatibility_annotations") or "").split(","):
            if a:
                annotated[a] += 1
        if len(examples) < 5:
            examples.append({k: resp.get(k) for k in ("reference_bar", "H0", "L0", "published_at", "F", "C0", "A0",
                                                      "F_cap_C0", "J0", "incompatibility_base",
                                                      "incompatibility_annotations", "execution_profile")}
                            | {"entry_attempt_id": f["id"], "direction": f["direction"]})
    return {"count": sum(by_base.values()), "by_base": {b: by_base.get(b, 0) for b in BASES},
            "by_direction": {d: by_dir.get(d, 0) for d in ("LONG", "SHORT")},
            "concurrent_annotations": dict(sorted(annotated.items())), "examples": examples}


def _attach(section: dict, fates: list[dict]) -> None:
    inc = _incompatible(fates)
    c = section["counts"]
    inc["ratio_over_P"] = None if c["P"] == 0 else str((Decimal(inc["count"]) / Decimal(c["P"])).quantize(
        Decimal("0.0001")))
    inc["subset_of_X"] = inc["count"] <= c["X"] and inc["count"] == section["other_endings_by_priority_cause"].get(
        REASON, 0)
    section["initial_incompatibility"] = inc
    section["identities"]["initial_incompatible_subset_of_X"] = inc["subset_of_X"]
    section["identities_hold"] = all(section["identities"].values())


def response_accounting(*, engine: dict, journal: list[dict], status: str) -> dict[str, Any]:
    out = r5.response_accounting(engine=engine, journal=journal, status=status)
    adv = engine["adviser"]
    es, ee = r2._dt(adv["eval_start"]), r2._dt(adv["eval_end"])
    fates = [f for f in r5.child_fates(journal).values() if es <= r2._dt(f["opened_at"]) < ee]
    _attach(out["total"], fates)
    for m, lo, hi in rp.month_bounds(es, ee):
        if m in (out.get("months") or {}):
            _attach(out["months"][m], [f for f in fates if lo <= r2._dt(f["opened_at"]) < hi])
    if out.get("months_reconcile"):
        out["months_reconcile"]["every_month_identities_hold"] = all(
            s["identities_hold"] for s in out["months"].values())
        out["months_reconcile"]["initial_incompatible_months_sum_to_total"] = sum(
            s["initial_incompatibility"]["count"] for s in out["months"].values()) == out["total"][
            "initial_incompatibility"]["count"]
    out["initial_incompatibility_notes"] = {"subset": SUBSET_NOTE, "information_loss": LOSS_NOTE,
                                            "attempt_not_scenario": ATTEMPT_NOTE}
    return out


def build(*, engine: dict, journal: list[dict], records: list[dict], view: dict | None, status: str,
          clock_end_reached: bool) -> dict[str, Any]:
    out = r5.build(engine=engine, journal=journal, records=records, view=view, status=status,
                   clock_end_reached=clock_end_reached)
    rel = methods.get("v0.6")
    resp = response_accounting(engine=engine, journal=journal, status=status)
    resp["report_cross_checks"] = (out.get("responses") or {}).get("report_cross_checks")
    f = out.get("funnel") or {}
    f["evidence_threshold"] = {**r5.THRESHOLD_NOT_APPLICABLE, "observed": f.get("a_return_owners_entered_primary_60s"),
                               "note": r5.THRESHOLD_NOT_APPLICABLE["note"].replace("v0.5 (WP-014 correction F3)",
                                                                                    "v0.5 and v0.6")}
    out.update(report_version=REPORT_VERSION,
               method={"method": "v0.6", "model": engine["adviser"]["identity"]["model"], "status": rel.status,
                       "status_label": rel.status_label, "economic_usefulness": "UNVALIDATED"},
               responses=resp,
               gates_note="v0.6 gate statistics are in the entry_attempt records (G/Q/K per routing, return sample, "
                          "initial incompatibility bases and decisive recovery)")
    if status == "completed":
        out["conclusion"] = {
            "verdict": "REPORTED_FOR_DIRECTOR_REVIEW",
            "text": ("v0.6 results are reported for Director diagnosis; no registered evidence criterion applies to "
                     "v0.6 (the earlier 20-owner RETURN convention is not applicable). More or fewer calls are not "
                     "improvement by themselves; a v0.5/v0.6 comparison on the same pack shows the integrated MP-005 "
                     "delta, and children ended at the preparation lose their later C/R classification (no "
                     "counterfactual).")}
    t = resp["total"]
    diag = [x for x in (out.get("diagnosis") or []) if not str(x).startswith("NO_LOCAL_RECOVERY_OBSERVED")]
    if t["counts"]["P"] and not t["counts"]["R"]:
        diag.append(f"NO_LOCAL_RECOVERY_OBSERVED: {t['counts']['P']} reference(s) prepared, {t['counts']['C']} "
                    f"contradicted, {t['initial_incompatibility']['count']} initially incompatible (subset of X), "
                    f"{t['counts']['X']} ended by another cause in total (X), {t['counts']['A']} still waiting")
    if diag or out.get("diagnosis") is not None:
        out["diagnosis"] = diag
    return out


def render_markdown(a: dict[str, Any]) -> list[str]:
    lines = r5.render_markdown(a)
    status_label = a["method"].get("status_label") or "engineering review pending"
    lines[1] = f"## Adviser evaluation — Candidate v0.6 (MP-005; {status_label}; hypothetical, no orders)"
    x = a.get("responses") or {}
    if not x:
        return lines
    i = next((k for k, ln in enumerate(lines) if ln.startswith("### A RETURN response")), None)
    if i is not None:
        lines[i] = "### A RETURN response (MP-004 §7 with MP-005 §6; unit = A RETURN child)"
    return lines + incompatibility_markdown(x)


def _inc_line(label: str, s: dict) -> str:
    inc = s["initial_incompatibility"]
    return (f"| {label} | {inc['count']} | {inc['by_base']['CORRIDOR']} | {inc['by_base']['HISTORICAL_ECONOMICS']} | "
            f"{s['counts']['X']} | {s['counts']['P']} | {inc['ratio_over_P'] or 'undef.'} | "
            f"{'yes' if inc['subset_of_X'] else '**NO**'} |")


def incompatibility_markdown(x: dict) -> list[str]:
    t = x["total"]
    inc = t["initial_incompatibility"]
    out = ["", "#### Initial response incompatibility (MP-005 §6; subset of X)",
           "| Period | INITIAL_RESPONSE_INCOMPATIBLE | base CORRIDOR | base HISTORICAL_ECONOMICS | X | P | ratio over P "
           "| subset of X |", "|---|---|---|---|---|---|---|---|", _inc_line("Total", t)]
    for m, s in (x.get("months") or {}).items():
        out.append(_inc_line(m, s))
    out.append(f"- By direction: {inc['by_direction']} · concurrent annotations (never a second terminal): "
               f"{inc['concurrent_annotations'] or '{}'}")
    for e in inc["examples"][:3]:
        out.append(f"  - {e['direction']} {e['entry_attempt_id']}: reference {e['reference_bar']} H0 {e['H0']} L0 "
                   f"{e['L0']} · F {e['F']} · C0 {e['C0']} · A0 {e['A0'] or '—'} · F∩C0 {e['F_cap_C0'] or '∅'} · J0 "
                   f"{e['J0'] or '∅'} → {e['incompatibility_base']}")
    notes = x.get("initial_incompatibility_notes") or {}
    out += [f"- {notes.get('subset', SUBSET_NOTE)}", f"- {notes.get('attempt_not_scenario', ATTEMPT_NOTE)}",
            f"- {notes.get('information_loss', LOSS_NOTE)}"]
    mr = x.get("months_reconcile") or {}
    if "initial_incompatible_months_sum_to_total" in mr:
        out.append("- Months (WAIT-open cohort, no reset): initial incompatibility sums to total "
                   f"{'yes' if mr['initial_incompatible_months_sum_to_total'] else '**NO**'}")
    return out
