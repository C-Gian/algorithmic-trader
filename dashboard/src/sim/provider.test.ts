import { describe, expect, it } from 'vitest';
import type { ActionId, Snapshot } from '../contract/types';
import { SimulatedProvider } from './provider';

const make = (checkpoint = 'long-5-protection') => new SimulatedProvider({ exitDelayMs: 0, initialCheckpointId: checkpoint });

/** Opzioni di invio che approvano l'anteprima corrente (impronta del contesto mostrato). */
function approve(p: SimulatedProvider, action: ActionId, acknowledged = false) {
  const preview = p.preview({ action });
  return preview.kind === 'CONFIRM' ? { acknowledged, contextToken: preview.confirmation.contextToken } : { acknowledged };
}

let seq = 0;
function run(p: SimulatedProvider, action: ActionId, acknowledged = false) {
  const preview = p.preview({ action });
  const result = p.dispatch({ action }, `req-${++seq}`, approve(p, action, acknowledged));
  return { preview, result };
}

const protections = (s: Snapshot) => s.orders.filter((o) => o.purpose === 'PROTECTION' && o.status === 'ACCEPTED');

describe('checkpoint predeterminati', () => {
  it('attesa: aspettativa senza call, nessun ordine', () => {
    const s = make('long-1-waiting').getSnapshot();
    expect(s.expectation?.direction).toBe('UNCERTAIN');
    expect(s.call).toBeNull();
    expect(s.plan).toBeNull();
    expect(s.orders).toHaveLength(0);
  });

  it('opportunità: call disponibile senza ordini né posizione', () => {
    const s = make('long-2-opportunity').getSnapshot();
    expect(s.call?.status).toBe('AVAILABLE');
    expect(s.orders).toHaveLength(0);
    expect(s.position).toBeNull();
    expect(s.account.balance.amount).toBe(10000);
  });

  it('ordine accettato non eseguito: nessuna posizione, nessun P&L, nessuna commissione', () => {
    const s = make('long-3-pending').getSnapshot();
    const entry = s.orders.find((o) => o.purpose === 'ENTRY')!;
    expect(entry.status).toBe('ACCEPTED');
    expect(entry.filledQty.amount).toBe(0);
    expect(s.fills).toHaveLength(0);
    expect(s.position).toBeNull();
    expect(s.account.feesCharged.amount).toBe(0);
    expect(s.account.unrealizedGross).toEqual({ value: { amount: 0, currency: 'USDT' } });
  });

  it('ordine rifiutato: nessun fill e nessuna commissione', () => {
    const s = make('long-3r-rejected').getSnapshot();
    const entry = s.orders.find((o) => o.purpose === 'ENTRY')!;
    expect(entry.status).toBe('REJECTED');
    expect(entry.rejection?.code).toBe('SIM-E104');
    expect(s.fills).toHaveLength(0);
    expect(s.account.feesCharged.amount).toBe(0);
    expect(s.position).toBeNull();
  });

  it('posizione LONG: numeri dell’esempio a 61.000', () => {
    const s = make('long-4-open').getSnapshot();
    expect(s.position).toMatchObject({ side: 'LONG', qty: { amount: 0.01 }, avgEntryPrice: { amount: 60000 }, management: 'BOT' });
    expect(s.account.unrealizedGross.value?.amount).toBe(10);
    expect(s.account.balance.amount).toBe(9999.4);
    expect(s.account.equity.value?.amount).toBe(10009.4);
    expect(s.call?.status).toBe('ACTIVE');
    expect(protections(s).map((o) => o.side)).toEqual(['SELL', 'SELL']);
  });

  it('protezione aggiornata: piano originario immutabile, prima/dopo in cronologia, nessun realizzato', () => {
    const s = make('long-5-protection').getSnapshot();
    expect(s.plan?.original.stop.amount).toBe(59000);
    expect(s.plan?.current.stop.amount).toBe(60200);
    expect(s.plan?.changes).toHaveLength(1);
    expect(protections(s).find((o) => o.protectionKind === 'STOP')?.triggerPrice?.amount).toBe(60200);
    const ev = s.history.find((h) => h.type === 'PLAN_CHANGE');
    expect(ev?.change).toEqual({ field: 'Stop', before: '59.000', after: '60.200' });
    expect(s.account.realizedGross.amount).toBe(0);
    expect(s.chart.levels.find((l) => l.id === 'plan-original-stop')?.validTo).not.toBeNull();
  });

  it('uscita parziale e chiusura riproducono i totali del task', () => {
    const partial = make('long-6-partial').getSnapshot();
    expect(partial.position?.qty.amount).toBe(0.006);
    expect(partial.account.balance.amount).toBe(10003.156);
    expect(partial.account.equity.value?.amount).toBe(10009.156);
    expect(protections(partial).every((o) => o.requestedQty.amount === 0.006)).toBe(true);

    const closed = make('long-7-closed').getSnapshot();
    expect(closed.position).toBeNull();
    expect(closed.account.realizedGross.amount).toBe(7);
    expect(closed.account.feesCharged.amount).toBe(1.207);
    expect(closed.account.realizedNet.amount).toBe(5.793);
    expect(closed.account.balance.amount).toBe(10005.793);
    expect(protections(closed)).toHaveLength(0);
    expect(closed.call?.status).toBe('COMPLETED');
    // gli eseguiti sono l'unica fonte delle quantità: ingresso = somma delle uscite
    const sum = (side: string) => closed.fills.filter((f) => f.side === side).reduce((a, f) => a + f.qty.amount, 0);
    expect(sum('BUY')).toBeCloseTo(sum('SELL'), 12);
  });

  it('variante SHORT: ingresso SELL, protezioni BUY sopra il prezzo, numeri a 59.000', () => {
    const s = make('short-4-open').getSnapshot();
    expect(s.fills[0].side).toBe('SELL');
    expect(s.position?.side).toBe('SHORT');
    expect(s.account.unrealizedGross.value?.amount).toBe(10);
    expect(s.account.balance.amount).toBe(9999.4);
    expect(s.account.equity.value?.amount).toBe(10009.4);
    const stop = protections(s).find((o) => o.protectionKind === 'STOP')!;
    expect(stop.side).toBe('BUY');
    expect(stop.triggerPrice!.amount).toBeGreaterThan(s.context.market.lastKnownPrice.value.amount);
  });

  it('le due scale coincidono nei periodi sovrapposti', () => {
    const s = make('long-7-closed').getSnapshot();
    const intraday15 = s.chart.timeframes['45m'].candles.filter((c) => c.openTime.startsWith('2026-10-15'));
    const daily15 = s.chart.timeframes['1D'].candles.at(-1)!;
    expect(daily15.partial).toBe(true);
    expect(daily15.high).toBe(Math.max(...intraday15.map((c) => c.high)));
    expect(daily15.low).toBe(Math.min(...intraday15.map((c) => c.low)));
    expect(daily15.close).toBe(intraday15.at(-1)!.close);
  });
});

