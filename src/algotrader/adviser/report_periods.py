"""Continuous-run report sections (WP-013), built from COMMITTED records only, additive to ``adviser.report.v4``.

* ``initial_context`` — attestation of the context at the evaluation start of a run with a registered explicit
  initialization: coverage of the periods the method's existing landmarks/scales need, scale readiness, and the
  state of the relevant landmarks (previous day/week/month, 15m/1h pivots and their memory windows). Insufficient
  data and never-built landmarks are kept apart from levels that were built and then legitimately broken, expired or
  retired. Completeness of the pivot memory is never certified.
* ``launch_pins`` — method, parameters, build, profile, costs, clock and evaluator identities of the run.
* ``periods`` — whole-run totals and calendar-month sections of ONE continuous run. Calls belong to their month of
  issue and are followed to their outcome even after that month ends (never counted twice); confirmations, WAITs,
  coverage and view samples use their own times and denominators. Per variant, each section states the expected
  call-variant pairs (evaluable calls x pinned evaluator variants), the terminal records available and the pairs
  without a terminal record yet. ``reconciliation`` is the arithmetic of the AVAILABLE records only;
  ``outcome_completeness`` is separate and uses the run's actual status (feed coverage is not finalization): a pair
  without a record is "not yet recorded at checkpoint" for an unfinished run and makes the report explicitly
  INCOMPLETE for a run declared completed. Nothing is inferred for a missing pair (no entry, outcome, result or
  censoring) and the run's saved status/assurance are never changed.

Nothing here changes the method, its kernel, the evaluator or any stored record. Hypothetical sums are normalized
one-unit price-net sums (funding not covered), never an account return.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from typing import Any

from . import report as r2

MIN = timedelta(minutes=1)
VARIANTS = ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY")
STATUSES = ("CLOSED", "NO_ENTRY", "CENSORED", "UNRESOLVED", "AMBIGUOUS")
PENDING = "OUTCOMES_NOT_YET_RECORDED_AT_CHECKPOINT"
INCOMPLETE = "REPORT_INCOMPLETE_EXPECTED_TERMINAL_RECORD_MISSING"
PERIOD_LANDMARKS = (("PREV_1D", "previous_day"), ("PREV_1W", "previous_week"), ("PREV_1MO", "previous_month"))
PIVOTS = (("PIVOT_HIGH_15M", "PIVOT_LOW_15M", "15m"), ("PIVOT_HIGH_1H", "PIVOT_LOW_1H", "1h"))
SUM_MEANING = ("sum of normalized one-unit hypothetical price-net outcomes (N0=1, q=1/E): not an account return, not "
               "compounded, no sizing; funding not covered (PRICE_NET_ONLY)")


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def exact_sum(xs) -> Decimal:
    """Exact Decimal sum (no 28-digit context rounding); rounding is for presentation only."""
    with localcontext() as ctx:
        ctx.prec = 400
        return +sum((Decimal(str(x)) for x in xs), Decimal(0))


def _pct(x: Decimal | None) -> str | None:
    return None if x is None else format((x * 100).quantize(Decimal("0.001")), "f")


def add_months(t: datetime, n: int) -> datetime:
    m = t.month - 1 + n
    return t.replace(year=t.year + m // 12, month=m % 12 + 1)


def month_bounds(es: datetime, ee: datetime) -> list[tuple[str, datetime, datetime]]:
    """Calendar months [start, end) intersecting [es, ee), clipped to the evaluation window."""
    out, t = [], es.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while t < ee:
        n = add_months(t, 1)
        out.append((f"{t:%Y-%m}", max(t, es), min(n, ee)))
        t = n
    return out


def pinned_variants(engine: dict) -> tuple[str, ...] | None:
    """Variants actually configured and pinned by the run's evaluator identity (None when no evaluator is pinned)."""
    prof = (engine["adviser"].get("evaluator") or {}).get("profiles")
    if not prof:
        return None
    return tuple(v for v in VARIANTS if v in prof) + tuple(sorted(v for v in prof if v not in VARIANTS))


def _evaluable(c: dict) -> bool:
    """The evaluator consumes historical-modeled calls issued inside the evaluation window (window checked apart)."""
    return (c.get("env") or {}).get("origin", "HISTORICAL_MODELED") == "HISTORICAL_MODELED"


def is_multi_month(engine: dict) -> bool:
    adv = engine["adviser"]
    return len(month_bounds(r2._dt(adv["eval_start"]), r2._dt(adv["eval_end"]))) > 1


