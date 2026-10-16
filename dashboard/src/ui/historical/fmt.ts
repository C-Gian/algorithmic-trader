import type { Measure } from '../../contract/historical';
import { formatNumber, formatSigned } from '../../lib/numbers';

export const REASON: Record<string, string> = {
  INSUFFICIENT_HISTORY: 'storia insufficiente',
  INCOMPLETE_INPUT: 'input incompleto (lacuna)',
  ZERO_DENOMINATOR: 'denominatore zero',
  NO_CONFIRMED_PIVOTS: 'pivot confermati insufficienti',
  ANCHORS_EQUAL: 'ancore uguali',
  ORIGIN_INCOMPLETE: 'barra di origine incompleta',
  A_NOT_POSITIVE: 'A45m nulla',
  A_UNAVAILABLE: 'A45m non disponibile',
  RIGHT_CENSORED: 'oltre la fine dell’input (censurato)',
  GAP: 'lacuna nel futuro',
};

export const reasonText = (r: string | null | undefined) => (r ? (REASON[r] ?? r) : '—');

export const STRUCTURE_LABEL: Record<string, string> = {
  UP: 'Crescente',
  DOWN: 'Decrescente',
  MIXED: 'Mista',
  UNAVAILABLE: 'Non disponibile',
};

export const RELATION_LABEL: Record<string, string> = {
  CONCORDANT: 'Concorde',
  OPPOSITE: 'Contraria',
  MIXED: '1D mista',
  UNAVAILABLE: '1D non disponibile',
  NOT_APPLICABLE: 'Non applicabile (45m non direzionale)',
};

/** Valore della misura oppure motivo dell'assenza; uno zero noto resta «0». */
export function measure(m: Measure | undefined, digits: number, opts: { signed?: boolean; suffix?: string } = {}): string {
  if (!m) return '—';
  if (m.v === null) return `n.d. · ${reasonText(m.r)}`;
  const s = opts.signed ? formatSigned(m.v, digits) : formatNumber(m.v, digits);
  return opts.suffix ? `${s} ${opts.suffix}` : s;
}

export const price = (x: number | null | undefined) => (x == null ? '—' : formatNumber(x, 2));
export const ratio = (x: number | null | undefined, digits = 3) => (x == null ? '—' : formatSigned(x, digits));
export const plain = (x: number | null | undefined, digits = 3) => (x == null ? '—' : formatNumber(x, digits));
