import { useEffect, useMemo, useState } from "react";
import { adviserApi, CallDetail, ENTRY_TEXT, EXPECTED_TEXT, reasonText, ROW_TEXT, THESIS_TEXT } from "../adviser";
import { AdviserSection, ObsReplay } from "../api";
import { fmtNum, fmtTime, humanize } from "../lib/format";
import { Badge, Card, cx, Metric, Notice, Skeleton } from "../ui/primitives";

// Adviser evaluation result (WP-009). Everything shown comes from the committed report / journal. Hypothetical
// outcomes are normalized one-unit simulations (never fills, account results, size or leverage) and are labelled so.
// Completion and coverage come first; no headline win rate is shown alone.

function bps(x: string | null | undefined): string {
  return x === null || x === undefined ? "—" : `${fmtNum(x, 1)} bps`;
}
function frac(x: string | null | undefined): string {
  return x === null || x === undefined ? "—" : `${fmtNum(Number(x) * 10000, 1)} bps`;
}

export function AdviserSummary({ a }: { a: AdviserSection }) {
  if (a.pending) return <Notice tone="info" title="Adviser section pending">{a.text}</Notice>;
  const c = a.calls;
  const p = a.outcomes.variants.PRIMARY;
  const cov = a.coverage;
  return (
    <div className="stack" data-testid="adviser-summary">
      <div className="adv-metrics">
        <Metric label="Calls (evaluation window)" value={String(c.count)} testid="adv-calls"
                hint={`${c.per_evaluated_week}/evaluated week · ${c.per_assessable_week ?? "—"}/assessable week`} />
        <Metric label="Entry valid (per call)" value={c.entry_available_minutes.median ? `${c.entry_available_minutes.median} min` : "—"}
                hint={`median · max ${c.entry_available_minutes.max ?? "—"} min · reopens ${c.entry_reopens}`} testid="adv-entry" />
        <Metric label="Longest no-call interval" value={`${fmtNum(c.longest_no_call_interval_hours, 1)} h`} />
        <Metric label="Assessable time" value={`${Math.round((cov.assessable_minutes / Math.max(1, cov.evaluation_minutes)) * 100)}%`}
                hint={`${cov.unavailable_minutes} min unavailable (warmup/data)`} testid="adv-coverage" />
        <Metric label="Hypothetical entries" value={`${p.paths - p.no_entry}/${p.paths}`}
                hint={`NO_ENTRY ${p.no_entry} · censored ${p.censored} · unresolved ${p.unresolved}`} testid="adv-entries" />
        <Metric label="Target / stop / guidance exits" value={`${p.target_exits} / ${p.stop_exits} / ${p.guidance_exits}`}
                hint={`ambiguous ${p.ambiguous}`} />
        <Metric label="Price-net (normalized)" value={p.price_net_bps_distribution.median ? `${p.price_net_bps_distribution.median} bps` : "—"}
                hint={`median per closed path · sum ${fmtNum(Number(p.sum_price_net) * 10000, 1)} bps · total net unavailable`} testid="adv-net" />
      </div>
      <Notice tone="info" title="Hypothetical, normalized, price-net only" testid="adv-hypo-note">
        {a.outcomes.note}. Funding completeness is unproven for this pack, so total net is unavailable — never assumed zero.
      </Notice>
      {a.diagnosis.length > 0 && (
        <Notice tone="warn" title="Why few or no calls" testid="adv-diagnosis">
          {a.diagnosis.map((d) => <div key={d}>{d}</div>)}
        </Notice>
      )}
      <div className="adv-section-title">Candidate funnel</div>
      <div className="funnel" data-testid="adv-funnel">
        <span className="step">births {Object.values(a.funnel.births).reduce((x, y) => x + y, 0)}</span>›
        <span className="step">armed {Object.values(a.funnel.arms).reduce((x, y) => x + y, 0)}</span>›
        <span className="step">trigger evaluations {a.funnel.trigger_evaluations}</span>›
        <span className="step">calls {a.funnel.issued}</span>
        <span className="muted small-text">slot occupied {a.funnel.slot_occupied} · priority {a.funnel.priority} · conflicted {a.funnel.conflicted}</span>
      </div>
      {Object.keys(a.funnel.rejection_blockers).length > 0 && (
        <div className="small-text muted">Trigger rejections: {Object.entries(a.funnel.rejection_blockers).map(([k, n]) => `${humanize(k)} ${n}`).join(" · ")}</div>
      )}
      <details className="more inset">
        <summary>Funnel, gates, sensitivities and view samples (all details)</summary>
        <div className="more-body">
          <div className="small-table-wrap">
            <table className="small-table">
              <thead><tr><th>Family/direction</th><th>Births</th><th>Armed</th></tr></thead>
              <tbody>{Object.keys({ ...a.funnel.births, ...a.funnel.arms }).sort().map((k) => (
                <tr key={k}><td>{k}</td><td>{a.funnel.births[k] ?? 0}</td><td>{a.funnel.arms[k.split("_")[0]] ?? a.funnel.arms[k] ?? 0}</td></tr>))}</tbody>
            </table>
          </div>
          <div className="small-text">Attempt endings: {Object.entries(a.funnel.end_reasons).map(([k, n]) => `${humanize(k)} ${n}`).join(" · ") || "none"}</div>
          <div className="small-table-wrap">
            <table className="small-table">
              <thead><tr><th>Family</th><th>G median</th><th>Q median</th><th>K</th><th>margin G−1.2Q−2.2K</th><th>n</th></tr></thead>
              <tbody>{Object.entries(a.gates).map(([f, g]) => (
                <tr key={f}><td>{f}</td><td>{g.G.median}</td><td>{g.Q.median}</td><td>{g.K.median}</td><td>{g.margin.median}</td><td>{g.G.n}</td></tr>))}</tbody>
            </table>
          </div>
          <div className="small-table-wrap">
            <table className="small-table" data-testid="adv-sensitivity">
              <thead><tr><th>Variant</th><th>Paths</th><th>No entry</th><th>Target</th><th>Stop</th><th>Guidance</th><th>Price-net sum</th></tr></thead>
              <tbody>{Object.entries(a.outcomes.variants).map(([v, x]) => (
                <tr key={v}><td>{humanize(v)}</td><td>{x.paths}</td><td>{x.no_entry}</td><td>{x.target_exits}</td><td>{x.stop_exits}</td>
                  <td>{x.guidance_exits}</td><td>{frac(x.sum_price_net)}</td></tr>))}</tbody>
            </table>
          </div>
          <div className="small-text">Cost stress (5 bps/leg allowance) on the same primary paths: {frac(p.sum_stress_price_net)} — outcome
            sensitivity only, calls unchanged.</div>
          <pre className="mono small-text">{JSON.stringify(a.view_samples, null, 1)}</pre>
        </div>
      </details>
    </div>
  );
}

