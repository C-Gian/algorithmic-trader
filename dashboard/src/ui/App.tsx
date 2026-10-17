import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { ApiContext, httpApi, type BacktestApi } from '../backtest/api';
import type { Environment } from '../contract/historical';
import type { DashboardProvider, SimulationControls } from '../contract/provider';
import type { BacktestStudy } from '../backtest/study';
import type { HistoricalStudy } from '../historical/study';
import { AccountSection } from './components/AccountSection';
import { CallCard } from './components/CallCard';
import { ChartCard } from './components/ChartCard';
import { ConfirmDialog } from './components/ConfirmDialog';
import { Header } from './components/Header';
import { PositionCard } from './components/PositionCard';
import { SignalsSection } from './components/SignalsSection';
import { TopBar, type NavLink, type NavTarget } from './components/TopBar';
import { Unavailable } from './components/Unavailable';
import { BacktestEnvironment } from './backtest/BacktestEnvironment';
import { HistoricalEnvironment } from './historical/HistoricalEnvironment';
import { Link } from './Link';
import { defaultPath, navigate, parse, paths, useLocationPath, useScrollOnRoute, type Route, type SimView } from './router';
import { DashboardContext, useDashboardState } from './useDashboard';

export type View = SimView;
export type SimulationSource = DashboardProvider & SimulationControls & { dispose?: () => void };

const SCROLL_TARGET: Partial<Record<NavTarget, string>> = { history: 'storico', account: 'conto', signals: 'segnali' };

export interface ShellProps {
  readonly view: View;
  readonly navigate: (target: NavTarget) => void;
  readonly environment: Environment;
  readonly onEnvironmentChange: (env: Environment) => void;
  readonly links?: readonly NavLink[];
}

/** Contenitore comune: barra superiore e area principale; `shellRef` è il fondo reso inerte dai dialoghi. */
export function Shell({ shell, shellRef, controls, children }: { shell: ShellProps; shellRef: RefObject<HTMLDivElement>; controls?: SimulationControls; children: ReactNode }) {
  return (
    <div className="app" ref={shellRef}>
      <TopBar active={shell.view} onNavigate={shell.navigate} environment={shell.environment} onEnvironmentChange={shell.onEnvironmentChange} controls={controls} links={shell.links} />
      <div className="main">{children}</div>
    </div>
  );
}

function backtestLinks(route: Route): NavLink[] {
  const page = route.env === 'BACKTEST' ? route.page : null;
  return [
    { id: 'new', label: 'Nuovo backtest', icon: 'play16Grey', to: paths.backtestNew(), active: page === 'new' || page === 'job' },
    { id: 'saved', label: 'Risultati salvati', icon: 'history17Grey', to: paths.backtestSaved(), active: page === 'saved' || page === 'result' || page === 'episode' },
  ];
}

/**
 * Tre ambienti distinti, ciascuno con i propri indirizzi #/simulation, #/historical, #/backtest.
 * Il cambio smonta l'ambiente precedente: conferme e richieste aperte della simulazione spariscono
 * senza essere applicate e nessun bot/ordine passa allo storico o al backtest. Un frammento vuoto
 * mostra l'ambiente predefinito senza riscrivere la cronologia; nessun calcolo parte al montaggio.
 */
