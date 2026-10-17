/**
 * Servizio APP-001 finto per i test della dashboard: stessi tipi del client reale, stato in memoria,
 * avanzamento guidato dal test (nessun timer). Registra le chiamate per verificare POST e GET.
 */
import { ApiError, type BacktestApi } from '../api';
import type { Job, ProfileInfo, Progress, SavedResult } from '../../contract/app';

const JAN = { start: Date.UTC(2025, 0, 1), end: Date.UTC(2025, 1, 1) };

export function profile(over: Partial<ProfileInfo> = {}): ProfileInfo {
  return {
    id: 'APP_CHECK_2025_01', label: 'Prova di gennaio 2025', kind: 'PRODUCT_CHECK', registry: 'APP-001/profiles/v1', window: JAN, withinPhase: 'ADDITIONAL_2025',
    description: 'Collaudo del prodotto.', inputStart: Date.UTC(2022, 9, 1), candidate: { id: 'CAND-001/v1', version: '1.0.0', configHash: 'aed2c4ef6277' },
    engineVersion: '1.0.3', notionalUSDT: 1000, costs: { baseline: { fee: 0.0005, slippage: 0.0003 }, stress: { fee: 0.001, slippage: 0.001 }, funding: 'storico' },
    availability: { available: true, missing: [], files: { trade: 28, funding: 1, mark: 1 }, reuseObs: 0, tradeMonths: ['2022-10', '2025-01'], costMonths: ['2025-01', '2025-01'] },
    ...over,
  };
}

export function emptyProgress(): Progress {
  const base = { status: 'PENDING' as const, startedAt: null, finishedAt: null };
  return {
    stage: null,
    window: JAN,
    stages: {
      check: { ...base, filesExpected: null, filesDone: null, byKind: null, current: null },
      init: { ...base, minutes: null, prefixMinutes: null, windowMinutes: null, steps: null, current: null },
      simulate: { ...base, closesTotal: null, closes: null, t: null, episodes: null, calls: null, requests: null, fills: null, tradesClosed: null, positionOpen: null, pendingEntry: null, haltedAt: null },
      save: { ...base, step: null, publishing: false },
    },
  };
}

type Mutable<T> = { -readonly [K in keyof T]: T[K] extends object ? Mutable<T[K]> : T[K] };

export class FakeApi implements BacktestApi {
  calls: string[] = [];
  profilesList: ProfileInfo[] = [profile()];
  jobsById = new Map<string, Mutable<Job>>();
  byKey = new Map<string, string>();
  savedResults: SavedResult[] = [];
  bundles = new Map<string, string>();
  down = false;
  failNextStart = 0;
  serverTime = '2026-10-17T12:00:05.000Z';
  private n = 0;

  private guard(name: string) {
    this.calls.push(name);
    if (this.down) throw new ApiError('SERVICE_UNAVAILABLE', 'Il servizio locale non risponde.');
  }

  active(): Mutable<Job> | undefined {
    return [...this.jobsById.values()].find((j) => ['STARTING', 'RUNNING', 'CANCEL_REQUESTED'].includes(j.state));
  }

  async profiles() {
    this.guard('GET profiles');
    return { profiles: this.profilesList, activeJob: (this.active() as Job) ?? null };
  }

  async jobs() {
    this.guard('GET jobs');
    return { jobs: [...this.jobsById.values()] as Job[], activeJobId: this.active()?.jobId ?? null };
  }

  async job(id: string) {
    this.guard(`GET job ${id}`);
    const j = this.jobsById.get(id);
    if (!j) throw new ApiError('NOT_FOUND', 'esecuzione non trovata', 'NOT_FOUND');
    return { job: structuredClone(j) as Job, serverTime: this.serverTime };
  }

  async start(profileId: string, key: string) {
    this.guard(`POST start ${profileId} ${key}`);
    if (this.failNextStart > 0) {
      this.failNextStart--;
      throw new ApiError('SERVICE_UNAVAILABLE', 'risposta persa');
    }
    const known = this.byKey.get(key);
    if (known) return { job: structuredClone(this.jobsById.get(known)!) as Job, created: false };
    const act = this.active();
    if (act) throw new ApiError('CONFLICT', 'C’è già un backtest in corso', 'ACTIVE_JOB_EXISTS', { job: structuredClone(act) });
    const p = this.profilesList.find((x) => x.id === profileId)!;
    const jobId = `job-20261017T120000Z-00000${++this.n}`;
    const job: Mutable<Job> = {
      jobId, profileId, profile: { id: p.id, label: p.label, kind: p.kind, window: p.window }, state: 'RUNNING',
      createdAt: '2026-10-17T12:00:00.000Z', startedAt: '2026-10-17T12:00:00.000Z', updatedAt: '2026-10-17T12:00:00.500Z', finishedAt: null,
      engineVersion: '1.0.3', candidate: p.candidate, progress: emptyProgress() as Mutable<Progress>, result: null, error: null, cancel: null,
    } as Mutable<Job>;
    this.jobsById.set(jobId, job);
    this.byKey.set(key, jobId);
    return { job: structuredClone(job) as Job, created: true };
  }

  async cancel(id: string) {
    this.guard(`POST cancel ${id}`);
    const j = this.jobsById.get(id)!;
    if (['COMPLETED', 'INCOMPLETE', 'CANCELLED', 'INTERRUPTED', 'FAILED'].includes(j.state)) return { job: structuredClone(j) as Job, outcome: 'ALREADY_FINISHED' };
    j.state = 'CANCEL_REQUESTED';
    j.cancel = { requestedAt: '2026-10-17T12:00:03.000Z', outcome: null };
    return { job: structuredClone(j) as Job, outcome: 'REQUESTED' };
  }

  async results() {
    this.guard('GET results');
    return { results: this.savedResults };
  }

  async bundleText(id: string) {
    this.guard(`GET bundle ${id}`);
    const b = this.bundles.get(id);
    if (!b) throw new ApiError('NOT_FOUND', 'risultato non trovato', 'NOT_FOUND');
    return b;
  }
}

export function saved(id: string, over: Partial<SavedResult> = {}): SavedResult {
  return {
    resultId: id, status: 'OK', reason: null, profile: { id: 'APP_CHECK_2025_01', label: 'Prova di gennaio 2025', kind: 'PRODUCT_CHECK', window: JAN }, window: JAN,
    schema: 'cand001.bundle/3', engineVersion: '1.0.3', candidate: { id: 'CAND-001/v1', version: '1.0.0', configHash: 'aed2' }, startedAt: '2026-10-17T12:00:00Z',
    finishedAt: '2026-10-17T12:00:20Z', complete: true, trades: 4, net: -5, halted: null, inputHash: 'abc', bundleBytes: 1000, via: 'APP-001', jobId: null, ...over,
  };
}
