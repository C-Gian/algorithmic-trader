import type { ReactNode } from 'react';
import type { CausalSnapshot, HistScale, ObservationRecord, PivotRef } from '../../contract/historical';
import { formatNumber } from '../../lib/numbers';
import { Badge } from '../components/primitives';
import { fmtUtc, isoMinute } from '../format';
import { STRUCTURE_LABEL, measure, plain, price, ratio, reasonText } from './fmt';

type Row = [string, ReactNode];

function Rows({ rows }: { rows: Row[] }) {
  return (
    <div className="fam-rows">
      {rows.map(([k, v]) => (
        <div className="fam-row" key={k}>
          <span className="fam-k">{k}</span>
          <span className="fam-v">{v}</span>
        </div>
      ))}
    </div>
  );
}

const pivot = (p: PivotRef | undefined) =>
  p ? `${price(p.price)} · candela ${isoMinute(p.candidateOpen)} · nota ${isoMinute(p.availableAt)}` : '—';

const pct = (r: number) => `${formatNumber(r * 100, 1)}%`;

function Family({
  title,
  formula,
  snapshot,
  render,
  note,
}: {
  title: string;
  formula: string;
  snapshot: CausalSnapshot;
  render: (rec: ObservationRecord, scale: HistScale) => Row[];
  note?: string;
}) {
  const scales: [HistScale, ObservationRecord | null][] = [
    ['45m', snapshot.m45],
    ['1D', snapshot.d1],
  ];
  return (
    <article className="card signal fam-card" aria-label={title}>
      <div className="signal-head">
        <p className="signal-title">{title}</p>
        <Badge tone="neutral">45m · 1D</Badge>
      </div>
      <p className="fam-formula mono">{formula}</p>
      <div className="fam-scales">
        {scales.map(([scale, rec]) => (
          <div key={scale} className="fam-scale">
            <p className="kv-label">
              {scale === '45m' ? 'SCALA 45m' : 'SCALA 1D'} · {rec ? `barra chiusa ${fmtUtc(rec.end)}` : 'nessun giorno chiuso'}
            </p>
            {!rec ? (
              <p className="empty">Non disponibile: storia insufficiente.</p>
            ) : rec.status !== 'COMPLETE' ? (
              <p className="empty">Barra incompleta ({rec.inputRef.missing} minuti mancanti): {reasonText('INCOMPLETE_INPUT')}.</p>
            ) : (
              <Rows rows={render(rec, scale)} />
            )}
          </div>
        ))}
      </div>
      {note && <p className="signal-context">{note}</p>}
    </article>
  );
}

