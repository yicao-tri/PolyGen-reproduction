#!/usr/bin/env python3
"""Publication figures for the frozen multi-property interpolation outputs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from publication_plot_style import apply_style, save_publication_figure

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results" / "multi-property" / "interpolation"
OUT = IN / "publication"
OUT.mkdir(parents=True, exist_ok=True)
ARMS = ["multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"]
LABELS = {"multi_continuous": "Multi-property", "scalar_continuous": "Scalar", "binary_conductivity": "Binary", "unconditional_reranking": "Uncond. + rerank"}
COLORS = {"multi_continuous": "#007C83", "scalar_continuous": "#4477AA", "binary_conductivity": "#D95F02", "unconditional_reranking": "#6B6B6B"}
PROPS = ["log10_conductivity", "log10_li_diffusivity", "log10_tfsi_diffusivity", "log10_poly_diffusivity", "transference_number", "molality"]
SHORT = {"log10_conductivity": "conductivity", "log10_li_diffusivity": "Li diffusivity", "log10_tfsi_diffusivity": "TFSI diffusivity", "log10_poly_diffusivity": "polymer diffusivity", "transference_number": "transference", "molality": "molality"}


def sem(x):
    x = pd.Series(x).dropna()
    return float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else np.nan


def save(fig, stem):
    save_publication_figure(fig, OUT, stem)


def main():
    apply_style()
    m = pd.read_csv(IN / "metrics_by_cell.csv")
    cells = pd.read_csv(IN / "target_cells.csv")
    m = m.merge(cells[["target_cell", "target_family", "probe_property", "quantile"]], on=["target_cell", "target_family"], how="left", suffixes=("", "_cell"))
    probes = m[m.target_family == "property_probe"].copy()
    # Figure 1: six small multiples, one per property-probe family.
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 5.6), sharey=False)
    x = np.arange(3)
    for panel_i, (ax, prop) in enumerate(zip(axes.flat, PROPS)):
        for arm in ARMS:
            g = probes[(probes.probe_property == prop) & (probes.arm == arm)]
            a = g.groupby("quantile").joint_target_error.agg(["mean", "std", "count"]).reindex([.50, .65, .80])
            ax.errorbar(x, a["mean"], yerr=a["std"] / np.sqrt(a["count"]), color=COLORS[arm], marker="o", ms=4, lw=1.5, capsize=2.2, label=LABELS[arm])
        ax.set_xticks(x, ["Q50", "Q65", "Q80"])
        ax.set_title(SHORT[prop], loc="left", fontsize=10, fontweight="bold")
        ax.set_ylabel("Joint error (normalized RMSE)" if panel_i % 3 == 0 else "")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.set_ylim(bottom=0)
    handles = [Line2D([0], [0], color=COLORS[a], marker="o", lw=1.5, label=LABELS[a]) for a in ARMS]
    fig.legend(handles=handles, frameon=False, loc="upper center", bbox_to_anchor=(.5, .985), ncol=4, fontsize=9)
    fig.subplots_adjust(top=.86, bottom=.12, left=.08, right=.98, wspace=.35, hspace=.45)
    save(fig, "Figure_1_property_probe_joint_error")

    # Figure 2: coherent joint targets, with paired descriptive contrasts.
    joint = m[m.target_family == "coherent_joint"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.0), gridspec_kw={"wspace": .45})
    qorder = ["joint_empirical_copula_Q50", "joint_empirical_copula_Q65", "joint_empirical_copula_Q80"]
    qlabels = ["Q50", "Q65", "Q80"]
    for ax, metric, ylabel in zip(axes, ["joint_target_error", "joint_strict_hit_rate"], ["Joint error (normalized RMSE)", "Joint strict-hit rate"]):
        for arm in ARMS:
            g = joint[joint.arm == arm].groupby("target_cell")[metric].agg(["mean", "std", "count"]).reindex(qorder)
            ax.errorbar(np.arange(3), g["mean"], yerr=g["std"] / np.sqrt(g["count"]), color=COLORS[arm], marker="o", ms=4.5, lw=1.6, capsize=2.5, label=LABELS[arm])
        ax.set_xticks(np.arange(3), qlabels)
        ax.set_ylabel(ylabel)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.set_title("A  Coherent joint target error" if metric == "joint_target_error" else "B  Coherent joint strict hit", loc="left", fontsize=10, fontweight="bold")
        if metric == "joint_strict_hit_rate": ax.set_ylim(0, 1)
    axes[1].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.subplots_adjust(left=.15, right=.76, bottom=.22, top=.88)
    save(fig, "Figure_2_coherent_joint_targets")

    # Figure 3: cell-level support-aware quality audit.
    order = cells.sort_values(["target_family", "cell_index"]).target_cell.tolist()
    fig, axes = plt.subplots(2, 1, figsize=(12, 4.5), sharex=True)
    for ax, metric, title in zip(axes, ["joint_strict_hit_rate", "validity"], ["C  Strict-hit rate", "D  Validity fraction"]):
        mat = m.pivot_table(index="arm", columns="target_cell", values=metric, aggfunc="mean").reindex(index=ARMS, columns=order)
        im = ax.imshow(mat.to_numpy(), aspect="auto", vmin=0, vmax=1, cmap="YlGnBu")
        ax.set_yticks(np.arange(len(ARMS)), [LABELS[a] for a in ARMS])
        ax.set_title(title, loc="left", fontsize=10, fontweight="bold")
        ax.spines[:].set_visible(False)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat.iloc[i, j]
                if np.isfinite(val): ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=5.6, color="white" if val > .52 else "#222")
        if ax is axes[-1]:
            short_labels = {"joint_empirical_copula": "joint", "log10_conductivity": "cond.", "log10_li_diffusivity": "Li D", "log10_tfsi_diffusivity": "TFSI D", "log10_poly_diffusivity": "poly D", "transference_number": "t+", "molality": "molality"}
            labels = []
            for c in order:
                base, q = c.rsplit("_Q", 1)
                labels.append(f"{short_labels.get(base, base)} Q{q}")
            ax.set_xticks(np.arange(len(order)), labels, rotation=60, ha="right", fontsize=6.2)
        else: ax.tick_params(axis="x", length=0, labelbottom=False)
    cax = fig.add_axes([.90, .25, .018, .50])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("Fraction", fontsize=9)
    fig.subplots_adjust(left=.14, right=.87, top=.91, bottom=.34, hspace=.22)
    save(fig, "Figure_3_cell_quality_audit")

    (OUT / "FIGURE_CAPTIONS.md").write_text("""# Multi-property interpolation publication figures\n\n**Figure 1 | Property-probe joint error.** Each panel is one of the six conditioned properties. The x-axis is the Q50/Q65/Q80 probe level for that property, with the other five target coordinates fixed at their train-only medians. Lines and error bars are means ± SEM across five matched seeds; the unit is the arm × seed × target cell. The plotted RF errors are normalized by the train-only property standard deviations and summarize all six predicted properties jointly. This figure does not establish physical controllability or MD performance.\n\n**Figure 2 | Coherent joint targets.** The three target vectors are train-only empirical-copula rows selected at Q50/Q65/Q80 of the mean marginal percentile score. No independent Cartesian product of marginal quantiles is used. Points and error bars are means ± SEM across five seeds. Strict-hit status additionally requires validity, exact-training novelty, structural support, normalized RF uncertainty, joint target error, and a supported target cell.\n\n**Figure 3 | Cell-level support-aware quality audit.** Heatmaps show descriptive means across seeds for strict-hit rate and validity across all 21 target cells. The row unit is arm; the column unit is target cell. Empty or unsupported cells would be shown as missing rather than zero; the delivered audit retains them in `unsupported_cells.csv`. All metrics are surrogate-screening evidence only, with MD status fixed to `not_run`.\n""")


if __name__ == "__main__":
    main()
