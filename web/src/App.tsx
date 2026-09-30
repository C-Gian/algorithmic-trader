import { useCallback, useEffect, useMemo, useState } from "react";
import { api, Decision, Health, JournalEvent, Manifest, PricePoint, Run, Snapshot } from "./api";
import { DataView } from "./DataView";

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

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/(\.\d+)?(Z|\+00:00)$/, " UTC");
}

function fmtNum(v: string | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("en-US", { maximumFractionDigits: digits }) : v;
}

function fmtSecs(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  return s < 60 ? `${s.toFixed(1)}s` : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

function selectedFromHash(): string | null {
  const m = window.location.hash.match(/run=([\w-]+)/);
  return m ? m[1] : null;
}

function PriceChart({ points }: { points: PricePoint[] }) {
  const W = 720;
  const H = 220;
  const valid = points.filter((p) => p.close !== null);
  if (valid.length < 2) return <div className="chart empty">waiting for synthetic bars…</div>;
  const closes = valid.map((p) => Number(p.close));
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const n = Math.max(points[points.length - 1].step + 1, 2);
  const x = (step: number) => (step / (n - 1)) * (W - 20) + 10;
  const y = (v: number) => H - 20 - ((v - min) / (max - min || 1)) * (H - 40);
  const path = valid.map((p, i) => `${i ? "L" : "M"}${x(p.step).toFixed(1)},${y(Number(p.close)).toFixed(1)}`).join(" ");
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="synthetic BTC price chart">
      <text x={10} y={14} className="chart-label">
        SYNTHETIC BTC-PERP close · {fmtNum(String(min), 1)} – {fmtNum(String(max), 1)} · shaded = missing data ·
        green = buy fill · red = sell fill
      </text>
      {points
        .filter((p) => p.quality !== "OK")
        .map((p) => (
          <rect key={`gap-${p.step}`} x={x(p.step) - 3} y={20} width={6} height={H - 40} className="gap" />
        ))}
      <path d={path} className="line" />
      {points
        .filter((p) => p.fill && p.close !== null)
        .map((p) => (
          <circle key={`f-${p.step}`} cx={x(p.step)} cy={y(Number(p.close))} r={4} className={p.fill === "BUY" ? "buy" : "sell"}>
            <title>{`${p.fill} fill at bar ${p.step}`}</title>
          </circle>
        ))}
    </svg>
  );
}

function RunStatusBadge({ run }: { run: Run }) {
  return (
    <span className={`badge ${run.runtime_state}`} data-testid="run-status" title={run.runtime_detail}>
      {run.runtime_state.replace("_", " ").toUpperCase()}
    </span>
  );
}

function speedLabel(v: number): string {
  return v === 0 ? "max" : `${v} bar${v === 1 ? "" : "s"}/s`;
}

