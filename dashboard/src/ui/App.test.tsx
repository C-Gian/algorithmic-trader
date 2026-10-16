import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { SimulatedProvider } from '../sim/provider';
import { App } from './App';

afterEach(cleanup);
// jsdom non implementa lo scorrimento.
window.scrollTo = () => {};

function setup(checkpoint = 'long-5-protection') {
  const provider = new SimulatedProvider({ exitDelayMs: 0, initialCheckpointId: checkpoint });
  render(<App provider={provider} controls={provider} />);
  return provider;
}

describe('interazioni della dashboard', () => {
  it('mostra sempre il banner di simulazione', () => {
    setup();
    expect(screen.getByText('SIMULAZIONE LOCALE — nessun collegamento exchange')).toBeTruthy();
    expect(screen.queryByText(/Binance Demo/)).toBeNull();
  });

  it('annullare la conferma di stop totale lascia tutto invariato', () => {
    const provider = setup();
    const before = provider.getSnapshot();
    fireEvent.click(screen.getByRole('button', { name: 'Stop totale' }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('Fermare il bot, non la posizione?')).toBeTruthy();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Annulla' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(provider.getSnapshot()).toBe(before);
  });

  it('un doppio click sulla conferma di chiusura produce una sola richiesta', () => {
    const provider = setup();
    fireEvent.click(screen.getAllByRole('button', { name: 'Chiudi posizione' })[0]);
    const confirm = within(screen.getByRole('dialog')).getByRole('button', { name: 'Chiudi posizione' });
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    const exits = provider.getSnapshot().orders.filter((o) => o.purpose === 'EXIT');
    expect(exits).toHaveLength(1);
    expect(exits[0].status).toBe('REQUESTED');
    act(() => {
      provider.completePendingExit();
    });
    expect(provider.getSnapshot().position).toBeNull();
    expect(screen.getAllByRole('button', { name: 'Chiudi posizione' })[0].hasAttribute('disabled')).toBe(true);
  });

  it('la ripresa automatica richiede la spunta esplicita', () => {
    const provider = setup('long-5m-manual');
    fireEvent.click(screen.getAllByRole('button', { name: 'Riprendi automatico' })[0]);
    const dialog = screen.getByRole('dialog');
    const confirm = within(dialog).getByRole('button', { name: 'Riprendi automatico' });
    expect(confirm.hasAttribute('disabled')).toBe(true);
    fireEvent.click(within(dialog).getByRole('checkbox'));
    fireEvent.click(confirm);
    expect(provider.getSnapshot().position?.management).toBe('BOT');
  });

  it('le sezioni fuori perimetro sono dichiarate non disponibili', () => {
    setup();
    fireEvent.click(screen.getByRole('button', { name: 'Ricerca / Backtest' }));
    expect(screen.getByText('Non disponibile in questa versione.')).toBeTruthy();
  });
});
