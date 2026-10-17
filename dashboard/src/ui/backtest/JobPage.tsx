/**
 * Pagina di un'esecuzione: stato e avanzamento dichiarati dal servizio (nessun timer che simula
 * progressi), aggiornati circa ogni secondo finché il job è attivo, poi il polling si ferma. Se il
 * servizio non risponde si mostra l'ultimo stato noto come non aggiornato, senza presumere esiti.
 * Ricaricare la pagina ritrova lo stesso job: nessun nuovo avvio e nessun annullamento implicito.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, useApi } from '../../backtest/api';
import { isActive, type Job, type Progress } from '../../contract/app';
import { formatNumber } from '../../lib/numbers';
import { Badge, Button, Notice } from '../components/primitives';
import { fmtUtc } from '../format';
import { Link } from '../Link';
import { paths } from '../router';
import { periodText } from './ResultsPage';

/** Polling applicativo dello stato (circa ogni secondo) solo mentre il job è attivo; i test lo accorciano. */
export const JOB_POLL = { activeMs: 1000, retryMs: 2000 };

const STATE_LABEL: Record<Job['state'], string> = {
  STARTING: 'in preparazione',
  RUNNING: 'in corso',
  CANCEL_REQUESTED: 'annullamento richiesto',
  COMPLETED: 'completato · risultato completo',
  INCOMPLETE: 'terminato · risultato incompleto',
  CANCELLED: 'annullato',
  INTERRUPTED: 'interrotto',
  FAILED: 'errore',
};
const STATE_TONE: Record<Job['state'], 'accent' | 'warning' | 'positive' | 'negative' | 'neutral'> = {
  STARTING: 'accent',
  RUNNING: 'accent',
  CANCEL_REQUESTED: 'warning',
  COMPLETED: 'positive',
  INCOMPLETE: 'warning',
  CANCELLED: 'neutral',
  INTERRUPTED: 'warning',
  FAILED: 'negative',
};
const STAGE_STATUS = { PENDING: 'in attesa', RUNNING: 'in corso', DONE: 'conclusa', STOPPED: 'fermata' } as const;
const STEP_LABEL: Record<string, string> = {
  aggregate45m: 'candele da 45 minuti',
  aggregate1D: 'candele giornaliere',
  observe45m: 'osservazioni 45m',
  observe1D: 'osservazioni giornaliere',
};
const KIND_LABEL: Record<string, string> = { trade: 'prezzi al minuto', funding: 'pagamenti periodici', mark: 'prezzi di riferimento (mark)' };
const n = (x: number | null | undefined) => (x == null ? 'non ancora calcolato' : formatNumber(x, 0));
const seconds = (a: string | null, b: string | null) => {
  if (!a || !b) return null;
  const s = Math.max(0, (Date.parse(b) - Date.parse(a)) / 1000);
  return s < 0.1 ? 'meno di 0,1 s' : `${formatNumber(s, 1)} s`;
};
const clock = (iso: string) => new Date(iso).toISOString().slice(11, 19) + ' UTC';

/** Solo per la fase in corso e con totale noto: una fase conclusa o fermata non mostra percentuali. */
function Bar({ done, total, label, running }: { done: number | null; total: number | null; label: string; running: boolean }) {
  if (!running || done == null || !total) return null;
  const share = Math.min(1, done / total);
  return (
    <div className="pbar" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
      <div className="pbar-fill" style={{ width: `${(share * 100).toFixed(1)}%` }} />
      <span className="pbar-text">{formatNumber(share * 100, 0)}% di questa fase</span>
    </div>
  );
}

function Stage({ title, st, children, statusText }: { title: string; st: { status: keyof typeof STAGE_STATUS; startedAt: string | null; finishedAt: string | null }; children?: ReactNode; statusText?: string }) {
  const took = st.status === 'DONE' || st.status === 'STOPPED' ? seconds(st.startedAt, st.finishedAt) : null;
  return (
    <li className={`stage is-${st.status.toLowerCase()}`}>
      <div className="stage-head">
        <span className="stage-mark" aria-hidden="true">{st.status === 'DONE' ? '✓' : st.status === 'RUNNING' ? '●' : st.status === 'STOPPED' ? '■' : '○'}</span>
        <span className="stage-title">{title}</span>
        <span className="stage-status">
          {statusText ?? STAGE_STATUS[st.status]}
          {took ? ` · ${took}` : ''}
        </span>
      </div>
      {st.status !== 'PENDING' && children && <div className="stage-body">{children}</div>}
    </li>
  );
}

