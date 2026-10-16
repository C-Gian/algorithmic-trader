/**
 * Motore degli eventi della simulazione locale.
 *
 * Lo stato si ottiene applicando in ordine eventi predeterminati (scenario e checkpoint)
 * ed eventuali comandi dell'Owner. Nessuna decisione deriva dai prezzi: gli eventi del bot
 * sono scritti nello scenario, i comandi dell'Owner hanno esiti fissati dalle convenzioni
 * di questa UI simulata (non da un protocollo exchange).
 */
import type {
  BotStatus,
  Call,
  Direction,
  ExecutionMode,
  Expectation,
  FeedStatus,
  Fill,
  HistoryEvent,
  HistoryType,
  Order,
  Plan,
  PlanLevels,
  Price,
  Quantity,
  Side,
} from '../contract/types';
import { clean, computeAccounting } from './accounting';
import { formatBtc, formatNumber, formatPrice, formatSigned } from '../lib/numbers';
import type { Ohlcv } from './fixtures/market';
import { INTRADAY_START, INTRADAY_STEP_MS } from './fixtures/market';

/** Commissione di fixture: 0,1% del nozionale. Non è una tariffa exchange. */
export const FIXTURE_FEE_RATE = 0.001;
/** Quantità predeterminata dell'uscita parziale nello scenario. */
export const PARTIAL_EXIT_QTY = 0.004;
export const INITIAL_BALANCE = 10000;
const QTY_EPSILON = 1e-9;

export const toIso = (ms: number): string => new Date(ms).toISOString().replace('.000Z', 'Z');
export const utc = (iso: string): number => Date.parse(iso);

export const usdt = (amount: number): Price => ({ amount, quote: 'USDT', base: 'BTC' });
export const btc = (amount: number): Quantity => ({ amount, unit: 'BTC' });

/* --------------------------------------------------------------- Scenario */

export type MiniSpec =
  | { readonly kind: 'CLOSES' }
  | { readonly kind: 'CLOSES_WITH_LEVELS'; readonly levels: readonly number[] }
  | { readonly kind: 'MOVING_AVERAGES' }
  | { readonly kind: 'VOLUMES'; readonly highlightLast: number }
  | { readonly kind: 'STATIC_LINE'; readonly values: readonly number[] }
  | { readonly kind: 'CLOSES_WITH_FIB' };

export interface ObservationDef {
  readonly id: string;
  readonly family: import('../contract/types').ObservationFamily;
  readonly title: string;
  readonly value: { readonly display: string; readonly caption: string };
  readonly badge: { readonly text: string; readonly tone: import('../contract/types').Tone };
  readonly observes: string;
  readonly means: string;
  readonly context: string;
  readonly explanation: string;
  readonly limits: string;
  readonly mini: MiniSpec;
}

export interface ObservationSetDef {
  readonly id: string;
  readonly observedAt: number;
  readonly observations: readonly ObservationDef[];
  readonly levels: readonly { readonly id: string; readonly kind: 'SUPPORT' | 'RESISTANCE'; readonly price: number; readonly label: string }[];
  readonly fibonacci: readonly { readonly ratio: string; readonly price: number }[];
  readonly reading: string;
}

export interface ScenarioMarket {
  readonly intraday: readonly Ohlcv[];
  readonly dailySynthetic: readonly Ohlcv[];
  readonly oct14BeforeIntraday: { readonly open: number; readonly high: number; readonly low: number; readonly volume: number };
  readonly maFast45: readonly number[];
  readonly maSlow45: readonly number[];
  readonly maFast1D: readonly number[];
  readonly maSlow1D: readonly number[];
}

export interface CheckpointDef {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly at: number;
  readonly initialMode: ExecutionMode;
  readonly exclude?: readonly string[];
  readonly extra?: readonly SimEvent[];
}

