/**
 * Dati di mercato FITTIZI, già preparati per la visualizzazione.
 *
 * Nessun dato reale, nessuna rete. Le candele sono scritte a mano attorno all'esempio
 * contabile del task (ingresso 60.000, valutazione 61.000, chiusura 60.500). Le "medie"
 * sono curve illustrative definite per punti di ancoraggio: non sono calcolate dai prezzi
 * e i loro parametri sono solo etichette d'esempio.
 */

export type Ohlcv = readonly [open: number, high: number, low: number, close: number, volume: number];

/** Prima apertura intraday: 14 ott 2026 10:30 UTC. Passo 45 minuti. */
export const INTRADAY_START = Date.UTC(2026, 9, 14, 10, 30);
export const INTRADAY_STEP_MS = 45 * 60 * 1000;

/** 39 candele 45m del percorso LONG (14 ott 10:30Z → 15 ott 15:45Z). */
export const INTRADAY_LONG: readonly Ohlcv[] = [
  [59850, 59910, 59820, 59880, 92],
  [59880, 59985, 59797, 59950, 121.6],
  [59950, 60010, 59930, 59990, 112.5],
  [59990, 59995, 59691, 59760, 103.4],
  [59760, 59818, 59558, 59620, 94.3],
  [59620, 59655, 59425, 59480, 123.2],
  [59480, 59552, 59302, 59350, 114.1],
  [59350, 59360, 59250, 59300, 105],
  [59300, 59506, 59266, 59420, 96.6],
  [59420, 59623, 59333, 59560, 125.5],
  [59560, 59740, 59480, 59700, 116.4],
  [59700, 59917, 59627, 59840, 107.3],
  [59840, 60000, 59800, 59960, 98.2],
  [59960, 59985, 59721, 59780, 127.1],
  [59780, 59848, 59588, 59640, 118],
  [59640, 59685, 59475, 59520, 109.6],
  [59520, 59540, 59420, 59480, 100.5],
  [59480, 59659, 59449, 59600, 129.4],
  [59600, 59756, 59516, 59720, 120.3],
  [59720, 59923, 59643, 59850, 111.2],
  [59850, 60000, 59820, 59930, 102.1],
  [59930, 59985, 59727, 59790, 93],
  [59790, 59854, 59644, 59700, 122.6],
  [59700, 59741, 59605, 59640, 113.5],
  [59640, 59710, 59600, 59660, 104.4],
  [59660, 59795, 59625, 59740, 95.3],
  [59740, 59842, 59652, 59810, 124.2],
  [59810, 59949, 59729, 59880, 115.1],
  [59880, 59990, 59870, 59940, 106],
  [59940, 59985, 59793, 59860, 97.6],
  [59860, 59920, 59710, 59770, 126.5],
  [59770, 59857, 59717, 59820, 102.4],
  [59820, 60240, 59800, 60180, 168.1],
  [60180, 60260, 60070, 60120, 121.6],
  [60120, 60520, 59960, 60450, 142.3],
  [60450, 61080, 60400, 61000, 155],
  [61000, 61150, 60850, 61000, 118],
  [61000, 61120, 60820, 61000, 104.2],
  [61000, 61050, 60430, 60500, 131.5],
];

/** Prima apertura giornaliera sintetica: 6 set 2026 (UTC). */
export const DAILY_START = Date.UTC(2026, 8, 6);
export const DAY_MS = 24 * 60 * 60 * 1000;

