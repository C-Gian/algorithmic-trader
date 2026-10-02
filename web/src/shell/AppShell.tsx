import { ReactNode, useEffect, useState } from "react";
import { navigate, Section } from "../lib/route";
import { Icon, IconName } from "../ui/Icon";
import { cx } from "../ui/primitives";
import { CAPABILITY_ORDER, capabilityLabel, capabilityTone, systemVerdict, useHealth } from "./health";

const CAP_SHORT = { market_replay: "Market replay", corpus: "Corpus prep", recorder: "Recorder", synthetic_replay: "Synthetic demo" } as const;

interface NavItem {
  id: Section;
  label: string;
  icon: IconName;
  hint: string;
  chip?: { text: string; tone: string };
}

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Desk",
    items: [
      { id: "market", label: "Market", icon: "market", hint: "BTC cockpit and system readiness" },
      { id: "backtest", label: "Historical Workbench", icon: "gauge", hint: "Corpus, market replay runs (data and engine check) and copyable reports" },
    ],
  },
  {
    group: "Workbench",
    items: [
      { id: "replay", label: "Replay Lab", icon: "replay", hint: "Real-market observation replay and synthetic demo" },
      { id: "data", label: "Data", icon: "data", hint: "Historical evidence datasets" },
      { id: "recorder", label: "Recorder", icon: "recorder", hint: "Public live evidence collection" },
    ],
  },
];

const TITLES: Record<Section, string> = {
  market: "Market",
  backtest: "Historical Workbench",
  replay: "Replay Lab",
  data: "Data",
  recorder: "Recorder",
};

function BrandMark() {
  // Monogram: a single completed candle inside a bracket — "one decision, bounded".
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden>
      <rect x="1" y="1" width="30" height="30" rx="8" className="brand-mark-bg" />
      <path d="M9 9v14M23 9v14" className="brand-mark-rail" />
      <path d="M16 7v4M16 21v4" className="brand-mark-wick" />
      <rect x="13" y="11" width="6" height="10" rx="1.2" className="brand-mark-body" />
    </svg>
  );
}

function UtcClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return (
    <span className="utc-clock mono" title="Your system clock (UTC)">
      {now.toISOString().slice(11, 19)} <span className="muted">UTC</span>
    </span>
  );
}

function GlobalHealth() {
  const state = useHealth();
  const v = systemVerdict(state);
  const h = state.health;
  return (
    <div className="side-health" data-testid="global-health" data-tone={v.tone}>
      <div className="side-health-head">
        <span className={cx("pulse-dot", `tone-${v.tone}`)} aria-hidden />
        <span className="side-health-label">System {v.label}</span>
      </div>
      <div className="side-health-detail">{v.detail}</div>
      <dl className="side-health-rows">
        {CAPABILITY_ORDER.map((k) => {
          const c = h?.capabilities?.[k];
          return (
            <div key={k} data-testid={`capability-${k}`} title={c ? `${c.label}: ${capabilityLabel(c)}` : undefined}>
              <dt>{CAP_SHORT[k]}</dt>
              <dd className={cx("cap-state", `tone-${capabilityTone(c)}`)}>
                <span className="cap-dot" aria-hidden />{c ? (c.status === "available" ? "up" : c.status === "stalled" ? "stalled" : "off") : "—"}
              </dd>
            </div>
          );
        })}
        <div><dt>Build</dt><dd className="mono">{h?.version ?? "—"}</dd></div>
      </dl>
    </div>
  );
}

function Legend() {
  return (
    <div className="legend" aria-label="Surface legend">
      <div className="legend-title">Reading this desk</div>
      <div className="legend-row"><span className="swatch m-real" aria-hidden /> Real — operational or evidence</div>
      <div className="legend-row"><span className="swatch m-synthetic" aria-hidden /> Synthetic — demo only</div>
      <div className="legend-row"><span className="swatch m-pending" aria-hidden /> Pending — not built yet</div>
    </div>
  );
}

export function AppShell({ section, children }: { section: Section; children: ReactNode }) {
  const v = systemVerdict(useHealth());
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#market" onClick={(e) => { e.preventDefault(); navigate("market"); }}>
          <BrandMark />
          <span className="brand-text">
            <span className="brand-name">Algorithmic Trader</span>
            <span className="brand-sub">BTC decision desk · beta</span>
          </span>
        </a>
        <nav className="nav" aria-label="Primary">
          {NAV.map((g) => (
            <div className="nav-group" key={g.group}>
              <div className="nav-group-label">{g.group}</div>
              {g.items.map((it) => (
                <button
                  key={it.id}
                  type="button"
                  className={cx("nav-item", section === it.id && "is-active")}
                  aria-current={section === it.id ? "page" : undefined}
                  onClick={() => navigate(it.id)}
                  data-testid={`nav-${it.id}`}
                  title={it.hint}
                >
                  <Icon name={it.icon} size={18} />
                  <span className="nav-label">{it.label}</span>
                  {it.chip && <span className={cx("nav-chip", `tone-${it.chip.tone}`)}>{it.chip.text}</span>}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <GlobalHealth />
          <Legend />
        </div>
      </aside>

      <div className="workspace">
        <div className="topbar">
          <div className="crumbs">
            <span className="muted">Algorithmic Trader</span>
            <Icon name="chevron" size={14} />
            <span className="crumb-current">{TITLES[section]}</span>
          </div>
          <div className="topbar-right">
            <span className="instrument-chip" title="Primary analysed instrument; OKX is a public, read-only reference source">
              <span className="instrument-sym">BTC-USDT-SWAP</span>
              <span className="muted">OKX public reference</span>
            </span>
            <span className={cx("topbar-status", `tone-${v.tone}`)} title={v.detail}>
              <span className={cx("pulse-dot", `tone-${v.tone}`)} aria-hidden /> {v.label}
            </span>
            <UtcClock />
          </div>
        </div>
        <main className="content" key={section}>{children}</main>
      </div>
    </div>
  );
}
