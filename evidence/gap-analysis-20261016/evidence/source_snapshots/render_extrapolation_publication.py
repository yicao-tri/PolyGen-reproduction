#!/usr/bin/env python3
"""Render publication-style extrapolation figures from frozen CSV outputs."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from publication_plot_style import apply_style, save_publication_figure, shared_legend, response_layout, heatmap_layout

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/extrapolation"
OUT = IN / "publication"
ARMS = ["continuous", "binary", "unconditional_reranking"]
COLORS = {"continuous": "#007C83", "binary": "#D55F02", "unconditional_reranking": "#6B6B6B"}
LABELS = {"continuous": "Continuous", "binary": "Binary", "unconditional_reranking": "Unconditional + reranking"}
SHORT = {"continuous": "Continuous", "binary": "Binary", "unconditional_reranking": "Uncond. + rerank"}
TARGETS = ["Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50"]
TARGET_SHORT = {"Q90": "Q90", "Q100": "Q100", "train_max_plus_0.25": "+0.25", "train_max_plus_0.50": "+0.50"}


def sem(values):
    values = pd.Series(values).dropna()
    return values.std(ddof=1) / np.sqrt(len(values)) if len(values) > 1 else np.nan


def aggregate(metrics):
    rows = []
    for (arm, label), group in metrics.groupby(["arm", "target_label"], sort=False):
        row = {"arm": arm, "target_label": label, "target": float(group.target.iloc[0]), "n_seeds": int(len(group))}
        for col in ["validity", "target_mae", "rf_prediction_mean", "rf_uncertainty_mean", "support_mean", "failure_rate", "frontier_crossing_predicted_hit_rate", "strict_hit_rate"]:
            row[col] = group[col].mean()
            row[col + "_sem"] = sem(group[col])
        rows.append(row)
    return pd.DataFrame(rows)


def save(fig, name):
    save_publication_figure(fig, OUT, name)


def main():
    apply_style()
    OUT.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(IN / "metrics_by_cell.csv")
    candidates = pd.read_csv(IN / "candidate_predictions.csv")
    tail = pd.read_csv(IN / "locked_tail_verifier_audit.csv")
    manifest = json.loads((IN / "frozen_manifest.json").read_text())
    agg = aggregate(metrics)
    agg.to_csv(OUT / "extrapolation_aggregate_metrics.csv", index=False)

    # Figure 1: absolute target response, target error, and surrogate frontier crossings.
    fig, axes = plt.subplots(1, 3, figsize=(8.1, 3.05), gridspec_kw={"wspace": 0.58})
    x = np.arange(len(TARGETS))
    for arm in ARMS:
        a = agg[agg.arm == arm].set_index("target_label").reindex(TARGETS)
        axes[0].errorbar(x, a.rf_prediction_mean, yerr=a.rf_prediction_mean_sem, color=COLORS[arm], marker="o", lw=1.6, ms=4.5, capsize=2.5, label=LABELS[arm])
        if a.target_mae.notna().any():
            axes[1].errorbar(x, a.target_mae, yerr=a.target_mae_sem, color=COLORS[arm], marker="o", lw=1.6, ms=4.5, capsize=2.5)
        axes[2].errorbar(x, a.frontier_crossing_predicted_hit_rate, yerr=a.frontier_crossing_predicted_hit_rate_sem, color=COLORS[arm], marker="o", lw=1.6, ms=4.5, capsize=2.5)
    boundary = float(manifest["training_max_log10_sigma"])
    axes[0].axhline(boundary, color="#222222", lw=1.1, ls=(0, (3, 2)))
    axes[0].text(3.02, boundary + 0.008, "training maximum", ha="right", va="bottom", fontsize=7.5)
    requested = [float(metrics[metrics.target_label == label].target.iloc[0]) for label in TARGETS]
    axes[0].plot(x, requested, color="#333333", lw=1.0, ls=(0, (1.5, 1.5)), marker="x", ms=3.5, label="Requested target")
    axes[0].set_ylabel(r"RF prediction, log$_{10}\sigma$")
    axes[1].set_ylabel(r"Target MAE, $\Delta$ log$_{10}\sigma$")
    axes[2].set_ylabel("Predicted frontier crossing")
    for ax in axes:
        ax.set_xticks(x, [TARGET_SHORT[t] for t in TARGETS])
        ax.set_xlim(-0.2, 3.2)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="x", rotation=22)
        ax.yaxis.label.set_size(11.5)
    axes[0].set_ylim(-4.6, -3.05)
    axes[1].set_ylim(0, 1.25)
    axes[2].set_ylim(-0.03, 0.45)
    axes[0].set_title("A  RF response", loc="left", fontweight="bold")
    axes[1].set_title("B  Target error", loc="left", fontweight="bold")
    axes[2].set_title("C  RF crossing", loc="left", fontweight="bold")
    handles = [Line2D([0], [0], color=COLORS[a], marker="o", lw=1.6, label=LABELS[a]) for a in ARMS]
    handles.append(Line2D([0], [0], color="#333333", marker="x", lw=1.0, ls=(0, (1.5, 1.5)), label="Requested target"))
    shared_legend(fig, handles, 4)
    response_layout(fig)
    save(fig, "Figure_1_extrapolation_response")

    # Figure 2: paired seed contrasts using the same cell and seed identity.
    paired = pd.read_csv(IN / "paired_contrasts.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"wspace": 0.58})
    for seed, group in paired.groupby("seed"):
        g = group.set_index("target_label").reindex(TARGETS)
        axes[0].plot(x, g["continuous__frontier_crossing_predicted_hit_rate"], color=COLORS["continuous"], alpha=0.38, lw=1.0)
        axes[0].plot(x, g["binary__frontier_crossing_predicted_hit_rate"], color=COLORS["binary"], alpha=0.38, lw=1.0)
        axes[1].plot(x, g["continuous_minus_binary__frontier_crossing_predicted_hit_rate"], color="#4A4A4A", alpha=0.45, lw=1.0, marker="o", ms=3)
    mean = paired.groupby("target_label")["continuous_minus_binary__frontier_crossing_predicted_hit_rate"].agg(["mean", "std", "count"]).reindex(TARGETS)
    mean["sem"] = mean["std"] / np.sqrt(mean["count"].clip(lower=1))
    axes[1].errorbar(x, mean["mean"], yerr=mean["sem"], color="#111111", marker="o", lw=2.0, capsize=2.5, label="Mean ± SEM")
    axes[1].axhline(0, color="#222222", lw=1.0, ls=(0, (3, 2)))
    axes[0].set_ylabel("Predicted crossing fraction")
    axes[1].set_ylabel("Continuous − binary")
    for ax in axes:
        ax.set_xticks(x, [TARGET_SHORT[t] for t in TARGETS])
        ax.set_xlim(-0.2, 3.2)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.tick_params(axis="x", rotation=22)
    axes[0].set_title("D  Paired seed traces", loc="left", fontweight="bold")
    axes[1].set_title("E  Matched RF-only contrast", loc="left", fontweight="bold")
    axes[0].legend(handles=[Line2D([0], [0], color=COLORS["continuous"], lw=1.8, label="Continuous"), Line2D([0], [0], color=COLORS["binary"], lw=1.8, label="Binary")], frameon=False, fontsize=8)
    axes[1].legend(frameon=False, fontsize=8)
    fig.subplots_adjust(top=0.88, bottom=0.25, left=0.16, right=0.97)
    save(fig, "Figure_2_extrapolation_paired_contrast")

    # Figure 3: support, uncertainty, and failure coverage.
    fig, axes = plt.subplots(1, 3, figsize=(8.2, 3.0), gridspec_kw={"wspace": 0.65})
    for ax, metric, title, vmax in zip(axes, ["support_mean", "rf_uncertainty_mean", "failure_rate"], ["F  Nearest-train support", "G  RF uncertainty", "H  Failure fraction"], [1.0, 0.35, 1.0]):
        matrix = metrics.pivot_table(index="arm", columns="target_label", values=metric, aggfunc="mean").reindex(index=ARMS, columns=TARGETS)
        im = ax.imshow(matrix.to_numpy(), vmin=0, vmax=vmax, cmap="YlGnBu" if metric != "failure_rate" else "OrRd", aspect="auto")
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                value = matrix.iloc[row, col]
                label = "—" if pd.isna(value) else f"{value:.2f}"
                ax.text(col, row, label, ha="center", va="center", fontsize=8, color="white" if pd.notna(value) and value > vmax * 0.55 else "#222222")
        ax.set_xticks(range(4), [TARGET_SHORT[t] for t in TARGETS])
        ax.set_xticklabels([TARGET_SHORT[t] for t in TARGETS], rotation=22, ha="right", fontsize=9.5)
        ax.set_yticks(range(3), [SHORT[a] for a in ARMS])
        if ax is not axes[0]:
            ax.set_yticklabels([])
        else:
            ax.set_yticklabels([SHORT[a] for a in ARMS], fontsize=9.5)
        ax.tick_params(length=0); ax.spines[:].set_visible(False); ax.set_title(title, loc="left", fontweight="bold")
        cbar = fig.colorbar(im, ax=ax, fraction=0.055, pad=0.04); cbar.set_label("Fraction" if metric != "rf_uncertainty_mean" else "log$_{10}\sigma$", fontsize=8); cbar.ax.tick_params(labelsize=7, length=2)
    heatmap_layout(fig)
    save(fig, "Figure_3_extrapolation_support_uncertainty_failure")

    # Figure 4: locked-tail calibration audit, separate from generated-candidate evidence.
    fig, ax = plt.subplots(figsize=(3.55, 3.1))
    colors = {"Q80-Q90": "#4C78A8", "Q90-Q95": "#F58518", "Q95-Q100": "#E45756"}
    for label, group in tail.groupby("tail_bin", observed=True):
        ax.scatter(group.rf_prediction, group.observed_log_sigma, s=8, alpha=0.24, linewidths=0, color=colors.get(str(label), "#777777"), label=str(label))
    low = min(tail.rf_prediction.min(), tail.observed_log_sigma.min()) - 0.02
    high = max(tail.rf_prediction.max(), tail.observed_log_sigma.max()) + 0.02
    ax.plot([low, high], [low, high], color="#222222", ls=(0, (3, 2)), lw=1.1, label="Ideal calibration")
    ax.axvline(boundary, color="#007C83", lw=1.0, ls=(0, (1.5, 1.5)))
    ax.axhline(boundary, color="#007C83", lw=1.0, ls=(0, (1.5, 1.5)))
    ax.set_xlim(low, high); ax.set_ylim(low, high)
    ax.set_xlabel(r"RF prediction, log$_{10}$ S cm$^{-1}$")
    ax.set_ylabel(r"Observed locked-tail value, log$_{10}$ S cm$^{-1}$")
    ax.set_title("I  Locked-tail verifier audit", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=7.2, loc="upper left")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    verifier = json.loads((IN / "verifier_metrics.json").read_text())
    ax.text(0.98, 0.04, f"MAE = {verifier['locked_tail_rf_mae']:.3f}\nmean residual = {verifier['locked_tail_rf_residual_mean']:+.3f}", transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8})
    save(fig, "Figure_4_locked_tail_rf_calibration")

    captions = """# Extrapolation publication figures

