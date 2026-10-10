import { useEffect, useState } from "react";
import { adviserApi, CallDetail, ENTRY_TEXT, LiveView, THESIS_TEXT } from "../adviser";
import { fmtTime } from "../lib/format";
import { Button, Card, Mono, Notice, Skeleton } from "../ui/primitives";
import { RevisionList } from "./AdviserResult";

// Live call history: the recorded journal of ONE call, identified by its continuity run and call id. It only reads
// GET /api/adviser/runs/{run}/calls/{call} (the records the live worker already committed) and never changes the
// adviser. It refetches when the cockpit's own poll shows a new revision or terminal of this call, never on a timer.
// Recorded advice history only: no Owner entry is implied and no hypothetical evaluator path is shown here.

export interface HistoryKey {
  runId: string;
  callId: string;
  /** Live session that showed the call when the history was opened (context; records are keyed by run + call). */
  sessionId: string | null;
}

type Loaded =
  | { key: string; kind: "ok"; detail: CallDetail }
  | { key: string; kind: "missing"; message: string }
  | { key: string; kind: "error"; message: string };

const keyOf = (k: HistoryKey) => `${k.runId}\u0000${k.callId}`;

/** Recorded revision numbers missing from 1..max (a partial journal page); recorded order is kept as received. */
function revisionGaps(nums: number[]): number[] {
  const have = new Set(nums);
  const max = nums.length ? Math.max(...nums) : 0;
  const out: number[] = [];
  for (let i = 1; i <= max; i += 1) if (!have.has(i)) out.push(i);
  return out;
}