describe('percorso di prova dell’Owner', () => {
  it('stop → ripresa → manuale → automatico → parziale → chiusura riconcilia i totali', () => {
    const p = make();
    const before = p.getSnapshot();

    const stop = run(p, 'STOP_TOTAL');
    expect(stop.preview.kind).toBe('CONFIRM');
    let s = p.getSnapshot();
    expect(s.context.bot.status).toBe('STOPPED');
    expect(s.position?.qty.amount).toBe(0.01);
    expect(protections(s)).toHaveLength(2);
    expect(s.account).toEqual(before.account);

    expect(run(p, 'START').result.status).toBe('APPLIED');
    expect(p.getSnapshot().context.bot.status).toBe('RUNNING');

    const manual = run(p, 'TAKE_MANUAL');
    expect(manual.preview.kind).toBe('CONFIRM');
    if (manual.preview.kind === 'CONFIRM') {
      const text = manual.preview.confirmation.consequences.join(' ');
      expect(text).toContain('0,01000 BTC');
      expect(text).toContain('60.200');
      expect(text).toContain('Solo call');
    }
    s = p.getSnapshot();
    expect(s.context.mode).toBe('CALL_ONLY');
    expect(s.position?.management).toBe('MANUAL');
    expect(protections(s)).toHaveLength(2);

    // la ripresa richiede la spunta esplicita di presa in gestione
    const noAck = p.dispatch({ action: 'RESUME_AUTOMATIC' }, 'resume-no-ack', approve(p, 'RESUME_AUTOMATIC'));
    expect(noAck.status).toBe('REJECTED');
    expect(run(p, 'RESUME_AUTOMATIC', true).result.status).toBe('APPLIED');
    s = p.getSnapshot();
    expect(s.context.mode).toBe('CALL_AND_EXECUTION');
    expect(s.position?.management).toBe('BOT');
    expect(s.fills.filter((f) => f.side === 'BUY')).toHaveLength(1);

    run(p, 'PARTIAL_EXIT');
    s = p.getSnapshot();
    expect(s.orders.find((o) => o.purpose === 'EXIT')?.status).toBe('REQUESTED');
    expect(s.position?.qty.amount).toBe(0.01);
    expect(p.completePendingExit()).toBe(true);
    s = p.getSnapshot();
    expect(s.position?.qty.amount).toBe(0.006);
    expect(s.account.balance.amount).toBe(10003.156);

    run(p, 'CLOSE_POSITION');
    expect(p.getSnapshot().position?.qty.amount).toBe(0.006);
    p.completePendingExit();
    s = p.getSnapshot();
    expect(s.position).toBeNull();
    expect(s.account.balance.amount).toBe(10005.793);
    expect(s.account.realizedNet.amount).toBe(5.793);

    p.reset();
    expect(p.getSnapshot().account).toEqual(before.account);
    expect(p.getSnapshot().history).toEqual(before.history);
  });

  it('stop totale non chiude: annulla solo gli ingressi pendenti', () => {
    const p = make('long-3-pending');
    const preview = p.preview({ action: 'STOP_TOTAL' });
    expect(preview.kind).toBe('CONFIRM');
    p.dispatch({ action: 'STOP_TOTAL' }, 'stop-1', approve(p, 'STOP_TOTAL'));
    const s = p.getSnapshot();
    expect(s.orders.find((o) => o.purpose === 'ENTRY')?.status).toBe('CANCELLED');
    expect(s.fills).toHaveLength(0);
  });

  it('il passaggio a Solo call dichiara e annulla l’ingresso pendente', () => {
    const p = make('long-3-pending');
    const preview = p.preview({ action: 'MODE_CALL_ONLY' });
    expect(preview.kind).toBe('CONFIRM');
    if (preview.kind === 'CONFIRM') expect(preview.confirmation.consequences.join(' ')).toContain('verrà annullato');
    p.dispatch({ action: 'MODE_CALL_ONLY' }, 'mode-1', approve(p, 'MODE_CALL_ONLY'));
    expect(p.getSnapshot().orders.find((o) => o.purpose === 'ENTRY')?.status).toBe('CANCELLED');
  });

  it('chiudi posizione funziona con il bot fermo ed è disabilitato senza posizione', () => {
    const p = make('long-5s-stopped');
    expect(p.getSnapshot().context.bot.status).toBe('STOPPED');
    expect(run(p, 'CLOSE_POSITION').result.status).toBe('APPLIED');
    p.completePendingExit();
    expect(p.getSnapshot().position).toBeNull();
    expect(p.getSnapshot().actions.CLOSE_POSITION.enabled).toBe(false);
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'again').status).toBe('REJECTED');
  });

  it('comandi duplicati o click rapidi non duplicano gli eseguiti', () => {
    const p = make();
    const approved = approve(p, 'CLOSE_POSITION');
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'same', approved).status).toBe('APPLIED');
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'same', approved).status).toBe('DUPLICATE');
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'other', approved).status).toBe('REJECTED');
    p.completePendingExit();
    p.completePendingExit();
    const s = p.getSnapshot();
    expect(s.fills.filter((f) => f.side === 'SELL')).toHaveLength(1);
    expect(s.position).toBeNull();
  });

  it('l’anteprima non modifica lo stato (annullare il dialogo lascia tutto invariato)', () => {
    const p = make();
    const before = p.getSnapshot();
    for (const a of ['STOP_TOTAL', 'TAKE_MANUAL', 'PARTIAL_EXIT', 'CLOSE_POSITION'] as const) p.preview({ action: a });
    expect(p.getSnapshot()).toBe(before);
  });
});

