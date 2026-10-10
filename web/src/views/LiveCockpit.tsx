import { useMemo, useState } from "react";
import {
  AdviserMethod, adviserApi, Lens, LiveStatus, LiveView, METHOD_STATUS, METHOD_TEXT,
  METHODS, reasonText, THESIS_TEXT,
} from "../adviser";
import { fmtNum, fmtRecorded, fmtTime, humanize } from "../lib/format";
import { usePoll } from "../lib/usePoll";
import { Icon } from "../ui/Icon";
import { Badge, Button, Card, cx, Mono, Notice, Tone } from "../ui/primitives";
import { HistoryKey, LiveCallHistory } from "./LiveCallHistory";
import { ProposalPanel } from "./LiveProposal";
import { useCopyFeedback } from "./replay/MarketReplay";

// Home live cockpit (WP-009): the Owner starts/stops the local live adviser here. Every value comes from the committed
// live session view (/api/adviser/live); nothing is computed in the browser. Stopped means nothing is monitored and no
// alert is produced. Advice is for a human decision only: no orders, size, leverage or account.

const STATE_TONE: Record<string, Tone> = {
  LIVE: "pos", WARMING_UP: "info", RECONSTRUCTING: "info", STARTING: "info", DISCONNECTED: "warn", UNRESPONSIVE: "neg",
  STOPPED: "neutral", FAILED: "neg",
};
const STATE_TEXT: Record<string, string> = {
  LIVE: "Live", WARMING_UP: "Warming up", RECONSTRUCTING: "Catching up", STARTING: "Starting",
  DISCONNECTED: "Disconnected", UNRESPONSIVE: "Not responding", STOPPED: "Stopped", FAILED: "Failed",
};

