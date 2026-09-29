#!/usr/bin/env python3
"""Pre-MD benchmark for Full-RF upper-tail candidates and analogues."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/upper-tail"
FULL = BASE / "full-rf-audit"
OUT = FULL / "pre-md-benchmark"
OUT.mkdir(parents=True, exist_ok=True)
RDLogger.DisableLog("rdApp.warning")
RDLogger.DisableLog("rdApp.error")

def fp(smiles):
    mol = Chem.MolFromSmiles(smiles.replace("[Cu]", "[*]").replace("[Au]", "[*]"))
    return None if mol is None else AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

def similarity(query, refs):
    return np.asarray([DataStructs.TanimotoSimilarity(query, r) for r in refs], dtype=float)

def neighbor_record(query_smiles, frame, fps, prefix):
    q = fp(query_smiles)
    if q is None:
        return {f"{prefix}_top5_mean_similarity": np.nan, f"{prefix}_top5_max_similarity": np.nan,
                f"{prefix}_top5_mean_log_sigma": np.nan, f"{prefix}_top5_max_log_sigma": np.nan,
                f"{prefix}_top5_ids": ""}
    sims = similarity(q, fps)
    order = np.argsort(-sims)[:5]
    return {
        f"{prefix}_top5_mean_similarity": float(sims[order].mean()),
        f"{prefix}_top5_max_similarity": float(sims[order].max()),
        f"{prefix}_top5_mean_log_sigma": float(frame.iloc[order].log_sigma.mean()),
        f"{prefix}_top5_max_log_sigma": float(frame.iloc[order].log_sigma.max()),
        f"{prefix}_top5_ids": ";".join(str(int(frame.iloc[i].source_row_id)) for i in order),
    }

def main():
    source = pd.read_csv(ROOT / "inputs/release-data/htpmd-trainset.csv")[["mol_smiles", "conductivity"]].copy()
    source["log_sigma"] = np.log10(source.conductivity)
    source["source_row_id"] = np.arange(len(source))
    q80 = float(source.log_sigma.quantile(0.80))
    boundary = float(source[source.log_sigma <= q80].log_sigma.max())
    train = source[source.log_sigma <= q80].reset_index(drop=True)
    tail = source[(source.log_sigma > q80) & (source.log_sigma <= source.log_sigma.quantile(0.95))].reset_index(drop=True)
    train_fps = [fp(s) for s in train.mol_smiles]
    tail_fps = [fp(s) for s in tail.mol_smiles]
    candidates = pd.read_csv(FULL / "fullrf_candidate_predictions.csv")
    candidates["pre_md_selected"] = (
        (candidates.arm == "continuous") & candidates.fullrf_valid & candidates.fullrf_novel_vs_train &
        (candidates.fullrf_prediction > boundary) & candidates.fullrf_support_eligible &
        candidates.fullrf_uncertainty_eligible
    )
    selected = candidates[candidates.pre_md_selected].copy()
    rows = []
    for _, row in selected.iterrows():
        rec = row.to_dict()
        rec.update(neighbor_record(row.smiles, train, train_fps, "train"))
        rec.update(neighbor_record(row.smiles, tail, tail_fps, "locked_tail_posthoc"))
        rec["fullrf_minus_train_top5_mean"] = row.fullrf_prediction - rec["train_top5_mean_log_sigma"]
        rec["fullrf_minus_tail_top5_mean_posthoc"] = row.fullrf_prediction - rec["locked_tail_posthoc_top5_mean_log_sigma"]
        rec["screening_score"] = row.fullrf_prediction - 1.96 * row.fullrf_uncertainty + 0.10 * row.fullrf_support
        rows.append(rec)
    selected = pd.DataFrame(rows)
    if not selected.empty:
        selected = selected.sort_values(["screening_score", "fullrf_prediction"], ascending=False)
    selected.to_csv(OUT / "continuous_predicted_upper_tail_candidates.csv", index=False)
    top = selected.head(20) if not selected.empty else selected
    top.to_csv(OUT / "continuous_top20_for_md.csv", index=False)

    all_valid = candidates[candidates.fullrf_valid & candidates.fullrf_novel_vs_train].copy()
    summary = {
        "status": "complete_pre_md_benchmark",
        "boundary": boundary,
        "candidate_rows": int(len(candidates)),
        "fullrf_valid_novel_candidates": int(len(all_valid)),
        "continuous_fullrf_predicted_upper_tail_candidates": int(len(selected)),
        "continuous_fullrf_predicted_upper_tail_fraction": float(len(selected) / len(candidates[candidates.arm == "continuous"])) if (candidates.arm == "continuous").any() else 0.0,
        "max_fullrf_prediction_selected": float(selected.fullrf_prediction.max()) if not selected.empty else None,
        "max_fullrf_prediction_all_continuous": float(candidates.loc[candidates.arm == "continuous", "fullrf_prediction"].max()),
        "max_screening_score_selected": float(selected.screening_score.max()) if not selected.empty else None,
        "benchmark_warning": "locked_tail nearest-neighbor values are posthoc descriptive only and were not used for selection",
        "primary_analog_reference": "Q80 training rows only",
        "md_comparison_unit": "generated candidate paired with its train-top5 analog set and later MD measurement",
    }
    (OUT / "benchmark_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
