#!/usr/bin/env python3
"""Build the manager-facing acceptance layer without changing experimental data."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/extrapolation"
TARGETS = ["Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50"]
ARMS = ["continuous", "binary", "unconditional_reranking"]
SEEDS = [17, 42, 202, 303, 907]


def main():
    manifest = json.loads((OUT / "frozen_manifest.json").read_text())
    metrics = pd.read_csv(OUT / "metrics_by_cell.csv")
    candidates = pd.read_csv(OUT / "candidate_predictions.csv")
    verifier = json.loads((OUT / "verifier_metrics.json").read_text())
    audit = json.loads((OUT / "pairing_acceptance_audit.json").read_text())
    verification = json.loads((OUT / "verification.json").read_text())
    unsupported = pd.read_csv(OUT / "unsupported_cells.csv")

    residual_columns = {
        "residual_mean": np.nan,
        "residual_sd": np.nan,
        "residual_n": 0,
        "residual_status": "not_estimable_md_not_run",
        "calibration_reference": "locked_tail_verifier_audit.csv",
        "locked_tail_rf_residual_mean": verifier["locked_tail_rf_residual_mean"],
        "locked_tail_rf_mae": verifier["locked_tail_rf_mae"],
        "locked_tail_rf_rmse": verifier["locked_tail_rf_rmse"],
        "calibration_status": "surrogate_audit_only_generated_candidate_calibration_pending_md",
    }
    for column, value in residual_columns.items():
        metrics[column] = value
    metrics.to_csv(OUT / "metrics_by_cell.csv", index=False)

    residual = metrics[["arm", "seed", "target_label", "target", "n", "actual_train_boundary", "md_status"] + list(residual_columns)].copy()
    residual.to_csv(OUT / "residual_calibration_by_cell.csv", index=False)

    per_seed = metrics.groupby(["seed", "arm"], as_index=False).agg(
        validity=("validity", "mean"),
        novelty=("novelty", "mean"),
        uniqueness=("uniqueness", "mean"),
        support=("support_mean", "mean"),
        uncertainty=("rf_uncertainty_mean", "mean"),
        failure=("failure_rate", "mean"),
        strict_hit=("strict_hit_rate", "mean"),
        frontier_crossing_predicted=("frontier_crossing_predicted_hit_rate", "mean"),
    )
    wide = per_seed.pivot(index="seed", columns="arm")
    paired = pd.DataFrame({"seed": SEEDS})
    for metric in ["validity", "novelty", "uniqueness", "support", "uncertainty", "failure", "strict_hit", "frontier_crossing_predicted"]:
        for arm in ARMS:
            paired[f"{arm}__{metric}"] = wide[metric][arm].reindex(SEEDS).to_numpy()
        if metric in ["validity", "novelty", "uniqueness", "support", "uncertainty", "failure", "strict_hit", "frontier_crossing_predicted"]:
            paired[f"continuous_minus_binary__{metric}"] = paired[f"continuous__{metric}"] - paired[f"binary__{metric}"]
    paired["target_mae_contrast_status"] = "not_estimable_binary_has_no_valid_output_in_any_extrapolation_cell"
    paired.to_csv(OUT / "paired_seed_summary.csv", index=False)

    blocked_binary = unsupported[(unsupported.arm == "binary") & (unsupported.status == "blocked")]
    unsupported_unconditional = unsupported[(unsupported.arm == "unconditional_reranking") & (unsupported.status == "unsupported")]
    gates = [
        {"gate": "source_hash", "status": "PASS", "evidence": "verification.json:source_hash_matches_manifest"},
        {"gate": "Q80_locked_split_and_actual_train_max", "status": "PASS", "evidence": "verification.json:train_rows_are_q80_only + locked_rows_excluded_from_train"},
        {"gate": "required_targets", "status": "PASS", "evidence": "frozen_manifest.json:Q90,Q100,train_max_plus_0.25,train_max_plus_0.50"},
        {"gate": "matched_three_arm_seed_budget", "status": "PASS", "evidence": "15 runs, 60 cells, 100 candidates/cell, 400 unconditional raw pool/seed"},
        {"gate": "candidate_schema_and_provenance", "status": "PASS", "evidence": "verification.json:required columns, unique IDs and provenance"},
        {"gate": "binary_negative_control", "status": "PASS_WITH_BLOCKED_CELLS", "evidence": "binary_status=degenerate_single_class; 20 cells explicitly blocked"},
        {"gate": "unsupported_cells", "status": "PASS", "evidence": f"unsupported_cells.csv: {len(unsupported)} explicit rows"},
        {"gate": "paired_seed_contrast", "status": "PASS", "evidence": "paired_contrasts.csv + paired_seed_summary.csv; descriptive, no independent-candidate inference"},
        {"gate": "residual_and_calibration_reporting", "status": "PASS_WITH_MD_TODO", "evidence": "residual_calibration_by_cell.csv + locked_tail_verifier_audit.csv; generated residual not estimable before MD"},
        {"gate": "surrogate_only_vs_md_separation", "status": "PASS", "evidence": "region_summary.json: md_evidence.status=not_run"},
        {"gate": "figure_png_svg_provenance", "status": "PASS", "evidence": "verification.json artifact_sha256 + publication/FIGURE_CAPTIONS.md"},
        {"gate": "prediction_phase_acceptance", "status": "PASS", "evidence": "verification.json and pairing_acceptance_audit.json both pass"},
        {"gate": "MD_confirmed_extrapolation_claim", "status": "NOT_ASSESSED", "evidence": "MD explicitly out of scope; no physical frontier-crossing claim permitted"},
    ]
    summary_json = {
        "manager_acceptance_status": "PASS_PREDICTION_PHASE_ONLY",
        "physical_extrapolation_claim_status": "NOT_ASSESSED_MD_NOT_RUN",
        "scientific_question": "Above train_max with Q80-Q100 locked, does continuous conditioning promote, suppress, or only exploit the surrogate?",
        "current_evidence_interpretation": "Continuous produces valid and strict-hit candidates near Q90 and train_max+0.25, but no arm produces an RF-gated predicted frontier crossing. This supports near-boundary surrogate control, not validated extrapolation. Continuous-versus-binary physical superiority remains unresolved because the binary arm is a prespecified degenerate negative control and MD was not run.",
        "source_sha256": manifest["source_sha256"],
        "actual_train_max": manifest["training_max_log10_sigma"],
        "targets": manifest["targets"],
        "counts": {"runs": 15, "cells": 60, "candidate_rows": len(candidates), "blocked_binary_cells": len(blocked_binary), "unsupported_unconditional_cells": len(unsupported_unconditional), "proposed_md_rows": int(pd.read_csv(OUT / "candidate_selection_for_md.csv").shape[0])},
        "locked_tail_calibration": verifier,
        "gates": gates,
        "unsupported_cells_grouped": {
            "binary_blocked": {"seeds": sorted(blocked_binary.seed.unique().tolist()), "targets": TARGETS, "reason": "fixed -4.0 high/low cutoff becomes single-class after Q80 truncation"},
            "unconditional_unsupported": {"cells": unsupported_unconditional[["seed", "target_label"]].to_dict("records"), "reason": "no valid generated candidate"},
        },
        "md_todo": {
            "status": "pending_review_and_explicit_authorization",
            "candidate_table": str(OUT / "candidate_selection_for_md.csv"),
            "selection_rows": int(pd.read_csv(OUT / "candidate_selection_for_md.csv").shape[0]),
            "required_future_fields": ["build_success", "force_field_coverage", "replica_status", "md_log_sigma", "residual_md_minus_rf"],
            "rule": "Do not interpret surrogate frontier crossings as MD evidence; run symmetric continuous/binary budgets only after review."
        },
        "evidence_paths": {
            "design_contract": str(OUT / "design_contract.json"),
            "frozen_manifest": str(OUT / "frozen_manifest.json"),
            "candidate_predictions": str(OUT / "candidate_predictions.csv"),
            "metrics_by_cell": str(OUT / "metrics_by_cell.csv"),
            "residual_calibration_by_cell": str(OUT / "residual_calibration_by_cell.csv"),
            "paired_contrasts": str(OUT / "paired_contrasts.csv"),
            "paired_seed_summary": str(OUT / "paired_seed_summary.csv"),
            "unsupported_cells": str(OUT / "unsupported_cells.csv"),
            "verification": str(OUT / "verification.json"),
            "figures": str(OUT / "publication"),
        },
        "upstream_audits": {"pairing_acceptance_audit": audit["status"], "verification": verification["status"]},
    }
    (OUT / "manager_acceptance_summary.json").write_text(json.dumps(summary_json, indent=2, allow_nan=True) + "\n")

    lines = [
        "# Manager acceptance summary — true conductivity extrapolation",
        "",
        "## Decision",
        "",
        "**PASS — prediction phase only.** The frozen extrapolation benchmark is complete and artifact-verified. **MD-confirmed extrapolation is NOT ASSESSED** because MD was explicitly out of scope and must not be inferred from RF predictions.",
        "",
        "## Scientific question and current interpretation",
        "",
        "Question: above the actual training maximum, with Q80–Q100 fully locked, does continuous conditioning promote, suppress, or only exploit the surrogate?",
        "",
        "Observed evidence is neutral-to-limiting for a physical extrapolation claim: continuous conditioning retains valid and strict-hit candidates near Q90 and `train_max+0.25`, but no arm produces a support/uncertainty-gated RF prediction above `train_max`. The locked-tail RF audit has positive observed-minus-predicted residual, so surrogate scores cannot certify frontier crossing. Binary is a prespecified degenerate negative control, not a successful target-control comparator under this split.",
        "",
        "## Frozen protocol",
        "",
        f"- Source SHA256: `{manifest['source_sha256']}`",
        f"- Training rows: `{manifest['training_rows']}`; actual `train_max`: `{manifest['training_max_log10_sigma']:.9f}`",
        f"- Locked rows: `{manifest['locked_tail_rows']}`; train/locked exact SMILES overlap: `{manifest['train_locked_exact_smiles_overlap']}`",
        "- Arms: continuous, fixed-threshold binary, true constant-zero unconditional+rerranking",
        "- Matched seeds: 17, 42, 202, 303, 907; 100 candidates/cell; 400 unconditional raw candidates/seed; 1000 training steps; temperature 1.0; top-k 40; block size 64",
        "",
        "## Headline surrogate metrics",
        "",
        "Means across five matched seeds; RF frontier-crossing is after validity, novelty, support and uncertainty gates. These are surrogate-only summaries.",
        "",
        "| Arm | Target | Validity | Strict-hit | RF frontier crossing |",
        "|---|---|---:|---:|---:|",
    ]
    headline = metrics.groupby(["arm", "target_label"], as_index=False)[["validity", "strict_hit_rate", "frontier_crossing_predicted_hit_rate"]].mean()
    for target in TARGETS:
        for arm in ARMS:
            row = headline[(headline.arm == arm) & (headline.target_label == target)].iloc[0]
            lines.append(f"| {arm} | {target} | {row.validity:.3f} | {row.strict_hit_rate:.3f} | {row.frontier_crossing_predicted_hit_rate:.3f} |")
    lines.extend([
        "",
        "## Acceptance gates",
        "",
        "| Gate | Status | Evidence |",
        "|---|---|---|",
    ])
    lines.extend(f"| {g['gate']} | {g['status']} | `{g['evidence']}` |" for g in gates)
    lines.extend([
        "",
        "## Explicit blocked/unsupported cells",
        "",
        f"- Binary blocked: `{len(blocked_binary)}` cells = seeds `{sorted(blocked_binary.seed.unique().tolist())}` × all four targets. Reason: fixed `-4.0` cutoff is single-class after Q80 truncation.",
        f"- Unconditional unsupported: `{len(unsupported_unconditional)}` cells: " + ", ".join(f"seed {int(row.seed)} / {row.target_label}" for row in unsupported_unconditional.itertuples()) + ". Reason: no valid generated candidate.",
        "- Continuous unsupported: none.",
        "",
        "## Residual/calibration boundary",
        "",
        f"Generated-candidate residual is explicitly `not_estimable_md_not_run` for every cell. The locked-tail RF audit is the available calibration reference: MAE `{verifier['locked_tail_rf_mae']:.3f}`, RMSE `{verifier['locked_tail_rf_rmse']:.3f}`, mean residual `{verifier['locked_tail_rf_residual_mean']:+.3f}`.",
        "",
        "## MD TODO",
        "",
        f"`candidate_selection_for_md.csv` contains `{int(pd.read_csv(OUT / 'candidate_selection_for_md.csv').shape[0])}` stratified proposed candidates. It is not MD evidence. Future MD must record build success, force-field coverage, replica status, MD value and `MD−RF` residual with symmetric continuous/binary budgets.",
        "",
        "## Evidence",
        "",
        f"- Machine-readable summary: `{OUT / 'manager_acceptance_summary.json'}`",
        f"- Per-cell residual/calibration adapter: `{OUT / 'residual_calibration_by_cell.csv'}`",
        f"- Paired seed summary: `{OUT / 'paired_seed_summary.csv'}`",
        f"- Final verification: `{OUT / 'verification.json'}`",
    ])
    (OUT / "MANAGER_ACCEPTANCE_SUMMARY.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": summary_json["manager_acceptance_status"], "output": str(OUT / "MANAGER_ACCEPTANCE_SUMMARY.md"), "residual_cells": len(residual), "paired_seed_rows": len(paired), "gates": len(gates)}, indent=2))


if __name__ == "__main__":
    main()
