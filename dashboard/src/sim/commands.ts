/**
 * Comandi dell'Owner: disponibilità, testo delle conferme e traduzione in eventi.
 * Conseguenze e guardie derivano dallo stato corrente; i componenti le mostrano soltanto.
 */
import type { ActionId, ActionState } from '../contract/types';
import type { CommandPreview, ConfirmationPreview } from '../contract/provider';
import { formatBtc, formatPrice } from '../lib/numbers';
import { formatClock } from '../lib/time';
import { clean } from './accounting';
import type { ScenarioDef, SimEvent, SimState } from './engine';
import {
  PARTIAL_EXIT_QTY,
  accountingOf,
  entrySide,
  isActiveProtection,
  isPendingEntry,
  isBeyondSegment,
  isPendingExit,
  opposite,
  priceAt,
} from './engine';

const QTY_EPSILON = 1e-9;

function facts(state: SimState) {
  const acc = accountingOf(state);
  const pos = acc.position;
  const pendingEntries = state.orders.filter(isPendingEntry);
  const pendingExit = state.orders.find(isPendingExit) ?? null;
  const protections = state.orders.filter(isActiveProtection);
  return { acc, pos, pendingEntries, pendingExit, protections };
}

const on = (): ActionState => ({ enabled: true, reason: null });
const off = (reason: string): ActionState => ({ enabled: false, reason });

/** Feed non regolare: descrizione e orario dell'ultimo dato, oppure null con feed regolare. */
function feedLimit(state: SimState): { what: string; at: string } | null {
  if (state.feed.status === 'OK') return null;
  return {
    what: state.feed.status === 'STALE' ? 'feed simulato non aggiornato' : 'feed simulato disconnesso',
    at: formatClock(state.feed.observedAt),
  };
}

/**
 * Convenzione della UI simulata (review UI-001/R1): con feed non regolare Start e presa
 * in gestione automatica restano bloccati; al ripristino l'Owner li richiede di nuovo.
 */
function automationBlock(state: SimState, subject: string): string | null {
  const limit = feedLimit(state);
  if (!limit) return null;
  return `${limit.what[0].toUpperCase()}${limit.what.slice(1)} (ultimo dato alle ${limit.at}): ${subject} resta bloccato finché il feed non torna regolare. Al ripristino non riparte da solo: va richiesto e confermato.`;
}

export function actionStates(state: SimState): Record<ActionId, ActionState> {
  const { pos, pendingEntries, pendingExit } = facts(state);
  const exitBlock = !pos ? 'Nessuna posizione aperta: niente da ridurre o chiudere.' : pendingExit ? "Un'uscita è già stata richiesta ed è in attesa." : null;
  const takeover = automationBlock(state, 'il ritorno alla gestione automatica');
  const startBlock = automationBlock(state, 'lo Start');
  return {
    START: state.bot.status === 'RUNNING' ? off('Il bot simulato è già attivo.') : startBlock ? off(startBlock) : on(),
    STOP_TOTAL: state.bot.status === 'RUNNING' ? on() : off('Il bot simulato è già fermo.'),
    MODE_CALL_ONLY: state.mode === 'CALL_AND_EXECUTION' ? on() : off('Modalità già attiva.'),
    MODE_CALL_AND_EXECUTION: state.mode !== 'CALL_ONLY' ? off('Modalità già attiva.') : pos && state.management === 'MANUAL' && takeover ? off(takeover) : on(),
    TAKE_MANUAL: !pos ? off('Nessuna posizione da gestire.') : state.management === 'MANUAL' ? off('Posizione già in gestione manuale.') : on(),
    RESUME_AUTOMATIC: !pos
      ? off('Nessuna posizione da gestire.')
      : state.management === 'BOT'
        ? off('Posizione già in gestione automatica.')
        : takeover
          ? off(takeover)
          : on(),
    PARTIAL_EXIT: exitBlock
      ? off(exitBlock)
      : pos!.qty <= PARTIAL_EXIT_QTY + QTY_EPSILON
        ? off(`Residuo ${formatBtc(pos!.qty)}: non resta abbastanza per un'uscita parziale di ${formatBtc(PARTIAL_EXIT_QTY)}.`)
        : on(),
    CLOSE_POSITION: exitBlock ? off(exitBlock) : on(),
    CANCEL_ENTRY_ORDER: pendingEntries.length > 0 ? on() : off("Nessun ordine d'ingresso in attesa."),
    CANCEL_EXIT_REQUEST: pendingExit ? on() : off("Nessuna richiesta d'uscita in attesa."),
  };
}

