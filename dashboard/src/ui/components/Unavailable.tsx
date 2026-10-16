import { Button } from './primitives';

/** Sezioni fuori perimetro: dichiarate, senza pagine apparentemente operative. */
export function Unavailable({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="content">
      <section className="card unavailable" aria-label={title}>
        <p className="section-title">{title}</p>
        <p className="t-2">Non disponibile in questa versione.</p>
        <p className="t-3" style={{ fontSize: 12 }}>
          Questa simulazione locale comprende soltanto la dashboard. Nessuna funzione di questa sezione è stata costruita o collegata.
        </p>
        <Button onClick={onBack}>Torna alla dashboard</Button>
      </section>
    </div>
  );
}
