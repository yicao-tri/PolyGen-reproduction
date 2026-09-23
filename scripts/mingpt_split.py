#!/usr/bin/env python3
"""Build auditable minGPT train/validation splits.

The released ``htp_md.csv`` is already class-balanced by duplicating the
high-conductivity structures.  Splitting its rows therefore leaks structures.
This module provides both the released row split and a corrected split that
groups by p-SMILES before balancing the training partition only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


@dataclass(frozen=True)
class SplitResult:
    train: pd.DataFrame
    validation: pd.DataFrame
    unique_source: pd.DataFrame
    metadata: dict


def _partition_summary(frame: pd.DataFrame) -> dict:
    by_label = {}
    for label, group in frame.groupby("conductivity", sort=True):
        by_label[str(int(label))] = {
            "rows": int(len(group)),
            "unique_structures": int(group["mol_smiles"].nunique()),
        }
    return {
        "rows": int(len(frame)),
        "unique_structures": int(frame["mol_smiles"].nunique()),
        "by_label": by_label,
    }


def _overlap_summary(train: pd.DataFrame, validation: pd.DataFrame) -> dict:
    result = {}
    for label in sorted(set(train["conductivity"]) | set(validation["conductivity"])):
        train_structures = set(train.loc[train["conductivity"] == label, "mol_smiles"])
        validation_rows = validation.loc[validation["conductivity"] == label]
        validation_structures = set(validation_rows["mol_smiles"])
        intersection = train_structures & validation_structures
        result[str(int(label))] = {
            "overlap_unique_structures": len(intersection),
            "validation_unique_structures": len(validation_structures),
            "overlap_validation_rows": int(validation_rows["mol_smiles"].isin(train_structures).sum()),
            "validation_rows": int(len(validation_rows)),
        }
    return result


def _read_released(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep="\t")
    required = {"mol_smiles", "conductivity"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{path} must contain {sorted(required)}")
    frame = frame[["mol_smiles", "conductivity"]].copy()
    frame["conductivity"] = frame["conductivity"].astype(int)
    conflicting = frame.groupby("mol_smiles")["conductivity"].nunique()
    if (conflicting > 1).any():
        raise ValueError("the same structure has conflicting conductivity labels")
    return frame


def build_split(path: Path, policy: str, seed: int = 42, test_size: float = 0.2) -> SplitResult:
    released = _read_released(path)
    unique_source = released.drop_duplicates("mol_smiles", keep="first").reset_index(drop=True)

    if policy == "released-random":
        train, validation = train_test_split(
            released, test_size=test_size, random_state=seed, shuffle=True
        )
        train = train.reset_index(drop=True)
        validation = validation.reset_index(drop=True)
        balance_stage = "before_split_in_released_file"
    elif policy == "structure-disjoint":
        train_unique, validation = train_test_split(
            unique_source,
            test_size=test_size,
            random_state=seed,
            shuffle=True,
            stratify=unique_source["conductivity"],
        )
        counts = train_unique["conductivity"].value_counts()
        target = int(counts.max())
        rng = np.random.RandomState(seed)
        balanced_parts = []
        for label in sorted(counts.index):
            group = train_unique.loc[train_unique["conductivity"] == label]
            extra_count = target - len(group)
            if extra_count:
                sampled_positions = rng.choice(len(group), size=extra_count, replace=True)
                group = pd.concat([group, group.iloc[sampled_positions]], ignore_index=True)
            balanced_parts.append(group)
        train = pd.concat(balanced_parts, ignore_index=True)
        train = train.iloc[rng.permutation(len(train))].reset_index(drop=True)
        validation = validation.reset_index(drop=True)
        balance_stage = "training_partition_only"
    else:
        raise ValueError(f"unknown split policy: {policy}")

    overlap = _overlap_summary(train, validation)
    if policy == "structure-disjoint" and any(
        values["overlap_unique_structures"] for values in overlap.values()
    ):
        raise AssertionError("structure-disjoint split contains train/validation overlap")

    metadata = {
        "policy": policy,
        "seed": seed,
        "test_size": test_size,
        "balance_stage": balance_stage,
        "released_source": _partition_summary(released),
        "unique_source": _partition_summary(unique_source),
        "train": _partition_summary(train),
        "validation": _partition_summary(validation),
        "overlap_by_label": overlap,
    }
    return SplitResult(train=train, validation=validation, unique_source=unique_source, metadata=metadata)


def write_prepared_split(result: SplitResult, path: Path) -> tuple[list[int], list[int]]:
    """Write one TSV suitable for SmilesDataset and return partition indices."""
    path.parent.mkdir(parents=True, exist_ok=True)
    combined = pd.concat([result.train, result.validation], ignore_index=True)
    combined.to_csv(path, sep="\t", index=False)
    train_indices = list(range(len(result.train)))
    validation_indices = list(range(len(result.train), len(combined)))
    return train_indices, validation_indices
