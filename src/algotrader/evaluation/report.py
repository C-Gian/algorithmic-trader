"""Market replay (observation-only) evaluation report: compact Markdown for chat + structured JSON.

Built from persisted state only: the evaluation row (corpus facts captured at launch), the
observation replay row (status, phase history, health, assurance, counters) and - when one
exists - its terminal manifest.

* Terminal runs: the same terminal state always yields the same bytes (no capture time).
* Non-terminal runs, or terminal runs without a manifest: a **diagnostic snapshot** with its
  capture time, explicitly INCOMPLETE; it never infers validation from a full replay cursor.

No trading field is ever reported as a number: while no professional adviser exists,
every call/MarketView/outcome metric is ``null`` with status ``UNAVAILABLE`` and a reason.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .. import version

REPORT_KIND = "OBSERVATION_ONLY_EVALUATION"
REPORT_FORMAT = "algotrader.evaluation-report.v0"  # operational report format (not a domain contract)
RUN_TYPE_LABEL = "Market replay — data and engine check (observation only)"
NOT_CONNECTED = ("Professional adviser not connected yet. This run validates data/replay/product workflow only; "
                 "trade-call metrics are unavailable.")
UNAVAILABLE_REASON = "no professional adviser connected yet"
ADVISER_NOTICE = ("Adviser evaluation: the integrated MP-001 adviser replayed causally over the prepared pack, with a "
                  "SEPARATE normalized hypothetical evaluator (one abstract unit, declared delay/costs). It never "
                  "places orders or chooses size/leverage; outcomes are hypothetical, not fills or account results.")
ADVISER_KIND = "ADVISER_EVALUATION"

UNAVAILABLE_METRICS = (
    ("market_view_metrics", "MarketView metrics"),
    ("call_count", "Call count"),
    ("calls_per_week", "Calls per evaluated week"),
    ("entry_window_durations", "Entry-window durations"),
    ("longest_no_call_interval", "Longest no-call interval"),
    ("outcomes", "Win/loss/expired/unresolved outcomes"),
    ("normalized_gross_net_results", "Normalized gross/net results"),
    ("candidate_funnel", "Candidate funnel / rejection reasons"),
    ("baseline_comparison", "Baseline comparison"),
)


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, datetime) else str(v)


def _mb(n: int | None) -> str:
    return "—" if n is None else f"{n / 1_000_000:.1f} MB ({n:,} bytes)"


def build_report(ev: dict[str, Any], replay: dict[str, Any], manifest: dict[str, Any] | None,
                 op: dict[str, Any] | None = None, diagnostic: dict[str, Any] | None = None,
                 now: datetime | None = None, adviser: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = replay["config"]
    corpus = ev["corpus"]
    status = replay["status"]
    terminal = status in ("completed", "cancelled", "failed")
    snapshot = not terminal or manifest is None
    applied = manifest["applied_events"] if manifest else (replay.get("applied") or 0)
    total = replay["total_events"]
    complete = status == "completed" and total is not None and applied == total and manifest is not None
    started, finished = replay["started_at"], replay["finished_at"]
    elapsed = (finished - started).total_seconds() if started and finished else None
    validation = manifest["validation"] if manifest else None
    checks = validation["checks"] if validation else []
    validation_ran = bool(checks) and not (len(checks) == 1 and checks[0]["name"] == "source_loadable")
    outcome = (validation.get("outcome") or ("passed" if validation["passed"] else "failed")) if validation else None
    source = (cfg or {}).get("source") or {}
    availability = (cfg or {}).get("availability_policy")
    recovery = list(replay["recovery_log"] or [])
    control = list(replay["control_log"] or [])
    phase = (op or {}).get("phase") or replay.get("phase")

    warnings: list[str] = [*source.get("warnings", []), *source.get("exclusions", [])]
    if corpus.get("quality_status") not in (None, "clean") and not any(
            w.startswith("dataset quality") for w in warnings):  # the source already states it
        warnings.append(f"dataset quality {str(corpus['quality_status']).upper()}: missing/rejected slots were "
                        "delivered as quality events and never filled")
    warnings.append("MODELED availability: historical bar/funding knowledge times follow the zero-extra-delay "
                    "convention; they are not measured publication or receipt times")

    total_text = f"{total:,}" if total is not None else "PENDING"
    if not terminal:
        verdict = "IN_PROGRESS_SNAPSHOT"
        text = (f"Diagnostic snapshot while {status.upper()} in phase {phase or '—'}: {applied:,} of {total_text} feed "
                "events committed. This is not a result; terminal validation has not completed.")
    elif complete and outcome == "passed" and adviser is not None:
        verdict = "ADVISER_EVALUATION_COMPLETED"
        text = ("The adviser evaluation ran end to end over the whole prepared pack and its runtime integrity checks "
                "(bounded terminal reconciliation incl. adviser journal/evaluation commitments) passed. Integrity is "
                "not profitability or forecast quality: the adviser section reports calls, entry windows, the "
                "candidate funnel and hypothetical outcomes for Director diagnosis.")
    elif complete and outcome == "passed":
        verdict = "WORKFLOW_VALID"
        text = ("Corpus data, causal feed and durable observation replay worked end to end: every feed event of the "
                "prepared chunk was applied and the run's own runtime integrity checks (bounded terminal "
                "reconciliation) passed. No reference re-execution was performed in this run (the optional Deep "
                "validation provides one: a separate execution path over the canonical feed cache with the "
                "shared reducer, not a wholly independent method or a source audit). This says nothing about "
                "trading performance; no adviser was evaluated.")
    elif status == "completed":
        verdict = "OPERATIONAL_FAILURE"
        text = ("The replay reached the end of the feed but validation FAILED; the data/replay path needs diagnosis."
                if manifest else "The run is marked completed but no terminal manifest is recorded; needs diagnosis.")
    elif status == "cancelled":
        verdict = "INCOMPLETE_CANCELLED"
        if outcome == "incomplete" and total is not None and applied == total:
            text = (f"Cancelled by the Owner during validation: all {total:,} feed events were replayed, but "
                    "validation did not finish (assurance INCOMPLETE). This is not a successful evaluation.")
        else:
            text = (f"Cancelled by the Owner after {applied:,} of {total_text} feed events. Coverage is incomplete; "
                    "this is not a successful evaluation.")
    else:
        verdict = "OPERATIONAL_FAILURE"
        text = (f"The replay failed after {applied:,} of {total_text} feed events: {replay.get('error') or 'see error'}. "
                "Coverage is incomplete; this is not a successful evaluation.")

    stopped = None
    if terminal and not complete:
        stopped = {
            "applied_events": applied,
            "total_events": total,
            "information_time": manifest["final_as_of"] if manifest else _iso(replay.get("info_time")),
            "last_event_id": replay.get("last_event_id"),
            "reason": replay.get("error") or ("cancelled by the Owner" if status == "cancelled" else None),
        }

    operation = None
    if op is not None:
        operation = {
            "phase": op["phase"], "health": op["health"], "health_detail": op["health_detail"] if not terminal else None,
            "assurance": op["assurance"], "generation": op["generation"],
            "active_seconds_total": op["timeline"]["active_seconds_total"],
            "waiting_seconds_total": op["timeline"]["waiting_seconds_total"],
            "unmeasured_spans": op["timeline"]["unmeasured_spans"],
            "phases": [{k: x[k] for k in ("phase", "label", "state", "active_seconds", "wall_seconds", "spans",
                                          "interrupted_spans", "waiting_seconds", "unmeasured_spans")}
                       for x in op["timeline"]["phases"] if x["spans"] or x["state"] == "current"],
            "counters": op["metrics"],
            "environment": ((replay.get("supervisor") or {}).get("environment")),
        }
    caps = {
        "professional_adviser": {"status": "NOT_IMPLEMENTED", "reason": UNAVAILABLE_REASON},
        **{key: {"label": label, "status": "UNAVAILABLE", "value": None, "reason": UNAVAILABLE_REASON}
           for key, label in UNAVAILABLE_METRICS},
    }
    if adviser is not None:
        model = (adviser.get("identity") or {}).get("model") or "btc.context-action.v0.2"
        caps = {"professional_adviser": {"status": "CONNECTED", "reason": (
                    "MP-002 " if model.endswith("v0.3") else "MP-001 ") + f"{model} adviser"},
                **{key: {"label": label, "status": "REPORTED", "value": None, "reason": "see the adviser section"}
                   for key, label in UNAVAILABLE_METRICS}}
    return {
        "report_kind": ADVISER_KIND if adviser is not None else REPORT_KIND,
        "report_format": REPORT_FORMAT,
        "run_type": "Adviser evaluation (hypothetical outcomes, no orders)" if adviser is not None else RUN_TYPE_LABEL,
        "notice": ADVISER_NOTICE if adviser is not None else NOT_CONNECTED,
        **({"adviser": adviser} if adviser is not None else {}),
        "evaluation_id": ev["evaluation_id"],
        "preset": ev["preset"],
        "replay_id": replay["replay_id"],
        "status": status,
        "snapshot": snapshot,
        "captured_at": now.isoformat() if (snapshot and now is not None and not terminal) else None,
        "completion": "COMPLETE" if complete else "INCOMPLETE",
        "corpus": corpus,
        "source": {
            "source": "okx", "base_url": corpus.get("base_url"), "inst_id": source.get("inst_id", "PENDING"),
            "index_id": source.get("index_id", "PENDING"), "dataset_id": source.get("source_id", ev["dataset_id"]),
            "schema": source.get("source_schema", "PENDING"),
            "verification": (cfg or {}).get("verification") or "PENDING (not yet verified by the worker)",
        },
        "coverage": {
            "requested": {"start": corpus["start"], "end": corpus["end"]},
            "channels": [{"family": c["channel"]["family"], "covered_from": c["covered_from"],
                          "covered_until": c["covered_until"]} for c in source.get("coverage", [])],
            "final_information_time": manifest["final_as_of"] if manifest else None,
            "committed_information_time": _iso(replay.get("info_time")),
            "applied_events": applied,
            "total_events": total,
            "fraction": (applied / total) if total else None,
        },
        "quality_status": corpus.get("quality_status"),
        "availability": ({"basis": availability["basis"], "policy_id": availability["policy_id"],
                          "measured": availability["measured"], "label": cfg["availability_label"]}
                         if availability else "PENDING"),
        "feed": ({"content_identity": cfg["feed"]["content_identity"],
                  "ordered_event_hash": cfg["feed"]["ordered_event_hash"], "event_count": cfg["feed"]["event_count"],
                  "event_counts": cfg["feed"]["event_counts"], "applied_events": applied}
                 if cfg else {"content_identity": "PENDING", "ordered_event_hash": "PENDING", "event_count": None,
                              "event_counts": {}, "applied_events": applied}),
        "runtime": {
            "created_at": _iso(replay["created_at"]), "started_at": _iso(started), "finished_at": _iso(finished),
            "elapsed_seconds": elapsed,
            "throughput_events_per_second": (applied / elapsed) if elapsed else None,
            "final_pacing_events_per_second": replay["speed"],
            "pacing_note": "0 = max pacing; pacing is operational only and never changes state",
            "attempts": replay["attempt"], "max_attempts": replay["max_attempts"],
            "recoveries": len(recovery), "recovery_log": recovery,
            "control_commands": [c.get("command") for c in control],
        },
        "operation": operation,
        "validation": {"ran": validation_ran, "passed": validation["passed"] if validation else None,
                       "outcome": outcome, "checks": checks,
                       "validator": (validation or {}).get("validator"),
                       "scope": (validation or {}).get("scope")},
        "manifest_check": (diagnostic or {}).get("manifest"),
        "stopped_at": stopped,
        "warnings": warnings,
        "capabilities": caps,
        "conclusion": {"verdict": verdict, "text": text},
        "next_diagnostic": (("Copy this report to the Director: diagnose calls/coverage/funnel before any change; "
                             "no parameter search.") if complete and adviser is not None else
                            ("Adviser evaluation pending: rerun this same prepared chunk once the professional "
                             "adviser is connected; call/outcome sections will then be reported.")
                            if complete else (diagnostic or {}).get("next_diagnostic")
                            or "Copy this report to the Director for diagnosis."),
        "code_version": (cfg or {}).get("code_version") or (replay.get("launch") or {}).get("code_version"),
        "temporal": (diagnostic or {}).get("temporal"),
        "pack": pack_section(corpus.get("pack"), applied, total, status, adviser is not None),
    }


def pack_section(p: dict[str, Any] | None, applied: int, total: int | None, status: str,
                 adviser: bool = False) -> dict[str, Any] | None:
    """Evaluation-pack facts (R3): identities, windows, per-family/window coverage, capabilities and limits.
    Full feed consumption and per-minute source coverage are reported as separate facts."""
    if not p:
        return None
    cov = p["coverage"]
    bars = [c for c in cov if c.get("expected_slots")]
    return {
        "pack_id": p["pack_id"], "status": p["status"], "acknowledged_limitations": p.get("acknowledged_limitations"),
        "preset_id": p["preset"]["preset_id"], "preset_sha256": p["preset_sha256"], "method": p["method"],
        "rules_version": p["rules_version"], "register_sha256": p["register_sha256"],
        "capability_profile_sha256": p["capability_profile_sha256"], "capability_profile": p["capability_profile"],
        "windows": p["windows"], "evidence_classes": p["evidence_classes"], "boundaries": p["boundaries"],
        "clock_end": p["clock_end"], "tail_end": p["tail_end"],
        "feed_consumed": ("entirely" if status == "completed" and total is not None and applied == total
                          else f"{applied}/{total if total is not None else 'PENDING'}"),
        "source_coverage": {"expected_bar_slots": sum(c["expected_slots"] for c in bars),
                            "missing_or_rejected": sum(c["missing"] + c["rejected"] for c in bars)},
        "coverage": cov, "capabilities": p["capabilities"], "limitations": p["limitations"],
        "sources": p["sources"], "overlap": p["overlap"], "instrument": p["instrument"],
        "input_readiness_preview": p["input_readiness_preview"], "storage": p["storage"],
        "scoring_note": ("warmup and tail are never scored; only calls issued inside the evaluation window are scored "
                         "(hypothetical evaluator)" if adviser else
                         "warmup and tail are never scored; no adviser exists, so nothing is scored in this run"),
        **({"adviser_run": True} if adviser else {}),
    }


def render_markdown(r: dict[str, Any]) -> str:
    c, cov, rt, st = r["corpus"], r["coverage"], r["runtime"], r["corpus"].get("storage") or {}
    v = r["validation"]
    vtext = ("not run" if not v["ran"] else "INCOMPLETE" if v.get("outcome") == "incomplete"
             else "PASS" if v["passed"] else "FAIL")
    npass = sum(1 for x in v["checks"] if x["passed"])
    acq = c.get("acquisition") or {}
    total = f"{cov['total_events']:,}" if cov["total_events"] is not None else "PENDING"
    op = r.get("operation") or {}
    head = "Market replay evaluation report" if not r.get("snapshot") else \
        "Market replay evaluation — DIAGNOSTIC SNAPSHOT (incomplete)"
    lines = [
        f"# {head}",
        "",
        f"**{r['report_kind']}** · evaluation `{r['evaluation_id']}` · replay `{r['replay_id']}`"
        + (f" · captured {r['captured_at']}" if r.get("captured_at") else ""),
        f"**Status:** {r['status'].upper()}" + ((f" · phase **{op.get('phase')}** · health **{op.get('health')}**"
                                                if r.get("snapshot") else
                                                f" · finished (last phase {op.get('phase') or '—'} closed)")
                                               if op else "")
        + f" · coverage **{r['completion']}** ({cov['applied_events']:,}/{total} feed events) · validation **{vtext}**",
        "",
        f"> {r['notice']}",
        "",
        "## Data",
        f"- Preset: {r['preset']}",
        (f"- Evaluation preset: `{c['chunk_id']}` ({c.get('chunk_label')}), presets `{c['plan_id']}` "
         f"v{c.get('plan_version')}" if c.get("pack") else
         f"- Corpus chunk: `{c['chunk_id']}` ({c.get('chunk_label')}), plan `{c['plan_id']}` v{c.get('plan_version')}"),
        (f"- Pack: `{c['dataset_id']}` · manifest sha256 `{str(c.get('manifest_sha256'))[:16]}…` · "
         f"source quality {str(r['quality_status']).upper()}" if c.get("pack") else
         f"- Dataset: `{c['dataset_id']}` · manifest sha256 `{str(c.get('manifest_sha256'))[:16]}…` · "
         f"quality {str(r['quality_status']).upper()}"),
        f"- Source: OKX public REST {r['source']['base_url']} · {r['source']['inst_id']} "
        f"(index {r['source']['index_id']})",
        f"- Requested: {cov['requested']['start']} → {cov['requested']['end']}",
        f"- Final information time: {cov['final_information_time'] or '—'}",
        (f"- Availability: {r['availability']['basis']} (`{r['availability']['policy_id']}`), measured="
         f"{str(r['availability']['measured']).lower()}" if isinstance(r["availability"], dict)
         else "- Availability: PENDING (fixed by the worker-owned preparation)"),
        f"- Storage: {_mb(st.get('total_bytes'))} total · raw {_mb(st.get('raw_bytes'))} · parquet "
        f"{_mb(st.get('parquet_bytes'))} · {st.get('file_count', '—')} files · {st.get('raw_page_count', '—')} pages",
    ]
    fams = st.get("families") or []
    if fams:
        lines.append("- Rows: " + " · ".join(
            f"{f['family']} {f['rows']:,}" + (f"/{f['expected_rows']:,}" if f.get("expected_rows") else "")
            for f in fams))
    if acq:
        lines.append(f"- Preparation: {acq.get('outcome')} · job `{acq.get('job_id')}` · "
                     f"{acq.get('elapsed_seconds') and round(acq['elapsed_seconds'], 1)} s")
    fc = r["feed"]["event_count"]
    lines += [
        "",
        "## Run",
        f"- Feed: {(f'{fc:,}' if fc is not None else 'PENDING')} events "
        f"({', '.join(f'{k} {n:,}' for k, n in sorted(r['feed']['event_counts'].items())) or 'identity pending'}); "
        f"applied {r['feed']['applied_events']:,}",
        f"- Runtime: elapsed {rt['elapsed_seconds'] and round(rt['elapsed_seconds'], 1)} s · throughput "
        f"{rt['throughput_events_per_second'] and round(rt['throughput_events_per_second'], 1)} events/s · "
        f"attempts {rt['attempts']}/{rt['max_attempts']} · recoveries {rt['recoveries']}",
        f"- Validation: {vtext} ({npass}/{len(v['checks'])} checks)"
        + (f" · validator {v.get('validator')}" + (" — bounded stream reconciliation, not a full reference "
                                                    "re-execution" if v.get("validator") == "observe.stream-reconciliation"
                                                    else "") if v.get("validator") else ""),
    ]
    # coverage/identity checks the Owner compares, and every failed check, with their recorded details
    lines += [f"  - {'PASS' if x['passed'] else 'FAIL'} `{x['name']}`: {x['detail']}" for x in v["checks"]
              if not x["passed"] or x["name"] in ("cache_receipt_and_pin", "completed_consumed_entire_feed")]
    if r["stopped_at"]:
        s = r["stopped_at"]
        lines.append(f"- Stopped at: {s['applied_events']:,}/{s['total_events']:,} events · information time "
                     f"{s['information_time']} · reason: {s['reason'] or '—'}")
    for x in rt["recovery_log"]:
        lines.append(f"- Recovery: attempt {x.get('attempt')} · {x.get('event')} — {x.get('detail')}")
    if op:
        a = op.get("assurance") or {}
        lines.append(f"- Assurance: {str(a.get('state')).upper()}"
                     + (f" · {a.get('validator')} v{a.get('validator_version')}" if a.get("validator") else "")
                     + f" · fencing generation {op.get('generation')}")
        if op.get("health_detail"):
            lines.append(f"- Health: {op['health']} — {op['health_detail']}")
        lines.append(f"- Phases (measured active time; total {op['active_seconds_total']:.1f} s, declared waits "
                     f"{op['waiting_seconds_total']:.1f} s"
                     + (f"; {op['unmeasured_spans']} unmeasured span(s): active time incomplete" if op["unmeasured_spans"]
                        else "") + "):")
        for x in op["phases"]:
            lines.append(f"  - {x['label']}: {x['active_seconds']:.1f} s active · {x['wall_seconds']:.1f} s wall"
                         + (f" · {x['interrupted_spans']} interrupted" if x["interrupted_spans"] else "")
                         + (f" · {x['unmeasured_spans']} unmeasured" if x["unmeasured_spans"] else "")
                         + (" · CURRENT" if x["state"] == "current" else ""))
        for gen, cnt in sorted((op.get("counters") or {}).items()):
            keys = ("events_applied", "snapshots_built", "transactions_committed", "delivery_rows_written",
                    "prefix_restore_events", "validation_deliveries_rederived", "output_bytes", "cpu_seconds",
                    "max_rss_bytes")
            lines.append(f"- Counters g{gen}: " + " · ".join(f"{k} {cnt.get(k)}" for k in keys if k in cnt))
    mc = r.get("manifest_check")
    if mc:
        lines.append("- Terminal manifest: " + ("not recorded" if not mc.get("claimed") else
                     f"{mc.get('artifact_dir')} · file present {mc.get('manifest_file_present')}"))
    pk = r.get("pack")
    if pk:
        w = pk["windows"]
        lines += ["", "## Evaluation pack" if pk.get("adviser_run") else "## Evaluation pack (observation only; no adviser)",
                  f"- Pack `{pk['pack_id']}` · status **{pk['status']}**"
                  + (" · limitations acknowledged for this inspection run" if pk.get("acknowledged_limitations")
                     else ""),
                  f"- Preset `{pk['preset_id']}` ({pk['evidence_classes']['label']}) · method {pk['method']} / "
                  f"{pk['rules_version']} (register `{pk['register_sha256'][:12]}`, input requirements only) · "
                  f"profile `{pk['capability_profile_sha256'][:12]}`",
                  f"- Warmup {w['warmup']['start']} → {w['warmup']['end']} (unscored) · evaluation "
                  f"{w['evaluation']['start']} → {w['evaluation']['end']} · tail {w['tail']['start']} → "
                  f"{w['tail']['end']} (unscored) · engine clock end {pk['clock_end']}",
                  f"- Feed consumed: {pk['feed_consumed']} · source coverage (separate fact): "
                  f"{pk['source_coverage']['missing_or_rejected']} missing/rejected of "
                  f"{pk['source_coverage']['expected_bar_slots']} expected bar slots"]
        for c in pk["coverage"]:
            if c["expected_slots"] is not None:
                lines.append(f"  - {c['family']} {c['window']}: {c['valid']}/{c['expected_slots']} usable · missing "
                             f"{c['missing']} · rejected {c['rejected']}")
            else:
                lines.append(f"  - {c['family']} {c['window']}: {c['valid']} settlement row(s) observed "
                             "(not a completeness proof)")
        for x in pk["capabilities"]:
            lines.append(f"  - capability {x['capability']}: {x['status']}")
        lines += [f"- Limitation: {x}" for x in pk["limitations"]]
        lines.append(f"- {pk['input_readiness_preview']['label']}: trade 15m "
                     f"{pk['input_readiness_preview']['trade_15m_contiguous_complete']}/"
                     f"{pk['input_readiness_preview']['trade_15m_required_by_mp001']}, 1h "
                     f"{pk['input_readiness_preview']['trade_1h_contiguous_complete']}/"
                     f"{pk['input_readiness_preview']['trade_1h_required_by_mp001']} contiguous complete bars before "
                     "the evaluation start")
        lines.append("- Sources: " + "; ".join(f"{s['dataset_id']} [{s['start']}, {s['end']})"
                                               for s in pk["sources"]))
        lines.append(f"- {pk['scoring_note']}")
    t = r.get("temporal")
    if t:
        c = t.get("committed") or {}
        lines += ["", "## Temporal substrate (temporal substrate only; no adviser)",
                  f"- {t['contract']} · profile {t['profile_id']} · clock policy {t['clock_policy']} · seal policy "
                  f"{t['seal_policy']} · finite clock end {t['clock_end']}",
                  f"- Committed clock {c.get('clock_time') or '—'} · admitted cursor {c.get('admitted_cursor')} · "
                  f"dispatches {c.get('dispatch_seq')} · late-excluded {(c.get('counters') or {}).get('late_excluded')}"
                  " (the clock-end finish is in the temporal.json artifact and the temporal validation checks)"]
        warm = [x for x in t["readiness"] if x["status"] != "READY"]
        lines.append("- Demonstration readiness: " + (", ".join(f"{x['dependency']} {x['status']}" for x in warm)
                                                      if warm else "all READY"))
        lines.append(f"- {t['readiness_note']}")
    if r.get("adviser"):
        if r["adviser"].get("pending"):
            lines += ["", "## Adviser evaluation", f"- PENDING: {r['adviser']['text']}"]
        else:
            if r["adviser"].get("report_version") == "adviser.report.v3":
                from ..adviser.report3 import render_markdown as adviser_md
            else:
                from ..adviser.report import render_markdown as adviser_md

            lines += adviser_md(r["adviser"])
    else:
        lines += [
            "",
            "## Adviser capabilities",
            "| Capability | Status |",
            "|---|---|",
            f"| Professional adviser | {r['capabilities']['professional_adviser']['status']} |",
        ]
        for key, label in UNAVAILABLE_METRICS:
            lines.append(f"| {label} | {r['capabilities'][key]['status']} |")
        lines.append(f"Reason: {UNAVAILABLE_REASON}.")
    lines += [
        "",
        "## Conclusion",
        f"**{r['conclusion']['verdict']}** — {r['conclusion']['text']}",
        "",
        f"Next diagnostic: {r['next_diagnostic']}",
    ]
    if r["warnings"]:
        lines += ["", "## Warnings / limitations"] + [f"- {w}" for w in r["warnings"]]
    lines += ["", f"_Report format {r['report_format']} · code version {version.describe(r['code_version'])}_", ""]
    return "\n".join(lines)


def render_json(r: dict[str, Any]) -> str:
    return json.dumps(r, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
