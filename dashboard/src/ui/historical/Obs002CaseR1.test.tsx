/**
 * OBS-002/R1-B: coerenza dell'esito OBS-002 importato (fixture SINTETICHE). Regressioni scritte prima
 * della correzione: i due casi riprodotti dal Director erano accettati dal validatore consegnato a c8ac744.
 * Si controlla la coerenza del pacchetto già calcolato, senza ricostruire il percorso di mercato.
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import obs001Fixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import censoredFixture from '../../historical/__fixtures__/synthetic-obs002-case-censored.json?raw';
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
const variant = (base: string, f: (b: Pkg, o: Pkg) => void) => {
  const b = JSON.parse(base);
  f(b, b.retrospective.obs002.outcome);
  return JSON.stringify(b);
};
const MIN = 60_000;

/** I due casi riprodotti nella review R1. */
const FAVOURABLE_NULL = variant(caseFixture, (_, o) => (o.favourable = null));
const CLASS_WITHOUT_CONTACTS = variant(caseFixture, (_, o) => Object.assign(o, { class: 'F_BEFORE_A', final: 0, contactF: null, contactA: null }));

describe('R1-B: casi riprodotti', () => {
  it('rifiuta un esito completo con una componente ignota', () => {
    expect(() => parseBundle(FAVOURABLE_NULL)).toThrow(/favourable/);
  });

  it('rifiuta una classe di ordine senza i contatti che la giustificano', () => {
    expect(() => parseBundle(CLASS_WITHOUT_CONTACTS)).toThrow(/contatti incoerenti con la classe/);
  });

  it('dal selettore: errore leggibile, studio aperto conservato, nessun blocco retrospettivo falso', async () => {
    const s = new HistoricalStudy(parseBundle(caseFixture));
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
    const cutoff = `Cutoff t · ${fmtUtc(s.obs002Case!.t)}`;
    for (const [text, msg] of [
      [FAVOURABLE_NULL, /favourable/],
      [CLASS_WITHOUT_CONTACTS, /contatti incoerenti con la classe/],
    ] as const) {
      const input = screen.getByLabelText('Apri altro studio', { selector: 'input' }) as HTMLInputElement;
      await act(async () => {
        fireEvent.change(input, { target: { files: [new File([text], 'caso.json', { type: 'application/json' })] } });
      });
      await waitFor(() => expect(screen.getByText(msg)).toBeTruthy());
      expect(screen.getByText(cutoff)).toBeTruthy();
    }
    expect(screen.queryByText(/OBS-002 · verso/)).toBeNull();
  });
});

describe('R1-B: relazioni dei campi usati dal blocco OBS-002', () => {
  const rejects: [string, string, (b: Pkg, o: Pkg) => void, RegExp][] = [
    ['base', caseFixture, (_, o) => (o.adverse = -0.1), /non negative/],
    ['base', caseFixture, (_, o) => (o.flags = ['GAP']), /flag/],
    ['base', caseFixture, (_, o) => (o.flags = ['QUALCOSA']), /flag non riconosciuto/],
    ['base', caseFixture, (_, o) => (o.contactF.minute = o.horizonEnd), /fuori dalla finestra/],
    ['base', caseFixture, (_, o) => (o.contactF.minute = o.contactF.minute + 1), /minuto/],
    ['base', caseFixture, (_, o) => (o.contactF.interval = [o.contactF.minute, o.contactF.minute]), /intervallo/],
    ['base', caseFixture, (_, o) => (o.contactA = { minute: o.contactF.minute - MIN, atOpen: false, interval: [o.contactF.minute - MIN, o.contactF.minute] }), /contatti incoerenti con la classe/],
    ['base', caseFixture, (_, o) => (o.class = 'BOTH_UNORDERED'), /contatti incoerenti con la classe/],
    ['base', caseFixture, (_, o) => (o.class = 'NEITHER'), /contatti incoerenti con la classe/],
    ['base', caseFixture, (_, o) => (o.markers.F = o.markers.A), /riferimenti/],
    ['base', caseFixture, (_, o) => (o.markers = null), /riferimenti/],
    ['base', caseFixture, (_, o) => (o.horizonEnd = o.horizonEnd + MIN), /orizzonte/],
    ['base', caseFixture, (_, o) => (o.A = 0), /A all'origine/],
    ['censurato', censoredFixture, (_, o) => (o.flags = []), /flag/],
    ['censurato', censoredFixture, (_, o) => (o.final = 0.5), /misure complete/],
    ['censurato', censoredFixture, (_, o) => (o.contactF = { minute: o.t, atOpen: true, interval: [o.t, o.t] }), /contatti/],
    ['censurato', censoredFixture, (b, o) => (o.horizonEnd = b.periods.end - MIN), /orizzonte/],
  ];

  it.each(rejects)('%s: rifiuto %#', (_, base, f, msg) => {
    expect(() => parseBundle(variant(base, f))).toThrow(msg);
  });

  it('pacchetti validi completi e censurati e bundle OBS-001 continuano ad aprirsi', () => {
    expect(parseBundle(caseFixture).retrospective.obs002?.outcome.class).toBe('F_BEFORE_A');
    const c = parseBundle(censoredFixture).retrospective.obs002!.outcome;
    expect([c.complete, c.class, c.flags]).toEqual([false, null, ['RIGHT_CENSORED']]);
    expect(parseBundle(obs001Fixture).kind).toBe('OBS001_BUNDLE');
    // contatto nello stesso minuto con apertura che ordina: accettato
    expect(() =>
      parseBundle(variant(caseFixture, (_, o) => Object.assign(o.contactA, { minute: o.contactF.minute, interval: [o.contactF.minute, o.contactF.minute + MIN] }, (o.contactF.atOpen = true), (o.contactF.interval = [o.contactF.minute, o.contactF.minute])))),
    ).not.toThrow();
  });

  it('il caso censurato si consulta: nessuna classe inventata nel blocco OBS-002', () => {
    const s = new HistoricalStudy(parseBundle(censoredFixture));
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
    fireEvent.click(screen.getByRole('button', { name: 'Mostra seguito retrospettivo 24h' }));
    expect(screen.getByText(/esito incompleto/)).toBeTruthy();
    expect(screen.queryByText('F_BEFORE_A')).toBeNull();
  });
});
