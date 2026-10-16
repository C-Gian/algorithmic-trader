/**
 * Review UI-001/R1: una conferma vale solo per il contesto mostrato (R1-A) e, con feed
 * non regolare, nessun testo attesta l'attualità di posizione e protezioni (R1-B).
 */
import { describe, expect, it } from 'vitest';
import type { ActionId, Snapshot } from '../contract/types';
import { SimulatedProvider } from './provider';

const make = (checkpoint = 'long-5-protection') => new SimulatedProvider({ exitDelayMs: 0, initialCheckpointId: checkpoint });

function previewOf(p: SimulatedProvider, action: ActionId) {
  const preview = p.preview({ action });
  if (preview.kind !== 'CONFIRM') throw new Error(`${action}: attesa una conferma, ottenuto ${preview.kind}`);
  return preview.confirmation;
}

const text = (c: ReturnType<typeof previewOf>) =>
  [c.title, c.lead, ...c.summary, ...c.consequences, c.notice?.title ?? '', c.notice?.text ?? ''].join(' ');

const exits = (s: Snapshot) => s.orders.filter((o) => o.purpose === 'EXIT');
const protections = (s: Snapshot) =>
  s.orders.filter((o) => o.purpose === 'PROTECTION' && o.status === 'ACCEPTED').map((o) => [o.id, o.triggerPrice?.amount ?? o.limitPrice?.amount, o.requestedQty.amount]);

describe('R1-A · la conferma autorizza solo il contesto mostrato', () => {
  it('cambio di scenario a dialogo aperto: nessun ordine sulla posizione SHORT', () => {
    const p = make();
    const shown = previewOf(p, 'CLOSE_POSITION');
    expect(shown.summary[0]).toContain('LONG');
    p.selectCheckpoint('short-4-open');
    const result = p.dispatch({ action: 'CLOSE_POSITION' }, 'stale-close', { contextToken: shown.contextToken });
    expect(result.status).toBe('CONTEXT_CHANGED');
    const s = p.getSnapshot();
    expect(s.position?.side).toBe('SHORT');
    expect(exits(s)).toHaveLength(0);
    // La nuova anteprima descrive la posizione corrente e, approvata, agisce su di essa.
    const fresh = previewOf(p, 'CLOSE_POSITION');
    expect(fresh.contextToken).not.toBe(shown.contextToken);
    expect(fresh.summary[0]).toContain('SHORT');
    expect(fresh.consequences.join(' ')).toContain('lato BUY');
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'fresh-close', { contextToken: fresh.contextToken }).status).toBe('APPLIED');
    expect(exits(p.getSnapshot())[0].side).toBe('BUY');
  });

  it('il reset invalida la conferma anche se riporta allo stesso stato', () => {
    const p = make();
    const shown = previewOf(p, 'STOP_TOTAL');
    p.reset();
    expect(p.dispatch({ action: 'STOP_TOTAL' }, 'after-reset', { contextToken: shown.contextToken }).status).toBe('CONTEXT_CHANGED');
    expect(p.getSnapshot().context.bot.status).toBe('RUNNING');
  });

  it('variazione pertinente nello stesso scenario: quantità cambiata da un eseguito', () => {
    const p = make();
    const partial = previewOf(p, 'PARTIAL_EXIT');
    expect(p.dispatch({ action: 'PARTIAL_EXIT' }, 'partial', { contextToken: partial.contextToken }).status).toBe('APPLIED');
    const manual = previewOf(p, 'TAKE_MANUAL');
    expect(manual.summary.join(' ')).toContain('0,01000 BTC');
    expect(p.completePendingExit()).toBe(true);
    expect(p.dispatch({ action: 'TAKE_MANUAL' }, 'manual', { contextToken: manual.contextToken }).status).toBe('CONTEXT_CHANGED');
    expect(p.getSnapshot().position?.management).toBe('BOT');
    expect(previewOf(p, 'TAKE_MANUAL').summary.join(' ')).toContain('0,00600 BTC');
  });

  it('variazione pertinente nello stesso scenario: feed e bot', () => {
    const p = make();
    const manual = previewOf(p, 'TAKE_MANUAL');
    p.setFeedCondition('DISCONNECTED');
    expect(p.dispatch({ action: 'TAKE_MANUAL' }, 'm1', { contextToken: manual.contextToken }).status).toBe('CONTEXT_CHANGED');

    const q = make();
    const close = previewOf(q, 'CLOSE_POSITION');
    expect(q.dispatch({ action: 'STOP_TOTAL' }, 's1', { contextToken: previewOf(q, 'STOP_TOTAL').contextToken }).status).toBe('APPLIED');
    expect(q.dispatch({ action: 'CLOSE_POSITION' }, 'c1', { contextToken: close.contextToken }).status).toBe('CONTEXT_CHANGED');
    expect(exits(q.getSnapshot())).toHaveLength(0);
  });

  it('un comando con conferma non si applica senza impronta; l’impronta è stabile se nulla cambia', () => {
    const p = make();
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'no-token').status).toBe('REJECTED');
    expect(previewOf(p, 'CLOSE_POSITION').contextToken).toBe(previewOf(p, 'CLOSE_POSITION').contextToken);
    expect(exits(p.getSnapshot())).toHaveLength(0);
  });
});

