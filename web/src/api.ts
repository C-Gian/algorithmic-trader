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
  code_version?: string | null;
  code_version_label?: string;
  database?: string;
  schema_version: string;
  recorder_workers?: {
    alive: number;
    recent: { worker_id: string; current_session: string | null; heartbeat_age_seconds: number }[];
  };
  observation_workers?: { alive: number };
  corpus_workers?: { alive: number };
  adviser_workers?: { alive: number; active_sessions: number };
  capabilities?: Record<"core" | "market_replay" | "corpus" | "recorder" | "synthetic_replay" | "live_adviser", Capability>;
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

// ---- Real-market observation replay (algotrader.observe.v1; observation only) ----

export type ReplayRuntimeState =
  | "queued" | "preparing" | "running" | "finishing" | "pausing" | "paused" | "stepping" | "recovering"
  | "unresponsive" | "suspended" | "cancel_requested" | "completed" | "cancelled" | "failed";

export interface ChannelCoverage {
  channel: { source: string; family: string; series_id: string };
  covered_from: string;
  covered_until: string;
  expected_cadence: string | null;
}

export interface ObsSourceSummary {
  kind: "dataset" | "recording";
  source_id: string;
  source_schema: string | null;
  inst_id: string | null;
  index_id: string | null;
  source_status: string;
  coverage: ChannelCoverage[];
  warnings: string[];
  exclusions: string[];
  notes: string[];
  pending?: boolean; // source not yet verified/prepared by the worker
}

export interface Availability {
  basis: "MODELED" | "RECORDED";
  policy_id: string;
  measured: boolean;
  label: string;
  note: string;
}

export interface FeedIdentity {
  schema_version: string;
  contract_status: string;
  schema_revision: number;
  content_identity: string;
  ordered_event_hash: string;
  ordering_policy_id: string;
  event_count: number;
  event_counts: Record<string, number>;
}

export interface Verification {
  verified: boolean;
  method: string;
  problems: string[];
  checked_at: string;
}

export interface ReplayableSource {
  kind: "dataset" | "recording";
  source_id: string;
  inst_id: string | null;
  coverage_from: string | null;
  coverage_until: string | null;
  status: string;
  availability_basis: "MODELED" | "RECORDED";
  replayable: boolean;
  reason: string | null;
}

export interface Preflight {
  // Cheap preview only: verification and feed construction are durable worker-owned phases after launch.
  source: { kind: string; source_id: string; inst_id: string; coverage_from: string; coverage_until: string; source_status: string };
  verification: null;
  verification_note: string;
  feed: null;
  availability: { basis: string; label: string; policy_id: string | null; measured: boolean; note: string };
  reference: string;
}

// ---- Shared operational job contract (algotrader.ops.v1) ----

export type OpsHealth =
  | "progressing" | "waiting" | "alive_no_progress" | "compute_lost" | "unresponsive" | "recovering"
  | "suspended" | "finished" | "disconnected";

export interface OpsControl { enabled: boolean; reason: string | null }

export interface OpsPhase {
  phase: string;
  label: string;
  state: "done" | "current" | "pending";
  active_seconds: number; // compute time minus declared waits, over MEASURED spans only
  waiting_seconds: number; // declared waits (queue, pacing)
  wall_seconds: number;
  spans: number;
  interrupted_spans: number;
  unmeasured_spans: number; // spans whose active time is unknown (never counted as zero)
  active_complete: boolean;
}

export interface OpsAssurance {
  state: "not_checked" | "incomplete" | "passed" | "failed";
  detail?: string;
  validator?: string | null;
  validator_version?: string | null;
  scope?: string | null;
}

