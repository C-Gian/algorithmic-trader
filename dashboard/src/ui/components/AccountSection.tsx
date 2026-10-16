import type { Order, Tone } from '../../contract/types';
import { formatNumber, formatPrice, formatSigned } from '../../lib/numbers';
import { fmtHm, fmtTime } from '../format';
import { useDashboard } from '../useDashboard';
import { Badge, Icon } from './primitives';

/** Due decimali, tre quando servono a non nascondere i millesimi di fixture. */
const money = (x: number) => formatNumber(x, Math.round(x * 100) === Math.round(x * 1000) / 10 ? 2 : 3);
const signedMoney = (x: number) => formatSigned(x, Math.round(x * 100) === Math.round(x * 1000) / 10 ? 2 : 3);

function orderType(o: Order): string {
  const side = o.side === 'BUY' ? 'acquisto' : 'vendita';
  if (o.purpose === 'ENTRY') return `Ingresso · ${side}`;
  if (o.purpose === 'EXIT') return `Uscita · ${side}`;
  return `${o.protectionKind === 'TARGET' ? 'Target' : 'Stop'} · ${side}`;
}

function orderStatus(o: Order): { text: string; tone: Tone } {
  const stale = o.freshness === 'LAST_KNOWN' ? ' · ultimo noto' : '';
  switch (o.status) {
    case 'ACCEPTED':
      if (o.purpose === 'PROTECTION') return { text: `${o.protectionKind === 'TARGET' ? 'Limite in attesa' : 'In attesa del trigger'}${stale}`, tone: 'accent' };
      return { text: `Accettato · non eseguito${stale}`, tone: 'accent' };
    case 'REQUESTED':
      return { text: `Richiesto · in attesa dell’eseguito${stale}`, tone: 'warning' };
    case 'PARTIALLY_FILLED':
      return { text: 'Eseguito in parte', tone: 'warning' };
    case 'FILLED':
      return { text: 'Eseguito', tone: 'positive' };
    case 'CANCELLED':
      return { text: 'Annullato', tone: 'neutral' };
    case 'REJECTED':
      return { text: `Rifiutato · ${o.rejection?.code ?? ''}`, tone: 'negative' };
  }
}

const TONE_CLASS: Record<Tone, string> = { accent: 't-accent', positive: 't-pos', warning: 't-warn', negative: 't-neg', neutral: 't-3' };

