"""R1C correction: the benchmark gate inventory never turns component measurements or estimates into PASS.

Pure evaluation of the stored raw measurements in ``delivery/evidence`` (no benchmark is run).
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "delivery" / "evidence"


def _bench():
    spec = importlib.util.spec_from_file_location("bench_observe", ROOT / "scripts" / "bench_observe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stored_measurements_evaluate_to_month_gates_and_pending_annual_gates():
    bench = _bench()
    raw = json.loads((EVIDENCE / "WP-008-R1C-benchmark.json").read_text(encoding="utf-8"))
    g = bench.evaluate(raw)
    assert [x["result"] for x in g["month_application_gates"]] == ["PASS"] * 3
    assert [x["result"] for x in g["annual_application_gates"]] == ["NOT_MEASURED"] * 3
    assert all(x["status"].startswith("PENDING") for x in g["annual_application_gates"])
    assert all(x["result"] == "COMPONENT_WITHIN_LIMIT" for x in g["annual_component_comparisons"])
    assert not any(x["result"] == "PASS" for x in g["annual_component_comparisons"])
    assert g["summary"]["annual_application_gates"] == "NOT_MEASURED / PENDING"
    # the committed re-evaluation is exactly what the evaluator produces from the unchanged raw report
    committed = json.loads((EVIDENCE / "WP-008-R1C-benchmark-gates-v2.json").read_text(encoding="utf-8"))
    assert committed["gate_evaluation"] == json.loads(json.dumps(g))
    assert committed["source_gate_evaluation_v1"] == raw["gate_evaluation"]  # historical v1 labels preserved


def test_month_gate_requires_a_completed_run_with_passed_assurance():
    bench = _bench()
    raw = json.loads((EVIDENCE / "WP-008-R1C-benchmark.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(raw)
    bad["tiers"]["month"]["warm"]["assurance"] = "failed"
    rows = {x["gate"]: x["result"] for x in bench.evaluate(bad)["month_application_gates"]}
    assert rows["month cached observation"] == "FAIL" and rows["month terminal validation/report"] == "FAIL"
    assert rows["month cold preparation"] == "PASS"  # measured on the separate cold run
    empty = bench.evaluate({"tiers": {}})
    assert empty["month_application_gates"] == [] and not empty["summary"]["month_application_gates_pass"]
    assert [x["result"] for x in empty["annual_application_gates"]] == ["NOT_MEASURED"] * 3
