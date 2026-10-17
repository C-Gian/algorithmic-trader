/**
 * Provider dello studio storico: selezione causale dei dati del bundle a un cutoff t.
 * Nessun calcolo del motore: barre, osservazioni ed eventi sono già nel bundle. Le righe con
 * gli esiti si leggono solo tramite `retrospective()`, chiamato dalle viste a posteriori.
 */
import { CASE_KIND, MOVE_KIND, type CausalSnapshot, type HistCandle, type HistScale, type Move001Case, type Ms, type Obs002Case, type Obs002Outcome, type StudyBundle, type StudyEvent, type StudyRow } from '../contract/historical';

const DAY_MS = 86_400_000;

function lastIndexAtOrBefore(events: readonly StudyEvent[], t: Ms): number {
  let lo = 0;
  let hi = events.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (events[mid].availableAt <= t) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export class HistoricalStudy {
  readonly bundle: StudyBundle;
  readonly origins: readonly Ms[];
  private readonly step: Record<HistScale, Ms>;
  private readonly rowsByT: Map<Ms, StudyRow>;

  constructor(bundle: StudyBundle) {
    this.bundle = bundle;
    this.origins = bundle.origins;
    const width = (scale: HistScale) => bundle.bars[scale].open[1] - bundle.bars[scale].open[0];
    this.step = { '45m': width('45m'), '1D': width('1D') };
    this.rowsByT = new Map(bundle.retrospective.rows.map((r) => [r.t, r]));
  }

  get synthetic(): boolean {
    return this.bundle.run.synthetic === true;
  }

  /** Caso del pacchetto OBS-002 (informazioni note a t), assente nei bundle OBS-001. */
  get obs002Case(): Obs002Case | null {
    return this.bundle.kind === CASE_KIND ? ((this.bundle.case as Obs002Case | undefined) ?? null) : null;
  }

  /** Riferimento del pacchetto MOVE-001 (identità e fatti datati), assente negli altri pacchetti. */
  get moveCase(): Move001Case | null {
    return this.bundle.kind === MOVE_KIND ? ((this.bundle.case as unknown as Move001Case | undefined) ?? null) : null;
  }

  /** Fatti MOVE-001 noti al momento t: soli eventi del ledger con istante <= t. */
  moveFactsAt(t: Ms): Move001Case['ledger'] {
    const c = this.moveCase;
    return c ? c.ledger.filter((e) => e.t <= t) : [];
  }

  /** Esito OBS-002 a posteriori dell'origine t, solo se è l'istante del caso. Solo per viste retrospettive. */
  obs002Outcome(t: Ms): Obs002Outcome | null {
    const o = this.bundle.retrospective.obs002;
    return o && o.outcome.t === t ? o.outcome : null;
  }

  indexOf(t: Ms): number {
    return this.origins.indexOf(t);
  }

  /** Indice dell'ultima barra della scala terminata entro t (giorno in formazione escluso). */
  private lastBarIndex(scale: HistScale, t: Ms): number {
    const start = this.bundle.periods.inputStart;
    const ref = scale === '1D' ? t - (t % DAY_MS) : t;
    return Math.floor((ref - start) / this.step[scale]) - 1;
  }

  snapshot(t: Ms): CausalSnapshot {
    const k45 = this.lastBarIndex('45m', t);
    const kd = this.lastBarIndex('1D', t);
    const m45 = this.bundle.observations['45m'][k45];
    if (!m45 || m45.end !== t) throw new Error(`Cutoff ${t} fuori dalla griglia 45m del bundle`);
    const d1 = kd >= 0 ? this.bundle.observations['1D'][kd] : null;
    const events = {
      '45m': this.bundle.events['45m'].slice(0, lastIndexAtOrBefore(this.bundle.events['45m'], t)),
      '1D': this.bundle.events['1D'].slice(0, lastIndexAtOrBefore(this.bundle.events['1D'], t)),
    };
    return { t, m45, d1, events };
  }

  /**
   * Candele della scala fino al cutoff (count barre) e, solo se richiesto, il seguito
   * retrospettivo fino a min(t+24h, fine input), marcato come tale.
   */
  candles(scale: HistScale, t: Ms, count: number, retrospective: boolean): HistCandle[] {
    const bars = this.bundle.bars[scale];
    const last = this.lastBarIndex(scale, t);
    const from = Math.max(0, last - count + 1);
    let to = last;
    if (retrospective) {
      const horizon = Math.min(t + DAY_MS, this.bundle.periods.end);
      while (to + 1 < bars.open.length && bars.open[to + 1] + this.step[scale] <= horizon) to += 1;
    }
    const out: HistCandle[] = [];
    for (let i = from; i <= to; i++) {
      const gap = bars.status[i] !== 'COMPLETE';
      out.push({
        openTime: bars.open[i],
        end: bars.open[i] + this.step[scale],
        open: bars.o[i] ?? 0,
        high: bars.h[i] ?? 0,
        low: bars.l[i] ?? 0,
        close: bars.c[i] ?? 0,
        volume: bars.v[i] ?? 0,
        gap,
        retrospective: i > last,
      });
    }
    return out;
  }

  /**
   * Ultima chiusura completa della scala terminata entro t (mai oltre il cutoff) con il suo
   * orario di fine. Serve solo a qualificare un «ultimo noto» quando la barra al cutoff manca.
   */
  lastKnownClose(scale: HistScale, t: Ms): { price: number; end: Ms } | null {
    const bars = this.bundle.bars[scale];
    for (let i = this.lastBarIndex(scale, t); i >= 0; i--) {
      const c = bars.c[i];
      if (bars.status[i] === 'COMPLETE' && c !== null) return { price: c, end: bars.open[i] + this.step[scale] };
    }
    return null;
  }

  /** Serie SMA20/SMA50 della scala per le barre mostrate, dai record già calcolati. */
  sma(scale: HistScale, candles: readonly HistCandle[]): { sma20: { time: Ms; value: number }[]; sma50: { time: Ms; value: number }[] } {
    const recs = this.bundle.observations[scale];
    const start = this.bundle.periods.inputStart;
    const sma20: { time: Ms; value: number }[] = [];
    const sma50: { time: Ms; value: number }[] = [];
    for (const c of candles) {
      if (c.retrospective) continue; // le medie restano allo snapshot: nessuna serie oltre il cutoff
      const rec = recs[Math.round((c.openTime - start) / this.step[scale])];
      if (rec?.avg.sma20.v != null) sma20.push({ time: c.openTime, value: rec.avg.sma20.v });
      if (rec?.avg.sma50.v != null) sma50.push({ time: c.openTime, value: rec.avg.sma50.v });
    }
    return { sma20, sma50 };
  }

  /**
   * Gruppo dell'origine t (struttura 45m, 1D e relazione giornaliera), calcolato dal motore con
   * informazioni disponibili a t. Restituisce solo questi campi causali, mai gli esiti.
   */
  causalGroup(t: Ms): Pick<StudyRow, 's45' | 's1d' | 'dailyRelation'> | null {
    const row = this.rowsByT.get(t);
    return row ? { s45: row.s45, s1d: row.s1d, dailyRelation: row.dailyRelation } : null;
  }

  /** Riga a posteriori dell'origine t: esiti 24h. Solo per viste retrospettive esplicite. */
  retrospective(t: Ms): StudyRow | undefined {
    return this.rowsByT.get(t);
  }
}
