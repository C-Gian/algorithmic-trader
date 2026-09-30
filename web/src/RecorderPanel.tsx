import { useCallback, useEffect, useState } from "react";
import { recorderApi, RecorderSession } from "./api";

// Owner-facing control/status for the durable public market recorder. No trading controls.

const DURATIONS = [
  { label: "30 min", minutes: 30 },
  { label: "2 h", minutes: 120 },
  { label: "6 h", minutes: 360 },
  { label: "12 h", minutes: 720 },
];

function secs(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

function nsTime(ns: number | null | undefined): string {
  if (!ns) return "—";
  return new Date(ns / 1e6).toISOString().replace("T", " ").replace("Z", " UTC");
}

function SessionRow({ s, onStop, detail }: { s: RecorderSession; onStop: () => void; detail: RecorderSession | null }) {
  const active = s.status === "running" || s.status === "queued";
  const st = s.stats ?? {};
  const report = detail?.report;
  return (
    <li className="recorder-session" data-testid={`recorder-session-${s.session_id}`}>
      <div className="row">
        <code>{s.session_id}</code>
        <span className={`badge q-${s.status}`} data-testid="recorder-status">{s.status.toUpperCase()}</span>
        {s.stop_requested && s.status === "running" && <span className="muted">stopping…</span>}
        {s.lease_expired && <span className="warn">recorder process not heartbeating — awaiting recovery</span>}
        {active && !s.stop_requested && (
          <button className="secondary" onClick={onStop} data-testid="recorder-stop">Stop</button>
        )}
      </div>
      <div className="grid4 small-grid">
        <div><label>Elapsed</label><span>{secs(s.elapsed_seconds)}{s.max_duration_seconds ? ` / max ${secs(s.max_duration_seconds)}` : ""}</span></div>
        <div><label>Heartbeat</label><span>{s.heartbeat_age_seconds === null ? "—" : `${secs(s.heartbeat_age_seconds)} ago`}</span></div>
        <div>
          <label>Connections</label>
          <span data-testid="recorder-connections">
            {active
              ? Object.entries(st.connection_state ?? {}).map(([k, v]) => `${k}: ${v}`).join(" · ") || "—"
              : "closed (session ended)"}
          </span>
        </div>
        <div><label>Messages</label><span data-testid="recorder-records">{st.records ?? 0}</span></div>
        <div><label>Last receipt</label><span>{nsTime(st.last_recv_utc_ns)}</span></div>
        <div><label>Reconnects / errors</label><span>{st.reconnects ?? 0} / {st.errors ?? 0}</span></div>
        <div><label>Subscribed</label><span>{(st.subscribed ?? []).join(", ") || "—"}{st.funding_fallback ? " (+ funding REST poll)" : ""}</span></div>
        <div><label>Output</label><span><code>{s.session_path}</code></span></div>
      </div>
      {s.error && <div className="error" data-testid="recorder-error">{s.error}</div>}
      {report && (
        <div className="small" data-testid="recorder-report">
          <b>Measured receipt timing (this session only; client-observed, not exchange publication):</b>{" "}
          {report.bars.map((b) => `${b.channel_key}: ${b.completed_bars} completed bars, bar-end→first completion p50 ${b.delay_raw.p50_s ?? "—"}s max ${b.delay_raw.max_s ?? "—"}s`).join(" · ")}
          {" · "}funding snapshots {report.funding.snapshots_ws} ws / {report.funding.snapshots_poll} poll
          {" · "}clock {report.clock.clock_quality}{report.clock.offset_estimate_ms_median !== null ? ` (offset ≈ ${report.clock.offset_estimate_ms_median.toFixed(1)} ms)` : ""}
          {" · "}outages {report.outages.length}
          {" · "}<a href={`/api/recorder/sessions/${s.session_id}/files/manifest.json`} target="_blank" rel="noreferrer">manifest</a>
          {" · "}<a href={`/api/recorder/sessions/${s.session_id}/files/report.json`} target="_blank" rel="noreferrer">report</a>
        </div>
      )}
    </li>
  );
}

export function RecorderPanel() {
  const [sessions, setSessions] = useState<RecorderSession[]>([]);
  const [details, setDetails] = useState<Record<string, RecorderSession>>({});
  const [minutes, setMinutes] = useState(360);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await recorderApi.list();
      setSessions(r.sessions);
      setError(null);
      for (const s of r.sessions.slice(0, 5)) {
        if (s.manifest_status && !details[s.session_id]) {
          const d = await recorderApi.detail(s.session_id);
          setDetails((cur) => ({ ...cur, [s.session_id]: d }));
        }
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [details]);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(refresh, 3000);
    return () => window.clearInterval(t);
  }, [refresh]);

  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const active = sessions.some((s) => s.status === "running" || s.status === "queued");
  return (
    <section className="panel" data-testid="recorder-panel">
      <h3>Public Market Recorder — no trading</h3>
      <p className="muted small">
        Records public OKX BTC-USDT-SWAP candles (traded, mark, index) and live funding information with local receipt
        times, for later availability research. Runs in the recorder worker; closing the browser does not stop it.
      </p>
      <div className="controls">
        <label className="inline">
          Max duration
          <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} data-testid="recorder-duration">
            {DURATIONS.map((d) => <option key={d.minutes} value={d.minutes}>{d.label}</option>)}
          </select>
        </label>
        <button onClick={() => act(() => recorderApi.start(minutes))} disabled={active} data-testid="recorder-start">
          Start recording
        </button>
        {active && <span className="muted">a session is active</span>}
      </div>
      {error && <div className="error">{error}</div>}
      <ul className="recorder-list" data-testid="recorder-sessions">
        {sessions.slice(0, 5).map((s) => (
          <SessionRow key={s.session_id} s={s} detail={details[s.session_id] ?? null}
                      onStop={() => act(() => recorderApi.stop(s.session_id))} />
        ))}
        {sessions.length === 0 && <li className="muted">No recording sessions yet.</li>}
      </ul>
    </section>
  );
}
