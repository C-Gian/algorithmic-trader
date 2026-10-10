// Display formatting shared by every view. Pure functions; no data is invented here.

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/(\.\d+)?(Z|\+00:00)$/, " UTC");
}

export function fmtNum(v: string | number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("en-US", { maximumFractionDigits: digits }) : String(v);
}

export function fmtInt(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : v.toLocaleString("en-US");
}

/** Short duration: 4.2s · 3m 12s · 2h 05m. */
export function fmtSecs(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  return `${Math.floor(s / 3600)}h ${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}m`;
}

export function fmtNs(ns: number | null | undefined): string {
  if (!ns) return "—";
  return new Date(ns / 1e6).toISOString().replace("T", " ").replace("Z", " UTC");
}

export function fmtBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

export function speedLabel(v: number): string {
  return v === 0 ? "max" : `${v} bar${v === 1 ? "" : "s"}/s`;
}

/** Human label for snake_case identifiers (runtime states etc.). */
export function humanize(s: string): string {
  return s.replace(/_/g, " ");
}

export function shortId(id: string, keep = 10): string {
  return id.length <= keep + 1 ? id : `${id.slice(0, keep)}…`;
}

const LOCAL_TIME = new Intl.DateTimeFormat("it-IT", {
  day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  timeZoneName: "short",
});

/** Readable local date/time with an identifiable time zone (e.g. 01/09/2025, 07:07:01 CEST); precise UTC stays in fmtTime. */
export function fmtLocal(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(/(\.\d{3})\d+/, "$1"));
  return Number.isNaN(d.getTime()) ? iso : LOCAL_TIME.format(d);
}
