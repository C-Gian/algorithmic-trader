# Current Handoff — OWNER CORPUS PREP / OBSERVATION EVALUATION

Status: **READY FOR OWNER ACTION**  
Authority: FOUNDATION.md v3.0 → STATE.md  
Executor implementation task: **NONE**

## Why this handoff exists

WP-008 is accepted.

The next required evidence is a real Owner-machine measurement of the new workflow, not another Claude/Codex implementation package.

The professional adviser is still not implemented.

This run must remain observation-only.

## Owner action

Start the latest application and use the Backtest page.

### 1. Update and start

From the repository root:

`git pull --ff-only origin main`

Then:

`docker compose up --build`

Open:

`http://localhost:8000`

### 2. Prepare the bootstrap month

Navigate:

**Backtest → A · Historical corpus**

Select:

**September 2025 · bootstrap**  
logical id: `btc-okx-2025-09`  
coverage: `2025-09-01T00:00:00Z → 2025-10-01T00:00:00Z`

Click:

**Prepare Sep 2025**

The Owner may close/reopen the browser; the corpus worker owns acquisition.

Do not start another preparation for this chunk.

Wait until the month is:

**PREPARED**

If preparation fails, copy the visible failure/status details to the Director; do not manually repair files.

### 3. Run the observation evaluation

In:

**B · Run setup**

Keep:

- prepared month: September 2025 · bootstrap
- run type: Observation-only historical evaluation
- pacing: **max**
- start paused: off

Click:

**Start observation evaluation**

This run is historical and observation-only.

It does not contain:
- professional MarketView;
- LONG/SHORT calls;
- targets/stops;
- trading P&L.

### 4. Let the run complete

Watch Stage C.

The run measures:
- acquisition/storage facts already captured for the corpus chunk;
- actual replay throughput;
- ETA behavior;
- browser responsiveness;
- final causal validation.

Pause/cancel is available if needed, but a normal measurement should be allowed to complete if practical.

### 5. Copy the report

When terminal:

**C · Run & report → Report → Copy report for chat**

Paste the complete Markdown report into the Director chat.

Do not summarize it manually.

## What the Director needs from this run

The copied report should give enough evidence to decide:

- actual month total/raw/Parquet size;
- file/page/row counts;
- acquisition outcome and elapsed time;
- full-month feed event count;
- replay runtime and events/s;
- recoveries;
- validation;
- warnings/quality;
- whether the local Owner workflow is practical enough before connecting the real adviser.

## Important boundaries

Do not:

- prepare the other eleven planned months;
- run a full-year acquisition;
- interpret this as a trading backtest;
- ask Claude/Codex to optimize replay before the measured report exists;
- start historical RP-001 work;
- edit frozen research cases.

## Executor instruction

If Claude Code / Codex sees this handoff:

**Stop. No implementation task is active.**

Wait for a new Director task after the Owner returns the copied report.
