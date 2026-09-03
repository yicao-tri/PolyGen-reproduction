#!/usr/bin/env python3
"""Recompute PolyGen metrics for a released diffusionLM sample file."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


BUNDLED_REPO = Path(__file__).resolve().parents[1] / "vendor" / "PolyGen-1.0.0"
METRIC_NAMES = (
    "uniqueness",
    "novelty",
    "validity",
    "synthesizability",
    "similarity",
    "diversity",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=BUNDLED_REPO,
        help="PolyGen checkout; defaults to the patched v1.0.0 source bundled in this package",
    )
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--label", choices=("conditional", "unconditional"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import numpy as np  # pylint: disable=import-outside-toplevel
    import torch  # pylint: disable=import-outside-toplevel

    # Load the Conda C++ runtime via torch before pandas on the Ubuntu 20.04 DLAMI.
    import pandas as pd  # pylint: disable=import-outside-toplevel
    from rdkit import Chem  # pylint: disable=import-outside-toplevel
    from rdkit.DataStructs import TanimotoSimilarity  # pylint: disable=import-outside-toplevel

    repo = args.repo.resolve()
    samples_path = args.samples.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(repo)
    sys.path.insert(0, str(repo))

    from diffusionLM.metrics import (  # pylint: disable=import-outside-toplevel
        calculateScore,
        calculate_diversity,
        calculate_morgan_fingerprint,
        check_novelty,
        extract_samples,
        extract_smiles,
        has_two_ends,
        validate_mol,
    )

    generated = pd.read_csv(samples_path, header=None, names=["mol_smiles"])
    original_rows = len(generated)
    if args.label == "conditional":
        generated, low = extract_samples(generated)
        selected_low_rows = len(low)
    else:
        selected_low_rows = None
    generated = generated.copy()
    generated["mol_smiles"] = generated["mol_smiles"].apply(
        lambda token: extract_smiles(token, args.label)
    )
    num_samples = len(generated)
    if not num_samples:
        raise RuntimeError("No samples remained after label selection")

    train = pd.read_csv(repo / "diffusionLM" / "htp_md.csv", sep="\t")
    generated["duplicate"] = generated["mol_smiles"].duplicated()
    uniqueness = 1 - generated["duplicate"].sum() / num_samples
    scored = check_novelty(generated, train, "mol_smiles")
    novelty = 1 - (scored["diversity"] != "novel").sum() / num_samples
    scored = has_two_ends(validate_mol(scored, "mol_smiles"))
    # The release helper redirects sys.stderr to a StringIO and does not restore it.
    sys.stderr = sys.__stderr__
    valid = scored[(scored["validity"] == "ok") & (scored["has_two_ends"] == True)]  # noqa: E712
    validity = len(valid) / num_samples
    clean = scored[
        (~scored["duplicate"])
        & (scored["diversity"] == "novel")
        & (scored["validity"] == "ok")
        & (scored["has_two_ends"] == True)  # noqa: E712
    ]
    if clean.empty:
        synthesizability = similarity = diversity = None
    else:
        sa_scores = [calculateScore(Chem.MolFromSmiles(smiles)) for smiles in clean["mol_smiles"]]
        synthesizability = sum(score < 5 for score in sa_scores) / len(clean)
        generated_fp = calculate_morgan_fingerprint(clean["mol_smiles"])
        train_fp = calculate_morgan_fingerprint(train["mol_smiles"])
        similarities = [
            np.mean([TanimotoSimilarity(fp, other) for other in train_fp])
            for fp in generated_fp
        ]
        similarity = float(np.mean(similarities))
        if len(clean) >= 2:
            _, diversity = calculate_diversity(clean["mol_smiles"].tolist())
            diversity = float(diversity)
        else:
            diversity = None

    metric_values = (uniqueness, novelty, validity, synthesizability, similarity, diversity)
    metrics = dict(
        zip(METRIC_NAMES, (None if value is None else float(value) for value in metric_values))
    )
    result = {
        "samples": str(samples_path),
        "label": args.label,
        "input_rows": original_rows,
        "selected_rows": num_samples,
        "selected_low_rows": selected_low_rows,
        "clean_rows": len(clean),
        "torch_version": torch.__version__,
        "metrics": metrics,
    }
    scored.to_csv(output / "scored_samples.csv", index=False)
    (output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # Preserve a traceback even if release metrics redirected stderr.
        sys.stderr = sys.__stderr__
        traceback.print_exc(file=sys.stdout)
        raise
