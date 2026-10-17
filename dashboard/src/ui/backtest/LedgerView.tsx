import type { BacktestStudy } from '../../backtest/study';
import { formatNumber } from '../../lib/numbers';
import { isoMinute } from '../format';
import { Link } from '../Link';
import { navigate, paths, type ResultSource } from '../router';
import { periodText } from './ResultsPage';
import { ABSTAIN_TEXT, EXIT_TEXT, SIDE, px, usdt } from './text';

const when = (ms: number) => isoMinute(ms).replace('T', ' ').replace('Z', ' UTC');

/** Registro completo delle operazioni simulate e dei tentativi non eseguiti: ogni riga apre il dettaglio. */
export function LedgerView({ study, source }: { study: BacktestStudy; source: ResultSource }) {
  const b = study.bundle;
  const rejected = b.requests.filter((r) => r.outcome !== 'FILLED');
  const open = (episodeId: string) => navigate(paths.episode(source, episodeId, 'operations'));
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <div className="back-row">
        <Link to={paths.result(source)} className="btn btn-secondary">
          ← Torna ai risultati
        </Link>
        <span className="t-2">
          {study.profile.label} · {periodText(b.window.start, b.window.end)}
        </span>
      </div>
      <section className="card table-card" aria-label="Tutte le operazioni">
        <p className="table-title">Tutte le operazioni ({b.trades.length})</p>
        <p className="footnote">
          Ordine cronologico. Ogni operazione vale {formatNumber(b.notionalUSDT, 0)} USDT (dimensione convenzionale). Clic su una riga per vedere decisione, ingresso,
          chiusura e costi.
        </p>
        <div className="table-scroll">
          <table className="data-table rows-link">
            <thead>
              <tr>
                <th>Ingresso</th>
                <th>Verso</th>
                <th>Prezzo d’ingresso</th>
                <th>Chiusa per</th>
                <th>Prezzo d’uscita</th>
                <th>Durata (min)</th>
                <th>Commissioni e pagamenti</th>
                <th>Risultato dopo i costi</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {b.trades.map((t) => (
                <tr key={t.id} onClick={() => open(t.episodeId)}>
                  <td>{when(t.entryTime)}</td>
                  <td>{t.side === 'LONG' ? 'salita (LONG)' : 'discesa (SHORT)'}</td>
                  <td>{px(t.E)}</td>
                  <td>{t.exit ? EXIT_TEXT[t.exit.reason] : 'percorso irrisolto'}</td>
                  <td>{t.exit ? px(t.exit.X) : '—'}</td>
                  <td>{t.durationMin != null ? formatNumber(t.durationMin, 0) : '—'}</td>
                  <td>{usdt(t.feeExit == null || t.funding.total == null ? null : -(t.feeEntry + t.feeExit) + t.funding.total)}</td>
                  <td className={t.net != null && t.net < 0 ? 't-neg' : 't-pos'}>{usdt(t.net)}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <Link to={paths.episode(source, t.episodeId, 'operations')} ariaLabel={`Apri il dettaglio dell’operazione del ${when(t.entryTime)}`}>
                      Apri dettaglio
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card table-card" aria-label="Tentativi non eseguiti">
        <p className="table-title">Tentativi d’ingresso non eseguiti ({rejected.length})</p>
        <p className="footnote">Nessuna posizione aperta e nessuna commissione: il bot aveva deciso di tentare, ma l’ingresso non è avvenuto.</p>
        {rejected.length === 0 ? (
          <p className="empty">Nessuno.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table rows-link">
              <thead>
                <tr>
                  <th>Minuto previsto</th>
                  <th>Tentativo</th>
                  <th>Perché non è stato eseguito</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rejected.map((r) => (
                  <tr key={r.episodeId} onClick={() => open(r.episodeId)}>
                    <td>{when(r.executeAt)}</td>
                    <td>{SIDE[r.side].attempt}</td>
                    <td>{ABSTAIN_TEXT[r.outcome] ?? r.outcome}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <Link to={paths.episode(source, r.episodeId, 'operations')} ariaLabel={`Apri il dettaglio del tentativo del ${when(r.executeAt)}`}>
                        Apri dettaglio
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
