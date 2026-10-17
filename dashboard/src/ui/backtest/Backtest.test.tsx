/**
 * CAND-001 nella dashboard, su bundle di backtest SINTETICO prodotto dal motore (prezzi inventati).
 * Import e contratto, pagina risultati, esempi con un clic, vista causale vs seguito a posteriori,
 * astensione, registro e separazione dalla simulazione.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import obsFixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import { BacktestBundleError, parseBacktest } from '../../backtest/loadBacktest';
import { BacktestStudy } from '../../backtest/study';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { usdt } from './text';

const BANNER = 'BACKTEST DI SVILUPPO — esecuzioni modellate, nessun collegamento exchange';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const study = () => new BacktestStudy(parseBacktest(fixture));
const sim = () => new SimulatedProvider({ exitDelayMs: 0 });
const env = (name: string) => within(screen.getByRole('group', { name: 'Ambiente', hidden: true })).getByRole('button', { name, hidden: true });
const nav = () => within(screen.getByRole('navigation', { name: 'Navigazione' }));

async function upload(label: string, text: string) {
  const input = screen.getByLabelText(label, { selector: 'input' }) as HTMLInputElement;
  await act(async () => {
    fireEvent.change(input, { target: { files: [new File([text], 'cand001-bundle.json', { type: 'application/json' })] } });
  });
}

function setup() {
  const s = study();
  render(<App createSimulation={sim} initialEnvironment="BACKTEST" initialBacktest={s} />);
  return s;
}

describe('import del backtest', () => {
  it('senza file: istruzione di apertura, nessun risultato inventato', () => {
    render(<App createSimulation={sim} />);
    fireEvent.click(env('Backtest di sviluppo'));
    expect(screen.getByText(BANNER)).toBeTruthy();
    expect(screen.getByText(/nessun risultato aperto/)).toBeTruthy();
    expect(screen.queryByText(/Netto modellato/)).toBeNull();
    expect(screen.queryByRole('button', { name: /Scenari simulati/ })).toBeNull();
  });

  it('file di altro tipo o incompleto: errore leggibile; il backtest aperto resta; poi file valido', async () => {
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" />);
    await upload('Apri backtest', obsFixture);
    await waitFor(() => expect(screen.getByText(/bundle dello studio osservativo OBS-001/)).toBeTruthy());
    await upload('Apri backtest', fixture);
    await waitFor(() => expect(screen.getByText(/Apri un episodio con un clic/)).toBeTruthy());
    const broken = JSON.parse(fixture);
    delete broken.trades[0].exit.Xref;
    await upload('Apri altro backtest', JSON.stringify(broken));
    await waitFor(() => expect(screen.getByText(/Operazioni, 1ª, uscita: valore «Xref» assente/)).toBeTruthy());
    expect(screen.getByText(/Apri un episodio con un clic/)).toBeTruthy(); // backtest precedente conservato
  });

  it('il validatore richiede finestre per gli esempi e campi annidati dei mesi', () => {
    const noWindow = JSON.parse(fixture);
    const ref = noWindow.summary.examples.LONG.FIRST_TRADE;
    delete noWindow.windows[ref.episodeId];
    expect(() => parseBacktest(JSON.stringify(noWindow))).toThrow(/finestra del grafico assente/);
    const month = JSON.parse(fixture);
    const m = Object.keys(month.summary.months)[0];
    delete month.summary.months[m].trades.exits.STOP;
    expect(() => parseBacktest(JSON.stringify(month))).toThrow(BacktestBundleError);
  });
});

describe('risultati ed episodi', () => {
  it('la pagina risultati mostra netto, costi, periodi ed esempi; categoria assente dichiarata', () => {
    setup();
    expect(screen.getByText(BANNER)).toBeTruthy();
    expect(screen.getByText('Netto modellato')).toBeTruthy();
    expect(screen.getByText('Fee assunte')).toBeTruthy();
    expect(screen.getByText(/FIXTURE SINTETICA/)).toBeTruthy();
    for (const label of ['Prima decisione', 'Prima operazione', 'Primo caso negativo', 'Prima astensione']) {
      expect(screen.getByRole('button', { name: label })).toBeTruthy();
    }
    const absent = screen.getByRole('button', { name: 'Prima protezione aggiornata · assente' });
    expect(absent.hasAttribute('disabled')).toBe(true);
    expect(screen.queryByText(/10\.000|saldo personale/)).toBeNull();
  });

  it('un clic apre l’operazione al momento della decisione; il seguito solo su richiesta', () => {
    const s = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Prima operazione' }));
    expect(screen.getByText('Ha riconosciuto questo movimento')).toBeTruthy();
    expect(screen.getByText('Ha chiesto un ingresso a queste condizioni')).toBeTruthy();
    expect(screen.getByText('SOLO INFORMAZIONI AL MOMENTO')).toBeTruthy();
    expect(screen.queryByText('Uscita modellata')).toBeNull();
    expect(screen.queryByLabelText("Risultato modellato dell'operazione")).toBeNull();
    // Il grafico mostra solo candele terminate entro il momento della decisione.
    const ref = s.headlines().find((h) => h.label === 'Prima operazione')!.ref!;
    const ep = s.episode(ref.episodeId!)!;
    expect(s.candles(ep.id, '45m', ep.call!.t, false).every((c) => c.end <= ep.call!.t)).toBe(true);
    expect(s.levels(ep, ep.call!.t, false).some((l) => l.kind === 'EXIT')).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito modellato' }));
    expect(screen.getByText('Uscita modellata')).toBeTruthy();
    const result = screen.getByLabelText("Risultato modellato dell'operazione");
    expect(within(result).getByText('A POSTERIORI')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Solo informazioni al momento della decisione' }));
    expect(screen.queryByLabelText("Risultato modellato dell'operazione")).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: '← Risultati' }));
    expect(screen.getByText(/Apri un episodio con un clic/)).toBeTruthy();
  });

  it('primo caso negativo e prima astensione spiegano il motivo', () => {
    const s = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Primo caso negativo' }));
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito modellato' }));
    const neg = s.trade(s.headlines().find((h) => h.label === 'Primo caso negativo')!.ref!.id)!;
    expect(neg.net!).toBeLessThan(0);
    const result = screen.getByLabelText("Risultato modellato dell'operazione");
    expect(within(result).getByText('Netto modellato').nextElementSibling?.textContent).toBe(usdt(neg.net));
    fireEvent.click(screen.getByRole('button', { name: '← Risultati' }));
    fireEvent.click(screen.getByRole('button', { name: 'Prima astensione' }));
    expect(screen.getByText('Si è astenuto')).toBeTruthy();
    expect(screen.queryByText('Ingresso modellato')).toBeNull();
  });

  it('il registro elenca tutte le operazioni e apre l’episodio', () => {
    const s = setup();
    fireEvent.click(nav().getByRole('button', { name: 'Registro operazioni' }));
    const table = screen.getByLabelText('Registro operazioni');
    expect(within(table).getAllByRole('button', { name: 'Apri episodio' })).toHaveLength(s.bundle.trades.length);
    fireEvent.click(within(table).getAllByRole('button', { name: 'Apri episodio' })[0]);
    expect(screen.getByText('Ha riconosciuto questo movimento')).toBeTruthy();
  });

  it('i comandi della simulazione non modificano i risultati congelati', () => {
    const s = setup();
    const before = JSON.stringify(s.bundle.summary.tables);
    fireEvent.click(env('Simulazione locale'));
    fireEvent.click(screen.getByRole('button', { name: 'Stop totale' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Ferma il bot' }));
    fireEvent.click(env('Backtest di sviluppo'));
    expect(screen.getByText(/Apri un episodio con un clic/)).toBeTruthy();
    expect(JSON.stringify(s.bundle.summary.tables)).toBe(before);
  });
});
