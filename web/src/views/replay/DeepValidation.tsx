import { useCallback, useEffect, useState } from "react";
import { AssuranceSummary, deepApi, DeepValidation, ObsReplay } from "../../api";
import { fmtInt, fmtSecs, fmtTime } from "../../lib/format";
import { Badge, Button, Card, Metric, Notice, statusTone, Tone } from "../../ui/primitives";
import { CopyDiagnostics, healthTone } from "./MarketReplay";

// Current assurance of a run + the optional Deep validation diagnostic (an independent reference execution over the
// run's canonical feed cache). Deep validation is launched only by an explicit Owner action, is its own durable job
// with its own progress/health/controls/report, and never changes the originating run's records or report.

const DEEP_TERMINAL = new Set(["completed", "cancelled", "failed"]);
const LAUNCHABLE = new Set(["completed", "cancelled", "failed", "paused"]);

function outcomeTone(o: string | undefined): Tone {
  return o === "match" ? "pos" : o === "mismatch" ? "neg" : o === "incomplete" ? "warn" : "neutral";
}

export function AssuranceStrip({ a }: { a: AssuranceSummary | undefined }) {
  if (!a) return null;
  return (
    <div className="assurance-strip" data-testid="assurance-summary">
      <Notice tone={a.warnings.length ? "neg" : a.deep_validation === "match" ? "pos" : "info"} icon="shield"
              title={<span data-testid="assurance-headline">{a.headline}</span>}>
        <span className="small-text">
          Run validation: <b>{a.run_validation ?? "pending"}</b> · Deep validation: <b data-testid="assurance-deep">{a.deep_validation.replace("_", " ")}</b>
          {a.deep_validations > 0 && ` (${a.deep_validations} linked)`}
        </span>
        {a.warnings.map((w) => <div key={w} className="text-warn small-text" data-testid="assurance-warning">{w}</div>)}
      </Notice>
    </div>
  );
}

