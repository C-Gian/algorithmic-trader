/**
 * Review UI-001/R1 lato interfaccia: invalidazione della conferma aperta (R1-A),
 * isolamento del dialogo e testi/badge con feed non regolare (R1-B).
 */
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { SimulatedProvider } from '../sim/provider';
import { App } from './App';

afterEach(cleanup);
window.scrollTo = () => {};

function setup(checkpoint = 'long-5-protection') {
  const provider = new SimulatedProvider({ exitDelayMs: 0, initialCheckpointId: checkpoint });
  const view = render(<App provider={provider} controls={provider} />);
  return { provider, shell: view.container.querySelector('.app') as HTMLElement };
}

const exitOrders = (p: SimulatedProvider) => p.getSnapshot().orders.filter((o) => o.purpose === 'EXIT');

describe('R1-A · conferma aperta e cambi di contesto', () => {
  it('riproduzione della review: cambio a SHORT con «Chiudi posizione» aperto non crea ordini', () => {
    const { provider } = setup();
    fireEvent.click(screen.getAllByRole('button', { name: 'Chiudi posizione' })[0]);
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('BTC / USDT · LONG aperta')).toBeTruthy();
    const staleConfirm = within(dialog).getByRole('button', { name: 'Chiudi posizione' });

    fireEvent.change(screen.getByRole('combobox', { hidden: true }), { target: { value: 'short-4-open' } });

    expect(provider.getSnapshot().position?.side).toBe('SHORT');
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByText(/Conferma annullata: lo stato simulato è cambiato/)).toBeTruthy();
    fireEvent.click(staleConfirm);
    expect(exitOrders(provider)).toHaveLength(0);

    // Una nuova conferma, corretta per il nuovo contesto, agisce sulla posizione SHORT.
    fireEvent.click(screen.getAllByRole('button', { name: 'Chiudi posizione' })[0]);
    const fresh = screen.getByRole('dialog');
    expect(within(fresh).getByText('BTC / USDT · SHORT aperta')).toBeTruthy();
    fireEvent.click(within(fresh).getByRole('button', { name: 'Chiudi posizione' }));
    expect(exitOrders(provider).map((o) => o.side)).toEqual(['BUY']);
  });

  it('aggiornamento del provider nello stesso scenario (feed) invalida la conferma aperta', () => {
    const { provider } = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Gestione manuale' }));
    expect(screen.getByRole('dialog')).toBeTruthy();
    act(() => provider.setFeedCondition('DISCONNECTED'));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(provider.getSnapshot().position?.management).toBe('BOT');

    fireEvent.click(screen.getByRole('button', { name: 'Gestione manuale' }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText(/sono gli ultimi noti alle .* non sono verificabili ora/)).toBeTruthy();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Passa a manuale' }));
    expect(provider.getSnapshot().position?.management).toBe('MANUAL');
  });

  it('un eseguito arrivato a dialogo aperto (quantità cambiata) invalida la conferma', () => {
    const { provider } = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Uscita parziale' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Conferma uscita parziale' }));
    fireEvent.click(screen.getByRole('button', { name: 'Stop totale' }));
    expect(screen.getByRole('dialog')).toBeTruthy();
    act(() => {
      provider.completePendingExit();
    });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(provider.getSnapshot().context.bot.status).toBe('RUNNING');
  });

  it('il fondo è inerte durante il dialogo, Tab resta nel dialogo e il focus torna al comando', () => {
    const { shell } = setup();
    const opener = screen.getByRole('button', { name: 'Stop totale' });
    opener.focus();
    fireEvent.click(opener);
    const dialog = screen.getByRole('dialog');
    expect(shell.hasAttribute('inert')).toBe(true);
    expect(shell.getAttribute('aria-hidden')).toBe('true');

    const cancel = within(dialog).getByRole('button', { name: 'Annulla' });
    const confirm = within(dialog).getByRole('button', { name: 'Ferma il bot' });
    expect(document.activeElement).toBe(cancel);
    confirm.focus();
    fireEvent.keyDown(confirm, { key: 'Tab' });
    expect(document.activeElement).toBe(cancel);
    fireEvent.keyDown(cancel, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(confirm);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(shell.hasAttribute('inert')).toBe(false);
    expect(shell.hasAttribute('aria-hidden')).toBe(false);
    expect(document.activeElement).toBe(opener);
  });
});

describe('R1-B · badge e comandi con feed non regolare', () => {
  it('feed disconnesso: gestione e bot dichiarati sospesi, protezioni ultime note', () => {
    const { provider } = setup();
    act(() => provider.setFeedCondition('DISCONNECTED'));
    expect(screen.getByText('Gestione automatica sospesa · feed disconnesso')).toBeTruthy();
    expect(screen.getByText('Bot attivo · azioni automatiche sospese')).toBeTruthy();
    expect(screen.queryByText('Gestione automatica')).toBeNull();
    expect(screen.getAllByText(/ultimo noto, non verificato/).length).toBe(2);
    expect(screen.getByText('2 protezioni · ultime note, non verificabili ora')).toBeTruthy();
    expect(screen.queryByText(/protezioni attive/)).toBeNull();
  });

  it('feed non aggiornato in gestione manuale: ripresa bloccata con spiegazione, poi esplicita', () => {
    const { provider } = setup('long-5m-manual');
    act(() => provider.setFeedCondition('STALE'));
    const resume = screen.getAllByRole('button', { name: 'Riprendi automatico' })[0];
    expect(resume.hasAttribute('disabled')).toBe(true);
    expect(resume.getAttribute('title')).toContain('finché il feed non torna regolare');
    expect(screen.getByText(/Start e ripresa automatica bloccati/)).toBeTruthy();

    act(() => provider.setFeedCondition('OK'));
    expect(provider.getSnapshot().position?.management).toBe('MANUAL');
    fireEvent.click(screen.getAllByRole('button', { name: 'Riprendi automatico' })[0]);
    const dialog = screen.getByRole('dialog');
    fireEvent.click(within(dialog).getByRole('checkbox'));
    fireEvent.click(within(dialog).getByRole('button', { name: 'Riprendi automatico' }));
    expect(provider.getSnapshot().position?.management).toBe('BOT');
  });
});
