import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChannelState, Delivery, obsApi, ObsManifest, obsReport, ObsReplay, ObsStateDoc, Operation, OpsHealth, Preflight,
  ReplayableSource, TradedBar,
} from "../../api";
import { fmtInt, fmtSecs, fmtTime, humanize } from "../../lib/format";
import { obsFromHash, replaceHash, sourceFromHash } from "../../lib/route";
import { useHealth } from "../../shell/health";
import { Icon } from "../../ui/Icon";
import { Badge, Button, Card, cx, EmptyState, Field, Metric, Mono, Notice, Skeleton, statusTone, Tone } from "../../ui/primitives";
import { MarketChart } from "./MarketChart";

// Market Replay: durable observation-only replay of REAL market evidence through the causal feed.
// It shows what the system was allowed to know at each replay instant and the resulting observable state.
// No interpretation, no MarketView, no LONG/SHORT/NO_TRADE.

const TERMINAL = new Set(["completed", "cancelled", "failed"]);
export const PACING = [
  { label: "1 event/s", value: 1 },
  { label: "5 events/s", value: 5 },
  { label: "20 events/s", value: 20 },
  { label: "100 events/s", value: 100 },
  { label: "max", value: 0 },
];

export const ROLE: Record<string, { name: string; role: string; short: string }> = {
  trade_bar_1m: { name: "Traded price · 1m", short: "Traded", role: "What traded. The only price series charted." },
  mark_bar_1m: { name: "Mark price · 1m", short: "Mark", role: "Venue valuation reference — not an execution price." },
  index_bar_1m: { name: "Index price · 1m", short: "Index", role: "External reference benchmark — not an execution price." },
  funding_settlement: { name: "Settled funding", short: "Funding", role: "Sparse settlement events; no freshness schedule." },
};
const FAMILY_ORDER = ["trade_bar_1m", "mark_bar_1m", "index_bar_1m", "funding_settlement"];

export function pacingLabel(v: number): string {
  return v === 0 ? "max" : `${v} event${v === 1 ? "" : "s"}/s`;
}

/** ISO-8601 duration from the API (e.g. "PT90.5S", "P1DT2H") → seconds. */
function isoSecs(d: string | null | undefined): number | null {
  if (!d) return null;
  const m = d.match(/^(-)?P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?)?$/);
  if (!m) return null;
  const [, neg, dd, hh, mm, ss] = m;
  const s = (Number(dd || 0) * 86400) + (Number(hh || 0) * 3600) + (Number(mm || 0) * 60) + Number(ss || 0);
  return neg ? -s : s;
}

function conditionTone(c: string): Tone {
  return c === "VALID" ? "pos" : c === "GAP" ? "warn" : c === "REJECTED" || c === "INVALID_ONLY" ? "neg" : "neutral";
}
function freshnessTone(f: string): Tone {
  return f === "FRESH" ? "pos" : f === "STALE" ? "warn" : "neutral";
}

export function AvailabilityBadge({ basis, testid }: { basis: string; testid?: string }) {
  return (
    <Badge tone="info" icon="clock" testid={testid}
           title={basis === "MODELED" ? "Modeled availability — not measured publication timing"
             : "Recorded client-observed receipt times — not exchange publication"}>
      {basis === "MODELED" ? "Modeled availability" : "Recorded availability"}
    </Badge>
  );
}

