// Typed client for the adviser endpoints (/api/adviser/*). Payloads mirror src/algotrader/adviser/api.py and the
// algotrader.semantic.v2 / algotrader.adviser-evaluation.v1 records. Nothing here sizes, leverages or places orders.

export type Expected = "UP" | "DOWN" | "BALANCED" | "UNCERTAIN" | "UNAVAILABLE";

export interface ScenarioView {
  scenario_id: string;
  family: "A" | "B" | "C";
  direction: "LONG" | "SHORT";
  antecedent: string;
  trigger_level: string | null;
  invalidation_level: string | null;
  conditional_target: string;
  alternative: string;
  expires_at: string | null;
  candidate_domain: string;
}

export interface MarketViewDoc {
  observed_context: string;
  phase: string;
  expected_direction: Expected;
  conditional: boolean;
  table_row: string;
  principal: ScenarioView | null;
  alternatives: ScenarioView[];
  ongoing_call_id: string | null;
  horizon_minutes: [number, number] | null;
  levels: Record<string, string | null>;
  reasons: string[];
  counterevidence: string[];
  blockers: string[];
}

export interface CallView {
  call_id: string;
  family: "A" | "B" | "C";
  family_text: string;
  direction: "LONG" | "SHORT";
  origin: string;
  issued_at: string;
  issue_reference: string;
  target: string;
  target_type: string;
  stop: string;
  structural_area: [string, string];
  admissible_bounds: [string, string] | null;
  entry_status: "AVAILABLE" | "CLOSED" | "UNVERIFIED";
  entry_reasons: string[];
  thesis_status: string;
  hard_deadline: string;
  remaining_minutes: number;
  expected_minutes: [number, number];
  duration_window: [number, number] | null;
  progress_check_at: string;
  premise: string;
  limiting_landmark: Record<string, string | null> | null;
  revision: number;
  guidance: string;
}

export interface Lens {
  lens: string;
  name: string;
  result: unknown;
  role: string;
  status: string;
  detail?: Record<string, unknown>;
  since?: string | null;
}

export interface LiveView {
  status: string;
  connected: boolean;
  live_since: string | null;
  last_receipt: string | null;
  run_id: string | null;
  clock: string | null;
  origin: string;
  market_view: MarketViewDoc | null;
  call: CallView | null;
  lenses: Lens[];
  recent_calls: { call_id: string; family: string; direction: string; issued_at: string; terminal: string;
                  reason: string; terminal_at: string; origin: string }[];
  attempts: { attempt_id: string; family: string; direction: string; status: string; trigger_level: string | null;
              invalidation_level: string | null; expires_at: string; owner: string | null }[];
  box: Record<string, unknown> | null;
  readiness: { name: string; status: string; latest_ref: string | null; event_end: string | null; known_at: string | null }[];
  levels: Record<string, string | null> | null;
  chart: { minutes: { t: string; o: string; h: string; l: string; c: string }[]; m15: unknown[][] };
  notes: { at: string; event: string; [k: string]: unknown }[];
  counters: Record<string, number | null>;
  stale_session?: boolean;
}

export interface LiveAlert {
  alert_key: string;
  change_type: string;
  subject_id: string;
  summary: string;
  acknowledged: boolean;
  created_at: string;
}

export interface LiveStatus {
  session: null | {
    session_id: string; status: string; phase: string | null; created_at: string; started_at: string | null;
    stopped_at: string | null; stop_requested: boolean; error: string | null; identity: Record<string, unknown> | null;
    heartbeat_age_seconds: number | null; progress: Record<string, unknown>; connection: Record<string, unknown>;
    notes: { at: string; event: string; [k: string]: unknown }[];
  };
  state: string;
  running: boolean;
  message: string;
  view: LiveView | null;
  alerts: LiveAlert[];
  notice: string;
}

export interface CallRecord {
  call_id: string;
  attempt_id: string;
  family: string;
  direction: string;
  thesis: string;
  issued_at: string;
  issue_reference: string;
  invalidation: string;
  target: string;
  target_type: string;
  structural_area: [string, string];
  expected_minutes: [number, number];
  hard_deadline: string;
  premise: string;
  env: { factual_cursor: number; origin: string; published_at: string };
  actionability: { gain_bps: string | null; risk_bps: string | null; cost_envelope_bps: string | null;
                   admissible_bounds: [string, string] | null; side_price: string | null; side_price_source: string | null };
  limiting_landmark: Record<string, string | null> | null;
}

