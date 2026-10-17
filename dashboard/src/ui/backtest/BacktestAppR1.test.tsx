/**
 * APP-001/R1 nell'interfaccia, con servizio finto e fixture SINTETICHE (prezzi inventati):
 * - R1-A: costo pertinente mancante → «risultato dopo i costi non calcolabile», non «completo»;
 * - R1-B: dopo un'interruzione il progresso mostra le chiusure realmente valutate (245/395, valori
 *   del motore reale sull'esempio sintetico di CAND/R1), non 640/640;
 * - R1-C: il ritorno interno ritrova la posizione nel registro e nei risultati;
 * - R1-D: costi della scheda «Nuovo backtest» in percentuali semplici con spiegazioni accessibili.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import { FakeApi, saved } from '../../backtest/__fixtures__/fakeApi';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { clearResultCacheForTests } from './BacktestEnvironment';
import { JOB_POLL } from './JobPage';

const sim = () => new SimulatedProvider({ exitDelayMs: 0 });
const RID = 'CAND-001-v1.0.0-e1.0.3-DEV-r1-test';

let scrollY = 0;
const scrollCalls: number[] = [];
beforeEach(() => {
  JOB_POLL.activeMs = 15;
  JOB_POLL.retryMs = 15;
  clearResultCacheForTests();
  scrollY = 0;
  scrollCalls.length = 0;
  Object.defineProperty(window, 'scrollY', { configurable: true, get: () => scrollY });
  window.scrollTo = ((opts: ScrollToOptions) => {
    scrollY = opts.top ?? 0;
    scrollCalls.push(scrollY);
  }) as typeof window.scrollTo;
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

function at(path: string, api: FakeApi) {
  window.history.replaceState(null, '', `/#${path}`);
  return render(<App createSimulation={sim} api={api} />);
}

/** Bundle sintetico in cui il mark di un pagamento periodico durante la prima operazione manca. */
function missingMarkBundle(): string {
  const d = JSON.parse(fixture);
  const t = d.trades[0];
  const tau = t.entryTime + 5 * 60_000 + 5;
  t.funding = { events: [{ tau, rate: 0.0001, intervalHours: 8, markMinute: tau - (tau % 60_000) - 60_000, M: null, cashflow: null, counted: true, ambiguous: false }], total: null, missing: true, ambiguous: false };
  t.net = null;
  t.netBps = null;
  t.netRange = null;
  t.stress.net = null;
  for (const tab of [d.summary.tables.DEV, ...Object.values(d.summary.periods.filter((p: string) => p !== 'DEV').map((p: string) => d.summary.tables[p]))] as { trades: Record<string, unknown> }[]) {
    for (const k of ['net', 'netBps', 'funding', 'stressNet']) tab.trades[k] = null;
  }
  d.summary.reconciliation.net = null;
  d.run.runId = RID;
  return JSON.stringify(d);
}