export interface Operation {
  contract: string;
  lifecycle_version?: number;
  status: string;
  phase: string | null;
  phase_label: string;
  health: OpsHealth;
  health_label: string;
  health_detail: string;
  assurance: OpsAssurance;
  generation: number;
  attempt: number;
  progress: {
    stage: string | null;
    done: number | null;
    total: number | null;
    unit: string | null;
    fraction: number | null;
    detail: string | null;
    waiting?: string | null;
    progress_seq: number;
    last_progress_at: string | null;
    last_progress_age_seconds?: number | null;
    stall_limit_seconds?: number | null;
  };
  eta?: { seconds: number | null; basis: string; scope: string };
  timeline: {
    current: { phase: string; label: string; started_at: string | null; wall_seconds: number | null;
               active_seconds: number | null; waiting_seconds: number | null; active_basis: string } | null;
    phases: OpsPhase[];
    active_seconds_total: number;
    waiting_seconds_total: number;
    unmeasured_spans: number;
    active_complete: boolean;
    definitions: Record<string, string>;
  };
  wall_seconds?: number;
  controls: Record<string, OpsControl>;
  supervisor?: Record<string, unknown>;
  suspension?: null | { at: string | null; reason: string; historical_status?: string };
  diagnostic_log?: { event: string; detail?: string; at?: string }[];
}

export interface ObsReplay {
  replay_id: string;
  kind: string;
  status: string;
  runtime_state: ReplayRuntimeState;
  runtime_detail: string;
  run_type_label?: string;
  configured: boolean;
  source: ObsSourceSummary;
  verification: Verification | null;
  availability: Availability | null;
  freshness_policy: { policy_id: string; note: string; bar_max_age: string; history_limit: number } | null;
  feed: FeedIdentity | null;
  clock_policy: string | null;
  control: { paused: boolean; step_budget: number; speed: number; unit: string };
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
  validation_passed: boolean | null;
  progress: {
    applied_events: number;
    committed_events?: number;
    computed_events?: number;
    total_events: number | null;
    information_time: string | null;
    last_event_id: string | null;
    snapshot_id: string | null;
    snapshot_digest: string | null;
    heartbeat_age_seconds: number | null;
    elapsed_seconds: number | null;
    eta_seconds: number | null;
    eta_basis: string;
  };
  code_version: string | null;
  code_version_label?: string;
  labels: string[];
  operation: Operation;
  assurance_summary?: AssuranceSummary;
  temporal?: TemporalView | null;
}

// ---- Causal temporal substrate (algotrader.temporal.v1; factual infrastructure, no adviser) ----

export interface TemporalTrack {
  track: string;
  family: string;
  horizon: string;
  role: string;
  newest_sealed: null | {
    record_id: string; status: string; known_at: string; interval_start: string; interval_end: string;
    valid: number; expected: number;
  };
  forming: { interval_start: string; valid: number; missing: number; rejected: number; expected: number }[];
  next_unsealed_start: string | null;
  late_excluded: number;
  sealed_by_status: Record<string, number>;
  retained: number;
  retention: number;
}

export interface TemporalView {
  note: string;
  contract: string;
  contract_revision: number;
  profile_id: string;
  profile_fingerprint: string;
  clock_policy: string;
  seal_policy: string;
  clock_end: string;
  closure_allowance: string;
  committed: null | {
    clock_time: string | null;
    admitted_cursor: number;
    pending_tie_time: string | null;
    next_deadline: string | null;
    dispatch_seq: number;
    counters: { sealed: number; late_excluded: number; dispatches: number; [k: string]: number };
    tracks: TemporalTrack[];
    readiness: { dependency: string; status: string; blockers: string[] }[];
  };
}

export interface AssuranceSummary {
  headline: string;
  run_validation: string | null;
  runtime?: { state: string | null; label: string };
  deep_validation: string;
  reference?: { state: string; label: string; earlier_match: string | null };
  latest_deep_validation: string | null;
  deep_validations: number;
  warnings: string[];
  limitations?: string[];
}

export interface DeepMismatch { cursor: number; at: string; kind: string; expected: string; reference: string }

