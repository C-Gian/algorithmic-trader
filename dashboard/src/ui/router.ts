/**
 * Navigazione comune a tutti gli ambienti: URL a frammento (#/...) con la cronologia del browser
 * (Indietro/Avanti), senza dipendenze di routing. Il percorso identifica ambiente, vista e, dove
 * pertinente, esecuzione, risultato ed episodio; gli ID sono identificatori opachi da validare, mai
 * percorsi di file. La pagina iniziale non naviga: un frammento vuoto si interpreta con l'ambiente
 * predefinito senza riscrivere la cronologia.
 *
 * Scorrimento: con Indietro/Avanti si ritrova la posizione registrata per quel percorso (registro
 * delle operazioni, risultati); una navigazione nuova parte dall'alto.
 */
import { useEffect, useLayoutEffect, useState } from 'react';
import type { Environment } from '../contract/historical';

export type SimView = 'dashboard' | 'research' | 'settings';
export type ResultSource = { readonly kind: 'saved'; readonly id: string } | { readonly kind: 'file' };
export type From = 'operations' | 'examples';

export type Route =
  | { readonly env: 'SIMULATION'; readonly view: SimView }
  | { readonly env: 'HISTORICAL'; readonly view: SimView; readonly t?: number }
  | { readonly env: 'BACKTEST'; readonly page: 'new' | 'saved' | 'settings' }
  | { readonly env: 'BACKTEST'; readonly page: 'job'; readonly jobId: string }
  | { readonly env: 'BACKTEST'; readonly page: 'result'; readonly source: ResultSource; readonly view: 'overview' | 'operations' }
  | { readonly env: 'BACKTEST'; readonly page: 'episode'; readonly source: ResultSource; readonly episodeId: string; readonly from: From }
  | { readonly env: 'UNKNOWN'; readonly path: string };

const SEG = /^[A-Za-z0-9._:~-]{1,200}$/;
const decode = (s: string): string | null => {
  try {
    const d = decodeURIComponent(s);
    return SEG.test(d) ? d : null;
  } catch {
    return null;
  }
};
const enc = (s: string) => encodeURIComponent(s);

export function defaultPath(env: Environment, hasBacktest = false): string {
  if (env === 'HISTORICAL') return '/historical';
  if (env === 'BACKTEST') return hasBacktest ? '/backtest/file' : '/backtest/new';
  return '/simulation';
}

export function parse(path: string): Route {
  const [raw, query = ''] = path.split('?');
  const parts = raw.split('/').filter(Boolean);
  const params = new URLSearchParams(query);
  const unknown: Route = { env: 'UNKNOWN', path };
  const [env, ...rest] = parts;
  if (env === 'simulation' || env === undefined) {
    if (rest.length === 0) return { env: 'SIMULATION', view: 'dashboard' };
    if (rest.length === 1 && (rest[0] === 'research' || rest[0] === 'settings')) return { env: 'SIMULATION', view: rest[0] };
    return unknown;
  }
  if (env === 'historical') {
    if (rest.length === 0) return { env: 'HISTORICAL', view: 'dashboard' };
    if (rest.length === 2 && rest[0] === 'at' && /^\d{1,15}$/.test(rest[1])) return { env: 'HISTORICAL', view: 'dashboard', t: Number(rest[1]) };
    if (rest.length === 1 && rest[0] === 'summary') return { env: 'HISTORICAL', view: 'research' };
    if (rest.length === 1 && rest[0] === 'settings') return { env: 'HISTORICAL', view: 'settings' };
    return unknown;
  }
  if (env !== 'backtest') return unknown;
  if (rest.length === 0) return { env: 'BACKTEST', page: 'new' };
  const [page, a] = rest;
  if (rest.length === 1 && (page === 'new' || page === 'saved' || page === 'settings')) return { env: 'BACKTEST', page };
  if (page === 'jobs' && rest.length === 2) {
    const jobId = decode(a);
    return jobId ? { env: 'BACKTEST', page: 'job', jobId } : unknown;
  }
  let source: ResultSource | null = null;
  let tail: string[] = [];
  if (page === 'results' && a) {
    const id = decode(a);
    if (!id) return unknown;
    source = { kind: 'saved', id };
    tail = rest.slice(2);
  } else if (page === 'file') {
    source = { kind: 'file' };
    tail = rest.slice(1);
  }
  if (!source) return unknown;
  if (tail.length === 0) return { env: 'BACKTEST', page: 'result', source, view: 'overview' };
  if (tail.length === 1 && tail[0] === 'operations') return { env: 'BACKTEST', page: 'result', source, view: 'operations' };
  if (tail.length === 2 && tail[0] === 'episodes') {
    const episodeId = decode(tail[1]);
    if (!episodeId) return unknown;
    return { env: 'BACKTEST', page: 'episode', source, episodeId, from: params.get('from') === 'examples' ? 'examples' : 'operations' };
  }
  return unknown;
}

