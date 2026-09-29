#!/usr/bin/env python3
"""Render publication figures and manuscript-ready tables for Upper-tail."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from publication_plot_style import apply_style, shared_legend, save_publication_figure, response_layout, heatmap_layout

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/upper-tail"
OUT = IN / "publication"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "continuous": "#007C83",
    "binary": "#D95F02",
    "unconditional_reranking": "#6B6B6B",
}
LABELS = {
    "continuous": "Continuous",
    "binary": "Binary",
    "unconditional_reranking": "Unconditional + reranking",
}
SHORT_LABELS = {
    "continuous": "Continuous",
    "binary": "Binary",
    "unconditional_reranking": "Uncond. + rerank",
}
TARGET_ORDER = ["Q80_boundary_actual_train_max", "Q85", "Q90", "Q95"]
TARGET_SHORT = {"Q80_boundary_actual_train_max": "Boundary", "Q85": "Q85", "Q90": "Q90", "Q95": "Q95"}


def style():
    apply_style()


def sem(values):
    values = pd.Series(values).dropna()
    return values.std(ddof=1) / np.sqrt(len(values)) if len(values) > 1 else np.nan


def aggregate(metrics):
    rows = []
    for (arm, target_label), g in metrics.groupby(["arm", "target_label"], sort=False):
        row = {"arm": arm, "target_label": target_label, "target": g.target.iloc[0], "n_seeds": len(g)}
        for col in ["validity", "novelty", "strict_hit_rate", "target_mae", "rf_prediction_mean", "rf_uncertainty_mean", "support_mean", "upper_tail_predicted_hit_rate"]:
            row[col] = g[col].mean()
            row[col + "_sem"] = sem(g[col])
        rows.append(row)
    return pd.DataFrame(rows)


def save(fig, name):
    save_publication_figure(fig, OUT, name)


def main():
    style()
    metrics = pd.read_csv(IN / "metrics_by_cell.csv")
    tail = pd.read_csv(IN / "locked_tail_verifier_audit.csv")
    unsupported = pd.read_csv(IN / "unsupported_cells.csv")
    agg = aggregate(metrics)
    agg.to_csv(OUT / "upper_tail_aggregate_metrics.csv", index=False)
    unsupported.groupby(["arm", "target_label"], as_index=False).size().rename(columns={"size": "unsupported_seed_cells"}).to_csv(OUT / "upper_tail_unsupported_summary.csv", index=False)

    # Figure 1: response, target adherence, and valid yield.
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.9), gridspec_kw={"wspace": 0.55})
    x = np.arange(len(TARGET_ORDER))
    for arm in COLORS:
        a = agg[agg.arm == arm].set_index("target_label").reindex(TARGET_ORDER)
        axes[0].errorbar(x, a.rf_prediction_mean, yerr=a.rf_prediction_mean_sem, color=COLORS[arm], marker="o", lw=1.6, ms=4.5, capsize=2.5, label=LABELS[arm])
        axes[1].errorbar(x, a.target_mae, yerr=a.target_mae_sem, color=COLORS[arm], marker="o", lw=1.6, ms=4.5, capsize=2.5)
        axes[2].errorbar(x, a.validity, yerr=a.validity_sem, color=COLORS[arm], marker="o", lw=1.6, ms=4.5, capsize=2.5)
    boundary = float(pd.read_json(IN / "frozen_manifest.json").get("training_max_log10_sigma", np.nan)) if False else float(json.loads((IN / "frozen_manifest.json").read_text())["training_max_log10_sigma"])
    axes[0].axhline(boundary, color="#222222", lw=1.1, ls=(0, (3, 2)))
    axes[0].text(3.02, boundary + 0.008, "training maximum", ha="right", va="bottom", fontsize=7.5)
    axes[0].plot(x, [float(agg[agg.target_label == t].target.iloc[0]) for t in TARGET_ORDER], color="#333333", lw=1.0, ls=(0, (1.5, 1.5)), marker="x", ms=3.5, label="Requested target")
    axes[0].set_ylabel(r"RF prediction, $\log_{10}\sigma$")
    axes[1].set_ylabel(r"Target MAE, $\Delta\log_{10}\sigma$")
    axes[2].set_ylabel("Validity fraction")
    for ax in axes:
        ax.yaxis.label.set_size(12.0)
        ax.yaxis.labelpad = 6
    for ax in axes:
        ax.set_xticks(x, ["Bdy.", "Q85", "Q90", "Q95"])
        ax.set_xticklabels(["Bdy.", "Q85", "Q90", "Q95"], rotation=0, ha="center", fontsize=10.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlim(-0.2, 3.25)
        ax.tick_params(axis="x", rotation=0)
    axes[0].set_ylim(-4.42, -3.82)
    axes[1].set_ylim(0, 0.52)
    axes[2].set_ylim(0, 0.72)
    axes[0].set_title("A  RF response", loc="left", fontweight="bold")
    axes[1].set_title("B  Target error", loc="left", fontweight="bold")
    axes[2].set_title("C  Validity", loc="left", fontweight="bold")
    handles = [Line2D([0], [0], color=COLORS[a], marker="o", lw=1.6, label=LABELS[a]) for a in COLORS]
    handles.append(Line2D([0], [0], color="#333333", marker="x", lw=1.0, ls=(0, (1.5, 1.5)), label="Requested target"))
    shared_legend(fig, handles, 4)
    response_layout(fig)
    save(fig, "Figure_1_upper_tail_response")

    # Figure 2: strict-hit and unsupported cells.
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 2.9), gridspec_kw={"wspace": 0.65})
    for i, metric in enumerate(["strict_hit_rate", "validity"]):
        ax = axes[i]
        mat = metrics.pivot_table(index="arm", columns="target_label", values=metric, aggfunc="mean").reindex(index=list(COLORS), columns=TARGET_ORDER)
        im = ax.imshow(mat.to_numpy(), vmin=0, vmax=0.7, cmap="YlGnBu", aspect="auto")
        for r in range(mat.shape[0]):
            for c in range(mat.shape[1]):
                value = mat.iloc[r, c]
                text = "—" if pd.isna(value) else f"{value:.2f}"
                ax.text(c, r, text, ha="center", va="center", fontsize=8, color="white" if value > 0.38 else "#222222")
        ax.set_xticks(range(4), [TARGET_SHORT[t] for t in TARGET_ORDER])
        ax.set_xticklabels([TARGET_SHORT[t] for t in TARGET_ORDER], rotation=25, ha="right", fontsize=10.5)
        ax.set_yticks(range(3), [SHORT_LABELS[a] for a in COLORS])
        ax.set_yticklabels([SHORT_LABELS[a] for a in COLORS], fontsize=10.5)
        ax.tick_params(length=0)
        ax.set_title(("D  Strict-hit rate" if i == 0 else "E  Validity"), loc="left", fontweight="bold")
        ax.spines[:].set_visible(False)
        if i == 1:
            cbar = fig.colorbar(im, ax=ax, fraction=0.055, pad=0.04)
            cbar.set_label("Fraction", fontsize=8)
            cbar.ax.tick_params(labelsize=7, length=2)
    heatmap_layout(fig)
    save(fig, "Figure_2_upper_tail_quality_heatmap")

    # Figure 3: locked-tail RF calibration.
    fig, ax = plt.subplots(figsize=(3.45, 3.0))
    colors = {"Q80-Q85": "#4C78A8", "Q85-Q90": "#F58518", "Q90-Q95": "#E45756"}
    for label, g in tail.groupby("tail_bin", observed=True):
        ax.scatter(g.predicted_log_sigma, g.observed_log_sigma, s=8, alpha=0.28, linewidths=0, color=colors.get(str(label), "#777777"), label=str(label))
    lo = min(tail.predicted_log_sigma.min(), tail.observed_log_sigma.min()) - 0.02
    hi = max(tail.predicted_log_sigma.max(), tail.observed_log_sigma.max()) + 0.02
    ax.plot([lo, hi], [lo, hi], color="#222222", ls=(0, (3, 2)), lw=1.1, label="Ideal calibration")
    ax.axvline(boundary, color="#007C83", lw=1.0, ls=(0, (1.5, 1.5)))
    ax.axhline(boundary, color="#007C83", lw=1.0, ls=(0, (1.5, 1.5)))
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(r"RF prediction, log$_{10}$ S cm$^{-1}$")
    ax.set_ylabel(r"Observed locked-tail value, log$_{10}$ S cm$^{-1}$")
    ax.set_title("F  Frozen RF underpredicts the locked tail", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=7.2, loc="upper left")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.text(0.98, 0.04, "MAE = 0.262\nmean residual = +0.262", transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8})
    save(fig, "Figure_3_locked_tail_rf_calibration")

    captions = """# Upper-tail publication figures

