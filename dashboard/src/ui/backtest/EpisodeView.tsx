import { useState, type ReactNode } from 'react';
import type { BtEpisode, BtState, BtTrade } from '../../contract/backtest';
import type { BacktestStudy, PlanLevel } from '../../backtest/study';
import { formatNumber } from '../../lib/numbers';
import { CandleChart, type ChartCandle, type ChartLevel, type ChartMarker, type ChartOverlays } from '../components/CandleChart';
import { Info } from '../components/Info';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc, isoMinute } from '../format';
import { Link } from '../Link';
import { paths, type From, type ResultSource } from '../router';
import { UNIT_INFO } from './ResultsPage';
import { ABSTAIN_TEXT, CLOSE_WHY, SIDE, bps, num, pct, plainUsdt, px, stateText, usdt } from './text';

const KEY_STATES = ['RECOGNIZED', 'WAIT_REACTION', 'WAIT_RESUMPTION', 'CALL', 'FILLED', 'PROTECTION_UPDATE', 'EXIT_STRUCTURE_REQUESTED', 'CLOSED'];
const iso = (ms: number) => new Date(ms).toISOString();
const hm = (ms: number) => isoMinute(ms).replace('T', ' ').replace('Z', ' UTC');

function moments(ep: BtEpisode): BtState[] {
  const out: BtState[] = [];
  let lastWait = '';
  for (const s of ep.states) {
    const terminal = ep.termination && s.t === ep.termination.t && s.state === ep.termination.code;
    if (!KEY_STATES.includes(s.state) && !terminal) continue;
    if ((s.state === 'WAIT_REACTION' || s.state === 'WAIT_RESUMPTION') && s.state === lastWait) continue;
    lastWait = s.state.startsWith('WAIT') ? s.state : '';
    out.push(s);
  }
  return out;
}

/** Momento della decisione: la decisione di tentare, oppure la rinuncia, oppure il riconoscimento. */
function decisionMoment(ep: BtEpisode): number {
  return ep.call?.t ?? ep.termination?.t ?? ep.t0;
}

function Step({ title, children, tone = 'neutral' }: { title: string; children: ReactNode; tone?: 'neutral' | 'accent' | 'warning' | 'positive' | 'negative' }) {
  return (
    <div className={`bt-step tone-${tone}`}>
      <p className="bt-step-title">{title}</p>
      <div className="bt-step-body">{children}</div>
    </div>
  );
}

function planLevels(levels: PlanLevel[]): ChartLevel[] {
  return levels.map((l) => ({ id: l.id, kind: l.kind, origin: 'PLAN', overlay: 'PLAN', validTo: null, label: `${l.label} · ${formatNumber(l.price, 0)}`, price: { amount: l.price } }));
}

/** Ritorno evidente secondo la provenienza; il registro resta comunque raggiungibile. */
function BackRow({ source, from }: { source: ResultSource; from: From }) {
  return (
    <div className="back-row">
      {from === 'operations' ? (
        <>
          <Link to={paths.operations(source)} className="btn btn-primary">
            ← Torna alle operazioni
          </Link>
          <Link to={paths.result(source)} className="btn btn-secondary">
            Risultati
          </Link>
        </>
      ) : (
        <>
          <Link to={paths.result(source)} className="btn btn-primary">
            ← Torna ai risultati
          </Link>
          <Link to={paths.operations(source)} className="btn btn-secondary">
            Tutte le operazioni
          </Link>
        </>
      )}
    </div>
  );
}

export function EpisodeView({ study, id, source, from, initialCursor }: { study: BacktestStudy; id: string; source: ResultSource; from: From; initialCursor?: number }) {
  const ep = study.episode(id);
  if (!ep) return <LegView study={study} id={id} source={source} from={from} />;
  return <Episode study={study} ep={ep} source={source} from={from} initialCursor={initialCursor} />;
}