function positionSummary(state: SimState): string[] {
  const { pos, protections } = facts(state);
  const limit = feedLimit(state);
  if (!pos) return [limit ? `Nessuna posizione aperta · ultimo stato noto alle ${limit.at}` : 'Nessuna posizione aperta'];
  const stop = protections.find((p) => p.protectionKind === 'STOP')?.triggerPrice?.amount;
  const target = protections.find((p) => p.protectionKind === 'TARGET')?.limitPrice?.amount;
  return [
    limit ? `BTC / USDT · ${pos.side} aperta · ultimo stato noto alle ${limit.at}` : `BTC / USDT · ${pos.side} aperta`,
    `${formatBtc(pos.qty)} · ingresso ${formatPrice(pos.avgEntryPrice)}`,
    stop !== undefined || target !== undefined
      ? `Stop ${stop !== undefined ? formatPrice(stop) : '—'} · target ${target !== undefined ? formatPrice(target) : '—'} USDT${limit ? ' · ultimi noti, non verificabili ora' : ''}`
      : limit
        ? 'Nessuna protezione simulata memorizzata'
        : 'Nessuna protezione simulata attiva',
  ];
}

function pendingEntryLine(state: SimState): string | null {
  const entries = facts(state).pendingEntries;
  if (entries.length === 0) return null;
  return entries
    .map((o) => `L'ordine d'ingresso in attesa (${o.side} ${formatBtc(o.requestedQty.amount)}${o.limitPrice ? ` limite ${formatPrice(o.limitPrice.amount)}` : ''}) verrà annullato.`)
    .join(' ');
}

const feedNotice = (state: SimState) =>
  state.feed.status === 'OK'
    ? null
    : {
        tone: 'warning' as const,
        title: 'Feed simulato non aggiornato',
        text: 'La richiesta resterà in attesa di conferma fino al ripristino del feed. Nessun eseguito verrà presunto.',
      };

function exitTimingLine(state: SimState, market: ScenarioDef['market']): string {
  return isBeyondSegment(market, state.clock)
    ? 'Prima la richiesta, poi l’eseguito simulato: oltre il segmento dello scenario il prezzo fittizio viene mantenuto (ultima chiusura, un minuto dopo). Non è un prezzo di mercato osservato.'
    : 'Prima la richiesta, poi l’eseguito simulato alla chiusura della successiva candela 45m dello scenario.';
}

/** Anteprima senza impronta: il provider aggiunge `contextToken` prima di esporla. */
export type ConfirmationDraft = Omit<ConfirmationPreview, 'contextToken'>;
export type PreviewDraft = Exclude<CommandPreview, { kind: 'CONFIRM' }> | { readonly kind: 'CONFIRM'; readonly confirmation: ConfirmationDraft };

function confirm(c: Omit<ConfirmationDraft, 'acknowledgement'> & { acknowledgement?: string }): PreviewDraft {
  return { kind: 'CONFIRM', confirmation: { acknowledgement: null, ...c } };
}

/**
 * Fatti da cui dipendono le conseguenze di una conferma. Con il testo dell'anteprima
 * formano l'impronta del contesto: se uno cambia, il consenso precedente non vale più.
 */
export function consequenceFacts(state: SimState) {
  const { pos, pendingEntries, pendingExit, protections } = facts(state);
  return {
    checkpoint: state.checkpointId,
    position: pos ? { side: pos.side, qty: pos.qty, avg: pos.avgEntryPrice } : null,
    management: state.management,
    mode: state.mode,
    bot: state.bot.status,
    feed: state.feed,
    plan: state.plan ? { callId: state.plan.callId, version: state.plan.version, stop: state.plan.current.stop.amount, targets: state.plan.current.targets.map((t) => t.amount) } : null,
    protections: protections.map((o) => [o.id, o.protectionKind, o.triggerPrice?.amount ?? null, o.limitPrice?.amount ?? null, o.requestedQty.amount]),
    pendingEntries: pendingEntries.map((o) => [o.id, o.requestedQty.amount]),
    pendingExit: pendingExit ? [pendingExit.id, pendingExit.requestedQty.amount] : null,
  };
}

