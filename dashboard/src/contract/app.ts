/**
 * Contratto del servizio locale APP-001 (/api): profili fissi, esecuzioni (job) e risultati salvati.
 * L'app mostra lo stato che il servizio dichiara; non calcola segnali, conti o avanzamenti.
 */
import type { Ms } from './historical';

export type JobState = 'STARTING' | 'RUNNING' | 'CANCEL_REQUESTED' | 'COMPLETED' | 'INCOMPLETE' | 'CANCELLED' | 'INTERRUPTED' | 'FAILED';
export const ACTIVE_STATES: readonly JobState[] = ['STARTING', 'RUNNING', 'CANCEL_REQUESTED'];
export const isActive = (s: JobState) => ACTIVE_STATES.includes(s);

export interface ProfileRef {
  readonly id: string;
  readonly label: string;
  readonly kind: string;
  readonly registry?: string;
  readonly window: { readonly start: Ms; readonly end: Ms };
  readonly withinPhase?: string;
  readonly inferred?: boolean;
}

export interface Availability {
  readonly available: boolean;
  readonly missing: readonly { readonly kind: string; readonly month: string; readonly reason: string }[];
  readonly files: { readonly trade: number; readonly funding: number; readonly mark: number };
  readonly reuseObs: number;
  readonly tradeMonths: readonly [string, string];
  readonly costMonths: readonly [string, string];
}

export interface ProfileInfo extends ProfileRef {
  readonly description: string;
  readonly inputStart: Ms;
  readonly candidate: { readonly id: string; readonly version: string; readonly configHash: string };
  readonly engineVersion: string;
  readonly notionalUSDT: number;
  readonly costs: { readonly baseline: { readonly fee: number; readonly slippage: number }; readonly stress: { readonly fee: number; readonly slippage: number }; readonly funding: string };
  readonly availability: Availability;
}

export type StageStatus = 'PENDING' | 'RUNNING' | 'DONE' | 'STOPPED';

interface StageBase {
  readonly status: StageStatus;
  readonly startedAt: string | null;
  readonly finishedAt: string | null;
}

export interface Progress {
  readonly stage: 'check' | 'init' | 'simulate' | 'save' | null;
  readonly window: { readonly start: Ms; readonly end: Ms };
  readonly stages: {
    readonly check: StageBase & {
      readonly filesExpected: number | null;
      readonly filesDone: number | null;
      readonly byKind: Readonly<Record<'trade' | 'funding' | 'mark', { readonly expected: number; readonly done: number }>> | null;
      readonly current: { readonly kind: string; readonly month: string; readonly rows: number } | null;
      readonly reuseObs?: number;
    };
    readonly init: StageBase & {
      readonly minutes: number | null;
      readonly minutesValid?: number | null;
      readonly prefixMinutes: number | null;
      readonly windowMinutes: number | null;
      readonly steps: Readonly<Record<string, { readonly done: number; readonly total: number }>> | null;
      readonly current: string | null;
    };
    readonly simulate: StageBase & {
      readonly closesTotal: number | null;
      readonly closes: number | null;
      readonly t: Ms | null;
      readonly episodes: number | null;
      readonly calls: number | null;
      readonly requests: number | null;
      readonly fills: number | null;
      readonly tradesClosed: number | null;
      readonly positionOpen: boolean | null;
      readonly pendingEntry: boolean | null;
      readonly haltedAt: Ms | null;
    };
    readonly save: StageBase & { readonly step: string | null; readonly publishing: boolean };
  };
}

export interface Job {
  readonly jobId: string;
  readonly profileId: string;
  readonly profile: ProfileRef;
  readonly state: JobState;
  readonly stateHistory?: readonly { readonly state: JobState; readonly at: string; readonly note?: string }[];
  readonly createdAt: string;
  readonly startedAt: string;
  readonly updatedAt: string;
  readonly finishedAt: string | null;
  readonly engineVersion: string;
  readonly candidate?: { readonly id: string; readonly version: string; readonly configHash: string };
  readonly progress?: Progress;
  readonly result: {
    readonly resultId: string;
    readonly bundleSha256: string;
    readonly complete: boolean;
    readonly reusedIdenticalBundle: boolean;
    readonly inputHash: string;
    readonly configHash: string;
    readonly counts: { readonly trades: number; readonly requests?: number; readonly episodes: number };
    readonly halted: { readonly at: Ms; readonly reason: string } | null;
  } | null;
  readonly error: { readonly kind: string; readonly message: string; readonly qualityReport?: string } | null;
  readonly cancel: { readonly requestedAt: string; readonly outcome: 'CANCELLED' | 'TOO_LATE' | null } | null;
}

export interface SavedResult {
  readonly resultId: string;
  readonly status: 'OK' | 'NOT_OPENABLE' | 'UNSUPPORTED_SCHEMA';
  readonly reason: string | null;
  readonly profile: ProfileRef | null;
  readonly window: { readonly start: Ms; readonly end: Ms } | null;
  readonly schema: string | null;
  readonly engineVersion: string | null;
  readonly candidate: { readonly id: string; readonly version: string; readonly configHash: string } | null;
  readonly startedAt: string | null;
  readonly finishedAt: string | null;
  readonly complete: boolean | null;
  readonly trades: number | null;
  readonly net: number | null;
  readonly halted: { readonly at: Ms; readonly reason: string } | null;
  readonly inputHash: string | null;
  readonly bundleBytes: number | null;
  readonly via: string | null;
  readonly jobId: string | null;
}
