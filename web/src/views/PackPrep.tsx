import { useEffect, useState } from "react";
import { packApi, PackCoverage, PackJob, PresetView, PresetsResponse, PublishedPack } from "../api";
import { fmtBytes, fmtInt, fmtTime, humanize } from "../lib/format";
import { Icon } from "../ui/Icon";
import { Badge, Button, cx, Field, Metric, Mono, Notice, statusTone } from "../ui/primitives";
import { CopyDiagnostics, OperationPanel } from "./replay/MarketReplay";

// Step 1 of the Historical Workbench (WP-008-R3): prepare an evaluation pack for a registered preset (warmup +
// evaluation months + outcome tail) from data already on this computer plus only the missing boundary slices.
// Opening the page never downloads anything; only the Prepare button starts a durable preparation. Data
// preparation only: no adviser, nothing scored.

const utc = (iso: string) => fmtTime(iso).replace(":00 UTC", " UTC");
const fam: Record<string, string> = {
  trade_bar_1m: "Trade 1m", mark_bar_1m: "Mark 1m", index_bar_1m: "Index 1m", funding_settlement: "Funding settlements",
};
const OUTCOME: Record<string, string> = {
  reused_pack: "Already prepared — the verified pack was reused; nothing was downloaded",
  prepared: "Prepared — sources verified and composed into one immutable pack",
  prepared_converged: "Prepared — identical pack already published; it was reused",
};

export function packState(p: PresetView): { label: string; tone: "pos" | "warn" | "info" | "neutral" | "neg" } {
  const job = p.latest_job;
  if (job && (job.status === "queued" || job.status === "running")) return { label: "Preparing", tone: "info" };
  if (p.published?.usable) {
    return p.published.status === "READY" ? { label: "Ready", tone: "pos" } : { label: "Ready with limitations", tone: "warn" };
  }
  if (p.published && !p.published.usable) return { label: "Needs attention", tone: "neg" };
  return { label: p.needed.length ? "Not prepared yet" : "All sources local — not composed yet", tone: "neutral" };
}

function Windows({ p }: { p: PresetView }) {
  const w = p.windows;
  return (
    <div className="metric-grid compact" data-testid="pack-windows">
      <Metric label="Evaluation (scored later)" value={`${utc(w.evaluation.start)} → ${utc(w.evaluation.end)}`} mono={false} />
      <Metric label="Warmup (not scored)" value={`${utc(w.warmup.start)} → ${utc(w.warmup.end)}`} mono={false}
              hint={`${fmtInt(w.warmup.minutes / 60)} h before the evaluation`} />
      <Metric label="Outcome tail (not scored)" value={`${utc(w.tail.start)} → ${utc(w.tail.end)}`} mono={false}
              hint={`${fmtInt(w.tail.minutes)} min after the evaluation`} />
      <Metric label="Evidence class" value={humanize(p.classification.label)} mono={false} hint={p.classification.note} />
    </div>
  );
}

