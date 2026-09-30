// Thin typed client for the FastAPI backend. Payloads mirror src/algotrader/contracts.py.

export type RunStatus = "queued" | "running" | "paused" | "completed" | "cancelled" | "failed";

export type RuntimeState =
  | "queued"
  | "running"
  | "pausing"
  | "paused"
  | "stepping"
  | "recovering"
  | "cancel_requested"
  | "completed"
  | "cancelled"
  | "failed";

export interface ControlEntry {
  at: string;
  command: string;
  [detail: string]: unknown;
}

export interface RecoveryEntry {
  at: string;
  attempt: number;
  event: string;
  detail: string;
}

export interface Run {
  run_id: string;
  status: RunStatus;
  runtime_state: RuntimeState;
  runtime_detail: string;
  config: { fault: string; fault_at_step: number; fixture_id: string; seed: number };
  control: { paused: boolean; step_budget: number; speed: number };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancel_requested: boolean;
  attempt: number;
  max_attempts: number;
  recovery_log: RecoveryEntry[];
  control_log: ControlEntry[];
  error: string | null;
  lease_owner: string | null;
  lease_expired: boolean;
  has_manifest: boolean;
  progress: {
    steps_done: number;
    total_steps: number;
    sim_time: string | null;
    heartbeat_at: string | null;
    heartbeat_age_seconds: number | null;
    elapsed_seconds: number | null;
    eta_seconds: number | null;
    eta_basis: string;
  };
}

export interface Health {
  status: string;
  version?: string;
  database?: string;
  schema_version: string;
  recorder_workers?: {
    alive: number;
    recent: { worker_id: string; current_session: string | null; heartbeat_age_seconds: number }[];
  };
  workers: {
    alive: number;
    alive_threshold_seconds: number;
    recent: { worker_id: string; heartbeat_age_seconds: number; current_run: string | null; alive: boolean }[];
  };
}

export interface Scenario {
  scenario_id: string;
  kind: string;
  label: string;
  rank: number;
}

export interface MarketView {
  view_id: string;
  as_of: string;
  validity: string;
  confidence: string;
  summary: string;
  horizons: { horizon: string; bias: string; freshness: string }[];
  scenarios: Scenario[];
  data_quality: { status: string; bars_since_valid: number };
}

export interface Decision {
  decision_id: string;
  as_of: string;
  proposed_action: string;
  permitted_action: string;
  blocking_reasons: string[];
  reason: string;
  target_quantity: string;
}

export interface Account {
  equity: string;
  realized_pnl: string;
  unrealized_pnl: string;
  fees_paid: string;
  mark_price: string | null;
  exposure_fraction: string;
  funding: string;
  position: { side: string; quantity: string; average_entry_price: string | null };
}

export interface Snapshot {
  run: Run;
  latest: {
    observation?: { available_time: string; close: string | null; quality: string };
    market_view?: MarketView;
    decision?: Decision;
    account?: Account;
  };
}

export interface PricePoint {
  step: number;
  time: string;
  close: string | null;
  quality: string;
  fill: string | null;
}

export interface JournalEvent<T> {
  seq: number;
  step: number;
  kind: string;
  sim_time: string;
  payload: T;
}

export interface ArtifactRef {
  name: string;
  path: string;
  sha256: string;
  rows: number | null;
}