export function Stages({ p, inputStart }: { p: Progress; inputStart?: number }) {
  const { check, init, simulate, save } = p.stages;
  return (
    <ol className="stages" aria-label="Fasi del backtest">
      <Stage title="1. Controllo dei file, dei checksum e della copertura" st={check}>
        <p>
          File controllati: <strong>{n(check.filesDone)}</strong> di {n(check.filesExpected)}
          {check.byKind &&
            ` (${Object.entries(check.byKind)
              .map(([k, v]) => `${KIND_LABEL[k] ?? k} ${v.done}/${v.expected}`)
              .join(', ')})`}
          .
        </p>
        {check.current && check.status === 'RUNNING' && (
          <p className="t-2">
            Ora: {KIND_LABEL[check.current.kind] ?? check.current.kind} di {check.current.month}, righe lette {formatNumber(check.current.rows, 0)}.
          </p>
        )}
        <Bar done={check.filesDone} total={check.filesExpected} label="File controllati" running={check.status === 'RUNNING'} />
      </Stage>
      <Stage title="2. Preparazione: candele e osservazioni sulla storia" st={init}>
        <p>
          Minuti di prezzo caricati: <strong>{n(init.minutes)}</strong>
          {init.prefixMinutes != null && init.windowMinutes != null && (
            <>
              {' '}
              — {formatNumber(init.prefixMinutes, 0)} di storia usata solo per osservare{inputStart ? ` (dal ${fmtUtc(inputStart).slice(0, 11)})` : ''}, nessuna operazione in quel
              tratto; {formatNumber(init.windowMinutes, 0)} del periodo valutato.
            </>
          )}
        </p>
        {init.steps &&
          Object.entries(init.steps).map(([k, v]) => (
            <p key={k} className="t-2">
              {STEP_LABEL[k] ?? k}: {formatNumber(v.done, 0)} di {formatNumber(v.total, 0)}
            </p>
          ))}
      </Stage>
      <Stage title="3. Simulazione chiusura per chiusura" st={simulate} statusText={simulate.haltedAt != null ? 'interrotta per dati mancanti' : undefined}>
        {simulate.haltedAt != null ? (
          <p className="stage-alert">
            <strong>Valutazione interrotta il {fmtUtc(simulate.haltedAt)}</strong>: manca un minuto di prezzo mentre una posizione era aperta. Chiusure 45m valutate{' '}
            <strong>{n(simulate.closes)}</strong> di {n(simulate.closesTotal)}; {n(simulate.notEvaluatedCloses)} non valutate dopo la lacuna (nessun valore, non zero).
          </p>
        ) : (
          <p>
            Data raggiunta: <strong>{simulate.t != null ? fmtUtc(simulate.t) : 'non ancora calcolata'}</strong> · chiusure 45m valutate {n(simulate.closes)} di{' '}
            {n(simulate.closesTotal)}
          </p>
        )}
        <p className="t-2">
          Fin qui: movimenti riconosciuti {n(simulate.episodes)} · tentativi d’ingresso conclusi {n(simulate.requests)} (eseguiti {n(simulate.fills)}) · operazioni
          concluse {n(simulate.tradesClosed)} · posizione aperta adesso: {simulate.positionOpen == null ? 'non ancora calcolato' : simulate.positionOpen ? 'sì' : 'no'}
        </p>
        <Bar done={simulate.closes} total={simulate.closesTotal} label="Chiusure valutate" running={simulate.status === 'RUNNING'} />
      </Stage>
      <Stage title="4. Riepilogo e salvataggio" st={save}>
        <p className="t-2">
          {save.status === 'DONE' ? 'Risultato pubblicato: si trova in «Risultati salvati».' : save.publishing ? 'Pubblicazione del risultato in corso: l’annullamento non è più possibile.' : save.step ? `Passo: ${save.step === 'summary' ? 'riepilogo calcolato' : save.step === 'bundle' ? 'file del risultato preparato' : save.step === 'staged' ? 'file pronti, in attesa di pubblicazione' : save.step}` : 'in corso'}
        </p>
      </Stage>
    </ol>
  );
}

