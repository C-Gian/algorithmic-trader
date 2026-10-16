import { formatNumber, formatSigned } from '../../lib/numbers';
import { fmtAgo, fmtDate, fmtTime, tzAbbr } from '../format';
import { useDashboard } from '../useDashboard';
import { Badge, Button } from './primitives';

export function Header() {
  const { snapshot, request } = useDashboard();
  const { context, actions } = snapshot;
  const { feed, market, bot, mode } = context;
  const now = context.clock.now;
  const feedOk = feed.status === 'OK';
  const price = market.price.value?.amount ?? market.lastKnownPrice.value.amount;
  const change = market.change24hPct;

  const modeDesc =
    mode === 'CALL_AND_EXECUTION'
      ? '✓ Esecuzione automatica simulata · 1 sola posizione BTC · Nessun aumento di quantità'
      : '◉ Solo call · Nessun nuovo ordine simulato; una posizione esistente resta a te';

  return (
    <header className="header">
      <div className="header-row">
        <div className="crumbs">
          <span>Workspace</span>
          <span>/</span>
          <strong>Dashboard</strong>
          <Badge tone="accent">SIMULAZIONE</Badge>
        </div>
        <div className="sys-time">
          <span className="mono">
            {fmtDate(now)} · {fmtTime(now)} {tzAbbr(now)} · orologio simulato
          </span>
          <span className={feedOk ? undefined : 't-warn'}>
            {feedOk ? `Aggiornato alle ${fmtTime(feed.observedAt)} · ${fmtAgo(feed.observedAt, now)}` : `Ultimo dato alle ${fmtTime(feed.observedAt)} · ${fmtAgo(feed.observedAt, now)}`}
          </span>
        </div>
      </div>

      <div className="header-row">
        <div className="quote">
          <span className="btc-mark" aria-hidden>
            ₿
          </span>
          <div className="pair">
            <p className="pair-name">BTC / USDT</p>
            <p className="pair-sub">Bitcoin · {context.instrument.productLabel}</p>
          </div>
          <p className={`price-big${feedOk ? '' : ' is-stale'}`} title={feedOk ? 'Prezzo simulato corrente' : 'Ultimo prezzo noto, non corrente'}>
            {formatNumber(price, 2)}
          </p>
          {change.value !== null ? (
            <Badge tone={change.value >= 0 ? 'positive' : 'negative'}>
              {change.value >= 0 ? '↗' : '↘'} {formatSigned(change.value, 2)}% · 24 h
            </Badge>
          ) : (
            <Badge tone="warning">Ultimo noto alle {fmtTime(market.lastKnownPrice.at)} · variazione non disponibile</Badge>
          )}
        </div>

        <div className="controls">
          {feed.status === 'OK' ? (
            <Badge tone="accent" icon="wifi13">
              Feed simulato · regolare
            </Badge>
          ) : (
            <Badge tone="warning">{feed.status === 'STALE' ? 'Feed simulato · dati non aggiornati' : 'Feed simulato · disconnesso'}</Badge>
          )}
          {bot.status === 'RUNNING' && feedOk ? (
            <Badge tone="positive" icon="activity">
              Bot attivo
            </Badge>
          ) : bot.status === 'RUNNING' ? (
            <Badge tone="warning">Bot attivo · azioni automatiche sospese</Badge>
          ) : (
            <Badge tone="warning">Bot fermo</Badge>
          )}
          <Button
            variant={actions.START.enabled ? 'primary' : 'secondary'}
            icon={actions.START.enabled ? 'play16Dark' : 'play16Grey'}
            disabled={!actions.START.enabled}
            reason={actions.START.reason}
            onClick={() => request('START')}
          >
            Start
          </Button>
          <Button variant="danger" icon="square16Red" disabled={!actions.STOP_TOTAL.enabled} reason={actions.STOP_TOTAL.reason} onClick={() => request('STOP_TOTAL')}>
            Stop totale
          </Button>
        </div>
      </div>

      <div className="header-row">
        <div className="mode-switch" role="group" aria-label="Modalità di esecuzione">
          <Button
            variant={mode === 'CALL_ONLY' ? 'primary' : 'ghost'}
            icon={mode === 'CALL_ONLY' ? undefined : 'eye'}
            pressed={mode === 'CALL_ONLY'}
            onClick={() => mode !== 'CALL_ONLY' && request('MODE_CALL_ONLY')}
          >
            Solo call
          </Button>
          <Button
            variant={mode === 'CALL_AND_EXECUTION' ? 'primary' : 'ghost'}
            icon={mode === 'CALL_AND_EXECUTION' ? 'checkCheck16Dark' : undefined}
            pressed={mode === 'CALL_AND_EXECUTION'}
            onClick={() => mode !== 'CALL_AND_EXECUTION' && request('MODE_CALL_AND_EXECUTION')}
          >
            Call + esecuzione
          </Button>
        </div>
        <p className="mode-desc">
          {modeDesc}
          {!feedOk && ' · Feed non regolare: azioni automatiche sospese, nuovi ingressi, Start e ripresa automatica bloccati'}
          {bot.status === 'STOPPED' && ' · Bot fermo: nessuna azione automatica'}
        </p>
      </div>
    </header>
  );
}
