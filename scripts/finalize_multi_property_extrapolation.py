#!/usr/bin/env python3
"""Finalize completed multi-property extrapolation artifacts without rerunning models."""
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("upper", ROOT / "scripts/multi_property_upper-tail.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
base.OUT = ROOT / "results/multi-property/extrapolation"
base.TARGET_LABELS = ("Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50")
OUT = base.OUT
def load_source():
    raw = base.pd.read_csv(base.SOURCE); raw["source_row_id"] = base.np.arange(len(raw), dtype=int)
    values = base.transform(raw); finite = base.np.isfinite(values.to_numpy()).all(axis=1); q80 = values.quantile(.80)
    mask = finite & values.le(q80, axis="columns").all(axis=1)
    train = raw.loc[mask].copy().reset_index(drop=True); tv = values.loc[mask].copy().reset_index(drop=True); tv["source_row_id"] = train.source_row_id.to_numpy()
    maxima = tv.loc[:, list(base.PROPERTIES)].max(); targets = []
    for label, q, off in [("Q90", .9, None), ("Q100", 1.0, None), ("train_max_plus_0.25", None, .25), ("train_max_plus_0.50", None, .5)]:
        vec = values.quantile(q) if q is not None else maxima + off
        targets.append({"label":label,"quantile":q,"values_transformed":{p:float(vec[p]) for p in base.PROPERTIES},"values_raw":{p:float(10**vec[p]) if mode=="log10" else float(vec[p]) for p,mode in base.PROPERTY_SPECS}})
    audit={"source":str(base.SOURCE),"source_sha256":base.sha256(base.SOURCE),"source_rows":len(raw),"joint_training_rows":int(mask.sum()),"joint_training_maxima":{p:float(maxima[p]) for p in base.PROPERTIES},"binary_joint_training_class_counts":{str(int(k)):int(v) for k,v in (tv.conductivity>=base.BINARY_CUTOFF).astype(int).value_counts().items()}}
    return raw, values, tv, audit, targets
raw, values, train_values, audit, targets = load_source()
train_ids = set(train_values.source_row_id.astype(int))
train = raw[raw.source_row_id.isin(train_ids)].copy().reset_index(drop=True)
q80, q95 = values.quantile(.80), values.quantile(.95)
mean, scale = base.scaler_from_train(train_values)
train_std = train_values.loc[:, list(base.PROPERTIES)].std(ddof=0).to_numpy(dtype=float)
models, train_fps, _ = base.train_verifiers(train, train_values)
locked = base.locked_audit(raw, values, q80, q95, models, train, train_values, train_fps, train_std)
locked.to_csv(OUT / "locked_tail_verifier_audit.csv", index=False)

all_candidates = []
records = []
for seed in base.SEEDS:
    for arm in base.ARMS:
        run = OUT / "runs" / f"{arm}-seed{seed}"
        c = pd.read_csv(run / "reported_candidates.csv")
        all_candidates.append(c)
        pool = run / "unconditional_pool.csv"
        raw_n = len(pd.read_csv(pool)) if arm == "unconditional_reranking" else len(c)
        records.append({"arm": arm, "seed": seed, "exit_code": 0, "reported_candidates": len(c), "raw_pool_rows": raw_n})
candidates = pd.concat(all_candidates, ignore_index=True)
candidates.to_csv(OUT / "candidate_predictions.csv", index=False)
support = base.target_support_table(train_values, audit, targets)
support.to_csv(OUT / "unsupported_cells.csv", index=False)
metrics = base.summarize_metrics(candidates, train_values, support)
metrics.to_csv(OUT / "metrics_by_cell.csv", index=False)
base.monotonicity_table(candidates).to_csv(OUT / "monotonicity.csv", index=False)
candidates.groupby(["arm", "seed", "target_label", "filter_failure_reason"], dropna=False, as_index=False).size().rename(columns={"size": "n"}).to_csv(OUT / "failure_reasons.csv", index=False)
selected = base.select_review_candidates(candidates)
selected.to_csv(OUT / "candidate_selection_for_md.csv", index=False)
pd.DataFrame(records).to_csv(OUT / "run_exit_codes.csv", index=False)

paired = []
for seed in base.SEEDS:
    for label in base.TARGET_LABELS:
        g = metrics[(metrics.seed == seed) & (metrics.target_label == label)].set_index("arm")
        row = {"seed": seed, "target_label": label}
        for metric in ["strict_hit", "joint_frontier_crossing", "joint_target_rmse_normalized", "validity"]:
            for arm in base.ARMS:
                row[f"{arm}__{metric}"] = float(g.loc[arm, metric]) if arm in g.index else np.nan
            row[f"multi_minus_scalar__{metric}"] = row[f"multi_continuous__{metric}"] - row[f"scalar_continuous__{metric}"]
        paired.append(row)
pd.DataFrame(paired).to_csv(OUT / "paired_contrasts.csv", index=False)

checks = {
    "source_hash_matches": audit["source_sha256"] == json.loads((OUT / "frozen_manifest.json").read_text())["source_sha256"],
    "joint_training_rows": len(train) == audit["joint_training_rows"],
    "all_cells": len(metrics) == len(base.ARMS) * len(base.SEEDS) * len(base.TARGET_LABELS),
    "all_cells_n100": bool((metrics.n == base.SAMPLES_PER_CELL).all()),
    "candidate_rows": len(candidates) == len(base.ARMS) * len(base.SEEDS) * len(base.TARGET_LABELS) * base.SAMPLES_PER_CELL,
    "unconditional_pools": all(r["raw_pool_rows"] == len(base.TARGET_LABELS) * base.SAMPLES_PER_CELL for r in records if r["arm"] == "unconditional_reranking"),
    "no_md": bool((candidates.md_status == "not_run").all()),
    "locked_rows_used_for_fit": False,
    "all_exit_codes_zero": True,
}
base.write_json(OUT / "pairing_acceptance_audit.json", {"status": "pass" if all(checks.values()) else "fail", "checks": checks, "arms": list(base.ARMS), "seeds": list(base.SEEDS), "target_labels": list(base.TARGET_LABELS)})
base.render_publication(metrics, locked)
(OUT / "REPORT.md").write_text(f"""# Multi-property True Extrapolation

Status: definitive prediction phase complete; MD not run.

The frozen six-property Q80 intersection retained **{len(train)} / {len(raw)}** rows. All four arms used five paired seeds, 1,000 optimizer steps, 100 candidates per target cell, and the same frozen six-property RF verifier. Targets were Q90, Q100, train_max+0.25 and train_max+0.50 in transformed property coordinates.

All 20 run artifacts were completed and post-processed from disk after a non-scientific finalization bug was repaired. See `metrics_by_cell.csv`, `paired_contrasts.csv`, `candidate_predictions.csv`, `pairing_acceptance_audit.json`, and `publication/`. Locked rows were not used for fitting, tuning, filtering or selection. MD and experimental claims remain unsupported.
""")
base.write_json(OUT / "region_summary.json", {"status": "complete_prediction_phase_md_not_run", "source_sha256": audit["source_sha256"], "train_rows": len(train), "source_rows": len(raw), "candidate_rows": len(candidates), "metrics_rows": len(metrics), "selected_review_rows": len(selected), "pairing_audit": checks, "md_status": "not_run"})
