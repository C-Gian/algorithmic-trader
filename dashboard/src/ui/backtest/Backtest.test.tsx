/**
 * CAND-001 nella dashboard, su bundle di backtest SINTETICO prodotto dal motore (prezzi inventati).
 * Import di un file esterno e contratto, pagina risultati in linguaggio semplice, esempi dal registro,
 * vista del momento vs ciò che è successo dopo, rinuncia, tentativo non eseguito, motivi veri di
 * chiusura, spiegazioni «i» da mouse/clic/tastiera, registro → dettaglio e separazione dalla simulazione.
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fixture from '../../backtest/__fixtures__/synthetic-backtest.json?raw';
import obsFixture from '../../historical/__fixtures__/synthetic-bundle.json?raw';
import { FakeApi } from '../../backtest/__fixtures__/fakeApi';
import { BacktestBundleError, parseBacktest } from '../../backtest/loadBacktest';
import { BacktestStudy } from '../../backtest/study';
import { SimulatedProvider } from '../../sim/provider';
import { App } from '../App';
import { EpisodeView } from './EpisodeView';
import { usdt } from './text';

const BANNER = 'Simulazione su prezzi storici. Nessuna operazione reale.';

beforeEach(() => {
  window.scrollTo = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

const study = () => new BacktestStudy(parseBacktest(fixture));
const sim = () => new SimulatedProvider({ exitDelayMs: 0 });
const env = (name: string) => within(screen.getByRole('group', { name: 'Ambiente', hidden: true })).getByRole('button', { name, hidden: true });
const FILE = { kind: 'file' } as const;

async function upload(label: string, text: string) {
  const input = screen.getByLabelText(label, { selector: 'input' }) as HTMLInputElement;
  await act(async () => {
    fireEvent.change(input, { target: { files: [new File([text], 'cand001-bundle.json', { type: 'application/json' })] } });
  });
}

function setup() {
  const s = study();
  render(<App createSimulation={sim} initialEnvironment="BACKTEST" initialBacktest={s} api={new FakeApi()} />);
  return s;
}

describe('file esterno del backtest', () => {
  it('l’ambiente si chiama Backtest, ha il banner e parte da «Nuovo backtest»', async () => {
    render(<App createSimulation={sim} api={new FakeApi()} />);
    fireEvent.click(env('Backtest'));
    expect(window.location.hash).toBe('#/backtest/new');
    expect(screen.getByText(BANNER)).toBeTruthy();
    expect(await screen.findByRole('region', { name: 'Nuovo backtest' })).toBeTruthy();
    expect(screen.queryByText('Risultato dopo i costi')).toBeNull();
    expect(screen.queryByRole('button', { name: /Scenari simulati/ })).toBeNull();
  });

  it('file di altro tipo o incompleto: errore leggibile; il file aperto resta; poi file valido', async () => {
    render(<App createSimulation={sim} initialEnvironment="BACKTEST" api={new FakeApi()} />);
    fireEvent.click(screen.getByRole('link', { name: 'Risultati salvati' }));
    await upload('Apri file esterno', obsFixture);
    await waitFor(() => expect(screen.getByText(/bundle dello studio osservativo OBS-001/)).toBeTruthy());
    await upload('Apri file esterno', fixture);
    await waitFor(() => expect(screen.getByText('Esempi dal registro')).toBeTruthy());
    expect(window.location.hash).toBe('#/backtest/file');
    fireEvent.click(screen.getByRole('link', { name: 'Risultati salvati' }));
    const broken = JSON.parse(fixture);
    delete broken.trades[0].exit.Xref;
    await upload('Apri file esterno', JSON.stringify(broken));
    await waitFor(() => expect(screen.getByText(/Operazioni, 1ª, uscita: valore «Xref» assente/)).toBeTruthy());
    act(() => window.history.back());
    await waitFor(() => expect(screen.getByText('Esempi dal registro')).toBeTruthy()); // file precedente conservato
  });

  it('il validatore richiede finestre per gli esempi, campi annidati dei mesi e un profilo coerente per /3', () => {
    const noWindow = JSON.parse(fixture);
    const ref = noWindow.summary.examples.LONG.FIRST_TRADE;
    delete noWindow.windows[ref.episodeId];
    expect(() => parseBacktest(JSON.stringify(noWindow))).toThrow(/finestra del grafico assente/);
    const month = JSON.parse(fixture);
    const m = Object.keys(month.summary.months)[0];
    delete month.summary.months[m].trades.exits.STOP;
    expect(() => parseBacktest(JSON.stringify(month))).toThrow(BacktestBundleError);
    const v3 = JSON.parse(fixture);
    v3.schema = 'cand001.bundle/3';
    expect(() => parseBacktest(JSON.stringify(v3))).toThrow(/campo «profile» assente/);
    v3.profile = { id: 'DEV', label: 'x', kind: 'DEVELOPMENT', window: { start: v3.window.start, end: v3.window.end + 1 } };
    expect(() => parseBacktest(JSON.stringify(v3))).toThrow(/Periodo del profilo diverso/);
    v3.profile.window.end = v3.window.end;
    expect(new BacktestStudy(parseBacktest(JSON.stringify(v3))).profile.inferred).toBeUndefined();
    const v1 = JSON.parse(fixture);
    v1.schema = 'cand001.bundle/1';
    expect(() => parseBacktest(JSON.stringify(v1))).toThrow(/conservato ma non supportato/);
    expect(study().profile).toMatchObject({ id: 'DEV', label: 'Sviluppo 2023–2024', inferred: true });
  });
});

describe('risultati in linguaggio semplice', () => {
  it('risultato dopo i costi, dimensione convenzionale, voci riconciliate, stress separato, dettagli tecnici espandibili', () => {
    const s = setup();
    const t = s.bundle.summary.tables.DEV.trades;
    expect(screen.getByText(BANNER)).toBeTruthy();
    const head = screen.getByRole('region', { name: 'Risultato del backtest' });
    expect(within(head).getByText('Risultato dopo i costi')).toBeTruthy();
    expect(within(head).getByText(usdt(t.net))).toBeTruthy();
    expect(within(head).getByText('Dimensione di ogni operazione: 1.000 USDT')).toBeTruthy();
    expect(within(head).getByText(/non promosso/)).toBeTruthy();
    expect(within(head).getByText('FIXTURE SINTETICA')).toBeTruthy();
    expect(within(head).getByRole('link', { name: `Tutte le operazioni (${s.bundle.trades.length})` })).toBeTruthy();
    const parts = screen.getByRole('region', { name: 'Da dove viene il risultato' });
    const cell = (label: string) => within(parts).getByText(label).closest('tr')!.querySelectorAll('td')[1].textContent;
    expect(cell('Guadagno/perdita dal solo movimento dei prezzi')).toBe(usdt(t.pricePnLRef));
    expect(cell('Effetto del prezzo di esecuzione')).toBe(usdt(t.slippage));
    expect(cell('Commissioni')).toBe(usdt(-t.fees!));
    expect(cell('Pagamento periodico del contratto')).toBe(usdt(t.funding));
    expect(t.pricePnLRef! + t.slippage! - t.fees! + t.funding!).toBeCloseTo(t.net!, 6); // nessun doppio conteggio
    const stress = screen.getByRole('region', { name: 'Scenario con costi più alti' });
    expect(within(stress).getByText(usdt(t.stressNet))).toBeTruthy();
    // bp, N0 e profit factor solo nei dettagli espandibili, non nel riepilogo.
    expect(within(head).queryByText(/bp|N0/)).toBeNull();
    const tech = screen.getByLabelText('Dettagli tecnici');
    expect(tech.tagName).toBe('DETAILS');
    expect(within(tech).getByText(/−40 bp di N0\s+corrispondono a circa −4 USDT/)).toBeTruthy();
    expect(screen.queryByText(/10\.000/)).toBeNull();
  });

  it('spiegazioni «i»: al passaggio del mouse, al focus da tastiera e al clic; Esc chiude', () => {
    setup();
    const btn = screen.getByRole('button', { name: 'Spiegazione: Effetto del prezzo di esecuzione' });
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.focus(btn);
    expect(screen.getByRole('tooltip').textContent).toMatch(/non viene sottratta una seconda volta/);
    expect(btn.getAttribute('aria-describedby')).toBe(screen.getByRole('tooltip').id);
    fireEvent.keyDown(btn, { key: 'Escape' });
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.click(btn);
    expect(screen.getByRole('tooltip')).toBeTruthy();
    fireEvent.click(btn);
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.mouseEnter(btn.parentElement!);
    expect(screen.getByRole('tooltip')).toBeTruthy();
    fireEvent.mouseLeave(btn.parentElement!);
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(screen.getByRole('region', { name: 'Risultato del backtest' })).toBeTruthy(); // contesto conservato
  });

  it('esempi dal registro: primi casi cronologici, categorie assenti dichiarate, coincidenze spiegate', () => {
    const s = setup();
    const ex = screen.getByRole('region', { name: 'Esempi dal registro' });
    expect(within(ex).getByText(/Non\s+sono tutto il risultato/)).toBeTruthy();
    for (const label of ['Prima decisione', 'Prima operazione', 'Primo caso negativo', 'Prima astensione']) {
      expect(within(ex).getByRole('link', { name: label })).toBeTruthy();
    }
    expect(within(ex).getByText('Prima protezione aggiornata · assente')).toBeTruthy();
    const h = s.headlines();
    const first = h.find((x) => x.label === 'Prima operazione')!.ref!;
    const neg = h.find((x) => x.label === 'Primo caso negativo')!.ref!;
    if (first.episodeId === neg.episodeId) expect(within(ex).getByText(/è lo stesso episodio di «Prima operazione»/)).toBeTruthy();
  });
});

describe('dettaglio dell’operazione', () => {
  it('un clic apre la decisione con le sole informazioni del momento; il seguito solo su richiesta; ritorno ai risultati', () => {
    const s = setup();
    fireEvent.click(screen.getByRole('link', { name: 'Prima operazione' }));
    expect(window.location.hash).toMatch(/^#\/backtest\/file\/episodes\/.+\?from=examples$/);
    const ref = s.headlines().find((h) => h.label === 'Prima operazione')!.ref!;
    const ep = s.episode(ref.episodeId!)!;
    const side = ep.side === 'LONG' ? 'una salita' : 'una discesa';
    expect(screen.getByText(`Il bot ha riconosciuto ${side}`)).toBeTruthy();
    expect(screen.getByText('Ha aspettato una reazione')).toBeTruthy();
    expect(screen.getByText(`Ha deciso di tentare ${ep.side === 'LONG' ? 'un acquisto' : 'una vendita'}`)).toBeTruthy();
    expect(screen.getByText('Non è ancora entrato')).toBeTruthy();
    expect(screen.getByText('SOLO INFORMAZIONI DEL MOMENTO')).toBeTruthy();
    expect(screen.queryByText(/La posizione è stata chiusa perché/)).toBeNull();
    expect(screen.queryByText(/La posizione simulata è stata aperta/)).toBeNull();
    expect(screen.queryByLabelText("Risultato dell'operazione")).toBeNull();
    expect(s.candles(ep.id, '45m', ep.call!.t, false).every((c) => c.end <= ep.call!.t)).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: 'Mostra cosa è successo dopo' }));
    const tr = s.trade(ep.tradeId)!;
    expect(screen.getByText(`La posizione simulata è stata aperta a ${tr.E.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`)).toBeTruthy();
    expect(screen.getByText(/La posizione è stata chiusa perché/)).toBeTruthy();
    const result = screen.getByLabelText("Risultato dell'operazione");
    expect(within(result).getByText('A POSTERIORI')).toBeTruthy();
    expect(within(result).getByText('Risultato dopo i costi').parentElement!.querySelector('.metric-value')!.textContent).toBe(usdt(tr.net));
    fireEvent.click(screen.getByRole('button', { name: 'Solo informazioni del momento' }));
    expect(screen.queryByLabelText("Risultato dell'operazione")).toBeNull();
    fireEvent.click(screen.getByRole('link', { name: '← Torna ai risultati' }));
    expect(window.location.hash).toBe('#/backtest/file');
    expect(screen.getByText('Esempi dal registro')).toBeTruthy();
  });

  it('prima astensione: «Ha rinunciato» con il motivo, nessuna posizione', () => {
    setup();
    fireEvent.click(screen.getByRole('link', { name: 'Prima astensione' }));
    expect(screen.getByText('Ha rinunciato')).toBeTruthy();
    expect(screen.queryByText(/La posizione simulata è stata aperta/)).toBeNull();
  });

  it('tutte le operazioni: ogni riga apre il dettaglio con «Torna alle operazioni»', () => {
    const s = setup();
    fireEvent.click(screen.getByRole('link', { name: `Tutte le operazioni (${s.bundle.trades.length})` }));
    const table = screen.getByRole('region', { name: 'Tutte le operazioni' });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(s.bundle.trades.length);
    expect(rows[0].textContent).toMatch(/obiettivo raggiunto|limite di perdita|fine del periodo/);
    fireEvent.click(rows[1]);
    expect(screen.getByRole('link', { name: '← Torna alle operazioni' })).toBeTruthy();
    fireEvent.click(screen.getByRole('link', { name: '← Torna alle operazioni' }));
    expect(screen.getByRole('region', { name: 'Tutte le operazioni' })).toBeTruthy();
    fireEvent.click(screen.getByRole('link', { name: '← Torna ai risultati' }));
    expect(screen.getByRole('region', { name: 'Risultato del backtest' })).toBeTruthy();
  });

  it('i comandi della simulazione non modificano i risultati congelati', () => {
    const s = setup();
    const before = JSON.stringify(s.bundle.summary.tables);
    fireEvent.click(env('Simulazione locale'));
    fireEvent.click(screen.getByRole('button', { name: 'Stop totale' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Ferma il bot' }));
    act(() => window.history.back());
    return waitFor(() => {
      expect(screen.getByText('Esempi dal registro')).toBeTruthy();
      expect(JSON.stringify(s.bundle.summary.tables)).toBe(before);
    });
  });
});

describe('tentativo non eseguito, limiti di protezione e motivi di chiusura', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function mutated(edit: (b: any) => void) {
    const b = JSON.parse(fixture);
    edit(b);
    return new BacktestStudy(b);
  }

  it('richiesta rifiutata: «non è stato/a eseguito/a» con il motivo, nessuna posizione né costo', () => {
    const s = mutated((b) => {
      const tr = b.trades[0];
      const ep = b.episodes.find((e: any) => e.id === tr.episodeId);
      ep.request = { ...ep.request, outcome: 'REJECTED_PRICE', Oref: ep.call.entryBound * (ep.d === 1 ? 1.01 : 0.99) };
      ep.tradeId = null;
      ep.termination = { t: ep.call.executeAt, code: 'REJECTED_PRICE' };
      ep.states = [...ep.states.filter((x: any) => x.t <= ep.call.t), { t: ep.call.executeAt, state: 'REJECTED_PRICE' }];
    });
    const ep = s.bundle.episodes.find((e) => e.request?.outcome === 'REJECTED_PRICE')!;
    render(<EpisodeView study={s} id={ep.id} source={FILE} from="operations" />);
    expect(screen.queryByText(/non è stat. eseguit/)).toBeNull(); // al momento della decisione l'esito non è ancora noto
    fireEvent.click(screen.getByRole('button', { name: 'Mostra cosa è successo dopo' }));
    const verb = ep.side === 'LONG' ? 'L’acquisto non è stato eseguito' : 'La vendita non è stata eseguita';
    expect(screen.getByText(verb)).toBeTruthy();
    expect(screen.getByText(/il prezzo era già oltre il limite fissato.*Nessuna posizione\s+è stata aperta e nessuna commissione/s)).toBeTruthy();
    expect(screen.queryByText(/La posizione simulata è stata aperta/)).toBeNull();
    expect(screen.queryByLabelText("Risultato dell'operazione")).toBeNull();
    expect(screen.queryByText('Ha rinunciato')).toBeNull();
  });

  it('limite di protezione su SHORT: scende, con prima/dopo e momento efficace', () => {
    const s = mutated((b) => {
      const tr = b.trades.find((t: any) => t.side === 'SHORT');
      tr.stops = [{ decidedAt: tr.entryTime + 45 * 60_000, effectiveAt: tr.entryTime + 46 * 60_000, from: tr.S0, to: tr.S0 - 50, pivot: tr.S0 - 80 }];
    });
    const tr = s.bundle.trades.find((t) => t.stops.length)!;
    render(<EpisodeView study={s} id={tr.episodeId} source={FILE} from="operations" />);
    fireEvent.click(screen.getByRole('button', { name: 'Mostra cosa è successo dopo' }));
    expect(screen.getByText(/^Nuovo limite di protezione: da .* a .*$/)).toBeTruthy();
    expect(screen.getByText(/Per una posizione su una discesa il limite scende/)).toBeTruthy();
    expect(screen.queryByText(/alzat/)).toBeNull();
  });

  it('motivi veri di chiusura e contatto dentro il minuto distinto dall’orario contabile', () => {
    const s = study();
    const why: Record<string, RegExp> = {
      TARGET: /chiusa perché il prezzo ha raggiunto l’obiettivo/,
      STOP: /chiusa perché il prezzo ha raggiunto il limite di perdita/,
      END_OF_SEGMENT: /chiusa perché è finito il periodo valutato/,
    };
    for (const tr of s.bundle.trades) {
      cleanup();
      render(<EpisodeView study={s} id={tr.episodeId} source={FILE} from="operations" />);
      fireEvent.click(screen.getByRole('button', { name: 'Mostra cosa è successo dopo' }));
      expect(screen.getByText(why[tr.exit!.reason])).toBeTruthy();
      if (tr.exit!.intrabar) expect(screen.getByText(/Contatto avvenuto durante il minuto .*registrato alle/)).toBeTruthy();
      else expect(screen.getByText(/all’apertura del minuto. Prezzo di riferimento/)).toBeTruthy();
    }
  });
});
