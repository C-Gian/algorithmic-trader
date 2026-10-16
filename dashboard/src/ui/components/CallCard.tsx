import type { Call, CallStatus, Tone } from '../../contract/types';
import { formatBtc, formatPrice } from '../../lib/numbers';
import { fmtDate, fmtHm, fmtTime, tzAbbr } from '../format';
import type { IconName } from '../icons';
import { useDashboard } from '../useDashboard';
import { Badge, Button, Icon, IconSlot, Notice } from './primitives';

const STATUS: Record<CallStatus, { text: string; tone: Tone; icon?: IconName }> = {
  PROPOSED: { text: 'Proposta', tone: 'accent' },
  AVAILABLE: { text: 'Disponibile', tone: 'accent' },
  ACTIVE: { text: 'Call attiva', tone: 'positive', icon: 'circleDot' },
  EXPIRED: { text: 'Scaduta', tone: 'neutral' },
  WITHDRAWN: { text: 'Ritirata', tone: 'neutral' },
  COMPLETED: { text: 'Call conclusa', tone: 'neutral' },
};

const EXPECTATION_LABEL = { UP: 'rialzo plausibile', DOWN: 'ribasso plausibile', UNCERTAIN: 'direzione incerta' } as const;

function dayLabel(iso: string, nowIso: string) {
  return fmtDate(iso) === fmtDate(nowIso) ? 'Oggi' : fmtDate(iso);
}

export function CallCard() {
  const { snapshot } = useDashboard();
  const { call } = snapshot;
  return <section className="card card-call" aria-label="Call attuale">{call ? <CallBody call={call} /> : <Waiting />}</section>;
}