# ----------------------------------------------------------------------------------------------------------------------
# launch pins
# ----------------------------------------------------------------------------------------------------------------------

def launch_pins(engine: dict) -> dict[str, Any]:
    adv = engine["adviser"]
    ident = adv["identity"]
    ev = adv.get("evaluator") or {}
    prof = ev.get("profiles") or {}
    prim = prof.get("PRIMARY") or {}
    return {
        "method": adv["method"], "model": ident.get("model"), "rules_version": ident.get("rules_version"),
        "rules_sha256": ident.get("rules_sha256"), "register_sha256": ident.get("register_sha256"),
        "implementation": ident.get("implementation"), "identity_sha256": ident.get("identity_sha256"),
        "build": adv.get("build"), "runtime_format": adv.get("format"),
        "capability_profile": adv.get("profile"), "capability_profile_sha256": ident.get("capability_profile_sha256"),
        "clock_policy": adv.get("clock_policy"), "tick": adv.get("tick"), "channels": adv.get("channels"),
        "pack_id": (ident.get("pins") or {}).get("pack_id"),
        "feed_content_identity": (ident.get("pins") or {}).get("feed_content_identity"),
        "evaluator_format": ev.get("format"), "evaluator_sha256": ev.get("sha256"),
        "costs": {v: {k: p.get(k) for k in ("fee_per_leg", "allowance_per_leg", "adequacy_envelope_bps",
                                             "entry_delay_seconds", "exit_delay_seconds", "exit_mode", "funding")}
                  for v, p in sorted(prof.items())},
        "primary_entry_delay_seconds": prim.get("entry_delay_seconds"),
        "primary_is_60s": prim.get("entry_delay_seconds") == 60,
        "windows": {"initialization_start": adv.get("warmup_start"), "evaluation": [adv["eval_start"], adv["eval_end"]],
                    "tail_end": adv.get("tail_end"), "clock_end": adv.get("clock_end")},
    }


# ----------------------------------------------------------------------------------------------------------------------
# initial context attestation
# ----------------------------------------------------------------------------------------------------------------------

def _required_periods(es: datetime, age_15m: timedelta, age_1h: timedelta) -> dict[str, tuple[datetime, datetime]]:
    day = es.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = day - timedelta(days=day.weekday())
    month = day.replace(day=1)
    return {"previous_day": (day - timedelta(days=1), day), "previous_week": (monday - timedelta(days=7), monday),
            "previous_month": (add_months(month, -1), month), "pivot_15m_memory": (es - age_15m, es),
            "pivot_1h_memory": (es - age_1h, es)}


def _readiness(journal: list[dict], es: datetime) -> dict[str, Any]:
    last, first_ready = None, {}
    for e in journal:
        if e["kind"] != "observation" or e["record"].get("name") != "readiness":
            continue
        t = r2._dt(e["clock_time"])
        if t > es:
            break
        last = (t, e["record"]["category"])
        for part in str(e["record"]["category"]).split("/"):
            dep, _, st = part.partition(":")
            if st == "READY":
                first_ready.setdefault(dep, _iso(t))
    scales = {}
    if last:
        for part in str(last[1]).split("/"):
            dep, _, st = part.partition(":")
            scales[dep] = st
    return {"at_evaluation_start": scales or "NO_READINESS_OBSERVATION_BEFORE_START",
            "observed_since": _iso(last[0]) if last else None, "first_ready": first_ready}


