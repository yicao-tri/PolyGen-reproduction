#!/usr/bin/env python3
"""Render the real five-seed MolMiner smoke-vs-extended comparison.

The panel uses the Plot Atlas grouped-bar-with-points grammar: bars are means
over training seeds, error bars are SEM, and open points preserve the five
seed-level observations.  Both arms use the same 150-request C1 generation
budget and frozen verifier policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plot_atlas import apply_publication_style, get_palette, grouped_bar_with_points


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evidence/experiments/molminer_strict_c1"


def sem(values):
    values = np.asarray(values, dtype=float)
    return float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else np.nan


def summarize(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = (
        frame.groupby("training_seed", as_index=False)
        .agg(
            valid_rate=("repeat_unit_validity", "mean"),
            strict_hit_rate=("strict_hit_rate", "mean"),
            target_mae_valid=("target_mae_valid", "mean"),
        )
        .rename(columns={
            "valid_rate": f"{prefix}_valid_rate",
            "strict_hit_rate": f"{prefix}_strict_hit_rate",
            "target_mae_valid": f"{prefix}_target_mae_valid",
        })
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extended-epochs", type=int, default=20)
    ap.add_argument("--output-stem", type=Path)
    ap.add_argument("--table", type=Path)
    args = ap.parse_args()

    label = f"extended{args.extended_epochs}"
    if args.output_stem is None:
        args.output_stem = ROOT / f"assets/figures/S1_molminer_{label}_vs_smoke"
    if args.table is None:
        args.table = ROOT / f"assets/tables/T13_molminer_{label}_vs_smoke.csv"

    smoke = pd.read_csv(BASE / "five_seed_generation_smoke/aggregate_metrics_by_training_seed_target.csv")
    extended = pd.read_csv(BASE / f"extended_{args.extended_epochs}epoch_generation/metrics_by_training_seed_target.csv")
    merged = summarize(smoke, "smoke").merge(summarize(extended, "extended"), on="training_seed", how="outer")
    merged["delta_valid_rate"] = merged["extended_valid_rate"] - merged["smoke_valid_rate"]
    merged["delta_strict_hit_rate"] = merged["extended_strict_hit_rate"] - merged["smoke_strict_hit_rate"]
    merged["delta_target_mae_valid"] = merged["extended_target_mae_valid"] - merged["smoke_target_mae_valid"]
    merged["generation_budget"] = "150 requests; 3 targets; 10 samples/target/seed"
    merged["evidence_status"] = "observed_engineering_comparison"
    merged.to_csv(args.table, index=False)

    categories = ["Valid repeat-unit rate", "Strict-hit rate"]
    smoke_values = [merged.smoke_valid_rate.to_numpy(), merged.smoke_strict_hit_rate.to_numpy()]
    extended_values = [merged.extended_valid_rate.to_numpy(), merged.extended_strict_hit_rate.to_numpy()]
    matrix = np.array([
        [merged.smoke_valid_rate.mean(), merged.extended_valid_rate.mean()],
        [merged.smoke_strict_hit_rate.mean(), merged.extended_strict_hit_rate.mean()],
    ])
    errors = np.array([
        [sem(merged.smoke_valid_rate), sem(merged.extended_valid_rate)],
        [sem(merged.smoke_strict_hit_rate), sem(merged.extended_strict_hit_rate)],
    ])
    points = [smoke_values, extended_values]

    apply_publication_style(font_size=9)
    palette = get_palette("paired_teal_orange")
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    grouped_bar_with_points(
        ax,
        categories,
        matrix,
        ["5-epoch smoke", f"{args.extended_epochs}-epoch extended"],
        palette["categorical"][:2],
        errors=errors,
        points=points,
        ylabel="Rate",
        legend=True,
        ylim=(0, 1.0),
    )
    legend = ax.get_legend()
    if legend is not None:
        legend.set_title(None)
    ax.set_xlabel("C1 generation outcome")
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_yticklabels([f"{x:.1f}" for x in np.linspace(0, 1, 6)])
    fig.text(
        0.5,
        0.035,
        "n=5 training seeds; bars=mean ± SEM; open points=seed-level values",
        ha="center",
        va="bottom",
        fontsize=7,
        color="#666666",
    )
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.26, top=0.96)
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(args.output_stem.with_suffix(f".{ext}"), dpi=300, facecolor="white")
    plt.close(fig)
    print(merged.to_string(index=False))


if __name__ == "__main__":
    main()
