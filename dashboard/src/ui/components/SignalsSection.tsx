import { useEffect, useRef, useState } from 'react';
import type { MiniSeries, Observation, Tone } from '../../contract/types';
import { fmtHm, fmtTime, tzAbbr } from '../format';
import { useDashboard } from '../useDashboard';
import { Badge, Button, Icon } from './primitives';

const TONE_COLOR: Record<Tone, string> = {
  positive: '#72dab0',
  negative: '#ff9395',
  warning: '#edc078',
  accent: '#8cbbff',
  neutral: '#7f8c9a',
};

/** Mini grafico 380 × 76 (nodo Figma 3:135): solo geometria dei valori preparati. */
function MiniChart({ mini }: { mini: MiniSeries }) {
  const W = 400;
  const H = 76;
  const grid = [20, 40, 60].map((y) => <rect key={y} x={12} y={y} width={W - 24} height={1} fill="#28313a" />);

  if (mini.kind === 'BARS') {
    const values = mini.series[0]?.values ?? [];
    const max = Math.max(...values, 1);
    const hl = mini.highlightLast ?? 0;
    return (
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden>
        {grid}
        {values.map((v, i) => {
          const h = Math.max(3, (v / max) * 52);
          const highlighted = i >= values.length - hl;
          return (
            <rect key={i} x={14 + i * 16} y={66 - h} width={10} height={h} fill={highlighted ? '#8cbbff' : '#7f8c9a'} opacity={highlighted ? 1 : 0.45} />
          );
        })}
      </svg>
    );
  }

  const all = [...mini.series.flatMap((s) => s.values), ...mini.referenceLevels.map((l) => l.value)];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const y = (v: number) => 66 - ((v - min) / span) * 56;
  const x = (i: number, n: number) => 16 + (i * 350) / Math.max(1, n - 1);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden>
      {grid}
      {mini.referenceLevels.map((l, i) => (
        <g key={i}>
          <rect x={12} y={y(l.value)} width={W - 24} height={1} fill={TONE_COLOR[l.tone]} opacity={0.5} />
          {l.label && (
            <text x={322} y={y(l.value) + 12} fill={TONE_COLOR[l.tone]} fontSize={10} fontFamily="IBM Plex Mono">
              {l.label}
            </text>
          )}
        </g>
      ))}
      {mini.series.map((s) => (
        <polyline
          key={s.name}
          points={s.values.map((v, i) => `${x(i, s.values.length).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}
          fill="none"
          stroke={TONE_COLOR[s.tone]}
          strokeWidth={2}
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}

function SignalCard({ o, onDetails }: { o: Observation; onDetails: () => void }) {
  return (
    <article className="card signal">
      <div className="signal-head">
        <p className="signal-title">{o.title}</p>
        <Badge tone={o.badge.tone}>{o.badge.text}</Badge>
      </div>
      <div>
        {o.value.value ? (
          <>
            <p className="signal-value" style={o.family === 'FIBONACCI' ? { fontSize: 22 } : undefined}>
              {o.value.value.display}
            </p>
            <p className="signal-caption">{o.value.value.caption}</p>
          </>
        ) : (
          <p className="signal-value t-2">Non disponibile</p>
        )}
      </div>
      <div className="mini">
        <MiniChart mini={o.mini} />
      </div>
      <div>
        <p className="kv-label">COSA OSSERVA</p>
        <p className="kv-text">{o.observes}</p>
      </div>
      <div>
        <p className="kv-label">COSA SIGNIFICA</p>
        <p className="kv-text t-2">{o.means}</p>
      </div>
      <p className="signal-context">{o.context}</p>
      <div className="signal-foot">
        <span>
          Agg. {fmtTime(o.observedAt)} · {o.timeframe}
          {o.freshness === 'LAST_KNOWN' ? ' · ultimo noto' : ''}
        </span>
        <button type="button" className="details-link" onClick={onDetails}>
          Dettagli <Icon name="arrowUpRight" />
        </button>
      </div>
    </article>
  );
}

function DetailsDialog({ o, onClose }: { o: Observation; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="overlay" onClick={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="details-title" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-identity">
          <p className="dialog-kicker">DETTAGLI DEL SEGNALE · {o.timeframe}</p>
          <Badge tone={o.badge.tone}>{o.badge.text}</Badge>
        </div>
        <div>
          <p className="dialog-title" id="details-title" style={{ marginTop: 0 }}>
            {o.title}
          </p>
          <p className="t-2" style={{ marginTop: 6 }}>
            {o.value.value ? `${o.value.value.display} · ${o.value.value.caption}` : 'Valore non disponibile'}
          </p>
        </div>
        <div className="consequences">
          <div>
            <p className="kv-label">COME FUNZIONA</p>
            <p className="kv-text">{o.explanation}</p>
          </div>
          <div>
            <p className="kv-label">COSA OSSERVA</p>
            <p className="kv-text">{o.observes}</p>
          </div>
          <div>
            <p className="kv-label">COSA SIGNIFICA</p>
            <p className="kv-text t-2">{o.means}</p>
          </div>
          <div>
            <p className="kv-label">VALORI DI CONTESTO</p>
            <p className="kv-text t-2">{o.context}</p>
          </div>
          <div>
            <p className="kv-label">LIMITI</p>
            <p className="kv-text t-2">{o.limits}</p>
          </div>
          <div>
            <p className="kv-label">TEMPO E DISPONIBILITÀ</p>
            <p className="kv-text t-2">
              Osservato alle {fmtHm(o.observedAt)} {tzAbbr(o.observedAt)} sul {o.timeframe} ·{' '}
              {o.availability === 'AVAILABLE' ? 'disponibile' : 'non disponibile'}
              {o.freshness === 'LAST_KNOWN' ? ' · ultimo valore noto, feed non aggiornato' : ''}
            </p>
          </div>
        </div>
        <p className="footnote">Testo d’esempio della simulazione: nessuna probabilità stimata, nessuna nuova conclusione.</p>
        <div className="dialog-actions">
          <span />
          <button ref={closeRef} type="button" className="btn btn-secondary" onClick={onClose}>
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
}

export function SignalsSection() {
  const { snapshot } = useDashboard();
  const [open, setOpen] = useState<string | null>(null);
  const list = snapshot.observations;
  const selected = list.find((o) => o.id === open) ?? null;

  return (
    <section className="section" id="segnali" aria-label="Segnali di mercato">
      <div className="section-head">
        <div>
          <p className="section-title">Perché il bot la pensa così</p>
          <p className="section-desc">Sei letture del mercato, spiegate una per una. Nessuna probabilità stimata o promessa di risultato.</p>
        </div>
        <p className="section-aside">Dati simulati · Timeframe 45m</p>
      </div>
      {list.length === 0 ? (
        <div className="card table-card">
          <p className="empty">Nessuna lettura disponibile in questo momento della simulazione.</p>
          <Button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>Torna al grafico</Button>
        </div>
      ) : (
        <div className="signals-grid">
          {list.map((o) => (
            <SignalCard key={o.id} o={o} onDetails={() => setOpen(o.id)} />
          ))}
        </div>
      )}
      {selected && <DetailsDialog o={selected} onClose={() => setOpen(null)} />}
    </section>
  );
}