export interface DeepValidation {
  validation_id: string;
  replay_id: string;
  kind: "deep_validation";
  validator: string;
  validator_version: string;
  scope: string;
  mode: string;
  status: string;
  phase: string | null;
  phase_label: string;
  health: OpsHealth;
  health_label: string;
  health_detail: string;
  generation: number;
  attempt: number;
  progress: { done: number | null; total: number; unit: string; fraction: number | null; saved_cursor: number | null;
              stage: string | null; last_progress_at: string | null };
  eta: { seconds: number | null; basis: string; scope: string };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  controls: { cancel: { enabled: boolean }; pause: { enabled: boolean }; resume: { enabled: boolean } };
  cancel_requested: boolean;
  paused: boolean;
  plan: { committed_cursor: number; total_events: number; cache_id: string; cache_manifest_sha256: string };
  comparisons: { compared: number; mismatches: number };
  result: null | { outcome: string; covered_events: number; target_events: number; comparison_cursors: number;
                   compared: number; mismatches: DeepMismatch[]; input_examined: string };
  error: string | null;
  recovery_log: RecoveryEntry[];
}

export interface FeedEventLite {
  event_id: string;
  channel: { source: string; family: string; series_id: string };
  kind: string;
  event_time: string;
  event_end_time: string | null;
  available_time: string;
  availability_basis: string;
  payload: Record<string, string | null> & { payload_type: string; reason?: string; detail?: string };
}

export interface ChannelState {
  channel: { source: string; family: string; series_id: string };
  channel_id: string;
  condition: "NEVER_SEEN" | "VALID" | "GAP" | "REJECTED" | "INVALID_ONLY";
  freshness: "UNKNOWN" | "FRESH" | "STALE" | "NOT_APPLICABLE";
  latest_valid: FeedEventLite | null;
  age_since_available: string | null;
  age_since_event_end: string | null;
  latest_slot_time: string | null;
  last_quality: FeedEventLite | null;
  quality_slots_since_valid: number;
  counts: Record<string, number>;
  beyond_coverage: boolean;
  history_len: number;
}

export interface ObservableState {
  snapshot_id: string;
  content_digest: string;
  as_of: string;
  information_cutoff: string;
  cursor: { applied_events: number; last_event_id: string | null };
  availability_policy_id: string;
  freshness_policy_id: string;
  feed_content_identity: string;
  channels: ChannelState[];
  labels: string[];
}

export interface ChannelChange {
  channel_id: string;
  new_events: number;
  condition_before: string;
  condition_after: string;
  freshness_before: string;
  freshness_after: string;
  latest_valid_before: string | null;
  latest_valid_after: string | null;
}

export interface Delivery {
  seq: number;
  event_id: string;
  channel_id: string;
  family: string;
  kind: string;
  event_time: string;
  event_end_time: string | null;
  available_time: string;
  quality_reason: string | null;
  snapshot_digest: string | null; // null for streaming runs (snapshots only at checkpoints)
  changes: ChannelChange[]; // empty for streaming runs (no per-event delta)
  payload: Record<string, string | null> | null;
}

export interface TradedBar {
  seq: number;
  event_time: string;
  available_time: string;
  kind: string;
  quality_reason: string | null;
  open?: string;
  high?: string;
  low?: string;
  close?: string;
  volume_base?: string;
  volume_base_ccy?: string;
}

export interface ObsManifest {
  replay_id: string;
  status: string;
  applied_events: number;
  total_events: number;
  final_as_of: string;
  final_snapshot_id: string;
  final_content_digest: string;
  source_reference: string;
  validation: { passed: boolean; checks: { name: string; passed: boolean; detail: string }[] };
  artifacts: { name: string; sha256: string; bytes: number; lines: number | null }[];
}

export interface ObsStateDoc {
  replay: ObsReplay;
  state: ObservableState | null;
}

const O = "/api/observations";