describe('R1-A · costo pertinente mancante', () => {
  it('job, risultati salvati e risultato dicono «non calcolabile» con il motivo, non «completo»', async () => {
    const api = new FakeApi();
    api.bundles.set(RID, missingMarkBundle());
    const reason = 'risultato dopo i costi non calcolabile: manca il prezzo mark che valorizza 1 pagamento periodico durante una posizione';
    api.savedResults = [saved(RID, { complete: false, priceCoverageComplete: true, incompleteReason: reason, net: null })];
    const { job } = await api.start('APP_CHECK_2025_01', 'r1a-click-0001');
    const j = api.jobsById.get(job.jobId)!;
    j.state = 'INCOMPLETE';
    j.result = { resultId: RID, bundleSha256: 'x', complete: false, priceCoverageComplete: true, incompleteReason: reason, reusedIdenticalBundle: false, inputHash: 'i', configHash: 'c', counts: { trades: 4, episodes: 9 }, halted: null };
    const view = at(`/backtest/jobs/${job.jobId}`, api);
    expect(await screen.findByText('Storico elaborato, ma risultato dopo i costi non calcolabile')).toBeTruthy();
    expect(screen.getByText(/Risultato dopo i costi non calcolabile: manca il prezzo mark/)).toBeTruthy();
    expect(screen.queryByText(/risultato completo/i)).toBeNull();
    expect(screen.queryByText(/periodo non è valutabile per intero/)).toBeNull(); // non è una lacuna dei prezzi
    view.unmount();

    at('/backtest/saved', api);
    const row = (await screen.findByText(/incompleto: risultato dopo i costi non calcolabile/)).closest('tr')!;
    expect(row.textContent).toContain('non calcolabile (incompleto)');
    cleanup();

    at(`/backtest/results/${RID}`, api);
    const head = await screen.findByRole('region', { name: 'Risultato del backtest' });
    expect(within(head).getByText('non calcolabile')).toBeTruthy();
    const parts = screen.getByRole('region', { name: 'Da dove viene il risultato' });
    expect(within(parts).getByText('Storico elaborato, ma risultato dopo i costi non calcolabile')).toBeTruthy();
    expect(within(parts).getByText(/manca il prezzo di riferimento \(mark\) che valorizza 1 pagamento periodico/)).toBeTruthy();
    expect(within(parts).getByText('Guadagno/perdita dal solo movimento dei prezzi').closest('tr')!.textContent).not.toContain('n.d.'); // componenti note conservate
    expect(within(screen.getByRole('region', { name: 'Decisioni e operazioni' })).getByText('Copertura del percorso dei prezzi').closest('tr')!.textContent).toContain('completa');
  });
});

describe('R1-B · progresso dopo un’interruzione', () => {
  it('mostra 245 chiusure valutate e 395 non valutate, non 640 di 640', async () => {
    const api = new FakeApi();
    const { job } = await api.start('APP_CHECK_2025_01', 'r1b-click-0001');
    const j = api.jobsById.get(job.jobId)!;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const p = j.progress as any;
    const halted = 1673190360000;
    Object.assign(p.stages.check, { status: 'DONE', filesDone: 4, filesExpected: 4 });
    Object.assign(p.stages.init, { status: 'DONE', minutes: 1, prefixMinutes: 0, windowMinutes: 1, steps: {} });
    Object.assign(p.stages.simulate, { status: 'DONE', closesTotal: 640, closes: 245, notEvaluatedCloses: 395, t: halted, haltedAt: halted, episodes: 3, calls: 1, requests: 1, fills: 1, tradesClosed: 0, positionOpen: true, pendingEntry: false });
    Object.assign(p.stages.save, { status: 'DONE' });
    j.state = 'INCOMPLETE';
    j.result = { resultId: RID, bundleSha256: 'x', complete: false, priceCoverageComplete: false, incompleteReason: 'periodo interrotto', reusedIdenticalBundle: false, inputHash: 'i', configHash: 'c', counts: { trades: 1, episodes: 3 }, halted: { at: halted, reason: 'minuto negoziato assente' } };
    at(`/backtest/jobs/${job.jobId}`, api);
    const stages = await screen.findByRole('list', { name: 'Fasi del backtest' });
    expect(within(stages).getByText('interrotta per dati mancanti')).toBeTruthy();
    const alert = within(stages).getByText(/Valutazione interrotta il/).closest('p')!;
    expect(alert.textContent).toMatch(/Chiusure 45m valutate 245 di 640; 395 non valutate dopo la lacuna/);
    expect(within(stages).queryByText(/640 di 640/)).toBeNull();
    expect(within(stages).queryByText(/Data raggiunta/)).toBeNull();
    expect(screen.getByText('Terminato con risultato incompleto')).toBeTruthy();
  });
});

