/**
 * APP-001 nella dashboard con un servizio finto (stessi contratti del servizio reale): avvio con un
 * clic e una sola richiesta, job attivo unico, avanzamento dichiarato dal servizio, annullamento,
 * ricaricamento senza nuovi avvii, risultati salvati, registro → dettaglio → Indietro/Avanti.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import { FakeApi, profile, saved } from '../../backtest/__fixtures__/fakeApi';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { scrollMemoryForTests } from '../router';
import { clearResultCacheForTests } from './BacktestEnvironment';
import { JOB_POLL } from './JobPage';

const sim = () => new SimulatedProvider({ exitDelayMs: 0 });
const RID = 'CAND-001-v1.0.0-e1.0.3-APP_CHECK_2025_01-abc-def';

/** Fixture sintetica nello schema /3 come «Prova di gennaio 2025». */
function bundleV3(): string {
  const d = JSON.parse(fixture);
  const ph = 'APP_CHECK_2025_01';
  d.schema = 'cand001.bundle/3';
  d.phase = ph;
  d.summary.phase = ph;
  d.summary.tables[ph] = d.summary.tables.DEV;
  delete d.summary.tables.DEV;
  d.summary.periods = d.summary.periods.map((p: string) => (p === 'DEV' ? ph : p));
  d.profile = { id: ph, label: 'Prova di gennaio 2025', kind: 'PRODUCT_CHECK', registry: 'APP-001/profiles/v1', window: { start: d.window.start, end: d.window.end }, withinPhase: 'ADDITIONAL_2025' };
  d.run.runId = RID;
  return JSON.stringify(d);
}

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
const hash = () => window.location.hash;
const posts = (api: FakeApi) => api.calls.filter((c) => c.startsWith('POST start'));

