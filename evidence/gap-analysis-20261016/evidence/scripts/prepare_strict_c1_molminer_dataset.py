#!/usr/bin/env python3
"""Prepare an isolated, one-property MolMiner C1 training preflight.

This does not claim to be the final five-seed strict retraining. It creates a
task-aligned corpus from the exact PolyGen C1 generator-training rows, maps
Au/Cu endpoints to MolMiner wildcards, and keeps the locked C1 rows in a
separate test file. The output is intended for vocabulary/preprocessing smoke
and subsequent owner-reviewed retraining.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--canonical-root", type=Path, required=True)
    p.add_argument("--molminer-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()

    sys.path.insert(0, str(args.molminer_root.resolve()))
    from molminer import repeat_unit

    source_path = args.canonical_root / "inputs/release-data/htpmd-trainset.csv"
    raw = pd.read_csv(source_path)[["mol_smiles", "conductivity"]].copy()
    raw["log_conductivity"] = np.log10(raw.conductivity.astype(float))
    deciles = pd.qcut(raw.log_conductivity, 10, labels=False, duplicates="drop")
    train, locked = train_test_split(
        raw, test_size=0.2, random_state=20260923, stratify=deciles
    )

    def convert(frame: pd.DataFrame) -> pd.DataFrame:
        rows = []
        failed = []
        for source_index, row in frame.iterrows():
            psmiles = repeat_unit.normalise_endpoints(
                str(row.mol_smiles).replace("[Au]", "*").replace("[Cu]", "*")
            )
            if repeat_unit.validate(psmiles):
                failed.append({"source_index": int(source_index), "reason": "invalid_repeat_unit", "smiles": psmiles})
                continue
            canonical = repeat_unit.canonical(psmiles)
            if canonical is None:
                failed.append({"source_index": int(source_index), "reason": "canonicalization_failed", "smiles": psmiles})
                continue
            rows.append({
                "source_index": int(source_index),
                "smiles": canonical,
                "log_conductivity": float(row.log_conductivity),
            })
        return pd.DataFrame(rows), failed

    train_out, train_fail = convert(train)
    locked_out, locked_fail = convert(locked)
    # Keep the exact C1 generator-training support in train.csv. The valid file
    # is a small structural smoke subset only; final strict retraining must
    # define its checkpoint-selection split before publication claims.
    valid_out = train_out.sample(n=min(128, len(train_out)), random_state=20261016).sort_values("source_index")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    train_out[["smiles", "log_conductivity"]].to_csv(out / "train.csv", index=False)
    valid_out[["smiles", "log_conductivity"]].to_csv(out / "valid.csv", index=False)
    locked_out[["smiles", "log_conductivity"]].to_csv(out / "test.csv", index=False)
    (out / "source_train_rows.csv").write_text(train_out.to_csv(index=False))
    (out / "source_locked_rows.csv").write_text(locked_out.to_csv(index=False))
    manifest = {
        "schema_version": "polygen-c1-molminer-preflight-v1",
        "source": str(source_path),
        "source_sha256": sha256(source_path),
        "split_policy": "train_test_split(test_size=0.2, random_state=20260923, stratified by 10 log-conductivity deciles)",
        "source_rows": int(len(raw)),
        "generator_training_source_rows": int(len(train)),
        "locked_source_rows": int(len(locked)),
        "converted_train_rows": int(len(train_out)),
        "converted_locked_rows": int(len(locked_out)),
        "train_unique_smiles": int(train_out.smiles.nunique()),
        "locked_unique_smiles": int(locked_out.smiles.nunique()),
        "train_conversion_failures": train_fail,
        "locked_conversion_failures": locked_fail,
        "property": "log_conductivity",
        "endpoint_policy": "[Au]/[Cu] -> two MolMiner wildcard endpoints, then repeat_unit.canonical",
        "valid_file_policy": "128-row structural smoke subset sampled from train support; not a final checkpoint-selection protocol",
        "strict_claim_status": "preprocessing_preflight_only",
        "files": {},
    }
    for name in ("train.csv", "valid.csv", "test.csv", "source_train_rows.csv", "source_locked_rows.csv"):
        path = out / name
        manifest["files"][name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "output": str(out),
        "train_rows": len(train_out),
        "locked_rows": len(locked_out),
        "train_failures": len(train_fail),
        "locked_failures": len(locked_fail),
        "status": manifest["strict_claim_status"],
    }, indent=2))


if __name__ == "__main__":
    main()