function PriceChart({ v }: { v: LiveView | null }) {
  const bars = v?.chart?.minutes ?? [];
  const call = v?.call ?? null;
  const lv = v?.levels ?? {};
  const W = 720;
  const H = 260;
  const shapes = useMemo(() => {
    if (bars.length < 2) return null;
    const closes = bars.map((b) => Number(b.c));
    const lines: { y: number; label: string; cls: string }[] = [];
    const add = (val: string | null | undefined, label: string, cls: string) => {
      if (val) lines.push({ y: Number(val), label, cls });
    };
    add(lv.nearest_resistance_near_edge, "resistance", "lvl-res");
    add(lv.nearest_support_near_edge, "support", "lvl-sup");
    add(lv.box_low, "box low", "lvl-box");
    add(lv.box_up, "box high", "lvl-box");
    if (call) {
      add(call.target, "target", "lvl-target");
      add(call.stop, "stop", "lvl-stop");
    }
    const all = [...bars.flatMap((b) => [Number(b.h), Number(b.l)]), ...lines.map((l) => l.y),
                 ...(call ? call.structural_area.map(Number) : [])];
    const lo = Math.min(...all);
    const hi = Math.max(...all);
    const pad = (hi - lo) * 0.06 || 1;
    const y = (p: number) => H - 16 - ((p - (lo - pad)) / (hi - lo + 2 * pad)) * (H - 32);
    const x = (i: number) => 8 + (i / (bars.length - 1)) * (W - 90);
    const path = closes.map((c, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(c).toFixed(1)}`).join(" ");
    const area = call ? { y1: y(Number(call.structural_area[1])), y2: y(Number(call.structural_area[0])) } : null;
    // the admissible band is drawn only while the backend says the entry is AVAILABLE (never as a usable-looking past level)
    const adm = call?.admissible_bounds && call.entry_status === "AVAILABLE" && call.presentation !== "NOT_CURRENT" ? { y1: y(Number(call.admissible_bounds[1])), y2: y(Number(call.admissible_bounds[0])) } : null;
    return { path, lines: lines.map((l) => ({ ...l, py: y(l.y) })), area, adm, last: { x: x(closes.length - 1), y: y(closes[closes.length - 1]) } };
  }, [bars, call, lv]);
  if (!shapes) {
    return <div className="chart-empty" data-testid="live-chart-empty">No live price yet — start the adviser to load the
      latest complete minutes.</div>;
  }
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="live-chart" role="img" aria-label="BTC traded price, last complete minutes"
         data-testid="live-chart">
      {shapes.area && <rect x={8} width={W - 90} y={shapes.area.y1} height={Math.max(1, shapes.area.y2 - shapes.area.y1)}
                            className="band-area"><title>structural entry area</title></rect>}
      {shapes.adm && <rect x={8} width={W - 90} y={shapes.adm.y1} height={Math.max(1, shapes.adm.y2 - shapes.adm.y1)}
                           className="band-admissible"><title>admissible now</title></rect>}
      {shapes.lines.map((l) => (
        <g key={l.label + l.y} className={cx("lvl", l.cls)}>
          <line x1={8} x2={W - 90} y1={l.py} y2={l.py} />
          <text x={W - 84} y={l.py + 4}>{l.label} {fmtNum(l.y, 1)}</text>
        </g>
      ))}
      <path d={shapes.path} className="price-line" />
      <circle cx={shapes.last.x} cy={shapes.last.y} r={3} className="price-dot" />
    </svg>
  );
}

function lensText(l: Lens): string {
  if (l.result === null || l.result === undefined) return "unavailable";
  if (typeof l.result === "object") {
    return Object.entries(l.result as Record<string, unknown>).map(([k, v]) => `${humanize(k)} ${String(v)}`).join(" · ");
  }
  return humanize(String(l.result));
}

function LensCard({ l }: { l: Lens }) {
  const st = String(l.status);
  const tone: Tone = st === "READY" || st === "LIVE_QUOTED" || st === "HISTORICAL_BASE" ? "pos"
    : st === "UNAVAILABLE" || st === "STALE" ? "warn" : st === "LIMITED" || st.includes("UNKNOWN") || st === "NOT_COVERED" ? "pending" : "info";
  return (
    <div className="lens-card" data-testid={`lens-${l.lens}`}>
      <div className="lens-top">
        <span className="lens-name">{l.name}</span>
        <Badge tone={tone}>{humanize(st)}</Badge>
      </div>
      <div className="lens-result">{lensText(l)}</div>
      <div className="lens-role">{l.role}</div>
      {l.since && <div className="lens-since mono">since {fmtTime(l.since)}</div>}
    </div>
  );
}

// A stored alert is a past event: its headline describes, in the past tense, what the recorded change type was; the
// guidance text frozen at that revision stays readable only as history. Current availability is never read from here.
const ALERT_EVENT_IT: Record<string, string> = {
  NEW_CALL: "Il sistema ha emesso una nuova call.",
  ENTRY_REOPENED: "Il sistema ha segnalato che l'ingresso era di nuovo disponibile.",
  ENTRY_WITHDRAWN: "Il sistema ha segnalato che l'ingresso non era più disponibile.",
  ENTRY_UNVERIFIED: "Il sistema ha segnalato che la disponibilità dell'ingresso non era confermabile.",
  TERMINAL: "Il sistema ha segnalato la conclusione della call.",
};
const CURRENT_IS_IN_PANEL = "La disponibilità attuale dell'ingresso si legge nel riquadro principale «Che cosa propone il "
  + "sistema adesso», che riporta lo stato attuale del sistema.";

function HistoricalAlert({ a }: { a: LiveStatus["alerts"][number] }) {
  return (
    <div className="hist-alert" data-testid="historical-alert" data-change-type={a.change_type} data-alert-key={a.alert_key}>
      <span className="hist-alert-time mono small-text" data-testid="alert-time">{fmtRecorded(a.created_at)}</span>
      <span className="hist-alert-event" data-testid="alert-event">
        {ALERT_EVENT_IT[a.change_type] ?? `Il sistema ha registrato un cambiamento (${humanize(a.change_type)}).`}</span>
      <details className="hist-alert-recorded" data-testid="alert-recorded">
        <summary>Testo registrato a quell'ora</summary>
        <p className="hist-alert-text" data-testid="alert-recorded-text">{a.summary}</p>
        <p className="muted small-text" data-testid="alert-recorded-note">Fasce d'ingresso, livelli e scadenze in questo
          testo si riferiscono a quell'evento passato: non indicano un ingresso utilizzabile adesso.</p>
      </details>
    </div>
  );
}

function Timeline({ st, onHistory }: { st: LiveStatus; onHistory: (callId: string) => void }) {
  const v = st.view;
  const items: { at: string; kind: string; text: string; alert: LiveStatus["alerts"][number] | null; callId?: string }[] = [
    ...st.alerts.map((a) => ({ at: a.created_at, kind: humanize(a.change_type), text: a.summary, alert: a })),
    ...(v?.recent_calls ?? []).map((c) => ({ at: c.terminal_at, kind: `${c.direction} ${c.family} ${THESIS_TEXT[c.terminal] ?? c.terminal}`,
                                             text: reasonText(c.reason), alert: null, callId: c.call_id })),
    ...(v?.notes ?? []).slice(-6).map((n) => ({ at: n.at, kind: humanize(n.event), text: "", alert: null })),
  ].sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, 14);
  if (!items.length) return <p className="muted small-text">No material change yet.</p>;
  return (
    <>
      {items.some((x) => x.alert) && (
        <p className="muted small-text alerts-pointer" data-testid="timeline-current-pointer">Gli avvisi sono eventi registrati nel passato.
          {" "}{CURRENT_IS_IN_PANEL}</p>
      )}
      <ol className="change-timeline" data-testid="live-timeline">
        {items.map((x, i) => (
          <li key={i} className={cx(x.alert && "tl-alert", x.alert && !x.alert.acknowledged && "is-new")}>
            {x.alert ? <HistoricalAlert a={x.alert} /> : (
              <>
                <span className="mono small-text">{fmtTime(x.at).slice(11, 19)}</span>
                <span className="tl-kind">{x.kind}</span>
                <span className="tl-text">{x.text}</span>
              </>
            )}
            {x.alert && !x.alert.acknowledged && (
              <button type="button" className="link-btn" onClick={() => void adviserApi.ack(x.alert!.alert_key)}>dismiss</button>
            )}
            {x.callId && v?.run_id && (
              <button type="button" className="link-btn" onClick={() => onHistory(x.callId!)}
                      data-testid="timeline-call-history-open">history</button>
            )}
          </li>
        ))}
      </ol>
    </>
  );
}

export function LiveCockpit() {
  const poll = usePoll(adviserApi.live, 1500);
  const st = poll.data;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, runCopy] = useCopyFeedback();
  // WP-011: the method is chosen explicitly before Start; a running session keeps its pinned method
  const [method, setMethod] = useState<AdviserMethod>("v0.2");
  const v = st?.view && st.view.chart ? st.view : null;
  const state = st?.state ?? "STOPPED";
  const running = !!st?.running;
  const act = async (fn: () => Promise<LiveStatus>) => {
    setBusy(true);
    try {
      await fn();
      await poll.refresh();
      setError(null);
    } catch (e) {
      setError((e as Error).message.replace(/^\d+ /, ""));
    } finally {
      setBusy(false);
    }
  };
  const copy = () => void runCopy(() => adviserApi.analysis());
  // the history of one call, fixed to the run + call it was opened from (never re-pointed at a newer call/session)
  const [history, setHistory] = useState<HistoryKey | null>(null);
  const openHistory = (callId: string) => {
    if (!v?.run_id) return;
    setHistory({ runId: v.run_id, callId, sessionId: st?.session?.session_id ?? null });
    window.setTimeout(() => document.querySelector("[data-testid=live-call-history]")?.scrollIntoView({ block: "nearest" }), 0);
  };
  const newAlerts = (st?.alerts ?? []).filter((a) => !a.acknowledged);
  return (
    <section className="live-cockpit" data-testid="live-cockpit">
      <div className="live-bar">
        <div className="live-bar-main">
          <Badge tone={STATE_TONE[state] ?? "neutral"} dot testid="live-state">{STATE_TEXT[state] ?? humanize(state)}</Badge>
          <span className="live-msg" data-testid="live-message">{st?.message ?? "Loading…"}</span>
          {v?.last_receipt && <span className="muted small-text mono">last receipt {fmtTime(v.last_receipt)}</span>}
          {st?.session && <Badge tone="info" testid="live-session-method">{METHOD_TEXT[st.session.method ?? "v0.2"] ?? st.session.method}</Badge>}
        </div>
        <div className="live-bar-actions">
          {running ? (
            <>
              <Button variant="secondary" icon="refresh" onClick={() => act(adviserApi.reassess)} disabled={busy}
                      data-testid="live-reassess" title="Run the current assessment now (never rewrites history)">Reassess now</Button>
              <Button variant="danger" icon="stop" onClick={() => act(adviserApi.stop)} disabled={busy || !!st?.session?.stop_requested}
                      data-testid="live-stop-button">{st?.session?.stop_requested ? "Stopping…" : "Stop live adviser"}</Button>
            </>
          ) : (
            <>
              <label className="small-text live-method" data-testid="live-method">
                <span>Method</span>
                <select className="control" value={method}
                        onChange={(e) => setMethod(e.target.value as AdviserMethod)}
                        data-testid="live-method-select" disabled={busy}>
                  {METHODS.map((m) => (
                    <option key={m} value={m}>{METHOD_TEXT[m]} ({METHOD_STATUS[m].text.toLowerCase()})</option>))}
                </select>
              </label>
              <Button icon="play" onClick={() => act(() => adviserApi.start(method))} disabled={busy} data-testid="live-start"
                      className="btn-lg">Start live adviser</Button>
            </>
          )}
          <Button variant="secondary" icon={copied === "copied" ? "check" : "copy"} onClick={copy} data-testid="copy-analysis">
            {copied === "copied" ? "Copied" : copied === "copying" ? "Copying…" : copied === "error" ? "Copy failed"
              : "Copy analysis for chat"}</Button>
        </div>
      </div>
      {error && <Notice tone="neg" title="Could not change the live adviser">{error}</Notice>}
      {newAlerts.length > 0 && (
        <Notice tone="info" icon="pulse" testid="live-alerts"
                title={newAlerts.length > 1 ? `${newAlerts.length} avvisi registrati non ancora letti`
                  : "1 avviso registrato non ancora letto"}>
          <p className="small-text alerts-pointer" data-testid="alerts-current-pointer">Sono eventi passati, mostrati con l'ora in cui
            sono stati registrati. {CURRENT_IS_IN_PANEL}</p>
          {newAlerts.slice(0, 3).map((a) => <HistoricalAlert key={a.alert_key} a={a} />)}
        </Notice>
      )}
      {v?.stale_session && (
        <Notice tone="warn" title={state === "STOPPED" ? "Stopped" : "Not current advice"} testid="live-not-current">
          {state === "STOPPED" ? "The last view below is from the stopped session and is not current advice."
            : `The session is ${humanize(state).toLowerCase()}: the view below is not current and no entry is presented as usable now.`}
        </Notice>
      )}
      <div className="live-grid">
        <aside className="live-side">
          <ProposalPanel v={v} onHistory={openHistory} />
        </aside>
        <div className="live-main">
          {history && (
            <LiveCallHistory key={`${history.runId}|${history.callId}`} sel={history} view={v}
                             sessionId={st?.session?.session_id ?? null} onClose={() => setHistory(null)} />
          )}
          <Card title="BTC price · last complete minutes" icon="market" testid="live-price"
                eyebrow={v?.clock ? `as of ${fmtTime(v.clock)} · ${v.origin === "LIVE" ? "live receipts" : "reconstructed history"}` : "no data yet"}
                actions={<Badge tone={v?.origin === "LIVE" ? "pos" : "pending"}>{v?.origin === "LIVE" ? "LIVE" : "NOT LIVE"}</Badge>}>
            <PriceChart v={v} />
          </Card>
          <div className="lens-grid" data-testid="live-lenses">
            {(v?.lenses ?? []).map((l) => <LensCard key={l.lens} l={l} />)}
            {!v && <p className="muted small-text">Lens results appear once the adviser has assessed the market. Several lenses
              are not majority votes: each has a stated role.</p>}
          </div>
          <Card title="What changed" icon="pulse" testid="live-changes">
            {st ? <Timeline st={st} onHistory={openHistory} /> : null}
          </Card>
        </div>
      </div>
      <details className="more" data-testid="live-technical">
        <summary><Icon name="chevron" size={14} className="summary-chevron" /> Technical details
          <span className="summary-hint">identity, readiness, armed scenarios, catch-up and connection</span></summary>
        <div className="more-body">
          {st?.session && (
            <div className="kv-grid">
              <span>Session</span><Mono>{st.session.session_id}</Mono>
              <span>Continuity epoch</span><Mono>{v?.run_id ?? "—"}</Mono>
              <span>Heartbeat age</span><Mono>{st.session.heartbeat_age_seconds?.toFixed(1) ?? "—"} s</Mono>
              <span>Catch-up</span><Mono>{JSON.stringify(st.session.progress)}</Mono>
              <span>Connection</span><Mono>{JSON.stringify(st.session.connection)}</Mono>
              <span>Identity</span><Mono>{String((st.session.identity as Record<string, string> | null)?.identity_sha256 ?? "—").slice(0, 16)}</Mono>
            </div>
          )}
          <ul className="check-list">
            {(v?.readiness ?? []).map((r) => <li key={r.name}><span className="mono">{r.name}</span> <Badge tone={r.status === "READY" ? "pos" : "warn"}>{r.status}</Badge> <span className="muted">{r.latest_ref ?? ""}</span></li>)}
          </ul>
          {(v?.attempts ?? []).length > 0 && (
            <ul className="check-list" data-testid="live-attempts">
              {v!.attempts.map((a) => <li key={a.attempt_id}><span className="mono">{a.attempt_id.slice(0, 28)}</span> {a.family} {a.direction} {humanize(a.status)} trigger {a.trigger_level ?? "—"} invalidation {a.invalidation_level ?? "—"}</li>)}
            </ul>
          )}
          <p className="muted small-text">{st?.notice}</p>
        </div>
      </details>
    </section>
  );
}