function MiniChart({ bars, call }: { bars: { t: string; c: string; h: string; l: string }[]; call: CallDetail["call"] }) {
  const W = 640;
  const H = 180;
  const d = useMemo(() => {
    if (!call || bars.length < 2) return null;
    const vals = [...bars.flatMap((b) => [Number(b.h), Number(b.l)]), Number(call.target), Number(call.invalidation)];
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const y = (p: number) => H - 10 - ((p - lo) / (hi - lo || 1)) * (H - 20);
    const t0 = Date.parse(bars[0].t);
    const t1 = Date.parse(bars[bars.length - 1].t);
    const x = (t: string) => 6 + ((Date.parse(t) - t0) / (t1 - t0 || 1)) * (W - 12);
    return {
      path: bars.map((b, i) => `${i ? "L" : "M"}${x(b.t).toFixed(1)},${y(Number(b.c)).toFixed(1)}`).join(" "),
      t: y(Number(call.target)), v: y(Number(call.invalidation)), issue: x(call.issued_at),
      a1: y(Number(call.structural_area[1])), a0: y(Number(call.structural_area[0])),
    };
  }, [bars, call]);
  if (!d) return <Skeleton lines={2} />;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="live-chart" data-testid="call-chart" role="img" aria-label="Price around the call">
      <rect x={6} width={W - 12} y={d.a1} height={Math.max(1, d.a0 - d.a1)} className="band-area" />
      <g className="lvl lvl-target"><line x1={6} x2={W - 6} y1={d.t} y2={d.t} /></g>
      <g className="lvl lvl-stop"><line x1={6} x2={W - 6} y1={d.v} y2={d.v} /></g>
      <line x1={d.issue} x2={d.issue} y1={0} y2={H} stroke="var(--brand)" strokeDasharray="2 3" />
      <path d={d.path} className="price-line" />
    </svg>
  );
}

