/**
 * Grafico a candele e volumi in SVG. Solo geometria: candele, serie e livelli arrivano
 * già preparati dal provider. Le misure di riferimento (778 × 412) seguono il nodo Figma 2:9366.
 */
import { useEffect, useRef, useState } from 'react';
import type { Candle, Level, PreparedSeries, Timeframe } from '../../contract/types';
import { formatNumber, formatPrice } from '../../lib/numbers';
import { fmtDay, fmtHm } from '../format';

const H = 412;
const PAD_L = 12;
const AXIS_W = 106;
const Y_TOP = 40;
const Y_BOTTOM = 330;
const VOL_BASE = 378;
const VOL_MAX = 44;
const COLORS = { up: '#72dab0', down: '#ff9395', grid: '#28313a', fast: '#8cbbff', slow: '#edc078', text3: '#7f8c9a', text2: '#a7b2be', label: '#151a20' };

const LEVEL_COLOR: Record<string, string> = {
  TARGET: '#72dab0',
  STOP: '#edc078',
  ENTRY: '#8cbbff',
  RESISTANCE: '#edc078',
  SUPPORT: '#edc078',
  FIBONACCI: '#8cbbff',
};

export interface ChartOverlays {
  readonly averages: boolean;
  readonly levels: boolean;
  readonly fibonacci: boolean;
  readonly volume: boolean;
}

function niceStep(range: number): number {
  const steps = [50, 100, 200, 250, 500, 1000, 2000, 2500, 5000];
  return steps.find((s) => range / s <= 5) ?? 10000;
}

const labelWidth = (text: string) => Math.round(text.length * 6.6 + 14);

/** Evita la sovrapposizione delle etichette spostandole verticalmente. */
function spread(items: { y: number }[], gap = 22) {
  const sorted = [...items].sort((a, b) => a.y - b.y);
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i].y - sorted[i - 1].y < gap) sorted[i].y = sorted[i - 1].y + gap;
  }
}

function smoothPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return '';
  let d = `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }
  return d;
}

export function CandleChart({
  timeframe,
  candles,
  series,
  levels,
  overlays,
  lastPrice,
  lastPriceCurrent,
}: {
  timeframe: Timeframe;
  candles: readonly Candle[];
  series: readonly PreparedSeries[];
  levels: readonly Level[];
  overlays: ChartOverlays;
  lastPrice: number;
  lastPriceCurrent: boolean;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(778);

  useEffect(() => {
    const el = boxRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(320, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const plotRight = width - AXIS_W;
  const n = Math.max(candles.length, 1);
  const step = (plotRight - PAD_L - 8) / n;
  const bodyW = Math.max(3, Math.min(11, step * 0.58));
  const cx = (i: number) => PAD_L + 8 + step * (i + 0.5);

  const visibleLevels = levels.filter(
    (l) => l.validTo === null && l.origin !== 'ORIGINAL_PLAN' && (l.overlay === 'PLAN' || (l.overlay === 'LEVELS' && overlays.levels) || (l.overlay === 'FIBONACCI' && overlays.fibonacci)),
  );
  const visibleSeries = overlays.averages ? series : [];
  const startTime = candles[0]?.openTime;
  const seriesPoints = visibleSeries.map((s) => s.points.filter((p) => !startTime || p.time >= startTime));

  const values = [
    ...candles.flatMap((c) => [c.high, c.low]),
    ...visibleLevels.map((l) => l.price.amount),
    ...seriesPoints.flatMap((pts) => pts.map((p) => p.value)),
    lastPrice,
  ];
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const pad = Math.max((rawMax - rawMin) * 0.06, 20);
  const min = rawMin - pad;
  const max = rawMax + pad;
  const y = (p: number) => Y_BOTTOM - ((p - min) / (max - min)) * (Y_BOTTOM - Y_TOP);

  const tickStep = niceStep(max - min);
  const ticks: number[] = [];
  for (let t = Math.ceil(min / tickStep) * tickStep; t <= max; t += tickStep) ticks.push(t);

  const maxVol = Math.max(...candles.map((c) => c.volume), 1);
  const timeLabelEvery = Math.max(1, Math.round(n / 6));

  const left = visibleLevels
    .filter((l) => l.overlay === 'PLAN')
    .map((l) => ({ level: l, y: y(l.price.amount) - 22 }));
  const right = visibleLevels
    .filter((l) => l.overlay !== 'PLAN')
    .map((l) => ({ level: l, y: y(l.price.amount) - 22 }));
  spread(left);
  spread(right);

  return (
    <div className="chart-box" ref={boxRef}>
      <svg width={width} height={H} role="img" aria-label={`Grafico ${timeframe} con ${candles.length} candele simulate`}>
        {ticks.map((t) => (
          <g key={t}>
            <rect x={PAD_L} y={y(t)} width={plotRight - PAD_L} height={1} fill={COLORS.grid} />
            {Math.abs(y(t) - y(lastPrice)) > 14 && (
              <text x={plotRight + 8} y={y(t) + 4} fill={COLORS.text3} fontSize={10} fontFamily="IBM Plex Mono">
                {formatPrice(t)}
              </text>
            )}
          </g>
        ))}
        {candles.map((c, i) =>
          i % timeLabelEvery === 0 ? (
            <g key={`t-${c.openTime}`}>
              <rect x={cx(i)} y={26} width={1} height={322} fill={COLORS.grid} />
              <text x={cx(i) - 14} y={400} fill={COLORS.text3} fontSize={10} fontFamily="IBM Plex Mono">
                {timeframe === '45m' ? fmtHm(c.openTime) : fmtDay(c.openTime)}
              </text>
            </g>
          ) : null,
        )}
        <text x={plotRight + 12} y={18} fill={COLORS.text2} fontSize={10}>
          USDT
        </text>

        {overlays.volume && (
          <>
            <text x={14} y={352} fill={COLORS.text2} fontSize={10}>
              Vol. BTC
            </text>
            {candles.map((c, i) => {
              const h = Math.max(2, (c.volume / maxVol) * VOL_MAX);
              return (
                <rect
                  key={`v-${c.openTime}`}
                  x={cx(i) - bodyW / 2}
                  y={VOL_BASE - h}
                  width={bodyW}
                  height={h}
                  fill={c.close >= c.open ? COLORS.up : COLORS.down}
                  opacity={0.35}
                />
              );
            })}
          </>
        )}

        {candles.map((c, i) => {
          const color = c.close >= c.open ? COLORS.up : COLORS.down;
          const top = y(Math.max(c.open, c.close));
          const bodyH = Math.max(1, Math.abs(y(c.open) - y(c.close)));
          return (
            <g key={c.openTime} opacity={c.partial ? 0.55 : 1}>
              <title>
                {`${timeframe === '45m' ? fmtHm(c.openTime) : fmtDay(c.openTime)}${c.partial ? ' (in formazione)' : ''} · A ${formatPrice(c.open)} · Max ${formatPrice(c.high)} · Min ${formatPrice(c.low)} · C ${formatPrice(c.close)} · Vol ${formatNumber(c.volume, 1)} BTC`}
              </title>
              <rect x={cx(i) - 0.5} y={y(c.high)} width={1} height={Math.max(1, y(c.low) - y(c.high))} fill={color} />
              <rect x={cx(i) - bodyW / 2} y={top} width={bodyW} height={bodyH} rx={1} fill={color} />
            </g>
          );
        })}

        {seriesPoints.map((pts, si) => {
          const idx = new Map(candles.map((c, i) => [c.openTime, i]));
          const path = smoothPath(pts.filter((p) => idx.has(p.time)).map((p) => ({ x: cx(idx.get(p.time)!), y: y(p.value) })));
          return <path key={visibleSeries[si].id} d={path} fill="none" stroke={si === 0 ? COLORS.fast : COLORS.slow} strokeWidth={2} />;
        })}

        {visibleLevels.map((l) => {
          const color = LEVEL_COLOR[l.kind.startsWith('ENTRY') ? 'ENTRY' : l.kind] ?? COLORS.text2;
          const yy = Math.round(y(l.price.amount)) + 0.5;
          const dashed = l.overlay === 'PLAN' || l.overlay === 'FIBONACCI';
          return (
            <line
              key={l.id}
              x1={PAD_L}
              x2={plotRight - 3}
              y1={yy}
              y2={yy}
              stroke={color}
              strokeWidth={1}
              strokeDasharray={dashed ? '4 4' : undefined}
              opacity={l.overlay === 'PLAN' ? (l.freshness === 'CURRENT' ? 1 : 0.6) : 0.5}
            />
          );
        })}

        {[...left.map((a) => ({ ...a, side: 'left' as const })), ...right.map((a) => ({ ...a, side: 'right' as const }))].map(({ level, y: ly, side }) => {
          const text = level.freshness === 'LAST_KNOWN' && level.overlay === 'PLAN' ? `${level.label} · ULTIMO NOTO` : level.label;
          const w = labelWidth(text);
          const x = side === 'left' ? 14 : plotRight - 6 - w;
          const color = LEVEL_COLOR[level.kind.startsWith('ENTRY') ? 'ENTRY' : level.kind] ?? COLORS.text2;
          return (
            <g key={`lbl-${level.id}`}>
              <rect x={x} y={ly} width={w} height={20} rx={4} fill={COLORS.label} />
              <text x={x + 7} y={ly + 14} fill={color} fontSize={11} fontFamily="IBM Plex Mono">
                {text}
              </text>
            </g>
          );
        })}

        <g>
          <rect x={plotRight + 1} y={y(lastPrice) - 10} width={54} height={20} rx={4} fill={COLORS.label} />
          <text x={plotRight + 8} y={y(lastPrice) + 4} fill={lastPriceCurrent ? COLORS.up : COLORS.slow} fontSize={11} fontFamily="IBM Plex Mono">
            {formatPrice(lastPrice)}
          </text>
        </g>
      </svg>
    </div>
  );
}