function CoverageTable({ rows }: { rows: PackCoverage[] }) {
  return (
    <div className="table-wrap">
      <table className="table table-compact" data-testid="pack-coverage">
        <thead><tr><th>Series</th><th>Window</th><th className="num">Usable</th><th className="num">Missing</th>
          <th className="num">Rejected</th></tr></thead>
        <tbody>
          {rows.map((c) => (
            <tr key={`${c.family}-${c.window}`}>
              <td className="nowrap">{fam[c.family] ?? c.family}</td>
              <td className="nowrap">{c.window}</td>
              <td className="num mono">{c.expected_slots === null ? `${fmtInt(c.valid)} row(s)` : `${fmtInt(c.valid)}/${fmtInt(c.expected_slots)}`}</td>
              <td className="num mono">{c.expected_slots === null ? "unknown" : fmtInt(c.missing)}</td>
              <td className="num mono">{c.expected_slots === null ? "—" : fmtInt(c.rejected)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PackFacts({ pub }: { pub: PublishedPack }) {
  return (
    <details className="more inset" data-testid="pack-details">
      <summary><Icon name="chevron" size={14} className="summary-chevron" /> Sources, coverage and capabilities
        <span className="summary-hint">{pub.pack_id}</span></summary>
      <div className="more-body">
        <ul className="list small-text" data-testid="pack-sources">
          {pub.sources.map((s) => (
            <li key={`${s.dataset_id}-${s.start}`}><Mono>{s.dataset_id}</Mono> · {utc(s.start)} → {utc(s.end)}</li>
          ))}
        </ul>
        <CoverageTable rows={pub.coverage} />
        <ul className="list small-text" data-testid="pack-capabilities">
          {pub.capabilities.map((c) => <li key={c.capability}><b>{humanize(c.capability)}</b>: {c.status} — <span className="muted">{c.detail}</span></li>)}
        </ul>
        {pub.input_readiness_preview && (
          <p className="muted small-text" data-testid="pack-readiness-preview">
            {String(pub.input_readiness_preview.label)}: trade 15m {String(pub.input_readiness_preview.trade_15m_contiguous_complete)}/
            {String(pub.input_readiness_preview.trade_15m_required_by_mp001)}, 1h {String(pub.input_readiness_preview.trade_1h_contiguous_complete)}/
            {String(pub.input_readiness_preview.trade_1h_required_by_mp001)} contiguous complete bars before the evaluation start.
          </p>
        )}
        {pub.storage && (
          <p className="muted small-text">Stored: sources {fmtBytes(pub.storage.source_package_bytes)} (referenced, not copied) ·
            pack feed cache {fmtBytes(pub.storage.pack_cache_bytes)} added · {fmtInt(pub.event_count)} canonical events ·
            engine clock end {pub.clock_end ? utc(pub.clock_end) : "—"}</p>
        )}
        {pub.overlap && pub.overlap.overlapping_slots > 0 && (
          <p className="muted small-text">Overlapping sources: {fmtInt(pub.overlap.overlapping_slots)} slot(s) ·
            {" "}{fmtInt(pub.overlap.identical_collapsed)} identical copies collapsed · {fmtInt(pub.overlap.gap_replaced_by_valid)} gap
            placeholder(s) superseded by valid evidence (all provenance kept)</p>
        )}
      </div>
    </details>
  );
}

function PackJobBox({ job, onCancel }: { job: PackJob; onCancel: () => void }) {
  const active = job.status === "queued" || job.status === "running";
  return (
    <div className={cx("job", active && "is-active")} data-testid="pack-job" data-state={job.status}>
      <div className="job-head">
        <div className="min-0">
          <div className="eyebrow">Pack preparation</div>
          <div className="mono job-id">{job.job_id}</div>
        </div>
        <Badge tone={statusTone(job.status)} dot testid="pack-job-status">{job.status.toUpperCase()}</Badge>
      </div>
      {job.status === "completed" && <p data-testid="pack-job-outcome">{OUTCOME[job.outcome ?? ""] ?? job.outcome}</p>}
      {active && <OperationPanel op={job.operation} testid="pack-op" what="preparation" />}
      {job.children.length > 0 && (
        <ul className="list small-text" data-testid="pack-children">
          {job.children.map((c, i) => (
            <li key={i}>Download {utc(c.start)} → {utc(c.end)}: <b>{c.status}</b>
              {c.bytes ? ` · ${fmtBytes(c.bytes)}` : ""}{c.error ? ` · ${c.error}` : ""}</li>
          ))}
        </ul>
      )}
      {job.status === "failed" && <Notice tone="neg" title="Preparation failed" testid="pack-job-error">{job.error}</Notice>}
      {job.status === "cancelled" && <Notice tone="warn" title="Preparation cancelled" testid="pack-job-error">{job.error}</Notice>}
      <CopyDiagnostics markdown={() => packApi.reportMarkdown(job.job_id)} mdUrl={packApi.downloadUrl(job.job_id, "md")}
                       jsonUrl={packApi.downloadUrl(job.job_id, "json")} label="Copy preparation report for chat"
                       testid="pack-copy-report" />
      {active && (
        <div className="job-foot">
          <span className="muted small-text">Downloaded so far: {fmtInt(job.downloaded.children)} package(s) · {fmtBytes(job.downloaded.bytes)}</span>
          <Button variant="danger" icon="stop" onClick={onCancel} disabled={job.cancel_requested} data-testid="pack-cancel">
            {job.cancel_requested ? "Cancelling…" : "Cancel"}
          </Button>
        </div>
      )}
    </div>
  );
}

function PresetPanel({ p, onPrepare, onCancel, busy, testid }: {
  p: PresetView; onPrepare: () => void; onCancel: (jobId: string) => void; busy: boolean; testid: string;
}) {
  const st = packState(p);
  const job = p.latest_job;
  const active = job && (job.status === "queued" || job.status === "running");
  return (
    <div className="pack-panel" data-testid={testid}>
      <div className="op-badges">
        <b data-testid="pack-label">{p.preset.label}</b>
        <Badge tone={st.tone} dot testid="pack-state">{st.label}</Badge>
        {p.classification.label !== "DEVELOPMENT" && <Badge tone="warn" testid="pack-class">{humanize(p.classification.label)}</Badge>}
      </div>
      <Windows p={p} />
      <ul className="list small-text" data-testid="pack-plan">
        {p.local.map((s) => <li key={`${s.dataset_id}-${s.start}`}>Already on this computer: {utc(s.start)} → {utc(s.end)}</li>)}
        {p.needed.map((s) => <li key={s.start}><b>Needs download</b>: {utc(s.start)} → {utc(s.end)}</li>)}
        {!p.local.length && !p.needed.length && <li>Nothing local yet.</li>}
      </ul>
      <p className="muted small-text" data-testid="pack-estimate">
        {p.estimate.estimated_bytes === null ? "Download size unknown" : `About ${fmtBytes(p.estimate.estimated_bytes)} to download`}
        {" "}— {p.estimate.basis}. {p.note}
      </p>
      {p.published && !p.published.usable && (
        <Notice tone="neg" title="Published pack not trustworthy">{p.published.problem} Prepare again to rebuild it.</Notice>
      )}
      {p.published?.usable && p.published.status === "READY_WITH_LIMITATIONS" && (
        <Notice tone="warn" title="Ready with limitations" testid="pack-limitations">
          {p.published.limitations.join(" · ")}
        </Notice>
      )}
      <div className="job-foot">
        <Button icon="download" onClick={onPrepare} disabled={busy || !!active} data-testid="pack-prepare">
          {p.published?.usable ? "Prepare again (reuses the verified pack)" : "Prepare data"}
        </Button>
      </div>
      {job && <PackJobBox job={job} onCancel={() => onCancel(job.job_id)} />}
      {p.published?.usable && <PackFacts pub={p.published} />}
    </div>
  );
}

export function PackPrepare({ data, onChanged }: { data: PresetsResponse; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [first, setFirst] = useState(data.months[0]?.month ?? "");
  const [last, setLast] = useState(data.months[0]?.month ?? "");
  const [sel, setSel] = useState<PresetView | null>(null);
  const def = data.presets.find((p) => p.preset.default) ?? data.presets[0];
  const others = data.presets.filter((p) => p !== def);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      setError(null);
      onChanged();
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    } finally {
      setBusy(false);
    }
  };
  const months = (() => {
    const i = data.months.findIndex((m) => m.month === first);
    const j = data.months.findIndex((m) => m.month === last);
    return i >= 0 && j >= i ? data.months.slice(i, j + 1).map((m) => m.month) : [];
  })();
  useEffect(() => {
    let alive = true;
    if (!months.length) { setSel(null); return; }
    packApi.selection(months).then((v) => alive && setSel(v)).catch((e) => alive && setError((e as Error).message));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [first, last]);

  return (
    <div data-testid="pack-prepare-card">
      {error && <Notice tone="neg" title="Could not prepare">{error}</Notice>}
      <PresetPanel p={def} busy={busy} testid="pack-default"
                   onPrepare={() => act(() => packApi.preparePreset(def.preset.preset_id))}
                   onCancel={(id) => act(() => packApi.cancel(id))} />
      <details className="more inset" data-testid="pack-other">
        <summary><Icon name="chevron" size={14} className="summary-chevron" /> Other selections
          <span className="summary-hint">registered presets and contiguous months — prepared only when you press Prepare</span>
        </summary>
        <div className="more-body">
          {others.map((p) => (
            <PresetPanel key={p.preset.preset_id} p={p} busy={busy} testid={`pack-preset-${p.preset.preset_id}`}
                         onPrepare={() => act(() => packApi.preparePreset(p.preset.preset_id))}
                         onCancel={(id) => act(() => packApi.cancel(id))} />
          ))}
          <div className="setup-facts">
            <Field label="First month">
              <select className="control" value={first} data-testid="pack-month-first"
                      onChange={(e) => { setFirst(e.target.value); if (e.target.value > last) setLast(e.target.value); }}>
                {data.months.map((m) => <option key={m.month} value={m.month}>{m.label}{m.class !== "DEVELOPMENT" ? " · protected (provisional)" : ""}</option>)}
              </select>
            </Field>
            <Field label="Last month">
              <select className="control" value={last} data-testid="pack-month-last" onChange={(e) => setLast(e.target.value)}>
                {data.months.filter((m) => m.month >= first).map((m) => <option key={m.month} value={m.month}>{m.label}</option>)}
              </select>
            </Field>
          </div>
          {sel && (
            <PresetPanel p={sel} busy={busy} testid="pack-selection"
                         onPrepare={() => act(() => packApi.prepareSelection(months))}
                         onCancel={(id) => act(() => packApi.cancel(id))} />
          )}
        </div>
      </details>
    </div>
  );
}