export const obsApi = {
  sources: () => req<{ data_root: string; datasets: ReplayableSource[]; recordings: ReplayableSource[] }>(`${O}/sources`),
  preflight: (kind: string, id: string) => req<Preflight>(`${O}/sources/${kind}/${encodeURIComponent(id)}`),
  start: (kind: string, id: string, speed: number) =>
    req<ObsReplay>(O, { method: "POST", body: JSON.stringify({ source_kind: kind, source_id: id, speed }) }),
  list: () => req<ObsReplay[]>(O),
  state: (id: string) => req<ObsStateDoc>(`${O}/${id}/state`),
  deliveries: (id: string, latest: number) => req<Delivery[]>(`${O}/${id}/deliveries?latest=${latest}`),
  bars: (id: string) => req<{ information_time: string | null; bars: TradedBar[] }>(`${O}/${id}/traded-bars`),
  manifest: (id: string) => req<ObsManifest>(`${O}/${id}/manifest`),
  pause: (id: string) => req<ObsReplay>(`${O}/${id}/pause`, { method: "POST" }),
  resume: (id: string) => req<ObsReplay>(`${O}/${id}/resume`, { method: "POST" }),
  step: (id: string) => req<ObsReplay>(`${O}/${id}/step`, { method: "POST" }),
  cancel: (id: string) => req<ObsReplay>(`${O}/${id}/cancel`, { method: "POST" }),
  setSpeed: (id: string, speed: number) =>
    req<ObsReplay>(`${O}/${id}/speed`, { method: "POST", body: JSON.stringify({ speed }) }),
};

export const deepApi = {
  list: (replayId: string) => req<DeepValidation[]>(`${O}/${replayId}/deep-validations`),
  launch: (replayId: string) => req<DeepValidation>(`${O}/${replayId}/deep-validations`, { method: "POST" }),
  assurance: (replayId: string) => req<AssuranceSummary>(`${O}/${replayId}/assurance`),
  cancel: (vid: string) => req<DeepValidation>(`${O}/deep-validations/${vid}/cancel`, { method: "POST" }),
  pause: (vid: string) => req<DeepValidation>(`${O}/deep-validations/${vid}/pause`, { method: "POST" }),
  resume: (vid: string) => req<DeepValidation>(`${O}/deep-validations/${vid}/resume`, { method: "POST" }),
  markdown: (vid: string) => text(`${O}/deep-validations/${vid}/report.md`),
  downloadUrl: (vid: string, fmt: "md" | "json") => `${O}/deep-validations/${vid}/report.${fmt}?download=true`,
};

export interface Capability {
  label: string;
  status: "available" | "unavailable" | "stalled";
  workers_alive: number | null;
  active_jobs: number | null;
}

// ---- Owner evaluation workbench: corpus preparation + observation-only evaluations ----

export interface StorageFamily {
  family: string;
  rows: number;
  pages: number;
  expected_rows: number | null;
  missing_rows: number | null;
  gaps: number;
  status: string;
  first_time: string | null;
  last_time: string | null;
}

export interface StorageSummary {
  total_bytes: number;
  raw_bytes: number;
  parquet_bytes: number;
  metadata_bytes: number;
  file_count: number;
  raw_page_count: number;
  quality_status: string;
  families: StorageFamily[];
  note: string;
}

export interface CorpusJob {
  job_id: string;
  chunk_id: string;
  plan_id: string;
  status: "queued" | "running" | "completed" | "cancelled" | "failed";
  runtime_state: "queued" | "running" | "cancel_requested" | "unresponsive" | "completed" | "cancelled" | "failed";
  operation: Operation;
  runtime_detail: string;
  cancel_requested: boolean;
  source: { source: string; base_url: string };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  attempt: number;
  max_attempts: number;
  recovery_log: RecoveryEntry[];
  recovery_behavior: string;
  lease_expired: boolean;
  outcome: string | null;
  dataset_id: string | null;
  error: string | null;
  progress: {
    phase?: string;
    detail?: string;
    windows_done?: number;
    windows_total?: number;
    pages?: number;
    bytes?: number;
    acquire_elapsed_seconds?: number;
    fraction: number | null;
    elapsed_seconds: number | null;
    heartbeat_age_seconds: number | null;
    eta_seconds: number | null;
    eta_basis: string;
  };
}

export interface CorpusChunk {
  chunk_id: string;
  label: string;
  start: string;
  end: string;
  preparable: boolean;
  note: string;
  status: "prepared" | "preparing" | "not_prepared" | "invalid" | "planned";
  source: string;
  inst_id: string;
  local: null | {
    dataset_id: string;
    manifest_sha256: string;
    base_url: string;
    quality_status: string;
    verification_ok: boolean;
    verification_problems: string[];
    verified_at: string | null;
    retrieved_at: string | null;
    bytes_on_disk: number;
    storage: StorageSummary;
    bound_at: string;
    bound_by_job: string | null;
    outcome: string;
    previous_dataset_id: string | null;
    usable: boolean;
    problem: string | null;
    reuse: string;
  };
  latest_job: CorpusJob | null;
}

