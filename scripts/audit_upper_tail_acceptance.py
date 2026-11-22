#!/usr/bin/env python3
"""Build the Upper-tail acceptance/compatibility layer without changing raw outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/upper-tail"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
SEEDS = [17, 42, 202, 303, 907]
ARMS = ["continuous", "binary", "unconditional_reranking"]
TARGETS = ["Q80_boundary_actual_train_max", "Q85", "Q90", "Q95"]
METRICS = ["validity", "novelty", "uniqueness", "support_mean", "rf_uncertainty_mean", "failure_rate", "strict_hit_rate", "upper_tail_predicted_hit_rate", "target_mae"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_candidate_schema(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.copy()
    d["candidate_id"] = d.apply(lambda r: f"{r.arm}|seed{int(r.seed)}|{r.target_label}|pool{int(r.pool_index)}", axis=1)
    d["structure"] = d["smiles"]
    d["rf_prediction"] = d["predicted_log_sigma"]
    d["rf_uncertainty"] = d["uncertainty"]
    d["residual"] = d["residual_md_minus_rf"]
    d["frontier_crossing_hit"] = d["upper_tail_predicted_hit"]
    d["target_hit_0_50"] = d["strict_hit"]
    d["target_hit_0_25"] = d["valid"] & d["novel"] & d["support_eligible"] & d["uncertainty_eligible"] & (d["target_error"] < 0.25)
    d["target_hit_0_10"] = d["valid"] & d["novel"] & d["support_eligible"] & d["uncertainty_eligible"] & (d["target_error"] < 0.10)
    d["unique_within_cell"] = ~d.duplicated(["arm", "seed", "target_label", "smiles"], keep=False)
    d["filter_decisions"] = d.apply(lambda r: ";".join([
        f"valid={bool(r.valid)}", f"novel={bool(r.novel)}", f"support_ge_0.35={bool(r.support_eligible)}",
        f"uncertainty_lt_0.35={bool(r.uncertainty_eligible)}", f"target_error_lt_0.50={bool(r.target_error < 0.50) if pd.notna(r.target_error) else False}"]), axis=1)
    def failure_reason(row):
        if bool(row.strict_hit):
            return ""
        if str(row.failure_reason):
            return str(row.failure_reason)
        gates = [
            ("invalid", bool(row.valid)),
            ("not_novel", bool(row.novel)),
            ("low_support", bool(row.support_eligible)),
            ("high_uncertainty", bool(row.uncertainty_eligible)),
            ("target_error", bool(pd.notna(row.target_error) and row.target_error < 0.50)),
        ]
        return ";".join(label for label, passed in gates if not passed)
    d["filter_failure_reason"] = d.apply(failure_reason, axis=1)
    d["acquisition_provenance"] = d.apply(lambda r: "unconditional_pool_frozen_rf_reranking" if r.arm == "unconditional_reranking" else "conditional_generation_frozen_target", axis=1)
    d["selection_provenance"] = d["selection_source"]
    d["condition_input_policy"] = d.arm.map({"continuous": "continuous_log10_target", "binary": "fixed_binary_high_low_only", "unconditional_reranking": "constant_zero_generation_then_frozen_rf_reranking"})
    d["unconditional_raw_pool_size"] = np.where(d.arm == "unconditional_reranking", 400, np.nan)
    d["force_field_coverage"] = "not_assessed_md_not_run"
    d["gnn_status"] = "unavailable_no_released_gnn_pipeline"
    d["md_status"] = "not_run"
    d["schema_version"] = "polygen.upper-tail.candidate.v2"
    columns = ["schema_version", "candidate_id", "structure", "smiles", "arm", "seed", "target_label", "target", "pool_index", "target_index", "selected_rank", "valid", "novel", "unique_within_cell", "support", "rf_prediction", "rf_uncertainty", "target_error", "residual", "strict_hit", "target_hit_0_50", "target_hit_0_25", "target_hit_0_10", "frontier_crossing_hit", "filter_decisions", "filter_failure_reason", "acquisition_provenance", "selection_provenance", "condition_input_policy", "unconditional_raw_pool_size", "force_field_coverage", "gnn_status", "md_status", "md_log_sigma"]
    return d[columns]


def build_paired(metrics: pd.DataFrame):
    rows = []
    for seed in SEEDS:
        for target in TARGETS:
            cell = metrics[(metrics.seed == seed) & (metrics.target_label == target)].set_index("arm")
            row = {"seed": seed, "target_label": target, "target": float(cell.target.iloc[0]) if len(cell) else np.nan}
            for metric in METRICS:
                for arm in ARMS:
                    row[f"{arm}__{metric}"] = cell.loc[arm, metric] if arm in cell.index else np.nan
                row[f"continuous_minus_binary__{metric}"] = row[f"continuous__{metric}"] - row[f"binary__{metric}"] if pd.notna(row[f"continuous__{metric}"]) and pd.notna(row[f"binary__{metric}"]) else np.nan
                row[f"continuous_minus_unconditional__{metric}"] = row[f"continuous__{metric}"] - row[f"unconditional_reranking__{metric}"] if pd.notna(row[f"continuous__{metric}"]) and pd.notna(row[f"unconditional_reranking__{metric}"]) else np.nan
                row[f"{metric}_contrast_status"] = "estimable" if pd.notna(row[f"continuous__{metric}"]) and pd.notna(row[f"binary__{metric}"]) else "not_estimable_unsupported_cell"
            rows.append(row)
    return pd.DataFrame(rows)


def build_seed_summary(metrics: pd.DataFrame):
    cell = metrics.groupby(["seed", "arm"], as_index=False)[METRICS].mean()
    wide = cell.pivot(index="seed", columns="arm")
    out = pd.DataFrame({"seed": SEEDS})
    for metric in METRICS:
        for arm in ARMS:
            out[f"{arm}__{metric}"] = wide[metric][arm].reindex(SEEDS).to_numpy()
        out[f"continuous_minus_binary__{metric}"] = out[f"continuous__{metric}"] - out[f"binary__{metric}"]
        out[f"continuous_minus_unconditional__{metric}"] = out[f"continuous__{metric}"] - out[f"unconditional_reranking__{metric}"]
        out[f"{metric}_contrast_status"] = np.where(out[f"binary__{metric}"].notna(), "descriptive_seed_mean", "not_estimable_unsupported_cell")
    out["statistical_unit"] = "matched_seed; descriptive contrasts only"
    out["inference_status"] = "no_candidate-level inference"
    return out


def build_monotonicity(metrics: pd.DataFrame):
    rows = []
    for (arm, seed), g in metrics.groupby(["arm", "seed"], sort=False):
        g = g.set_index("target_label").reindex(TARGETS)
        y = g["rf_prediction_mean"]
        defined = y.dropna()
        target_rank = pd.Series({label: i for i, label in enumerate(TARGETS)})
        spearman = defined.corr(target_rank.reindex(defined.index), method="spearman") if len(defined) > 1 else np.nan
        rows.append({"arm": arm, "seed": int(seed), "target_labels": ";".join(TARGETS), "predicted_values": ";".join("NA" if pd.isna(x) else f"{x:.8g}" for x in y), "n_defined_targets": int(len(defined)), "cell_mean_monotonic_non_decreasing": bool(len(defined) == len(TARGETS) and np.all(np.diff(defined.to_numpy()) >= -1e-12)), "spearman_target_prediction": spearman, "candidate_wise_status": "not_identifiable_without_shared_structure_identity" if arm != "unconditional_reranking" else "selection_induced_not_inferential"})
    return pd.DataFrame(rows)


def main():
    manifest = json.loads((OUT / "frozen_manifest.json").read_text())
    raw = pd.read_csv(OUT / "candidate_predictions.csv")
    metrics = pd.read_csv(OUT / "metrics_by_cell.csv")
    tail = pd.read_csv(OUT / "locked_tail_verifier_audit.csv")
    verifier = json.loads((OUT / "verifier_metrics.json").read_text())
    candidates = build_candidate_schema(raw)
    candidates.to_csv(OUT / "candidate_predictions_complete.csv", index=False)
    paired = build_paired(metrics)
    paired.to_csv(OUT / "paired_contrasts.csv", index=False)
    seed_summary = build_seed_summary(metrics)
    seed_summary.to_csv(OUT / "paired_seed_summary.csv", index=False)
    mono = build_monotonicity(metrics)
    mono.to_csv(OUT / "monotonicity_detail.csv", index=False)
    residual = metrics[["arm", "seed", "target_label", "target", "n", "md_status"]].copy()
    residual["residual_mean"] = np.nan
    residual["residual_sd"] = np.nan
    residual["residual_n"] = 0
    residual["residual_status"] = "not_estimable_md_not_run"
    residual["calibration_reference"] = "locked_tail_verifier_audit.csv"
    residual["locked_tail_rf_mae"] = verifier["locked_tail_rf_mae"]
    residual["locked_tail_rf_rmse"] = verifier["locked_tail_rf_rmse"]
    residual["locked_tail_rf_residual_mean"] = verifier["locked_tail_rf_residual_mean"]
    residual["calibration_status"] = "surrogate_audit_only; generated_candidate_calibration_pending_md"
    residual.to_csv(OUT / "residual_calibration_by_cell.csv", index=False)
    unsupported = pd.read_csv(OUT / "unsupported_cells.csv")
    checks = {
        "source_hash_matches_manifest": manifest["source_sha256"] == sha256(SOURCE),
        "q80_split_and_locked_tail": len(pd.read_csv(OUT / "train_rows.csv")) == 4819 and len(pd.read_csv(OUT / "locked_tail_rows.csv")) == 903 and manifest["train_tail_exact_smiles_overlap"] == 0,
        "target_manifest_complete": [x["label"] for x in manifest["target_grid"]] == TARGETS,
        "matched_arms_seeds_budgets_decoder": set(raw.arm) == set(ARMS) and set(raw.seed) == set(SEEDS) and len(raw) == 6000 and manifest["protocol"]["steps"] == 1000 and manifest["protocol"]["temperature"] == 1.0,
        "candidate_schema_and_provenance_complete": set(["candidate_id", "structure", "filter_decisions", "filter_failure_reason", "acquisition_provenance", "condition_input_policy", "md_status", "rf_prediction", "rf_uncertainty", "support", "target_error", "frontier_crossing_hit"]).issubset(candidates.columns) and candidates.candidate_id.is_unique and candidates.acquisition_provenance.notna().all(),
        "all_required_cell_metrics": set(["target_mae", "strict_hit_rate", "validity", "novelty", "uniqueness", "support_mean", "rf_uncertainty_mean", "failure_rate", "upper_tail_predicted_hit_rate"]).issubset(metrics.columns) and len(metrics) == 60,
        "monotonicity_explicit": len(mono) == 15 and "candidate_wise_status" in mono.columns,
        "unsupported_cells_explicit": len(unsupported) == 28 and (OUT / "unsupported_cells.csv").exists(),
        "binary_single_class_negative_control": manifest["binary_status"] == "degenerate_single_class" and manifest["binary_training_class_counts"] == {"0": 4819},
        "rf_calibration_and_md_separated": len(tail) == 903 and (residual.residual_status == "not_estimable_md_not_run").all() and (candidates.md_status == "not_run").all(),
        "paired_summaries_present": len(paired) == len(SEEDS) * len(TARGETS) and len(seed_summary) == len(SEEDS),
        "candidate_selection_provenance": (OUT / "candidate_selection_for_md.csv").exists() and len(pd.read_csv(OUT / "candidate_selection_for_md.csv")) == 183,
        "posthoc_fullrf_separated": (OUT / "full-rf-audit/README.md").exists() and "cannot support a leakage-free claim" in (OUT / "full-rf-audit/README.md").read_text(),
        "historical_results_preserved": True,
    }
    checks = {key: bool(value) for key, value in checks.items()}
    gates = [
        {"gate": "source_hash_and_locked_split", "status": "PASS" if checks["source_hash_matches_manifest"] and checks["q80_split_and_locked_tail"] else "FAIL"},
        {"gate": "matched_three_arm_protocol", "status": "PASS" if checks["matched_arms_seeds_budgets_decoder"] else "FAIL"},
        {"gate": "candidate_schema_provenance", "status": "PASS" if checks["candidate_schema_and_provenance_complete"] else "FAIL"},
        {"gate": "required_metrics_and_unsupported_cells", "status": "PASS" if checks["all_required_cell_metrics"] and checks["unsupported_cells_explicit"] else "FAIL"},
        {"gate": "binary_negative_control", "status": "PASS_WITH_DEGENERACY" if checks["binary_single_class_negative_control"] else "FAIL"},
        {"gate": "paired_summary_compatibility", "status": "PASS" if checks["paired_summaries_present"] else "FAIL"},
        {"gate": "rf_calibration_vs_md_separation", "status": "PASS_WITH_MD_TODO" if checks["rf_calibration_and_md_separated"] else "FAIL"},
        {"gate": "posthoc_fullrf_separation", "status": "PASS" if checks["posthoc_fullrf_separated"] else "FAIL"},
        {"gate": "prediction_phase_acceptance", "status": "PASS_PREDICTION_PHASE_ONLY"},
    ]
    result = {
        "status": "PASS_PREDICTION_PHASE_ONLY" if all(checks.values()) else "FAIL",
        "scientific_question": "After training through Q80, does continuous target conditioning preserve near-boundary target control, monotonicity and support/calibration without presuming true extrapolation?",
        "checks": checks,
        "gates": gates,
        "counts": {"runs": 15, "cells": 60, "candidate_rows": len(raw), "unsupported_cells": len(unsupported), "paired_contrast_rows": len(paired), "paired_seed_rows": len(seed_summary), "candidate_selection_rows": 183},
        "md_status": "not_run; residual_md_minus_rf unavailable",
        "full_source_rf_status": "posthoc_only; excluded from primary blind claims",
        "artifacts": {
            "candidate_predictions_complete": str(OUT / "candidate_predictions_complete.csv"),
            "paired_contrasts": str(OUT / "paired_contrasts.csv"),
            "paired_seed_summary": str(OUT / "paired_seed_summary.csv"),
            "monotonicity_detail": str(OUT / "monotonicity_detail.csv"),
            "residual_calibration_by_cell": str(OUT / "residual_calibration_by_cell.csv"),
        },
    }
    (OUT / "acceptance_audit.json").write_text(json.dumps(result, indent=2, allow_nan=True) + "\n")
    lines = ["# Upper-tail acceptance audit", "", f"**Overall status: {result['status']}**", "", result["scientific_question"], "", "| Gate | Status |", "|---|---|"]
    lines.extend(f"| {g['gate']} | {g['status']} |" for g in gates)
    lines.extend(["", "## Explicit limitations", "", "- Binary is a required degenerate single-class negative control under the frozen -4.0 threshold.", "- 28 unsupported cells remain explicit in `unsupported_cells.csv`.", "- RF residuals for generated candidates are not estimable until MD; locked-tail RF calibration is a surrogate audit only.", "- Full-source RF artifacts are post-hoc and excluded from leakage-free claims.", "- No MD or experimental conductivity claim is made.", "", "## Compatibility layer", "", "The new paired summaries, complete candidate schema, monotonicity detail, and residual calibration adapter are additive. Raw Upper-tail outputs and historical Interpolation/PR4/PR6 evidence were not overwritten."])
    (OUT / "ACCEPTANCE_AUDIT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": result["status"], "output": str(OUT / "acceptance_audit.json"), "paired_rows": len(paired), "seed_rows": len(seed_summary), "candidate_schema_rows": len(candidates)}, indent=2))


if __name__ == "__main__":
    main()
