import type { BtPeriod } from '../../contract/backtest';
import type { BacktestStudy } from '../../backtest/study';
import { formatNumber } from '../../lib/numbers';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { BacktestFilePicker } from './BacktestEnvironment';
import { CATEGORY_TEXT, EXIT_TEXT, bps, num, pct, usdt } from './text';

const PERIOD_LABEL = (p: string) => (p === 'DEV' ? '2023–2024' : p === 'ADDITIONAL_2025' ? '2025' : p);
/** ADDITIONAL_2025: confronto aggiuntivo su dati già esposti, separato dallo sviluppo 2023–2024. */
const isAdditional = (phase: string) => phase === 'ADDITIONAL_2025';

/** Stato di copertura di un periodo: con valutazione interrotta i conteggi descrivono solo la parte valutata. */
const coverageText = (t: BtPeriod) =>
  !t.coverage.evaluated ? 'non valutato' : t.coverage.complete ? 'completa' : `parziale fino al ${fmtUtc(t.coverage.evaluatedUntil)}`;
/** Statistiche per operazione calcolate dal motore sulle sole concluse: con irrisolte sono parte nota, non complete. */
const closedOnly = (t: BtPeriod, text: string) => (t.trades.unresolved ? `${text} · solo concluse` : text);

function Row({ label, periods, value }: { label: string; periods: [string, BtPeriod][]; value: (t: BtPeriod) => string }) {
  return (
    <tr>
      <td>{label}</td>
      {periods.map(([p, t]) => (
        <td key={p}>{value(t)}</td>
      ))}
    </tr>
  );
}

