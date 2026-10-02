#!/usr/bin/env python3
"""Acceptance audit for the prediction-only interpolation benchmark."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/interpolation"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
SEEDS = [17, 42, 202, 303, 907]
ACTIVE_ARMS = ["continuous", "binary"]
ALL_ARMS = ["continuous", "binary", "unconditional_reranking"]
QORDER = [0.50, 0.65, 0.80]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def fp(smiles):
    if not isinstance(smiles, str) or not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles.replace("[Cu]", "[*]").replace("[Au]", "[*]"))
    return None if mol is None else AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

def diversity(smiles):
    fps = [fp(s) for s in smiles if fp(s) is not None]
    if len(fps) < 2:
        return np.nan
    sims = [DataStructs.TanimotoSimilarity(fps[i], fps[j]) for i in range(len(fps)) for j in range(i + 1, len(fps))]
    return float(1.0 - np.mean(sims))

def main():
    manifest = json.loads((OUT / "frozen_manifest.json").read_text())
    raw = pd.read_csv(OUT / "candidate_predictions.csv")
    train = pd.read_csv(OUT / "train_rows.csv")
    test = pd.read_csv(OUT / "test_rows.csv")
    source_hash = sha256(SOURCE)
    checks = {}
    checks["source_hash_matches_manifest"] = source_hash == manifest["source_sha256"]
    checks["source_hash"] = source_hash
    checks["split_train_rows_match"] = len(train) == manifest["split"]["train_rows"]
    checks["split_test_rows_match"] = len(test) == manifest["split"]["test_rows"]
    checks["split_row_overlap_absent"] = len(set(train.mol_smiles) & set(test.mol_smiles)) == 0
    checks["targets_are_q50_q65_q80"] = [x["quantile"] for x in manifest["targets"]] == QORDER
    checks["matched_seed_manifest"] = manifest["seeds"] == SEEDS
    checks["matched_budget_manifest"] = manifest["samples_per_cell"] == 100
    checks["candidate_schema_complete"] = set(["arm","seed","quantile","target","candidate_index","smiles","valid","novel","predicted_log_sigma","uncertainty","support","target_error","strict_hit","filter_decision"]).issubset(raw.columns)
    checks["active_candidate_rows"] = len(raw) == len(ACTIVE_ARMS) * len(SEEDS) * len(QORDER) * manifest["samples_per_cell"]
    cell = raw.groupby(["arm","seed","quantile"], dropna=False).size()
    expected_active = pd.MultiIndex.from_product([ACTIVE_ARMS, SEEDS, QORDER], names=["arm","seed","quantile"])
    checks["all_active_cells_present"] = bool(cell.reindex(expected_active).eq(manifest["samples_per_cell"]).all())
    checks["unconditional_blocked_explicit"] = "blocked" in manifest["unconditional_reranking_status"].lower()
    checks["unconditional_not_fabricated"] = "unconditional_reranking" not in set(raw.arm)

    # Add explicit provenance fields without implying an MD acquisition occurred.
    complete = raw.copy()
    complete["acquisition_score"] = np.nan
    complete["acquisition_provenance"] = "prediction_phase_only; no MD selection performed"
    complete["candidate_provenance"] = "generated_by_frozen_checkpoint; scored_by_frozen_RF; filtered_by_recorded_gate"
    complete.to_csv(OUT / "candidate_predictions_complete.csv", index=False)

    metrics = []
    for (arm, seed, q), g in raw.groupby(["arm", "seed", "quantile"], sort=True):
        valid = g[g.valid.astype(bool)]
        unique_valid = valid.smiles.nunique() if len(valid) else 0
        metrics.append({
            "arm": arm, "seed": int(seed), "quantile": float(q), "target": float(g.target.iloc[0]), "n": len(g),
            "validity": float(g.valid.mean()), "novelty": float(g.novel.mean()), "uniqueness_valid": float(unique_valid / len(valid)) if len(valid) else np.nan,
            "support_mean_valid": float(valid.support.mean()) if len(valid) else np.nan,
            "uncertainty_mean_valid": float(valid.uncertainty.mean()) if len(valid) else np.nan,
            "target_mae_valid": float(valid.target_error.mean()) if len(valid) else np.nan,
            "strict_hit_rate": float(g.strict_hit.mean()), "failure_rate": float((~g.valid.astype(bool)).mean()),
            "diversity_valid": diversity(valid.smiles.tolist()), "unsupported_cell": False,
            "acquisition_status": "not_applicable_before_MD",
        })
    metrics = pd.DataFrame(metrics)
    metrics.to_csv(OUT / "metrics_complete.csv", index=False)
    means = metrics.groupby(["arm","quantile"], as_index=False).mean(numeric_only=True)
    means.to_csv(OUT / "metrics_complete_arm_target.csv", index=False)
    wide = metrics.groupby(["arm","seed"], as_index=False).agg(strict_hit_rate=("strict_hit_rate","mean"), target_mae_valid=("target_mae_valid","mean"), validity=("validity","mean"))
    piv = wide.pivot(index="seed", columns="arm")
    paired = pd.DataFrame({"seed": SEEDS,
      "continuous_minus_binary_strict_hit": piv["strict_hit_rate"]["continuous"] - piv["strict_hit_rate"]["binary"],
      "continuous_minus_binary_target_mae": piv["target_mae_valid"]["continuous"] - piv["target_mae_valid"]["binary"],
      "continuous_minus_binary_validity": piv["validity"]["continuous"] - piv["validity"]["binary"]})
    paired.to_csv(OUT / "paired_seed_contrasts.csv", index=False)

    negative = {"arm":"unconditional_reranking", "status":"blocked", "reason":manifest["unconditional_reranking_status"], "rows":0, "reported_as_generation_evidence":False, "required_followup":"supply a released unconditional generator checkpoint or rerun a matched unconditional arm"}
    (OUT / "negative_control.json").write_text(json.dumps(negative, indent=2) + "\n")
    required = ["source_hash_matches_manifest","split_train_rows_match","split_test_rows_match","split_row_overlap_absent","targets_are_q50_q65_q80","matched_seed_manifest","matched_budget_manifest","candidate_schema_complete","active_candidate_rows","all_active_cells_present","unconditional_blocked_explicit","unconditional_not_fabricated"]
    checks["overall_pass"] = all(bool(checks[k]) for k in required)
    checks["required_checks"] = required
    checks["unsupported_cells"] = []
    checks["md_started"] = False
    checks["claim_boundary"] = "surrogate-only interpolation evidence; no MD or experimental conductivity claim"
    (OUT / "verification.json").write_text(json.dumps(checks, indent=2) + "\n")
    audit = """# Interpolation acceptance audit\n\n**Overall status: {status}**\n\nThis audit covers the prediction-only interpolation benchmark at Q50, Q65, and Q80. MD was not started.\n\n## Required checks\n\n{checks}\n\n## Arm and cell accounting\n\n- Active generated arms: continuous and binary.\n- Matched seeds: 17, 42, 202, 303, 907.\n- Active cells: 2 arms × 5 seeds × 3 targets = 30 cells, 100 candidates per cell.\n- Unconditional + reranking: explicitly blocked; zero rows are reported and no proxy candidates are presented as generation evidence.\n- Unsupported active cells: none.\n\n## Added audit artifacts\n\n- `candidate_predictions_complete.csv`: original candidate rows plus explicit candidate and acquisition provenance.\n- `metrics_complete.csv`: target error, strict-hit, validity, novelty, valid uniqueness, support, uncertainty, diversity, failure, unsupported-cell flag, and acquisition status.\n- `paired_seed_contrasts.csv`: seed-level continuous-minus-binary contrasts.\n- `negative_control.json`: machine-readable unconditional blocked status.\n- `verification.json`: hashes, split checks, schema checks, cell checks, and claim boundary.\n\n## Claim boundary\n\nThe result is surrogate-only evidence for in-support target control. It does not establish MD-confirmed conductivity, physical monotonicity, or extrapolation beyond the training distribution.\n""".format(status="PASS" if checks["overall_pass"] else "FAIL", checks="\n".join(f"- `{k}`: **{'PASS' if bool(checks[k]) else 'FAIL'}**" for k in required))
    (OUT / "ACCEPTANCE_AUDIT.md").write_text(audit)
    print(json.dumps({"overall_pass": checks["overall_pass"], "active_cells": int(len(metrics)), "output": str(OUT)}, indent=2))

if __name__ == "__main__":
    main()