def initial_context(engine: dict, journal: list[dict]) -> dict[str, Any] | None:
    adv = engine["adviser"]
    init = adv.get("initialization")
    if not init:
        return None
    from . import methods

    params = methods.for_engine(adv).params()
    es, ws = r2._dt(adv["eval_start"]), r2._dt(adv["warmup_start"])
    cov = init.get("coverage") or []
    trade = next((c for c in cov if c.get("family") == "trade_bar_1m"), None)
    trade_complete = bool(trade and trade.get("expected_slots") and trade["missing"] + trade["rejected"] == 0
                          and trade["valid"] == trade["expected_slots"])
    periods = {}
    for name, (a, b) in _required_periods(es, params.pivot_age_15m, params.pivot_age_1h).items():
        inside = a >= ws and b <= es
        periods[name] = {"start": _iso(a), "end": _iso(b), "inside_initialization": inside,
                         "data": ("COVERED" if inside and trade_complete else
                                  "INSUFFICIENT_BEFORE_INITIALIZATION" if not inside else
                                  "INITIALIZATION_TRADE_COVERAGE_INCOMPLETE_UNLOCATED")}
    # latest committed record per landmark id at or before the evaluation start (publication at es included)
    latest: dict[str, dict] = {}
    for e in journal:
        if e["kind"] != "landmark":
            continue
        if r2._dt(e["clock_time"]) > es:
            break
        latest[e["record"]["landmark_id"]] = e["record"]
    by_type: dict[str, list[dict]] = defaultdict(list)
    for rec in latest.values():
        by_type[rec["landmark_type"]].append(rec)
    landmarks = {}
    for prefix, period in PERIOD_LANDMARKS:
        req = periods[period]
        for side in ("HIGH", "LOW"):
            typ = f"{prefix}_{side}"
            # latest instance = latest source period (source ids end with the period start, e.g. ``.../1w/<start>``)
            built = sorted(by_type.get(typ, []), key=lambda r: (sorted(map(str, r.get("source_ids") or [])),
                                                                r["landmark_id"]))
            if not built:
                state = ("NOT_BUILT_DATA_INSUFFICIENT" if req["data"] != "COVERED" else
                         "NOT_BUILT_WITH_COVERED_PERIOD_UNEXPLAINED_NOT_CERTIFIED")
                landmarks[typ] = {"state": state, "required_period": [req["start"], req["end"]], "ever_built": 0}
                continue
            last = built[-1]
            for_period = any(req["start"].replace("+00:00", "") in str(s) for s in last.get("source_ids") or [])
            st = last["status"]
            landmarks[typ] = {
                "state": ("BUILT_ACTIVE" if st == "ACTIVE" else f"BUILT_THEN_{st}") + ("" if for_period else
                                                                                       "_FOR_ANOTHER_PERIOD"),
                "status_reason": last.get("status_reason"), "price": last.get("price"),
                "landmark_id": last["landmark_id"], "source_ids": last.get("source_ids"),
                "covers_required_period": for_period, "required_period": [req["start"], req["end"]],
                "ever_built": len(built)}
    for hi, lo, h in PIVOTS:
        mem = periods[f"pivot_{h}_memory"]
        recs = by_type.get(hi, []) + by_type.get(lo, [])
        ext = sorted(str(r.get("extremum_time")) for r in recs if r.get("extremum_time"))
        landmarks[f"PIVOTS_{h.upper()}"] = {
            "ever_built": len(recs), "state_at_start": dict(sorted(Counter(
                f"{r['status']}" + (f":{r['status_reason']}" if r.get("status_reason") else "") for r in recs).items())),
            "active_at_start": sum(1 for r in recs if r["status"] == "ACTIVE"),
            "earliest_extremum": ext[0] if ext else None, "memory_window": [mem["start"], mem["end"]],
            "memory_window_inside_initialization": mem["inside_initialization"], "memory_window_data": mem["data"],
            "memory_completeness": "NOT_CERTIFIED",
            "state": "NEVER_BUILT" if not recs else ("BUILT" if mem["data"] == "COVERED" else
                                                    "BUILT_WITH_INSUFFICIENT_MEMORY_WINDOW")}
    return {
        "evaluation_start": _iso(es), "initialization": {k: init.get(k) for k in
                                                         ("policy", "preset_id", "start", "end", "hours", "evaluated")},
        "initialization_coverage": cov, "initialization_trade_complete": trade_complete,
        "readiness": _readiness(journal, es), "required_periods": periods, "landmarks": landmarks,
        "note": ("Facts at the evaluation start (records published at that dispatch included). 'Never built' and "
                 "'insufficient data' are kept apart from levels built and then legitimately broken, expired or "
                 "retired. Pivot memory completeness is NOT certified: formation, publication, breaking, retirement "
                 "and the per-horizon cap are not reconstructed. The initialization is never evaluated."),
    }


# ----------------------------------------------------------------------------------------------------------------------
# whole-run totals and monthly sections
# ----------------------------------------------------------------------------------------------------------------------

def _view_minutes(journal: list[dict], lo: datetime, hi: datetime, covered_to: datetime) -> Counter:
    rows: Counter = Counter()
    prev_t, prev_row = None, None
    for e in journal:
        if e["kind"] != "market_view":
            continue
        t = r2._dt(e["clock_time"])
        if prev_t is not None:
            a, b = max(prev_t, lo), min(t, hi, covered_to)
            if b > a:
                rows[prev_row] += int((b - a) / MIN)
        prev_t, prev_row = t, e["record"]["table_row"]
    if prev_t is not None:
        a, b = max(prev_t, lo), min(hi, covered_to)
        if b > a:
            rows[prev_row] += int((b - a) / MIN)
    return rows