describe('dati non aggiornati e disconnessione', () => {
  it('conserva ultimo valore e orario, rende nulli prezzo e P&L correnti', () => {
    const p = make();
    const before = p.getSnapshot();
    p.setFeedCondition('DISCONNECTED');
    const s = p.getSnapshot();
    expect(s.context.feed.status).toBe('DISCONNECTED');
    expect(s.context.market.price).toMatchObject({ value: null, reason: 'UNAVAILABLE' });
    expect(s.context.market.lastKnownPrice).toEqual(before.context.market.lastKnownPrice);
    expect(s.account.unrealizedGross.value).toBeNull();
    expect(s.account.equity.value).toBeNull();
    expect(s.account.lastKnownUnrealizedGross?.value.amount).toBe(10);
    expect(s.position?.valuation.value).toBeNull();
    expect(s.position?.protections.every((x) => x.freshness === 'LAST_KNOWN')).toBe(true);
    expect(Date.parse(s.context.clock.now)).toBeGreaterThan(Date.parse(s.context.feed.observedAt));
  });

  it('la chiusura senza feed resta una richiesta; il ripristino la completa', () => {
    const p = make();
    p.setFeedCondition('STALE');
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'close-stale', approve(p, 'CLOSE_POSITION')).status).toBe('APPLIED');
    expect(p.completePendingExit()).toBe(false);
    let s = p.getSnapshot();
    expect(s.orders.find((o) => o.purpose === 'EXIT')?.status).toBe('REQUESTED');
    expect(s.position?.qty.amount).toBe(0.01);
    expect(s.fills.filter((f) => f.side === 'SELL')).toHaveLength(0);

    p.setFeedCondition('OK');
    expect(p.completePendingExit()).toBe(true);
    s = p.getSnapshot();
    expect(s.position).toBeNull();
    expect(s.orders.find((o) => o.purpose === 'EXIT')?.status).toBe('FILLED');
  });

  it('una richiesta in attesa può essere ritirata senza eseguiti', () => {
    const p = make();
    p.setFeedCondition('DISCONNECTED');
    p.dispatch({ action: 'CLOSE_POSITION' }, 'c1', approve(p, 'CLOSE_POSITION'));
    p.dispatch({ action: 'CANCEL_EXIT_REQUEST' }, 'c2');
    p.setFeedCondition('OK');
    expect(p.completePendingExit()).toBe(false);
    expect(p.getSnapshot().position?.qty.amount).toBe(0.01);
  });
});
