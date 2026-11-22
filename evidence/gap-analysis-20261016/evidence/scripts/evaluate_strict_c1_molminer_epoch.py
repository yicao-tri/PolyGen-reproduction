#!/usr/bin/env python3
"""Evaluate a strict-C1 MolMiner epoch directory under the frozen RF audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import importlib.util


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--training-seeds", type=int, nargs="+", default=[17, 23, 31, 47, 59])
    parser.add_argument("--evaluation-seeds", type=int, nargs="+", default=[17])
    parser.add_argument("--samples-per-target", type=int, default=10)
    args = parser.parse_args()

    module = load_smoke_module()
    checkpoint_root = STRICT / f"extended_{args.epochs}epoch"
    seeds = list(args.training_seeds)
    module.checkpoint_map = lambda requested: {
        int(seed): checkpoint_root
        / f"seed{seed}"
        / "checkpoints"
        / f"best_c1_extended{args.epochs}_seed{seed}.pth"
        for seed in requested
    }
    smoke_args = type("Args", (), {
        "output": args.output,
        "training_seeds": seeds,
        "evaluation_seeds": list(args.evaluation_seeds),
        "samples_per_target": args.samples_per_target,
        "device": "cpu",
        "max_fragments": 80,
    })()
    module.run(smoke_args)
    boundary = (
        f"five-seed {args.epochs}-epoch strict-C1 engineering comparison; same "
        "150-row generation budget as the five-epoch smoke; not a final "
        "publication leaderboard"
    )
    for name in ("manifest.json", "summary.json"):
        path = args.output / name
        data = json.loads(path.read_text())
        data["schema_version"] = f"polygen-strict-c1-molminer-{args.epochs}epoch-comparison-v1"
        data["status"] = "extended_training_engineering_comparison"
        data["publication_boundary"] = boundary
        path.write_text(json.dumps(data, indent=2, allow_nan=True) + "\n")


if __name__ == "__main__":
    main()
