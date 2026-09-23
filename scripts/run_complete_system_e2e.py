#!/usr/bin/env python3
"""Run a scoped complete-system generator on the MIT PCL formulation data."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from rdkit import Chem
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "inputs/external/mit-pcl-formulation/supplemental_data_all_experiments.csv"
DEFAULT_OUTPUT = ROOT / "results/experiment-b/tables"
EXPECTED_SHA256 = "94e80bdcc2386cd6412618c4bd7857afbfdf37094dc9fa232d321d6401a0b936"
T0_K = 180.0
SEED = 20260923


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def features(frame: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    out["salt"] = frame["salt_shortname"].astype(str)
    out["molality"] = frame["molality"].astype(float)
    out["molality_sq"] = out["molality"] ** 2
    out["vtf"] = 1.0 / (frame["temperature_K"].astype(float) - T0_K)
    out["molality_vtf"] = out["molality"] * out["vtf"]
    out["salt_molality"] = out["salt"] + "@" + out["molality"].round(6).astype(str)
    return out


def estimator(include_vtf: bool = True) -> Pipeline:
    numeric = ["molality", "molality_sq"]
    if include_vtf:
        numeric += ["vtf", "molality_vtf"]
    transform = ColumnTransformer(
        [
            ("salt", OneHotEncoder(handle_unknown="ignore"), ["salt"]),
            ("salt_m", OneHotEncoder(handle_unknown="ignore"), ["salt_molality"]),
            ("numeric", StandardScaler(), numeric),
        ]
    )
    return Pipeline([("features", transform), ("ridge", Ridge(alpha=3.0))])


def load_and_audit(path: Path) -> tuple[pd.DataFrame, dict]:
    actual_hash = sha256(path)
    if actual_hash != EXPECTED_SHA256:
        raise ValueError(f"input hash mismatch: {actual_hash}")
    data = pd.read_csv(path)
    required = {"smiles", "conductivity", "mw", "salt smiles", "molality", "temperature", "salt_shortname"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    if data[list(required)].isna().any().any():
        raise ValueError("required fields contain missing values")
    if (data["conductivity"] <= 0).any():
        raise ValueError("conductivity must be positive for log transform")
    data = data.copy()
    data["temperature_K"] = data["temperature"] + 273.15
    data["log10_conductivity"] = np.log10(data["conductivity"])
    data["formulation_group"] = data["salt_shortname"].astype(str) + "|" + data["molality"].round(6).astype(str)
    duplicate_cols = ["smiles", "mw", "salt_shortname", "molality", "temperature"]
    audit = {
        "source_sha256": actual_hash,
        "rows": int(len(data)),
        "repeat_units": int(data["smiles"].nunique()),
        "molecular_weights": sorted(map(float, data["mw"].unique())),
        "salts": int(data["salt_shortname"].nunique()),
        "molality_values": int(data["molality"].nunique()),
        "formulation_groups": int(data["formulation_group"].nunique()),
        "temperature_C_range": [float(data["temperature"].min()), float(data["temperature"].max())],
        "conductivity_range": [float(data["conductivity"].min()), float(data["conductivity"].max())],
        "exact_condition_duplicate_rows": int(data.duplicated(duplicate_cols, keep=False).sum()),
        "missing_required_values": 0,
        "identified_effects": ["salt", "molality", "temperature"],
        "non_identified_effects": ["repeat_unit", "mw_or_dp", "architecture", "plasticizer"],
    }
    return data, audit


def cross_validate(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    x = features(data)
    y = data["log10_conductivity"].to_numpy()
    groups = data["formulation_group"].to_numpy()
    rows = []
    null_predictions = []
    splitter = GroupKFold(n_splits=5)
    for fold, (train, test) in enumerate(splitter.split(x, y, groups), 1):
        model = estimator().fit(x.iloc[train], y[train])
        pred = model.predict(x.iloc[test])
        null_model = estimator(include_vtf=False).fit(x.iloc[train], y[train])
        null_pred = null_model.predict(x.iloc[test])
        null_predictions.extend(zip(test, null_pred))
        for idx, value in zip(test, pred):
            rows.append({
                "row_index": int(idx), "fold": fold, "formulation_group": groups[idx],
                "observed_log10_S_cm": y[idx], "predicted_log10_S_cm": float(value),
            })
    preds = pd.DataFrame(rows).sort_values("row_index")
    null_frame = pd.DataFrame(null_predictions, columns=["row_index", "prediction"]).sort_values("row_index")
    null_rmse = mean_squared_error(preds["observed_log10_S_cm"], null_frame["prediction"]) ** 0.5
    physics_rmse = mean_squared_error(preds["observed_log10_S_cm"], preds["predicted_log10_S_cm"]) ** 0.5
    metrics = {
        "group_cv_folds": 5,
        "group_definition": "salt_shortname|molality",
        "rmse_log10_S_cm": float(physics_rmse),
        "temperature_agnostic_null_rmse_log10_S_cm": float(null_rmse),
        "rmse_improvement_over_temperature_agnostic_null": float(null_rmse - physics_rmse),
        "mae_log10_S_cm": float(mean_absolute_error(preds["observed_log10_S_cm"], preds["predicted_log10_S_cm"])),
        "r2": float(r2_score(preds["observed_log10_S_cm"], preds["predicted_log10_S_cm"])),
        "interpretation": "Formulation-held-out interpolation diagnostic; not a cross-polymer generalization estimate.",
    }
    return preds, metrics


def candidate_grid(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    temperatures = [303.15, 323.15, 343.15, 363.15]
    for salt, group in data.groupby("salt_shortname"):
        unique_loadings = group["molality"].nunique()
        if unique_loadings < 2:
            continue
        lo, hi = float(group["molality"].min()), float(group["molality"].max())
        salt_smiles = str(group["salt smiles"].iloc[0])
        for loading in np.linspace(lo, hi, 9):
            for temp in temperatures:
                rows.append({
                    "repeat_unit": str(group["smiles"].iloc[0]),
                    "mw_g_mol": float(group["mw"].iloc[0]),
                    "architecture": "linear_assumed_not_varied",
                    "salt_shortname": salt,
                    "salt_smiles": salt_smiles,
                    "molality": float(loading),
                    "plasticizer": "none_recorded",
                    "temperature_K": temp,
                    "support_status": "in_domain_interpolation",
                })
    candidates = pd.DataFrame(rows)
    candidates["system_id"] = [f"PCL-{i:04d}" for i in range(1, len(candidates) + 1)]
    candidates["formulation_id"] = (
        candidates["salt_shortname"] + "-m" + candidates["molality"].map(lambda x: f"{x:.4f}")
    )
    return candidates


def bootstrap_predict(data: pd.DataFrame, candidates: pd.DataFrame, n_boot: int = 40) -> np.ndarray:
    rng = np.random.default_rng(SEED)
    groups = data["formulation_group"].unique()
    x_candidate = features(candidates)
    all_predictions = []
    for _ in range(n_boot):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        indices = np.concatenate([np.flatnonzero(data["formulation_group"].to_numpy() == group) for group in sampled])
        model = estimator().fit(features(data.iloc[indices]), data.iloc[indices]["log10_conductivity"])
        all_predictions.append(model.predict(x_candidate))
    return np.asarray(all_predictions)


def polygen_interface_audit() -> pd.DataFrame:
    sample_path = ROOT / "results/experiment-a/structure-disjoint-seed42-10000/samples.csv"
    source = pd.read_csv(sample_path)
    rows = []
    for _, row in source.head(25).iterrows():
        smiles = str(row["mol_smiles"])
        mol = Chem.MolFromSmiles(smiles)
        two_ends = smiles.count("[Cu]") == 1 and smiles.count("[Au]") == 1
        rows.append({
            "sample_index": int(row["sample_index"]),
            "repeat_unit": smiles,
            "rdkit_valid": mol is not None,
            "two_polymerization_ends": two_ends,
            "schema_compilable": bool(mol is not None and two_ends),
            "surrogate_support": "OOD_BLOCKED_repeat_unit_not_in_PCL_training",
            "eligible_for_robust_ranking": False,
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data, audit = load_and_audit(args.input)
    cv, metrics = cross_validate(data)
    candidates = candidate_grid(data)
    ensemble = bootstrap_predict(data, candidates)
    candidates["predicted_mean_log10_S_cm"] = ensemble.mean(axis=0)
    candidates["predicted_sd_log10_S_cm"] = ensemble.std(axis=0, ddof=1)
    candidates["predicted_lcb05_log10_S_cm"] = np.quantile(ensemble, 0.05, axis=0)
    rankings = (
        candidates.groupby(["formulation_id", "salt_shortname", "molality"], as_index=False)
        .agg(
            worst_window_lcb_log10_S_cm=("predicted_lcb05_log10_S_cm", "min"),
            mean_window_prediction_log10_S_cm=("predicted_mean_log10_S_cm", "mean"),
            max_uncertainty_sd_log10_S_cm=("predicted_sd_log10_S_cm", "max"),
            temperature_points=("temperature_K", "size"),
        )
        .sort_values("worst_window_lcb_log10_S_cm", ascending=False)
        .reset_index(drop=True)
    )
    rankings.insert(0, "robust_rank", np.arange(1, len(rankings) + 1))
    rankings["selection_status"] = "eligible_in_domain_PCL_only"
    interface = polygen_interface_audit()
    paths = {
        "data_audit.json": audit,
        "model_metrics.json": metrics,
    }
    for name, payload in paths.items():
        (args.output / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    cv.to_csv(args.output / "cv_predictions.csv", index=False)
    candidates.to_csv(args.output / "candidate_predictions.csv", index=False)
    rankings.to_csv(args.output / "robust_rankings.csv", index=False)
    interface.to_csv(args.output / "polygen_interface_audit.csv", index=False)
    artifacts = [args.output / name for name in paths] + [
        args.output / "cv_predictions.csv", args.output / "candidate_predictions.csv",
        args.output / "robust_rankings.csv", args.output / "polygen_interface_audit.csv",
    ]
    manifest = {
        "status": "complete",
        "seed": SEED,
        "input": str(args.input.resolve()),
        "input_sha256": sha256(args.input),
        "script_sha256": sha256(Path(__file__)),
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "rows": len(data),
        "candidate_condition_rows": len(candidates),
        "ranked_formulations": len(rankings),
        "bootstrap_repetitions": int(ensemble.shape[0]),
        "artifacts": {path.name: {"sha256": sha256(path), "bytes": path.stat().st_size} for path in artifacts},
    }
    (args.output / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": metrics, "top5": rankings.head().to_dict("records"), "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
