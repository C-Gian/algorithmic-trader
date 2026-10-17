import { useState, type ReactNode } from 'react';
import type { BtEpisode, BtState, BtTrade } from '../../contract/backtest';
import type { BacktestStudy, PlanLevel } from '../../backtest/study';
import { formatNumber } from '../../lib/numbers';
import { CandleChart, type ChartCandle, type ChartLevel, type ChartMarker, type ChartOverlays } from '../components/CandleChart';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc, isoMinute } from '../format';
import { ABSTAIN_TEXT, EXIT_TEXT, bps, num, pct, plainUsdt, px, stateText, usdt } from './text';

const KEY_STATES = ['RECOGNIZED', 'WAIT_REACTION', 'WAIT_RESUMPTION', 'CALL', 'FILLED', 'PROTECTION_UPDATE', 'EXIT_STRUCTURE_REQUESTED', 'CLOSED'];
const iso = (ms: number) => new Date(ms).toISOString();

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

/** Momento della decisione: la call, oppure la conclusione (astensione), oppure il riconoscimento. */
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

export function EpisodeView({ study, id, initialCursor, onBack }: { study: BacktestStudy; id: string; initialCursor?: number; onBack: () => void }) {
  const ep = study.episode(id);
  if (!ep) return <LegView study={study} id={id} onBack={onBack} />;
  return <Episode study={study} ep={ep} initialCursor={initialCursor} onBack={onBack} />;
}

