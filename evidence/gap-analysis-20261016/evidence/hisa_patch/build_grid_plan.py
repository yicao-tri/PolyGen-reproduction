#!/usr/bin/env python3
"""Build the explicit PolyGen generation grid manifest.

The planner creates design cells only; it never launches generation.
"""
from pathlib import Path
import csv, json

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [17, 42, 202, 303, 907]
ARMS = ["binary", "continuous"]
STEPS = [1000, 2000, 3000]
TEMPS = [0.8, 1.0, 1.2]
TARGETS = [-5.0, -4.0, -3.0]
MODELS = [("gpt-nano", "planned"), ("gpt-small", "blocked_missing_checkpoint")]

def main():
    rows = []
    for model, model_status in MODELS:
        for steps in STEPS:
            for temp in TEMPS:
                config = f"{model}_steps{steps}_temp{temp:.1f}"
                for seed in SEEDS:
                    for arm in ARMS:
                        rows.append({
                            "config_id": config,
                            "cell_id": f"{config}_{arm}_seed{seed}",
                            "model": model,
                            "model_status": model_status,
                            "steps": steps,
                            "temperature": temp,
                            "seed": seed,
                            "arm": arm,
                            "targets_log10_S_cm": "-5.0|-4.0|-3.0",
                            "samples_per_target": "100|100|100",
                            "raw_samples_per_seed_arm": 300,
                            "raw_samples_per_arm_config": 1500,
                            "paired_with": f"{config}_{'continuous' if arm == 'binary' else 'binary'}_seed{seed}",
                            "output_root": f"results/experiment-c/grid/{config}/{arm}-seed{seed}",
                            "status": "planned" if model_status == "planned" else "blocked",
                            "blocker": "" if model_status == "planned" else "real gpt-small checkpoint and training entry point required",
                            "estimated_gpu_hours": {1000: 0.5, 2000: 1.0, 3000: 1.5}[steps]
                        })
    out = ROOT / "GRID_CELLS.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    model_rows = {
        model: [row for row in rows if row["model"] == model]
        for model, _ in MODELS
    }
    model_totals = {
        model: {
            "raw_samples": sum(int(row["raw_samples_per_seed_arm"]) for row in model_rows[model]),
            "estimated_gpu_hours": sum(float(row["estimated_gpu_hours"]) for row in model_rows[model]),
        }
        for model, _ in MODELS
    }
    plan = {
        "schema_version": "polygen-grid-plan-v1",
        "status": "design_only_not_executed",
        "dimensions": {"models": [x[0] for x in MODELS], "steps": STEPS, "temperatures": TEMPS, "seeds": SEEDS, "arms": ARMS, "targets": TARGETS},
        "cells_total": len(rows),
        "planned_executable_cells": sum(r["status"] == "planned" for r in rows),
        "blocked_cells": sum(r["status"] == "blocked" for r in rows),
        "raw_samples_per_arm_config": 1500,
        "raw_samples_per_seed_arm": 300,
        "target_allocation_per_seed_arm": {"-5.0": 100, "-4.0": 100, "-3.0": 100},
        "planned_raw_samples_gpt_nano": model_totals["gpt-nano"]["raw_samples"],
        "estimated_gpu_hours_gpt_nano": model_totals["gpt-nano"]["estimated_gpu_hours"],
        "blocked_raw_samples_gpt_small": model_totals["gpt-small"]["raw_samples"],
        "estimated_gpu_hours_gpt_small": model_totals["gpt-small"]["estimated_gpu_hours"],
        "model_totals_derived_from_rows": model_totals,
        "pairing_rule": "same seed, target allocation, split, steps, temperature, and sample budget for binary/continuous",
        "identity_key": "model x steps x temperature x seed x arm",
        "primary_ranking": "valid + novel + in-support + uncertainty gate, then predicted_log_sigma - 1.96 * uncertainty descending",
        "stage_3_pfp_md": "out of scope and requires explicit user sign-off"
    }
    (ROOT / "GRID_PLAN.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan, indent=2))

if __name__ == "__main__": main()