export function DeepValidationPanel({ r }: { r: ObsReplay }) {
  const [rows, setRows] = useState<DeepValidation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(() => {
    deepApi.list(r.replay_id).then((x) => { setRows(x); setError(null); }).catch((e) => setError((e as Error).message));
  }, [r.replay_id]);
  const active = rows?.find((d) => !DEEP_TERMINAL.has(d.status));
  useEffect(() => {
    refresh();
    if (!active) return;
    const t = window.setInterval(refresh, 1000);
    return () => window.clearInterval(t);
  }, [refresh, active?.validation_id, active?.status, r.status]);

  const act = async (fn: () => Promise<DeepValidation>) => {
    setBusy(true);
    try {
      await fn();
      refresh();
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    } finally {
      setBusy(false);
    }
  };
  const committed = r.progress.committed_events ?? r.progress.applied_events;
  const canLaunch = LAUNCHABLE.has(r.status) && committed > 0 && !active;
  const latest = rows?.[0];

  return (
    <Card title="Deep validation" icon="shield" testid="deep-panel"
          eyebrow="Optional diagnostic · independent reference execution of this run's committed prefix"
          actions={<Button icon="play" variant="secondary" disabled={!canLaunch || busy} data-testid="deep-launch"
                           title={canLaunch ? undefined : active ? "a Deep validation of this run is already active"
                             : "available once the run is completed, cancelled, failed or paused with committed events"}
                           onClick={() => act(() => deepApi.launch(r.replay_id))}>Run Deep validation</Button>}>
      <p className="muted small-text">
        Never launched automatically. Re-executes the committed feed events with an independent reference reducer and
        compares input commitments, snapshot digests and state hashes at every committed range / restore point. Scope:
        the canonical feed cache only (not an independent audit of the original source files). The run's own records,
        artifacts and terminal report are never changed; a mismatch is shown as a linked assurance warning.
      </p>
      {error && <Notice tone="neg" title="Deep validation">{error}</Notice>}
      {!latest ? (
        <p className="muted small-text" data-testid="deep-none">No Deep validation of this run.</p>
      ) : (
        <DeepRow d={latest} busy={busy} act={act} />
      )}
      {rows && rows.length > 1 && (
        <ul className="list small-text" data-testid="deep-history">
          {rows.slice(1, 6).map((d) => (
            <li key={d.validation_id} className="mono">
              {d.validation_id} · {d.status} · {d.result?.outcome ?? "—"} · {fmtTime(d.finished_at ?? d.created_at)}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DeepRow({ d, busy, act }: { d: DeepValidation; busy: boolean; act: (fn: () => Promise<DeepValidation>) => void }) {
  const terminal = DEEP_TERMINAL.has(d.status);
  const p = d.progress;
  const pct = p.fraction === null ? null : Math.min(100, Math.round(p.fraction * 1000) / 10);
  const res = d.result;
  return (
    <div className="deep-row" data-testid="deep-latest" data-status={d.status}>
      <div className="op-badges">
        <Badge tone={statusTone(d.status)} dot testid="deep-status">{d.status.toUpperCase()}</Badge>
        <Badge tone="brand">{d.phase_label}</Badge>
        {!terminal && <Badge tone={healthTone(d.health)} dot title={d.health_detail} testid="deep-health">{d.health_label}</Badge>}
        {res && <Badge tone={outcomeTone(res.outcome)} icon="shield" testid="deep-outcome">Outcome {res.outcome.toUpperCase()}</Badge>}
        <span className="muted small-text mono">{d.validation_id} · attempt {d.attempt} · generation {d.generation}</span>
      </div>
      {!terminal && (
        <div className="progress" role="progressbar" aria-label="Deep validation progress" aria-valuemin={0}
             aria-valuemax={100} aria-valuenow={pct ?? undefined}>
          <div className="progress-fill real" style={{ width: `${pct ?? 0}%` }} />
        </div>
      )}
      <div className="metric-grid">
        <Metric label="Covered events" testid="deep-covered"
                value={`${fmtInt(res?.covered_events ?? p.done ?? 0)}/${fmtInt(d.plan.committed_cursor)}`}
                hint={`run total ${fmtInt(d.plan.total_events)} · saved cursor ${p.saved_cursor ?? "—"}`} />
        <Metric label="Comparisons" value={`${d.comparisons.compared} · ${d.comparisons.mismatches} mismatch(es)`}
                testid="deep-comparisons" />
        <Metric label="ETA (this phase)" value={d.eta.seconds === null ? "—" : fmtSecs(d.eta.seconds)} hint={d.eta.basis} />
        <Metric label="Validator" value={`${d.validator} v${d.validator_version}`} hint={d.mode} />
      </div>
      {res?.mismatches.slice(0, 5).map((m) => (
        <Notice key={`${m.cursor}-${m.kind}`} tone="neg" testid="deep-mismatch">
          Mismatch at cursor {m.cursor} ({m.at}, {m.kind}): expected <span className="mono">{m.expected.slice(0, 16)}</span>,
          reference <span className="mono">{m.reference.slice(0, 16)}</span>
        </Notice>
      ))}
      {d.error && <Notice tone="warn">{d.error}</Notice>}
      <div className="diag-row">
        {!terminal && (
          <div className="controls" data-testid="deep-controls">
            {d.paused
              ? <Button icon="play" disabled={busy || !d.controls.resume.enabled} data-testid="deep-resume"
                        onClick={() => act(() => deepApi.resume(d.validation_id))}>Resume</Button>
              : <Button variant="secondary" icon="pause" disabled={busy || !d.controls.pause.enabled} data-testid="deep-pause"
                        onClick={() => act(() => deepApi.pause(d.validation_id))}>Pause</Button>}
            <Button variant="danger" icon="stop" disabled={busy || !d.controls.cancel.enabled} data-testid="deep-cancel"
                    onClick={() => act(() => deepApi.cancel(d.validation_id))}>
              {d.cancel_requested ? "Cancelling…" : "Cancel"}
            </Button>
          </div>
        )}
        <CopyDiagnostics markdown={() => deepApi.markdown(d.validation_id)} mdUrl={deepApi.downloadUrl(d.validation_id, "md")}
                         jsonUrl={deepApi.downloadUrl(d.validation_id, "json")} label="Copy Deep validation report"
                         testid="deep-copy-report" />
      </div>
    </div>
  );
}
