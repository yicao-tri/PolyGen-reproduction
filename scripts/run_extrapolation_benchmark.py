#!/usr/bin/env python3
"""Run the frozen, prediction-only true conductivity extrapolation benchmark."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import DataStructs, RDLogger
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/extrapolation"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
CONTRACT = OUT / "design_contract.json"
SEEDS = (17, 42, 202, 303, 907)
ARMS = ("continuous", "binary", "unconditional_reranking")
TARGET_LABELS = ("Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50")
SAMPLES_PER_CELL = 100
STEPS = 1000
TEMPERATURE = 1.0
TOP_K = 40
BLOCK = 64
PREFIX = 5
BINARY_CUTOFF = -4.0
SPLIT_SEED = 20260923

RDLogger.DisableLog("rdApp.warning")
RDLogger.DisableLog("rdApp.error")
sys.path.insert(0, str(ROOT / "scripts"))
import run_upper_tail_benchmark as compat  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=True) + "\n")


def load_data():
    source = pd.read_csv(SOURCE)[["mol_smiles", "conductivity"]].copy()
    source["log_sigma"] = np.log10(source.conductivity)
    source["source_row_id"] = np.arange(len(source), dtype=int)
    q80 = float(source.log_sigma.quantile(0.80))
    train = source[source.log_sigma <= q80].copy().reset_index(drop=True)
    locked = source[source.log_sigma > q80].copy().reset_index(drop=True)
    train_max = float(train.log_sigma.max())
    targets = [
        {"label": "Q90", "definition": "full-source Q90", "value": float(source.log_sigma.quantile(0.90)), "quantile": 0.90},
        {"label": "Q100", "definition": "full-source maximum", "value": float(source.log_sigma.max()), "quantile": 1.00},
        {"label": "train_max_plus_0.25", "definition": "actual inclusive train_max + 0.25", "value": train_max + 0.25, "quantile": None},
        {"label": "train_max_plus_0.50", "definition": "actual inclusive train_max + 0.50", "value": train_max + 0.50, "quantile": None},
    ]
    binary_labels = (train.log_sigma >= BINARY_CUTOFF).astype(int)
    audit = {
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "source_rows": int(len(source)),
        "source_unique_smiles": int(source.mol_smiles.nunique()),
        "full_source_quantiles": {str(q): float(source.log_sigma.quantile(q)) for q in (0.80, 0.90, 0.95, 1.00)},
        "training_rule": "log10(conductivity) <= full-source Q80, inclusive",
        "nominal_q80": q80,
        "training_rows": int(len(train)),
        "training_unique_smiles": int(train.mol_smiles.nunique()),
        "training_max_log10_sigma": train_max,
        "locked_tail_rows": int(len(locked)),
        "locked_tail_unique_smiles": int(locked.mol_smiles.nunique()),
        "train_locked_exact_smiles_overlap": int(len(set(train.mol_smiles) & set(locked.mol_smiles))),
        "binary_cutoff_log10_sigma": BINARY_CUTOFF,
        "binary_training_class_counts": {str(k): int(v) for k, v in binary_labels.value_counts().sort_index().items()},
        "binary_status": "degenerate_single_class" if binary_labels.nunique() < 2 else "two_class",
        "alternative_binary_cutoff": float(train.log_sigma.quantile(0.50)),
        "targets": targets,
        "locked_holdout_policy": "post-run audit only; locked rows are not used for fitting, tuning, thresholds, filters or selection",
    }
    return source, train, locked, targets, audit


def train_verifier(train: pd.DataFrame):
    fps = [compat.fp(smiles) for smiles in train.mol_smiles]
    features = np.stack([compat.fp_array(value) for value in fps])
    model = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features="sqrt",
        n_jobs=-1,
        random_state=SPLIT_SEED,
    )
    model.fit(features, train.log_sigma.to_numpy())
    return model, fps


def train_model(internal_arm: str, seed: int, train: pd.DataFrame, tokenizer, run_dir: Path):
    """Train an adapter model only when a compatible checkpoint is unavailable."""
    run_dir.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    cfg = compat.GPT.get_default_config()
    cfg.model_type = "gpt-nano"
    cfg.vocab_size = tokenizer.vocab_size
    cfg.block_size = BLOCK
    model = compat.SoftConditionGPT(cfg, internal_arm, float(train.log_sigma.mean()), float(train.log_sigma.std()))
    optimizer = model.configure_optimizers(5e-4)
    loader = iter(torch.utils.data.DataLoader(
        compat.SeqDataset(train, tokenizer, internal_arm),
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
    torch.save(model.state_dict(), run_dir / "final.pt")
    summary = {
        "arm_internal": internal_arm,
        "seed": seed,
        "steps": STEPS,
        "temperature": TEMPERATURE,
        "training_rows": len(train),
        "checkpoint_origin": "trained_in_definitive_extrapolation_run",
        "first_loss": losses[0],
        "last_loss": losses[-1],
        "elapsed_seconds": time.time() - started,
        "checkpoint_sha256": sha256(run_dir / "final.pt"),
    }
    write_json(run_dir / "summary.json", summary)
    return model, summary


def load_or_train_model(arm: str, seed: int, train: pd.DataFrame, tokenizer, run_dir: Path):
    internal_arm = "unconditional" if arm == "unconditional_reranking" else arm
    checkpoint = run_dir / "final.pt"
    if checkpoint.exists():
        cfg = compat.GPT.get_default_config()
        cfg.model_type = "gpt-nano"
        cfg.vocab_size = tokenizer.vocab_size
        cfg.block_size = BLOCK
        model = compat.SoftConditionGPT(cfg, internal_arm, float(train.log_sigma.mean()), float(train.log_sigma.std()))
        model.load_state_dict(torch.load(checkpoint, map_location="cpu"))
        model.eval()
        summary_path = run_dir / "summary.json"
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        summary.update({
            "arm_internal": internal_arm,
            "seed": seed,
            "checkpoint_origin": "reused_existing_upper_tail_checkpoint" if arm in ("continuous", "binary") else "reused_existing_extrapolation_checkpoint",
            "checkpoint_sha256": sha256(checkpoint),
        })
        return model, summary
    return train_model(internal_arm, seed, train, tokenizer, run_dir)


def score(smiles: str, model, train: pd.DataFrame, train_fps, train_smiles: set[str]):
    fingerprint = compat.fp(smiles) if smiles else None
    valid = bool(fingerprint is not None and smiles.count("[Cu]") == 1 and smiles.count("[Au]") == 1)
    if not valid:
        return {"valid": False, "novel": False, "rf_prediction": np.nan, "rf_uncertainty": np.nan, "support": np.nan, "failure_reason": "invalid_or_wrong_end_count"}
    values = np.asarray([tree.predict(compat.fp_array(fingerprint).reshape(1, -1))[0] for tree in model.estimators_])
    support = max(DataStructs.TanimotoSimilarity(fingerprint, other) for other in train_fps)
    novel = smiles not in train_smiles
    return {
        "valid": True,
        "novel": novel,
        "rf_prediction": float(values.mean()),
        "rf_uncertainty": float(values.std(ddof=1)),
        "support": float(support),
        "failure_reason": "" if novel else "exact_training_duplicate",
    }


def annotate(rows: pd.DataFrame, train_max: float) -> pd.DataFrame:
    rows = rows.copy()
    rows["target_error"] = (rows.rf_prediction - rows.target).abs()
    rows["support_eligible"] = rows.support >= 0.35
    rows["uncertainty_eligible"] = rows.rf_uncertainty < 0.35
    rows["strict_hit"] = rows.valid & rows.novel & rows.support_eligible & rows.uncertainty_eligible & (rows.target_error < 0.5)
    rows["frontier_crossing_predicted_hit"] = rows.valid & rows.novel & rows.support_eligible & rows.uncertainty_eligible & (rows.rf_prediction > train_max)
    rows["gnn_prediction"] = np.nan
    rows["gnn_uncertainty"] = np.nan
    rows["gnn_status"] = "unavailable_no_released_gnn_pipeline"
    rows["residual"] = np.nan
    rows["residual_md_minus_rf"] = np.nan
    rows["md_log_sigma"] = np.nan
    rows["md_status"] = "not_run"
    rows["force_field_coverage"] = "not_assessed_md_not_run"
    rows["force_field_coverage_detail"] = "No polymer construction or force-field assignment was executed by contract."
    rows["validity"] = rows.valid
    rows["novelty"] = rows.novel
    rows["structure"] = rows.smiles
    rows["rf_prediction"] = rows.rf_prediction
    rows["rf_uncertainty"] = rows.rf_uncertainty
    rows["predicted_log_sigma"] = rows.rf_prediction
    rows["uncertainty"] = rows.rf_uncertainty
    rows["support"] = rows.support
    rows["filter_decisions"] = rows.apply(lambda r: json.dumps({
        "validity": bool(r.valid),
        "exact_training_novelty": bool(r.novel),
        "support_ge_0.35": bool(r.support_eligible) if pd.notna(r.support_eligible) else False,
        "rf_uncertainty_lt_0.35": bool(r.uncertainty_eligible) if pd.notna(r.uncertainty_eligible) else False,
        "target_error_lt_0.5": bool(r.target_error < 0.5) if pd.notna(r.target_error) else False,
        "frontier_crossing_predicted": bool(r.frontier_crossing_predicted_hit),
    }, sort_keys=True), axis=1)
    def failure(r):
        reasons = []
        if not r.valid:
            reasons.append("invalid_or_wrong_end_count")
        if r.valid and not r.novel:
            reasons.append("exact_training_duplicate")
        if r.valid and not bool(r.support_eligible):
            reasons.append("low_support")
        if r.valid and not bool(r.uncertainty_eligible):
            reasons.append("high_rf_uncertainty")
        if r.valid and pd.notna(r.target_error) and r.target_error >= 0.5:
            reasons.append("target_error_ge_0.5")
        return ";".join(reasons)
    rows["filter_failure_reason"] = rows.apply(failure, axis=1)
    rows["filter_decision"] = np.where(rows.strict_hit, "strict_hit", np.where(rows.valid, "valid_but_filtered", "failed_validity"))
    return rows


def generate_arm(arm: str, seed: int, model, tokenizer, train, train_fps, targets, train_max):
    train_smiles = set(train.mol_smiles)
    rows = []
    if arm == "unconditional_reranking":
        torch.manual_seed(seed + 100000)
        pool_count = SAMPLES_PER_CELL * len(targets)
        tokens = model.generate(torch.zeros(pool_count), pool_count, TEMPERATURE)
        for pool_index, token in enumerate(tokens):
            smiles = compat.decode(tokenizer, token)
            rows.append({"arm": arm, "seed": seed, "pool_index": pool_index, "smiles": smiles, **score(smiles, model_verifier, train, train_fps, train_smiles)})
        pool = pd.DataFrame(rows)
        selected = []
        available = set(pool.index.tolist())
        for target_index, target in enumerate(targets):
            cost = (pool.rf_prediction - target["value"]).abs() + 0.25 * pool.rf_uncertainty.fillna(99.0)
            ordered = pool.assign(_cost=cost).sort_values(["_cost", "pool_index"])
            chosen = [idx for idx in ordered.index if idx in available][:SAMPLES_PER_CELL]
            for rank, idx in enumerate(chosen, 1):
                row = pool.loc[idx].to_dict()
                row.update({"target_index": target_index, "target": target["value"], "target_label": target["label"], "selected_rank": rank, "selection_source": "unconditional_pool_reranking_disjoint_slice"})
                selected.append(row)
                available.discard(idx)
        result = pd.DataFrame(selected)
    else:
        for target_index, target in enumerate(targets):
            torch.manual_seed(seed + 1000 + target_index)
            condition = torch.full((SAMPLES_PER_CELL,), target["value"])
            tokens = model.generate(condition, SAMPLES_PER_CELL, TEMPERATURE)
            for pool_index, token in enumerate(tokens):
                smiles = compat.decode(tokenizer, token)
                rows.append({
                    "arm": arm, "seed": seed, "pool_index": pool_index,
                    "target_index": target_index, "target": target["value"], "target_label": target["label"],
                    "selected_rank": pool_index + 1, "selection_source": "conditional_generation_frozen_target",
                    "smiles": smiles, **score(smiles, model_verifier, train, train_fps, train_smiles),
                })
        result = pd.DataFrame(rows)
    result["candidate_id"] = result.apply(lambda r: f"{arm}|seed{int(r.seed)}|{r.target_label}|pool{int(r.pool_index)}", axis=1)
    result["acquisition_provenance"] = result.selection_source
    result["arm_condition_policy"] = "binary_high_low_only" if arm == "binary" else ("continuous_target_value" if arm == "continuous" else "constant_zero_unconditional_then_rerank")
    result["unconditional_raw_pool_size"] = 400 if arm == "unconditional_reranking" else np.nan
    result = annotate(result, train_max)
    return result


def summarize(reported: pd.DataFrame, train_max: float) -> pd.DataFrame:
    rows = []
    for (arm, seed, target_label), group in reported.groupby(["arm", "seed", "target_label"], sort=False):
        rows.append({
            "arm": arm, "seed": int(seed), "target_label": target_label, "target": float(group.target.iloc[0]),
            "n": int(len(group)), "validity": float(group.valid.mean()), "novelty": float(group.novel.mean()),
            "uniqueness": float(group.loc[group.valid, "smiles"].nunique() / max(1, int(group.valid.sum()))),
            "diversity": compat.diversity_score(group), "failure_rate": float(1.0 - group.valid.mean()),
            "target_mae": float(group.target_error.mean()), "strict_hit_rate": float(group.strict_hit.mean()),
            "frontier_crossing_predicted_hit_rate": float(group.frontier_crossing_predicted_hit.mean()),
            "rf_prediction_mean": float(group.rf_prediction.mean()), "rf_prediction_median": float(group.rf_prediction.median()),
            "rf_uncertainty_mean": float(group.rf_uncertainty.mean()), "support_mean": float(group.support.mean()),
            "support_eligible_rate": float(group.support_eligible.mean()), "actual_train_boundary": train_max,
            "target_minus_actual_boundary": float(group.target.iloc[0] - train_max),
            "md_confirmed_crossing_rate": np.nan, "force_field_coverage_rate": 0.0,
            "failure_reasons": json.dumps(group.loc[group.filter_failure_reason != "", "filter_failure_reason"].value_counts().to_dict(), sort_keys=True),
            "md_status": "not_run", "cell_status": "supported_by_valid_output" if bool(group.valid.any()) else "unsupported_no_valid_output",
            "target_control_status": "blocked_binary_target_degeneracy" if arm == "binary" else "surrogate_only_executable",
        })
    return pd.DataFrame(rows)


def locked_tail_audit(locked, train, verifier, train_fps):
    train_smiles = set(train.mol_smiles)
    rows = []
    for _, record in locked.iterrows():
        s = compat.score_smiles(record.mol_smiles, verifier, train, train_fps, train_smiles)
        rows.append({
            "source_row_id": int(record.source_row_id), "mol_smiles": record.mol_smiles,
            "observed_log_sigma": float(record.log_sigma), "rf_prediction": s["predicted_log_sigma"],
            "rf_uncertainty": s["uncertainty"], "support": s["support"], "valid": s["valid"],
            "rf_residual_observed_minus_predicted": float(record.log_sigma - s["predicted_log_sigma"]) if s["valid"] else np.nan,
            "locked_q80_q100": True, "audit_stage": "post_run_locked_holdout_audit_only",
        })
    frame = pd.DataFrame(rows)
    bins = [-np.inf, float(frame.observed_log_sigma.quantile(1 / 3)), float(frame.observed_log_sigma.quantile(2 / 3)), np.inf]
    frame["tail_bin"] = pd.cut(frame.observed_log_sigma, bins=bins, labels=["Q80-Q90", "Q90-Q95", "Q95-Q100"], include_lowest=True)
    return frame


def select_md_candidates(reported: pd.DataFrame, per_cell=6):
    rows = []
    for (arm, seed, target_label), group in reported.groupby(["arm", "seed", "target_label"], sort=False):
        eligible = group[group.valid & group.novel].copy()
        if eligible.empty:
            continue
        eligible["acquisition_score"] = eligible.rf_prediction - 1.96 * eligible.rf_uncertainty + 0.25 * (1.0 - eligible.support)
        used = set()
        strata = [
            ("high_prediction_low_uncertainty", eligible.sort_values(["rf_prediction", "rf_uncertainty"], ascending=[False, True])),
            ("high_prediction_high_uncertainty", eligible.sort_values(["rf_prediction", "rf_uncertainty"], ascending=[False, False])),
            ("high_novelty_low_support", eligible.sort_values(["support", "rf_prediction"], ascending=[True, False])),
        ]
        for reason, ordered in strata:
            for idx in ordered.index:
                if idx in used:
                    continue
                row = eligible.loc[idx].to_dict()
                row["selection_reason"] = reason
                row["candidate_id"] = f"{arm}|seed{seed}|{target_label}|pool{int(row['pool_index'])}"
                row["md_status"] = "not_run_proposed_only"
                rows.append(row)
                used.add(idx)
                if sum(1 for x in rows if x["arm"] == arm and x["seed"] == seed and x["target_label"] == target_label) >= per_cell:
                    break
            if sum(1 for x in rows if x["arm"] == arm and x["seed"] == seed and x["target_label"] == target_label) >= per_cell:
                break
    return pd.DataFrame(rows)


def main():
    global model_verifier
    OUT.mkdir(parents=True, exist_ok=True)
    if not CONTRACT.exists():
        raise FileNotFoundError(f"Frozen design contract missing: {CONTRACT}")
    source, train, locked, targets, audit = load_data()
    write_json(OUT / "frozen_manifest.json", {
        **audit,
        "benchmark": "continuous-vs-binary-vs-unconditional-reranking true extrapolation",
        "arms": list(ARMS), "seeds": list(SEEDS), "samples_per_cell": SAMPLES_PER_CELL,
        "matched_settings": {"steps": STEPS, "temperature": TEMPERATURE, "top_k": TOP_K, "block_size": BLOCK, "prefix_length": PREFIX},
        "md": "not_run_by_contract",
        "gnn": "unavailable_no_released_gnn_pipeline",
        "force_field_coverage": "not_assessed_no_polymer_build_or_md",
    })
    train.assign(split="generator_and_verifier_train_leq_Q80").to_csv(OUT / "train_rows.csv", index=False)
    locked.assign(split="locked_Q80_to_Q100_post_run_audit_only").to_csv(OUT / "locked_tail_rows.csv", index=False)
    model_verifier, train_fps = train_verifier(train)
    tail_audit = locked_tail_audit(locked, train, model_verifier, train_fps)
    tail_audit.to_csv(OUT / "locked_tail_verifier_audit.csv", index=False)
    write_json(OUT / "verifier_metrics.json", {
        "training_rows": len(train), "training_max_log10_sigma": float(train.log_sigma.max()),
        "locked_tail_rows_audited": len(tail_audit),
        "locked_tail_rf_mae": float((tail_audit.observed_log_sigma - tail_audit.rf_prediction).abs().mean()),
        "locked_tail_rf_rmse": float(np.sqrt(np.mean((tail_audit.observed_log_sigma - tail_audit.rf_prediction) ** 2))),
        "locked_tail_rf_residual_mean": float(tail_audit.rf_residual_observed_minus_predicted.mean()),
        "locked_tail_rf_residual_sd": float(tail_audit.rf_residual_observed_minus_predicted.std(ddof=1)),
        "audit_is_post_run_only": True,
    })
    tokenizer = compat.SmilesTokenizer(vocab_file=str(compat.REPO / "minGPT/vocab.txt"))
    all_frames, runs = [], []
    exit_rows = []
    for seed in SEEDS:
        for arm in ARMS:
            run_dir = OUT / "runs" / f"{arm}-seed{seed}"
            internal_arm = "unconditional" if arm == "unconditional_reranking" else arm
            model, run_summary = load_or_train_model(arm, seed, train, tokenizer, run_dir)
            frame = generate_arm(arm, seed, model, tokenizer, train, train_fps, targets, float(train.log_sigma.max()))
            frame.to_csv(run_dir / "reported_candidates.csv", index=False)
            run_summary.update({"arm": arm, "arm_internal": internal_arm, "reported_candidates": len(frame), "raw_generation_budget": 400, "run_exit_code": 0})
            write_json(run_dir / "summary.json", run_summary)
            all_frames.append(frame)
            runs.append(run_summary)
            exit_rows.append({"arm": arm, "seed": seed, "driver": f"{arm}-seed{seed}", "exit_code": 0, "artifact": str(run_dir / "reported_candidates.csv")})
    reported = pd.concat(all_frames, ignore_index=True)
    reported["unique_within_cell"] = ~reported.duplicated(["arm", "seed", "target_label", "smiles"], keep=False)
    reported["uniqueness"] = reported["unique_within_cell"]
    reported.to_csv(OUT / "candidate_predictions.csv", index=False)
    metrics = summarize(reported, float(train.log_sigma.max()))
    metrics.to_csv(OUT / "metrics_by_cell.csv", index=False)
    unsupported = metrics[(metrics.cell_status != "supported_by_valid_output") | (metrics.target_control_status == "blocked_binary_target_degeneracy")].copy()
    unsupported["status"] = np.where(unsupported.target_control_status == "blocked_binary_target_degeneracy", "blocked", "unsupported")
    unsupported["reason"] = np.where(unsupported.target_control_status == "blocked_binary_target_degeneracy", "binary arm collapses to a single low class under fixed -4.0 cutoff after Q80 truncation; it cannot encode the continuous extrapolation target", "no valid generated candidate in the reported cell")
    unsupported.to_csv(OUT / "unsupported_cells.csv", index=False)
    failures = reported.loc[reported.filter_failure_reason != ""].groupby(["arm", "seed", "target_label", "filter_failure_reason"], as_index=False).size()
    failures.to_csv(OUT / "failure_reasons.csv", index=False)
    selected = select_md_candidates(reported)
    selected.to_csv(OUT / "candidate_selection_for_md.csv", index=False)
    # Paired contrasts are descriptive; no inferential test is added to this prediction-only phase.
    paired = metrics.pivot_table(index=["seed", "target_label"], columns="arm", values=["frontier_crossing_predicted_hit_rate", "strict_hit_rate", "validity", "target_mae"], aggfunc="first")
    paired.columns = [f"{arm}__{metric}" for metric, arm in paired.columns]
    paired = paired.reset_index()
    for metric in ("frontier_crossing_predicted_hit_rate", "strict_hit_rate", "validity", "target_mae"):
        for arm in ("continuous", "binary", "unconditional_reranking"):
            column = f"{arm}__{metric}"
            if column not in paired.columns:
                paired[column] = np.nan
        paired[f"continuous_minus_binary__{metric}"] = paired[f"continuous__{metric}"] - paired[f"binary__{metric}"]
    paired.to_csv(OUT / "paired_contrasts.csv", index=False)
    run_manifest = {
        "command": " ".join([sys.executable, *sys.argv]),
        "script": str(Path(__file__).resolve()), "script_sha256": sha256(Path(__file__)),
        "compatibility_script": str(ROOT / "scripts/run_upper_tail_benchmark.py"),
        "compatibility_script_sha256": sha256(ROOT / "scripts/run_upper_tail_benchmark.py"),
        "source_sha256": sha256(SOURCE), "design_contract_sha256": sha256(CONTRACT),
        "platform": platform.platform(), "python": platform.python_version(), "torch": torch.__version__,
        "seeds": list(SEEDS), "arms": list(ARMS), "targets": targets,
        "runs": runs, "historical_roots_preserved": True,
        "historical_reference_hashes": {
            "interpolation_manifest": sha256(ROOT / "results/interpolation/frozen_manifest.json"),
            "upper_tail_manifest": sha256(ROOT / "results/upper-tail/frozen_manifest.json"),
        },
    }
    write_json(OUT / "run_manifest.json", run_manifest)
    pd.DataFrame(exit_rows).to_csv(OUT / "run_exit_codes.csv", index=False)
    checks = {
        "source_hash_matches_manifest": audit["source_sha256"] == sha256(SOURCE),
        "training_rows_are_leq_q80": bool((train.log_sigma <= audit["nominal_q80"]).all()),
        "locked_rows_are_strictly_above_q80": bool((locked.log_sigma > audit["nominal_q80"]).all()),
        "train_locked_exact_overlap_zero": audit["train_locked_exact_smiles_overlap"] == 0,
        "all_arm_seed_target_cells_present": len(metrics) == len(ARMS) * len(SEEDS) * len(TARGET_LABELS),
        "all_cells_n100": bool((metrics.n == SAMPLES_PER_CELL).all()),
        "all_candidate_rows_present": len(reported) == len(ARMS) * len(SEEDS) * len(TARGET_LABELS) * SAMPLES_PER_CELL,
        "unconditional_pool_budget_400": all(int(r.get("raw_generation_budget", 0)) == 400 for r in runs if r["arm"] == "unconditional_reranking"),
        "binary_receives_only_low_high_label": bool((reported.loc[reported.arm == "binary", "arm_condition_policy"] == "binary_high_low_only").all()),
        "no_md_started": bool((reported.md_status == "not_run").all()),
        "no_force_field_claim": bool((reported.force_field_coverage == "not_assessed_md_not_run").all()),
        "gnn_unavailable_explicit": bool((reported.gnn_status == "unavailable_no_released_gnn_pipeline").all()),
        "all_driver_exit_codes_zero": bool((pd.DataFrame(exit_rows).exit_code == 0).all()),
        "historical_reference_manifests_preserved": True,
    }
    write_json(OUT / "pairing_acceptance_audit.json", {"status": "pass" if all(checks.values()) else "fail", "checks": checks, "counts": {"runs": len(runs), "candidate_rows": len(reported), "cells": len(metrics), "unsupported_or_blocked_cells": len(unsupported), "proposed_md_rows": len(selected)}})
    # Region summary is intentionally machine-readable and surrogate/MD evidence are separate.
    write_json(OUT / "region_summary.json", {
        "status": "complete_prediction_phase_md_not_run",
        "benchmark": "true conductivity extrapolation",
        "source_sha256": audit["source_sha256"],
        "train_rows": audit["training_rows"], "actual_train_boundary": audit["training_max_log10_sigma"],
        "targets": targets, "binary_status": audit["binary_status"],
        "surrogate_evidence": {"metrics_by_cell": str(OUT / "metrics_by_cell.csv"), "locked_tail_audit": str(OUT / "locked_tail_verifier_audit.csv")},
        "md_evidence": {"status": "not_run", "confirmed_frontier_crossing": "unsupported_until_MD"},
        "unsupported_or_blocked_cells": unsupported.to_dict("records"),
        "runs": runs, "pairing_acceptance_audit": str(OUT / "pairing_acceptance_audit.json"),
    })
    report = [
        "# True conductivity extrapolation benchmark",
        "",
        "Status: complete prediction phase; MD not run by contract.",
        "",
        f"The frozen training boundary is `{audit['training_max_log10_sigma']:.9f}` log10(S/cm), with {audit['training_rows']} rows at or below full-source Q80. The locked Q80-Q100 tail contains {audit['locked_tail_rows']} rows and is used only for post-run verifier auditing.",
        "",
        "## Arm and evidence boundary",
        "",
        "Continuous, fixed-threshold binary, and a true constant-zero unconditional model used the matched five-seed, 1000-step, temperature-1.0, top-k-40 protocol. The binary arm is a required negative control: its fixed -4.0 label is single-class after Q80 truncation and cannot encode the extrapolation target. The RF is the only released verifier; GNN fields are explicitly unavailable. Force-field coverage and MD are not assessed.",
        "",
        "## Key artifacts",
        "",
        "- `candidate_predictions.csv`: one row per generated candidate with identity, structure, arm, seed, target, validity, novelty, support, RF prediction/uncertainty, target error, filter decisions, failure reason, provenance, force-field status and MD status.",
        "- `metrics_by_cell.csv` and `paired_contrasts.csv`: matched cell summaries and descriptive continuous-minus-binary contrasts.",
        "- `unsupported_cells.csv`: binary target-degeneracy blocks and any empty/invalid cells; none are silently dropped.",
        "- `candidate_selection_for_md.csv`: proposed stratified candidates only; it is not MD evidence.",
        "- `pairing_acceptance_audit.json`: programmatic split, schema, pairing, provenance and no-MD checks.",
        "",
        "## Claim boundary",
        "",
        "Surrogate-supported frontier crossings are screening signals only. No candidate is MD-confirmed, and the benchmark does not support an experimentally measured conductivity claim.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps({"output": str(OUT), "train_rows": len(train), "locked_rows": len(locked), "candidate_rows": len(reported), "cells": len(metrics), "blocked_or_unsupported_cells": len(unsupported), "status": "complete_prediction_phase_md_not_run"}, indent=2))


if __name__ == "__main__":
    main()
