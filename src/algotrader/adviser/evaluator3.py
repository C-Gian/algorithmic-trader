"""v0.3 hypothetical evaluator (``adviser.evaluator.v3``, state ``algotrader.adviser-evaluation-state.v2``).

The MP-001 evaluator (``evaluator.Evaluator``, unchanged for v0.2 runs) with the explicit MP-002 §7 deltas only:

* it consumes issued calls only - WAIT_PRICE creates neither a path nor a NO_ENTRY pseudo-trade;
* A HORIZON_ONLY exit request uses the call's frozen hard deadline H = confirmation + 4h (then the existing exit
  delay/alignment), never issue + 4h; B/C keep their frozen existing deadlines (the base computes the request from the
  frozen ``hard_deadline``, which is H for v0.3 A calls);
* guidance ended for coverage loss (``coverage_loss_from`` on the terminal revision, including a scenario-terminal
  coverage loss) CENSORS open paths from the first missing interval - never a repaired delayed exit;
* hourly view samples count a conditional scenario's antecedent as activated at its structural CONFIRM.

Primary entry delay 60 s with 0/120 s sensitivities on the same calls; opening-price admissibility, protection, gap /
ambiguity / funding / censoring and one-unit accounting are the MP-001 rules. Disabling the evaluator leaves every
professional record identical (it never feeds back).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from ..feed.ordering import canonical
from .evaluation_contracts import EVALUATION_VERSION, EvaluatorProfile
from .evaluator import Evaluator, _dt

STATE_FORMAT = "algotrader.adviser-evaluation-state.v2"
EVALUATOR_IMPLEMENTATION = "adviser.evaluator.v3"


class EvaluatorV3(Evaluator):
    def profile(self, variant: str) -> EvaluatorProfile:
        base = super().profile(variant)
        return base.model_copy(update={"profile_id": f"mp002.evaluation.{variant.lower()}.v1"})

    def identity(self) -> dict:
        body = {"format": EVALUATION_VERSION, "implementation": EVALUATOR_IMPLEMENTATION,
                "profiles": {v: json.loads(self.profile(v).model_dump_json())
                             for v in ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY")},
                "stress_allowance_per_leg": str(self.a_stress), "exit_delay_sensitivities": "NOT_IMPLEMENTED_SECONDARY",
                "view_sampling": "EVERY_UTC_HOUR_AFTER_DISPATCH_UPDATES", "horizons_hours": [1, 4],
                "horizon_baseline_deadline": "A_FROZEN_CONFIRMATION_PLUS_4H_BC_FROZEN_EXISTING_HARD_DEADLINE",
                "wait_price": "NO_PATH_NO_NO_ENTRY_PSEUDO_TRADE",
                "coverage_loss": "CENSOR_FROM_FIRST_MISSING_INTERVAL"}
        return {**body, "sha256": hashlib.sha256(canonical(body)).hexdigest()}

    def on_journal(self, entries: list[dict]) -> None:
        for e in entries:
            k = e["kind"]
            if k == "call":
                self._new_call(e["record"])
            elif k == "call_revision":
                self._revision(e["record"])
            elif k == "scenario" and e["record"]["transition"] == "CONFIRM":
                sid = e["record"]["scenario_id"]
                for s in self.samples:
                    if s.get("scenario_id") == sid and s.get("activated_at") is None:
                        s["activated_at"] = e["record"]["env"]["published_at"]

    def _revision(self, r: dict) -> None:
        c = self.calls.get(r["call_id"])
        if c is not None and c["terminal"] is None and r["thesis_status"] != "ONGOING" and r.get("coverage_loss_from"):
            frm = _dt(r["coverage_loss_from"])
            for v in sorted(c["paths"]):
                ps = c["paths"][v]
                if ps.status == "OPEN":
                    self._close(c, ps, "CENSORED", f"GUIDANCE_COVERAGE_LOSS:{r.get('terminal_reason')}", None, frm)
        super()._revision(r)

    def encode(self) -> dict:
        doc = super().encode()
        doc["format"] = STATE_FORMAT
        return doc

    def restore(self, doc: dict) -> None:
        if doc.get("format") != STATE_FORMAT:
            raise ValueError(f"evaluator state format {doc.get('format')!r} is not {STATE_FORMAT}")
        super().restore({**doc, "format": "algotrader.adviser-evaluation-state.v1"})


_ = datetime
