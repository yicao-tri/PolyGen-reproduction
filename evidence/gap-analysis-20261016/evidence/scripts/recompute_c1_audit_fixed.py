#!/usr/bin/env python3
"""Recompute the real C1 audit with a valid cross-target correlation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEEDS = [17, 42, 202, 303, 907]
ARMS = ["binary", "continuous"]


def corr(group: pd.DataFrame) -> float:
    target = group["target"].to_numpy(dtype=float)
    prediction = group["predicted_log_sigma"].to_numpy(dtype=float)
    mask = np.isfinite(target) & np.isfinite(prediction)
    if mask.sum() < 2 or np.ptp(target[mask]) == 0.0 or np.ptp(prediction[mask]) == 0.0:
        return float("nan")
    return float(np.corrcoef(target[mask], prediction[mask])[0, 1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    file_rows = []
    for seed in SEEDS:
        base = (
            args.canonical_root / "results/experiment-c/c1"
            if seed in [17, 42, 907]
            else args.canonical_root / "results/experiment-c/extra-seeds/seeds202-303"
        )
        for arm in ARMS:
            path = base / f"{arm}-seed{seed}/samples.csv"
            frame = pd.read_csv(path)
            frame["arm"] = arm
            frame["seed"] = seed
            frame["config_id"] = "c1_gptnano_steps1000_temp1.0_raw300_seedtarget100"
            frame["eligible"] = frame["valid"] & frame["novel"] & (frame["support"] >= 0.35) & (frame["uncertainty"] < 0.35)
            frames.append(frame)
            file_rows.append({
                "arm": arm,
                "seed": seed,
                "source_file": str(path),
                "raw_samples": int(len(frame)),
                "valid_count": int(frame["valid"].sum()),
                "eligible_count": int(frame["eligible"].sum()),
                "strict_hit_count": int(frame["hit"].sum()),
            })

    raw = pd.concat(frames, ignore_index=True)
    raw.to_csv(args.output_dir / "raw_with_identity.csv", index=False)
    pd.DataFrame(file_rows).to_csv(args.output_dir / "file_audit.csv", index=False)

    target_rows = []
    for (arm, seed, target), group in raw.groupby(["arm", "seed", "target"], sort=True):
        target_rows.append({
            "arm": arm,
            "seed": int(seed),
            "target": float(target),
            "raw_n": int(len(group)),
            "validity": float(group["valid"].mean()),
            "uniqueness": float(group.loc[group["valid"], "smiles"].nunique() / len(group)) if len(group) else np.nan,
            "novelty": float(group["novel"].mean()),
            "similarity_in_support": float((group["support"] >= 0.35).mean()),
            "uncertainty_gate_rate": float((group["uncertainty"] < 0.35).mean()),
            "strict_hit_rate": float(group["hit"].mean()),
            "target_mae": float(group["target_error"].mean()),
            "target_prediction_correlation": np.nan,
            "mean_predicted_log_sigma": float(group["predicted_log_sigma"].mean()),
            "mean_uncertainty": float(group["uncertainty"].mean()),
            "correlation_scope": "undefined within one constant target",
        })
    pd.DataFrame(target_rows).to_csv(args.output_dir / "arm_seed_target_metrics.csv", index=False)

    arm_seed = raw.groupby(["arm", "seed"], as_index=False).agg(
        raw_n=("index", "size"),
        validity=("valid", "mean"),
        uniqueness=("smiles", "nunique"),
        novelty=("novel", "mean"),
        strict_hit_rate=("hit", "mean"),
        target_mae=("target_error", "mean"),
        mean_uncertainty=("uncertainty", "mean"),
    )
    # pandas 2.0 compatibility: corr() only reads target/prediction columns,
    # so inclusion of the grouping columns does not affect the calculation.
    correlations = raw.groupby(["arm", "seed"], as_index=False).apply(corr)
    correlations = correlations.rename(columns={None: "target_prediction_correlation", 0: "target_prediction_correlation"})
    arm_seed = arm_seed.merge(correlations, on=["arm", "seed"], how="left")
    arm_seed.to_csv(args.output_dir / "arm_seed_metrics.csv", index=False)

    target_summary = raw.groupby(["arm", "target"], as_index=False).agg(
        predicted_mean=("predicted_log_sigma", "mean"),
        strict_hit_rate=("hit", "mean"),
        target_mae=("target_error", "mean"),
    )
    target_summary.to_csv(args.output_dir / "target_summary.csv", index=False)

    summary = {
        "status": "fixed_audit_complete",
        "raw_total": int(len(raw)),
        "raw_per_arm": {arm: int((raw["arm"] == arm).sum()) for arm in ARMS},
        "correlation_definition": "Pearson correlation over per-sample target and predicted_log_sigma across all three target levels within each arm x seed; single-target bins are undefined/NaN.",
        "correlation_values": arm_seed[["arm", "seed", "target_prediction_correlation"]].to_dict(orient="records"),
        "source_is_canonical_read_only": True,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=True) + "\n")
    print(json.dumps(summary, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