def _samples(samples: list[dict]) -> dict[str, Any]:
    out: dict[str, Any] = {"samples": len(samples), "by_view": dict(sorted(Counter(s["view"] for s in samples).items()))}
    for h in (1, 4):
        k = f"outcome_{h}h"
        d = [s for s in samples if s["view"] in ("UP", "DOWN") and s[k] is not None]
        out[f"{h}h"] = {"directional_scored": len(d), "directional_matching_sign": sum(1 for s in d if s[k] == s["view"]),
                        "endpoint_unavailable": sum(1 for s in samples if s[k] is None)}
    return out


def _section(lo, hi, covered_to, journal, scen, ents, calls, revs, paths, samples, in_eval, variants, pending_label
             ) -> dict[str, Any]:
    def inside(rec):
        t = r2._dt(rec["env"]["published_at"])
        return lo <= t < hi and in_eval(t)

    rows = _view_minutes(journal, lo, hi, covered_to)
    minutes = int((hi - lo) / MIN)
    covered = int((min(hi, covered_to) - lo) / MIN) if covered_to > lo else 0
    unavailable = rows.get("REQUIRED_CONTEXT_UNAVAILABLE", 0)
    trans = Counter(f"{s['family']}_{s['transition']}" for s in scen if inside(s))
    # A routing: first routing record per child published in this period
    routed: dict[str, dict] = {}
    for e in ents:
        if e["family"] == "A" and e["entry_attempt_id"] not in routed and (e.get("diagnostic") or {}).get("in_D") \
                is not None and inside(e):
            routed[e["entry_attempt_id"]] = e
    route = Counter()
    for e in routed.values():
        route["RETURN_WAIT" if e["transition"] == "WAIT_OPEN" else "IMMEDIATE_ISSUED" if e["transition"] == "ISSUE"
              else "IMMEDIATE_SELECTION_REJECTED" if e["transition"] == "REJECT"
              else f"TERMINAL:{str(e['reason']).split(':')[0]}"] += 1
    d_rows = [e for e in routed.values() if e["diagnostic"].get("in_D") == "true"]
    waits = {e["entry_attempt_id"] for e in ents if e["transition"] == "WAIT_OPEN" and inside(e)}
    wait_end, ended_later, usable = Counter(), 0, 0
    for eid in waits:
        mine = [e for e in ents if e["entry_attempt_id"] == eid]
        if any(e["transition"] == "RETURN_USABLE" for e in mine):
            usable += 1
        end = next((e for e in reversed(mine) if e["transition"] in ("TERMINAL", "REJECT", "ISSUE")), None)
        if end is None:
            wait_end["OPEN_AT_LAST_COMMIT"] += 1
            continue
        wait_end[f"{end['transition']}:{str(end['reason']).split(':')[0].split(',')[0]}"
                 if end["transition"] != "ISSUE" else "ISSUE"] += 1
        if r2._dt(end["env"]["published_at"]) >= hi:
            ended_later += 1
    mine_calls = [c for c in calls if lo <= r2._dt(c["issued_at"]) < hi and in_eval(r2._dt(c["issued_at"]))]
    guidance, resolved_later, open_calls = Counter(), 0, 0
    for c in mine_calls:
        term = next((r for r in revs.get(c["call_id"], []) if r["thesis_status"] != "ONGOING"), None)
        if term is None:
            guidance["ONGOING_AT_LAST_COMMIT"] += 1
            open_calls += 1
        else:
            guidance[term["thesis_status"]] += 1
            if r2._dt(term["env"]["published_at"]) >= hi:
                resolved_later += 1
    hyp = {}
    evaluable = [c for c in mine_calls if _evaluable(c)]
    for v in VARIANTS + tuple(x for x in (variants or ()) if x not in VARIANTS):
        ps = [paths[(c["call_id"], v)] for c in mine_calls if (c["call_id"], v) in paths]
        nets = [p["price_net"] for p in ps if p.get("status") == "CLOSED" and p.get("price_net") is not None]
        exits_later = sum(1 for p in ps if (p.get("exit") or {}).get("time_end")
                          and r2._dt(p["exit"]["time_end"]) >= hi)
        tot = exact_sum(nets) if nets else Decimal(0)
        st = Counter(p.get("status") for p in ps)
        # expected pairs: evaluable calls x pinned variants; a pair without a terminal record is only counted
        expected = None if variants is None else (len(evaluable) if v in variants else 0)
        awaiting = None if variants is None else sum(1 for c in evaluable if v in variants
                                                     and (c["call_id"], v) not in paths)
        hyp[v] = {"paths": len(ps), "status": dict(sorted(st.items())),
                  "exit_class": dict(sorted(Counter(p.get("exit_class") for p in ps if p.get("status") == "CLOSED")
                                            .items())),
                  "closed_with_price_net": len(nets), "exits_after_period_end": exits_later,
                  "sum_price_net_normalized": format(tot, "f"), "sum_price_net_pct_presentation": _pct(tot),
                  "censored_or_unresolved": sum(1 for p in ps if p.get("status") in ("CENSORED", "UNRESOLVED",
                                                                                     "AMBIGUOUS")),
                  "expected_pairs": expected, "records_available": len(ps),
                  "awaiting_terminal_record": awaiting, "awaiting_meaning": pending_label if awaiting else None,
                  "by_status": {k: st.get(k, 0) for k in STATUSES},
                  "other_status": dict(sorted((str(k), n) for k, n in st.items() if k not in STATUSES)),
                  "sum_population": {"closed_with_price_net": len(nets), "records_available": len(ps),
                                     "expected_pairs": expected},
                  "economic_result_observed": bool(nets)}
    return {
        "start": _iso(lo), "end": _iso(hi),
        "coverage": {"minutes": minutes, "covered_minutes": covered, "assessable_minutes": sum(rows.values()) -
                     unavailable, "unavailable_minutes": unavailable, "view_row_minutes": dict(sorted(rows.items()))},
        "market_view_samples": _samples([s for s in samples if lo <= r2._dt(s["sample_time"]) < hi]),
        "scenario_transitions": dict(sorted(trans.items())),
        "a_confirmations": len(routed), "a_routing": dict(sorted(route.items())),
        "a_D": len(d_rows), "a_N": sum(1 for e in d_rows if e["diagnostic"].get("in_N") == "true"),
        "waits": {"opened": len(waits), "observed_usable_return": usable, "endings": dict(sorted(wait_end.items())),
                  "ended_after_period_end": ended_later},
        "calls": {"issued": len(mine_calls), "call_ids": [c["call_id"] for c in mine_calls],
                  "by_family_mode": dict(sorted(Counter(f"{c['family']}_{c.get('entry_mode', 'IMMEDIATE')}"
                                                        for c in mine_calls).items())),
                  "guidance_outcome": dict(sorted(guidance.items())), "resolved_after_period_end": resolved_later,
                  "ongoing_at_last_commit": open_calls},
        "hypothetical": hyp,
    }


