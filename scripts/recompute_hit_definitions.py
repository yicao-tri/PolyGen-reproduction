#!/usr/bin/env python3
"""Recompute precise target-hit and frontier-crossing definitions."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/upper-tail"
OUT = BASE / "publication_v2"
OUT.mkdir(parents=True, exist_ok=True)

def derive(df, prefix, boundary):
    out = df.copy()
    if prefix == "blind":
        quality = out.valid & out.novel & out.support_eligible & out.uncertainty_eligible
        error = out.target_error
        prediction = out.predicted_log_sigma
    else:
        quality = out.fullrf_valid & out.fullrf_novel_vs_train & out.fullrf_support_eligible & out.fullrf_uncertainty_eligible
        error = out.fullrf_target_error
        prediction = out.fullrf_prediction
    out[f"{prefix}_target_hit_0_50"] = quality & (error < 0.50)
    out[f"{prefix}_target_hit_0_25"] = quality & (error < 0.25)
    out[f"{prefix}_target_hit_0_10"] = quality & (error < 0.10)
    out[f"{prefix}_frontier_crossing_hit"] = quality & (prediction > boundary)
    out[f"{prefix}_validated_frontier_crossing_hit"] = pd.NA
    return out

def summarize(df, prefix):
    rows = []
    for arm, g in df.groupby("arm", sort=False):
        row = {"rf_layer": prefix, "arm": arm, "n": len(g)}
        for metric in ["target_hit_0_50", "target_hit_0_25", "target_hit_0_10", "frontier_crossing_hit"]:
            row[metric] = float(g[f"{prefix}_{metric}"].mean())
            row[metric + "_n"] = int(g[f"{prefix}_{metric}"].sum())
        row["validated_frontier_crossing_hit"] = "NA_MD_not_run"
        rows.append(row)
    row = {"rf_layer": prefix, "arm": "ALL_ARMS", "n": len(df)}
    for metric in ["target_hit_0_50", "target_hit_0_25", "target_hit_0_10", "frontier_crossing_hit"]:
        row[metric] = float(df[f"{prefix}_{metric}"].mean())
        row[metric + "_n"] = int(df[f"{prefix}_{metric}"].sum())
    row["validated_frontier_crossing_hit"] = "NA_MD_not_run"
    rows.append(row)
    return rows

def main():
    blind = pd.read_csv(BASE / "candidate_predictions.csv")
    full = pd.read_csv(BASE / "full-rf-audit/fullrf_candidate_predictions.csv")
    manifest = json.loads((BASE / "frozen_manifest.json").read_text())
    boundary = float(manifest["training_max_log10_sigma"])
    blind = derive(blind, "blind", boundary)
    full = derive(full, "fullrf", boundary)
    blind.to_csv(OUT / "candidate_hits_blind_rf.csv", index=False)
    full.to_csv(OUT / "candidate_hits_full_source_rf.csv", index=False)
    summary = pd.DataFrame(summarize(blind, "blind") + summarize(full, "fullrf"))
    summary.to_csv(OUT / "hit_definition_summary.csv", index=False)
    (OUT / "hit_definition_summary.json").write_text(json.dumps({
        "boundary": boundary,
        "definitions": {
            "target_hit_0_50": "quality gates and absolute RF target error < 0.50",
            "target_hit_0_25": "quality gates and absolute RF target error < 0.25",
            "target_hit_0_10": "quality gates and absolute RF target error < 0.10",
            "frontier_crossing_hit": "quality gates and RF prediction > actual Q80 training maximum",
            "validated_frontier_crossing_hit": "MD measured value > actual Q80 training maximum; unavailable because MD was not run"
        },
        "rows": summary.to_dict(orient="records")
    }, indent=2) + "\n")
    (OUT / "HIT_DEFINITIONS.md").write_text(f"""# Upper-tail hit definitions v2

Boundary: `{boundary:.6f}` log10(S cm−1).

All target-hit metrics require valid, training-novel, support-eligible and
uncertainty-eligible candidates. They differ only in the allowed absolute RF
target error:

- `target_hit_0.50`: error < 0.50;
- `target_hit_0.25`: error < 0.25;
- `target_hit_0.10`: error < 0.10;
- `frontier_crossing_hit`: RF prediction > the actual Q80 training maximum;
- `validated_frontier_crossing_hit`: MD measurement > the boundary.

The last metric is `NA_MD_not_run` in this prediction-only phase. Full-source
RF values are post-hoc surrogate values and cannot support leakage-free
extrapolation claims.
""")
    print(OUT)

if __name__ == "__main__":
    main()
