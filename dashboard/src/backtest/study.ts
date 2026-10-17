/**
 * Provider del backtest di sviluppo: selezione dei dati già elaborati dal motore CAND-001.
 * Nessun ricalcolo di decisioni o costi. Il «momento consultato» separa ciò che era noto
 * (available_at <= momento) dal seguito modellato, mostrato solo su richiesta esplicita.
 */
import type { BacktestBundle, BtEpisode, BtLeg, BtPivot, BtSnapshot, BtTrade, BtWindow, ExampleCategory, ExampleRef, Side } from '../contract/backtest';
import type { HistCandle, Ms } from '../contract/historical';

export interface HeadlineExample {
  readonly label: string;
  readonly categories: readonly ExampleCategory[];
  readonly ref: (ExampleRef & { readonly side: Side; readonly category: ExampleCategory }) | null;
}

export interface PlanLevel {
  readonly id: string;
  readonly kind: 'TARGET' | 'STOP' | 'ENTRY' | 'EXIT' | 'P0' | 'REACTION';
  readonly label: string;
  readonly price: number;
}

const HEADLINES: [string, ExampleCategory[]][] = [
  ['Prima decisione', ['FIRST_CALL']],
  ['Prima operazione', ['FIRST_TRADE']],
  ['Primo caso negativo', ['FIRST_NEGATIVE_TRADE']],
  ['Prima astensione', ['FIRST_ABSTAIN_REACTION_INVALIDATED', 'FIRST_ABSTAIN_REWARD_RISK', 'FIRST_ABSTAIN_MISSING_DATA']],
  ['Prima protezione aggiornata', ['FIRST_PROTECTION_UPDATE']],
];

export class BacktestStudy {
  readonly bundle: BacktestBundle;
  private readonly episodes: Map<string, BtEpisode>;
  private readonly trades: Map<string, BtTrade>;
  private readonly legs: Map<string, BtLeg>;

  constructor(bundle: BacktestBundle) {
    this.bundle = bundle;
    this.episodes = new Map(bundle.episodes.map((e) => [e.id, e]));
    this.trades = new Map(bundle.trades.map((t) => [t.id, t]));
    this.legs = new Map(bundle.exampleLegs.map((l) => [l.id, l]));
  }

  get synthetic(): boolean {
    return this.bundle.run.synthetic === true;
  }

  /** I cinque pulsanti: per ciascuno il primo esempio cronologico fra LONG e SHORT (tie: tempo, poi ID). */
  headlines(): HeadlineExample[] {
    const ex = this.bundle.summary.examples;
    return HEADLINES.map(([label, cats]) => {
      const found = (['LONG', 'SHORT'] as Side[]).flatMap((side) =>
        cats.flatMap((c) => (ex[side][c] ? [{ ...(ex[side][c] as ExampleRef), side, category: c }] : [])),
      );
      found.sort((a, b) => a.t - b.t || a.id.localeCompare(b.id));
      return { label, categories: cats, ref: found[0] ?? null };
    });
  }

  allExamples(): (ExampleRef & { side: Side; category: ExampleCategory })[] {
    const ex = this.bundle.summary.examples;
    return (['LONG', 'SHORT'] as Side[]).flatMap((side) =>
      (Object.keys(ex[side]) as ExampleCategory[]).flatMap((c) => (ex[side][c] ? [{ ...(ex[side][c] as ExampleRef), side, category: c }] : [])),
    );
  }

  episode(id: string): BtEpisode | undefined {
    return this.episodes.get(id);
  }

  leg(id: string): BtLeg | undefined {
    return this.legs.get(id);
  }

  trade(id: string | null | undefined): BtTrade | undefined {
    return id ? this.trades.get(id) : undefined;
  }

  window(id: string): BtWindow | undefined {
    return this.bundle.windows[id];
  }