def periods(*, engine: dict, journal: list[dict], records: list[dict], base: dict[str, Any],
            status: str | None = None) -> dict[str, Any] | None:
    adv = engine["adviser"]
    es, ee = r2._dt(adv["eval_start"]), r2._dt(adv["eval_end"])
    months = month_bounds(es, ee)
    if len(months) < 2:
        return None
    in_eval = lambda t: es <= t < ee  # noqa: E731
    last_t = r2._dt(journal[-1]["clock_time"]) if journal else None
    covered_to = min(ee, last_t) if last_t else es
    scen = [e["record"] for e in journal if e["kind"] == "scenario"]
    ents = [e["record"] for e in journal if e["kind"] == "entry_attempt"]
    calls = [e["record"] for e in journal if e["kind"] == "call"]
    revs: dict[str, list] = defaultdict(list)
    for e in journal:
        if e["kind"] == "call_revision":
            revs[e["record"]["call_id"]].append(e["record"])
    path_recs = [r["record"] for r in records if r["kind"] == "path"]
    paths: dict[tuple[str, str], dict] = {}
    for p in path_recs:  # one terminal record per pair; a repeated one is reported, never counted twice
        paths.setdefault((p["call_id"], p["variant"]), p)
    duplicates = len(path_recs) - len(paths)
    samples = [r["record"] for r in records if r["kind"] == "view_sample"]
    variants = pinned_variants(engine)
    pending_label = ("expected terminal record missing from a run declared completed" if status == "completed" else
                     "outcome not yet recorded at checkpoint")
    args = (covered_to, journal, scen, ents, calls, revs, paths, samples, in_eval, variants, pending_label)
    total = _section(es, ee, *args)
    sections = {m: _section(lo, hi, *args) for m, lo, hi in months}
    ids = [cid for s in sections.values() for cid in s["calls"]["call_ids"]]
    f = base.get("funnel") or {}
    checks = {
        "calls_partitioned_without_duplicates": len(ids) == len(set(ids)) and sorted(ids) ==
        sorted(total["calls"]["call_ids"]),
        "calls_equal_report_total": sum(s["calls"]["issued"] for s in sections.values()) == f.get("issued"),
        "a_confirmations_equal_report_total": sum(s["a_confirmations"] for s in sections.values())
        == f.get("a_confirmations"),
        "waits_equal_report_total": sum(s["waits"]["opened"] for s in sections.values())
        == (f.get("waiting") or {}).get("opened"),
        "minutes_sum_to_evaluation": sum(s["coverage"]["minutes"] for s in sections.values())
        == total["coverage"]["minutes"],
        "assessable_minutes_sum": sum(s["coverage"]["assessable_minutes"] for s in sections.values())
        == total["coverage"]["assessable_minutes"],
        "view_samples_sum": sum(s["market_view_samples"]["samples"] for s in sections.values())
        == total["market_view_samples"]["samples"],
    }
    hv = list(total["hypothetical"])
    for v in hv:
        checks[f"{v}_price_net_sum_exact"] = exact_sum(s["hypothetical"][v]["sum_price_net_normalized"]
                                                       for s in sections.values()) == \
            Decimal(total["hypothetical"][v]["sum_price_net_normalized"])
        checks[f"{v}_paths_sum"] = sum(s["hypothetical"][v]["paths"] for s in sections.values()) == \
            total["hypothetical"][v]["paths"]
    # every available terminal record of an evaluated call is attributed exactly once; none is repeated
    eval_ids = {c["call_id"] for c in calls if in_eval(r2._dt(c["issued_at"]))}
    checks["path_records_attributed_to_evaluated_calls"] = sum(
        total["hypothetical"][v]["records_available"] for v in hv) == sum(1 for k in paths if k[0] in eval_ids)
    checks["no_duplicate_terminal_records"] = duplicates == 0
    return {
        "attribution": ("calls -> month of issue, followed to their outcome after the month ends (never counted "
                        "twice); confirmations/scenario transitions -> month of publication; WAITs -> month opened, "
                        "with their ending wherever it falls; coverage -> minutes inside the month; view samples -> "
                        "sample time (their 1h/4h endpoint may fall in the next month)"),
        "denominators": ("each section uses its own denominator: evaluation minutes, view samples, A confirmations, "
                         "opened WAITs and issued calls are different populations"),
        "sum_meaning": SUM_MEANING, "censoring": "paths still open at the clock end are CENSORED/UNRESOLVED and kept "
                                                 "visible; tail data are never scored",
        "total": total, "months": sections,
        "reconciliation": {"scope": "ARITHMETIC_OF_AVAILABLE_RECORDS", "checks": checks,
                           "all_passed": all(checks.values())},
        "outcome_completeness": _completeness(status, variants, total, sections, duplicates, pending_label),
    }