export interface ScenarioDef {
  readonly id: string;
  readonly label: string;
  readonly direction: Direction;
  readonly startsAt: number;
  readonly market: ScenarioMarket;
  readonly observationSets: readonly ObservationSetDef[];
  readonly events: readonly SimEvent[];
  readonly checkpoints: readonly CheckpointDef[];
}

/* ------------------------------------------------------------------ Events */

type Origin = 'BOT' | 'OWNER' | 'SIMULATION';

export type SimEvent =
  | {
      readonly kind: 'OBSERVATIONS';
      readonly id: string;
      readonly at: number;
      readonly setId: string;
      readonly expectation: Expectation;
      readonly summary: string;
    }
  | {
      readonly kind: 'CALL_CREATED';
      readonly id: string;
      readonly at: number;
      readonly call: Call;
      readonly plan: { readonly original: PlanLevels; readonly expiresAt: number; readonly reason: string };
    }
  | {
      readonly kind: 'ORDER_CREATED';
      readonly id: string;
      readonly at: number;
      readonly origin: Origin;
      readonly order: {
        readonly id: string;
        readonly purpose: Order['purpose'];
        readonly side: Side;
        readonly type: Order['type'];
        readonly qty: number;
        readonly limitPrice?: number;
      };
      readonly outcome: 'ACCEPTED' | 'REJECTED' | 'REQUESTED';
      readonly rejection?: { readonly code: string; readonly message: string };
    }
  | { readonly kind: 'ORDER_CANCELLED'; readonly id: string; readonly at: number; readonly origin: Origin; readonly orderId: string; readonly reason: string }
  | { readonly kind: 'FILL'; readonly id: string; readonly at: number; readonly orderId: string; readonly price: number }
  | {
      readonly kind: 'PROTECTIONS_PLACED';
      readonly id: string;
      readonly at: number;
      readonly stopOrderId: string;
      readonly targetOrderId: string;
    }
  | { readonly kind: 'PLAN_CHANGE'; readonly id: string; readonly at: number; readonly field: 'STOP'; readonly after: number; readonly reason: string }
  | { readonly kind: 'MODE'; readonly id: string; readonly at: number; readonly origin: Origin; readonly mode: ExecutionMode }
  | { readonly kind: 'BOT'; readonly id: string; readonly at: number; readonly origin: Origin; readonly status: BotStatus; readonly reason: string }
  | { readonly kind: 'FEED'; readonly id: string; readonly at: number; readonly status: FeedStatus; readonly observedAt: number };

/* ------------------------------------------------------------------- State */

export interface SimState {
  readonly scenarioId: string;
  readonly checkpointId: string;
  readonly clock: number;
  readonly mode: ExecutionMode;
  readonly bot: { readonly status: BotStatus; readonly since: number; readonly reason: string };
  readonly management: 'BOT' | 'MANUAL';
  readonly feed: { readonly status: FeedStatus; readonly observedAt: number };
  readonly observationSetId: string | null;
  readonly expectation: Expectation | null;
  readonly call: Call | null;
  readonly plan: Plan | null;
  readonly orders: readonly Order[];
  readonly fills: readonly Fill[];
  readonly history: readonly HistoryEvent[];
  readonly processedRequests: readonly string[];
  readonly seq: number;
}

type Draft = { -readonly [K in keyof SimState]: SimState[K] };

export function initialState(scn: ScenarioDef, cp: CheckpointDef): SimState {
  return {
    scenarioId: scn.id,
    checkpointId: cp.id,
    clock: scn.startsAt,
    mode: cp.initialMode,
    bot: { status: 'RUNNING', since: scn.startsAt, reason: 'Avvio della simulazione' },
    management: 'BOT',
    feed: { status: 'OK', observedAt: scn.startsAt },
    observationSetId: null,
    expectation: null,
    call: null,
    plan: null,
    orders: [],
    fills: [],
    history: [],
    processedRequests: [],
    seq: 0,
  };
}

