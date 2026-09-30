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