describe('R1-C · ritorno interno con la posizione conservata', () => {
  function withResult() {
    const api = new FakeApi();
    const d = JSON.parse(fixture);
    d.run.runId = RID;
    api.bundles.set(RID, JSON.stringify(d));
    return { api, bundle: d };
  }

  it('registro a 640 px → dettaglio → «Torna alle operazioni» torna a 640; Indietro del browser invariato', async () => {
    const { api } = withResult();
    at(`/backtest/results/${RID}/operations`, api);
    const table = await screen.findByRole('region', { name: 'Tutte le operazioni' });
    scrollY = 640;
    fireEvent.click(within(table).getAllByRole('link', { name: /Apri il dettaglio dell’operazione/ })[2]);
    expect(scrollCalls.at(-1)).toBe(0); // il dettaglio è una pagina nuova
    fireEvent.click(screen.getByRole('link', { name: '← Torna alle operazioni' }));
    await screen.findByRole('region', { name: 'Tutte le operazioni' });
    expect(window.location.hash).toBe(`#/backtest/results/${RID}/operations`);
    expect(scrollCalls.at(-1)).toBe(640);

    // Regressione: anche Indietro del browser ritrova la posizione.
    scrollY = 300;
    fireEvent.click(within(screen.getByRole('region', { name: 'Tutte le operazioni' })).getAllByRole('link', { name: /Apri il dettaglio dell’operazione/ })[0]);
    expect(scrollCalls.at(-1)).toBe(0);
    window.history.back();
    await waitFor(() => expect(window.location.hash).toBe(`#/backtest/results/${RID}/operations`));
    await waitFor(() => expect(scrollCalls.at(-1)).toBe(300));
  });

  it('dalle scorciatoie «Torna ai risultati» ritrova la posizione; un collegamento diretto parte dall’alto', async () => {
    const { api } = withResult();
    at(`/backtest/results/${RID}`, api);
    const ex = await screen.findByRole('region', { name: 'Esempi dal registro' });
    scrollY = 900;
    fireEvent.click(within(ex).getByRole('link', { name: 'Prima operazione' }));
    fireEvent.click(screen.getByRole('link', { name: '← Torna ai risultati' }));
    await screen.findByRole('region', { name: 'Esempi dal registro' });
    expect(scrollCalls.at(-1)).toBe(900);
    cleanup();

    const fresh = withResult();
    clearResultCacheForTests();
    at(`/backtest/results/${RID}/episodes/${encodeURIComponent(fresh.bundle.trades[0].episodeId)}?from=operations`, fresh.api);
    fireEvent.click(await screen.findByRole('link', { name: '← Torna alle operazioni' }));
    await screen.findByRole('region', { name: 'Tutte le operazioni' });
    expect(scrollCalls.at(-1)).toBe(0); // nessuna posizione da ritrovare: registro dall'inizio
  });
});

describe('R1-D · costi della scheda iniziale in parole semplici', () => {
  it('percentuali leggibili, apertura e chiusura, prezzo di esecuzione già incluso, mark spiegato; aiuti da clic e tastiera', async () => {
    at('/backtest/new', new FakeApi());
    const card = await screen.findByRole('region', { name: 'Prova di gennaio 2025' });
    expect(within(card).queryByText(/\bbp\b/)).toBeNull();
    expect(within(card).getByText(/Commissione: 0,05% del valore dell’operazione, pagata all’apertura e alla chiusura/)).toBeTruthy();
    expect(within(card).getByText(/0,03% per lato, già incluso nei prezzi usati/)).toBeTruthy();
    expect(within(card).getByText(/costi più alti \(0,10% di commissione e\s+0,10% di prezzo peggiore per lato\)\. Non è un’impostazione/)).toBeTruthy();
    const fee = within(card).getByRole('button', { name: 'Spiegazione: Commissione' });
    fireEvent.click(fee);
    expect(screen.getByRole('tooltip').textContent).toMatch(/circa 0,50 USDT all’apertura e\s+altrettanti alla chiusura/);
    fireEvent.click(fee);
    const slip = within(card).getByRole('button', { name: 'Spiegazione: Prezzo di esecuzione' });
    fireEvent.focus(slip);
    expect(screen.getByRole('tooltip').textContent).toMatch(/non va sottratto una seconda volta/);
    fireEvent.keyDown(slip, { key: 'Escape' });
    const mark = within(card).getByRole('button', { name: 'Spiegazione: Prezzi mark' });
    fireEvent.focus(mark);
    expect(screen.getByRole('tooltip').textContent).toMatch(/prezzo di riferimento del contratto.*pagamenti periodici/s);
  });
});
