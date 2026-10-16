/**
 * UI-002 fase B: navigazione superiore, pannello «Scenari simulati» richiudibile e
 * isolamento di barra e pannello durante le conferme (regressione R1-A).
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SimulatedProvider } from '../sim/provider';
import { App } from './App';

const scrolled: string[] = [];
beforeEach(() => {
  scrolled.length = 0;
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = vi.fn(function (this: Element) {
    scrolled.push(this.id);
  });
});
afterEach(cleanup);

function setup(checkpoint = 'long-5-protection') {
  const provider = new SimulatedProvider({ exitDelayMs: 0, initialCheckpointId: checkpoint });
  const view = render(<App provider={provider} controls={provider} />);
  return { provider, shell: view.container.querySelector('.app') as HTMLElement, container: view.container };
}

const nav = () => screen.getByRole('navigation', { name: 'Navigazione' });
const toggle = () => screen.getByRole('button', { name: /Scenari simulati/ });

describe('navigazione superiore', () => {
  it('nessuna barra laterale; le cinque destinazioni sono in alto con Dashboard selezionata', () => {
    const { container } = setup();
    expect(container.querySelector('aside, .sidebar, .sidebar-col')).toBeNull();
    const items = within(nav()).getAllByRole('button').map((b) => b.textContent);
    expect(items).toEqual(['Dashboard', 'Ricerca / Backtest', 'Storico', 'Conto', 'Impostazioni', 'Guida ai segnali ↗']);
    expect(within(nav()).getByRole('button', { name: 'Dashboard' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByText('SIMULAZIONE LOCALE — nessun collegamento exchange')).toBeTruthy();
  });

  it('Storico e Conto scorrono alla sezione; Impostazioni è dichiarata non disponibile', async () => {
    setup();
    fireEvent.click(within(nav()).getByRole('button', { name: 'Storico' }));
    await waitFor(() => expect(scrolled).toContain('storico'));
    fireEvent.click(within(nav()).getByRole('button', { name: 'Conto' }));
    await waitFor(() => expect(scrolled).toContain('conto'));

    fireEvent.click(within(nav()).getByRole('button', { name: 'Impostazioni' }));
    expect(screen.getByText('Non disponibile in questa versione.')).toBeTruthy();
    expect(within(nav()).getByRole('button', { name: 'Impostazioni' }).getAttribute('aria-current')).toBe('page');
    expect(screen.queryByRole('button', { name: 'Stop totale' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Torna alla dashboard' }));
    expect(screen.getByRole('button', { name: 'Stop totale' })).toBeTruthy();
  });
});

describe('pannello «Scenari simulati»', () => {
  it('parte chiuso, si apre con stato accessibile e contiene checkpoint, feed e reset', () => {
    const { provider } = setup();
    expect(toggle().getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByRole('region', { name: 'Scenari simulati' })).toBeNull();

    fireEvent.click(toggle());
    expect(toggle().getAttribute('aria-expanded')).toBe('true');
    const panel = screen.getByRole('region', { name: 'Scenari simulati' });
    expect(toggle().getAttribute('aria-controls')).toBe(panel.id);
    expect(within(panel).getByText(/LOCALE/)).toBeTruthy();
    const select = within(panel).getByRole('combobox') as HTMLSelectElement;
    expect(select.options).toHaveLength(provider.listCheckpoints().length);

    fireEvent.change(select, { target: { value: 'short-4-open' } });
    expect(provider.getSnapshot().position?.side).toBe('SHORT');
    fireEvent.click(within(panel).getByRole('button', { name: 'Disconnesso' }));
    expect(provider.getSnapshot().context.feed.status).toBe('DISCONNECTED');
    expect(within(panel).getByRole('button', { name: 'Disconnesso' }).getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(within(panel).getByRole('button', { name: 'Reimposta simulazione' }));
    expect(provider.currentCheckpointId()).toBe('long-5-protection');
    expect(provider.getSnapshot().context.feed.status).toBe('OK');

    fireEvent.click(within(panel).getByRole('button', { name: 'Chiudi' }));
    expect(screen.queryByRole('region', { name: 'Scenari simulati' })).toBeNull();
    expect(document.activeElement).toBe(toggle());
  });

  it('Esc dal pannello lo chiude e riporta il focus al pulsante', () => {
    setup();
    fireEvent.click(toggle());
    const select = within(screen.getByRole('region', { name: 'Scenari simulati' })).getByRole('combobox');
    select.focus();
    fireEvent.keyDown(select, { key: 'Escape' });
    expect(screen.queryByRole('region', { name: 'Scenari simulati' })).toBeNull();
    expect(toggle().getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(toggle());
  });

  it('con una conferma aperta barra e pannello sono inerti; Esc chiude solo il dialogo', () => {
    const { shell, provider } = setup();
    const scenarios = toggle();
    fireEvent.click(scenarios);
    const panel = screen.getByRole('region', { name: 'Scenari simulati' });
    const opener = screen.getByRole('button', { name: 'Stop totale' });
    opener.focus();
    fireEvent.click(opener);

    const dialog = screen.getByRole('dialog');
    expect(shell.hasAttribute('inert')).toBe(true);
    expect(shell.contains(panel)).toBe(true);
    expect(shell.contains(scenarios)).toBe(true);
    expect(shell.getAttribute('aria-hidden')).toBe('true');
    expect(shell.contains(dialog)).toBe(false);
    const confirm = within(dialog).getByRole('button', { name: 'Ferma il bot' });
    confirm.focus();
    fireEvent.keyDown(confirm, { key: 'Tab' });
    expect(document.activeElement).toBe(within(dialog).getByRole('button', { name: 'Annulla' }));

    act(() => {
      fireEvent.keyDown(window, { key: 'Escape' });
    });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(shell.hasAttribute('inert')).toBe(false);
    expect(screen.getByRole('region', { name: 'Scenari simulati' })).toBeTruthy();
    expect(document.activeElement).toBe(opener);
    expect(provider.getSnapshot().context.bot.status).toBe('RUNNING');

    // Conferma eseguita dopo l'annullamento: comando applicato una sola volta.
    fireEvent.click(opener);
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Ferma il bot' }));
    expect(provider.getSnapshot().context.bot.status).toBe('STOPPED');
  });
});
