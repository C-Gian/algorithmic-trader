"""Compute the A v0.6 method/implementation/evaluator/profile identities from a source tree (no study execution).

Usage: python v06_identity.py <tree_root> <out_json>
<tree_root> contains src/ and delivery/ of the commit to examine (e.g. extracted with git archive).
Uses only the project's existing identity functions (methods.V06, identity.historical_profile, EvaluatorV3.identity).
"""
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "src"))

from algotrader.adviser import methods, identity as idn  # noqa: E402
from algotrader.adviser.evaluator3 import EvaluatorV3  # noqa: E402


def sha_lf(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


rel = methods.get("v0.6")
assert Path(methods.__file__).resolve().is_relative_to(root), methods.__file__
out = {"tree": str(root), "release": {k: getattr(rel, k) for k in (
    "key", "model", "rules_version", "implementation", "evaluator_implementation", "core_state_format",
    "runtime_format", "evaluator_state_format", "engine_format", "report_version", "reconciliation_version",
    "deep_version")}}
out["rules_manifest"] = rel.rules_manifest()
out["rules_sha256"] = rel.rules_sha256()
out["register_file_sha256_lf"] = sha_lf(rel.register_file)
out["register_canonical_sha256"] = rel.register_sha256()
reg = rel.register()
out["register_model"] = [reg.get("model"), reg.get("rules_version")]

# packaged method documents vs the Director documents in delivery/
pk = {}
for f in sorted(idn.METHOD_DIR.iterdir()):
    d = root / "delivery" / f.name
    pk[f.name] = {"packaged_sha256_lf": sha_lf(f),
                  "delivery_sha256_lf": sha_lf(d) if d.exists() else None,
                  "identical": d.exists() and sha_lf(d) == sha_lf(f)}
out["packaged_vs_delivery"] = pk

params = rel.params()
out["primary_entry_delay_seconds"] = params.eval_primary_delay
out["exit_delay_seconds"] = params.eval_exit_delay

# capability profiles: historical_profile(dislocation, funding_covered); the pack decides the inputs
prof = {}
for disl in (True, False):
    for fund in (False, True):
        p = idn.historical_profile(dislocation=disl, funding_covered=fund)
        prof[f"dislocation={disl},funding_covered={fund}"] = {"profile": p.model_dump(mode="json"), "sha256": p.sha256()}
out["historical_profiles"] = prof

# evaluator identity per funding mode; checked for tick independence
ev = {}
for mode in ("PRICE_NET_ONLY", "AUTHORITATIVE_IF_COVERED"):
    shas = {}
    for tick in ("0.1", "1"):
        e = EvaluatorV3(params, Decimal(tick), eval_start=None, eval_end=None, funding_mode=mode)
        ident = e.identity()
        shas[tick] = ident["sha256"]
    assert len(set(shas.values())) == 1, shas
    ev[mode] = {"sha256": ident["sha256"], "tick_independent": True,
                "primary_profile": ident["profiles"]["PRIMARY"]}
out["evaluator_identity"] = ev

Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
print(json.dumps({"rules_sha256": out["rules_sha256"], "register": out["register_canonical_sha256"],
                  "eval": {k: v["sha256"] for k, v in ev.items()},
                  "profiles": {k: v["sha256"] for k, v in prof.items()}}, indent=1))
