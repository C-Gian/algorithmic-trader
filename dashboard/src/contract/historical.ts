/**
 * Contratto dello studio storico OBS-001 (bundle `obs001.bundle/1`).
 *
 * Distinto dal contratto della simulazione locale (`types.ts`, `simulated: true`): l'ambiente
 * è un discriminante reale (`Environment`), non un flag forzato. Tempi in millisecondi epoch
 * UTC. Ogni misura è `{ v, r }`: valore noto (anche zero) oppure null con motivo.
 */

export type Environment = 'SIMULATION' | 'HISTORICAL' | 'BACKTEST';

export const BUNDLE_KIND = 'OBS001_BUNDLE' as const;
export const BUNDLE_SCHEMA = 'obs001.bundle/1' as const;

export type Ms = number;
export type HistScale = '45m' | '1D';

export interface Measure<T = number> {
  readonly v: T | null;
  readonly r: string | null;
}

export interface PivotRef {
  readonly kind: 'HIGH' | 'LOW';
  readonly price: number;
  readonly candidateOpen: Ms;
  readonly eventTime: Ms;
  readonly availableAt: Ms;
}

export interface LevelObs {
  readonly id: string | null;
  readonly kind: 'PIVOT_HIGH' | 'PIVOT_LOW' | 'DAY_HIGH' | 'DAY_LOW';
  readonly price: number | null;
  readonly reason?: string;
  readonly origin?: Ms;
  readonly eventTime?: Ms;
  readonly availableAt?: Ms;
  readonly dist?: Measure;
}

export interface FibLevel {
  readonly ratio: number;
  readonly price: number;
  readonly dist: Measure;
}

export interface FibObs {
  readonly version: number;
  readonly anchors: Measure<{ readonly P0: PivotRef; readonly P1: PivotRef }>;
  readonly u?: number;
  readonly r?: number;
  readonly retracements?: readonly FibLevel[];
  readonly projections?: readonly FibLevel[];
}

export interface PivotCheck {
  readonly candidateOpen: Ms;
  readonly eventTime: Ms;
  readonly availableAt: Ms;
  readonly high: string;
  readonly low: string;
}

/** Record immutabile alla chiusura di una barra: usa solo barre terminate entro `end`. */
export interface ObservationRecord {
  readonly id: string;
  readonly open: Ms;
  readonly end: Ms;
  readonly availableAt: Ms;
  readonly status: 'COMPLETE' | 'INCOMPLETE';
  readonly inputRef: { readonly minutes: readonly [Ms, Ms]; readonly valid: number; readonly missing: number; readonly invalid: number };
  readonly segment: { readonly id: number; readonly bars: number } | null;
  readonly C: number | null;
  readonly vol: { readonly tr: Measure; readonly A: Measure; readonly AoverC: Measure };
  readonly avg: {
    readonly sma20: Measure;
    readonly sma50: Measure;
    readonly dist: Measure;
    readonly slope: Measure;
    readonly pos: Measure;
    readonly cross: Measure<'UP' | 'DOWN' | 'NONE'>;
  };
  readonly volu: {
    readonly base: number | null;
    readonly quote: number | null;
    readonly trades: number | null;
    readonly takerBase: number | null;
    readonly takerQuote: number | null;
    readonly median: Measure;
    readonly ratio: Measure;
  };
  readonly piv: {
    readonly check: Measure<PivotCheck>;
    readonly structure: Measure<'UP' | 'DOWN' | 'MIXED'>;
    readonly highs: readonly PivotRef[];
    readonly lows: readonly PivotRef[];
  };
  readonly fib: FibObs;
  readonly lvl: readonly LevelObs[];
  readonly crossings: readonly { readonly levelId: string; readonly levelKind: string; readonly price: number; readonly direction: 'UP' | 'DOWN' }[];
}

export interface StudyEvent {
  readonly id: string;
  readonly scale: HistScale;
  readonly type: string;
  readonly eventTime: Ms;
  readonly availableAt: Ms;
  readonly kind?: string;
  readonly [key: string]: unknown;
}

export interface ColumnarBars {
  readonly open: readonly Ms[];
  readonly status: readonly ('COMPLETE' | 'INCOMPLETE')[];
  readonly o: readonly (number | null)[];
  readonly h: readonly (number | null)[];
  readonly l: readonly (number | null)[];
  readonly c: readonly (number | null)[];
  readonly v: readonly (number | null)[];
  readonly q: readonly (number | null)[];
  readonly trades: readonly (number | null)[];
  readonly valid: readonly number[];
  readonly missing: readonly number[];
  readonly invalid: readonly number[];
}

export type StructureState = 'UP' | 'DOWN' | 'MIXED' | 'UNAVAILABLE';
export type DailyRelation = 'CONCORDANT' | 'OPPOSITE' | 'MIXED' | 'UNAVAILABLE' | 'NOT_APPLICABLE';

