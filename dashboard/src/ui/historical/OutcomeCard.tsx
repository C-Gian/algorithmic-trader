import type { StudyRow } from '../../contract/historical';
import { formatNumber } from '../../lib/numbers';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { RELATION_LABEL, STRUCTURE_LABEL, price, ratio, reasonText } from './fmt';

/** Scheda a posteriori: compare solo dopo «Mostra seguito retrospettivo 24h». */
export function OutcomeCard({ row, onClose }: { row: StudyRow | undefined; onClose: () => void }) {
  if (!row) return null;
  const complete = row.final !== null;
  const reasons = [
    row.originStatus !== 'VALID' ? reasonText(row.originStatus) : null,
    row.aStatus !== 'VALID' ? reasonText(row.aStatus) : null,
    ...row.futureFlags.map(reasonText),
  ].filter(Boolean);
  return (
    <section className="card card-position retro-card" aria-label="Seguito retrospettivo 24h">
      <div className="card-head">
        <div>
          <p className="section-title">Seguito retrospettivo 24h</p>
          <p className="card-sub">
            Da {fmtUtc(row.t)} a {fmtUtc(row.horizonEnd)} · gruppo {STRUCTURE_LABEL[row.s45]} 45m · {RELATION_LABEL[row.dailyRelation]}
          </p>
        </div>
        <Badge tone="warning">A POSTERIORI · non noto al momento t</Badge>
      </div>
      <div className="metrics">
        <Metric label="final = (C₍t+24h₎ − p) / a" value={ratio(row.final)} sub={`C 24h ${price(row.close24h)} · firmato nel verso del prezzo`} />
        <Metric label="up = max(0, max H − p) / a" value={ratio(row.up)} sub={`massimo futuro ${price(row.maxHigh)} · ampiezza, non profitto`} />
        <Metric label="down = max(0, p − min L) / a" value={ratio(row.down)} sub={`minimo futuro ${price(row.minLow)} · ampiezza, non perdita`} />
        <Metric label="p = C_t · a = A45m a t" value={price(row.p)} sub={`a = ${row.a == null ? '—' : formatNumber(row.a, 2)} USDT (congelata all’origine)`} />
      </div>
      {!complete && (
        <Notice tone="warning" title="Esiti 24h non disponibili">
          {reasons.join(' · ')}. Minuti disponibili {row.futureMinutesValid}/{row.futureMinutesExpected} (contigui da t: {row.futureMinutesContiguous}). Nessun
          prezzo finale portato avanti, nessuna escursione parziale presentata come completa.
        </Notice>
      )}
      <div className="pos-bottom">
        <p className="footnote">
          Le osservazioni sopra restano quelle del momento t. Origini vicine hanno finestre sovrapposte: non sono prove indipendenti.
        </p>
        <Button onClick={onClose}>Solo informazioni al momento</Button>
      </div>
    </section>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-sub">{sub}</p>
    </div>
  );
}
