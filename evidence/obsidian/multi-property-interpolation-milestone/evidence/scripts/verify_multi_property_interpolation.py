#!/usr/bin/env python3
"""Independent artifact verifier for the multi-property interpolation package."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "multi-property" / "interpolation"
SOURCE = ROOT / "inputs" / "release-data" / "htpmd-trainset.csv"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main():
    required = ["design_contract.json", "source_audit.json", "frozen_manifest.json", "transform_scaler_manifest.json", "target_cells.csv", "target_support_audit.json", "candidate_predictions.csv", "metrics_by_cell.csv", "paired_contrasts.csv", "unsupported_cells.csv", "pairing_leakage_audit.json", "run_manifest.json", "run_exit_codes.csv", "REPORT.md"]
    checks = {f"file:{f}": (OUT / f).is_file() and (OUT / f).stat().st_size > 0 for f in required}
    manifest = json.loads((OUT / "frozen_manifest.json").read_text())
    audit = json.loads((OUT / "source_audit.json").read_text())
    leakage = json.loads((OUT / "pairing_leakage_audit.json").read_text())
    cells = pd.read_csv(OUT / "target_cells.csv")
    cand = pd.read_csv(OUT / "candidate_predictions.csv")
    metrics = pd.read_csv(OUT / "metrics_by_cell.csv")
    unsupported = pd.read_csv(OUT / "unsupported_cells.csv")
    checks.update({
        "source_hash_matches": audit["source_sha256"] == sha(SOURCE) == manifest["source_sha256"],
        "split_counts": audit["split"]["train_rows"] == 4819 and audit["split"]["test_rows"] == 1205,
        "six_properties": manifest["properties"] == ["log10_conductivity", "log10_li_diffusivity", "log10_tfsi_diffusivity", "log10_poly_diffusivity", "transference_number", "molality"],
        "target_grid_21": len(cells) == 21 and cells.target_cell.nunique() == 21,
        "target_grid_non_cartesian": manifest["joint_target_cartesian_product_used"] is False,
        "coherent_joint_targets_3": int((cells.target_family == "coherent_joint").sum()) == 3,
        "candidate_rows_42000": len(cand) == 42000,
        "metrics_rows_420": len(metrics) == 420,
        "all_cells_n100": bool((cand.groupby(["arm", "seed", "target_cell"]).size() == 100).all()),
        "all_arms": set(cand.arm) == {"multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"},
        "all_seeds": set(cand.seed) == {17, 42, 202, 303, 907},
        "binary_policy_explicit": bool((cand.loc[cand.arm == "binary_conductivity", "condition_input_policy"] == "fixed_high_low_conductivity_label_only").all()),
        "no_md": bool((cand.md_status == "not_run").all()),
        "no_force_field": bool((cand.force_field_coverage == "not_assessed").all()),
        "historical_audit_pass": leakage["checks"]["historical_reference_manifests_preserved"],
        "pairing_audit_pass": leakage["status"] == "pass",
        "unsupported_file_schema": set(unsupported.columns) == {"scope", "arm", "seed", "target_cell", "status", "reason"},
    })
    # Every run must have an explicit, internally consistent checkpoint origin.
    origins = manifest.get("checkpoint_origins", {})
    for arm in ("multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"):
        for seed in (17, 42, 202, 303, 907):
            key = f"{arm}|seed{seed}"
            origin = origins.get(key, {})
            steps = origin.get("steps")
            source = origin.get("checkpoint_origin", "")
            checks[f"checkpoint_origin:{key}"] = (steps in (0, 1000)) and bool(source) and bool(origin.get("checkpoint_sha256"))
            if steps == 0:
                checks[f"checkpoint_file:{key}"] = "results/experiment-c" in source
            else:
                checks[f"checkpoint_file:{key}"] = source == "trained_in_multi_property_interpolation"
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "counts": {"cells": len(cells), "candidate_rows": len(cand), "metrics_rows": len(metrics), "unsupported_rows": len(unsupported)}}
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
