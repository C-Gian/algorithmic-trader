import type { CausalSnapshot, ObservationRecord } from '../../contract/historical';
import type { HistoricalStudy } from '../../historical/study';
import { Badge, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { RELATION_LABEL, STRUCTURE_LABEL, reasonText } from './fmt';

const AVAIL_KEYS: [string, (r: ObservationRecord) => { v: unknown; r: string | null } | { price: number | null; reason?: string }][] = [
  ['A (volatilità)', (r) => r.vol.A],
  ['SMA20', (r) => r.avg.sma20],
  ['SMA50', (r) => r.avg.sma50],
  ['Distanza medie', (r) => r.avg.dist],
  ['Pendenza SMA20', (r) => r.avg.slope],
  ['Incrocio medie', (r) => r.avg.cross],
  ['Struttura', (r) => r.piv.structure],
  ['Volume relativo', (r) => r.volu.ratio],
  ['Ancore Fibonacci', (r) => r.fib.anchors],
];

function availability(rec: ObservationRecord | null) {
  if (!rec) return { ok: 0, total: AVAIL_KEYS.length, missing: [['Scala', 'storia insufficiente']] as [string, string][] };
  const missing: [string, string][] = [];
  for (const [label, get] of AVAIL_KEYS) {
    const m = get(rec) as { v: unknown; r: string | null };
    if (m.v === null) missing.push([label, reasonText(m.r)]);
  }
  return { ok: AVAIL_KEYS.length - missing.length, total: AVAIL_KEYS.length, missing };
}

const tone = (s: string) => (s === 'UP' ? 'positive' : s === 'DOWN' ? 'negative' : 'neutral');

/** Sostituisce il riquadro della call: solo osservazioni disponibili a t, nessuna decisione. */
export function ObservationsCard({ study, snapshot }: { study: HistoricalStudy; snapshot: CausalSnapshot }) {
  const group = study.causalGroup(snapshot.t);
  const s45 = snapshot.m45.piv.structure;
  const s1d = snapshot.d1?.piv.structure;
  const a45 = availability(snapshot.m45);
  const a1d = availability(snapshot.d1);
  return (
    <section className="card card-call" aria-label="Osservazioni al cutoff">
      <div className="card-head">
        <p className="call-kicker">OSSERVAZIONI AL {fmtUtc(snapshot.t).toUpperCase()}</p>
        <Badge tone="accent">Studio osservativo</Badge>
      </div>
      <div className="levels-table">
        <div className="lt-row">
          <span className="lt-label">Struttura 45m</span>
          <span className="lt-val">
            <Badge tone={tone(s45.v ?? 'UNAVAILABLE')}>{STRUCTURE_LABEL[s45.v ?? 'UNAVAILABLE']}</Badge>
          </span>
          <span className="lt-val t-3">{s45.v ? 'ultimi 2 high e 2 low' : reasonText(s45.r)}</span>
        </div>
        <div className="lt-row">
          <span className="lt-label">Struttura 1D (giorno chiuso)</span>
          <span className="lt-val">
            <Badge tone={tone(s1d?.v ?? 'UNAVAILABLE')}>{STRUCTURE_LABEL[s1d?.v ?? 'UNAVAILABLE']}</Badge>
          </span>
          <span className="lt-val t-3">{s1d?.v ? 'ultimi 2 high e 2 low' : reasonText(s1d?.r ?? 'INSUFFICIENT_HISTORY')}</span>
        </div>
        <div className="lt-row">
          <span className="lt-label">Relazione 1D rispetto a 45m</span>
          <span className="lt-val">{group ? RELATION_LABEL[group.dailyRelation] : '—'}</span>
          <span />
        </div>
      </div>
      <div className="sep" />
      <div className="horizon">
        <div>
          <p className="h-label">Misure disponibili 45m</p>
          <p className="h-value">
            {a45.ok} / {a45.total}
          </p>
        </div>
        <div>
          <p className="h-label">Misure disponibili 1D</p>
          <p className="h-value">
            {a1d.ok} / {a1d.total}
          </p>
        </div>
      </div>
      {[...a45.missing.map(([k, r]) => `45m · ${k}: ${r}`), ...a1d.missing.map(([k, r]) => `1D · ${k}: ${r}`)].length > 0 && (
        <ul className="expect-list">
          {a45.missing.map(([k, r]) => (
            <li key={`45-${k}`}>45m · {k}: {r}</li>
          ))}
          {a1d.missing.map(([k, r]) => (
            <li key={`1d-${k}`}>1D · {k}: {r}</li>
          ))}
        </ul>
      )}
      <div className="update-box">
        <p>
          Barra 45m chiusa alle {fmtUtc(snapshot.m45.end)}; giorno 1D chiuso alle {snapshot.d1 ? fmtUtc(snapshot.d1.end) : '—'}. Queste sono descrizioni del
          mercato, non una previsione, una call o una decisione dell’algoritmo.
        </p>
      </div>
      <p className="footnote">Il gruppo (struttura 45m × relazione 1D) è quello dello studio descrittivo; il seguito 24h si vede solo col comando esplicito.</p>
    </section>
  );
}

/** Area posizione/conto/ordini: non alimentata nello studio. */
export function NotInStudy() {
  return (
    <section className="card card-position" id="conto" aria-label="Posizione e conto" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
      <p className="section-title">Posizione, conto e ordini</p>
      <Notice tone="neutral" title="Non previsti nello studio osservativo">
        Nessuna call, posizione, saldo, commissione o ordine è calcolato sui prezzi reali. Start, Stop totale, modalità di esecuzione e uscite non
        esistono in questo ambiente: sono solo nella simulazione locale.
      </Notice>
    </section>
  );
}
