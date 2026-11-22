#!/usr/bin/env python3
"""Plot-Atlas-style signed-deviation ECDF with seed-level uncertainty ribbons."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/upper-tail"
kind = sys.argv[1] if len(sys.argv) > 1 else "blind"
if kind == "blind":
    data = pd.read_csv(BASE / "candidate_predictions.csv")
    pred, valid = "predicted_log_sigma", "valid"
    outdir = BASE / "publication_v2"
    title = "Signed target deviation under the Q80-only blind RF"
else:
    data = pd.read_csv(BASE / "full-rf-audit/fullrf_candidate_predictions.csv")
    pred, valid = "fullrf_prediction", "fullrf_valid"
    outdir = BASE / "full-rf-audit/publication"
    title = "Signed target deviation under the full-source RF audit"
outdir.mkdir(parents=True, exist_ok=True)

SEEDS = [17, 42, 202, 303, 907]
TARGETS = ["Q80_boundary_actual_train_max", "Q85", "Q90", "Q95"]
TARGET_LABELS = {TARGETS[0]: "Boundary", "Q85": "Q85", "Q90": "Q90", "Q95": "Q95"}
ARMS = ["continuous", "binary", "unconditional_reranking"]
LABELS = {"continuous": "Continuous", "binary": "Binary", "unconditional_reranking": "Unconditional + reranking"}
COLORS = {"continuous": "#007C83", "binary": "#D55F02", "unconditional_reranking": "#6A6A6A"}
X = np.linspace(-0.65, 0.12, 500)

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 13,
    "axes.labelsize": 15,
    "axes.titlesize": 17,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "axes.linewidth": 1.6,
    "xtick.major.width": 1.4,
    "ytick.major.width": 1.4,
    "xtick.major.size": 5,
    "ytick.major.size": 5,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "savefig.dpi": 600,
})

def ecdf(values):
    values = np.sort(np.asarray(values, dtype=float))
    if len(values) == 0:
        return np.full_like(X, np.nan, dtype=float)
    return np.searchsorted(values, X, side="right") / len(values)

fig, axes = plt.subplots(4, 1, figsize=(8.2, 11.8), sharex=True, sharey=True, gridspec_kw={"hspace": 0.22})
for ax, target in zip(axes, TARGETS):
    for arm in ARMS:
        seed_curves = []
        valid_counts = []
        for seed in SEEDS:
            g = data[(data.target_label == target) & (data.arm == arm) & (data.seed == seed)]
            deviations = (g.loc[g[valid], pred] - g.loc[g[valid], "target"]).dropna().to_numpy()
            valid_counts.append(len(deviations))
            if len(deviations):
                seed_curves.append(ecdf(deviations))
        if not seed_curves:
            continue
        curves = np.vstack(seed_curves)
        median = np.nanmedian(curves, axis=0)
        low = np.nanpercentile(curves, 10, axis=0)
        high = np.nanpercentile(curves, 90, axis=0)
        ax.fill_between(X, low, high, color=COLORS[arm], alpha=0.14, linewidth=0)
        ax.plot(X, median, color=COLORS[arm], linewidth=2.4, label=LABELS[arm])
        n_total = int(data[(data.target_label == target) & (data.arm == arm)].shape[0])
        n_valid = int(sum(valid_counts))
        ax.text(0.985, 0.84 - 0.075 * ARMS.index(arm), f"{LABELS[arm]}  {n_valid}/{n_total}", transform=ax.transAxes, ha="right", va="center", color=COLORS[arm], fontsize=10.5, bbox={"facecolor":"white", "edgecolor":"none", "pad":1.5, "alpha":0.82})
    ax.axvline(0, color="#222222", linewidth=1.3, linestyle=(0, (4, 3)))
    for threshold in (-0.50, -0.25, -0.10):
        ax.axvline(threshold, color="#BBBBBB", linewidth=0.8, linestyle=(0, (2, 3)))
    ax.set_title(TARGET_LABELS[target], loc="left", fontweight="bold", pad=8)
    ax.set_ylim(0, 1.02)
    ax.set_xlim(-0.65, 0.12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("ECDF", labelpad=8)
    ax.text(-0.64, 0.08, "0 = exact target", fontsize=10, color="#555555")
axes[-1].set_xlabel(r"Signed deviation: RF prediction − requested target  (log$_{10}$ S cm$^{-1}$)", labelpad=12)
fig.legend(handles=[Line2D([0], [0], color=COLORS[a], lw=2.4, label=LABELS[a]) for a in ARMS], loc="upper center", bbox_to_anchor=(0.58, 0.952), frameon=False, fontsize=11, ncol=3, columnspacing=1.5, handlelength=2.2)
fig.suptitle(title, x=0.05, ha="left", y=0.985, fontsize=20, fontweight="bold")
fig.subplots_adjust(left=0.14, right=0.985, top=0.93, bottom=0.075)
base = outdir / f"Figure_signed_target_deviation_ecdf_{kind}_atlas"
fig.savefig(base.with_suffix(".png"), dpi=600, bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print(base)