export function sourceBase(source: ResultSource): string {
  return source.kind === 'saved' ? `/backtest/results/${enc(source.id)}` : '/backtest/file';
}

export const paths = {
  simulation: (view: SimView = 'dashboard') => (view === 'dashboard' ? '/simulation' : `/simulation/${view}`),
  historical: (view: SimView = 'dashboard', t?: number) =>
    view === 'research' ? '/historical/summary' : view === 'settings' ? '/historical/settings' : t !== undefined ? `/historical/at/${t}` : '/historical',
  backtestNew: () => '/backtest/new',
  backtestSaved: () => '/backtest/saved',
  job: (jobId: string) => `/backtest/jobs/${enc(jobId)}`,
  result: (source: ResultSource) => sourceBase(source),
  operations: (source: ResultSource) => `${sourceBase(source)}/operations`,
  episode: (source: ResultSource, episodeId: string, from: From) => `${sourceBase(source)}/episodes/${enc(episodeId)}?from=${from}`,
};

// ------------------------------------------------------------------ stato del browser

const scrolls = new Map<string, number>();
let lastKind: 'push' | 'pop' = 'push';
let pendingPush: string | null = null;
let currentPath = readHash();
const listeners = new Set<() => void>();

function readHash(): string {
  const h = typeof window === 'undefined' ? '' : window.location.hash;
  return h.startsWith('#') ? h.slice(1) : h;
}

function safeScroll(y: number): void {
  try {
    window.scrollTo({ top: y });
  } catch {
    // jsdom: scorrimento non implementato
  }
}

if (typeof window !== 'undefined') {
  try {
    window.history.scrollRestoration = 'manual';
  } catch {
    // facoltativo
  }
  window.addEventListener('hashchange', () => {
    const next = readHash();
    if (next === currentPath) return;
    const push = pendingPush === next;
    // Indietro/Avanti o modifica manuale dell'indirizzo: traversata, si ritrova lo scorrimento registrato.
    if (!push) scrolls.set(currentPath, window.scrollY);
    lastKind = push ? 'push' : 'pop';
    pendingPush = null;
    currentPath = next;
    listeners.forEach((l) => l());
  });
}

/** Nuova voce di cronologia (oppure sostituzione dell'attuale, senza aggiungerne). */
export function navigate(path: string, opts: { replace?: boolean } = {}): void {
  if (path === currentPath) return;
  scrolls.set(currentPath, window.scrollY);
  if (opts.replace) {
    window.history.replaceState(window.history.state, '', `#${path}`);
    lastKind = 'push';
    currentPath = path;
    listeners.forEach((l) => l());
    return;
  }
  pendingPush = path;
  lastKind = 'push';
  window.location.hash = path;
  // Alcuni ambienti (test) non emettono hashchange in modo sincrono: l'evento successivo è ignorato se già applicato.
  if (readHash() === path && currentPath !== path) {
    currentPath = path;
    pendingPush = null;
    listeners.forEach((l) => l());
  }
}

/** Percorso corrente; si aggiorna con navigate() e con Indietro/Avanti. */
export function useLocationPath(): string {
  const [, force] = useState(0);
  useEffect(() => {
    const l = () => force((n) => n + 1);
    listeners.add(l);
    // Il frammento può essere cambiato fra il primo render e la sottoscrizione.
    if (readHash() !== currentPath) {
      currentPath = readHash();
      l();
    }
    return () => {
      listeners.delete(l);
    };
  }, []);
  return currentPath;
}

/**
 * Dopo ogni cambio di percorso: in alto per una navigazione nuova, posizione registrata per
 * Indietro/Avanti. `ready` rinvia il ripristino finché il contenuto (per esempio il risultato
 * caricato dal servizio) non è presente.
 */
export function useScrollOnRoute(path: string, ready = true): void {
  useLayoutEffect(() => {
    if (!ready) return;
    if (lastKind === 'pop' && scrolls.has(path)) {
      const y = scrolls.get(path)!;
      safeScroll(y);
      // Il contenuto può crescere subito dopo (grafici, tabelle): un nuovo tentativo al frame successivo.
      if (typeof requestAnimationFrame === 'function') requestAnimationFrame(() => Math.abs(window.scrollY - y) > 2 && safeScroll(y));
    } else {
      safeScroll(0);
    }
  }, [path, ready]);
}

/** Solo per i test: stato iniziale del modulo. */
export function resetRouterForTests(): void {
  scrolls.clear();
  lastKind = 'push';
  pendingPush = null;
  currentPath = readHash();
}

export function scrollMemoryForTests(): Map<string, number> {
  return scrolls;
}
