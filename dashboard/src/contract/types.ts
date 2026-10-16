/**
 * Contratto di presentazione UI-001.
 *
 * Indipendente dal rendering e dal provider: descrive ciò che la dashboard mostra,
 * non uno schema di database o un protocollo exchange. Tutti i tempi sono ISO 8601 UTC;
 * il fuso leggibile è scelto dall'interfaccia. Importi e quantità portano l'unità
 * esplicita e non sono arrotondati: l'arrotondamento avviene solo in visualizzazione.
 */
export const CONTRACT_VERSION = '1.0.0' as const;

/** ISO 8601 UTC, sempre con suffisso `Z`. */
export type IsoUtc = string;

export type MissingReason = 'NOT_APPLICABLE' | 'NOT_PROVIDED' | 'STALE' | 'UNAVAILABLE';

/** Valore noto oppure assente con motivo. Uno zero noto è `{ value: 0 }`, mai un'assenza. */
export type Maybe<T> =
  | { readonly value: T; readonly reason?: undefined; readonly note?: string }
  | { readonly value: null; readonly reason: MissingReason; readonly note?: string };

export type Currency = 'USDT';
export type Asset = 'BTC';

export interface Money {
  readonly amount: number;
  readonly currency: Currency;
}

export interface Quantity {
  readonly amount: number;
  readonly unit: Asset;
}

/** Prezzo in valuta di quotazione per unità di base (USDT per BTC). */
export interface Price {
  readonly amount: number;
  readonly quote: Currency;
  readonly base: Asset;
}

/** Ultimo valore noto con orario: distinto da un valore corrente. */
export interface LastKnown<T> {
  readonly value: T;
  readonly at: IsoUtc;
}

export type Freshness = 'CURRENT' | 'LAST_KNOWN';

/* ------------------------------------------------------------------ Context */

export type ExecutionMode = 'CALL_ONLY' | 'CALL_AND_EXECUTION';
export type BotStatus = 'RUNNING' | 'STOPPED';
export type FeedStatus = 'OK' | 'STALE' | 'DISCONNECTED';

export interface Context {
  readonly scenarioId: string;
  readonly checkpointId: string;
  readonly simulated: true;
  readonly environment: 'LOCAL_SIMULATION';
  readonly clock: { readonly now: IsoUtc; readonly kind: 'SIMULATED_DETERMINISTIC' };
  readonly instrument: {
    readonly symbol: 'BTCUSDT';
    readonly base: Asset;
    readonly quote: Currency;
    /** Etichetta illustrativa del prodotto: non è una scelta di prodotto approvata. */
    readonly productLabel: string;
  };
  readonly mode: ExecutionMode;
  readonly bot: { readonly status: BotStatus; readonly since: IsoUtc; readonly reason: string };
  readonly feed: {
    readonly status: FeedStatus;
    /** Sempre "feed simulato": nessuna sessione exchange esiste. */
    readonly label: 'feed simulato';
    readonly observedAt: IsoUtc;
    readonly receivedAt: IsoUtc;
    readonly freshness: Freshness;
    readonly explanation: string;
  };
  readonly market: {
    /** Prezzo corrente; null con STALE/UNAVAILABLE se il feed non è aggiornato. */
    readonly price: Maybe<Price>;
    readonly lastKnownPrice: LastKnown<Price>;
    readonly change24hPct: Maybe<number>;
  };
}

/* -------------------------------------------------------------------- Chart */

export type Timeframe = '45m' | '1D';

export interface Candle {
  /** Apertura della candela. */
  readonly openTime: IsoUtc;
  readonly open: number;
  readonly high: number;
  readonly low: number;
  readonly close: number;
  readonly volume: number;
  /** true per la candela giornaliera ancora in formazione. */
  readonly partial?: boolean;
}

export interface PreparedSeries {
  readonly id: string;
  readonly name: string;
  readonly unit: Currency;
  readonly kind: 'MOVING_AVERAGE';
  /** Parametri mostrati come esempio: non sono decisioni operative. */
  readonly params: Readonly<Record<string, number>>;
  readonly illustrative: true;
  readonly points: readonly { readonly time: IsoUtc; readonly value: number }[];
}

export type LevelOrigin = 'OBSERVATION' | 'ORIGINAL_PLAN' | 'CURRENT_PLAN' | 'POSITION';
export type LevelKind = 'ENTRY' | 'ENTRY_ZONE_LOW' | 'ENTRY_ZONE_HIGH' | 'STOP' | 'TARGET' | 'RESISTANCE' | 'SUPPORT' | 'FIBONACCI';

export interface Level {
  readonly id: string;
  readonly kind: LevelKind;
  readonly origin: LevelOrigin;
  readonly label: string;
  readonly price: Price;
  readonly validFrom: IsoUtc;
  /** null = ancora valido. Un livello sostituito conserva la propria validità passata. */
  readonly validTo: IsoUtc | null;
  readonly freshness: Freshness;
  readonly overlay: 'LEVELS' | 'FIBONACCI' | 'PLAN';
}