function Episode({ study, ep, source, from, initialCursor }: { study: BacktestStudy; ep: BtEpisode; source: ResultSource; from: From; initialCursor?: number }) {
  const tr = study.trade(ep.tradeId);
  const ms = moments(ep);
  const [cursor, setCursor] = useState<number>(initialCursor ?? decisionMoment(ep));
  const [retro, setRetro] = useState(false);
  const [scale, setScale] = useState<'45m' | '1D'>('45m');
  const [overlays, setOverlays] = useState<ChartOverlays>({ averages: true, levels: true, fibonacci: false, volume: true });
  const known = (t: number) => retro || t <= cursor;
  const statesNow = ep.states.filter((s) => s.t <= cursor);
  const lastWait = [...statesNow].reverse().find((s) => s.state === 'WAIT_REACTION' || s.state === 'WAIT_RESUMPTION');
  const terminated = ep.termination && known(ep.termination.t) ? ep.termination : null;
  const req = ep.request;
  const notExecuted = req && req.outcome !== 'FILLED' && known(req.executeAt) ? req : null;
  const abstained = terminated && terminated.code !== 'CLOSED' && terminated.code !== 'UNRESOLVED_DATA_GAP' && !notExecuted ? terminated : null;
  const callKnown = ep.call && ep.call.t <= cursor ? ep.call : null;
  const entryKnown = tr && known(tr.entryTime) ? tr : null;
  const exit = tr?.exit ?? null;
  const exitKnown = exit && known(exit.accountingTime) ? exit : null;
  const gapKnown = tr?.gap && known(tr.gap.at) ? tr.gap : null;
  const snap = study.snapshotAt(ep.id, cursor);
  const w = SIDE[ep.side];

  const raw = study.candles(ep.id, scale, cursor, retro);
  const candles: ChartCandle[] = raw.map((c) => ({ openTime: iso(c.openTime), open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume, partial: false, gap: c.gap, retrospective: c.retrospective }));
  const sma = scale === '45m' ? study.sma(ep.id, raw) : { sma20: [], sma50: [] };
  const markers: ChartMarker[] = scale === '45m'
    ? study.pivots(ep.id, cursor).map((p) => ({ time: iso(p.candidateOpen), kind: p.kind, title: `Pivot ${p.kind} sulla candela ${isoMinute(p.candidateOpen)}, noto alla chiusura ${isoMinute(p.availableAt)}` }))
    : [];
  // R1-C: prezzo corrente solo se una candela completa della scala termina esattamente al momento;
  // altrimenti ultimo noto della stessa scala, separato e dichiarato non corrente.
  const lastCausal = raw.filter((c) => !c.retrospective && !c.gap).at(-1);
  const currentPrice = lastCausal && lastCausal.end === cursor ? lastCausal.close : null;
  const plan = ep.plan;

  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <BackRow source={source} from={from} />
      <section className="card table-card" aria-label="Episodio">
        <div className="card-head">
          <div>
            <p className="section-title">
              {ep.side === 'LONG' ? 'Salita' : 'Discesa'} riconosciuta il {fmtUtc(ep.t0)} · {ep.side}
              <Info label="LONG e SHORT">
                LONG significa puntare su una salita del prezzo; SHORT significa puntare su una discesa. Uno SHORT non è la vendita di BTC posseduti: nella simulazione
                guadagna se il prezzo scende.
              </Info>
            </p>
            <p className="card-sub mono">{ep.id}</p>
          </div>
          <div className="actions">
            <Badge tone={retro ? 'warning' : 'accent'}>{retro ? 'A POSTERIORI · ciò che è successo dopo' : 'SOLO INFORMAZIONI DEL MOMENTO'}</Badge>
          </div>
        </div>
        <p className="t-2">
          Il programma ha già elaborato tutto il periodo; qui consulti un momento. Momento consultato: <strong>{fmtUtc(cursor)}</strong>.
        </p>
        <div className="actions" role="group" aria-label="Momenti dell'episodio">
          {ms.map((s) => (
            <Button key={`${s.t}-${s.state}`} variant={s.t === cursor ? 'primary' : 'secondary'} pressed={s.t === cursor} onClick={() => setCursor(s.t)}>
              {isoMinute(s.t).slice(5, 16).replace('T', ' ')} · {stateText(s.state)}
            </Button>
          ))}
        </div>
      </section>

      <div className="row-market">
        <section className="card card-chart" aria-label="Grafico dell'episodio">
          <div className="toolbar">
            <div className="tools">
              <Button variant={scale === '45m' ? 'primary' : 'secondary'} pressed={scale === '45m'} onClick={() => setScale('45m')}>
                45m
              </Button>
              <Button variant={scale === '1D' ? 'primary' : 'secondary'} pressed={scale === '1D'} onClick={() => setScale('1D')}>
                1D
              </Button>
            </div>
            {retro ? (
              <Button onClick={() => setRetro(false)}>Solo informazioni del momento</Button>
            ) : (
              <Button variant="primary" onClick={() => setRetro(true)}>
                Mostra cosa è successo dopo
              </Button>
            )}
          </div>
          {currentPrice === null && (
            <Notice tone="warning" title={`Prezzo al momento non disponibile sulla scala ${scale}`}>
              Nessuna candela {scale} completa termina alle {fmtUtc(cursor)}: nessun prezzo corrente sul grafico.{' '}
              {lastCausal
                ? `Ultimo noto della stessa scala: ${px(lastCausal.close)} USDT, chiusura alle ${fmtUtc(lastCausal.end)} (non corrente).`
                : 'Nessuna candela completa nel tratto entro il momento consultato: prezzo non disponibile.'}
            </Notice>
          )}
          <CandleChart
            timeframe={scale}
            candles={candles}
            series={[
              { id: 'sma20', name: 'SMA20', points: sma.sma20.map((p) => ({ time: iso(p.time), value: p.value })) },
              { id: 'sma50', name: 'SMA50', points: sma.sma50.map((p) => ({ time: iso(p.time), value: p.value })) },
            ]}
            levels={planLevels(study.levels(ep, cursor, retro))}
            overlays={overlays}
            lastPrice={currentPrice}
            lastPriceCurrent
            utc
            markers={markers}
            dataLabel="storiche"
          />
          <div className="overlays">
            <span>Overlay</span>
            {(['averages', 'volume'] as const).map((k) => (
              <button key={k} type="button" className={`badge ${overlays[k] ? 'tone-accent' : 'tone-neutral'}`} role="switch" aria-checked={overlays[k]} onClick={() => setOverlays((o) => ({ ...o, [k]: !o[k] }))}>
                {overlays[k] ? '☑' : '☐'} {k === 'averages' ? 'SMA20 / SMA50 (contesto)' : 'Volumi'}
              </button>
            ))}
          </div>
          <p className="reading">
            Orari UTC. Le linee del piano (P0, P1, stop, ingresso, uscita) compaiono solo quando erano note.{' '}
            {retro ? 'Le candele attenuate dopo la linea sono il seguito, mostrato a posteriori.' : 'Le candele successive al momento non sono mostrate.'} 45m e 1D cambiano
            solo la scala del grafico, non avviano una nuova prova.
          </p>
        </section>

        <section className="card card-call" aria-label="Che cosa ha fatto il bot">
          <p className="call-kicker">CHE COSA HA FATTO IL BOT</p>
          <Step title={`Il bot ha riconosciuto una ${w.move}`} tone="accent">
            {ep.side === 'LONG' ? 'Salita' : 'Discesa'} da P0 {px(ep.P0.price)} (candela {hm(ep.P0.candidateOpen)}) a P1 {px(ep.P1.price)} (candela{' '}
            {hm(ep.P1.candidateOpen)}): ampiezza {num(ep.L)} USDT, almeno 3 volte la volatilità A0 = {num(ep.A0)} ({num(3 * ep.A0)}). Struttura 45m{' '}
            {ep.side === 'LONG' ? 'crescente' : 'decrescente'}. P1 è diventato noto solo alla chiusura delle {hm(ep.P1.availableAt)}, due barre dopo la sua candela.
          </Step>
          {lastWait && (
            <Step title="Ha aspettato una reazione">
              Il prezzo è tornato indietro fino a {px(lastWait.Rext as number)}, cioè {pct(lastWait.depth as number, 0)} del movimento (ammesso fra 25% e 75%), con{' '}
              {String(lastWait.counterCloses)} chiusure contrarie; {String(lastWait.barsSinceP1)} barre dalla candela estrema su un massimo di 12. Stato:{' '}
              {stateText(lastWait.state).toLowerCase()}.
            </Step>
          )}
          {callKnown && plan && (
            <Step title={`Ha deciso di tentare ${w.attempt}`} tone="positive">
              Alla chiusura delle {hm(callKnown.t)} la candela ha chiuso a {px(plan.Ck)},{' '}
              {ep.side === 'LONG' ? 'sopra il massimo della precedente e sopra la propria apertura' : 'sotto il minimo della precedente e sotto la propria apertura'}: segnale
              di ripresa. Tentativo unico all’apertura del minuto {hm(callKnown.executeAt)}, solo se il prezzo è{' '}
              {ep.side === 'LONG' ? 'al massimo' : 'almeno'} {px(callKnown.entryBound)}. Limite di protezione (stop) {px(callKnown.S0)}, obiettivo {px(callKnown.T)}, prezzo
              d’ingresso stimato {px(callKnown.Estar)}: il guadagno possibile è {num(plan.ratio)} volte il rischio (minimo 1,5). <strong>Non è ancora entrato</strong>: non è un
              ordine che resta in attesa che il mercato tocchi il prezzo. Attesa: «{callKnown.expectation}», non una probabilità.
            </Step>
          )}
          {notExecuted && (
            <Step title={`${w.the} non è stat${ep.side === 'LONG' ? 'o' : 'a'} ${w.done}`} tone="warning">
              Alle {hm(notExecuted.executeAt)}: {ABSTAIN_TEXT[notExecuted.outcome] ?? notExecuted.outcome}.
              {notExecuted.Oref != null && ` Prezzo all’apertura ${px(notExecuted.Oref)} contro un limite di ${callKnown ? px(callKnown.entryBound) : '—'}.`} Nessuna posizione
              è stata aperta e nessuna commissione è stata pagata.
            </Step>
          )}
          {abstained && (
            <Step title="Ha rinunciato" tone="warning">
              Alle {hm(abstained.t)}: {ABSTAIN_TEXT[abstained.code] ?? abstained.code}.
              {abstained.code === 'ABSTAIN_REWARD_RISK' && plan && ` Rapporto calcolato ${num(plan.ratio)} con stop ${px(plan.S0)} e obiettivo ${px(plan.T)}.`}
            </Step>
          )}
          {entryKnown && (
            <Step title={`La posizione simulata è stata aperta a ${px(entryKnown.E)}`} tone="accent">
              Alle {hm(entryKnown.entryTime)}: prezzo d’apertura del minuto {px(entryKnown.Eref)}, più l’effetto del prezzo di esecuzione = {px(entryKnown.E)}. Posizione per{' '}
              {w.bet}, dimensione {formatNumber(entryKnown.N0, 0)} USDT ({formatNumber(entryKnown.q, 5)} BTC). Rischio fino al limite di protezione:{' '}
              {plainUsdt(entryKnown.q * entryKnown.R0)}.
            </Step>
          )}
          {tr && tr.stops.filter((s) => known(s.effectiveAt)).map((s) => (
            <Step key={s.effectiveAt} title={`Nuovo limite di protezione: da ${px(s.from)} a ${px(s.to)}`}>
              Deciso alle {hm(s.decidedAt)}, valido dalle {hm(s.effectiveAt)}: un nuovo punto di svolta a {px(s.pivot)} confermato dopo l’ingresso.{' '}
              {ep.side === 'LONG' ? 'Per una posizione su una salita il limite sale' : 'Per una posizione su una discesa il limite scende'} e non viene mai allontanato
              dal prezzo.
            </Step>
          ))}
          {exitKnown && tr && (
            <Step title={`La posizione è stata chiusa perché ${CLOSE_WHY[exitKnown.reason] ?? exitKnown.reason}`} tone={tr.net != null && tr.net < 0 ? 'negative' : 'positive'}>
              {exitKnown.intrabar
                ? `Contatto avvenuto durante il minuto ${hm(exitKnown.minute)}–${isoMinute(exitKnown.minute + 60_000).slice(11, 16)}, registrato alle ${hm(exitKnown.accountingTime)} (l’istante esatto nel minuto non è noto). `
                : `Alle ${hm(exitKnown.minute)}, all’apertura del minuto. `}
              Prezzo di riferimento {px(exitKnown.Xref)}, prezzo usato per la chiusura {px(exitKnown.X)}
              {exitKnown.gap ? ' (il prezzo d’apertura era già oltre il livello)' : ''}
              {exitKnown.bothTouched ? '; stop e obiettivo toccati nello stesso minuto: per prudenza si assume prima lo stop' : ''}.
            </Step>
          )}
          {gapKnown && (
            <Step title="Esito non calcolabile" tone="warning">
              Alle {hm(gapKnown.at)} manca il minuto di prezzo mentre la posizione era aperta: stop o obiettivo potrebbero essere stati toccati senza che si possa saperlo. Non
              è una chiusura: la valutazione del periodo si interrompe qui e nessun prezzo o risultato viene inventato.
            </Step>
          )}
          {!retro && ((tr && !exitKnown && !gapKnown) || (req && !known(req.executeAt))) && (
            <Notice tone="neutral" title="Il seguito non è ancora mostrato">
              Esito del tentativo, gestione, chiusura e costi successivi al momento consultato si vedono con «Mostra cosa è successo dopo».
            </Notice>
          )}
          {snap && <Context snap={snap} />}
        </section>
      </div>

      {retro && tr && <Result tr={tr} />}
    </main>
  );
}

