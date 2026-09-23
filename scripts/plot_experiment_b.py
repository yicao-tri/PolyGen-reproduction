#!/usr/bin/env python3
"""Render standalone Experiment B panels using the user's Plot Atlas style."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ATLAS = Path("/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library")
sys.path.insert(0, str(ATLAS / "src"))
from plot_atlas import apply_publication_style, get_palette, joint_scatter, save_figure  # noqa: E402


def calibration_panel(tables: Path, figures: Path) -> None:
    data = pd.read_csv(tables / "cv_predictions.csv")
    palette = get_palette("agro_joint")
    apply_publication_style(9.5)
    fig = plt.figure(figsize=(5.8, 5.3))
    gs = fig.add_gridspec(1, 1)
    result = joint_scatter(
        fig, gs[0], data["observed_log10_S_cm"], data["predicted_log10_S_cm"], palette,
        color_values=np.abs(data["observed_log10_S_cm"] - data["predicted_log10_S_cm"]),
        regression=False, marginal="hist", marginal_axes=True, annotate=False,
        xlabel="Observed log$_{10}$ conductivity (S cm$^{-1}$)",
        ylabel="Group-held-out prediction",
        point_size=18, alpha=.62, axis_linewidth=1.35, tick_width=1.25,
    )
    ax = result["main"]
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0]); hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], ls=(0, (4, 3)), lw=1.2, color="#343A40", zorder=2)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.text(.04, .95, "5-fold CV; groups = salt + molality", transform=ax.transAxes, va="top", fontsize=9)
    fig.subplots_adjust(left=.17, right=.95, bottom=.14, top=.95)
    for suffix in ("png", "svg"):
        save_figure(fig, figures / f"experiment_b_cv_calibration.{suffix}")
    plt.close(fig)


def robust_curve_panel(tables: Path, figures: Path) -> None:
    pred = pd.read_csv(tables / "candidate_predictions.csv")
    ranks = pd.read_csv(tables / "robust_rankings.csv").head(5)
    palette = get_palette("isotope_sites")["categorical"]
    apply_publication_style(9.5)
    fig, ax = plt.subplots(figsize=(6.1, 4.4))
    for index, row in ranks.iterrows():
        group = pred[pred["formulation_id"] == row["formulation_id"]].sort_values("temperature_K")
        x = group["temperature_K"]
        mean = group["predicted_mean_log10_S_cm"]
        lcb = group["predicted_lcb05_log10_S_cm"]
        color = palette[index % len(palette)]
        ax.plot(x, mean, marker="o", ms=4.5, lw=1.8, color=color, label=f"{row['salt_shortname']} {row['molality']:.2f} m")
        ax.fill_between(x, lcb, mean, color=color, alpha=.13, linewidth=0)
    ax.set_xlabel("Temperature (K)")
    ax.set_ylabel("Predicted log$_{10}$ conductivity (S cm$^{-1}$)")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    for spine in ax.spines.values(): spine.set_linewidth(1.35)
    ax.tick_params(width=1.25, length=4)
    ax.text(.02, .97, "Line: bootstrap mean   Band: mean to 5th percentile", transform=ax.transAxes, va="top", fontsize=8.5)
    fig.tight_layout()
    for suffix in ("png", "svg"):
        save_figure(fig, figures / f"experiment_b_top5_temperature_robustness.{suffix}")
    plt.close(fig)


if __name__ == "__main__":
    tables = ROOT / "results/experiment-b/tables"
    figures = ROOT / "results/experiment-b/figures"
    figures.mkdir(parents=True, exist_ok=True)
    calibration_panel(tables, figures)
    robust_curve_panel(tables, figures)
