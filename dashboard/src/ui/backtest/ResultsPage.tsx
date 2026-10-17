import type { BtPeriod } from '../../contract/backtest';
import type { BacktestStudy } from '../../backtest/study';
import { formatNumber } from '../../lib/numbers';
import { Info } from '../components/Info';
import { Badge, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { Link } from '../Link';
import { paths, type ResultSource } from '../router';
import { CATEGORY_TEXT, EXIT_TEXT, bps, num, pct, plainUsdt, usdt } from './text';

const day = (ms: number) => fmtUtc(ms).slice(0, 11).trim();
/** Ultimo giorno incluso di un periodo [start, end). */
const lastDay = (end: number) => day(end - 1);
export const periodText = (start: number, end: number) => `dal ${day(start)} al ${lastDay(end)} (UTC)`;

const PERIOD_LABEL = (p: string, profileLabel: string, mainPhase: string) => (p === mainPhase ? profileLabel : p);

/** Stato di copertura di un periodo: con valutazione interrotta i conteggi descrivono solo la parte valutata. */
const coverageText = (t: BtPeriod) =>
  !t.coverage.evaluated ? 'non valutato' : t.coverage.complete ? 'completa' : `parziale fino al ${fmtUtc(t.coverage.evaluatedUntil)}`;
/** Statistiche per operazione calcolate dal motore sulle sole concluse: con irrisolte sono parte nota, non complete. */
const closedOnly = (t: BtPeriod, text: string) => (t.trades.unresolved ? `${text} · solo concluse` : text);

function Row({ label, info, periods, value, strong }: { label: string; info?: string; periods: [string, BtPeriod][]; value: (t: BtPeriod) => string; strong?: boolean }) {
  return (
    <tr className={strong ? 'row-total' : undefined}>
      <td>
        {label}
        {info && <Info label={label}>{info}</Info>}
      </td>
      {periods.map(([p, t]) => (
        <td key={p}>{value(t)}</td>
      ))}
    </tr>
  );
}

function PeriodHead({ periods, profileLabel, phase }: { periods: [string, BtPeriod][]; profileLabel: string; phase: string }) {
  return (
    <thead>
      <tr>
        <th>Voce</th>
        {periods.map(([p]) => (
          <th key={p}>{PERIOD_LABEL(p, profileLabel, phase)}</th>
        ))}
      </tr>
    </thead>
  );
}

export const UNIT_INFO =
  'USDT è l’unità di conto usata in questa simulazione (una moneta digitale agganciata al dollaro): non sono euro e non è il saldo di un conto.';

export function ResultsPage({ study, source }: { study: BacktestStudy; source: ResultSource }) {
  const b = study.bundle;
  const s = b.summary;
  const profile = study.profile;
  // Un anno che coincide con l'intera finestra (2025, gennaio 2025) è mostrato una volta sola, come periodo del profilo.
  const periods: [string, BtPeriod][] = s.periods
    .filter((p) => p === s.phase || s.tables[p].start !== s.tables[s.phase].start || s.tables[p].end !== s.tables[s.phase].end)
    .map((p) => [p, s.tables[p]]);
  const main = s.tables[s.phase];
  const exposed2025 = s.phase === 'ADDITIONAL_2025' || s.phase === 'APP_CHECK_2025_01';
  const check = profile.kind === 'PRODUCT_CHECK';
  const q = b.quality;
  const headlines = study.headlines();
  const halted = s.halted;
  const rec = s.reconciliation;
  const n0 = b.notionalUSDT;
  const tr = main.trades;
  const riskMedian = tr.perTrade.riskInitialOverN0.p50;
  const seenExample = new Map<string, string>();

  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Risultato del backtest">
        <div className="card-head">
          <div>
            <p className="section-title">
              {profile.label} · {periodText(b.window.start, b.window.end)}
            </p>
            <p className="card-sub">
              Candidato di sviluppo {b.candidate.id} versione {b.candidate.version}, <strong>non promosso</strong> all’uso reale · motore {b.engineVersion} · dati
              Binance Vision BTCUSDT perpetual · risultato <span className="mono">{b.run.runId}</span>
            </p>
          </div>
          <div className="actions">
            {study.synthetic && <Badge tone="warning">FIXTURE SINTETICA</Badge>}
            {exposed2025 && <Badge tone="warning">2025 GIÀ ESPOSTO · NON È UNA VERIFICA INDIPENDENTE</Badge>}
            {check && <Badge tone="neutral">COLLAUDO DEL PRODOTTO</Badge>}
          </div>
        </div>
        <p className="t-2">
          Il programma ha già elaborato tutto il periodo, una chiusura da 45 minuti dopo l’altra, partendo senza posizioni. La storia dal {day(b.window.inputStart)} serve
          soltanto a osservare il mercato: le operazioni simulate iniziano il {day(b.window.start)}.
          {check && ' È una prova breve per verificare avvio, avanzamento e risultati dell’app: non è un nuovo studio né un mese scelto per il risultato.'}
          {s.phase === 'ADDITIONAL_2025' && ' Il 2025 era già stato esaminato in studi precedenti: è un confronto aggiuntivo, separato dallo sviluppo 2023–2024.'}
          {profile.inferred && ' Risultato prodotto prima dell’app: il profilo è dedotto dalla fase registrata.'}
        </p>

        <div className="hero">
          <div className="hero-main">
            <p className="metric-label">
              Risultato dopo i costi
              <Info label="Risultato dopo i costi">
                Somma dei risultati di tutte le operazioni simulate del periodo, dopo commissioni, effetto del prezzo di esecuzione e pagamenti periodici del contratto.{' '}
                {UNIT_INFO}
              </Info>
            </p>
            <p className={`metric-value big ${tr.net == null ? 'is-missing' : tr.net < 0 ? 't-neg' : 't-pos'}`}>{tr.net == null ? 'non calcolabile' : usdt(tr.net)}</p>
            <p className="metric-sub">unità usata in questa simulazione; non euro</p>
          </div>
          <div className="hero-side">
            <p>
              <strong>Dimensione di ogni operazione: {formatNumber(n0, 0)} USDT</strong>
              <Info label="Dimensione di ogni operazione">
                Valore convenzionale fisso di ogni operazione simulata, uguale per tutte. Non è il capitale di un conto e non è la perdita massima: il rischio fino allo
                stop è molto più piccolo{riskMedian != null ? ` (a metà delle operazioni circa ${plainUsdt(riskMedian * n0)} o meno)` : ''}. Non esiste un saldo personale.
              </Info>
            </p>
            <p>
              Operazioni simulate: <strong>{tr.n}</strong> ({tr.long} su una salita, {tr.short} su una discesa)
            </p>
            <Link to={paths.operations(source)} className="btn btn-primary">
              Tutte le operazioni ({b.trades.length})
            </Link>
          </div>
        </div>
      </section>

      {halted && (
        <Notice tone="warning" title={`Periodo interrotto il ${fmtUtc(halted.at)}: risultato completo non disponibile`}>
          Manca un minuto di prezzo mentre una posizione era aperta ({halted.reason}): il percorso di quell’operazione non si può ricostruire e la valutazione si ferma
          lì. Risultato, scenario con costi più alti e perdita massima del periodo restano mancanti. Parte nota, dichiaratamente parziale: {rec.closedTrades} operazioni
          concluse con {usdt(rec.knownPartNet)}; {rec.unresolvedTrades} irrisolte; {formatNumber(rec.evaluatedCloses, 0)} chiusure 45m valutate e{' '}
          {formatNumber(rec.notEvaluatedCloses, 0)} non valutate.
        </Notice>
      )}

      <section className="card table-card" aria-label="Da dove viene il risultato">
        <p className="table-title">Da dove viene il risultato (USDT, somme sulle operazioni del periodo)</p>
        <div className="table-scroll">
          <table className="data-table">
            <PeriodHead periods={periods} profileLabel={profile.label} phase={s.phase} />
            <tbody>
              <Row
                label="Guadagno/perdita dal solo movimento dei prezzi"
                info="Differenza fra il prezzo di riferimento d’uscita e quello d’ingresso, per la dimensione dell’operazione, come se si potesse comprare e vendere esattamente al prezzo del grafico."
                periods={periods}
                value={(t) => usdt(t.trades.pricePnLRef)}
              />
              <Row
                label="Effetto del prezzo di esecuzione"
                info="Slippage: differenza sfavorevole assunta fra il prezzo del grafico e quello a cui l’operazione viene eseguita (3 punti base per lato). È già dentro i prezzi d’ingresso e d’uscita: qui è solo mostrata a parte, non viene sottratta una seconda volta."
                periods={periods}
                value={(t) => usdt(t.trades.slippage)}
              />
              <Row
                label="Commissioni"
                info="Commissione assunta di 5 punti base su ciascuno dei due eseguiti, ingresso e uscita. Un tentativo non eseguito non paga commissioni."
                periods={periods}
                value={(t) => usdt(t.trades.fees == null ? null : -t.trades.fees)}
              />
              <Row
                label="Pagamento periodico del contratto"
                info="Funding: pagamento periodico fra chi punta su una salita e chi su una discesa, preso dallo storico di Binance. Può essere pagato o ricevuto. Un dato mancante resta mancante, non diventa zero."
                periods={periods}
                value={(t) => usdt(t.trades.funding)}
              />
              <Row label="Risultato dopo i costi" periods={periods} value={(t) => usdt(t.trades.net)} strong />
              {halted && <Row label="Operazioni irrisolte (percorso non valutabile)" periods={periods} value={(t) => String(t.trades.unresolved)} />}
              {halted && (
                <Row
                  label="Parte nota: solo operazioni concluse (parziale)"
                  periods={periods}
                  value={(t) => `${usdt(t.trades.closedSubset.net)} su ${t.trades.closedSubset.trades}`}
                />
              )}
            </tbody>
          </table>
        </div>
        <p className="footnote">
          Le quattro voci sommate danno il risultato dopo i costi. Ogni operazione vale {formatNumber(n0, 0)} USDT: i totali sono somme di operazioni simulate, non un
          rendimento di un conto.
        </p>
        {main.trades.net === null && (
          <Notice tone="warning" title="Risultato completo non disponibile">
            {halted
              ? 'Un’operazione ha il percorso irrisolto: risultato, scenario con costi più alti e perdita massima restano mancanti, non vengono sostituiti con zero né con un’uscita ipotetica.'
              : 'Almeno un costo non è valutabile: il risultato resta mancante, non viene sostituito con zero.'}
          </Notice>
        )}
      </section>

      <section className="section" aria-label="Esempi dal registro">
        <div className="section-head">
          <div>
            <p className="section-title">Esempi dal registro</p>
            <p className="section-desc">
              Scorciatoie ai primi casi di ciascun tipo, in ordine di tempo, scelti con una regola fissata prima di conoscere i risultati (non i grafici più belli). Non
              sono tutto il risultato: ogni operazione è in «Tutte le operazioni».
            </p>
          </div>
        </div>
        <ul className="examples">
          {headlines.map((h) => {
            if (!h.ref) {
              return (
                <li key={h.label}>
                  <span className="btn btn-secondary is-static" aria-disabled="true">
                    {h.label} · assente
                  </span>
                  <span className="t-3">nessun caso di questo tipo nel periodo</span>
                </li>
              );
            }
            const target = h.ref.kind === 'trade' ? h.ref.episodeId! : h.ref.id;
            const same = seenExample.get(target);
            if (!same) seenExample.set(target, h.label);
            return (
              <li key={h.label}>
                <Link to={paths.episode(source, target, 'examples')} className="btn btn-primary">
                  {h.label}
                </Link>
                <span className="t-2">
                  {h.ref.side === 'LONG' ? 'su una salita' : 'su una discesa'}, {fmtUtc(h.ref.t)} — {CATEGORY_TEXT[h.ref.category]}
                  {same ? ` · è lo stesso episodio di «${same}»: in questo periodo il primo caso dei due tipi coincide` : ''}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="card table-card" aria-label="Scenario con costi più alti">
        <p className="table-title">
          Scenario con costi più alti
          <Info label="Scenario con costi più alti">
            Le stesse operazioni, con gli stessi ingressi e le stesse uscite, ricalcolate con commissioni di 10 punti base e prezzo di esecuzione peggiore di 10 punti base
            per lato. Non è un altro percorso del bot e non va sommato al risultato principale.
          </Info>
        </p>
        <div className="table-scroll">
          <table className="data-table">
            <PeriodHead periods={periods} profileLabel={profile.label} phase={s.phase} />
            <tbody>
              <Row label="Stesse operazioni con costi più severi" periods={periods} value={(t) => usdt(t.trades.stressNet)} />
            </tbody>
          </table>
        </div>
      </section>

      <section className="card table-card" aria-label="Decisioni e operazioni">
        <p className="table-title">Decisioni del bot e motivi di chiusura</p>
        <div className="table-scroll">
          <table className="data-table">
            <PeriodHead periods={periods} profileLabel={profile.label} phase={s.phase} />
            <tbody>
              <Row label="Copertura della valutazione" periods={periods} value={coverageText} />
              <Row
                label="Chiusure 45m valutate (con dati validi) · non valutate"
                periods={periods}
                value={(t) => `${t.evaluatedCloses} (${t.validCloses})${t.notEvaluatedCloses ? ` · ${t.notEvaluatedCloses} non valutate` : ''}`}
              />
              <Row label="Movimenti considerati" periods={periods} value={(t) => String(t.legs)} />
              <Row label="Movimenti riconosciuti (episodi)" periods={periods} value={(t) => String(t.episodes)} />
              <Row
                label="Decisioni di tentare un ingresso"
                info="Il bot decide di tentare l’ingresso al minuto successivo, solo se il prezzo resta entro un limite. Un tentativo non è ancora una posizione."
                periods={periods}
                value={(t) => String(t.calls)}
              />
              <Row label="Tentativi eseguiti / non eseguiti per il prezzo" periods={periods} value={(t) => `${t.requests.FILLED} / ${t.requests.REJECTED_PRICE}`} />
              {Object.keys(EXIT_TEXT).map((r) => (
                <Row key={r} label={`Chiuse per ${EXIT_TEXT[r]}`} periods={periods} value={(t) => String(t.trades.exits[r])} />
              ))}
              <Row label="Limiti di protezione aggiornati (operazioni)" periods={periods} value={(t) => `${t.trades.protectionUpdates} (${t.trades.tradesWithProtectionUpdate})`} />
              <Row label="Stop e obiettivo toccati nello stesso minuto" periods={periods} value={(t) => String(t.trades.bothTouched)} />
            </tbody>
          </table>
        </div>
      </section>

      <section className="card table-card" id="storico" aria-label="Mesi" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
        <p className="table-title">Mesi · operazioni per mese d’ingresso, pagamenti per data effettiva</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mese</th>
                <th>Episodi</th>
                <th>Tentativi</th>
                <th>Operazioni</th>
                <th>Risultato per mese d’ingresso</th>
                <th>Movimenti di denaro per data</th>
                <th>Stop / obiettivo</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(s.months).map(([m, t]) => (
                <tr key={m} className={t.trades.n === 0 || !t.coverage.evaluated ? 'is-empty' : undefined}>
                  <td>{m}</td>
                  {!t.coverage.evaluated ? (
                    <td colSpan={6}>non valutato: dopo l’interruzione del periodo (nessun valore, non zero)</td>
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
        <p className="footnote">Il percorso è continuo: nessun azzeramento a fine mese o anno.</p>
      </section>

      <details className="card table-card tech" aria-label="Dettagli tecnici">
        <summary>Dettagli tecnici: punti base, N0, profit factor e altre misure</summary>
        <p className="t-2">
          bp = punti base: 1 bp = 0,01%. N0 = dimensione convenzionale di ogni operazione, {formatNumber(n0, 0)} USDT. Per una singola operazione, −40 bp di N0
          corrispondono a circa −4 USDT, cioè −0,40% della dimensione convenzionale; per un totale su molte operazioni non è un rendimento del conto, perché non esiste un
          capitale cumulato.
        </p>
        <div className="table-scroll">
          <table className="data-table">
            <PeriodHead periods={periods} profileLabel={profile.label} phase={s.phase} />
            <tbody>
              <Row label="Netto in punti base di N0" periods={periods} value={(t) => bps(t.trades.netBps)} />
              <Row label="PnL ai prezzi di riferimento" periods={periods} value={(t) => usdt(t.trades.pricePnLRef)} />
              <Row label="Netto con costi di stress (10 bp + 10 bp)" periods={periods} value={(t) => usdt(t.trades.stressNet)} />
              <Row label="Quota operazioni positive" periods={periods} value={(t) => closedOnly(t, pct(t.trades.positiveShare))} />
              <Row label="Profit factor (somma guadagni / somma perdite)" periods={periods} value={(t) => closedOnly(t, num(t.trades.profitFactor))} />
              <Row label="Payoff medio (guadagno medio / perdita media)" periods={periods} value={(t) => closedOnly(t, num(t.trades.payoff))} />
              <Row
                label="Netto per operazione: mediana (P25 / P75)"
                periods={periods}
                value={(t) => closedOnly(t, `${num(t.trades.perTrade.net.p50)} (${num(t.trades.perTrade.net.p25)} / ${num(t.trades.perTrade.net.p75)})`)}
              />
              <Row label="Rischio iniziale fino allo stop (mediana, % di N0)" periods={periods} value={(t) => closedOnly(t, pct(t.trades.perTrade.riskInitialOverN0.p50, 2))} />
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
        <p className="footnote">
          {b.economicsLabel}. Qualità dei dati: {formatNumber(q.trade.totals.valid, 0)}/{formatNumber(q.trade.totals.expected, 0)} minuti validi dal{' '}
          {day(b.window.inputStart)} (storia osservata inclusa), funding {q.funding.series.events} eventi ({q.funding.series.anomalies.length} anomalie), mark per il funding{' '}
          {q.mark.pointsAvailable}/{q.mark.pointsNeeded} punti. Configurazione <span className="mono">{b.candidate.hash.slice(0, 12)}</span>, input{' '}
          <span className="mono">{b.run.inputHash?.slice(0, 12) ?? '—'}</span>. {b.source.attribution}.
        </p>
      </details>

      <section className="card unavailable" id="conto" aria-label="Conto" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
        <p className="section-title">Nessun conto personale</p>
        <p className="t-2">
          Il backtest usa una dimensione fissa per operazione, senza leva, margine o reinvestimento. Non esiste un saldo dell’Owner; i comandi della simulazione locale non
          modificano questi risultati.
        </p>
      </section>
    </main>
  );
}
