import { Capability, dataApi, DatasetSummary, recorderApi, RecorderSession } from "../api";
import { fmtInt, fmtNs, fmtSecs, fmtTime } from "../lib/format";
import { navigate } from "../lib/route";
import { usePoll } from "../lib/usePoll";
import { CAPABILITY_ORDER, capabilityLabel, capabilityTone, systemVerdict, useHealth } from "../shell/health";
import { Icon, IconName } from "../ui/Icon";
import { Badge, Button, Card, cx, Metric, Mono, PageHeader, Skeleton, statusTone, Tone } from "../ui/primitives";
import { LiveCockpit } from "./LiveCockpit";

// Market (Home): the live adviser cockpit first (Start/Stop, direction, call, lenses, chart, changes), then what else
// can be done and the real system/data readiness. Cockpit values come only from the committed live session view; the
// readiness panels read /api/health, /api/datasets and /api/recorder/sessions. Synthetic demo output never appears here.

interface Stage {
  label: string;
  state: string;
  tone: Tone;
  detail: string;
  dev?: string;
}

function pipeline(datasets: number | null, recorder: Capability | undefined, replay: Capability | undefined): Stage[] {
  const cap = (c: Capability | undefined, up: string): [string, Tone] =>
    !c ? ["Checking", "neutral"] : c.status === "available" ? [up, "pos"]
      : c.status === "stalled" ? ["Jobs waiting · no worker", "warn"] : ["Available · worker offline", "warn"];
  const [recState, recTone] = cap(recorder, "Available");
  const [repState, repTone] = cap(replay, "Available");
  return [
    {
      label: "Historical market evidence",
      state: datasets === null ? "Checking" : datasets > 0 ? "Available" : "Ready · no datasets yet",
      tone: datasets === null ? "neutral" : datasets > 0 ? "pos" : "info",
      detail: "Immutable, hashed OKX public datasets with quality reports.",
    },
    {
      label: "Live public recording",
      state: recState,
      tone: recTone,
      detail: "Prospective capture with measured client-side receipt times.",
    },
    {
      label: "Causal feed & observable state",
      state: "Connected",
      tone: "pos",
      detail: "Evidence reaches the app only through causal feed deliveries and the pure state reducer.",
    },
    {
      label: "Real-market observation replay",
      state: repState,
      tone: repTone,
      detail: "Durable replay of datasets (modeled availability) and recordings (recorded receipt times) in Replay Lab.",
    },
    {
      label: "Integrated adviser",
      state: "Implemented · MP-001 v0.2",
      tone: "pos",
      detail: "Market view, scenarios and persistent LONG / SHORT calls or no actionable trade (live and historical).",
      dev: "Economic usefulness is not established: evaluated by Owner backtests",
    },
  ];
}

