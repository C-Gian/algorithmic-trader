/**
 * «Nuovo backtest»: i tre profili fissi, che cosa sarà calcolato, dati richiesti e disponibilità.
 * L'avvio parte solo dal clic su «Avvia» (POST con chiave univoca del clic, ripetuta solo in caso di
 * risposta persa). Aprire un risultato già presente è un'azione distinta e non ricalcola.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, newRequestKey, useApi } from '../../backtest/api';
import type { Job, ProfileInfo, SavedResult } from '../../contract/app';
import { formatNumber } from '../../lib/numbers';
import { Info } from '../components/Info';
import { Badge, Button, Notice } from '../components/primitives';
import { Link } from '../Link';
import { navigate, paths } from '../router';
import { periodText } from './ResultsPage';

const RETRIES = 2;
const month = (m: string) => {
  const [y, mm] = m.split('-');
  return `${['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'][Number(mm) - 1]} ${y}`;
};
const bp = (x: number) => formatNumber(x * 10_000, 0);

export function NewBacktestPage() {
  const api = useApi();
  const [profiles, setProfiles] = useState<ProfileInfo[] | null>(null);
  const [active, setActive] = useState<Job | null>(null);
  const [saved, setSaved] = useState<SavedResult[]>([]);
  const [loadError, setLoadError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [startError, setStartError] = useState<{ profileId: string; error: ApiError } | null>(null);
  const starting = useRef(false);

  const load = useCallback(async () => {
    try {
      const r = await api.profiles();
      setProfiles(r.profiles);
      setActive(r.activeJob);
      setLoadError(null);
      try {
        setSaved((await api.results()).results);
      } catch {
        setSaved([]);
      }
    } catch (e) {
      setLoadError(e instanceof ApiError ? e : new ApiError('SERVICE_UNAVAILABLE', String(e)));
    }
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  const start = async (profileId: string) => {
    if (starting.current) return; // doppio clic: un solo avvio
    starting.current = true;
    setBusy(profileId);
    setStartError(null);
    const key = newRequestKey();
    try {
      for (let attempt = 0; ; attempt++) {
        try {
          const r = await api.start(profileId, key);
          navigate(paths.job(r.job.jobId));
          return;
        } catch (e) {
          const err = e instanceof ApiError ? e : new ApiError('SERVICE_UNAVAILABLE', String(e));
          // Risposta persa: stessa chiave, quindi al più lo stesso job; mai un secondo calcolo.
          if (err.kind === 'SERVICE_UNAVAILABLE' && attempt < RETRIES) {
            await new Promise((ok) => setTimeout(ok, 700));
            continue;
          }
          setStartError({ profileId, error: err });
          if (err.code === 'ACTIVE_JOB_EXISTS') setActive((err.details.job as Job) ?? null);
          return;
        }
      }
    } finally {
      starting.current = false;
      setBusy(null);
    }
  };

  if (loadError) {
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <Notice tone="warning" title="Servizio locale non raggiungibile">
          {loadError.message} Senza il servizio non si può avviare un backtest; i file esterni si possono comunque aprire da «Risultati salvati».
        </Notice>
        <div className="actions">
          <Button onClick={load}>Riprova</Button>
          <Link to={paths.backtestSaved()} className="btn btn-secondary">
            Risultati salvati
          </Link>
        </div>
      </main>
    );
  }
  if (!profiles) {
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <p className="t-2">Lettura dei profili disponibili…</p>
      </main>
    );
  }

  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Nuovo backtest">
        <p className="section-title">Nuovo backtest</p>
        <p className="t-2">
          Scegli un periodo e premi «Avvia»: il calcolo parte sul tuo PC con i dati già scaricati e verificati, senza download. Vedrai le fasi reali (controllo dei file,
          preparazione, simulazione chiusura per chiusura, salvataggio) e potrai annullare. Le regole del bot, la dimensione delle operazioni e i costi sono fissi: qui non si
          cambiano.
        </p>
        {active && (
          <Notice tone="warning" title="C’è già un backtest in corso">
            {active.profile.label}, avviato alle {new Date(active.startedAt).toISOString().slice(11, 19)} UTC. Se ne esegue uno alla volta.{' '}
            <Link to={paths.job(active.jobId)}>Segui il backtest in corso</Link>
          </Notice>
        )}
      </section>
      <div className="profile-grid">
        {profiles.map((p) => {
          const av = p.availability;
          const previous = saved.filter((r) => r.status === 'OK' && r.profile?.id === p.id);
          const err = startError?.profileId === p.id ? startError.error : null;
          return (
            <section key={p.id} className="card profile-card" aria-label={p.label}>
              <div className="card-head">
                <p className="card-title">{p.label}</p>
                {p.kind === 'PRODUCT_CHECK' ? (
                  <Badge tone="neutral">COLLAUDO · BREVE</Badge>
                ) : p.kind === 'ADDITIONAL_COMPARISON' ? (
                  <Badge tone="warning">GIÀ ESPOSTO</Badge>
                ) : (
                  <Badge tone="neutral">SVILUPPO</Badge>
                )}
              </div>
              <p className="t-2">{p.description}</p>
              <dl className="facts">
                <dt>Periodo con operazioni simulate</dt>
                <dd>{periodText(p.window.start, p.window.end)}</dd>
                <dt>
                  Storia usata solo per osservare
                  <Info label="Storia usata solo per osservare">
                    Il bot guarda i prezzi dal 1 ottobre 2022 per calcolare le sue osservazioni, ma in quel tratto non simula operazioni. Ogni periodo parte senza posizioni
                    aperte.
                  </Info>
                </dt>
                <dd>dal {month(av.tradeMonths[0])}; nessuna operazione in quel tratto</dd>
                <dt>Candidato</dt>
                <dd>
                  {p.candidate.id} versione {p.candidate.version} (di sviluppo, non promosso) · motore {p.engineVersion}
                </dd>
                <dt>Dimensione di ogni operazione</dt>
                <dd>{formatNumber(p.notionalUSDT, 0)} USDT, fissa (non è un capitale né la perdita massima)</dd>
                <dt>Costi</dt>
                <dd>
                  commissioni {bp(p.costs.baseline.fee)} bp e prezzo di esecuzione {bp(p.costs.baseline.slippage)} bp per lato; pagamenti periodici storici; scenario a parte con{' '}
                  {bp(p.costs.stress.fee)} + {bp(p.costs.stress.slippage)} bp
                </dd>
                <dt>Dati richiesti</dt>
                <dd>
                  prezzi al minuto {month(av.tradeMonths[0])} – {month(av.tradeMonths[1])} ({av.files.trade} file
                  {av.reuseObs ? `, di cui ${av.reuseObs} dallo studio OBS-001` : ''}); pagamenti periodici e prezzi mark{' '}
                  {av.costMonths[0] === av.costMonths[1] ? month(av.costMonths[0]) : `${month(av.costMonths[0])} – ${month(av.costMonths[1])}`} ({av.files.funding} + {av.files.mark}{' '}
                  file)
                </dd>
                <dt>Disponibilità</dt>
                <dd className={av.available ? 't-pos' : 't-warn'}>
                  {av.available ? '✓ tutti i file presenti (checksum verificati all’avvio)' : `✗ mancano ${av.missing.length} file`}
                </dd>
              </dl>
              {!av.available && (
                <Notice tone="warning" title="Dati mancanti: avvio non possibile">
                  {av.missing.slice(0, 6).map((m) => `${m.kind} ${m.month}: ${m.reason}`).join('; ')}
                  {av.missing.length > 6 ? '…' : ''}. L’app non scarica nulla.
                </Notice>
              )}
              {err && (
                <Notice tone={err.kind === 'CONFLICT' ? 'warning' : 'negative'} title={err.code === 'ACTIVE_JOB_EXISTS' ? 'C’è già un backtest in corso' : 'Avvio non riuscito'}>
                  {err.message}
                  {err.code === 'ACTIVE_JOB_EXISTS' && active ? ': nessun nuovo calcolo è stato creato.' : ''}
                </Notice>
              )}
              <div className="actions">
                <Button
                  variant="primary"
                  onClick={() => start(p.id)}
                  disabled={busy !== null || !av.available || active !== null}
                  reason={active ? 'C’è già un backtest in corso' : !av.available ? 'Dati mancanti' : 'Avvio in corso'}
                >
                  {busy === p.id ? 'Avvio…' : 'Avvia'}
                </Button>
                {previous[0] && (
                  <Link to={paths.result({ kind: 'saved', id: previous[0].resultId })} className="btn btn-secondary">
                    Apri risultato salvato (non ricalcola)
                  </Link>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </main>
  );
}
