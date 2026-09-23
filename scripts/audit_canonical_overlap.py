#!/usr/bin/env python3
"""Check exact-string split results again using RDKit canonical SMILES."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from rdkit import Chem


def canonicalize(value: str) -> str | None:
    molecule = Chem.MolFromSmiles(value)
    return Chem.MolToSmiles(molecule, canonical=True) if molecule is not None else None


def audit(run_summary: Path) -> dict:
    summary = json.loads(run_summary.read_text(encoding="utf-8"))
    prepared = run_summary.parent / "prepared_split.tsv"
    frame = pd.read_csv(prepared, sep="\t")
    frame["canonical"] = frame["mol_smiles"].map(canonicalize)
    train_rows = summary["training"]["train_rows"]
    train = set(frame.iloc[:train_rows]["canonical"].dropna())
    validation = set(frame.iloc[train_rows:]["canonical"].dropna())
    return {
        "policy": summary["split"]["policy"],
        "parse_failures": int(frame["canonical"].isna().sum()),
        "train_unique_canonical_structures": len(train),
        "validation_unique_canonical_structures": len(validation),
        "train_validation_canonical_overlap": len(train & validation),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-summary", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"runs": [audit(path) for path in args.run_summary]}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