function Outcome({ job }: { job: Job }) {
  const res = job.result;
  switch (job.state) {
    case 'COMPLETED':
      return (
        <Notice tone="positive" title="Backtest completato: il risultato è salvato">
          {res && `${res.counts.trades} operazioni simulate. `}Il risultato resta in «Risultati salvati» e si può riaprire senza ricalcolare.
          {job.cancel?.outcome === 'TOO_LATE' ? ' L’annullamento è arrivato dopo la pubblicazione del risultato: il risultato completo è stato conservato.' : ''}
        </Notice>
      );
    case 'INCOMPLETE':
      // Copertura dei prezzi e completezza dopo i costi sono distinte: un costo mancante non è una lacuna di prezzo.
      return res && res.priceCoverageComplete !== false && !res.halted ? (
        <Notice tone="warning" title="Storico elaborato, ma risultato dopo i costi non calcolabile">
          {res.incompleteReason ? `${res.incompleteReason.charAt(0).toUpperCase()}${res.incompleteReason.slice(1)}. ` : ''}Le operazioni e le voci note restano visibili; il
          totale non viene sostituito con zero né con una stima.
        </Notice>
      ) : (
        <Notice tone="warning" title="Terminato con risultato incompleto">
          Il calcolo è finito ma il periodo non è valutabile per intero{res?.halted ? ` (interrotto il ${fmtUtc(res.halted.at)}: ${res.halted.reason})` : ''}. Il risultato
          mostra soltanto i fatti noti; i valori mancanti restano mancanti.
        </Notice>
      );
    case 'CANCELLED':
      return (
        <Notice tone="neutral" title="Backtest annullato: nessun risultato">
          Annullato su richiesta{job.cancel?.requestedAt ? ` alle ${clock(job.cancel.requestedAt)}` : ''}. Restano lo stato e l’avanzamento raggiunto; nessun risultato
          parziale è presentato come valido. Per rifarlo serve un nuovo avvio.
        </Notice>
      );
    case 'INTERRUPTED':
      return (
        <Notice tone="warning" title="Backtest interrotto: nessun risultato">
          {job.error?.message ?? 'Il servizio si è fermato prima della fine.'} Per rifarlo avvia un nuovo backtest.
        </Notice>
      );
    case 'FAILED':
      return (
        <Notice tone="negative" title={job.error?.kind === 'INTERNAL' ? 'Errore del programma: nessun risultato' : 'Dati mancanti o non utilizzabili: nessun risultato'}>
          {job.error?.message}
          {job.error?.qualityReport ? ` Rapporto di qualità: ${job.error.qualityReport} nella cartella dati.` : ''} Nessun dato viene scaricato o inventato.
        </Notice>
      );
    default:
      return null;
  }
}

