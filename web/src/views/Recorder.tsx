import { useCallback, useEffect, useRef, useState } from "react";
import { recorderApi, RecorderSession } from "../api";
import { fmtInt, fmtNs, fmtSecs, fmtTime } from "../lib/format";
import { replaySource } from "../lib/route";
import { useHealth } from "../shell/health";
import { Icon } from "../ui/Icon";
import { Badge, Button, Card, cx, EmptyState, Field, Metric, Notice, PageHeader, Skeleton, statusTone } from "../ui/primitives";

// Owner-facing control/status for the durable public market recorder. Public, read-only evidence
// collection — there are no trading controls anywhere in this view.

const DURATIONS = [
  { label: "30 min", minutes: 30 },
  { label: "2 h", minutes: 120 },
  { label: "6 h", minutes: 360 },
  { label: "12 h", minutes: 720 },
];

const RECORDED = [
  { name: "Traded 1m candles", ch: "candle1m", conn: "business WS" },
  { name: "Mark-price 1m candles", ch: "mark-price-candle1m", conn: "business WS" },
  { name: "Index 1m candles", ch: "index-candle1m", conn: "business WS" },
  { name: "Live funding information", ch: "funding-rate", conn: "public WS" },
  { name: "Server-time clock probe", ch: "public/time", conn: "REST" },
];

function delay(s: number | null): string {
  return s === null ? "—" : `${s.toFixed(3)} s`;
}

function isActive(s: RecorderSession): boolean {
  return s.status === "running" || s.status === "queued";
}

function Connections({ s }: { s: RecorderSession }) {
  const entries = Object.entries(s.stats?.connection_state ?? {});
  return (
    <span className="conn-list" data-testid="recorder-connections">
      {isActive(s)
        ? entries.length
          ? entries.map(([k, v]) => (
              <Badge key={k} tone={statusTone(v)} dot>{`${k}: ${v}`}</Badge>
            ))
          : "—"
        : "closed (session ended)"}
    </span>
  );
}

