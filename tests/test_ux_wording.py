"""WP-010 wording regressions: pause pending vs paused, modeled vs measured availability, Deep validation scope.

The plain run status (``web/src/views/replay/runStory.ts``) is shared by the Historical Workbench and Replay Lab.
It is executed here directly with Node's built-in TypeScript type stripping (Node 24, already required for the web
build); no browser, database or extra test framework is involved.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from algotrader.observe import deep

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"

HARNESS = r"""
import { runStory, knowledgeOrder } from "./runStory.ts";
const base = (over) => ({
  status: "running", runtime_state: "running", cancel_requested: false,
  control: { paused: false, step_budget: 0, speed: 0, unit: "events" },
  progress: { total_events: 100, committed_events: 40, applied_events: 40 },
  availability: { basis: "MODELED" }, source: { kind: "dataset" },
  operation: { phase: "REPLAYING", phase_label: "Replaying", health: "progressing", health_detail: "",
               assurance: { state: "not_checked" }, suspension: null },
  ...over,
});
const cases = {
  pausing: base({ runtime_state: "pausing", control: { paused: true, step_budget: 0, speed: 0, unit: "events" } }),
  paused: base({ status: "paused", runtime_state: "paused",
                 control: { paused: true, step_budget: 0, speed: 0, unit: "events" } }),
  stepping: base({ runtime_state: "stepping", control: { paused: true, step_budget: 1, speed: 0, unit: "events" } }),
  queued_start_paused: base({ status: "queued", runtime_state: "queued",
                              control: { paused: true, step_budget: 0, speed: 0, unit: "events" },
                              operation: { phase: "QUEUED", phase_label: "Queued", health: "waiting", health_detail: "",
                                           assurance: { state: "not_checked" }, suspension: null } }),
  replay_modeled: base({}),
  replay_recorded: base({ availability: { basis: "RECORDED" }, source: { kind: "recording" } }),
};
const out = {};
for (const [k, v] of Object.entries(cases)) out[k] = runStory(v, 1);
out.pending_dataset = knowledgeOrder({ availability: null, source: { kind: "dataset" } });
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def stories(tmp_path_factory) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed (CI and the web build require Node 24)")
    d = tmp_path_factory.mktemp("runstory")
    (d / "package.json").write_text('{"type": "module"}', encoding="utf-8")
    shutil.copy(WEB / "lib" / "format.ts", d / "format.ts")
    src = (WEB / "views" / "replay" / "runStory.ts").read_text(encoding="utf-8")
    assert 'from "../../lib/format";' in src
    (d / "runStory.ts").write_text(src.replace('from "../../lib/format";', 'from "./format.ts";'), encoding="utf-8")
    (d / "harness.ts").write_text(HARNESS, encoding="utf-8")
    res = subprocess.run([node, "harness.ts"], cwd=d, capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_pause_request_is_not_presented_as_paused(stories):
    s = stories["pausing"]
    assert s["title"] == "Pause requested" and s["working"] is True
    assert "may still be processed" in s["sentence"]
    assert "No further events" not in s["sentence"] and "Nothing is processed" not in s["sentence"]
    p = stories["paused"]  # only the worker's acknowledgement (status paused) promises no further processing
    assert p["title"] == "Paused" and p["working"] is False and "No further events are processed" in p["sentence"]
    st = stories["stepping"]
    assert st["title"].startswith("Paused") and st["working"] is True and "single event" in st["sentence"]
    q = stories["queued_start_paused"]
    assert q["title"] == "Waiting to start" and "pause was requested" in q["sentence"]


def test_modeled_replay_never_claims_measured_historical_availability(stories):
    for text in (stories["replay_modeled"]["sentence"], stories["pending_dataset"]):
        assert "modeled availability convention" in text and "not measured" in text
        assert "exactly as they would have been known" not in text
    rec = stories["replay_recorded"]["sentence"]
    assert "measured local receipt times" in rec and "not exchange publication" in rec


def test_deep_validation_scope_is_reference_reexecution_not_independent_method():
    assert deep.SCOPE.startswith("Reference re-execution")
    assert "reducer code is shared" in deep.SCOPE and "not a wholly independent" in deep.SCOPE
    assert "not an" in deep.SCOPE and "source audit" in deep.SCOPE
    ui = (WEB / "views" / "replay" / "DeepValidation.tsx").read_text(encoding="utf-8")
    workbench = (WEB / "views" / "Backtest.tsx").read_text(encoding="utf-8")
    report = (ROOT / "src" / "algotrader" / "evaluation" / "report.py").read_text(encoding="utf-8")
    for text in (ui, workbench, report):
        assert "independent reference" not in text.replace("\n", " ")
        assert "independent way" not in text
