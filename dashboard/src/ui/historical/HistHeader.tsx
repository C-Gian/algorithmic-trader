import type { CausalSnapshot, Ms } from '../../contract/historical';
import { formatNumber } from '../../lib/numbers';
import type { HistoricalStudy } from '../../historical/study';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { StudyFilePicker } from './OpenStudy';

const DAY_MS = 86_400_000;
const pad = (n: number) => String(n).padStart(2, '0');
const dayKey = (t: Ms) => new Date(t).toISOString().slice(0, 10);
const hhmm = (t: Ms) => `${pad(new Date(t).getUTCHours())}:${pad(new Date(t).getUTCMinutes())}`;

/** Intestazione dello studio: fonte, qualità, run e selettore del cutoff t (UTC). */
export function HistHeader({
  study,
  cutoff,
  onCutoff,
  snapshot,
  onOpen,
}: {
  study: HistoricalStudy;
  cutoff: Ms;
  onCutoff: (t: Ms) => void;
  snapshot: CausalSnapshot;
  onOpen: (s: HistoricalStudy) => void;
}) {
  const b = study.bundle;
  const origins = study.origins;
  const idx = study.indexOf(cutoff);
  const day = dayKey(cutoff);
  const dayStart = cutoff - (cutoff % DAY_MS);
  const closes = origins.filter((t) => t >= dayStart && t < dayStart + DAY_MS);
  const totals = b.inputQuality.totals;
  const quality = `${formatNumber(totals.input.valid, 0)}/${formatNumber(totals.input.expected, 0)} minuti validi`;
  const m45 = snapshot.m45;
  const c = study.obs002Case;

  const setDay = (value: string) => {
    if (!value) return;
    const start = Date.parse(`${value}T00:00:00Z`);
    const offset = cutoff - dayStart;
    const target = origins.find((t) => t === start + offset) ?? origins.find((t) => t >= start);
    if (target !== undefined) onCutoff(target);
  };

  return (
    <header className="header">
      <div className="header-row">
        <p className="hist-source">
          Binance Vision · BTCUSDT perpetual USDⓈ-M · prezzo negoziato · UTC
          {study.synthetic && (
            <Badge tone="warning" title="Bundle di test con prezzi inventati">
              FIXTURE SINTETICA
            </Badge>
          )}
        </p>
        <div className="sys-time">
          <span className="mono">
            Input {fmtUtc(b.periods.inputStart)} → {fmtUtc(b.periods.end)} · studio da {fmtUtc(b.periods.studyStart)}
          </span>
          <span>Qualità input: {quality}</span>
        </div>
      </div>

      <div className="header-row">
        <div className="quote">
          <span className="btc-mark" aria-hidden>
            ₿
          </span>
          <div className="pair">
            <p className="pair-name">Cutoff t · {fmtUtc(cutoff)}</p>
            <p className="pair-sub">
              Origine {idx + 1} di {origins.length} · tutto ciò che vedi usa solo dati terminati entro t
            </p>
          </div>
          <p className="price-big" title="Chiusura della barra 45m che termina in t">
            {m45.C !== null ? formatNumber(m45.C, 2) : '—'}
          </p>
          <Badge tone="neutral">C_t · chiusura 45m</Badge>
        </div>
        <StudyFilePicker onOpen={onOpen} label="Apri altro studio" />
      </div>

      <div className="header-row cutoff-row" role="group" aria-label="Scelta del cutoff">
        <div className="controls">
          <Button disabled={idx <= 0} reason="Prima origine dello studio" onClick={() => onCutoff(origins[idx - 1])}>
            ← Chiusura precedente
          </Button>
          <Button disabled={idx >= origins.length - 1} reason="Ultima origine dello studio" onClick={() => onCutoff(origins[idx + 1])}>
            Chiusura successiva →
          </Button>
          <label className="cutoff-field">
            Giorno (UTC)
            <input type="date" value={day} min={dayKey(origins[0])} max={dayKey(origins[origins.length - 1])} onChange={(e) => setDay(e.target.value)} />
          </label>
          <label className="cutoff-field">
            Chiusura 45m (UTC)
            <select value={cutoff} onChange={(e) => onCutoff(Number(e.target.value))}>
              {closes.map((t) => (
                <option key={t} value={t}>
                  {hhmm(t)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <input
          className="cutoff-slider"
          type="range"
          min={0}
          max={origins.length - 1}
          value={idx}
          aria-label="Origine dello studio"
          onChange={(e) => onCutoff(origins[Number(e.target.value)])}
        />
      </div>
      {c && (
        <Notice tone="accent" title={`Pacchetto OBS-002 · caso ${c.attemptId}`}>
          Tentativo di ripresa {c.side} {c.ordinal > 1 ? `n. ${c.ordinal} dello stesso movimento (riepilogo secondario)` : '(primo del movimento)'} alla chiusura {fmtUtc(c.t)} · profilo {c.profile} ·
          categorie {c.categories.join(', ')}. {c.t !== cutoff && 'Stai guardando un altro momento del pacchetto. '}
          {c.note} Le origini selezionabili sono le chiusure attorno al caso.
          {c.t !== cutoff && (
            <>
              {' '}
              <Button onClick={() => onCutoff(c.t)}>Vai al caso</Button>
            </>
          )}
        </Notice>
      )}
      <p className="mode-desc">
        {b.study ? `${b.study.label} · ` : ''}Run <span className="mono">{b.run.runId}</span> · convenzioni {b.conventions.id} <span className="mono">{b.conventions.hash.slice(0, 12)}</span> · {b.source.attribution} ·
        nessun collegamento exchange, nessun dato live
      </p>
      {m45.status !== 'COMPLETE' && (
        <Notice tone="warning" title="Lacuna all'origine">
          La barra 45m che termina in t è incompleta ({m45.inputRef.missing} minuti mancanti, {m45.inputRef.invalid} invalidi): misure non disponibili, nessun valore stimato.
        </Notice>
      )}
    </header>
  );
}
