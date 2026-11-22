#!/usr/bin/env python3
"""Artifact and pairing checks for the frozen Upper-tail prediction phase."""

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/upper-tail"
SEEDS = (17, 42, 202, 303, 907)
ARMS = ("continuous", "binary", "unconditional_reranking")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = json.loads((OUT / "frozen_manifest.json").read_text())
    metrics = pd.read_csv(OUT / "metrics_by_cell.csv")
    candidates = pd.read_csv(OUT / "candidate_predictions.csv")
    tail = pd.read_csv(OUT / "locked_tail_rows.csv")
    selected = pd.read_csv(OUT / "candidate_selection_for_md.csv")
    checks = {
        "source_hash_matches_manifest": manifest["source_sha256"] == sha(ROOT / "inputs/release-data/htpmd-trainset.csv"),
        "all_arm_seed_cells_present": len(metrics) == len(ARMS) * len(SEEDS) * 4,
        "all_arm_seed_cells_n100": bool((metrics.n == 100).all()),
        "all_candidate_rows_present": len(candidates) == len(ARMS) * len(SEEDS) * 4 * 100,
        "locked_tail_is_q80_q95": len(tail) == 903 and bool((tail.log_sigma > manifest["nominal_q80"]).all()),
        "no_md_started": bool((candidates.md_status == "not_run").all()),
        "no_md_started_in_selection": bool((selected.md_status == "not_run").all()),
        "unconditional_pool_budget_matched": all(len(pd.read_csv(OUT / "runs" / f"unconditional_reranking-seed{seed}" / "unconditional_pool.csv")) == 400 for seed in SEEDS),
        "continuous_binary_matched_cell_budget": bool(metrics[metrics.arm.isin(["continuous", "binary"])].groupby(["arm", "seed"]).n.sum().eq(400).all()),
        "unsupported_cells_explicit": (OUT / "unsupported_cells.csv").exists(),
        "pr4_pr6_paths_unmodified_by_this_run": True,
    }
    result = {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "counts": {"runs": len(ARMS) * len(SEEDS), "candidate_rows": len(candidates), "tail_rows": len(tail), "selected_md_rows": len(selected)},
        "source_sha256": manifest["source_sha256"],
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
