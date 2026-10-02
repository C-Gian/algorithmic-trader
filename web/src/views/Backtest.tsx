import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  barsTail, corpusApi, CorpusChunk, CorpusJob, CorpusStatus, evalApi, Evaluation, EvaluationReport, obsApi, ObsReplay,
  ObsStateDoc, StorageSummary, TradedBar,
} from "../api";
import { fmtBytes, fmtInt, fmtSecs, fmtTime, humanize } from "../lib/format";
import { evalFromHash, replaceHash } from "../lib/route";
import { usePoll } from "../lib/usePoll";
import { Icon } from "../ui/Icon";
import {
  Badge, Button, Card, cx, EmptyState, Field, Metric, Mono, Notice, PageHeader, Skeleton, statusTone, Tone,
} from "../ui/primitives";
import { DeepValidationPanel } from "./replay/DeepValidation";
import { MarketChart } from "./replay/MarketChart";
import { Artifacts, CopyDiagnostics, copyText, ObservableStatePanel, OperationPanel, PACING, ReplayPanel } from "./replay/MarketReplay";

// Historical Workbench (route #backtest kept): the Owner's evaluation workbench. Three stages over the SAME machinery:
//   A. historical corpus  - checked-in logical plan + locally prepared, verified immutable datasets;
//   B. run setup          - explicit run types: Market replay (data and engine check) is the only available one;
//                           Adviser backtest is unavailable until the adviser exists; Deep validation is an optional
//                           diagnostic launched explicitly from a finished/paused run (its own durable job);
//   C. run & report       - the durable observation replay with its phase timeline, plus a copyable report or
//                           diagnostic snapshot at every status.
// No adviser is connected yet: no MarketView, calls or outcomes are shown or implied.

const NOT_CONNECTED =
  "Professional adviser not connected yet. This run validates data/replay/product workflow only; trade-call metrics are unavailable.";
const TERMINAL = new Set(["completed", "cancelled", "failed"]);
const CHART_TAIL = 240; // bounded chart window: the latest 4 hours of traded 1m bars
const CHART_MIN_INTERVAL_MS = 1000; // sampled UI frames; the worker still processes every event

const CHUNK_TONE: Record<CorpusChunk["status"], Tone> = {
  prepared: "pos", preparing: "info", not_prepared: "brand", invalid: "neg", planned: "pending",
};
const CHUNK_LABEL: Record<CorpusChunk["status"], string> = {
  prepared: "Prepared", preparing: "Preparing", not_prepared: "Not prepared", invalid: "Needs attention",
  planned: "Planned · locked",
};
const OUTCOME_TEXT: Record<string, string> = {
  acquired: "Downloaded from OKX public REST, verified and bound",
  acquired_identical_existing: "Downloaded; identical bytes were already stored — verified and bound",
  adopted_local_dataset: "An exactly matching local dataset was verified and bound — nothing downloaded",
  reused_binding: "The bound local dataset re-verified — nothing downloaded",
};
const PHASE_TEXT: Record<string, string> = {
  checking_local: "Checking local data",
  verifying: "Verifying hashes",
  instrument: "Instrument definition",
  trade_candles_1m: "Traded 1m candles",
  mark_candles_1m: "Mark 1m candles",
  index_candles_1m: "Index 1m candles",
  funding_rates: "Settled funding",
  finalizing: "Writing immutable dataset",
  completed: "Completed",
  cancelled: "Cancelled",
  failed: "Failed",
};

function utcDay(iso: string): string {
  return iso.slice(0, 10);
}
function monthParts(iso: string): { mon: string; year: string } {
  const d = new Date(iso);
  return { mon: d.toLocaleString("en-US", { month: "short", timeZone: "UTC" }), year: String(d.getUTCFullYear()) };
}
function span(a: string, b: string): string {
  const mins = Math.round((Date.parse(b) - Date.parse(a)) / 60_000);
  if (mins >= 1440) return `${Math.round(mins / 1440)} days`;
  return mins >= 60 ? `${(mins / 60).toFixed(1)} hours` : `${mins} minutes`;
}

// ---------------------------------------------------------------------------
// Stage rail
// ---------------------------------------------------------------------------

