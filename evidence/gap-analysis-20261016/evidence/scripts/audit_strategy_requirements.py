#!/usr/bin/env python3
"""Emit a machine-readable strategy-to-evidence traceability ledger."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROWS = [
    ("A1", "verifier ceiling", "complete", "real", "assets/tables/T3_locked_tail_verifier_bins.csv"),
    ("A2", "stratified extrapolation MD", "blocked", "missing", "assets/tables/T4_md_funnel.csv"),
    ("A3", "candidate-specific PCFF+ typing funnel", "NO_GO", "missing", "evidence/data/pcff_plus_bundle_audit/pcff_plus_bundle_audit.json"),
    ("A4", "Hisa review correctness fixes", "isolated_complete_canonical_merge_pending", "real", "evidence/data/hisa_patch_regression_results.json"),
    ("A5", "MD hit and convergence freeze card", "proposed_not_owner_approved", "planned", "assets/tables/T6_freeze_card.csv"),
    ("A6", "decision value metric", "defined_pending_MD", "planned", "assets/tables/T6_freeze_card.csv"),
    ("A7", "residual-driven active learning", "blocked_on_MD", "missing", "assets/figures/F8_decision_change_SYNTHETIC.png"),
    ("A8", "strict same-support MolMiner and WeeMiner", "partial_final_budget_and_Wee_pending", "real_plus_missing", "assets/tables/T14_molminer_extended50_vs_smoke.csv"),
    ("A9", "fragment PI1M Ohsaki ablations", "partial_external_PI1M_missing", "exploratory_only", "evidence/data/pi1m_near_overlap_full/README.md"),
    ("A10", "structural OOD", "split_audit_complete_family_OOD_pending", "real_audit", "evidence/data/structure_split_audit/canonical_overlap_audit.json"),
    ("A11", "figure repair and unified style", "complete_package_level", "real_plus_planned", "evidence/data/figure_visual_qa.csv"),
    ("A12", "documentation grid and Overleaf debt", "partial_owner_sync_pending", "real_package_snapshot", "STRATEGY_CROSSWALK.md"),
    ("A13", "PolyGen pitch insertion", "materials_ready_owner_sync_pending", "real_plus_planned", "OVERLEAF_HANDOFF.md"),
    ("P1", "decision-value pitch page", "complete_observed", "real", "assets/figures/P1_decision_value_tradeoff.png"),
    ("P2", "verifier-blindness pitch page", "complete_observed", "real", "assets/figures/P2_verifier_blind_locked_tail.png"),
    ("P3", "verifier-repair next-action pitch page", "planned_MD_observed_RF", "real_plus_planned", "assets/figures/P3_verifier_repair_experiment.png"),
    ("F1", "framework and closed loop", "complete_package_level", "real_plus_planned", "assets/figures/F1_framework_and_closed_loop.png"),
    ("F2", "interpolation controllability", "complete_observed", "real", "assets/figures/F2_interpolation_controllability.png"),
    ("F3", "upper-tail response", "complete_observed", "real", "assets/figures/F3_upper_tail_response.png"),
    ("F4", "extrapolation response", "complete_observed_surrogate_only", "real", "assets/figures/F4_extrapolation_response.png"),
    ("F5", "verifier audit", "complete_observed", "real", "assets/figures/F5_verifier_audit.png"),
    ("F6", "MD residual ladder", "planned_missing_MD", "real_RF_plus_planned_MD", "assets/figures/F6_md_residual_ladder.png"),
    ("F7", "representation and data ablation", "synthetic_replace_before_publication", "synthetic", "assets/figures/F7_representation_data_ablation_SYNTHETIC.png"),
    ("F8", "decision change", "synthetic_replace_after_MD", "synthetic", "assets/figures/F8_decision_change_SYNTHETIC.png"),
    ("T1-T6", "strategy core tables", "complete_package_level", "real_plus_planned", "assets/tables/T6_freeze_card.csv"),
    ("T7-T14", "audit and generator extension tables", "complete_package_level", "real_plus_exploratory", "assets/tables/T14_molminer_extended50_vs_smoke.csv"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    output = (args.output or root / "evidence/data/strategy_requirements_traceability.csv").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["requirement_id", "description", "status", "data_status", "primary_evidence", "evidence_exists"])
        writer.writeheader()
        for requirement_id, description, status, data_status, primary_evidence in ROWS:
            writer.writerow({
                "requirement_id": requirement_id,
                "description": description,
                "status": status,
                "data_status": data_status,
                "primary_evidence": primary_evidence,
                "evidence_exists": str((root / primary_evidence).exists()).lower(),
            })
    print(f"wrote {len(ROWS)} rows to {output}")


if __name__ == "__main__":
    main()