function Report({ s }: { s: RecorderSession }) {
  const report = s.report!;
  return (
    <div className="report" data-testid="recorder-report">
      <div className="report-head">
        <div>
          <div className="log-title"><Icon name="clock" size={14} /> Measured receipt timing</div>
          <div className="muted small-text">This session only; client-observed, not exchange publication. Bar end → first completed push.</div>
        </div>
        <div className="report-links">
          <a className="file-link" href={`/api/recorder/sessions/${s.session_id}/files/manifest.json`} target="_blank" rel="noreferrer">
            <Icon name="file" size={14} /><span className="mono">manifest</span>
          </a>
          <a className="file-link" href={`/api/recorder/sessions/${s.session_id}/files/report.json`} target="_blank" rel="noreferrer">
            <Icon name="file" size={14} /><span className="mono">report</span>
          </a>
        </div>
      </div>
      <div className="table-wrap">
        <table className="table table-compact">
          <thead><tr><th>Channel</th><th className="num">Completed bars</th><th className="num">Delay p50</th><th className="num">Delay max</th></tr></thead>
          <tbody>
            {report.bars.map((b) => (
              <tr key={b.channel_key} data-testid={`report-row-${b.channel_key}`}>
                <td className="mono strong">{b.channel_key}</td>
                <td className="num mono" data-testid="completed-bars">{b.completed_bars}</td>
                <td className="num mono" title={b.delay_raw.p50_s === null ? undefined : `${b.delay_raw.p50_s} s`}>{delay(b.delay_raw.p50_s)}</td>
                <td className="num mono" title={b.delay_raw.max_s === null ? undefined : `${b.delay_raw.max_s} s`}>{delay(b.delay_raw.max_s)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="metric-row">
        <Metric label="Funding snapshots" value={`${report.funding.snapshots_ws} ws / ${report.funding.snapshots_poll} poll`} />
        <Metric label="Clock quality" value={report.clock.clock_quality}
                hint={report.clock.offset_estimate_ms_median !== null ? `offset ≈ ${report.clock.offset_estimate_ms_median.toFixed(1)} ms vs OKX server time` : undefined} />
        <Metric label="Outages" value={report.outages.length} tone={report.outages.length ? "warn" : undefined} />
        <Metric label="Duration" value={fmtSecs(report.duration_s)} />
      </div>
    </div>
  );
}

function SessionCard({ s, detail, onStop }: { s: RecorderSession; detail: RecorderSession | null; onStop: () => void }) {
  const active = isActive(s);
  const st = s.stats ?? {};
  const withReport = detail?.report ? detail : null;
  return (
    <li className={cx("session", active && "is-active")} data-testid={`recorder-session-${s.session_id}`}>
      <div className="session-head">
        <div className="min-0">
          <div className="eyebrow">{active ? "Active session" : `Session · ${fmtTime(s.created_at)}`}</div>
          <div className="session-id mono">{s.session_id}</div>
        </div>
        <div className="session-status">
          <Badge tone={statusTone(s.status)} dot testid="recorder-status">{s.status.toUpperCase()}</Badge>
          {s.stop_requested && s.status === "running" && <span className="muted small-text">stopping…</span>}
          {active && !s.stop_requested && (
            <Button variant="danger" icon="stop" onClick={onStop} data-testid="recorder-stop">Stop</Button>
          )}
          {!active && s.manifest_status && s.manifest_status !== "failed" && (
            <Button variant="secondary" icon="play" onClick={() => replaySource("recording", s.session_id)}
                    data-testid="recorder-replay" title="Open Market Replay with this recording preselected">
              Replay recording
            </Button>
          )}
        </div>
      </div>
      {s.lease_expired && <Notice tone="warn">Recorder process not heartbeating — awaiting recovery.</Notice>}
      <div className="metric-grid compact">
        <Metric label="Elapsed" value={`${fmtSecs(s.elapsed_seconds)}${s.max_duration_seconds ? ` / max ${fmtSecs(s.max_duration_seconds)}` : ""}`} />
        <Metric label="Heartbeat" value={s.heartbeat_age_seconds === null ? "—" : `${fmtSecs(s.heartbeat_age_seconds)} ago`} />
        <Metric label="Messages" value={fmtInt(st.records ?? 0)} testid="recorder-records" />
        <Metric label="Last receipt" value={fmtNs(st.last_recv_utc_ns)} />
        <Metric label="Reconnects / errors" value={`${st.reconnects ?? 0} / ${st.errors ?? 0}`}
                tone={(st.reconnects ?? 0) + (st.errors ?? 0) > 0 ? "warn" : undefined} />
        <Metric label="Connections" value={<Connections s={s} />} mono={false} />
      </div>
      <div className="session-foot">
        <div className="chips">
          <span className="chips-label">Subscribed</span>
          {(st.subscribed ?? []).length
            ? (st.subscribed ?? []).map((c) => <span key={c} className="chip mono">{c}</span>)
            : <span className="muted">—</span>}
          {st.funding_fallback && <Badge tone="warn">+ funding REST poll (POLL_OBSERVED)</Badge>}
        </div>
        <div className="output-ref"><span className="chips-label">Output</span><code>{s.session_path}</code></div>
      </div>
      {s.error && <Notice tone="neg" title="Session error"><span data-testid="recorder-error">{s.error}</span></Notice>}
      {withReport && <Report s={withReport} />}
    </li>
  );
}

export function Recorder() {
  const { health } = useHealth();
  const [sessions, setSessions] = useState<RecorderSession[] | null>(null);
  const [details, setDetails] = useState<Record<string, RecorderSession>>({});
  const detailsRef = useRef(details);
  detailsRef.current = details;
  const [minutes, setMinutes] = useState(360);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await recorderApi.list();
      setSessions(r.sessions);
      setError(null);
      for (const s of r.sessions.slice(0, 5)) {
        if (s.manifest_status && !detailsRef.current[s.session_id]) {
          const d = await recorderApi.detail(s.session_id);
          setDetails((cur) => ({ ...cur, [s.session_id]: d }));
        }
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(refresh, 3000);
    return () => window.clearInterval(t);
  }, [refresh]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const list = sessions ?? [];
  const active = list.some(isActive);
  const recorderWorkers = health?.recorder_workers?.alive ?? null;

  return (
    <div className="page page-recorder" data-testid="page-recorder">
      <PageHeader
        eyebrow="Workbench · live evidence"
        title="Recorder"
        lede="Prospective capture of public OKX BTC-USDT-SWAP market data with measured local receipt times — evidence that cannot be reconstructed later."
        meta={
          <div className="badge-row">
            <Badge tone="info" icon="eye">Public data</Badge>
            <Badge tone="info" icon="lock">Read-only</Badge>
            <Badge tone="neutral" icon="x">No trading</Badge>
          </div>
        }
      />

      <div className="recorder-layout" data-testid="recorder-panel">
        <div className="recorder-top">
          <Card className="recorder-hero" icon="recorder" eyebrow="Recorder control"
                title="Public market evidence collection — no trading">
            <p className="body-text muted">
              Records public candles (traded, mark, index) and live funding information with local receipt times, for
              availability research. Recording runs in the recorder worker; closing the browser does not stop it.
            </p>
            <div className="recorder-controls">
              <Field label="Max duration">
                <select className="control" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} data-testid="recorder-duration">
                  {DURATIONS.map((d) => <option key={d.minutes} value={d.minutes}>{d.label}</option>)}
                </select>
              </Field>
              <Button icon="recorder" onClick={() => act(() => recorderApi.start(minutes))} disabled={active || busy} data-testid="recorder-start">
                Start recording
              </Button>
              <div className="recorder-state">
                {active
                  ? <Badge tone="info" dot>A session is active</Badge>
                  : <Badge tone="neutral">Idle</Badge>}
                <span className={cx("small-text", recorderWorkers === 0 ? "text-warn" : "muted")}>
                  {recorderWorkers === null ? "Recorder worker status unknown"
                    : recorderWorkers === 0 ? "No recorder worker alive — a started session stays queued"
                    : `${recorderWorkers} recorder worker alive`}
                </span>
              </div>
            </div>
            {error && <Notice tone="neg" title="Recorder request failed">{error}</Notice>}
          </Card>

          <Card title="What is recorded" icon="layers" eyebrow="Official OKX public endpoints only">
            <ul className="recorded-list">
              {RECORDED.map((r) => (
                <li key={r.ch}>
                  <span>{r.name}</span>
                  <span className="mono muted">{r.ch}</span>
                  <span className="chip mono">{r.conn}</span>
                </li>
              ))}
            </ul>
            <p className="muted small-text">
              Receipt time is taken immediately after each read returns — client-observed, not the exchange's publication
              instant. A REST poll is used only if the funding channel is unavailable, and is labelled POLL_OBSERVED.
            </p>
          </Card>
        </div>

        <div className="section-head">
          <h2 className="section-title">Sessions</h2>
          <span className="section-hint">Latest five · append-only journals under the data root</span>
        </div>

        {sessions === null && !error && <Card><Skeleton lines={4} /></Card>}
        <ul className="session-list" data-testid="recorder-sessions">
          {list.slice(0, 5).map((s) => (
            <SessionCard key={s.session_id} s={s} detail={details[s.session_id] ?? null}
                         onStop={() => act(() => recorderApi.stop(s.session_id))} />
          ))}
          {sessions !== null && list.length === 0 && (
            <li>
              <Card>
                <EmptyState icon="recorder" title="No recording sessions yet">
                  Start a session to begin collecting public evidence. Sessions survive browser closes and are finalized
                  with hashes and a timing report.
                </EmptyState>
              </Card>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
