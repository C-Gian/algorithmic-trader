/**
 * Contabilità del contratto lineare illustrativo della simulazione.
 *
 * Unica funzione che trasforma i fill in posizione e risultati: i componenti non la
 * duplicano. Regole dell'esempio del task:
 * - saldo = saldo iniziale + realizzato lordo − costi addebitati (nessuna detrazione del nozionale);
 * - equity = saldo + non realizzato lordo, solo con una valutazione corrente;
 * - i costi d'uscita non sono inclusi nel non realizzato; margine e leva non modellati.
 */
import type { Direction, Side } from '../contract/types';

export interface AccountingFill {
  readonly id: string;
  readonly at: number;
  readonly side: Side;
  readonly qty: number;
  readonly price: number;
  readonly fee: number;
}

export interface Mark {
  readonly price: number;
  readonly at: number;
  readonly current: boolean;
}

export interface ClosedLeg {
  readonly fillId: string;
  readonly at: number;
  readonly direction: Direction;
  readonly qty: number;
  readonly entryPrice: number;
  readonly exitPrice: number;
  readonly gross: number;
  readonly exitFee: number;
}

export interface AccountingResult {
  readonly position: {
    readonly side: Direction;
    readonly qty: number;
    readonly avgEntryPrice: number;
    readonly openedAt: number;
    readonly openingFillId: string;
  } | null;
  readonly realizedGross: number;
  readonly fees: number;
  readonly realizedNet: number;
  readonly balance: number;
  /** null se non esiste una valutazione corrente. */
  readonly unrealizedGross: number | null;
  readonly lastKnownUnrealizedGross: { readonly value: number; readonly at: number } | null;
  readonly equity: number | null;
  readonly lastKnownEquity: { readonly value: number; readonly at: number } | null;
  readonly closedLegs: readonly ClosedLeg[];
  readonly entryFees: number;
}

/** Rimuove soltanto il rumore binario dei float; non è un arrotondamento contabile. */
export const clean = (x: number): number => Math.round(x * 1e9) / 1e9;

const signOf = (side: Side): 1 | -1 => (side === 'BUY' ? 1 : -1);

export function computeAccounting(
  initialBalance: number,
  fills: readonly AccountingFill[],
  mark: Mark | null,
): AccountingResult {
  let signedQty = 0;
  let avg = 0;
  let openedAt = 0;
  let openingFillId = '';
  let realizedGross = 0;
  let fees = 0;
  let entryFees = 0;
  const closedLegs: ClosedLeg[] = [];

  const ordered = [...fills].sort((a, b) => a.at - b.at);
  for (const f of ordered) {
    if (!(f.qty > 0) || !(f.price > 0) || f.fee < 0) {
      throw new Error(`Fill non valido: ${f.id}`);
    }
    const d = signOf(f.side) * f.qty;
    fees = clean(fees + f.fee);

    if (signedQty === 0 || Math.sign(signedQty) === Math.sign(d)) {
      if (signedQty === 0) {
        openedAt = f.at;
        openingFillId = f.id;
      }
      const newQty = clean(signedQty + d);
      avg = clean((Math.abs(signedQty) * avg + f.qty * f.price) / Math.abs(newQty));
      signedQty = newQty;
      entryFees = clean(entryFees + f.fee);
      continue;
    }

    if (f.qty > Math.abs(signedQty) + 1e-12) {
      // La simulazione non permette di invertire la posizione con un solo eseguito.
      throw new Error(`Il fill ${f.id} supera la quantità residua`);
    }
    const direction: Direction = signedQty > 0 ? 'LONG' : 'SHORT';
    const gross = clean(f.qty * (f.price - avg) * Math.sign(signedQty));
    realizedGross = clean(realizedGross + gross);
    signedQty = clean(signedQty + d);
    closedLegs.push({
      fillId: f.id,
      at: f.at,
      direction,
      qty: f.qty,
      entryPrice: avg,
      exitPrice: f.price,
      gross,
      exitFee: f.fee,
    });
    if (signedQty === 0) avg = 0;
  }

  const balance = clean(initialBalance + realizedGross - fees);
  const position =
    signedQty === 0
      ? null
      : {
          side: (signedQty > 0 ? 'LONG' : 'SHORT') as Direction,
          qty: Math.abs(signedQty),
          avgEntryPrice: avg,
          openedAt,
          openingFillId,
        };

  let unrealizedGross: number | null = null;
  let lastKnownUnrealizedGross: AccountingResult['lastKnownUnrealizedGross'] = null;
  if (position === null) {
    unrealizedGross = 0;
  } else if (mark) {
    const value = clean(position.qty * (mark.price - position.avgEntryPrice) * (position.side === 'LONG' ? 1 : -1));
    lastKnownUnrealizedGross = { value, at: mark.at };
    unrealizedGross = mark.current ? value : null;
  }

  const equity = unrealizedGross === null ? null : clean(balance + unrealizedGross);
  const lastKnownEquity =
    lastKnownUnrealizedGross === null ? null : { value: clean(balance + lastKnownUnrealizedGross.value), at: lastKnownUnrealizedGross.at };

  return {
    position,
    realizedGross,
    fees,
    realizedNet: clean(realizedGross - fees),
    balance,
    unrealizedGross,
    lastKnownUnrealizedGross,
    equity,
    lastKnownEquity,
    closedLegs,
    entryFees,
  };
}