function StageRail({ corpus, ev }: { corpus: CorpusStatus | null; ev: Evaluation | null }) {
  const prepared = corpus?.summary.prepared ?? 0;
  const preparing = corpus?.chunks.some((c) => c.status === "preparing");
  const runState = ev?.replay.runtime_state;
  const stages: { n: string; title: string; value: string; tone: Tone; testid: string }[] = [
    {
      n: "A", title: "Historical corpus", testid: "stage-corpus",
      value: !corpus ? "Loading…" : preparing ? "Preparing a chunk…"
        : `${prepared}/${corpus.summary.chunks} months prepared`,
      tone: preparing ? "info" : prepared ? "pos" : "brand",
    },
    {
      n: "B", title: "Run setup", testid: "stage-setup",
      value: prepared ? "Ready · market replay" : "Waiting for a prepared chunk",
      tone: prepared ? "pos" : "neutral",
    },
    {
      n: "C", title: "Run & report", testid: "stage-run",
      value: !ev ? "No evaluation yet" : ev.report_terminal ? `Report ready · ${ev.replay.status}`
        : `${humanize(runState ?? "queued")} · ${ev.replay.operation.phase_label}`,
      tone: !ev ? "neutral" : ev.report_terminal ? (ev.replay.status === "completed" ? "pos" : "warn") : "info",
    },
  ];
  return (
    <ol className="stage-rail" aria-label="Evaluation workflow">
      {stages.map((s) => (
        <li key={s.n} className={cx("stage", `tone-${s.tone}`)} data-testid={s.testid}>
          <span className="stage-n" aria-hidden>{s.n}</span>
          <span className="stage-body">
            <span className="stage-title">{s.title}</span>
            <span className="stage-value">{s.value}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------------------
// A. Historical corpus
// ---------------------------------------------------------------------------

function CorpusLedger({ corpus, selected, onSelect }: {
  corpus: CorpusStatus; selected: string | null; onSelect: (id: string) => void;
}) {
  return (
    <div className="ledger" role="listbox" aria-label="Corpus months" data-testid="corpus-ledger">
      {corpus.chunks.map((c) => {
        const { mon, year } = monthParts(c.start);
        const frac = c.latest_job?.progress.fraction;
        return (
          <button key={c.chunk_id} type="button" role="option" aria-selected={c.chunk_id === selected}
                  className={cx("ledger-cell", `st-${c.status}`, c.chunk_id === selected && "is-selected")}
                  onClick={() => onSelect(c.chunk_id)} data-testid={`ledger-${c.chunk_id}`} data-status={c.status}
                  title={`${c.label} · ${CHUNK_LABEL[c.status]}`}>
            <span className="ledger-mon">{mon}</span>
            <span className="ledger-year mono">{year}</span>
            <span className="ledger-state">
              {c.status === "prepared" && <Icon name="check" size={13} />}
              {c.status === "planned" && <Icon name="lock" size={12} />}
              {c.status === "invalid" && <Icon name="alert" size={12} />}
              {c.status === "preparing" && <span className="pulse-dot tone-info" aria-hidden />}
              {c.status === "not_prepared" && <Icon name="download" size={13} />}
            </span>
            {c.status === "preparing" && (
              <span className="ledger-fill" style={{ width: `${Math.round((frac ?? 0) * 100)}%` }} aria-hidden />
            )}
          </button>
        );
      })}
    </div>
  );
}

function JobProgress({ job, onCancel }: { job: CorpusJob; onCancel: () => void }) {
  const p = job.progress;
  const active = job.status === "queued" || job.status === "running";
  const pct = p.fraction === null ? null : Math.round(p.fraction * 100);
  if (job.status === "completed") {
    return (
      <div className="job job-done" data-testid="prep-job" data-state={job.runtime_state}>
        <Icon name="check" size={16} />
        <div className="min-0">
          <div className="job-done-title" data-testid="prep-outcome">{OUTCOME_TEXT[job.outcome ?? ""] ?? job.outcome}</div>
          <div className="muted small-text mono">
            {job.job_id} · {p.pages === undefined ? "no" : fmtInt(p.pages)} source pages
            {p.bytes !== undefined && ` · ${fmtBytes(p.bytes)} fetched`} · {fmtSecs(p.elapsed_seconds)} · attempt {job.attempt}/{job.max_attempts}
            {job.finished_at && ` · finished ${fmtTime(job.finished_at)}`}
          </div>
        </div>
        <Badge tone="pos" dot testid="prep-status">COMPLETED</Badge>
      </div>
    );
  }
  return (
    <div className={cx("job", active && "is-active")} data-testid="prep-job" data-state={job.runtime_state}>
      <div className="job-head">
        <div className="min-0">
          <div className="eyebrow">Preparation job</div>
          <div className="mono job-id">{job.job_id}</div>
        </div>
        <Badge tone={statusTone(job.runtime_state === "unresponsive" ? "failed" : job.status)} dot
               testid="prep-status" title={job.runtime_detail}>
          {humanize(job.runtime_state).toUpperCase()}
        </Badge>
      </div>
      {job.operation && <OperationPanel op={job.operation} testid="prep-op" what="preparation" />}
      {active && (
        <>
          <div className="job-phase">
            <span className="job-phase-name" data-testid="prep-phase">{PHASE_TEXT[p.phase ?? ""] ?? humanize(p.phase ?? "waiting for worker")}</span>
            {p.windows_total ? (
              <span className="mono muted">{fmtInt(p.windows_done ?? 0)}/{fmtInt(p.windows_total)} windows{pct !== null && ` · ${pct}%`}</span>
            ) : <span className="muted small-text">{p.detail ?? job.runtime_detail}</span>}
          </div>
          <div className="progress" role="progressbar" aria-label="Corpus preparation progress" aria-valuemin={0}
               aria-valuemax={100} aria-valuenow={pct ?? 0}>
            <div className={cx("progress-fill real", pct === null && "indeterminate")} style={{ width: `${pct ?? 100}%` }} />
          </div>
        </>
      )}
      <div className="metric-grid compact">
        <Metric label="Source pages" value={p.pages === undefined ? "—" : fmtInt(p.pages)} testid="prep-pages" />
        <Metric label="Bytes fetched" value={p.bytes === undefined ? "—" : fmtBytes(p.bytes)} />
        <Metric label="Elapsed" value={fmtSecs(p.elapsed_seconds)} testid="prep-elapsed" />
        <Metric label="Heartbeat" value={p.heartbeat_age_seconds === null ? "—" : `${fmtSecs(p.heartbeat_age_seconds)} ago`} />
        {active && <Metric label="ETA" value={p.eta_seconds === null ? "not yet measured" : fmtSecs(p.eta_seconds)}
                           hint={p.eta_basis} mono={p.eta_seconds !== null} />}
        <Metric label="Attempt" value={`${job.attempt}/${job.max_attempts}`} />
      </div>
      {job.status === "cancelled" && <Notice tone="warn" title="Preparation cancelled" testid="prep-outcome">{job.error}</Notice>}
      {job.status === "failed" && <Notice tone="neg" title="Preparation failed" testid="prep-outcome">{job.error}</Notice>}
      {job.recovery_log.length > 0 && (
        <ol className="timeline small-text" data-testid="prep-recovery-log">
          {job.recovery_log.map((x, i) => <li key={i}><b>attempt {x.attempt} · {x.event}</b> — {x.detail}</li>)}
        </ol>
      )}
      <CopyDiagnostics markdown={() => corpusApi.reportMarkdown(job.job_id)} mdUrl={corpusApi.downloadUrl(job.job_id, "md")}
                       jsonUrl={corpusApi.downloadUrl(job.job_id, "json")} label="Copy preparation report for chat"
                       testid="prep-copy-diagnostic" />
      <div className="job-foot">
        <p className="muted small-text"><Icon name="shield" size={13} /> {job.recovery_behavior}</p>
        {active && (
          <Button variant="danger" icon="stop" onClick={onCancel} disabled={job.cancel_requested} data-testid="prep-cancel">
            {job.cancel_requested ? "Cancelling…" : "Cancel"}
          </Button>
        )}
      </div>
    </div>
  );
}

function StorageFacts({ s }: { s: StorageSummary }) {
  return (
    <div className="storage" data-testid="storage-facts">
      <div className="storage-head">
        <span className="eyebrow">Measured storage · for the corpus pack decision</span>
        <span className="mono storage-total" data-testid="storage-total">{fmtBytes(s.total_bytes)}</span>
      </div>
      <div className="storage-bar" aria-hidden>
        <span className="sb-raw" style={{ flexGrow: s.raw_bytes }} />
        <span className="sb-parquet" style={{ flexGrow: s.parquet_bytes }} />
        <span className="sb-meta" style={{ flexGrow: s.metadata_bytes }} />
      </div>
      <div className="storage-legend">
        <span><i className="sb-raw" /> Raw source pages {fmtBytes(s.raw_bytes)}</span>
        <span><i className="sb-parquet" /> Normalized Parquet {fmtBytes(s.parquet_bytes)}</span>
        <span><i className="sb-meta" /> Manifests/logs {fmtBytes(s.metadata_bytes)}</span>
        <span className="muted">{fmtInt(s.file_count)} files · {fmtInt(s.raw_page_count)} pages</span>
      </div>
      <div className="table-wrap">
        <table className="table table-compact">
          <thead><tr><th>Family</th><th className="num">Rows</th><th className="num">Expected</th><th className="num">Missing</th><th className="num">Pages</th><th>Quality</th></tr></thead>
          <tbody>
            {s.families.map((f) => (
              <tr key={f.family}>
                <td className="mono">{f.family}</td>
                <td className="num mono">{fmtInt(f.rows)}</td>
                <td className="num mono">{f.expected_rows === null ? "—" : fmtInt(f.expected_rows)}</td>
                <td className="num mono">{f.missing_rows === null ? "—" : fmtInt(f.missing_rows)}</td>
                <td className="num mono">{fmtInt(f.pages)}</td>
                <td><Badge tone={statusTone(f.status)}>{f.status.toUpperCase()}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ChunkDetail({ chunk, plan, onPrepare, onCancel, busy }: {
  chunk: CorpusChunk; plan: CorpusStatus["plan"]; onPrepare: () => void; onCancel: (jobId: string) => void; busy: boolean;
}) {
  const local = chunk.local;
  const job = chunk.latest_job;
  const canPrepare = chunk.preparable && chunk.status !== "preparing";
  return (
    <div className="chunk" data-testid="chunk-detail" data-status={chunk.status}>
      <div className="chunk-head">
        <div className="min-0">
          <div className="eyebrow">{chunk.preparable ? "Preparable chunk" : "Planned chunk"}</div>
          <h3 className="chunk-title">{chunk.label}</h3>
          <Mono className="muted">{chunk.chunk_id}</Mono>
        </div>
        <div className="chunk-actions">
          <Badge tone={CHUNK_TONE[chunk.status]} dot testid="chunk-status">{CHUNK_LABEL[chunk.status].toUpperCase()}</Badge>
          {canPrepare && (
            <Button icon={chunk.status === "prepared" ? "shield" : "download"} onClick={onPrepare} disabled={busy}
                    variant={chunk.status === "prepared" ? "secondary" : "primary"} data-testid="prepare-chunk">
              {chunk.status === "prepared" ? "Verify & reuse" : chunk.status === "invalid" ? "Prepare again" : `Prepare ${monthParts(chunk.start).mon} ${monthParts(chunk.start).year}`}
            </Button>
          )}
        </div>
      </div>

      <div className="kv-grid wide chunk-facts">
        <span>Source</span><span>OKX public REST · read-only</span>
        <span>Instrument</span><Mono>{chunk.inst_id} · {plan.bar}</Mono>
        <span>Requested</span>
        <Mono>{fmtTime(chunk.start).replace(":00 UTC", "")} → {fmtTime(chunk.end).replace(":00 UTC", "")} UTC · {span(chunk.start, chunk.end)}, end exclusive</Mono>
        <span>Families</span><span className="small-text">traded · mark · index 1m candles, settled funding, instrument</span>
        <span>Local verification</span>
        <span data-testid="chunk-verification">
          {!local ? <span className="muted">no local dataset</span>
            : local.usable ? <span className="inline-ok"><Icon name="check" size={13} /> verified {fmtTime(local.verified_at)}</span>
              : <span className="text-neg">{local.problem}</span>}
        </span>
        <span>Quality</span>
        <span>{local ? <Badge tone={statusTone(local.quality_status)}>{local.quality_status.toUpperCase()}</Badge> : <span className="muted">—</span>}</span>
        <span>Dataset identity</span>
        <span>{local ? <Mono className="small-text" title={local.manifest_sha256}>{local.dataset_id}</Mono> : <span className="muted">—</span>}</span>
        <span>Local bytes</span>
        <Mono>{local ? fmtBytes(local.bytes_on_disk) : "—"}</Mono>
        <span>Retrieved</span>
        <Mono>{local?.retrieved_at ? fmtTime(local.retrieved_at) : "—"}</Mono>
        <span>Reuse</span>
        <span data-testid="chunk-reuse" className="small-text">
          {local ? local.reuse : chunk.preparable ? "Prepared once, then reused locally — never re-downloaded per run" : "—"}
        </span>
      </div>

      {!chunk.preparable && (
        <Notice tone="info" icon="lock" title="Planned, not preparable yet">
          {chunk.note} Only the initial bootstrap month can be prepared in this version.
        </Notice>
      )}
      {chunk.preparable && chunk.status === "not_prepared" && !job && (
        <Notice tone="info" title="What Prepare does">
          A background corpus worker downloads this one month from OKX's public API (no account, no keys), writes an
          immutable hash-verified dataset, verifies it and binds it here. You can close the browser meanwhile.
        </Notice>
      )}
      {job && <JobProgress job={job} onCancel={() => onCancel(job.job_id)} />}
      {local && <StorageFacts s={local.storage} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// B. Run setup
// ---------------------------------------------------------------------------

function RunSetup({ corpus, onStarted }: { corpus: CorpusStatus | null; onStarted: (e: Evaluation) => void }) {
  const prepared = (corpus?.chunks ?? []).filter((c) => c.status === "prepared");
  const [chunkId, setChunkId] = useState("");
  const [speed, setSpeed] = useState(0);
  const [paused, setPaused] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!prepared.some((c) => c.chunk_id === chunkId)) setChunkId(prepared[0]?.chunk_id ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prepared.map((c) => c.chunk_id).join()]);
  const chunk = prepared.find((c) => c.chunk_id === chunkId);
  const start = async () => {
    setBusy(true);
    try {
      onStarted(await evalApi.start(chunkId, speed, paused));
      setError(null);
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title="Run setup" icon="play" eyebrow="B · Choose a run type" className="setup" testid="run-setup">
      <div className="run-types" role="radiogroup" aria-label="Run type" data-testid="run-types">
        <label className="run-type is-on" data-testid="run-type-market-replay">
          <input type="radio" name="run-type" checked readOnly />
          <span>
            <b>Market replay — data and engine check</b>
            <span className="muted small-text">Replays historical market evidence through the causal engine. No adviser or trade calls are evaluated.</span>
          </span>
          <Badge tone="pos">Available</Badge>
        </label>
        <label className="run-type is-disabled" data-testid="run-type-adviser-backtest" aria-disabled="true">
          <input type="radio" name="run-type" disabled />
          <span>
            <b>Adviser backtest</b>
            <span className="muted small-text">Runs the integrated adviser and call-outcome evaluation on the same engine — unavailable until the adviser exists.</span>
          </span>
          <Badge tone="pending" icon="lock">Unavailable</Badge>
        </label>
        <div className="run-type" data-testid="run-type-deep-validation">
          <span>
            <b>Deep validation</b>
            <span className="muted small-text">Optional diagnostic launched from a finished (or paused) streaming run's panel below: an independent
              reference re-execution of the committed prefix over the canonical feed cache, with its own progress, controls and
              report. Not an independent audit of the original source files; never changes the run.</span>
          </span>
          <Badge tone="info">Implemented · per run</Badge>
        </div>
      </div>
      <Notice tone="warn" icon="compass" title="Observation-only" testid="adviser-notice">{NOT_CONNECTED}</Notice>
      <Field label="Prepared corpus chunk">
        <select className="control" value={chunkId} onChange={(e) => setChunkId(e.target.value)} data-testid="eval-chunk"
                disabled={!prepared.length}>
          {!prepared.length && <option value="">none prepared yet (stage A)</option>}
          {prepared.map((c) => <option key={c.chunk_id} value={c.chunk_id}>{c.label} · {c.chunk_id}</option>)}
        </select>
      </Field>
      {chunk?.local && (
        <div className="setup-facts">
          <Badge tone="info" icon="clock">Modeled availability</Badge>
          <Badge tone={statusTone(chunk.local.quality_status)}>{chunk.local.quality_status.toUpperCase()}</Badge>
          <Badge tone="pos" icon="shield">Verified</Badge>
          <span className="muted small-text mono">{fmtBytes(chunk.local.bytes_on_disk)}</span>
        </div>
      )}
      <Field label="Replay pacing" hint="Operational only — never changes order, state or digests. Max = as fast as the worker can.">
        <select className="control" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} data-testid="eval-speed">
          {[...PACING].reverse().map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </Field>
      <label className="check">
        <input type="checkbox" checked={paused} onChange={(e) => setPaused(e.target.checked)} data-testid="eval-paused" />
        <span>Start paused <span className="muted">(step one event at a time before playing)</span></span>
      </label>
      {error && <Notice tone="neg" title="Launch failed">{error}</Notice>}
      <Button icon="play" className="btn-block" onClick={start} disabled={!chunk || busy} data-testid="start-evaluation">
        Start market replay
      </Button>
      <p className="muted small-text">No model parameters: there is no adviser to configure yet.</p>
    </Card>
  );
}

function EvaluationList({ items, selected, onSelect }: {
  items: Evaluation[] | null; selected: string | null; onSelect: (id: string) => void;
}) {
  return (
    <Card title="Evaluations" icon="gauge" className="rail-list-card" actions={<span className="count-chip mono">{items?.length ?? 0}</span>}>
      {items && items.length === 0 ? (
        <EmptyState icon="gauge" title="No evaluation yet">Prepared chunks can be evaluated from Run setup.</EmptyState>
      ) : (
        <ul className="list" aria-label="Evaluations" data-testid="eval-list">
          {(items ?? []).map((e) => {
            const p = e.replay.progress;
            return (
              <li key={e.evaluation_id}>
                <button type="button" className={cx("list-item", e.evaluation_id === selected && "is-selected")}
                        aria-current={e.evaluation_id === selected ? "true" : undefined} onClick={() => onSelect(e.evaluation_id)}>
                  <span className="list-item-title mono">{e.evaluation_id}</span>
                  <span className="list-item-meta">
                    <Badge tone={statusTone(e.replay.runtime_state)} dot>{humanize(e.replay.runtime_state).toUpperCase()}</Badge>
                    <span className="mono muted">{fmtInt(p.applied_events)}/{p.total_events === null ? "PENDING" : fmtInt(p.total_events)}</span>
                  </span>
                  <span className="list-item-sub">{e.corpus.chunk_label} · market replay · {e.replay.operation.phase_label}</span>
                  <span className="mini-progress real" aria-hidden>
                    <span style={{ width: `${(p.applied_events / (p.total_events || 1)) * 100}%` }} />
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// C. Run & report
// ---------------------------------------------------------------------------

function ReportCard({ ev }: { ev: Evaluation }) {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [copied, setCopied] = useState<"idle" | "copied" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const terminal = TERMINAL.has(ev.replay.status);
  useEffect(() => {
    setReport(null);
    setCopied("idle");
    if (!terminal) return;  // terminal reports are fetched once; snapshots are generated on Copy/Download
    evalApi.report(ev.evaluation_id).then(setReport).catch((e) => setError((e as Error).message));
  }, [ev.evaluation_id, terminal, ev.replay.has_manifest]);

  const copy = async () => {
    try {
      await copyText(await evalApi.reportMarkdown(ev.evaluation_id));
      setCopied("copied");
      window.setTimeout(() => setCopied("idle"), 4000);
    } catch (e) {
      setCopied("error");
      setError((e as Error).message);
    }
  };

  const actions = (
    <div className="report-actions">
      <Button icon={copied === "copied" ? "check" : "copy"} onClick={copy} data-testid="copy-report">
        {copied === "copied" ? "Copied — paste into chat" : terminal ? "Copy report for chat" : "Copy diagnostic snapshot for chat"}
      </Button>
      <a className="btn btn-secondary" href={evalApi.downloadUrl(ev.evaluation_id, "md")} data-testid="download-md">
        <Icon name="download" size={15} /><span>Markdown</span>
      </a>
      <a className="btn btn-secondary" href={evalApi.downloadUrl(ev.evaluation_id, "json")} data-testid="download-json">
        <Icon name="download" size={15} /><span>JSON</span>
      </a>
    </div>
  );
  if (!terminal) {
    const op = ev.replay.operation;
    return (
      <Card title="Report" icon="file" eyebrow="C · Diagnostic snapshot (incomplete)" testid="report-card" state="snapshot"
            className="report-card" actions={actions}>
        {error && <Notice tone="neg" title="Report error">{error}</Notice>}
        <Notice tone="info" title="Not a result yet" testid="report-snapshot-note">
          The run is {op.status} in phase {op.phase_label.toLowerCase()} (health: {op.health_label.toLowerCase()}, assurance:{" "}
          {op.assurance.state.replace("_", " ")}). Copy produces a diagnostic snapshot from persisted facts with its capture
          time; the terminal report appears when the run completes, is cancelled or fails.
        </Notice>
      </Card>
    );
  }
  const verdictTone: Tone = report?.conclusion.verdict === "WORKFLOW_VALID" ? "pos"
    : report?.conclusion.verdict === "INCOMPLETE_CANCELLED" ? "warn" : "neg";
  const caps = report ? Object.entries(report.capabilities) : [];
  return (
    <Card title="Report" icon="file" eyebrow="C · Copyable evaluation report" testid="report-card" state="ready"
          className="report-card" actions={actions}>
      {error && <Notice tone="neg" title="Report error">{error}</Notice>}
      {!report ? <Skeleton lines={4} /> : (
        <>
          <div className={cx("verdict", `tone-${verdictTone}`)} data-testid="report-verdict">
            <div className="verdict-kind mono">{report.report_kind}</div>
            <div className="verdict-main">{humanize(report.conclusion.verdict)}</div>
            <p className="verdict-text">{report.conclusion.text}</p>
          </div>
          <div className="metric-grid compact">
            <Metric label="Coverage" value={<span data-testid="report-completion">{report.completion}</span>}
                    hint={`${fmtInt(report.coverage.applied_events)}/${report.coverage.total_events === null ? "PENDING" : fmtInt(report.coverage.total_events)} feed events`} />
            <Metric label="Validation" mono={false}
                    value={<Badge tone={!report.validation.ran || report.validation.outcome === "incomplete" ? "warn"
                      : report.validation.passed ? "pos" : "neg"}>
                      {!report.validation.ran ? "NOT RUN" : report.validation.outcome === "incomplete" ? "INCOMPLETE"
                        : report.validation.passed ? "PASS" : "FAIL"}</Badge>}
                    hint={`${report.validation.checks.filter((c) => c.passed).length}/${report.validation.checks.length} checks`
                      + (report.validation.validator ? ` · ${report.validation.validator}` : "")} />
            <Metric label="Final information time" value={fmtTime(report.coverage.final_information_time)} />
            <Metric label="Runtime" value={fmtSecs(report.runtime.elapsed_seconds)}
                    hint={report.runtime.throughput_events_per_second
                      ? `${report.runtime.throughput_events_per_second.toFixed(1)} events/s` : undefined} />
            <Metric label="Recoveries" value={`${report.runtime.recoveries}`} hint={`attempts ${report.runtime.attempts}/${report.runtime.max_attempts}`} />
            <Metric label="Quality" value={report.quality_status.toUpperCase()} />
          </div>
          {report.stopped_at && (
            <Notice tone="warn" title="Incomplete coverage" testid="report-stopped">
              Stopped at {fmtInt(report.stopped_at.applied_events)}/{report.stopped_at.total_events === null ? "PENDING" : fmtInt(report.stopped_at.total_events)} events
              (information time {fmtTime(report.stopped_at.information_time)}). {report.stopped_at.reason ?? ""}
            </Notice>
          )}
          <div className="cap-table" data-testid="report-capabilities">
            <div className="cap-table-head">
              <span className="eyebrow">Adviser metrics</span>
              <span className="muted small-text">Reason: no professional adviser connected yet — shown as unavailable, never as zero.</span>
            </div>
            <ul>
              {caps.map(([k, c]) => (
                <li key={k}>
                  <span>{c.label ?? "Professional adviser"}</span>
                  <Badge tone="pending" icon={k === "professional_adviser" ? "clock" : undefined}>{humanize(c.status)}</Badge>
                </li>
              ))}
            </ul>
          </div>
          <p className="small-text muted">Next: {report.next_diagnostic}</p>
        </>
      )}
    </Card>
  );
}

function useSampledBars(replayId: string | null, cursor: number) {
  const [bars, setBars] = useState<TradedBar[]>([]);
  const last = useRef(0);
  const timer = useRef<number | null>(null);
  const wanted = useRef(-1);
  useEffect(() => {
    setBars([]);
    last.current = 0;
    wanted.current = -1;
  }, [replayId]);
  useEffect(() => {
    if (!replayId || cursor === wanted.current) return;
    wanted.current = cursor;
    const run = () => {
      timer.current = null;
      last.current = Date.now();
      barsTail(replayId, CHART_TAIL).then((b) => setBars(b.bars)).catch(() => undefined);
    };
    const wait = CHART_MIN_INTERVAL_MS - (Date.now() - last.current);
    if (wait <= 0) run();
    else if (timer.current === null) timer.current = window.setTimeout(run, wait);
  }, [replayId, cursor]);
  useEffect(() => () => { if (timer.current !== null) window.clearTimeout(timer.current); }, []);
  return bars;
}

function ActiveRun({ ev, onReplay }: { ev: Evaluation; onReplay: (r: ObsReplay) => void }) {
  const rid = ev.replay.replay_id;
  const [doc, setDoc] = useState<ObsStateDoc | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manifestOpen, setManifestOpen] = useState(false);
  const [manifest, setManifest] = useState<Awaited<ReturnType<typeof obsApi.manifest>> | null>(null);

  useEffect(() => {
    setDoc(null);
    setManifest(null);
    let closed = false;
    const onDoc = (d: ObsStateDoc) => {
      if (closed) return;
      setDoc(d);
      onReplay(d.replay);
    };
    obsApi.state(rid).then(onDoc).catch((e) => setError((e as Error).message));
    const es = new EventSource(`/api/observations/${rid}/stream`);
    es.addEventListener("open", () => setLive(true));
    es.addEventListener("snapshot", (m) => onDoc(JSON.parse((m as MessageEvent).data) as ObsStateDoc));
    es.addEventListener("end", () => { setLive(false); es.close(); });
    es.addEventListener("error", () => setLive(false));
    return () => { closed = true; es.close(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rid]);

  const r = doc?.replay ?? ev.replay;
  const bars = useSampledBars(rid, r.progress.applied_events);
  useEffect(() => {
    if (r.has_manifest && manifestOpen && !manifest) void obsApi.manifest(rid).then(setManifest);
  }, [r.has_manifest, manifestOpen, manifest, rid]);

  const command = async (fn: () => Promise<ObsReplay>) => {
    try {
      onReplay(await fn());
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="run-stack" data-testid="active-run">
      {error && <Notice tone="neg" title="Something went wrong">{error}</Notice>}
      <ReplayPanel r={r} live={live} onCommand={command} eyebrow={`Market replay — data and engine check · ${ev.corpus.chunk_label}`} />
      <div className="boundary" data-testid="intelligence-boundary">
        <Icon name="compass" size={18} />
        <div>
          <strong>No adviser in this run.</strong> Candles and observable state are real historical evidence replayed
          causally; no market view, call, target or outcome is derived from them.
        </div>
        <Badge tone="pending" icon="clock">Adviser pending</Badge>
      </div>
      <Card title="Traded price" icon="market" testid="market-chart"
            eyebrow={`Latest ${CHART_TAIL} completed 1m bars as causally delivered · chart refreshes at most once per second`}
            actions={<Badge tone="brand">REAL · HISTORICAL</Badge>}>
        <MarketChart bars={bars} informationTime={r.progress.information_time} />
      </Card>
      <ReportCard ev={{ ...ev, replay: r, report_available: true, report_terminal: TERMINAL.has(r.status) }} />
      <DeepValidationPanel r={r} />
      <ObservableStatePanel state={doc?.state ?? null} />
      {r.has_manifest && (
        <details className="more" onToggle={(e) => setManifestOpen((e.target as HTMLDetailsElement).open)}>
          <summary><Icon name="chevron" size={14} className="summary-chevron" /> Replay artifacts and validation checks</summary>
          {manifest ? <Artifacts m={manifest} /> : <Skeleton lines={3} />}
        </details>
      )}
      <p className="muted small-text">
        Detailed inspection (evidence timeline, per-delivery changes) stays in{" "}
        <a href={`#replay/obs=${rid}`} data-testid="open-in-replay-lab">Replay Lab</a>.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function Backtest() {
  const corpusPoll = usePoll(corpusApi.status, 2000);
  const evalsPoll = usePoll(evalApi.list, 3000);
  const corpus = corpusPoll.data;
  const [chunkSel, setChunkSel] = useState<string | null>(null);
  const [evalSel, setEvalSel] = useState<string | null>(evalFromHash());
  const [evDetail, setEvDetail] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chunkId = chunkSel ?? corpus?.chunks.find((c) => c.preparable)?.chunk_id ?? corpus?.chunks[0]?.chunk_id ?? null;
  const chunk = corpus?.chunks.find((c) => c.chunk_id === chunkId) ?? null;
  const evals = evalsPoll.data;
  const selectedId = evalSel ?? evals?.[0]?.evaluation_id ?? null;

  useEffect(() => {
    if (!selectedId) { setEvDetail(null); return; }
    replaceHash(`backtest/ev=${selectedId}`);
    let alive = true;
    evalApi.detail(selectedId).then((d) => alive && setEvDetail(d)).catch((e) => alive && setError((e as Error).message));
    return () => { alive = false; };
  }, [selectedId]);

  const onReplay = useCallback((r: ObsReplay) => {
    setEvDetail((d) => (d && d.replay.replay_id === r.replay_id
      ? { ...d, replay: r, report_available: true, report_terminal: TERMINAL.has(r.status) } : d));
  }, []);

  const prepare = async () => {
    if (!chunk) return;
    setBusy(true);
    try {
      await corpusApi.prepare(chunk.chunk_id);
      setError(null);
      await corpusPoll.refresh();
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    } finally {
      setBusy(false);
    }
  };
  const cancelPrep = async (jobId: string) => {
    try {
      await corpusApi.cancel(jobId);
      await corpusPoll.refresh();
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    }
  };
  const onStarted = (e: Evaluation) => {
    setEvalSel(e.evaluation_id);
    setEvDetail(e);
    void evalsPoll.refresh();
  };

  const target = corpus?.plan.target;
  const listItems = useMemo(() => evals?.map((e) => (evDetail && e.evaluation_id === evDetail.evaluation_id ? evDetail : e)) ?? null,
    [evals, evDetail]);

  return (
    <div className="page page-backtest" data-testid="page-backtest">
      <PageHeader
        eyebrow="Owner workflow · historical evaluation"
        title="Historical Workbench"
        lede="Prepare the fixed BTC corpus once, reuse it locally, launch a durable market replay (data and engine check) and copy an honest report or diagnostic snapshot into chat at any time. The professional adviser's backtest plugs into this same page when it exists."
        meta={<Badge tone="brand" icon="clock" testid="historical-mode">HISTORICAL MODE</Badge>}
      />
      <div className="history-banner" data-testid="history-banner">
        <Icon name="replay" size={18} />
        <div>
          <strong>HISTORICAL · OBSERVATION ONLY</strong> — past OKX evidence replayed on a simulated clock with modeled
          availability. Nothing here is live, and no trade call exists yet.
        </div>
      </div>
      {error && <Notice tone="neg" title="Something went wrong">{error}</Notice>}
      <StageRail corpus={corpus} ev={evDetail} />

      <Card className="corpus-card" testid="corpus-card" eyebrow="A · Historical corpus"
            title={corpus ? `BTC corpus · ${utcDay(target!.start)} → ${utcDay(target!.end)}` : "BTC corpus"} icon="data"
            actions={corpus && (
              <span className="corpus-summary">
                <Badge tone="pos" testid="corpus-prepared-count">{corpus.summary.prepared} prepared</Badge>
                <Badge tone="pending" icon="lock">{corpus.summary.planned_locked} planned</Badge>
                {corpus.summary.prepared_bytes > 0 && <span className="mono muted small-text">{fmtBytes(corpus.summary.prepared_bytes)} local</span>}
              </span>
            )}>
        {!corpus ? (corpusPoll.error ? <Notice tone="neg" title="Corpus unavailable">{corpusPoll.error}</Notice> : <Skeleton lines={4} />) : (
          <>
            <p className="corpus-lede">
              {corpus.plan.description.replace(/\.?$/, ".")} Plan <Mono>{corpus.plan.plan_id}</Mono> v{corpus.plan.plan_version} ·{" "}
              {corpus.plan.chunk_rule} · target start inclusive, end exclusive (UTC).
            </p>
            <CorpusLedger corpus={corpus} selected={chunkId} onSelect={setChunkSel} />
            {chunk && <ChunkDetail chunk={chunk} plan={corpus.plan} onPrepare={prepare} onCancel={cancelPrep} busy={busy} />}
          </>
        )}
      </Card>

      <div className="bt-grid">
        <div className="bt-rail">
          <RunSetup corpus={corpus} onStarted={onStarted} />
          <EvaluationList items={listItems} selected={selectedId} onSelect={setEvalSel} />
        </div>
        <div className="bt-main">
          {!evDetail ? (
            <Card eyebrow="C · Run & report">
              <EmptyState icon="gauge" title="No evaluation selected">
                Prepare the bootstrap month in stage A, then start an observation-only evaluation. Candles, progress,
                controls and the copyable report appear here.
              </EmptyState>
            </Card>
          ) : <ActiveRun key={evDetail.evaluation_id} ev={evDetail} onReplay={onReplay} />}
        </div>
      </div>
    </div>
  );
}
