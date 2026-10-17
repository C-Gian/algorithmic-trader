/**
 * Review CAND-001/R1 nella dashboard, su bundle SINTETICI del motore 1.0.1:
 * - R1-B: bundle con finestra interrotta (HALT) e operazione dal percorso irrisolto;
 * - R1-C: nessun prezzo corrente senza una candela completa che termina al momento consultato.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import haltFixture from '../../backtest/__fixtures__/synthetic-backtest-halt.json?raw';
import { FakeApi } from '../../backtest/__fixtures__/fakeApi';
import { parseBacktest } from '../../backtest/loadBacktest';
import { BacktestStudy } from '../../backtest/study';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { EpisodeView } from './EpisodeView';
import { usdt } from './text';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const sim = () => new SimulatedProvider({ exitDelayMs: 0 });
const FILE = { kind: 'file' } as const;
const lastPriceMark = () => document.querySelector('[data-role="last-price"] title')?.textContent ?? null;

async function upload(label: string, text: string) {
  const input = screen.getByLabelText(label, { selector: 'input' }) as HTMLInputElement;
  await act(async () => {
    fireEvent.change(input, { target: { files: [new File([text], 'cand001-bundle.json', { type: 'application/json' })] } });
  });
}

describe('R1-B · bundle con finestra interrotta', () => {
  const halt = () => new BacktestStudy(parseBacktest(haltFixture));

  it('si apre dal selettore: avviso, netto completo mancante, parte nota parziale e chiusure teoriche separate', async () => {
    const s = halt();
    const rec = s.bundle.summary.reconciliation;
    expect(rec.windowComplete).toBe(false);
    expect(rec.unresolvedTrades).toBe(1);
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" api={new FakeApi()} />);
    fireEvent.click(screen.getByRole('link', { name: 'Risultati salvati' }));
    await upload('Apri file esterno', haltFixture);
    await waitFor(() => expect(screen.getByText(/Periodo interrotto il .*risultato completo non disponibile/)).toBeTruthy());
    expect(within(screen.getByRole('region', { name: 'Risultato del backtest' })).getByText('non calcolabile')).toBeTruthy();
    const table = screen.getByLabelText('Da dove viene il risultato');
    const row = (label: string | RegExp, scope = table) => within(scope).getByText(label).closest('tr')!;
    expect(within(row('Risultato dopo i costi')).getAllByText('n.d.').length).toBeGreaterThan(0);
    expect(row('Operazioni irrisolte (percorso non valutabile)').textContent).toContain('1');
    expect(row('Parte nota: solo operazioni concluse (parziale)').textContent).toContain(`${usdt(rec.knownPartNet)} su ${rec.closedTrades}`);
    const stress = screen.getByLabelText('Scenario con costi più alti');
    expect(within(row('Stesse operazioni con costi più severi', stress)).getAllByText('n.d.').length).toBeGreaterThan(0);
    const tech = screen.getByLabelText('Dettagli tecnici');
    expect(within(row('Drawdown massimo (chiusure 1m)', tech)).getAllByText('n.d.').length).toBeGreaterThan(0);
    expect(row('Quota operazioni positive', tech).textContent).toMatch(/solo concluse/);
    expect(row('Tempo in posizione', tech).textContent).toMatch(/solo concluse/);
    const decisions = screen.getByLabelText('Decisioni e operazioni');
    expect(within(decisions).getByText('Copertura del percorso dei prezzi').closest('tr')!.textContent).toMatch(/parziale fino al/);
    expect(within(decisions).getByText(/· non valutate/).closest('tr')!.textContent).toContain(`${rec.notEvaluatedCloses} non valutate`);
  });

  it('un mese dopo la lacuna è «non valutato», non zero', () => {
    const data = JSON.parse(haltFixture);
    const [m0] = Object.keys(data.summary.months);
    const after = structuredClone(data.summary.months[m0]);
    after.coverage = { ...after.coverage, evaluated: false };
    after.trades = { ...after.trades, n: 0, unresolved: 0, net: null };
    after.cashflowByTimestamp = { net: null };
    data.summary.months['2023-02'] = after;
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" initialBacktest={new BacktestStudy(parseBacktest(JSON.stringify(data)))} api={new FakeApi()} />);
    const months = screen.getByLabelText('Mesi');
    expect(within(months).getByText('2023-02').closest('tr')!.textContent).toMatch(/non valutato/);
    expect(within(months).getByText(m0).closest('tr')!.textContent).toMatch(/irrisolta.*parziale/);
  });

  it('registro ed episodio irrisolto: nessuna uscita fittizia, nemmeno col seguito', () => {
    const s = halt();
    const tr = s.bundle.trades.find((t) => t.status === 'UNRESOLVED_DATA_GAP')!;
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" initialBacktest={s} api={new FakeApi()} />);
    fireEvent.click(screen.getByRole('link', { name: `Tutte le operazioni (${s.bundle.trades.length})` }));
    const ledger = screen.getByLabelText('Tutte le operazioni');
    const rows = within(ledger).getAllByRole('row').slice(1);
    const idx = s.bundle.trades.indexOf(tr);
    expect(rows[idx].textContent).toContain('percorso irrisolto');
    expect(rows[idx].textContent).toContain('n.d.');
    fireEvent.click(within(rows[idx]).getByRole('link', { name: /Apri il dettaglio/ }));
    expect(screen.getByText(/^Ha deciso di tentare/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Mostra cosa è successo dopo' }));
    expect(screen.getByText('Esito non calcolabile')).toBeTruthy();
    expect(screen.queryByText(/La posizione è stata chiusa perché/)).toBeNull();
    const result = screen.getByLabelText("Risultato dell'operazione");
    expect(within(result).getByText('Percorso irrisolto: risultato non disponibile')).toBeTruthy();
    const metric = (label: string) => within(result).getByText(label).parentElement!.querySelector('.metric-value')!.textContent;
    expect(metric('Risultato dopo i costi')).toBe('n.d.');
    expect(within(result).getByText(/^Con costi più alti: n\.d\./)).toBeTruthy();
    expect(metric('Commissioni')).toBe(usdt(-tr.feeEntry));
    expect(s.levels(s.episode(tr.episodeId)!, tr.gap!.at + 86_400_000, true).some((l) => l.kind === 'EXIT')).toBe(false);
  });
});

describe('R1-C · prezzo corrente della scala nell’episodio', () => {
  const s = new BacktestStudy(parseBacktest(fixture));
  const tr = s.bundle.trades[0];
  const ep = s.episode(tr.episodeId)!;

  it('alla call (chiusura 45m) il 45m ha il prezzo corrente; il giorno incompleto in 1D no', () => {
    expect(tr.callTime % 86_400_000).not.toBe(0);
    render(<EpisodeView study={s} id={ep.id} initialCursor={tr.callTime} source={FILE} from="operations" />);
    expect(screen.queryByText(/Prezzo al momento non disponibile/)).toBeNull();
    expect(lastPriceMark()).toBe('Prezzo corrente della scala');
    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    expect(screen.getByText('Prezzo al momento non disponibile sulla scala 1D')).toBeTruthy();
    expect(screen.getByText(/Ultimo noto della stessa scala: .* USDT, chiusura alle .* \(non corrente\)/)).toBeTruthy();
    expect(lastPriceMark()).toBeNull();
    // Il seguito non promuove una candela futura a prezzo corrente.
    fireEvent.click(screen.getByRole('button', { name: 'Mostra cosa è successo dopo' }));
    expect(lastPriceMark()).toBeNull();
  });

  it('al momento d’ingresso (t+60s) nessuna scala ha un prezzo corrente', () => {
    expect(tr.entryTime - tr.callTime).toBe(60_000);
    render(<EpisodeView study={s} id={ep.id} initialCursor={tr.entryTime} source={FILE} from="operations" />);
    expect(screen.getByText('Prezzo al momento non disponibile sulla scala 45m')).toBeTruthy();
    expect(screen.getByText(/\(non corrente\)/)).toBeTruthy();
    expect(lastPriceMark()).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    expect(screen.getByText('Prezzo al momento non disponibile sulla scala 1D')).toBeTruthy();
    expect(lastPriceMark()).toBeNull();
  });

  it('tratto senza candele complete: messaggio di indisponibilità, nessun prezzo', () => {
    const data = JSON.parse(fixture);
    const w = data.windows[ep.id];
    w.bars1d.status = w.bars1d.status.map(() => 'MISSING');
    const s2 = new BacktestStudy(parseBacktest(JSON.stringify(data)));
    render(<EpisodeView study={s2} id={ep.id} initialCursor={tr.callTime} source={FILE} from="operations" />);
    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    expect(screen.getByText(/Nessuna candela completa nel tratto entro il momento consultato: prezzo non disponibile/)).toBeTruthy();
    expect(screen.getByLabelText('Grafico 1D: nessuna barra completa nel tratto')).toBeTruthy();
    expect(lastPriceMark()).toBeNull();
  });
});
