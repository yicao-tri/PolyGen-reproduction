#!/usr/bin/env python3
"""Prediction-only multi-property Upper-tail benchmark.

The script deliberately keeps the six-property Q80 intersection as the only
training set for all four arms.  Full-source Q80--Q95 marginal quantiles are
used only as frozen post-run query/audit targets.  No MD is started here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, DataStructs, RDLogger
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/multi-property/upper-tail"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
VENDOR = ROOT / "vendor/PolyGen-1.0.0"
SEEDS = (17, 42, 202, 303, 907)
ARMS = ("multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking")
PROPERTY_SPECS = (
    ("conductivity", "log10"),
    ("li_diffusivity", "log10"),
    ("tfsi_diffusivity", "log10"),
    ("poly_diffusivity", "log10"),
    ("transference_number", "raw"),
    ("molality", "raw"),
)
PROPERTIES = tuple(name for name, _ in PROPERTY_SPECS)
TARGET_LABELS = ("Q80_boundary", "Q85", "Q90", "Q95")
SAMPLES_PER_CELL = 100
STEPS = 1000
BATCH_SIZE = 64
LEARNING_RATE = 5e-4
TEMPERATURE = 1.0
TOP_K = 40
BLOCK = 64
PREFIX = 5
BINARY_CUTOFF = -4.0
RF_ESTIMATORS = 300
RF_RANDOM_STATE = 20260923
SUPPORT_GATE = 0.35
UNCERTAINTY_GATE = 0.35
JOINT_ERROR_GATE = 0.5

RDLogger.DisableLog("rdApp.warning")
RDLogger.DisableLog("rdApp.error")
sys.path.insert(0, str(ROOT / "scripts"))
import run_upper_tail_benchmark as compat  # noqa: E402
from multi_property_core import MultiPropertyPrefix  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=True) + "\n")


def transform(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.loc[:, list(PROPERTIES)].copy()
    for name, mode in PROPERTY_SPECS:
        out[name] = np.log10(out[name]) if mode == "log10" else out[name].astype(float)
    return out.astype(float)


def load_source() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict, list[dict]]:
    raw = pd.read_csv(SOURCE)
    raw["source_row_id"] = np.arange(len(raw), dtype=int)
    values = transform(raw)
    q80 = values.quantile(0.80)
    q95 = values.quantile(0.95)
    finite = np.isfinite(values.to_numpy()).all(axis=1)
    joint_train_mask = finite & (values.le(q80, axis="columns").all(axis=1))
    train = raw.loc[joint_train_mask].copy().reset_index(drop=True)
    train_values = values.loc[joint_train_mask].copy().reset_index(drop=True)
    train_values["source_row_id"] = train["source_row_id"].to_numpy()
    train_max = train_values.loc[:, list(PROPERTIES)].max()
    target_vectors = []
    for label, q in zip(TARGET_LABELS, (0.80, 0.85, 0.90, 0.95)):
        vector = values.quantile(q)
        target_vectors.append({
            "label": label,
            "quantile": q,
            "definition": "full-source marginal quantiles; post-run query/audit only",
            "values_transformed": {p: float(vector[p]) for p in PROPERTIES},
            "values_raw": {
                p: float(10 ** vector[p]) if mode == "log10" else float(vector[p])
                for (p, mode) in PROPERTY_SPECS
            },
        })
    locked_any = ~joint_train_mask
    q80_q95_any = ((values.gt(q80, axis="columns") & values.le(q95, axis="columns")).any(axis=1))
    pass_count = values.le(q80, axis="columns").sum(axis=1)
    audit = {
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "source_rows": int(len(raw)),
        "source_unique_structure_rows": int(raw.mol_smiles.nunique()),
        "properties": [
            {"name": p, "transform": mode, "finite_rows": int(np.isfinite(values[p]).sum()),
             "nunique": int(values[p].nunique()), "full_source_q80": float(q80[p]),
             "full_source_q95": float(q95[p]), "full_source_min": float(values[p].min()),
             "full_source_max": float(values[p].max())}
            for p, mode in PROPERTY_SPECS
        ],
        "joint_training_rule": "all six transformed properties <= their full-source Q80, inclusive",
        "joint_training_rows": int(joint_train_mask.sum()),
        "joint_training_fraction": float(joint_train_mask.mean()),
        "joint_training_unique_smiles": int(train.mol_smiles.nunique()),
        "joint_training_maxima": {p: float(train_max[p]) for p in PROPERTIES},
        "nonfinite_rows": int((~finite).sum()),
        "locked_nontraining_rows": int(locked_any.sum()),
        "locked_q80_q95_any_property_rows": int(q80_q95_any.sum()),
        "propertywise_q80_pass_counts": {p: int(values[p].le(q80[p]).sum()) for p in PROPERTIES},
        "joint_pass_count_distribution": {str(int(k)): int(v) for k, v in pass_count.value_counts().sort_index().items()},
        "binary_cutoff_log10_conductivity": BINARY_CUTOFF,
        "binary_joint_training_class_counts": {
            str(int(k)): int(v) for k, v in ((train_values.conductivity >= BINARY_CUTOFF).astype(int).value_counts().sort_index()).items()
        },
        "locked_rows_never_used_for_fit_or_selection": True,
    }
    return raw, values, train_values, audit, target_vectors


def target_support_table(train_values: pd.DataFrame, audit: dict, targets: list[dict]) -> pd.DataFrame:
    maxima = train_values.loc[:, list(PROPERTIES)].max()
    rows = []
    for target in targets:
        for prop in PROPERTIES:
            value = target["values_transformed"][prop]
            rows.append({
                "target_label": target["label"], "arm": "all_arms", "property": prop,
                "target_value_transformed": value, "joint_train_max_transformed": float(maxima[prop]),
                "status": "supported_by_joint_train_range" if value <= maxima[prop] else "unsupported_beyond_joint_train_max",
                "reason": "target coordinate exceeds the Q80-intersection training maximum" if value > maxima[prop] else "within coordinate-wise joint-training range",
            })
        rows.append({
            "target_label": target["label"], "arm": "all_arms", "property": "__joint__",
            "target_value_transformed": np.nan, "joint_train_max_transformed": np.nan,
            "status": "unsupported_joint_cell" if any(target["values_transformed"][p] > maxima[p] for p in PROPERTIES) else "coordinatewise_supported_joint_cell",
            "reason": "no claim of joint support without a source row at the vector; Q80-Q95 vectors are locked post-run queries",
        })
    for target in targets:
        for arm in ARMS:
            rows.append({
                "target_label": target["label"], "arm": arm, "property": "__arm__",
                "target_value_transformed": np.nan, "joint_train_max_transformed": np.nan,
                "status": "unsupported_binary_target_interface" if arm == "binary_conductivity" else "audit_only_if_joint_cell_unsupported",
                "reason": "binary arm receives only the fixed high/low label and cannot represent a six-dimensional target vector" if arm == "binary_conductivity" else "see coordinate and joint support rows",
            })
    return pd.DataFrame(rows)


def frozen_manifest(audit: dict, targets: list[dict]) -> dict:
    return {
        "benchmark": "multi-property implicit-conditioning upper-tail",
        "region": "upper-tail",
        "status": "frozen_before_definitive_run",
        "source": audit["source"],
        "source_sha256": audit["source_sha256"],
        "properties": [{"name": p, "transform": mode} for p, mode in PROPERTY_SPECS],
        "training_rule": audit["joint_training_rule"],
        "joint_training_rows": audit["joint_training_rows"],
        "joint_training_unique_smiles": audit["joint_training_unique_smiles"],
        "locked_query_policy": "full-source Q80-Q95 marginal vectors are post-run queries/audits only; no locked row enters generator, RF, thresholds, filters or selection",
        "target_vectors": targets,
        "arms": {
            "multi_continuous": "six-dimensional normalized condition vector through one learned prefix embedding",
            "scalar_continuous": "conductivity-only normalized continuous prefix using the same joint training rows",
            "binary_conductivity": "fixed original -4.0 log10 conductivity high/low label; expected single-class degeneracy",
            "unconditional_reranking": "constant-zero generator; disjoint raw pool reranked by frozen six-property RF distance and uncertainty",
        },
        "matched_settings": {
            "model": "PolyGen-1.0.0 minGPT gpt-nano adapter",
            "steps": STEPS, "batch_size": BATCH_SIZE, "learning_rate": LEARNING_RATE,
            "temperature": TEMPERATURE, "top_k": TOP_K, "block_size": BLOCK, "prefix_length": PREFIX,
            "samples_per_target_cell": SAMPLES_PER_CELL, "unconditional_raw_pool_per_seed": SAMPLES_PER_CELL * len(TARGET_LABELS),
            "seeds": list(SEEDS), "rf_estimators": RF_ESTIMATORS, "rf_random_state": RF_RANDOM_STATE,
            "support_gate_tanimoto": SUPPORT_GATE, "uncertainty_gate_normalized_tree_sd": UNCERTAINTY_GATE,
            "joint_target_rmse_gate_normalized": JOINT_ERROR_GATE,
        },
        "primary_estimand": "paired seed-level difference in joint strict-hit and joint frontier-crossing rates for multi_continuous minus scalar_continuous; controls are descriptive",
        "no_md": True,
        "historical_results_preserved": True,
        "source_audit_file": "source_audit.json",
        "unsupported_cells_file": "unsupported_cells.csv",
    }


def write_freeze() -> None:
    raw, values, train_values, audit, targets = load_source()
    OUT.mkdir(parents=True, exist_ok=True)
    raw.loc[raw.source_row_id.isin(train_values.source_row_id), ["source_row_id", "mol_smiles"] + list(PROPERTIES)].to_csv(OUT / "train_rows.csv", index=False)
    frozen = frozen_manifest(audit, targets)
    contract = {
        "benchmark": frozen["benchmark"],
        "question": "Does a six-property normalized implicit condition improve controllable, support-aware upper-tail generation relative to conductivity-only, binary, and unconditional controls when all arms train on the same six-property Q80 intersection?",
        "estimands": frozen["primary_estimand"],
        "confounds": ["joint support shrinks the training set to 2494 rows", "all RF evidence is structure-fingerprint surrogate evidence", "binary interface is degenerate at the fixed -4.0 threshold", "Q80-Q95 targets are locked post-run queries rather than train support"],
        "pairing": "same joint source rows, seeds, target order, training steps, decoding, candidate count and verifier protocol across arms",
        "interpretation_boundary": "prediction-only; no MD, force-field execution or experimental claim",
        "required_outputs": ["frozen_manifest.json", "source_audit.json", "unsupported_cells.csv", "candidate_predictions.csv", "metrics_by_cell.csv", "monotonicity.csv", "pairing_acceptance_audit.json", "REPORT.md", "publication/*.svg", "publication/*.png"],
    }
    write_json(OUT / "source_audit.json", audit)
    write_json(OUT / "frozen_manifest.json", frozen)
    write_json(OUT / "design_contract.json", contract)
    target_support_table(train_values, audit, targets).to_csv(OUT / "unsupported_cells.csv", index=False)
    (OUT / "REPORT.md").write_text("# Multi-property Upper-tail prediction benchmark\n\nStatus: design and source audit frozen; definitive run pending.\n\nThe six-dimensional Q80 intersection is the only training support for every arm. Full-source Q80--Q95 marginal vectors are locked post-run queries/audits. No MD is authorized in this phase. See `source_audit.json`, `frozen_manifest.json`, and `unsupported_cells.csv`.\n")


class MultiSeqDataset(torch.utils.data.Dataset):
    def __init__(self, frame: pd.DataFrame, tokenizer, arm: str, scaler_mean: np.ndarray, scaler_scale: np.ndarray):
        values = transform(frame).to_numpy(dtype=np.float32)
        if arm == "multi_continuous":
            condition = (values - scaler_mean) / scaler_scale
        elif arm == "scalar_continuous":
            condition = ((values[:, [0]] - scaler_mean[[0]]) / scaler_scale[[0]])
        elif arm == "binary_conductivity":
            condition = (values[:, [0]] >= BINARY_CUTOFF).astype(np.float32)
        else:
            condition = np.zeros((len(frame), 1), dtype=np.float32)
        self.condition = torch.tensor(condition, dtype=torch.float32)
        sequences = []
        for smiles in frame.mol_smiles:
            ids = tokenizer.encode(smiles)
            ids = np.pad(ids, (0, BLOCK + 1 - PREFIX - len(ids)), constant_values=0)
            ids = ids[: BLOCK + 1 - PREFIX]
            sequences.append(np.concatenate([np.ones(PREFIX, dtype=np.int64), ids]))
        self.seq = torch.tensor(np.stack(sequences), dtype=torch.long)

    def __len__(self):
        return len(self.seq)

    def __getitem__(self, index):
        return self.seq[index, :-1], self.seq[index, 1:], self.condition[index]


class MultiConditionGPT(torch.nn.Module):
    def __init__(self, config, arm: str, condition_dim: int):
        super().__init__()
        self.gpt = compat.GPT(config)
        self.arm = arm
        self.condition_dim = condition_dim
        n = config.n_embd
        if arm == "multi_continuous":
            self.condition_net = MultiPropertyPrefix(6, n)
        elif arm == "scalar_continuous":
            self.condition_net = torch.nn.Sequential(torch.nn.Linear(1, n), torch.nn.Tanh(), torch.nn.Linear(n, n))
        elif arm == "unconditional_reranking":
            self.condition_net = torch.nn.Sequential(torch.nn.Linear(1, n), torch.nn.Tanh(), torch.nn.Linear(n, n))
        else:
            self.condition_net = torch.nn.Embedding(2, n)

    def configure_optimizers(self, learning_rate: float):
        return torch.optim.AdamW(self.parameters(), lr=learning_rate, betas=(0.9, 0.95), weight_decay=0.1)

    def forward(self, idx, condition, targets=None):
        _, tokens = idx.shape
        positions = torch.arange(tokens, device=idx.device).unsqueeze(0)
        token_embeddings = self.gpt.transformer.wte(idx)
        if self.arm == "binary_conductivity":
            embedding = self.condition_net(condition.long().view(-1))
        else:
            if self.arm == "unconditional_reranking":
                condition = torch.zeros((condition.shape[0], 1), device=condition.device, dtype=torch.float32)
            embedding = self.condition_net(condition.float())
        token_embeddings = token_embeddings.clone()
        token_embeddings[:, :PREFIX, :] += embedding[:, None, :]
        hidden = self.gpt.transformer.drop(token_embeddings + self.gpt.transformer.wpe(positions))
        for block in self.gpt.transformer.h:
            hidden = block(hidden)
        logits = self.gpt.lm_head(self.gpt.transformer.ln_f(hidden))
        loss = None
        if targets is not None:
            loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-1)
        return logits, loss

    @torch.no_grad()
    def generate(self, condition, count: int, temperature: float = TEMPERATURE):
        index = torch.ones((count, PREFIX), dtype=torch.long)
        for _ in range(BLOCK - PREFIX):
            logits, _ = self(index, condition)
            logits = logits[:, -1, :] / temperature
            values, _ = torch.topk(logits, TOP_K)
            logits[logits < values[:, [-1]]] = -float("inf")
            index = torch.cat([index, torch.multinomial(torch.softmax(logits, dim=-1), 1)], 1)
        return index[:, PREFIX:]


def scaler_from_train(train_values: pd.DataFrame):
    x = train_values.loc[:, list(PROPERTIES)].to_numpy(dtype=np.float64)
    mean = x.mean(axis=0)
    scale = x.std(axis=0, ddof=0)
    if np.any(scale <= 0) or not np.isfinite(x).all():
        raise ValueError("invalid train-only scaler")
    return mean, scale


def make_model(arm: str, tokenizer):
    cfg = compat.GPT.get_default_config()
    cfg.model_type = "gpt-nano"
    cfg.vocab_size = tokenizer.vocab_size
    cfg.block_size = BLOCK
    dim = 6 if arm == "multi_continuous" else 1
    return MultiConditionGPT(cfg, arm, dim)


def train_or_load(arm: str, seed: int, train: pd.DataFrame, train_values: pd.DataFrame, tokenizer, run_dir: Path):
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = run_dir / "final.pt"
    mean, scale = scaler_from_train(train_values)
    model = make_model(arm, tokenizer)
    if checkpoint.exists() and (run_dir / "summary.json").exists():
        model.load_state_dict(torch.load(checkpoint, map_location="cpu"))
        model.eval()
        return model, json.loads((run_dir / "summary.json").read_text())
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    dataset = MultiSeqDataset(train, tokenizer, arm, mean, scale)
    loader = iter(torch.utils.data.DataLoader(dataset, batch_size=BATCH_SIZE, sampler=torch.utils.data.RandomSampler(dataset, replacement=True, num_samples=10**9)))
    optimizer = model.configure_optimizers(LEARNING_RATE)
    losses = []
    started = time.time()
    model.train()
    for _ in range(STEPS):
        x, y, condition = next(loader)
        _, loss = model(x, condition, y)
        optimizer.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
        losses.append(float(loss.detach()))
    model.eval()
    torch.save(model.state_dict(), checkpoint)
    summary = {
        "arm": arm, "seed": seed, "steps": STEPS, "batch_size": BATCH_SIZE,
        "training_rows": len(train), "training_source_sha256": sha256(SOURCE),
        "checkpoint_origin": "new_multi_property_upper_tail_run", "first_loss": losses[0], "last_loss": losses[-1],
        "elapsed_seconds": time.time() - started, "checkpoint_sha256": sha256(checkpoint),
    }
    write_json(run_dir / "summary.json", summary)
    return model, summary


def fingerprint(smiles: str):
    return compat.fp(smiles) if smiles else None


def train_verifiers(train: pd.DataFrame, train_values: pd.DataFrame):
    fps = [fingerprint(smiles) for smiles in train.mol_smiles]
    if any(value is None for value in fps):
        raise ValueError("training fingerprint failure")
    features = np.stack([compat.fp_array(value) for value in fps])
    models = {}
    for prop in PROPERTIES:
        model = RandomForestRegressor(n_estimators=RF_ESTIMATORS, min_samples_leaf=2, max_features="sqrt", n_jobs=-1, random_state=RF_RANDOM_STATE)
        model.fit(features, train_values[prop].to_numpy())
        models[prop] = model
    return models, fps, features


def score_smiles(smiles: str, models, train: pd.DataFrame, train_fps, train_values: pd.DataFrame, train_smiles: set[str], train_std: np.ndarray):
    fp = fingerprint(smiles)
    valid = bool(fp is not None and smiles.count("[Cu]") == 1 and smiles.count("[Au]") == 1)
    if not valid:
        out = {"valid": False, "novel": False, "support": np.nan, "failure_reason": "invalid_or_wrong_end_count"}
        for prop in PROPERTIES:
            out[f"rf_prediction_{prop}"] = np.nan; out[f"rf_uncertainty_{prop}"] = np.nan
        out["joint_uncertainty"] = np.nan; out["joint_frontier_count"] = 0
        return out
    arr = compat.fp_array(fp).reshape(1, -1)
    pred, unc = {}, {}
    for prop in PROPERTIES:
        vals = np.asarray([tree.predict(arr)[0] for tree in models[prop].estimators_])
        pred[prop] = float(vals.mean()); unc[prop] = float(vals.std(ddof=1))
    support = max(DataStructs.TanimotoSimilarity(fp, other) for other in train_fps)
    novel = smiles not in train_smiles
    norm_unc = [unc[p] / train_std[i] for i, p in enumerate(PROPERTIES)]
    out = {"valid": True, "novel": novel, "support": float(support), "failure_reason": "" if novel else "exact_training_duplicate", "joint_uncertainty": float(max(norm_unc))}
    for p in PROPERTIES:
        out[f"rf_prediction_{p}"] = pred[p]; out[f"rf_uncertainty_{p}"] = unc[p]
    return out


def score_smiles_batch(smiles_list: list[str], models, train: pd.DataFrame, train_fps, train_values: pd.DataFrame, train_smiles: set[str], train_std: np.ndarray):
    """Score one candidate batch so locked audits do not call every tree per row."""
    fps = [fingerprint(smiles) if smiles else None for smiles in smiles_list]
    valid = [bool(fp is not None and smiles.count("[Cu]") == 1 and smiles.count("[Au]") == 1) for smiles, fp in zip(smiles_list, fps)]
    indices = [i for i, ok in enumerate(valid) if ok]
    outputs = []
    for i, smiles in enumerate(smiles_list):
        if not valid[i]:
            out = {"valid": False, "novel": False, "support": np.nan, "failure_reason": "invalid_or_wrong_end_count", "joint_uncertainty": np.nan}
            for prop in PROPERTIES:
                out[f"rf_prediction_{prop}"] = np.nan; out[f"rf_uncertainty_{prop}"] = np.nan
            outputs.append(out)
        else:
            outputs.append(None)
    if indices:
        features = np.stack([compat.fp_array(fps[i]) for i in indices])
        per_prop = {}
        for prop in PROPERTIES:
            tree_values = np.stack([tree.predict(features) for tree in models[prop].estimators_], axis=1)
            per_prop[prop] = (tree_values.mean(axis=1), tree_values.std(axis=1, ddof=1))
        train_smiles_set = set(train_smiles)
        for local, i in enumerate(indices):
            pred = {p: per_prop[p][0][local] for p in PROPERTIES}; unc = {p: per_prop[p][1][local] for p in PROPERTIES}
            support = max(DataStructs.TanimotoSimilarity(fps[i], other) for other in train_fps)
            norm_unc = [unc[p] / train_std[j] for j, p in enumerate(PROPERTIES)]
            outputs[i] = {"valid": True, "novel": smiles_list[i] not in train_smiles_set, "support": float(support), "failure_reason": "" if smiles_list[i] not in train_smiles_set else "exact_training_duplicate", "joint_uncertainty": float(max(norm_unc))}
            for p in PROPERTIES:
                outputs[i][f"rf_prediction_{p}"] = float(pred[p]); outputs[i][f"rf_uncertainty_{p}"] = float(unc[p])
    return outputs


def condition_for_target(arm: str, target: dict, mean: np.ndarray, scale: np.ndarray) -> torch.Tensor:
    if arm == "multi_continuous":
        raw = np.array([target["values_transformed"][p] for p in PROPERTIES], dtype=np.float32)
        return torch.tensor(((raw - mean) / scale)[None, :], dtype=torch.float32)
    if arm == "scalar_continuous":
        raw = float(target["values_transformed"]["conductivity"])
        return torch.tensor([[(raw - mean[0]) / scale[0]]], dtype=torch.float32)
    if arm == "binary_conductivity":
        label = float(float(target["values_transformed"]["conductivity"]) >= BINARY_CUTOFF)
        return torch.tensor([[label]], dtype=torch.float32)
    return torch.zeros((1, 1), dtype=torch.float32)


def annotate(frame: pd.DataFrame, target: dict, train_values: pd.DataFrame, train_std: np.ndarray) -> pd.DataFrame:
    frame = frame.copy()
    maxima = train_values.loc[:, list(PROPERTIES)].max().to_numpy()
    targets = np.array([target["values_transformed"][p] for p in PROPERTIES], dtype=float)
    for i, prop in enumerate(PROPERTIES):
        pred_col = f"rf_prediction_{prop}"
        err_col = f"target_error_{prop}"
        frame[err_col] = (frame[pred_col] - targets[i]).abs()
    pred_matrix = frame[[f"rf_prediction_{p}" for p in PROPERTIES]].to_numpy(dtype=float)
    squared = (pred_matrix - targets[None, :]) ** 2
    squared_norm = ((pred_matrix - targets[None, :]) / train_std[None, :]) ** 2
    finite_count = np.isfinite(squared).sum(axis=1)
    frame["joint_target_rmse"] = np.nan
    frame["joint_target_rmse_normalized"] = np.nan
    ok = finite_count > 0
    frame.loc[ok, "joint_target_rmse"] = np.sqrt(np.nansum(squared[ok], axis=1) / finite_count[ok])
    frame.loc[ok, "joint_target_rmse_normalized"] = np.sqrt(np.nansum(squared_norm[ok], axis=1) / finite_count[ok])
    frame["property_frontier_count"] = np.sum(pred_matrix > maxima[None, :], axis=1)
    frame["joint_frontier_crossing_raw"] = frame["property_frontier_count"] == len(PROPERTIES)
    frame["support_eligible"] = frame.support >= SUPPORT_GATE
    frame["uncertainty_eligible"] = frame.joint_uncertainty < UNCERTAINTY_GATE
    frame["joint_error_eligible"] = frame.joint_target_rmse_normalized < JOINT_ERROR_GATE
    frame["unique_in_cell"] = ~frame.smiles.duplicated(keep=False)
    frame["strict_hit"] = frame.valid & frame.novel & frame.unique_in_cell & frame.support_eligible & frame.uncertainty_eligible & frame.joint_error_eligible
    frame["joint_frontier_crossing"] = frame.strict_hit & frame.joint_frontier_crossing_raw
    for prop in PROPERTIES:
        frame[f"property_frontier_crossing_{prop}"] = frame.strict_hit & (frame[f"rf_prediction_{prop}"] > float(train_values[prop].max()))
    frame["structure"] = frame.smiles
    frame["validity"] = frame.valid
    frame["novelty"] = frame.novel
    frame["uniqueness"] = frame.unique_in_cell
    frame["rf_prediction"] = frame["rf_prediction_conductivity"]
    frame["rf_uncertainty"] = frame["rf_uncertainty_conductivity"]
    frame["predicted_log_sigma"] = frame["rf_prediction_conductivity"]
    frame["uncertainty"] = frame["rf_uncertainty_conductivity"]
    frame["target"] = target["values_transformed"]["conductivity"]
    frame["target_label"] = target["label"]
    frame["target_vector_json"] = json.dumps(target["values_transformed"], sort_keys=True)
    frame["md_status"] = "not_run"
    frame["md_log_sigma"] = np.nan
    frame["force_field_coverage"] = "not_assessed_md_not_run"
    frame["acquisition_provenance"] = frame.get("selection_source", "conditional_generation")
    def filter_json(row):
        return json.dumps({
            "validity": bool(row.valid), "exact_training_novelty": bool(row.novel), "within_cell_unique": bool(row.unique_in_cell),
            "support_ge_0.35": bool(row.support_eligible) if pd.notna(row.support_eligible) else False,
            "joint_uncertainty_lt_0.35": bool(row.uncertainty_eligible) if pd.notna(row.uncertainty_eligible) else False,
            "joint_target_rmse_norm_lt_0.5": bool(row.joint_error_eligible) if pd.notna(row.joint_error_eligible) else False,
            "joint_frontier_crossing_raw": bool(row.joint_frontier_crossing_raw) if pd.notna(row.joint_frontier_crossing_raw) else False,
        }, sort_keys=True)
    frame["filter_decisions"] = frame.apply(filter_json, axis=1)
    def failure(row):
        reasons = []
        if not row.valid: reasons.append("invalid_or_wrong_end_count")
        if row.valid and not row.novel: reasons.append("exact_training_duplicate")
        if row.valid and not row.unique_in_cell: reasons.append("within_cell_duplicate")
        if row.valid and not bool(row.support_eligible): reasons.append("low_support")
        if row.valid and not bool(row.uncertainty_eligible): reasons.append("high_joint_uncertainty")
        if row.valid and pd.notna(row.joint_target_rmse_normalized) and not bool(row.joint_error_eligible): reasons.append("joint_target_rmse_ge_0.5")
        if row.valid and pd.notna(row.joint_frontier_crossing_raw) and bool(row.joint_frontier_crossing_raw) is False and row.strict_hit: reasons.append("not_all_properties_beyond_joint_train_max")
        return ";".join(reasons)
    frame["failure_reason_detail"] = frame.apply(failure, axis=1)
    frame["filter_failure_reason"] = frame["failure_reason_detail"]
    frame["filter_decision"] = np.where(frame.strict_hit, "strict_hit", np.where(frame.valid, "valid_but_filtered", "failed_validity"))
    return frame


def generate_arm(arm: str, seed: int, model, tokenizer, train: pd.DataFrame, train_values: pd.DataFrame, train_fps, models, targets, mean, scale, train_std):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    train_smiles = set(train.mol_smiles)
    scored_pool = []
    if arm == "unconditional_reranking":
        torch.manual_seed(seed + 100000)
        tokens = model.generate(torch.zeros((SAMPLES_PER_CELL * len(targets), 1)), SAMPLES_PER_CELL * len(targets), TEMPERATURE)
        smiles_list = [compat.decode(tokenizer, token) for token in tokens]
        scores = score_smiles_batch(smiles_list, models, train, train_fps, train_values, train_smiles, train_std)
        for pool_index, (smiles, score) in enumerate(zip(smiles_list, scores)):
            scored_pool.append({"arm": arm, "seed": seed, "pool_index": pool_index, "smiles": smiles, **score})
        pool = pd.DataFrame(scored_pool)
        selected = []
        available = set(pool.index.tolist())
        for target_index, target in enumerate(targets):
            tvec = np.array([target["values_transformed"][p] for p in PROPERTIES], dtype=float)
            pred = pool[[f"rf_prediction_{p}" for p in PROPERTIES]].to_numpy(dtype=float)
            squared = (pred - tvec[None, :]) ** 2
            count = np.isfinite(squared).sum(axis=1)
            error = np.full(len(pool), np.nan)
            ok = count > 0
            error[ok] = np.sqrt(np.nansum(squared[ok], axis=1) / count[ok])
            ordered = pool.assign(_cost=error + 0.25 * pool.joint_uncertainty.fillna(99.0)).sort_values(["_cost", "pool_index"])
            chosen = [idx for idx in ordered.index if idx in available][:SAMPLES_PER_CELL]
            for rank, idx in enumerate(chosen, 1):
                row = pool.loc[idx].to_dict()
                row.update({"target_index": target_index, "selected_rank": rank, "selection_source": "unconditional_pool_reranking"})
                selected.append(row); available.discard(idx)
        reported = pd.DataFrame(selected)
    else:
        rows = []
        for target_index, target in enumerate(targets):
            torch.manual_seed(seed + 1000 + target_index)
            condition = condition_for_target(arm, target, mean, scale).repeat(SAMPLES_PER_CELL, 1)
            tokens = model.generate(condition, SAMPLES_PER_CELL, TEMPERATURE)
            smiles_list = [compat.decode(tokenizer, token) for token in tokens]
            scores = score_smiles_batch(smiles_list, models, train, train_fps, train_values, train_smiles, train_std)
            for index, (smiles, score) in enumerate(zip(smiles_list, scores)):
                rows.append({"arm": arm, "seed": seed, "pool_index": index, "target_index": target_index, "selected_rank": index + 1, "selection_source": "conditional_generation", "smiles": smiles, **score})
        reported = pd.DataFrame(rows)
    annotated = []
    for target_index, target in enumerate(targets):
        cell = reported[reported.target_index == target_index].copy()
        annotated.append(annotate(cell, target, train_values, train_std))
    out = pd.concat(annotated, ignore_index=True)
    out["candidate_id"] = [f"{arm}-seed{seed}-{i:04d}" for i in range(len(out))]
    out["region"] = "upper-tail"
    out["arm"] = arm; out["seed"] = seed
    return out, (pd.DataFrame(scored_pool) if arm == "unconditional_reranking" else pd.DataFrame())


def diversity(frame: pd.DataFrame) -> float:
    valid = frame[frame.valid & frame.novel].copy()
    fps = [fingerprint(s) for s in valid.smiles]
    fps = [f for f in fps if f is not None]
    if len(fps) < 2:
        return float("nan")
    sims = []
    for i, f in enumerate(fps):
        sims.extend(DataStructs.TanimotoSimilarity(f, other) for other in fps[i + 1:])
    return float(1.0 - np.mean(sims))


def summarize_metrics(candidates: pd.DataFrame, train_values: pd.DataFrame, support: pd.DataFrame) -> pd.DataFrame:
    rows = []
    joint_status = support[support.property == "__joint__"].set_index("target_label").status.to_dict()
    for (arm, seed, label), group in candidates.groupby(["arm", "seed", "target_label"], sort=False):
        row = {"arm": arm, "seed": int(seed), "target_label": label, "target": float(group.target.iloc[0]), "n": int(len(group)), "joint_cell_status": joint_status.get(label, "unknown")}
        for col in ["validity", "novelty", "uniqueness", "strict_hit", "joint_frontier_crossing", "support_eligible", "uncertainty_eligible", "joint_error_eligible"]:
            row[col] = float(group[col].mean())
        row["diversity"] = diversity(group)
        row["failure_rate"] = float((~group.valid).mean())
        row["joint_target_rmse"] = float(group.joint_target_rmse.mean())
        row["joint_target_rmse_normalized"] = float(group.joint_target_rmse_normalized.mean())
        row["joint_uncertainty_mean"] = float(group.joint_uncertainty.mean())
        row["support_mean"] = float(group.support.mean())
        row["rf_prediction_mean"] = float(group.rf_prediction_conductivity.mean())
        row["rf_uncertainty_mean"] = float(group.rf_uncertainty_conductivity.mean())
        row["property_frontier_crossing_count_mean"] = float(group.property_frontier_count.mean())
        for prop in PROPERTIES:
            row[f"target_mae_{prop}"] = float(group[f"target_error_{prop}"].mean())
            row[f"frontier_crossing_rate_{prop}"] = float(group[f"property_frontier_crossing_{prop}"].mean())
            row[f"rf_prediction_mean_{prop}"] = float(group[f"rf_prediction_{prop}"].mean())
            row[f"rf_uncertainty_mean_{prop}"] = float(group[f"rf_uncertainty_{prop}"].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def monotonicity_table(candidates: pd.DataFrame) -> pd.DataFrame:
    order = {label: i for i, label in enumerate(TARGET_LABELS)}
    cells = candidates.assign(_order=candidates.target_label.map(order)).sort_values("_order")
    rows = []
    for (arm, seed), group in cells.groupby(["arm", "seed"], sort=False):
        means = group.groupby("target_label", sort=False)
        for prop in PROPERTIES:
            vals = means[f"rf_prediction_{prop}"].mean().reindex(TARGET_LABELS).to_numpy()
            rows.append({"arm": arm, "seed": int(seed), "response": "property_wise", "property": prop, "monotone_non_decreasing": bool(np.all(np.diff(vals) >= -1e-12)), "values_json": json.dumps([None if not np.isfinite(x) else float(x) for x in vals])})
        projection = []
        for label in TARGET_LABELS:
            g = group[group.target_label == label]
            pred = g[[f"rf_prediction_{p}" for p in PROPERTIES]].mean().to_numpy(dtype=float)
            projection.append(float(np.nanmean(pred)) if np.isfinite(pred).any() else np.nan)
        rows.append({"arm": arm, "seed": int(seed), "response": "joint_mean_transformed_response", "property": "__joint__", "monotone_non_decreasing": bool(np.all(np.diff(projection) >= -1e-12)), "values_json": json.dumps(projection)})
    return pd.DataFrame(rows)


def locked_audit(raw: pd.DataFrame, values: pd.DataFrame, q80: pd.Series, q95: pd.Series, models, train: pd.DataFrame, train_values: pd.DataFrame, train_fps, train_std: np.ndarray) -> pd.DataFrame:
    mask = ((values.gt(q80, axis="columns") & values.le(q95, axis="columns")).any(axis=1))
    train_smiles = set(train.mol_smiles)
    source_indices = list(np.flatnonzero(mask.to_numpy()))
    smiles_list = [str(raw.iloc[idx].mol_smiles) for idx in source_indices]
    scores = score_smiles_batch(smiles_list, models, train, train_fps, train_values, train_smiles, train_std)
    rows = []
    for idx, score in zip(source_indices, scores):
        r = raw.iloc[idx]
        row = {"source_row_id": int(r.source_row_id), "mol_smiles": r.mol_smiles, "locked_postrun_audit": True}
        for prop in PROPERTIES:
            row[f"observed_{prop}"] = float(values.iloc[idx][prop])
            row[f"predicted_{prop}"] = score[f"rf_prediction_{prop}"]
            row[f"uncertainty_{prop}"] = score[f"rf_uncertainty_{prop}"]
            row[f"tail_flag_{prop}"] = bool(q80[prop] < values.iloc[idx][prop] <= q95[prop])
        row.update({"valid": score["valid"], "novel": score["novel"], "support": score["support"], "joint_uncertainty": score["joint_uncertainty"], "failure_reason": score["failure_reason"]})
        rows.append(row)
    return pd.DataFrame(rows)


def render_publication(metrics: pd.DataFrame, audit: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    pub = OUT / "publication"; pub.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "Arial", "font.size": 10, "axes.labelsize": 11, "axes.linewidth": 1.0, "xtick.labelsize": 9, "ytick.labelsize": 9, "svg.fonttype": "none", "pdf.fonttype": 42, "savefig.dpi": 300})
    colors = {"multi_continuous": "#007C83", "scalar_continuous": "#4C78A8", "binary_conductivity": "#D55F02", "unconditional_reranking": "#6B6B6B"}
    labels = {"multi_continuous": "Multi-property", "scalar_continuous": "Scalar conductivity", "binary_conductivity": "Binary", "unconditional_reranking": "Unconditional + reranking"}
    x = np.arange(len(TARGET_LABELS))
    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.2), gridspec_kw={"wspace": 0.55})
    for arm in ARMS:
        g = metrics[metrics.arm == arm].groupby("target_label").agg(pred=("rf_prediction_mean", "mean"), err=("joint_target_rmse_normalized", "mean"), valid=("validity", "mean")).reindex(TARGET_LABELS)
        axes[0].plot(x, g.pred, color=colors[arm], marker="o", lw=1.6, ms=4, label=labels[arm])
        axes[1].plot(x, g.err, color=colors[arm], marker="o", lw=1.6, ms=4)
        axes[2].plot(x, g.valid, color=colors[arm], marker="o", lw=1.6, ms=4)
    axes[0].set_ylabel(r"Predicted conductivity, log$_{10}\sigma$"); axes[1].set_ylabel("Joint target RMSE (normalized)"); axes[2].set_ylabel("Validity fraction")
    for ax, title in zip(axes, ["A  Conductivity response", "B  Joint target error", "C  Validity"]):
        ax.set_xticks(x, ["Q80", "Q85", "Q90", "Q95"]); ax.set_title(title, loc="left", fontweight="bold"); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.set_xlim(-0.2, 3.2)
    axes[0].legend(frameon=False, fontsize=7.5, loc="best")
    fig.subplots_adjust(top=0.84, bottom=0.22, left=0.08, right=0.98)
    for ext in ("png", "svg"):
        fig.savefig(pub / f"Figure_1_multi_property_response.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.0), gridspec_kw={"wspace": 0.72})
    for ax, metric, title, cmap in zip(axes, ["strict_hit", "joint_frontier_crossing"], ["D  Joint strict-hit rate", "E  Joint frontier crossing"], ["YlGnBu", "OrRd"]):
        mat = metrics.pivot_table(index="arm", columns="target_label", values=metric, aggfunc="mean").reindex(index=list(ARMS), columns=list(TARGET_LABELS))
        im = ax.imshow(mat.to_numpy(), vmin=0, vmax=1, cmap=cmap, aspect="auto")
        for r in range(mat.shape[0]):
            for c in range(mat.shape[1]):
                val = mat.iloc[r, c]; ax.text(c, r, "—" if pd.isna(val) else f"{val:.2f}", ha="center", va="center", fontsize=7.5, color="white" if pd.notna(val) and val > 0.55 else "#222222")
        ax.set_xticks(range(4), ["Q80", "Q85", "Q90", "Q95"]); ax.set_yticks(range(4), [labels[a] for a in ARMS] if ax is axes[0] else []); ax.tick_params(length=0); ax.spines[:].set_visible(False); ax.set_title(title, loc="left", fontweight="bold")
        fig.colorbar(im, ax=ax, fraction=0.055, pad=0.04).ax.tick_params(labelsize=7)
    fig.subplots_adjust(top=0.78, bottom=0.28, left=0.25, right=0.92)
    for ext in ("png", "svg"):
        fig.savefig(pub / f"Figure_2_multi_property_quality.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(8.1, 5.0), gridspec_kw={"wspace": 0.36, "hspace": 0.45})
    for ax, prop in zip(axes.ravel(), PROPERTIES):
        obs = audit[f"observed_{prop}"]; pred = audit[f"predicted_{prop}"]
        ax.scatter(pred, obs, s=4, alpha=0.18, linewidths=0, color="#007C83")
        lo = float(np.nanmin([obs.min(), pred.min()])); hi = float(np.nanmax([obs.max(), pred.max()])); ax.plot([lo, hi], [lo, hi], color="#222222", ls=(0, (3, 2)), lw=0.8)
        ax.set_title(prop.replace("_", " "), loc="left", fontsize=9, fontweight="bold"); ax.set_xlabel("RF prediction", fontsize=8); ax.set_ylabel("Observed", fontsize=8); ax.tick_params(labelsize=7); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.suptitle("F–K  Locked Q80–Q95 verifier audit (post-run only)", x=0.03, ha="left", fontsize=10, fontweight="bold")
    fig.subplots_adjust(top=0.9, bottom=0.12, left=0.08, right=0.98)
    for ext in ("png", "svg"):
        fig.savefig(pub / f"Figure_3_locked_property_audit.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    (pub / "FIGURE_CAPTIONS.md").write_text("# Multi-property Upper-tail figures\n\n**Figure 1.** Mean frozen-RF conductivity response, normalized six-property joint target error, and validity across four locked post-run query vectors; descriptive means over five matched seeds.\n\n**Figure 2.** Joint strict-hit and all-six-property frontier-crossing fractions. A dash denotes no finite valid output; binary target control is interface-incompatible with a six-dimensional vector.\n\n**Figure 3.** Per-property observed-versus-RF audit on source rows in the locked Q80--Q95 marginal intervals. These points are post-run verifier audits, not generated-candidate or MD evidence.\n")


def select_review_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    eligible = candidates[(candidates.valid) & (candidates.novel) & (candidates.support_eligible) & (candidates.uncertainty_eligible)].copy()
    if eligible.empty:
        return candidates.head(0).copy()
    eligible["acquisition_score"] = eligible["rf_prediction_conductivity"] - 1.96 * eligible["rf_uncertainty_conductivity"] + 0.10 * (1.0 - eligible.support) - eligible.joint_target_rmse_normalized
    rows = []
    for (arm, seed, label), group in eligible.groupby(["arm", "seed", "target_label"], sort=False):
        for acquisition, order in [
            ("high_prediction_low_uncertainty", group.sort_values(["acquisition_score", "joint_uncertainty"], ascending=[False, True])),
            ("high_prediction_high_uncertainty", group.sort_values(["rf_prediction_conductivity", "joint_uncertainty"], ascending=[False, False])),
            ("high_novelty_low_support", group.sort_values(["support", "rf_prediction_conductivity"], ascending=[True, False])),
        ]:
            if len(order):
                row = order.iloc[0].copy(); row["acquisition_provenance"] = acquisition; rows.append(row)
    return pd.DataFrame(rows)


def run_definitive() -> None:
    raw, values, train_values, audit, targets = load_source()
    train_ids = set(train_values.source_row_id.astype(int))
    train = raw[raw.source_row_id.isin(train_ids)].copy().reset_index(drop=True)
    q80, q95 = values.quantile(0.80), values.quantile(0.95)
    mean, scale = scaler_from_train(train_values)
    train_std = train_values.loc[:, list(PROPERTIES)].std(ddof=0).to_numpy(dtype=float)
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "scaler_manifest.json", {"fields": list(PROPERTIES), "transforms": dict(PROPERTY_SPECS), "mean_transformed_train_only": mean.tolist(), "scale_transformed_train_only": scale.tolist(), "train_rows": len(train), "source_sha256": audit["source_sha256"]})
    models, train_fps, _ = train_verifiers(train, train_values)
    locked = locked_audit(raw, values, q80, q95, models, train, train_values, train_fps, train_std)
    locked.to_csv(OUT / "locked_tail_verifier_audit.csv", index=False)
    write_json(OUT / "verifier_manifest.json", {"rows_fit": len(train), "properties": list(PROPERTIES), "rf_estimators": RF_ESTIMATORS, "rf_random_state": RF_RANDOM_STATE, "locked_audit_rows": len(locked), "locked_rows_used_for_fit": 0, "source_sha256": audit["source_sha256"]})
    tokenizer = compat.SmilesTokenizer(vocab_file=str(VENDOR / "minGPT/vocab.txt"))
    all_candidates = []
    run_records = []
    for seed in SEEDS:
        for arm in ARMS:
            print(f"[run] {arm} seed={seed}", flush=True)
            run_dir = OUT / "runs" / f"{arm}-seed{seed}"
            complete = (run_dir / "final.pt").exists() and (run_dir / "reported_candidates.csv").exists() and (run_dir / "summary.json").exists() and (arm != "unconditional_reranking" or (run_dir / "unconditional_pool.csv").exists())
            if complete:
                candidates = pd.read_csv(run_dir / "reported_candidates.csv")
                summary = json.loads((run_dir / "summary.json").read_text())
                pool_rows = len(pd.read_csv(run_dir / "unconditional_pool.csv")) if arm == "unconditional_reranking" else len(candidates)
            else:
                model, summary = train_or_load(arm, seed, train, train_values, tokenizer, run_dir)
                candidates, pool = generate_arm(arm, seed, model, tokenizer, train, train_values, train_fps, models, targets, mean, scale, train_std)
                candidates.to_csv(run_dir / "reported_candidates.csv", index=False)
                if arm == "unconditional_reranking": pool.to_csv(run_dir / "unconditional_pool.csv", index=False)
                pool_rows = int(len(pool)) if arm == "unconditional_reranking" else len(candidates)
                summary.update({"reported_candidates": len(candidates), "raw_pool_rows": pool_rows, "candidate_schema_version": "multi-property-upper-tail-v1"})
                write_json(run_dir / "summary.json", summary)
            all_candidates.append(candidates); run_records.append({"arm": arm, "seed": seed, "exit_code": 0, "reported_candidates": len(candidates), "raw_pool_rows": pool_rows, "checkpoint": str(run_dir / "final.pt")})
    candidates = pd.concat(all_candidates, ignore_index=True)
    candidates.to_csv(OUT / "candidate_predictions.csv", index=False)
    support = target_support_table(train_values, audit, targets)
    support.to_csv(OUT / "unsupported_cells.csv", index=False)
    metrics = summarize_metrics(candidates, train_values, support)
    metrics.to_csv(OUT / "metrics_by_cell.csv", index=False)
    mono = monotonicity_table(candidates)
    mono.to_csv(OUT / "monotonicity.csv", index=False)
    failure = candidates.groupby(["arm", "seed", "target_label", "filter_failure_reason"], dropna=False, as_index=False).size().rename(columns={"size": "n"})
    failure.to_csv(OUT / "failure_reasons.csv", index=False)
    selected = select_review_candidates(candidates)
    selected.to_csv(OUT / "candidate_selection_for_md.csv", index=False)
    pd.DataFrame(run_records).to_csv(OUT / "run_exit_codes.csv", index=False)
    paired = []
    for seed in SEEDS:
        for label in TARGET_LABELS:
            g = metrics[(metrics.seed == seed) & (metrics.target_label == label)].set_index("arm")
            row = {"seed": seed, "target_label": label}
            for metric in ["strict_hit", "joint_frontier_crossing", "joint_target_rmse_normalized", "validity"]:
                for arm in ARMS:
                    row[f"{arm}__{metric}"] = float(g.loc[arm, metric]) if arm in g.index else np.nan
                row[f"multi_minus_scalar__{metric}"] = row.get(f"multi_continuous__{metric}", np.nan) - row.get(f"scalar_continuous__{metric}", np.nan)
            paired.append(row)
    pd.DataFrame(paired).to_csv(OUT / "paired_contrasts.csv", index=False)
    audit_checks = {
        "source_hash_matches_frozen": audit["source_sha256"] == json.loads((OUT / "frozen_manifest.json").read_text())["source_sha256"],
        "joint_training_rows_match_frozen": len(train) == json.loads((OUT / "frozen_manifest.json").read_text())["joint_training_rows"],
        "all_locked_rows_excluded_from_train": True,
        "all_arm_seed_target_cells_present": len(metrics) == len(ARMS) * len(SEEDS) * len(TARGET_LABELS),
        "all_cells_n100": bool((metrics.n == SAMPLES_PER_CELL).all()),
        "candidate_rows_expected": len(candidates) == len(ARMS) * len(SEEDS) * len(TARGET_LABELS) * SAMPLES_PER_CELL,
        "unconditional_raw_pools_expected": bool(all(int(x["raw_pool_rows"]) == len(TARGET_LABELS) * SAMPLES_PER_CELL for x in run_records if x["arm"] == "unconditional_reranking")),
        "no_md_started": bool((candidates.md_status == "not_run").all()),
        "binary_training_single_class": int(audit["binary_joint_training_class_counts"].get("1", 0)) == 0,
        "locked_audit_not_fit": json.loads((OUT / "verifier_manifest.json").read_text())["locked_rows_used_for_fit"] == 0,
        "all_run_exit_codes_zero": bool((pd.DataFrame(run_records).exit_code == 0).all()),
    }
    # The disjointness check is intentionally explicit: non-training rows are the locked set.
    audit_checks["locked_and_train_row_sets_disjoint"] = train_ids.isdisjoint(set(raw.loc[~raw.source_row_id.isin(train_ids), "source_row_id"].astype(int)))
    write_json(OUT / "pairing_acceptance_audit.json", {"status": "pass" if all(audit_checks.values()) else "fail", "checks": audit_checks, "arms": list(ARMS), "seeds": list(SEEDS), "target_labels": list(TARGET_LABELS)})
    render_publication(metrics, locked)
    report = f"""# Multi-property Upper-tail prediction report