export function LiveCallHistory({ sel, view, sessionId, onClose }: {
  sel: HistoryKey; view: LiveView | null; sessionId: string | null; onClose: () => void;
}) {
  const key = keyOf(sel);
  const sameRun = !!view && view.run_id === sel.runId;
  const liveCall = sameRun && view!.call?.call_id === sel.callId ? view!.call : null;
  const recent = sameRun ? (view!.recent_calls ?? []).find((c) => c.call_id === sel.callId) : undefined;
  // the cockpit's poll already carries this call's revision number / terminal: a change is the only refetch trigger
  const signal = `${liveCall?.revision ?? ""}|${recent?.terminal ?? ""}`;
  const [reload, setReload] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let cancelled = false; // a response for an older selection/refresh is dropped, never shown under this identity
    adviserApi.call(sel.runId, sel.callId).then((d) => {
      if (cancelled) return;
      const foreign = d.call?.call_id !== sel.callId || d.revisions.some((r) => r.call_id !== sel.callId);
      setLoaded(foreign
        ? { key, kind: "error", message: "The response does not belong to the selected call; nothing from it is shown." }
        : { key, kind: "ok", detail: d });
    }).catch((e) => {
      if (cancelled) return;
      const msg = (e as Error).message;
      setLoaded(msg.startsWith("404")
        ? { key, kind: "missing", message: "No call record with this identity in the run journal." }
        : { key, kind: "error", message: msg.replace(/^\d+ /, "") });
    });
    return () => { cancelled = true; };
  }, [key, sel.runId, sel.callId, signal, reload]);

  // only data loaded for exactly this run + call is ever rendered (an older identity's data is never reused)
  const shown = loaded && loaded.key === key ? loaded : null;
  const d = shown?.kind === "ok" ? shown.detail : null;
  const revs = d?.revisions ?? [];
  const last = revs.length ? revs[revs.length - 1] : null;
  const terminalThesis = last && last.thesis_status !== "ONGOING" ? last.thesis_status
    : recent ? recent.terminal : null;
  const gaps = revisionGaps(revs.map((r) => r.revision));
  const loadedMax = revs.length ? Math.max(...revs.map((r) => r.revision)) : 0;
  const behindLive = liveCall ? liveCall.revision > loadedMax : false;

  let status: { tone: "pos" | "warn" | "neutral" | "info"; text: string; testid: string };
  if (terminalThesis) {
    status = { tone: "neutral", testid: "history-status-terminal",
      text: `Terminal — ${THESIS_TEXT[terminalThesis] ?? terminalThesis}. No entry is available from this call now; earlier revisions are history only.` };
  } else if (liveCall && liveCall.presentation === "NOT_CURRENT") {
    status = { tone: "warn", testid: "history-status-not-current",
      text: "Shown in the live view, but the session is not current: entry cannot be verified now." };
  } else if (liveCall) {
    status = { tone: liveCall.entry_status === "AVAILABLE" ? "pos" : "info", testid: "history-status-current",
      text: `Current call in the live view — ${ENTRY_TEXT[liveCall.entry_status] ?? liveCall.entry_status} (live view revision r${liveCall.revision}).` };
  } else {
    status = { tone: "warn", testid: "history-status-not-shown",
      text: sameRun ? "Not the call shown in the live view now; the records below are history only."
        : "From another continuity run than the live view now; the records below are history only." };
  }

  return (
    <Card title="Call history" icon="clock" testid="live-call-history"
          eyebrow="Recorded advice history · all times UTC" state={shown ? shown.kind : "loading"}
          actions={<>
            <Button variant="secondary" icon="refresh" onClick={() => setReload((n) => n + 1)} data-testid="history-reload">Reload</Button>
            <Button variant="ghost" icon="x" onClick={onClose} data-testid="history-close">Close</Button>
          </>}>
      <div className="kv-grid small-text" data-testid="history-identity">
        <span>Call</span><Mono>{sel.callId}</Mono>
        <span>Run (continuity epoch)</span><Mono>{sel.runId}</Mono>
        <span>Opened from session</span><Mono>{sel.sessionId ?? "—"}</Mono>
      </div>
      {sessionId !== sel.sessionId && (
        <Notice tone="info" testid="history-session-changed" title="Live session changed since this history was opened">
          The records below still belong only to the run and call named above.
        </Notice>
      )}
      <Notice tone={status.tone} testid={status.testid}>{status.text}</Notice>
      {!shown && <div data-testid="history-loading"><Skeleton lines={3} /></div>}
      {shown?.kind === "missing" && (
        <Notice tone="warn" title="Call history not available" testid="history-missing">{shown.message}</Notice>)}
      {shown?.kind === "error" && (
        <Notice tone="neg" title="Could not load the call history" testid="history-error">{shown.message}</Notice>)}
      {d && d.call && (
        <>
          <div className="adv-section-title">At issue (call record)</div>
          <dl className="call-geo" data-testid="history-issue">
            <dt>Issued</dt><dd className="mono">{fmtTime(d.call.issued_at)} at {d.call.issue_reference} · {d.call.env.origin}</dd>
            <dt>Direction</dt><dd>{d.call.direction} {d.call.family}</dd>
            <dt>Entry at issue</dt><dd className="mono">{d.call.entry_status ?? "not recorded"} · admissible {d.call.actionability.admissible_bounds?.join(" – ") ?? "none recorded"}</dd>
            <dt>Structural area</dt><dd className="mono">{d.call.structural_area[0]} – {d.call.structural_area[1]}</dd>
            <dt>Target / invalidation</dt><dd className="mono">{d.call.target} / {d.call.invalidation}</dd>
            <dt>Hard deadline</dt><dd className="mono">{fmtTime(d.call.hard_deadline)}</dd>
          </dl>
          <div className="adv-section-title">Revisions in recorded order</div>
          {gaps.length > 0 && (
            <Notice tone="warn" testid="history-partial" title="Partial history">
              Recorded revisions r{gaps.join(", r")} are not in this response.
            </Notice>
          )}
          {behindLive && (
            <Notice tone="info" testid="history-behind" title="Live view is newer">
              The live view is at revision r{liveCall!.revision}; this history is loaded up to r{loadedMax}. Reload to read
              the newer records.
            </Notice>
          )}
          {revs.length === 0
            ? <p className="muted small-text" data-testid="history-no-revisions">No revision recorded since issue: the call
                record above is the whole history so far.</p>
            : <RevisionList revisions={revs} detail testid="history-revisions" />}
        </>
      )}
      <p className="muted small-text">Recorded advice only: it does not mean you entered, and no hypothetical outcome is
        computed here. Stops are guidance, not orders.</p>
    </Card>
  );
}
