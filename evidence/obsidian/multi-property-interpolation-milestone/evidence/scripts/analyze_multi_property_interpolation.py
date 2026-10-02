#!/usr/bin/env python3
"""Derive publication-facing summaries from the frozen interpolation outputs.

This script never retrains or changes candidate selection.  It reads the frozen
candidate table and target manifest, writes deterministic summaries under the
existing multi-property interpolation result root, and labels metrics that are
not identifiable from an interpolation-only, prediction-only design.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, t


PROPERTIES = [
    "log10_conductivity",
    "log10_li_diffusivity",
    "log10_tfsi_diffusivity",
    "log10_poly_diffusivity",
    "transference_number",
    "molality",
]
ARMS = ["multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"]
SEEDS = [17, 42, 202, 303, 907]


def ci95(values: pd.Series) -> tuple[float, float, float, float]:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    mean = float(np.mean(x)) if len(x) else float("nan")
    sem = float(np.std(x, ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")
    half = float(t.ppf(0.975, len(x) - 1) * sem) if len(x) > 1 else float("nan")
    return mean, sem, mean - half, mean + half


def pairwise_diversity(smiles: pd.Series) -> float:
    """Mean 1-Tanimoto over deterministic valid unique molecules in a cell."""
    try:
        from rdkit import Chem, DataStructs
        from rdkit.Chem import AllChem
    except Exception:
        return float("nan")
    mols = []
    seen = set()
    for s in smiles.dropna().astype(str):
        mol = Chem.MolFromSmiles(s)
        if mol is None:
            continue
        can = Chem.MolToSmiles(mol, canonical=True)
        if can in seen:
            continue
        seen.add(can)
        mols.append(AllChem.GetMorganGenerator(radius=2, fpSize=2048).GetFingerprint(mol))
        if len(mols) >= 100:
            break
    if len(mols) < 2:
        return 0.0 if mols else float("nan")
    vals = []
    for i in range(len(mols)):
        sims = DataStructs.BulkTanimotoSimilarity(mols[i], mols[i + 1 :])
        vals.extend(1.0 - float(x) for x in sims)
    return float(np.mean(vals)) if vals else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results/multi-property/interpolation", type=Path)
    args = ap.parse_args()
    root = args.root
    out = root / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    cand = pd.read_csv(root / "candidate_predictions.csv")
    targets = pd.read_csv(root / "target_cells.csv")
    cand = cand.merge(targets[["target_cell", "target_family", "target_label"]], on=["target_cell", "target_family", "target_label"], how="left", suffixes=("", "_manifest"))

    # Cell-level quality and target-control summaries.
    rows = []
    for (arm, seed, cell), g in cand.groupby(["arm", "seed", "target_cell"], sort=True):
        target = targets.loc[targets.target_cell.eq(cell)].iloc[0]
        row = {
            "arm": arm, "seed": int(seed), "target_cell": cell,
            "target_family": target.target_family, "cell_index": int(target.cell_index),
            "n": int(len(g)), "validity": float(g.valid.mean()),
            "invalid_rate": float(1.0 - g.valid.mean()),
            "novelty": float(g.novel.mean()),
            "uniqueness_fraction": float(g.unique_within_cell.mean()),
            "support_mean": float(g.support.mean()),
            "structural_support_mean": float(pd.to_numeric(g.structural_support, errors="coerce").mean()),
            "filter_failure_rate": float((g.filter_decision != "eligible").mean()),
            "high_uncertainty_rate": float(g.filter_failure_reason.fillna("").str.contains("high_uncertainty").mean()),
            "low_support_rate": float(g.filter_failure_reason.fillna("").str.contains("low_structural_support").mean()),
            "not_novel_rate": float(g.filter_failure_reason.fillna("").str.contains("not_novel").mean()),
            "joint_target_rmse": float(np.sqrt(np.mean(np.square(g.joint_target_error)))),
            "joint_strict_hit_rate": float(g.joint_strict_hit.mean()),
            "rf_mean_prediction_overall": float(g.target_error_mean.mul(-1).mean()),
            "rf_uncertainty_mean": float(g.uncertainty_normalized_mean.mean()),
            "diversity_mean_1_minus_tanimoto": pairwise_diversity(g.loc[g.valid.astype(bool), "smiles"]),
            "target_support_status": target.target_support_status,
            "md_status": g.md_status.iloc[0],
        }
        for prop in PROPERTIES:
            pred = f"rf__{prop}__prediction"
            unc = f"rf__{prop}__uncertainty"
            err = f"target_error__{prop}"
            row[f"rf_mean_prediction__{prop}"] = float(g[pred].mean())
            row[f"rf_uncertainty__{prop}"] = float(g[unc].mean())
            row[f"target_mae__{prop}"] = float(g[err].mean())
            row[f"target__{prop}"] = float(json.loads(g.target_vector_json.iloc[0])[PROPERTIES.index(prop)]) if isinstance(g.target_vector_json.iloc[0], str) else float("nan")
        rows.append(row)
    cell = pd.DataFrame(rows)
    cell.to_csv(out / "cell_quality_and_control.csv", index=False)

    metric_cols = [
        "joint_target_rmse", "joint_strict_hit_rate", "validity", "novelty",
        "uniqueness_fraction", "support_mean", "structural_support_mean",
        "diversity_mean_1_minus_tanimoto", "rf_uncertainty_mean", "invalid_rate",
        "filter_failure_rate", "high_uncertainty_rate", "low_support_rate", "not_novel_rate",
    ] + [f"target_mae__{p}" for p in PROPERTIES]
    seed_level = cell.groupby(["arm", "seed"], as_index=False)[metric_cols].mean()
    summary_rows = []
    for arm in ARMS:
        sub = seed_level.loc[seed_level.arm.eq(arm)]
        for metric in metric_cols:
            mean, sem, lo, hi = ci95(sub[metric])
            summary_rows.append({"arm": arm, "metric": metric, "n_seeds": int(len(sub)), "mean": mean, "sem": sem, "ci95_low": lo, "ci95_high": hi})
    pd.DataFrame(summary_rows).to_csv(out / "arm_summary.csv", index=False)

    # Paired comparisons use seed as the independent unit and preserve target-cell pairing.
    paired = []
    for metric in metric_cols:
        wide = seed_level.pivot(index="seed", columns="arm", values=metric)
        for other in ["scalar_continuous", "binary_conductivity", "unconditional_reranking"]:
            if other not in wide or "multi_continuous" not in wide:
                continue
            d = wide["multi_continuous"] - wide[other]
            mean, sem, lo, hi = ci95(d)
            paired.append({"contrast": f"multi_continuous_minus_{other}", "metric": metric, "n_seeds": int(d.notna().sum()), "mean_difference": mean, "sem": sem, "ci95_low": lo, "ci95_high": hi, "all_seed_values": ";".join(f"{x:.8g}" for x in d.dropna())})
    pd.DataFrame(paired).to_csv(out / "paired_summary.csv", index=False)

    # Property-wise response and monotonicity.  This is monotonicity of the
    # matched cell means; candidate-wise monotonicity is not identifiable because
    # independent target cells do not share structure identities.
    mono = []
    for arm in ARMS:
        for seed in SEEDS:
            for prop in PROPERTIES:
                allowed_cells = set(targets.loc[targets.probe_property.eq(prop), "target_cell"])
                sub = cell[(cell.arm == arm) & (cell.seed == seed) & (cell.target_family == "property_probe") & (cell.target_cell.isin(allowed_cells))].copy()
                if len(sub) != 3:
                    continue
                sub = sub.sort_values("target__" + prop)
                x = sub["target__" + prop].to_numpy(float)
                y = sub["rf_mean_prediction__" + prop].to_numpy(float)
                corr = float(pearsonr(x, y).statistic) if np.std(x) > 0 and np.std(y) > 0 else float("nan")
                mono.append({"arm": arm, "seed": seed, "property": prop, "n_target_levels": 3, "target_values": ";".join(f"{v:.8g}" for v in x), "predicted_values": ";".join(f"{v:.8g}" for v in y), "cell_mean_monotonic_non_decreasing": bool(np.all(np.diff(y) >= -1e-12)), "pearson_target_prediction": corr, "candidate_wise_status": "not_identifiable_without_matched_structure_identity"})
    mono_df = pd.DataFrame(mono)
    mono_df.to_csv(out / "property_monotonicity.csv", index=False)
    if len(mono_df):
        mono_df.groupby(["arm", "property"], as_index=False).agg(
            n_seed_rows=("seed", "count"),
            monotonic_fraction=("cell_mean_monotonic_non_decreasing", "mean"),
            mean_pearson=("pearson_target_prediction", "mean"),
        ).to_csv(out / "property_monotonicity_summary.csv", index=False)

    unavailable = pd.DataFrame([
        {"metric": "property_wise_frontier_crossing_rate", "status": "not_applicable_for_interpolation", "reason": "All requested targets are constructed inside the train-support interpolation design; frontier crossing belongs to the separate extrapolation benchmark."},
        {"metric": "joint_frontier_crossing_rate", "status": "not_applicable_for_interpolation", "reason": "No extrapolation target is evaluated here."},
        {"metric": "surrogate_calibration_on_locked_holdout", "status": "unavailable_in_current_candidate_package", "reason": "This package freezes generation-time RF screening outputs; a separate locked-holdout calibration artifact is required before making calibration claims."},
        {"metric": "md_confirmed_frontier_crossing", "status": "unavailable", "reason": "Prediction-only contract; md_status is not_run for every candidate."},
        {"metric": "residual_log_sigma_md_minus_log_sigma_rf", "status": "unavailable", "reason": "No MD outcomes exist in this package."},
    ])
    unavailable.to_csv(out / "unavailable_metrics.csv", index=False)

    schema = {
        "schema_version": 1,
        "source": "candidate_predictions.csv and target_cells.csv",
        "statistical_unit": "seed for arm summaries and paired contrasts; candidate for descriptive quality rows",
        "ci": "two-sided 95% Student-t interval across five seed-level values",
        "diversity": "mean pairwise 1-Tanimoto over up to 100 deterministic valid unique molecules per cell",
        "monotonicity": "cell-mean RF prediction across Q50/Q65/Q80; candidate-wise monotonicity is not identifiable without shared structures",
        "unavailable_metrics_file": "unavailable_metrics.csv",
    }
    (out / "analysis_schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "cell_rows": len(cell), "seed_rows": len(seed_level), "paired_rows": len(paired), "monotonicity_rows": len(mono_df), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
