import type { TemporalView } from "../../api";
import { fmtInt, fmtTime } from "../../lib/format";
import { Icon } from "../../ui/Icon";
import { Badge, Metric, Tone } from "../../ui/primitives";

// Minimal inspection of the causal temporal substrate committed with the run's latest checkpoint (WP-008-R2).
// Factual infrastructure only: horizons, sealed intervals, clock and readiness of engineering demonstration
// dependencies. It is not adviser output and never interprets the market.

const STATUS_TONE: Record<string, Tone> = {
  COMPLETE: "pos", INCOMPLETE: "warn", OUTSIDE_COVERAGE: "neutral", FORMING: "info",
  READY: "pos", WARMING_UP: "info", GAP: "warn", STALE: "warn", UNAVAILABLE: "neutral",
};

const FAMILY: Record<string, string> = { trade_bar_1m: "Trade", mark_bar_1m: "Mark", index_bar_1m: "Index" };

export function TemporalPanel({ t }: { t: TemporalView }) {
  const c = t.committed;
  const tracks = c?.tracks ?? [];
  return (
    <details className="more inset" data-testid="run-temporal">
      <summary><Icon name="chevron" size={14} className="summary-chevron" /> Temporal substrate
        <span className="summary-hint">temporal substrate only; no adviser</span>
      </summary>
      <div className="more-body">
        <p className="muted small-text" data-testid="temporal-note">
          Factual UTC horizons built from the admitted 1m evidence ({t.profile_id}). Roles are design labels, not
          votes; readiness below concerns engineering demonstration dependencies only, not trading decisions.
        </p>
        <div className="metric-grid">
          <Metric label="Clock policy" value={<span className="small-text">{t.clock_policy}</span>} mono={false}
                  hint={`seal ${t.seal_policy} · closure allowance ${t.closure_allowance}`} />
          <Metric label="Clock time (committed)" value={c?.clock_time ? fmtTime(c.clock_time) : "no barrier yet"}
                  testid="temporal-clock" hint={`finite clock end ${fmtTime(t.clock_end)}`} />
          <Metric label="Admitted cursor" value={c ? fmtInt(c.admitted_cursor) : "—"} testid="temporal-cursor"
                  hint={c?.pending_tie_time ? `tie group at ${fmtTime(c.pending_tie_time)} not yet closed by a barrier`
                    : "no pending tie boundary"} />
          <Metric label="Dispatches" value={c ? fmtInt(c.dispatch_seq) : "—"}
                  hint={c?.next_deadline ? `next deadline ${fmtTime(c.next_deadline)}` : "no pending deadline"} />
          <Metric label="Sealed / late-excluded" value={c ? `${fmtInt(c.counters.sealed)} / ${fmtInt(c.counters.late_excluded)}` : "—"}
                  testid="temporal-late" hint="late evidence never revises a sealed interval (seal-no-revision)" />
        </div>
        {tracks.length > 0 && (
          <div className="table-wrap">
            <table className="table table-compact" data-testid="temporal-tracks">
              <thead>
                <tr><th>Series</th><th>Horizon</th><th>Newest sealed interval (UTC)</th><th>Status</th>
                  <th className="num">Valid / expected</th><th>Known at</th>
                  <th className="num" title="open interval still accumulating (not a published closure)">Forming now</th>
                  <th className="num">Late</th></tr>
              </thead>
              <tbody>
                {tracks.map((x) => (
                  <tr key={x.track} data-testid="temporal-track">
                    <td className="nowrap">{FAMILY[x.family] ?? x.family}</td>
                    <td className="nowrap">{x.horizon} <span className="muted small-text">{x.role}</span></td>
                    <td className="mono nowrap">{x.newest_sealed ? fmtTime(x.newest_sealed.interval_start) : "—"}</td>
                    <td>{x.newest_sealed
                      ? <Badge tone={STATUS_TONE[x.newest_sealed.status] ?? "neutral"}>{x.newest_sealed.status}</Badge>
                      : x.forming.length ? <Badge tone="info">FORMING</Badge> : <span className="muted">—</span>}</td>
                    <td className="num mono">{x.newest_sealed ? `${fmtInt(x.newest_sealed.valid)}/${fmtInt(x.newest_sealed.expected)}` : "—"}</td>
                    <td className="mono nowrap">{x.newest_sealed ? fmtTime(x.newest_sealed.known_at) : "—"}</td>
                    <td className="num mono" data-testid="temporal-forming">
                      {x.forming.length ? `${fmtInt(x.forming[0].valid + x.forming[0].missing + x.forming[0].rejected)}/${fmtInt(x.forming[0].expected)}` : "—"}
                    </td>
                    <td className="num mono">{fmtInt(x.late_excluded)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {(c?.readiness ?? []).length > 0 && (
          <ul className="list small-text" data-testid="temporal-readiness">
            {c!.readiness.map((r) => (
              <li key={r.dependency}>
                <Badge tone={STATUS_TONE[r.status] ?? "neutral"}>{r.status}</Badge>{" "}
                <span className="mono">{r.dependency}</span>
                {r.blockers.length > 0 && <span className="muted"> — {r.blockers.join("; ")}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}
