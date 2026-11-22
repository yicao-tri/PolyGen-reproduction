#!/usr/bin/env python3
"""Audit canonical PolyGen assets without mutating the canonical repository.

The audit is deliberately narrow: it checks the frozen prediction assets, the
generation grid completeness, and the physical-validation gate.  It writes
only into the evidence package passed by --out.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SEEDS = (17, 42, 202, 303, 907)
ARMS = ("binary", "continuous")
CONFIGS = tuple(
    f"gpt-nano_steps{steps}_temp{temp}"
    for steps in (1000, 2000, 3000)
    for temp in ("0.8", "1.0", "1.2")
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_rows(path: Path):
    with path.open(newline="") as fh:
        yield from csv.DictReader(fh)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = args.canonical_root
    out = args.out
    data_dir = out / "evidence/data"
    data_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = root / "results/extrapolation/frozen_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    grid_root = root / "results/experiment-c/grid"
    grid_summary_path = grid_root / "analysis/grid_analysis_summary.json"
    grid_summary = json.loads(grid_summary_path.read_text())
    grid_audit_path = grid_root / "analysis/grid_file_audit.csv"
    grid_audit = list(csv_rows(grid_audit_path))

    expected_pairs = len(CONFIGS) * len(ARMS) * len(SEEDS)
    observed_pairs = len(grid_audit)
    complete_configs = []
    config_rows = []
    for config in CONFIGS:
        present = []
        for arm in ARMS:
            for seed in SEEDS:
                sample = grid_root / config / f"{arm}-seed{seed}/samples.csv"
                present.append(sample.exists())
        n_present = sum(present)
        config_rows.append({
            "config_id": config,
            "expected_arm_seed_pairs": len(ARMS) * len(SEEDS),
            "observed_arm_seed_pairs": n_present,
            "complete": n_present == len(ARMS) * len(SEEDS),
            "raw_samples_expected": len(ARMS) * len(SEEDS) * 300,
            "raw_samples_observed": n_present * 300,
            "analysis_in_summary": config in grid_summary.get("configs", []),
            "status": "observed_complete" if n_present == len(ARMS) * len(SEEDS) else "missing_outputs",
        })
        if n_present == len(ARMS) * len(SEEDS):
            complete_configs.append(config)

    critical = [
        ("frozen_source", root / "inputs/release-data/htpmd-trainset.csv", "observed", "frozen HTP-MD source"),
        ("c1_effect_summary", root / "results/experiment-c/publication/c1_five_seed_effect_summary.csv", "observed", "five-seed effect summary"),
        ("extrapolation_aggregate", root / "results/extrapolation/publication/extrapolation_aggregate_metrics.csv", "observed", "prediction-only extrapolation"),
        ("locked_tail_audit", root / "results/extrapolation/locked_tail_verifier_audit.csv", "observed", "blind locked-tail audit"),
        ("candidate_selection", root / "results/extrapolation/candidate_selection_for_md.csv", "observed_status_only", "candidate queue proposal; MD not started"),
        ("md_batch_manifest", root / "results/experiment-c/md-validation/md_batch_manifest.csv", "observed_status_only", "PLANNED_NOT_RUN manifest"),
        ("top1_readiness", root / "results/experiment-c/md-validation/top1_readiness_audit.json", "observed_status_only", "PCFF+ readiness gate"),
        ("pfp_pilot_summary", root / "results/experiment-c/pfp-pilot/production/analysis/paired/paired_summary.json", "mixed_observed_and_planned", "smoke-only physical anchor"),
        ("grid_summary", grid_summary_path, "observed", "generation-grid summary"),
    ]
    asset_rows = []
    for asset_id, path, status, note in critical:
        asset_rows.append({
            "asset_id": asset_id,
            "canonical_path": str(path),
            "present": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256(path) if path.exists() else "",
            "status": status if path.exists() else "unavailable",
            "notes": note,
        })

    with (data_dir / "grid_asset_audit.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(config_rows[0]))
        writer.writeheader()
        writer.writerows(config_rows)
    with (data_dir / "asset_inventory.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asset_rows[0]))
        writer.writeheader()
        writer.writerows(asset_rows)

    gate = json.loads((root / "results/experiment-c/md-validation/top1_readiness_audit.json").read_text())
    gates = gate.get("gates", {})
    result = {
        "canonical_root": str(root),
        "source": {
            "path": str(root / "inputs/release-data/htpmd-trainset.csv"),
            "sha256": manifest.get("source_sha256"),
            "source_rows": manifest.get("source_rows"),
            "training_rows": manifest.get("training_rows"),
            "locked_tail_rows": manifest.get("locked_tail_rows"),
            "training_max_log10_sigma": manifest.get("training_max_log10_sigma"),
        },
        "grid": {
            "expected_configs": list(CONFIGS),
            "observed_complete_configs": complete_configs,
            "expected_config_count": len(CONFIGS),
            "complete_config_count": len(complete_configs),
            "expected_arm_seed_pairs": expected_pairs,
            "observed_arm_seed_pairs": observed_pairs,
            "expected_raw_rows": expected_pairs * 300,
            "observed_raw_rows_from_file_audit": sum(int(r.get("raw_n", 0)) for r in grid_audit),
            "analysis_summary_status": grid_summary.get("status"),
            "analysis_summary_raw_total": grid_summary.get("raw_total"),
            "status": "complete" if len(complete_configs) == len(CONFIGS) and observed_pairs == expected_pairs else "incomplete",
            "note": "All nine planned configurations have sample outputs; the analysis log is stale relative to grid_analysis_summary.json and should be regenerated before publication.",
        },
        "physical_validation_gate": {
            "top1_readiness_decision": gate.get("decision", "unknown"),
            "top1_pcff_plus_parameter_coverage": gates.get("top1_pcff_plus_parameter_coverage"),
            "arc_pcff_plus_execution_integration": gates.get("arc_pcff_plus_execution_integration"),
            "md_status": manifest.get("md"),
            "decision": "blocked_until_pcff_plus_coverage_and_owner_approval",
        },
        "asset_rows": asset_rows,
    }
    (data_dir / "asset_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
