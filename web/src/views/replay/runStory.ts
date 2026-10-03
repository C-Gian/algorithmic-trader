import type { ObsReplay } from "../../api";
import { fmtInt } from "../../lib/format";
import type { Tone } from "../../ui/primitives";

// Plain-language reading of a market-replay run for people who do not know the internal vocabulary.
// It only re-states facts already present in the run document (status, phase, health, cursor, assurance);
// it never infers progress from a heartbeat and never merges "finished" with "checks passed".

export const TERMINAL_STATUSES = new Set(["completed", "cancelled", "failed"]);
const PREP = new Set(["PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED", "INITIALIZING"]);
const POST = new Set(["FINALIZING", "VALIDATING", "GENERATING_REPORT"]);

export interface RunStory {
  /** Short state title, e.g. "Finished", "Replaying market history". */
  title: string;
  /** One sentence: what is happening / what happened, and what to do. */
  sentence: string;
  tone: Tone;
  /** True while the system is actively working on this run (not paused, not finished). */
  working: boolean;
  terminal: boolean;
  /** Index (0-3) in the four beginner steps: waiting · preparing data · replaying · checking & report. */
  step: number;
}

export const RUN_STEPS = ["Waiting to start", "Preparing the data", "Replaying market history", "Checking & writing the report"];

function stepOf(phase: string | null | undefined): number {
  if (!phase || phase === "QUEUED") return 0;
  if (PREP.has(phase)) return 1;
  if (phase === "REPLAYING") return 2;
  if (POST.has(phase)) return 3;
  return 0;
}

/** Where the finished result lives: the Workbench shows a report card; Replay Lab lists checks + diagnostics. */
export type ResultPlace = "report" | "lab";

/** How a replay orders knowledge. A dataset's times are a modeled convention, never measured historical availability. */
export function knowledgeOrder(r: Pick<ObsReplay, "availability" | "source">): string {
  const basis = r.availability?.basis ?? (r.source.kind === "recording" ? "RECORDED" : "MODELED");
  return basis === "RECORDED"
    ? "in the order this computer received them while recording (measured local receipt times, not exchange publication)."
    : "in time order under the dataset's modeled availability convention (a bar counts as known at its close, funding at its funding time), not measured historical publication or receipt times.";
}

export function runStory(r: ObsReplay, workersAlive?: number, place: ResultPlace = "report"): RunStory {
  const op = r.operation;
  const p = r.progress;
  const total = p.total_events;
  const done = p.committed_events ?? p.applied_events;
  const of = total === null ? `${fmtInt(done)} events` : `${fmtInt(done)} of ${fmtInt(total)} events`;
  const assurance = op.assurance.state;
  const terminal = TERMINAL_STATUSES.has(r.status);
  const step = terminal ? 3 : stepOf(op.phase);
  const base = { terminal, step };

  if (op.suspension) {
    return { ...base, title: "Preserved older run (read-only)", tone: "pending", working: false,
      sentence: "This run comes from before an upgrade. It is kept unchanged for inspection and cannot be resumed; copy its diagnostics if needed." };
  }
  if (r.status === "completed") {
    const checks = assurance === "passed" ? "and its integrity checks passed"
      : assurance === "failed" ? "but its integrity checks FAILED — see the warnings below"
        : `but its integrity checks are ${assurance.replace("_", " ")}`;
    return { ...base, title: "Finished", tone: assurance === "passed" ? "pos" : "warn", working: false,
      sentence: `The run replayed ${of} ${checks}. ${place === "report" ? "The report is ready below."
        : "Its validation checks and artifacts are listed below, and its diagnostics can be copied for chat."}` };
  }
  if (r.status === "cancelled") {
    return { ...base, title: "Cancelled", tone: "warn", working: false,
      sentence: `Stopped after ${of}. Coverage is incomplete, so this is not a successful check; its report still explains what happened.` };
  }
  if (r.status === "failed") {
    return { ...base, title: "Failed", tone: "neg", working: false,
      sentence: `The run stopped with an error after ${of}. Copy the report for chat so the problem can be diagnosed.` };
  }
  if (r.cancel_requested) {
    return { ...base, title: "Cancelling", tone: "warn", working: true,
      sentence: "Cancel was requested; the run stops at the next safe point and then writes its report." };
  }
  if (r.runtime_state === "recovering") {
    return { ...base, title: "Recovering", tone: "warn", working: true,
      sentence: "The previous attempt was interrupted; a new attempt is restoring the last saved point. Nothing needs to be done." };
  }
  if (r.runtime_state === "unresponsive" || op.health === "compute_lost" || op.health === "unresponsive") {
    return { ...base, title: "Not responding", tone: "neg", working: false,
      sentence: `${op.health_detail} If this persists, check that the application is running and copy the diagnostics for chat.` };
  }
  // A pause is only a request until the worker acknowledges it by parking the run (status "paused"); until then the
  // worker may still prepare or finish its current unit of work, so "nothing is processed" is never promised early.
  if (r.control.paused && r.control.step_budget > 0) {
    return { ...base, title: "Paused · stepping", tone: "warn", working: true,
      sentence: `Paused at ${of}; applying the requested single event, then the run stays paused.` };
  }
  if (r.status === "paused") {
    return { ...base, title: "Paused", tone: "warn", working: false,
      sentence: `Paused at ${of}. No further events are processed until you press Resume (or Step one event).` };
  }
  if (r.control.paused && r.status === "running" && !PREP.has(op.phase ?? "")) {
    return { ...base, title: "Pause requested", tone: "warn", working: true,
      sentence: `Pausing: the worker finishes and saves its current unit of work (now at ${of}), then the run shows Paused. Until then events may still be processed.` };
  }
  const thenPause = r.control.paused ? " A pause was requested: the run will stop before replaying the first event." : "";
  if (r.status === "queued" || op.phase === "QUEUED" || !op.phase) {
    const noWorker = workersAlive === 0;
    return { ...base, title: "Waiting to start", tone: noWorker ? "warn" : "info", working: !noWorker,
      sentence: (noWorker
        ? "Queued, but no replay worker is running, so it cannot start yet. Start the application's worker services."
        : "Queued: a replay worker will pick it up in a moment.") + thenPause };
  }
  if (op.health === "alive_no_progress") {
    return { ...base, title: "Working, but no recent progress", tone: "warn", working: true,
      sentence: `${op.health_detail} Wait a little; if it stays like this, copy the diagnostics for chat.` };
  }
  if (PREP.has(op.phase ?? "")) {
    return { ...base, title: "Preparing the data", tone: "info", working: true,
      sentence: `${op.phase_label}: checking and indexing the stored data before replaying. Total events are known after this step.${thenPause}` };
  }
  if (op.phase === "REPLAYING") {
    return { ...base, title: "Replaying market history", tone: "info", working: true,
      sentence: `Replayed ${of} so far, ${knowledgeOrder(r)}` };
  }
  return { ...base, title: "Checking & writing the report", tone: "info", working: true,
    sentence: `All events are replayed; ${op.phase_label.toLowerCase()} is in progress. The run is not finished until the report is written.` };
}
