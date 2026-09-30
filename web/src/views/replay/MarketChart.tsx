import { useEffect, useRef, useState } from "react";
import { TradedBar } from "../../api";
import { fmtNum, fmtTime } from "../../lib/format";
import { EmptyState } from "../../ui/primitives";

// Traded price from causally delivered, completed 1m bars only. The API returns committed deliveries,
// so a bar can only appear after its availability time. No indicators, no overlays, no mark/index.

const H = 360;
const PAD = { top: 18, right: 88, bottom: 34, left: 14 };
const MIN = 60_000;

function ticks(min: number, max: number, n = 5): number[] {
  if (max === min) return [min];
  const raw = (max - min) / n;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(v);
  return out;
}

export function MarketChart({ bars, informationTime }: { bars: TradedBar[]; informationTime: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(900);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(320, Math.floor(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const valid = bars.filter((b) => b.kind === "bar_observation" && b.close !== undefined);
  if (bars.length === 0) {
    return (
      <div ref={ref} className="chart-frame">
        <EmptyState icon="market" title="No traded bar delivered yet">
          Completed traded bars appear here only once the replay reaches their availability time.
        </EmptyState>
      </div>
    );
  }

  const times = bars.map((b) => Date.parse(b.event_time));
  const info = informationTime ? Date.parse(informationTime) : null;
  const t0 = Math.min(...times);
  const t1 = Math.max(Math.max(...times) + MIN, info ?? 0);
  const lows = valid.map((b) => Number(b.low));
  const highs = valid.map((b) => Number(b.high));
  let lo = lows.length ? Math.min(...lows) : 0;
  let hi = highs.length ? Math.max(...highs) : 1;
  const pad = (hi - lo || Math.abs(hi) * 0.001 || 1) * 0.08;
  lo -= pad;
  hi += pad;
  const iw = W - PAD.left - PAD.right;
  const ih = H - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - t0) / (t1 - t0 || 1)) * iw;
  const y = (v: number) => PAD.top + ih - ((v - lo) / (hi - lo || 1)) * ih;
  const slot = Math.max(2, (MIN / (t1 - t0 || MIN)) * iw);
  const body = Math.max(1.5, slot * 0.62);
  const last = valid[valid.length - 1];
  const nX = Math.max(3, Math.floor(iw / 120));
  const xTicks = Array.from({ length: nX + 1 }, (_, i) => t0 + ((t1 - t0) * i) / nX);

  return (
    <div ref={ref} className="chart-frame">
      <svg className="chart market-chart" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label="Traded price, completed 1-minute bars as causally delivered (real market evidence)">
        <defs>
          <pattern id="mkt-gap" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" className="gap-hatch-line" />
          </pattern>
        </defs>
        {ticks(lo, hi).map((v) => (
          <g key={`y${v}`}>
            <line x1={PAD.left} x2={PAD.left + iw} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.left + iw + 8} y={y(v)} className="axis" dominantBaseline="middle">{fmtNum(v, 1)}</text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={`x${t}`} x={x(t)} y={H - 12} className="axis" textAnchor="middle">
            {new Date(t).toISOString().slice(11, 16)}
          </text>
        ))}
        {bars.filter((b) => b.kind !== "bar_observation").map((b) => {
          const t = Date.parse(b.event_time);
          return (
            <rect key={`q${b.seq}`} x={x(t)} y={PAD.top} width={slot} height={ih} className="gap">
              <title>{`${fmtTime(b.event_time)}: ${b.quality_reason} — known ${fmtTime(b.available_time)}; no value admitted`}</title>
            </rect>
          );
        })}
        {valid.map((b) => {
          const t = Date.parse(b.event_time);
          const o = Number(b.open), c = Number(b.close);
          const up = c >= o;
          const cx = x(t) + slot / 2;
          return (
            <g key={`b${b.seq}`} className={up ? "candle up" : "candle down"}>
              <line x1={cx} x2={cx} y1={y(Number(b.high))} y2={y(Number(b.low))} className="wick" />
              <rect x={cx - body / 2} y={y(Math.max(o, c))} width={body} height={Math.max(1, Math.abs(y(o) - y(c)))}
                    className="body" />
              <title>{`${fmtTime(b.event_time)} O ${b.open} H ${b.high} L ${b.low} C ${b.close} · known ${fmtTime(b.available_time)}`}</title>
            </g>
          );
        })}
        {info !== null && (
          <g>
            <line x1={x(info)} x2={x(info)} y1={PAD.top} y2={PAD.top + ih} className="info-line" />
            <text x={Math.min(x(info), PAD.left + iw) - 4} y={PAD.top + 10} className="info-label" textAnchor="end">
              information time
            </text>
          </g>
        )}
        <line x1={PAD.left + iw} x2={PAD.left + iw} y1={PAD.top} y2={PAD.top + ih} className="axis-line" />
        {last && (
          <g transform={`translate(${PAD.left + iw},${y(Number(last.close))})`}>
            <rect x={2} y={-10} width={PAD.right - 6} height={20} rx={4} className="last-tag real" />
            <text x={8} y={0} dominantBaseline="middle" className="last-tag-text real">{fmtNum(last.close, 1)}</text>
          </g>
        )}
      </svg>
      <div className="chart-legend">
        <span><i className="lg-candle" aria-hidden /> Completed traded 1m bar (as delivered)</span>
        <span><i className="lg-gap" /> Missing / rejected slot (never filled)</span>
        <span><i className="lg-info" aria-hidden /> Information time</span>
        <span className="muted">{valid.length} valid · {bars.length - valid.length} quality · no indicators</span>
      </div>
    </div>
  );
}