export interface Manifest {
  schema_version: string;
  run_id: string;
  status: string;
  semantic_trace_hash: string;
  event_count: number;
  engine_version: string;
  validation: { passed: boolean; failed: string[] };
  artifacts: ArtifactRef[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${body}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listRuns: () => req<Run[]>("/api/runs"),
  startRun: (speed: number, fault: string) =>
    req<Run>("/api/runs", { method: "POST", body: JSON.stringify({ speed, fault }) }),
  cancelRun: (id: string) => req<Run>(`/api/runs/${id}/cancel`, { method: "POST" }),
  pauseRun: (id: string) => req<Run>(`/api/runs/${id}/pause`, { method: "POST" }),
  resumeRun: (id: string) => req<Run>(`/api/runs/${id}/resume`, { method: "POST" }),
  stepRun: (id: string) => req<Run>(`/api/runs/${id}/step`, { method: "POST" }),
  setSpeed: (id: string, speed: number) =>
    req<Run>(`/api/runs/${id}/speed`, { method: "POST", body: JSON.stringify({ speed }) }),
  health: () => req<Health>("/api/health"),
  snapshot: (id: string) => req<Snapshot>(`/api/runs/${id}/snapshot`),
  prices: (id: string) => req<PricePoint[]>(`/api/runs/${id}/prices`),
  decisions: (id: string) => req<JournalEvent<Decision>[]>(`/api/runs/${id}/events?kind=decision&limit=5000`),
  manifest: (id: string) => req<Manifest>(`/api/runs/${id}/manifest`),
};

// ---- Market-data datasets (read-only; algotrader.marketdata.v1) ----

export interface DatasetFamily {
  family: string;
  rows: number;
  first_time: string | null;
  last_time: string | null;
  status: string;
  expected_rows: number | null;
  missing_rows: number | null;
  gaps: number;
}

export interface DatasetSummary {
  dataset_id: string;
  schema_version: string;
  source: string;
  base_url: string;
  inst_id: string;
  requested: { start: string; end: string };
  retrieved_at: string;
  quality_status: string;
  families: DatasetFamily[];
  prior_versions: string[];
}

export interface QualityFinding {
  family: string;
  check: string;
  severity: string;
  count: number;
  detail: string;
  examples: string[];
}

export interface DatasetDetail {
  summary: DatasetSummary;
  manifest: {
    availability_policy: string;
    availability_policy_text: string;
    retrieval_started_at: string;
    retrieval_finished_at: string;
    code_version: string | null;
    raw_page_count: number;
    identity_basis: string;
    labels: string[];
    instrument: Record<string, string | null>;
    files: { name: string; sha256: string; bytes: number; rows: number | null }[];
  };
  quality: {
    status: string;
    scope_note: string;
    findings: QualityFinding[];
    families: { family: string; gaps: { first_missing_open_time: string; last_missing_open_time: string; missing_bars: number }[] }[];
  };
}

export const dataApi = {
  list: () => req<{ data_root: string; schema_version: string; datasets: DatasetSummary[] }>("/api/datasets"),
  detail: (id: string) => req<DatasetDetail>(`/api/datasets/${id}`),
  verify: (id: string) => req<{ ok: boolean; problems: string[] }>(`/api/datasets/${id}/verify`),
};

// ---- Public market recorder (no trading) ----

export interface RecorderSession {
  session_id: string;
  status: string;
  stop_requested: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  heartbeat_age_seconds: number | null;
  lease_expired: boolean;
  endpoints: { ws_public_url: string; ws_business_url: string; rest_base_url: string };
  channels: string[];
  max_duration_seconds: number | null;
  stats: {
    records?: number;
    per_channel?: Record<string, number>;
    last_recv_utc_ns?: number | null;
    connection_state?: Record<string, string>;
    subscribed?: string[];
    reconnects?: number;
    errors?: number;
    funding_fallback?: boolean;
  };
  error: string | null;
  session_path: string;
  manifest_status: string | null;
  report?: {
    duration_s: number;
    bars: { channel_key: string; completed_bars: number; delay_raw: { count: number; p50_s: number | null; max_s: number | null } }[];
    funding: { snapshots_ws: number; snapshots_poll: number };
    clock: { clock_quality: string; offset_estimate_ms_median: number | null };
    outages: unknown[];
  };
}

export const recorderApi = {
  list: () => req<{ data_root: string; sessions: RecorderSession[] }>("/api/recorder/sessions"),
  detail: (id: string) => req<RecorderSession>(`/api/recorder/sessions/${id}`),
  start: (minutes: number) =>
    req<RecorderSession>("/api/recorder/sessions", { method: "POST", body: JSON.stringify({ max_duration_minutes: minutes }) }),
  stop: (id: string) => req<RecorderSession>(`/api/recorder/sessions/${id}/stop`, { method: "POST" }),
};
