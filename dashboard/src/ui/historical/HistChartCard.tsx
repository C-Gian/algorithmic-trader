import { useState } from 'react';
import type { CausalSnapshot, HistScale, ObservationRecord } from '../../contract/historical';
import { formatNumber } from '../../lib/numbers';
import type { HistoricalStudy } from '../../historical/study';
import { CandleChart, type ChartCandle, type ChartLevel, type ChartMarker, type ChartOverlays, type ChartSeries } from '../components/CandleChart';
import { Badge, Button } from '../components/primitives';
import { fmtUtc, isoMinute } from '../format';

const ZOOM: Record<HistScale, number[]> = { '45m': [32, 64, 96, 160], '1D': [30, 60, 90, 150] };
const iso = (ms: number) => new Date(ms).toISOString();
const LEVEL_LABEL: Record<string, string> = { PIVOT_HIGH: 'PIVOT H', PIVOT_LOW: 'PIVOT L', DAY_HIGH: 'GIORNO PREC. H', DAY_LOW: 'GIORNO PREC. L' };
const pct = (r: number) => `${formatNumber(r * 100, 1)}%`;

function chartLevels(rec: ObservationRecord | null): ChartLevel[] {
  if (!rec) return [];
  const out: ChartLevel[] = [];
  for (const lv of rec.lvl) {
    if (lv.price == null || !lv.id) continue;
    out.push({ id: lv.id, kind: lv.kind, origin: 'OBSERVED', overlay: 'LEVELS', validTo: null, label: `${LEVEL_LABEL[lv.kind]} · ${formatNumber(lv.price, 0)}`, price: { amount: lv.price } });
  }
  for (const f of [...(rec.fib.retracements ?? []), ...(rec.fib.projections ?? [])]) {
    out.push({ id: `fib-${f.ratio}`, kind: 'FIBONACCI', origin: 'OBSERVED', overlay: 'FIBONACCI', validTo: null, label: `FIB ${pct(f.ratio)} · ${formatNumber(f.price, 0)}`, price: { amount: f.price } });
  }
  return out;
}

export function HistChartCard({
  study,
  snapshot,
  retrospective,
  onRetrospective,
}: {
  study: HistoricalStudy;
  snapshot: CausalSnapshot;
  retrospective: boolean;
  onRetrospective: (on: boolean) => void;
}) {
  const [scale, setScale] = useState<HistScale>('45m');
  const [zoom, setZoom] = useState<Record<HistScale, number>>({ '45m': 1, '1D': 1 });
  const [overlays, setOverlays] = useState<ChartOverlays>({ averages: true, levels: true, fibonacci: false, volume: true });
  const t = snapshot.t;
  const count = ZOOM[scale][zoom[scale]];
  const raw = study.candles(scale, t, count, retrospective);
  const candles: ChartCandle[] = raw.map((c) => ({ openTime: iso(c.openTime), open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume, partial: false, gap: c.gap, retrospective: c.retrospective }));
  const sma = study.sma(scale, raw);
  const series: ChartSeries[] = [
    { id: 'sma20', name: 'SMA20', points: sma.sma20.map((p) => ({ time: iso(p.time), value: p.value })) },
    { id: 'sma50', name: 'SMA50', points: sma.sma50.map((p) => ({ time: iso(p.time), value: p.value })) },
  ];
  const rec = scale === '45m' ? snapshot.m45 : snapshot.d1;
  const lastPrice = rec?.C ?? raw.filter((c) => !c.retrospective && !c.gap).at(-1)?.close ?? 0;
  // Pivot disegnati sulla candela candidata soltanto se già confermati entro t.
  const markers: ChartMarker[] = snapshot.events[scale]
    .filter((e) => e.type === 'PIVOT_CONFIRMED')
    .map((e) => ({
      time: iso(e.candidateOpen as number),
      kind: e.kind as 'HIGH' | 'LOW',
      title: `Pivot ${e.kind} sulla candela ${isoMinute(e.candidateOpen as number)} (fine ${isoMinute(e.eventTime)}), noto solo alla chiusura ${isoMinute(e.availableAt)}: servono le due barre successive.`,
    }));
  const toggle = (key: keyof ChartOverlays) => setOverlays((o) => ({ ...o, [key]: !o[key] }));
  const chip = (key: keyof ChartOverlays, label: string) => (
    <button type="button" className={`badge ${overlays[key] ? 'tone-accent' : 'tone-neutral'}`} role="switch" aria-checked={overlays[key]} onClick={() => toggle(key)}>
      {overlays[key] ? '☑' : '☐'} {label}
    </button>
  );
  const shown = raw.filter((c) => !c.retrospective).length;

  return (
    <section className="card card-chart" aria-label="Grafico storico">
      <div className="card-head">
        <div>
          <p className="card-title">Il mercato al cutoff t</p>
          <p className="card-sub">
            BTCUSDT perpetual · {scale === '45m' ? 'candele 45 minuti' : 'candele giornaliere UTC (giorno in formazione escluso)'} · {shown} barre terminate entro {fmtUtc(t)}
          </p>
        </div>
        {retrospective ? <Badge tone="warning">A POSTERIORI · seguito 24h visibile</Badge> : <Badge tone="accent">SOLO INFORMAZIONI AL MOMENTO</Badge>}
      </div>

      <div className="toolbar">
        <div className="tools">
          <Button variant={scale === '45m' ? 'primary' : 'secondary'} pressed={scale === '45m'} onClick={() => setScale('45m')}>
            45m
          </Button>
          <Button variant={scale === '1D' ? 'primary' : 'secondary'} pressed={scale === '1D'} onClick={() => setScale('1D')}>
            1D
          </Button>
          <Button disabled={zoom[scale] === ZOOM[scale].length - 1} reason="Massima estensione" onClick={() => setZoom((z) => ({ ...z, [scale]: z[scale] + 1 }))}>
            − Zoom
          </Button>
          <Button disabled={zoom[scale] === 0} reason="Massimo ingrandimento" onClick={() => setZoom((z) => ({ ...z, [scale]: z[scale] - 1 }))}>
            + Zoom
          </Button>
        </div>
        {retrospective ? (
          <Button variant="secondary" onClick={() => onRetrospective(false)}>
            Solo informazioni al momento
          </Button>
        ) : (
          <Button variant="secondary" onClick={() => onRetrospective(true)}>
            Mostra seguito retrospettivo 24h
          </Button>
        )}
      </div>

      <CandleChart
        timeframe={scale}
        candles={candles}
        series={series}
        levels={chartLevels(rec)}
        overlays={overlays}
        lastPrice={lastPrice}
        lastPriceCurrent
        utc
        markers={markers}
        dataLabel="storiche"
      />

      <div className="overlays">
        <span>Overlay</span>
        {chip('averages', 'SMA20 / SMA50')}
        {chip('levels', 'Pivot e giorno precedente')}
        {chip('fibonacci', 'Fibonacci')}
        {chip('volume', 'Volumi')}
      </div>

      <p className="reading">
        Orari in UTC. Livelli, medie, Fibonacci e triangoli dei pivot sono quelli noti a t
        {retrospective ? '; le candele attenuate a destra della linea sono il seguito a posteriori e non cambiano le osservazioni.' : '.'} I triangoli
        segnano la candela del pivot, che diventa noto solo due barre dopo: passa il mouse per i due orari.
      </p>
    </section>
  );
}
