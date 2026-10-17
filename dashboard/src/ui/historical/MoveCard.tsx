/**
 * MOVE-001: riferimento del movimento al momento scelto. Ricostruisce giudizio e ancore soltanto dai
 * fatti del ledger con istante <= t (nessuna revisione o sostituzione futura). Nessun esito 24h,
 * nessuna operazione: rappresentazione sperimentale.
 */
import type { MoveAnchor, MoveLedgerEvent, Ms } from '../../contract/historical';
import type { HistoricalStudy } from '../../historical/study';
import { formatNumber } from '../../lib/numbers';
import { Badge, Notice } from '../components/primitives';
import { fmtUtc } from '../format';

const price = (x: unknown) => (typeof x === 'number' ? formatNumber(x, 2) : '—');

export interface MoveState {
  readonly judgement: string;
  readonly reason: string;
  readonly P1: MoveAnchor | null;
  readonly archived: { readonly reason: string; readonly judgement: string; readonly judgementReason: string; readonly t: Ms } | null;
  readonly openAtEnd: boolean;
}

/** Stato del riferimento dai soli fatti noti (già filtrati per istante). */
export function moveState(facts: readonly MoveLedgerEvent[]): MoveState {
  let judgement = 'INDETERMINATO';
  let reason = 'FORMAZIONE_NON_CONCLUSA';
  let P1: MoveAnchor | null = null;
  let archived: MoveState['archived'] = null;
  let openAtEnd = false;
  for (const e of facts) {
    if (e.type === 'P1_PUBLISHED') P1 = e.P1 as MoveAnchor;
    if (e.type === 'SUSPENSION') [judgement, reason] = ['INDETERMINATO', e.reason as string];
    if (e.type === 'USABLE') [judgement, reason] = ['UTILIZZABILE', 'P1_NOTO'];
    if (e.type === 'ARCHIVE') {
      archived = { reason: e.reason as string, judgement: e.judgement as string, judgementReason: e.judgementReason as string, t: e.t };
      [judgement, reason] = [archived.judgement, archived.judgementReason];
    }
    if (e.type === 'OPEN_AT_END') openAtEnd = true;
  }
  return { judgement, reason, P1, archived, openAtEnd };
}

function describe(e: MoveLedgerEvent): string {
  const flags = Array.isArray(e.flags) && e.flags.length ? ` · ${(e.flags as string[]).join(', ')}` : '';
  switch (e.type) {
    case 'BIRTH':
      return `Nascita: chiusura ${price(e.C)} oltre B ${price((e.B as MoveAnchor).price)} (chiusura precedente ${price(e.Cprev)}); base P0 ${price((e.P0 as MoveAnchor).price)} non testata`;
    case 'P1_PUBLISHED':
      return `P1 ${price((e.P1 as MoveAnchor).price)} pubblicato (candela ${fmtUtc((e.P1 as MoveAnchor).candidateOpen)})${e.whileSuspended ? ' — da sospeso: non rende la lettura utilizzabile' : ''}`;
    case 'USABLE':
      return 'Primo passaggio a UTILIZZABILE: P1 noto, nessuna sospensione';
    case 'SUSPENSION':
      return `Sospensione ${String(e.reason)}: la lettura non viene riattivata, si attende una nuova struttura${flags}`;
    case 'FACT':
      return `Fatto successivo da sospeso: ${String(e.fact)}${flags}`;
    case 'ARCHIVE':
      return `Archiviazione ${String(e.reason)} · ultimo giudizio ${String(e.judgement)}/${String(e.judgementReason)}${e.replacedBy ? ` · sostituito da ${String(e.replacedBy)}` : ''}${flags}`;
    case 'CANDIDATE_REJECTED':
      return `Struttura ${String(e.candidateSide)} qualificata non adottata: ${String(e.outcome)} (P0 ${price(e.candidateP0)}, livello ${price(e.candidateB)})`;
    case 'OPEN_AT_END':
      return 'Fine della copertura dei dati: riferimento ancora aperto (archiviazione amministrativa, non un fatto di mercato)';
    default:
      return e.type;
  }
}

const TONE: Record<string, 'positive' | 'negative' | 'warning'> = { UTILIZZABILE: 'positive', NON_SOSTIENE_PIU_LA_TESI: 'negative', INDETERMINATO: 'warning' };

export function MoveCard({ study, t }: { study: HistoricalStudy; t: Ms }) {
  const c = study.moveCase;
  if (!c) return null;
  const facts = study.moveFactsAt(t);
  const born = t >= c.birthAt;
  const st = moveState(facts);
  const anchors: [string, MoveAnchor | null][] = [
    ['Q (pivot precedente)', c.Q],
    ['B (estremo rotto in chiusura)', c.B],
    ['P0 (base della rottura)', c.P0],
    ['P1 (estremo finale)', st.P1],
  ];
  return (
    <section className="card move-card" aria-label="Movimento di riferimento MOVE-001">
      <div className="card-head">
        <div>
          <p className="section-title">Movimento di riferimento · {c.side}</p>
          <p className="card-sub mono">{c.refId}</p>
        </div>
        <Badge tone="accent">NOTO AL {fmtUtc(t).toUpperCase()}</Badge>
      </div>
      {!born ? (
        <Notice tone="warning" title="Riferimento non ancora nato a questo momento">
          Il caso consultato nasce alla chiusura {fmtUtc(c.birthAt)}: prima di allora non esiste alcuna lettura. Le barre mostrano solo il prezzo e le osservazioni note.
        </Notice>
      ) : (
        <>
          <div className="levels-table">
            <div className="lt-row">
              <span className="lt-label">Giudizio</span>
              <span className="lt-val">
                <Badge tone={TONE[st.judgement] ?? 'warning'}>{st.judgement}</Badge>
              </span>
              <span className="lt-val t-3">{st.reason}{st.archived ? ` · archiviato alle ${fmtUtc(st.archived.t)} (${st.archived.reason})` : st.openAtEnd ? ' · aperto a fine copertura' : ''}</span>
            </div>
            {anchors.map(([label, a]) => (
              <div className="lt-row" key={label}>
                <span className="lt-label">{label}</span>
                <span className="lt-val mono">{a ? price(a.price) : 'non ancora noto'}</span>
                <span className="lt-val t-3">{a ? `candela ${fmtUtc(a.candidateOpen)} · nota ${fmtUtc(a.availableAt)}` : 'si conosce solo alla conferma del pivot (2 barre dopo la candela)'}</span>
              </div>
            ))}
          </div>
          <p className="table-title" style={{ marginTop: 12 }}>
            Fatti noti fino a questo momento ({facts.length})
          </p>
          <ol className="move-facts">
            {[...facts].reverse().map((e, i) => (
              <li key={`${e.t}-${i}`}>
                <span className="mono t-3">{fmtUtc(e.t)}</span> · {describe(e)}
              </li>
            ))}
          </ol>
        </>
      )}
      <p className="footnote">
        {c.label}. Nessun esito 24h, prezzo d’uscita o operazione: i giudizi descrivono la lettura del movimento a quella chiusura.
      </p>
    </section>
  );
}
