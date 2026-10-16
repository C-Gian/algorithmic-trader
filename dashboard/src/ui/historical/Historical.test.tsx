/**
 * OBS-001 nella dashboard, su bundle SINTETICO prodotto dallo stesso motore (prezzi inventati):
 * import, cutoff sincronizzato, seguito solo su comando, dati null leggibili, niente conto/call
 * fittizi nello storico, cambio d'ambiente che invalida una conferma aperta.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import { BundleError, parseBundle } from '../../historical/loadBundle';
import { HistoricalStudy } from '../../historical/study';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';

const HIST_BANNER = 'STORICO REALE — studio osservativo locale — nessun collegamento exchange';
const SIM_BANNER = 'SIMULAZIONE LOCALE — nessun collegamento exchange';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const study = () => new HistoricalStudy(parseBundle(fixture));
// hidden: con un dialogo aperto il fondo è aria-hidden/inert; il test usa la via programmatica.
const env = (name: string) => within(screen.getByRole('group', { name: 'Ambiente', hidden: true })).getByRole('button', { name, hidden: true });

function setupHistorical() {
  const s = study();
  render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
  return s;
}

async function upload(text: string, name = 'obs001-bundle.json') {
  const input = screen.getByLabelText('Apri studio storico', { selector: 'input' }) as HTMLInputElement;
  const file = new File([text], name, { type: 'application/json' });
  await act(async () => {
    fireEvent.change(input, { target: { files: [file] } });
  });
}

describe('import del bundle', () => {
  it('senza bundle lo storico chiede di aprirlo e non mostra prezzi', () => {
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} />);
    expect(screen.getByText(SIM_BANNER)).toBeTruthy();
    fireEvent.click(env('Studio storico'));
    expect(screen.getByText(HIST_BANNER)).toBeTruthy();
    expect(screen.getByText(/nessun bundle aperto/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Scenari simulati/ })).toBeNull();
    expect(screen.queryByLabelText('Grafico storico')).toBeNull();
  });

  it('un file errato produce un errore leggibile, nessun ripiego', async () => {
    render(<App createSimulation={() => new SimulatedProvider()} initialEnvironment="HISTORICAL" />);
    await upload('{"kind":"ALTRO"}');
    await waitFor(() => expect(screen.getByText(/Non è un bundle OBS-001/)).toBeTruthy());
    expect(screen.queryByLabelText('Grafico storico')).toBeNull();
    await upload('non json');
    await waitFor(() => expect(screen.getByText(/non è un JSON valido/)).toBeTruthy());
  });

  it('un bundle valido porta allo studio, dalla prima origine', async () => {
    render(<App createSimulation={() => new SimulatedProvider()} />);
    fireEvent.click(env('Studio storico'));
    await upload(fixture);
    await waitFor(() => expect(screen.getByLabelText('Grafico storico')).toBeTruthy());
    expect(screen.getByText(/Origine 1 di 64/)).toBeTruthy();
    expect(screen.getByText('FIXTURE SINTETICA')).toBeTruthy();
  });

  it('validazione del formato', () => {
    const bad = JSON.parse(fixture);
    bad.observations['45m'] = bad.observations['45m'].slice(1);
    expect(() => parseBundle(JSON.stringify(bad))).toThrow(BundleError);
    expect(() => parseBundle(JSON.stringify({ ...JSON.parse(fixture), schema: 'obs001.bundle/9' }))).toThrow(/schema non supportata/);
  });
});

describe('vista causale', () => {
  it('nessun saldo, call, ordine o comando operativo nello storico', () => {
    setupHistorical();
    expect(screen.getByText(HIST_BANNER)).toBeTruthy();
    expect(screen.getByText('Non previsti nello studio osservativo')).toBeTruthy();
    for (const name of ['Start', 'Stop totale', 'Chiudi posizione', 'Gestione manuale', 'Solo call']) {
      expect(screen.queryByRole('button', { name })).toBeNull();
    }
    expect(screen.queryByText(/10\.000/)).toBeNull();
    expect(screen.queryByText(/CALL ATTUALE|il bot la pensa/i)).toBeNull();
    expect(screen.getByText(/OSSERVAZIONI AL/)).toBeTruthy();
  });

  it('cutoff sincronizzato fra 45m e 1D e avanzamento di 45 minuti', () => {
    const s = setupHistorical();
    const [t0, t1] = s.origins;
    expect(screen.getByText(/Origine 1 di 64/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
    expect(screen.getByText(/Origine 2 di 64/)).toBeTruthy();
    expect(t1 - t0).toBe(45 * 60_000);
    const snap = s.snapshot(t1);
    expect(snap.m45.end).toBe(t1);
    expect(snap.d1?.end).toBe(t1 - (t1 % 86_400_000)); // ultimo giorno chiuso, non quello in formazione
    expect(screen.getByRole('button', { name: '← Chiusura precedente' }).hasAttribute('disabled')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    const chart = screen.getByRole('img', { name: /Grafico 1D con 2 candele/ });
    expect(chart).toBeTruthy();
  });

  it('il seguito retrospettivo compare solo col comando esplicito e si può togliere', () => {
    setupHistorical();
    expect(screen.queryByLabelText('Seguito retrospettivo 24h')).toBeNull();
    const before = screen.getByRole('img', { name: /Grafico 45m con (\d+) candele/ }).getAttribute('aria-label');
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito retrospettivo 24h' }));
    const card = screen.getByLabelText('Seguito retrospettivo 24h');
    expect(within(card).getByText(/A POSTERIORI/)).toBeTruthy();
    const after = screen.getByRole('img', { name: /Grafico 45m con (\d+) candele/ }).getAttribute('aria-label');
    expect(Number(after!.match(/(\d+) candele/)![1])).toBe(Number(before!.match(/(\d+) candele/)![1]) + 32);
    fireEvent.click(screen.getAllByRole('button', { name: 'Solo informazioni al momento' })[0]);
    expect(screen.queryByLabelText('Seguito retrospettivo 24h')).toBeNull();
  });

  it('fine censurata e dati null leggibili', () => {
    setupHistorical();
    // Seconda origine: il giorno 2 della fixture contiene una lacuna; la scala 1D lo dichiara, senza valori stimati.
    fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
    expect(screen.getAllByText(/Barra incompleta \(1 minuti mancanti\)/).length).toBe(6);
    // Ultima origine: orizzonte oltre la fine dell'input.
    fireEvent.change(screen.getByRole('slider', { name: 'Origine dello studio' }), { target: { value: '63' } });
    expect(screen.getByText(/Origine 64 di 64/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Chiusura successiva →' }).hasAttribute('disabled')).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito retrospettivo 24h' }));
    expect(screen.getByText('Esiti 24h non disponibili')).toBeTruthy();
    expect(screen.getAllByText(/censurato/).length).toBeGreaterThan(0);
  });

  it('gli eventi mostrati hanno available_at entro il cutoff', () => {
    const s = setupHistorical();
    const snap = s.snapshot(s.origins[0]);
    const all = [...s.bundle.events['45m']];
    expect(snap.events['45m'].length).toBeLessThan(all.length);
    expect(snap.events['45m'].every((e) => e.availableAt <= s.origins[0])).toBe(true);
    expect(s.candles('45m', s.origins[0], 500, false).every((c) => c.end <= s.origins[0])).toBe(true);
  });
});

describe('riepilogo e ambienti', () => {
  it('il riepilogo è nella voce Studio osservativo e apre un esempio nella vista causale', () => {
    setupHistorical();
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('button', { name: 'Studio osservativo' }));
    expect(screen.getByText(/confronto descrittivo/)).toBeTruthy();
    expect(screen.getByText(/finestre 24h fortemente sovrapposte/)).toBeTruthy();
    const example = screen.getAllByRole('button', { name: /prima origine/ })[0];
    fireEvent.click(example);
    expect(screen.getByLabelText('Grafico storico')).toBeTruthy();
    expect(screen.queryByLabelText('Seguito retrospettivo 24h')).toBeNull();
  });

  it('il cambio di ambiente invalida la conferma aperta e non trasferisce lo stato del bot', () => {
    let created = 0;
    render(
      <App
        createSimulation={() => {
          created += 1;
          return new SimulatedProvider({ exitDelayMs: 0 });
        }}
        initialStudy={study()}
      />,
    );
    const first = created;
    fireEvent.click(screen.getByRole('button', { name: 'Stop totale' }));
    expect(screen.getByRole('dialog')).toBeTruthy();
    fireEvent.click(env('Studio storico'));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByLabelText('Grafico storico')).toBeTruthy();
    fireEvent.click(env('Simulazione locale'));
    expect(created).toBeGreaterThan(first);
    expect(screen.getByText('Bot attivo')).toBeTruthy();
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
