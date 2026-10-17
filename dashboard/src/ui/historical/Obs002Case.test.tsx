/**
 * OBS-002: pacchetto di consultazione di un caso, su fixture SINTETICA prodotta dallo stesso codice
 * (prezzi inventati). Il lettore lo apre con identità OBS-002, parte dal momento del caso, mostra
 * l'esito OBS-002 solo nel seguito esplicito e non inventa la tabulazione OBS-001. I bundle OBS-001
 * continuano ad aprirsi.
 */
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import obs001Fixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import caseFixture from '../../historical/__fixtures__/synthetic-obs002-case.json?raw';
import { parseBundle } from '../../historical/loadBundle';
import { HistoricalStudy } from '../../historical/study';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { fmtUtc } from '../format';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const mutate = (f: (b: Record<string, any>) => void) => {
  const b = JSON.parse(caseFixture);
  f(b);
  return JSON.stringify(b);
};

describe('validazione del pacchetto OBS-002', () => {
  it('apre il pacchetto e continua ad aprire il bundle OBS-001', () => {
    const c = parseBundle(caseFixture);
    expect(c.kind).toBe('OBS002_CASE');
    expect(c.case?.attemptId).toMatch(/^ATT:(LONG|SHORT):/);
    expect(c.retrospective.summary).toBeNull();
    const o = parseBundle(obs001Fixture);
    expect(o.kind).toBe('OBS001_BUNDLE');
    expect(o.retrospective.summary).not.toBeNull();
  });

  it('rifiuta tabulazione OBS-001 inventata, caso fuori dalle origini, schema sbagliato ed esito incoerente', () => {
    const summary = JSON.parse(obs001Fixture).retrospective.summary;
    expect(() => parseBundle(mutate((b) => (b.retrospective.summary = summary)))).toThrow(/summary atteso null/);
    expect(() => parseBundle(mutate((b) => (b.case.t = b.case.t + 60_000)))).toThrow(/non è fra le origini/);
    expect(() => parseBundle(mutate((b) => (b.schema = 'obs001.bundle/1')))).toThrow(/attesa obs002.case\/1/);
    expect(() => parseBundle(mutate((b) => (b.retrospective.obs002.outcome.class = null)))).toThrow(/esito completo senza classe/);
    expect(() => parseBundle(mutate((b) => (b.study.id = 'OBS-001/v1')))).toThrow(/Studio OBS-002/);
  });
});

describe('consultazione del caso', () => {
  function setup() {
    const s = new HistoricalStudy(parseBundle(caseFixture));
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
    return s;
  }

  it('parte dal momento del caso con identità OBS-002 e nessun esito prima del comando', () => {
    const s = setup();
    const c = s.obs002Case!;
    expect(screen.getByText(`Cutoff t · ${fmtUtc(c.t)}`)).toBeTruthy();
    expect(screen.getByText(`Pacchetto OBS-002 · caso ${c.attemptId}`)).toBeTruthy();
    expect(screen.queryByText(/OBS-002 · verso/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito retrospettivo 24h' }));
    const card = screen.getByRole('region', { name: 'Seguito retrospettivo 24h' });
    expect(within(card).getByText(new RegExp(`OBS-002 · verso ${c.side}`))).toBeTruthy();
    expect(within(card).getByText(s.obs002Outcome(c.t)!.class!)).toBeTruthy();
    // un altro momento del pacchetto: nessun esito OBS-002 attribuito, ritorno al caso disponibile
    fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
    expect(screen.queryByText(/OBS-002 · verso/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Vai al caso' }));
    expect(screen.getByText(`Cutoff t · ${fmtUtc(c.t)}`)).toBeTruthy();
  });

  it('la voce Studio osservativo spiega che la tabulazione OBS-001 non è pertinente e torna al caso', () => {
    const s = setup();
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('button', { name: 'Studio osservativo' }));
    expect(screen.getByText(/nessuna tabulazione OBS-001/)).toBeTruthy();
    expect(screen.getByText(/docs\/research\/OBS-002-results.md/)).toBeTruthy();
    expect(screen.queryByText(/Copertura e disponibilità/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: `Torna al caso · ${fmtUtc(s.obs002Case!.t)}` }));
    expect(screen.getByText(`Cutoff t · ${fmtUtc(s.obs002Case!.t)}`)).toBeTruthy();
  });
});