export function buildCheckpointState(scn: ScenarioDef, cp: CheckpointDef): SimState {
  const excluded = new Set(cp.exclude ?? []);
  const events = [...scn.events.filter((e) => e.at <= cp.at && !excluded.has(e.id)), ...(cp.extra ?? [])].sort(
    (a, b) => a.at - b.at,
  );
  let state = initialState(scn, cp);
  for (const ev of events) state = applyEvent(state, ev);
  return { ...state, clock: cp.at, feed: { status: 'OK', observedAt: cp.at } };
}

/* ---------------------------------------------------------------- Helpers */

export const opposite = (side: Side): Side => (side === 'BUY' ? 'SELL' : 'BUY');
export const entrySide = (d: Direction): Side => (d === 'LONG' ? 'BUY' : 'SELL');
const sideLabel = (side: Side) => (side === 'BUY' ? 'BUY' : 'SELL');

export function accountingOf(state: SimState, mark: { price: number; at: number; current: boolean } | null = null) {
  return computeAccounting(
    INITIAL_BALANCE,
    state.fills.map((f) => ({ id: f.id, at: Date.parse(f.at), side: f.side, qty: f.qty.amount, price: f.price.amount, fee: f.fee.amount })),
    mark,
  );
}

export const isPendingEntry = (o: Order) => o.purpose === 'ENTRY' && (o.status === 'REQUESTED' || o.status === 'ACCEPTED');
export const isPendingExit = (o: Order) => o.purpose === 'EXIT' && o.status === 'REQUESTED';
export const isActiveProtection = (o: Order) => o.purpose === 'PROTECTION' && o.status === 'ACCEPTED';

/** Candela k: apertura INTRADAY_START + k·45m, chiusura un passo dopo. */
export const candleCloseTime = (k: number) => INTRADAY_START + (k + 1) * INTRADAY_STEP_MS;

/** Ultimo prezzo di chiusura noto all'istante t (nessun dato tra due chiusure). */
export function priceAt(market: ScenarioMarket, t: number): number | null {
  let price: number | null = t >= INTRADAY_START ? market.intraday[0][0] : null;
  for (let k = 0; k < market.intraday.length; k++) {
    if (candleCloseTime(k) <= t) price = market.intraday[k][3];
    else break;
  }
  return price;
}

/**
 * Convenzione della UI simulata: un'uscita richiesta all'istante t viene eseguita alla
 * chiusura della successiva candela 45m dello scenario, al suo prezzo di chiusura.
 * Oltre la fine dei dati: un minuto dopo, all'ultimo prezzo noto.
 */
export function nextExecutionTick(market: ScenarioMarket, t: number): { at: number; price: number } {
  for (let k = 0; k < market.intraday.length; k++) {
    const closeAt = candleCloseTime(k);
    if (closeAt > t) return { at: closeAt, price: market.intraday[k][3] };
  }
  return { at: t + 60_000, price: market.intraday[market.intraday.length - 1][3] };
}

function pushHistory(
  s: Draft,
  at: number,
  type: HistoryType,
  origin: Origin,
  title: string,
  text: string,
  extra: Partial<Pick<HistoryEvent, 'links' | 'change' | 'notification'>> = {},
) {
  s.seq += 1;
  s.history = [
    ...s.history,
    {
      id: `h-${String(s.seq).padStart(3, '0')}`,
      type,
      at: toIso(at),
      links: extra.links ?? {},
      title,
      text,
      change: extra.change ?? null,
      notification: extra.notification ?? { kind: 'NONE', text: 'Nessuna notifica' },
      origin,
    },
  ];
}

const SIMULATED_NOTICE = (at: number) => ({ kind: 'SIMULATED' as const, text: `Notifica simulata · nessun invio · ${toIso(at)}` });

function updateOrder(s: Draft, id: string, patch: Partial<Order>) {
  s.orders = s.orders.map((o) => (o.id === id ? { ...o, ...patch } : o));
}

