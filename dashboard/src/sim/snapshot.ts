/**
 * Dallo stato simulato allo snapshot del contratto di presentazione.
 * Qui si preparano candele, serie e livelli già pronti per la visualizzazione:
 * nessuna analisi, solo selezione temporale e aggregazione delle candele fittizie.
 */
import type {
  Account,
  Candle,
  Chart,
  Level,
  LevelKind,
  Maybe,
  MiniSeries,
  Money,
  Observation,
  Order,
  Position,
  PreparedSeries,
  Snapshot,
  TimeframeData,
} from '../contract/types';
import { CONTRACT_VERSION } from '../contract/types';
import { formatPrice } from '../lib/numbers';
import { actionStates } from './commands';
import type { MiniSpec, ObservationSetDef, ScenarioDef, ScenarioMarket, SimState } from './engine';
import { INITIAL_BALANCE, accountingOf, candleCloseTime, isActiveProtection, priceAt, toIso, usdt } from './engine';
import { DAILY_START, DAY_MS, INTRADAY_START, INTRADAY_STEP_MS } from './fixtures/market';

const money = (amount: number): Money => ({ amount, currency: 'USDT' });
const known = <T>(value: T): Maybe<T> => ({ value });
const missing = <T>(reason: 'NOT_APPLICABLE' | 'NOT_PROVIDED' | 'STALE' | 'UNAVAILABLE', note?: string): Maybe<T> => ({ value: null, reason, note });

const PRODUCT_LABEL = 'Contratto lineare · esempio simulato';

/* ---------------------------------------------------------------- Candles */

function intradayCandles(market: ScenarioMarket, until: number): Candle[] {
  const out: Candle[] = [];
  market.intraday.forEach(([open, high, low, close, volume], k) => {
    if (candleCloseTime(k) <= until) out.push({ openTime: toIso(INTRADAY_START + k * INTRADAY_STEP_MS), open, high, low, close, volume });
  });
  return out;
}

function aggregate(day: number, parts: Candle[], before?: ScenarioMarket['oct14BeforeIntraday'], partial = false): Candle {
  const highs = parts.map((c) => c.high);
  const lows = parts.map((c) => c.low);
  const volume = parts.reduce((sum, c) => sum + c.volume, before?.volume ?? 0);
  return {
    openTime: toIso(day),
    open: before?.open ?? parts[0].open,
    high: Math.max(...highs, before?.high ?? -Infinity),
    low: Math.min(...lows, before?.low ?? Infinity),
    close: parts[parts.length - 1].close,
    volume: Math.round(volume * 10) / 10,
    ...(partial ? { partial: true } : {}),
  };
}

/** Giornaliero: 38 giorni sintetici + 14 ott (sintetico prima del segmento intraday) + 15 ott in formazione. */
function dailyCandles(market: ScenarioMarket, until: number): Candle[] {
  const synthetic: Candle[] = market.dailySynthetic.map(([open, high, low, close, volume], i) => ({
    openTime: toIso(DAILY_START + i * DAY_MS),
    open,
    high,
    low,
    close,
    volume,
  }));
  const intraday = intradayCandles(market, until);
  const oct14 = DAILY_START + market.dailySynthetic.length * DAY_MS;
  const oct15 = oct14 + DAY_MS;
  const day14 = intraday.filter((c) => Date.parse(c.openTime) < oct15);
  const day15 = intraday.filter((c) => Date.parse(c.openTime) >= oct15);
  const out = [...synthetic];
  if (day14.length) out.push(aggregate(oct14, day14, market.oct14BeforeIntraday));
  if (day15.length) out.push(aggregate(oct15, day15, undefined, true));
  return out;
}

function series(id: string, name: string, period: number, candles: Candle[], values: readonly number[], offset: number): PreparedSeries {
  return {
    id,
    name,
    unit: 'USDT',
    kind: 'MOVING_AVERAGE',
    params: { period },
    illustrative: true,
    points: candles.map((c, i) => ({ time: c.openTime, value: values[i + offset] })),
  };
}

/* ------------------------------------------------------------ Observation */

function activeSet(scn: ScenarioDef, state: SimState): ObservationSetDef | null {
  return scn.observationSets.find((o) => o.id === state.observationSetId) ?? null;
}

