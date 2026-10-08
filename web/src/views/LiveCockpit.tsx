import { useMemo, useState } from "react";
import {
  AdviserMethod, adviserApi, CallView, ENTRY_TEXT, EXPECTED_TEXT, Lens, LiveStatus, LiveView, METHOD_STATUS, METHOD_TEXT,
  METHODS, reasonText, ROW_TEXT, THESIS_TEXT,
} from "../adviser";
import { fmtNum, fmtTime, humanize } from "../lib/format";
import { usePoll } from "../lib/usePoll";
import { Icon } from "../ui/Icon";
import { Badge, Button, Card, cx, Mono, Notice, Tone } from "../ui/primitives";
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

function dirTone(d: string | undefined): Tone {
  return d === "UP" ? "pos" : d === "DOWN" ? "neg" : d === "UNAVAILABLE" ? "pending" : "neutral";
}

function Arrow({ d }: { d: string | undefined }) {
  if (d === "UP") return <span className="dir-arrow up" aria-hidden>▲</span>;
  if (d === "DOWN") return <span className="dir-arrow down" aria-hidden>▼</span>;
  return <span className="dir-arrow flat" aria-hidden>◆</span>;
}

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
    const adm = call?.admissible_bounds ? { y1: y(Number(call.admissible_bounds[1])), y2: y(Number(call.admissible_bounds[0])) } : null;
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