describe.each(['STALE', 'DISCONNECTED'] as const)('R1-B · feed %s', (condition) => {
  it('dialoghi con ultimi noti, ripresa bloccata, nessuna perdita di posizione o protezioni', () => {
    const p = make();
    const before = p.getSnapshot();
    p.setFeedCondition(condition);
    let s = p.getSnapshot();
    expect(s.context.bot.status).toBe('RUNNING');
    expect(protections(s)).toEqual(protections(before));

    for (const action of ['TAKE_MANUAL', 'STOP_TOTAL', 'PARTIAL_EXIT', 'CLOSE_POSITION'] as const) {
      const t = text(previewOf(p, action));
      expect(t, action).not.toMatch(/restano attivi|possono chiudere la posizione/);
      expect(t, action).toMatch(/ultimi noti|ultimo stato noto/);
    }
    const manual = previewOf(p, 'TAKE_MANUAL');
    expect(manual.consequences[0]).toContain('non sono verificabili ora');
    expect(manual.lead).toContain('azioni automatiche del bot sono sospese');
    expect(manual.notice?.tone).toBe('warning');

    expect(p.dispatch({ action: 'TAKE_MANUAL' }, 'manual', { contextToken: manual.contextToken }).status).toBe('APPLIED');
    s = p.getSnapshot();
    expect(s.position?.management).toBe('MANUAL');
    expect(s.history[s.history.length - 1].text).toContain('non verificabili');
    expect(s.history[s.history.length - 1].text).not.toContain('restano attivi');
    for (const action of ['RESUME_AUTOMATIC', 'MODE_CALL_AND_EXECUTION'] as const) {
      expect(s.actions[action].enabled, action).toBe(false);
      expect(s.actions[action].reason, action).toContain('finché il feed non torna regolare');
      expect(p.preview({ action }).kind).toBe('BLOCKED');
      expect(p.dispatch({ action }, `blocked-${action}`, { acknowledged: true }).status).toBe('REJECTED');
    }
    expect(s.position?.qty).toEqual(before.position?.qty);
    expect(protections(s)).toEqual(protections(before));

    // Al ritorno del feed la ripresa non è automatica: va richiesta e confermata.
    p.setFeedCondition('OK');
    s = p.getSnapshot();
    expect(s.position?.management).toBe('MANUAL');
    expect(s.context.mode).toBe('CALL_ONLY');
    const resume = previewOf(p, 'RESUME_AUTOMATIC');
    expect(resume.acknowledgement).not.toBeNull();
    expect(p.dispatch({ action: 'RESUME_AUTOMATIC' }, 'resume', { contextToken: resume.contextToken, acknowledged: true }).status).toBe('APPLIED');
    s = p.getSnapshot();
    expect(s.position?.management).toBe('BOT');
    expect(protections(s)).toEqual(protections(before));
  });

  it('Start bloccato con bot fermo; dopo il ripristino resta fermo finché l’Owner non conferma', () => {
    const p = make('long-5s-stopped');
    p.setFeedCondition(condition);
    expect(p.getSnapshot().actions.START).toMatchObject({ enabled: false });
    expect(p.getSnapshot().actions.START.reason).toContain('lo Start resta bloccato');
    expect(text(previewOf(p, 'CLOSE_POSITION'))).toContain('ultimi noti');
    p.setFeedCondition('OK');
    expect(p.getSnapshot().context.bot.status).toBe('STOPPED');
    const start = previewOf(p, 'START');
    expect(p.dispatch({ action: 'START' }, 'start', { contextToken: start.contextToken }).status).toBe('APPLIED');
    expect(p.getSnapshot().context.bot.status).toBe('RUNNING');
  });

  it('una richiesta d’uscita resta REQUESTED e il ripristino la completa senza riattivare il bot', () => {
    const p = make('long-5s-stopped');
    p.setFeedCondition(condition);
    const close = previewOf(p, 'CLOSE_POSITION');
    expect(p.dispatch({ action: 'CLOSE_POSITION' }, 'close', { contextToken: close.contextToken }).status).toBe('APPLIED');
    expect(p.completePendingExit()).toBe(false);
    expect(exits(p.getSnapshot())[0].status).toBe('REQUESTED');
    p.setFeedCondition('OK');
    expect(p.completePendingExit()).toBe(true);
    const s = p.getSnapshot();
    expect(s.position).toBeNull();
    expect(s.context.bot.status).toBe('STOPPED');
    expect(s.orders.filter((o) => o.purpose === 'ENTRY' && o.status !== 'FILLED')).toHaveLength(0);
  });
});
