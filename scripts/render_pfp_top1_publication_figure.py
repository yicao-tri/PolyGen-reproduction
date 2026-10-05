#!/usr/bin/env python3
"""Render the publication-style PFP top-1 paired pilot figure.

The figure is derived only from the committed paired-results and convergence
CSV files; no trajectory values are hard-coded in the plotting logic.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "results/experiment-c/pfp-pilot/production/analysis"
OUT = ANALYSIS / "figures"
COLORS = {"continuous": "#147D92", "binary": "#D97941", "proxy": "#6E6E6E"}
ARMS = ("continuous", "binary")
LABELS = ("Continuous\ntop-1", "Binary\ntop-1")

mpl.rcParams.update({
    "font.family": "Arial",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "axes.linewidth": 1.1,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "xtick.major.width": 1.0,
    "ytick.major.width": 1.0,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    paired = {row["arm"]: row for row in read_csv(ANALYSIS / "paired/paired_results.csv")}
    convergence = {
        arm: read_csv(ANALYSIS / arm / "convergence.csv") for arm in ARMS
    }
    log_pfp = np.array([float(paired[arm]["cluster_ne_log10_S_cm"]) for arm in ARMS])
    log_proxy = np.array([float(paired[arm]["proxy_log10_S_cm"]) for arm in ARMS])
    li_D = np.array([float(paired[arm]["li_diffusivity_cm2_s"]) * 1e6 for arm in ARMS])
    tfsi_D = np.array([float(paired[arm]["tfsi_diffusivity_cm2_s"]) * 1e6 for arm in ARMS])

    mpl.rcParams.update({"figure.dpi": 120})
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.55), gridspec_kw={"wspace": 0.42})

    ax = axes[0]
    x = np.arange(2)
    for i, arm in enumerate(ARMS):
        ax.plot([x[i], x[i]], [log_proxy[i], log_pfp[i]], color=COLORS[arm], lw=2.2, zorder=1)
        ax.scatter(x[i], log_proxy[i], s=28, color=COLORS["proxy"], edgecolor="white", linewidth=0.6, zorder=3)
        ax.scatter(x[i], log_pfp[i], s=35, color=COLORS[arm], edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_xticks(x, LABELS)
    ax.set_ylabel(r"log$_{10}$ conductivity (S cm$^{-1}$)")
    ax.set_title("Proxy versus PFP")
    ax.set_ylim(-4.05, -2.15)
    residuals = [float(paired[arm]["residual_pfp_minus_proxy_log10_S_cm"]) for arm in ARMS]
    ax.text(0.04, 0.04, f"Δ(PFP−proxy): +{residuals[0]:.2f}, +{residuals[1]:.2f}", transform=ax.transAxes, fontsize=7.2)

    ax = axes[1]
    width = 0.34
    ax.bar(x - width / 2, li_D, width, color=COLORS["continuous"], label="Li$^+$")
    ax.bar(x + width / 2, tfsi_D, width, color=COLORS["binary"], label="TFSI$^-$")
    ax.set_xticks(x, LABELS)
    ax.set_ylabel(r"D ($10^{-6}$ cm$^2$ s$^{-1}$)")
    ax.set_title("Ion diffusivity")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    ax.set_ylim(0, 6.7)

    ax = axes[2]
    for arm in ARMS:
        rows = convergence[arm]
        times = np.array([float(row["analysis_duration_ps"]) for row in rows])
        values = np.array([float(row["cluster_ne_log10_S_cm"]) for row in rows])
        ax.plot(times, values, marker="o", ms=3.5, lw=1.8, color=COLORS[arm], label=arm.title())
    ax.axvline(40, color="#999999", ls="--", lw=0.8)
    ax.text(41.5, -2.18, "discard", color="#666666", fontsize=7, va="top")
    ax.set_xlabel("Analysis window (ps)")
    ax.set_ylabel(r"log$_{10}$ cNE conductivity")
    ax.set_title("Window convergence")
    ax.set_xlim(15, 165)
    ax.set_ylim(-3.1, -1.95)
    ax.legend(frameon=False, fontsize=7, loc="lower left")

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(direction="out", length=3)

    fig.text(0.01, -0.045,
             "One matched top-1 candidate per arm; 200 ps PFP-MD, final 160 ps analysed after 40 ps discard; one replica, no uncertainty estimate.",
             ha="left", va="top", fontsize=7)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "pfp_top1_publication_figure.svg", bbox_inches="tight")
    fig.savefig(OUT / "pfp_top1_publication_figure.pdf", bbox_inches="tight")
    fig.savefig(OUT / "pfp_top1_publication_figure.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
