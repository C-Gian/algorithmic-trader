import { useEffect, useRef, useState } from "react";
import { PricePoint } from "../../api";
import { fmtNum } from "../../lib/format";
import { EmptyState } from "../../ui/primitives";

// Framed chart of the SYNTHETIC fixture close series. No indicators, no signals — just the demo series,
// missing-data bars and the dummy trader's simulated fills.

const H = 340;
const PAD = { top: 18, right: 84, bottom: 30, left: 14 };

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [w, setW] = useState(900);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(320, Math.floor(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

function ticks(min: number, max: number, n = 5): number[] {
  if (max === min) return [min];
  const raw = (max - min) / n;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(v);
  return out;
}

export function SyntheticChart({ points, totalSteps }: { points: PricePoint[]; totalSteps: number }) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const valid = points.filter((p) => p.close !== null);

  if (valid.length < 2) {
    return (
      <div ref={ref} className="chart-frame">
        <EmptyState icon="pulse" title="Waiting for synthetic bars…">The series draws as the demo run progresses.</EmptyState>
      </div>
    );
  }

  const closes = valid.map((p) => Number(p.close));
  let min = Math.min(...closes);
  let max = Math.max(...closes);
  const padV = (max - min || 1) * 0.08;
  min -= padV;
  max += padV;
  const n = Math.max(totalSteps, points[points.length - 1].step + 1, 2);
  const iw = W - PAD.left - PAD.right;
  const ih = H - PAD.top - PAD.bottom;
  const x = (step: number) => PAD.left + (step / (n - 1)) * iw;
  const y = (v: number) => PAD.top + ih - ((v - min) / (max - min || 1)) * ih;
  const line = valid.map((p, i) => `${i ? "L" : "M"}${x(p.step).toFixed(1)},${y(Number(p.close)).toFixed(1)}`).join(" ");
  const area = `${line} L${x(valid[valid.length - 1].step).toFixed(1)},${PAD.top + ih} L${x(valid[0].step).toFixed(1)},${PAD.top + ih} Z`;
  const yt = ticks(min, max);
  const xt = ticks(0, n - 1, Math.max(3, Math.floor(iw / 110))).filter((v) => Number.isInteger(v));
  const bw = Math.max(3, iw / n);
  const last = valid[valid.length - 1];

  return (
    <div ref={ref} className="chart-frame">
      <svg className="chart" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label="Synthetic BTC-perpetual close series (demo fixture, not market data)">
        <defs>
          <linearGradient id="synth-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" className="area-stop-top" />
            <stop offset="100%" className="area-stop-bottom" />
          </linearGradient>
          <pattern id="gap-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" className="gap-hatch-line" />
          </pattern>
        </defs>
        <text x={PAD.left + iw / 2} y={PAD.top + ih / 2} className="chart-watermark" textAnchor="middle" dominantBaseline="middle">
          SYNTHETIC
        </text>
        {yt.map((v) => (
          <g key={`y${v}`}>
            <line x1={PAD.left} x2={PAD.left + iw} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.left + iw + 8} y={y(v)} className="axis" dominantBaseline="middle">{fmtNum(v, 1)}</text>
          </g>
        ))}
        {xt.map((v) => (
          <text key={`x${v}`} x={x(v)} y={H - 10} className="axis" textAnchor="middle">bar {v}</text>
        ))}
        {points.filter((p) => p.quality !== "OK").map((p) => (
          <rect key={`gap-${p.step}`} x={x(p.step) - bw / 2} y={PAD.top} width={bw} height={ih} className="gap">
            <title>{`bar ${p.step}: ${p.quality} (missing/invalid synthetic data)`}</title>
          </rect>
        ))}
        <path d={area} className="area" />
        <path d={line} className="line" />
        {points.filter((p) => p.fill && p.close !== null).map((p) => {
          const cxv = x(p.step);
          const cyv = y(Number(p.close));
          const buy = p.fill === "BUY";
          const d = buy
            ? `M${cxv},${cyv - 7} l6,10 h-12 z`
            : `M${cxv},${cyv + 7} l6,-10 h-12 z`;
          return (
            <path key={`f-${p.step}`} d={d} className={buy ? "fill-buy" : "fill-sell"}>
              <title>{`simulated ${p.fill} fill at bar ${p.step}`}</title>
            </path>
          );
        })}
        <line x1={PAD.left + iw} x2={PAD.left + iw} y1={PAD.top} y2={PAD.top + ih} className="axis-line" />
        <g transform={`translate(${PAD.left + iw},${y(Number(last.close))})`}>
          <rect x={2} y={-10} width={PAD.right - 6} height={20} rx={4} className="last-tag" />
          <text x={8} y={0} dominantBaseline="middle" className="last-tag-text">{fmtNum(last.close, 1)}</text>
        </g>
      </svg>
      <div className="chart-legend">
        <span><i className="lg-line" /> Synthetic close</span>
        <span><i className="lg-gap" /> Missing / invalid bar</span>
        <span><i className="lg-buy" aria-hidden>▲</i> Simulated buy fill</span>
        <span><i className="lg-sell" aria-hidden>▼</i> Simulated sell fill</span>
        <span className="muted">Range {fmtNum(Math.min(...closes), 1)} – {fmtNum(Math.max(...closes), 1)}</span>
      </div>
    </div>
  );
}
