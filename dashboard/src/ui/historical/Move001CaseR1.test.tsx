/**
 * MOVE-001/R1 (fixture SINTETICHE dello stesso codice). Regressioni scritte prima della correzione:
 * R1-A — il validatore consegnato a 1235e64 accettava fatti incompleti o incoerenti letti dalla scheda;
 * R1-B — l'ultima chiusura disponibile (OPEN_AT_END o conclusione a fine copertura) non era selezionabile.
 * Si controlla la coerenza del pacchetto calcolato, senza ricalcolare pivot o prezzi nel browser.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import obs001Fixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import finalFixture from '../../historical/__fixtures__/synthetic-move001-case-final.json?raw';
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
const variant = (base: string, f: (b: Pkg, l: Pkg[]) => void) => {
  const b = JSON.parse(base);
  f(b, b.case.ledger);
  return JSON.stringify(b);
};
const find = (l: Pkg[], type: string) => l.find((e) => e.type === type)!;
const idx = (l: Pkg[], type: string) => l.findIndex((e) => e.type === type);
const BAR = 45 * 60_000;

// La fixture base: BIRTH, P1_PUBLISHED, USABLE, CANDIDATE_REJECTED, SUSPENSION TEST_ORIGINE, FACT…, ARCHIVE ORIGINE_IN_CHIUSURA.
const REJECTS: [string, (b: Pkg, l: Pkg[]) => void, RegExp][] = [
  ['nascita senza B (riproduzione 1)', (_, l) => delete l[0].B, /BIRTH: ancora B/],
  ['P1 senza candidateOpen (riproduzione 2)', (_, l) => delete find(l, 'P1_PUBLISHED').P1.candidateOpen, /P1_PUBLISHED: ancora P1/],
  ['UTILIZZABILE dopo la conclusione (riproduzione 3)', (_, l) => l.push({ ...find(l, 'USABLE'), t: l[l.length - 1].t }), /dopo la conclusione/],
  ['chiusure della nascita non numeriche', (_, l) => (l[0].C = 'x'), /BIRTH: C/],
  ['ancore della nascita diverse dal caso', (_, l) => (l[0].P0 = { ...l[0].P0, price: l[0].P0.price + 1 }), /ancore della nascita/],
  ['verso del fatto diverso dal caso', (_, l) => (l[1].side = l[1].side === 'LONG' ? 'SHORT' : 'LONG'), /verso/],
  ['seconda nascita', (_, l) => l.splice(1, 0, { ...l[0] }), /seconda nascita/],
  ['seconda pubblicazione di P1', (_, l) => l.splice(idx(l, 'USABLE') + 1, 0, { ...find(l, 'P1_PUBLISHED') }), /seconda pubblicazione/],
  ['UTILIZZABILE senza P1', (_, l) => l.splice(idx(l, 'P1_PUBLISHED'), 1), /UTILIZZABILE senza P1/],
  ['UTILIZZABILE dopo sospensione', (_, l) => l.splice(idx(l, 'USABLE'), 0, { ...find(l, 'SUSPENSION'), t: find(l, 'USABLE').t }), /UTILIZZABILE dopo una sospensione/],
  ['seconda sospensione iniziale', (_, l) => l.splice(idx(l, 'SUSPENSION') + 1, 0, { ...find(l, 'SUSPENSION') }), /seconda sospensione/],
  ['motivo di sospensione sconosciuto', (_, l) => (find(l, 'SUSPENSION').reason = 'ALTRO'), /motivo di sospensione/],
  ['sospensione alla nascita fuori dalla nascita', (_, l) => (find(l, 'SUSPENSION').reason = 'STRUTTURA_OPPOSTA_ALLA_NASCITA'), /alla nascita/],
  ['fatto successivo senza sospensione', (_, l) => l.splice(idx(l, 'SUSPENSION'), 1), /fatto successivo senza sospensione/],
  ['fatto sconosciuto', (_, l) => (find(l, 'FACT').fact = 'ALTRO'), /fatto non riconosciuto/],
  ['flag non in elenco', (_, l) => (find(l, 'FACT').flags = 'DOPPIO'), /flag/],
  ['P1 da sospeso dichiarato in formazione', (_, l) => (find(l, 'P1_PUBLISHED').whileSuspended = true), /whileSuspended/],
  ['P1 di verso sbagliato', (_, l) => (find(l, 'P1_PUBLISHED').P1.kind = l[0].P0.kind), /P1_PUBLISHED: ancora P1/],
  ['P1 candidato prima della barra di nascita', (_, l) => (find(l, 'P1_PUBLISHED').P1.candidateOpen = l[0].t - 2 * BAR), /P1 candidato prima della nascita/],
  ['P1 non oltre B', (_, l) => (find(l, 'P1_PUBLISHED').P1.price = l[0].B.price), /P1 non oltre B/],
  ['archiviazione con giudizio incoerente', (_, l) => (l[l.length - 1].judgement = 'UTILIZZABILE'), /giudizio/],
  ['motivo di archiviazione sconosciuto', (_, l) => (l[l.length - 1].reason = 'ALTRO'), /motivo di archiviazione/],
  ['rifiuto senza prezzi del candidato', (_, l) => delete find(l, 'CANDIDATE_REJECTED').candidateP0, /CANDIDATE_REJECTED: candidateP0/],
  ['rifiuto con esito sconosciuto', (_, l) => (find(l, 'CANDIDATE_REJECTED').outcome = 'ADOTTATA'), /esito del rifiuto/],
  ['tipo di fatto sconosciuto', (_, l) => (l[1].type = 'ALTRO'), /tipo, istante o riferimento/],
];

describe('R1-A: validazione dei fatti letti dalla scheda', () => {
  it.each(REJECTS)('rifiuta: %s', (_, f, msg) => {
    expect(() => parseBundle(variant(moveFixture, f))).toThrow(msg);
  });

  it('accetta gli ordini concorrenti validi del motore alla stessa chiusura', () => {
    // nascita + sospensione per struttura opposta alla nascita; P1 poi pubblicato da sospeso; perdita
    const atBirth = variant(moveFixture, (_, l) => {
      const p1 = { ...find(l, 'P1_PUBLISHED'), whileSuspended: true };
      const loss = l[l.length - 1];
      l.splice(0, l.length, l[0], { t: l[0].t, type: 'SUSPENSION', refId: l[0].refId, side: l[0].side, reason: 'STRUTTURA_OPPOSTA_ALLA_NASCITA', condition: 'SOSPESO_SENZA_P1' }, p1, loss);
      loss.conditionBefore = 'SOSPESO_CON_P1';
    });
    expect(() => parseBundle(atBirth)).not.toThrow();
    // P1 pubblicato e perdita della base alla stessa chiusura
    const p1AndLoss = variant(moveFixture, (_, l) => {
      const p1 = find(l, 'P1_PUBLISHED');
      const loss = { ...l[l.length - 1], t: p1.t, conditionBefore: 'FORMAZIONE' };
      l.splice(0, l.length, l[0], p1, loss);
    });
    expect(() => parseBundle(p1AndLoss)).not.toThrow();
    expect(() => parseBundle(moveFixture)).not.toThrow();
    expect(parseBundle(obs001Fixture).kind).toBe('OBS001_BUNDLE');
    expect(parseBundle(caseFixture).kind).toBe('OBS002_CASE');
  });

  it('dal selettore: errore preciso, studio e momento precedenti intatti', async () => {
    const s = new HistoricalStudy(parseBundle(moveFixture));
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
    fireEvent.click(screen.getByRole('button', { name: 'Chiusura successiva →' }));
    const cutoff = `Cutoff t · ${fmtUtc(s.moveCase!.birthAt + BAR)}`;
    expect(screen.getByText(cutoff)).toBeTruthy();
    const input = screen.getByLabelText('Apri altro studio', { selector: 'input' }) as HTMLInputElement;
    const bad = variant(moveFixture, (_, l) => delete l[0].B);
    await act(async () => {
      fireEvent.change(input, { target: { files: [new File([bad], 'caso.json', { type: 'application/json' })] } });
    });
    await waitFor(() => expect(screen.getByText(/BIRTH: ancora B/)).toBeTruthy());
    expect(screen.getByText(cutoff)).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' })).toBeTruthy();
    expect(screen.queryByText(/dati non previsti/)).toBeNull(); // nessun ricorso al contenimento ViewGuard
  });
});

describe('R1-B: ultima chiusura disponibile', () => {
  const lastClose = (text: string) => {
    const s = new HistoricalStudy(parseBundle(text));
    render(<App createSimulation={() => new SimulatedProvider({ exitDelayMs: 0 })} initialEnvironment="HISTORICAL" initialStudy={s} />);
    const nextBtn = () => screen.getByRole('button', { name: 'Chiusura successiva →' });
    for (let i = 0; i < s.origins.length && !nextBtn().hasAttribute('disabled'); i++) fireEvent.click(nextBtn());
    return s;
  };

  it('la fine copertura è selezionabile e mostra il riferimento aperto, senza conclusioni inventate', () => {
    const s = lastClose(finalFixture);
    const end = s.bundle.periods.end;
    expect(s.origins[s.origins.length - 1]).toBe(end);
    expect(screen.getByText(`Cutoff t · ${fmtUtc(end)}`)).toBeTruthy();
    const card = screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' });
    expect(within(card).getByText(/aperto a fine copertura/)).toBeTruthy();
    expect(within(card).queryByText(/archiviato/)).toBeNull();
    expect(within(card).queryByText('NON_SOSTIENE_PIU_LA_TESI')).toBeNull();
  });

  it('una conclusione esattamente sull’ultima chiusura è visibile solo da quella chiusura', () => {
    const lossAtEnd = variant(finalFixture, (b, l) => {
      const last = l.pop()!;
      l.push({ t: b.periods.end, type: 'ARCHIVE', refId: last.refId, side: last.side, reason: 'ORIGINE_IN_CHIUSURA', judgement: 'NON_SOSTIENE_PIU_LA_TESI',
        judgementReason: 'ORIGINE_IN_CHIUSURA', conditionBefore: 'UTILIZZABILE', C: 1, flags: [] });
    });
    lastClose(lossAtEnd);
    let card = screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' });
    expect(within(card).getByText('NON_SOSTIENE_PIU_LA_TESI')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '← Chiusura precedente' }));
    card = screen.getByRole('region', { name: 'Movimento di riferimento MOVE-001' });
    expect(within(card).queryByText('NON_SOSTIENE_PIU_LA_TESI')).toBeNull();
  });

  it('i pacchetti vecchi restano validi e gli altri formati non accettano origini al confine', () => {
    const old = parseBundle(moveFixture);
    expect(old.origins[old.origins.length - 1]).toBeLessThan(old.periods.end);
    const obs = JSON.parse(obs001Fixture);
    obs.origins.push(obs.periods.end);
    expect(() => parseBundle(JSON.stringify(obs))).toThrow(/griglia 45m/);
    const o2 = JSON.parse(caseFixture);
    o2.origins.push(o2.periods.end);
    expect(() => parseBundle(JSON.stringify(o2))).toThrow(/griglia 45m/);
  });
});