function Episode({ study, ep, initialCursor, onBack }: { study: BacktestStudy; ep: BtEpisode; initialCursor?: number; onBack: () => void }) {
  const tr = study.trade(ep.tradeId);
  const ms = moments(ep);
  const [cursor, setCursor] = useState<number>(initialCursor ?? decisionMoment(ep));
  const [retro, setRetro] = useState(false);
  const [scale, setScale] = useState<'45m' | '1D'>('45m');
  const [overlays, setOverlays] = useState<ChartOverlays>({ averages: true, levels: true, fibonacci: false, volume: true });
  const known = (t: number) => retro || t <= cursor;
  const statesNow = ep.states.filter((s) => s.t <= cursor);
  const lastWait = [...statesNow].reverse().find((s) => s.state === 'WAIT_REACTION' || s.state === 'WAIT_RESUMPTION');
  const terminated = ep.termination && ep.termination.t <= cursor ? ep.termination : null;
  const abstained = terminated && terminated.code !== 'CLOSED' ? terminated : null;
  const callKnown = ep.call && ep.call.t <= cursor ? ep.call : null;
  const entryKnown = tr && known(tr.entryTime) ? tr : null;
  const exit = tr?.exit ?? null;
  const exitKnown = exit && known(exit.accountingTime) ? exit : null;
  const gapKnown = tr?.gap && known(tr.gap.at) ? tr.gap : null;
  const snap = study.snapshotAt(ep.id, cursor);

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
  const side = ep.side === 'LONG' ? 'rialzo' : 'ribasso';
  const plan = ep.plan;

  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Episodio">
        <div className="card-head">
          <div>
            <p className="section-title">
              Episodio {ep.side} · movimento al {side} riconosciuto il {fmtUtc(ep.t0)}
            </p>
            <p className="card-sub mono">{ep.id}</p>
          </div>
          <div className="actions">
            <Badge tone={retro ? 'warning' : 'accent'}>{retro ? 'A POSTERIORI · seguito modellato visibile' : 'SOLO INFORMAZIONI AL MOMENTO'}</Badge>
            <Button onClick={onBack}>← Risultati</Button>
          </div>
        </div>
        <p className="t-2">Il programma ha già elaborato tutti gli episodi; qui consulti un momento. Momento consultato: <strong>{fmtUtc(cursor)}</strong>.</p>
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
              <Button onClick={() => setRetro(false)}>Solo informazioni al momento della decisione</Button>
            ) : (
              <Button variant="primary" onClick={() => setRetro(true)}>
                Mostra seguito modellato
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

        <section className="card card-call" aria-label="Che cosa ha deciso">
          <p className="call-kicker">CHE COSA HA FATTO IL PROGRAMMA</p>
          <Step title="Ha riconosciuto questo movimento" tone="accent">
            {ep.side === 'LONG' ? 'Salita' : 'Discesa'} da P0 {px(ep.P0.price)} (candela {isoMinute(ep.P0.candidateOpen)}) a P1 {px(ep.P1.price)} (candela{' '}
            {isoMinute(ep.P1.candidateOpen)}): ampiezza {num(ep.L)} USDT, almeno 3 volte la volatilità A0 = {num(ep.A0)} ({num(3 * ep.A0)}). Struttura 45m{' '}
            {ep.side === 'LONG' ? 'crescente' : 'decrescente'}. P1 è diventato noto solo alla chiusura delle {isoMinute(ep.P1.availableAt)}, due barre dopo la sua candela.
          </Step>
          {lastWait && (
            <Step title="Ha atteso questa reazione">
              Estremo della reazione {px(lastWait.Rext as number)}, profondità {pct(lastWait.depth as number, 0)} del movimento (ammessa fra 25% e 75%), chiusure contrarie{' '}
              {String(lastWait.counterCloses)}, barre dalla candela estrema {String(lastWait.barsSinceP1)} su un massimo di 12. Stato: {stateText(lastWait.state).toLowerCase()}.
            </Step>
          )}
          {callKnown && plan && (
            <Step title="Ha chiesto un ingresso a queste condizioni" tone="positive">
              Alla chiusura delle {isoMinute(callKnown.t)} la candela ha chiuso a {px(plan.Ck)},{' '}
              {ep.side === 'LONG' ? 'sopra il massimo della precedente e sopra la propria apertura' : 'sotto il minimo della precedente e sotto la propria apertura'}: tentativo
              di ripresa. Stop {px(callKnown.S0)} (estremo della reazione ± 0,10·A0), obiettivo {px(callKnown.T)} (ritorno a P1), ingresso stimato {px(callKnown.Estar)},
              rapporto spazio/rischio {num(plan.ratio)} (minimo 1,5). Tentativo unico all’apertura del minuto {isoMinute(callKnown.executeAt)}, solo se il prezzo modellato
              resta {ep.side === 'LONG' ? 'sotto' : 'sopra'} {px(callKnown.entryBound)}. Attesa: «{callKnown.expectation}» — non è una probabilità.
            </Step>
          )}
          {abstained && (
            <Step title="Si è astenuto" tone="warning">
              Alle {isoMinute(abstained.t)}: {ABSTAIN_TEXT[abstained.code] ?? abstained.code}.
              {abstained.code === 'ABSTAIN_REWARD_RISK' && plan && ` Rapporto calcolato ${num(plan.ratio)} con stop ${px(plan.S0)} e obiettivo ${px(plan.T)}.`}
            </Step>
          )}
          {entryKnown && (
            <Step title="Ingresso modellato" tone="accent">
              Alle {isoMinute(entryKnown.entryTime)} all’apertura {px(entryKnown.Eref)} più slippage assunto: {px(entryKnown.E)}. Quantità {formatNumber(entryKnown.q, 5)} BTC per{' '}
              {formatNumber(entryKnown.N0, 0)} USDT di nozionale. Rischio iniziale fino allo stop {plainUsdt(entryKnown.q * entryKnown.R0)}.
            </Step>
          )}
          {tr && tr.stops.filter((s) => known(s.effectiveAt)).map((s) => (
            <Step key={s.effectiveAt} title="Ha alzato la protezione">
              Nuovo pivot a {px(s.pivot)} confermato dopo l’ingresso: stop da {px(s.from)} a {px(s.to)}, deciso alle {isoMinute(s.decidedAt)}, efficace alle{' '}
              {isoMinute(s.effectiveAt)}. Lo stop non viene mai allargato.
            </Step>
          ))}
          {exitKnown && tr && (
            <Step title="Uscita modellata" tone={tr.net != null && tr.net < 0 ? 'negative' : 'positive'}>
              Per {EXIT_TEXT[exitKnown.reason]} alle {isoMinute(exitKnown.minute)}: riferimento {px(exitKnown.Xref)}, prezzo modellato {px(exitKnown.X)}
              {exitKnown.gap ? ' (apertura già oltre il livello)' : ''}
              {exitKnown.bothTouched ? ' · stop e target toccati nello stesso minuto: si assume prima lo stop' : ''}.
            </Step>
          )}
          {gapKnown && (
            <Step title="Percorso irrisolto" tone="warning">
              Alle {isoMinute(gapKnown.at)} manca il minuto negoziato mentre la posizione era aperta: stop o target potrebbero essere stati toccati senza che si
              possa saperlo. La valutazione della finestra si interrompe qui; nessuna uscita, prezzo o risultato viene inventato.
            </Step>
          )}
          {!retro && tr && !exitKnown && !gapKnown && (
            <Notice tone="neutral" title="Seguito non mostrato">
              Ingresso, gestione, uscita e costi successivi al momento consultato si vedono con «Mostra seguito modellato».
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
      <p className="lt-head">Contesto noto alle {isoMinute(snap.t)} (le famiglie contestuali non decidono)</p>
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
  return (
    <section className="card card-position retro-card" aria-label="Risultato modellato dell'operazione">
      <div className="card-head">
        <p className="section-title">Risultato modellato dell’operazione</p>
        <Badge tone="warning">{tr.exit ? 'A POSTERIORI' : 'A POSTERIORI · PERCORSO IRRISOLTO'}</Badge>
      </div>
      {!tr.exit && (
        <Notice tone="warning" title="Risultato non disponibile">
          Lacuna nei dati alle {tr.gap ? isoMinute(tr.gap.at) : '—'} con posizione aperta: uscita, PnL e netto restano mancanti. Sono mostrati solo i fatti noti
          fino alla lacuna (ingresso, fee d’ingresso, funding valutabile).
        </Notice>
      )}
      <div className="metrics">
        <div className="metric"><p className="metric-label">Netto modellato</p><p className={`metric-value ${tr.net != null && tr.net < 0 ? 't-neg' : 't-pos'}`}>{usdt(tr.net)}</p><p className="metric-sub">{bps(tr.netBps)} di N0</p></div>
        <div className="metric"><p className="metric-label">PnL ai prezzi di riferimento</p><p className="metric-value">{usdt(tr.pricePnLRef)}</p><p className="metric-sub">senza slippage</p></div>
        <div className="metric"><p className="metric-label">Slippage assunto</p><p className="metric-value">{usdt(tr.slippageCost)}</p><p className="metric-sub">3 bp per lato, già nei prezzi</p></div>
        <div className="metric"><p className="metric-label">Fee assunte</p><p className="metric-value">{usdt(tr.feeExit == null ? -tr.feeEntry : -(tr.feeEntry + tr.feeExit))}</p><p className="metric-sub">{tr.feeExit == null ? 'solo ingresso: uscita non avvenuta' : '5 bp per lato'}</p></div>
        <div className="metric"><p className="metric-label">Funding storico</p><p className="metric-value">{usdt(tr.funding.total)}</p><p className="metric-sub">{counted.length} eventi · mark 1m{tr.funding.ambiguous ? ' · ambiguo ai confini' : ''}</p></div>
        <div className="metric"><p className="metric-label">Netto con costi di stress</p><p className="metric-value">{usdt(tr.stress.net)}</p><p className="metric-sub">10 bp fee + 10 bp slippage, stesso percorso</p></div>
      </div>
      <p className="footnote">
        {tr.durationMin != null ? `Durata ${formatNumber(tr.durationMin, 0)} minuti.` : `In posizione per ${formatNumber(tr.durationUntilGapMin ?? 0, 0)} minuti fino alla lacuna.`} Netto = PnL ai prezzi modellati − fee + funding. Non include margine, leva, liquidazioni o un conto reale.
        {tr.targetFirst ? ` Alternativa target-first nello stesso minuto: ${usdt(tr.targetFirst.net)}.` : ''}
        {tr.netRange && tr.netRange[0] !== tr.netRange[1] ? ` Intervallo per ambiguità del funding: ${usdt(tr.netRange[0])} … ${usdt(tr.netRange[1])}.` : ''}
      </p>
    </section>
  );
}

function LegView({ study, id, onBack }: { study: BacktestStudy; id: string; onBack: () => void }) {
  const leg = study.leg(id);
  if (!leg) {
    return (
      <main className="content">
        <Notice tone="negative" title="Episodio non trovato">Il riferimento {id} non è presente nel backtest aperto.</Notice>
        <Button onClick={onBack}>← Risultati</Button>
      </main>
    );
  }
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Movimento non riconosciuto">
        <div className="card-head">
          <p className="section-title">Movimento considerato il {fmtUtc(leg.t)}</p>
          <Button onClick={onBack}>← Risultati</Button>
        </div>
        <Step title="Si è astenuto" tone="warning">
          Movimento {leg.d === 1 ? 'al rialzo' : 'al ribasso'} da {px(leg.P0.price)} a {px(leg.P1.price)}: {ABSTAIN_TEXT[leg.outcome] ?? leg.outcome}.
        </Step>
      </section>
    </main>
  );
}