function mini(spec: MiniSpec, set: ObservationSetDef, market: ScenarioMarket): MiniSeries {
  const upTo = intradayCandles(market, set.observedAt);
  const closes = upTo.slice(-12).map((c) => c.close);
  const lastIndex = upTo.length - 1;
  switch (spec.kind) {
    case 'CLOSES':
      return { kind: 'LINE', series: [{ name: 'Prezzo', tone: 'positive', values: closes }], referenceLevels: [] };
    case 'CLOSES_WITH_LEVELS':
      return {
        kind: 'LINE',
        series: [{ name: 'Prezzo', tone: 'warning', values: closes }],
        referenceLevels: spec.levels.map((value) => ({ value, tone: 'warning' as const })),
      };
    case 'MOVING_AVERAGES': {
      const from = Math.max(0, lastIndex - 11);
      return {
        kind: 'LINE',
        series: [
          { name: 'Media veloce', tone: 'positive', values: market.maFast45.slice(from, lastIndex + 1) },
          { name: 'Media lenta', tone: 'warning', values: market.maSlow45.slice(from, lastIndex + 1) },
        ],
        referenceLevels: [],
      };
    }
    case 'VOLUMES':
      return {
        kind: 'BARS',
        series: [{ name: 'Volume', tone: 'neutral', values: upTo.slice(-22).map((c) => c.volume) }],
        referenceLevels: [],
        highlightLast: spec.highlightLast,
      };
    case 'STATIC_LINE':
      return { kind: 'LINE', series: [{ name: 'Escursione', tone: 'warning', values: spec.values }], referenceLevels: [] };
    case 'CLOSES_WITH_FIB':
      return {
        kind: 'LINE',
        series: [{ name: 'Prezzo', tone: 'accent', values: closes }],
        referenceLevels: set.fibonacci.map((f) => ({ value: f.price, tone: 'accent' as const, label: f.ratio === '61,8%' ? f.ratio : undefined })),
      };
  }
}

function observations(scn: ScenarioDef, state: SimState): Observation[] {
  const set = activeSet(scn, state);
  if (!set) return [];
  const freshness = state.feed.status === 'OK' ? 'CURRENT' : 'LAST_KNOWN';
  return set.observations.map((o) => ({
    id: o.id,
    family: o.family,
    title: o.title,
    availability: 'AVAILABLE',
    timeframe: '45m',
    observedAt: toIso(set.observedAt),
    freshness,
    value: known(o.value),
    badge: o.badge,
    observes: o.observes,
    means: o.means,
    context: o.context,
    explanation: o.explanation,
    limits: o.limits,
    mini: mini(o.mini, set, scn.market),
  }));
}

/* ------------------------------------------------------------------ Levels */

function levels(scn: ScenarioDef, state: SimState, positionOpen: boolean, avgEntry: number | null): Level[] {
  const out: Level[] = [];
  const freshness = state.feed.status === 'OK' ? 'CURRENT' : 'LAST_KNOWN';
  const set = activeSet(scn, state);
  if (set) {
    for (const l of set.levels) {
      out.push({
        id: `${set.id}-${l.id}`,
        kind: l.kind,
        origin: 'OBSERVATION',
        label: l.label,
        price: usdt(l.price),
        validFrom: toIso(set.observedAt),
        validTo: null,
        freshness,
        overlay: 'LEVELS',
      });
    }
    for (const f of set.fibonacci) {
      out.push({
        id: `${set.id}-fib-${f.ratio}`,
        kind: 'FIBONACCI',
        origin: 'OBSERVATION',
        label: `FIB ${f.ratio} · ${formatPrice(f.price)}`,
        price: usdt(f.price),
        validFrom: toIso(set.observedAt),
        validTo: null,
        freshness,
        overlay: 'FIBONACCI',
      });
    }
  }

  const plan = state.plan;
  const call = state.call;
  if (!plan || !call) return out;
  const planOpen = positionOpen || call.status === 'PROPOSED' || call.status === 'AVAILABLE';
  const add = (id: string, kind: LevelKind, origin: Level['origin'], price: number, label: string, validFrom: string, validTo: string | null) =>
    out.push({ id, kind, origin, label, price: usdt(price), validFrom, validTo, freshness, overlay: 'PLAN' });

  // Piano originario: sempre presente nei dati; non più valido se sostituito.
  const originalStopValidTo = plan.changes.find((c) => c.field === 'STOP')?.at ?? (planOpen ? null : toIso(state.clock));
  add('plan-original-stop', 'STOP', 'ORIGINAL_PLAN', plan.original.stop.amount, `STOP ORIGINALE · ${formatPrice(plan.original.stop.amount)}`, plan.original.setAt, originalStopValidTo);

  if (!planOpen) return out;
  if (positionOpen && avgEntry !== null) {
    add('position-entry', 'ENTRY', 'POSITION', avgEntry, `INGRESSO · ${formatPrice(avgEntry)}`, plan.current.setAt, null);
  } else {
    const pendingLimit = state.orders.find((o) => o.purpose === 'ENTRY' && o.status === 'ACCEPTED')?.limitPrice?.amount;
    const zone = plan.current.entryZone;
    const mid = pendingLimit ?? (zone.low.amount + zone.high.amount) / 2;
    add(
      'plan-entry',
      'ENTRY',
      'CURRENT_PLAN',
      mid,
      pendingLimit !== undefined ? `ORDINE INGRESSO · ${formatPrice(mid)}` : `FASCIA INGRESSO · ${formatPrice(zone.low.amount)}–${formatPrice(zone.high.amount)}`,
      plan.current.setAt,
      null,
    );
  }
  add('plan-stop', 'STOP', 'CURRENT_PLAN', plan.current.stop.amount, `STOP · ${formatPrice(plan.current.stop.amount)}`, plan.current.setAt, null);
  plan.current.targets.forEach((t, i) =>
    add(`plan-target-${i}`, 'TARGET', 'CURRENT_PLAN', t.amount, `TARGET · ${formatPrice(t.amount)}`, plan.current.setAt, null),
  );
  return out;
}

