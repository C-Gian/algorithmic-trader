import { createContext, ReactNode, useContext } from "react";
import { api, Capability, Health } from "../api";
import { usePoll } from "../lib/usePoll";
import { Tone } from "../ui/primitives";

// One application-wide health poll shared by the shell and every view.

interface HealthState {
  health: Health | null;
  error: string | null;
  loading: boolean;
}

const Ctx = createContext<HealthState>({ health: null, error: null, loading: true });

export function HealthProvider({ children }: { children: ReactNode }) {
  const { data, error, loading } = usePoll(api.health, 3000);
  return <Ctx.Provider value={{ health: error ? null : data, error, loading }}>{children}</Ctx.Provider>;
}

export function useHealth(): HealthState {
  return useContext(Ctx);
}

export interface SystemVerdict {
  tone: Tone;
  label: string;
  detail: string;
}

export const CAPABILITY_ORDER = ["market_replay", "corpus", "recorder", "synthetic_replay"] as const;
export type CapabilityKey = (typeof CAPABILITY_ORDER)[number];

export function capabilityTone(c: Capability | undefined): Tone {
  if (!c) return "neutral";
  return c.status === "available" ? "pos" : c.status === "stalled" ? "warn" : "neutral";
}

export function capabilityLabel(c: Capability | undefined): string {
  if (!c) return "Unknown";
  return c.status === "available" ? "Available" : c.status === "stalled" ? "Jobs waiting · no worker" : "Worker offline";
}

/**
 * Capability-aware verdict from the real /api/health response. Core (API + database) down is an outage;
 * a missing optional worker only limits that capability and is never shown as a whole-system outage.
 */
export function systemVerdict({ health, error, loading }: HealthState): SystemVerdict {
  if (loading && !health) return { tone: "neutral", label: "Checking", detail: "Contacting the API…" };
  if (!health || error) return { tone: "neg", label: "Unreachable", detail: "The API is not responding." };
  const caps = health.capabilities;
  if (!caps) {
    return health.workers.alive === 0
      ? { tone: "warn", label: "Limited", detail: "API up · no live run worker." }
      : { tone: "pos", label: "Operational", detail: "API and database up." };
  }
  // Older APIs may not report every capability; a missing entry is simply not listed.
  const known = CAPABILITY_ORDER.filter((k) => caps[k]);
  const stalled = known.filter((k) => caps[k].status === "stalled").map((k) => caps[k].label);
  const off = known.filter((k) => caps[k].status === "unavailable").map((k) => caps[k].label);
  if (stalled.length) {
    return { tone: "warn", label: "Degraded", detail: `Jobs waiting without a worker: ${stalled.join(", ")}.` };
  }
  if (off.length) {
    return { tone: "info", label: "Limited", detail: `API and database up · worker offline: ${off.join(", ")}.` };
  }
  return { tone: "pos", label: "Operational", detail: "API, database and every capability worker are up." };
}