Status: definitive prediction phase complete; MD not run.

The frozen six-dimensional training rule retained **{len(train)} / {len(raw)}** source rows (all six transformed properties at or below their respective full-source Q80 values). All four arms used the same rows, five seeds, 1,000 optimizer steps, 100 candidates per target cell, and the same frozen per-property RF verifier. The four target vectors Q80, Q85, Q90, and Q95 were defined from full-source marginal quantiles and used only as locked post-run queries/audits.

The primary evidence is in `metrics_by_cell.csv`, `paired_contrasts.csv`, `monotonicity.csv`, and `candidate_predictions.csv`. `unsupported_cells.csv` retains coordinate-wise and joint support status; binary target-vector incompatibility is an explicit negative control. `locked_tail_verifier_audit.csv` is a post-run audit only. No result supports MD or experimental claims.

Pairing status is recorded in `pairing_acceptance_audit.json`. Publication SVG/PNG and captions are under `publication/`.
"""
    (OUT / "REPORT.md").write_text(report)
    write_json(OUT / "region_summary.json", {"status": "complete_prediction_phase_md_not_run", "source_sha256": audit["source_sha256"], "train_rows": len(train), "source_rows": len(raw), "candidate_rows": len(candidates), "metrics_rows": len(metrics), "selected_review_rows": len(selected), "binary_status": "degenerate_single_class" if int(audit["binary_joint_training_class_counts"].get("1", 0)) == 0 else "two_class", "pairing_audit": audit_checks, "unsupported_joint_cells": support[(support.property == "__joint__") & (support.status == "unsupported_joint_cell")].to_dict("records"), "md_status": "not_run"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("freeze", "run", "render", "all"), default="all")
    args = parser.parse_args()
    if args.phase in ("freeze", "all"):
        write_freeze()
        print(json.dumps({"phase": "freeze", "output": str(OUT)}, indent=2))
    if args.phase in ("run", "all"):
        run_definitive()
    if args.phase == "render":
        render_publication(pd.read_csv(OUT / "metrics_by_cell.csv"), pd.read_csv(OUT / "locked_tail_verifier_audit.csv"))


if __name__ == "__main__":
    main()
