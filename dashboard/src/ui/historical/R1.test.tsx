/**
 * OBS-001/R1 (review del Director): R1-A import solo di bundle coerenti, via file picker, con
 * lo studio precedente conservato; R1-B prezzo al cutoff mancante mai mostrato come corrente.
 * Fixture SINTETICA (prezzi inventati) prodotta dal motore; nessun dato reale.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import { parseBundle } from '../../historical/loadBundle';
import { HistoricalStudy } from '../../historical/study';
import { formatNumber, formatPrice } from '../../lib/numbers';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { CandleChart } from '../components/CandleChart';
import { fmtUtc } from '../format';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const base = () => JSON.parse(fixture);
const sim = () => new SimulatedProvider({ exitDelayMs: 0 });

async function upload(label: string, content: string) {
  const input = screen.getByLabelText(label, { selector: 'input' }) as HTMLInputElement;
  await act(async () => {
    fireEvent.change(input, { target: { files: [new File([content], 'obs001-bundle.json', { type: 'application/json' })] } });
  });
}

const without = (key: string) => {
  const b = base();
  delete b[key];
  return JSON.stringify(b);
};

describe('R1-A · import solo di bundle coerenti', () => {
  it('senza «run» o senza «inputQuality» il file è rifiutato prima del rendering', async () => {
    render(<App createSimulation={sim} initialEnvironment="HISTORICAL" />);
    await upload('Apri studio storico', without('run'));
    await waitFor(() => expect(screen.getByText(/Identità del run: campo «run» assente/)).toBeTruthy());
    expect(screen.queryByLabelText('Grafico storico')).toBeNull();
    await upload('Apri studio storico', without('inputQuality'));
    await waitFor(() => expect(screen.getByText(/Qualità degli input: campo «inputQuality» assente/)).toBeTruthy());
    expect(screen.queryByLabelText('Grafico storico')).toBeNull();
    // Il file corretto si apre normalmente dopo i rifiuti.
    await upload('Apri studio storico', fixture);
    await waitFor(() => expect(screen.getByLabelText('Grafico storico')).toBeTruthy());
    expect(screen.queryByText('Bundle non valido')).toBeNull();
  });

  it('con uno studio aperto, un file incoerente non lo sostituisce; un file valido sì', async () => {
    render(<App createSimulation={sim} initialStudy={new HistoricalStudy(parseBundle(fixture))} initialEnvironment="HISTORICAL" />);
    fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
    expect(screen.getByText(/Origine 2 di 64/)).toBeTruthy();

    const shifted = base();
    shifted.observations['45m'][10].end += 60_000; // record non allineato alla sua barra
    await upload('Apri altro studio', JSON.stringify(shifted));
    await waitFor(() => expect(screen.getByText(/Osservazioni 45m, record 11: tempi non allineati/)).toBeTruthy());
    expect(screen.getByText(/Origine 2 di 64/)).toBeTruthy(); // studio precedente conservato

    const grid = base();
    grid.origins[3] += 45 * 60_000; // griglia delle origini incoerente
    await upload('Apri altro studio', JSON.stringify(grid));
    await waitFor(() => expect(screen.getByText(/Origini: la 4ª non è sulla griglia 45m/)).toBeTruthy());

    const column = base();
    column.bars['1D'].c.pop(); // colonna non allineata
    await upload('Apri altro studio', JSON.stringify(column));
    await waitFor(() => expect(screen.getByText(/Barre 1D: colonna «c» non allineata/)).toBeTruthy());

    await upload('Apri altro studio', without('run'));
    await waitFor(() => expect(screen.getByText(/campo «run» assente/)).toBeTruthy());
    expect(screen.getByText(/Origine 2 di 64/)).toBeTruthy();

    await upload('Apri altro studio', fixture);
    await waitFor(() => expect(screen.getByText(/Origine 1 di 64/)).toBeTruthy()); // nuovo studio aperto dalla prima origine
    expect(screen.queryByText('Bundle non valido')).toBeNull();
  });

  it('il validatore accetta la fixture sintetica e rifiuta misure fuori formato', () => {
    expect(() => parseBundle(fixture)).not.toThrow();
    const bad = base();
    bad.observations['1D'][1].vol.A = { v: null };
    expect(() => parseBundle(JSON.stringify(bad))).toThrow(/vol\.A: misura non nel formato/);
    const events = base();
    events.events['45m'].reverse();
    expect(() => parseBundle(JSON.stringify(events))).toThrow(/ordine temporale/);
  });
});

const lastPriceMark = () => document.querySelector('.chart-box [data-role="last-price"]');
const lastPriceText = () => lastPriceMark()?.querySelector('text')?.textContent;

describe('R1-B · prezzo al cutoff mancante', () => {
  it('1D incompleto della fixture: nessun prezzo corrente, ultimo noto qualificato della stessa scala', () => {
    const study = new HistoricalStudy(parseBundle(fixture));
    render(<App createSimulation={sim} initialStudy={study} initialEnvironment="HISTORICAL" />);
    const t = study.origins[0];
    // Controllo: la scala 45m al cutoff ha una chiusura e il marker la mostra.
    expect(lastPriceText()).toBe(formatPrice(study.snapshot(t).m45.C!));

    fireEvent.click(screen.getByRole('button', { name: '1D' }));
    const d1 = study.snapshot(t).d1!;
    expect(d1.status).toBe('INCOMPLETE');
    expect(lastPriceMark()).toBeNull();
    const day1 = study.bundle.bars['1D'];
    const known = { price: day1.c[0]!, end: day1.open[0] + 86_400_000 };
    expect(known.end).toBeLessThanOrEqual(t);
    const note = screen.getByText(/Prezzo al cutoff non disponibile sulla scala 1D/).closest('[role="note"]')!;
    expect(within(note as HTMLElement).getByText(new RegExp(`Ultimo noto della stessa scala: ${formatNumber(known.price, 2).replace('.', '\\.')} USDT, chiusura alle ${fmtUtc(known.end)}`))).toBeTruthy();
    expect(note.textContent).not.toContain(formatPrice(study.snapshot(t).m45.C!));
  });

  it('lacuna 45m al cutoff: niente marker; ultimo noto = barra 45m precedente, non il futuro', () => {
    const b = base();
    const t = b.origins[0];
    const k = (t - b.periods.inputStart) / (45 * 60_000) - 1;
    for (const col of ['o', 'h', 'l', 'c', 'v', 'q', 'trades']) b.bars['45m'][col][k] = null;
    b.bars['45m'].status[k] = 'INCOMPLETE';
    Object.assign(b.observations['45m'][k], { status: 'INCOMPLETE', C: null });
    const study = new HistoricalStudy(parseBundle(JSON.stringify(b)));
    render(<App createSimulation={sim} initialStudy={study} initialEnvironment="HISTORICAL" />);
    expect(lastPriceMark()).toBeNull();
    expect(screen.getByText(/Lacuna all'origine/)).toBeTruthy();
    const note = screen.getByText(/Prezzo al cutoff non disponibile sulla scala 45m/).closest('[role="note"]')!;
    expect(note.textContent).toContain(`chiusura alle ${fmtUtc(t - 45 * 60_000)}`);
    expect(note.textContent).toContain(formatNumber(b.bars['45m'].c[k - 1], 2));
  });

  it('tratto senza prezzi validi: messaggio leggibile, nessun prezzo inventato', () => {
    const gap = (i: number) => ({ openTime: new Date(Date.UTC(2025, 5, 1, 0, 45 * i)).toISOString(), open: 0, high: 0, low: 0, close: 0, volume: 0, partial: false, gap: true });
    render(
      <CandleChart
        timeframe="45m"
        candles={[gap(0), gap(1), gap(2)]}
        series={[]}
        levels={[]}
        overlays={{ averages: true, levels: true, fibonacci: false, volume: true }}
        lastPrice={null}
        lastPriceCurrent
        utc
        dataLabel="storiche"
      />,
    );
    expect(screen.getByRole('img', { name: 'Grafico 45m: nessuna barra completa nel tratto' })).toBeTruthy();
    expect(screen.getByText(/non c’è alcun prezzo da disegnare/)).toBeTruthy();
    expect(document.querySelector('svg')).toBeNull();
  });
});
