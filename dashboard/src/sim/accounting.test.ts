import { describe, expect, it } from 'vitest';
import { computeAccounting } from './accounting';

const fill = (id: string, at: number, side: 'BUY' | 'SELL', qty: number, price: number, fee: number) => ({ id, at, side, qty, price, fee });

describe('contabilità del contratto lineare illustrativo', () => {
  it('riconcilia l’esempio LONG vincolante del task passo per passo', () => {
    const entry = fill('f1', 1, 'BUY', 0.01, 60000, 0.6);
    const open = computeAccounting(10000, [entry], { price: 61000, at: 2, current: true });
    expect(open.position).toMatchObject({ side: 'LONG', qty: 0.01, avgEntryPrice: 60000 });
    expect(open.unrealizedGross).toBe(10);
    expect(open.balance).toBe(9999.4);
    expect(open.equity).toBe(10009.4);
    expect(open.realizedGross).toBe(0);

    const partial = fill('f2', 3, 'SELL', 0.004, 61000, 0.244);
    const afterPartial = computeAccounting(10000, [entry, partial], { price: 61000, at: 3, current: true });
    expect(afterPartial.realizedGross).toBe(4);
    expect(afterPartial.fees).toBe(0.844);
    expect(afterPartial.realizedNet).toBe(3.156);
    expect(afterPartial.balance).toBe(10003.156);
    expect(afterPartial.position?.qty).toBe(0.006);
    expect(afterPartial.unrealizedGross).toBe(6);
    expect(afterPartial.equity).toBe(10009.156);

    const close = fill('f3', 4, 'SELL', 0.006, 60500, 0.363);
    const closed = computeAccounting(10000, [entry, partial, close], { price: 60500, at: 4, current: true });
    expect(closed.position).toBeNull();
    expect(closed.realizedGross).toBe(7);
    expect(closed.fees).toBe(1.207);
    expect(closed.realizedNet).toBe(5.793);
    expect(closed.balance).toBe(10005.793);
    expect(closed.equity).toBe(10005.793);
    expect(closed.closedLegs.map((l) => l.gross)).toEqual([4, 3]);
  });

  it('riconcilia l’esempio SHORT: guadagno quando il prezzo scende', () => {
    const r = computeAccounting(10000, [fill('s1', 1, 'SELL', 0.01, 60000, 0.6)], { price: 59000, at: 2, current: true });
    expect(r.position).toMatchObject({ side: 'SHORT', qty: 0.01 });
    expect(r.unrealizedGross).toBe(10);
    expect(r.balance).toBe(9999.4);
    expect(r.equity).toBe(10009.4);
  });

  it('senza valutazione corrente: P&L e equity assenti, ultimo noto conservato', () => {
    const r = computeAccounting(10000, [fill('f1', 1, 'BUY', 0.01, 60000, 0.6)], { price: 61000, at: 2, current: false });
    expect(r.unrealizedGross).toBeNull();
    expect(r.equity).toBeNull();
    expect(r.lastKnownUnrealizedGross).toEqual({ value: 10, at: 2 });
    expect(r.lastKnownEquity).toEqual({ value: 10009.4, at: 2 });
    expect(r.balance).toBe(9999.4);
  });

  it('nessun eseguito: saldo invariato, zero noto e nessun costo', () => {
    const r = computeAccounting(10000, [], null);
    expect(r.position).toBeNull();
    expect(r.balance).toBe(10000);
    expect(r.fees).toBe(0);
    expect(r.unrealizedGross).toBe(0);
    expect(r.equity).toBe(10000);
  });

  it('rifiuta un eseguito che invertirebbe la posizione', () => {
    expect(() => computeAccounting(10000, [fill('a', 1, 'BUY', 0.01, 60000, 0.6), fill('b', 2, 'SELL', 0.02, 60000, 1.2)], null)).toThrow();
  });
});