function Context({ snap }: { snap: NonNullable<ReturnType<BacktestStudy['snapshotAt']>> }) {
  const m = (x: { v: unknown; r: string | null }, digits = 2) => (x.v == null ? `n.d. (${x.r})` : typeof x.v === 'number' ? num(x.v, digits) : String(x.v));
  return (
    <div className="levels-table" aria-label="Contesto delle sei famiglie">
      <p className="lt-head">Contesto noto alle {isoMinute(snap.t)} (le famiglie di contesto non decidono)</p>
      <div className="lt-row"><span className="lt-label">Struttura 45m · decisionale</span><span className="lt-val">{m(snap.structure45m)}</span><span /></div>
      <div className="lt-row"><span className="lt-label">Volatilità A · decisionale</span><span className="lt-val">{m(snap.A)}</span><span /></div>
      <div className="lt-row"><span className="lt-label">Struttura 1D · contesto</span><span className="lt-val">{m(snap.structure1D)}</span><span /></div>
      <div className="lt-row"><span className="lt-label">SMA20 / SMA50 · contesto</span><span className="lt-val">{m(snap.sma20)} / {m(snap.sma50)}</span><span /></div>
      <div className="lt-row"><span className="lt-label">Volume relativo · contesto</span><span className="lt-val">{m(snap.volumeRatio, 3)}</span><span /></div>
      <div className="lt-row"><span className="lt-label">Fibonacci u / r · contesto</span><span className="lt-val">{num(snap.fib.u, 3)} / {num(snap.fib.r, 3)}</span><span /></div>
    </div>
  );
}

