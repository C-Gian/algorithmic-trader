import type { BacktestStudy } from '../../backtest/study';
import { formatNumber } from '../../lib/numbers';
import { isoMinute } from '../format';
import { ABSTAIN_TEXT, EXIT_TEXT, bps, usdt } from './text';

/** Registro completo delle operazioni modellate e delle richieste non eseguite: ogni riga apre l'episodio. */
export function LedgerView({ study, onOpen }: { study: BacktestStudy; onOpen: (id: string) => void }) {
  const b = study.bundle;
  const rejected = b.requests.filter((r) => r.outcome !== 'FILLED');
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Registro operazioni">
        <p className="table-title">Registro delle operazioni modellate ({b.trades.length})</p>
        <p className="footnote">Ordine cronologico. Ogni operazione vale {formatNumber(b.notionalUSDT, 0)} USDT di nozionale; clic su una riga per aprire l’episodio.</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ingresso (UTC)</th>
                <th>Verso</th>
                <th>Uscita</th>
                <th>Durata (min)</th>
                <th>Netto</th>
                <th>Punti base</th>
                <th>Protezioni</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {b.trades.map((t) => (
                <tr key={t.id}>
                  <td>{isoMinute(t.entryTime).replace('T', ' ')}</td>
                  <td>{t.side}</td>
                  <td>{t.exit ? EXIT_TEXT[t.exit.reason] : 'percorso irrisolto'}</td>
                  <td>{t.exit ? formatNumber(t.durationMin, 0) : '—'}</td>
                  <td className={t.net != null && t.net < 0 ? 't-neg' : 't-pos'}>{usdt(t.net)}</td>
                  <td>{bps(t.netBps)}</td>
                  <td>{t.stops?.length ?? 0}</td>
                  <td>
                    <button type="button" className="link" onClick={() => onOpen(t.episodeId)}>
                      Apri episodio
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card table-card" aria-label="Richieste non eseguite">
        <p className="table-title">Richieste d’ingresso non eseguite ({rejected.length})</p>
        {rejected.length === 0 ? (
          <p className="empty">Nessuna.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Minuto (UTC)</th>
                  <th>Verso</th>
                  <th>Motivo</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rejected.map((r) => (
                  <tr key={r.episodeId}>
                    <td>{isoMinute(r.executeAt).replace('T', ' ')}</td>
                    <td>{r.side}</td>
                    <td>{ABSTAIN_TEXT[r.outcome] ?? r.outcome}</td>
                    <td>
                      <button type="button" className="link" onClick={() => onOpen(r.episodeId)}>
                        Apri episodio
                      </button>
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