export interface CorpusStatus {
  plan: {
    plan_id: string;
    plan_version: number;
    description: string;
    source: string;
    inst_id: string;
    bar: string;
    families: string[];
    chunk_rule: string;
    target: { start: string; end: string };
  };
  summary: { chunks: number; prepared: number; preparable: number; planned_locked: number; prepared_bytes: number };
  chunks: CorpusChunk[];
  recovery_behavior: string;
}

export interface Evaluation {
  evaluation_id: string;
  run_type: string;
  run_type_label: string;
  preset: string;
  notice: string;
  created_at: string;
  corpus: {
    plan_id: string;
    chunk_id: string;
    chunk_label: string;
    start: string;
    end: string;
    dataset_id: string;
    quality_status: string;
    bytes_on_disk: number;
    storage: StorageSummary;
    pack?: PackFacts;
  };
  replay: ObsReplay;
  report_available: boolean;
  report_terminal: boolean;
}

export interface CapabilityRow {
  label?: string;
  status: string;
  value?: null;
  reason: string;
}

export interface EvaluationReport {
  report_kind: string;
  report_format: string;
  run_type: string;
  notice: string;
  evaluation_id: string;
  replay_id: string;
  status: string;
  snapshot: boolean;
  captured_at: string | null;
  completion: "COMPLETE" | "INCOMPLETE";
  coverage: {
    requested: { start: string; end: string };
    final_information_time: string | null;
    committed_information_time: string | null;
    applied_events: number;
    total_events: number | null;
    fraction: number | null;
  };
  quality_status: string;
  runtime: {
    elapsed_seconds: number | null;
    throughput_events_per_second: number | null;
    attempts: number;
    max_attempts: number;
    recoveries: number;
  };
  validation: { ran: boolean; passed: boolean | null; outcome: string | null; validator?: string | null; scope?: string | null;
                checks: { name: string; passed: boolean; detail: string }[] };
  operation: null | { phase: string | null; health: string; assurance: OpsAssurance; active_seconds_total: number };
  stopped_at: null | { applied_events: number; total_events: number | null; information_time: string | null; reason: string | null };
  warnings: string[];
  capabilities: Record<string, CapabilityRow>;
  conclusion: { verdict: string; text: string };
  next_diagnostic: string;
  adviser?: AdviserSection | null;
  pack?: null | {
    pack_id: string; status: string; preset_id: string; feed_consumed: string;
    source_coverage: { expected_bar_slots: number; missing_or_rejected: number };
    windows: PackWindows; limitations: string[]; acknowledged_limitations?: boolean;
  };
}

