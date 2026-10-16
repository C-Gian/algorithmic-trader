/**
 * Ambiente «Studio storico» (OBS-001): dati reali Binance Vision da bundle locale.
 * Vista causale al cutoff t; seguito retrospettivo solo su comando esplicito; riepilogo
 * mensile nella voce «Studio osservativo». Nessuna call, posizione, saldo, ordine o comando.
 */
import { useRef, useState } from 'react';
import type { Ms } from '../../contract/historical';
import { HistoricalStudy } from '../../historical/study';
import type { ShellProps } from '../App';
import { Shell } from '../App';
import { Unavailable } from '../components/Unavailable';
import { HistChartCard } from './HistChartCard';
import { HistHeader } from './HistHeader';
import { FamiliesSection } from './FamiliesSection';
import { NotInStudy, ObservationsCard } from './ObservationsCard';
import { OpenStudy } from './OpenStudy';
import { OutcomeCard } from './OutcomeCard';
import { RevisionsSection } from './RevisionsSection';
import { StudySummaryView } from './StudySummaryView';

export function HistoricalEnvironment({ study, onOpen, shell }: { study: HistoricalStudy | null; onOpen: (s: HistoricalStudy) => void; shell: ShellProps }) {
  const shellRef = useRef<HTMLDivElement>(null);
  return (
    <Shell shell={shell} shellRef={shellRef}>
      {!study ? (
        <OpenStudy onOpen={onOpen} />
      ) : shell.view === 'settings' ? (
        <Unavailable title="Impostazioni" onBack={() => shell.navigate('dashboard')} />
      ) : (
        <StudyWorkspace key={study.bundle.run.runId + study.bundle.conventions.hash} study={study} onOpen={onOpen} shell={shell} />
      )}
    </Shell>
  );
}

function StudyWorkspace({ study, onOpen, shell }: { study: HistoricalStudy; onOpen: (s: HistoricalStudy) => void; shell: ShellProps }) {
  // Impostazione iniziale: prima origine dello studio.
  const [cutoff, setCutoff] = useState<Ms>(study.origins[0]);
  const [retrospective, setRetrospective] = useState(false);

  const goTo = (t: Ms) => {
    setCutoff(t);
    setRetrospective(false);
  };

  if (shell.view === 'research') {
    return (
      <StudySummaryView
        study={study}
        onOpenOrigin={(t) => {
          goTo(t);
          shell.navigate('dashboard');
        }}
      />
    );
  }

  const snap = study.snapshot(cutoff);
  return (
    <>
      <HistHeader study={study} cutoff={cutoff} onCutoff={goTo} snapshot={snap} onOpen={onOpen} />
      <main className="content" id="main-content" tabIndex={-1}>
        <div className="row-market">
          <HistChartCard study={study} snapshot={snap} retrospective={retrospective} onRetrospective={setRetrospective} />
          <ObservationsCard study={study} snapshot={snap} />
        </div>
        {retrospective && <OutcomeCard row={study.retrospective(cutoff)} onClose={() => setRetrospective(false)} />}
        <FamiliesSection snapshot={snap} />
        <RevisionsSection snapshot={snap} />
        <NotInStudy />
      </main>
    </>
  );
}
