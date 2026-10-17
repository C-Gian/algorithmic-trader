/**
 * Ambiente «Backtest» (CAND-001, APP-001): Nuovo backtest → calcolo seguito dal vivo; Risultati
 * salvati → consultazione; Tutte le operazioni → dettaglio. Ogni vista ha il proprio indirizzo
 * #/backtest/... (Indietro/Avanti, ricaricamento). Un risultato salvato si rilegge dal servizio; un
 * file esterno resta solo in memoria e dopo il ricaricamento va riaperto. Nessun comando operativo.
 */
import { Component, useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, useApi } from '../../backtest/api';
import { BacktestBundleError, parseBacktest } from '../../backtest/loadBacktest';
import { BacktestStudy } from '../../backtest/study';
import type { ShellProps } from '../App';
import { Shell } from '../App';
import { Notice } from '../components/primitives';
import { Unavailable } from '../components/Unavailable';
import { Link } from '../Link';
import { navigate, paths, useScrollOnRoute, type ResultSource, type Route } from '../router';
import { EpisodeView } from './EpisodeView';
import { JobPage } from './JobPage';
import { LedgerView } from './LedgerView';
import { NewBacktestPage } from './NewBacktestPage';
import { ResultsPage } from './ResultsPage';
import { SavedPage } from './SavedPage';

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

export function BacktestFilePicker({ onOpen, label = 'Apri file esterno' }: { onOpen: (s: BacktestStudy) => void; label?: string }) {
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
      <label className="btn btn-secondary">
        {busy ? 'Lettura del file…' : label}
        <input type="file" accept=".json,application/json" className="sr-only" aria-label={label} onChange={(e) => load(e.target.files?.[0])} />
      </label>
      <p className="footnote">
        Percorso tipico: <span className="mono">{BACKTEST_PATH_HINT}</span>
      </p>
      {error && (
        <Notice tone="negative" title="File non valido">
          {error}
        </Notice>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ risultati salvati

const cache = new Map<string, BacktestStudy>();
const CACHE_SIZE = 3;

type Loaded = { state: 'loading' } | { state: 'ready'; study: BacktestStudy } | { state: 'error'; error: ApiError | BacktestBundleError };

/** Un risultato salvato si legge una volta e resta in memoria per registro e dettagli (niente ricarichi a ogni vista). */
function useSavedStudy(id: string): Loaded {
  const api = useApi();
  const [loaded, setLoaded] = useState<Loaded>(() => (cache.has(id) ? { state: 'ready', study: cache.get(id)! } : { state: 'loading' }));
  useEffect(() => {
    if (cache.has(id)) {
      setLoaded({ state: 'ready', study: cache.get(id)! });
      return;
    }
    let alive = true;
    setLoaded({ state: 'loading' });
    api
      .bundleText(id)
      .then((text) => {
        const study = new BacktestStudy(parseBacktest(text));
        cache.set(id, study);
        while (cache.size > CACHE_SIZE) cache.delete(cache.keys().next().value!);
        if (alive) setLoaded({ state: 'ready', study });
      })
      .catch((e) => alive && setLoaded({ state: 'error', error: e instanceof ApiError || e instanceof BacktestBundleError ? e : new ApiError('REFUSED', String(e)) }));
    return () => {
      alive = false;
    };
  }, [api, id]);
  return loaded;
}

export function clearResultCacheForTests(): void {
  cache.clear();
}

class ViewGuard extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <Notice tone="negative" title="Il risultato contiene dati non previsti">
          La vista si è fermata invece di mostrare valori incompleti: {this.state.error.message}
        </Notice>
        <Link to={paths.backtestSaved()} className="btn btn-secondary">
          Risultati salvati
        </Link>
      </main>
    );
  }
}