export interface Dist { n: string; min: string | null; p25: string | null; median: string | null; p75: string | null; max: string | null }
export interface VariantOutcome {
  paths: number; status: Record<string, number>; exit_class: Record<string, number>; target_exits: number; stop_exits: number;
  guidance_exits: number; no_entry: number; ambiguous: number; censored: number; unresolved: number; sum_gross: string;
  sum_price_net: string; mean_price_net: string | null; sum_stress_price_net: string | null; price_net_bps_distribution: Dist;
  held_minutes_distribution: Dist; positive_price_net: number; nonpositive_price_net: number; total_net: string;
}
export interface AdviserCallRow {
  call_id: string; family: string; direction: string; issued_at: string; issue_reference: string; stop: string; target: string;
  target_type: string; structural_area: [string, string]; hard_deadline: string; entry_available_minutes: string;
  entry_reopens: number; terminal: string; terminal_reason: string | null; terminal_at: string | null;
  limiting_landmark: string | null; gain_bps: string | null; risk_bps: string | null;
}
export interface AdviserSection {
  section: string; pending?: boolean; text?: string;
  identity: Record<string, unknown>;
  windows: { warmup_start: string; evaluation: [string, string]; tail_end: string; clock_end: string; clock_end_reached: boolean };
  coverage: { evaluation_minutes: number; covered_minutes: number; assessable_minutes: number; unavailable_minutes: number;
              view_row_minutes: Record<string, number>; assessable_weeks: string; capabilities: Record<string, string> };
  calls: { count: number; warmup_calls_not_scored: number; per_evaluated_week: string; per_assessable_week: string | null;
           by_family: Record<string, number>; entry_available_minutes: Dist; entry_reopens: number;
           longest_no_call_interval_hours: string; terminal: Record<string, number>; list: AdviserCallRow[] };
  funnel: { births: Record<string, number>; arms: Record<string, number>; trigger_evaluations: number; issued: number;
            ends: Record<string, number>; end_reasons: Record<string, number>; rejection_blockers: Record<string, number>;
            slot_occupied: number; priority: number; conflicted: number;
            slot_priority_minutes?: Record<string, string> | null };
  /** WP-009 correction (report v2): overlapping named-condition durations from the durable accumulator. */
  condition_durations?: { available: boolean; covered_minutes?: string; note: string;
                          conditions?: Record<string, { minutes: string; fraction_of_covered: string | null; onsets: number }> };
  /** Room to the target frozen at trigger by stage (A impulse/reaction; B/C NOT_APPLICABLE). */
  room_erosion_staged?: { note: string; triggered_attempts: number; by_family: Record<string, Record<string, Dist>>;
                          list: Record<string, string | boolean | null>[]; truncated: number };
  gates: Record<string, Record<string, Dist>>;
  limiting_landmarks: Record<string, number>;
  outcomes: { note: string; variants: Record<string, VariantOutcome> };
  view_samples: Record<string, unknown>;
  diagnosis: string[];
  conclusion: { verdict: string; text: string };
}

// ---- Evaluation packs (algotrader.corpus-pack.v1; data preparation only, no adviser) ----

export interface PackWindow { start: string; end: string; scored: boolean; minutes: number }
export interface PackWindows { warmup: PackWindow; evaluation: PackWindow; tail: PackWindow; requested: { start: string; end: string } }
export interface PackCoverage { family: string; window: string; expected_slots: number | null; valid: number; missing: number; rejected: number }
export interface PackCapability { capability: string; status: string; detail: string }
export interface PackSourceSlice { dataset_id: string; start: string; end: string }
export interface PackFacts {
  pack_id: string; status: "READY" | "READY_WITH_LIMITATIONS"; windows: PackWindows; coverage: PackCoverage[];
  capabilities: PackCapability[]; limitations: string[]; sources: PackSourceSlice[];
  input_readiness_preview: Record<string, string | number>; clock_end: string; tail_end: string;
}
export interface PublishedPack {
  pack_id: string; usable: boolean; problem: string | null; status: "READY" | "READY_WITH_LIMITATIONS";
  created_at: string; event_count: number; limitations: string[]; coverage: PackCoverage[];
  capabilities: PackCapability[]; sources: PackSourceSlice[];
  storage: { source_package_bytes: number; pack_cache_bytes: number; pack_cache_partitions: number; note: string } | null;
  overlap: { overlapping_slots: number; identical_collapsed: number; gap_replaced_by_valid: number } | null;
  input_readiness_preview: Record<string, string | number> | null; clock_end: string | null;
}
export interface PackChild { kind: string; start: string; end: string; status: string; dataset_id?: string; bytes?: number; error?: string }
export interface PackJob {
  operation: Operation; job_id: string; preset_id: string; status: "queued" | "running" | "completed" | "cancelled" | "failed";
  cancel_requested: boolean; outcome: string | null; pack_id: string | null; children: PackChild[];
  downloaded: { children: number; bytes: number }; error: string | null; created_at: string; finished_at: string | null;
  plan: null | { slices: { dataset_id: string; start: string; end: string }[]; acquisitions: string[][] };
}
export interface PresetView {
  preset: { preset_id: string; label: string; default: boolean; evidence_class: string };
  preset_sha256: string; windows: PackWindows;
  classification: { label: string; note: string; portions: { class: string; start: string; end: string; contamination: string }[] };
  local: { dataset_id: string; start: string; end: string }[];
  needed: { start: string; end: string }[];
  estimate: { estimated_bytes: number | null; minutes: number; basis: string };
  published: PublishedPack | null; latest_job: PackJob | null; note: string; adviser: string;
}
export interface PresetsResponse {
  file: { schema_version: string; version: number; method: string; rules_version: string; register_sha256: string;
          capability_profile: Record<string, string> };
  presets: PresetView[]; months: { month: string; label: string; class: string }[]; note: string;
}

