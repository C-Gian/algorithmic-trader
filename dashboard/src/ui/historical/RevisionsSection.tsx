import type { CausalSnapshot, HistScale, StudyEvent } from '../../contract/historical';
import { isoMinute } from '../format';
import { price } from './fmt';

const LIMIT = 14;

function describe(e: StudyEvent): { title: string; text: string } {
  const p = (x: unknown) => price(typeof x === 'number' ? x : null);
  switch (e.type) {
    case 'PIVOT_CONFIRMED':
      return { title: `Pivot ${e.kind} confermato`, text: `${p(e.price)} sulla candela ${isoMinute(e.candidateOpen as number)}` };
    case 'PIVOT_REJECTED':
      return { title: `Candidata ${e.kind} scartata (parità)`, text: `candela ${isoMinute(e.candidateOpen as number)} · ${p(e.price)}` };
    case 'PIVOT_DUAL_AMBIGUOUS':
      return { title: 'Candidata ambigua (high e low insieme)', text: `candela ${isoMinute(e.candidateOpen as number)}: esclusa da struttura e sequenza` };
    case 'FIB_SEQUENCE': {
      const before = e.before as { price: number } | null | undefined;
      const after = (e.after ?? e.ignored) as { price: number } | undefined;
      const label = e.action === 'REPLACE' ? 'sostituzione' : e.action === 'APPEND' ? 'aggiunta' : 'conservato (non più esteso)';
      return { title: `Fibonacci v${e.version as number}: ${label}`, text: before ? `${p(before.price)} → ${p(after?.price)}` : `${e.kind} ${p(after?.price)}` };
    }
    case 'LEVEL_CROSS':
      return { title: `Attraversamento ${e.direction as string} di ${e.levelKind as string}`, text: `livello ${p(e.price)} · chiusura prec. ${p(e.previousClose)} → ${p(e.close)}` };
    case 'SMA_CROSS':
      return { title: `Incrocio medie ${e.direction as string}`, text: 'cambio di segno di (SMA20−SMA50)/A' };
    case 'SEGMENT_RESET':
      return { title: 'Azzeramento per lacuna', text: `finestre, pivot e ancore ripartono dopo ${e.missing as number} minuti mancanti` };
    default:
      return { title: e.type, text: '' };
  }
}

function Column({ scale, events }: { scale: HistScale; events: readonly StudyEvent[] }) {
  const shown = events.slice(-LIMIT).reverse();
  return (
    <div className="card timeline">
      <div className="card-head">
        <p className="table-title">Scala {scale}</p>
        <span className="t-3" style={{ fontSize: 11 }}>
          {events.length} eventi noti
        </span>
      </div>
      <div className="tl-list">
        {shown.length === 0 && <p className="empty">Nessun evento noto entro t.</p>}
        {shown.map((e) => {
          const d = describe(e);
          return (
            <div className="tl-event" key={e.id}>
              <span className="tl-time">{isoMinute(e.availableAt).slice(5, 16).replace('T', ' ')}</span>
              <div className="tl-body">
                <p className="tl-title">{d.title}</p>
                <p className="tl-text">{d.text}</p>
                <p className="tl-text t-3">
                  evento {isoMinute(e.eventTime)} · noto {isoMinute(e.availableAt)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Storia delle revisioni filtrata per available_at ≤ t: distinta dal seguito del prezzo. */
export function RevisionsSection({ snapshot }: { snapshot: CausalSnapshot }) {
  return (
    <section className="section" id="storico" aria-label="Revisioni note al cutoff" style={{ scrollMarginTop: 'calc(var(--sticky-h, 96px) + 16px)' }}>
      <div className="section-head">
        <div>
          <p className="section-title">Revisioni ed eventi noti a t</p>
          <p className="section-desc">
            Pivot, scarti, versioni Fibonacci, attraversamenti e incroci con il loro orario di disponibilità (UTC). Nessun evento successivo a t; non è il seguito del prezzo.
          </p>
        </div>
        <span className="section-aside">Ultimi {LIMIT} per scala</span>
      </div>
      <div className="account-row">
        <div className="col-left">
          <Column scale="45m" events={snapshot.events['45m']} />
        </div>
        <div className="col-right">
          <Column scale="1D" events={snapshot.events['1D']} />
        </div>
      </div>
    </section>
  );
}
