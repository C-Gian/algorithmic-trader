/** Testi semplici per stati, astensioni, tentativi e chiusure del candidato CAND-001 (codici del motore). */
import type { Side } from '../../contract/backtest';
import { formatNumber, formatSigned } from '../../lib/numbers';

export const ABSTAIN_TEXT: Record<string, string> = {
  ABSTAIN_STRUCTURE: 'la struttura 45m non andava nel verso del movimento',
  ABSTAIN_AMPLITUDE: 'il movimento era troppo piccolo rispetto alla volatilità (meno di 3 volte A)',
  ABSTAIN_DURATION: 'il movimento era durato più di 24 ore (32 barre da 45 minuti)',
  ABSTAIN_INCOMPLETE_INPUT: 'mancavano dati nelle barre del movimento',
  ABSTAIN_VOLATILITY_UNAVAILABLE: 'la volatilità A non era disponibile',
  ABSTAIN_REWARD_RISK: 'lo spazio fino all’estremo P1 era meno di 1,5 volte il rischio fino allo stop',
  INVALIDATED_DEPTH: 'la reazione è andata troppo a fondo (oltre 3/4 del movimento o oltre P0)',
  INVALIDATED_TARGET_REACHED: 'il prezzo era già tornato all’estremo P1: il movimento atteso era già avvenuto',
  INVALIDATED_STRUCTURE: 'la struttura 45m si è girata contro il movimento',
  INVALIDATED_DATA: 'mancavano dati durante l’attesa',
  EXPIRED: 'nessuna ripresa entro 12 barre (9 ore) dalla candela estrema',
  REJECTED_PRICE: 'all’apertura del minuto previsto il prezzo era già oltre il limite fissato (il guadagno possibile non era più almeno 1,5 volte il rischio)',
  CANCELLED_NO_QUOTE: 'in quel minuto mancava il prezzo negoziato',
  CANCELLED_END_OF_WINDOW: 'il periodo valutato stava finendo',
  SKIPPED_BUSY: 'il bot era già impegnato con un altro episodio',
  UNRESOLVED_DATA_GAP: 'mancavano minuti mentre la posizione era aperta: percorso irrisolto',
};

export const STATE_TEXT: Record<string, string> = {
  RECOGNIZED: 'Ha riconosciuto il movimento',
  WAIT_REACTION: 'Aspetta una reazione',
  WAIT_RESUMPTION: 'Reazione adatta: aspetta la ripresa',
  CALL: 'Ha deciso di tentare l’ingresso',
  ENTRY_PENDING: 'Tentativo d’ingresso al minuto successivo',
  FILLED: 'Posizione simulata aperta',
  HOLD: 'Mantiene la posizione',
  PROTECTION_UPDATE: 'Aggiorna il limite di protezione',
  PROTECTION_REJECTED: 'Nuovo limite di protezione scartato',
  PROTECTION_PIVOT_BEFORE_ENTRY: 'Punto precedente all’ingresso: non usato per la protezione',
  EXIT_STRUCTURE_REQUESTED: 'Cambio di direzione: chiede la chiusura',
  CLOSED: 'Posizione chiusa',
};

/** Motivo d'uscita breve, per tabelle e registro. */
export const EXIT_TEXT: Record<string, string> = {
  STOP: 'limite di perdita (stop)',
  TARGET: 'obiettivo raggiunto',
  EXIT_STRUCTURE: 'cambio di direzione rilevato',
  TIME_EXIT: 'limite di 24 ore',
  END_OF_SEGMENT: 'fine del periodo',
};

/** «La posizione è stata chiusa perché …»: l'evento vero, nessuna «uscita» generica. */
export const CLOSE_WHY: Record<string, string> = {
  STOP: 'il prezzo ha raggiunto il limite di perdita (stop)',
  TARGET: 'il prezzo ha raggiunto l’obiettivo (ritorno all’estremo P1 del movimento)',
  EXIT_STRUCTURE: 'le regole hanno rilevato un cambiamento di direzione (struttura 45m opposta)',
  TIME_EXIT: 'è scaduto il limite di 24 ore per operazione',
  END_OF_SEGMENT: 'è finito il periodo valutato (chiusura prevista dal protocollo)',
};

export const CATEGORY_TEXT: Record<string, string> = {
  FIRST_CALL: 'prima decisione di tentare un ingresso',
  FIRST_TRADE: 'prima operazione',
  FIRST_NEGATIVE_TRADE: 'primo risultato negativo',
  FIRST_POSITIVE_TRADE: 'primo risultato positivo',
  FIRST_PROTECTION_UPDATE: 'primo aggiornamento del limite di protezione',
  FIRST_ABSTAIN_REACTION_INVALIDATED: 'prima rinuncia per reazione non valida',
  FIRST_ABSTAIN_REWARD_RISK: 'prima rinuncia per spazio/rischio insufficiente',
  FIRST_ABSTAIN_MISSING_DATA: 'prima rinuncia per dato mancante',
};

/** Parole per verso: LONG punta su una salita, SHORT su una discesa (non è vendere BTC posseduti). */
export const SIDE = {
  LONG: { move: 'salita', attempt: 'un acquisto', the: 'L’acquisto', done: 'eseguito', bet: 'puntare su una salita del prezzo', limitWord: 'massimo' },
  SHORT: { move: 'discesa', attempt: 'una vendita', the: 'La vendita', done: 'eseguita', bet: 'puntare su una discesa del prezzo', limitWord: 'minimo' },
} as const satisfies Record<Side, unknown>;

export const stateText = (s: string) => STATE_TEXT[s] ?? (ABSTAIN_TEXT[s] ? `Rinuncia: ${ABSTAIN_TEXT[s]}` : s);
export const usdt = (x: number | null | undefined, digits = 2) => (x == null ? 'n.d.' : `${formatSigned(x, digits)} USDT`);
export const plainUsdt = (x: number | null | undefined, digits = 2) => (x == null ? 'n.d.' : `${formatNumber(x, digits)} USDT`);
export const px = (x: number | null | undefined) => (x == null ? '—' : formatNumber(x, 2));
export const pct = (x: number | null | undefined, digits = 1) => (x == null ? '—' : `${formatNumber(x * 100, digits)}%`);
export const num = (x: number | null | undefined, digits = 2) => (x == null ? '—' : formatNumber(x, digits));
export const bps = (x: number | null | undefined) => (x == null ? 'n.d.' : `${formatSigned(x, 0)} bp`);
