import { useEffect, useState } from "react";

// Minimal hash routing. Refreshing any section/deep link returns to the same view.
//
//   ""  | #market                  → Market overview (default landing)
//   #replay | #replay/run=<id>     → Replay Lab (legacy #run=<id> still opens the run)
//   #data   | #data=<id>           → Data workspace
//   #recorder                      → Recorder

export type Section = "market" | "replay" | "data" | "recorder";

export const SECTIONS: Section[] = ["market", "replay", "data", "recorder"];

export function sectionFromHash(hash: string = window.location.hash): Section {
  const h = hash.replace(/^#\/?/, "");
  if (h.startsWith("replay") || h.startsWith("run=")) return "replay";
  if (h.startsWith("data")) return "data";
  if (h.startsWith("recorder")) return "recorder";
  return "market";
}

export function runFromHash(hash: string = window.location.hash): string | null {
  const m = hash.match(/run=([\w-]+)/);
  return m ? m[1] : null;
}

// Replay Lab modes:
//   #replay | #replay/obs=<id> | #replay/src=<kind>:<id>   → Market Replay (real evidence; default)
//   #replay/demo | #replay/demo/run=<id> | legacy #run=<id> → Synthetic Demo
export type ReplayMode = "market" | "demo";

export function replayModeFromHash(hash: string = window.location.hash): ReplayMode {
  const h = hash.replace(/^#\/?/, "");
  return h.startsWith("replay/demo") || h.startsWith("run=") ? "demo" : "market";
}

export function obsFromHash(hash: string = window.location.hash): string | null {
  const m = hash.match(/obs=([\w-]+)/);
  return m ? m[1] : null;
}

export function sourceFromHash(hash: string = window.location.hash): { kind: "dataset" | "recording"; id: string } | null {
  const m = hash.match(/src=(dataset|recording):([\w.-]+)/);
  return m ? { kind: m[1] as "dataset" | "recording", id: m[2] } : null;
}

export function replaySource(kind: "dataset" | "recording", id: string): void {
  window.location.hash = `replay/src=${kind}:${id}`;
}

export function datasetFromHash(hash: string = window.location.hash): string | null {
  const m = hash.match(/^#data=([\w.-]+)/);
  return m ? m[1] : null;
}

export function navigate(section: Section): void {
  window.location.hash = section === "market" ? "market" : section;
}

/** Replace the hash without adding a history entry (used for in-view selection). */
export function replaceHash(hash: string): void {
  if (window.location.hash === `#${hash}`) return;
  window.history.replaceState(null, "", `#${hash}`);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function useSection(): Section {
  const [section, setSection] = useState<Section>(sectionFromHash());
  useEffect(() => {
    const on = () => setSection(sectionFromHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return section;
}