function cancelPendingEntries(s: Draft, at: number, origin: Origin, why: string) {
  for (const o of s.orders.filter(isPendingEntry)) {
    updateOrder(s, o.id, { status: 'CANCELLED', updatedAt: toIso(at) });
    pushHistory(
      s,
      at,
      'ORDER',
      origin,
      "Ordine d'ingresso annullato",
      `${sideLabel(o.side)} ${formatBtc(o.requestedQty.amount)}${o.limitPrice ? ` limite ${formatPrice(o.limitPrice.amount)} USDT` : ''}: ${why}. Nessun eseguito, nessuna commissione.`,
      { links: { orderId: o.id, callId: o.callId ?? undefined } },
    );
  }
}

/* ------------------------------------------------------------ applyEvent */

export function applyEvent(state: SimState, ev: SimEvent): SimState {
  const s: Draft = { ...state, clock: Math.max(state.clock, ev.at) };
  // Con il feed regolare l'ultimo dato osservato segue l'orologio simulato.
  if (s.feed.status === 'OK') s.feed = { status: 'OK', observedAt: s.clock };

  switch (ev.kind) {
    case 'OBSERVATIONS': {
      s.observationSetId = ev.setId;
      s.expectation = ev.expectation;
      pushHistory(s, ev.at, 'EXPECTATION', 'BOT', 'Analisi aggiornata', ev.summary, {
        notification: { kind: 'NONE', text: "Nessun invio: solo aggiornamento dell'analisi" },
      });
      break;
    }

    case 'CALL_CREATED': {
      s.call = ev.call;
      s.plan = {
        callId: ev.call.id,
        version: 1,
        original: ev.plan.original,
        current: ev.plan.original,
        changes: [],
        expiresAt: toIso(ev.plan.expiresAt),
        reason: ev.plan.reason,
      };
      const p = ev.plan.original;
      pushHistory(
        s,
        ev.at,
        'CALL',
        'BOT',
        `Nuova call ${ev.call.direction} · ${ev.call.displayId}`,
        `Fascia ${formatPrice(p.entryZone.low.amount)}–${formatPrice(p.entryZone.high.amount)} · stop ${formatPrice(p.stop.amount)} · target ${p.targets
          .map((t) => formatPrice(t.amount))
          .join(' / ')} USDT. ${ev.call.status === 'PROPOSED' ? 'Proposta: nessun ordine.' : 'Nessun ordine ancora inviato.'}`,
        { links: { callId: ev.call.id, planVersion: 1 }, notification: SIMULATED_NOTICE(ev.at) },
      );
      break;
    }

    case 'ORDER_CREATED': {
      const o = ev.order;
      const status = ev.outcome;
      const callId = s.call?.id ?? null;
      const order: Order = {
        id: o.id,
        callId,
        purpose: o.purpose,
        protectionKind: null,
        side: o.side,
        type: o.type,
        requestedQty: btc(o.qty),
        filledQty: btc(0),
        status,
        limitPrice: o.limitPrice ? usdt(o.limitPrice) : null,
        triggerPrice: null,
        createdAt: toIso(ev.at),
        updatedAt: toIso(ev.at),
        origin: ev.origin === 'OWNER' ? 'OWNER' : 'BOT',
        rejection: ev.rejection ?? null,
        freshness: 'CURRENT',
      };
      s.orders = [...s.orders, order];
      const desc = `${sideLabel(o.side)} ${formatBtc(o.qty)}${o.limitPrice ? ` limite ${formatPrice(o.limitPrice)} USDT` : ' a mercato (simulato)'}`;
      if (status === 'REJECTED') {
        pushHistory(
          s,
          ev.at,
          'ORDER',
          ev.origin,
          "Ordine d'ingresso rifiutato",
          `${ev.rejection?.code ?? 'SIM'} · ${ev.rejection?.message ?? 'Rifiuto simulato'}. ${desc}. Nessun eseguito, nessuna commissione; nessun reinvio automatico.`,
          { links: { orderId: o.id, callId: callId ?? undefined }, notification: SIMULATED_NOTICE(ev.at) },
        );
      } else if (o.purpose === 'ENTRY') {
        pushHistory(s, ev.at, 'ORDER', ev.origin, "Ordine d'ingresso accettato (simulato)", `${desc}. Accettato non significa eseguito.`, {
          links: { orderId: o.id, callId: callId ?? undefined },
        });
      } else {
        const isClose = Math.abs(o.qty - (accountingOf(s).position?.qty ?? 0)) < QTY_EPSILON;
        const waiting =
          s.feed.status === 'OK'
            ? "In attesa dell'eseguito simulato."
            : 'Feed simulato non aggiornato: richiesta in attesa di conferma, nessun eseguito presunto.';
        pushHistory(s, ev.at, 'ORDER', ev.origin, isClose ? 'Chiusura richiesta' : 'Uscita parziale richiesta', `${desc}. ${waiting}`, {
          links: { orderId: o.id, callId: callId ?? undefined },
        });
      }
      break;
    }

    case 'ORDER_CANCELLED': {
      const o = s.orders.find((x) => x.id === ev.orderId);
      if (!o || (o.status !== 'ACCEPTED' && o.status !== 'REQUESTED')) break;
      updateOrder(s, o.id, { status: 'CANCELLED', updatedAt: toIso(ev.at) });
      pushHistory(
        s,
        ev.at,
        'ORDER',
        ev.origin,
        o.purpose === 'ENTRY' ? "Ordine d'ingresso annullato" : "Richiesta d'uscita annullata",
        `${sideLabel(o.side)} ${formatBtc(o.requestedQty.amount)}: ${ev.reason}. Nessun eseguito, nessuna commissione.`,
        { links: { orderId: o.id, callId: o.callId ?? undefined } },
      );
      break;
    }

    case 'FILL': {
      const o = s.orders.find((x) => x.id === ev.orderId);
      if (!o) throw new Error(`Ordine sconosciuto: ${ev.orderId}`);
      if (o.status !== 'ACCEPTED' && o.status !== 'REQUESTED' && o.status !== 'PARTIALLY_FILLED') break;
      const qty = clean(o.requestedQty.amount - o.filledQty.amount);
      const fee = clean(qty * ev.price * FIXTURE_FEE_RATE);
      const fill: Fill = {
        id: `fill-${o.id}`,
        orderId: o.id,
        at: toIso(ev.at),
        side: o.side,
        qty: btc(qty),
        price: usdt(ev.price),
        fee: { amount: fee, currency: 'USDT' },
      };
      const before = accountingOf(s);
      s.fills = [...s.fills, fill];
      updateOrder(s, o.id, { status: 'FILLED', filledQty: btc(clean(o.filledQty.amount + qty)), updatedAt: toIso(ev.at) });
      const after = accountingOf(s);

      if (o.purpose === 'ENTRY') {
        s.management = s.mode === 'CALL_AND_EXECUTION' ? 'BOT' : 'MANUAL';
        if (s.call && (s.call.status === 'AVAILABLE' || s.call.status === 'PROPOSED')) s.call = { ...s.call, status: 'ACTIVE' };
        pushHistory(
          s,
          ev.at,
          'FILL',
          'BOT',
          `Ingresso eseguito · ${after.position?.side ?? ''}`,
          `${formatBtc(qty)} a ${formatPrice(ev.price)} USDT · commissione ${formatNumber(fee, 2)} USDT (fixture).`,
          { links: { orderId: o.id, callId: o.callId ?? undefined }, notification: SIMULATED_NOTICE(ev.at) },
        );
        break;
      }

      const leg = after.closedLegs[after.closedLegs.length - 1];
      const closed = after.position === null;
      pushHistory(
        s,
        ev.at,
        'FILL',
        o.origin === 'OWNER' ? 'OWNER' : 'BOT',
        closed ? 'Chiusura eseguita' : 'Uscita parziale eseguita',
        `${formatBtc(qty)} a ${formatPrice(ev.price)} USDT · lordo ${formatSigned(leg?.gross ?? 0, 2)} · commissione ${formatNumber(fee, 3)} USDT (fixture).`,
        { links: { orderId: o.id, callId: o.callId ?? undefined }, notification: SIMULATED_NOTICE(ev.at) },
      );
      if (closed) {
        for (const p of s.orders.filter(isActiveProtection)) updateOrder(s, p.id, { status: 'CANCELLED', updatedAt: toIso(ev.at) });
        if (s.call && s.call.status === 'ACTIVE') s.call = { ...s.call, status: 'COMPLETED' };
        pushHistory(
          s,
          ev.at,
          'PROTECTION',
          'SIMULATION',
          'Posizione chiusa',
          `Nessuna quantità residua. Ordini protettivi annullati. Realizzato lordo totale ${formatSigned(after.realizedGross, 2)} · costi ${formatNumber(after.fees, 3)} · netto ${formatSigned(after.realizedNet, 3)} USDT.`,
          { links: { callId: o.callId ?? undefined } },
        );
      } else if (before.position && after.position) {
        const residual = after.position.qty;
        for (const p of s.orders.filter(isActiveProtection)) updateOrder(s, p.id, { requestedQty: btc(residual), updatedAt: toIso(ev.at) });
        pushHistory(s, ev.at, 'PROTECTION', 'SIMULATION', 'Protezioni adeguate al residuo', `Stop e target simulati ora su ${formatBtc(residual)}.`, {
          links: { callId: o.callId ?? undefined },
        });
      }
      break;
    }

    case 'PROTECTIONS_PLACED': {
      const pos = accountingOf(s).position;
      if (!pos || !s.plan) break;
      const side = opposite(entrySide(pos.side));
      const base = {
        callId: s.plan.callId,
        purpose: 'PROTECTION' as const,
        side,
        requestedQty: btc(pos.qty),
        filledQty: btc(0),
        status: 'ACCEPTED' as const,
        createdAt: toIso(ev.at),
        updatedAt: toIso(ev.at),
        origin: 'BOT' as const,
        rejection: null,
        freshness: 'CURRENT' as const,
      };
      s.orders = [
        ...s.orders,
        { ...base, id: ev.stopOrderId, protectionKind: 'STOP', type: 'STOP', limitPrice: null, triggerPrice: s.plan.current.stop },
        { ...base, id: ev.targetOrderId, protectionKind: 'TARGET', type: 'LIMIT', limitPrice: s.plan.current.targets[0], triggerPrice: null },
      ];
      pushHistory(
        s,
        ev.at,
        'PROTECTION',
        'BOT',
        'Protezioni simulate attive',
        `Stop ${formatPrice(s.plan.current.stop.amount)} · target ${formatPrice(s.plan.current.targets[0].amount)} USDT su ${formatBtc(pos.qty)}.`,
        { links: { callId: s.plan.callId } },
      );
      break;
    }

    case 'PLAN_CHANGE': {
      if (!s.plan) break;
      const before = s.plan.current.stop;
      const after = usdt(ev.after);
      const version = s.plan.version + 1;
      s.plan = {
        ...s.plan,
        version,
        current: { ...s.plan.current, stop: after, setAt: toIso(ev.at) },
        changes: [...s.plan.changes, { at: toIso(ev.at), field: 'STOP', before, after, reason: ev.reason }],
      };
      for (const p of s.orders.filter((o) => isActiveProtection(o) && o.protectionKind === 'STOP')) {
        updateOrder(s, p.id, { triggerPrice: after, updatedAt: toIso(ev.at) });
      }
      const verb = ev.after > before.amount ? 'alzato' : 'abbassato';
      pushHistory(
        s,
        ev.at,
        'PLAN_CHANGE',
        'BOT',
        `Stop ${verb} a ${formatPrice(ev.after)} USDT`,
        `${ev.reason} Nessun risultato realizzato dalla modifica.`,
        {
          links: { callId: s.plan.callId, planVersion: version },
          change: { field: 'Stop', before: formatPrice(before.amount), after: formatPrice(ev.after) },
          notification: SIMULATED_NOTICE(ev.at),
        },
      );
      break;
    }

    case 'MODE': {
      if (s.mode === ev.mode) break;
      s.mode = ev.mode;
      const pos = accountingOf(s).position;
      if (ev.mode === 'CALL_ONLY') {
        cancelPendingEntries(s, ev.at, ev.origin, 'passaggio a «Solo call»');
        const released = pos !== null && s.management === 'BOT';
        if (pos) s.management = 'MANUAL';
        pushHistory(
          s,
          ev.at,
          'MODE',
          ev.origin,
          released ? 'Gestione manuale confermata' : 'Modalità: Solo call',
          released
            ? `Il bot osserva e non modifica più le uscite. Stop e target esistenti restano attivi su ${formatBtc(pos!.qty)}.`
            : 'Nessun nuovo ordine simulato verrà inviato.',
          { notification: SIMULATED_NOTICE(ev.at) },
        );
      } else {
        const taken = pos !== null && s.management === 'MANUAL';
        if (pos) s.management = 'BOT';
        pushHistory(
          s,
          ev.at,
          'MODE',
          ev.origin,
          taken ? 'Gestione automatica ripresa' : 'Modalità: Call + esecuzione',
          taken
            ? `Il bot riprende la posizione esistente (${formatBtc(pos!.qty)}) dai livelli attuali. Nessun nuovo ingresso.`
            : 'Esecuzione automatica simulata abilitata. Una sola posizione BTC, nessun aumento.',
          { notification: SIMULATED_NOTICE(ev.at) },
        );
      }
      break;
    }

    case 'BOT': {
      if (s.bot.status === ev.status) break;
      s.bot = { status: ev.status, since: ev.at, reason: ev.reason };
      if (ev.status === 'STOPPED') {
        cancelPendingEntries(s, ev.at, ev.origin, 'stop totale');
        const pos = accountingOf(s).position;
        pushHistory(
          s,
          ev.at,
          'BOT',
          ev.origin,
          'Stop totale',
          pos
            ? `Analisi e azioni simulate del bot ferme. La posizione (${formatBtc(pos.qty)}) e le protezioni restano invariate: non è una chiusura.`
            : 'Analisi e azioni simulate del bot ferme.',
          { notification: SIMULATED_NOTICE(ev.at) },
        );
      } else {
        pushHistory(s, ev.at, 'BOT', ev.origin, 'Bot riavviato', 'Analisi e azioni simulate riprese. Nessun ordine annullato viene ripristinato.', {
          notification: SIMULATED_NOTICE(ev.at),
        });
      }
      break;
    }

    case 'FEED': {
      s.feed = { status: ev.status, observedAt: ev.observedAt };
      const text =
        ev.status === 'OK'
          ? 'Feed simulato ripristinato. I valori tornano correnti.'
          : ev.status === 'STALE'
            ? 'Alterazione controllata: dati non aggiornati. Restano visibili gli ultimi valori noti con il loro orario; nuovi ingressi bloccati.'
            : 'Alterazione controllata: feed simulato disconnesso. Prezzo e P&L correnti non disponibili; protezioni solo ultime note.';
      pushHistory(s, ev.at, 'FEED', 'SIMULATION', ev.status === 'OK' ? 'Feed simulato ripristinato' : 'Feed simulato alterato', text, {
        notification: ev.status === 'DISCONNECTED' ? SIMULATED_NOTICE(ev.at) : { kind: 'NONE', text: 'Nessuna notifica' },
      });
      break;
    }
  }

  return s;
}
