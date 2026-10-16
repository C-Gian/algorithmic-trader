import { useCallback, useState } from 'react';
import type { DashboardProvider, SimulationControls } from '../contract/provider';
import { AccountSection } from './components/AccountSection';
import { CallCard } from './components/CallCard';
import { ChartCard } from './components/ChartCard';
import { ConfirmDialog } from './components/ConfirmDialog';
import { Header } from './components/Header';
import { PositionCard } from './components/PositionCard';
import { Sidebar, type NavTarget } from './components/Sidebar';
import { SignalsSection } from './components/SignalsSection';
import { Unavailable } from './components/Unavailable';
import { Icon } from './components/primitives';
import { DashboardContext, useDashboardState } from './useDashboard';

const SCROLL_TARGET: Partial<Record<NavTarget, string>> = { history: 'storico', account: 'conto', signals: 'segnali' };

export function App({ provider, controls }: { provider: DashboardProvider; controls: SimulationControls }) {
  const api = useDashboardState(provider);
  const [view, setView] = useState<'dashboard' | 'research' | 'settings'>('dashboard');

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

  return (
    <DashboardContext.Provider value={api}>
      <div className="app">
        <div className="sidebar-col">
          <Sidebar active={view} onNavigate={navigate} controls={controls} />
        </div>
        <div className="main">
          <div className="sim-banner" role="status">
            <Icon name="shieldCheck13" />
            SIMULAZIONE LOCALE — nessun collegamento exchange
          </div>
          {view === 'dashboard' ? (
            <>
              <Header />
              <main className="content">
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
            <Unavailable title={view === 'research' ? 'Ricerca / Backtest' : 'Impostazioni'} onBack={() => navigate('dashboard')} />
          )}
        </div>
      </div>
      {api.confirmation && (
        <ConfirmDialog key={api.confirmation.requestId} preview={api.confirmation.preview} onConfirm={api.confirm} onCancel={api.cancel} />
      )}
      {api.toast && (
        <div className="toast" role="status">
          {api.toast}
        </div>
      )}
    </DashboardContext.Provider>
  );
}
