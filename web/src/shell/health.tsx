import { createContext, ReactNode, useContext } from "react";
import { api, Health } from "../api";
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

/** Operational verdict derived only from the real /api/health response. */
export function systemVerdict({ health, error, loading }: HealthState): SystemVerdict {
  if (loading && !health) return { tone: "neutral", label: "Checking", detail: "Contacting the API…" };
  if (!health || error) return { tone: "neg", label: "Unreachable", detail: "The API is not responding." };
  if (health.workers.alive === 0) {
    return { tone: "warn", label: "Degraded", detail: "API up · no live run worker — replays cannot progress." };
  }
  return { tone: "pos", label: "Operational", detail: `API and database up · ${health.workers.alive} run worker alive` };
}
