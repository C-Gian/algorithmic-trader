/**
 * Client del servizio locale APP-001 tramite /api (proxy di Vite verso 127.0.0.1:8765).
 * Gli errori distinguono servizio assente/non raggiungibile, risorsa non trovata, dati mancanti,
 * conflitto con un'esecuzione attiva e richiesta rifiutata. Nessun percorso o comando inviato: solo ID.
 */
import { createContext, useContext } from 'react';
import type { Job, ProfileInfo, SavedResult } from '../contract/app';

export type ApiErrorKind = 'SERVICE_UNAVAILABLE' | 'NOT_FOUND' | 'DATA_MISSING' | 'CONFLICT' | 'NOT_OPENABLE' | 'REFUSED';

export class ApiError extends Error {
  constructor(
    readonly kind: ApiErrorKind,
    message: string,
    readonly code: string | null = null,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

export interface BacktestApi {
  profiles(): Promise<{ profiles: ProfileInfo[]; activeJob: Job | null }>;
  jobs(): Promise<{ jobs: Job[]; activeJobId: string | null }>;
  job(jobId: string): Promise<{ job: Job; serverTime: string }>;
  start(profileId: string, requestKey: string): Promise<{ job: Job; created: boolean }>;
  cancel(jobId: string): Promise<{ job: Job; outcome: string }>;
  results(): Promise<{ results: SavedResult[] }>;
  bundleText(resultId: string): Promise<string>;
}

const KIND_BY_CODE: Record<string, ApiErrorKind> = {
  NOT_FOUND: 'NOT_FOUND',
  DATA_MISSING: 'DATA_MISSING',
  ACTIVE_JOB_EXISTS: 'CONFLICT',
  WORKER_BUSY: 'CONFLICT',
  REQUEST_KEY_CONFLICT: 'CONFLICT',
  TOO_LATE: 'CONFLICT',
  RESULT_NOT_OPENABLE: 'NOT_OPENABLE',
};

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(path, { cache: 'no-store', ...init });
  } catch {
    throw new ApiError('SERVICE_UNAVAILABLE', 'Il servizio locale non risponde. Avvia l’app con «npm run dev» nella cartella dashboard.');
  }
  if (!res.headers.get('x-app001-service')) {
    // Risposta del proxy di Vite (servizio spento) o di altro programma: non è il servizio dell'app.
    throw new ApiError('SERVICE_UNAVAILABLE', 'Il servizio locale non risponde. Avvia l’app con «npm run dev» nella cartella dashboard.');
  }
  if (!res.ok) {
    let body: { error?: { code?: string; message?: string } & Record<string, unknown> } = {};
    try {
      body = await res.json();
    } catch {
      // corpo non JSON
    }
    const code = body.error?.code ?? null;
    const { code: _c, message: _m, ...details } = body.error ?? {};
    void _c;
    void _m;
    throw new ApiError((code && KIND_BY_CODE[code]) || 'REFUSED', body.error?.message ?? `richiesta rifiutata (${res.status})`, code, details);
  }
  return res;
}

const json = async <T>(path: string, init?: RequestInit): Promise<T> => (await request(path, init)).json() as Promise<T>;
const post = <T>(path: string, body: unknown) => json<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const httpApi: BacktestApi = {
  profiles: () => json('/api/profiles'),
  jobs: () => json('/api/jobs'),
  job: (id) => json(`/api/jobs/${encodeURIComponent(id)}`),
  start: (profileId, requestKey) => post('/api/jobs', { profileId, requestKey }),
  cancel: (id) => post(`/api/jobs/${encodeURIComponent(id)}/cancel`, {}),
  results: () => json('/api/results'),
  bundleText: async (id) => (await request(`/api/results/${encodeURIComponent(id)}/bundle`)).text(),
};

export const ApiContext = createContext<BacktestApi>(httpApi);
export const useApi = () => useContext(ApiContext);

export function newRequestKey(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === 'function') return c.randomUUID();
  return `k${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
}
