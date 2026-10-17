/**
 * Contratto del backtest CAND-001 (bundle `cand001.bundle/2` e `/3`).
 * Distinto dal bundle osservativo OBS-001 e dalla simulazione: esecuzioni modellate su prezzi
 * storici, nozionale normalizzato fisso, nessun conto o saldo personale. Tempi in ms epoch UTC.
 */
import type { ProfileRef } from './app';
import type { Measure, Ms } from './historical';

export const BACKTEST_KIND = 'CAND001_BUNDLE' as const;
/**
 * /2 (motore 1.0.1, review R1): operazioni irrisolte, copertura dei periodi, riconciliazione separata.
 * /3 (motore 1.0.3, APP-001): /2 più l'identità del profilo eseguito (per esempio la prova di gennaio 2025).
 * I risultati /2 già consegnati restano apribili: il profilo si deduce dalla fase, dichiarandolo.
 */
export const BACKTEST_SCHEMAS = ['cand001.bundle/2', 'cand001.bundle/3'] as const;

export type Side = 'LONG' | 'SHORT';

export interface BtPivot {
  readonly kind: 'HIGH' | 'LOW';
  readonly price: number;
  readonly candidateOpen: Ms;
  readonly eventTime: Ms;
  readonly availableAt: Ms;
}

/** Stato del candidato a un istante: decisione reale del motore, non testo della dashboard. */
export interface BtState {
  readonly t: Ms;
  readonly state: string;
  readonly [key: string]: unknown;
}

export interface BtPlan {
  readonly S0: number;
  readonly T: number;
  readonly Estar: number;
  readonly risk: number;
  readonly gain: number;
  readonly ratio: number | null;
  readonly Ck: number;
  readonly Rext: number;
  readonly depth: number;
  readonly counterCloses: number;
  readonly barsSinceP1: number;
}

export interface BtCall {
  readonly t: Ms;
  readonly side: Side;
  readonly expectation: string;
  readonly S0: number;
  readonly T: number;
  readonly Estar: number;
  readonly entryBound: number;
  readonly executeAt: Ms;
}

export interface BtRequest {
  readonly episodeId: string;
  readonly callTime: Ms;
  readonly executeAt: Ms;
  readonly side: Side;
  readonly outcome: string;
  readonly Oref?: number;
  readonly E?: number;
  readonly R0?: number;
  readonly G0?: number;
  readonly ratio?: number | null;
}

export interface BtContext {
  readonly t: Ms;
  readonly C: number | null;
  readonly A: Measure;
  readonly structure45m: Measure<string>;
  readonly structure1D: Measure<string>;
  readonly sma20: Measure;
  readonly sma50: Measure;
  readonly smaDist: Measure;
  readonly volumeRatio: Measure;
  readonly fibVersion: number;
}

export interface BtEpisode {
  readonly id: string;
  readonly legId: string;
  readonly side: Side;
  readonly d: 1 | -1;
  readonly P0: BtPivot;
  readonly P1: BtPivot;
  readonly A0: number;
  readonly L: number;
  readonly t0: Ms;
  readonly status: string;
  readonly states: readonly BtState[];
  readonly plan: BtPlan | null;
  readonly call: BtCall | null;
  readonly termination: { readonly t: Ms; readonly code: string; readonly [key: string]: unknown } | null;
  readonly context0: BtContext;
  readonly tradeId: string | null;
  readonly request: BtRequest | null;
}

export interface BtStop {
  readonly decidedAt: Ms;
  readonly effectiveAt: Ms;
  readonly from: number;
  readonly to: number;
  readonly pivot: number;
}

export interface BtFundingEvent {
  readonly tau: Ms;
  readonly rate: number;
  readonly M: number | null;
  /** Minuto mark [u-60s, u) che valorizza l'evento. */
  readonly markMinute?: Ms;
  readonly cashflow: number | null;
  readonly counted: boolean;
  readonly ambiguous: boolean;
}

export interface BtExit {
  readonly reason: string;
  readonly minute: Ms;
  readonly accountingTime: Ms;
  readonly Xref: number;
  readonly X: number;
  readonly gap: boolean;
  readonly intrabar: boolean;
  readonly bothTouched: boolean;
}

