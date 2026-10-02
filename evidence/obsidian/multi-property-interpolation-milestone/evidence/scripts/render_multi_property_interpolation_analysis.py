#!/usr/bin/env python3
"""Render the derived paired-effect and failure-audit figure."""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from publication_plot_style import apply_style, save_publication_figure


ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results" / "multi-property" / "interpolation" / "analysis"
OUT = ROOT / "results" / "multi-property" / "interpolation" / "publication"
ARMS = ["multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"]
LABELS = {"multi_continuous": "Multi-property", "scalar_continuous": "Scalar", "binary_conductivity": "Binary", "unconditional_reranking": "Uncond. + rerank"}
COLORS = {"multi_continuous": "#007C83", "scalar_continuous": "#4477AA", "binary_conductivity": "#D95F02", "unconditional_reranking": "#6B6B6B"}


def panel_heading(ax, label: str, text: str) -> None:
    """Separate the panel index from the subtitle for clean reading."""
    ax.text(-0.13, 1.035, label, transform=ax.transAxes, ha="right", va="bottom", fontsize=10, fontweight="bold", clip_on=False)
    ax.set_title(text, loc="left", fontsize=10, fontweight="bold", pad=16)


def main() -> None:
    apply_style()
    summary = pd.read_csv(IN / "arm_summary.csv")
    paired = pd.read_csv(IN / "paired_summary.csv")
    mono = pd.read_csv(IN / "property_monotonicity_summary.csv")
    cell = pd.read_csv(IN / "cell_quality_and_control.csv")

    fig, axes = plt.subplots(2, 2, figsize=(10.4, 7.2))
    ax = axes[0, 0]
    metrics = ["joint_target_rmse", "validity", "novelty", "support_mean"]
    labels = ["Joint RMSE", "Validity", "Novelty", "Support"]
    x = np.arange(len(metrics))
    width = 0.19
    for i, arm in enumerate(ARMS):
        g = summary[(summary.arm == arm) & summary.metric.isin(metrics)].set_index("metric").reindex(metrics)
        ax.bar(x + (i - 1.5) * width, g["mean"], width, yerr=[g["mean"] - g["ci95_low"], g["ci95_high"] - g["mean"]], capsize=2, color=COLORS[arm], label=LABELS[arm], linewidth=0.4, edgecolor="white")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Mean across target cells")
    panel_heading(ax, "A", "Absolute performance and quality")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    ax = axes[0, 1]
    contrast = "multi_continuous_minus_scalar_continuous"
    wanted = ["joint_target_rmse", "validity", "novelty", "support_mean", "diversity_mean_1_minus_tanimoto", "rf_uncertainty_mean"]
    short = ["Joint RMSE", "Validity", "Novelty", "Support", "Diversity", "RF uncertainty"]
    g = paired[(paired.contrast == contrast) & paired.metric.isin(wanted)].set_index("metric").reindex(wanted)
    y = np.arange(len(wanted))
    ax.errorbar(g["mean_difference"], y, xerr=[g["mean_difference"] - g["ci95_low"], g["ci95_high"] - g["mean_difference"]], fmt="o", color="#007C83", ecolor="#007C83", capsize=3, lw=1.4)
    ax.axvline(0, color="#333333", lw=0.9)
    ax.set_yticks(y, short)
    ax.set_xlabel("Multi-property − scalar")
    panel_heading(ax, "B", "Matched seed contrasts")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    ax = axes[1, 0]
    sub = mono[mono.arm.isin(["multi_continuous", "scalar_continuous"])].pivot(index="property", columns="arm", values="monotonic_fraction").reindex(columns=["multi_continuous", "scalar_continuous"])
    prop_labels = ["Conductivity", "Li D", "TFSI D", "Poly D", "Transference", "Molality"]
    sub.index = prop_labels
    im = ax.imshow(sub.to_numpy(), vmin=0, vmax=1, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(2), ["Multi-property", "Scalar"])
    ax.set_yticks(range(6), prop_labels)
    for i in range(sub.shape[0]):
        for j in range(sub.shape[1]):
            ax.text(j, i, f"{sub.iloc[i, j]:.2f}", ha="center", va="center", fontsize=9, color="white" if sub.iloc[i, j] > .55 else "#222")
    panel_heading(ax, "C", "Q50→Q65→Q80 monotonicity")
    ax.set_xlabel("Fraction of five seeds")
    ax.spines[:].set_visible(False)

    ax = axes[1, 1]
    rows = []
    for arm in ARMS:
        g = cell[cell.arm == arm]
        rows.append({"arm": arm, "Invalid": 1 - g.validity.mean(), "Not novel": g.not_novel_rate.mean(), "Low support": g.low_support_rate.mean(), "High uncertainty": g.high_uncertainty_rate.mean()})
    fail = pd.DataFrame(rows).set_index("arm")
    cats = ["Invalid", "Not novel", "Low support", "High uncertainty"]
    x = np.arange(len(cats)); w = .19
    for i, arm in enumerate(ARMS):
        ax.bar(x + (i - 1.5) * w, fail.loc[arm, cats], w, label=LABELS[arm], color=COLORS[arm])
    ax.set_xticks(x, cats, rotation=18, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fraction of 21 cells")
    panel_heading(ax, "D", "Candidate failure modes")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    handles = [Patch(facecolor=COLORS[arm], edgecolor="none", label=LABELS[arm]) for arm in ARMS]
    fig.legend(handles=handles, frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, .985), ncol=4, handlelength=1.8, columnspacing=1.2)
    fig.subplots_adjust(left=.12, right=.98, bottom=.10, top=.82, wspace=.38, hspace=.52)
    save_publication_figure(fig, OUT, "Figure_4_paired_quality_audit")

    (OUT / "Figure_4_caption.md").write_text("""**Figure 4 | Paired quality audit for six-dimensional interpolation.** (A) Mean joint RMSE, validity, novelty, and structural support across the 21 target cells; bars show means across five seeds and whiskers show two-sided 95% Student-t intervals over seed-level means. (B) Matched seed contrasts for multi-property versus scalar conditioning; points and whiskers show the mean difference and 95% Student-t interval, with positive values favoring the multi-property arm only for quality metrics and negative values favoring it for error. (C) Fraction of seeds for which the cell-mean RF prediction is non-decreasing across the Q50/Q65/Q80 probe sequence for each property. Candidate-wise monotonicity is not identifiable because target cells do not share structure identities. (D) Descriptive failure-mode fractions from the full 100-candidate cell tables; failure categories are on the x-axis, arm colors are shared with panel A, and categories can overlap. All quantities are surrogate-screening diagnostics, not MD or experimental evidence.""")


if __name__ == "__main__":
    main()
