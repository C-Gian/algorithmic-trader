/** Testi semplici per stati, astensioni e uscite del candidato CAND-001 (codici del motore). */
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
  REJECTED_PRICE: 'all’apertura del minuto d’ingresso il prezzo non rispettava più il rapporto 1,5',
  CANCELLED_NO_QUOTE: 'nel minuto d’ingresso mancava la quotazione',
  CANCELLED_END_OF_WINDOW: 'la finestra valutata stava finendo',
  SKIPPED_BUSY: 'il candidato era già occupato da un altro episodio',
  UNRESOLVED_DATA_GAP: 'mancavano minuti mentre la posizione era aperta: percorso irrisolto',
};

export const STATE_TEXT: Record<string, string> = {
  RECOGNIZED: 'Ha riconosciuto il movimento',
  WAIT_REACTION: 'Attende una reazione sufficiente',
  WAIT_RESUMPTION: 'Reazione compatibile: attende la ripresa',
  CALL: 'Ha chiesto un ingresso condizionato',
  ENTRY_PENDING: 'Richiesta d’ingresso in attesa (60 s)',
  FILLED: 'Ingresso modellato eseguito',
  HOLD: 'Mantiene la posizione',
  PROTECTION_UPDATE: 'Alza la protezione',
  PROTECTION_REJECTED: 'Proposta di protezione scartata',
  PROTECTION_PIVOT_BEFORE_ENTRY: 'Pivot precedente all’ingresso: non usato per la protezione',
  EXIT_STRUCTURE_REQUESTED: 'Struttura opposta: chiede l’uscita',
  CLOSED: 'Operazione chiusa',
};

export const EXIT_TEXT: Record<string, string> = {
  STOP: 'stop',
  TARGET: 'ritorno all’estremo P1 (target)',
  EXIT_STRUCTURE: 'struttura 45m opposta',
  TIME_EXIT: 'durata massima di 24 ore',
  END_OF_SEGMENT: 'fine della finestra valutata',
};

export const CATEGORY_TEXT: Record<string, string> = {
  FIRST_CALL: 'prima call',
  FIRST_TRADE: 'prima operazione',
  FIRST_NEGATIVE_TRADE: 'primo netto negativo',
  FIRST_POSITIVE_TRADE: 'primo netto positivo',
  FIRST_PROTECTION_UPDATE: 'prima protezione aggiornata',
  FIRST_ABSTAIN_REACTION_INVALIDATED: 'prima astensione per reazione invalidata',
  FIRST_ABSTAIN_REWARD_RISK: 'prima astensione per spazio/rischio',
  FIRST_ABSTAIN_MISSING_DATA: 'prima astensione per dato mancante',
};

export const stateText = (s: string) => STATE_TEXT[s] ?? (ABSTAIN_TEXT[s] ? `Si astiene: ${ABSTAIN_TEXT[s]}` : s);
export const usdt = (x: number | null | undefined, digits = 2) => (x == null ? 'n.d.' : `${formatSigned(x, digits)} USDT`);
export const plainUsdt = (x: number | null | undefined, digits = 2) => (x == null ? 'n.d.' : `${formatNumber(x, digits)} USDT`);
export const px = (x: number | null | undefined) => (x == null ? '—' : formatNumber(x, 2));
export const pct = (x: number | null | undefined, digits = 1) => (x == null ? '—' : `${formatNumber(x * 100, digits)}%`);
export const num = (x: number | null | undefined, digits = 2) => (x == null ? '—' : formatNumber(x, digits));
export const bps = (x: number | null | undefined) => (x == null ? 'n.d.' : `${formatSigned(x, 0)} bp`);