function Pipeline({ stages }: { stages: Stage[] }) {
  return (
    <ol className="pipeline" data-testid="evidence-pipeline">
      {stages.map((s, i) => (
        <li key={s.label} className={cx("pipeline-step", `tone-${s.tone}`)}>
          <span className="pipeline-node" aria-hidden>{s.tone === "pos" ? <Icon name="check" size={12} /> : i + 1}</span>
          <div className="pipeline-body">
            <div className="pipeline-row">
              <span className="pipeline-label">{s.label}</span>
              <Badge tone={s.tone}>{s.state}</Badge>
            </div>
            <div className="pipeline-detail">{s.detail}</div>
            {s.dev && <div className="pipeline-dev mono">{s.dev}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}

function LatestDataset({ d, count }: { d: DatasetSummary | undefined; count: number }) {
  if (!d) {
    return (
      <p className="muted small-text">
        No historical datasets yet. Create one with <code>algotrader data fetch-okx</code>.
      </p>
    );
  }
  return (
    <div className="stack-sm">
      <div className="row-between">
        <Mono className="ellipsis" title={d.dataset_id}>{d.dataset_id}</Mono>
        <Badge tone={statusTone(d.quality_status)} dot>{d.quality_status.toUpperCase()}</Badge>
      </div>
      <div className="kv-grid">
        <span>Instrument</span><Mono>{d.inst_id}</Mono>
        <span>Window</span><Mono>{fmtTime(d.requested.start)} → {fmtTime(d.requested.end)}</Mono>
        <span>Families</span><Mono>{d.families.length}</Mono>
        <span>Total datasets</span><Mono>{fmtInt(count)}</Mono>
      </div>
    </div>
  );
}

function LatestRecording({ s }: { s: RecorderSession | undefined }) {
  if (!s) return <p className="muted small-text">No recording sessions yet.</p>;
  const active = s.status === "running" || s.status === "queued";
  return (
    <div className="stack-sm">
      <div className="row-between">
        <Mono className="ellipsis" title={s.session_id}>{s.session_id}</Mono>
        <Badge tone={statusTone(s.status)} dot>{s.status.toUpperCase()}</Badge>
      </div>
      <div className="kv-grid">
        <span>Messages</span><Mono>{fmtInt(s.stats?.records ?? 0)}</Mono>
        <span>Last receipt</span><Mono>{fmtNs(s.stats?.last_recv_utc_ns)}</Mono>
        <span>{active ? "Elapsed" : "Duration"}</span><Mono>{fmtSecs(s.elapsed_seconds)}</Mono>
      </div>
    </div>
  );
}

const TASKS: { section: "backtest" | "replay" | "data" | "recorder"; icon: IconName; title: string; text: string; cta: string; primary?: boolean }[] = [
  { section: "backtest", icon: "gauge", primary: true, title: "Evaluate the adviser on history",
    text: "Prepare a pack of BTC data, run an adviser evaluation (or a data and engine check) and copy a plain report into chat.",
    cta: "Open Historical Workbench" },
  { section: "replay", icon: "replay", title: "Inspect a replay event by event",
    text: "Pause, step and slow down a replay to see what it had admitted at each step (modeled times for datasets, measured receipt times for recordings).", cta: "Open Replay Lab" },
  { section: "data", icon: "data", title: "See the stored data and its quality",
    text: "Datasets on this computer: coverage, gaps and verification.", cta: "Open Data" },
  { section: "recorder", icon: "recorder", title: "Record live public market data",
    text: "Collect live public OKX data with measured receipt times while the app is running.", cta: "Open Recorder" },
];

/** Task-first entry point: what a person can actually do today, before the reserved adviser cockpit. */
function StartHere() {
  return (
    <section className="start-here reveal" data-testid="start-here" aria-labelledby="start-here-title" style={{ ["--i" as string]: 0 }}>
      <div className="start-here-head">
        <h2 className="start-here-title" id="start-here-title">More you can do</h2>
        <p className="muted small-text">The live adviser cockpit is above. These tools work alongside it:</p>
      </div>
      <ul className="task-grid">
        {TASKS.map((t) => (
          <li key={t.section}>
            <button type="button" className={cx("task-card", t.primary && "is-primary")} onClick={() => navigate(t.section)}
                    data-testid={`task-${t.section}`}>
              <span className="task-icon"><Icon name={t.icon} size={18} /></span>
              <span className="task-title">{t.title}</span>
              <span className="task-text">{t.text}</span>
              <span className="task-cta">{t.cta} <Icon name="chevron" size={13} /></span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Overview() {
  const healthState = useHealth();
  const verdict = systemVerdict(healthState);
  const h = healthState.health;
  const datasets = usePoll(dataApi.list, 15000);
  const recordings = usePoll(recorderApi.list, 5000);
  const dsList = datasets.data?.datasets ?? null;
  const sessions = recordings.data?.sessions ?? null;
  const latestSession = sessions?.[0];
  const caps = h?.capabilities;
  const lastReceipt = sessions?.find((s) => s.stats?.last_recv_utc_ns)?.stats?.last_recv_utc_ns ?? null;

  return (
    <div className="page page-overview" data-testid="page-overview">
      <PageHeader
        eyebrow="BTC perpetual · market desk"
        title="Market"
        lede="What BTC is doing, which scenarios are plausible and whether a professional trade exists — LONG, SHORT or NO_TRADE, with trigger, invalidation and targets. Capital, size, leverage and execution stay with you."
      />

      <LiveCockpit />

      <StartHere />

      {/* Market identity */}
      <section className="market-strip reveal" style={{ ["--i" as string]: 0 }}>
        <div className="market-id">
          <div className="market-sym">
            <span className="market-sym-main">BTC</span>
            <span className="market-sym-sep">/</span>
            <span className="market-sym-quote">USDT perpetual</span>
          </div>
          <div className="market-sub">
            <Mono>BTC-USDT-SWAP</Mono> · OKX public, read-only reference · analysis horizon minutes to hours
          </div>
        </div>
        <div className="market-facts">
          <Metric label="Last public message recorded" value={lastReceipt ? fmtNs(lastReceipt) : "—"}
                  hint="From the Recorder (evidence only)" testid="overview-last-receipt" />
          <Metric label="System" value={<Badge tone={verdict.tone} dot>{verdict.label}</Badge>} mono={false}
                  hint={verdict.detail} testid="overview-system" />
        </div>
      </section>

      <div className="overview-grid readiness-only">
        <aside className="readiness" data-testid="readiness">
          <div className="readiness-head">
            <span className="eyebrow">Real today</span>
            <h2 className="section-title">System & data readiness</h2>
          </div>

          <Card title="Runtime" icon="cpu" testid="readiness-runtime"
                actions={<Badge tone={h ? "pos" : verdict.tone} dot>{h ? "API up" : verdict.label}</Badge>}>
            <ul className="cap-list" data-testid="overview-capabilities">
              {CAPABILITY_ORDER.map((k) => {
                const c = caps?.[k];
                const n = k === "synthetic_replay" ? h?.workers.alive : k === "recorder" ? h?.recorder_workers?.alive
                  : k === "corpus" ? h?.corpus_workers?.alive : k === "live_adviser" ? h?.adviser_workers?.alive
                  : h?.observation_workers?.alive;
                const testid = { synthetic_replay: "overview-run-workers", recorder: "overview-recorder-workers",
                                 market_replay: "overview-observation-workers", corpus: "overview-corpus-workers",
                                 live_adviser: "overview-adviser-workers" }[k];
                return (
                  <li key={k}>
                    <span className="cap-name">{c?.label ?? k}</span>
                    <span className="cap-count"><span className="mono" data-testid={testid}>{n ?? "—"}</span> worker{n === 1 ? "" : "s"}</span>
                    <Badge tone={capabilityTone(c)} dot>{capabilityLabel(c)}</Badge>
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card title="Evidence pipeline" icon="layers">
            <Pipeline stages={pipeline(dsList ? dsList.length : null, caps?.recorder, caps?.market_replay)} />
          </Card>

          <Card title="Latest historical dataset" icon="data" testid="readiness-dataset"
                actions={<Button variant="ghost" onClick={() => navigate("data")}>Open Data</Button>}>
            {datasets.loading && !dsList ? <Skeleton lines={3} /> :
              datasets.error && !dsList ? <p className="text-neg small-text">Datasets unavailable: {datasets.error}</p> :
              <LatestDataset d={dsList?.[0]} count={dsList?.length ?? 0} />}
          </Card>

          <Card title="Latest recording session" icon="recorder" testid="readiness-recorder"
                actions={<Button variant="ghost" onClick={() => navigate("recorder")}>Open Recorder</Button>}>
            {recordings.loading && !sessions ? <Skeleton lines={3} /> :
              recordings.error && !sessions ? <p className="text-neg small-text">Recorder unavailable: {recordings.error}</p> :
              <LatestRecording s={latestSession} />}
          </Card>

          <Card title="Replay Lab" icon="replay" eyebrow="Real observation replay · synthetic demo"
                actions={<Button variant="ghost" onClick={() => navigate("replay")}>Open lab</Button>}>
            <p className="muted small-text">
              Market Replay steps through verified real evidence and shows the observable market state at each instant —
              evidence only, never interpretation. The separate synthetic demo exercises the shell and never feeds this
              cockpit.
            </p>
          </Card>
        </aside>
      </div>
    </div>
  );
}