/** 38 giorni sintetici, 6 set → 13 ott. Il 14 e il 15 ott si ricavano dal segmento intraday. */
export const DAILY_SYNTHETIC_LONG: readonly Ohlcv[] = [
  [56500, 56980, 56340, 56800, 2600],
  [56800, 57401, 56593, 57150, 2989],
  [57150, 57472, 56766, 57020, 3378],
  [57020, 57873, 56719, 57480, 2767],
  [57480, 58144, 57132, 57900, 3156],
  [57900, 58215, 57255, 57650, 3545],
  [57650, 58506, 57448, 58120, 2934],
  [58120, 58637, 57871, 58400, 3323],
  [58400, 58708, 57964, 58260, 2712],
  [58260, 59129, 57917, 58750, 3101],
  [58750, 59330, 58360, 59100, 3490],
  [59100, 59401, 58683, 58880, 2879],
  [58880, 59692, 58636, 59320, 3268],
  [59320, 59873, 59029, 59650, 2657],
  [59650, 59944, 59142, 59480, 3046],
  [59480, 60265, 59095, 59900, 3435],
  [59900, 60466, 59708, 60250, 2824],
  [60250, 60537, 59841, 60080, 3213],
  [60080, 60878, 59794, 60520, 2602],
  [60520, 61109, 60187, 60900, 2991],
  [60900, 61180, 60270, 60650, 3380],
  [60650, 61451, 60463, 61100, 2769],
  [61100, 61582, 60866, 61380, 3158],
  [61380, 61653, 60919, 61200, 3547],
  [61200, 61794, 60872, 61450, 2936],
  [61450, 61645, 60925, 61300, 3325],
  [61300, 61566, 60868, 61050, 2714],
  [61050, 61737, 60821, 61400, 3103],
  [61400, 61588, 60974, 61250, 3492],
  [61250, 61759, 60927, 61500, 2881],
  [61500, 62000, 61130, 61700, 3270],
  [61700, 61850, 60923, 61100, 2659],
  [61100, 61400, 60876, 61250, 3048],
  [61250, 61300, 60229, 60500, 3437],
  [60500, 60894, 59482, 59800, 2826],
  [59800, 60045, 59150, 59400, 3215],
  [59400, 60016, 59228, 59700, 2604],
  [59700, 60060, 59481, 59950, 2993],
];

/** Parte sintetica del 14 ott prima dell'inizio del segmento intraday (00:00–10:30 UTC). */
export const DAY_OCT14_BEFORE_INTRADAY_LONG = { open: 59950, high: 60050, low: 59780, volume: 1210 } as const;

/** Ancoraggi [indice candela, valore] delle curve illustrative sul 45m. */
export const MA_FAST_45M_ANCHORS: readonly (readonly [number, number])[] = [
  [0, 59820], [4, 59760], [8, 59600], [12, 59700], [16, 59640], [20, 59720], [24, 59700], [28, 59770],
  [31, 59760], [32, 59880], [33, 59960], [34, 60100], [35, 60420], [36, 60780], [37, 60800], [38, 60760],
];
export const MA_SLOW_45M_ANCHORS: readonly (readonly [number, number])[] = [
  [0, 59700], [8, 59680], [16, 59660], [24, 59690], [31, 59740], [32, 59790], [33, 59850], [34, 59940],
  [35, 60120], [36, 60310], [37, 60420], [38, 60480],
];
export const MA_FAST_1D_ANCHORS: readonly (readonly [number, number])[] = [
  [0, 56600], [10, 58300], [20, 60200], [30, 61300], [33, 61000], [36, 60300], [39, 60000],
];
export const MA_SLOW_1D_ANCHORS: readonly (readonly [number, number])[] = [
  [0, 55900], [10, 57300], [20, 58900], [30, 60200], [36, 60300], [39, 60250],
];

/** Interpolazione lineare tra punti d'ancoraggio scritti a mano (nessun prezzo in ingresso). */
export function interpolateAnchors(anchors: readonly (readonly [number, number])[], length: number): number[] {
  const values: number[] = [];
  for (let i = 0; i < length; i++) {
    const nextIdx = anchors.findIndex(([idx]) => idx >= i);
    if (nextIdx === -1) {
      values.push(anchors[anchors.length - 1][1]);
      continue;
    }
    if (nextIdx === 0) {
      values.push(anchors[0][1]);
      continue;
    }
    const [i0, v0] = anchors[nextIdx - 1];
    const [i1, v1] = anchors[nextIdx];
    values.push(Math.round(v0 + ((v1 - v0) * (i - i0)) / (i1 - i0)));
  }
  return values;
}

/** Centro di simmetria della variante SHORT: ogni prezzo p diventa 2·60.000 − p. */
export const MIRROR_AXIS = 60000;
export const mirrorPrice = (p: number): number => 2 * MIRROR_AXIS - p;
export function mirrorOhlcv([o, h, l, c, v]: Ohlcv): Ohlcv {
  return [mirrorPrice(o), mirrorPrice(l), mirrorPrice(h), mirrorPrice(c), v];
}
