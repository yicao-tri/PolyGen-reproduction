#!/usr/bin/env python3
"""Run the frozen six-property true-extrapolation benchmark.

The implementation reuses the audited multi-property upper-tail runner while
changing only the pre-frozen region split and target grid.
"""
from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mp_upper", ROOT / "scripts/multi_property_upper-tail.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
base.OUT = ROOT / "results/multi-property/extrapolation"
base.TARGET_LABELS = ("Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50")
base.ARMS = ("multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking")

def load_source():
    raw = base.pd.read_csv(base.SOURCE)
    raw["source_row_id"] = base.np.arange(len(raw), dtype=int)
    values = base.transform(raw)
    finite = base.np.isfinite(values.to_numpy()).all(axis=1)
    q80 = values.quantile(.80)
    train_mask = finite & values.le(q80, axis="columns").all(axis=1)
    train = raw.loc[train_mask].copy().reset_index(drop=True)
    train_values = values.loc[train_mask].copy().reset_index(drop=True)
    train_values["source_row_id"] = train.source_row_id.to_numpy()
    maxima = train_values.loc[:, list(base.PROPERTIES)].max()
    full_targets = []
    for label, q, offset in [("Q90", .90, None), ("Q100", 1.0, None), ("train_max_plus_0.25", None, .25), ("train_max_plus_0.50", None, .50)]:
        vec = values.quantile(q) if q is not None else maxima + offset
        full_targets.append({"label": label, "quantile": q, "definition": "full-source query; locked post-run only", "values_transformed": {p: float(vec[p]) for p in base.PROPERTIES}, "values_raw": {p: float(10 ** vec[p]) if mode == "log10" else float(vec[p]) for p, mode in base.PROPERTY_SPECS}})
    audit = {"source": str(base.SOURCE), "source_sha256": base.sha256(base.SOURCE), "source_rows": len(raw), "properties": [{"name": p, "transform": mode, "full_source_q80": float(values[p].quantile(.8)), "full_source_q90": float(values[p].quantile(.9)), "full_source_q100": float(values[p].max()), "finite_rows": int(np.isfinite(values[p]).sum())} for p, mode in base.PROPERTY_SPECS], "joint_training_rule": "all six transformed properties <= full-source Q80", "joint_training_rows": int(train_mask.sum()), "joint_training_unique_smiles": int(train.mol_smiles.nunique()), "joint_training_maxima": {p: float(maxima[p]) for p in base.PROPERTIES}, "locked_rows": int((~train_mask).sum()), "binary_cutoff_log10_conductivity": base.BINARY_CUTOFF, "binary_joint_training_class_counts": {str(int(k)): int(v) for k, v in (train_values.conductivity >= base.BINARY_CUTOFF).astype(int).value_counts().items()}, "locked_rows_never_used_for_fit_or_selection": True}
    return raw, values, train_values, audit, full_targets

base.load_source = load_source
base.write_freeze()
base.run_definitive()
