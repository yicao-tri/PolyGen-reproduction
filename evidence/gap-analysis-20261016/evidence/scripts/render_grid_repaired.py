#!/usr/bin/env python3
"""Render a clean, real-data generation-grid figure from audited summaries."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLORS = {"binary": "#d2691e", "continuous": "#1b7f86"}


def matrix(frame: pd.DataFrame, arm: str, metric: str) -> pd.DataFrame:
    return (
        frame[frame["arm"] == arm]
        .pivot(index="steps", columns="temperature", values=metric)
        .sort_index()
        .sort_index(axis=1)
    )


def draw_heatmap(ax, values: pd.DataFrame, title: str, cmap: str, vmin: float, vmax: float, fmt: str):
    image = ax.imshow(values.to_numpy(), cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xticks(range(len(values.columns)), [f"{x:.1f}" for x in values.columns])
    ax.set_yticks(range(len(values.index)), [str(int(x)) for x in values.index])
    ax.set_xlabel("temperature")
    ax.set_ylabel("training steps")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            value = values.iloc[i, j]
            ax.text(j, i, format(value, fmt), ha="center", va="center", fontsize=9, color="black")
    ax.spines[:].set_visible(False)
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-stem", type=Path, required=True)
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    binary_hit = matrix(frame, "binary", "strict_hit_rate")
    continuous_hit = matrix(frame, "continuous", "strict_hit_rate")
    delta_hit = continuous_hit - binary_hit
    continuous_mae = matrix(frame, "continuous", "target_mae")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.6))
    panels = [
        (axes[0, 0], binary_hit, "A  Binary strict hit rate", "YlOrBr", 0.0, 0.85, ".2f"),
        (axes[0, 1], continuous_hit, "B  Continuous strict hit rate", "YlGnBu", 0.0, 0.85, ".2f"),
        (axes[1, 0], delta_hit, "C  Continuous - binary strict hit", "coolwarm", -0.12, 0.12, "+.2f"),
        (axes[1, 1], continuous_mae, "D  Continuous target MAE", "magma", 0.55, 0.75, ".2f"),
    ]
    for ax, values, title, cmap, vmin, vmax, fmt in panels:
        image = draw_heatmap(ax, values, title, cmap, vmin, vmax, fmt)
        cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=8)

    fig.suptitle("PolyGen generation grid: real frozen-RF audit", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0.0, 0.10, 1.0, 0.94])
    fig.text(
        0.5,
        0.025,
        "9 configurations x 5 paired seeds x 2 arms x 300 samples/seed-arm = 27,000 raw rows; property values are verifier predictions, not measured conductivity.",
        ha="center",
        va="bottom",
        fontsize=8.5,
    )
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_stem.with_suffix(".png"), dpi=320, bbox_inches="tight")
    fig.savefig(args.output_stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(args.output_stem.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