  /** Fotografia delle osservazioni più recente con t <= momento (solo informazioni già note). */
  snapshotAt(id: string, cursor: Ms): BtSnapshot | null {
    const w = this.window(id);
    if (!w) return null;
    const ts = Object.keys(w.snapshots).map(Number).filter((t) => t <= cursor).sort((a, b) => a - b);
    return ts.length ? w.snapshots[String(ts[ts.length - 1])] : null;
  }

  /** Candele della finestra: fino al momento (vista causale) oppure tutte con il seguito marcato. */
  candles(id: string, scale: '45m' | '1D', cursor: Ms, retrospective: boolean): HistCandle[] {
    const w = this.window(id);
    if (!w) return [];
    const bars = scale === '45m' ? w.bars45 : w.bars1d;
    const step = scale === '45m' ? 45 * 60_000 : 86_400_000;
    const out: HistCandle[] = [];
    for (let i = 0; i < bars.open.length; i++) {
      const end = bars.open[i] + step;
      const after = end > cursor;
      if (after && !retrospective) break;
      out.push({
        openTime: bars.open[i], end, open: bars.o[i] ?? 0, high: bars.h[i] ?? 0, low: bars.l[i] ?? 0, close: bars.c[i] ?? 0, volume: bars.v[i] ?? 0,
        gap: bars.status[i] !== 'COMPLETE', retrospective: after,
      });
    }
    return out;
  }

  sma(id: string, candles: readonly HistCandle[]): { sma20: { time: Ms; value: number }[]; sma50: { time: Ms; value: number }[] } {
    const w = this.window(id);
    const out = { sma20: [] as { time: Ms; value: number }[], sma50: [] as { time: Ms; value: number }[] };
    if (!w) return out;
    const idx = new Map(w.bars45.open.map((t, i) => [t, i]));
    for (const c of candles) {
      if (c.retrospective) continue;
      const i = idx.get(c.openTime);
      if (i === undefined) continue;
      const a = w.sma20[i];
      const b = w.sma50[i];
      if (a !== null) out.sma20.push({ time: c.openTime, value: a });
      if (b !== null) out.sma50.push({ time: c.openTime, value: b });
    }
    return out;
  }

  /** Pivot confermati entro il momento: disegnati sulla candela d'origine solo dopo available_at. */
  pivots(id: string, cursor: Ms): BtPivot[] {
    return (this.window(id)?.pivots ?? []).filter((p) => p.availableAt <= cursor);
  }

  /**
   * Livelli del piano noti al momento: P0/P1 dalla gamba, stop originario e target dalla call,
   * stop corrente dalle protezioni già efficaci; ingresso/uscita solo se avvenuti entro il momento
   * o nel seguito richiesto.
   */
  levels(ep: BtEpisode, cursor: Ms, retrospective: boolean): PlanLevel[] {
    const out: PlanLevel[] = [];
    const known = (t: Ms) => retrospective || t <= cursor;
    if (ep.t0 <= cursor) {
      out.push({ id: 'p0', kind: 'P0', label: `P0 · ${ep.P0.kind === 'LOW' ? 'minimo' : 'massimo'} di partenza`, price: ep.P0.price });
      out.push({ id: 'p1', kind: 'TARGET', label: 'P1 · estremo della gamba', price: ep.P1.price });
    }
    if (ep.call && ep.call.t <= cursor) out.push({ id: 's0', kind: 'STOP', label: 'STOP ORIGINARIO', price: ep.call.S0 });
    const tr = this.trade(ep.tradeId);
    if (tr) {
      if (known(tr.entryTime)) out.push({ id: 'entry', kind: 'ENTRY', label: 'INGRESSO MODELLATO', price: tr.E });
      const active = tr.stops.filter((s) => known(s.effectiveAt));
      if (active.length) out.push({ id: 'stop', kind: 'STOP', label: 'STOP CORRENTE', price: active[active.length - 1].to });
      // Percorso irrisolto: nessuna uscita da disegnare, mai un prezzo inventato.
      if (tr.exit && known(tr.exit.accountingTime)) out.push({ id: 'exit', kind: 'EXIT', label: 'USCITA MODELLATA', price: tr.exit.X });
    }
    return out;
  }
}