export function JobPage({ jobId }: { jobId: string }) {
  const api = useApi();
  const [job, setJob] = useState<Job | null>(null);
  const [serverTime, setServerTime] = useState<string | null>(null);
  const [lastOk, setLastOk] = useState<number | null>(null);
  const [problem, setProblem] = useState<ApiError | null>(null);
  const [cancelMsg, setCancelMsg] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const r = await api.job(jobId);
        if (!alive.current) return;
        setJob(r.job);
        setServerTime(r.serverTime);
        setLastOk(Date.now());
        setProblem(null);
        if (isActive(r.job.state)) timer = setTimeout(poll, JOB_POLL.activeMs);
      } catch (e) {
        if (!alive.current) return;
        const err = e instanceof ApiError ? e : new ApiError('SERVICE_UNAVAILABLE', String(e));
        setProblem(err);
        if (err.kind !== 'NOT_FOUND') timer = setTimeout(poll, JOB_POLL.retryMs);
      }
    };
    poll();
    return () => {
      alive.current = false;
      if (timer) clearTimeout(timer);
    };
  }, [api, jobId]);

  if (!job) {
    if (problem?.kind === 'NOT_FOUND') {
      return (
        <main className="content" id="main-content" tabIndex={-1}>
          <Notice tone="negative" title="Esecuzione non trovata">
            Il collegamento indica un’esecuzione che il servizio non conosce. Nessun grafico o risultato viene mostrato al suo posto.
          </Notice>
          <div className="actions">
            <Link to={paths.backtestSaved()} className="btn btn-primary">
              Vai ai risultati salvati
            </Link>
            <Link to={paths.backtestNew()} className="btn btn-secondary">
              Nuovo backtest
            </Link>
          </div>
        </main>
      );
    }
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        {problem ? (
          <Notice tone="warning" title="Servizio locale non raggiungibile">
            {problem.message} Riprovo ogni pochi secondi.
          </Notice>
        ) : (
          <p className="t-2">Lettura dello stato dell’esecuzione…</p>
        )}
      </main>
    );
  }

  const active = isActive(job.state);
  const p = job.progress;
  const elapsedTo = active ? serverTime : job.finishedAt;
  const cancel = async () => {
    setCancelling(true);
    setCancelMsg(null);
    try {
      const r = await api.cancel(jobId);
      setJob(r.job);
      if (r.outcome === 'ALREADY_FINISHED') setCancelMsg('Il backtest era già concluso: nessuna modifica.');
    } catch (e) {
      setCancelMsg(e instanceof ApiError ? e.message : String(e));
    } finally {
      setCancelling(false);
    }
  };

  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card table-card" aria-label="Esecuzione del backtest">
        <div className="card-head">
          <div>
            <p className="section-title">
              {job.profile.label} · {periodText(job.profile.window.start, job.profile.window.end)}
            </p>
            <p className="card-sub">
              Esecuzione <span className="mono">{job.jobId}</span> · avviata alle {clock(job.startedAt)} · candidato {job.candidate?.id} {job.candidate?.version} · motore{' '}
              {job.engineVersion}
            </p>
          </div>
          <div className="actions">
            <Badge tone={STATE_TONE[job.state]}>{STATE_LABEL[job.state].toUpperCase()}</Badge>
          </div>
        </div>
        <p className="t-2">
          Tempo trascorso: {seconds(job.startedAt, elapsedTo) ?? '—'} · ultimo aggiornamento del calcolo: {clock(job.updatedAt)}
          {lastOk ? ` · stato letto dal servizio alle ${clock(new Date(lastOk).toISOString())}` : ''}
        </p>
        {problem && (
          <Notice tone="warning" title="Stato non aggiornato">
            Il servizio locale non risponde ({problem.message}). Mostro l’ultimo stato ricevuto, senza presumere che il backtest sia finito o annullato.
          </Notice>
        )}
        {job.state === 'CANCEL_REQUESTED' && (
          <Notice tone="warning" title="Annullamento richiesto">
            Il calcolo si ferma al prossimo punto di controllo (di solito entro pochi secondi). L’esito effettivo comparirà qui.
          </Notice>
        )}
        <div className="actions">
          {active && (
            <Button
              variant="danger"
              onClick={cancel}
              disabled={cancelling || job.state === 'CANCEL_REQUESTED' || p?.stages.save.publishing}
              reason={p?.stages.save.publishing ? 'Il risultato è già in pubblicazione' : 'Annullamento già richiesto'}
            >
              Annulla backtest
            </Button>
          )}
          {job.result && (job.state === 'COMPLETED' || job.state === 'INCOMPLETE') && (
            <Link to={paths.result({ kind: 'saved', id: job.result.resultId })} className="btn btn-primary">
              Apri risultati
            </Link>
          )}
          {!active && (
            <Link to={paths.backtestNew()} className="btn btn-secondary">
              Nuovo backtest
            </Link>
          )}
          <Link to={paths.backtestSaved()} className="btn btn-ghost">
            Risultati salvati
          </Link>
        </div>
        {cancelMsg && <p className="t-2">{cancelMsg}</p>}
        <Outcome job={job} />
      </section>
      {p && (
        <section className="card table-card" aria-label="Avanzamento">
          <p className="table-title">Avanzamento reale</p>
          <p className="footnote">
            Conteggi forniti dal motore durante il calcolo. Le percentuali valgono solo per la fase indicata e solo dove il totale è noto; nessuna stima del tempo
            restante. Una fase rapida può risultare già conclusa.
          </p>
          <Stages p={p} />
        </section>
      )}
    </main>
  );
}