function DirectionPanel({ v }: { v: LiveView | null }) {
  const mv = v?.market_view;
  const d = mv?.expected_direction ?? "UNAVAILABLE";
  return (
    <section className={cx("dir-panel", `tone-${dirTone(d)}`)} data-testid="live-direction">
      <div className="eyebrow">Expected direction {mv?.conditional ? "· conditional" : ""}</div>
      <div className="dir-main"><Arrow d={d} /><span data-testid="live-expected">{EXPECTED_TEXT[d] ?? d}</span></div>
      <div className="dir-sub">{mv ? ROW_TEXT[mv.table_row] ?? humanize(mv.table_row) : "No view yet"}
        {mv?.horizon_minutes && <> · horizon {mv.horizon_minutes[0]}–{mv.horizon_minutes[1]} min</>}</div>
      <div className="dir-facts">
        <span>Observed 1h context <b>{mv?.observed_context ?? "—"}</b></span>
        <span>Phase <b>{mv ? humanize(mv.phase) : "—"}</b></span>
      </div>
      {(mv?.reasons.length ?? 0) > 0 && <ul className="dir-reasons">{mv!.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
      {(mv?.counterevidence.length ?? 0) > 0 && (
        <ul className="dir-counter">{mv!.counterevidence.map((r) => <li key={r}>Against: {r}</li>)}</ul>)}
      <div className="muted small-text">Qualitative, not a probability. Observed context is a measured path label, not a
        forecast.</div>
    </section>
  );
}

function CallPanel({ v }: { v: LiveView | null }) {
  const c: CallView | null = v?.call ?? null;
  const mv = v?.market_view;
  if (!v) {
    return (
      <section className="call-panel is-none" data-testid="live-call">
        <div className="call-none-title">No current assessment</div>
        <div className="call-none-why">Start the live adviser to assess the market now. While it is stopped nothing is
          monitored.</div>
      </section>
    );
  }
  if (!c) {
    const top = mv?.blockers?.[0] ?? (mv ? ROW_TEXT[mv.table_row] : null);
    return (
      <section className="call-panel is-none" data-testid="live-call">
        <div className="call-none-title" data-testid="live-no-trade">No actionable trade now</div>
        <div className="call-none-why">{top ? `Top reason: ${reasonText(top)}` : "Waiting for the first assessment"}</div>
        {mv?.principal && (
          <div className="call-scenario" data-testid="live-scenario">
            <Badge tone={mv.principal.direction === "LONG" ? "pos" : "neg"}>{mv.principal.direction} {mv.principal.family}{" "}
              {(mv.principal.status ?? "ARMED").toLowerCase()}</Badge>
            <span className="small-text">{mv.principal.antecedent}</span>
          </div>
        )}
        {(v?.scenarios ?? []).filter((s) => s.observing).map((s) => (
          <div className="call-waiting" key={s.scenario_id} data-testid="live-observing">
            <Badge tone="neutral">{s.direction} {s.family} — scenario under observation</Badge>
            <p className="small-text">{s.observing!.text} The previous reaction anchor
              {s.observing!.lost_anchor?.V ? ` (stop ${s.observing!.lost_anchor.V})` : ""} was touched before confirmation.
              This is not a call and not an entry: nothing to do now.</p>
            <dl className="call-geo">
              <dt>Narrative destination</dt><dd className="mono">{s.destination ?? "—"}</dd>
              <dt>Observation ends</dt><dd className="mono">{fmtTime(s.observing!.original_expiry)} (original deadline)</dd>
            </dl>
          </div>
        ))}
        {(v?.scenarios ?? []).filter((s) => s.waiting).map((s) => (
          <div className="call-waiting" key={s.scenario_id} data-testid="live-waiting">
            <Badge tone="info">{s.direction} {s.family} confirmed — {s.waiting!.phase === "WAIT_RESPONSE"
              ? "waiting for a local recovery" : "waiting for a usable price"}</Badge>
            <p className="small-text">{s.waiting!.text} This is not a call: do not treat it as “enter now”.</p>
            {s.waiting!.response && (
              <dl className="kv-grid small-text" data-testid="live-waiting-response">
                <dt>Return reference</dt><dd className="mono">H0 {s.waiting!.response.H0} · L0 {s.waiting!.response.L0} · published {fmtTime(s.waiting!.response.published_at)}</dd>
                <dt>Call possible only if</dt><dd>{s.waiting!.response.recovery_rule}</dd>
                <dt>Ends this attempt</dt><dd>{s.waiting!.response.contradiction_rule}</dd>
              </dl>
            )}
            <dl className="call-geo">
              <dt>Usable return corridor</dt><dd className="mono">{s.waiting!.corridor ? `${s.waiting!.corridor[0]} – ${s.waiting!.corridor[1]}` : "none left"}</dd>
              <dt>Target now</dt><dd className="mono">{s.waiting!.target_now} <span className="muted">(at confirmation {s.waiting!.target_at_confirmation})</span></dd>
              <dt>Stop guidance if issued</dt><dd className="mono">{s.waiting!.stop_V}</dd>
              <dt>Waits until</dt><dd className="mono">{fmtTime(s.waiting!.wait_until)} · hard deadline {fmtTime(s.waiting!.hard_deadline)}</dd>
              <dt>Blockers now</dt><dd>{s.waiting!.blockers.length ? s.waiting!.blockers.map(reasonText).join(", ") : "none (waiting for a fresh minute)"}</dd>
            </dl>
          </div>
        ))}
      </section>
    );
  }
  const entryTone: Tone = c.entry_status === "AVAILABLE" ? "pos" : c.entry_status === "UNVERIFIED" ? "warn" : "neutral";
  return (
    <section className={cx("call-panel", c.direction === "LONG" ? "is-long" : "is-short")} data-testid="live-call">
      <div className="call-head">
        <span className="call-dir" data-testid="live-call-direction">{c.direction}</span>
        <span className="call-family">{c.family} · {c.family_text}</span>
        {c.presentation === "NOT_CURRENT"
          ? <Badge tone="warn" testid="live-call-not-current">Not current — entry not verifiable</Badge>
          : <Badge tone={c.origin === "LIVE" ? "pos" : "pending"}>{c.origin === "LIVE" ? "Live call" : "Reconstructed — not actionable"}</Badge>}
      </div>
      <div className={cx("call-entry", `tone-${entryTone}`)} data-testid="live-entry">
        <b>{ENTRY_TEXT[c.entry_status]}</b>
        {c.entry_reasons.length > 0 && <span className="small-text"> ({c.entry_reasons.map(reasonText).join(", ")})</span>}
      </div>
      <dl className="call-geo">
        <dt>Entry now (admissible)</dt>
        <dd className="mono" data-testid="live-admissible">{c.admissible_bounds ? `${c.admissible_bounds[0]} – ${c.admissible_bounds[1]}` : "not verifiable"}</dd>
        <dt>Structural area</dt><dd className="mono">{c.structural_area[0]} – {c.structural_area[1]}</dd>
        <dt>Target</dt><dd className="mono" data-testid="live-target">{c.target} <span className="muted">({humanize(c.target_type)})</span></dd>
        <dt>Stop guidance</dt><dd className="mono" data-testid="live-stop-guidance">{c.stop}</dd>
        <dt>Expected duration</dt><dd>{c.duration_window ? `${c.duration_window[0]}–${c.duration_window[1]} min` : "too late for a new entry"}</dd>
        <dt>Time left</dt><dd className="mono">{c.remaining_minutes} min · hard deadline {fmtTime(c.hard_deadline)}</dd>
        <dt>Thesis</dt><dd><Badge tone={c.thesis_status === "ONGOING" ? "info" : "neutral"}>{THESIS_TEXT[c.thesis_status] ?? c.thesis_status}</Badge></dd>
      </dl>
      <p className="call-guidance" data-testid="live-guidance">{c.guidance}</p>
      <p className="muted small-text">Stop is guidance, not an order or guaranteed fill. Size, leverage and orders are yours.</p>
    </section>
  );
}

function Timeline({ st }: { st: LiveStatus }) {
  const v = st.view;
  const items = [
    ...st.alerts.map((a) => ({ at: a.created_at, kind: humanize(a.change_type), text: a.summary, alert: a })),
    ...(v?.recent_calls ?? []).map((c) => ({ at: c.terminal_at, kind: `${c.direction} ${c.family} ${THESIS_TEXT[c.terminal] ?? c.terminal}`,
                                             text: reasonText(c.reason), alert: null })),
    ...(v?.notes ?? []).slice(-6).map((n) => ({ at: n.at, kind: humanize(n.event), text: "", alert: null })),
  ].sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, 14);
  if (!items.length) return <p className="muted small-text">No material change yet.</p>;
  return (
    <ol className="change-timeline" data-testid="live-timeline">
      {items.map((x, i) => (
        <li key={i} className={x.alert && !x.alert.acknowledged ? "is-new" : undefined}>
          <span className="mono small-text">{fmtTime(x.at).slice(11, 19)}</span>
          <span className="tl-kind">{x.kind}</span>
          <span className="tl-text">{x.text}</span>
          {x.alert && !x.alert.acknowledged && (
            <button type="button" className="link-btn" onClick={() => void adviserApi.ack(x.alert!.alert_key)}>dismiss</button>
          )}
        </li>
      ))}
    </ol>
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
        <Notice tone="info" icon="pulse" title={`${newAlerts.length} new change${newAlerts.length > 1 ? "s" : ""}`} testid="live-alerts">
          {newAlerts.slice(0, 3).map((a) => <div key={a.alert_key}>{humanize(a.change_type)} — {a.summary}</div>)}
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
          <DirectionPanel v={v} />
          <CallPanel v={v} />
        </aside>
        <div className="live-main">
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
            {st ? <Timeline st={st} /> : null}
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
