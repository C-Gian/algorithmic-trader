/**
 * Bundle della fase ADDITIONAL_2025 (fixture SINTETICA rietichettata): stessa app, confronto aggiuntivo
 * dichiarato come già esposto e separato dallo sviluppo; un anno uguale alla finestra non è duplicato.
 */
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import { parseBacktest } from '../../backtest/loadBacktest';
import { BacktestStudy } from '../../backtest/study';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

function additional(): BacktestStudy {
  const data = JSON.parse(fixture);
  data.phase = 'ADDITIONAL_2025';
  data.summary.phase = 'ADDITIONAL_2025';
  data.summary.tables.ADDITIONAL_2025 = data.summary.tables.DEV;
  delete data.summary.tables.DEV;
  data.summary.periods = data.summary.periods.map((p: string) => (p === 'DEV' ? 'ADDITIONAL_2025' : p));
  return new BacktestStudy(parseBacktest(JSON.stringify(data)));
}

describe('confronto aggiuntivo 2025', () => {
  it('dichiara la fase, il riuso già esposto e un solo periodo per la finestra', () => {
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="BACKTEST" initialBacktest={additional()} />);
    const head = screen.getByLabelText('Confronto aggiuntivo 2025');
    expect(within(head).getByText(/confronto aggiuntivo 2025/)).toBeTruthy();
    expect(within(head).getByText('2025 GIÀ ESPOSTO · NON VALIDAZIONE INDIPENDENTE')).toBeTruthy();
    expect(within(head).getByText(/non è una prova su dati mai visti/)).toBeTruthy();
    expect(within(head).getByText(/ripartono da zero/)).toBeTruthy();
    const cols = within(screen.getByLabelText('Risultato modellato')).getAllByRole('columnheader').map((c) => c.textContent);
    expect(cols).toEqual(['Voce', '2025']);
    expect(screen.queryByLabelText('Backtest di sviluppo')).toBeNull();
    expect(screen.getByRole('button', { name: 'Prima operazione' })).toBeTruthy();
  });
});
