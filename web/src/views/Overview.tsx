import { Capability, dataApi, DatasetSummary, recorderApi, RecorderSession } from "../api";
import { fmtInt, fmtNs, fmtSecs, fmtTime } from "../lib/format";
import { navigate } from "../lib/route";
import { usePoll } from "../lib/usePoll";
import { CAPABILITY_ORDER, capabilityLabel, capabilityTone, systemVerdict, useHealth } from "../shell/health";
import { Icon, IconName } from "../ui/Icon";
import { Badge, Button, Card, cx, Metric, Mono, PageHeader, Skeleton, statusTone, Tone } from "../ui/primitives";

// The Market overview is the future professional trader cockpit. The trader engine does not exist yet, so
// every trader-intelligence area renders an explicit pending state. Nothing here reads replay output (real
// or synthetic): only /api/health, /api/datasets and /api/recorder/sessions (real operational state).

const PENDING_EYEBROW = "Trader engine · pending";

function PendingBadge() {
  return <Badge tone="pending" icon="clock">Not yet implemented</Badge>;
}

function Slot({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="slot">
      <div className="slot-label">{label}</div>
      <div className="slot-value">Awaiting engine</div>
      {hint && <div className="slot-hint">{hint}</div>}
    </div>
  );
}

function PendingCard({ id, title, icon, lede, children, className }: {
  id: string; title: string; icon: IconName; lede: string; children?: React.ReactNode; className?: string;
}) {
  return (
    <Card material="pending" testid={`pending-${id}`} state="pending" className={cx("pending-card", className)}>
      <div className="pending-top">
        <span className="eyebrow">{PENDING_EYEBROW}</span>
        <PendingBadge />
      </div>
      <h3 className="card-title"><Icon name={icon} size={16} />{title}</h3>
      <p className="pending-lede">{lede}</p>
      {children}
    </Card>
  );
}

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
      label: "Professional trader engine",
      state: "Not implemented",
      tone: "pending",
      detail: "Market view, scenarios and LONG / SHORT / NO_TRADE decisions.",
      dev: "After the strategic trader-design checkpoint",
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

      {/* Market identity + intelligence status */}
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
          <Metric label="Live price in cockpit" value={<span className="muted-value">Not connected</span>} mono={false}
                  hint="Arrives with real-market integration" />
          <Metric label="Last public message recorded" value={lastReceipt ? fmtNs(lastReceipt) : "—"}
                  hint="From the Recorder (evidence only)" testid="overview-last-receipt" />
          <Metric label="System" value={<Badge tone={verdict.tone} dot>{verdict.label}</Badge>} mono={false}
                  hint={verdict.detail} testid="overview-system" />
        </div>
      </section>

      <section className="engine-banner reveal" data-testid="trader-engine-status" style={{ ["--i" as string]: 1 }}>
        <div className="engine-banner-icon"><Icon name="compass" size={22} /></div>
        <div className="engine-banner-body">
          <div className="engine-banner-title">
            Professional trader engine <Badge tone="pending" icon="clock">Not yet implemented</Badge>
          </div>
          <p>
            The cockpit below is the reserved layout for the real engine. Every trader area stays empty until that engine
            publishes a view. Nothing on this page is derived from the synthetic demo or from observable-state
            heuristics, and no signal, price level or confidence is shown before it exists.
          </p>
        </div>
      </section>

      <div className="overview-grid">
        <div className="cockpit">
          <PendingCard id="market-view" title="Market view" icon="eye" className="span-2"
                       lede="The current professional interpretation of BTC: state per horizon, directional or structural bias where justified, relevant levels, uncertainty and expected response.">
            <div className="slot-row">
              <Slot label="Bias by horizon" />
              <Slot label="Relevant levels" />
              <Slot label="Uncertainty" hint="Qualitative first — not a probability" />
              <Slot label="Expected response" />
            </div>
          </PendingCard>

          <PendingCard id="scenarios" title="Scenarios & prediction" icon="branch"
                       lede="Competing scenarios instead of one forecast, each with expected behaviour, horizon, expiry and what would invalidate it.">
            <div className="scenario-slots">
              <div className="scenario-slot"><span className="scenario-rank">Primary</span><span className="slot-value">Awaiting engine</span></div>
              <div className="scenario-slot"><span className="scenario-rank">Alternative</span><span className="slot-value">Awaiting engine</span></div>
            </div>
          </PendingCard>

          <PendingCard id="decision" title="Trade decision" icon="scale"
                       lede="Whether a professional opportunity exists right now. The engine will publish one of LONG, SHORT or NO_TRADE — abstaining is a legitimate decision.">
            <div className="decision-slot" data-testid="decision-slot">
              <span className="decision-slot-value">No decision published</span>
              <span className="decision-slot-hint">Decision support only — the product never sizes, leverages or places orders.</span>
            </div>
          </PendingCard>

          <PendingCard id="geometry" title="Trade geometry" icon="target"
                       lede="When a trade exists: what must happen before entry, where the thesis is wrong, and where it should go.">
            <div className="slot-grid">
              <Slot label="Trigger / entry" />
              <Slot label="Invalidation" />
              <Slot label="Target(s)" />
              <Slot label="Horizon / expiry" />
            </div>
          </PendingCard>

          <PendingCard id="changes" title="What changed" icon="pulse"
                       lede="A timeline of view and recommendation updates as the market evolves — including thesis status (hold, reduce, exit, invalidated) once a recommendation is active.">
            <ol className="timeline-slot" aria-label="Update timeline (empty)">
              <li><span className="slot-value">Awaiting engine</span></li>
            </ol>
          </PendingCard>

          <PendingCard id="evidence" title="Evidence & what would change the view" icon="layers" className="span-2"
                       lede="Supporting and opposing evidence with provenance, conflicts between horizons, and the observable conditions that would change the system's mind.">
            <div className="slot-grid three">
              <Slot label="Supporting" />
              <Slot label="Opposing" />
              <Slot label="Would change the view" />
            </div>
          </PendingCard>
        </div>

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
                  : k === "corpus" ? h?.corpus_workers?.alive : h?.observation_workers?.alive;
                const testid = { synthetic_replay: "overview-run-workers", recorder: "overview-recorder-workers",
                                 market_replay: "overview-observation-workers", corpus: "overview-corpus-workers" }[k];
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
