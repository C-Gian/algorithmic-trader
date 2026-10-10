// Typed client for the adviser endpoints (/api/adviser/*). Payloads mirror src/algotrader/adviser/api.py and the
// algotrader.semantic.v2 / algotrader.adviser-evaluation.v1 records. Nothing here sizes, leverages or places orders.

export type Expected = "UP" | "DOWN" | "BALANCED" | "UNCERTAIN" | "UNAVAILABLE";

/** Packaged adviser releases selectable before Start (stored runs always show their pinned method). */
export type AdviserMethod = "v0.2" | "v0.3" | "v0.4" | "v0.5" | "v0.6";
export const METHODS: readonly AdviserMethod[] = ["v0.2", "v0.3", "v0.4", "v0.5", "v0.6"];

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
  /** v0.3 (MP-002) structural fields. */
  status?: "WATCH" | "ARMED" | "CONFIRMED";
  destination?: string | null;
  destination_type?: string;
  confirmed_at?: string | null;
}

/** v0.4 (MP-003) pre-confirmation local reaction anchor of an A scenario (inspection only). */
export interface AnchorState {
  epoch: number | null; status: string; published_at: string | null; ever_armed: boolean;
  destination_monitoring_from: string | null; previous: Record<string, string | null> | null;
  replacements: number; losses: number;
}

/** v0.5 (MP-004): the A RETURN local reference prepared by the first usable return (never a call or an entry). */
export interface ResponseWait {
  reference_bar: string; H0: string; L0: string; published_at: string; recovery_close: string;
  recovery_rule: string; contradiction_rule: string; bars_checked: number;
}

/** v0.6 (MP-005): the child entry attempt ended at its return reference; the scenario itself is NOT invalidated. */
export interface EntryEnded {
  reason: "INITIAL_RESPONSE_INCOMPATIBLE" | string; base: "CORRIDOR" | "HISTORICAL_ECONOMICS" | string; at: string;
  scenario_invalidated: false; text: string;
}

/** v0.3-v0.6 structural scenario with its child entry state (inspection; a WAIT is never a call). */
export interface ScenarioState {
  scenario_id: string; family: "A" | "B" | "C"; family_text: string; direction: "LONG" | "SHORT";
  status: "WATCH" | "ARMED" | "CONFIRMED"; antecedent: string; trigger_level: string | null;
  invalidation_level: string | null; destination: string | null; destination_type: string; original_expiry: string;
  confirmed_at: string | null; confirmed_deadline: string | null; progress_check_at: string | null;
  owner: string | null; discovery_owner: string | null; entry_state: string; call_id: string | null;
  waiting?: { text: string; corridor: [string, string] | null; stop_V: string; target_now: string;
              target_at_confirmation: string; wait_until: string; hard_deadline: string; remaining_wait_minutes: number | null;
              blockers: string[]; caps: { cap: string; since: string; zone_id: string }[];
              /** v0.5: WAIT_RETURN (waiting for a usable return) or WAIT_RESPONSE (reference prepared). */
              phase?: "WAIT_RETURN" | "WAIT_RESPONSE"; response?: ResponseWait };
  /** v0.4: the local reaction anchor and, after an anchor loss, the observation state (never an entry). */
  anchor?: AnchorState;
  observing?: { text: string; lost_anchor: Record<string, string | null> | null; original_expiry: string };
  /** v0.6: the entry attempt ended (INITIAL_RESPONSE_INCOMPATIBLE) while the scenario stays alive. */
  entry_ended?: EntryEnded;
}

