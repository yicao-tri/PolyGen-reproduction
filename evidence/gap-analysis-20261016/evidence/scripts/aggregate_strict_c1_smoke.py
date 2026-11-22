#!/usr/bin/env python3
"""Aggregate the per-training-seed strict-C1 MolMiner smoke outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evidence/experiments/molminer_strict_c1/five_seed_generation_smoke"
SEEDS = [17, 23, 31, 47, 59]


def main():
    seed_manifests = {
        str(seed): json.loads((BASE / f"seed{seed}/manifest.json").read_text())
        for seed in SEEDS
    }
    samples = pd.concat(
        [pd.read_csv(BASE / f"seed{s}/samples.csv") for s in SEEDS],
        ignore_index=True,
    )
    metrics = pd.concat(
        [pd.read_csv(BASE / f"seed{s}/metrics_by_training_seed_target.csv") for s in SEEDS],
        ignore_index=True,
    )
    samples.to_csv(BASE / "aggregate_samples.csv", index=False)
    metrics.to_csv(BASE / "aggregate_metrics_by_training_seed_target.csv", index=False)
    by_target = (
        metrics.groupby("target", as_index=False)
        .agg(
            training_seed_count=("training_seed", "nunique"),
            raw_n=("raw_n", "sum"),
            validity_mean=("repeat_unit_validity", "mean"),
            validity_sem=("repeat_unit_validity", lambda x: x.std(ddof=1) / len(x) ** 0.5),
            exactly_two_star_mean=("exactly_two_star_rate", "mean"),
            strict_hit_mean=("strict_hit_rate", "mean"),
            target_mae_valid_mean=("target_mae_valid", "mean"),
        )
    )
    by_target.to_csv(BASE / "aggregate_metrics_by_target.csv", index=False)
    table = by_target.copy()
    table.insert(0, "arm", "MolMiner strict C1 five-seed smoke")
    table["evidence_status"] = "engineering_smoke_only"
    table["notes"] = "five training seeds, five epochs, 10 samples per target; not final matched-budget result"
    table.to_csv(ROOT / "assets/tables/T12_molminer_strict_c1_smoke.csv", index=False)
    training_rows = []
    for seed in SEEDS:
        log = ROOT / f"evidence/experiments/molminer_strict_c1/c1_strict_5seed_smoke_seed{seed}_trainlog.txt"
        lines = log.read_text(errors="replace").splitlines()
        parsed = []
        for line in lines:
            m = re.search(
                r"Epoch \[(\d+)/5\].*Mean train loss: ([0-9.]+).*Mean val loss: ([0-9.]+).*Non-term top1: ([0-9.]+)",
                line,
            )
            if m:
                parsed.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
        if len(parsed) != 5:
            raise RuntimeError(f"expected 5 finite epoch records for seed {seed}, got {len(parsed)}")
        best = min(parsed, key=lambda x: x[2])
        last = parsed[-1]
        training_rows.append({
            "training_seed": seed,
            "epochs_completed": len(parsed),
            "best_val_loss": best[2],
            "best_val_epoch": best[0],
            "final_train_loss": last[1],
            "final_val_loss": last[2],
            "final_nonterm_top1": last[3],
            "all_losses_finite": True,
        })
    pd.DataFrame(training_rows).to_csv(ROOT / "evidence/data/molminer_strict_c1_five_seed_training_summary.csv", index=False)
    summary = {
        "status": "engineering_smoke_only",
        "training_seeds": SEEDS,
        "raw_rows": int(len(samples)),
        "valid_repeat_units": int(samples.valid_repeat_unit.sum()),
        "exactly_two_star_units": int(samples.exactly_two_stars.sum()),
        "strict_hits": int(samples.strict_hit.sum()),
        "valid_rate": float(samples.valid_repeat_unit.mean()),
        "exactly_two_star_rate": float(samples.exactly_two_stars.mean()),
        "strict_hit_rate": float(samples.strict_hit.mean()),
        "target_mae_valid": float(samples.loc[samples.valid_repeat_unit, "target_error"].mean()),
        "per_training_seed": (
            samples.groupby("training_seed", as_index=False)
            .agg(
                raw_n=("training_seed", "size"),
                valid_rate=("valid_repeat_unit", "mean"),
                exactly_two_star_rate=("exactly_two_stars", "mean"),
                strict_hit_rate=("strict_hit", "mean"),
            )
            .to_dict(orient="records")
        ),
        "publication_boundary": "five-seed five-epoch smoke only; not the final matched-budget comparison",
        "training_summary": "evidence/data/molminer_strict_c1_five_seed_training_summary.csv",
    }
    aggregate_manifest = {
        "schema_version": "polygen-strict-c1-molminer-five-seed-common-budget-smoke-v1",
        "status": "complete_engineering_smoke_only",
        "training_seeds": SEEDS,
        "evaluation_seeds": [17],
        "targets": [-5.0, -4.0, -3.0],
        "samples_per_target_per_training_seed": 10,
        "total_requested_samples": 150,
        "checkpoint_sha256": {seed: seed_manifests[str(seed)]["checkpoint_sha256"][str(seed)] for seed in SEEDS},
        "per_seed_manifests": [f"seed{seed}/manifest.json" for seed in SEEDS],
        "aggregate_outputs": ["aggregate_samples.csv", "aggregate_metrics_by_target.csv", "aggregate_summary.json"],
        "publication_boundary": summary["publication_boundary"],
    }
    (BASE / "aggregate_manifest.json").write_text(json.dumps(aggregate_manifest, indent=2) + "\n")
    (BASE / "aggregate_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=True) + "\n")
    print(json.dumps(summary, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
