// Thin typed client for the FastAPI backend. Payloads mirror src/algotrader/contracts.py.

export type RunStatus = "queued" | "running" | "completed" | "cancelled" | "failed";

export interface RecoveryEntry {
  at: string;
  attempt: number;
  event: string;
  detail: string;
}

export interface Run {
  run_id: string;
  status: RunStatus;
  config: { speed: number; fault: string; fault_at_step: number; fixture_id: string; seed: number };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancel_requested: boolean;
  attempt: number;
  max_attempts: number;
  recovery_log: RecoveryEntry[];
  error: string | null;
  lease_expired: boolean;
  has_manifest: boolean;
  progress: {
    steps_done: number;
    total_steps: number;
    sim_time: string | null;
    heartbeat_at: string | null;
    heartbeat_age_seconds: number | null;
    elapsed_seconds: number | null;
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
  snapshot: (id: string) => req<Snapshot>(`/api/runs/${id}/snapshot`),
  prices: (id: string) => req<PricePoint[]>(`/api/runs/${id}/prices`),
  decisions: (id: string) => req<JournalEvent<Decision>[]>(`/api/runs/${id}/events?kind=decision&limit=5000`),
  manifest: (id: string) => req<Manifest>(`/api/runs/${id}/manifest`),
};
