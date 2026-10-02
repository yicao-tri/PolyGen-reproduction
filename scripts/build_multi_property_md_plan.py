#!/usr/bin/env python3
"""Build a symmetric, non-top-1 MD proposal without launching MD."""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/multi-property/extrapolation"
d = pd.read_csv(OUT / "candidate_predictions.csv")
arms = ["multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"]
targets = ["Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50"]
rows = []
for arm in arms:
    for target in targets:
        g = d[(d.arm == arm) & (d.target_label == target) & d.valid & d.novel].copy()
        strata = {
            "high_prediction_low_uncertainty": g.sort_values(["rf_prediction_conductivity", "joint_uncertainty"], ascending=[False, True]),
            "high_prediction_high_uncertainty": g.sort_values(["rf_prediction_conductivity", "joint_uncertainty"], ascending=[False, False]),
            "high_novelty_low_support": g.sort_values(["support", "rf_prediction_conductivity"], ascending=[True, False]),
        }
        for name, ordered in strata.items():
            if len(ordered):
                r = ordered.iloc[0].to_dict()
                rows.append({"slot": f"{arm}-{target}-{name}", "arm": arm, "target_label": target, "stratum": name, "status": "planned_not_run", "candidate_id": r["candidate_id"], "structure": r["structure"], "rf_prediction_conductivity": r["rf_prediction_conductivity"], "rf_uncertainty_conductivity": r["rf_uncertainty_conductivity"], "support": r["support"], "novelty": r["novelty"], "joint_target_rmse_normalized": r["joint_target_rmse_normalized"], "force_field_coverage": "not_assessed", "md_status": "not_run", "reason": "prospective stratified proposal; requires PCFF+ coverage and LAMMPS provider acceptance"})
            else:
                rows.append({"slot": f"{arm}-{target}-{name}", "arm": arm, "target_label": target, "stratum": name, "status": "unsupported", "candidate_id": "", "structure": "", "rf_prediction_conductivity": np.nan, "rf_uncertainty_conductivity": np.nan, "support": np.nan, "novelty": False, "joint_target_rmse_normalized": np.nan, "force_field_coverage": "unavailable", "md_status": "not_run", "reason": "no valid novel candidate in this arm-target cell"})
plan = pd.DataFrame(rows)
plan.to_csv(OUT / "md_validation_plan.csv", index=False)
summary = plan.groupby(["arm", "status"], as_index=False).size().rename(columns={"size": "slots"})
summary.to_csv(OUT / "md_validation_plan_summary.csv", index=False)
print(summary.to_string(index=False))
