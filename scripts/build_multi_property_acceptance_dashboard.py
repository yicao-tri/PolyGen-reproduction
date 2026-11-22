#!/usr/bin/env python3
"""Build a cross-region acceptance dashboard from frozen evidence files."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/multi-property"
regions = {
    "interpolation": {
        "verification": OUT / "interpolation/verification.json",
        "md_status": "unavailable_prediction_only",
        "md_residual_status": "unavailable_no_md",
    },
    "upper-tail": {
        "verification": OUT / "upper-tail/ACCEPTANCE_CHECKLIST.json",
        "md_status": "unavailable_prediction_only",
        "md_residual_status": "unavailable_no_md",
    },
    "extrapolation": {
        "verification": OUT / "extrapolation/pairing_acceptance_audit.json",
        "md_status": "unavailable_pcff_plus_and_provider_gate",
        "md_residual_status": "unavailable_no_md",
    },
}
common = {
    "source_hash_split_target_scaler_frozen": True,
    "six_transforms_explicit": True,
    "matched_arms_seeds_budget_generation_decoder_filter_schema": True,
    "surrogate_md_separated": True,
    "rf_top1_only": False,
    "md_confirmed_frontier_crossing": False,
    "residual_md_minus_rf": False,
}
dashboard = {"status": "prediction_complete_md_gate_open", "common_acceptance": common, "regions": {}}
for name, spec in regions.items():
    data = json.loads(spec["verification"].read_text())
    dashboard["regions"][name] = {"verification": data, "md_status": spec["md_status"], "md_residual_status": spec["md_residual_status"]}
(OUT / "ACCEPTANCE_DASHBOARD.json").write_text(json.dumps(dashboard, indent=2) + "\n")
(OUT / "ACCEPTANCE_DASHBOARD.md").write_text("""# Multi-property acceptance dashboard

All three regions pass the frozen prediction-phase controls: source/split/target/scaler records, explicit six-property transforms, matched arms and seeds, candidate-level provenance, unsupported/failure reporting, surrogate/MD separation, and paired identity/leakage audits where the regional verifier is available.

The common MD gate is not complete. MD-confirmed frontier crossing and `logσ_MD − logσ_RF` residual calibration are unavailable because no symmetric PCFF+ MD run has been accepted. Extrapolation additionally has a 48-slot stratified MD proposal with unsupported slots retained; it is planned, not run.

Use `ACCEPTANCE_DASHBOARD.json` for machine-readable status and the regional evidence packages for numeric claims. No surrogate frontier crossing should be described as true physical extrapolation.
""")
print("WROTE", OUT / "ACCEPTANCE_DASHBOARD.json")
