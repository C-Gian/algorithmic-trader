import { useCallback, useEffect, useMemo, useState } from "react";
import { api, Decision, Health, JournalEvent, Manifest, PricePoint, Run, Snapshot } from "../../api";
import { fmtNum, fmtSecs, fmtTime, humanize, speedLabel } from "../../lib/format";
import { replaceHash, runFromHash } from "../../lib/route";
import { useHealth } from "../../shell/health";
import { Icon } from "../../ui/Icon";
import { Badge, Button, Card, cx, EmptyState, Field, Metric, Mono, Notice, statusTone } from "../../ui/primitives";
import { SyntheticChart } from "./SyntheticChart";

// Synthetic Demo (Replay Lab, secondary mode): the synthetic DEMO replay (durable run/worker/replay-control machinery with a scripted dummy
// trader). Everything here is scaffolding; none of it is market evidence or real trader output.

const TERMINAL = new Set(["completed", "cancelled", "failed"]);

const SPEEDS: { label: string; value: number }[] = [
  { label: "1 bar/s", value: 1 },
  { label: "4 bars/s", value: 4 },
  { label: "20 bars/s", value: 20 },
  { label: "max", value: 0 },
];

const FAULTS: { label: string; value: string }[] = [
  { label: "none", value: "none" },
  { label: "crash worker once (recovers)", value: "crash_once" },
  { label: "crash worker every attempt (fails)", value: "crash_always" },
];

function RunStatusBadge({ run }: { run: Run }) {
  return (
    <Badge tone={statusTone(run.runtime_state)} dot testid="run-status" title={run.runtime_detail}>
      {run.runtime_state.replace("_", " ").toUpperCase()}
    </Badge>
  );
}

