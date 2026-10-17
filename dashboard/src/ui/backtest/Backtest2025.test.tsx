/**
 * Bundle della fase ADDITIONAL_2025 (fixture SINTETICA rietichettata): stessa app, confronto aggiuntivo
 * dichiarato come già esposto e separato dallo sviluppo; un anno uguale alla finestra non è duplicato.
 */
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import { FakeApi } from '../../backtest/__fixtures__/fakeApi';
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
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="BACKTEST" initialBacktest={additional()} api={new FakeApi()} />);
    const head = screen.getByLabelText('Risultato del backtest');
    expect(within(head).getByText(/^Confronto 2025 · dal 01 gen 2023/)).toBeTruthy(); // profilo dedotto dalla fase del bundle /2
    expect(within(head).getByText('2025 GIÀ ESPOSTO · NON È UNA VERIFICA INDIPENDENTE')).toBeTruthy();
    expect(within(head).getByText(/confronto aggiuntivo, separato dallo sviluppo 2023–2024/)).toBeTruthy();
    expect(within(head).getByText(/le operazioni simulate iniziano il/)).toBeTruthy();
    expect(within(head).getByText(/profilo è dedotto dalla fase registrata/)).toBeTruthy();
    const cols = within(screen.getByLabelText('Da dove viene il risultato')).getAllByRole('columnheader').map((c) => c.textContent);
    expect(cols).toEqual(['Voce', 'Confronto 2025']);
    expect(screen.getByRole('link', { name: 'Prima operazione' })).toBeTruthy();
  });
});