export function previewAction(state: SimState, market: ScenarioDef['market'], action: ActionId): PreviewDraft {
  const status = actionStates(state)[action];
  if (!status.enabled) return { kind: 'BLOCKED', reason: status.reason ?? 'Azione non disponibile.' };
  const { pos, protections, pendingEntries } = facts(state);
  const limit = feedLimit(state);
  const stop = protections.find((p) => p.protectionKind === 'STOP')?.triggerPrice?.amount;
  const target = protections.find((p) => p.protectionKind === 'TARGET')?.limitPrice?.amount;
  const hasProtections = stop !== undefined || target !== undefined;
  const levels = `Stop ${stop !== undefined ? formatPrice(stop) : '—'} e target ${target !== undefined ? formatPrice(target) : '—'} USDT`;
  const onQty = pos ? ` su ${formatBtc(pos.qty)}` : '';
  // Con feed non regolare le protezioni sono solo ultime note: nessun testo ne attesta l'attualità.
  const protectionLine = !hasProtections
    ? limit
      ? 'Nessuna protezione simulata memorizzata.'
      : 'Nessuna protezione simulata è attiva.'
    : limit
      ? `${levels} sono gli ultimi noti alle ${limit.at} (${limit.what}): restano memorizzati${onQty}, ma non sono verificabili ora.`
      : `${levels} già presenti restano attivi${onQty}.`;
  const suspendedLine = limit ? `Con il ${limit.what} le azioni automatiche del bot sono sospese.` : null;

  switch (action) {
    case 'STOP_TOTAL': {
      if (!pos && pendingEntries.length === 0) return { kind: 'IMMEDIATE' };
      return confirm({
        action,
        icon: 'square',
        kicker: 'STOP TOTALE',
        title: pos ? 'Fermare il bot, non la posizione?' : 'Fermare il bot?',
        lead: `Il bot smette di analizzare e di inviare nuovi ordini simulati.${pos ? ' La tua posizione BTC rimane aperta.' : ''}`,
        summary: positionSummary(state),
        consequences: [
          !pos
            ? 'Nessuna posizione da proteggere.'
            : limit
              ? `${protectionLine} Lo stop totale agisce solo sullo stato locale del bot e non verifica gli ordini.`
              : `${levels} già presenti restano presenti e possono chiudere la posizione${onQty}.`,
          pendingEntryLine(state) ?? "Gli eventuali ordini d'ingresso non eseguiti verrebbero annullati. In questo stato non ce ne sono.",
          limit
            ? 'Quotazioni e conto restano visibili come ultimi noti. “Start” resterà bloccato finché il feed non torna regolare, poi richiederà una conferma.'
            : 'Quotazioni e conto restano visibili. “Start” richiederà una conferma di ripresa.',
        ],
        notice: pos
          ? { tone: 'warning', title: 'Questo comando non chiude la posizione.', text: 'Per uscire usa “Chiudi posizione”, un’azione separata.' }
          : null,
        confirmLabel: 'Ferma il bot',
        confirmTone: 'danger',
      });
    }

    case 'START':
      return confirm({
        action,
        icon: 'bot',
        kicker: 'RIAVVIO DEL BOT',
        title: 'Riavviare il bot simulato?',
        lead: `Il bot riprende analisi e azioni simulate in modalità “${state.mode === 'CALL_ONLY' ? 'Solo call' : 'Call + esecuzione'}”.`,
        summary: positionSummary(state),
        consequences: [
          "Gli ordini d'ingresso annullati dallo stop non vengono ripristinati.",
          pos
            ? `La posizione esistente non viene aumentata né duplicata${state.management === 'MANUAL' ? '; resta in gestione manuale finché non confermi la ripresa automatica' : ''}.`
            : 'Nessuna posizione aperta.',
          'Prima di agire, il bot riconcilia saldo, quantità e ordini simulati esistenti.',
        ],
        notice: null,
        confirmLabel: 'Start · riprendi',
        confirmTone: 'primary',
      });

    case 'MODE_CALL_ONLY':
    case 'TAKE_MANUAL': {
      if (pos && state.management === 'BOT') {
        const entryLine = pendingEntryLine(state);
        return confirm({
          action,
          icon: 'hand',
          kicker: 'PASSAGGIO ALLA GESTIONE MANUALE',
          title: 'Vuoi gestire tu la posizione?',
          lead: limit
            ? `Il bot smette di modificare o eseguire automaticamente le uscite. ${suspendedLine}`
            : 'Il bot continua a leggere il mercato, ma smette di modificare o eseguire automaticamente le uscite.',
          summary: positionSummary(state),
          consequences: [
            protectionLine,
            `Quantità in gestione${limit ? ' (ultima nota)' : ''}: ${formatBtc(pos.qty)}. Puoi ridurre o chiudere la posizione. Non puoi aumentare la quantità.`,
            limit
              ? 'La modalità diventa “Solo call”. Il ritorno all’automatico resta bloccato finché il feed non torna regolare, poi servirà una conferma.'
              : 'La modalità diventa “Solo call”. Per tornare all’automatico servirà una conferma.',
            ...(entryLine ? [entryLine] : []),
          ],
          notice: limit
            ? {
                tone: 'warning',
                title: `Posizione e protezioni sono ultime note alle ${limit.at}, non verificabili ora.`,
                text: 'Il passaggio agisce solo sullo stato locale della simulazione e non esegue acquisti o vendite. La responsabilità delle prossime modifiche passa a te.',
              }
            : { tone: 'accent', title: 'La responsabilità delle prossime modifiche passa a te.', text: 'Il passaggio non esegue acquisti o vendite.' },
          confirmLabel: 'Passa a manuale',
          confirmTone: 'primary',
        });
      }
      const entryLine = pendingEntryLine(state);
      if (action === 'MODE_CALL_ONLY' && entryLine) {
        return confirm({
          action,
          icon: 'mode',
          kicker: 'PASSAGGIO A SOLO CALL',
          title: 'Passare a “Solo call”?',
          lead: 'Il bot continua a proporre call ma non invia nuovi ordini simulati.',
          summary: positionSummary(state),
          consequences: [entryLine, 'Nessun nuovo ordine simulato verrà inviato.', 'La call resta visibile come lettura del mercato.'],
          notice: null,
          confirmLabel: 'Passa a Solo call',
          confirmTone: 'primary',
        });
      }
      return { kind: 'IMMEDIATE' };
    }

    case 'MODE_CALL_AND_EXECUTION':
    case 'RESUME_AUTOMATIC': {
      if (!(pos && state.management === 'MANUAL')) return { kind: 'IMMEDIATE' };
      const original = state.plan?.original.stop.amount;
      return confirm({
        action,
        icon: 'bot',
        kicker: 'RIPRESA DELL’AUTOMAZIONE',
        title: 'Riprendere la gestione automatica?',
        lead: 'Il bot torna a gestire la posizione esistente. Non apre una seconda posizione BTC e non aumenta la quantità.',
        summary: positionSummary(state),
        consequences: [
          'La modalità diventa “Call + esecuzione”.',
          'Prima di agire, il bot riconcilia saldo, quantità e ordini simulati esistenti.',
          original !== undefined && stop !== undefined && original !== stop
            ? `La gestione riparte dai livelli attuali (stop ${formatPrice(stop)}), non dallo stop originale a ${formatPrice(original)} USDT.`
            : 'La gestione riparte dai livelli attuali.',
          ...(state.bot.status === 'STOPPED' ? ['Il bot è fermo: la gestione automatica agirà solo dopo “Start”.'] : []),
        ],
        notice: { tone: 'accent', title: 'Presa in gestione esplicita', text: 'La ripresa può modificare le uscite secondo il piano attuale.' },
        confirmLabel: 'Riprendi automatico',
        confirmTone: 'primary',
        acknowledgement: 'Ho verificato quantità, stop e target.',
      });
    }

    case 'PARTIAL_EXIT': {
      const residual = clean(pos!.qty - PARTIAL_EXIT_QTY);
      return confirm({
        action,
        icon: 'partial',
        kicker: 'USCITA PARZIALE',
        title: `Ridurre la posizione di ${formatBtc(PARTIAL_EXIT_QTY)}?`,
        lead: `Richiesta ${opposite(entrySide(pos!.side))} simulata a mercato per una parte della posizione.`,
        summary: positionSummary(state),
        consequences: [
          `Quantità richiesta ${formatBtc(PARTIAL_EXIT_QTY)} (predeterminata dallo scenario); residuo previsto ${formatBtc(residual)}.`,
          exitTimingLine(state, market),
          'Stop e target si adeguano alla quantità residua.',
          'La commissione d’uscita (cifra di fixture) è conteggiata solo all’esecuzione.',
        ],
        notice: feedNotice(state),
        confirmLabel: 'Conferma uscita parziale',
        confirmTone: 'primary',
      });
    }

    case 'CLOSE_POSITION': {
      const last = priceAt(market, state.feed.observedAt);
      return confirm({
        action,
        icon: 'close',
        kicker: 'CHIUDI POSIZIONE',
        title: 'Chiudere tutta la posizione?',
        lead: 'Comando esplicito dell’Owner, distinto dallo stop del bot. Funziona anche con il bot fermo.',
        summary: positionSummary(state),
        consequences: [
          `Quantità: ${formatBtc(pos!.qty)} (tutto il residuo), lato ${opposite(entrySide(pos!.side))}.`,
          exitTimingLine(state, market),
          last !== null
            ? `Il prezzo eseguito può differire dall’ultimo noto (${formatPrice(last)} USDT): il risultato si realizza al prezzo eseguito.`
            : 'Il risultato si realizza al prezzo eseguito.',
          'Dopo l’esecuzione completa gli ordini protettivi vengono annullati.',
        ],
        notice: feedNotice(state),
        confirmLabel: 'Chiudi posizione',
        confirmTone: 'danger',
      });
    }

    case 'CANCEL_ENTRY_ORDER':
    case 'CANCEL_EXIT_REQUEST':
      return { kind: 'IMMEDIATE' };
  }
}

