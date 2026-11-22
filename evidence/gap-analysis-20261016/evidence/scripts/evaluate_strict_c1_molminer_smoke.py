#!/usr/bin/env python3
"""Evaluate five isolated strict-C1 MolMiner smoke checkpoints.

This runner keeps the strict training support and the frozen PolyGen C1 RF
verifier separate from the released MolMiner descriptive baseline. It is a
five-seed, five-epoch engineering smoke, not a publication-budget result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT
CANONICAL = Path("/Users/yicao/Documents/ARC/PolyGen-reproduction")
MOLMINER = Path("/Users/yicao/Documents/ARC/resourses/molminer-polymer")
STRICT = PACKAGE / "evidence/experiments/molminer_strict_c1"
TARGETS = (-5.0, -4.0, -3.0)
RDLogger.DisableLog("rdApp.warning")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def endpoint_label_smiles(smiles: str) -> str:
    out = smiles
    for token in ("[Au]", "[Cu]"):
        out = out.replace("*", token, 1)
    return out


def fingerprint(smiles: str):
    mol = Chem.MolFromSmiles(smiles.replace("[Cu]", "[*]").replace("[Au]", "[*]"))
    return None if mol is None else AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)


def fp_array(fp):
    out = np.zeros(2048, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fp, out)
    return out


def make_verifier():
    frame = pd.read_csv(CANONICAL / "inputs/release-data/htpmd-trainset.csv")
    frame = frame[["mol_smiles", "conductivity"]].copy()
    frame["log_sigma"] = np.log10(frame.conductivity)
    bins = pd.qcut(frame.log_sigma, 10, labels=False, duplicates="drop")
    train, test = train_test_split(
        frame, test_size=0.2, random_state=20260923, stratify=bins
    )
    train = train.reset_index(drop=True)
    test = test.reset_index(drop=True)
    train_fp = [fingerprint(x) for x in train.mol_smiles]
    test_fp = [fingerprint(x) for x in test.mol_smiles]
    if any(x is None for x in train_fp + test_fp):
        raise RuntimeError("unparseable source row in frozen C1 verifier")
    model = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features="sqrt",
        n_jobs=-1,
        random_state=20260923,
    )
    model.fit(np.stack([fp_array(x) for x in train_fp]), train.log_sigma)
    return model, train_fp, set(train.mol_smiles), {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_max_log_sigma": float(train.log_sigma.max()),
    }


def score_common(smiles, target, verifier, train_fp, train_smiles):
    labelled = endpoint_label_smiles(smiles)
    fp = fingerprint(labelled)
    if fp is None:
        return {
            "verifier_valid": False,
            "predicted_log_sigma": np.nan,
            "uncertainty": np.nan,
            "support": np.nan,
            "novel": False,
            "target_error": np.nan,
            "strict_hit": False,
        }
    vec = np.asarray([fp_array(fp)])
    pred = float(verifier.predict(vec)[0])
    tree = np.asarray([est.predict(vec)[0] for est in verifier.estimators_])
    support = float(max(DataStructs.TanimotoSimilarity(fp, x) for x in train_fp))
    novel = labelled not in train_smiles and smiles not in train_smiles
    err = abs(pred - target)
    return {
        "verifier_valid": True,
        "predicted_log_sigma": pred,
        "uncertainty": float(tree.std(ddof=1)),
        "support": support,
        "novel": bool(novel),
        "target_error": err,
        "strict_hit": bool(novel and support >= 0.35 and tree.std(ddof=1) < 0.35 and err < 0.5),
    }


def checkpoint_map(seeds):
    return {
        int(seed): STRICT / f"checkpoints_strict5_seed{seed}/best_c1_strict_5seed_smoke_seed{seed}.pth"
        for seed in seeds
    }


def run(args):
    sys.path.insert(0, str(MOLMINER))
    from molminer import repeat_unit  # noqa: E402
    from molminer.generator import MolecularGenerator  # noqa: E402

    verifier, train_fp, verifier_train_smiles, verifier_meta = make_verifier()
    train_frame = pd.read_csv(STRICT / "train.csv")
    strict_corpus = {
        c for c in (repeat_unit.canonical(x) for x in train_frame.smiles) if c is not None
    }
    checkpoints = checkpoint_map(args.training_seeds)
    missing = [str(p) for p in checkpoints.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("missing checkpoints: " + "; ".join(missing))

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "polygen-strict-c1-molminer-five-seed-smoke-v1",
        "status": "engineering_smoke_only",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "training_seeds": list(args.training_seeds),
        "evaluation_seeds": list(args.evaluation_seeds),
        "targets": list(TARGETS),
        "samples_per_target_per_evaluation_seed": args.samples_per_target,
        "total_requested_samples": len(args.training_seeds) * len(args.evaluation_seeds) * len(TARGETS) * args.samples_per_target,
        "strict_data_dir": str(STRICT),
        "strict_train_rows": int(len(train_frame)),
        "checkpoint_sha256": {str(k): sha256(v) for k, v in checkpoints.items()},
        "verifier": verifier_meta,
        "verifier_policy": "same frozen PolyGen C1 RF policy: support >= 0.35, tree SD < 0.35, target error < 0.5, novel",
        "publication_boundary": "five-seed five-epoch smoke only; not the final matched-budget comparison",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    rows = []
    dock_rows = []
    for training_seed, checkpoint in checkpoints.items():
        generator = MolecularGenerator(
            ckpt_molminer=checkpoint,
            stats_path=STRICT / "stats.json",
            vocab_fragments=STRICT / "vocab_fragments.csv",
            vocab_attachments=STRICT / "vocab_attachments.csv",
            vocab_anchors=STRICT / "vocab_anchors.csv",
            device=args.device,
            max_fragments=args.max_fragments,
            track_dock_stats=True,
        )
        for evaluation_seed in args.evaluation_seeds:
            for target_index, target in enumerate(TARGETS):
                batch_seed = int(training_seed * 100000 + evaluation_seed * 10 + target_index)
                random.seed(batch_seed)
                np.random.seed(batch_seed % (2**32 - 1))
                torch.manual_seed(batch_seed)
                generator.reset_dock_stats()
                results = generator.sample_with_intermediate_smiles(
                    num_samples=args.samples_per_target,
                    properties={"log_conductivity": target},
                    seed=batch_seed,
                    greedy=False,
                    max_tries=10,
                )
                for sample_index, (smiles, failed, message, intermediates) in enumerate(results):
                    reasons = repeat_unit.validate(smiles) if smiles else [message or "generation_failed"]
                    canonical = repeat_unit.canonical(smiles) if smiles else None
                    common = score_common(smiles, target, verifier, train_fp, verifier_train_smiles) if smiles else {
                        "verifier_valid": False, "predicted_log_sigma": np.nan,
                        "uncertainty": np.nan, "support": np.nan, "novel": False,
                        "target_error": np.nan, "strict_hit": False,
                    }
                    mol = Chem.MolFromSmiles(smiles) if smiles else None
                    rows.append({
                        "training_seed": training_seed,
                        "evaluation_seed": evaluation_seed,
                        "target": target,
                        "sample_index": sample_index,
                        "batch_seed": batch_seed,
                        "smiles": smiles or "",
                        "canonical": canonical or "",
                        "generation_failed": bool(failed),
                        "failure_message": message,
                        "validation_reasons": ";".join(reasons),
                        "valid_repeat_unit": not reasons,
                        "exactly_two_stars": bool(smiles and smiles.count("*") == 2),
                        "strict_corpus_novel": bool(canonical and canonical not in strict_corpus),
                        "fragment_steps": len(intermediates),
                        "heavy_atoms": int(mol.GetNumHeavyAtoms()) if mol is not None else np.nan,
                        **common,
                    })
                dock = generator.dock_stats_summary()
                dock.update({"training_seed": training_seed, "evaluation_seed": evaluation_seed, "target": target})
                dock_rows.append(dock)
                print(f"completed training_seed={training_seed} evaluation_seed={evaluation_seed} target={target:g}", flush=True)

    raw = pd.DataFrame(rows)
    raw.to_csv(output / "samples.csv", index=False)
    pd.DataFrame(dock_rows).to_csv(output / "dock_stats.csv", index=False)
    metrics = []
    for (training_seed, target), group in raw.groupby(["training_seed", "target"], sort=True):
        valid = group[group.valid_repeat_unit]
        metrics.append({
            "training_seed": int(training_seed),
            "target": float(target),
            "raw_n": int(len(group)),
            "generation_success": float((~group.generation_failed).mean()),
            "repeat_unit_validity": float(group.valid_repeat_unit.mean()),
            "exactly_two_star_rate": float(group.exactly_two_stars.mean()),
            "strict_corpus_novelty": float(group.strict_corpus_novel.mean()),
            "common_verifier_validity": float(group.verifier_valid.mean()),
            "common_verifier_novelty": float(group.novel.mean()),
            "in_support_rate": float((group.support >= 0.35).mean()),
            "uncertainty_gate_rate": float((group.uncertainty < 0.35).mean()),
            "strict_hit_rate": float(group.strict_hit.mean()),
            "target_mae_valid": float(valid.target_error.mean()) if len(valid) else np.nan,
        })
    metric_frame = pd.DataFrame(metrics)
    metric_frame.to_csv(output / "metrics_by_training_seed_target.csv", index=False)
    summary = {
        "status": "engineering_smoke_only",
        "raw_rows": int(len(raw)),
        "valid_repeat_units": int(raw.valid_repeat_unit.sum()),
        "exactly_two_star_units": int(raw.exactly_two_stars.sum()),
        "strict_hits": int(raw.strict_hit.sum()),
        "valid_rate": float(raw.valid_repeat_unit.mean()),
        "exactly_two_star_rate": float(raw.exactly_two_stars.mean()),
        "strict_hit_rate": float(raw.strict_hit.mean()),
        "target_mae_valid": float(raw.loc[raw.valid_repeat_unit, "target_error"].mean()),
        "by_training_seed": metric_frame.groupby("training_seed", as_index=False).agg(
            valid_rate=("repeat_unit_validity", "mean"),
            exactly_two_star_rate=("exactly_two_star_rate", "mean"),
            strict_hit_rate=("strict_hit_rate", "mean"),
        ).to_dict(orient="records"),
        "publication_boundary": manifest["publication_boundary"],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=True) + "\n")
    print(json.dumps(summary, indent=2, allow_nan=True))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=STRICT / "five_seed_generation_smoke")
    p.add_argument("--training-seeds", type=int, nargs="+", default=[17, 23, 31, 47, 59])
    p.add_argument("--evaluation-seeds", type=int, nargs="+", default=[17, 42, 202, 303, 907])
    p.add_argument("--samples-per-target", type=int, default=20)
    p.add_argument("--device", default="cpu")
    p.add_argument("--max-fragments", type=int, default=80)
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