export interface TimeframeData {
  readonly timeframe: Timeframe;
  readonly candles: readonly Candle[];
  readonly volumeUnit: Asset;
  readonly series: readonly PreparedSeries[];
  readonly coverageNote: string;
}

export interface Chart {
  readonly timeframes: Readonly<Record<Timeframe, TimeframeData>>;
  readonly levels: readonly Level[];
  /** Frase di lettura guidata già preparata dal provider. */
  readonly reading: string;
}

/* -------------------------------------------------------------- Observation */

export type ObservationFamily = 'STRUCTURE' | 'LEVELS' | 'MOVING_AVERAGES' | 'VOLUME' | 'VOLATILITY' | 'FIBONACCI';
export type Tone = 'positive' | 'negative' | 'warning' | 'accent' | 'neutral';

export interface MiniSeries {
  readonly kind: 'LINE' | 'BARS';
  readonly series: readonly { readonly name: string; readonly tone: Tone; readonly values: readonly number[] }[];
  readonly referenceLevels: readonly { readonly value: number; readonly tone: Tone; readonly label?: string }[];
  /** Numero di barre finali evidenziate (solo BARS). */
  readonly highlightLast?: number;
}

export interface Observation {
  readonly id: string;
  readonly family: ObservationFamily;
  readonly title: string;
  readonly availability: 'AVAILABLE' | 'UNAVAILABLE';
  readonly timeframe: Timeframe;
  readonly observedAt: IsoUtc;
  readonly freshness: Freshness;
  readonly value: Maybe<{ readonly display: string; readonly caption: string }>;
  readonly badge: { readonly text: string; readonly tone: Tone };
  readonly observes: string;
  readonly means: string;
  readonly context: string;
  readonly explanation: string;
  readonly limits: string;
  readonly mini: MiniSeries;
}

/* -------------------------------------------------------------- Expectation */

export interface Expectation {
  readonly id: string;
  readonly direction: 'UP' | 'DOWN' | 'UNCERTAIN';
  readonly description: string;
  readonly alternatives: readonly string[];
  readonly contraindications: readonly string[];
  readonly updatedAt: IsoUtc;
}

/* --------------------------------------------------------------------- Call */

export type Direction = 'LONG' | 'SHORT';
export type CallStatus = 'PROPOSED' | 'AVAILABLE' | 'ACTIVE' | 'EXPIRED' | 'WITHDRAWN' | 'COMPLETED';

/** Una call non è un ordine né una posizione. */
export interface Call {
  readonly id: string;
  readonly displayId: string;
  readonly direction: Direction;
  readonly status: CallStatus;
  readonly createdAt: IsoUtc;
  readonly rationale: string;
  readonly explanation: string;
  readonly contraindication: { readonly title: string; readonly text: string };
  readonly conditions: readonly string[];
  readonly validity: { readonly from: IsoUtc; readonly entryUntil: IsoUtc; readonly note: string };
  readonly expectedDuration: string;
}

/* --------------------------------------------------------------------- Plan */

export interface PlanLevels {
  readonly setAt: IsoUtc;
  readonly entryZone: { readonly low: Price; readonly high: Price };
  readonly entryCondition: string;
  readonly stop: Price;
  readonly targets: readonly Price[];
  readonly invalidation: string;
}

export interface PlanChange {
  readonly at: IsoUtc;
  readonly field: 'STOP' | 'TARGET';
  readonly before: Price;
  readonly after: Price;
  readonly reason: string;
}

export interface Plan {
  readonly callId: string;
  readonly version: number;
  /** Immutabile: il piano come è stato emesso. */
  readonly original: PlanLevels;
  readonly current: PlanLevels;
  readonly changes: readonly PlanChange[];
  readonly expiresAt: IsoUtc;
  readonly reason: string;
}

/* -------------------------------------------------------------------- Order */

export type OrderPurpose = 'ENTRY' | 'PROTECTION' | 'EXIT';
export type OrderStatus = 'REQUESTED' | 'ACCEPTED' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'REJECTED';
export type Side = 'BUY' | 'SELL';

/** ACCEPTED non significa eseguito: la quantità eseguita deriva solo dai fill. */
export interface Order {
  readonly id: string;
  readonly callId: string | null;
  readonly purpose: OrderPurpose;
  readonly protectionKind: 'STOP' | 'TARGET' | null;
  readonly side: Side;
  /** Tipo illustrativo del simulatore. */
  readonly type: 'LIMIT' | 'STOP' | 'MARKET';
  readonly requestedQty: Quantity;
  readonly filledQty: Quantity;
  readonly status: OrderStatus;
  readonly limitPrice: Price | null;
  readonly triggerPrice: Price | null;
  readonly createdAt: IsoUtc;
  readonly updatedAt: IsoUtc;
  readonly origin: 'BOT' | 'OWNER';
  readonly rejection: { readonly code: string; readonly message: string } | null;
  /** Le protezioni durante disconnessione sono solo ultime note, non verificate. */
  readonly freshness: Freshness;
}