**Figure 1 | Upper-tail response under a Q80 training boundary.** (A) Mean frozen-RF prediction versus requested target for continuous, binary, and unconditional+rerranking arms; points and error bars are means ± SEM across five matched seeds. Crosses show requested targets and the horizontal dashed line marks the actual maximum of the Q80 training set. No arm crosses the training maximum after the support and uncertainty gates. (B) Target MAE increases toward Q95, most clearly for continuous conditioning. (C) Continuous conditioning retains the highest valid yield, whereas the binary and unconditional+rerranking controls lose valid output in the most distant cells. Values are verifier-defined and are not MD or experimental measurements.

**Figure 2 | Target adherence and valid-output coverage.** Heatmaps show descriptive cell means for (D) strict-hit rate and (E) validity. A dash denotes a cell with no valid generated candidate, not a zero-valued measurement. The binary arm is a degenerate single-class control under the frozen -4.0 threshold; unconditional+rerranking is effectively unsupported beyond the boundary in this run.

**Figure 3 | Calibration of the frozen verifier on locked Q80–Q95 rows.** Each point is one held-out source row, colored by tail interval. The diagonal is ideal calibration; teal dotted lines mark the actual Q80 training maximum. The RF underpredicts the locked tail by a mean residual of +0.262 log units (MAE 0.262), demonstrating surrogate bias in the very region where generated extrapolation would be claimed. This audit does not validate generated candidates.
"""
    (OUT / "FIGURE_CAPTIONS.md").write_text(captions)


if __name__ == "__main__":
    main()
