#!/usr/bin/env python3
"""Evaluate the finite 20-epoch strict-C1 MolMiner checkpoints.

This deliberately reuses the smoke evaluator's frozen C1 verifier and scoring
policy, but points it at the independent extended-training checkpoints.  The
result is a separate engineering comparison and never overwrites the
five-epoch smoke evidence.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STRICT = ROOT / "evidence/experiments/molminer_strict_c1"
SMOKE_SCRIPT = ROOT / "evidence/scripts/evaluate_strict_c1_molminer_smoke.py"


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("strict_c1_smoke_evaluator", SMOKE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SMOKE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    module = load_smoke_module()
    seeds = [17, 23, 31, 47, 59]
    epochs = 20
    checkpoint_root = STRICT / f"extended_{epochs}epoch"
    module.checkpoint_map = lambda requested: {
        int(seed): checkpoint_root
        / f"seed{seed}"
        / "checkpoints"
        / f"best_c1_extended{epochs}_seed{seed}.pth"
        for seed in requested
    }
    # The original evaluator uses this path as its smoke default.  Keep the
    # same small comparison budget: one evaluation seed and 10 samples per
    # target, now with a 20-epoch checkpoint.
    args = module.parse_args()
    if args.output == module.STRICT / "five_seed_generation_smoke":
        args.output = STRICT / "extended_20epoch_generation"
    if args.training_seeds == [17, 23, 31, 47, 59]:
        args.training_seeds = seeds
    if args.evaluation_seeds == [17, 42, 202, 303, 907]:
        args.evaluation_seeds = [17]
    if args.samples_per_target == 20:
        args.samples_per_target = 10
    module.run(args)
    # The shared evaluator writes its smoke schema by design.  Rewrite only
    # the boundary metadata for this isolated extended run so the numeric
    # outputs remain directly comparable without being mislabeled.
    boundary = (
        "five-seed twenty-epoch strict-C1 engineering comparison; same 150-row "
        "generation budget as the five-epoch smoke; not a final publication leaderboard"
    )
    for name in ("manifest.json", "summary.json"):
        path = args.output / name
        data = json.loads(path.read_text())
        data["schema_version"] = data["schema_version"].replace(
            "five-seed-smoke", "five-seed-extended20-comparison"
        )
        data["status"] = "extended_training_engineering_comparison"
        data["publication_boundary"] = boundary
        path.write_text(json.dumps(data, indent=2, allow_nan=True) + "\n")


if __name__ == "__main__":
    main()
