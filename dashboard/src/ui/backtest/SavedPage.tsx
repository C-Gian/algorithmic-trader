/**
 * «Risultati salvati»: risultati riconosciuti dalla cartella runs (anche quelli prodotti prima
 * dell'app) ed esecuzioni avviate dall'app. Consultare non ricalcola. Righe non apribili spiegate.
 * L'apertura di un file esterno è un'opzione secondaria, solo in memoria.
 */
import { useCallback, useEffect, useState } from 'react';
import { ApiError, useApi } from '../../backtest/api';
import type { BacktestStudy } from '../../backtest/study';
import type { Job, SavedResult } from '../../contract/app';
import { Button, Notice } from '../components/primitives';
import { Link } from '../Link';
import { paths } from '../router';
import { BacktestFilePicker } from './BacktestEnvironment';
import { periodText } from './ResultsPage';
import { usdt } from './text';

const when = (iso: string | null) => (iso ? iso.replace('T', ' ').slice(0, 16) + ' UTC' : '—');
const JOB_STATE: Record<Job['state'], string> = {
  STARTING: 'in preparazione',
  RUNNING: 'in corso',
  CANCEL_REQUESTED: 'annullamento richiesto',
  COMPLETED: 'completato',
  INCOMPLETE: 'risultato incompleto',
  CANCELLED: 'annullato',
  INTERRUPTED: 'interrotto',
  FAILED: 'errore',
};

function resultStatus(r: SavedResult): string {
  if (r.status === 'UNSUPPORTED_SCHEMA') return 'formato vecchio, conservato ma non apribile';
  if (r.status === 'NOT_OPENABLE') return `non apribile: ${r.reason}`;
  if (r.complete === false) return r.halted ? 'incompleto: periodo interrotto' : 'incompleto';
  return 'completo';
}

export function SavedPage({ onOpenFile }: { onOpenFile: (s: BacktestStudy) => void }) {
  const api = useApi();
  const [results, setResults] = useState<SavedResult[] | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<ApiError | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, j] = await Promise.all([api.results(), api.jobs()]);
      setResults(r.results);
      setJobs(j.jobs);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError('SERVICE_UNAVAILABLE', String(e)));
    }
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Risultati salvati">
        <p className="section-title">Risultati salvati</p>
        <p className="t-2">Aprire un risultato non ricalcola nulla: mostra quello che il motore ha già salvato. Per un nuovo calcolo usa «Nuovo backtest».</p>
        {error && (
          <Notice tone="warning" title="Servizio locale non raggiungibile">
            {error.message}
          </Notice>
        )}
        {error && <Button onClick={load}>Riprova</Button>}
        {results && results.length === 0 && <p className="empty">Nessun risultato nella cartella dei run.</p>}
        {results && results.length > 0 && (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Profilo</th>
                  <th>Periodo valutato</th>
                  <th>Versione</th>
                  <th>Calcolato il</th>
                  <th>Stato</th>
                  <th>Operazioni</th>
                  <th>Risultato dopo i costi</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.resultId} className={r.status !== 'OK' ? 'is-empty' : undefined}>
                    <td>
                      {r.profile?.label ?? '—'}
                      {r.profile?.inferred ? <span className="t-3"> (profilo dedotto dalla fase)</span> : null}
                    </td>
                    <td>{r.window ? periodText(r.window.start, r.window.end) : '—'}</td>
                    <td>
                      {r.candidate ? `${r.candidate.id} ${r.candidate.version}` : '—'} · motore {r.engineVersion ?? '—'}
                    </td>
                    <td>
                      {when(r.finishedAt)}
                      <span className="t-3"> · {r.via === 'APP-001' ? 'dall’app' : 'comando diretto'}</span>
                    </td>
                    <td>{resultStatus(r)}</td>
                    <td>{r.trades ?? '—'}</td>
                    <td>{r.status !== 'OK' ? '—' : r.net == null && r.complete === false ? 'non calcolabile (incompleto)' : usdt(r.net)}</td>
                    <td>
                      {r.status === 'OK' ? (
                        <Link to={paths.result({ kind: 'saved', id: r.resultId })} ariaLabel={`Apri ${r.profile?.label ?? r.resultId}`}>
                          Apri
                        </Link>
                      ) : (
                        <span className="t-3">non apribile</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card table-card" aria-label="Esecuzioni dall’app">
        <p className="table-title">Esecuzioni avviate dall’app ({jobs.length})</p>
        <p className="footnote">
          Ogni avvio ha una propria esecuzione con data, stato e avanzamento; due calcoli identici possono portare allo stesso risultato salvato.
        </p>
        {jobs.length === 0 ? (
          <p className="empty">Nessuna esecuzione finora.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Avviata</th>
                  <th>Profilo</th>
                  <th>Stato</th>
                  <th>Risultato</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.jobId}>
                    <td>{when(j.startedAt)}</td>
                    <td>{j.profile.label}</td>
                    <td>{JOB_STATE[j.state]}</td>
                    <td>
                      {j.result ? (
                        <Link to={paths.result({ kind: 'saved', id: j.result.resultId })}>Apri risultato</Link>
                      ) : (
                        <span className="t-3">nessuno</span>
                      )}
                    </td>
                    <td>
                      <Link to={paths.job(j.jobId)} ariaLabel={`Apri l’esecuzione ${j.jobId}`}>
                        Dettagli dell’esecuzione
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card unavailable" aria-label="Apri un file esterno">
        <p className="table-title">Apri un file esterno (opzione secondaria)</p>
        <p className="t-2">
          Per consultare un file <span className="mono">cand001-bundle.json</span> copiato altrove. Il file resta solo in memoria: dopo un ricaricamento della pagina va
          riaperto. Gli stessi controlli di validità si applicano anche qui.
        </p>
        <BacktestFilePicker onOpen={onOpenFile} label="Apri file esterno" />
      </section>
    </main>
  );
}