/**
 * Operazione modellata. Con `status: 'UNRESOLVED_DATA_GAP'` il percorso è irrisolto: `exit` è null,
 * prezzo d'uscita, PnL, netto e stress sono null; restano ingresso, fee d'ingresso, protezioni,
 * funding valutabile fino alla lacuna e il momento della lacuna (`gap`).
 */
export interface BtTrade {
  readonly id: string;
  readonly status?: 'UNRESOLVED_DATA_GAP';
  readonly gap?: { readonly at: Ms; readonly reason: string };
  readonly durationUntilGapMin?: number;
  readonly episodeId: string;
  readonly side: Side;
  readonly d: 1 | -1;
  readonly callTime: Ms;
  readonly entryTime: Ms;
  readonly Eref: number;
  readonly E: number;
  readonly q: number;
  readonly N0: number;
  readonly S0: number;
  readonly T: number;
  readonly R0: number;
  readonly G0: number;
  readonly stops: readonly BtStop[];
  readonly exit: BtExit | null;
  readonly pricePnL: number | null;
  readonly pricePnLRef: number | null;
  readonly slippageCost: number | null;
  readonly feeEntry: number;
  readonly feeExit: number | null;
  readonly funding: { readonly events: readonly BtFundingEvent[]; readonly total: number | null; readonly missing: boolean; readonly ambiguous: boolean };
  readonly net: number | null;
  readonly netRange: readonly [number, number] | null;
  readonly stress: { readonly fee: number; readonly slippage: number; readonly net: number | null };
  readonly targetFirst?: { readonly Xref: number; readonly net: number | null; readonly delta: number | null };
  readonly durationMin: number | null;
  readonly riskInitial: number;
  readonly netBps: number | null;
}

export interface BtBars {
  readonly open: readonly Ms[];
  readonly status: readonly string[];
  readonly o: readonly (number | null)[];
  readonly h: readonly (number | null)[];
  readonly l: readonly (number | null)[];
  readonly c: readonly (number | null)[];
  readonly v: readonly (number | null)[];
}

export interface BtSnapshot {
  readonly t: Ms;
  readonly C: number | null;
  readonly A: Measure;
  readonly structure45m: Measure<string>;
  readonly structure1D: Measure<string>;
  readonly sma20: Measure;
  readonly sma50: Measure;
  readonly volumeRatio: Measure;
  readonly fib: { readonly version: number; readonly u: number | null; readonly r: number | null };
}

export interface BtWindow {
  readonly bars45: BtBars;
  readonly bars1d: BtBars;
  readonly sma20: readonly (number | null)[];
  readonly sma50: readonly (number | null)[];
  readonly pivots: readonly BtPivot[];
  readonly snapshots: Readonly<Record<string, BtSnapshot>>;
}

export interface BtStats {
  readonly n: number;
  readonly mean: number | null;
  readonly p10: number | null;
  readonly p25: number | null;
  readonly p50: number | null;
  readonly p75: number | null;
  readonly p90: number | null;
}

export interface BtTradeStats {
  readonly n: number;
  readonly closed: number;
  readonly unresolved: number;
  /** Parte nota: somme delle sole operazioni concluse, dichiarate parziali. */
  readonly closedSubset: { readonly trades: number; readonly net: number | null; readonly label: string };
  readonly long: number;
  readonly short: number;
  readonly pricePnLRef: number | null;
  readonly slippage: number | null;
  readonly fees: number | null;
  readonly funding: number | null;
  readonly net: number | null;
  readonly netBps: number | null;
  readonly stressNet: number | null;
  readonly positiveShare: number | null;
  readonly payoff: number | null;
  readonly profitFactor: number | null;
  readonly maxLosingStreak: number;
  readonly exits: Readonly<Record<string, number>>;
  readonly protectionUpdates: number;
  readonly tradesWithProtectionUpdate: number;
  readonly bothTouched: number;
  readonly gapExits: number;
  readonly fundingAmbiguousTrades: number;
  readonly fundingMissingTrades: number;
  readonly exposureShare: number;
  readonly perTrade: { readonly net: BtStats; readonly durationMin: BtStats; readonly riskInitialOverN0: BtStats };
  readonly concentration: { readonly top5AbsShare: number | null; readonly best5PositiveShare: number | null; readonly worst5NegativeShare: number | null };
}

