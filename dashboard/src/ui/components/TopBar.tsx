/**
 * Navigazione superiore (UI-002, richiesta dell'Owner: sostituisce la barra laterale del Figma).
 * Contiene il banner di simulazione, le stesse destinazioni della barra laterale e il pulsante
 * del pannello «Scenari simulati», che parte chiuso e resta separato dai comandi di trading.
 * OBS-001: scelta distinta dell'ambiente «Simulazione locale» / «Studio storico»; il pannello
 * scenari esiste solo nella simulazione. APP-001: ambiente «Backtest» con voci proprie (collegamenti
 * #/backtest/...); il selettore d'ambiente non è il pulsante Indietro.
 */
import { useEffect, useRef, useState } from 'react';
import type { Environment } from '../../contract/historical';
import type { FeedCondition, SimulationControls } from '../../contract/provider';
import type { IconName } from '../icons';
import { Link } from '../Link';
import { Icon } from './primitives';

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

const PANEL_ID = 'scenari-simulati';

export const BANNER: Record<Environment, string> = {
  SIMULATION: 'SIMULAZIONE LOCALE — nessun collegamento exchange',
  HISTORICAL: 'STORICO REALE — studio osservativo locale — nessun collegamento exchange',
  BACKTEST: 'Simulazione su prezzi storici. Nessuna operazione reale.',
};

const ENVIRONMENTS: { id: Environment; label: string }[] = [
  { id: 'SIMULATION', label: 'Simulazione locale' },
  { id: 'HISTORICAL', label: 'Studio storico' },
  { id: 'BACKTEST', label: 'Backtest' },
];

/** Voce di navigazione con indirizzo proprio (ambiente Backtest). */
export interface NavLink {
  readonly id: string;
  readonly label: string;
  readonly icon: IconName;
  readonly to: string;
  readonly active: boolean;
}

export function TopBar({
  active,
  onNavigate,
  environment,
  onEnvironmentChange,
  controls,
  links,
}: {
  active: NavTarget;
  onNavigate: (target: NavTarget) => void;
  environment: Environment;
  onEnvironmentChange: (env: Environment) => void;
  /** Solo nella simulazione locale: controlli del pannello «Scenari simulati». */
  controls?: SimulationControls;
  /** Se presenti sostituiscono le destinazioni della dashboard (ambiente Backtest). */
  links?: readonly NavLink[];
}) {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const barRef = useRef<HTMLDivElement>(null);

  // Altezza della parte fissa: serve allo scorrimento verso Storico/Conto/Segnali.
  useEffect(() => {
    const el = barRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => document.documentElement.style.setProperty('--sticky-h', `${Math.round(el.getBoundingClientRect().height)}px`));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const close = () => {
    setOpen(false);
    toggleRef.current?.focus();
  };

  const checkpoints = controls?.listCheckpoints() ?? [];
  const currentId = controls?.currentCheckpointId() ?? '';
  const current = checkpoints.find((c) => c.id === currentId);
  const scenarios = [...new Set(checkpoints.map((c) => c.scenarioId))];
  const feed = controls?.feedCondition() ?? 'OK';
  const feedLabel = FEED_OPTIONS.find((o) => o.id === feed)?.label ?? feed;
  const historical = environment === 'HISTORICAL';
  const researchLabel = historical ? 'Studio osservativo' : environment === 'BACKTEST' ? 'Registro operazioni' : null;
  const nav = NAV.map((item) => (researchLabel && item.id === 'research' ? { ...item, label: researchLabel } : item));

  return (
    <div className="topbar-wrap" ref={barRef}>
      <div className={`sim-banner${historical ? ' is-historical' : environment === 'BACKTEST' ? ' is-backtest' : ''}`} role="status">
        <Icon name="shieldCheck13" />
        {BANNER[environment]}
      </div>

      <div className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="orbit" />
          </span>
          <p className="brand-name">
            orbit<span className="t-accent">.</span>
          </p>
        </div>

        <nav className="topnav" aria-label="Navigazione">
          {links?.map((item) => (
            <Link key={item.id} to={item.to} className={`nav-item${item.active ? ' is-active' : ''}`} ariaLabel={item.label}>
              <Icon name={item.icon} />
              {item.label}
            </Link>
          ))}
          {!links && nav.map((item) => (
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
          {!links && (
            <button type="button" className="link topnav-guide" onClick={() => onNavigate('signals')} title="Ogni segnale spiega cosa osserva e cosa significa.">
              Guida ai segnali ↗
            </button>
          )}
        </nav>

        <div className="topbar-sim">
          <div className="env-switch" role="group" aria-label="Ambiente">
            {ENVIRONMENTS.map((e) => (
              <button key={e.id} type="button" aria-pressed={environment === e.id} onClick={() => environment !== e.id && onEnvironmentChange(e.id)}>
                {e.label}
              </button>
            ))}
          </div>
          {controls && (
            <>
          <span className="scn-current" aria-hidden="true">
            {current?.label} · feed {feedLabel.toLowerCase()}
          </span>
          <button
            ref={toggleRef}
            type="button"
            className={`scn-toggle${open ? ' is-open' : ''}`}
            aria-expanded={open}
            aria-controls={PANEL_ID}
            onClick={() => setOpen((v) => !v)}
          >
            <Icon name="layers" />
            Scenari simulati
            <span aria-hidden="true">{open ? '▴' : '▾'}</span>
          </button>
            </>
          )}
        </div>
      </div>

      {controls && open && (
        <section
          id={PANEL_ID}
          className="simpanel simpanel-strip"
          aria-label="Scenari simulati"
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.stopPropagation();
              close();
            }
          }}
        >
          <div className="simpanel-intro">
            <p className="simpanel-title">PANNELLO DI SIMULAZIONE · LOCALE</p>
            <p className="simpanel-desc">Sceglie lo stato dello scenario: non è un comando del bot.</p>
          </div>
          <label className="simpanel-field">
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
            {current && <span className="simpanel-desc">{current.description}</span>}
          </label>
          <div className="simpanel-field">
            <span>Feed simulato (alterazione controllata)</span>
            <div className="seg" role="group" aria-label="Condizione del feed simulato">
              {FEED_OPTIONS.map((o) => (
                <button key={o.id} type="button" aria-pressed={feed === o.id} onClick={() => controls.setFeedCondition(o.id)}>
                  {o.label}
                </button>
              ))}
            </div>
          </div>
          <div className="simpanel-field">
            <button type="button" className="sim-reset" onClick={() => controls.reset()}>
              Reimposta simulazione
            </button>
            <span className="simpanel-desc">Torna al checkpoint iniziale e azzera il ramo dei comandi.</span>
          </div>
          <button type="button" className="btn btn-ghost simpanel-close" onClick={close}>
            Chiudi
          </button>
        </section>
      )}
    </div>
  );
}