export function ResultsPage({ study, onOpen, onOpenFile }: { study: BacktestStudy; onOpen: (id: string, cursor?: number) => void; onOpenFile: (s: BacktestStudy) => void }) {
  const b = study.bundle;
  const s = b.summary;
  // Un anno che coincide con l'intera finestra (2025) è mostrato una volta sola, come periodo della fase.
  const periods: [string, BtPeriod][] = s.periods
    .filter((p) => p === s.phase || s.tables[p].start !== s.tables[s.phase].start || s.tables[p].end !== s.tables[s.phase].end)
    .map((p) => [p, s.tables[p]]);
  const additional = isAdditional(s.phase);
  const dev = s.tables[s.phase];
  const q = b.quality;
  const headlines = study.headlines();
  const halted = s.halted;
  const rec = s.reconciliation;
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label={additional ? 'Confronto aggiuntivo 2025' : 'Backtest di sviluppo'}>
        <div className="card-head">
          <div>
            <p className="section-title">
              {b.candidate.id} · versione {b.candidate.version} · {additional ? 'confronto aggiuntivo 2025' : 'backtest di sviluppo'}{' '}
              {fmtUtc(b.window.start).slice(0, 11)} → {fmtUtc(b.window.end).slice(0, 11)}
            </p>
            <p className="card-sub">
              Binance Vision · BTCUSDT perpetual USDⓈ-M · prezzo negoziato 1m · UTC · run <span className="mono">{b.run.runId}</span> · configurazione{' '}
              <span className="mono">{b.candidate.hash.slice(0, 12)}</span>
            </p>
          </div>
          <div className="actions">
            {study.synthetic && <Badge tone="warning">FIXTURE SINTETICA</Badge>}
            {additional && <Badge tone="warning">2025 GIÀ ESPOSTO · NON VALIDAZIONE INDIPENDENTE</Badge>}
            <Badge tone="warning">ESECUZIONI MODELLATE</Badge>
          </div>
        </div>
        <p className="t-2">
          Il programma ha già elaborato tutti gli episodi del periodo, una chiusura da 45 minuti dopo l’altra, partendo senza posizioni. Qui consulti i risultati e
          puoi aprire un episodio: vedrai che cosa sapeva al momento della decisione e, solo se lo chiedi, che cosa è successo dopo.
        </p>
        {additional && (
          <p className="t-2">
            È il confronto aggiuntivo sul 2025 con la stessa versione congelata, separato dallo sviluppo 2023–2024 (che è in un altro file). Il 2025 era già stato
            esaminato in studi precedenti: non è una prova su dati mai visti. Le osservazioni usano tutta la storia dal {fmtUtc(b.window.inputStart).slice(0, 11)};
            decisioni e operazioni ripartono da zero il {fmtUtc(b.window.start).slice(0, 11)}, senza nulla ereditato dal 2024.
          </p>
        )}
        <p className="footnote">
          Ogni operazione vale {formatNumber(b.notionalUSDT, 0)} USDT di nozionale fisso: i totali sono somme di operazioni ipotetiche, non il saldo di un conto né un
          rendimento composto. {b.economicsLabel}. Qualità input: {formatNumber(q.trade.totals.valid, 0)}/{formatNumber(q.trade.totals.expected, 0)} minuti validi dal{' '}
          {fmtUtc(b.window.inputStart).slice(0, 11)} (storia osservata inclusa), funding{' '}
          {q.funding.series.events} eventi ({q.funding.series.anomalies.length} anomalie), mark per il funding {q.mark.pointsAvailable}/{q.mark.pointsNeeded} punti.
        </p>
        <BacktestFilePicker onOpen={onOpenFile} label="Apri altro backtest" />
      </section>

      {halted && (
        <Notice tone="warning" title={`Finestra interrotta il ${fmtUtc(halted.at)}: risultati completi non disponibili`}>
          Manca un minuto negoziato mentre una posizione era aperta ({halted.reason}): il percorso di quell’operazione è irrisolto e la valutazione si ferma lì. Netto,
          stress e drawdown del periodo restano mancanti. Parte nota, dichiaratamente parziale: {rec.closedTrades} operazioni concluse con netto{' '}
          {usdt(rec.knownPartNet)}; {rec.unresolvedTrades} irrisolte; {formatNumber(rec.evaluatedCloses, 0)} chiusure 45m valutate e{' '}
          {formatNumber(rec.notEvaluatedCloses, 0)} solo teoriche, non valutate.
        </Notice>
      )}

      <section className="section" aria-label="Esempi">
        <div className="section-head">
          <div>
            <p className="section-title">Apri un episodio con un clic</p>
            <p className="section-desc">Esempi scelti con una regola cronologica fissata prima dei risultati: il primo caso di ciascun tipo, senza preferire i grafici migliori.</p>
          </div>
        </div>
        <div className="actions">
          {headlines.map((h) =>
            h.ref ? (
              <Button key={h.label} variant="primary" onClick={() => onOpen(h.ref!.kind === 'trade' ? h.ref!.episodeId! : h.ref!.id)}>
                {h.label}
              </Button>
            ) : (
              <Button key={h.label} disabled reason="Categoria assente in questo periodo">
                {h.label} · assente
              </Button>
            ),
          )}
        </div>
        <p className="footnote">
          {headlines.map((h) => (h.ref ? `${h.label}: ${h.ref.side} ${fmtUtc(h.ref.t)} (${CATEGORY_TEXT[h.ref.category]})` : `${h.label}: categoria assente`)).join(' · ')}
        </p>
      </section>

      <section className="card table-card" aria-label="Risultato modellato">
        <p className="table-title">Risultato modellato (USDT, somme per operazioni da {formatNumber(b.notionalUSDT, 0)} USDT)</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Voce</th>
                {periods.map(([p]) => (
                  <th key={p}>{PERIOD_LABEL(p)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <Row label="Netto modellato" periods={periods} value={(t) => usdt(t.trades.net)} />
              <Row label="Netto in punti base di N0" periods={periods} value={(t) => bps(t.trades.netBps)} />
              <Row label="PnL ai prezzi di riferimento" periods={periods} value={(t) => usdt(t.trades.pricePnLRef)} />
              <Row label="Slippage assunto" periods={periods} value={(t) => usdt(t.trades.slippage)} />
              <Row label="Fee assunte" periods={periods} value={(t) => usdt(t.trades.fees == null ? null : -t.trades.fees)} />
              <Row label="Funding storico (mark 1m)" periods={periods} value={(t) => usdt(t.trades.funding)} />
              <Row label="Netto con costi di stress (10 bp + 10 bp)" periods={periods} value={(t) => usdt(t.trades.stressNet)} />
              <Row label="Operazioni (LONG / SHORT)" periods={periods} value={(t) => `${t.trades.n} (${t.trades.long} / ${t.trades.short})`} />
              {halted && <Row label="Operazioni irrisolte (percorso non valutabile)" periods={periods} value={(t) => String(t.trades.unresolved)} />}
              {halted && (
                <Row
                  label="Parte nota: netto delle sole operazioni concluse (parziale)"
                  periods={periods}
                  value={(t) => `${usdt(t.trades.closedSubset.net)} su ${t.trades.closedSubset.trades}`}
                />
              )}
              <Row label="Quota operazioni positive" periods={periods} value={(t) => closedOnly(t, pct(t.trades.positiveShare))} />
              <Row label="Netto per operazione: mediana (P25 / P75)" periods={periods} value={(t) => closedOnly(t, `${num(t.trades.perTrade.net.p50)} (${num(t.trades.perTrade.net.p25)} / ${num(t.trades.perTrade.net.p75)})`)} />
              <Row label="Rischio iniziale per operazione (mediana, % di N0)" periods={periods} value={(t) => closedOnly(t, pct(t.trades.perTrade.riskInitialOverN0.p50, 2))} />
              <Row label="Drawdown massimo (chiusure 1m)" periods={periods} value={(t) => usdt(t.drawdown.maxDrawdown)} />
              {halted && (
                <Row
                  label="Drawdown della sola parte valutata (parziale)"
                  periods={periods}
                  value={(t) => (t.drawdown.partialUntil != null ? `${usdt(t.drawdown.partialMaxDrawdown ?? null)} fino al ${fmtUtc(t.drawdown.partialUntil)}` : '—')}
                />
              )}
              <Row label="Sequenza massima di perdite" periods={periods} value={(t) => closedOnly(t, String(t.trades.maxLosingStreak))} />
              <Row label="Tempo in posizione" periods={periods} value={(t) => closedOnly(t, pct(t.trades.exposureShare))} />
              <Row label="Peso dei 5 trade maggiori (|netto|)" periods={periods} value={(t) => closedOnly(t, pct(t.trades.concentration.top5AbsShare))} />
            </tbody>
          </table>
        </div>
        {dev.trades.net === null && (
          <Notice tone="warning" title="Netto completo non disponibile">
            {halted
              ? 'Un’operazione ha il percorso irrisolto: netto, stress e drawdown restano mancanti, non vengono sostituiti con zero né con un’uscita ipotetica.'
              : 'Almeno un costo non è valutabile: il netto resta mancante, non viene sostituito con zero.'}
          </Notice>
        )}
      </section>

      <section className="card table-card" aria-label="Decisioni e operazioni">
        <p className="table-title">Decisioni del candidato e motivi d’uscita</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Voce</th>
                {periods.map(([p]) => (
                  <th key={p}>{PERIOD_LABEL(p)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <Row label="Copertura della valutazione" periods={periods} value={coverageText} />
              <Row
                label="Chiusure 45m valutate (valide) · solo teoriche"
                periods={periods}
                value={(t) => `${t.evaluatedCloses} (${t.validCloses})${t.notEvaluatedCloses ? ` · ${t.notEvaluatedCloses} non valutate` : ''}`}
              />
              <Row label="Movimenti considerati" periods={periods} value={(t) => String(t.legs)} />
              <Row label="Movimenti riconosciuti (episodi)" periods={periods} value={(t) => String(t.episodes)} />
              <Row label="Call (richieste d’ingresso)" periods={periods} value={(t) => String(t.calls)} />
              <Row label="Ingressi eseguiti / rifiutati al prezzo" periods={periods} value={(t) => `${t.requests.FILLED} / ${t.requests.REJECTED_PRICE}`} />
              {Object.keys(EXIT_TEXT).map((r) => (
                <Row key={r} label={`Uscite per ${EXIT_TEXT[r]}`} periods={periods} value={(t) => String(t.trades.exits[r])} />
              ))}
              <Row label="Protezioni aggiornate (operazioni)" periods={periods} value={(t) => `${t.trades.protectionUpdates} (${t.trades.tradesWithProtectionUpdate})`} />
              <Row label="Stop e target nello stesso minuto" periods={periods} value={(t) => String(t.trades.bothTouched)} />
            </tbody>
          </table>
        </div>
      </section>

      <section className="card table-card" id="storico" aria-label="Mesi" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
        <p className="table-title">Mesi · operazioni per mese d’ingresso, cashflow per data effettiva</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mese</th>
                <th>Episodi</th>
                <th>Call</th>
                <th>Operazioni</th>
                <th>Netto per ingresso</th>
                <th>Cashflow netto per data</th>
                <th>Stop / target</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(s.months).map(([m, t]) => (
                <tr key={m} className={t.trades.n === 0 || !t.coverage.evaluated ? 'is-empty' : undefined}>
                  <td>{m}</td>
                  {!t.coverage.evaluated ? (
                    <td colSpan={6}>non valutato: dopo l’interruzione della finestra (nessun valore, non zero)</td>
                  ) : (
                    <>
                      <td>{t.episodes}</td>
                      <td>{t.calls}</td>
                      <td>
                        {t.trades.n}
                        {t.trades.unresolved ? ` (${t.trades.unresolved} irrisolta)` : ''}
                      </td>
                      <td>
                        {t.trades.n === 0 ? 'nessuna operazione' : usdt(t.trades.net)}
                        {!t.coverage.complete ? ' · parziale' : ''}
                      </td>
                      <td>{usdt(t.cashflowByTimestamp.net)}</td>
                      <td>
                        {t.trades.exits.STOP} / {t.trades.exits.TARGET}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="footnote">
          Il percorso {PERIOD_LABEL(s.phase)} è continuo: nessun azzeramento a fine mese{additional ? '' : ' o anno'}. Il registro completo delle operazioni è nella voce
          «Registro operazioni».
        </p>
      </section>

      <section className="card unavailable" id="conto" aria-label="Conto" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
        <p className="section-title">Nessun conto personale</p>
        <p className="t-2">
          Il backtest usa un nozionale normalizzato fisso per operazione, senza leva, margine o reinvestimento. Non esiste un saldo dell’Owner; i comandi della simulazione
          locale non modificano questi risultati.
        </p>
      </section>
    </main>
  );
}
