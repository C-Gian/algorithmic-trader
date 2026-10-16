import { useState } from 'react';
import type { GroupSummary, Ms, StructureState } from '../../contract/historical';
import type { HistoricalStudy } from '../../historical/study';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { RELATION_LABEL, STRUCTURE_LABEL, ratio } from './fmt';

const PERIOD_LABEL: Record<string, string> = {
  '2025-09': 'Settembre 2025',
  '2025-10': 'Ottobre 2025',
  '2025-11': 'Novembre 2025',
  '2025-12': 'Dicembre 2025',
  TOTAL: 'Totale',
};
const STATES: StructureState[] = ['UP', 'DOWN', 'MIXED', 'UNAVAILABLE'];
const RELATIONS = ['CONCORDANT', 'OPPOSITE', 'MIXED', 'UNAVAILABLE'] as const;
const MEASURES = ['final', 'up', 'down'] as const;
const STAT_KEYS = ['mean', 'min', 'p10', 'p25', 'p50', 'p75', 'p90', 'max'] as const;
const STAT_HEAD = ['Media', 'Min', 'P10', 'P25', 'Mediana', 'P75', 'P90', 'Max'];

function CountsHead() {
  return (
    <tr>
      <th>Gruppo</th>
      <th>Origini</th>
      <th>Origine valida</th>
      <th>A valida</th>
      <th>Futuro completo</th>
      <th>Misure disp.</th>
      <th>Mancanti (motivi)</th>
    </tr>
  );
}

function CountsRow({ label, g }: { label: string; g: GroupSummary }) {
  const flags = Object.entries(g.missingFlags)
    .filter(([, v]) => v)
    .map(([k, v]) => `${k} ${v}`)
    .join(', ');
  return (
    <tr className={g.n === 0 ? 'is-empty' : g.n < 30 ? 'is-sparse' : undefined}>
      <td>{label}</td>
      <td>{g.n}</td>
      <td>{g.originValid}</td>
      <td>{g.aValid}</td>
      <td>{g.futureComplete}</td>
      <td>{g.measuresAvailable}</td>
      <td>
        {g.measuresMissing}
        {flags && ` (${flags})`}
      </td>
    </tr>
  );
}

function StatsTable({ groups }: { groups: [string, GroupSummary][] }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Gruppo</th>
            <th>Misura</th>
            <th>n</th>
            {STAT_HEAD.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.flatMap(([label, g]) =>
            MEASURES.map((m) => {
              const s = g.stats?.[m];
              return (
                <tr key={`${label}-${m}`} className={!s || s.n === 0 ? 'is-empty' : s.n < 30 ? 'is-sparse' : undefined}>
                  <td>{m === 'final' ? label : ''}</td>
                  <td>{m}</td>
                  <td>{s?.n ?? 0}</td>
                  {STAT_KEYS.map((k) => (
                    <td key={k}>{ratio(s?.[k] ?? null, 2)}</td>
                  ))}
                </tr>
              );
            }),
          )}
        </tbody>
      </table>
    </div>
  );
}