def _completeness(status, variants, total, sections, duplicates, pending_label) -> dict[str, Any]:
    """Expected call-variant terminal records versus those available, by variant and month of issue. Separate from
    the arithmetic reconciliation; the run's actual status (not feed coverage) decides pending versus incomplete."""
    if variants is None:
        return {"run_status": status or "UNKNOWN", "state": "UNKNOWN_EVALUATOR_NOT_PINNED",
                "configured_variants": None, "duplicate_terminal_records": duplicates,
                "note": "no evaluator variants are pinned for this run, so the expected outcomes cannot be determined"}
    h = total["hypothetical"]
    by = {v: {"expected": h[v]["expected_pairs"], "available": h[v]["records_available"],
              "awaiting": h[v]["awaiting_terminal_record"],
              "awaiting_by_issue_month": {m: s["hypothetical"][v]["awaiting_terminal_record"]
                                          for m, s in sections.items()}} for v in variants}
    expected = sum(b["expected"] for b in by.values())
    awaiting = sum(b["awaiting"] for b in by.values())
    return {
        "run_status": status or "UNKNOWN", "configured_variants": list(variants),
        "evaluable_calls": max((b["expected"] for b in by.values()), default=0),
        "expected_pairs": expected, "terminal_records_available": expected - awaiting,
        "awaiting_terminal_record": awaiting, "duplicate_terminal_records": duplicates,
        "state": "COMPLETE" if awaiting == 0 else INCOMPLETE if status == "completed" else PENDING,
        "awaiting_meaning": pending_label if awaiting else None, "by_variant": by,
        "note": ("expected pairs = evaluable calls issued in the evaluation window x pinned evaluator variants. A pair "
                 "without a terminal record has no inferred entry, outcome, economic result or censoring. This is "
                 "outcome completeness, separate from the arithmetic reconciliation of the available records; for a "
                 "run declared completed a missing record makes this report INCOMPLETE, while the run's saved status "
                 "and assurance are unchanged."),
    }


