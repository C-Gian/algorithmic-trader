import { useEffect, useState } from "react";
import { replayModeFromHash, ReplayMode } from "../lib/route";
import { Icon } from "../ui/Icon";
import { Badge, cx, PageHeader } from "../ui/primitives";
import { MarketReplay } from "./replay/MarketReplay";
import { SyntheticDemo } from "./replay/SyntheticDemo";

// Replay Lab hosts two strictly separate paths:
//   Market Replay  (primary) - real evidence -> causal feed -> observable state (algotrader.observe.v1);
//   Synthetic Demo (secondary) - the frozen synthetic semantic.v1 DEMO shell.

export function ReplayLab() {
  const [mode, setMode] = useState<ReplayMode>(replayModeFromHash());
  useEffect(() => {
    const on = () => setMode(replayModeFromHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const go = (m: ReplayMode) => {
    window.location.hash = m === "market" ? "replay" : "replay/demo";
    setMode(m);
  };
  return (
    <div className="page page-replay" data-testid="page-replay">
      <PageHeader
        eyebrow="Inspect · event by event"
        title="Replay Lab"
        lede="Inspect market history event by event: play, pause, step one event and change speed, and see exactly what the system knew at each instant. Market Replay uses real, verified evidence; the Synthetic Demo is a separate practice shell with made-up data."
        meta={
          <div className="mode-switch" role="tablist" aria-label="Replay mode">
            <button type="button" role="tab" aria-selected={mode === "market"} data-testid="mode-market"
                    className={cx("mode-tab", "mode-real", mode === "market" && "is-on")} onClick={() => go("market")}>
              <Icon name="market" size={16} />
              <span>Market Replay</span>
              <Badge tone="brand">Real</Badge>
            </button>
            <button type="button" role="tab" aria-selected={mode === "demo"} data-testid="mode-demo"
                    className={cx("mode-tab", "mode-synthetic", mode === "demo" && "is-on")} onClick={() => go("demo")}>
              <Icon name="flask" size={16} />
              <span>Synthetic Demo</span>
              <Badge tone="synthetic">Demo</Badge>
            </button>
          </div>
        }
      />
      {mode === "market" ? <MarketReplay /> : <SyntheticDemo />}
    </div>
  );
}