**Figure 1 | Surrogate-only response beyond a locked Q80 boundary.** (A) Mean frozen-RF prediction versus four prespecified extrapolation targets for continuous, fixed-threshold binary, and unconditional+rerranking arms; points and error bars are means ± SEM across five matched seeds. Crosses show requested targets and the horizontal dashed line marks the actual Q80 training maximum. (B) Target MAE is shown only where at least one valid candidate exists; missing values are unsupported, not zero. (C) Fraction of candidates that cross the training maximum according to the frozen RF after validity, novelty, support, and uncertainty gates. These are screening signals only, not MD-confirmed crossings.

**Figure 2 | Paired RF-only contrast.** (D) Thin traces show each matched seed's predicted frontier-crossing fraction for continuous and binary arms. (E) The dark summary is the continuous-minus-binary contrast, mean ± SEM across the five paired seeds. The unit is the arm × seed × target cell; no independent-candidate inferential test is implied.

**Figure 3 | Support, uncertainty, and failure coverage.** Heatmaps show cell means for (F) nearest-training Morgan-fingerprint support, (G) RF tree uncertainty, and (H) failure fraction. A dash denotes no valid generated candidate. Binary cells are structurally blocked for target control because the fixed -4.0 label is single-class after Q80 truncation.

**Figure 4 | Locked-tail verifier audit, separate from generated-candidate evidence.** Each point is one source row held above full-source Q80, colored by locked-tail interval. The diagonal is ideal calibration and teal dotted lines mark the actual training maximum. This post-run audit demonstrates why RF-only frontier crossings cannot be treated as physical extrapolation evidence; MD was not run in this phase.
"""
    (OUT / "FIGURE_CAPTIONS.md").write_text(captions)


if __name__ == "__main__":
    main()