export function App({
  createSimulation,
  initialEnvironment = 'SIMULATION',
  initialStudy = null,
  initialBacktest = null,
  api = httpApi,
}: {
  createSimulation: () => SimulationSource;
  initialEnvironment?: Environment;
  initialStudy?: HistoricalStudy | null;
  initialBacktest?: BacktestStudy | null;
  api?: BacktestApi;
}) {
  const location = useLocationPath();
  const path = location || defaultPath(initialEnvironment, initialBacktest !== null);
  const route = parse(path);
  const [study, setStudy] = useState<HistoricalStudy | null>(initialStudy);
  // Ogni apertura riuscita monta lo studio da capo (anche se è lo stesso file): niente stato residuo.
  const [studyLoad, setStudyLoad] = useState(0);
  const [fileBacktest, setFileBacktest] = useState<BacktestStudy | null>(initialBacktest);

  const env: Environment = route.env === 'UNKNOWN' ? 'SIMULATION' : route.env;
  const view: View = route.env === 'SIMULATION' || route.env === 'HISTORICAL' ? route.view : 'dashboard';

  const go = useCallback(
    (target: NavTarget) => {
      const to = (v: SimView) => (env === 'HISTORICAL' ? paths.historical(v, v === 'dashboard' && route.env === 'HISTORICAL' ? route.t : undefined) : paths.simulation(v));
      if (target === 'research' || target === 'settings') {
        navigate(to(target));
        return;
      }
      if (view !== 'dashboard') navigate(to('dashboard'));
      const id = SCROLL_TARGET[target];
      requestAnimationFrame(() => {
        if (id) document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        else window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    },
    [env, view, route],
  );

  const changeEnvironment = useCallback((next: Environment) => {
    navigate(next === 'BACKTEST' ? paths.backtestNew() : defaultPath(next));
  }, []);

  const openStudy = useCallback(
    (s: HistoricalStudy) => {
      const reopening = study === null && route.env === 'HISTORICAL';
      setStudy(s);
      setStudyLoad((n) => n + 1);
      // Riaperto dopo un ricaricamento: si resta sulla vista e sul momento dell'indirizzo; un altro studio riparte dalla prima origine.
      if (!reopening) navigate(paths.historical());
    },
    [study, route.env],
  );

  const openBacktest = useCallback((b: BacktestStudy, stay = false) => {
    setFileBacktest(b);
    if (!stay) navigate('/backtest/file');
  }, []);

  const shell: ShellProps = { view, navigate: go, environment: env, onEnvironmentChange: changeEnvironment, links: env === 'BACKTEST' ? backtestLinks(route) : undefined };
  let body: ReactNode;
  if (route.env === 'UNKNOWN') body = <NotFound shell={shell} path={path} />;
  else if (route.env === 'SIMULATION') body = <SimulationEnvironment create={createSimulation} shell={shell} path={path} />;
  else if (route.env === 'BACKTEST') body = <BacktestEnvironment route={route} path={path} fileStudy={fileBacktest} onOpenFile={openBacktest} shell={shell} />;
  else body = <HistoricalEnvironment study={study} studyLoad={studyLoad} onOpen={openStudy} shell={shell} moment={route.t} path={path} />;
  return <ApiContext.Provider value={api}>{body}</ApiContext.Provider>;
}

function NotFound({ shell, path }: { shell: ShellProps; path: string }) {
  const shellRef = useRef<HTMLDivElement>(null);
  return (
    <Shell shell={shell} shellRef={shellRef}>
      <main className="content" id="main-content" tabIndex={-1}>
        <section className="card unavailable" aria-label="Pagina non trovata">
          <p className="section-title">Pagina non trovata</p>
          <p className="t-2">
            L’indirizzo <span className="mono">#{path}</span> non corrisponde a una vista dell’app.
          </p>
          <div className="actions">
            <Link to={paths.backtestNew()} className="btn btn-primary">
              Backtest
            </Link>
            <Link to={paths.simulation()} className="btn btn-secondary">
              Simulazione locale
            </Link>
            <Link to={paths.historical()} className="btn btn-secondary">
              Studio storico
            </Link>
          </div>
        </section>
      </main>
    </Shell>
  );
}

function SimulationEnvironment({ create, shell, path }: { create: () => SimulationSource; shell: ShellProps; path: string }) {
  // Un provider nuovo a ogni ingresso nell'ambiente: niente stato trasferito dallo storico o da prima.
  const [provider] = useState(create);
  useEffect(() => () => provider.dispose?.(), [provider]);
  const api = useDashboardState(provider);
  const shellRef = useRef<HTMLDivElement>(null);
  useScrollOnRoute(path);

  return (
    <DashboardContext.Provider value={api}>
      <Shell shell={shell} shellRef={shellRef} controls={provider}>
        {shell.view === 'dashboard' ? (
          <>
            <Header />
            <main className="content" id="main-content" tabIndex={-1}>
              <div className="row-market">
                <ChartCard />
                <CallCard />
              </div>
              <PositionCard />
              <SignalsSection />
              <AccountSection />
              <p className="footnote">
                Simulazione locale con scenari fittizi: a ogni apertura o ricaricamento della pagina riparte dallo scenario iniziale. Nessuna posizione locale viene
                ripristinata.
              </p>
            </main>
          </>
        ) : (
          <Unavailable title={shell.view === 'research' ? 'Ricerca / Backtest' : 'Impostazioni'} onBack={() => shell.navigate('dashboard')} />
        )}
      </Shell>
      {api.confirmation && (
        <ConfirmDialog
          key={api.confirmation.requestId}
          preview={api.confirmation.preview}
          onConfirm={api.confirm}
          onCancel={api.cancel}
          background={shellRef}
        />
      )}
      {api.toast && (
        <div className="toast" role="status">
          {api.toast}
        </div>
      )}
    </DashboardContext.Provider>
  );
}
