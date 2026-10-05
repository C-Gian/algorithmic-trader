import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  barsTail, corpusApi, CorpusChunk, CorpusJob, CorpusStatus, evalApi, Evaluation, EvaluationReport, obsApi, ObsReplay,
  ObsStateDoc, packApi, PackListItem, PresetsResponse, StorageSummary, TradedBar,
} from "../api";
import { PackPrepare } from "./PackPrep";
import { fmtBytes, fmtInt, fmtSecs, fmtTime, humanize } from "../lib/format";
import { evalFromHash, replaceHash } from "../lib/route";
import { usePoll } from "../lib/usePoll";
import { Icon } from "../ui/Icon";
import {
  Badge, Button, Card, cx, EmptyState, Field, Metric, Mono, Notice, PageHeader, Skeleton, statusTone, Tone,
} from "../ui/primitives";
import { DeepValidationPanel } from "./replay/DeepValidation";
import { MarketChart } from "./replay/MarketChart";
import {
  Artifacts, CopyDiagnostics, ObservableStatePanel, OperationPanel, PACING, phaseText, ReplayPanel, useCopyFeedback,
} from "./replay/MarketReplay";
import { runStory } from "./replay/runStory";
import { AdviserProgress, AdviserSummary, CallTimeline } from "./AdviserResult";

// Historical Workbench (route #backtest kept): the Owner's evaluation workbench, organised as one guided task
// (prepare data -> start a check -> follow it and get the report) over the SAME machinery:
//   1. data   - checked-in logical plan + locally prepared, verified immutable datasets (details on demand);
//   2. start  - explicit run types next to their settings: Adviser evaluation (MP-001 adviser + separate hypothetical
//               evaluator, packs only) and Market replay (data and engine check); Deep validation is an optional
//               diagnostic launched explicitly from a finished/paused run (its own durable job);
//   3. result - plain run status with its controls, then the result/report (Copy for chat) directly below, then
//               chart, optional Deep validation and every technical detail behind progressive disclosure.
// Market replay runs stay observation-only; adviser evaluation results come only from committed journal/records.

const NOT_CONNECTED =
  "Market replay: this run validates data/replay/product workflow only; it makes and judges no trade calls.";