function WorkerHealth({ health }: { health: Health | null }) {
  if (!health) return <span data-testid="worker-health" className="warn">unknown (API unreachable)</span>;
  const w = health.workers;
  const last = w.recent[0];
  if (w.alive === 0) {
    return (
      <span data-testid="worker-health" className="warn">
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

function RunsView() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<string | null>(selectedFromHash());
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [prices, setPrices] = useState<PricePoint[]>([]);
  const [decisions, setDecisions] = useState<JournalEvent<Decision>[]>([]);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [speed, setSpeed] = useState(4);
  const [fault, setFault] = useState("none");
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);

  const refreshRuns = useCallback(async () => {
    try {
      const [rs, h] = await Promise.all([api.listRuns(), api.health()]);
      setRuns(rs);
      setHealth(h);
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

  const loadDetails = useCallback(async (id: string, s: Snapshot) => {
    const [p, d] = await Promise.all([api.prices(id), api.decisions(id)]);
    setPrices(p);
    setDecisions(d);
    if (s.run.has_manifest) setManifest(await api.manifest(id));
  }, []);

  // Live updates via SSE. Every (re)connection starts from a full snapshot.
  useEffect(() => {
    if (!selected) return;
    window.location.hash = `run=${selected}`;
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

  const start = async () => {
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
    <div className="app">
      <div className="demo-banner" data-testid="demo-banner">
        DEMO / SYNTHETIC — scripted dummy trader on a synthetic BTC-perpetual fixture. Not market data. Nothing
        here is research or profitability evidence.
      </div>
      {error && <div className="error">{error}</div>}
      <div className="layout">
        <aside className="panel runs">
          <h2>Runs</h2>
          <div className="start">
            <label>
              Replay speed
              <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} data-testid="speed">
                {SPEEDS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </label>
            <label>
              Fault injection (demo)
              <select value={fault} onChange={(e) => setFault(e.target.value)} data-testid="fault">
                {FAULTS.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </label>
            <button onClick={start} data-testid="start-run">Start synthetic replay</button>
          </div>
          <ul className="run-list">
            {runs.map((r) => (
              <li key={r.run_id} className={r.run_id === selected ? "selected" : ""} onClick={() => setSelected(r.run_id)}>
                <div className="run-id">{r.run_id}</div>
                <div className="run-meta">
                  <RunStatusBadge run={r} /> {r.progress.steps_done}/{r.progress.total_steps}
                  {r.config.fault !== "none" && <span className="tag">fault: {r.config.fault}</span>}
                </div>
              </li>
            ))}
            {runs.length === 0 && <li className="muted">No runs yet.</li>}
          </ul>
        </aside>

        <main className="home">
          {!run && <div className="panel muted">Start a synthetic replay to see the dummy trader.</div>}
          {run && (
            <>
              <section className="panel health" data-testid="run-panel">
                <div className="row">
                  <h2>{run.run_id}</h2>
                  <RunStatusBadge run={run} />
                  <span className={`live ${live ? "on" : ""}`}>{live ? "● live" : "○ idle"}</span>
                  {!TERMINAL.has(run.status) && (
                    <button className="secondary" onClick={() => command(() => api.cancelRun(run.run_id))} disabled={run.cancel_requested} data-testid="cancel-run">
                      {run.cancel_requested ? "Cancelling…" : "Cancel"}
                    </button>
                  )}
                </div>
                {!TERMINAL.has(run.status) && !run.cancel_requested && (
                  <div className="controls" data-testid="replay-controls">
                    {run.control.paused ? (
                      <>
                        <button onClick={() => command(() => api.resumeRun(run.run_id))} data-testid="resume-run">Resume</button>
                        <button
                          onClick={() => command(() => api.stepRun(run.run_id))}
                          disabled={run.progress.steps_done + run.control.step_budget >= run.progress.total_steps}
                          data-testid="step-run"
                        >
                          Step one bar
                        </button>
                      </>
                    ) : (
                      <button onClick={() => command(() => api.pauseRun(run.run_id))} data-testid="pause-run">Pause</button>
                    )}
                    <label className="inline">
                      Speed
                      <select
                        value={run.control.speed}
                        onChange={(e) => command(() => api.setSpeed(run.run_id, Number(e.target.value)))}
                        data-testid="run-speed"
                      >
                        {[...new Set([...SPEEDS.map((s) => s.value), run.control.speed])].map((v) => (
                          <option key={v} value={v}>{speedLabel(v)}</option>
                        ))}
                      </select>
                    </label>
                    <span className="muted">Speed changes pacing only, never decisions.</span>
                  </div>
                )}
                <progress value={run.progress.steps_done} max={run.progress.total_steps} />
                <div className="grid4">
                  <div>
                    <label>Runtime state</label>
                    <span data-testid="runtime-state" className={["recovering", "failed"].includes(run.runtime_state) ? "warn" : ""}>
                      {run.runtime_state.replace("_", " ")}
                    </span>
                    <div className="muted small" data-testid="runtime-detail">{run.runtime_detail}</div>
                  </div>
                  <div><label>Progress (bars)</label><span data-testid="progress">{run.progress.steps_done}/{run.progress.total_steps}</span></div>
                  <div><label>Simulation time</label><span data-testid="sim-time">{fmtTime(obs?.available_time ?? run.progress.sim_time)}</span></div>
                  <div><label>Elapsed</label><span>{fmtSecs(run.progress.elapsed_seconds)}</span></div>
                  <div>
                    <label>ETA</label>
                    <span data-testid="eta" title={run.progress.eta_basis}>
                      {run.progress.eta_seconds === null ? "unavailable" : fmtSecs(run.progress.eta_seconds)}
                    </span>
                    <div className="muted small">{run.progress.eta_basis}</div>
                  </div>
                  <div><label>Worker</label><WorkerHealth health={health} /></div>
                  <div>
                    <label>Heartbeat</label>
                    <span className={run.lease_expired ? "warn" : ""}>
                      {run.progress.heartbeat_age_seconds === null ? "—" : `${fmtSecs(run.progress.heartbeat_age_seconds)} ago`}
                      {run.lease_expired && " (lease expired — awaiting recovery)"}
                    </span>
                  </div>
                  <div><label>Attempt</label><span>{run.attempt}/{run.max_attempts}</span></div>
                  <div><label>Speed</label><span data-testid="speed-now">{speedLabel(run.control.speed)}</span></div>
                  <div><label>Fixture</label><span>{run.config.fixture_id} · seed {run.config.seed}</span></div>
                  <div><label>Last price</label><span data-testid="last-price">{fmtNum(obs?.close)}</span></div>
                </div>
                {run.error && <div className="error" data-testid="run-error">{run.status === "failed" ? "Failure: " : ""}{run.error}</div>}
                {run.recovery_log.length > 0 && (
                  <div className="recovery" data-testid="recovery-log">
                    <label>Recovery log</label>
                    <ul>
                      {run.recovery_log.map((r, i) => (
                        <li key={i}><b>attempt {r.attempt} · {r.event}</b> — {r.detail}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {run.control_log.length > 1 && (
                  <div className="recovery" data-testid="control-log">
                    <label>Replay control log (operational, not part of the decision trace)</label>
                    <ul>
                      {run.control_log.slice(-6).map((c, i) => (
                        <li key={i}>
                          <b>{c.command}</b>
                          {c.at_step !== undefined && ` at bar ${String(c.at_step)}`}
                          {c.speed !== undefined && ` · speed ${speedLabel(Number(c.speed))}`} · {fmtTime(c.at)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>

              <section className="panel">
                <PriceChart points={prices} />
              </section>

              <div className="cols">
                <section className="panel" data-testid="market-view">
                  <h3>Market view <span className="tag">DEMO</span></h3>
                  {view ? (
                    <>
                      <div className="big">
                        <span className={`bias ${view.horizons[0]?.bias}`} data-testid="view-bias">{view.horizons[0]?.bias}</span>
                        <span className={`validity ${view.validity}`} data-testid="view-validity">{view.validity}</span>
                      </div>
                      <p>{view.summary}</p>
                      <p className="muted">Confidence (qualitative, not a probability): {view.confidence} · data {view.data_quality.status}</p>
                      <ol className="scenarios">
                        {view.scenarios.map((s) => (<li key={s.scenario_id}>{s.label}</li>))}
                      </ol>
                    </>
                  ) : <p className="muted">—</p>}
                </section>

                <section className="panel" data-testid="decision">
                  <h3>Decision</h3>
                  {decision ? (
                    <>
                      <div className="big">
                        <span className={`action ${decision.permitted_action}`} data-testid="permitted-action">{decision.permitted_action}</span>
                        {decision.proposed_action !== decision.permitted_action && (
                          <span className="muted">proposed {decision.proposed_action}</span>
                        )}
                      </div>
                      <p data-testid="decision-reason">{decision.reason}</p>
                      {decision.blocking_reasons.length > 0 && (
                        <p className="warn">Blocked: {decision.blocking_reasons.join(", ")}</p>
                      )}
                    </>
                  ) : <p className="muted">—</p>}
                </section>

                <section className="panel" data-testid="position">
                  <h3>Position <span className="tag">paper</span></h3>
                  {account ? (
                    <div className="kv">
                      <label>Side</label><span data-testid="position-side">{account.position.side}</span>
                      <label>Quantity</label><span>{account.position.quantity} BTC</span>
                      <label>Avg entry</label><span>{fmtNum(account.position.average_entry_price)}</span>
                      <label>Exposure</label><span>{fmtNum(account.exposure_fraction, 3)}× equity</span>
                      <label>Equity</label><span>{fmtNum(account.equity)}</span>
                      <label>Realized / unrealized</label><span>{fmtNum(account.realized_pnl)} / {fmtNum(account.unrealized_pnl)}</span>
                      <label>Fees</label><span>{fmtNum(account.fees_paid)}</span>
                      <label>Funding</label><span>{account.funding}</span>
                    </div>
                  ) : <p className="muted">—</p>}
                </section>
              </div>

              <section className="panel">
                <h3>Action history (changes, entries, exits, blocks)</h3>
                <table className="history" data-testid="action-history">
                  <thead><tr><th>Sim time</th><th>Proposed</th><th>Permitted</th><th>Reason</th></tr></thead>
                  <tbody>
                    {actionHistory.map((d) => (
                      <tr key={d.seq}>
                        <td>{fmtTime(d.sim_time)}</td>
                        <td>{d.payload.proposed_action}</td>
                        <td><span className={`action ${d.payload.permitted_action}`}>{d.payload.permitted_action}</span></td>
                        <td>{d.payload.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              {manifest && (
                <section className="panel" data-testid="artifacts">
                  <h3>Run artifacts</h3>
                  <p>
                    Validation: <b data-testid="validation">{manifest.validation.passed ? "PASS" : `FAIL (${manifest.validation.failed.join(", ")})`}</b>
                    {" · "}semantic trace <code data-testid="trace-hash">{manifest.semantic_trace_hash.slice(0, 16)}…</code> ({manifest.event_count} events)
                    {" · "}<a href={`/api/runs/${manifest.run_id}/manifest`} target="_blank" rel="noreferrer">manifest.json</a>
                  </p>
                  <ul className="artifact-list">
                    {manifest.artifacts.map((a) => (
                      <li key={a.name}>
                        <a href={`/api/runs/${manifest.run_id}/artifacts/${a.name}`}>{a.name}</a>
                        {a.name.endsWith(".parquet") && (
                          <> · <a href={`/api/runs/${manifest.run_id}/artifacts/${a.name}?format=json`} target="_blank" rel="noreferrer">view</a></>
                        )}
                        {a.rows !== null && <span className="muted"> · {a.rows} rows</span>}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function viewFromHash(): "runs" | "data" {
  return window.location.hash.startsWith("#data") ? "data" : "runs";
}

export function App() {
  const [view, setView] = useState<"runs" | "data">(viewFromHash());
  const go = (v: "runs" | "data") => {
    window.location.hash = v === "data" ? "data" : "";
    setView(v);
  };
  return (
    <>
      <nav className="topnav">
        <button className={view === "runs" ? "on" : ""} onClick={() => go("runs")} data-testid="nav-runs">Runs (DEMO replay)</button>
        <button className={view === "data" ? "on" : ""} onClick={() => go("data")} data-testid="nav-data">Data (market datasets)</button>
      </nav>
      {view === "runs" ? <RunsView /> : <DataView />}
    </>
  );
}