function WorkerHealth({ health }: { health: Health | null }) {
  if (!health) return <span data-testid="worker-health" className="text-warn">unknown (API unreachable)</span>;
  const w = health.workers;
  const last = w.recent[0];
  if (w.alive === 0) {
    return (
      <span data-testid="worker-health" className="text-warn">
        no live worker{last ? ` (last heartbeat ${fmtSecs(last.heartbeat_age_seconds)} ago)` : ""} — runs cannot progress
      </span>
    );
  }
  return (
    <span data-testid="worker-health">
      {w.alive} alive · last heartbeat {fmtSecs(last.heartbeat_age_seconds)} ago
    </span>
  );
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total ? Math.min(100, (done / total) * 100) : 0;
  return (
    <div className="progress" role="progressbar" aria-label="Replay progress" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
      <div className="progress-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

function RunRail({ runs, selected, onSelect, onStart }: {
  runs: Run[]; selected: string | null; onSelect: (id: string) => void; onStart: (speed: number, fault: string) => void;
}) {
  const [speed, setSpeed] = useState(4);
  const [fault, setFault] = useState("none");
  return (
    <div className="rail">
      <Card material="synthetic" title="New synthetic replay" icon="play" eyebrow="Demo fixture · 120 bars">
        <div className="form-stack">
          <Field label="Replay speed">
            <select className="control" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} data-testid="speed">
              {SPEEDS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </Field>
          <Field label="Fault injection (demo)" hint="Exercises crash recovery of the durable worker.">
            <select className="control" value={fault} onChange={(e) => setFault(e.target.value)} data-testid="fault">
              {FAULTS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </Field>
          <Button icon="play" onClick={() => onStart(speed, fault)} data-testid="start-run" className="btn-block">
            Start synthetic replay
          </Button>
        </div>
      </Card>

      <Card title="Runs" icon="replay" className="rail-list-card" actions={<span className="count-chip mono">{runs.length}</span>}>
        {runs.length === 0 ? (
          <EmptyState icon="replay" title="No runs yet">Start a synthetic replay to exercise the demo pipeline.</EmptyState>
        ) : (
          <ul className="list" aria-label="Synthetic runs">
            {runs.map((r) => (
              <li key={r.run_id}>
                <button type="button" className={cx("list-item", r.run_id === selected && "is-selected")}
                        aria-current={r.run_id === selected ? "true" : undefined} onClick={() => onSelect(r.run_id)}>
                  <span className="list-item-title mono">{r.run_id}</span>
                  <span className="list-item-meta">
                    <RunStatusBadge run={r} />
                    <span className="mono muted">{r.progress.steps_done}/{r.progress.total_steps}</span>
                    {r.config.fault !== "none" && <Badge tone="warn">fault: {r.config.fault}</Badge>}
                  </span>
                  <span className="mini-progress" aria-hidden>
                    <span style={{ width: `${(r.progress.steps_done / (r.progress.total_steps || 1)) * 100}%` }} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export function SyntheticDemo() {
  const { health } = useHealth();
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<string | null>(runFromHash());
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [prices, setPrices] = useState<PricePoint[]>([]);
  const [decisions, setDecisions] = useState<JournalEvent<Decision>[]>([]);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);

  const refreshRuns = useCallback(async () => {
    try {
      const rs = await api.listRuns();
      setRuns(rs);
      setSelected((cur) => cur ?? rs[0]?.run_id ?? null);
      setError(null);
    } catch (e) {
      setError(`API unreachable: ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void refreshRuns();
    const t = window.setInterval(refreshRuns, 3000);
    return () => window.clearInterval(t);
  }, [refreshRuns]);

  // Follow run deep links while the lab stays mounted (back/forward, pasted links).
  useEffect(() => {
    const on = () => {
      const id = runFromHash();
      if (id) setSelected((cur) => (cur === id ? cur : id));
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  const loadDetails = useCallback(async (id: string, s: Snapshot) => {
    const [p, d] = await Promise.all([api.prices(id), api.decisions(id)]);
    setPrices(p);
    setDecisions(d);
    if (s.run.has_manifest) setManifest(await api.manifest(id));
  }, []);

  // Live updates via SSE. Every (re)connection starts from a full snapshot.
  useEffect(() => {
    if (!selected) return;
    replaceHash(`replay/demo/run=${selected}`);
    setSnap(null);
    setPrices([]);
    setDecisions([]);
    setManifest(null);
    let closed = false;
    const onSnapshot = (s: Snapshot) => {
      if (closed) return;
      setSnap(s);
      setRuns((rs) => rs.map((r) => (r.run_id === s.run.run_id ? s.run : r)));
      void loadDetails(selected, s);
    };
    void api.snapshot(selected).then(onSnapshot).catch((e) => setError((e as Error).message));
    const es = new EventSource(`/api/runs/${selected}/stream`);
    es.addEventListener("open", () => setLive(true));
    es.addEventListener("snapshot", (ev) => onSnapshot(JSON.parse((ev as MessageEvent).data) as Snapshot));
    es.addEventListener("end", () => {
      setLive(false);
      es.close();
    });
    es.addEventListener("error", () => setLive(false));
    return () => {
      closed = true;
      es.close();
    };
  }, [selected, loadDetails]);

  const start = async (speed: number, fault: string) => {
    try {
      const run = await api.startRun(speed, fault);
      setSelected(run.run_id);
      await refreshRuns();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // Control commands are persisted by the backend; the UI only reflects the returned state.
  const command = async (fn: () => Promise<Run>) => {
    try {
      const updated = await fn();
      setSnap((s) => (s && s.run.run_id === updated.run_id ? { ...s, run: updated } : s));
      await refreshRuns();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const run = snap?.run ?? runs.find((r) => r.run_id === selected) ?? null;
  const view = snap?.latest.market_view;
  const decision = snap?.latest.decision;
  const account = snap?.latest.account;
  const obs = snap?.latest.observation;
  const actionHistory = useMemo(
    () =>
      decisions
        .filter((d, i) => {
          const prev = decisions[i - 1]?.payload;
          const p = d.payload;
          return p.blocking_reasons.length > 0 || !prev || prev.permitted_action !== p.permitted_action || !["NO_TRADE", "HOLD"].includes(p.permitted_action);
        })
        .slice(-14)
        .reverse(),
    [decisions],
  );

  return (
    <div className="lab-mode" data-testid="synthetic-demo">
      <div className="demo-banner" data-testid="demo-banner">
        <Icon name="flask" size={18} />
        <div>
          <strong>DEMO / SYNTHETIC</strong> — scripted dummy trader on a synthetic BTC-perpetual fixture. Not market data.
          Nothing here is research or profitability evidence, and none of it reaches the Market cockpit.
        </div>
      </div>

      {error && <Notice tone="neg" title="Something went wrong">{error}</Notice>}

      <div className="lab-grid">
        <RunRail runs={runs} selected={selected} onSelect={setSelected} onStart={start} />

        <div className="lab-main">
          {!run && (
            <Card>
              <EmptyState icon="flask" title="No run selected">
                Start a synthetic replay to watch the dummy trader move through the demo fixture.
              </EmptyState>
            </Card>
          )}
          {run && (
            <>
              <Card className="run-card" testid="run-panel">
                <div className="run-head">
                  <div className="run-head-id">
                    <div className="eyebrow">Synthetic run</div>
                    <h2 className="run-title mono">{run.run_id}</h2>
                  </div>
                  <div className="run-head-status">
                    <RunStatusBadge run={run} />
                    <span className={cx("live-pill", live && "is-live")}>
                      <span className={cx("pulse-dot", live ? "tone-pos" : "tone-neutral")} aria-hidden />
                      {live ? "Live stream" : "Stream idle"}
                    </span>
                  </div>
                  {!TERMINAL.has(run.status) && (
                    <div className="run-head-controls">
                      {!run.cancel_requested && (
                        <div className="controls" data-testid="replay-controls">
                          {run.control.paused ? (
                            <>
                              <Button icon="play" onClick={() => command(() => api.resumeRun(run.run_id))} data-testid="resume-run">Resume</Button>
                              <Button variant="secondary" icon="step"
                                      onClick={() => command(() => api.stepRun(run.run_id))}
                                      disabled={run.progress.steps_done + run.control.step_budget >= run.progress.total_steps}
                                      data-testid="step-run">
                                Step one bar
                              </Button>
                            </>
                          ) : (
                            <Button variant="secondary" icon="pause" onClick={() => command(() => api.pauseRun(run.run_id))} data-testid="pause-run">Pause</Button>
                          )}
                          <label className="inline-field">
                            <span>Speed</span>
                            <select className="control control-sm" value={run.control.speed}
                                    onChange={(e) => command(() => api.setSpeed(run.run_id, Number(e.target.value)))}
                                    data-testid="run-speed">
                              {[...new Set([...SPEEDS.map((s) => s.value), run.control.speed])].map((v) => (
                                <option key={v} value={v}>{speedLabel(v)}</option>
                              ))}
                            </select>
                          </label>
                        </div>
                      )}
                      <Button variant="danger" icon="stop" onClick={() => command(() => api.cancelRun(run.run_id))}
                              disabled={run.cancel_requested} data-testid="cancel-run">
                        {run.cancel_requested ? "Cancelling…" : "Cancel"}
                      </Button>
                    </div>
                  )}
                </div>

                <div className="run-progress">
                  <ProgressBar done={run.progress.steps_done} total={run.progress.total_steps} />
                  <span className="muted small-text">Speed changes pacing only, never decisions.</span>
                </div>

                <div className="metric-grid">
                  <Metric label="Runtime state" mono={false}
                          value={<span data-testid="runtime-state" className={["recovering", "failed"].includes(run.runtime_state) ? "text-warn" : ""}>{humanize(run.runtime_state)}</span>}
                          hint={<span data-testid="runtime-detail">{run.runtime_detail}</span>} />
                  <Metric label="Progress (bars)" value={`${run.progress.steps_done}/${run.progress.total_steps}`} testid="progress" />
                  <Metric label="Simulation time" value={fmtTime(obs?.available_time ?? run.progress.sim_time)} testid="sim-time" />
                  <Metric label="Elapsed" value={fmtSecs(run.progress.elapsed_seconds)} />
                  <Metric label="ETA" value={run.progress.eta_seconds === null ? "unavailable" : fmtSecs(run.progress.eta_seconds)}
                          testid="eta" title={run.progress.eta_basis} hint={run.progress.eta_basis} />
                  <Metric label="Worker" value={<WorkerHealth health={health} />} mono={false} />
                  <Metric label="Heartbeat" mono={false}
                          value={
                            <span className={run.lease_expired ? "text-warn" : "mono"}>
                              {run.progress.heartbeat_age_seconds === null ? "—" : `${fmtSecs(run.progress.heartbeat_age_seconds)} ago`}
                              {run.lease_expired && " (lease expired — awaiting recovery)"}
                            </span>
                          } />
                  <Metric label="Attempt" value={`${run.attempt}/${run.max_attempts}`} />
                  <Metric label="Speed" value={speedLabel(run.control.speed)} testid="speed-now" />
                  <Metric label="Fixture" value={`${run.config.fixture_id} · seed ${run.config.seed}`} />
                  <Metric label="Last synthetic price" value={fmtNum(obs?.close)} testid="last-price" />
                </div>

                {run.error && (
                  <Notice tone="neg" title={run.status === "failed" ? "Run failed" : "Run error"}>
                    <span data-testid="run-error">{run.status === "failed" ? "Failure: " : ""}{run.error}</span>
                  </Notice>
                )}

                {(run.recovery_log.length > 0 || run.control_log.length > 1) && (
                  <div className="log-grid">
                    {run.recovery_log.length > 0 && (
                      <div className="log" data-testid="recovery-log">
                        <div className="log-title"><Icon name="shield" size={14} /> Recovery log</div>
                        <ol className="timeline">
                          {run.recovery_log.map((r, i) => (
                            <li key={i}><b>attempt {r.attempt} · {r.event}</b> — {r.detail}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                    {run.control_log.length > 1 && (
                      <div className="log" data-testid="control-log">
                        <div className="log-title"><Icon name="replay" size={14} /> Replay control log <span className="muted">(operational, not part of the decision trace)</span></div>
                        <ol className="timeline">
                          {run.control_log.slice(-6).map((c, i) => (
                            <li key={i}>
                              <b>{c.command}</b>
                              {c.at_step !== undefined && ` at bar ${String(c.at_step)}`}
                              {c.speed !== undefined && ` · speed ${speedLabel(Number(c.speed))}`} · <span className="mono">{fmtTime(c.at)}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}
              </Card>

              <Card material="synthetic" title="Synthetic price series" icon="market" eyebrow="Demo fixture · not market data"
                    actions={<Badge tone="synthetic">SYNTHETIC</Badge>}>
                <SyntheticChart points={prices} totalSteps={run.progress.total_steps} />
              </Card>

              <div className="two-col">
                <Card material="synthetic" testid="market-view" title="Dummy market view" icon="eye"
                      eyebrow="Scripted demo output" actions={<Badge tone="synthetic">DEMO</Badge>}>
                  {view ? (
                    <div className="stack-sm">
                      <div className="demo-readout">
                        <span className="demo-readout-value" data-testid="view-bias">{view.horizons[0]?.bias}</span>
                        <Badge tone={view.validity === "STALE" ? "warn" : "neutral"} testid="view-validity">{view.validity}</Badge>
                      </div>
                      <p className="body-text">{view.summary}</p>
                      <p className="muted small-text">Qualitative confidence (not a probability): {view.confidence} · data {view.data_quality.status}</p>
                      <ol className="scenario-list">
                        {view.scenarios.map((s) => <li key={s.scenario_id}>{s.label}</li>)}
                      </ol>
                    </div>
                  ) : <p className="muted">—</p>}
                </Card>

                <Card material="synthetic" testid="decision" title="Dummy decision" icon="scale"
                      eyebrow="Scripted demo output" actions={<Badge tone="synthetic">DEMO</Badge>}>
                  {decision ? (
                    <div className="stack-sm">
                      <div className="demo-readout">
                        <span className="demo-readout-value" data-testid="permitted-action">{decision.permitted_action}</span>
                        {decision.proposed_action !== decision.permitted_action && (
                          <span className="muted small-text">proposed {decision.proposed_action}</span>
                        )}
                      </div>
                      <p className="body-text" data-testid="decision-reason">{decision.reason}</p>
                      {decision.blocking_reasons.length > 0 && (
                        <Notice tone="warn">Blocked by demo scaffolding: {decision.blocking_reasons.join(", ")}</Notice>
                      )}
                    </div>
                  ) : <p className="muted">—</p>}
                </Card>
              </div>

              <Card material="synthetic" title="Action history" icon="pulse" eyebrow="Changes, entries, exits and blocks (demo)">
                <div className="table-wrap">
                  <table className="table" data-testid="action-history">
                    <thead><tr><th>Sim time</th><th>Proposed</th><th>Permitted</th><th>Reason</th></tr></thead>
                    <tbody>
                      {actionHistory.map((d) => (
                        <tr key={d.seq}>
                          <td className="mono nowrap">{fmtTime(d.sim_time)}</td>
                          <td className="mono">{d.payload.proposed_action}</td>
                          <td><span className="mono strong">{d.payload.permitted_action}</span></td>
                          <td>{d.payload.reason}</td>
                        </tr>
                      ))}
                      {actionHistory.length === 0 && (
                        <tr><td colSpan={4} className="muted">No decisions yet.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>

              {manifest && (
                <Card title="Run artifacts" icon="file" testid="artifacts" eyebrow="Immutable, hashed run outputs"
                      actions={<a className="btn btn-ghost" href={`/api/runs/${manifest.run_id}/manifest`} target="_blank" rel="noreferrer"><Icon name="file" size={15} /><span>manifest.json</span></a>}>
                  <div className="artifact-summary">
                    <Metric label="Validation" mono={false}
                            value={<Badge tone={manifest.validation.passed ? "pos" : "neg"} icon={manifest.validation.passed ? "check" : "x"}>
                              <span data-testid="validation">{manifest.validation.passed ? "PASS" : `FAIL (${manifest.validation.failed.join(", ")})`}</span>
                            </Badge>} />
                    <Metric label="Semantic trace" value={<code data-testid="trace-hash">{manifest.semantic_trace_hash.slice(0, 16)}…</code>}
                            hint={`${manifest.event_count} events`} />
                    <Metric label="Schema" value={manifest.schema_version} />
                    <Metric label="Engine" value={manifest.engine_version} />
                  </div>
                  <ul className="artifact-grid">
                    {manifest.artifacts.map((a) => (
                      <li key={a.name} className="artifact">
                        <Icon name="file" size={15} />
                        <a href={`/api/runs/${manifest.run_id}/artifacts/${a.name}`} className="mono">{a.name}</a>
                        {a.name.endsWith(".parquet") && (
                          <a className="artifact-view" href={`/api/runs/${manifest.run_id}/artifacts/${a.name}?format=json`} target="_blank" rel="noreferrer">view</a>
                        )}
                        {a.rows !== null && <span className="muted mono">{a.rows} rows</span>}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              <details className="demo-internals" data-testid="demo-internals">
                <summary>
                  <Icon name="chevron" size={14} className="summary-chevron" />
                  <span>DEMO internals — synthetic account scaffolding</span>
                  <span className="muted small-text">Replay infrastructure only. The product never sizes positions, chooses leverage or manages an account.</span>
                </summary>
                <div className="demo-internals-body" data-testid="position">
                  {account ? (
                    <div className="kv-grid wide">
                      <span>Side</span><Mono><span data-testid="position-side">{account.position.side}</span></Mono>
                      <span>Quantity</span><Mono>{account.position.quantity} BTC</Mono>
                      <span>Avg entry</span><Mono>{fmtNum(account.position.average_entry_price)}</Mono>
                      <span>Exposure</span><Mono>{fmtNum(account.exposure_fraction, 3)}× equity</Mono>
                      <span>Equity</span><Mono>{fmtNum(account.equity)}</Mono>
                      <span>Realized / unrealized</span><Mono>{fmtNum(account.realized_pnl)} / {fmtNum(account.unrealized_pnl)}</Mono>
                      <span>Fees</span><Mono>{fmtNum(account.fees_paid)}</Mono>
                      <span>Funding</span><Mono>{account.funding}</Mono>
                    </div>
                  ) : <p className="muted">—</p>}
                </div>
              </details>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
