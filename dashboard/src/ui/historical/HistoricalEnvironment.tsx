/**
 * Ambiente «Studio storico» (OBS-001): dati reali Binance Vision da bundle locale.
 * Vista causale al cutoff t; seguito retrospettivo solo su comando esplicito; riepilogo
 * mensile nella voce «Studio osservativo». Nessuna call, posizione, saldo, ordine o comando.
 * APP-001: vista e momento consultato nell'indirizzo (#/historical/at/<t>, #/historical/summary).
 * Il bundle resta solo in memoria: dopo un ricaricamento si chiede di riaprirlo e si torna al momento.
 */
import { Component, useRef, useState, type ReactNode } from 'react';
import type { Ms } from '../../contract/historical';
import { formatNumber } from '../../lib/numbers';
import type { ChartLevel } from '../components/CandleChart';
import { HistoricalStudy } from '../../historical/study';
import type { ShellProps } from '../App';
import { Shell } from '../App';
import { Notice } from '../components/primitives';
import { Unavailable } from '../components/Unavailable';
import { fmtUtc } from '../format';
import { navigate, paths, useScrollOnRoute } from '../router';
import { HistChartCard } from './HistChartCard';
import { HistHeader } from './HistHeader';
import { FamiliesSection } from './FamiliesSection';
import { NotInStudy, ObservationsCard } from './ObservationsCard';
import { OpenStudy, StudyFilePicker } from './OpenStudy';
import { MoveCard, moveState } from './MoveCard';
import { OutcomeCard } from './OutcomeCard';
import { RevisionsSection } from './RevisionsSection';
import { StudySummaryView } from './StudySummaryView';

export function HistoricalEnvironment({
  study,
  studyLoad = 0,
  onOpen,
  shell,
  moment,
  path = '/historical',
}: {
  study: HistoricalStudy | null;
  /** Numero dell'apertura corrente: rimonta lo studio a ogni bundle valido aperto. */
  studyLoad?: number;
  onOpen: (s: HistoricalStudy) => void;
  shell: ShellProps;
  /** Momento richiesto dall'indirizzo (ms UTC), se presente. */
  moment?: number;
  path?: string;
}) {
  const shellRef = useRef<HTMLDivElement>(null);
  useScrollOnRoute(path);
  const deep = moment !== undefined || shell.view === 'research';
  return (
    <Shell shell={shell} shellRef={shellRef}>
      {!study ? (
        <>
          {deep && (
            <div className="content" style={{ paddingBottom: 0 }}>
              <Notice tone="warning" title="Lo studio va riaperto">
                Lo studio storico resta solo in memoria: dopo un ricaricamento o da un collegamento diretto va riaperto dal file.
                {moment !== undefined ? ` Dopo l’apertura tornerai al momento ${fmtUtc(moment)}.` : ' Dopo l’apertura tornerai al riepilogo.'}
              </Notice>
            </div>
          )}
          <OpenStudy onOpen={onOpen} />
        </>
      ) : shell.view === 'settings' ? (
        <Unavailable title="Impostazioni" onBack={() => shell.navigate('dashboard')} />
      ) : (
        <ViewGuard key={studyLoad} onOpen={onOpen}>
          <StudyWorkspace study={study} onOpen={onOpen} shell={shell} moment={moment} />
        </ViewGuard>
      )}
    </Shell>
  );
}

/**
 * Contenimento difensivo: se una vista incontra comunque un dato inatteso, mostra l'errore in chiaro
 * (nessun valore sostitutivo) e permette di aprire un altro bundle. La difesa primaria resta il
 * validatore all'importazione.
 */
class ViewGuard extends Component<{ children: ReactNode; onOpen: (s: HistoricalStudy) => void }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="content" id="main-content" tabIndex={-1}>
        <section className="card unavailable" role="alert" aria-label="Errore di visualizzazione">
          <p className="section-title">Lo studio aperto contiene dati non previsti</p>
          <p className="t-2">La vista si è fermata invece di mostrare valori incompleti: {this.state.error.message}</p>
          <StudyFilePicker onOpen={this.props.onOpen} />
        </section>
      </main>
    );
  }
}

/** Ancore MOVE-001 note al momento: Q/B/P0 dalla nascita, P1 dalla sua pubblicazione; nulla prima della nascita. */
function moveLevels(study: HistoricalStudy, t: Ms): ChartLevel[] {
  const c = study.moveCase;
  if (!c || t < c.birthAt) return [];
  const p1 = moveState(study.moveFactsAt(t)).P1;
  const fmt = (x: number) => formatNumber(x, 0);
  const lv = (id: string, kind: string, label: string, p: number): ChartLevel => ({ id, kind, origin: 'MOVE001', overlay: 'PLAN', validTo: null, label, price: { amount: p } });
  const out = [lv('move-B', 'ENTRY', `MOVE B · ${fmt(c.B.price)}`, c.B.price), lv('move-P0', 'SUPPORT', `MOVE P0 base · ${fmt(c.P0.price)}`, c.P0.price)];
  if (p1) out.push(lv('move-P1', c.side === 'LONG' ? 'PIVOT_HIGH' : 'PIVOT_LOW', `MOVE P1 · ${fmt(p1.price)}`, p1.price));
  return out;
}

function StudyWorkspace({ study, onOpen, shell, moment }: { study: HistoricalStudy; onOpen: (s: HistoricalStudy) => void; shell: ShellProps; moment?: number }) {
  // Momento dall'indirizzo se è un'origine dello studio; altrimenti il caso OBS-002 o la prima origine.
  const fallback = study.obs002Case?.t ?? study.moveCase?.birthAt ?? study.origins[0];
  const cutoff: Ms = moment !== undefined && study.indexOf(moment) >= 0 ? moment : fallback;
  const [retrospective, setRetrospective] = useState(false);

  // Spostare il cutoff sostituisce la voce corrente (niente cronologia a ogni passo); il riepilogo apre una voce nuova.
  const goTo = (t: Ms) => {
    setRetrospective(false);
    navigate(paths.historical('dashboard', t), { replace: true });
  };

  if (shell.view === 'research') {
    return (
      <StudySummaryView
        study={study}
        onOpenOrigin={(t) => {
          setRetrospective(false);
          navigate(paths.historical('dashboard', t));
        }}
      />
    );
  }

  const snap = study.snapshot(cutoff);
  const move = study.moveCase;
  return (
    <>
      <HistHeader study={study} cutoff={cutoff} onCutoff={goTo} snapshot={snap} onOpen={onOpen} />
      <main className="content" id="main-content" tabIndex={-1}>
        <div className="row-market">
          <HistChartCard
            study={study}
            snapshot={snap}
            retrospective={move ? false : retrospective}
            onRetrospective={setRetrospective}
            allowRetrospective={!move}
            extraLevels={move ? moveLevels(study, cutoff) : []}
          />
          <ObservationsCard study={study} snapshot={snap} />
        </div>
        {move && <MoveCard study={study} t={cutoff} />}
        {retrospective && !move && <OutcomeCard row={study.retrospective(cutoff)} obs002={study.obs002Outcome(cutoff)} side={study.obs002Case?.side} onClose={() => setRetrospective(false)} />}
        <FamiliesSection snapshot={snap} />
        <RevisionsSection snapshot={snap} />
        <NotInStudy />
      </main>
    </>
  );
}
