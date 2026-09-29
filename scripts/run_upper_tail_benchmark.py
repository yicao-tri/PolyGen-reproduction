#!/usr/bin/env python3
"""Run the frozen prediction-only upper-tail PolyGen benchmark.

The benchmark deliberately keeps the original C1 binary threshold (-4.0).
Under the Q80 training boundary that threshold becomes single-class; this is
recorded as a protocol fact rather than silently changing the estimand.  An
unconditional model is trained with a constant zero condition and is evaluated
by frozen-verifier reranking from a matched raw candidate budget.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
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

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "vendor/PolyGen-1.0.0"
OUT = ROOT / "results/upper-tail"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
SEEDS = (17, 42, 202, 303, 907)
ARMS = ("continuous", "binary", "unconditional_reranking")
QUANTILES = (0.80, 0.85, 0.90, 0.95)
SAMPLES_PER_CELL = 100
BINARY_CUTOFF = -4.0
STEPS = 1000
TEMPERATURE = 1.0
TOP_K = 40
BLOCK = 64
PREFIX = 5
SPLIT_SEED = 20260923

RDLogger.DisableLog("rdApp.warning")
RDLogger.DisableLog("rdApp.error")
sys.path.insert(0, str(REPO))
from deepchem.feat.smiles_tokenizer import SmilesTokenizer  # noqa: E402
from minGPT.model.mingpt.model import GPT  # noqa: E402
from torch import nn  # noqa: E402
from torch.nn import functional as F  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fp(smiles: str):
    molecule = Chem.MolFromSmiles(smiles.replace("[Cu]", "[*]").replace("[Au]", "[*]"))
    return None if molecule is None else AllChem.GetMorganFingerprintAsBitVect(molecule, 2, nBits=2048)


def fp_array(fingerprint):
    values = np.zeros(2048, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fingerprint, values)
    return values


class SeqDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, tokenizer: SmilesTokenizer, arm: str):
        condition = frame.log_sigma.to_numpy() if arm != "unconditional" else np.zeros(len(frame))
        self.cond = torch.tensor(condition, dtype=torch.float32)
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
        return self.seq[index, :-1], self.seq[index, 1:], self.cond[index]


class SoftConditionGPT(nn.Module):
    """C1 architecture with an unconditional constant-zero condition option."""

    def __init__(self, config, arm: str, mean: float, std: float):
        super().__init__()
        self.gpt = GPT(config)
        self.arm = arm
        self.mean = mean
        self.std = std
        n = config.n_embd
        self.cont = nn.Sequential(nn.Linear(1, n), nn.Tanh(), nn.Linear(n, n))
        self.binary = nn.Embedding(2, n)

    def configure_optimizers(self, learning_rate: float):
        return torch.optim.AdamW(self.parameters(), lr=learning_rate, betas=(0.9, 0.95), weight_decay=0.1)

    def forward(self, idx, condition, targets=None):
        _, tokens = idx.shape
        positions = torch.arange(tokens, device=idx.device).unsqueeze(0)
        token_embeddings = self.gpt.transformer.wte(idx)
        if self.arm == "unconditional":
            normalized = torch.zeros_like(condition).view(-1, 1)
            embedding = self.cont(normalized)
        else:
            normalized = ((condition - self.mean) / self.std).view(-1, 1)
            embedding = self.cont(normalized) if self.arm == "continuous" else self.binary((condition >= BINARY_CUTOFF).long())
        token_embeddings = token_embeddings.clone()
        token_embeddings[:, :PREFIX, :] += embedding[:, None, :]
        hidden = self.gpt.transformer.drop(token_embeddings + self.gpt.transformer.wpe(positions))
        for block in self.gpt.transformer.h:
            hidden = block(hidden)
        logits = self.gpt.lm_head(self.gpt.transformer.ln_f(hidden))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-1)
        return logits, loss

    @torch.no_grad()
    def generate(self, condition, count: int, temperature: float = 1.0):
        index = torch.ones((count, PREFIX), dtype=torch.long)
        for _ in range(BLOCK - PREFIX):
            logits, _ = self(index, condition)
            logits = logits[:, -1, :] / temperature
            values, _ = torch.topk(logits, TOP_K)
            logits[logits < values[:, [-1]]] = -float("inf")
            index = torch.cat([index, torch.multinomial(F.softmax(logits, dim=-1), 1)], 1)
        return index[:, PREFIX:]


def decode(tokenizer: SmilesTokenizer, row) -> str:
    text = tokenizer.decode(row).replace(" ", "")
    if "[CLS]" not in text or "[SEP]" not in text:
        return ""
    return text.split("[CLS]", 1)[1].split("[SEP]", 1)[0]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    source = pd.read_csv(SOURCE)[["mol_smiles", "conductivity"]].copy()
    source["log_sigma"] = np.log10(source.conductivity)
    source["source_row_id"] = np.arange(len(source), dtype=int)
    full_targets = {str(q): float(source.log_sigma.quantile(q)) for q in QUANTILES}
    q80 = full_targets["0.8"]
    train = source[source.log_sigma <= q80].copy().reset_index(drop=True)
    tail = source[(source.log_sigma > q80) & (source.log_sigma <= full_targets["0.95"])].copy().reset_index(drop=True)
    source["region"] = np.where(source.log_sigma <= q80, "generator_train", "locked_tail")
    audit = {
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "source_rows": int(len(source)),
        "source_unique_smiles": int(source.mol_smiles.nunique()),
        "full_source_quantiles": full_targets,
        "training_rule": "log10(conductivity) <= full-source Q80, inclusive",
        "training_rows": int(len(train)),
        "training_unique_smiles": int(train.mol_smiles.nunique()),
        "training_max_log10_sigma": float(train.log_sigma.max()),
        "locked_tail_q80_q95_rows": int(len(tail)),
        "locked_tail_unique_smiles": int(tail.mol_smiles.nunique()),
        "train_tail_exact_smiles_overlap": int(len(set(train.mol_smiles) & set(tail.mol_smiles))),
        "binary_cutoff_log10_sigma": BINARY_CUTOFF,
        "binary_training_class_counts": {
            str(k): int(v) for k, v in train.assign(binary_label=(train.log_sigma >= BINARY_CUTOFF).astype(int)).binary_label.value_counts().sort_index().items()
        },
        "binary_status": "degenerate_single_class" if train.log_sigma.max() < BINARY_CUTOFF else "two_class",
        "alternative_binary_cutoff": float(train.log_sigma.quantile(0.5)),
    }
    return train, tail, audit


def fit_verifier(train: pd.DataFrame):
    fingerprints = [fp(smiles) for smiles in train.mol_smiles]
    features = np.stack([fp_array(value) for value in fingerprints])
    model = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features="sqrt",
        n_jobs=-1,
        random_state=SPLIT_SEED,
    )
    model.fit(features, train.log_sigma.to_numpy())
    return model, fingerprints


def score_smiles(smiles: str, model, train: pd.DataFrame, train_fps, train_smiles: set[str]):
    fingerprint = fp(smiles) if smiles else None
    valid = bool(fingerprint is not None and smiles.count("[Cu]") == 1 and smiles.count("[Au]") == 1)
    if not valid:
        return {
            "valid": False, "novel": False, "predicted_log_sigma": np.nan,
            "uncertainty": np.nan, "support": np.nan, "failure_reason": "invalid_or_wrong_end_count",
        }
    values = np.asarray([tree.predict(fp_array(fingerprint).reshape(1, -1))[0] for tree in model.estimators_])
    support = max(DataStructs.TanimotoSimilarity(fingerprint, other) for other in train_fps)
    novel = smiles not in train_smiles
    return {
        "valid": True, "novel": novel, "predicted_log_sigma": float(values.mean()),
        "uncertainty": float(values.std(ddof=1)), "support": float(support),
        "failure_reason": "" if novel else "exact_training_duplicate",
    }


def train_and_generate(arm, seed, train, tokenizer, verifier, train_fps, targets, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    cfg = GPT.get_default_config()
    cfg.model_type = "gpt-nano"
    cfg.vocab_size = tokenizer.vocab_size
    cfg.block_size = BLOCK
    model = SoftConditionGPT(cfg, arm, float(train.log_sigma.mean()), float(train.log_sigma.std()))
    optimizer = model.configure_optimizers(5e-4)
    loader = iter(DataLoader(
        SeqDataset(train, tokenizer, arm),
        batch_size=64,
        sampler=torch.utils.data.RandomSampler(train, replacement=True, num_samples=10**9),
    ))
    losses = []
    started = time.time()
    model.train()
    for _ in range(STEPS):
        x, y, condition = next(loader)
        _, loss = model(x, condition, y)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss))
    model.eval()
    train_smiles = set(train.mol_smiles)
    raw = []
    if arm == "unconditional_reranking":
        torch.manual_seed(seed + 100000)
        count = SAMPLES_PER_CELL * len(targets)
        condition = torch.zeros(count)
        tokens = model.generate(condition, count, TEMPERATURE)
        for index, token in enumerate(tokens):
            smiles = decode(tokenizer, token)
            score = score_smiles(smiles, verifier, train, train_fps, train_smiles)
            raw.append({"arm": arm, "seed": seed, "pool_index": index, "smiles": smiles, **score})
        raw_frame = pd.DataFrame(raw)
        selected = []
        available = set(raw_frame.index.tolist())
        for target_index, target in enumerate(targets):
            costs = raw_frame.predicted_log_sigma.sub(target["value"]).abs() + 0.25 * raw_frame.uncertainty.fillna(99.0)
            ordered = raw_frame.assign(_cost=costs).sort_values(["_cost", "pool_index"])
            chosen = [idx for idx in ordered.index if idx in available][:SAMPLES_PER_CELL]
            if len(chosen) < SAMPLES_PER_CELL:
                chosen = [idx for idx in ordered.index if idx not in chosen][:SAMPLES_PER_CELL]
            for rank, idx in enumerate(chosen, 1):
                row = raw_frame.loc[idx].to_dict()
                row.update({"target_index": target_index, "target": target["value"], "target_label": targets[target_index]["label"], "selected_rank": rank, "selection_source": "unconditional_pool_reranking"})
                selected.append(row)
                available.discard(idx)
        reported = pd.DataFrame(selected)
        raw_frame.to_csv(output_dir / "unconditional_pool.csv", index=False)
    else:
        reported_rows = []
        for target_index, target in enumerate(targets):
            torch.manual_seed(seed + 1000 + target_index)
            condition_value = 0.0 if arm == "unconditional" else target["value"]
            condition = torch.full((SAMPLES_PER_CELL,), condition_value)
            tokens = model.generate(condition, SAMPLES_PER_CELL, TEMPERATURE)
            for index, token in enumerate(tokens):
                smiles = decode(tokenizer, token)
                score = score_smiles(smiles, verifier, train, train_fps, train_smiles)
                reported_rows.append({
                    "arm": arm, "seed": seed, "pool_index": index,
                    "target_index": target_index, "target": target["value"],
                    "target_label": target["label"], "selected_rank": index + 1,
                    "selection_source": "conditional_generation", "smiles": smiles, **score,
                })
        reported = pd.DataFrame(reported_rows)
    reported["target_error"] = (reported.predicted_log_sigma - reported.target).abs()
    reported["support_eligible"] = reported.support >= 0.35
    reported["uncertainty_eligible"] = reported.uncertainty < 0.35
    reported["strict_hit"] = (
        reported.valid & reported.novel & reported.support_eligible & reported.uncertainty_eligible & (reported.target_error < 0.5)
    )
    reported["upper_tail_predicted_hit"] = reported.valid & reported.novel & reported.support_eligible & reported.uncertainty_eligible & (reported.predicted_log_sigma > train.log_sigma.max())
    reported["md_status"] = "not_run"
    reported["md_log_sigma"] = np.nan
    reported["residual_md_minus_rf"] = np.nan
    reported.to_csv(output_dir / "reported_candidates.csv", index=False)
    torch.save(model.state_dict(), output_dir / "final.pt")
    summary = {
        "arm": arm, "seed": seed, "steps": STEPS, "temperature": TEMPERATURE,
        "raw_generation_budget": len(raw) if arm == "unconditional_reranking" else len(reported),
        "reported_candidates": len(reported), "first_loss": losses[0], "last_loss": losses[-1],
        "elapsed_seconds": time.time() - started, "checkpoint_sha256": sha256(output_dir / "final.pt"),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return reported, summary


def diversity_score(frame: pd.DataFrame) -> float:
    valid = frame[frame.valid & frame.novel].copy()
    fingerprints = [fp(smiles) for smiles in valid.smiles]
    fingerprints = [value for value in fingerprints if value is not None]
    if len(fingerprints) < 2:
        return float("nan")
    similarities = []
    for i, value in enumerate(fingerprints):
        similarities.extend(DataStructs.TanimotoSimilarity(value, other) for other in fingerprints[i + 1 :])
    return float(1.0 - np.mean(similarities))


def summarize(reported: pd.DataFrame, train: pd.DataFrame, targets):
    rows = []
    for (arm, seed, target_label), group in reported.groupby(["arm", "seed", "target_label"], sort=False):
        rows.append({
            "arm": arm, "seed": int(seed), "target_label": target_label,
            "target": float(group.target.iloc[0]), "n": int(len(group)),
            "validity": float(group.valid.mean()), "novelty": float(group.novel.mean()),
            "uniqueness": float(group.loc[group.valid, "smiles"].nunique() / max(1, len(group))),
            "diversity": diversity_score(group),
            "failure_rate": float(1.0 - group.valid.mean()),
            "target_mae": float(group.target_error.mean()),
            "strict_hit_rate": float(group.strict_hit.mean()),
            "upper_tail_predicted_hit_rate": float(group.upper_tail_predicted_hit.mean()),
            "rf_prediction_mean": float(group.predicted_log_sigma.mean()),
            "rf_prediction_median": float(group.predicted_log_sigma.median()),
            "rf_uncertainty_mean": float(group.uncertainty.mean()),
            "support_mean": float(group.support.mean()),
            "support_eligible_rate": float(group.support_eligible.mean()),
            "failure_reasons": json.dumps(group.loc[~group.valid, "failure_reason"].value_counts().to_dict(), sort_keys=True),
            "md_status": "not_run",
        })
    metrics = pd.DataFrame(rows)
    monotonicity = []
    for (arm, seed), group in metrics.groupby(["arm", "seed"], sort=False):
        ordered = group.sort_values("target")
        monotonicity.append({
            "arm": arm, "seed": int(seed),
            "mean_prediction_monotonic_increasing": bool(ordered.rf_prediction_mean.is_monotonic_increasing),
            "mean_prediction_spearman": float(ordered[["target", "rf_prediction_mean"]].corr(method="spearman").iloc[0, 1]),
        })
    return metrics, pd.DataFrame(monotonicity)


def tail_audit(tail: pd.DataFrame, train: pd.DataFrame, verifier, train_fps) -> pd.DataFrame:
    train_smiles = set(train.mol_smiles)
    rows = []
    q80, q85, q90, q95 = [float(tail.log_sigma.quantile(q)) for q in (0, 1 / 3, 2 / 3, 1)]
    del q80, q85, q90, q95
    for _, record in tail.iterrows():
        score = score_smiles(record.mol_smiles, verifier, train, train_fps, train_smiles)
        rows.append({
            "source_row_id": int(record.source_row_id), "mol_smiles": record.mol_smiles,
            "observed_log_sigma": float(record.log_sigma), **score,
            "rf_residual_observed_minus_predicted": float(record.log_sigma - score["predicted_log_sigma"]) if score["valid"] else np.nan,
            "q80_q95_locked": True, "md_status": "not_run",
        })
    result = pd.DataFrame(rows)
    bins = [-np.inf] + [float(tail.log_sigma.quantile(q)) for q in (1 / 3, 2 / 3)] + [np.inf]
    result["tail_bin"] = pd.cut(result.observed_log_sigma, bins=bins, labels=["Q80-Q85", "Q85-Q90", "Q90-Q95"], include_lowest=True)
    return result


def select_md_candidates(reported: pd.DataFrame, per_cell: int = 6) -> pd.DataFrame:
    rows = []
    for (arm, seed, target_label), group in reported.groupby(["arm", "seed", "target_label"], sort=False):
        eligible = group[group.valid & group.novel].copy()
        if eligible.empty:
            continue
        eligible["acquisition_score"] = eligible.predicted_log_sigma - 1.96 * eligible.uncertainty + 0.25 * (1.0 - eligible.support)
        used = set()
        strata = [
            ("high_prediction_low_uncertainty", eligible.sort_values(["predicted_log_sigma", "uncertainty"], ascending=[False, True])),
            ("high_prediction_high_uncertainty", eligible.sort_values(["predicted_log_sigma", "uncertainty"], ascending=[False, False])),
            ("high_novelty_low_support", eligible.sort_values(["support", "predicted_log_sigma"], ascending=[True, False])),
        ]
        for reason, ordered in strata:
            for index in ordered.index:
                if index in used:
                    continue
                row = eligible.loc[index].to_dict()
                row["selection_reason"] = reason
                row["candidate_id"] = f"{arm}|seed{seed}|{target_label}|pool{int(row['pool_index'])}"
                rows.append(row)
                used.add(index)
                if sum(1 for x in rows if x["arm"] == arm and x["seed"] == seed and x["target_label"] == target_label) >= per_cell:
                    break
            if sum(1 for x in rows if x["arm"] == arm and x["seed"] == seed and x["target_label"] == target_label) >= per_cell:
                break
    return pd.DataFrame(rows)


def main():
    train, tail, audit = load_data()
    OUT.mkdir(parents=True, exist_ok=True)
    full = pd.read_csv(SOURCE)
    full["log_sigma"] = np.log10(full.conductivity)
    q80 = float(full.log_sigma.quantile(0.80))
    targets = [
        {"label": "Q80_boundary_actual_train_max", "quantile": 0.80, "value": float(train.log_sigma.max()), "note": "actual inclusive training maximum; nominal Q80 is recorded separately"},
        {"label": "Q85", "quantile": 0.85, "value": float(full.log_sigma.quantile(0.85)), "note": "full-source target grid only; locked rows never used for fitting"},
        {"label": "Q90", "quantile": 0.90, "value": float(full.log_sigma.quantile(0.90)), "note": "full-source target grid only; locked rows never used for fitting"},
        {"label": "Q95", "quantile": 0.95, "value": float(full.log_sigma.quantile(0.95)), "note": "full-source target grid only; locked rows never used for fitting"},
    ]
    audit["nominal_q80"] = q80
    audit["actual_train_boundary_minus_nominal_q80"] = float(train.log_sigma.max() - q80)
    audit["target_grid"] = targets
    audit["protocol"] = {
        "train_only_rule": "all generator and RF fitting rows satisfy log10 conductivity <= nominal Q80",
        "locked_holdout_rule": "rows above nominal Q80 are excluded from fitting, tuning, filtering and selection until post-run audit",
        "matched_seeds": list(SEEDS), "arms": list(ARMS), "steps": STEPS,
        "temperature": TEMPERATURE, "samples_per_target_cell": SAMPLES_PER_CELL,
        "unconditional_raw_pool_per_seed": SAMPLES_PER_CELL * len(targets),
        "strict_hit_definition": "valid, exact-training-novel, nearest-train Tanimoto >= 0.35, RF tree SD < 0.35, abs RF target error < 0.5",
        "upper_tail_hit_definition": "valid, exact-training-novel, support/uncertainty gated, RF prediction > actual training maximum",
        "md": "not run by contract",
    }
    audit["unconditional_reranking_status"] = "executed_with_matched_400_candidate_pool_and_disjoint_100-per-target_assignment"
    audit["alternative_binary_sensitivity"] = {
        "cutoff": float(audit["alternative_binary_cutoff"]),
        "definition": "training-median binary cutoff, balanced only within the truncated training distribution",
        "status": "not_executed; would be a different binary estimand and is retained as the prespecified fallback",
    }
    (OUT / "frozen_manifest.json").write_text(json.dumps(audit, indent=2) + "\n")
    train.assign(split="generator_and_verifier_train_leq_nominal_Q80").to_csv(OUT / "train_rows.csv", index=False)
    tail.assign(split="locked_evaluation_tail_Q80_to_Q95").to_csv(OUT / "locked_tail_rows.csv", index=False)
    (OUT / "run_contract.json").write_text(json.dumps({"script": str(Path(__file__).resolve()), "script_sha256": sha256(Path(__file__)), "source_sha256": sha256(SOURCE), "platform": platform.platform(), "python": platform.python_version(), "torch": torch.__version__, "steps": STEPS, "seeds": list(SEEDS), "arms": list(ARMS), "targets": targets, "binary_cutoff": BINARY_CUTOFF}, indent=2) + "\n")
    verifier, train_fps = fit_verifier(train)
    tail_predictions = tail_audit(tail, train, verifier, train_fps)
    tail_predictions.to_csv(OUT / "locked_tail_verifier_audit.csv", index=False)
    verifier_metrics = {
        "training_rows": int(len(train)), "training_max_log_sigma": float(train.log_sigma.max()),
        "locked_tail_rows_audited": int(len(tail_predictions)),
        "locked_tail_rf_mae": float((tail_predictions.observed_log_sigma - tail_predictions.predicted_log_sigma).abs().mean()),
        "locked_tail_rf_rmse": float(np.sqrt(np.mean((tail_predictions.observed_log_sigma - tail_predictions.predicted_log_sigma) ** 2))),
        "locked_tail_rf_residual_mean": float(tail_predictions.rf_residual_observed_minus_predicted.mean()),
        "locked_tail_rf_residual_sd": float(tail_predictions.rf_residual_observed_minus_predicted.std(ddof=1)),
    }
    (OUT / "verifier_metrics.json").write_text(json.dumps(verifier_metrics, indent=2) + "\n")
    tokenizer = SmilesTokenizer(vocab_file=str(REPO / "minGPT/vocab.txt"))
    all_reported = []
    runs = []
    for seed in SEEDS:
        for arm in ARMS:
            run_dir = OUT / "runs" / f"{arm}-seed{seed}"
            complete_files = [run_dir / "final.pt", run_dir / "reported_candidates.csv", run_dir / "summary.json"]
            if arm == "unconditional_reranking":
                complete_files.append(run_dir / "unconditional_pool.csv")
            if all(path.exists() for path in complete_files):
                frame = pd.read_csv(run_dir / "reported_candidates.csv")
                run = json.loads((run_dir / "summary.json").read_text())
            else:
                frame, run = train_and_generate(arm, seed, train, tokenizer, verifier, train_fps, targets, run_dir)
            all_reported.append(frame)
            runs.append(run)
    reported = pd.concat(all_reported, ignore_index=True)
    reported.to_csv(OUT / "candidate_predictions.csv", index=False)
    metrics, monotonicity = summarize(reported, train, targets)
    metrics.to_csv(OUT / "metrics_by_cell.csv", index=False)
    monotonicity.to_csv(OUT / "monotonicity.csv", index=False)
    support = metrics.copy()
    support["actual_boundary"] = float(train.log_sigma.max())
    support["target_minus_actual_boundary"] = support.target - support.actual_boundary
    support["cell_status"] = np.where((support.n > 0) & (support.validity > 0), "supported_by_valid_output", "unsupported_no_valid_output")
    support.to_csv(OUT / "cell_support.csv", index=False)
    unsupported = support[support.cell_status != "supported_by_valid_output"].copy()
    unsupported["reason"] = "no valid generated candidate in the reported cell"
    unsupported.to_csv(OUT / "unsupported_cells.csv", index=False)
    failure = reported.loc[~reported.valid].groupby(["arm", "seed", "target_label", "failure_reason"], as_index=False).size()
    failure.to_csv(OUT / "failure_reasons.csv", index=False)
    selected = select_md_candidates(reported)
    selected.to_csv(OUT / "candidate_selection_for_md.csv", index=False)
    result = {
        "status": "complete_prediction_phase_md_not_run",
        "benchmark": "continuous-vs-binary-vs-unconditional-reranking upper-tail",
        "source_sha256": sha256(SOURCE), "train_rows": len(train), "locked_tail_rows": len(tail),
        "actual_train_boundary": float(train.log_sigma.max()), "nominal_q80": q80,
        "binary_status": audit["binary_status"], "unsupported_cells": unsupported.to_dict("records"),
        "verifier": verifier_metrics, "runs": runs,
        "metrics": metrics.to_dict("records"), "monotonicity": monotonicity.to_dict("records"),
        "unconditional_reranking_status": audit["unconditional_reranking_status"],
        "alternative_binary_sensitivity": audit["alternative_binary_sensitivity"],
        "candidate_selection_rows": int(len(selected)),
        "md_status": "not_run",
    }
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(OUT), "train_rows": len(train), "tail_rows": len(tail), "runs": len(runs), "candidate_rows": len(reported), "selected_md_rows": len(selected), "binary_status": audit["binary_status"]}, indent=2))


if __name__ == "__main__":
    main()
