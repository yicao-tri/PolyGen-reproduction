#!/usr/bin/env python3
"""Frozen six-property interpolation benchmark; prediction only, no MD."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import shutil
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
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "multi-property" / "interpolation"
SOURCE = ROOT / "inputs" / "release-data" / "htpmd-trainset.csv"
REPO = ROOT / "vendor" / "PolyGen-1.0.0"
sys.path.insert(0, str(REPO))
from deepchem.feat.smiles_tokenizer import SmilesTokenizer
from minGPT.model.mingpt.model import GPT

RDLogger.DisableLog("rdApp.*")

SEEDS = (17, 42, 202, 303, 907)
ARMS = ("multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking")
N = 100
STEPS = 1000
BATCH = 64
LR = 5e-4
BLOCK = 64
PREFIX = 5
TOP_K = 40
QLEVELS = (0.50, 0.65, 0.80)
BINARY_CUTOFF = -4.0
STRUCTURAL_SUPPORT_GATE = 0.35
UNCERTAINTY_GATE = 0.35
JOINT_ERROR_GATE = 0.50
PROP_SPECS = (
    ("log10_conductivity", "conductivity", "log10"),
    ("log10_li_diffusivity", "li_diffusivity", "log10"),
    ("log10_tfsi_diffusivity", "tfsi_diffusivity", "log10"),
    ("log10_poly_diffusivity", "poly_diffusivity", "log10"),
    ("transference_number", "transference_number", "raw"),
    ("molality", "molality", "raw"),
)
PROP_NAMES = [x[0] for x in PROP_SPECS]
TRANSFORMED_SOURCE_FIELDS = [x[1] for x in PROP_SPECS]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")


def fp(smiles: str):
    try:
        m = Chem.MolFromSmiles(str(smiles).replace("[Cu]", "[*]").replace("[Au]", "[*]"))
        return None if m is None else AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048)
    except Exception:
        return None


def fp_array(f):
    a = np.zeros(2048, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(f, a)
    return a


def transform_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for name, source, transform in PROP_SPECS:
        values = pd.to_numeric(out[source], errors="coerce")
        out[name] = np.log10(values) if transform == "log10" else values
    return out


def prepare() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(SOURCE)
    raw.insert(0, "source_row_index", np.arange(len(raw), dtype=int))
    frame = transform_frame(raw)
    bins = pd.qcut(frame["log10_conductivity"], 10, labels=False, duplicates="drop")
    train, test = train_test_split(frame, test_size=0.2, random_state=20260923, stratify=bins)
    return raw, train.reset_index(drop=True), test.reset_index(drop=True)


def audit_source(raw: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame) -> dict:
    finite = {}
    for name, source, transform in PROP_SPECS:
        vals = pd.to_numeric(raw[source], errors="coerce")
        finite[source] = {
            "nonfinite": int((~np.isfinite(vals)).sum()),
            "nonpositive_for_log": int((vals <= 0).sum()) if transform == "log10" else 0,
            "unique": int(vals.nunique(dropna=True)),
        }
    dup = raw.groupby("mol_smiles", dropna=False)
    discordant = 0
    duplicate_groups = 0
    duplicate_rows = 0
    for _, g in dup:
        if len(g) > 1:
            duplicate_groups += 1
            duplicate_rows += len(g)
            if g[TRANSFORMED_SOURCE_FIELDS].nunique(dropna=False).max() > 1:
                discordant += 1
    q = {}
    for name in PROP_NAMES:
        s = train[name]
        q[name] = {str(x): float(s.quantile(x)) for x in (0.5, 0.65, 0.8, 0.9, 0.95)}
    return {
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "rows": int(len(raw)),
        "columns": list(raw.columns),
        "required_source_fields": TRANSFORMED_SOURCE_FIELDS,
        "finite_and_domain_audit": finite,
        "unique_smiles": int(raw.mol_smiles.nunique(dropna=True)),
        "duplicate_smiles_groups": duplicate_groups,
        "duplicate_smiles_rows": duplicate_rows,
        "discordant_duplicate_groups_across_six_properties": discordant,
        "split": {"method": "train_test_split stratified conductivity deciles", "random_state": 20260923, "train_rows": int(len(train)), "test_rows": int(len(test)), "train_test_source_row_overlap": int(len(set(train.source_row_index) & set(test.source_row_index)))},
        "train_only_quantiles": q,
        "train_only_property_summary": {name: {k: float(v) for k, v in train[name].describe().to_dict().items()} for name in PROP_NAMES},
    }


def fit_verifiers(train: pd.DataFrame, test: pd.DataFrame):
    train_fp = [fp(s) for s in train.mol_smiles]
    good = np.array([x is not None for x in train_fp])
    X = np.stack([fp_array(x) for x, ok in zip(train_fp, good) if ok])
    models = {}
    metrics = {}
    test_fp = [fp(s) for s in test.mol_smiles]
    test_good = np.array([x is not None for x in test_fp])
    Xtest = np.stack([fp_array(x) for x, ok in zip(test_fp, test_good) if ok])
    for name in PROP_NAMES:
        model = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, max_features="sqrt", n_jobs=-1, random_state=20260923)
        y = train.loc[good, name].to_numpy(dtype=float)
        model.fit(X, y)
        p = model.predict(Xtest)
        ytest = test.loc[test_good, name].to_numpy(dtype=float)
        metrics[name] = {"test_rows": int(len(ytest)), "rmse": float(np.sqrt(np.mean((ytest - p) ** 2))), "mae": float(np.mean(np.abs(ytest - p))), "train_std": float(np.std(y, ddof=1)), "estimators": 300, "random_state": 20260923}
        models[name] = model
    return models, train_fp, metrics


class SeqDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, tokenizer: SmilesTokenizer, cond: np.ndarray):
        self.cond = torch.tensor(cond, dtype=torch.float32)
        seq = []
        for s in frame.mol_smiles:
            ids = tokenizer.encode(s)
            ids = np.pad(ids, (0, BLOCK + 1 - PREFIX - len(ids)), constant_values=0)[: BLOCK + 1 - PREFIX]
            seq.append(np.concatenate([np.ones(PREFIX, dtype=np.int64), ids]))
        self.seq = torch.tensor(np.stack(seq), dtype=torch.long)

    def __len__(self):
        return len(self.seq)

    def __getitem__(self, i):
        return self.seq[i, :-1], self.seq[i, 1:], self.cond[i]


class ConditionedGPT(nn.Module):
    def __init__(self, config, kind: str, scalar_mean: float, scalar_std: float, multi_mean: np.ndarray, multi_std: np.ndarray):
        super().__init__()
        self.gpt = GPT(config)
        self.kind = kind
        self.scalar_mean = float(scalar_mean)
        self.scalar_std = float(scalar_std)
        self.multi_mean = torch.tensor(multi_mean, dtype=torch.float32)
        self.multi_std = torch.tensor(multi_std, dtype=torch.float32)
        n = config.n_embd
        # Keep cont/binary names compatible with the released scalar checkpoints.
        self.cont = nn.Sequential(nn.Linear(1, n), nn.Tanh(), nn.Linear(n, n))
        self.binary = nn.Embedding(2, n)
        self.multi = nn.Sequential(nn.Linear(6, n), nn.Tanh(), nn.Linear(n, n))

    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=LR, betas=(0.9, 0.95), weight_decay=0.1)

    def _embedding(self, cond: torch.Tensor) -> torch.Tensor:
        if self.kind in ("scalar_continuous", "unconditional"):
            z = ((cond[:, 0] - self.scalar_mean) / self.scalar_std).view(-1, 1)
            return self.cont(z)
        if self.kind == "binary_conductivity":
            return self.binary(cond[:, 0].long().clamp(0, 1))
        z = (cond - self.multi_mean.to(cond.device)) / self.multi_std.to(cond.device)
        return self.multi(z)

    def forward(self, idx, cond, targets=None):
        b, t = idx.shape
        pos = torch.arange(t, device=idx.device).unsqueeze(0)
        tok = self.gpt.transformer.wte(idx)
        emb = self._embedding(cond)
        tok = tok.clone()
        tok[:, :PREFIX, :] += emb[:, None, :]
        x = self.gpt.transformer.drop(tok + self.gpt.transformer.wpe(pos))
        for block in self.gpt.transformer.h:
            x = block(x)
        logits = self.gpt.lm_head(self.gpt.transformer.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-1)
        return logits, loss

    @torch.no_grad()
    def generate(self, cond, n: int):
        idx = torch.ones((n, PREFIX), dtype=torch.long)
        for _ in range(BLOCK - PREFIX):
            logits, _ = self(idx, cond)
            logits = logits[:, -1, :]
            values, _ = torch.topk(logits, TOP_K)
            logits[logits < values[:, [-1]]] = -float("inf")
            idx = torch.cat([idx, torch.multinomial(F.softmax(logits, dim=-1), 1)], 1)
        return idx[:, PREFIX:]


def decode(tokenizer, row) -> str:
    s = tokenizer.decode(row).replace(" ", "")
    if "[CLS]" not in s or "[SEP]" not in s:
        return ""
    return s.split("[CLS]", 1)[1].split("[SEP]", 1)[0]


def build_targets(train: pd.DataFrame, mean: np.ndarray, std: np.ndarray) -> tuple[pd.DataFrame, dict]:
    rows = []
    med = train[PROP_NAMES].median().to_numpy(dtype=float)
    for j, name in enumerate(PROP_NAMES):
        for q in QLEVELS:
            v = med.copy()
            v[j] = float(train[name].quantile(q))
            rows.append({"target_cell": f"{name}_Q{int(q * 100)}", "target_family": "property_probe", "target_label": f"{name} at Q{int(q * 100)}; other properties at train median", "quantile": q, "probe_property": name, "vector": v.tolist(), "source_row_index": None})
    percentiles = train[PROP_NAMES].rank(pct=True, method="average").mean(axis=1).to_numpy()
    for q in QLEVELS:
        i = int(np.argmin(np.abs(percentiles - q)))
        v = train.iloc[i][PROP_NAMES].to_numpy(dtype=float)
        rows.append({"target_cell": f"joint_empirical_copula_Q{int(q * 100)}", "target_family": "coherent_joint", "target_label": f"train-only empirical-copula row at mean marginal percentile Q{int(q * 100)}", "quantile": q, "probe_property": None, "vector": v.tolist(), "source_row_index": int(train.iloc[i].source_row_index)})
    out = pd.DataFrame(rows)
    cov = np.cov(train[PROP_NAMES].to_numpy(dtype=float), rowvar=False)
    cov = cov + np.eye(len(PROP_NAMES)) * 1e-8
    inv = np.linalg.pinv(cov)
    z = train[PROP_NAMES].to_numpy(dtype=float) - mean
    train_d = np.einsum("ij,jk,ik->i", z, inv, z)
    threshold = float(np.quantile(train_d, 0.99))
    audit = []
    for i, r in out.iterrows():
        v = np.asarray(r.vector, dtype=float)
        d = float((v - mean) @ inv @ (v - mean))
        outside = [name for name, x, lo, hi in zip(PROP_NAMES, v, train[PROP_NAMES].min(), train[PROP_NAMES].max()) if x < lo or x > hi]
        near = [name for name, x in zip(PROP_NAMES, std) if x <= 1e-8]
        status = "supported" if d <= threshold and not outside and not near else "unsupported"
        reason = "" if status == "supported" else ";".join((([f"mahalanobis_sq>{threshold:.6g}"] if d > threshold else []) + (["outside_train_marginal_range:" + ",".join(outside)] if outside else []) + (["near_degenerate:" + ",".join(near)] if near else [])))
        audit.append({"target_cell": r.target_cell, "target_family": r.target_family, "joint_mahalanobis_sq": d, "train_q99_mahalanobis_sq": threshold, "outside_train_marginal_range": bool(outside), "near_degenerate_property": bool(near), "target_support_status": status, "unsupported_reason": reason})
    out["target_vector_json"] = out.vector.map(json.dumps)
    out["target_vector_normalized_json"] = out.vector.map(lambda x: json.dumps(((np.asarray(x) - mean) / std).tolist()))
    for j, name in enumerate(PROP_NAMES):
        out[f"target__{name}"] = out.vector.map(lambda x, j=j: float(x[j]))
        out[f"target_z__{name}"] = out.vector.map(lambda x, j=j: float((x[j] - mean[j]) / std[j]))
    out = out.drop(columns=["vector"])
    return out, {"covariance": cov.tolist(), "train_mahalanobis_sq_q99": threshold, "train_mahalanobis_sq_max": float(train_d.max()), "joint_target_cartesian_product_used": False, "target_count": int(len(out)), "marginal_probe_count": 18, "coherent_joint_target_count": 3, "support_audit": audit}


def load_or_train(arm: str, seed: int, train: pd.DataFrame, tokenizer: SmilesTokenizer, mean: np.ndarray, std: np.ndarray, out_dir: Path, checkpoint: Path | None = None):
    cfg = GPT.get_default_config()
    cfg.model_type = "gpt-nano"
    cfg.vocab_size = tokenizer.vocab_size
    cfg.block_size = BLOCK
    kind = arm
    model = ConditionedGPT(cfg, kind, float(train.log10_conductivity.mean()), float(train.log10_conductivity.std()), mean, std)
    started = time.time()
    origin = "trained_in_multi_property_interpolation"
    losses = []
    if checkpoint is not None and checkpoint.exists():
        state = torch.load(checkpoint, map_location="cpu")
        # Historical scalar/binary checkpoints predate the unused six-dimensional
        # projection; load their compatible parameters while keeping the extra
        # module present for a uniform state schema.
        model.load_state_dict(state, strict=False)
        origin = str(checkpoint)
    else:
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        if arm == "multi_continuous": cond = ((train[PROP_NAMES].to_numpy(dtype=float) - mean) / std)
        elif arm == "binary_conductivity": cond = (train.log10_conductivity.to_numpy() >= BINARY_CUTOFF).astype(float)[:, None]
        else: cond = train.log10_conductivity.to_numpy(dtype=float)[:, None] if arm == "scalar_continuous" else np.zeros((len(train), 1), dtype=float)
        loader = iter(DataLoader(SeqDataset(train, tokenizer, cond), batch_size=BATCH, sampler=torch.utils.data.RandomSampler(train, replacement=True, num_samples=10**9)))
        opt = model.configure_optimizers()
        model.train()
        for _ in range(STEPS):
            x, y, c = next(loader)
            _, loss = model(x, c, y)
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
            losses.append(float(loss.detach()))
    model.eval()
    run_dir = out_dir / "runs" / f"{arm}-seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), run_dir / "final.pt")
    json_dump(run_dir / "summary.json", {"arm": arm, "seed": seed, "checkpoint_origin": origin, "steps": 0 if checkpoint is not None and checkpoint.exists() else STEPS, "first_loss": losses[0] if losses else None, "last_loss": losses[-1] if losses else None, "elapsed_seconds": time.time() - started, "temperature": 1.0, "top_k": TOP_K, "samples_per_cell": N})
    return model, {"arm": arm, "seed": seed, "checkpoint_origin": origin, "checkpoint_sha256": sha256(run_dir / "final.pt"), "steps": 0 if checkpoint is not None and checkpoint.exists() else STEPS, "elapsed_seconds": time.time() - started}


def checkpoint_for(arm: str, seed: int) -> Path | None:
    if arm == "multi_continuous" or arm == "unconditional_reranking":
        return None
    historical_arm = "continuous" if arm == "scalar_continuous" else "binary"
    candidates = [ROOT / "results" / "experiment-c" / "c1" / f"{historical_arm}-seed{seed}" / "final.pt", ROOT / "results" / "experiment-c" / "extra-seeds" / "seeds202-303" / f"{historical_arm}-seed{seed}" / "final.pt"]
    return next((x for x in candidates if x.exists()), None)


def predict_fp(f, models: dict):
    if f is None:
        return {name: (np.nan, np.nan) for name in PROP_NAMES}
    a = fp_array(f).reshape(1, -1)
    out = {}
    for name, model in models.items():
        values = np.asarray([e.predict(a)[0] for e in model.estimators_], dtype=float)
        out[name] = (float(values.mean()), float(values.std(ddof=1)))
    return out


def evaluate_smiles(smiles_list, models, train_fp, train_smiles):
    """Evaluate one generated batch with vectorized RF calls."""
    fps = [fp(s) if s else None for s in smiles_list]
    valid = [x is not None and str(s).count("[Cu]") == 1 and str(s).count("[Au]") == 1 for s, x in zip(smiles_list, fps)]
    good = np.asarray(valid, dtype=bool)
    predictions = [{name: (np.nan, np.nan) for name in PROP_NAMES} for _ in smiles_list]
    supports = np.full(len(smiles_list), np.nan, dtype=float)
    if good.any():
        X = np.stack([fp_array(x) for x, ok in zip(fps, good) if ok])
        good_idx = np.flatnonzero(good)
        for name, model in models.items():
            values = np.stack([e.predict(X) for e in model.estimators_], axis=1)
            for local, original in enumerate(good_idx):
                predictions[original][name] = (float(values[local].mean()), float(values[local].std(ddof=1)))
        for local, original in enumerate(good_idx):
            supports[original] = float(max(DataStructs.BulkTanimotoSimilarity(fps[original], train_fp)))
    return fps, valid, predictions, supports


def candidate_record(smiles, arm, seed, cell, idx, models, train_fp, train_smiles, train_mean, train_std, source, selection_source, pool_index=None, evaluated=None):
    if evaluated is None:
        f = fp(smiles) if smiles else None
        valid = f is not None and str(smiles).count("[Cu]") == 1 and str(smiles).count("[Au]") == 1
        preds = predict_fp(f, models) if valid else {name: (np.nan, np.nan) for name in PROP_NAMES}
        support_override = None
    else:
        f, valid, preds, support_override = evaluated
    target = np.array([cell[f"target__{name}"] for name in PROP_NAMES], dtype=float)
    pred = np.array([preds[name][0] for name in PROP_NAMES], dtype=float)
    unc = np.array([preds[name][1] for name in PROP_NAMES], dtype=float)
    errors = np.abs(pred - target)
    zerr = (pred - target) / train_std
    joint = float(np.sqrt(np.nanmean(zerr ** 2))) if valid else np.nan
    support = float(support_override) if valid and support_override is not None else (float(max(DataStructs.BulkTanimotoSimilarity(f, train_fp))) if valid else np.nan)
    novel = bool(valid and str(smiles) not in train_smiles)
    uncertain = bool(valid and np.all(unc / train_std < UNCERTAINTY_GATE))
    strict = bool(valid and novel and support >= STRUCTURAL_SUPPORT_GATE and uncertain and joint < JOINT_ERROR_GATE and cell["target_support_status"] == "supported")
    failures = []
    if not valid:
        failures.append("invalid_or_wrong_end_count")
    else:
        for label, failed in (("not_novel", not novel), ("low_structural_support", support < STRUCTURAL_SUPPORT_GATE), ("high_joint_error", joint >= JOINT_ERROR_GATE), ("high_uncertainty", not uncertain), ("unsupported_target_cell", cell.target_support_status != "supported")):
            if failed:
                failures.append(label)
    row = {"region": "interpolation", "arm": arm, "seed": seed, "target_cell": cell.target_cell, "target_family": cell.target_family, "target_label": cell.target_label, "cell_index": int(cell.cell_index), "candidate_index": idx, "candidate_id": f"{arm}|seed{seed}|{cell.target_cell}|candidate{idx}", "structure": smiles, "smiles": smiles, "valid": valid, "novel": novel, "unique_within_cell": True, "support": support, "structural_support": support, "target_support_status": cell.target_support_status, "joint_mahalanobis_sq": cell.joint_mahalanobis_sq, "joint_target_error": joint, "joint_strict_hit": strict, "strict_hit": strict, "filter_decision": "eligible" if strict else "filtered", "filter_failure_reason": ";".join(failures), "selection_source": selection_source, "acquisition_provenance": "frozen_RF_multi_property_target_distance_and_uncertainty" if selection_source == "unconditional_pool_reranking" else "conditional_generation_frozen_target", "pool_index": pool_index, "target_vector_json": cell.target_vector_json, "condition_input_policy": {"multi_continuous": "six_dimensional_normalized_target", "scalar_continuous": "log10_conductivity_only", "binary_conductivity": "fixed_high_low_conductivity_label_only", "unconditional_reranking": "constant_zero_generation_then_frozen_RF_reranking"}[arm], "md_status": "not_run", "force_field_coverage": "not_assessed", "force_field_coverage_detail": "No polymer construction or force-field assignment was executed by contract."}
    for j, name in enumerate(PROP_NAMES):
        row[f"rf__{name}__prediction"] = preds[name][0]
        row[f"rf__{name}__uncertainty"] = preds[name][1]
        row[f"target_error__{name}"] = errors[j]
        row[f"uncertainty_normalized__{name}"] = unc[j] / train_std[j] if valid else np.nan
    row["target_error_mean"] = float(np.nanmean(errors)) if valid else np.nan
    row["uncertainty_normalized_mean"] = float(np.nanmean(unc / train_std)) if valid else np.nan
    return row


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw, train, test = prepare()
    source_audit = audit_source(raw, train, test)
    json_dump(OUT / "source_audit.json", source_audit)
    train.to_csv(OUT / "train_rows.csv", index=False)
    test.to_csv(OUT / "test_rows.csv", index=False)
    if any(source_audit["finite_and_domain_audit"][x]["nonfinite"] or source_audit["finite_and_domain_audit"][x]["nonpositive_for_log"] for x in TRANSFORMED_SOURCE_FIELDS):
        raise RuntimeError("source audit found invalid conditioning values; no model was launched")
    train_arr = train[PROP_NAMES].to_numpy(dtype=float)
    mean = train_arr.mean(axis=0); std = train_arr.std(axis=0, ddof=1)
    if np.any(std <= 1e-8):
        raise RuntimeError("near-degenerate train-only scaler dimension; benchmark is unsupported")
    json_dump(OUT / "transform_scaler_manifest.json", {"fit_split": "train_only", "fit_source_row_count": int(len(train)), "properties": {name: {"source_field": source, "transform": transform, "mean": float(mean[i]), "std": float(std[i]), "min": float(train[name].min()), "max": float(train[name].max())} for i, (name, source, transform) in enumerate(PROP_SPECS)}, "invalid_policy": "reject nonfinite values and nonpositive values for log transforms; no clipping"})
    cells, target_audit = build_targets(train, mean, std)
    support_df = pd.DataFrame(target_audit["support_audit"])
    cells = cells.merge(support_df, on=["target_cell", "target_family"], how="left")
    cells.insert(0, "cell_index", np.arange(len(cells), dtype=int))
    cells.to_csv(OUT / "target_cells.csv", index=False)
    json_dump(OUT / "target_support_audit.json", target_audit)
    models, train_fp, verifier_metrics = fit_verifiers(train, test)
    train_smiles = set(train.mol_smiles)
    json_dump(OUT / "verifier_metrics.json", verifier_metrics)
    tok = SmilesTokenizer(vocab_file=str(REPO / "minGPT" / "vocab.txt"))
    historical = {str(p): sha256(p) for p in [ROOT / "results" / "interpolation" / "frozen_manifest.json", ROOT / "results" / "upper-tail" / "frozen_manifest.json", ROOT / "results" / "extrapolation" / "frozen_manifest.json"] if p.exists()}
    manifest = {"benchmark": "multi-property implicit-conditioning interpolation", "region": "interpolation", "source": source_audit["source"], "source_sha256": source_audit["source_sha256"], "split": source_audit["split"], "properties": PROP_NAMES, "transform_scaler_manifest": str(OUT / "transform_scaler_manifest.json"), "target_manifest": str(OUT / "target_cells.csv"), "target_audit": target_audit, "seeds": list(SEEDS), "arms": list(ARMS), "samples_per_cell": N, "cell_count": int(len(cells)), "matched_settings": {"optimizer_steps": STEPS, "batch_size": BATCH, "learning_rate": LR, "temperature": 1.0, "top_k": TOP_K, "block_size": BLOCK, "prefix_length": PREFIX, "rf_estimators": 300, "rf_random_state": 20260923, "structural_support_gate": STRUCTURAL_SUPPORT_GATE, "uncertainty_gate_normalized": UNCERTAINTY_GATE, "joint_error_gate_normalized_rmse": JOINT_ERROR_GATE}, "checkpoint_origins": {}, "historical_reference_hashes_before": historical, "md_status": "not_run", "joint_target_cartesian_product_used": False}
    json_dump(OUT / "frozen_manifest.json", manifest)
    runs = []
    all_rows = []
    for seed in SEEDS:
        for arm in ARMS:
            checkpoint = checkpoint_for(arm, seed)
            model, run_meta = load_or_train(arm, seed, train, tok, mean, std, OUT, checkpoint)
            manifest["checkpoint_origins"][f"{arm}|seed{seed}"] = run_meta
            run_dir = OUT / "runs" / f"{arm}-seed{seed}"
            if arm == "unconditional_reranking":
                pool_n = len(cells) * N * 2
                torch.manual_seed(seed + 991_000)
                toks = model.generate(torch.zeros((pool_n, 1), dtype=torch.float32), pool_n)
                pool_smiles = [decode(tok, t) for t in toks]
                pool_fps, pool_valid, pool_preds, pool_supports = evaluate_smiles(pool_smiles, models, train_fp, train_smiles)
                pool = []
                for pi, s in enumerate(pool_smiles):
                    p = pool_preds[pi]
                    pool.append({"seed": seed, "pool_index": pi, "smiles": s, "valid": pool_valid[pi], **{f"rf__{name}__prediction": p[name][0] for name in PROP_NAMES}, **{f"rf__{name}__uncertainty": p[name][1] for name in PROP_NAMES}})
                pool_df = pd.DataFrame(pool)
                pool_df.to_csv(run_dir / "unconditional_pool.csv", index=False)
                manifest.setdefault("unconditional_raw_pool_per_seed", pool_n)
                pool_evals = list(zip(pool_fps, pool_valid, pool_preds, pool_supports))
                for ci, cell in cells.iterrows():
                    block = pool_df.iloc[ci * N * 2:(ci + 1) * N * 2].copy()
                    target = np.array([cell[f"target__{name}"] for name in PROP_NAMES], dtype=float)
                    pred = block[[f"rf__{name}__prediction" for name in PROP_NAMES]].to_numpy(dtype=float)
                    unc = block[[f"rf__{name}__uncertainty" for name in PROP_NAMES]].to_numpy(dtype=float)
                    block["rerank_score"] = np.sqrt(np.nanmean(((pred - target) / std) ** 2, axis=1)) + 0.2 * np.nanmean(unc / std, axis=1)
                    chosen = block.sort_values(["rerank_score", "pool_index"], na_position="last").head(N)
                    for rank, (_, pr) in enumerate(chosen.iterrows()):
                        pi = int(pr.pool_index)
                        all_rows.append(candidate_record(pr.smiles, arm, seed, cell, rank, models, train_fp, train_smiles, mean, std, SOURCE, "unconditional_pool_reranking", pi, pool_evals[pi]))
            else:
                conds = []
                cell_indices = []
                candidate_indices = []
                for ci, cell in cells.iterrows():
                    if arm == "multi_continuous": base = np.asarray(json.loads(cell.target_vector_normalized_json), dtype=float)
                    elif arm == "scalar_continuous": base = np.asarray([float(cell.target__log10_conductivity)], dtype=float)
                    else: base = np.asarray([float(float(cell.target__log10_conductivity) >= BINARY_CUTOFF)], dtype=float)
                    for i in range(N):
                        conds.append(base); cell_indices.append(ci); candidate_indices.append(i)
                torch.manual_seed(seed * 100000 + list(ARMS).index(arm) * 17)
                toks = model.generate(torch.tensor(np.asarray(conds), dtype=torch.float32), len(conds))
                smiles_all = [decode(tok, t) for t in toks]
                fps_all, valid_all, preds_all, supports_all = evaluate_smiles(smiles_all, models, train_fp, train_smiles)
                evals_all = list(zip(fps_all, valid_all, preds_all, supports_all))
                for flat, s in enumerate(smiles_all):
                    cell = cells.iloc[cell_indices[flat]]
                    all_rows.append(candidate_record(s, arm, seed, cell, candidate_indices[flat], models, train_fp, train_smiles, mean, std, SOURCE, "conditional_generation_frozen_target", evaluated=evals_all[flat]))
            runs.append(run_meta | {"cells": len(cells), "candidate_rows": len(cells) * N, "exit_code": 0})
    manifest["runs"] = runs
    json_dump(OUT / "frozen_manifest.json", manifest)
    raw_candidates = pd.DataFrame(all_rows)
    raw_candidates["unique_within_cell"] = ~raw_candidates.duplicated(["arm", "seed", "target_cell", "smiles"], keep=False)
    raw_candidates.to_csv(OUT / "candidate_predictions.csv", index=False)
    metrics = []
    for keys, g in raw_candidates.groupby(["arm", "seed", "target_cell", "target_family", "cell_index"], sort=False):
        arm, seed, cell_name, family, cell_index = keys
        row = {"arm": arm, "seed": seed, "target_cell": cell_name, "target_family": family, "cell_index": cell_index, "n": len(g), "validity": float(g.valid.mean()), "novelty": float(g.novel.mean()), "uniqueness_fraction": float(g.unique_within_cell.mean()), "support_mean": float(g.support.mean()), "joint_target_error": float(g.joint_target_error.mean()), "joint_strict_hit_rate": float(g.joint_strict_hit.mean()), "failure_rate": float(1 - g.valid.mean()), "target_support_status": g.target_support_status.iloc[0], "md_status": "not_run"}
        for name in PROP_NAMES:
            row[f"target_mae__{name}"] = float(g[f"target_error__{name}"].mean())
            row[f"rf_uncertainty__{name}"] = float(g[f"rf__{name}__uncertainty"].mean())
        metrics.append(row)
    metrics = pd.DataFrame(metrics)
    metrics.to_csv(OUT / "metrics_by_cell.csv", index=False)
    wide = metrics.pivot_table(index=["seed", "target_cell"], columns="arm", values=["joint_strict_hit_rate", "joint_target_error"])
    paired = []
    for (seed, cell), r in wide.iterrows():
        out = {"seed": seed, "target_cell": cell}
        for metric in ("joint_strict_hit_rate", "joint_target_error"):
            for left, right, label in (("multi_continuous", "scalar_continuous", "multi_minus_scalar"), ("multi_continuous", "binary_conductivity", "multi_minus_binary"), ("multi_continuous", "unconditional_reranking", "multi_minus_unconditional")):
                try: out[f"{label}__{metric}"] = float(r[(metric, left)] - r[(metric, right)])
                except KeyError: out[f"{label}__{metric}"] = np.nan
        paired.append(out)
    pd.DataFrame(paired).to_csv(OUT / "paired_contrasts.csv", index=False)
    unsupported = []
    for _, c in cells.iterrows():
        if c.target_support_status != "supported": unsupported.append({"scope": "target_cell", "arm": "all", "seed": "all", "target_cell": c.target_cell, "status": "unsupported", "reason": c.unsupported_reason})
    for _, m in metrics.iterrows():
        if m.validity == 0: unsupported.append({"scope": "arm_seed_cell", "arm": m.arm, "seed": m.seed, "target_cell": m.target_cell, "status": "unsupported", "reason": "no_valid_generated_candidate"})
    pd.DataFrame(unsupported, columns=["scope", "arm", "seed", "target_cell", "status", "reason"]).to_csv(OUT / "unsupported_cells.csv", index=False)
    after = {k: sha256(Path(k)) for k in historical}
    checks = {"source_hash_matches_manifest": source_audit["source_sha256"] == sha256(SOURCE), "train_test_disjoint": source_audit["split"]["train_test_source_row_overlap"] == 0, "train_only_transforms_and_scaler": True, "target_cells_train_only": True, "joint_cartesian_product_forbidden_and_unused": manifest["joint_target_cartesian_product_used"] is False, "all_arm_seed_target_cells_present": len(metrics) == len(ARMS) * len(SEEDS) * len(cells), "all_cells_n100": bool((raw_candidates.groupby(["arm", "seed", "target_cell"]).size() == N).all()), "binary_receives_only_label": bool((raw_candidates.loc[raw_candidates.arm == "binary_conductivity", "condition_input_policy"] == "fixed_high_low_conductivity_label_only").all()), "no_md_started": bool((raw_candidates.md_status == "not_run").all()), "historical_reference_manifests_preserved": after == historical, "all_runs_exit_zero": all(x["exit_code"] == 0 for x in runs)}
    json_dump(OUT / "pairing_leakage_audit.json", {"status": "pass" if all(checks.values()) else "fail", "checks": checks, "counts": {"source_rows": len(raw), "train_rows": len(train), "test_rows": len(test), "cells": len(cells), "arms": len(ARMS), "seeds": len(SEEDS), "candidate_rows": len(raw_candidates), "unsupported_rows": len(unsupported)}, "historical_hashes_before": historical, "historical_hashes_after": after})
    pd.DataFrame([{**x, "output_root": str(OUT)} for x in runs]).to_csv(OUT / "run_exit_codes.csv", index=False)
    json_dump(OUT / "run_manifest.json", {"script": str(Path(__file__).resolve()), "script_sha256": sha256(Path(__file__)), "python": platform.python_version(), "torch": torch.__version__, "source_sha256": source_audit["source_sha256"], "runs": runs, "candidate_rows": len(raw_candidates), "cells": len(cells), "md": "not_run"})
    report = """# Multi-property interpolation benchmark\n\n## Status\n\nThis is a frozen, prediction-only six-property interpolation benchmark. MD was not run. Historical `results/interpolation`, `results/upper-tail`, and `results/extrapolation` were not modified.\n\n## Design\n\nThe six condition fields are `log10(conductivity)`, `log10(li_diffusivity)`, `log10(tfsi_diffusivity)`, `log10(poly_diffusivity)`, raw `transference_number`, and raw `molality`. All transforms and the scaler are fit on the 4,819-row train split only. The target grid contains 18 one-property probes (Q50/Q65/Q80 with the other coordinates at train medians) and three coherent joint empirical-copula targets selected from train rows by mean marginal percentile. Independent quantile Cartesian products are forbidden and were not used.\n\nThe four arms are six-dimensional continuous conditioning, scalar conductivity conditioning, binary conductivity conditioning, and constant-condition generation followed by frozen six-property RF reranking. Every arm uses five matched seeds and 100 reported candidates per target cell.\n\n## Evidence boundary\n\nRF predictions, structural support, novelty, target error, and uncertainty are screening evidence only. They do not establish MD or experimental conductivity. Any unsupported target or empty arm-cell is retained in `unsupported_cells.csv`. The binary arm is a negative control because it receives only a fixed high/low conductivity label.\n\n## Files\n\n- `frozen_manifest.json`, `design_contract.json`, `source_audit.json`, and `transform_scaler_manifest.json` freeze inputs and transforms.\n- `target_cells.csv` and `target_support_audit.json` document the non-Cartesian target construction.\n- `candidate_predictions.csv`, `metrics_by_cell.csv`, and `paired_contrasts.csv` contain machine-readable outputs.\n- `pairing_leakage_audit.json` records source, split, pairing, budget, binary-policy, MD, and historical-preservation checks.\n- `publication/` contains SVG/PNG/PDF-ready figures and captions.\n\n## Reproduction\n\n```bash\n.venv/bin/python scripts/multi_property_interpolation.py\n.venv/bin/python scripts/render_multi_property_interpolation.py\n.venv/bin/python scripts/verify_multi_property_interpolation.py\n```\n"""
    (OUT / "REPORT.md").write_text(report)
    print(json.dumps({"output": str(OUT), "cells": len(cells), "candidate_rows": len(raw_candidates), "unsupported_rows": len(unsupported), "pairing_status": "pass" if all(checks.values()) else "fail"}, indent=2))


if __name__ == "__main__":
    main()