describe('nuovo backtest', () => {
  it('mostra profili, periodo, prefisso, dimensione e dati; un doppio clic manda una sola richiesta', async () => {
    const api = new FakeApi();
    api.profilesList = [profile(), profile({ id: 'DEV', label: 'Sviluppo 2023–2024', kind: 'DEVELOPMENT' }), profile({ id: 'ADDITIONAL_2025', label: 'Confronto 2025', kind: 'ADDITIONAL_COMPARISON' })];
    at('/backtest/new', api);
    expect(screen.getByText('Simulazione su prezzi storici. Nessuna operazione reale.')).toBeTruthy();
    const card = await screen.findByRole('region', { name: 'Prova di gennaio 2025' });
    expect(within(card).getByText('dal 01 gen 2025 al 31 gen 2025 (UTC)')).toBeTruthy();
    expect(within(card).getByText(/dal ott 2022; nessuna operazione in quel tratto/)).toBeTruthy();
    expect(within(card).getByText(/1\.000 USDT, fissa/)).toBeTruthy();
    expect(within(card).getByText(/✓ tutti i file presenti/)).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Sviluppo 2023–2024' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Confronto 2025' })).toBeTruthy();
    expect(posts(api)).toHaveLength(0); // nessun calcolo al montaggio
    const start = within(card).getByRole('button', { name: 'Avvia' });
    fireEvent.click(start);
    fireEvent.click(start);
    await waitFor(() => expect(hash()).toMatch(/^#\/backtest\/jobs\/job-/));
    expect(posts(api)).toHaveLength(1);
    expect(api.jobsById.size).toBe(1);
  });

  it('risposta persa: la ripetizione usa la stessa chiave e ritrova lo stesso job', async () => {
    const api = new FakeApi();
    api.failNextStart = 1;
    at('/backtest/new', api);
    fireEvent.click(await screen.findByRole('button', { name: 'Avvia' }));
    await waitFor(() => expect(hash()).toMatch(/jobs\/job-/), { timeout: 3000 });
    const [a, b] = posts(api);
    expect(a.split(' ').at(-1)).toBe(b.split(' ').at(-1));
    expect(api.jobsById.size).toBe(1);
  });

  it('con un backtest già in corso: avviso con collegamento e nessun nuovo avvio', async () => {
    const api = new FakeApi();
    await api.start('APP_CHECK_2025_01', 'other-tab-0001');
    at('/backtest/new', api);
    const notice = await screen.findByText('C’è già un backtest in corso');
    expect(notice).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Segui il backtest in corso' }).getAttribute('href')).toMatch(/#\/backtest\/jobs\/job-/);
    expect(screen.getByRole('button', { name: 'Avvia' }).hasAttribute('disabled')).toBe(true);
  });

  it('dati mancanti: avvio non possibile e nessun download', async () => {
    const api = new FakeApi();
    api.profilesList = [profile({ availability: { ...profile().availability, available: false, missing: [{ kind: 'trade', month: '2024-11', reason: 'file assente sul disco' }] } })];
    at('/backtest/new', api);
    expect(await screen.findByText('Dati mancanti: avvio non possibile')).toBeTruthy();
    expect(screen.getByText(/trade 2024-11: file assente sul disco/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Avvia' }).hasAttribute('disabled')).toBe(true);
  });

  it('servizio spento: lo dice, senza inventare profili o risultati', async () => {
    const api = new FakeApi();
    api.down = true;
    at('/backtest/new', api);
    expect(await screen.findByText('Servizio locale non raggiungibile')).toBeTruthy();
    expect(screen.queryByText('Risultato dopo i costi')).toBeNull();
  });
});

describe('pagina dell’esecuzione', () => {
  it('avanzamento reale, conteggi assenti prima del motore, annullamento richiesto poi esito; ricaricamento senza nuovo avvio', async () => {
    const api = new FakeApi();
    const { job } = await api.start('APP_CHECK_2025_01', 'click-0000001');
    const j = api.jobsById.get(job.jobId)!;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const p = j.progress as any;
    Object.assign(p.stages.check, { status: 'RUNNING', startedAt: '2026-10-17T12:00:00.100Z', filesExpected: 30, filesDone: 3, byKind: { trade: { expected: 28, done: 3 }, funding: { expected: 1, done: 0 }, mark: { expected: 1, done: 0 } }, current: { kind: 'trade', month: '2023-01', rows: 20000 } });
    p.stage = 'check';
    const view = at(`/backtest/jobs/${job.jobId}`, api);
    const stages = await screen.findByRole('list', { name: 'Fasi del backtest' });
    expect(within(stages).getByText(/File controllati:/).textContent).toContain('3 di 30');
    expect(within(stages).getByText(/prezzi al minuto di 2023-01, righe lette 20\.000/)).toBeTruthy();
    expect(within(stages).queryByText(/Data raggiunta/)).toBeNull(); // fase non ancora iniziata: nessun conteggio
    expect(screen.queryByRole('link', { name: 'Apri risultati' })).toBeNull();

    Object.assign(p.stages.check, { status: 'DONE', finishedAt: '2026-10-17T12:00:01.000Z', filesDone: 30 });
    Object.assign(p.stages.init, { status: 'DONE', startedAt: '2026-10-17T12:00:01.000Z', finishedAt: '2026-10-17T12:00:01.900Z', minutes: 1_226_880, prefixMinutes: 1_182_240, windowMinutes: 44_640, steps: {} });
    Object.assign(p.stages.simulate, { status: 'RUNNING', startedAt: '2026-10-17T12:00:01.900Z', closesTotal: 992, closes: 320, t: Date.UTC(2025, 0, 11), episodes: 5, calls: 2, requests: 2, fills: 1, tradesClosed: 1, positionOpen: false, pendingEntry: false });
    p.stage = 'simulate';
    await waitFor(() => expect(screen.getByText(/chiusure 45m valutate 320 di 992/)).toBeTruthy());
    expect(screen.getByText(/operazioni\s+concluse 1/)).toBeTruthy();
    expect(screen.getByText(/1\.182\.240 di storia usata solo per osservare/)).toBeTruthy();
    expect(screen.getByRole('progressbar', { name: 'Chiusure valutate' }).getAttribute('aria-valuenow')).toBe('320');

    fireEvent.click(screen.getByRole('button', { name: 'Annulla backtest' }));
    await waitFor(() => expect(screen.getByText('Annullamento richiesto')).toBeTruthy());
    expect(screen.getByText('ANNULLAMENTO RICHIESTO')).toBeTruthy(); // non ancora «annullato»
    j.state = 'CANCELLED';
    j.finishedAt = '2026-10-17T12:00:04.000Z';
    p.stages.simulate.status = 'STOPPED';
    await waitFor(() => expect(screen.getByText('Backtest annullato: nessun risultato')).toBeTruthy());
    expect(screen.queryByRole('link', { name: 'Apri risultati' })).toBeNull();
    expect(screen.queryByText(/100%/)).toBeNull();

    view.unmount(); // ricaricamento della pagina
    const before = api.calls.length;
    at(`/backtest/jobs/${job.jobId}`, api);
    expect(await screen.findByText('Backtest annullato: nessun risultato')).toBeTruthy();
    expect(api.calls.slice(before).every((c) => c.startsWith('GET'))).toBe(true);
    expect(posts(api)).toHaveLength(1);
  });

  it('servizio che smette di rispondere: stato non aggiornato, nessun esito presunto', async () => {
    const api = new FakeApi();
    const { job } = await api.start('APP_CHECK_2025_01', 'click-0000002');
    at(`/backtest/jobs/${job.jobId}`, api);
    expect(await screen.findByText('IN CORSO')).toBeTruthy();
    api.down = true;
    await waitFor(() => expect(screen.getByText('Stato non aggiornato')).toBeTruthy());
    expect(screen.getByText('IN CORSO')).toBeTruthy();
    expect(screen.queryByText(/completato/i)).toBeNull();
  });

  it('esecuzione inesistente: messaggio e via d’uscita', async () => {
    at('/backtest/jobs/job-20991231T000000Z-ffffff', new FakeApi());
    expect(await screen.findByText('Esecuzione non trovata')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Vai ai risultati salvati' })).toBeTruthy();
  });
});

describe('risultato salvato, registro e dettaglio', () => {
  function completed() {
    const api = new FakeApi();
    api.bundles.set(RID, bundleV3());
    api.savedResults = [saved(RID)];
    return api;
  }

  it('dal job completato ai risultati, a tutte le operazioni e al dettaglio; Indietro/Avanti e scorrimento', async () => {
    const api = completed();
    const { job } = await api.start('APP_CHECK_2025_01', 'click-0000003');
    const j = api.jobsById.get(job.jobId)!;
    j.state = 'COMPLETED';
    j.result = { resultId: RID, bundleSha256: 'x', complete: true, reusedIdenticalBundle: false, inputHash: 'i', configHash: 'c', counts: { trades: 4, episodes: 9 }, halted: null };
    at(`/backtest/jobs/${job.jobId}`, api);
    fireEvent.click(await screen.findByRole('link', { name: 'Apri risultati' }));
    expect(hash()).toBe(`#/backtest/results/${RID}`);
    const head = await screen.findByRole('region', { name: 'Risultato del backtest' });
    expect(within(head).getByText(/Prova di gennaio 2025/)).toBeTruthy();
    expect(within(head).getByText('COLLAUDO DEL PRODOTTO')).toBeTruthy();
    expect(within(head).queryByText(/confronto aggiuntivo/i)).toBeNull(); // gennaio non è l'intero confronto 2025
    fireEvent.click(within(head).getByRole('link', { name: 'Tutte le operazioni (4)' }));
    expect(hash()).toBe(`#/backtest/results/${RID}/operations`);
    const table = screen.getByRole('region', { name: 'Tutte le operazioni' });
    const links = within(table).getAllByRole('link', { name: /Apri il dettaglio dell’operazione/ });
    expect(links).toHaveLength(4);
    scrollY = 640; // l'utente è sceso nel registro
    fireEvent.click(links[2]);
    expect(hash()).toMatch(/\/episodes\/.+\?from=operations$/);
    expect(screen.getByRole('link', { name: '← Torna alle operazioni' })).toBeTruthy();
    expect(scrollCalls.at(-1)).toBe(0);
    const detailHash = hash();

    act(() => window.history.back());
    await waitFor(() => expect(hash()).toBe(`#/backtest/results/${RID}/operations`));
    await waitFor(() => expect(screen.getByRole('region', { name: 'Tutte le operazioni' })).toBeTruthy());
    expect(scrollCalls.at(-1)).toBe(640); // posizione del registro ritrovata
    act(() => window.history.forward());
    await waitFor(() => expect(hash()).toBe(detailHash));
    expect(await screen.findByRole('link', { name: '← Torna alle operazioni' })).toBeTruthy();
    expect(api.calls.filter((c) => c.startsWith('GET bundle'))).toHaveLength(1); // letto una volta, non a ogni vista
    expect(scrollMemoryForTests().get(`/backtest/results/${RID}/operations`)).toBe(640);
  });

  it('ricaricando un dettaglio si rilegge il risultato dal servizio, senza avvii', async () => {
    const api = completed();
    const d = JSON.parse(bundleV3());
    at(`/backtest/results/${RID}/episodes/${encodeURIComponent(d.trades[0].episodeId)}?from=examples`, api);
    expect(await screen.findByRole('link', { name: '← Torna ai risultati' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Tutte le operazioni' })).toBeTruthy();
    expect(posts(api)).toHaveLength(0);
  });

  it('risultato o episodio inesistente: messaggio, nessun grafico vuoto', async () => {
    const api = completed();
    at('/backtest/results/CAND-001-non-esiste', api);
    expect(await screen.findByText('Risultato non trovato')).toBeTruthy();
    cleanup();
    at(`/backtest/results/${RID}/episodes/EP-inesistente?from=operations`, api);
    expect(await screen.findByText('Episodio non trovato')).toBeTruthy();
    expect(screen.queryByLabelText("Grafico dell'episodio")).toBeNull();
    expect(screen.getByRole('link', { name: '← Torna alle operazioni' })).toBeTruthy();
  });

  it('risultati salvati: stato di ogni riga, profilo dedotto, formati non apribili ed esecuzioni', async () => {
    const api = completed();
    api.savedResults = [
      saved(RID),
      saved('CAND-001-v1.0.0-e1.0.2-ADDITIONAL_2025-x', { profile: { id: 'ADDITIONAL_2025', label: 'Confronto 2025', kind: 'ADDITIONAL_COMPARISON', window: { start: Date.UTC(2025, 0, 1), end: Date.UTC(2026, 0, 1) }, inferred: true }, window: { start: Date.UTC(2025, 0, 1), end: Date.UTC(2026, 0, 1) }, via: 'DIRECT', schema: 'cand001.bundle/2' }),
      saved('CAND-001-v1.0.0-e1.0.0-DEV-old', { status: 'UNSUPPORTED_SCHEMA', reason: 'schema cand001.bundle/1 conservato', schema: 'cand001.bundle/1' }),
      saved('CAND-001-partial', { status: 'NOT_OPENABLE', reason: 'manifest del run assente', profile: null, window: null }),
      saved('CAND-001-halted', { complete: false, halted: { at: 1, reason: 'gap' }, net: null }),
    ];
    at('/backtest/saved', api);
    const table = await screen.findByRole('region', { name: 'Risultati salvati' });
    const row = (text: string | RegExp) => within(table).getAllByText(text)[0].closest('tr')!;
    expect(row('(profilo dedotto dalla fase)').textContent).toMatch(/comando diretto/);
    expect(row(/formato vecchio, conservato ma non apribile/).textContent).toContain('non apribile');
    expect(row(/non apribile: manifest del run assente/)).toBeTruthy();
    expect(row(/incompleto: periodo interrotto/).textContent).toContain('non calcolabile');
    expect(within(table).getAllByRole('link', { name: /^Apri / })).toHaveLength(3);
    expect(posts(api)).toHaveLength(0); // consultare non ricalcola
  });

  it('file esterno solo in memoria: dopo il ricaricamento si chiede di riaprirlo e si torna alla stessa vista', async () => {
    const api = new FakeApi();
    const d = JSON.parse(fixture);
    const ep = d.trades[0].episodeId;
    at(`/backtest/file/episodes/${encodeURIComponent(ep)}?from=operations`, api);
    expect(screen.getByText('Il file esterno va riaperto')).toBeTruthy();
    const input = screen.getByLabelText('Riapri il file', { selector: 'input' }) as HTMLInputElement;
    await act(async () => {
      fireEvent.change(input, { target: { files: [new File([fixture], 'cand001-bundle.json', { type: 'application/json' })] } });
    });
    await waitFor(() => expect(screen.getByRole('link', { name: '← Torna alle operazioni' })).toBeTruthy());
    expect(hash()).toBe(`#/backtest/file/episodes/${encodeURIComponent(ep)}?from=operations`);
  });
});