function reading(scn: ScenarioDef, state: SimState, positionOpen: boolean): string {
  const base = activeSet(scn, state)?.reading ?? 'Nessuna analisi disponibile in questo momento della simulazione.';
  const plan = state.plan;
  if (positionOpen && plan) {
    const change = plan.changes[plan.changes.length - 1];
    return `${base} Le linee tratteggiate mostrano i livelli attuali della posizione${
      change ? `; lo stop è passato da ${formatPrice(change.before.amount)} a ${formatPrice(change.after.amount)} (vedi cronologia).` : '.'
    }`;
  }
  if (plan && state.call && (state.call.status === 'PROPOSED' || state.call.status === 'AVAILABLE')) {
    return `${base} Le linee tratteggiate mostrano il piano della call: nessuna posizione aperta.`;
  }
  return base;
}

/* ---------------------------------------------------------------- Snapshot */

export function buildSnapshot(scn: ScenarioDef, state: SimState): Snapshot {
  const market = scn.market;
  const now = state.clock;
  const feedOk = state.feed.status === 'OK';
  const staleReason = state.feed.status === 'DISCONNECTED' ? 'UNAVAILABLE' : 'STALE';
  const observedAt = state.feed.observedAt;
  const lastKnownPrice = priceAt(market, observedAt) ?? market.intraday[0][0];
  const currentPrice = feedOk ? priceAt(market, now) : null;

  const acc = accountingOf(state, { price: lastKnownPrice, at: observedAt, current: feedOk });
  const posAcc = acc.position;

  const candles45 = intradayCandles(market, observedAt);
  const candles1D = dailyCandles(market, observedAt);
  const tf45: TimeframeData = {
    timeframe: '45m',
    candles: candles45,
    volumeUnit: 'BTC',
    series: [
      series('ma-fast-45m', 'EMA 20', 20, candles45, market.maFast45, 0),
      series('ma-slow-45m', 'EMA 50', 50, candles45, market.maSlow45, 0),
    ],
    coverageNote: 'Segmento intraday fittizio dal 14 ott 2026.',
  };
  const tf1D: TimeframeData = {
    timeframe: '1D',
    candles: candles1D,
    volumeUnit: 'BTC',
    series: [
      series('ma-fast-1d', 'EMA 20', 20, candles1D, market.maFast1D, 0),
      series('ma-slow-1d', 'EMA 50', 50, candles1D, market.maSlow1D, 0),
    ],
    coverageNote: 'Prima del 14 ott: contesto giornaliero sintetico, senza dati intraday. Ultima candela in formazione.',
  };
  const chart: Chart = {
    timeframes: { '45m': tf45, '1D': tf1D },
    levels: levels(scn, state, posAcc !== null, posAcc?.avgEntryPrice ?? null),
    reading: reading(scn, state, posAcc !== null),
  };

  const price24hAgo = priceAt(market, now - DAY_MS);
  const change24hPct: Maybe<number> =
    feedOk && currentPrice !== null && price24hAgo !== null
      ? known(((currentPrice - price24hAgo) / price24hAgo) * 100)
      : missing(feedOk ? 'NOT_PROVIDED' : staleReason);

  const orders: Order[] = state.orders.map((o) =>
    !feedOk && (o.status === 'ACCEPTED' || o.status === 'REQUESTED') ? { ...o, freshness: 'LAST_KNOWN' } : o,
  );

  const position: Position | null = posAcc
    ? {
        id: `pos-${posAcc.openingFillId}`,
        side: posAcc.side,
        qty: { amount: posAcc.qty, unit: 'BTC' },
        avgEntryPrice: usdt(posAcc.avgEntryPrice),
        openedAt: toIso(posAcc.openedAt),
        valuation: feedOk ? known({ price: usdt(lastKnownPrice), at: toIso(now) }) : missing(staleReason, 'Valutazione non corrente'),
        lastKnownValuation: { value: usdt(lastKnownPrice), at: toIso(observedAt) },
        protections: orders.filter(isActiveProtection).map((o) => ({
          orderId: o.id,
          kind: o.protectionKind ?? 'STOP',
          price: (o.protectionKind === 'TARGET' ? o.limitPrice : o.triggerPrice) ?? usdt(0),
          qty: o.requestedQty,
          freshness: o.freshness,
        })),
        management: state.management,
      }
    : null;

  const account: Account = {
    currency: 'USDT',
    initialBalance: money(INITIAL_BALANCE),
    balance: money(acc.balance),
    equity: acc.equity === null ? missing(staleReason, 'Equity non corrente senza valutazione aggiornata') : known(money(acc.equity)),
    lastKnownEquity: acc.lastKnownEquity ? { value: money(acc.lastKnownEquity.value), at: toIso(acc.lastKnownEquity.at) } : null,
    realizedGross: money(acc.realizedGross),
    feesCharged: money(acc.fees),
    realizedNet: money(acc.realizedNet),
    entryFeesCharged: money(acc.entryFees),
    realizedLegs: acc.closedLegs.map((l) => ({
      fillId: l.fillId,
      at: toIso(l.at),
      direction: l.direction,
      qty: { amount: l.qty, unit: 'BTC' as const },
      entryPrice: usdt(l.entryPrice),
      exitPrice: usdt(l.exitPrice),
      gross: money(l.gross),
      exitFee: money(l.exitFee),
    })),
    unrealizedGross: acc.unrealizedGross === null ? missing(staleReason, 'P&L attuale non disponibile') : known(money(acc.unrealizedGross)),
    lastKnownUnrealizedGross: acc.lastKnownUnrealizedGross
      ? { value: money(acc.lastKnownUnrealizedGross.value), at: toIso(acc.lastKnownUnrealizedGross.at) }
      : null,
    exitCostsIncluded: false,
    margin: missing('NOT_PROVIDED', 'Margine non simulato in questo esempio'),
    available: missing('NOT_PROVIDED', 'Disponibile non simulato in questo esempio'),
    funding: missing('NOT_APPLICABLE', 'Funding non applicato nell’esempio breve'),
  };

  const feedExplanation =
    state.feed.status === 'OK'
      ? 'Feed simulato aggiornato: valori correnti dello scenario locale.'
      : state.feed.status === 'STALE'
        ? 'Dati non aggiornati: sono mostrati gli ultimi valori noti con il loro orario. Nuovi ingressi bloccati.'
        : 'Feed simulato disconnesso: prezzo e P&L correnti non disponibili; protezioni solo ultime note. Nuovi ingressi bloccati.';

  return {
    contractVersion: CONTRACT_VERSION,
    context: {
      scenarioId: scn.id,
      checkpointId: state.checkpointId,
      simulated: true,
      environment: 'LOCAL_SIMULATION',
      clock: { now: toIso(now), kind: 'SIMULATED_DETERMINISTIC' },
      instrument: { symbol: 'BTCUSDT', base: 'BTC', quote: 'USDT', productLabel: PRODUCT_LABEL },
      mode: state.mode,
      bot: { status: state.bot.status, since: toIso(state.bot.since), reason: state.bot.reason },
      feed: {
        status: state.feed.status,
        label: 'feed simulato',
        observedAt: toIso(observedAt),
        receivedAt: toIso(observedAt),
        freshness: feedOk ? 'CURRENT' : 'LAST_KNOWN',
        explanation: feedExplanation,
      },
      market: {
        price: currentPrice === null ? missing(staleReason, 'Prezzo corrente non disponibile') : known(usdt(currentPrice)),
        lastKnownPrice: { value: usdt(lastKnownPrice), at: toIso(observedAt) },
        change24hPct,
      },
    },
    chart,
    observations: observations(scn, state),
    expectation: state.expectation,
    call: state.call,
    plan: state.plan,
    orders,
    fills: state.fills,
    position,
    account,
    history: state.history,
    actions: actionStates(state),
  };
}
