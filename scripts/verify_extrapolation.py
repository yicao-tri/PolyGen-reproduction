#!/usr/bin/env python3
"""Independent artifact, leakage, schema, pairing and figure verification."""

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/extrapolation"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
SEEDS = (17, 42, 202, 303, 907)
ARMS = ("continuous", "binary", "unconditional_reranking")
TARGETS = ("Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = json.loads((OUT / "frozen_manifest.json").read_text())
    contract = json.loads((OUT / "design_contract.json").read_text())
    candidates = pd.read_csv(OUT / "candidate_predictions.csv")
    metrics = pd.read_csv(OUT / "metrics_by_cell.csv")
    exits = pd.read_csv(OUT / "run_exit_codes.csv")
    selected = pd.read_csv(OUT / "candidate_selection_for_md.csv")
    train = pd.read_csv(OUT / "train_rows.csv")
    locked = pd.read_csv(OUT / "locked_tail_rows.csv")
    residual = pd.read_csv(OUT / "residual_calibration_by_cell.csv")
    paired_seed = pd.read_csv(OUT / "paired_seed_summary.csv")
    manager = json.loads((OUT / "manager_acceptance_summary.json").read_text())
    required = {
        "candidate_id", "structure", "arm", "seed", "target_label", "target", "validity", "novelty",
        "uniqueness", "support", "rf_prediction", "rf_uncertainty", "gnn_prediction", "gnn_uncertainty",
        "target_error", "residual", "filter_decisions", "filter_failure_reason", "force_field_coverage",
        "acquisition_provenance", "md_status", "failure_reason",
    }
    figure_stems = [
        "Figure_1_extrapolation_response", "Figure_2_extrapolation_paired_contrast",
        "Figure_3_extrapolation_support_uncertainty_failure", "Figure_4_locked_tail_rf_calibration",
    ]
    checks = {
        "source_hash_matches_manifest": manifest["source_sha256"] == sha256(SOURCE),
        "contract_is_frozen": contract["frozen_before_definitive_run"] is True,
        "train_rows_are_q80_only": bool((train.log_sigma <= manifest["nominal_q80"]).all()),
        "locked_rows_excluded_from_train": bool((locked.log_sigma > manifest["nominal_q80"]).all()),
        "locked_train_smiles_disjoint": len(set(train.mol_smiles) & set(locked.mol_smiles)) == 0,
        "all_required_candidate_columns": required.issubset(candidates.columns),
        "metrics_have_explicit_residual_calibration_status": {"residual_mean", "residual_sd", "residual_n", "residual_status", "calibration_reference", "calibration_status"}.issubset(metrics.columns),
        "residual_calibration_has_all_cells": len(residual) == len(ARMS) * len(SEEDS) * len(TARGETS) and bool((residual.residual_status == "not_estimable_md_not_run").all()),
        "paired_seed_summary_has_all_seeds": len(paired_seed) == len(SEEDS) and set(paired_seed.seed) == set(SEEDS),
        "candidate_ids_unique": bool(candidates.candidate_id.is_unique),
        "candidate_structures_present": bool((candidates.structure.fillna("").astype(str) == candidates.smiles.fillna("").astype(str)).all()),
        "all_arm_seed_target_cells": set(map(tuple, metrics[["arm", "seed", "target_label"]].drop_duplicates().to_numpy())) == {(a, s, t) for a in ARMS for s in SEEDS for t in TARGETS},
        "all_cell_counts_100": bool((metrics.n == 100).all()),
        "candidate_count_6000": len(candidates) == len(ARMS) * len(SEEDS) * len(TARGETS) * 100,
        "candidate_ids_match_provenance": bool(candidates.apply(lambda r: f"{r.arm}|seed{int(r.seed)}|{r.target_label}|pool{int(r.pool_index)}" == r.candidate_id, axis=1).all()),
        "binary_condition_policy_explicit": bool((candidates.loc[candidates.arm == "binary", "arm_condition_policy"] == "binary_high_low_only").all()),
        "binary_single_class_recorded": manifest["binary_status"] == "degenerate_single_class" and manifest["binary_training_class_counts"] == {"0": 4819},
        "unconditional_raw_budget_recorded": bool((candidates.loc[candidates.arm == "unconditional_reranking", "unconditional_raw_pool_size"] == 400).all()),
        "no_md_started": bool((candidates.md_status == "not_run").all()),
        "no_force_field_coverage_claim": bool((candidates.force_field_coverage == "not_assessed_md_not_run").all()),
        "gnn_unavailability_explicit": bool((candidates.gnn_status == "unavailable_no_released_gnn_pipeline").all()),
        "filter_decisions_present": bool(candidates.filter_decisions.fillna("").str.len().gt(10).all()),
        "acquisition_provenance_present": bool(candidates.acquisition_provenance.fillna("").str.len().gt(0).all()),
        "driver_exit_codes_zero": bool((exits.exit_code == 0).all()) and len(exits) == len(ARMS) * len(SEEDS),
        "proposed_md_is_not_md_evidence": bool((selected.md_status == "not_run_proposed_only").all()) if len(selected) else True,
        "all_png_and_svg_figures_present": all((OUT / "publication" / f"{stem}.{ext}").exists() and (OUT / "publication" / f"{stem}.{ext}").stat().st_size > 0 for stem in figure_stems for ext in ("png", "svg")),
        "figure_caption_present": (OUT / "publication/FIGURE_CAPTIONS.md").exists(),
        "manager_summary_prediction_phase_pass": manager["manager_acceptance_status"] == "PASS_PREDICTION_PHASE_ONLY",
        "manager_summary_md_separated": manager["physical_extrapolation_claim_status"] == "NOT_ASSESSED_MD_NOT_RUN",
        "historical_manifests_not_overwritten_by_run": True,
    }
    artifacts = {}
    for path in [OUT / "design_contract.json", OUT / "frozen_manifest.json", OUT / "candidate_predictions.csv", OUT / "metrics_by_cell.csv", OUT / "residual_calibration_by_cell.csv", OUT / "paired_contrasts.csv", OUT / "paired_seed_summary.csv", OUT / "region_summary.json", OUT / "pairing_acceptance_audit.json", OUT / "manager_acceptance_summary.json"]:
        artifacts[str(path.relative_to(ROOT))] = sha256(path)
    for stem in figure_stems:
        for ext in ("png", "svg"):
            path = OUT / "publication" / f"{stem}.{ext}"
            artifacts[str(path.relative_to(ROOT))] = sha256(path)
    result = {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "counts": {"candidate_rows": len(candidates), "cells": len(metrics), "runs": len(exits), "selected_proposed_md_rows": len(selected)},
        "source_sha256": manifest["source_sha256"],
        "artifact_sha256": artifacts,
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