function Waiting() {
  const { snapshot } = useDashboard();
  const e = snapshot.expectation;
  const now = snapshot.context.clock.now;
  return (
    <>
      <div className="card-head">
        <p className="call-kicker">NESSUNA CALL OPERATIVA</p>
        <Badge tone="warning">Nessuna call</Badge>
      </div>
      <div className="direction">
        <IconSlot name="pause24" size={28} />
        <p className="direction-word t-warn">ATTESA</p>
        <p className="direction-sub">{e ? `Aspettativa: ${EXPECTATION_LABEL[e.direction]}` : 'Aspettativa non disponibile'}</p>
      </div>
      {e ? (
        <>
          <p className="call-rationale">{e.description}</p>
          {e.alternatives.length > 0 && (
            <div>
              <p className="h-label">Alternative considerate</p>
              <ul className="expect-list">
                {e.alternatives.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          )}
          {e.contraindications.length > 0 && (
            <Notice tone="warning" icon="triangleAlert17" title="Controindicazione">
              {e.contraindications.join(' ')}
            </Notice>
          )}
        </>
      ) : (
        <p className="call-expl">Nessuna aspettativa registrata in questo momento della simulazione.</p>
      )}
      <div className="levels-table">
        <div className="lt-row">
          <span className="lt-label">Posizione BTC</span>
          <span className="lt-val" style={{ width: 'auto', flex: 'none' }}>
            {snapshot.position ? formatBtc(snapshot.position.qty.amount) : 'Nessuna'}
          </span>
        </div>
        <div className="lt-row">
          <span className="lt-label">Ingresso / stop / target</span>
          <span className="t-2" style={{ width: 'auto', flex: 'none', fontSize: 12 }}>
            Non definiti: nessun piano valido
          </span>
        </div>
      </div>
      <div className="sep" />
      <div className="update-box">
        <Icon name="clock17Grey" />
        <p>{e ? `${fmtHm(e.updatedAt)} · Aspettativa aggiornata. Nessun ordine inviato.` : 'Nessun aggiornamento.'}</p>
      </div>
      <p className="footnote">
        Un’aspettativa non è una call: il bot non apre una posizione per riempire il tempo. Orario {fmtTime(now)} {tzAbbr(now)}.
      </p>
      <Button icon="chartNoAxes" onClick={() => document.getElementById('segnali')?.scrollIntoView({ behavior: 'smooth' })}>
        Vedi segnali
      </Button>
    </>
  );
}

function CallBody({ call }: { call: Call }) {
  const { snapshot, request } = useDashboard();
  const { plan, orders, fills, position, actions, context } = snapshot;
  const now = context.clock.now;
  const status = STATUS[call.status];
  const long = call.direction === 'LONG';
  const entryOrder = [...orders].reverse().find((o) => o.purpose === 'ENTRY');
  const entryFill = entryOrder ? fills.find((f) => f.orderId === entryOrder.id) : undefined;
  const lastChange = plan?.changes[plan.changes.length - 1];

  const kicker = call.status === 'COMPLETED' ? 'CALL CONCLUSA' : call.status === 'ACTIVE' ? 'CALL ATTUALE' : 'CALL PROPOSTA';
  const directionIcon: IconName = call.status === 'COMPLETED' ? 'circleCheck24' : long ? 'trendingUp28' : 'trendingDown24';

  return (
    <>
      <div className="card-head">
        <p className="call-kicker">
          {kicker} · {call.displayId}
        </p>
        <Badge tone={status.tone} icon={status.icon}>
          {status.text}
        </Badge>
      </div>

      <div className="direction">
        <IconSlot name={directionIcon} size={28} />
        <p className={`direction-word ${long ? 't-pos' : 't-neg'}`}>{call.direction}</p>
        <p className="direction-sub">
          {long ? 'Acquisto · rialzo' : 'Vendita · ribasso'}
          {position ? ` · posizione ${position.side} aperta (vedi sotto)` : ' · nessuna posizione'}
        </p>
      </div>

      <p className="call-rationale">{call.rationale}</p>
      <p className="call-expl">{call.explanation}</p>

      <Notice tone="warning" icon="triangleAlert17" title={call.contraindication.title}>
        {call.contraindication.text}
      </Notice>

      {entryOrder?.status === 'REJECTED' && (
        <Notice tone="negative" icon="circleAlert17Red" title={`${entryOrder.rejection?.code ?? 'SIM'} · Ordine d’ingresso rifiutato`}>
          {entryOrder.rejection?.message}. Rifiutato alle {fmtTime(entryOrder.updatedAt)}: nessun eseguito, nessuna commissione, nessun reinvio automatico.
        </Notice>
      )}
      {entryOrder && (entryOrder.status === 'ACCEPTED' || entryOrder.status === 'REQUESTED') && (
        <>
          <Notice tone="accent" icon="clock17Blue" title="Ordine d’ingresso in attesa · nessuna posizione">
            {entryOrder.side} {formatBtc(entryOrder.requestedQty.amount)} limite {formatPrice(entryOrder.limitPrice?.amount ?? 0)} USDT, accettato alle{' '}
            {fmtTime(entryOrder.createdAt)}. Accettato non significa eseguito: P&L e commissioni non applicabili.
          </Notice>
          <div className="actions">
            <Button disabled={!actions.CANCEL_ENTRY_ORDER.enabled} reason={actions.CANCEL_ENTRY_ORDER.reason} onClick={() => request('CANCEL_ENTRY_ORDER')}>
              Annulla ordine
            </Button>
          </div>
        </>
      )}
      {call.status === 'PROPOSED' && (
        <Notice tone="accent" icon="info17" title="Proposta senza ordine">
          {context.mode === 'CALL_ONLY' ? 'Modalità “Solo call”: è una lettura di mercato, nessun ordine simulato verrà inviato.' : 'Nessun ordine inviato.'}
        </Notice>
      )}

      {plan && (
        <div className="levels-table">
          <div className="lt-row lt-head">
            <span>LIVELLI · USDT</span>
            <span>ORIGINALI · {fmtHm(plan.original.setAt)}</span>
            <span>
              {call.status === 'COMPLETED' ? 'ULTIMI' : 'ATTUALI'} · {fmtHm(plan.current.setAt)}
            </span>
          </div>
          <div className="lt-row">
            <span className="lt-label">Fascia ingresso</span>
            <span className="lt-val t-2">
              {formatPrice(plan.original.entryZone.low.amount)}–{formatPrice(plan.original.entryZone.high.amount)}
            </span>
            <span className="lt-val">
              {entryFill
                ? `Eseguito ${formatPrice(entryFill.price.amount)}`
                : `${formatPrice(plan.current.entryZone.low.amount)}–${formatPrice(plan.current.entryZone.high.amount)}`}
            </span>
          </div>
          <div className="lt-row">
            <span className="lt-label">Stop</span>
            <span className="lt-val t-2">{formatPrice(plan.original.stop.amount)}</span>
            <span className={`lt-val${lastChange ? ' t-warn' : ''}`}>
              {formatPrice(plan.current.stop.amount)}
              {lastChange ? (plan.current.stop.amount > plan.original.stop.amount ? ' ↑' : ' ↓') : ''}
            </span>
          </div>
          {plan.original.targets.map((t, i) => (
            <div className="lt-row" key={i}>
              <span className="lt-label">Target{plan.original.targets.length > 1 ? ` ${i + 1}` : ''}</span>
              <span className="lt-val t-2">{formatPrice(t.amount)}</span>
              <span className="lt-val">{formatPrice(plan.current.targets[i]?.amount ?? t.amount)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="sep" />
      <div className="horizon">
        <div>
          <p className="h-label">Durata prevista</p>
          <p className="h-value">{call.expectedDuration}</p>
        </div>
        <div>
          <p className="h-label">Scadenza del piano</p>
          <p className="h-value">{plan ? `${dayLabel(plan.expiresAt, now)} · ${fmtHm(plan.expiresAt)} ${tzAbbr(plan.expiresAt)}` : '—'}</p>
        </div>
      </div>

      <div className="update-box">
        <Icon name="history16Blue" />
        <p>
          {lastChange
            ? `${fmtHm(lastChange.at)} · Stop da ${formatPrice(lastChange.before.amount)} a ${formatPrice(lastChange.after.amount)}: ${lastChange.reason}`
            : `${fmtHm(call.createdAt)} · Piano originale (v${plan?.version ?? 1}), nessuna modifica.`}
        </p>
      </div>

      <p className="footnote">
        {call.validity.note} Ingresso valido fino alle {fmtHm(call.validity.entryUntil)} {tzAbbr(call.validity.entryUntil)}.
      </p>
    </>
  );
}