function CallDetailPanel({ replayId, callId }: { replayId: string; callId: string }) {
  const [d, setD] = useState<CallDetail | null>(null);
  const [bars, setBars] = useState<{ t: string; o: string; h: string; l: string; c: string }[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setD(null);
    setBars([]);
    adviserApi.call(replayId, callId).then((x) => {
      setD(x);
      if (x.call) void adviserApi.window(replayId, x.call.env.factual_cursor).then((w) => setBars(w.bars)).catch(() => undefined);
    }).catch((e) => setErr((e as Error).message));
  }, [replayId, callId]);
  if (err) return <Notice tone="neg" title="Could not load the call">{err}</Notice>;
  if (!d || !d.call) return <Skeleton lines={4} />;
  const c = d.call;
  const mv = d.market_view_at_issue;
  return (
    <div className="call-detail" data-testid="call-detail">
      <div className="call-head">
        <span className={cx("call-dir", c.direction === "LONG" ? "text-pos" : "text-neg")}>{c.direction}</span>
        <span className="call-family">{c.family} · {c.thesis}</span>
      </div>
      <MiniChart bars={bars} call={c} />
      <dl className="call-geo">
        <dt>Issued</dt><dd>{fmtTime(c.issued_at)} at {c.issue_reference}</dd>
        <dt>Structural area</dt><dd className="mono">{c.structural_area[0]} – {c.structural_area[1]}</dd>
        <dt>Admissible at issue</dt><dd className="mono">{c.actionability.admissible_bounds?.join(" – ") ?? "—"}</dd>
        <dt>Target / stop</dt><dd className="mono">{c.target} ({humanize(c.target_type)}) / {c.invalidation}</dd>
        <dt>G / Q / K</dt><dd className="mono">{bps(c.actionability.gain_bps)} / {bps(c.actionability.risk_bps)} / {bps(c.actionability.cost_envelope_bps)}</dd>
        <dt>Limiting level</dt><dd>{c.limiting_landmark ? `${c.limiting_landmark.type} (age ${c.limiting_landmark.age_minutes} min)` : "projection / midpoint"}</dd>
        <dt>Premise</dt><dd>{c.premise}</dd>
      </dl>
      {mv && (
        <div className="small-text" data-testid="call-scenario">Market view at issue: <b>{EXPECTED_TEXT[mv.expected_direction]}</b> ·
          {" "}{ROW_TEXT[mv.table_row] ?? mv.table_row} · observed context {mv.observed_context} · phase {humanize(mv.phase)}</div>
      )}
      <div className="adv-section-title">Scenario and candidate</div>
      <ol className="change-timeline">
        {d.candidate.map((x, i) => (
          <li key={i}><span className="mono small-text">{fmtTime(x.env.published_at).slice(11, 16)}</span>
            <span className="tl-kind">{humanize(x.transition)}</span>
            <span className="tl-text">{x.reason ?? ""} {x.trigger_level ? `K ${x.trigger_level}` : ""} {x.invalidation_level ? `V ${x.invalidation_level}` : ""}</span></li>
        ))}
      </ol>
      <div className="adv-section-title">Guidance revisions (the call itself)</div>
      <ol className="change-timeline" data-testid="call-revisions">
        {d.revisions.map((r) => (
          <li key={r.revision}><span className="mono small-text">{fmtTime(r.env.published_at).slice(11, 16)}</span>
            <span className="tl-kind">{r.thesis_status === "ONGOING" ? ENTRY_TEXT[r.entry_status] ?? r.entry_status : THESIS_TEXT[r.thesis_status] ?? r.thesis_status}</span>
            <span className="tl-text" title={r.terminal_reason ?? r.entry_reasons.join(", ")}>{r.terminal_reason ? reasonText(r.terminal_reason) : r.entry_reasons.map(reasonText).join(", ")}</span></li>
        ))}
      </ol>
      <div className="hypo" data-testid="call-hypothetical">
        <div className="adv-section-title">Hypothetical evaluation (separate; not a fill)</div>
        <div className="small-table-wrap">
          <table className="small-table">
            <thead><tr><th>Variant</th><th>Status</th><th>Entry</th><th>Exit</th><th>Gross</th><th>Price-net</th></tr></thead>
            <tbody>{d.hypothetical_paths.map((p) => (
              <tr key={p.path_id}><td>{humanize(p.variant)}</td><td>{humanize(p.status)}{p.exit_class ? ` · ${humanize(p.exit_class)}` : ""}</td>
                <td className="mono">{p.entry ? `${p.entry.price} @ ${fmtTime(p.entry.time_start).slice(11, 16)}` : "—"}</td>
                <td className="mono">{p.exit ? `${p.exit.price} @ ${fmtTime(p.exit.time_start).slice(11, 16)}` : "—"}</td>
                <td>{frac(p.gross)}</td><td>{frac(p.price_net)}</td></tr>))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function CallTimeline({ replayId, a }: { replayId: string; a: AdviserSection }) {
  const [sel, setSel] = useState<string | null>(null);
  if (a.pending) return null;
  if (!a.calls.list.length) {
    return <p className="muted small-text" data-testid="adv-no-calls">No calls in the evaluation window. The funnel and the
      diagnosis above name the blockers.</p>;
  }
  return (
    <div className="stack" data-testid="adv-call-timeline">
      <ul className="call-list">
        {a.calls.list.map((c) => (
          <li key={c.call_id}>
            <button type="button" className={cx("call-row", sel === c.call_id && "is-selected")} onClick={() => setSel(c.call_id)}
                    data-testid="adv-call-row">
              <span className="mono small-text">{fmtTime(c.issued_at).slice(0, 16)}</span>
              <span className={c.direction === "LONG" ? "long" : "short"}>{c.direction} {c.family}</span>
              <span className="small-text">target {c.target} · stop {c.stop} · entry valid {fmtNum(c.entry_available_minutes, 0)} min</span>
              <Badge tone={c.terminal === "TARGET_REACHED" ? "pos" : c.terminal === "INVALIDATED" ? "neg" : "neutral"}>{THESIS_TEXT[c.terminal] ?? c.terminal}</Badge>
            </button>
          </li>
        ))}
      </ul>
      {sel && <CallDetailPanel replayId={replayId} callId={sel} />}
    </div>
  );
}

/** Committed adviser state while an evaluation runs (simulated time; not current advice). */
export function AdviserProgress({ r }: { r: ObsReplay }) {
  const adv = (r as unknown as { adviser?: { committed?: Record<string, unknown> | null; pending?: boolean } }).adviser;
  const v = adv?.committed as { clock?: string; window?: string; view?: { expected_direction: string; table_row: string;
                                observed_context: string; phase: string } | null; call?: { direction: string; family: string;
                                entry_status: string; target: string; stop: string } | null; journal_seq?: number } | null | undefined;
  return (
    <Card title="Adviser during the replay" icon="compass" testid="adviser-progress"
          eyebrow="Historical simulated time — not current advice" actions={<Badge tone="brand">HISTORICAL</Badge>}>
      {!v ? <p className="muted small-text">The adviser state appears at the first committed checkpoint.</p> : (
        <div className="kv-grid">
          <span>Simulated clock</span><span className="mono">{fmtTime(v.clock ?? null)}</span>
          <span>Window</span><span>{humanize(String(v.window ?? "—"))}</span>
          <span>Expected direction</span><span>{v.view ? `${EXPECTED_TEXT[v.view.expected_direction] ?? v.view.expected_direction} · ${ROW_TEXT[v.view.table_row] ?? v.view.table_row}` : "—"}</span>
          <span>Observed context / phase</span><span>{v.view ? `${v.view.observed_context} / ${humanize(v.view.phase)}` : "—"}</span>
          <span>Call</span><span>{v.call ? `${v.call.direction} ${v.call.family} · ${ENTRY_TEXT[v.call.entry_status] ?? v.call.entry_status} · target ${v.call.target} · stop ${v.call.stop}` : "none"}</span>
          <span>Journal records</span><span className="mono">{v.journal_seq ?? 0}</span>
        </div>
      )}
    </Card>
  );
}
