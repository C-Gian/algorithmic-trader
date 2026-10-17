/**
 * MOVE-001 nel lettore storico, su fixture SINTETICA prodotta dallo stesso codice (prezzi inventati):
 * identità e avviso non operativo, nessun comando di seguito 24h, stato del riferimento ricostruito
 * soltanto dai fatti noti al momento scelto, rifiuto dei pacchetti incoerenti, compatibilità OBS-001/OBS-002.
 */
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import obs001Fixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import moveFixture from '../../historical/__fixtures__/synthetic-move001-case.json?raw';
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

type Pkg = Record<string, any>;
const variant = (f: (b: Pkg, c: Pkg) => void) => {
  const b = JSON.parse(moveFixture);
  f(b, b.case);
  return JSON.stringify(b);
};
const BAR = 45 * 60_000;
const LABEL = 'Rappresentazione sperimentale del movimento — nessuna decisione operativa';

describe('validazione MOVE001_CASE', () => {
  it('apre il pacchetto e i formati precedenti restano leggibili', () => {
    const b = parseBundle(moveFixture);
    expect(b.kind).toBe('MOVE001_CASE');
    expect(new HistoricalStudy(b).moveCase?.refId).toMatch(/^MOV:(LONG|SHORT):/);
    expect(new HistoricalStudy(b).obs002Case).toBeNull();
    expect(parseBundle(obs001Fixture).kind).toBe('OBS001_BUNDLE');
    expect(new HistoricalStudy(parseBundle(caseFixture)).moveCase).toBeNull();
  });

  it.each([
    ['seguito 24h inventato', (b: Pkg) => (b.retrospective.rows = [{}]), /nessun seguito 24h/],
    ['tabulazione presente', (b: Pkg) => (b.retrospective.summary = {}), /nessun seguito 24h/],
    ['identità dello studio', (b: Pkg) => (b.study.id = 'OBS-002/v1'), /Studio MOVE-001/],
    ['schema', (b: Pkg) => (b.schema = 'obs002.case/1'), /attesa move001.case\/1/],
    ['ancora futura', (_: Pkg, c: Pkg) => (c.P0.availableAt = c.birthAt + BAR), /non ancora nota alla nascita/],
    ['verso delle ancore', (_: Pkg, c: Pkg) => (c.B.kind = c.P0.kind), /B: ancora non valida/],
    ['ledger senza nascita', (_: Pkg, c: Pkg) => c.ledger.shift(), /iniziare con la nascita/],
    ['fatti non ordinati', (_: Pkg, c: Pkg) => c.ledger.reverse(), /ordine di tempo|nascita/],
    ['fatto oltre il pacchetto', (b: Pkg, c: Pkg) => (c.ledger[c.ledger.length - 1].t = b.periods.end + BAR), /fuori dalla vita/],
    ['P1 incoerente', (_: Pkg, c: Pkg) => (c.ledger.find((e: Pkg) => e.type === 'P1_PUBLISHED').P1.availableAt += BAR), /P1 non coerente/],
  ])('rifiuta: %s', (_, f, msg) => {
    expect(() => parseBundle(variant(f as (b: Pkg, c: Pkg) => void))).toThrow(msg);
  });
});

describe('consultazione del riferimento', () => {
  function setup() {
    const s = new HistoricalStudy(parseBundle(moveFixture));
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
    return s;
  }
  const next = (n: number) => {
    for (let i = 0; i < n; i++) fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
  };

  it('parte dalla nascita, avviso non operativo, nessun comando di seguito 24h', () => {
    const s = setup();
    const c = s.moveCase!;
    expect(screen.getByText(`Cutoff t · ${fmtUtc(c.birthAt)}`)).toBeTruthy();
    expect(screen.getAllByText(new RegExp(LABEL)).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'Mostra seguito retrospettivo 24h' })).toBeNull();
    const card = screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' });
    expect(within(card).getByText('INDETERMINATO')).toBeTruthy();
    expect(within(card).getByText(/FORMAZIONE_NON_CONCLUSA/)).toBeTruthy();
    expect(within(card).getByText('Fatti noti fino a questo momento (1)')).toBeTruthy();
    expect(within(card).queryByText(/Archiviazione/)).toBeNull(); // la conclusione futura non è nota
  });

  it('lo stato cambia solo quando i fatti diventano noti', () => {
    const s = setup();
    const c = s.moveCase!;
    const usable = c.ledger.find((e) => e.type === 'USABLE')!.t;
    next((usable - c.birthAt) / BAR - 1);
    let card = screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' });
    expect(within(card).getByText('INDETERMINATO')).toBeTruthy();
    expect(within(card).getByText('non ancora noto')).toBeTruthy(); // P1 non ancora pubblicato
    next(1);
    card = screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' });
    expect(within(card).getByText('UTILIZZABILE')).toBeTruthy();
    expect(within(card).queryByText('non ancora noto')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Vai alla nascita' }));
    fireEvent.click(screen.getByRole('button', { name: '← Chiusura precedente' }));
    expect(screen.getByText('Riferimento non ancora nato a questo momento')).toBeTruthy();
  });

  it('la voce Studio osservativo spiega l’assenza di tabulazione e torna al caso', () => {
    const s = setup();
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('button', { name: 'Studio osservativo' }));
    expect(screen.getByText(/Pacchetto di consultazione MOVE-001\/v1 · nessuna tabulazione OBS-001/)).toBeTruthy();
    expect(screen.getByText(/docs\/research\/MOVE-001-results.md/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: `Torna al caso · ${fmtUtc(s.moveCase!.birthAt)}` }));
    expect(screen.getByText(`Cutoff t · ${fmtUtc(s.moveCase!.birthAt)}`)).toBeTruthy();
  });
});
