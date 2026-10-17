/**
 * Review CAND-001/R1 nella dashboard, su bundle SINTETICI del motore 1.0.1:
 * - R1-B: bundle con finestra interrotta (HALT) e operazione dal percorso irrisolto;
 * - R1-C: nessun prezzo corrente senza una candela completa che termina al momento consultato.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import haltFixture from '../../backtest/__fixtures__/synthetic-backtest-halt.json?raw';
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
const nav = () => within(screen.getByRole('navigation', { name: 'Navigazione' }));
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
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" />);
    await upload('Apri backtest', haltFixture);
    await waitFor(() => expect(screen.getByText(/Finestra interrotta il .*risultati completi non disponibili/)).toBeTruthy());
    const table = screen.getByLabelText('Risultato modellato');
    const row = (label: string | RegExp) => within(table).getByText(label).closest('tr')!;
    expect(within(row('Netto modellato')).getAllByText('n.d.').length).toBeGreaterThan(0);
    expect(within(row('Netto con costi di stress (10 bp + 10 bp)')).getAllByText('n.d.').length).toBeGreaterThan(0);
    expect(within(row('Drawdown massimo (chiusure 1m)')).getAllByText('n.d.').length).toBeGreaterThan(0);
    expect(row('Operazioni irrisolte (percorso non valutabile)').textContent).toContain('1');
    expect(row('Parte nota: netto delle sole operazioni concluse (parziale)').textContent).toContain(`${usdt(rec.knownPartNet)} su ${rec.closedTrades}`);
    const decisions = screen.getByLabelText('Decisioni e operazioni');
    expect(within(decisions).getByText('Copertura della valutazione').closest('tr')!.textContent).toMatch(/parziale fino al/);
    expect(within(decisions).getByText(/solo teoriche/).closest('tr')!.textContent).toContain(`${rec.notEvaluatedCloses} non valutate`);
  });

  it('un mese dopo la lacuna è «non valutato», non zero', () => {
    const data = JSON.parse(haltFixture);
    const [m0] = Object.keys(data.summary.months);
    const after = structuredClone(data.summary.months[m0]);
    after.coverage = { ...after.coverage, evaluated: false };
    after.trades = { ...after.trades, n: 0, unresolved: 0, net: null };
    after.cashflowByTimestamp = { net: null };
    data.summary.months['2023-02'] = after;
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" initialBacktest={new BacktestStudy(parseBacktest(JSON.stringify(data)))} />);
    const months = screen.getByLabelText('Mesi');
    expect(within(months).getByText('2023-02').closest('tr')!.textContent).toMatch(/non valutato/);
    expect(within(months).getByText(m0).closest('tr')!.textContent).toMatch(/irrisolta.*parziale/);
  });

  it('registro ed episodio irrisolto: nessuna uscita fittizia, nemmeno col seguito', () => {
    const s = halt();
    const tr = s.bundle.trades.find((t) => t.status === 'UNRESOLVED_DATA_GAP')!;
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" initialBacktest={s} />);
    fireEvent.click(nav().getByRole('button', { name: 'Registro operazioni' }));
    const ledger = screen.getByLabelText('Registro operazioni');
    const rows = within(ledger).getAllByRole('row').slice(1);
    const idx = s.bundle.trades.indexOf(tr);
    expect(rows[idx].textContent).toContain('percorso irrisolto');
    expect(rows[idx].textContent).toContain('n.d.');
    fireEvent.click(within(rows[idx]).getByRole('button', { name: 'Apri episodio' }));
    expect(screen.getByText('Ha chiesto un ingresso a queste condizioni')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito modellato' }));
    expect(screen.getByText('Percorso irrisolto')).toBeTruthy();
    expect(screen.queryByText('Uscita modellata')).toBeNull();
    const result = screen.getByLabelText("Risultato modellato dell'operazione");
    expect(within(result).getByText('A POSTERIORI · PERCORSO IRRISOLTO')).toBeTruthy();
    expect(within(result).getByText('Netto modellato').nextElementSibling?.textContent).toBe('n.d.');
    expect(within(result).getByText('Netto con costi di stress').nextElementSibling?.textContent).toBe('n.d.');
    expect(within(result).getByText('Fee assunte').nextElementSibling?.textContent).toBe(usdt(-tr.feeEntry));
    expect(s.levels(s.episode(tr.episodeId)!, tr.gap!.at + 86_400_000, true).some((l) => l.kind === 'EXIT')).toBe(false);
  });
});

describe('R1-C · prezzo corrente della scala nell’episodio', () => {
  const s = new BacktestStudy(parseBacktest(fixture));
  const tr = s.bundle.trades[0];
  const ep = s.episode(tr.episodeId)!;

  it('alla call (chiusura 45m) il 45m ha il prezzo corrente; il giorno incompleto in 1D no', () => {
    expect(tr.callTime % 86_400_000).not.toBe(0);
    render(<EpisodeView study={s} id={ep.id} initialCursor={tr.callTime} onBack={() => {}} />);
    expect(screen.queryByText(/Prezzo al momento non disponibile/)).toBeNull();
    expect(lastPriceMark()).toBe('Prezzo corrente della scala');
    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    expect(screen.getByText('Prezzo al momento non disponibile sulla scala 1D')).toBeTruthy();
    expect(screen.getByText(/Ultimo noto della stessa scala: .* USDT, chiusura alle .* \(non corrente\)/)).toBeTruthy();
    expect(lastPriceMark()).toBeNull();
    // Il seguito non promuove una candela futura a prezzo corrente.
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito modellato' }));
    expect(lastPriceMark()).toBeNull();
  });

  it('al momento d’ingresso (t+60s) nessuna scala ha un prezzo corrente', () => {
    expect(tr.entryTime - tr.callTime).toBe(60_000);
    render(<EpisodeView study={s} id={ep.id} initialCursor={tr.entryTime} onBack={() => {}} />);
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
    render(<EpisodeView study={s2} id={ep.id} initialCursor={tr.callTime} onBack={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    expect(screen.getByText(/Nessuna candela completa nel tratto entro il momento consultato: prezzo non disponibile/)).toBeTruthy();
    expect(screen.getByLabelText('Grafico 1D: nessuna barra completa nel tratto')).toBeTruthy();
    expect(lastPriceMark()).toBeNull();
  });
});