/** Riepilogo descrittivo mensile/totale: viste a posteriori, separate dalla vista causale. */
export function StudySummaryView({ study, onOpenOrigin }: { study: HistoricalStudy; onOpenOrigin: (t: Ms) => void }) {
  const summary = study.bundle.retrospective.summary;
  const [period, setPeriod] = useState<string>('TOTAL');
  const tables = summary.tables[period];
  const months = summary.periods;
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="section" aria-label="Studio osservativo">
        <div className="section-head">
          <div>
            <p className="section-title">Studio osservativo OBS-001 · confronto descrittivo</p>
            <p className="section-desc">
              Tutte le chiusure 45m dal {fmtUtc(study.bundle.periods.studyStart)} al {fmtUtc(study.bundle.periods.end)}: seguito nelle 24 ore successive, in unità di
              A45m all’origine, per struttura 45m e relazione con la struttura 1D.
            </p>
          </div>
          <Badge tone="warning">A POSTERIORI</Badge>
        </div>
        <Notice tone="warning" title="Come leggere queste tabelle">
          Origini adiacenti hanno finestre 24h fortemente sovrapposte: le righe non sono prove indipendenti. Nessuna soglia di successo, significatività o
          classifica dei gruppi. Differenze fra gruppi possono riflettere altri fattori: non indicano causalità né un contributo della scala 1D. I quattro
          mesi sono già esposti a sviluppi precedenti, non un campione nuovo. final è firmato nel verso del prezzo; up e down sono ampiezze, non profitti o
          perdite. Righe attenuate: gruppo vuoto o con meno di 30 origini. Lettura estesa nel report locale{' '}
          <span className="mono">docs/research/OBS-001-results.md</span>.
        </Notice>
        <div className="tools" role="tablist" aria-label="Periodo">
          {months.map((p) => (
            <Button key={p} variant={p === period ? 'primary' : 'secondary'} pressed={p === period} onClick={() => setPeriod(p)}>
              {PERIOD_LABEL[p] ?? p}
            </Button>
          ))}
        </div>
      </section>

      <section className="card table-card" aria-label="Copertura">
        <p className="table-title">Copertura e disponibilità · tutti i periodi</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Periodo</th>
                <th>Origini</th>
                <th>Origine valida</th>
                <th>A45m valida</th>
                <th>Futuro completo</th>
                <th>Censurate a destra</th>
                <th>Con lacuna</th>
                <th>Misure disponibili</th>
              </tr>
            </thead>
            <tbody>
              {months.map((p) => {
                const c = summary.tables[p].coverage;
                return (
                  <tr key={p}>
                    <td>{PERIOD_LABEL[p] ?? p}</td>
                    <td>{c.n}</td>
                    <td>{c.originValid}</td>
                    <td>{c.aValid}</td>
                    <td>{c.futureComplete}</td>
                    <td>{c.missingFlags.RIGHT_CENSORED ?? 0}</td>
                    <td>{c.missingFlags.GAP ?? 0}</td>
                    <td>{c.measuresAvailable}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="footnote">
          Disponibilità per misura all’origine ({PERIOD_LABEL[period] ?? period}):{' '}
          {(['45m', '1D'] as const)
            .map((s) => {
              const a = tables.coverage.availabilityAtOrigin[s];
              const miss = Object.entries(a).filter(([, v]) => v.missing > 0);
              return `${s}: ${miss.length === 0 ? 'tutte le misure disponibili' : miss.map(([k, v]) => `${k} mancante ${v.missing}`).join(', ')}`;
            })
            .join(' · ')}
          .
        </p>
      </section>

      <section className="card table-card" aria-label="Sola struttura 45m">
        <p className="table-title">Sola struttura 45m · {PERIOD_LABEL[period] ?? period}</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <CountsHead />
            </thead>
            <tbody>
              {STATES.map((s) => (
                <CountsRow key={s} label={STRUCTURE_LABEL[s]} g={tables.s45[s]} />
              ))}
            </tbody>
          </table>
        </div>
        <StatsTable groups={STATES.map((s) => [STRUCTURE_LABEL[s], tables.s45[s]])} />
      </section>

      {(['UP', 'DOWN'] as const).map((side) => (
        <section key={side} className="card table-card" aria-label={`Struttura 45m ${side} per relazione 1D`}>
          <p className="table-title">
            Struttura 45m {STRUCTURE_LABEL[side].toLowerCase()} · per relazione con la struttura 1D · {PERIOD_LABEL[period] ?? period}
          </p>
          <p className="footnote">Confronto solo entro questo verso, fra i quattro stati della relazione giornaliera.</p>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <CountsHead />
              </thead>
              <tbody>
                {RELATIONS.map((rel) => (
                  <CountsRow key={rel} label={RELATION_LABEL[rel]} g={tables.relation[side][rel]} />
                ))}
              </tbody>
            </table>
          </div>
          <StatsTable groups={RELATIONS.map((rel) => [RELATION_LABEL[rel], tables.relation[side][rel]])} />
        </section>
      ))}

      <section className="card table-card" aria-label="Matrice">
        <p className="table-title">Matrice dei conteggi s45 × s1d · {PERIOD_LABEL[period] ?? period}</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>45m \ 1D</th>
                {STATES.map((s) => (
                  <th key={s}>{STRUCTURE_LABEL[s]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {STATES.map((s) => (
                <tr key={s}>
                  <td>{STRUCTURE_LABEL[s]}</td>
                  {STATES.map((d) => (
                    <td key={d}>{tables.matrix[s][d]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card table-card" aria-label="Esempi">
        <p className="table-title">Esempi (criterio retrospettivo dichiarato, non un nuovo test)</p>
        <p className="footnote">
          Per ciascun verso: la prima origine disponibile del periodo e l’origine con final più opposto al verso (a parità, la più antica). Si aprono nella vista
          causale: il seguito resta nascosto finché non lo chiedi.
        </p>
        <div className="actions">
          {(['UP', 'DOWN'] as const).flatMap((side) => {
            const ex = summary.examples[side];
            return [
              ex.first !== null && (
                <Button key={`${side}-first`} onClick={() => onOpenOrigin(ex.first!)}>
                  {STRUCTURE_LABEL[side]} 45m · prima origine {fmtUtc(ex.first)}
                </Button>
              ),
              ex.contrary !== null && (
                <Button key={`${side}-contrary`} onClick={() => onOpenOrigin(ex.contrary!)}>
                  {STRUCTURE_LABEL[side]} 45m · caso contrario {fmtUtc(ex.contrary)}
                </Button>
              ),
            ];
          })}
        </div>
      </section>
    </main>
  );
}