export interface BtCoverage {
  readonly complete: boolean;
  readonly evaluated: boolean;
  readonly evaluatedUntil: Ms;
  readonly haltedAt: Ms | null;
  readonly unresolvedTrades: number;
}

export interface BtPeriod {
  readonly start: Ms;
  readonly end: Ms;
  readonly coverage: BtCoverage;
  readonly closes: number;
  readonly evaluatedCloses: number;
  readonly notEvaluatedCloses: number;
  readonly validCloses: number;
  readonly legs: number;
  readonly episodes: number;
  readonly calls: number;
  readonly requests: Readonly<Record<string, number>>;
  readonly trades: BtTradeStats;
  readonly drawdown: { readonly maxDrawdown: number | null; readonly missing: boolean; readonly partialUntil?: Ms; readonly partialMaxDrawdown?: number | null };
  readonly legsByOutcome: Readonly<Record<string, number>>;
  readonly episodesByTermination: Readonly<Record<string, number>>;
}

export type ExampleCategory =
  | 'FIRST_CALL'
  | 'FIRST_TRADE'
  | 'FIRST_NEGATIVE_TRADE'
  | 'FIRST_POSITIVE_TRADE'
  | 'FIRST_PROTECTION_UPDATE'
  | 'FIRST_ABSTAIN_REACTION_INVALIDATED'
  | 'FIRST_ABSTAIN_REWARD_RISK'
  | 'FIRST_ABSTAIN_MISSING_DATA';

export interface ExampleRef {
  readonly kind: 'episode' | 'trade' | 'leg';
  readonly id: string;
  readonly episodeId?: string;
  readonly t: Ms;
}

export interface BtLeg {
  readonly id: string;
  readonly t: Ms;
  readonly d: 1 | -1;
  readonly outcome: string;
  readonly P0: BtPivot;
  readonly P1: BtPivot;
}

export interface BacktestBundle {
  readonly kind: typeof BACKTEST_KIND;
  readonly schema: (typeof BACKTEST_SCHEMAS)[number];
  /** Solo schema /3; per /2 vedi BacktestStudy.profile (dedotto dalla fase). */
  readonly profile?: ProfileRef;
  readonly engineVersion: string;
  readonly candidate: { readonly id: string; readonly version: string; readonly hash: string };
  readonly observationConventions: { readonly id: string; readonly hash: string };
  readonly phase: string;
  readonly window: { readonly start: Ms; readonly end: Ms; readonly inputStart: Ms };
  readonly run: { readonly runId: string; readonly inputHash: string | null; readonly engineVersion: string; readonly synthetic?: boolean };
  readonly source: { readonly attribution: string; readonly symbol: string; readonly segment: string; readonly contractType: string };
  readonly economicsLabel: string;
  readonly notionalUSDT: number;
  readonly quality: {
    readonly trade: { readonly totals: { readonly expected: number; readonly valid: number; readonly missing: number; readonly invalid: number } };
    readonly funding: { readonly series: { readonly events: number; readonly anomalies: readonly unknown[] } };
    readonly mark: { readonly pointsNeeded: number; readonly pointsAvailable: number };
  };
  readonly summary: {
    readonly phase: string;
    readonly periods: readonly string[];
    readonly tables: Readonly<Record<string, BtPeriod>>;
    readonly months: Readonly<Record<string, BtPeriod & { readonly cashflowByTimestamp: { readonly net: number | null } }>>;
    readonly examples: Readonly<Record<Side, Readonly<Record<ExampleCategory, ExampleRef | null>>>>;
    readonly halted: { readonly at: Ms; readonly reason: string; readonly positionId: string | null } | null;
    readonly reconciliation: {
      readonly knownPartReconciled: boolean;
      readonly windowComplete: boolean;
      readonly closedTrades: number;
      readonly unresolvedTrades: number;
      readonly knownPartNet: number | null;
      readonly evaluatedCloses: number;
      readonly notEvaluatedCloses: number;
    };
  };
  readonly trades: readonly BtTrade[];
  readonly requests: readonly BtRequest[];
  readonly episodes: readonly BtEpisode[];
  readonly exampleLegs: readonly BtLeg[];
  readonly windows: Readonly<Record<string, BtWindow>>;
}