const ADVISER_NOTICE =
  "Adviser evaluation: the integrated adviser runs causally over the pack; outcomes are a separate normalized hypothetical simulation (one abstract unit, 60 s delay, declared costs) — never fills, size, leverage or account results.";
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
  const { mon, year } = monthParts(chunk.start);
  const plain = chunk.status === "prepared" && local?.usable
    ? `Ready. This data is stored on this computer and was verified ${local.verified_at ? `on ${fmtTime(local.verified_at)}` : "locally"}. Nothing is downloaded again — go to step 2.`
    : chunk.status === "preparing" ? "Preparing: the data is being downloaded and verified in the background. You can leave this page; progress is saved."
      : chunk.status === "invalid" ? `This month needs attention: ${local?.problem ?? "the stored data failed verification"}. Prepare it again to restore a verified copy.`
        : chunk.status === "planned" ? "Planned for later — this month cannot be prepared in this version yet."
          : "Not on this computer yet. Prepare downloads this month once from OKX's public API (no account, no keys), verifies it and keeps it for every later check.";
  return (
    <div className="chunk" data-testid="chunk-detail" data-status={chunk.status}>
      <div className="chunk-head">
        <div className="min-0">
          <div className="eyebrow">{chunk.preparable ? "Selected month" : "Planned month"}</div>
          <h3 className="chunk-title">{chunk.label}</h3>
          <p className="chunk-plain" data-testid="chunk-plain">{plain}</p>
        </div>
        <div className="chunk-actions">
          <Badge tone={CHUNK_TONE[chunk.status]} dot testid="chunk-status">{CHUNK_LABEL[chunk.status].toUpperCase()}</Badge>
          {canPrepare && (
            <Button icon={chunk.status === "prepared" ? "shield" : "download"} onClick={onPrepare} disabled={busy}
                    variant={chunk.status === "prepared" ? "secondary" : "primary"} data-testid="prepare-chunk"
                    title={chunk.status === "prepared" ? "Re-check the stored data's hashes; nothing is downloaded" : undefined}>
              {chunk.status === "prepared" ? "Verify again" : chunk.status === "invalid" ? "Prepare again" : `Prepare ${mon} ${year}`}
            </Button>
          )}
        </div>
      </div>

      {!chunk.preparable && (
        <Notice tone="info" icon="lock" title="Planned, not preparable yet">
          {chunk.note} Only the initial bootstrap month can be prepared in this version.
        </Notice>
      )}
      {job && <JobProgress job={job} onCancel={() => onCancel(job.job_id)} />}

      <details className="more inset" data-testid="chunk-more">
        <summary><Icon name="chevron" size={14} className="summary-chevron" /> Data details
          <span className="summary-hint">source, period, verification, dataset identity and measured storage</span>
        </summary>
        <div className="more-body">
          <div className="kv-grid wide chunk-facts">
            <span>Chunk id</span><Mono>{chunk.chunk_id}</Mono>
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
          {local && <StorageFacts s={local.storage} />}
        </div>
      </details>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2. Start a check
// ---------------------------------------------------------------------------

function RunSetup({ corpus, preferred, packs, presets, onStarted }: {
  corpus: CorpusStatus | null; preferred: string | null; packs: PackListItem[]; presets: PresetsResponse | null;
  onStarted: (e: Evaluation) => void;
}) {
  const prepared = (corpus?.chunks ?? []).filter((c) => c.status === "prepared");
  const usablePacks = packs.filter((x) => x.usable);
  const [source, setSource] = useState("");
  const [picked, setPicked] = useState(false); // the Owner chose a source explicitly
  const [ack, setAck] = useState(false);
  const [chunkId, setChunkId] = useState("");
  const [speed, setSpeed] = useState(0);
  const [paused, setPaused] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // default: Adviser evaluation when a pack is selected, Market replay otherwise, until the Owner picks explicitly
  const [runChoice, setRunType] = useState<"adviser_evaluation" | "observation_only" | null>(null);
  const ids = prepared.map((c) => c.chunk_id).join();
  useEffect(() => {
    // follow the month selected in step 1 when it is prepared; otherwise keep a valid prepared month
    if (preferred && prepared.some((c) => c.chunk_id === preferred)) setChunkId(preferred);
    else if (!prepared.some((c) => c.chunk_id === chunkId)) setChunkId(prepared[0]?.chunk_id ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids, preferred]);
  const packKey = usablePacks.map((x) => x.pack_id).join();
  useEffect(() => {
    // evaluation packs are the primary source; the earlier single-month datasets stay selectable
    if (!picked || !source || (source.startsWith("pack:") && !usablePacks.some((x) => `pack:${x.pack_id}` === source))) {
      setSource(usablePacks[0] ? `pack:${usablePacks[0].pack_id}` : "month");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [packKey]);
  useEffect(() => setAck(false), [source]);
  const pack = usablePacks.find((x) => `pack:${x.pack_id}` === source) ?? null;
  const packView = pack ? presets?.presets.find((v) => v.published?.pack_id === pack.pack_id) ?? null : null;
  const chunk = source === "month" ? prepared.find((c) => c.chunk_id === chunkId) : undefined;
  const needsAck = pack?.status === "READY_WITH_LIMITATIONS";
  const runType = !pack ? "observation_only" : (runChoice ?? "adviser_evaluation");
  const adviser = runType === "adviser_evaluation";
  const canStart = pack ? !needsAck || ack : !!chunk && runType === "observation_only";
  const start = async () => {
    setBusy(true);
    try {
      onStarted(pack ? await evalApi.startPack(pack.pack_id, speed, paused, ack, runType)
        : await evalApi.start(chunkId, speed, paused));
      setError(null);
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="setup-grid" data-testid="run-setup">
      <div className="setup-what">
        <div className="setup-col-title">What will run</div>
        <div className="run-types" role="radiogroup" aria-label="Run type" data-testid="run-types">
          <label className={cx("run-type", runType === "adviser_evaluation" ? "is-on" : undefined, !pack && "is-disabled")}
                 data-testid="run-type-adviser">
            <input type="radio" name="run-type" checked={runType === "adviser_evaluation"} disabled={!pack}
                   onChange={() => setRunType("adviser_evaluation")} data-testid="run-type-adviser-input" />
            <span>
              <b>Adviser evaluation</b>
              <span className="muted small-text">Runs the integrated adviser (MP-001 v0.2: market view, A/B/C candidates,
                persistent calls) causally over the prepared pack, then scores its calls with a separate hypothetical
                evaluator. Needs a prepared evaluation pack.</span>
            </span>
            <Badge tone={pack ? "pos" : "pending"}>{pack ? "Available" : "Needs a pack"}</Badge>
          </label>
          <label className={cx("run-type", runType === "observation_only" && "is-on")} data-testid="run-type-market-replay">
            <input type="radio" name="run-type" checked={runType === "observation_only"}
                   onChange={() => setRunType("observation_only")} data-testid="run-type-market-replay-input" />
            <span>
              <b>Market replay — data and engine check</b>
              <span className="muted small-text">Replays the real market data in time order through the engine and
                checks that everything was processed correctly. It does not make or judge trade calls.</span>
            </span>
            <Badge tone="pos">Available</Badge>
          </label>
          <div className="run-type is-planned" data-testid="run-type-deep-validation">
            <span>
              <b>Deep validation <span className="muted">(optional, later)</span></b>
              <span className="muted small-text">An extra check you can start from a finished run in step 3: a reference
                re-execution of the committed prefix over the canonical feed cache, along a separate execution path but with
                the same reducer code, with its own progress and report. Not a wholly independent method or an audit of the
                original source files; never changes the run.</span>
            </span>
            <Badge tone="info">Implemented · per run</Badge>
          </div>
        </div>
        {adviser ? (
          <Notice tone="info" icon="compass" title="Hypothetical evaluation" testid="adviser-notice">{ADVISER_NOTICE}</Notice>
        ) : (
          <Notice tone="warn" icon="compass" title="Observation-only" testid="adviser-notice">{NOT_CONNECTED}</Notice>
        )}
      </div>

      <div className="setup-how">
        <div className="setup-col-title">Settings</div>
        <Field label="Data to check" hint="Prepared evaluation packs (step 1); earlier single-month datasets stay available.">
          <select className="control" value={source} onChange={(e) => { setPicked(true); setSource(e.target.value); }} data-testid="eval-source">
            {usablePacks.map((x) => (
              <option key={x.pack_id} value={`pack:${x.pack_id}`}>
                {presets?.presets.find((v) => v.published?.pack_id === x.pack_id)?.preset.label ?? x.preset_id} · pack
                {x.status === "READY_WITH_LIMITATIONS" ? " · with limitations" : ""}
              </option>
            ))}
            <option value="month">Single month (earlier workflow)</option>
          </select>
        </Field>
        {source === "month" && (
          <Field label="Month to check" hint={prepared.length ? "Prepared months only." : undefined}>
            <select className="control" value={chunkId} onChange={(e) => setChunkId(e.target.value)} data-testid="eval-chunk"
                    disabled={!prepared.length}>
              {!prepared.length && <option value="">none prepared yet</option>}
              {prepared.map((c) => <option key={c.chunk_id} value={c.chunk_id}>{c.label} · {c.chunk_id}</option>)}
            </select>
          </Field>
        )}
        {adviser && (
          <div className="setup-facts" data-testid="eval-adviser-pins">
            <Badge tone="brand" icon="shield">MP-001 v0.2</Badge>
            <Badge tone="info" title="Historical execution profile: modeled trade-minute closes, never measured quotes">HISTORICAL_BASE</Badge>
            <Badge tone="info" title="Funding completeness unproven: total net is unavailable">Price-net only</Badge>
            <Badge tone="pending" title="No historical as-known event calendar">Calendar unknown</Badge>
            <span className="muted small-text">Pinned preset/profile; no parameter choices. Development data only.</span>
          </div>
        )}
        {pack && (
          <div className="setup-facts" data-testid="eval-pack-facts">
            <Badge tone="pos" icon="shield">Verified pack</Badge>
            <Badge tone={pack.status === "READY" ? "pos" : "warn"}>{pack.status === "READY" ? "Ready" : "Ready with limitations"}</Badge>
            <Badge tone="info" icon="clock" title="Historical knowledge times follow a declared convention; they are not measured">Modeled availability</Badge>
            <span className="muted small-text mono">{fmtInt(pack.event_count)} events · warmup and tail are not scored</span>
          </div>
        )}
        {needsAck && (
          <Notice tone="warn" title="This pack has source gaps" testid="eval-ack-notice">
            {(packView?.published?.limitations ?? ["missing or rejected minutes are kept as explicit gaps, never filled"]).join(" · ")}
            <label className="check">
              <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} data-testid="eval-ack" />
              <span>I understand: this inspection run includes these gaps and is not complete market coverage.</span>
            </label>
          </Notice>
        )}
        {chunk?.local && (
          <div className="setup-facts">
            <Badge tone="pos" icon="shield">Verified</Badge>
            <Badge tone={statusTone(chunk.local.quality_status)}
                   title="DEGRADED means some minutes are missing in the source; they are reported, never filled in">
              Quality {chunk.local.quality_status.toUpperCase()}</Badge>
            <Badge tone="info" icon="clock" title="Historical knowledge times follow a declared convention; they are not measured">Modeled availability</Badge>
            <span className="muted small-text mono">{fmtBytes(chunk.local.bytes_on_disk)}</span>
          </div>
        )}
        <Field label="Replay speed" hint="Only changes how long it takes — never the result. “max” is recommended for a check.">
          <select className="control" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} data-testid="eval-speed">
            {[...PACING].reverse().map((p) => <option key={p.value} value={p.value}>{p.label}{p.value === 0 ? " (recommended)" : ""}</option>)}
          </select>
        </Field>
        <label className="check">
          <input type="checkbox" checked={paused} onChange={(e) => setPaused(e.target.checked)} data-testid="eval-paused" />
          <span>Start paused <span className="muted">(advanced: step one event at a time before playing)</span></span>
        </label>
        {error && <Notice tone="neg" title="Could not start">{error}</Notice>}
        <Button icon="play" className="btn-block btn-lg" onClick={start} disabled={!canStart || busy} data-testid="start-evaluation">
          {adviser ? "Start adviser evaluation · prepared pack" : pack ? "Start the check · prepared pack"
            : chunk ? `Start the check · ${chunk.label}` : "Start the check"}
        </Button>
        <p className="muted small-text">
          {pack || chunk ? "Starts in the background — you can close the browser; progress and the report appear in step 3."
            : "Prepare data in step 1 first. No model parameters to choose: the method and profile are pinned."}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 3. Runs, progress and report
// ---------------------------------------------------------------------------

function RunPicker({ items, selected, onSelect }: {
  items: Evaluation[] | null; selected: string | null; onSelect: (id: string) => void;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div className="run-picker-wrap">
      <div className="setup-col-title">Your runs <span className="count-chip mono">{items.length}</span>
        <span className="muted small-text"> · newest first — select one to see its progress and report</span></div>
      <ul className="run-picker" aria-label="Runs" data-testid="eval-list">
        {items.map((e) => {
          const p = e.replay.progress;
          const story = runStory(e.replay);
          const committed = p.committed_events ?? p.applied_events;
          return (
            <li key={e.evaluation_id}>
              <button type="button" className={cx("run-chip", `tone-${story.tone}`, e.evaluation_id === selected && "is-selected")}
                      aria-current={e.evaluation_id === selected ? "true" : undefined} onClick={() => onSelect(e.evaluation_id)}
                      title={`${e.evaluation_id} · replay ${e.replay.replay_id}`}>
                <span className="run-chip-top">
                  <span className="run-chip-title">{e.corpus.chunk_label}</span>
                  <Badge tone={statusTone(e.replay.runtime_state)} dot>{story.title}</Badge>
                </span>
                <span className="run-chip-sub mono">{fmtTime(e.created_at).slice(0, 16)} · {fmtInt(committed)}/{p.total_events === null ? "?" : fmtInt(p.total_events)}</span>
                <span className="mini-progress real" aria-hidden>
                  <span style={{ width: `${(committed / (p.total_events || 1)) * 100}%` }} />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

const VERDICT_TITLE: Record<string, string> = {
  ADVISER_EVALUATION_COMPLETED: "Adviser evaluation completed",
  WORKFLOW_VALID: "Data and engine check passed",
  INCOMPLETE_CANCELLED: "Check not completed (cancelled)",
  OPERATIONAL_FAILURE: "Check failed — needs diagnosis",
};

function ReportCard({ ev }: { ev: Evaluation }) {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [copied, runCopy] = useCopyFeedback();
  const [error, setError] = useState<string | null>(null);
  const terminal = TERMINAL.has(ev.replay.status);
  useEffect(() => {
    // re-fetch when the run becomes terminal or its manifest appears; the copy confirmation is NOT reset here
    // (a late manifest/terminal update must never erase a "Copied" the person just saw)
    setReport(null);
    if (!terminal) return;  // terminal reports are fetched once; snapshots are generated on Copy/Download
    evalApi.report(ev.evaluation_id).then(setReport).catch((e) => setError((e as Error).message));
  }, [ev.evaluation_id, terminal, ev.replay.has_manifest]);

  const copy = async () => {
    if (!(await runCopy(() => evalApi.reportMarkdown(ev.evaluation_id)))) {
      setError("Copy to the clipboard failed — use the Markdown download instead.");
    }
  };

  const actions = (
    <div className="report-actions">
      <Button icon={copied === "copied" ? "check" : "copy"} onClick={copy} data-testid="copy-report"
              variant={terminal ? "primary" : "secondary"} className={terminal ? "btn-lg" : undefined}>
        {copied === "copied" ? "Copied — paste into chat" : copied === "error" ? "Copy failed — use Markdown download"
          : terminal ? "Copy report for chat" : "Copy diagnostic snapshot for chat"}
      </Button>
      <a className="btn btn-secondary" href={evalApi.downloadUrl(ev.evaluation_id, "md")} data-testid="download-md"
         title="Download the same report as a Markdown file">
        <Icon name="download" size={15} /><span>Markdown</span>
      </a>
      <a className="btn btn-secondary" href={evalApi.downloadUrl(ev.evaluation_id, "json")} data-testid="download-json"
         title="Download the structured report (JSON)">
        <Icon name="download" size={15} /><span>JSON</span>
      </a>
    </div>
  );
  if (!terminal) {
    const op = ev.replay.operation;
    return (
      <Card title="Result and report" icon="file" eyebrow="Not ready yet" testid="report-card" state="snapshot"
            className="report-card">
        {error && <Notice tone="neg" title="Report error">{error}</Notice>}
        <Notice tone="info" title="The result appears here when the run finishes" testid="report-snapshot-note">
          The run is {op.status} ({phaseText(op).toLowerCase()}; health {op.health_label.toLowerCase()}; assurance{" "}
          {op.assurance.state.replace("_", " ")}). If something looks wrong you can already copy a diagnostic snapshot — it
          states its capture time and is not a result.
        </Notice>
        {actions}
      </Card>
    );
  }
  const verdict = report?.conclusion.verdict ?? "";
  const verdictTone: Tone = verdict === "WORKFLOW_VALID" || verdict === "ADVISER_EVALUATION_COMPLETED" ? "pos"
    : verdict === "INCOMPLETE_CANCELLED" ? "warn" : "neg";
  const adv = report?.adviser ?? null;
  const caps = report ? Object.entries(report.capabilities) : [];
  const v = report?.validation;
  const checksText = !v ? "" : !v.ran ? "NOT RUN" : v.outcome === "incomplete" ? "INCOMPLETE" : v.passed ? "PASS" : "FAIL";
  const checksTone: Tone = !v || !v.ran || v.outcome === "incomplete" ? "warn" : v.passed ? "pos" : "neg";
  const failed = v?.checks.filter((c) => !c.passed) ?? [];
  return (
    <Card title="Result and report" icon="file" eyebrow="Finished run · copy the report into chat" testid="report-card"
          state="ready" className="report-card is-final">
      {error && <Notice tone="neg" title="Report error">{error}</Notice>}
      {!report ? <Skeleton lines={4} /> : (
        <>
          <div className={cx("verdict", `tone-${verdictTone}`)} data-testid="report-verdict">
            <div className="verdict-main">{VERDICT_TITLE[verdict] ?? humanize(verdict)}</div>
            <p className="verdict-text">{report.conclusion.text}</p>
            <div className="verdict-kind mono">{report.report_kind} · verdict {humanize(verdict)}</div>
          </div>

          <ul className="outcome-facts" data-testid="outcome-facts">
            <li className={cx("outcome-fact", `tone-${report.completion === "COMPLETE" ? "pos" : "warn"}`)} data-testid="fact-operation">
              <span className="outcome-label">1 · The run</span>
              <span className="outcome-value">{ev.replay.status === "completed" ? "Finished" : humanize(ev.replay.status)} ·{" "}
                <span data-testid="report-completion">{report.completion}</span></span>
              <span className="outcome-hint">{fmtInt(report.coverage.applied_events)}/{report.coverage.total_events === null ? "PENDING" : fmtInt(report.coverage.total_events)} events replayed · {fmtSecs(report.runtime.elapsed_seconds)}</span>
            </li>
            <li className={cx("outcome-fact", `tone-${checksTone}`)} data-testid="fact-checks">
              <span className="outcome-label">2 · Integrity checks</span>
              <span className="outcome-value"><Badge tone={checksTone}>{checksText}</Badge>{" "}
                {v && `${v.checks.filter((c) => c.passed).length}/${v.checks.length} passed`}</span>
              <span className="outcome-hint">The run's own checks (bounded reconciliation) — not a reference re-execution;
                that is the optional Deep validation below.</span>
            </li>
            {adv && !adv.pending ? (
              <li className={cx("outcome-fact", adv.calls.count ? "tone-pos" : "tone-warn")} data-testid="fact-adviser">
                <span className="outcome-label">3 · Adviser calls</span>
                <span className="outcome-value">{adv.calls.count} call{adv.calls.count === 1 ? "" : "s"} · {adv.calls.per_evaluated_week}/week</span>
                <span className="outcome-hint">Hypothetical outcomes below are normalized simulations, not fills. Completion and
                  coverage first; no win rate is reported alone.</span>
              </li>
            ) : (
              <li className="outcome-fact tone-pending" data-testid="fact-adviser">
                <span className="outcome-label">3 · Trading adviser</span>
                <span className="outcome-value"><Badge tone="pending">Not in this run</Badge></span>
                <span className="outcome-hint">Market replay makes and judges no trade calls; use an Adviser evaluation for calls.</span>
              </li>
            )}
            {report.pack && (
              <li className={cx("outcome-fact", report.pack.source_coverage.missing_or_rejected ? "tone-warn" : "tone-pos")}
                  data-testid="fact-coverage">
                <span className="outcome-label">4 · Data coverage</span>
                <span className="outcome-value">
                  <Badge tone={report.pack.source_coverage.missing_or_rejected ? "warn" : "pos"}>
                    {report.pack.source_coverage.missing_or_rejected ? "With source gaps" : "No source gaps"}</Badge>{" "}
                  {fmtInt(report.pack.source_coverage.missing_or_rejected)} of {fmtInt(report.pack.source_coverage.expected_bar_slots)} bar minutes missing/rejected
                </span>
                <span className="outcome-hint">Separate from feed integrity: the whole feed can be consumed ({report.pack.feed_consumed}) while
                  the source itself has gaps. Warmup {fmtTime(report.pack.windows.warmup.start)} and tail up to {fmtTime(report.pack.windows.tail.end)} are not scored.</span>
              </li>
            )}
          </ul>

          {adv && (
            <Card title="Adviser evaluation" icon="compass" testid="adviser-result"
                  eyebrow="Calls, entry windows, funnel and hypothetical outcomes">
              <AdviserSummary a={adv} />
              <div className="adv-section-title">Calls (click one for its scenario, revisions and hypothetical path)</div>
              <CallTimeline replayId={ev.replay.replay_id} a={adv} />
            </Card>
          )}
          {failed.length > 0 && (
            <Notice tone="neg" title={`${failed.length} check(s) failed`} testid="report-failed-checks">
              {failed.map((c) => <div key={c.name}><span className="mono">{c.name}</span> — {c.detail}</div>)}
            </Notice>
          )}
          {report.stopped_at && (
            <Notice tone="warn" title="Incomplete coverage" testid="report-stopped">
              Stopped at {fmtInt(report.stopped_at.applied_events)}/{report.stopped_at.total_events === null ? "PENDING" : fmtInt(report.stopped_at.total_events)} events
              (information time {fmtTime(report.stopped_at.information_time)}). {report.stopped_at.reason ?? ""}
            </Notice>
          )}
          {report.warnings.length > 0 && (
            <div className="report-limits" data-testid="report-warnings">
              <div className="setup-col-title">Limits of this result</div>
              <ul>{report.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </div>
          )}

          <div className="report-next" data-testid="report-next">
            <div className="report-next-text">
              <div className="setup-col-title">Next step</div>
              <p>Copy the report and paste it into the Director chat. {report.next_diagnostic}</p>
            </div>
            {actions}
          </div>

          <details className="more inset" data-testid="report-more">
            <summary><Icon name="chevron" size={14} className="summary-chevron" /> Report details
              <span className="summary-hint">timing, quality, every check, adviser metrics</span>
            </summary>
            <div className="more-body">
              <div className="metric-grid compact">
                <Metric label="Coverage" value={report.completion}
                        hint={`${fmtInt(report.coverage.applied_events)}/${report.coverage.total_events === null ? "PENDING" : fmtInt(report.coverage.total_events)} feed events`} />
                <Metric label="Validation" mono={false} value={<Badge tone={checksTone}>{checksText}</Badge>}
                        hint={`${v?.checks.filter((c) => c.passed).length}/${v?.checks.length} checks` + (v?.validator ? ` · ${v.validator}` : "")} />
                <Metric label="Final information time" value={fmtTime(report.coverage.final_information_time)} />
                <Metric label="Runtime" value={fmtSecs(report.runtime.elapsed_seconds)}
                        hint={report.runtime.throughput_events_per_second
                          ? `${report.runtime.throughput_events_per_second.toFixed(1)} events/s` : undefined} />
                <Metric label="Recoveries" value={`${report.runtime.recoveries}`} hint={`attempts ${report.runtime.attempts}/${report.runtime.max_attempts}`} />
                <Metric label="Quality" value={report.quality_status.toUpperCase()} />
              </div>
              {v && (
                <ul className="check-list" data-testid="report-checks">
                  {v.checks.map((c) => (
                    <li key={c.name} className={c.passed ? "text-pos" : "text-neg"}>
                      <Icon name={c.passed ? "check" : "x"} size={13} />
                      <span className="mono">{c.name}</span>
                      <span className="muted">{c.detail}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="cap-table" data-testid="report-capabilities">
                <div className="cap-table-head">
                  <span className="eyebrow">Adviser metrics</span>
                  <span className="muted small-text">{adv ? "Reported in the adviser section above." : "Not part of a market replay — shown as unavailable, never as zero."}</span>
                </div>
                <ul>
                  {caps.map(([k, c]) => (
                    <li key={k}>
                      <span>{c.label ?? "Professional adviser"}</span>
                      <Badge tone={adv ? "pos" : "pending"}>{humanize(c.status)}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </details>
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
      <ReplayPanel r={r} live={live} onCommand={command} place="report"
                   eyebrow={`${ev.run_type === "adviser_evaluation" ? "Adviser evaluation" : "Market replay — data and engine check"} · ${ev.corpus.chunk_label}`} />
      <ReportCard ev={{ ...ev, replay: r, report_available: true, report_terminal: TERMINAL.has(r.status) }} />
      {ev.run_type === "adviser_evaluation" ? <AdviserProgress r={r} /> : (
        <div className="boundary" data-testid="intelligence-boundary">
          <Icon name="compass" size={18} />
          <div>
            <strong>No adviser in this run.</strong> Candles and observable state are real historical evidence replayed
            causally; no market view, call, target or outcome is derived from them.
          </div>
          <Badge tone="pending">Market replay only</Badge>
        </div>
      )}
      <Card title="Traded price" icon="market" testid="market-chart"
            eyebrow={`Latest ${CHART_TAIL} completed 1m bars as causally delivered · chart refreshes at most once per second`}
            actions={<Badge tone="brand">REAL · HISTORICAL</Badge>}>
        <MarketChart bars={bars} informationTime={r.progress.information_time} />
      </Card>
      <DeepValidationPanel r={r} onChanged={() => void obsApi.state(rid).then((d) => { setDoc(d); onReplay(d.replay); })} />
      <div className="section-divider"><span>More inspection</span></div>
      <ObservableStatePanel state={doc?.state ?? null} />
      {r.has_manifest && (
        <details className="more" onToggle={(e) => setManifestOpen((e.target as HTMLDetailsElement).open)}>
          <summary><Icon name="chevron" size={14} className="summary-chevron" /> Replay artifacts and validation checks</summary>
          {manifest ? <Artifacts m={manifest} /> : <Skeleton lines={3} />}
        </details>
      )}
      <p className="muted small-text">
        Event-by-event inspection (evidence timeline, per-delivery changes) is in{" "}
        <a href={`#replay/obs=${rid}`} data-testid="open-in-replay-lab">Replay Lab</a>.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function StepCard({ n, id, title, lede, status, children, testid }: {
  n: number; id: string; title: string; lede: ReactNode; status?: ReactNode; children: ReactNode; testid?: string;
}) {
  return (
    <section className="step-card" id={id} data-testid={testid} aria-labelledby={`${id}-title`}>
      <header className="step-head">
        <span className="step-n" aria-hidden>{n}</span>
        <div className="step-titles">
          <h2 className="step-title" id={`${id}-title`}>{title}</h2>
          <p className="step-lede">{lede}</p>
        </div>
        {status && <div className="step-status">{status}</div>}
      </header>
      <div className="step-body">{children}</div>
    </section>
  );
}

function StepNav({ corpus, ev }: { corpus: CorpusStatus | null; ev: Evaluation | null }) {
  const prepared = corpus?.summary.prepared ?? 0;
  const preparing = corpus?.chunks.some((c) => c.status === "preparing");
  const story = ev ? runStory(ev.replay) : null;
  const stages: { n: number; target: string; title: string; value: string; tone: Tone; testid: string }[] = [
    {
      n: 1, target: "step-data", title: "Choose & prepare data", testid: "stage-corpus",
      value: !corpus ? "Loading…" : preparing ? "Preparing a month…"
        : prepared ? `Ready · ${prepared}/${corpus.summary.chunks} months prepared` : "Prepare a month first",
      tone: preparing ? "info" : prepared ? "pos" : "brand",
    },
    {
      n: 2, target: "step-start", title: "Start a check", testid: "stage-setup",
      value: prepared ? "Ready to start · market replay" : "Waiting for a prepared month",
      tone: prepared ? "pos" : "neutral",
    },
    {
      n: 3, target: "step-result", title: "Follow & get the report", testid: "stage-run",
      value: !ev || !story ? "No run yet" : ev.report_terminal ? `${story.title} · report ready`
        : `${story.title} · ${humanize(ev.replay.runtime_state)}`,
      tone: !story ? "neutral" : story.terminal ? story.tone : story.tone === "warn" ? "warn" : "info",
    },
  ];
  return (
    <ol className="stage-rail" aria-label="Steps">
      {stages.map((s) => (
        <li key={s.n} className={cx("stage", `tone-${s.tone}`)} data-testid={s.testid}>
          <button type="button" className="stage-btn"
                  onClick={() => document.getElementById(s.target)?.scrollIntoView({ behavior: "smooth", block: "start" })}>
            <span className="stage-n" aria-hidden>{s.n}</span>
            <span className="stage-body">
              <span className="stage-title">{s.title}</span>
              <span className="stage-value">{s.value}</span>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

export function Backtest() {
  const corpusPoll = usePoll(corpusApi.status, 2000);
  const presetsPoll = usePoll(packApi.presets, 3000);
  const packsPoll = usePoll(packApi.list, 3000);
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
    window.setTimeout(() => document.getElementById("step-result")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  const target = corpus?.plan.target;
  const listItems = useMemo(() => evals?.map((e) => (evDetail && e.evaluation_id === evDetail.evaluation_id ? evDetail : e)) ?? null,
    [evals, evDetail]);
  const story = evDetail ? runStory(evDetail.replay) : null;

  return (
    <div className="page page-backtest" data-testid="page-backtest">
      <PageHeader
        eyebrow="Check historical data · step by step"
        title="Historical Workbench"
        lede="Evaluate the integrated adviser on real BTC history (or check that the data replays correctly), then copy the report into chat. Three steps: prepare the data, start the run, read the result. Outcomes are hypothetical normalized simulations — no orders, size or leverage."
        meta={<Badge tone="brand" icon="clock" testid="historical-mode">HISTORICAL MODE</Badge>}
      />
      <div className="history-banner" data-testid="history-banner">
        <Icon name="replay" size={18} />
        <div>
          <strong>HISTORICAL · OBSERVATION ONLY</strong> — past OKX evidence replayed on a simulated clock with modeled
          availability (a declared convention: each bar counts as known at its close; not measured historical timing).
          Nothing here is live, and no trade call exists yet.
        </div>
      </div>
      {error && <Notice tone="neg" title="Something went wrong">{error}</Notice>}
      <StepNav corpus={corpus} ev={evDetail} />

      <StepCard n={1} id="step-data" testid="pack-card" title="Prepare data"
                lede="The September 2025 development check needs 4 days before it (warmup) and 6 hours after it (tail). Data already on this computer is reused; Prepare downloads only what is missing, verifies everything once and composes one immutable pack."
                status={presetsPoll.data && (() => {
                  const def = presetsPoll.data.presets.find((x) => x.preset.default);
                  return def?.published?.usable
                    ? <Badge tone={def.published.status === "READY" ? "pos" : "warn"} testid="pack-ready-badge">Pack ready</Badge>
                    : <Badge tone="neutral">Not prepared yet</Badge>;
                })()}>
        {!presetsPoll.data ? (presetsPoll.error ? <Notice tone="neg" title="Presets unavailable">{presetsPoll.error}</Notice> : <Skeleton lines={4} />)
          : <PackPrepare data={presetsPoll.data} onChanged={() => { void presetsPoll.refresh(); void packsPoll.refresh(); }} />}
      </StepCard>

      <details className="more" data-testid="corpus-card-legacy">
        <summary><Icon name="chevron" size={14} className="summary-chevron" /> Single-month data (earlier workflow)
          <span className="summary-hint">the monthly corpus ledger, its preparation jobs and reports</span></summary>
        <div className="more-body">
      <StepCard n={1} id="step-month" testid="corpus-card" title="Single month"
                lede="Earlier workflow: one calendar month without warmup or tail. Kept for its existing runs and reports."
                status={corpus && (
                  <span className="corpus-summary">
                    <Badge tone="pos" testid="corpus-prepared-count">{corpus.summary.prepared} prepared</Badge>
                    <Badge tone="pending" icon="lock">{corpus.summary.planned_locked} planned</Badge>
                    {corpus.summary.prepared_bytes > 0 && <span className="mono muted small-text">{fmtBytes(corpus.summary.prepared_bytes)} local</span>}
                  </span>
                )}>
        {!corpus ? (corpusPoll.error ? <Notice tone="neg" title="Corpus unavailable">{corpusPoll.error}</Notice> : <Skeleton lines={4} />) : (
          <>
            <p className="corpus-lede">
              BTC corpus {utcDay(target!.start)} → {utcDay(target!.end)} · {corpus.plan.description.replace(/\.?$/, ".")} Plan{" "}
              <Mono>{corpus.plan.plan_id}</Mono> v{corpus.plan.plan_version} · {corpus.plan.chunk_rule} · start inclusive, end exclusive (UTC).
            </p>
            <CorpusLedger corpus={corpus} selected={chunkId} onSelect={setChunkSel} />
            {chunk && <ChunkDetail chunk={chunk} plan={corpus.plan} onPrepare={prepare} onCancel={cancelPrep} busy={busy} />}
          </>
        )}
      </StepCard>
        </div>
      </details>

      <StepCard n={2} id="step-start" title="Check data and engine"
                lede="Choose the run type and the prepared data, then press Start. The run continues in the background; you can close the browser.">
        <RunSetup corpus={corpus} preferred={chunk?.status === "prepared" ? chunk.chunk_id : null}
                  packs={packsPoll.data ?? []} presets={presetsPoll.data ?? null} onStarted={onStarted} />
      </StepCard>

      <StepCard n={3} id="step-result" title="Follow the run and get the report"
                lede="Status and progress update by themselves. When the run finishes, its result and the Copy report button appear right below the status."
                status={story && <Badge tone={story.tone} dot={story.working}>{story.title}</Badge>}>
        <RunPicker items={listItems} selected={selectedId} onSelect={setEvalSel} />
        {!evDetail ? (
          <EmptyState icon="gauge" title="No run yet">
            Prepare a month in step 1, then press Start in step 2. Progress, controls and the copyable report appear here.
          </EmptyState>
        ) : <ActiveRun key={evDetail.evaluation_id} ev={evDetail} onReplay={onReplay} />}
      </StepCard>
    </div>
  );
}
