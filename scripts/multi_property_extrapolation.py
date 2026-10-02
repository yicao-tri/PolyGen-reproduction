#!/usr/bin/env python3
"""Freeze and audit the multi-property extrapolation benchmark.

This driver intentionally stops before model fitting when the released assets do
not contain a six-dimensional conditioner or a joint verifier.  It emits an
auditable, machine-readable blocker instead of silently substituting the scalar
conductivity pipeline.
"""
from __future__ import annotations

import csv, hashlib, json, platform, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/multi-property/extrapolation"
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
PROPS = ["conductivity", "li_diffusivity", "tfsi_diffusivity", "poly_diffusivity", "transference_number", "molality"]
LOG_PROPS = set(PROPS[:4])
ARMS = ["multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"]
TARGETS = ["Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50"]
SEEDS = [17, 42, 202, 303, 907]

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=True) + "\n")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SOURCE)
    audit = {"source": str(SOURCE), "source_sha256": sha256(SOURCE), "source_rows": len(df), "properties": {}}
    transformed = {}
    for c in PROPS:
        x = pd.to_numeric(df[c], errors="coerce")
        valid = np.isfinite(x.to_numpy())
        if c in LOG_PROPS: valid &= x.to_numpy() > 0
        z = np.log10(x) if c in LOG_PROPS else x
        transformed[c] = z
        audit["properties"][c] = {"finite": int(valid.sum()), "missing_or_invalid": int((~valid).sum()), "unique": int(x.nunique(dropna=True)), "min": float(z[valid].min()) if valid.any() else None, "max": float(z[valid].max()) if valid.any() else None, "q80": float(z[valid].quantile(.8)) if valid.any() else None, "q90": float(z[valid].quantile(.9)) if valid.any() else None, "q100": float(z[valid].max()) if valid.any() else None}
    valid_joint = np.ones(len(df), dtype=bool)
    for c in PROPS:
        x = transformed[c].to_numpy(); valid_joint &= np.isfinite(x)
    joint = df.loc[valid_joint].copy(); joint["source_row_id"] = np.flatnonzero(valid_joint)
    boundary = np.ones(len(joint), dtype=bool)
    for c in PROPS:
        z = transformed[c].loc[valid_joint].to_numpy()
        boundary &= z <= np.quantile(z, .8)
    train = joint.loc[boundary].copy(); locked = joint.loc[~boundary].copy()
    dump(OUT / "source_audit.json", {**audit, "joint_valid_rows": int(len(joint)), "joint_train_rows": int(len(train)), "joint_locked_rows": int(len(locked)), "joint_rule": "all six transformed properties <= their full-source Q80"})
    dump(OUT / "design_contract.json", {"question": "Does a jointly normalized six-property condition improve support-aware generation beyond a locked multi-property Q80 frontier?", "estimand": "paired seed-level multi_continuous minus scalar_continuous frontier-crossing rate", "arms": ARMS, "properties": PROPS, "targets": TARGETS, "seeds": SEEDS, "locked_row_policy": "locked rows are excluded from generator, surrogate, tuning, thresholds, filtering and selection", "interpretation_boundary": "prediction-only; no MD or experimental claim", "status": "frozen_with_blocker", "blocker": "released assets lack a six-dimensional conditioner, joint surrogate and joint support estimator"})
    train.to_csv(OUT / "train_rows.csv", index=False)
    locked.to_csv(OUT / "locked_tail_rows.csv", index=False)
    targets = []
    for label, q, offset in [("Q90", .9, None), ("Q100", 1.0, None), ("train_max_plus_0.25", None, .25), ("train_max_plus_0.50", None, .50)]:
        vals = {}
        for c in PROPS:
            z = transformed[c].loc[valid_joint]
            vals[c] = float(z.quantile(q)) if q is not None else float(transformed[c].loc[valid_joint & boundary].max() + offset)
        targets.append({"label": label, "values_transformed": vals, "joint_support_status": "unsupported_no_released_joint_support_model"})
    manifest = {"benchmark":"multi-property true extrapolation", "status":"blocked_before_fitting", "source":str(SOURCE), "source_sha256":sha256(SOURCE), "source_rows":len(df), "joint_valid_rows":int(len(joint)), "joint_train_rows":int(len(train)), "joint_locked_rows":int(len(locked)), "properties":PROPS, "log_transformed_properties":sorted(LOG_PROPS), "training_rule":"all six transformed properties <= their full-source Q80", "targets":targets, "arms":ARMS, "seeds":SEEDS, "samples_per_target_cell":100, "locked_row_policy":"locked rows are audit-only and excluded from generator, surrogate, tuning, thresholds, filtering, and selection", "historical_results_preserved":True}
    dump(OUT / "frozen_manifest.json", manifest)
    rows=[]
    for arm in ARMS:
        for seed in SEEDS:
            for t in TARGETS:
                rows.append({"arm":arm,"seed":seed,"target_label":t,"status":"unsupported","reason":"missing_released_multi_property_pipeline_and_joint_surrogate"})
    pd.DataFrame(rows).to_csv(OUT / "unsupported_cells.csv", index=False)
    pd.DataFrame([{**r, "metric":"all", "value":np.nan} for r in rows]).to_csv(OUT / "metrics_by_cell.csv", index=False)
    pd.DataFrame(columns=["arm","seed","candidate_id","structure","target_label","reason"]).to_csv(OUT / "candidate_predictions.csv", index=False)
    pd.DataFrame(columns=["arm","seed","target_label","candidate_id","selection_status","reason"]).to_csv(OUT / "candidate_selection_for_md.csv", index=False)
    pd.DataFrame([{"check":"locked_rows_excluded_from_fit_and_selection","status":"not_run_no_fit_started"},{"check":"all_arm_budgets_matched","status":"unsupported"},{"check":"joint_targets_supported","status":"unsupported"}]).to_csv(OUT / "locked_row_audit.csv", index=False)
    dump(OUT / "pairing_acceptance_audit.json", {"status":"blocked","paired_claims_allowed":False,"reason":"No multi-property run was launched; all cells are explicit unsupported.","arms":ARMS,"seeds":SEEDS})
    dump(OUT / "region_summary.json", {"status":"blocked_before_fitting","supported_cells":0,"unsupported_cells":len(rows),"joint_valid_rows":len(joint),"joint_train_rows":len(train),"joint_locked_rows":len(locked)})
    dump(OUT / "run_manifest.json", {"status":"not_launched","reason":"required multi-property conditioner and joint surrogate are absent","python":sys.version,"platform":platform.platform()})
    pd.DataFrame([{"arm":a,"exit_code":"not_launched","reason":"unsupported prerequisite"} for a in ARMS]).to_csv(OUT / "run_exit_codes.csv", index=False)
    pd.DataFrame([{"failure_reason":"missing_released_multi_property_pipeline_and_joint_surrogate","count":len(rows)}]).to_csv(OUT / "failure_reasons.csv", index=False)
    (OUT / "REPORT.md").write_text("""# Multi-property true extrapolation\n\n## Status\n\nBlocked before fitting. The released repository contains scalar conductivity generation and scalar RF verification artifacts, but no six-dimensional conditioning interface, joint property surrogate, or joint support estimator. The scalar pipeline was not substituted because doing so would violate the benchmark contract.\n\nThe frozen manifest, transformed-property audit, train/locked row split, and explicit unsupported cells are complete. All locked rows are audit-only; no generator, surrogate, tuning, threshold, filter, or candidate-selection step used them. No candidates were generated, no MD was started, and no extrapolation claim is supported.\n\nSee `unsupported_cells.csv`, `frozen_manifest.json`, and `locked_row_audit.csv`. Historical single-property result roots were not modified.\n""")

if __name__ == "__main__": main()
