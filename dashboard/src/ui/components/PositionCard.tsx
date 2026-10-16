import type { ReactNode } from 'react';
import { formatBtc, formatNumber, formatSigned } from '../../lib/numbers';
import { fmtHm, fmtTime, tzAbbr } from '../format';
import { useDashboard } from '../useDashboard';
import { Badge, Button, Notice } from './primitives';

const PARTIAL_NOTE =
  'Uscita parziale: riduce 0,00400 BTC (quantità predeterminata dello scenario). Stop e target si adeguano alla quantità residua; la commissione d’uscita è conteggiata solo all’esecuzione.';

function Metric({ label, value, sub, tone, missing }: { label: string; value: ReactNode; sub: ReactNode; tone?: string; missing?: boolean }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className={`metric-value${missing ? ' is-missing' : ''}${tone ? ` ${tone}` : ''}`}>{value}</p>
      <p className="metric-sub">{sub}</p>
    </div>
  );
}

export function PositionCard() {
  const { snapshot, request } = useDashboard();
  const { position, account, orders, fills, actions, context } = snapshot;
  const pendingExit = orders.find((o) => o.purpose === 'EXIT' && o.status === 'REQUESTED');
  const exits = fills.filter((f) => orders.find((o) => o.id === f.orderId)?.purpose !== 'ENTRY');
  const feedOk = context.feed.status === 'OK';

  const header = (
    <div className="card-head" style={{ flexWrap: 'wrap' }}>
      <div className="pos-identity">
        <p className="section-title">La tua posizione</p>
        {position ? (
          <>
            <Badge tone={position.side === 'LONG' ? 'positive' : 'negative'}>{position.side === 'LONG' ? '↗' : '↘'} {position.side} · APERTA</Badge>
            {position.management === 'BOT' ? (
              context.bot.status !== 'RUNNING' ? (
                <Badge tone="warning">Gestione automatica sospesa · bot fermo</Badge>
              ) : feedOk ? (
                <Badge tone="accent" icon="bot13Blue">
                  Gestione automatica
                </Badge>
              ) : (
                <Badge tone="warning">
                  Gestione automatica sospesa · {context.feed.status === 'STALE' ? 'feed non aggiornato' : 'feed disconnesso'}
                </Badge>
              )
            ) : (
              <Badge tone="accent">Gestione manuale</Badge>
            )}
          </>
        ) : (
          <Badge tone="neutral">Nessuna posizione</Badge>
        )}
      </div>
      <p className="t-2" style={{ fontSize: 12 }}>
        {position ? '1 / 1 posizione BTC' : '0 / 1 posizione BTC'} · {context.instrument.productLabel} · margine e leva non modellati
      </p>
    </div>
  );

  const actionButtons = (
    <div className="actions">
      {position?.management === 'MANUAL' ? (
        <Button
          variant="primary"
          icon="bot16Dark"
          disabled={!actions.RESUME_AUTOMATIC.enabled}
          reason={actions.RESUME_AUTOMATIC.reason}
          onClick={() => request('RESUME_AUTOMATIC')}
        >
          Riprendi automatico
        </Button>
      ) : (
        <Button icon="hand16" disabled={!actions.TAKE_MANUAL.enabled} reason={actions.TAKE_MANUAL.reason} onClick={() => request('TAKE_MANUAL')}>
          Gestione manuale
        </Button>
      )}
      <Button disabled={!actions.PARTIAL_EXIT.enabled} reason={actions.PARTIAL_EXIT.reason} onClick={() => request('PARTIAL_EXIT')}>
        Uscita parziale
      </Button>
      <Button variant="danger" icon="x16Red" disabled={!actions.CLOSE_POSITION.enabled} reason={actions.CLOSE_POSITION.reason} onClick={() => request('CLOSE_POSITION')}>
        Chiudi posizione
      </Button>
    </div>
  );

  if (!position) {
    const lastExit = exits[exits.length - 1];
    return (
      <section className="card card-position" aria-label="Posizione">
        {header}
        <div className="metrics">
          <Metric label="Quantità in posizione" value={formatBtc(0)} sub={lastExit ? 'Nessuna esposizione residua' : 'Nessun eseguito ha aperto esposizione'} />
          <Metric label="Ingresso eseguito" value="Non applicabile" missing sub="Nessun ingresso eseguito" />
          <Metric label="Stop attuale" value="Non applicabile" missing sub="Le protezioni si attivano solo dopo l’ingresso" />
          <Metric label="Target" value="Non applicabile" missing sub="Le protezioni si attivano solo dopo l’ingresso" />
          <Metric label="Risultato aperto lordo" value="Non applicabile" missing sub="Nessuna posizione da valutare" />
        </div>
        <div className="sep" />
        <div className="pos-bottom">
          <div className="pos-costs">
            <p>
              {lastExit
                ? `Ultima uscita alle ${fmtHm(lastExit.at)} ${tzAbbr(lastExit.at)} · realizzato netto ${formatSigned(account.realizedNet.amount, 3)} USDT (dettagli nel conto).`
                : 'Nessuna operazione aperta. Una call senza ordine non occupa capitale.'}
            </p>
            <p>Chiusura e uscita parziale sono disponibili solo con una posizione aperta.</p>
          </div>
          {actionButtons}
        </div>
      </section>
    );
  }

  const stop = position.protections.find((p) => p.kind === 'STOP');
  const target = position.protections.find((p) => p.kind === 'TARGET');
  const avg = position.avgEntryPrice.amount;
  const unrealized = account.unrealizedGross.value?.amount ?? null;
  const lastKnown = account.lastKnownUnrealizedGross;
  const valuationPrice = position.valuation.value?.price.amount;
  const notional = position.qty.amount * avg;
  const entryFee = fills.find((f) => orders.find((o) => o.id === f.orderId)?.purpose === 'ENTRY')?.fee.amount ?? 0;
  const protSub = (fresh: string | undefined, kind: string) =>
    fresh === 'LAST_KNOWN' ? `USDT · ultimo noto, non verificato` : `USDT · ${kind} simulato attivo`;

  return (
    <section className="card card-position" aria-label="Posizione">
      {header}
      <div className="metrics">
        <Metric
          label="Quantità in posizione"
          value={formatBtc(position.qty.amount)}
          sub={`Aperta alle ${fmtHm(position.openedAt)} ${tzAbbr(position.openedAt)}${feedOk ? '' : ` · ultima nota alle ${fmtTime(context.feed.observedAt)}`}`}
        />
        <Metric label="Ingresso eseguito" value={formatNumber(avg, 2)} sub={`USDT / BTC · valore ${formatNumber(notional, 2)} USDT`} />
        <Metric
          label="Stop attuale"
          value={stop ? formatNumber(stop.price.amount, 2) : 'Nessuno'}
          missing={!stop}
          tone="t-warn"
          sub={stop ? protSub(stop.freshness, 'ordine protettivo') : 'Nessuna protezione attiva'}
        />
        <Metric
          label="Target"
          value={target ? formatNumber(target.price.amount, 2) : 'Nessuno'}
          missing={!target}
          sub={target ? protSub(target.freshness, 'ordine limite') : 'Nessun target attivo'}
        />
        {unrealized !== null ? (
          <Metric
            label="Risultato aperto lordo"
            value={`${formatSigned(unrealized, 2)} USDT`}
            tone={unrealized >= 0 ? 't-pos' : 't-neg'}
            sub={`${formatSigned((unrealized / notional) * 100, 2)}% · prima dei costi · valutazione ${formatNumber(valuationPrice ?? 0, 0)}`}
          />
        ) : (
          <Metric
            label="Risultato aperto lordo"
            value="Non disponibile"
            missing
            sub={lastKnown ? `Ultimo noto ${formatSigned(lastKnown.value.amount, 2)} USDT alle ${fmtTime(lastKnown.at)} · non aggiornato` : 'Valutazione non disponibile'}
          />
        )}
      </div>

      {pendingExit && (
        <div className="actions" style={{ alignItems: 'center' }}>
          <div style={{ flex: '1 1 320px' }}>
            <Notice
              tone={feedOk ? 'accent' : 'warning'}
              icon={feedOk ? 'clock17Blue' : 'triangleAlert17'}
              title={`Uscita richiesta · ${pendingExit.side} ${formatBtc(pendingExit.requestedQty.amount)} alle ${fmtTime(pendingExit.createdAt)}`}
            >
              {feedOk
                ? 'Richiesta simulata inviata: in attesa dell’eseguito. Nessun risultato è ancora realizzato.'
                : 'Feed simulato non aggiornato: la richiesta resta in attesa di conferma. Nessuna chiusura viene presunta.'}
            </Notice>
          </div>
          <Button onClick={() => request('CANCEL_EXIT_REQUEST')}>Ritira richiesta</Button>
        </div>
      )}

      <div className="sep" />
      <div className="pos-bottom">
        <div className="pos-costs">
          <p>
            Realizzato lordo: {formatSigned(account.realizedGross.amount, 2)} USDT ·{' '}
            {exits.length === 0 ? 'Nessuna uscita eseguita' : `${exits.length} ${exits.length === 1 ? 'uscita eseguita' : 'uscite eseguite'}`} · Commissione ingresso:{' '}
            {formatNumber(entryFee, 2)} USDT · Costi addebitati: {formatNumber(account.feesCharged.amount, 3)} USDT
          </p>
          <p>Sono consentite solo riduzioni. Nessun aumento di quantità · Funding non applicato in questo esempio · Costi d’uscita non inclusi nel risultato aperto.</p>
        </div>
        {actionButtons}
      </div>
      <p className="footnote">{PARTIAL_NOTE}</p>
    </section>
  );
}
