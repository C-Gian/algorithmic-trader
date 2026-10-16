import type { MissingReason } from '../contract/types';

const ZONE = 'Europe/Rome';
const timeFmt = new Intl.DateTimeFormat('it-IT', { timeZone: ZONE, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
const hmFmt = new Intl.DateTimeFormat('it-IT', { timeZone: ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const dateFmt = new Intl.DateTimeFormat('it-IT', { timeZone: ZONE, day: 'numeric', month: 'short', year: 'numeric' });
const dayFmt = new Intl.DateTimeFormat('it-IT', { timeZone: ZONE, day: '2-digit', month: 'short' });
const zoneFmt = new Intl.DateTimeFormat('en-GB', { timeZone: ZONE, timeZoneName: 'short' });

/** Fuso leggibile scelto dall'interfaccia; il contratto resta in UTC. */
export const fmtTime = (iso: string) => timeFmt.format(new Date(iso));
export const fmtHm = (iso: string) => hmFmt.format(new Date(iso));
export const fmtDate = (iso: string) => dateFmt.format(new Date(iso)).replace('.', '');
export const fmtDay = (iso: string) => dayFmt.format(new Date(iso)).replace('.', '');

/* UTC esplicito per lo studio storico: le chiusure non seguono il fuso locale. */
const utcDateTime = new Intl.DateTimeFormat('it-IT', { timeZone: 'UTC', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const utcHm = new Intl.DateTimeFormat('it-IT', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const utcDay = new Intl.DateTimeFormat('it-IT', { timeZone: 'UTC', day: '2-digit', month: 'short' });
export const fmtHmUtc = (iso: string) => utcHm.format(new Date(iso));
export const fmtDayUtc = (iso: string) => utcDay.format(new Date(iso)).replace('.', '');
/** «01 set 2025, 00:45 UTC» da millisecondi epoch. */
export const fmtUtc = (ms: number) => `${utcDateTime.format(new Date(ms)).replace('.', '')} UTC`;
/** «2025-09-01T00:45Z»: forma compatta e non ambigua. */
export const isoMinute = (ms: number) => new Date(ms).toISOString().slice(0, 16) + 'Z';

/** CEST/CET (Europe/Rome). */
export function tzAbbr(iso: string): string {
  const name = zoneFmt.formatToParts(new Date(iso)).find((p) => p.type === 'timeZoneName')?.value ?? '';
  if (name === 'CEST' || name === 'GMT+2') return 'CEST';
  if (name === 'CET' || name === 'GMT+1') return 'CET';
  return name;
}

export function fmtAgo(fromIso: string, toIso: string): string {
  const s = Math.max(0, Math.round((Date.parse(toIso) - Date.parse(fromIso)) / 1000));
  if (s < 60) return `${s} s fa`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min fa`;
  return `${Math.floor(m / 60)} h ${m % 60} min fa`;
}

export const REASON_LABEL: Record<MissingReason, string> = {
  NOT_APPLICABLE: 'Non applicabile',
  NOT_PROVIDED: 'Non simulato',
  STALE: 'Non aggiornato',
  UNAVAILABLE: 'Non disponibile',
};