/* --------------------------------------------------------------------- Fill */

/** Unica fonte degli eseguiti simulati. */
export interface Fill {
  readonly id: string;
  readonly orderId: string;
  readonly at: IsoUtc;
  readonly side: Side;
  readonly qty: Quantity;
  readonly price: Price;
  readonly fee: Money;
}

/* ----------------------------------------------------------------- Position */

export interface Position {
  readonly id: string;
  readonly side: Direction;
  readonly qty: Quantity;
  readonly avgEntryPrice: Price;
  readonly openedAt: IsoUtc;
  readonly valuation: Maybe<{ readonly price: Price; readonly at: IsoUtc }>;
  readonly lastKnownValuation: LastKnown<Price>;
  readonly protections: readonly {
    readonly orderId: string;
    readonly kind: 'STOP' | 'TARGET';
    readonly price: Price;
    readonly qty: Quantity;
    readonly freshness: Freshness;
  }[];
  readonly management: 'BOT' | 'MANUAL';
}

/* ------------------------------------------------------------------ Account */

export interface Account {
  readonly currency: Currency;
  readonly initialBalance: Money;
  /** Saldo contabile simulato: iniziale + realizzato lordo − costi addebitati. */
  readonly balance: Money;
  /** Saldo + non realizzato lordo; null se la valutazione non è corrente. */
  readonly equity: Maybe<Money>;
  readonly lastKnownEquity: LastKnown<Money> | null;
  readonly realizedGross: Money;
  readonly feesCharged: Money;
  readonly realizedNet: Money;
  /** Commissioni addebitate dagli eseguiti d'ingresso. */
  readonly entryFeesCharged: Money;
  /** Scomposizione del realizzato per eseguito d'uscita (contribuisce ai totali). */
  readonly realizedLegs: readonly {
    readonly fillId: string;
    readonly at: IsoUtc;
    readonly direction: Direction;
    readonly qty: Quantity;
    readonly entryPrice: Price;
    readonly exitPrice: Price;
    readonly gross: Money;
    readonly exitFee: Money;
  }[];
  readonly unrealizedGross: Maybe<Money>;
  readonly lastKnownUnrealizedGross: LastKnown<Money> | null;
  readonly exitCostsIncluded: false;
  readonly margin: Maybe<Money>;
  readonly available: Maybe<Money>;
  readonly funding: Maybe<Money>;
}

/* ------------------------------------------------------------------ History */

export type HistoryType =
  | 'EXPECTATION'
  | 'CALL'
  | 'ORDER'
  | 'FILL'
  | 'PLAN_CHANGE'
  | 'PROTECTION'
  | 'MODE'
  | 'MANAGEMENT'
  | 'BOT'
  | 'FEED'
  | 'SIMULATION';

export interface HistoryEvent {
  readonly id: string;
  readonly type: HistoryType;
  readonly at: IsoUtc;
  readonly links: {
    readonly callId?: string;
    readonly orderId?: string;
    readonly positionId?: string;
    readonly planVersion?: number;
  };
  readonly title: string;
  readonly text: string;
  readonly change: { readonly field: string; readonly before: string; readonly after: string } | null;
  /** Nessun invio reale: al più una notifica simulata. */
  readonly notification: { readonly kind: 'SIMULATED' | 'NONE'; readonly text: string };
  readonly origin: 'BOT' | 'OWNER' | 'SIMULATION';
}

/* ---------------------------------------------------------------- Snapshot */

export interface ActionState {
  readonly enabled: boolean;
  readonly reason: string | null;
}

export type ActionId =
  | 'START'
  | 'STOP_TOTAL'
  | 'MODE_CALL_ONLY'
  | 'MODE_CALL_AND_EXECUTION'
  | 'TAKE_MANUAL'
  | 'RESUME_AUTOMATIC'
  | 'PARTIAL_EXIT'
  | 'CLOSE_POSITION'
  | 'CANCEL_ENTRY_ORDER'
  | 'CANCEL_EXIT_REQUEST';

export interface Snapshot {
  readonly contractVersion: typeof CONTRACT_VERSION;
  readonly context: Context;
  readonly chart: Chart;
  readonly observations: readonly Observation[];
  readonly expectation: Expectation | null;
  readonly call: Call | null;
  readonly plan: Plan | null;
  readonly orders: readonly Order[];
  readonly fills: readonly Fill[];
  readonly position: Position | null;
  readonly account: Account;
  readonly history: readonly HistoryEvent[];
  readonly actions: Readonly<Record<ActionId, ActionState>>;
}
