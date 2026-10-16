import { useState } from 'react';
import type { Timeframe } from '../../contract/types';
import { formatNumber } from '../../lib/numbers';
import { fmtTime } from '../format';
import { useDashboard } from '../useDashboard';
import { CandleChart, type ChartOverlays } from './CandleChart';
import { Badge, Button } from './primitives';

const ZOOM: Record<Timeframe, number[]> = { '45m': [16, 24, 32], '1D': [20, 30, 40] };
const HOURS_45M: Record<number, string> = { 16: 'Ultime 12 ore', 24: 'Ultime 18 ore', 32: 'Ultime 24 ore' };

export function ChartCard() {
  const { snapshot } = useDashboard();
  const { chart, context } = snapshot;
  const [timeframe, setTimeframe] = useState<Timeframe>('45m');
  const [zoom, setZoom] = useState<Record<Timeframe, number>>({ '45m': 2, '1D': 2 });
  const [overlays, setOverlays] = useState<ChartOverlays>({ averages: true, levels: true, fibonacci: false, volume: true });

  const data = chart.timeframes[timeframe];
  const count = ZOOM[timeframe][zoom[timeframe]];
  const candles = data.candles.slice(-count);
  const last = candles[candles.length - 1];
  const feedOk = context.feed.status === 'OK';
  const lastPrice = context.market.price.value?.amount ?? context.market.lastKnownPrice.value.amount;

  const subtitle =
    timeframe === '45m'
      ? `BTC / USDT · Candele 45 minuti · ${HOURS_45M[count]}`
      : `BTC / USDT · Candele giornaliere · Ultimi ${count} giorni · ultima in formazione`;

  const setZoomIdx = (delta: number) =>
    setZoom((z) => ({ ...z, [timeframe]: Math.min(ZOOM[timeframe].length - 1, Math.max(0, z[timeframe] + delta)) }));

  const toggle = (key: keyof ChartOverlays) => setOverlays((o) => ({ ...o, [key]: !o[key] }));
  const chip = (key: keyof ChartOverlays, label: string) => (
    <button type="button" className={`badge ${overlays[key] ? 'tone-accent' : 'tone-neutral'}`} role="switch" aria-checked={overlays[key]} onClick={() => toggle(key)}>
      {overlays[key] ? '☑' : '☐'} {label}
    </button>
  );

  return (
    <section className="card card-chart" aria-label="Grafico di mercato">
      <div className="card-head">
        <div>
          <p className="card-title">Il mercato, nel suo contesto</p>
          <p className="card-sub">{subtitle}</p>
        </div>
        {feedOk ? (
          <Badge tone="accent" icon="radio">
            FEED SIMULATO
          </Badge>
        ) : (
          <Badge tone="warning">ULTIMO DATO · {fmtTime(context.feed.observedAt)}</Badge>
        )}
      </div>

      <div className="toolbar">
        <div className="tools">
          <Button variant={timeframe === '45m' ? 'primary' : 'secondary'} pressed={timeframe === '45m'} onClick={() => setTimeframe('45m')}>
            45m
          </Button>
          <Button variant={timeframe === '1D' ? 'primary' : 'secondary'} pressed={timeframe === '1D'} onClick={() => setTimeframe('1D')}>
            1D
          </Button>
          <Button disabled={zoom[timeframe] === ZOOM[timeframe].length - 1} reason="Massima estensione" onClick={() => setZoomIdx(1)}>
            − Zoom
          </Button>
          <Button disabled={zoom[timeframe] === 0} reason="Massimo ingrandimento" onClick={() => setZoomIdx(-1)}>
            + Zoom
          </Button>
        </div>
        {last && (
          <p className="mono t-2" style={{ fontSize: 12 }}>
            Vol. {timeframe} · {formatNumber(last.volume, 1)} BTC{last.partial ? ' · in formazione' : ''}
          </p>
        )}
      </div>

      <CandleChart
        timeframe={timeframe}
        candles={candles}
        series={data.series}
        levels={chart.levels}
        overlays={overlays}
        lastPrice={lastPrice}
        lastPriceCurrent={feedOk}
      />

      <div className="overlays">
        <span>Overlay</span>
        {chip('averages', 'Medie 20 / 50')}
        {chip('levels', 'Supporti / resistenze')}
        {chip('fibonacci', 'Fibonacci')}
        {chip('volume', 'Volumi')}
      </div>

      <p className="reading">
        {chart.reading}
        {timeframe === '1D' && ` ${data.coverageNote}`}
      </p>
    </section>
  );
}
