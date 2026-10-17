/**
 * Navigazione comune (#/...): percorsi validi e ID opachi, Indietro/Avanti negli ambienti esistenti,
 * studio storico solo in memoria spiegato dopo un ricaricamento con ritorno al momento richiesto.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../historical/__fixtures__/synthetic-bundle.json?raw';
import { FakeApi } from '../backtest/__fixtures__/fakeApi';
import { SimulatedProvider } from '../sim/provider';
import { App } from './App';
import { parse, paths } from './router';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const sim = () => new SimulatedProvider({ exitDelayMs: 0 });

describe('percorsi', () => {
  it('ogni vista ha un indirizzo e si rilegge uguale', () => {
    const src = { kind: 'saved', id: 'CAND-001-v1.0.0-e1.0.3-APP_CHECK_2025_01-a-b' } as const;
    const ep = 'EP:BTCUSDT:45m:1735700000000:LONG';
    expect(parse(paths.job('job-20261017T120000Z-abcdef'))).toEqual({ env: 'BACKTEST', page: 'job', jobId: 'job-20261017T120000Z-abcdef' });
    expect(parse(paths.operations(src))).toEqual({ env: 'BACKTEST', page: 'result', source: src, view: 'operations' });
    expect(parse(paths.episode(src, ep, 'examples'))).toEqual({ env: 'BACKTEST', page: 'episode', source: src, episodeId: ep, from: 'examples' });
    expect(parse(paths.episode({ kind: 'file' }, ep, 'operations'))).toMatchObject({ page: 'episode', source: { kind: 'file' }, from: 'operations' });
    expect(parse(paths.historical('dashboard', 1735700000000))).toEqual({ env: 'HISTORICAL', view: 'dashboard', t: 1735700000000 });
    expect(parse(paths.historical('research'))).toEqual({ env: 'HISTORICAL', view: 'research' });
    expect(parse('/simulation/settings')).toEqual({ env: 'SIMULATION', view: 'settings' });
    expect(parse('')).toEqual({ env: 'SIMULATION', view: 'dashboard' });
  });

  it('ID che non sono identificatori semplici non diventano percorsi', () => {
    expect(parse('/backtest/results/..%2F..%2Fmanifests').env).toBe('UNKNOWN');
    expect(parse('/backtest/jobs/a%20b').env).toBe('UNKNOWN');
    expect(parse('/backtest/results/x/qualcosa').env).toBe('UNKNOWN');
    expect(parse('/altro').env).toBe('UNKNOWN');
  });

  it('indirizzo sconosciuto: pagina spiegata con vie d’uscita', () => {
    window.history.replaceState(null, '', '/#/backtest/inesistente');
    render(<App createSimulation={sim} api={new FakeApi()} />);
    expect(screen.getByText('Pagina non trovata')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Backtest' })).toBeTruthy();
  });
});

describe('ambienti esistenti', () => {
  it('simulazione: le voci sono indirizzi e Indietro torna alla vista precedente; il selettore non è un Indietro', async () => {
    render(<App createSimulation={sim} api={new FakeApi()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Impostazioni' }));
    expect(window.location.hash).toBe('#/simulation/settings');
    expect(screen.getByText('Non disponibile in questa versione.')).toBeTruthy();
    act(() => window.history.back());
    await waitFor(() => expect(screen.getByRole('button', { name: 'Stop totale' })).toBeTruthy());
    const envs = within(screen.getByRole('group', { name: 'Ambiente' }));
    fireEvent.click(envs.getByRole('button', { name: 'Studio storico' }));
    expect(window.location.hash).toBe('#/historical');
    act(() => window.history.back());
    await waitFor(() => expect(window.location.hash).toBe(''));
    expect(screen.getByText(/riparte dallo scenario iniziale/)).toBeTruthy(); // la simulazione dichiara il ripristino
  });

  it('studio storico solo in memoria: ricaricando un momento si chiede di riaprire e si torna lì', async () => {
    const data = JSON.parse(fixture);
    const t = data.origins[5];
    window.history.replaceState(null, '', `/#/historical/at/${t}`);
    render(<App createSimulation={sim} api={new FakeApi()} />);
    expect(screen.getByText('Lo studio va riaperto')).toBeTruthy();
    expect(screen.getByText(/Dopo l’apertura tornerai al momento/)).toBeTruthy();
    const input = screen.getByLabelText('Apri studio storico', { selector: 'input' }) as HTMLInputElement;
    await act(async () => {
      fireEvent.change(input, { target: { files: [new File([fixture], 'obs001-bundle.json', { type: 'application/json' })] } });
    });
    await waitFor(() => expect(screen.getByText(/Origine 6 di 64/)).toBeTruthy());
    expect(window.location.hash).toBe(`#/historical/at/${t}`);
    fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
    expect(screen.getByText(/Origine 7 di 64/)).toBeTruthy();
    expect(window.location.hash).toBe(`#/historical/at/${data.origins[6]}`); // sostituisce la voce, nessuna cronologia a ogni passo
    fireEvent.click(screen.getByRole('button', { name: 'Studio osservativo' }));
    expect(window.location.hash).toBe('#/historical/summary');
    act(() => window.history.back());
    await waitFor(() => expect(screen.getByText(/Origine 7 di 64/)).toBeTruthy());
  });
});