function ProgressBar({ done, total }: { done: number; total: number | null }) {
  const pct = total ? Math.min(100, (done / total) * 100) : 0;
  return (
    <div className="progress" role="progressbar" aria-label="Feed deliveries applied" aria-valuemin={0}
         aria-valuemax={total ?? undefined} aria-valuenow={done}>
      <div className="progress-fill real" style={{ width: `${pct}%` }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared operation panel (status / phase / health / assurance are separate facts)
// ---------------------------------------------------------------------------

export function healthTone(h: OpsHealth): Tone {
  return h === "progressing" ? "pos" : h === "waiting" || h === "finished" ? "info"
    : h === "recovering" ? "brand" : h === "suspended" ? "pending" : h === "alive_no_progress" ? "warn" : "neg";
}

function assuranceTone(a: string): Tone {
  return a === "passed" ? "pos" : a === "failed" ? "neg" : a === "incomplete" ? "warn" : "neutral";
}

export function OperationPanel({ op, testid = "op-panel", what = "operation" }: {
  op: Operation; testid?: string; what?: string;
}) {
  const cur = op.timeline.phases.find((x) => x.state === "current");
  const pr = op.progress;
  const pct = pr.fraction === null ? null : Math.min(100, Math.round(pr.fraction * 1000) / 10);
  const terminal = ["completed", "cancelled", "failed"].includes(op.status);
  return (
    <div className="op-panel" data-testid={testid} data-phase={op.phase ?? ""} data-health={op.health}>
      <div className="op-badges">
        <Badge tone={statusTone(op.status)} dot testid={`${testid}-status`}>{op.status.toUpperCase()}</Badge>
        <Badge tone="brand" testid={`${testid}-phase`}>{op.phase_label}</Badge>
        <Badge tone={healthTone(op.health)} dot testid={`${testid}-health`} title={op.health_detail}>{op.health_label}</Badge>
        <Badge tone={assuranceTone(op.assurance.state)} icon="shield" testid={`${testid}-assurance`}
               title={op.assurance.scope ?? op.assurance.detail ?? ""}>
          Assurance {humanize(op.assurance.state)}
        </Badge>
        <span className="muted small-text mono">attempt {op.attempt} · generation {op.generation}</span>
      </div>
      <ol className="phase-timeline" aria-label={`Phases of this ${what}`} data-testid={`${testid}-timeline`}>
        {op.timeline.phases.map((x) => (
          <li key={x.phase} className={cx("phase-step", `is-${x.state}`, x.interrupted_spans > 0 && "was-interrupted")}
              data-testid={`phase-${x.phase}`} data-state={x.state}
              title={`${x.label}: ${fmtSecs(x.active_seconds)} active${x.interrupted_spans ? ` · ${x.interrupted_spans} interrupted` : ""}`}>
            <span className="phase-dot" aria-hidden />
            <span className="phase-name">{x.label}</span>
            <span className="phase-time mono">{x.spans || x.state === "current" ? fmtSecs(x.active_seconds) : "—"}</span>
          </li>
        ))}
      </ol>
      {!terminal && (
        <div className="op-current" data-testid={`${testid}-current`}>
          <div className="op-current-head">
            <span><b>{cur?.label ?? op.phase_label}</b>{pr.stage ? ` — ${pr.stage}` : ""}</span>
            <span className="mono muted">
              {pr.done !== null && pr.total !== null ? `${fmtInt(pr.done)}/${fmtInt(pr.total)} ${pr.unit ?? ""}`
                : pr.done !== null ? `${fmtInt(pr.done)} ${pr.unit ?? ""} · total unknown` : "progress not measurable yet"}
              {pct !== null && ` · ${pct}%`}
            </span>
          </div>
          <div className="progress" role="progressbar" aria-label="Current phase progress" aria-valuemin={0}
               aria-valuemax={100} aria-valuenow={pct ?? undefined}>
            <div className={cx("progress-fill real", pct === null && "indeterminate")} style={{ width: `${pct ?? 100}%` }} />
          </div>
          <div className="op-current-foot small-text muted">
            <span data-testid={`${testid}-elapsed`}>{fmtSecs(cur?.active_seconds ?? 0)} in this phase · {fmtSecs(op.timeline.active_seconds_total)} active total</span>
            <span data-testid={`${testid}-eta`}>
              {op.eta && op.eta.seconds !== null ? `~${fmtSecs(op.eta.seconds)} left in this phase` : "time remaining not yet known"}
            </span>
          </div>
        </div>
      )}
      <p className="small-text muted" data-testid={`${testid}-health-detail`}>{op.health_detail}</p>
      {op.suspension && (
        <Notice tone="warn" icon="lock" title="Suspended pre-upgrade run (read-only)" testid={`${testid}-suspension`}>
          {op.suspension.reason}
        </Notice>
      )}
    </div>
  );
}

export function CopyDiagnostics({ markdown, mdUrl, jsonUrl, label = "Copy report for chat", testid = "copy-diagnostic" }: {
  markdown: () => Promise<string>; mdUrl: string; jsonUrl: string; label?: string; testid?: string;
}) {
  const [state, setState] = useState<"idle" | "copied" | "error">("idle");
  const copy = async () => {
    try {
      await copyText(await markdown());
      setState("copied");
      window.setTimeout(() => setState("idle"), 4000);
    } catch {
      setState("error");
    }
  };
  return (
    <div className="report-actions">
      <Button icon={state === "copied" ? "check" : "copy"} variant="secondary" onClick={copy} data-testid={testid}>
        {state === "copied" ? "Copied — paste into chat" : state === "error" ? "Copy failed" : label}
      </Button>
      <a className="btn btn-secondary" href={mdUrl} data-testid={`${testid}-md`}><Icon name="download" size={15} /><span>Markdown</span></a>
      <a className="btn btn-secondary" href={jsonUrl} data-testid={`${testid}-json`}><Icon name="download" size={15} /><span>JSON</span></a>
    </div>
  );
}

export async function copyText(value: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value);
    return;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = value;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    if (!ok) throw new Error("clipboard unavailable");
  }
}

// ---------------------------------------------------------------------------
// Launcher
// ---------------------------------------------------------------------------

function Launcher({ onStarted }: { onStarted: (r: ObsReplay) => void }) {
  const initial = sourceFromHash();
  const [sources, setSources] = useState<{ datasets: ReplayableSource[]; recordings: ReplayableSource[] } | null>(null);
  const [kind, setKind] = useState<"dataset" | "recording">(initial?.kind ?? "dataset");
  const [sourceId, setSourceId] = useState<string>(initial?.id ?? "");
  const [pre, setPre] = useState<Preflight | null>(null);
  const [preErr, setPreErr] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [speed, setSpeed] = useState(20);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    obsApi.sources().then(setSources).catch((e) => setError((e as Error).message));
  }, []);

  const list = sources ? (kind === "dataset" ? sources.datasets : sources.recordings) : [];

  useEffect(() => {
    if (!sources) return;
    const replayable = list.filter((s) => s.replayable);
    if (!list.some((s) => s.source_id === sourceId && s.replayable)) setSourceId(replayable[0]?.source_id ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sources, kind]);

  useEffect(() => {
    setPre(null);
    setPreErr(null);
    if (!sourceId) return;
    let alive = true;
    setChecking(true);
    obsApi.preflight(kind, sourceId)
      .then((p) => alive && setPre(p))
      .catch((e) => alive && setPreErr((e as Error).message.replace(/^\d+ /, "")))
      .finally(() => alive && setChecking(false));
    return () => { alive = false; };
  }, [kind, sourceId]);

  const start = async () => {
    setBusy(true);
    try {
      onStarted(await obsApi.start(kind, sourceId, speed));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="New market replay" icon="play" eyebrow="Real evidence · observation only" className="launcher"
          testid="obs-launcher">
      <div className="segmented" role="tablist" aria-label="Source type">
        {(["dataset", "recording"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={kind === k} className={cx("segment", kind === k && "is-on")}
                  onClick={() => setKind(k)} data-testid={`obs-kind-${k}`}>
            <Icon name={k === "dataset" ? "data" : "recorder"} size={14} />
            {k === "dataset" ? "Historical dataset" : "Recorded session"}
          </button>
        ))}
      </div>
      <Field label={kind === "dataset" ? "Dataset" : "Finalized recording"}>
        <select className="control" value={sourceId} onChange={(e) => setSourceId(e.target.value)} data-testid="obs-source">
          {list.length === 0 && <option value="">{sources ? "none available" : "loading…"}</option>}
          {list.map((s) => (
            <option key={s.source_id} value={s.source_id} disabled={!s.replayable}>
              {s.source_id}{s.replayable ? ` · ${s.status}` : ` · ${s.reason ?? "not replayable"}`}
            </option>
          ))}
        </select>
      </Field>

      <div className="preflight" data-testid="obs-preflight">
        {checking && <Skeleton lines={3} />}
        {preErr && <Notice tone="neg" title="Not replayable">{preErr}</Notice>}
        {pre && !checking && (
          <>
            <div className="preflight-row">
              <AvailabilityBadge basis={pre.availability.basis} testid="obs-preflight-availability" />
              <Badge tone={statusTone(pre.source.source_status)} dot>{pre.source.source_status.toUpperCase()}</Badge>
              <Badge tone="pending" icon="clock">Verified after launch</Badge>
            </div>
            <div className="kv-grid">
              <span>Instrument</span><Mono>{pre.source.inst_id}</Mono>
              <span>Coverage</span><Mono>{`${fmtTime(pre.source.coverage_from)} → ${fmtTime(pre.source.coverage_until)}`}</Mono>
              <span>Feed events</span><span className="muted">counted during preparation</span>
            </div>
            <p className="preflight-note">{pre.availability.label}</p>
            <p className="preflight-note" data-testid="obs-preflight-verification">{pre.verification_note}</p>
          </>
        )}
      </div>

      <Field label="Pacing" hint="Operational only — never changes order, state or digests.">
        <select className="control" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} data-testid="obs-start-speed">
          {PACING.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </Field>
      {error && <Notice tone="neg" title="Launch failed">{error}</Notice>}
      <Button icon="play" className="btn-block" onClick={start} disabled={!pre || busy} data-testid="obs-start">
        Start market replay
      </Button>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Observable market state
// ---------------------------------------------------------------------------

function ChannelCard({ c }: { c: ChannelState }) {
  const fam = c.channel.family;
  const role = ROLE[fam] ?? { name: fam, role: "", short: fam };
  const lv = c.latest_valid;
  const p = lv?.payload;
  const age = isoSecs(c.age_since_available);
  const counts = c.counts;
  const rejected = (counts.invalid_row ?? 0) + (counts.conflicting_duplicate ?? 0) + (counts.incomplete_rejected ?? 0)
    + (counts.excluded_unclassified ?? 0);
  return (
    <section className={cx("channel", `fam-${fam}`)} data-testid={`channel-${fam}`}>
      <header className="channel-head">
        <div className="min-0">
          <div className="channel-name">{role.name}</div>
          <div className="channel-role">{role.role}</div>
        </div>
        <div className="channel-badges">
          <Badge tone={conditionTone(c.condition)} dot testid="channel-condition">{humanize(c.condition)}</Badge>
          <Badge tone={freshnessTone(c.freshness)} testid="channel-freshness">{humanize(c.freshness)}</Badge>
        </div>
      </header>
      <div className="channel-value" data-testid="channel-value">
        {!lv ? <span className="muted">No valid observation yet</span>
          : fam === "funding_settlement"
            ? <><span className="channel-big mono">{p?.funding_rate}</span><span className="muted"> funding rate</span></>
            : <>
                <span className="channel-big mono">{p?.close}</span>
                <span className="ohlc mono">O {p?.open} · H {p?.high} · L {p?.low}</span>
                {fam === "trade_bar_1m" && <span className="ohlc mono">Vol {p?.volume_base} {p?.volume_base_ccy}</span>}
              </>}
      </div>
      <dl className="channel-facts">
        <div><dt>Market time</dt><dd className="mono">{lv ? fmtTime(lv.event_time) : "—"}</dd></div>
        <div><dt>Known at</dt><dd className="mono">{lv ? fmtTime(lv.available_time) : "—"}</dd></div>
        <div><dt>Age since known</dt><dd className="mono">{age === null ? "—" : fmtSecs(age)}</dd></div>
        <div><dt>Latest slot</dt><dd className="mono">{c.latest_slot_time ? fmtTime(c.latest_slot_time) : "—"}</dd></div>
        <div>
          <dt>Last quality</dt>
          <dd className={cx("mono", c.last_quality && "text-warn")}>
            {c.last_quality ? `${c.last_quality.payload.reason} @ ${fmtTime(c.last_quality.event_time).slice(11)}` : "none"}
          </dd>
        </div>
        <div><dt>Quality slots since valid</dt><dd className="mono">{c.quality_slots_since_valid}</dd></div>
        <div><dt>Counts</dt><dd className="mono">{counts.valid ?? 0} valid · {counts.missing ?? 0} missing · {rejected} rejected</dd></div>
        <div>
          <dt>Coverage</dt>
          <dd className={cx("mono", c.beyond_coverage && "text-warn")}>{c.beyond_coverage ? "beyond coverage" : "within coverage"}</dd>
        </div>
      </dl>
    </section>
  );
}

export function ObservableStatePanel({ state }: { state: ObsStateDoc["state"] }) {
  if (!state) return <Card><Skeleton lines={5} /></Card>;
  const chans = [...state.channels].sort((a, b) => FAMILY_ORDER.indexOf(a.channel.family) - FAMILY_ORDER.indexOf(b.channel.family));
  return (
    <Card title="Observable market state" icon="layers" testid="observable-state"
          eyebrow={`As of ${fmtTime(state.as_of)} · cursor ${state.cursor.applied_events}`}
          actions={<Badge tone="neutral" title={state.content_digest}>digest {state.content_digest.slice(0, 10)}…</Badge>}>
      <div className="channel-grid">
        {chans.map((c) => <ChannelCard key={c.channel_id} c={c} />)}
      </div>
      <p className="muted small-text">
        Factual causal evidence only. Each channel keeps its own role, freshness and quality; missing input is shown, never
        filled. Freshness uses the inspection policy <code>{state.freshness_policy_id}</code> — a development default, not a
        research threshold.
      </p>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Delivery timeline
// ---------------------------------------------------------------------------

/** Time of day (UTC) with milliseconds; the full timestamp is in the cell title. */
function clock(iso: string): string {
  const m = iso.match(/T(\d{2}:\d{2}:\d{2})(\.\d{1,3})?/);
  return m ? `${m[1]}${m[2] ?? ""}` : iso;
}

function changeText(ch: Delivery["changes"][number]): string {
  const fam = ch.channel_id.split("/").pop() ?? ch.channel_id;
  const parts = [];
  if (ch.condition_before !== ch.condition_after) parts.push(`${ch.condition_before} → ${ch.condition_after}`);
  if (ch.freshness_before !== ch.freshness_after) parts.push(`${ch.freshness_before} → ${ch.freshness_after}`);
  if (!parts.length && ch.latest_valid_before !== ch.latest_valid_after) parts.push("new latest value");
  return `${ROLE[fam]?.short ?? fam}: ${parts.join(", ") || "evidence added"}`;
}

function Timeline({ items }: { items: Delivery[] }) {
  return (
    <Card title="Evidence timeline" icon="pulse" testid="delivery-timeline" eyebrow="Latest causal deliveries, newest first"
          actions={<span className="count-chip mono">{items.length}</span>}>
      {items.length === 0 ? (
        <EmptyState icon="pulse" title="No delivery yet">Deliveries appear as the replay advances.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="table table-compact">
            <thead>
              <tr><th className="num">#</th><th>Delivered (UTC)</th><th>Market time</th><th>Channel</th><th>Evidence</th><th className="wide">Change</th></tr>
            </thead>
            <tbody>
              {[...items].reverse().map((d) => (
                <tr key={d.seq} data-testid="delivery-row">
                  <td className="num mono">{d.seq + 1}</td>
                  <td className="mono nowrap" title={fmtTime(d.available_time)}>{clock(d.available_time)}</td>
                  <td className="mono nowrap" title={fmtTime(d.event_time)}>{clock(d.event_time)}</td>
                  <td className="nowrap">{ROLE[d.family]?.short ?? d.family}</td>
                  <td>
                    {d.kind === "slot_quality"
                      ? <Badge tone="warn">Quality · {d.quality_reason}</Badge>
                      : <Badge tone="neutral">Observation</Badge>}
                  </td>
                  <td className="small-text">{d.changes.length ? d.changes.map(changeText).join(" · ") : <span className="muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Replay panel
// ---------------------------------------------------------------------------

export function ReplayPanel({ r, live, onCommand, eyebrow = "Market replay · real evidence" }: {
  r: ObsReplay; live: boolean; onCommand: (fn: () => Promise<ObsReplay>) => void; eyebrow?: string;
}) {
  const { health } = useHealth();
  const workers = health?.observation_workers?.alive;
  const p = r.progress;
  const cov = r.source.coverage[0];
  const ctl = r.operation.controls;
  const total = p.total_events;
  const post = ["FINALIZING", "VALIDATING", "GENERATING_REPORT"].includes(r.operation.phase ?? "");
  const cursorText = `${p.applied_events}/${total ?? "PENDING"}`;
  return (
    <Card className="run-card obs-card" testid="obs-panel">
      <div className="run-head">
        <div className="run-head-id">
          <div className="eyebrow real-eyebrow">{eyebrow}</div>
          <h2 className="run-title mono">{r.replay_id}</h2>
        </div>
        <div className="run-head-status">
          <Badge tone={statusTone(r.runtime_state)} dot testid="obs-status" title={r.runtime_detail}>
            {r.runtime_state.replace("_", " ").toUpperCase()}
          </Badge>
          <Badge tone="brand" icon="check" testid="obs-real-badge">Real market evidence</Badge>
          {r.availability ? <AvailabilityBadge basis={r.availability.basis} testid="obs-availability" />
            : <Badge tone="pending" icon="clock" testid="obs-availability">Availability pending preparation</Badge>}
          <span className={cx("live-pill", live && "is-live")}>
            <span className={cx("pulse-dot", live ? "tone-pos" : "tone-neutral")} aria-hidden />
            {live ? "Live stream" : "Stream idle"}
          </span>
        </div>
        {!TERMINAL.has(r.status) && !r.operation.suspension && (
          <div className="run-head-controls">
            {!r.cancel_requested && (
              <div className="controls" data-testid="obs-controls">
                {r.control.paused ? (
                  <>
                    <Button icon="play" onClick={() => onCommand(() => obsApi.resume(r.replay_id))} data-testid="obs-resume"
                            disabled={!ctl.resume.enabled} title={ctl.resume.reason ?? undefined}>Resume</Button>
                    <Button variant="secondary" icon="step" onClick={() => onCommand(() => obsApi.step(r.replay_id))}
                            disabled={!ctl.step.enabled} title={ctl.step.reason ?? "exactly one source evidence event"}
                            data-testid="obs-step">
                      Step one event
                    </Button>
                  </>
                ) : (
                  <Button variant="secondary" icon="pause" onClick={() => onCommand(() => obsApi.pause(r.replay_id))} data-testid="obs-pause"
                          disabled={!ctl.pause.enabled} title={ctl.pause.reason ?? undefined}>
                    Pause
                  </Button>
                )}
                <label className="inline-field">
                  <span>Pacing</span>
                  <select className="control control-sm" value={r.control.speed} data-testid="obs-speed" disabled={!ctl.speed.enabled}
                          title={ctl.speed.reason ?? undefined}
                          onChange={(e) => onCommand(() => obsApi.setSpeed(r.replay_id, Number(e.target.value)))}>
                    {[...new Set([...PACING.map((x) => x.value), r.control.speed])].map((v) => (
                      <option key={v} value={v}>{pacingLabel(v)}</option>
                    ))}
                  </select>
                </label>
              </div>
            )}
            <Button variant="danger" icon="stop" onClick={() => onCommand(() => obsApi.cancel(r.replay_id))}
                    disabled={r.cancel_requested} data-testid="obs-cancel">
              {r.cancel_requested ? "Cancelling…" : "Cancel"}
            </Button>
          </div>
        )}
      </div>

      <OperationPanel op={r.operation} testid="obs-op" what="market replay" />

      <div className="run-progress">
        <ProgressBar done={p.applied_events} total={total} />
        <span className="muted small-text" data-testid="obs-replay-progress-note">
          {total === null ? "Replay cursor: total PENDING until the worker has verified the source and built the feed."
            : post && p.applied_events === total ? `Replay 100% — ${r.operation.phase_label.toLowerCase()}; not completed until results are validated and published.`
              : "One step = one causal feed delivery. Pacing never changes state."}
        </span>
      </div>

      <div className="metric-grid">
        <Metric label="Runtime state" mono={false}
                value={<span data-testid="obs-runtime" className={["recovering", "failed"].includes(r.runtime_state) ? "text-warn" : ""}>{humanize(r.runtime_state)}</span>}
                hint={r.runtime_detail} />
        <Metric label="Feed cursor (events)" value={cursorText} testid="obs-cursor"
                hint={p.last_event_id ? <span className="mono" title={p.last_event_id}>{p.last_event_id.split("/").slice(-1)[0]}</span> : "no delivery yet"} />
        <Metric label="Information time" value={fmtTime(p.information_time)} testid="obs-info-time"
                hint="Latest delivery's availability time" />
        <Metric label="Elapsed" value={fmtSecs(p.elapsed_seconds)} />
        <Metric label="Replay ETA" value={p.eta_seconds === null ? "not yet known" : fmtSecs(p.eta_seconds)} hint={p.eta_basis} />
        <Metric label="Observation worker service" mono={false}
                value={workers === undefined ? "unknown" : workers === 0
                  ? <span className="text-warn">no live supervisor — cannot progress</span> : `${workers} supervisor(s) alive`}
                hint="Service availability; this run's own health is shown above" />
        <Metric label="Heartbeat" mono={false}
                value={<span className={r.lease_expired ? "text-warn" : "mono"}>
                  {p.heartbeat_age_seconds === null ? "—" : `${fmtSecs(p.heartbeat_age_seconds)} ago`}
                  {r.lease_expired && " (lease expired — awaiting recovery)"}
                </span>} />
        <Metric label="Attempt" value={`${r.attempt}/${r.max_attempts}`} />
        <Metric label="Pacing" value={pacingLabel(r.control.speed)} testid="obs-speed-now" />
        <Metric label="Source" value={<span data-testid="obs-source-id">{r.source.kind} · {r.source.source_id}</span>}
                hint={`${r.source.source_status} · verified ${r.verification ? (r.verification.verified ? "yes" : "no") : "PENDING"}`} />
        <Metric label="Coverage" value={cov ? `${fmtTime(cov.covered_from).slice(0, 16)} → ${fmtTime(cov.covered_until).slice(11, 16)}` : "—"} />
        <Metric label="Feed identity" value={r.feed ? <span title={r.feed.content_identity}>{r.feed.content_identity.slice(0, 26)}…</span> : "PENDING"}
                hint={r.feed ? `ordered-event ${r.feed.ordered_event_hash.slice(0, 12)}…` : "fixed by the worker-owned preparation"} />
      </div>

      {r.availability && (
        <div className="availability-strip" data-testid="obs-availability-label">
          <Icon name="clock" size={15} />
          <div>
            <strong>{r.availability.basis}</strong> — {r.availability.label}
            <div className="muted small-text mono">{r.availability.policy_id}</div>
          </div>
        </div>
      )}

      {r.source.warnings.map((w) => <Notice key={w} tone="warn">{w}</Notice>)}
      {r.source.exclusions.length > 0 && (
        <Notice tone="warn" title={`${r.source.exclusions.length} bridge exclusion(s) — evidence not delivered`}>
          {r.source.exclusions.join(" · ")}
        </Notice>
      )}
      {r.error && <Notice tone="neg" title="Replay error"><span data-testid="obs-error">{r.error}</span></Notice>}
      <div className="diag-row">
        <span className="muted small-text">
          {TERMINAL.has(r.status) ? "Terminal diagnostic export (phase timings, counters, manifest check)."
            : "Diagnostic snapshot from persisted facts — available at any time; not a result."}
        </span>
        <CopyDiagnostics markdown={() => obsReport.markdown(r.replay_id)} mdUrl={obsReport.downloadUrl(r.replay_id, "md")}
                         jsonUrl={obsReport.downloadUrl(r.replay_id, "json")} label="Copy diagnostics for chat"
                         testid="obs-copy-diagnostic" />
      </div>

      {(r.recovery_log.length > 0 || r.control_log.length > 1) && (
        <div className="log-grid">
          {r.recovery_log.length > 0 && (
            <div className="log" data-testid="obs-recovery-log">
              <div className="log-title"><Icon name="shield" size={14} /> Recovery log</div>
              <ol className="timeline">
                {r.recovery_log.map((x, i) => <li key={i}><b>attempt {x.attempt} · {x.event}</b> — {x.detail}</li>)}
              </ol>
            </div>
          )}
          {r.control_log.length > 1 && (
            <div className="log" data-testid="obs-control-log">
              <div className="log-title"><Icon name="replay" size={14} /> Replay control log <span className="muted">(operational only)</span></div>
              <ol className="timeline">
                {r.control_log.slice(-6).map((c, i) => (
                  <li key={i}>
                    <b>{c.command}</b>
                    {c.at_cursor !== undefined && ` at cursor ${String(c.at_cursor)}`}
                    {c.speed !== undefined && ` · ${pacingLabel(Number(c.speed))}`} · <span className="mono">{fmtTime(c.at)}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export function Artifacts({ m }: { m: ObsManifest }) {
  return (
    <Card title="Replay artifacts" icon="file" testid="obs-artifacts" eyebrow="Immutable, hashed · source evidence referenced, not copied"
          actions={<a className="btn btn-ghost" href={`/api/observations/${m.replay_id}/manifest`} target="_blank" rel="noreferrer"><Icon name="file" size={15} /><span>manifest.json</span></a>}>
      <div className="artifact-summary">
        <Metric label="Validation" mono={false}
                value={<Badge tone={m.validation.passed ? "pos" : "neg"} icon={m.validation.passed ? "check" : "x"}>
                  <span data-testid="obs-validation">{m.validation.passed ? "PASS" : "FAIL"}</span>
                </Badge>}
                hint={`${m.validation.checks.filter((c) => c.passed).length}/${m.validation.checks.length} checks`} />
        <Metric label="Final snapshot digest" value={<code title={m.final_content_digest}>{m.final_content_digest.slice(0, 16)}…</code>}
                hint={`${m.applied_events}/${m.total_events} deliveries · as of ${fmtTime(m.final_as_of)}`} />
        <Metric label="Source evidence" value={m.source_reference} />
      </div>
      <ul className="check-list">
        {m.validation.checks.map((c) => (
          <li key={c.name} className={c.passed ? "text-pos" : "text-neg"}>
            <Icon name={c.passed ? "check" : "x"} size={13} />
            <span className="mono">{c.name}</span>
            <span className="muted">{c.detail}</span>
          </li>
        ))}
      </ul>
      <ul className="artifact-grid">
        {m.artifacts.map((a) => (
          <li key={a.name} className="artifact">
            <Icon name="file" size={15} />
            <a href={`/api/observations/${m.replay_id}/files/${a.name}`} className="mono" target="_blank" rel="noreferrer">{a.name}</a>
            <span className="muted mono">{a.lines !== null ? `${a.lines} lines` : `${a.bytes} B`}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Market Replay mode
// ---------------------------------------------------------------------------

export function MarketReplay() {
  const [replays, setReplays] = useState<ObsReplay[] | null>(null);
  const [selected, setSelected] = useState<string | null>(obsFromHash());
  const preselect = useRef(sourceFromHash() !== null);
  const [doc, setDoc] = useState<ObsStateDoc | null>(null);
  const [items, setItems] = useState<Delivery[]>([]);
  const [bars, setBars] = useState<TradedBar[]>([]);
  const [manifest, setManifest] = useState<ObsManifest | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastCursor = useRef(-1);

  const refresh = useCallback(async () => {
    try {
      const rs = await obsApi.list();
      setReplays(rs);
      setSelected((cur) => cur ?? (preselect.current ? null : rs[0]?.replay_id ?? null));
      setError(null);
    } catch (e) {
      setError(`API unreachable: ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(refresh, 3000);
    return () => window.clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    const on = () => {
      const id = obsFromHash();
      if (id) setSelected((cur) => (cur === id ? cur : id));
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  // Live state via SSE; every (re)connection starts from a full state document.
  useEffect(() => {
    if (!selected) return;
    replaceHash(`replay/obs=${selected}`);
    setDoc(null);
    setItems([]);
    setBars([]);
    setManifest(null);
    lastCursor.current = -1;
    let closed = false;
    const onDoc = (d: ObsStateDoc) => {
      if (closed) return;
      setDoc(d);
      setReplays((rs) => rs?.map((x) => (x.replay_id === d.replay.replay_id ? d.replay : x)) ?? rs);
      const cur = d.replay.progress.applied_events;
      if (cur !== lastCursor.current) {
        lastCursor.current = cur;
        void Promise.all([obsApi.deliveries(selected, 15), obsApi.bars(selected)]).then(([dl, b]) => {
          if (closed) return;
          setItems(dl);
          setBars(b.bars);
        });
      }
      if (d.replay.has_manifest) void obsApi.manifest(selected).then((m) => !closed && setManifest(m));
    };
    void obsApi.state(selected).then(onDoc).catch((e) => setError((e as Error).message));
    const es = new EventSource(`/api/observations/${selected}/stream`);
    es.addEventListener("open", () => setLive(true));
    es.addEventListener("snapshot", (ev) => onDoc(JSON.parse((ev as MessageEvent).data) as ObsStateDoc));
    es.addEventListener("end", () => { setLive(false); es.close(); });
    es.addEventListener("error", () => setLive(false));
    return () => { closed = true; es.close(); };
  }, [selected]);

  const command = async (fn: () => Promise<ObsReplay>) => {
    try {
      const updated = await fn();
      setDoc((d) => (d && d.replay.replay_id === updated.replay_id ? { ...d, replay: updated } : d));
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const onStarted = (r: ObsReplay) => {
    preselect.current = false;
    setSelected(r.replay_id);
    void refresh();
  };

  const r = doc?.replay ?? replays?.find((x) => x.replay_id === selected) ?? null;

  return (
    <div className="lab-mode" data-testid="market-replay">
      <div className="real-banner" data-testid="real-banner">
        <Icon name="shield" size={18} />
        <div>
          <strong>REAL MARKET EVIDENCE · OBSERVATION ONLY</strong> — verified OKX evidence delivered through the causal feed.
          Shows what the system was allowed to know at each replay instant and the resulting observable state.
        </div>
      </div>
      {error && <Notice tone="neg" title="Something went wrong">{error}</Notice>}

      <div className="lab-grid">
        <div className="rail">
          <Launcher onStarted={onStarted} />
          <Card title="Market replays" icon="replay" className="rail-list-card"
                actions={<span className="count-chip mono">{replays?.length ?? 0}</span>}>
            {replays && replays.length === 0 ? (
              <EmptyState icon="replay" title="No market replays yet">Choose a dataset or a finalized recording above.</EmptyState>
            ) : (
              <ul className="list" aria-label="Market replays" data-testid="obs-list">
                {(replays ?? []).map((x) => (
                  <li key={x.replay_id}>
                    <button type="button" className={cx("list-item", x.replay_id === selected && "is-selected")}
                            aria-current={x.replay_id === selected ? "true" : undefined}
                            onClick={() => { preselect.current = false; setSelected(x.replay_id); }}>
                      <span className="list-item-title mono">{x.replay_id}</span>
                      <span className="list-item-meta">
                        <Badge tone={statusTone(x.runtime_state)} dot>{x.runtime_state.replace("_", " ").toUpperCase()}</Badge>
                        <Badge tone="info">{x.availability?.basis ?? "PENDING"}</Badge>
                        <span className="mono muted">{x.progress.applied_events}/{x.progress.total_events ?? "?"}</span>
                      </span>
                      <span className="list-item-sub mono">{x.source.kind} · {x.source.source_id}</span>
                      <span className="mini-progress real" aria-hidden>
                        <span style={{ width: `${(x.progress.applied_events / (x.progress.total_events || 1)) * 100}%` }} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="lab-main">
          {!r ? (
            <Card>
              <EmptyState icon="market" title="No market replay selected">
                Launch a replay of a verified historical dataset (modeled availability) or a finalized recording (recorded
                receipt times) to inspect the observable market state instant by instant.
              </EmptyState>
            </Card>
          ) : (
            <>
              <ReplayPanel r={r} live={live} onCommand={command} />

              <div className="boundary" data-testid="intelligence-boundary">
                <Icon name="compass" size={18} />
                <div>
                  <strong>Professional interpretation and LONG/SHORT/NO_TRADE are not connected yet.</strong>{" "}
                  This replay shows observable evidence only — no market view, scenario, signal, level or target is derived
                  from it.
                </div>
                <Badge tone="pending" icon="clock">Not yet implemented</Badge>
              </div>

              <Card title="Traded price" icon="market" testid="market-chart" eyebrow="Completed 1m traded bars, as causally delivered"
                    actions={<Badge tone="brand">REAL</Badge>}>
                <MarketChart bars={bars} informationTime={r.progress.information_time} />
              </Card>

              <ObservableStatePanel state={doc?.state ?? null} />
              <Timeline items={items} />
              {manifest && <Artifacts m={manifest} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