function ResultViews({ route, study, source }: { route: Extract<Route, { page: 'result' | 'episode' }>; study: BacktestStudy; source: ResultSource }) {
  if (route.page === 'episode') return <EpisodeView key={route.episodeId} study={study} id={route.episodeId} source={source} from={route.from} />;
  if (route.view === 'operations') return <LedgerView study={study} source={source} />;
  return <ResultsPage study={study} source={source} />;
}

function SavedResult({ route, id, path }: { route: Extract<Route, { page: 'result' | 'episode' }>; id: string; path: string }) {
  const loaded = useSavedStudy(id);
  useScrollOnRoute(path, loaded.state === 'ready');
  if (loaded.state === 'loading') {
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <p className="t-2">Lettura del risultato salvato…</p>
      </main>
    );
  }
  if (loaded.state === 'error') {
    const e = loaded.error;
    const title =
      e instanceof ApiError && e.kind === 'NOT_FOUND'
        ? 'Risultato non trovato'
        : e instanceof ApiError && e.kind === 'SERVICE_UNAVAILABLE'
          ? 'Servizio locale non raggiungibile'
          : 'Risultato non apribile';
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <Notice tone="negative" title={title}>
          {e.message} Nessun grafico o valore viene mostrato al suo posto.
        </Notice>
        <div className="actions">
          <Link to={paths.backtestSaved()} className="btn btn-primary">
            Vai ai risultati salvati
          </Link>
        </div>
      </main>
    );
  }
  return (
    <ViewGuard key={id}>
      <ResultViews route={route} study={loaded.study} source={{ kind: 'saved', id }} />
    </ViewGuard>
  );
}

function FileResult({ route, study, onOpenFile, path }: { route: Extract<Route, { page: 'result' | 'episode' }>; study: BacktestStudy | null; onOpenFile: (s: BacktestStudy) => void; path: string }) {
  useScrollOnRoute(path, study !== null);
  if (!study) {
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <section className="card unavailable" aria-label="File esterno da riaprire">
          <p className="section-title">Il file esterno va riaperto</p>
          <p className="t-2">
            Il file era aperto solo in memoria e la pagina è stata ricaricata (o il collegamento viene da un’altra scheda). Riaprilo: tornerai a questa stessa vista.
            I risultati calcolati dall’app non hanno questo limite: sono in «Risultati salvati».
          </p>
          <BacktestFilePicker onOpen={onOpenFile} label="Riapri il file" />
          <Link to={paths.backtestSaved()}>Risultati salvati</Link>
        </section>
      </main>
    );
  }
  return (
    <ViewGuard key={study.bundle.run.runId}>
      <ResultViews route={route} study={study} source={{ kind: 'file' }} />
    </ViewGuard>
  );
}

export function BacktestEnvironment({
  route,
  path,
  fileStudy,
  onOpenFile,
  shell,
}: {
  route: Extract<Route, { env: 'BACKTEST' }>;
  path: string;
  fileStudy: BacktestStudy | null;
  onOpenFile: (s: BacktestStudy, stay?: boolean) => void;
  shell: ShellProps;
}) {
  const shellRef = useRef<HTMLDivElement>(null);
  const resultRoute = route.page === 'result' || route.page === 'episode';
  useScrollOnRoute(path, !resultRoute);
  let body: ReactNode;
  if (route.page === 'result' || route.page === 'episode') {
    body =
      route.source.kind === 'saved' ? (
        <SavedResult route={route} id={route.source.id} path={path} />
      ) : (
        <FileResult route={route} study={fileStudy} onOpenFile={(s) => onOpenFile(s, true)} path={path} />
      );
  } else if (route.page === 'job') body = <JobPage key={route.jobId} jobId={route.jobId} />;
  else if (route.page === 'saved') body = <SavedPage onOpenFile={(s) => onOpenFile(s)} />;
  else if (route.page === 'settings') body = <Unavailable title="Impostazioni" onBack={() => navigate(paths.backtestNew())} />;
  else body = <NewBacktestPage />;
  return (
    <Shell shell={shell} shellRef={shellRef}>
      {body}
    </Shell>
  );
}
