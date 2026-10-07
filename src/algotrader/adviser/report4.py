"""v0.4 adviser evaluation report section (``adviser.report.v4``), built from COMMITTED records only.

It is the v0.3 registered report (structural scenarios, D/N, IMMEDIATE/RETURN routing, waits, the entered-primary-60s
RETURN owner criterion, call outcomes and coverage) plus the MP-003 pre-confirmation A anchor diagnostics:

* owner level: distinct structural A owners (scenario ids) that lost a local anchor, were re-armed by a prospective
  replacement, confirmed after a replacement, or ended structurally while waiting without a replacement;
* event level: certified V contacts versus ambiguous anchors (by reason), replacements and supersessions.

Only records published inside the evaluation window count; owners born in warmup are reported separately. One owner
re-anchoring several times is ONE owner (never several independent observations). A dead anchor is never tested
again, so repeated contacts cannot inflate the counts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from . import methods
from . import report as r2
from . import report3 as r3
from . import report_periods as rp

REPORT_VERSION = "adviser.report.v4"


def anchor_diagnostics(*, engine: dict, journal: list[dict], calls: list[dict] | None = None) -> dict[str, Any]:
    adv = engine["adviser"]
    es, ee = r2._dt(adv["eval_start"]), r2._dt(adv["eval_end"])
    lost_ev: Counter = Counter()
    lost_reason: Counter = Counter()
    owners: dict[str, set] = {k: set() for k in ("lost", "lost_warmup_origin", "rearmed", "confirmed_after_rearm",
                                                 "terminal_without_rearm")}
    terminal_without: Counter = Counter()
    rearms = supersessions = 0
    had_rearm: set[str] = set()
    status: dict[str, str] = {}  # last scenario status per A scenario (structural)
    for e in journal:
        if e["kind"] != "scenario" or e["record"]["family"] != "A":
            continue
        rec = e["record"]
        sid, tr = rec["scenario_id"], rec["transition"]
        t = r2._dt(rec["env"]["published_at"])
        in_eval = es <= t < ee
        if tr == "REARM":
            had_rearm.add(sid)
        if in_eval:
            if tr == "ANCHOR_LOST":
                lost_ev[rec["anchor_status"]] += 1
                lost_reason[str(rec["reason"]).split(":")[0]] += 1
                owners["lost_warmup_origin" if rec["warmup_origin"] else "lost"].add(sid)
            elif tr == "REARM":
                rearms += 1
                owners["rearmed"].add(sid)
            elif tr == "REVISE":
                supersessions += 1
            elif tr == "CONFIRM" and sid in had_rearm:
                owners["confirmed_after_rearm"].add(sid)
            elif tr == "TERMINAL" and status.get(sid) == "LOST":
                owners["terminal_without_rearm"].add(sid)
                terminal_without[f"{rec['terminal_state']}:{str(rec['reason']).split(':')[0]}"] += 1
        status[sid] = "LOST" if tr == "ANCHOR_LOST" else ("ARMED" if tr in ("ARM", "REVISE", "REARM") else
                                                          status.get(sid, "WATCH") if tr != "CONFIRM" else "CONFIRMED")
    after_rearm_calls = [c for c in (calls or []) if c.get("scenario_id") in had_rearm
                         and es <= r2._dt(c["issued_at"]) < ee]
    return {
        "owners": {"lost_anchor": len(owners["lost"]), "lost_anchor_warmup_origin": len(owners["lost_warmup_origin"]),
                   "rearmed_by_replacement": len(owners["rearmed"]),
                   "confirmed_after_replacement": len(owners["confirmed_after_rearm"]),
                   "structural_terminal_without_replacement": len(owners["terminal_without_rearm"])},
        "events": {"anchor_losses": sum(lost_ev.values()), "certified_contacts": lost_ev.get("INVALIDATED", 0),
                   "ambiguous_anchors": lost_ev.get("UNASSESSABLE", 0), "loss_reasons": dict(sorted(lost_reason.items())),
                   "replacements": rearms, "supersessions_without_contact": supersessions},
        "terminals_without_replacement": dict(sorted(terminal_without.items())),
        "calls_after_replacement": len(after_rearm_calls),
        "note": ("Owner-level counts are distinct structural A scenario ids (one owner re-anchoring several times is one "
                 "owner, not several observations); event-level counts are journal transitions. Only records published "
                 "inside the evaluation window count; owners born in warmup are reported separately. A dead anchor is "
                 "never re-tested, so repeated contacts cannot inflate the counts."),
    }


def build(*, engine: dict, journal: list[dict], records: list[dict], view: dict | None, status: str,
          clock_end_reached: bool) -> dict[str, Any]:
    out = r3.build(engine=engine, journal=journal, records=records, view=view, status=status,
                   clock_end_reached=clock_end_reached)
    rel = methods.get("v0.4")
    calls = [e["record"] for e in journal if e["kind"] == "call"]
    anchors = anchor_diagnostics(engine=engine, journal=journal, calls=calls)
    out.update(report_version=REPORT_VERSION,
               method={"method": "v0.4", "model": engine["adviser"]["identity"]["model"], "status": rel.status,
                       "status_label": rel.status_label, "economic_usefulness": "UNVALIDATED"},
               anchors=anchors,
               gates_note="v0.4 gate statistics are in the entry_attempt records (G/Q/K per routing and return sample)")
    if status == "completed":
        out["conclusion"] = {
            "verdict": out["conclusion"]["verdict"],
            "text": ("v0.4 results are reported for Director diagnosis. More calls are not improvement by themselves; "
                     "compare against the accepted v0.3 baseline on the same pack with the comparison report (the "
                     "integrated MP-003 anchor delta, not a proof that any particular call would be recovered).")}
    # WP-013 (additive, only for a registered explicit initialization and/or a multi-month evaluation window, so the
    # reports of earlier single-month runs are unchanged): context attestation, launch pins, total + monthly sections
    ic = rp.initial_context(engine, journal)
    if ic is not None:
        out["initial_context"] = ic
    pr = rp.periods(engine=engine, journal=journal, records=records, base=out, status=status)
    if pr is not None:
        out["periods"] = pr
    if ic is not None or pr is not None:
        out["launch_pins"] = rp.launch_pins(engine)
    if anchors["owners"]["lost_anchor"] and not anchors["owners"]["rearmed_by_replacement"]:
        out["diagnosis"] = list(out.get("diagnosis") or []) + [
            f"ANCHOR_LOSS_WITHOUT_REPLACEMENT: {anchors['owners']['lost_anchor']} owner(s) lost a local anchor and "
            "none was re-armed by a newer deeper complete reaction"]
    return out


def render_markdown(a: dict[str, Any]) -> list[str]:
    lines = r3.render_markdown(a)
    status_label = a["method"].get("status_label") or "engineering review pending"
    lines[1] = f"## Adviser evaluation — Candidate v0.4 (MP-003; {status_label}; hypothetical, no orders)"
    x = a.get("anchors") or {}
    o, ev = x.get("owners") or {}, x.get("events") or {}
    extra = [
        f"- Pre-confirmation A anchors (owners): lost {o.get('lost_anchor', 0)} (warmup-origin "
        f"{o.get('lost_anchor_warmup_origin', 0)}) · re-armed by a deeper completed reaction "
        f"{o.get('rearmed_by_replacement', 0)} · confirmed after replacement {o.get('confirmed_after_replacement', 0)} "
        f"· structural end while waiting without replacement {o.get('structural_terminal_without_replacement', 0)}",
        f"- Anchor events: losses {ev.get('anchor_losses', 0)} (certified V contacts {ev.get('certified_contacts', 0)}"
        f", ambiguous {ev.get('ambiguous_anchors', 0)}) · replacements {ev.get('replacements', 0)} · supersessions "
        f"without contact {ev.get('supersessions_without_contact', 0)} · calls after replacement "
        f"{x.get('calls_after_replacement', 0)}",
    ]
    return lines[:3] + extra + lines[3:] + rp.render_markdown(a)
