#!/usr/bin/env python3
"""Freeze Structural-OOD scope and audit reusable checkpoints without MD."""
import hashlib, json
from pathlib import Path
import pandas as pd
from mingpt_split import build_split

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "structural-ood"
PY = ROOT / "vendor" / "PolyGen-1.0.0" / "minGPT" / "htp_md.csv"
SRC = ROOT / "inputs" / "release-data" / "htpmd-trainset.csv"

def sha(p):
    h = hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    split = build_split(PY, "structure-disjoint", seed=42)
    split.train.to_csv(OUT / "train_rows.csv", index=False)
    split.validation.to_csv(OUT / "heldout_rows.csv", index=False)
    all_rows = pd.concat([split.train, split.validation], ignore_index=True)
    targets = [float(all_rows.conductivity.astype(float).replace(0, float('nan')).dropna().min())]
    ckpts = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "results").glob("**/final.pt"))
    structural_ckpts = [p for p in ckpts if "structure-disjoint" in p or "structural-ood" in p]
    manifest = {
        "benchmark": "continuous-vs-binary Structural-OOD prediction phase",
        "region": "structural_ood",
        "status": "blocked_for_matched_prediction",
        "source_data": str(SRC), "source_sha256": sha(SRC),
        "split_source": str(PY), "split_source_sha256": sha(PY),
        "split": split.metadata,
        "grouping": {"primary": "exact p-SMILES / mol_smiles", "family_grouping": "not available in released table; exact structure grouping is conservative proxy", "close_analogue_crossing": "not assessed without repeat-unit family annotations"},
        "target_grid": {"policy": "reuse compatible interpolation grid; unsupported cells must remain explicit", "cells": targets, "note": "conductivity column is binary in this released minGPT table; continuous target grid is unsupported here"},
        "arms": ["continuous", "binary", "unconditional_reranking"],
        "matched_settings": {"seeds": [17,42,202,303,907], "samples_per_cell": 100, "md": False},
        "checkpoint_inventory": {"all_final_checkpoints": ckpts, "matched_structural_checkpoints": structural_ckpts},
        "blocking_reasons": [
            "No continuous and binary checkpoints trained on the frozen structure-disjoint split.",
            "Released structure-disjoint training run is unconditional only and cannot support the requested arm comparison.",
            "Released table lacks polymer scaffold/family annotations; exact structure grouping is not equivalent to family grouping.",
            "No MD launched; no MD-confirmed claims are made."
        ],
        "candidate_pool": "empty_until_matched_structural_checkpoints_and_family_annotations_exist"
    }
    (OUT / "frozen_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    pd.DataFrame(columns=["region","arm","target","candidate_id","structure","rf_prediction","uncertainty","support","novelty","acquisition_score","reason"]).to_csv(OUT / "candidate_pool_for_manager.csv", index=False)
    summary = {"status": manifest["status"], "train_rows": len(split.train), "heldout_rows": len(split.validation), "train_unique": split.train.mol_smiles.nunique(), "heldout_unique": split.validation.mol_smiles.nunique(), "candidate_pool_rows": 0, "blocking_reasons": manifest["blocking_reasons"]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = """# Structural-OOD prediction-phase audit\n\nStatus: BLOCKED_FOR_MATCHED_PREDICTION\n\nA reproducible exact-structure-disjoint split was frozen from the released minGPT table (seed 42). The released data contain binary conductivity labels and no scaffold/family annotation, so this is a conservative structure-disjoint proxy, not a validated scaffold/family split. Existing checkpoints do not include matched continuous and binary models trained on this split. The only structural-disjoint checkpoint is unconditional, so no arm comparison or candidate ranking is reported.\n\nNo MD was started. The manager candidate pool is intentionally empty.\n"""
    (OUT / "STRUCTURAL_OOD_REPORT.md").write_text(report)
    print(json.dumps({"output": str(OUT), **summary}, indent=2))

if __name__ == "__main__": main()