export interface RevisionRecord {
  call_id: string;
  revision: number;
  entry_status: string;
  entry_reasons: string[];
  thesis_status: string;
  terminal_reason: string | null;
  guidance: string;
  remaining_minutes: string | null;
  env: { published_at: string };
}

export interface PathRecord {
  path_id: string;
  variant: string;
  status: string;
  exit_class: string | null;
  entry: { price: string; time_start: string } | null;
  exit: { price: string; reason: string; time_start: string; time_end: string } | null;
  gross: string | null;
  price_net: string | null;
  stress_price_net: string | null;
  total_net: string | null;
  funding_status: string;
  bounds: Record<string, string | null>;
  held_minutes: string | null;
}

export interface CallDetail {
  call: CallRecord | null;
  candidate: { transition: string; reason: string | null; status: string; trigger_level: string | null;
               invalidation_level: string | null; setup: Record<string, string | null>; env: { published_at: string } }[];
  actionability: Record<string, unknown>[];
  revisions: RevisionRecord[];
  material_changes: { change_type: string; summary: string; env: { published_at: string } }[];
  market_view_at_issue: MarketViewDoc | null;
  hypothetical_paths: PathRecord[];
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 300)}`);
  return r.json() as Promise<T>;
}

export const adviserApi = {
  live: () => fetch("/api/adviser/live").then((r) => json<LiveStatus>(r)),
  start: () => fetch("/api/adviser/live/start", { method: "POST" }).then((r) => json<LiveStatus>(r)),
  stop: () => fetch("/api/adviser/live/stop", { method: "POST" }).then((r) => json<LiveStatus>(r)),
  reassess: () => fetch("/api/adviser/live/reassess", { method: "POST" }).then((r) => json<LiveStatus>(r)),
  ack: (key: string) => fetch(`/api/adviser/live/alerts/${encodeURIComponent(key)}/ack`, { method: "POST" })
    .then((r) => json<LiveStatus>(r)),
  analysis: () => fetch("/api/adviser/live/analysis.md").then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status))))),
  calls: (replayId: string) => fetch(`/api/adviser/runs/${replayId}/calls`).then((r) => json<{ calls: { call: CallRecord;
    revisions: RevisionRecord[]; hypothetical_paths: PathRecord[] }[] }>(r)),
  call: (replayId: string, callId: string) =>
    fetch(`/api/adviser/runs/${replayId}/calls/${encodeURIComponent(callId)}`).then((r) => json<CallDetail>(r)),
  window: (replayId: string, cursor: number, before = 600, after = 900) =>
    fetch(`/api/adviser/runs/${replayId}/window?cursor=${cursor}&before=${before}&after=${after}`)
      .then((r) => json<{ bars: { t: string; o: string; h: string; l: string; c: string }[] }>(r)),
};

export const EXPECTED_TEXT: Record<string, string> = {
  UP: "Up", DOWN: "Down", BALANCED: "Balanced", UNCERTAIN: "Uncertain", UNAVAILABLE: "Unavailable",
};

export const ROW_TEXT: Record<string, string> = {
  REQUIRED_CONTEXT_UNAVAILABLE: "Required 15m/1h context is not ready",
  OPPOSING_SCENARIOS: "Scenarios point in opposite directions",
  ONGOING_CALL: "Following the ongoing call while its premise survives",
  ARMED_SCENARIO: "Conditional: a call only if the trigger happens",
  BALANCED_RANGE: "Balanced range",
  NO_SUPPORTED_PLAN: "No supported plan in the current conditions",
};

export const THESIS_TEXT: Record<string, string> = {
  ONGOING: "Ongoing", TARGET_REACHED: "Target reached", INVALIDATED: "Invalidated", TIME_EXPIRED: "Time expired",
  UNASSESSABLE: "Unassessable", RETIRED: "Retired (guidance withdrawn)",
};

/** Plain sentence-case text for a machine reason code (the code itself stays in technical details). */
export function reasonText(code: string): string {
  const head = code.split(":")[0].toLowerCase().replace(/_/g, " ");
  return head.charAt(0).toUpperCase() + head.slice(1);
}

export const ENTRY_TEXT: Record<string, string> = {
  AVAILABLE: "Entry valid now", CLOSED: "Entry closed now", UNVERIFIED: "Entry cannot be verified now",
};