/** Traduce un comando in eventi. Chiamare solo dopo aver verificato la disponibilità. */
export function commandEvents(state: SimState, action: ActionId, requestId: string): SimEvent[] {
  const at = state.clock;
  const id = (suffix: string) => `cmd-${requestId}-${suffix}`;
  const { pos, pendingEntries, pendingExit } = facts(state);
  switch (action) {
    case 'STOP_TOTAL':
      return [{ kind: 'BOT', id: id('bot'), at, origin: 'OWNER', status: 'STOPPED', reason: 'Stop totale richiesto dall’Owner' }];
    case 'START':
      return [{ kind: 'BOT', id: id('bot'), at, origin: 'OWNER', status: 'RUNNING', reason: 'Start confermato dall’Owner' }];
    case 'MODE_CALL_ONLY':
    case 'TAKE_MANUAL':
      return [{ kind: 'MODE', id: id('mode'), at, origin: 'OWNER', mode: 'CALL_ONLY' }];
    case 'MODE_CALL_AND_EXECUTION':
    case 'RESUME_AUTOMATIC':
      return [{ kind: 'MODE', id: id('mode'), at, origin: 'OWNER', mode: 'CALL_AND_EXECUTION' }];
    case 'PARTIAL_EXIT':
    case 'CLOSE_POSITION':
      return [
        {
          kind: 'ORDER_CREATED',
          id: id('order'),
          at,
          origin: 'OWNER',
          order: {
            id: `exit-${requestId}`,
            purpose: 'EXIT',
            side: opposite(entrySide(pos!.side)),
            type: 'MARKET',
            qty: action === 'PARTIAL_EXIT' ? PARTIAL_EXIT_QTY : pos!.qty,
          },
          outcome: 'REQUESTED',
        },
      ];
    case 'CANCEL_ENTRY_ORDER':
      return pendingEntries.map((o, i) => ({
        kind: 'ORDER_CANCELLED' as const,
        id: id(`cancel-${i}`),
        at,
        origin: 'OWNER' as const,
        orderId: o.id,
        reason: 'annullato dall’Owner',
      }));
    case 'CANCEL_EXIT_REQUEST':
      return pendingExit
        ? [{ kind: 'ORDER_CANCELLED', id: id('cancel'), at, origin: 'OWNER', orderId: pendingExit.id, reason: 'richiesta ritirata dall’Owner prima dell’eseguito' }]
        : [];
  }
}
