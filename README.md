# Algorithmic Trader

Algorithmic Trader is a clean-room BTC-only research and paper-trading project whose goal is to translate professional market-reading and trade-decision practice into a deterministic, inspectable software trader.

## Current state

The project is in **Foundation / operational-shell bootstrap**. The repository currently contains the accepted project foundation and professional source dossiers. The real trader has not been implemented.

## Read first

1. `FOUNDATION.md` — canonical product, architecture and research directive.
2. `STATE.md` — current milestone, active task and next action.
3. `AGENTS.md` — executor workflow and clean-room rules.
4. `task.md` — the single current task to implement.
5. `source_notes/` and `knowledge/registry.yaml` — professional knowledge provenance.

## Product scope

Initial paper operation is **BTC perpetual futures**, LONG/SHORT/NO_TRADE, with no leverage above 1x exposure. Intended trades are short-duration (generally minutes to hours), while broader horizons may inform market context.

No real-money trading is authorized.

## Implementation

Implementation begins with the current `task.md`: a deterministic operational/dummy shell. The Project & Research Director replaces `task.md` after reviewing each pushed implementation.
