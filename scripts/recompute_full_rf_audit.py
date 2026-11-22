#!/usr/bin/env python3
"""Post-hoc full-source RF audit for already generated Upper-tail candidates.

This deliberately does not alter the blind Q80-only benchmark. The full RF is
an MD-surrogate audit and is not used to claim leakage-free extrapolation.
"""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestRegressor

RDLogger.DisableLog("rdApp.warning")
RDLogger.DisableLog("rdApp.error")

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
BASE = ROOT / "results/upper-tail"
OUT = BASE / "full-rf-audit"
OUT.mkdir(parents=True, exist_ok=True)

def fp(smiles):
    mol = Chem.MolFromSmiles(smiles.replace("[Cu]", "[*]").replace("[Au]", "[*]"))
    return None if mol is None else AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

def arr(value):
    out = np.zeros(2048, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(value, out)
    return out

def score(smiles, model, ref_fps, ref_smiles, train_smiles):
    fingerprint = fp(smiles) if isinstance(smiles, str) and smiles else None
    valid = bool(fingerprint is not None and smiles.count("[Cu]") == 1 and smiles.count("[Au]") == 1)
    if not valid:
        return {"fullrf_valid": False, "fullrf_novel_vs_train": False,
                "fullrf_novel_vs_full_source": False, "fullrf_prediction": np.nan,
                "fullrf_uncertainty": np.nan, "fullrf_support": np.nan,
                "fullrf_failure_reason": "invalid_or_wrong_end_count"}
    values = np.asarray([tree.predict(arr(fingerprint).reshape(1, -1))[0] for tree in model.estimators_])
    return {
        "fullrf_valid": True,
        "fullrf_novel_vs_train": smiles not in train_smiles,
        "fullrf_novel_vs_full_source": smiles not in ref_smiles,
        "fullrf_prediction": float(values.mean()),
        "fullrf_uncertainty": float(values.std(ddof=1)),
        "fullrf_support": float(max(DataStructs.TanimotoSimilarity(fingerprint, other) for other in ref_fps)),
        "fullrf_failure_reason": "" if smiles not in train_smiles else "exact_training_duplicate",
    }

def sem(values):
    values = pd.Series(values).dropna()
    return float(values.std(ddof=1) / math.sqrt(len(values))) if len(values) > 1 else np.nan

def main():
    source = pd.read_csv(SOURCE)[["mol_smiles", "conductivity"]].copy()
    source["log_sigma"] = np.log10(source.conductivity)
    q80 = float(source.log_sigma.quantile(0.80))
    train = source[source.log_sigma <= q80].copy()
    train_smiles = set(train.mol_smiles)
    ref_smiles = set(source.mol_smiles)
    ref_fps = [fp(s) for s in source.mol_smiles]
    valid_mask = [v is not None for v in ref_fps]
    valid_ref_fps = [v for v in ref_fps if v is not None]
    features = np.stack([arr(v) for v in valid_ref_fps])
    model = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, max_features="sqrt", n_jobs=-1, random_state=20260923)
    model.fit(features, source.loc[valid_mask, "log_sigma"].to_numpy())

    candidates = pd.read_csv(BASE / "candidate_predictions.csv")
    rescored = pd.concat([candidates.reset_index(drop=True), pd.DataFrame([score(s, model, valid_ref_fps, ref_smiles, train_smiles) for s in candidates.smiles])], axis=1)
    rescored["fullrf_target_error"] = (rescored.fullrf_prediction - rescored.target).abs()
    rescored["fullrf_support_eligible"] = rescored.fullrf_support >= 0.35
    rescored["fullrf_uncertainty_eligible"] = rescored.fullrf_uncertainty < 0.35
    rescored["fullrf_strict_hit"] = (rescored.fullrf_valid & rescored.fullrf_novel_vs_train & rescored.fullrf_support_eligible & rescored.fullrf_uncertainty_eligible & (rescored.fullrf_target_error < 0.5))
    rescored["fullrf_upper_tail_hit"] = rescored.fullrf_strict_hit & (rescored.fullrf_prediction > float(train.log_sigma.max()))
    rescored.to_csv(OUT / "fullrf_candidate_predictions.csv", index=False)

    rows = []
    for (arm, target_label), group in rescored.groupby(["arm", "target_label"], sort=False):
        row = {"arm": arm, "target_label": target_label, "target": float(group.target.iloc[0]), "n": len(group)}
        row.update({
            "validity": group.fullrf_valid.mean(),
            "novelty_vs_train": (group.fullrf_valid & group.fullrf_novel_vs_train).mean(),
            "strict_hit_rate": group.fullrf_strict_hit.mean(),
            "upper_tail_hit_rate": group.fullrf_upper_tail_hit.mean(),
            "target_mae": group.loc[group.fullrf_valid, "fullrf_target_error"].mean(),
            "rf_prediction_mean": group.fullrf_prediction.mean(),
            "rf_uncertainty_mean": group.fullrf_uncertainty.mean(),
            "support_mean": group.fullrf_support.mean(),
            "support_eligible_rate": group.fullrf_support_eligible.mean(),
            "failure_rate": 1.0 - group.fullrf_valid.mean(),
        })
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT / "fullrf_metrics_by_cell.csv", index=False)

    tail = source[(source.log_sigma > q80) & (source.log_sigma <= source.log_sigma.quantile(0.95))].copy()
    tail_score = pd.DataFrame([score(s, model, valid_ref_fps, ref_smiles, train_smiles) for s in tail.mol_smiles])
    tail_audit = pd.concat([tail.reset_index(drop=True), tail_score], axis=1)
    tail_audit["fullrf_residual_observed_minus_predicted"] = tail_audit.log_sigma - tail_audit.fullrf_prediction
    tail_audit.to_csv(OUT / "fullrf_locked_tail_audit.csv", index=False)
    residual = tail_audit.fullrf_residual_observed_minus_predicted.dropna()
    (OUT / "fullrf_summary.json").write_text(json.dumps({
        "status": "complete_posthoc_full_source_rf_audit",
        "warning": "Full-source RF sees locked-tail labels and is not valid for leakage-free extrapolation claims.",
        "source_rows": int(len(source)), "training_rows_q80": int(len(train)), "locked_tail_rows": int(len(tail)),
        "training_boundary": float(train.log_sigma.max()),
        "locked_tail_rf_mae": float((tail_audit.log_sigma - tail_audit.fullrf_prediction).abs().mean()),
        "locked_tail_rf_rmse": float(np.sqrt(np.mean((tail_audit.log_sigma - tail_audit.fullrf_prediction) ** 2))),
        "locked_tail_residual_mean": float(residual.mean()), "locked_tail_residual_sd": float(residual.std(ddof=1)),
    }, indent=2) + "\n")
    print(OUT)

if __name__ == "__main__":
    main()