function Result({ tr }: { tr: BtTrade }) {
  const counted = tr.funding.events.filter((e) => e.counted);
  const fees = tr.feeExit == null ? -tr.feeEntry : -(tr.feeEntry + tr.feeExit);
  return (
    <section className="card card-position retro-card" aria-label="Risultato dell'operazione">
      <div className="card-head">
        <p className="section-title">Risultato dell’operazione</p>
        <Badge tone="warning">A POSTERIORI</Badge>
      </div>
      {!tr.exit && (
        <Notice tone="warning" title="Percorso irrisolto: risultato non disponibile">
          Dati mancanti alle {tr.gap ? hm(tr.gap.at) : '—'} con posizione aperta: chiusura, guadagno/perdita e risultato restano mancanti. Sono mostrati solo i fatti noti
          fino alla lacuna (ingresso, commissione d’ingresso, pagamenti valutabili).
        </Notice>
      )}
      <div className="metrics">
        <div className="metric">
          <p className="metric-label">
            Risultato dopo i costi
            <Info label="Risultato dell’operazione">{UNIT_INFO}</Info>
          </p>
          <p className={`metric-value ${tr.net != null && tr.net < 0 ? 't-neg' : 't-pos'}`}>{usdt(tr.net)}</p>
          <p className="metric-sub">su {formatNumber(tr.N0, 0)} USDT di dimensione convenzionale</p>
        </div>
        <div className="metric">
          <p className="metric-label">Movimento dei prezzi</p>
          <p className="metric-value">{usdt(tr.pricePnLRef)}</p>
          <p className="metric-sub">ai prezzi del grafico</p>
        </div>
        <div className="metric">
          <p className="metric-label">
            Effetto del prezzo di esecuzione
            <Info label="Effetto del prezzo di esecuzione">
              Slippage: differenza sfavorevole assunta fra prezzo del grafico e prezzo usato per eseguire, 3 punti base per lato. È già nei prezzi d’ingresso e d’uscita:
              non viene sottratto una seconda volta.
            </Info>
          </p>
          <p className="metric-value">{usdt(tr.slippageCost)}</p>
          <p className="metric-sub">già nei prezzi usati</p>
        </div>
        <div className="metric">
          <p className="metric-label">Commissioni</p>
          <p className="metric-value">{usdt(fees)}</p>
          <p className="metric-sub">{tr.feeExit == null ? 'solo ingresso: chiusura non avvenuta' : 'ingresso e uscita, 5 punti base ciascuno'}</p>
        </div>
        <div className="metric">
          <p className="metric-label">
            Pagamento periodico del contratto
            <Info label="Pagamento periodico del contratto">
              Funding storico di Binance mentre la posizione era aperta: può essere pagato o ricevuto. Valorizzato con il prezzo mark del minuto precedente.
            </Info>
          </p>
          <p className="metric-value">{usdt(tr.funding.total)}</p>
          <p className="metric-sub">
            {counted.length} pagament{counted.length === 1 ? 'o' : 'i'}
            {tr.funding.ambiguous ? ' · orario ambiguo ai confini' : ''}
          </p>
        </div>
      </div>
      <p className="footnote">
        Movimento dei prezzi + effetto del prezzo di esecuzione − commissioni + pagamento periodico = risultato dopo i costi.{' '}
        {tr.durationMin != null ? `Durata ${formatNumber(tr.durationMin, 0)} minuti.` : `In posizione per ${formatNumber(tr.durationUntilGapMin ?? 0, 0)} minuti fino alla lacuna.`}{' '}
        Non include margine, leva, liquidazioni o un conto reale.
      </p>
      <div className="stress-box">
        <p className="metric-label">
          Con costi più alti: {usdt(tr.stress.net)}
          <Info label="Con costi più alti">
            Stessa operazione, stessi ingressi e uscite, ricalcolata con commissioni di 10 punti base e prezzo di esecuzione peggiore di 10 punti base per lato. Non è un
            altro percorso e non si somma al risultato.
          </Info>
        </p>
      </div>
      <details className="tech">
        <summary>Dettagli tecnici</summary>
        <p className="footnote">
          Netto {bps(tr.netBps)} di N0 ({formatNumber(tr.N0, 0)} USDT); PnL ai prezzi modellati {usdt(tr.pricePnL)}; rischio iniziale {plainUsdt(tr.riskInitial)}.
          {tr.targetFirst ? ` Alternativa «prima l’obiettivo» nello stesso minuto: ${usdt(tr.targetFirst.net)}.` : ''}
          {tr.netRange && tr.netRange[0] !== tr.netRange[1] ? ` Intervallo per ambiguità del funding: ${usdt(tr.netRange[0])} … ${usdt(tr.netRange[1])}.` : ''}
        </p>
      </details>
    </section>
  );
}

function LegView({ study, id, source, from }: { study: BacktestStudy; id: string; source: ResultSource; from: From }) {
  const leg = study.leg(id);
  if (!leg) {
    return (
      <main className="content">
        <BackRow source={source} from={from} />
        <Notice tone="negative" title="Episodio non trovato">
          Il riferimento {id} non è presente in questo risultato: nessun grafico o dato viene mostrato al suo posto.
        </Notice>
      </main>
    );
  }
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <BackRow source={source} from={from} />
      <section className="card table-card" aria-label="Movimento non riconosciuto">
        <div className="card-head">
          <p className="section-title">Movimento considerato il {fmtUtc(leg.t)}</p>
        </div>
        <Step title="Ha rinunciato" tone="warning">
          Movimento {leg.d === 1 ? 'al rialzo' : 'al ribasso'} da {px(leg.P0.price)} a {px(leg.P1.price)}: {ABSTAIN_TEXT[leg.outcome] ?? leg.outcome}.
        </Step>
      </section>
    </main>
  );
}
