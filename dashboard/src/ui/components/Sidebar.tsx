import type { FeedCondition, SimulationControls } from '../../contract/provider';
import type { IconName } from '../icons';
import { Badge, Icon } from './primitives';

export type NavTarget = 'dashboard' | 'research' | 'history' | 'account' | 'settings' | 'signals';

const NAV: { id: NavTarget; label: string; icon: IconName }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'layoutDashboard' },
  { id: 'research', label: 'Ricerca / Backtest', icon: 'flaskConical' },
  { id: 'history', label: 'Storico', icon: 'history17Grey' },
  { id: 'account', label: 'Conto', icon: 'wallet' },
  { id: 'settings', label: 'Impostazioni', icon: 'settings2' },
];

const FEED_OPTIONS: { id: FeedCondition; label: string }[] = [
  { id: 'OK', label: 'Regolare' },
  { id: 'STALE', label: 'Non aggiornato' },
  { id: 'DISCONNECTED', label: 'Disconnesso' },
];

export function Sidebar({
  active,
  onNavigate,
  controls,
}: {
  active: NavTarget;
  onNavigate: (target: NavTarget) => void;
  controls: SimulationControls;
}) {
  const checkpoints = controls.listCheckpoints();
  const currentId = controls.currentCheckpointId();
  const current = checkpoints.find((c) => c.id === currentId);
  const scenarios = [...new Set(checkpoints.map((c) => c.scenarioId))];
  const feed = controls.feedCondition();

  return (
    <aside className="sidebar" aria-label="Navigazione">
      <div className="brand">
        <span className="brand-mark">
          <Icon name="orbit" />
        </span>
        <p className="brand-name">
          orbit<span className="t-accent">.</span>
        </p>
      </div>

      <nav className="nav">
        <p className="nav-caption">WORKSPACE</p>
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`nav-item${active === item.id ? ' is-active' : ''}`}
            aria-current={active === item.id ? 'page' : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <Icon name={item.icon} />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="guide">
        <Icon name="bookOpen" />
        <p className="guide-title">Prima il contesto.</p>
        <p className="guide-text">Ogni segnale spiega cosa osserva e cosa significa.</p>
        <button type="button" className="link" onClick={() => onNavigate('signals')}>
          Guida ai segnali ↗
        </button>
      </div>

      <section className="simpanel" aria-label="Controlli della simulazione">
        <p className="simpanel-title">PANNELLO DI SIMULAZIONE</p>
        <p className="simpanel-desc">Sceglie lo stato dello scenario: non è un comando del bot.</p>
        <label>
          Checkpoint dello scenario
          <select value={currentId} onChange={(e) => controls.selectCheckpoint(e.target.value)}>
            {scenarios.map((sid) => {
              const group = checkpoints.filter((c) => c.scenarioId === sid);
              return (
                <optgroup key={sid} label={group[0].scenarioLabel}>
                  {group.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </optgroup>
              );
            })}
          </select>
        </label>
        {current && <p className="simpanel-desc">{current.description}</p>}
        <div>
          <p className="simpanel-desc" style={{ marginBottom: 4 }}>
            Feed simulato (alterazione controllata)
          </p>
          <div className="seg" role="group" aria-label="Condizione del feed simulato">
            {FEED_OPTIONS.map((o) => (
              <button key={o.id} type="button" aria-pressed={feed === o.id} onClick={() => controls.setFeedCondition(o.id)}>
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <button type="button" className="sim-reset" onClick={() => controls.reset()}>
          Reimposta simulazione
        </button>
        <p className="simpanel-desc">Il reset torna al checkpoint iniziale e azzera il ramo dei comandi.</p>
      </section>

      <div className="sidebar-spacer" />

      <div className="env">
        <div className="env-sep" />
        <Badge tone="accent" icon="shieldCheck13">
          SIMULAZIONE · FONDI FITTIZI
        </Badge>
        <p className="env-note">Simulazione locale. Nessuna API exchange, nessun denaro a rischio.</p>
        <div className="profile">
          <span className="avatar">MR</span>
          <div>
            <p className="profile-name">Il mio workspace</p>
            <p className="profile-sub">Simulazione · contratto lineare</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