/** Sei famiglie consultabili alle due scale: valori effettivi, parametri, tempi e motivi. */
export function FamiliesSection({ snapshot }: { snapshot: CausalSnapshot }) {
  return (
    <section className="section" id="segnali" aria-label="Osservazioni calcolate" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
      <div className="section-head">
        <div>
          <p className="section-title">Le sei famiglie di osservazioni al cutoff t</p>
          <p className="section-desc">
            Convenzioni OBS-001/v1, parametri iniziali non ottimizzati. Ogni valore usa solo barre terminate entro t; «n.d.» indica il motivo per misura.
          </p>
        </div>
        <span className="section-aside">Unità A = USDT per BTC</span>
      </div>
      <div className="fam-grid">
        <Family
          title="Volatilità"
          formula="TR = max(H−L, |H−Cprec|, |L−Cprec|) · A = media aritmetica degli ultimi 20 TR (21 barre contigue, non Wilder)"
          snapshot={snapshot}
          render={(r) => [
            ['TR ultima barra', measure(r.vol.tr, 2, { suffix: 'USDT' })],
            ['A', measure(r.vol.A, 2, { suffix: 'USDT' })],
            ['A / C', r.vol.AoverC.v === null ? measure(r.vol.AoverC, 4) : `${formatNumber(r.vol.AoverC.v * 100, 3)}%`],
            ['Barre contigue nel segmento', r.segment ? String(r.segment.bars) : '—'],
          ]}
        />
        <Family
          title="Medie (SMA)"
          formula="SMA20, SMA50 delle chiusure · distanza (SMA20−SMA50)/A · pendenza (SMA20−SMA20[−4])/A · posizione (C−SMA20)/A"
          snapshot={snapshot}
          render={(r) => [
            ['SMA20', measure(r.avg.sma20, 2)],
            ['SMA50', measure(r.avg.sma50, 2)],
            ['Distanza / A', measure(r.avg.dist, 3, { signed: true })],
            ['Pendenza SMA20 (4 barre) / A', measure(r.avg.slope, 3, { signed: true })],
            ['Posizione / A', measure(r.avg.pos, 3, { signed: true })],
            ['Incrocio a questa chiusura', r.avg.cross.v === null ? measure(r.avg.cross as never, 0) : r.avg.cross.v === 'NONE' ? 'nessuno' : r.avg.cross.v],
          ]}
          note="Medie semplici (SMA), non esponenziali. Incrocio: cambio di segno della distanza; zero mantenuto non è un nuovo incrocio."
        />
        <Family
          title="Pivot e struttura"
          formula="Pivot: H (o L) strettamente oltre le 2 barre prima e le 2 dopo · confermato alla chiusura della seconda barra destra"
          snapshot={snapshot}
          render={(r) => {
            const s = r.piv.structure;
            const check = r.piv.check.v;
            return [
              ['Struttura', s.v ? STRUCTURE_LABEL[s.v] : `n.d. · ${reasonText(s.r)}`],
              ['High precedente', pivot(r.piv.highs[0])],
              ['High ultimo', pivot(r.piv.highs[1])],
              ['Low precedente', pivot(r.piv.lows[0])],
              ['Low ultimo', pivot(r.piv.lows[1])],
              ['Candidata valutata ora', check ? `${isoMinute(check.candidateOpen)} · high ${check.high} · low ${check.low}` : reasonText(r.piv.check.r)],
            ];
          }}
          note="Un pivot diventa noto solo due barre dopo la sua candela: il grafico lo segna sulla candela originale e indica entrambi gli orari. Parità e candele ambigue (high e low insieme) sono escluse."
        />
        <Family
          title="Livelli"
          formula="Ultimo pivot high/low confermato · high/low del giorno UTC precedente completo · distanza firmata (C−L)/A"
          snapshot={snapshot}
          render={(r) => [
            ...r.lvl.map(
              (lv): Row => [
                { PIVOT_HIGH: 'Pivot high', PIVOT_LOW: 'Pivot low', DAY_HIGH: 'Giorno prec. high', DAY_LOW: 'Giorno prec. low' }[lv.kind],
                lv.price == null
                  ? `n.d. · ${reasonText(lv.reason)}`
                  : `${price(lv.price)} · dist ${measure(lv.dist, 3, { signed: true })} · noto ${lv.availableAt ? isoMinute(lv.availableAt) : '—'}`,
              ],
            ),
            ['Attraversamenti a questa chiusura', r.crossings.length ? r.crossings.map((c) => `${c.levelKind} ${c.direction} ${price(c.price)}`).join(', ') : 'nessuno'],
          ]}
          note="Attraversamento solo rispetto a un livello già noto alla chiusura precedente. Nessuna fascia di prossimità usata come classificazione."
        />
        <Family
          title="Volume"
          formula="Volume relativo = V barra / mediana dei 20 volumi precedenti (barra corrente esclusa, 21 barre)"
          snapshot={snapshot}
          render={(r) => [
            ['Volume base', r.volu.base == null ? '—' : `${formatNumber(r.volu.base, 3)} BTC`],
            ['Volume quote', r.volu.quote == null ? '—' : `${formatNumber(r.volu.quote, 0)} USDT`],
            ['Scambi', r.volu.trades == null ? '—' : formatNumber(r.volu.trades, 0)],
            ['Mediana 20 precedenti', measure(r.volu.median, 3, { suffix: 'BTC' })],
            ['Volume relativo', measure(r.volu.ratio, 3)],
            ['Acquisti taker (dato grezzo)', r.volu.takerBase == null ? '—' : `${formatNumber(r.volu.takerBase, 3)} BTC`],
          ]}
          note="Non corretto per stagionalità intraday. Il dato taker è riportato com’è: non indica un flusso netto di acquisto."
        />
        <Family
          title="Fibonacci"
          formula="Ancore P0→P1 = ultimi due pivot opposti · u=(C−P0)/(P1−P0), r=1−u · ritracciamenti 38,2/50/61,8/78,6% · proiezioni 127,2/161,8%"
          snapshot={snapshot}
          render={(r) => {
            const f = r.fib;
            if (f.anchors.v === null) return [['Ancore', `n.d. · ${reasonText(f.anchors.r)}`], ['Versione sequenza', String(f.version)]];
            const a = f.anchors.v;
            return [
              ['Versione sequenza (progressiva dall’inizio dell’input)', String(f.version)],
              ['P0', pivot(a.P0)],
              ['P1', pivot(a.P1)],
              ['u · r', `${plain(f.u)} · ${plain(f.r)}`],
              ...(f.retracements ?? []).map((l): Row => [`Ritracciamento ${pct(l.ratio)}`, `${price(l.price)} · dist ${measure(l.dist, 3, { signed: true })}`]),
              ...(f.projections ?? []).map((l): Row => [`Proiezione ${pct(l.ratio)}`, `${price(l.price)} · dist ${ratio(l.dist.v)}`]),
            ];
          }}
          note="Il 50% è una convenzione, non un rapporto di Fibonacci. I livelli sono descrizioni, non target. Le sostituzioni creano nuove versioni senza riscrivere il passato."
        />
      </div>
    </section>
  );
}
