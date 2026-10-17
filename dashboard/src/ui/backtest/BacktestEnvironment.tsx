/**
 * Ambiente «Backtest di sviluppo» (CAND-001): risultati congelati di un run batch, esempi apribili
 * con un clic, registro delle operazioni. Nessun comando operativo: Start/Stop/chiusura manuale
 * della simulazione non toccano questi risultati.
 */
import { useRef, useState } from 'react';
import { BacktestBundleError, parseBacktest } from '../../backtest/loadBacktest';
import { BacktestStudy } from '../../backtest/study';
import type { ShellProps } from '../App';
import { Shell } from '../App';
import { Notice } from '../components/primitives';
import { Unavailable } from '../components/Unavailable';
import { EpisodeView } from './EpisodeView';
import { LedgerView } from './LedgerView';
import { ResultsPage } from './ResultsPage';

export const BACKTEST_PATH_HINT = 'C:\\Projects\\algorithmic-trader-data\\CAND-001\\runs\\<ID del run>\\cand001-bundle.json';

function readText(file: File): Promise<string> {
  if (typeof file.text === 'function') return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error('lettura del file non riuscita'));
    reader.readAsText(file);
  });
}

export function BacktestFilePicker({ onOpen, label = 'Apri backtest' }: { onOpen: (s: BacktestStudy) => void; label?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      onOpen(new BacktestStudy(parseBacktest(await readText(file))));
    } catch (e) {
      setError(e instanceof BacktestBundleError ? e.message : `Lettura non riuscita: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="file-pick">
      <label className="btn btn-primary">
        {busy ? 'Lettura del backtest…' : label}
        <input type="file" accept=".json,application/json" className="sr-only" aria-label={label} onChange={(e) => load(e.target.files?.[0])} />
      </label>
      {error && (
        <Notice tone="negative" title="Backtest non valido">
          {error}
        </Notice>
      )}
    </div>
  );
}

export type Focus = { readonly id: string; readonly cursor?: number } | null;

export function BacktestEnvironment({ study, studyLoad = 0, onOpen, shell }: { study: BacktestStudy | null; studyLoad?: number; onOpen: (s: BacktestStudy) => void; shell: ShellProps }) {
  const shellRef = useRef<HTMLDivElement>(null);
  return (
    <Shell shell={shell} shellRef={shellRef}>
      {!study ? (
        <main className="content" id="main-content" tabIndex={-1}>
          <section className="card unavailable" aria-label="Apri backtest">
            <p className="section-title">Backtest di sviluppo · nessun risultato aperto</p>
            <p className="t-2">
              Qui si consultano i risultati del primo candidato CAND-001 sul periodo di sviluppo 2023–2024: decisioni reali del programma, ingressi e uscite
              modellati, costi e astensioni. Nessun dato è precaricato: apri il file prodotto dal comando <span className="mono">run</span>.
            </p>
            <p className="t-3" style={{ fontSize: 12 }}>
              Percorso del file: <span className="mono">{BACKTEST_PATH_HINT}</span>
            </p>
            <BacktestFilePicker onOpen={onOpen} />
          </section>
        </main>
      ) : shell.view === 'settings' ? (
        <Unavailable title="Impostazioni" onBack={() => shell.navigate('dashboard')} />
      ) : (
        <Workspace key={studyLoad} study={study} onOpen={onOpen} shell={shell} />
      )}
    </Shell>
  );
}

function Workspace({ study, onOpen, shell }: { study: BacktestStudy; onOpen: (s: BacktestStudy) => void; shell: ShellProps }) {
  const [focus, setFocus] = useState<Focus>(null);
  const open = (id: string, cursor?: number) => {
    setFocus({ id, cursor });
    shell.navigate('dashboard');
  };
  if (shell.view === 'research') return <LedgerView study={study} onOpen={open} />;
  if (focus) return <EpisodeView key={focus.id} study={study} id={focus.id} initialCursor={focus.cursor} onBack={() => setFocus(null)} />;
  return <ResultsPage study={study} onOpen={open} onOpenFile={onOpen} />;
}
