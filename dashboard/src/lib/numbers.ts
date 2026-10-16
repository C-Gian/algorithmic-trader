/**
 * Formattazione numerica italiana (punto per le migliaia, virgola decimale) con
 * raggruppamento sempre attivo, anche sotto 10.000. Solo visualizzazione.
 */
export function formatNumber(value: number, decimals = 0): string {
  const negative = value < 0 || Object.is(value, -0);
  const fixed = Math.abs(value).toFixed(decimals);
  const [intPart, decPart] = fixed.split('.');
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const body = decPart ? `${grouped},${decPart}` : grouped;
  return negative && Number(fixed) !== 0 ? `−${body}` : body;
}

/** Con segno esplicito: +10,00 / −0,60 / 0,00. */
export function formatSigned(value: number, decimals = 2): string {
  const body = formatNumber(Math.abs(value), decimals);
  if (Number(Math.abs(value).toFixed(decimals)) === 0) return body;
  return value > 0 ? `+${body}` : `−${body}`;
}

export const formatBtc = (qty: number): string => `${formatNumber(qty, 5)} BTC`;
export const formatPrice = (price: number): string => formatNumber(price, 0);
