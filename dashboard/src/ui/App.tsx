import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
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
import { TopBar, type NavTarget } from './components/TopBar';
import { Unavailable } from './components/Unavailable';
import { BacktestEnvironment } from './backtest/BacktestEnvironment';
import { HistoricalEnvironment } from './historical/HistoricalEnvironment';
import { DashboardContext, useDashboardState } from './useDashboard';

export type View = 'dashboard' | 'research' | 'settings';
export type SimulationSource = DashboardProvider & SimulationControls & { dispose?: () => void };

const SCROLL_TARGET: Partial<Record<NavTarget, string>> = { history: 'storico', account: 'conto', signals: 'segnali' };

export interface ShellProps {
  readonly view: View;
  readonly navigate: (target: NavTarget) => void;
  readonly environment: Environment;
  readonly onEnvironmentChange: (env: Environment) => void;
}

/** Contenitore comune: barra superiore e area principale; `shellRef` è il fondo reso inerte dai dialoghi. */
export function Shell({ shell, shellRef, controls, children }: { shell: ShellProps; shellRef: RefObject<HTMLDivElement>; controls?: SimulationControls; children: ReactNode }) {
  return (
    <div className="app" ref={shellRef}>
      <TopBar active={shell.view} onNavigate={shell.navigate} environment={shell.environment} onEnvironmentChange={shell.onEnvironmentChange} controls={controls} />
      <div className="main">{children}</div>
    </div>
  );
}

/**
 * Due ambienti distinti. Il cambio smonta l'ambiente precedente: conferme e richieste aperte
 * della simulazione spariscono senza essere applicate e nessun bot/ordine passa allo storico.
 * Default dichiarato: «Simulazione locale»; aprire un bundle valido porta allo studio storico.
 */
export function App({
  createSimulation,
  initialEnvironment = 'SIMULATION',
  initialStudy = null,
  initialBacktest = null,
}: {
  createSimulation: () => SimulationSource;
  initialEnvironment?: Environment;
  initialStudy?: HistoricalStudy | null;
  initialBacktest?: BacktestStudy | null;
}) {
  const [environment, setEnvironment] = useState<Environment>(initialEnvironment);
  const [study, setStudy] = useState<HistoricalStudy | null>(initialStudy);
  // Ogni apertura riuscita monta lo studio da capo (anche se è lo stesso file): niente stato residuo.
  const [studyLoad, setStudyLoad] = useState(0);
  const [view, setView] = useState<View>('dashboard');
  const [backtest, setBacktest] = useState<BacktestStudy | null>(initialBacktest);
  const [backtestLoad, setBacktestLoad] = useState(0);

  const navigate = useCallback((target: NavTarget) => {
    if (target === 'research' || target === 'settings') {
      setView(target);
      window.scrollTo({ top: 0 });
      return;
    }
    setView('dashboard');
    const id = SCROLL_TARGET[target];
    requestAnimationFrame(() => {
      if (id) document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      else window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }, []);

  const changeEnvironment = useCallback((env: Environment) => {
    setEnvironment(env);
    setView('dashboard');
    window.scrollTo({ top: 0 });
  }, []);

  const openStudy = useCallback((s: HistoricalStudy) => {
    setStudy(s);
    setStudyLoad((n) => n + 1);
    setEnvironment('HISTORICAL');
    setView('dashboard');
  }, []);

  const openBacktest = useCallback((b: BacktestStudy) => {
    setBacktest(b);
    setBacktestLoad((n) => n + 1);
    setEnvironment('BACKTEST');
    setView('dashboard');
  }, []);

  const shell: ShellProps = { view, navigate, environment, onEnvironmentChange: changeEnvironment };
  if (environment === 'SIMULATION') return <SimulationEnvironment create={createSimulation} shell={shell} />;
  if (environment === 'BACKTEST') return <BacktestEnvironment study={backtest} studyLoad={backtestLoad} onOpen={openBacktest} shell={shell} />;
  return <HistoricalEnvironment study={study} studyLoad={studyLoad} onOpen={openStudy} shell={shell} />;
}

function SimulationEnvironment({ create, shell }: { create: () => SimulationSource; shell: ShellProps }) {
  // Un provider nuovo a ogni ingresso nell'ambiente: niente stato trasferito dallo storico o da prima.
  const [provider] = useState(create);
  useEffect(() => () => provider.dispose?.(), [provider]);
  const api = useDashboardState(provider);
  const shellRef = useRef<HTMLDivElement>(null);

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