export function AccountSection() {
  const { snapshot } = useDashboard();
  const { account, orders, history, context } = snapshot;
  const now = context.clock.now;
  const equity = account.equity.value?.amount ?? null;
  const unrealized = account.unrealizedGross.value?.amount ?? null;
  const activeProtections = orders.filter((o) => o.purpose === 'PROTECTION' && o.status === 'ACCEPTED').length;
  const legs = account.realizedLegs;

  return (
    <>
      <section className="section" id="conto" aria-label="Conto simulato">
        <div className="section-head">
          <div>
            <p className="section-title">Il conto, senza sorprese</p>
            <p className="section-desc">
              Conto simulato in USDT · {context.instrument.productLabel} · Saldo iniziale {money(account.initialBalance.amount)} USDT · Valori alle{' '}
              {fmtTime(context.feed.observedAt)}
            </p>
          </div>
          <a className="link" href="#storico">
            Storico ↗
          </a>
        </div>

        <div className="card account-summary">
          <div className="metrics" style={{ gap: 28 }}>
            <div className="metric">
              <p className="metric-label">Saldo contabile simulato</p>
              <p className="metric-value big">{money(account.balance.amount)}</p>
              <p className="metric-sub">USDT · iniziale + realizzato lordo − costi</p>
            </div>
            <div className="metric">
              <p className="metric-label">Equity simulata</p>
              {equity !== null ? (
                <p className="metric-value big">{money(equity)}</p>
              ) : (
                <p className="metric-value big is-missing">Non disponibile</p>
              )}
              <p className="metric-sub">
                {equity !== null
                  ? 'USDT · saldo + non realizzato lordo'
                  : account.lastKnownEquity
                    ? `Ultima nota ${money(account.lastKnownEquity.value.amount)} alle ${fmtTime(account.lastKnownEquity.at)}`
                    : 'Valutazione non corrente'}
              </p>
            </div>
            <div className="metric">
              <p className="metric-label">Realizzato netto</p>
              <p className={`metric-value big ${account.realizedNet.amount > 0 ? 't-pos' : account.realizedNet.amount < 0 ? 't-neg' : ''}`}>
                {signedMoney(account.realizedNet.amount)}
              </p>
              <p className="metric-sub">
                USDT · lordo {signedMoney(account.realizedGross.amount)} − costi {money(account.feesCharged.amount)}
              </p>
            </div>
            <div className="metric">
              <p className="metric-label">Costi addebitati</p>
              <p className="metric-value big">{money(account.feesCharged.amount)}</p>
              <p className="metric-sub">USDT · commissioni di fixture sugli eseguiti</p>
            </div>
            <div className="metric">
              <p className="metric-label">Funding</p>
              <p className="metric-value">Non applicato</p>
              <p className="metric-sub">Esempio breve · nessun funding simulato</p>
            </div>
          </div>
          <div className="sep" />
          <p className="t-2" style={{ fontSize: 12 }}>
            {equity !== null && unrealized !== null
              ? `Equity = saldo ${money(account.balance.amount)} + non realizzato lordo ${signedMoney(unrealized)} = ${money(equity)} USDT. `
              : `Equity e non realizzato non disponibili: valutazione non corrente${
                  account.lastKnownUnrealizedGross
                    ? ` (ultimo non realizzato noto ${signedMoney(account.lastKnownUnrealizedGross.value.amount)} alle ${fmtTime(account.lastKnownUnrealizedGross.at)})`
                    : ''
                }. `}
            Saldo = {money(account.initialBalance.amount)} iniziale {signedMoney(account.realizedGross.amount)} realizzato lordo − {money(account.feesCharged.amount)}{' '}
            costi. Costi d’uscita non inclusi nel non realizzato. Margine e disponibile: non simulati.
          </p>
        </div>
      </section>

      <div className="account-row" id="storico">
        <div className="col-left">
          <div className="card table-card">
            <div className="card-head">
              <p className="table-title">Ordini simulati</p>
              {context.feed.status === 'OK' ? (
                <Badge tone="accent">
                  {activeProtections} {activeProtections === 1 ? 'protezione attiva' : 'protezioni attive'} · simulate
                </Badge>
              ) : (
                <Badge tone="warning">
                  {activeProtections} {activeProtections === 1 ? 'protezione' : 'protezioni'} · ultime note, non verificabili ora
                </Badge>
              )}
            </div>
            {orders.length === 0 ? (
              <p className="empty">Nessun ordine simulato in questo momento.</p>
            ) : (
              <>
                <div className="trow head">
                  <span style={{ width: 164 }}>TIPO / LATO</span>
                  <span style={{ width: 140 }}>BTC RICHIESTI / ESEGUITI</span>
                  <span style={{ width: 120 }}>PREZZO USDT</span>
                  <span style={{ flex: 1 }}>STATO</span>
                </div>
                {[...orders].reverse().map((o) => {
                  const st = orderStatus(o);
                  const price = o.limitPrice?.amount ?? o.triggerPrice?.amount ?? null;
                  return (
                    <div className="trow" key={o.id}>
                      <span style={{ width: 164 }}>{orderType(o)}</span>
                      <span className="mono" style={{ width: 140 }}>
                        {formatNumber(o.requestedQty.amount, 5)} / {formatNumber(o.filledQty.amount, 5)}
                      </span>
                      <span className="mono" style={{ width: 120 }}>
                        {price !== null ? formatNumber(price, 2) : 'a mercato'}
                      </span>
                      <span className={TONE_CLASS[st.tone]} style={{ flex: 1 }}>
                        {st.text} · {fmtHm(o.updatedAt)}
                      </span>
                    </div>
                  );
                })}
              </>
            )}
            <p className="t-2" style={{ fontSize: 11 }}>
              Accettato non significa eseguito: le quantità eseguite derivano solo dagli eseguiti simulati. Protezioni collegate: un’uscita annulla
              l’altra; quantità mai superiore al residuo.
            </p>
          </div>

          <div className="card table-card">
            <div className="card-head">
              <p className="table-title">Operazioni concluse</p>
              <span className="t-3" style={{ fontSize: 12 }}>
                Contribuiscono ai totali del conto
              </span>
            </div>
            {legs.length === 0 ? (
              <p className="empty">Nessuna uscita eseguita in questa simulazione. Le operazioni d’esempio del mockup non sono riportate: non hanno eseguiti nel conto simulato.</p>
            ) : (
              <>
                <div className="trow head" style={{ fontSize: 10 }}>
                  <span style={{ width: 62 }}>ORA</span>
                  <span style={{ width: 86 }}>BTC</span>
                  <span style={{ width: 190 }}>INGRESSO → USCITA</span>
                  <span style={{ width: 100 }}>LORDO USDT</span>
                  <span style={{ width: 100 }}>COSTO USCITA</span>
                  <span style={{ flex: 1 }}>NETTO USCITA</span>
                </div>
                {legs.map((l) => {
                  const net = l.gross.amount - l.exitFee.amount;
                  return (
                    <div className="trow" key={l.fillId} style={{ padding: '4px 0' }}>
                      <span className="t-2" style={{ width: 62 }}>
                        {fmtHm(l.at)}
                      </span>
                      <span className="mono t-2" style={{ width: 86 }}>
                        {formatNumber(l.qty.amount, 5)}
                      </span>
                      <span className="mono t-2" style={{ width: 190 }}>
                        {l.direction} {formatPrice(l.entryPrice.amount)} → {formatPrice(l.exitPrice.amount)}
                      </span>
                      <span className="mono t-2" style={{ width: 100 }}>
                        {signedMoney(l.gross.amount)}
                      </span>
                      <span className="mono t-2" style={{ width: 100 }}>
                        {money(l.exitFee.amount)}
                      </span>
                      <span className={`mono ${net >= 0 ? 't-pos' : 't-neg'}`} style={{ flex: 1 }}>
                        {signedMoney(net)}
                      </span>
                    </div>
                  );
                })}
              </>
            )}
            <div className="sep" />
            <p className="t-2" style={{ fontSize: 11 }}>
              Commissioni d’ingresso addebitate all’apertura: {money(account.entryFeesCharged.amount)} USDT. Totale realizzato: lordo{' '}
              {signedMoney(account.realizedGross.amount)} − costi {money(account.feesCharged.amount)} = netto {signedMoney(account.realizedNet.amount)} USDT.
            </p>
          </div>
        </div>

        <div className="col-right">
          <div className="card timeline">
            <div className="card-head">
              <p className="table-title">Timeline e notifiche</p>
              <Badge tone="accent">SIMULATE</Badge>
            </div>
            <div className="tl-list">
              {history.length === 0 && <p className="empty">Nessun evento registrato.</p>}
              {[...history].reverse().map((h) => (
                <div className="tl-event" key={h.id}>
                  <div className="tl-time">
                    <p>{fmtHm(h.at)}</p>
                    <p style={{ fontSize: 10, fontFamily: 'var(--font)' }}>{h.origin === 'OWNER' ? 'Owner' : h.origin === 'BOT' ? 'bot' : 'simul.'}</p>
                  </div>
                  <div className="tl-body">
                    <p className="tl-title">{h.title}</p>
                    <p className="tl-text">{h.text}</p>
                    {h.change && (
                      <p className="tl-change">
                        {h.change.field}: {h.change.before} → {h.change.after}
                      </p>
                    )}
                    <p className={`tl-notify${h.notification.kind === 'NONE' ? ' none' : ''}`}>
                      {h.notification.kind === 'SIMULATED' && <Icon name="send" />}
                      {h.notification.kind === 'SIMULATED' ? `Notifica simulata alle ${fmtTime(h.at)} · nessun invio` : h.notification.text}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="receipt">
              <p className="t-2">Ricevuta di consegna: non disponibile.</p>
              <p className="t-3">Telegram non collegato. Le notifiche sono esempi simulati: nessun invio.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="footer-note">
        <p>orbit. · Stazione di comando BTC · SIMULAZIONE LOCALE · orologio {fmtTime(now)}</p>
        <p>Nessun collegamento exchange · Tutti i prezzi, gli ordini e i risultati sono fittizi</p>
      </div>
    </>
  );
}
