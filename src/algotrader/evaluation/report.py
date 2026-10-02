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

REPORT_KIND = "OBSERVATION_ONLY_EVALUATION"
REPORT_FORMAT = "algotrader.evaluation-report.v0"  # operational report format (not a domain contract)
RUN_TYPE_LABEL = "Market replay — data and engine check (observation only)"
NOT_CONNECTED = ("Professional adviser not connected yet. This run validates data/replay/product workflow only; "
                 "trade-call metrics are unavailable.")
UNAVAILABLE_REASON = "no professional adviser connected yet"

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
                 now: datetime | None = None) -> dict[str, Any]:
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
    if corpus.get("quality_status") not in (None, "clean"):
        warnings.append(f"dataset quality {str(corpus['quality_status']).upper()}: missing/rejected slots were "
                        "delivered as quality events and never filled")
    warnings.append("MODELED availability: historical bar/funding knowledge times follow the zero-extra-delay "
                    "convention; they are not measured publication or receipt times")

    total_text = f"{total:,}" if total is not None else "PENDING"
    if not terminal:
        verdict = "IN_PROGRESS_SNAPSHOT"
        text = (f"Diagnostic snapshot while {status.upper()} in phase {phase or '—'}: {applied:,} of {total_text} feed "
                "events committed. This is not a result; terminal validation has not completed.")
    elif complete and outcome == "passed":
        verdict = "WORKFLOW_VALID"
        text = ("Corpus data, causal feed and durable observation replay worked end to end: every feed event of the "
                "prepared chunk was applied and independent validation passed. This says nothing about trading "
                "performance; no adviser was evaluated.")
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
    return {
        "report_kind": REPORT_KIND,
        "report_format": REPORT_FORMAT,
        "run_type": RUN_TYPE_LABEL,
        "notice": NOT_CONNECTED,
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
        "capabilities": {
            "professional_adviser": {"status": "NOT_IMPLEMENTED", "reason": UNAVAILABLE_REASON},
            **{key: {"label": label, "status": "UNAVAILABLE", "value": None, "reason": UNAVAILABLE_REASON}
               for key, label in UNAVAILABLE_METRICS},
        },
        "conclusion": {"verdict": verdict, "text": text},
        "next_diagnostic": (("Adviser evaluation pending: rerun this same prepared chunk once the professional "
                             "adviser is connected; call/outcome sections will then be reported.")
                            if complete else (diagnostic or {}).get("next_diagnostic")
                            or "Copy this report to the Director for diagnosis."),
        "code_version": (cfg or {}).get("code_version") or (replay.get("launch") or {}).get("code_version"),
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
        f"**Status:** {r['status'].upper()}" + (f" · phase **{op.get('phase')}** · health **{op.get('health')}**"
                                               if op else "")
        + f" · coverage **{r['completion']}** ({cov['applied_events']:,}/{total} feed events) · validation **{vtext}**",
        "",
        f"> {r['notice']}",
        "",
        "## Data",
        f"- Preset: {r['preset']}",
        f"- Corpus chunk: `{c['chunk_id']}` ({c.get('chunk_label')}), plan `{c['plan_id']}` v{c.get('plan_version')}",
        f"- Dataset: `{c['dataset_id']}` · manifest sha256 `{str(c.get('manifest_sha256'))[:16]}…` · "
        f"quality {str(r['quality_status']).upper()}",
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
    lines += [
        "",
        "## Adviser capabilities",
        "| Capability | Status |",
        "|---|---|",
        f"| Professional adviser | {r['capabilities']['professional_adviser']['status']} |",
    ]
    for key, label in UNAVAILABLE_METRICS:
        lines.append(f"| {label} | {r['capabilities'][key]['status']} |")
    lines += [
        f"Reason: {UNAVAILABLE_REASON}.",
        "",
        "## Conclusion",
        f"**{r['conclusion']['verdict']}** — {r['conclusion']['text']}",
        "",
        f"Next diagnostic: {r['next_diagnostic']}",
    ]
    if r["warnings"]:
        lines += ["", "## Warnings / limitations"] + [f"- {w}" for w in r["warnings"]]
    lines += ["", f"_Report format {r['report_format']} · code {r['code_version'] or 'unknown'}_", ""]
    return "\n".join(lines)


def render_json(r: dict[str, Any]) -> str:
    return json.dumps(r, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