export interface PackListItem { pack_id: string; preset_id: string; status: "READY" | "READY_WITH_LIMITATIONS"; event_count: number; created_at: string; usable: boolean; problem: string | null }

export const packApi = {
  presets: () => req<PresetsResponse>("/api/corpus/presets"),
  list: () => req<PackListItem[]>("/api/corpus/packs"),
  selection: (months: string[]) => req<PresetView>(`/api/corpus/selection?months=${encodeURIComponent(months.join(","))}`),
  preparePreset: (presetId: string) => req<PackJob>(`/api/corpus/presets/${encodeURIComponent(presetId)}/prepare`, { method: "POST" }),
  prepareSelection: (months: string[]) => req<PackJob>("/api/corpus/selection/prepare", { method: "POST", body: JSON.stringify({ months }) }),
  cancel: (jobId: string) => req<PackJob>(`/api/corpus/pack-jobs/${jobId}/cancel`, { method: "POST" }),
  reportMarkdown: (jobId: string) => text(`/api/corpus/pack-jobs/${jobId}/report.md`),
  downloadUrl: (jobId: string, fmt: "md" | "json") => `/api/corpus/pack-jobs/${jobId}/report.${fmt}?download=true`,
};

async function text(path: string): Promise<string> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.text();
}

export const corpusApi = {
  status: () => req<CorpusStatus>("/api/corpus"),
  prepare: (chunkId: string) => req<CorpusJob>(`/api/corpus/chunks/${encodeURIComponent(chunkId)}/prepare`, { method: "POST" }),
  cancel: (jobId: string) => req<CorpusJob>(`/api/corpus/jobs/${jobId}/cancel`, { method: "POST" }),
  reportMarkdown: (jobId: string) => text(`/api/corpus/jobs/${jobId}/report.md`),
  downloadUrl: (jobId: string, fmt: "md" | "json") => `/api/corpus/jobs/${jobId}/report.${fmt}?download=true`,
};

export const obsReport = {
  markdown: (replayId: string) => text(`/api/observations/${replayId}/report.md`),
  downloadUrl: (replayId: string, fmt: "md" | "json") => `/api/observations/${replayId}/report.${fmt}?download=true`,
};

const E = "/api/evaluations";

export const evalApi = {
  list: () => req<Evaluation[]>(E),
  detail: (id: string) => req<Evaluation>(`${E}/${id}`),
  start: (chunkId: string, speed: number, paused: boolean) =>
    req<Evaluation>(E, { method: "POST", body: JSON.stringify({ chunk_id: chunkId, speed, paused }) }),
  startPack: (packId: string, speed: number, paused: boolean, acknowledge: boolean,
              runType: "observation_only" | "adviser_evaluation" = "observation_only") =>
    req<Evaluation>(E, { method: "POST", body: JSON.stringify({ pack_id: packId, speed, paused, acknowledge_limitations: acknowledge,
                                                              run_type: runType }) }),
  report: (id: string) => req<EvaluationReport>(`${E}/${id}/report.json`),
  reportMarkdown: (id: string) => text(`${E}/${id}/report.md`),
  downloadUrl: (id: string, fmt: "md" | "json") => `${E}/${id}/report.${fmt}?download=true`,
};

export const barsTail = (replayId: string, tail: number) =>
  req<{ information_time: string | null; bars: TradedBar[] }>(`${O}/${replayId}/traded-bars?tail=${tail}`);