# ----------------------------------------------------------------------------------------------------------------------
# markdown
# ----------------------------------------------------------------------------------------------------------------------

def render_markdown(a: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lp = a.get("launch_pins")
    if lp:
        p = lp["costs"].get("PRIMARY") or {}
        lines += ["", "### Launch pins",
                  f"- Method {lp['method']} `{lp['model']}` / `{lp['rules_version']}` · rules `{str(lp['rules_sha256'])[:12]}`"
                  f" · register `{str(lp['register_sha256'])[:12]}` · implementation {lp['implementation']} · identity "
                  f"`{str(lp['identity_sha256'])[:12]}` · build `{lp['build']}`",
                  f"- Profile `{str(lp['capability_profile_sha256'])[:12]}` · clock {lp['clock_policy']} · evaluator "
                  f"{lp['evaluator_format']} `{str(lp['evaluator_sha256'])[:12]}` · PRIMARY entry delay "
                  f"{lp['primary_entry_delay_seconds']} s · fee/leg {p.get('fee_per_leg')} · allowance/leg "
                  f"{p.get('allowance_per_leg')} · funding {p.get('funding')}",
                  f"- Pack `{lp['pack_id']}` · initialization from {lp['windows']['initialization_start']} (not evaluated)"
                  f" · evaluation {lp['windows']['evaluation'][0]} → {lp['windows']['evaluation'][1]} · tail end "
                  f"{lp['windows']['tail_end']}"]
    ic = a.get("initial_context")
    if ic:
        i = ic["initialization"]
        lines += ["", "### Context at the evaluation start (initialization is not evaluated)",
                  f"- Initialization {i['start']} → {i['end']} ({i['hours']} h, {i['policy']}) · trade coverage "
                  + ("complete" if ic["initialization_trade_complete"] else "INCOMPLETE")
                  + " · " + "; ".join(f"{c['family']} {c['valid']}/{c['expected_slots']}"
                                      for c in ic["initialization_coverage"] if c.get("expected_slots")),
                  f"- Readiness at start: {ic['readiness']['at_evaluation_start']}"]
        for k, v in ic["required_periods"].items():
            lines.append(f"  - {k} [{v['start']}, {v['end']}): {v['data']}")
        for k, v in ic["landmarks"].items():
            if k.startswith("PIVOTS_"):
                lines.append(f"  - {k}: {v['state']} · ever built {v['ever_built']} · active {v['active_at_start']} · "
                             f"memory window {v['memory_window_data']} · completeness {v['memory_completeness']}")
            else:
                lines.append(f"  - {k}: {v['state']}" + (f" ({v['status_reason']})" if v.get("status_reason") else ""))
        lines.append(f"- {ic['note']}")
    pr = a.get("periods")
    if pr:
        lines += ["", "### Continuous run: total and monthly sections (one run, no monthly reset)",
                  f"- Attribution: {pr['attribution']}", f"- {pr['denominators']}",
                  f"- Hypothetical sums: {pr['sum_meaning']}", f"- {pr['censoring']}",
                  "| Period | Assessable min | A conf. | WAIT | Calls | Resolved later | PRIMARY closed | PRIMARY price-net |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        rows = [("TOTAL", pr["total"])] + list(pr["months"].items())
        for name, s in rows:
            h = s["hypothetical"]["PRIMARY"]
            lines.append(f"| {name} | {s['coverage']['assessable_minutes']}/{s['coverage']['minutes']} | "
                         f"{s['a_confirmations']} | {s['waits']['opened']} | {s['calls']['issued']} | "
                         f"{s['calls']['resolved_after_period_end']} | {h['closed_with_price_net']} | "
                         f"{_sum_text(h)} |")
        oc = pr.get("outcome_completeness")
        pending = "not yet recorded" if not oc or oc["state"] != INCOMPLETE else "missing (run completed)"
        lines += ["", "Hypothetical outcomes per variant (calls by month of issue; expected = evaluable calls for a "
                      f"pinned variant; '{pending}' = expected pair without a terminal record, nothing inferred for it)",
                  f"| Period | Variant | Expected | Records | {pending.capitalize()} | CLOSED | with price-net | "
                  "NO_ENTRY | CENSORED | UNRESOLVED | AMBIGUOUS | Exit after period | Price-net sum (population) |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for name, s in rows:
            for v, h in s["hypothetical"].items():
                b = h.get("by_status") or {}
                exp = h.get("expected_pairs")
                lines.append(f"| {name} | {v} | {'—' if exp is None else exp} | {h['paths']} | "
                             f"{'—' if h.get('awaiting_terminal_record') is None else h['awaiting_terminal_record']} | "
                             + " | ".join(str(b.get(k, 0)) for k in STATUSES[:1]) + f" | {h['closed_with_price_net']} | "
                             + " | ".join(str(b.get(k, 0)) for k in STATUSES[1:])
                             + f" | {h['exits_after_period_end']} | {_sum_text(h)}"
                             + (f"; other states {h['other_status']}" if h.get("other_status") else "") + " |")
        for name, s in rows:
            cv, sm = s["coverage"], s["market_view_samples"]
            lines.append(f"- {name} MarketView: covered {cv['covered_minutes']}/{cv['minutes']} min · assessable "
                         f"{cv['assessable_minutes']} · unavailable {cv['unavailable_minutes']} · rows "
                         + (", ".join(f"{k} {n}" for k, n in cv["view_row_minutes"].items()) or "none"))
            lines.append(f"- {name} samples: {sm['samples']} ("
                         + (", ".join(f"{k} {n}" for k, n in sm["by_view"].items()) or "none") + ") · "
                         + " · ".join(f"{h} directional {sm[h]['directional_matching_sign']}/"
                                      f"{sm[h]['directional_scored']} matching sign, endpoint unavailable "
                                      f"{sm[h]['endpoint_unavailable']}" for h in ("1h", "4h")))
            lines.append(f"- {name} scenarios: "
                         + (", ".join(f"{k} {n}" for k, n in s["scenario_transitions"].items()) or "none")
                         + f" · A confirmations {s['a_confirmations']} · D {s['a_D']} / N {s['a_N']}")
            lines.append(f"- {name} calls: guidance {s['calls']['guidance_outcome'] or '{}'} · routing "
                         f"{s['a_routing'] or '{}'} · WAIT endings {s['waits']['endings'] or '{}'}")
        rc = pr["reconciliation"]
        lines.append(f"- Reconciliation total vs months: {'PASS' if rc['all_passed'] else 'FAIL'} (arithmetic of the "
                     "available records only; it is not outcome completeness)"
                     + ("" if rc["all_passed"] else " — " + ", ".join(k for k, ok in rc["checks"].items() if not ok)))
        if oc:
            lines.append(_completeness_line(oc))
    return lines


def _sum_text(h: dict) -> str:
    """A sum is shown with its population; without a closed outcome with price-net no economic result is shown."""
    n = h["closed_with_price_net"]
    if not n:
        return "none observed (0 closed)"
    pct = h["sum_price_net_pct_presentation"]
    return f"{'' if pct.startswith('-') else '+'}{pct}% over {n} closed"


def _completeness_line(oc: dict) -> str:
    st = oc["state"]
    if st == "UNKNOWN_EVALUATOR_NOT_PINNED":
        return f"- Outcome completeness: UNKNOWN (no evaluator pinned) · run status {oc['run_status']}"
    head = (f"- Outcome completeness: {st.replace('_', ' ')} — {oc['awaiting_terminal_record']} of "
            f"{oc['expected_pairs']} expected call–variant terminal records "
            if st != "COMPLETE" else f"- Outcome completeness: COMPLETE — {oc['terminal_records_available']}/"
            f"{oc['expected_pairs']} expected call–variant terminal records available")
    if st == "COMPLETE":
        return head + f" · run status {oc['run_status']}" + (
            f" · {oc['duplicate_terminal_records']} repeated record(s) not counted" if oc["duplicate_terminal_records"]
            else "")
    detail = "; ".join(
        f"{v} {b['awaiting']} (" + ", ".join(f"{m} {n}" for m, n in b["awaiting_by_issue_month"].items() if n) + ")"
        for v, b in oc["by_variant"].items() if b["awaiting"])
    if st == INCOMPLETE:
        return (f"- **REPORT INCOMPLETE** — the run is declared COMPLETED but {oc['awaiting_terminal_record']} of "
                f"{oc['expected_pairs']} expected call–variant terminal records are missing: {detail}. Nothing is "
                "inferred for them; the run's saved status and assurance are unchanged.")
    return (head + f"have no terminal record yet (run status {oc['run_status']}): outcome not yet recorded at "
            f"checkpoint — {detail}. No entry, outcome, economic result or censoring is inferred for them.")