/** One plain phrase per structural scenario state: observation, active anchor, confirmed wait - never "enter now". */
export function scenarioPhrase(s: ScenarioState): { tone: "info" | "warn" | "neutral" | "brand"; text: string } {
  if (s.observing) return { tone: "neutral", text: "Scenario under observation; waiting for a new completed reaction" };
  if (s.waiting?.phase === "WAIT_RESPONSE") {
    return { tone: "info", text: "Confirmed — return reference prepared; waiting for a local recovery (not a call)" };
  }
  if (s.waiting) return { tone: "info", text: "Confirmed — waiting for a usable price (not a call)" };
  if (s.entry_ended) {
    return { tone: "neutral", text: "Confirmed scenario — its entry attempt ended (no call from it); the scenario is not invalidated" };
  }
  if (s.status === "CONFIRMED") return { tone: "brand", text: "Confirmed scenario" };
  if (s.status === "ARMED") {
    const ep = s.anchor?.epoch ? ` (anchor ${s.anchor.epoch})` : "";
    return { tone: "warn", text: `Active reaction anchor${ep}: needs a later close beyond ${s.trigger_level ?? "K"}, invalid at ${s.invalidation_level ?? "V"}` };
  }
  return { tone: "neutral", text: "Watching for a clean reaction (no anchor yet)" };
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
  /** Presentation boundary (API): a non-current session never presents a usable entry; the saved status is kept. */
  presentation?: "NOT_CURRENT";
  entry_status_saved?: string;
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
  current?: boolean;
  method?: string;
  scenarios?: ScenarioState[];
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
    method?: string;
  };
  state: string;
  running: boolean;
  current?: boolean;
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
  /** Entry/thesis status stored with the call record at issue. */
  entry_status?: string;
  thesis_status?: string;
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
  /** Further stored revision fields (semantic.v2 call_revision); shown as recorded, never reconstructed. */
  changed?: string[];
  current_admissible_bounds?: [string, string] | null;
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
  start: (method?: AdviserMethod) =>
    fetch(`/api/adviser/live/start${method ? `?method=${method}` : ""}`, { method: "POST" }).then((r) => json<LiveStatus>(r)),
  methods: () => fetch("/api/adviser/methods").then((r) => json<{ default: string; note: string;
    methods: { method: string; label: string; purpose: string; status: string; model: string }[] }>(r)),
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
  CONDITIONAL_SCENARIO: "Conditional: a supported scenario (armed or confirmed) in one direction",
  WATCH_ONLY: "Only conditional watch hypotheses (not a forecast, not a call)",
  NO_QUALIFIED_STRUCTURE: "No qualified structure in the current conditions",
};

export const METHOD_TEXT: Record<string, string> = {
  "v0.2": "Original v0.2",
  "v0.3": "Revised v0.3 — confirmation then usable entry",
  "v0.4": "Candidate v0.4 — reaction anchor may be replaced before confirmation",
  "v0.5": "Candidate v0.5 — RETURN waits for a local recovery",
  "v0.6": "Candidate v0.6 — RETURN reference ends early when its confirmation is already impossible",
};

/** Release status shown beside a method choice (economic usefulness is unvalidated for every version). */
export const METHOD_STATUS: Record<string, { tone: "pos" | "info" | "warn"; text: string }> = {
  "v0.2": { tone: "pos", text: "Baseline" },
  "v0.3": { tone: "info", text: "Technically accepted" },
  "v0.4": { tone: "warn", text: "Engineering review pending" },
  "v0.5": { tone: "warn", text: "Engineering review pending" },
  "v0.6": { tone: "warn", text: "Engineering review pending" },
};

/** Short method identity shown on pins and results (never the current default). */
export const METHOD_PIN: Record<string, string> = {
  "v0.2": "MP-001 v0.2", "v0.3": "MP-002 v0.3", "v0.4": "MP-003 v0.4", "v0.5": "MP-004 v0.5", "v0.6": "MP-005 v0.6",
};

export const METHOD_PURPOSE: Record<string, string> = {
  "v0.2": "The accepted MP-001 adviser exactly as evaluated so far — the fixed historical baseline.",
  "v0.3": "MP-002: a confirmed continuation may wait for a later usable price inside its reaction corridor instead of being rejected at once; scenarios persist independently of entry.",
  "v0.4": "MP-003: before confirmation, a touch of the reaction stop invalidates only that reaction anchor; the same scenario waits for a newer, deeper completed reaction. Everything after confirmation is unchanged from v0.3.",
  "v0.5": "MP-004: in the A RETURN wait the first usable return no longer issues a call; it fixes one reference bar, and a call can only follow a later completed 1-minute close beyond that bar's favourable extreme without breaking its other extreme (first recovery evaluated once). Everything else is v0.4.",
  "v0.6": "MP-005: as v0.5, but right after the RETURN reference is fixed the entry attempt ends at once when no confirming close beyond it could lie in the usable corridor (historical and live) or, historically, in the fixed-cost economic region. Only the entry attempt ends — the scenario is not invalidated. Everything else is v0.5.",
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