/** Riga di studio: contiene esiti a posteriori. Si legge solo nelle viste retrospettive. */
export interface StudyRow {
  readonly t: Ms;
  readonly horizonEnd: Ms;
  readonly month: string;
  readonly p: number | null;
  readonly a: number | null;
  readonly originStatus: string;
  readonly aStatus: string;
  readonly futureStatus: 'COMPLETE' | 'INCOMPLETE';
  readonly futureFlags: readonly string[];
  readonly futureMinutesExpected: number;
  readonly futureMinutesInRange: number;
  readonly futureMinutesValid: number;
  readonly futureMinutesContiguous: number;
  readonly close24h: number | null;
  readonly maxHigh: number | null;
  readonly minLow: number | null;
  readonly final: number | null;
  readonly up: number | null;
  readonly down: number | null;
  readonly s45: StructureState;
  readonly s1d: StructureState;
  readonly dailyRelation: DailyRelation;
}

export interface Stats {
  readonly n: number;
  readonly mean: number | null;
  readonly min: number | null;
  readonly max: number | null;
  readonly p10: number | null;
  readonly p25: number | null;
  readonly p50: number | null;
  readonly p75: number | null;
  readonly p90: number | null;
}

export interface GroupSummary {
  readonly n: number;
  readonly originValid: number;
  readonly aValid: number;
  readonly futureComplete: number;
  readonly measuresAvailable: number;
  readonly measuresMissing: number;
  readonly missingFlags: Readonly<Record<string, number>>;
  readonly stats?: Readonly<Record<'final' | 'up' | 'down', Stats>>;
}

export interface PeriodTables {
  readonly coverage: GroupSummary & {
    readonly rightCensoredOrigins: number;
    readonly availabilityAtOrigin: Readonly<Record<HistScale, Readonly<Record<string, { available: number; missing: number; reasons: Record<string, number> }>>>>;
  };
  readonly s45: Readonly<Record<StructureState, GroupSummary>>;
  readonly relation: Readonly<Record<'UP' | 'DOWN', Readonly<Record<'CONCORDANT' | 'OPPOSITE' | 'MIXED' | 'UNAVAILABLE', GroupSummary>>>>;
  readonly matrix: Readonly<Record<StructureState, Readonly<Record<StructureState, number>>>>;
}

export interface StudySummary {
  readonly periods: readonly string[];
  readonly tables: Readonly<Record<string, PeriodTables>>;
  readonly examples: Readonly<Record<'UP' | 'DOWN', { readonly contrary: Ms | null; readonly first: Ms | null }>>;
  readonly checks: { readonly origins: number; readonly rightCensored: number; readonly partitionsReconciled: boolean };
}

export interface StudyBundle {
  readonly kind: typeof BUNDLE_KIND;
  readonly schema: typeof BUNDLE_SCHEMA;
  readonly engineVersion: string;
  readonly conventions: { readonly id: string; readonly hash: string; readonly config: Record<string, unknown> };
  readonly timeUnit: string;
  readonly source: {
    readonly name: string;
    readonly attribution: string;
    readonly symbol: string;
    readonly segment: string;
    readonly contractType: string;
    readonly priceType: string;
    readonly interval: string;
    readonly termsUrl: string;
    readonly note: string;
  };
  readonly periods: { readonly inputStart: Ms; readonly studyStart: Ms; readonly end: Ms };
  /** Identità del run: input, convenzioni e motore. Commit e orari stanno nel manifest locale del run. */
  readonly run: { readonly runId: string; readonly inputHash: string | null; readonly engineVersion: string; readonly synthetic?: boolean };
  readonly inputQuality: {
    readonly totals: Readonly<Record<'input' | 'initialization' | 'study', { expected: number; valid: number; missing: number; invalid: number }>>;
    readonly files: readonly { readonly month: string; readonly file: string; readonly sha256: string; readonly rows: number; readonly coverage: { expected: number; valid: number; missing: number; invalid: number } }[];
  };
  readonly bars: Readonly<Record<HistScale, ColumnarBars>>;
  readonly observations: Readonly<Record<HistScale, readonly ObservationRecord[]>>;
  readonly events: Readonly<Record<HistScale, readonly StudyEvent[]>>;
  readonly origins: readonly Ms[];
  readonly retrospective: { readonly label: string; readonly rows: readonly StudyRow[]; readonly summary: StudySummary };
}

/** Candela preparata per il grafico storico. `gap`: barra INCOMPLETE resa come buco. */
export interface HistCandle {
  readonly openTime: Ms;
  readonly end: Ms;
  readonly open: number;
  readonly high: number;
  readonly low: number;
  readonly close: number;
  readonly volume: number;
  readonly gap: boolean;
  /** true per le barre oltre il cutoff, mostrate solo col seguito retrospettivo. */
  readonly retrospective: boolean;
}

export interface CausalSnapshot {
  readonly t: Ms;
  readonly m45: ObservationRecord;
  readonly d1: ObservationRecord | null;
  readonly events: Readonly<Record<HistScale, readonly StudyEvent[]>>;
}
