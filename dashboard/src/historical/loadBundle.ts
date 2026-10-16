/**
 * Import del bundle OBS-001 scelto dall'utente: validazione del formato con errori leggibili.
 * Nessun ripiego silenzioso sulle fixture della simulazione.
 */
import { BUNDLE_KIND, BUNDLE_SCHEMA, type StudyBundle } from '../contract/historical';

export class BundleError extends Error {}

const fail = (msg: string): never => {
  throw new BundleError(msg);
};

function isObj(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

export function parseBundle(text: string): StudyBundle {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return fail('Il file non è un JSON valido. Scegli il file obs001-bundle.json prodotto dal comando «process».');
  }
  if (!isObj(data)) return fail('Formato inatteso: il contenuto non è un oggetto JSON.');
  if (data.kind !== BUNDLE_KIND) return fail(`Non è un bundle OBS-001 (kind=${String(data.kind)}).`);
  if (data.schema !== BUNDLE_SCHEMA) return fail(`Versione di schema non supportata: ${String(data.schema)} (attesa ${BUNDLE_SCHEMA}).`);
  const conv = data.conventions;
  if (!isObj(conv) || typeof conv.id !== 'string' || !conv.id.startsWith('OBS-001/') || typeof conv.hash !== 'string') {
    return fail('Convenzioni assenti o non riconosciute nel bundle.');
  }
  const periods = data.periods;
  if (!isObj(periods) || ![periods.inputStart, periods.studyStart, periods.end].every((x) => Number.isInteger(x))) {
    return fail('Periodi del bundle mancanti o non validi.');
  }
  for (const key of ['bars', 'observations', 'events'] as const) {
    const section = data[key];
    if (!isObj(section) || !section['45m'] || !section['1D']) return fail(`Sezione «${key}» incompleta (servono le scale 45m e 1D).`);
  }
  const bars = data.bars as Record<string, Record<string, unknown[]>>;
  const obs = data.observations as Record<string, unknown[]>;
  for (const scale of ['45m', '1D']) {
    const b = bars[scale];
    const n = Array.isArray(b.open) ? b.open.length : -1;
    if (n <= 0) return fail(`Barre ${scale} assenti.`);
    for (const col of ['status', 'o', 'h', 'l', 'c', 'v']) {
      if (!Array.isArray(b[col]) || b[col].length !== n) return fail(`Colonna ${col} delle barre ${scale} incoerente.`);
    }
    if (!Array.isArray(obs[scale]) || obs[scale].length !== n) return fail(`Osservazioni ${scale} non allineate alle barre.`);
  }
  if (!Array.isArray(data.origins) || data.origins.length === 0) return fail('Nessuna origine di studio nel bundle.');
  const retro = data.retrospective;
  if (!isObj(retro) || !Array.isArray(retro.rows) || retro.rows.length !== data.origins.length || !isObj(retro.summary)) {
    return fail('Sezione retrospettiva assente o non allineata alle origini.');
  }
  if (!isObj(data.source) || typeof data.source.attribution !== 'string') return fail('Fonte dei dati non dichiarata nel bundle.');
  return data as unknown as StudyBundle;
}
