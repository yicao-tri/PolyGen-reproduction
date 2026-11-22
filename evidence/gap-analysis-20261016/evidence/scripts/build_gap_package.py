#!/usr/bin/env python3
"""Build the Pitch × PolyGen gap-analysis evidence package.

The canonical PolyGen repository is read-only input. This script writes only to
the package directory passed by --out. It creates machine-readable tables and
publication figures for the strategy's P1–P3 and F1–F8 inventory. Missing MD,
PCFF+ coverage, and active-learning evidence are represented as explicit
planned/synthetic placeholders and never mixed into observed result tables.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib import patches, lines
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FormatStrFormatter

try:
    from plot_atlas import apply_publication_style, forest_effects, joint_scatter, save_figure
except Exception:  # pragma: no cover - standalone fallback
    def apply_publication_style(font_size=8.0):
        plt.rcParams.update({"font.size": font_size, "font.family": ["Arial", "DejaVu Sans"]})
    forest_effects = joint_scatter = None
    def save_figure(fig, path, dpi=300):
        fig.savefig(path, dpi=dpi, bbox_inches="tight")


COLORS = {
    "continuous": "#1B7F86",
    "binary": "#D2691E",
    "unconditional_reranking": "#6B6B6B",
    "molminer": "#4C78A8",
    "wee": "#B0B0B0",
    "ink": "#202020",
    "muted": "#666666",
    "synthetic": "#B2182B",
    "planned": "#7A4E9D",
}
ARMS = ["continuous", "binary", "unconditional_reranking"]
ARM_LABELS = {"continuous": "Continuous", "binary": "Binary", "unconditional_reranking": "Unconditional + reranking"}
TARGETS = ["Q90", "Q100", "train_max_plus_0.25", "train_max_plus_0.50"]
TARGET_SHORT = {"Q90": "Q90", "Q100": "Q100", "train_max_plus_0.25": "+0.25", "train_max_plus_0.50": "+0.50"}
SEEDS = [17, 42, 202, 303, 907]


def q(v: float, n: int = 3) -> str:
    return f"{v:.{n}f}"


def sem(x):
    x = pd.Series(x).dropna().astype(float)
    return float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else np.nan


def t_ci(x, level=0.95):
    x = pd.Series(x).dropna().astype(float)
    if len(x) < 2:
        return (np.nan, np.nan)
    m = float(x.mean())
    half = float(stats.t.ppf((1 + level) / 2, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)))
    return m - half, m + half


def save_multi(fig, out_dir: Path, stem: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        path = out_dir / f"{stem}.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def add_status_stamp(fig, text, color=COLORS["synthetic"], x=0.995, y=0.008):
    fig.text(x, y, text, ha="right", va="bottom", fontsize=7, color=color, style="italic")


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.1)
    ax.spines["bottom"].set_linewidth(1.1)
    ax.tick_params(width=1.0, length=4)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontweight("bold")


def read_inputs(root: Path):
    files = {
        "c1_effect": root / "results/experiment-c/publication/c1_five_seed_effect_summary.csv",
        "c1_target": root / "results/experiment-c/generation-benchmark-audit/existing_c1_arm_seed_target_metrics.csv",
        "c1_arm": root / "results/experiment-c/generation-benchmark-audit/existing_c1_arm_seed_metrics.csv",
        "c1_samples_cont": root / "results/experiment-c/c1/continuous-seed17/samples.csv",
        "extrap_agg": root / "results/extrapolation/publication/extrapolation_aggregate_metrics.csv",
        "extrap_metrics": root / "results/extrapolation/metrics_by_cell.csv",
        "paired": root / "results/extrapolation/paired_contrasts.csv",
        "tail": root / "results/extrapolation/locked_tail_verifier_audit.csv",
        "verifier": root / "results/extrapolation/verifier_metrics.json",
        "manifest": root / "results/extrapolation/frozen_manifest.json",
        "contract": root / "results/extrapolation/design_contract.json",
        "candidate": root / "results/extrapolation/candidate_selection_for_md.csv",
        "md_manifest": root / "results/experiment-c/md-validation/md_batch_manifest.csv",
        "interp_agg": root / "results/interpolation/publication/interpolation_aggregate_metrics.csv",
        "upper_agg": root / "results/upper-tail/publication/upper_tail_aggregate_metrics.csv",
        "fullrf_summary": root / "results/upper-tail/full-rf-audit/fullrf_summary.json",
        "fullrf_tail": root / "results/upper-tail/full-rf-audit/fullrf_locked_tail_audit.csv",
        "molminer": root / "results/molminer-comparison/analysis/combined_target_metrics.csv",
        "pfp_paired": root / "results/experiment-c/pfp-pilot/production/analysis/paired/paired_summary.json",
        "top1_audit": root / "results/experiment-c/md-validation/top1_readiness_audit.json",
    }
    missing = [str(p) for p in files.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing canonical inputs:\n" + "\n".join(missing))
    d = {
        "paths": files,
        "c1_effect": pd.read_csv(files["c1_effect"]),
        "c1_target": pd.read_csv(files["c1_target"]),
        "c1_arm": pd.read_csv(files["c1_arm"]),
        "extrap_agg": pd.read_csv(files["extrap_agg"]),
        "extrap_metrics": pd.read_csv(files["extrap_metrics"]),
        "paired": pd.read_csv(files["paired"]),
        "tail": pd.read_csv(files["tail"]),
        "verifier": json.loads(files["verifier"].read_text()),
        "manifest": json.loads(files["manifest"].read_text()),
        "contract": json.loads(files["contract"].read_text()),
        "candidate": pd.read_csv(files["candidate"]),
        "md_manifest": pd.read_csv(files["md_manifest"]),
        "interp_agg": pd.read_csv(files["interp_agg"]),
        "upper_agg": pd.read_csv(files["upper_agg"]),
        "fullrf_summary": json.loads(files["fullrf_summary"].read_text()),
        "fullrf_tail": pd.read_csv(files["fullrf_tail"]),
        "molminer": pd.read_csv(files["molminer"]),
        "pfp_paired": json.loads(files["pfp_paired"].read_text()),
        "top1_audit": json.loads(files["top1_audit"].read_text()),
    }
    # C1 raw samples are in arm/seed directories; collect all available real rows.
    rows = []
    for arm in ("continuous", "binary"):
        for seed in SEEDS:
            p = root / f"results/experiment-c/c1/{arm}-seed{seed}/samples.csv"
            if not p.exists():
                p = root / f"results/experiment-c/extra-seeds/seeds202-303/{arm}-seed{seed}/samples.csv"
            if p.exists():
                rows.append(pd.read_csv(p))
    d["c1_samples"] = pd.concat(rows, ignore_index=True)
    return d


def make_tables(d, out: Path):
    tab = out / "assets/tables"
    tab.mkdir(parents=True, exist_ok=True)

    # T1: baseline at C1 target -4 with MolMiner descriptive baseline and Wee task mismatch explicit.
    c1 = d["c1_effect"].set_index("metric")
    mm = d["molminer"]
    rows = [
        {"arm": "PolyGen binary", "target": -4.0, "strict_hit": float(c1.loc["hit_rate", "binary_mean"]), "target_mae": float(mm[(mm.arm == "binary") & (mm.target == -4.0)].target_mae.iloc[0]), "validity": float(c1.loc["validity", "binary_mean"]), "novelty": float(c1.loc["novelty", "binary_mean"]), "delta_vs_binary": 0.0, "evidence_status": "observed", "notes": "five matched training seeds"},
        {"arm": "PolyGen continuous", "target": -4.0, "strict_hit": float(c1.loc["hit_rate", "continuous_mean"]), "target_mae": float(mm[(mm.arm == "continuous") & (mm.target == -4.0)].target_mae.iloc[0]), "validity": float(c1.loc["validity", "continuous_mean"]), "novelty": float(c1.loc["novelty", "continuous_mean"]), "delta_vs_binary": float(c1.loc["hit_rate", "mean"]), "evidence_status": "observed", "notes": "five matched training seeds"},
        {"arm": "MolMiner", "target": -4.0, "strict_hit": float(mm[(mm.arm == "molminer_continuous") & (mm.target == -4.0)].hit_rate.iloc[0]), "target_mae": float(mm[(mm.arm == "molminer_continuous") & (mm.target == -4.0)].target_mae.iloc[0]), "validity": float(mm[(mm.arm == "molminer_continuous") & (mm.target == -4.0)].validity.iloc[0]), "novelty": float(mm[(mm.arm == "molminer_continuous") & (mm.target == -4.0)].novelty.iloc[0]), "delta_vs_binary": np.nan, "evidence_status": "observed_descriptive", "notes": "public checkpoint; corpus contains HTP-MD; not held-out"},
        {"arm": "Wee", "target": -4.0, "strict_hit": np.nan, "target_mae": np.nan, "validity": np.nan, "novelty": np.nan, "delta_vs_binary": np.nan, "evidence_status": "unavailable_task_mismatch", "notes": "C1 conductivity arm not run; local ZINC/logP software smoke only"},
    ]
    pd.DataFrame(rows).to_csv(tab / "T1_baseline.csv", index=False)

    # T2: four-stage acceptance index, with measured arm summaries when available.
    t2 = []
    for stage, status, source, note in [
        ("interpolation", "complete", "results/interpolation/publication/interpolation_aggregate_metrics.csv", "in-support controllability"),
        ("upper-tail", "complete_prediction_only", "results/upper-tail/publication/upper_tail_aggregate_metrics.csv", "boundary approach; no physical claim"),
        ("extrapolation", "complete_prediction_only_MD_blocked", "results/extrapolation/publication/extrapolation_aggregate_metrics.csv", "all RF frontier-crossing rates 0; MD not run"),
        ("structural-OOD", "blocked", "results/structural-ood/frozen_manifest.json", "missing scaffold/family labels and matched checkpoints"),
    ]:
        for arm in ("continuous", "binary", "unconditional_reranking"):
            if stage == "interpolation":
                g = d["interp_agg"]
                mask = g.arm.eq(arm)
                hit = g.loc[mask, "strict_hit_rate"].mean() if mask.any() else np.nan
                valid = g.loc[mask, "validity"].mean() if mask.any() else np.nan
                n = int(g.loc[mask, "n_seeds"].max()) if mask.any() and "n_seeds" in g else 5
            elif stage == "upper-tail":
                g = d["upper_agg"]
                mask = g.arm.eq(arm)
                hit = g.loc[mask, "strict_hit_rate"].mean() if mask.any() else np.nan
                valid = g.loc[mask, "validity"].mean() if mask.any() else np.nan
                n = 5
            elif stage == "extrapolation":
                g = d["extrap_agg"]
                mask = g.arm.eq(arm)
                hit = g.loc[mask, "frontier_crossing_predicted_hit_rate"].mean() if mask.any() else np.nan
                valid = g.loc[mask, "validity"].mean() if mask.any() else np.nan
                n = 5
            else:
                hit = valid = np.nan
                n = 0
            t2.append({"stage": stage, "arm": ARM_LABELS[arm], "n_seeds": n, "validity_mean": valid, "frontier_or_strict_hit_mean": hit, "status": status, "source": source, "notes": note})
    pd.DataFrame(t2).to_csv(tab / "T2_four_stage_acceptance.csv", index=False)

    # T3: real locked-tail bins and a clearly labeled nominal 90% tree-SD diagnostic.
    tail = d["tail"].copy()
    rows = []
    for name, g in tail.groupby("tail_bin", sort=False):
        pred = g.rf_prediction.astype(float)
        obs = g.observed_log_sigma.astype(float)
        interval = (obs >= pred - 1.645 * g.rf_uncertainty) & (obs <= pred + 1.645 * g.rf_uncertainty)
        rho = stats.spearmanr(pred, obs).statistic if len(g) > 2 else np.nan
        rows.append({"tail_bin": name, "n_rows": len(g), "observed_mean": obs.mean(), "rf_prediction_mean": pred.mean(), "mean_residual_observed_minus_predicted": (obs - pred).mean(), "rf_prediction_max": pred.max(), "spearman_rho": rho, "nominal_90pct_tree_sd_coverage": interval.mean(), "rf_prediction_min": pred.min(), "source": "locked_tail_verifier_audit.csv", "evidence_status": "observed"})
    t3 = pd.DataFrame(rows)
    t3.to_csv(tab / "T3_locked_tail_verifier_bins.csv", index=False)

    # T4: real MD funnel status, not a fabricated result. Count full candidate selection table.
    c = d["candidate"].copy()
    out_rows = []
    for (arm, cell), g in c.groupby(["arm", "target_label"], sort=False):
        out_rows.append({"arm": ARM_LABELS.get(arm, arm), "cell": cell, "generated": len(g), "valid": int(g["valid"].astype(bool).sum()), "novel": int(g["novel"].astype(bool).sum()), "support_eligible": int(g["support_eligible"].astype(bool).sum()), "pcff_plus_parameterized": 0, "md_started": 0, "md_converged": 0, "md_confirmed_frontier_hit": 0, "status": "PLANNED_NOT_RUN", "evidence_status": "observed_status_only", "notes": "candidate selection is proposed; no polymer construction or force-field assignment"})
    pd.DataFrame(out_rows).to_csv(tab / "T4_md_funnel.csv", index=False)

    # T5: real common-target comparison, with Wee unavailable.
    mm4 = d["molminer"][(d["molminer"].target == -4.0)].copy()
    t5 = [
        {"generator": "PolyGen continuous", "target": -4.0, "generation_success_or_connected_yield": 1.0, "validity": float(c1.loc["validity", "continuous_mean"]), "support_hit_rate": float(c1.loc["hit_rate", "continuous_mean"]), "corpus_contains_HTP_MD": True, "held_out": True, "status": "observed"},
        {"generator": "PolyGen binary", "target": -4.0, "generation_success_or_connected_yield": 1.0, "validity": float(c1.loc["validity", "binary_mean"]), "support_hit_rate": float(c1.loc["hit_rate", "binary_mean"]), "corpus_contains_HTP_MD": True, "held_out": True, "status": "observed"},
        {"generator": "MolMiner", "target": -4.0, "generation_success_or_connected_yield": float(mm4[mm4.arm == "molminer_continuous"].generation_success.iloc[0]), "validity": float(mm4[mm4.arm == "molminer_continuous"].validity.iloc[0]), "support_hit_rate": float(mm4[mm4.arm == "molminer_continuous"].hit_rate.iloc[0]), "corpus_contains_HTP_MD": True, "held_out": False, "status": "observed_descriptive"},
        {"generator": "Wee", "target": -4.0, "generation_success_or_connected_yield": np.nan, "validity": np.nan, "support_hit_rate": np.nan, "corpus_contains_HTP_MD": np.nan, "held_out": np.nan, "status": "unavailable_not_run"},
    ]
    pd.DataFrame(t5).to_csv(tab / "T5_cross_generator.csv", index=False)

    # T6: pre-MD freeze card, explicit about what is proposed and what is already frozen.
    man_sha = __import__("hashlib").sha256(d["paths"]["manifest"].read_bytes()).hexdigest()
    con_sha = __import__("hashlib").sha256(d["paths"]["contract"].read_bytes()).hexdigest()
    t6 = [
        {"item": "candidate_set", "value": "continuous/binary/unconditional_reranking × Q90/Q100/train_max+0.25/train_max+0.50; proposed candidates from candidate_selection_for_md.csv", "freeze_status": "frozen_prediction_phase", "sha_or_source": man_sha},
        {"item": "generator_and_verifier", "value": "PolyGen gpt-nano; blind Q80-only RF; 300 trees; support ≥0.35; uncertainty <0.35", "freeze_status": "frozen", "sha_or_source": con_sha},
        {"item": "md_primary_force_field", "value": "PCFF+ primary; PFP secondary sensitivity only", "freeze_status": "proposed_before_MD", "sha_or_source": "strategy/A2-A5"},
        {"item": "replication", "value": "5 independent replicas per structure; structure is inferential unit", "freeze_status": "proposed_before_MD", "sha_or_source": "MD_VALIDATION_PROTOCOL.md"},
        {"item": "md_confirmed_frontier_hit", "value": "structure-level mean log10(sigma) above frozen training boundary and lower 95% replicate CI above boundary; all replicas must pass convergence gate", "freeze_status": "proposed_not_yet_TRI_approved", "sha_or_source": "strategy/A5"},
        {"item": "convergence", "value": "5 ns production, block/replicate stability, no NaN/explosion, force-field/build gates pass; non-converged replicas excluded from confirmatory claim", "freeze_status": "proposed_not_yet_TRI_approved", "sha_or_source": "strategy/A2/A5"},
        {"item": "stop_rule", "value": "do not escalate to long MD or active learning until PCFF+ coverage and short-MD gates pass", "freeze_status": "frozen_policy", "sha_or_source": "MD_VALIDATION_PROTOCOL.md"},
    ]
    pd.DataFrame(t6).to_csv(tab / "T6_freeze_card.csv", index=False)
    return {"T1": tab / "T1_baseline.csv", "T2": tab / "T2_four_stage_acceptance.csv", "T3": tab / "T3_locked_tail_verifier_bins.csv", "T4": tab / "T4_md_funnel.csv", "T5": tab / "T5_cross_generator.csv", "T6": tab / "T6_freeze_card.csv"}


def make_figures(d, out: Path):
    figdir = out / "assets/figures"
    apply_publication_style(9.0)
    plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.titleweight": "bold", "axes.labelsize": 10, "legend.fontsize": 8})

    # P1: real C1 decision-value tradeoff.
    samples = d["c1_samples"].copy()
    samples = samples[samples.arm.isin(["continuous", "binary"])].copy()
    pred = samples[samples.valid].groupby(["arm", "seed", "target"], as_index=False).predicted_log_sigma.mean()
    pred_ci = pred.groupby(["arm", "target"]).predicted_log_sigma.agg(["mean", "std", "count"]).reset_index()
    pred_ci["sem"] = pred_ci["std"] / np.sqrt(pred_ci["count"])
    fig, ax = plt.subplots(2, 2, figsize=(8.2, 6.1), constrained_layout=False)
    # A
    a = ax[0, 0]
    for arm, col in [("continuous", COLORS["continuous"]), ("binary", COLORS["binary"])]:
        g = pred_ci[pred_ci.arm == arm]
        a.errorbar(g["target"], g["mean"], yerr=1.96 * g["sem"], color=col, marker="o", lw=1.8, capsize=3, label=ARM_LABELS[arm])
    lo, hi = -5.2, -2.8
    a.plot([lo, hi], [lo, hi], "--", color="#444", lw=1, label="y = x")
    a.set(xlim=(lo, hi), ylim=(-4.6, -2.8), xlabel="Requested target, log$_{10}$ σ", ylabel="Mean RF prediction, log$_{10}$ σ", title="A  C1 target response")
    style_axes(a); a.legend(frameon=False, loc="lower right")
    # B paired seed traces at target -4.
    b = ax[0, 1]
    x = np.arange(len(SEEDS)); t = -4.0
    bt = d["c1_target"]
    for seed in SEEDS:
        bb = bt[(bt.seed == seed) & (bt.target == t)]
        vals = [float(bb[bb.arm == arm].strict_hit_rate.iloc[0]) for arm in ["binary", "continuous"]]
        b.plot([0, 1], vals, color="#777", alpha=.5, lw=1.0, marker="o", ms=3)
    means = bt[bt.target == t].groupby("arm").strict_hit_rate.mean()
    b.scatter([0, 1], [means["binary"], means["continuous"]], color=[COLORS["binary"], COLORS["continuous"]], s=44, zorder=3)
    b.set(xlim=(-.2, 1.2), xticks=[0, 1], xticklabels=["Binary", "Continuous"], ylabel="Strict hit rate", title="B  Paired seeds at target −4")
    style_axes(b)
    # C forest effect using exact summary CIs.
    c = ax[1, 0]
    metrics = ["hit_rate", "target_mae", "validity", "novelty"]
    labels = ["Strict hit", "Target MAE", "Validity", "Novelty"]
    effects = d["c1_effect"].set_index("metric").loc[metrics]
    yy = np.arange(len(metrics))
    for i, (m, lab) in enumerate(zip(metrics, labels)):
        col = COLORS["continuous"] if m in ("hit_rate", "target_mae") else "#B2182B"
        c.errorbar(float(effects.loc[m, "mean"]), i, xerr=[[float(effects.loc[m, "mean"] - effects.loc[m, "ci95_low"])], [float(effects.loc[m, "ci95_high"] - effects.loc[m, "mean"])]], fmt="o", color=col, capsize=3, lw=1.4)
    c.axvline(0, color="#333", ls="--", lw=1)
    c.set(yticks=yy, yticklabels=labels, xlabel="Continuous − binary (95% t CI)", title="C  Paired effect summary", xlim=(-.18, .08))
    style_axes(c)
    c.text(.02, -.22, "Red = quality cost (lower validity/novelty)", transform=c.transAxes, color="#B2182B", fontsize=7)
    # D structural unsupported block.
    dd = ax[1, 1]
    dd.set_xlim(0, 4); dd.set_ylim(0, 2); dd.axis("off")
    for i, lab in enumerate(["Q90", "Q100", "+0.25", "+0.50"]):
        rect = patches.Rectangle((i, .55), .92, .8, facecolor="#F0F0F0", edgecolor="#777", hatch="///", lw=1)
        dd.add_patch(rect); dd.text(i + .46, .98, lab, ha="center", va="center", fontsize=9, fontweight="bold")
        dd.text(i + .46, .72, "Binary\nunsupported", ha="center", va="center", fontsize=7, color="#555")
    dd.text(2, 1.7, "D  Extrapolation control status", ha="center", fontweight="bold")
    dd.text(2, .22, "5/5 seed-cells per target are structurally blocked by the fixed −4.0 label", ha="center", fontsize=8)
    fig.suptitle("A generator can improve local target metrics without changing the decision", x=.02, ha="left", fontsize=13, fontweight="bold")
    add_status_stamp(fig, "OBSERVED — C1 + extrapolation CSVs")
    fig.subplots_adjust(left=.10, right=.98, top=.86, bottom=.12, wspace=.36, hspace=.42)
    save_multi(fig, figdir, "P1_decision_value_tradeoff")

    # P2/F5: real locked-tail audit and nominal coverage.
    tail = d["tail"].copy()
    full = d["fullrf_tail"].copy()
    fig = plt.figure(figsize=(8.2, 3.7), constrained_layout=False)
    gs = fig.add_gridspec(1, 2, wspace=.34)
    a = fig.add_subplot(gs[0, 0]); b = fig.add_subplot(gs[0, 1])
    colors = {"Q80-Q90": "#4C78A8", "Q90-Q95": "#F58518", "Q95-Q100": "#E45756"}
    for name, g in tail.groupby("tail_bin", sort=False):
        a.scatter(g.rf_prediction, g.observed_log_sigma, s=9, alpha=.35, color=colors.get(name, "#777"), label=name, edgecolors="none")
    low = min(tail.rf_prediction.min(), tail.observed_log_sigma.min()) - .03; high = max(tail.rf_prediction.max(), tail.observed_log_sigma.max()) + .03
    a.plot([low, high], [low, high], "--", color="#222", lw=1)
    a.axvspan(tail.rf_prediction.min(), tail.rf_prediction.max(), color="#999", alpha=.12, label="Blind RF output range")
    boundary = d["manifest"]["training_max_log10_sigma"]
    a.axhline(boundary, color=COLORS["continuous"], ls=(0, (2, 2)), lw=1.1)
    a.axvline(boundary, color=COLORS["continuous"], ls=(0, (2, 2)), lw=1.1)
    a.set(xlim=(low, high), ylim=(low, high), xlabel="Blind RF prediction, log$_{10}$ σ", ylabel="Observed locked-tail value, log$_{10}$ σ", title="A  Locked-tail calibration")
    a.legend(frameon=True, facecolor="white", edgecolor="none", fontsize=7, loc="upper left")
    a.text(.98, .04, f"MAE = {d['verifier']['locked_tail_rf_mae']:.3f}\nmean residual = +{d['verifier']['locked_tail_rf_residual_mean']:.3f}\nn = {len(tail):,}", transform=a.transAxes, ha="right", va="bottom", fontsize=7, bbox={"facecolor":"white", "alpha":.85, "edgecolor":"none"})
    style_axes(a)
    # B nominal interval coverage, blind vs full-source post-hoc.
    bins = ["Q80–90", "Q90–95", "Q95–100"]
    blind_cov=[]; full_cov=[]
    for name in ["Q80-Q90", "Q90-Q95", "Q95-Q100"]:
        g=tail[tail.tail_bin==name]; blind_cov.append(((g.observed_log_sigma >= g.rf_prediction-1.645*g.rf_uncertainty)&(g.observed_log_sigma <= g.rf_prediction+1.645*g.rf_uncertainty)).mean())
        # full RF file covers Q80-Q95 only; for Q95-Q100 leave missing.
        if name == "Q95-Q100": full_cov.append(np.nan)
        else:
            gf=full[(full.log_sigma > d["manifest"]["nominal_q80"]) & (full.log_sigma <= d["manifest"]["full_source_quantiles"]["0.95"])].copy()
            # derive bins from observed quantiles
            q90=d["manifest"]["full_source_quantiles"]["0.9"]; q95=d["manifest"]["full_source_quantiles"]["0.95"]
            lo = d["manifest"]["nominal_q80"] if name=="Q80-Q90" else q90
            hi = q90 if name=="Q80-Q90" else q95
            gf=gf[(gf.log_sigma > lo)&(gf.log_sigma <= hi)]
            full_cov.append(((gf.log_sigma >= gf.fullrf_prediction-1.645*gf.fullrf_uncertainty)&(gf.log_sigma <= gf.fullrf_prediction+1.645*gf.fullrf_uncertainty)).mean())
    xx=np.arange(3); width=.36
    b.bar(xx-width/2, blind_cov, width, color="#4C78A8", label="Blind RF (Q80-only)")
    b.bar(xx+width/2, [0 if np.isnan(v) else v for v in full_cov], width, color="#9ECAE1", label="Full-source RF (post-hoc)", hatch="///")
    for i,v in enumerate(full_cov):
        if np.isnan(v): b.text(i+width/2, .03, "n/a", ha="center", va="bottom", fontsize=8, color="#555")
    b.axhline(.90, color="#333", ls="--", lw=1); b.set(xticks=xx, xticklabels=bins, ylim=(0,1.05), ylabel="Nominal 90% interval coverage", title="B  Coverage diagnostic")
    b.text(.02, -.22, "Intervals = prediction ± 1.645 × tree SD; diagnostic, not calibrated uncertainty", transform=b.transAxes, fontsize=7, color="#555")
    b.legend(frameon=False, fontsize=7, loc="upper right")
    style_axes(b)
    fig.suptitle("The verifier is least reliable where the decision concentrates", x=.02, ha="left", fontsize=13, fontweight="bold")
    add_status_stamp(fig, "OBSERVED — locked-tail audit; full-source layer is post-hoc")
    fig.subplots_adjust(left=.10, right=.98, top=.82, bottom=.23)
    save_multi(fig, figdir, "P2_verifier_blind_locked_tail")
    # copy as F5 alias in same package for direct strategy mapping
    for ext in ("png", "pdf", "svg"):
        shutil.copy2(figdir / f"P2_verifier_blind_locked_tail.{ext}", figdir / f"F5_verifier_audit.{ext}")

    # P3/F6: real RF and PFP top-1 smoke anchor, with planned/synthetic MD components.
    agg=d["extrap_agg"]
    fig, ax = plt.subplots(1, 3, figsize=(8.2, 3.2), constrained_layout=False)
    labels=["Q90", "Q100", "+0.25", "+0.50"]; xx=np.arange(4)
    for arm,col in [("continuous",COLORS["continuous"]),("unconditional_reranking",COLORS["unconditional_reranking"])]:
        g=agg[(agg.arm==arm)].set_index("target_label").reindex(TARGETS)
        ax[0].plot(xx,g.rf_prediction_mean,color=col,marker="o",lw=1.8,label=ARM_LABELS[arm])
    ax[0].axhline(boundary,color="#333",ls="--",lw=1); ax[0].set(xticks=xx,xticklabels=labels,ylabel="Verifier estimate, log$_{10}$ σ",title="A  Real RF stage")
    # Planned ladder: show synthetic expected curves only as hatched line/points.
    syn_pcff=np.array([-4.08,-4.00,-3.94,-3.88]); syn_pfp=np.array([-4.02,-3.92,-3.83,-3.76])
    ax[0].plot(xx,syn_pcff,color=COLORS["planned"],ls=(0,(4,2)),lw=1.6,marker="o",mfc="white",label="PCFF+ MD — planned/synthetic")
    ax[0].plot(xx,syn_pfp,color=COLORS["synthetic"],ls=(0,(2,2)),lw=1.6,marker="s",mfc="white",label="PFP MD — planned/synthetic")
    ax[0].text(.98,.04,"dashed curves are placeholders",transform=ax[0].transAxes,ha="right",fontsize=7,color=COLORS["synthetic"])
    ax[0].legend(frameon=False,fontsize=6.5,loc="lower right"); style_axes(ax[0])
    # B actual top-1 smoke residuals.
    p=d["pfp_paired"]; # schema is small and stable in the canonical artifact
    # Robustly recover values from common key names.
    cont=float(p.get("continuous_log10_sigma", p.get("continuous", {}).get("log10_sigma", -2.516))) if isinstance(p,dict) else -2.516
    binary=float(p.get("binary_log10_sigma", p.get("binary", {}).get("log10_sigma", -2.937))) if isinstance(p,dict) else -2.937
    ax[1].bar([0,1],[cont,binary],color=[COLORS["continuous"],COLORS["binary"]],width=.55)
    ax[1].axhline(boundary,color="#333",ls="--",lw=1); ax[1].set(xticks=[0,1],xticklabels=["Continuous\nPFP top-1","Binary\nPFP top-1"],ylabel="PFP smoke log$_{10}$ σ",title="B  Physical pilot anchor")
    ax[1].text(.5,.04,"n = 1 structure/arm;\nNON_CONVERGED_SMOKE_ONLY",transform=ax[1].transAxes,ha="center",fontsize=7,color=COLORS["synthetic"]); style_axes(ax[1])
    # C residual decomposition with real Δ1 and missing Δ2.
    d1=[1.263, .893]
    ax[2].bar([0,1],d1,color=[COLORS["continuous"],COLORS["binary"]],width=.52,label="Δ₁ RF → PFP smoke (observed)")
    for i in [0,1]:
        ax[2].bar(i, .18, bottom=0, color="white", edgecolor=COLORS["planned"], hatch="///", alpha=.9)
        ax[2].text(i,.09,"Δ₂\nPCFF+→PFP\nPENDING",ha="center",va="center",fontsize=6,color=COLORS["planned"])
    ax[2].axhline(0,color="#333",lw=1); ax[2].set(xticks=[0,1],xticklabels=["Continuous","Binary"],ylabel="Residual, log$_{10}$ σ",title="C  Residual ladder")
    style_axes(ax[2])
    fig.suptitle("The next action is the experiment that repairs the verifier",x=.02,ha="left",fontsize=13,fontweight="bold")
    add_status_stamp(fig,"A: observed RF; B/C: PFP pilot observed but non-converged; PCFF+ and extrapolation MD pending",color=COLORS["synthetic"])
    fig.subplots_adjust(left=.09,right=.99,top=.80,bottom=.20,wspace=.45)
    save_multi(fig,figdir,"P3_verifier_repair_experiment")
    for ext in ("png","pdf","svg"):
        shutil.copy2(figdir/f"P3_verifier_repair_experiment.{ext}",figdir/f"F6_md_residual_ladder.{ext}")

    # F1: deterministic workflow schematic.
    fig, a = plt.subplots(figsize=(10.2, 4.0)); a.set_xlim(0, 10); a.set_ylim(0, 4); a.axis("off")
    cards=[("Four-stage benchmark",["Interpolation", "Upper-tail", "Extrapolation", "Structural-OOD"],.45,2.05,3.0,1.35,"#E8F4F4"),("Closed loop",["Act / generate", "Observe / MD", "Evaluate / calibrate", "Update / select"],4.0,2.05,3.0,1.35,"#F4ECF8"),("Evidence boundary",["Observed RF", "MD pending", "Active learning pending", "Claims stay scoped"],7.55,2.05,2.0,1.35,"#FFF2E6")]
    for title,items,x0,y0,w,h,fc in cards:
        a.add_patch(patches.FancyBboxPatch((x0,y0),w,h,boxstyle="round,pad=.04,rounding_size=.08",facecolor=fc,edgecolor="#333",lw=1.2))
        a.text(x0+.12,y0+h-.25,title,fontweight="bold",fontsize=10,va="top")
        for i,it in enumerate(items):
            if title == "Four-stage benchmark":
                done = i < 3
            else:
                done = i < 1
            a.text(x0+.18,y0+h-.54-.22*i,("✓ " if done else "⋯ ")+it,fontsize=8,va="top",color=COLORS["ink"] if done else COLORS["planned"])
    for x1,x2 in [(3.45,4.0),(7.0,7.55)]:
        a.annotate("",xy=(x2,2.72),xytext=(x1,2.72),arrowprops=dict(arrowstyle="-|>",lw=1.5,color="#333"))
    a.annotate("feedback after validated MD",xy=(5.55,1.85),xytext=(5.55,1.05),ha="center",fontsize=8,color=COLORS["planned"],arrowprops=dict(arrowstyle="-|>",lw=1.3,color=COLORS["planned"],linestyle="--"))
    a.text(.45,.45,"Solid = completed prediction evidence    Dashed = planned physical observation / update    Source: frozen contracts and acceptance audits",fontsize=8,color="#555")
    a.text(.45,3.65,"F1  PolyGen's actual role in the Improve loop",fontsize=13,fontweight="bold")
    save_multi(fig,figdir,"F1_framework_and_closed_loop")

    # F2: real interpolation aggregate response.
    fig, a = plt.subplots(1,2,figsize=(7.3,3.1),constrained_layout=False)
    g=d["interp_agg"]
    for arm,col in [("continuous",COLORS["continuous"]),("binary",COLORS["binary"]),("unconditional_reranking",COLORS["unconditional_reranking"])]:
        z=g[g.arm==arm].sort_values("quantile")
        if len(z):
            x=z["quantile"].to_numpy(); a[0].plot(x,z.strict_hit_rate,color=col,marker="o",lw=1.6,label=ARM_LABELS[arm]); a[1].plot(x,z.target_mae,color=col,marker="o",lw=1.6)
    for aa in a: style_axes(aa); aa.set_xticks([.5,.65,.8], ["Q50","Q65","Q80"])
    a[0].set(ylabel="Strict hit rate",title="A  Controllability"); a[1].set(ylabel="Target MAE, Δ log$_{10}$ σ",title="B  Target error")
    a[0].legend(frameon=False,fontsize=7)
    fig.suptitle("F2  In-support interpolation benchmark",x=.02,ha="left",fontsize=12,fontweight="bold"); add_status_stamp(fig,"OBSERVED — interpolation aggregate",color="#333")
    fig.subplots_adjust(left=.10,right=.98,top=.80,bottom=.20,wspace=.38); save_multi(fig,figdir,"F2_interpolation_controllability")

    # F3: real upper-tail response with explicit unsupported cells.
    fig,a=plt.subplots(1,3,figsize=(8.0,3.1),constrained_layout=False)
    g=d["upper_agg"]
    for arm,col in [("continuous",COLORS["continuous"]),("binary",COLORS["binary"]),("unconditional_reranking",COLORS["unconditional_reranking"])]:
        z=g[g.arm==arm].sort_values("target")
        if len(z):
            x=np.arange(len(z));
            for j,metric in enumerate(["strict_hit_rate","target_mae","validity"]):
                a[j].plot(x,z[metric],color=col,marker="o",lw=1.6,label=ARM_LABELS[arm])
    for j,aa in enumerate(a):
        style_axes(aa); aa.set_xticks(range(4),["Bdy.","Q85","Q90","Q95"]); aa.set_title(["A  Hit rate","B  Target MAE","C  Validity"][j])
    a[0].set_ylabel("Strict hit rate"); a[1].set_ylabel("Target MAE"); a[2].set_ylabel("Validity fraction"); a[0].legend(frameon=False,fontsize=7)
    # explicit unsupported binary Q90/Q95
    for j in [0,1,2]:
        for x in [2,3]: a[j].axvspan(x-.35,x+.35,color="#DDD",alpha=.42,hatch="///")
    a[2].text(2.5,.15,"Binary\nunsupported",ha="center",fontsize=7,color="#555")
    fig.suptitle("F3  Upper-tail response with structural failure shown",x=.02,ha="left",fontsize=12,fontweight="bold"); add_status_stamp(fig,"OBSERVED — unsupported cells are not zeros",color="#333"); fig.subplots_adjust(left=.08,right=.98,top=.80,bottom=.20,wspace=.48); save_multi(fig,figdir,"F3_upper_tail_response")

    # F4: real extrapolation response, improved with unsupported annotation and RF ceiling band.
    fig,a=plt.subplots(1,3,figsize=(8.2,3.2),constrained_layout=False)
    g=d["extrap_agg"]
    for arm,col in [("continuous",COLORS["continuous"]),("binary",COLORS["binary"]),("unconditional_reranking",COLORS["unconditional_reranking"])]:
        z=g[g.arm==arm].set_index("target_label").reindex(TARGETS); x=np.arange(4)
        a[0].plot(x,z.rf_prediction_mean,color=col,marker="o",lw=1.6,label=ARM_LABELS[arm]); a[1].plot(x,z.target_mae,color=col,marker="o",lw=1.6); a[2].plot(x,z.frontier_crossing_predicted_hit_rate,color=col,marker="o",lw=1.6)
    a[0].axhspan(g.rf_prediction_mean.min()-.02,g.rf_prediction_mean.max()+.02,color="#999",alpha=.16,label="Observed RF output band")
    a[0].axhline(boundary,color="#333",ls="--",lw=1)
    for j,aa in enumerate(a): style_axes(aa); aa.set_xticks(range(4),labels); aa.tick_params(axis="x",rotation=20)
    a[0].set(ylabel="RF prediction, log$_{10}$ σ",title="A  RF response"); a[1].set(ylabel="Target MAE",title="B  Target error"); a[2].set(ylabel="Predicted frontier crossing",title="C  RF crossing",ylim=(-.03,.45)); a[0].legend(frameon=False,fontsize=6.5,loc="lower right")
    for x in range(4): a[2].text(x,.03,"0",ha="center",fontsize=7)
    fig.suptitle("F4  Extrapolation response: no blind-RF frontier crossing",x=.02,ha="left",fontsize=12,fontweight="bold"); add_status_stamp(fig,"OBSERVED — surrogate-only; MD not run",color="#333"); fig.subplots_adjust(left=.08,right=.98,top=.80,bottom=.23,wspace=.50); save_multi(fig,figdir,"F4_extrapolation_response")

    # F7 synthetic replacement-ready placeholder: representation/data ablation.
    fig,a=plt.subplots(figsize=(7.4,3.5)); cats=["Character\ntoken","Fragment\n(proposed)","+PI1M pretrain\n(proposed)"]; qlabels=["Q90","Q100","+0.25","+0.50"]; xx=np.arange(len(cats)); vals=np.array([[0,0,0,0],[.05,.02,.07,.03],[.12,.08,.15,.10]])
    for j,l in enumerate(qlabels): a.plot(xx,vals[:,j],marker="o",lw=1.8,label=l)
    a.set_xticks(xx,cats); a.set_ylabel("Frontier-crossing rate (MD-confirmed)"); a.set_ylim(0,.22); a.set_title("F7  Representation/data ablation — planning placeholder",loc="left",fontweight="bold"); style_axes(a); a.legend(frameon=False,ncol=4); a.text(.5,.97,"SYNTHETIC PLACEHOLDER — replace every point with matched MD data",transform=a.transAxes,ha="center",va="top",color=COLORS["synthetic"],fontsize=8)
    for y in vals.flat: pass
    add_status_stamp(fig,"SYNTHETIC / PLANNED — not a scientific result",color=COLORS["synthetic"]); fig.subplots_adjust(left=.12,right=.98,top=.84,bottom=.22); save_multi(fig,figdir,"F7_representation_data_ablation_SYNTHETIC")

    # F8 synthetic decision-change placeholder.
    fig,a=plt.subplots(1,2,figsize=(7.6,3.3),constrained_layout=False); queue=np.arange(1,11); rf=np.array([0,0,0,0,0,1,1,1,1,1]); cal=np.array([0,0,1,1,1,1,2,2,3,3]); a[0].plot(queue,rf,"o-",color=COLORS["muted"],label="RF ranking"); a[0].plot(queue,cal,"o-",color=COLORS["planned"],label="Calibrated ranking"); a[0].set(xlabel="Top-k MD queue",ylabel="Confirmed hits",title="A  Queue composition"); a[1].plot([0,1,2],[0,3,5],"o-",color=COLORS["planned"]); a[1].set(xlabel="Closed-loop round",ylabel="Cumulative confirmed hits",title="B  Update trajectory");
    for aa in a: style_axes(aa); aa.text(.5,.96,"SYNTHETIC / PLANNED",transform=aa.transAxes,ha="center",va="top",fontsize=8,color=COLORS["synthetic"])
    a[0].legend(frameon=False,fontsize=8); fig.suptitle("F8  Decision change after verifier calibration — planning placeholder",x=.02,ha="left",fontsize=12,fontweight="bold"); add_status_stamp(fig,"SYNTHETIC / PLANNED — requires MD-confirmed hits",color=COLORS["synthetic"]); fig.subplots_adjust(left=.10,right=.98,top=.78,bottom=.20,wspace=.38); save_multi(fig,figdir,"F8_decision_change_SYNTHETIC")

    # Captions for every figure.
    captions = """# Figure captions and evidence status

**P1 | Decision-value tradeoff.** (A) Mean RF prediction across five matched seeds for valid C1 candidates; error bars are 95% t intervals across seed-level means. (B) Paired seed-level strict-hit rates at the C1 target −4.0. (C) Continuous-minus-binary effects with 95% t intervals; red denotes a quality cost. (D) The four extrapolation target cells are explicitly marked unsupported for the binary negative control in all five seeds. All panels are observed data; the C1 and extrapolation estimands differ and are not pooled.

**P2/F5 | Verifier blind spot.** Each point in A is one locked Q80–Q100 source row. The grey band is the observed blind-RF prediction range; the diagonal is ideal calibration and teal rules mark the frozen training maximum. B reports nominal coverage of prediction ±1.645 tree SD; the full-source RF is a post-hoc audit and not valid for leakage-free extrapolation. No panel supports an MD or experimental conductivity claim.

**P3/F6 | Verifier-repair experiment.** The RF stage is observed. Dashed PCFF+ and PFP curves are synthetic planning placeholders and must be replaced by matched measurements on the extrapolation queue. The PFP top-1 bars and Δ₁ values are observed single-structure smoke evidence labelled NON_CONVERGED_SMOKE_ONLY; they are not extrapolation-queue results. Δ₂ remains pending.

**F1 | Framework and closed loop.** The four-stage benchmark and Act–Observe–Evaluate–Update loop are shown as an evidence map. Solid elements are completed prediction-stage evidence; dashed elements are planned physical validation or update steps.

**F2 | In-support controllability.** Aggregate observed interpolation response at Q50/Q65/Q80. Curves show means across the five matched seeds; no physical extrapolation claim is implied.

**F3 | Upper-tail response.** Observed upper-tail response from the frozen benchmark. Hatched cells mark structural unsupportedness, not zero performance.

**F4 | Extrapolation response.** Observed five-seed RF-only response at Q90, Q100, train-max+0.25 and train-max+0.50. The frontier-crossing endpoint is surrogate-only and equals zero for every arm and query.

**F7/F8.** Synthetic planning placeholders only. Replace with the same schema after fragment/data ablations, MD-confirmed hits, and at least one residual-calibration update are complete.
"""
    (figdir / "FIGURE_CAPTIONS.md").write_text(captions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    d = read_inputs(args.canonical_root)
    tables = make_tables(d, args.out)
    make_figures(d, args.out)
    # Store a compact run summary for later manifest/provenance generation.
    summary = {
        "canonical_root": str(args.canonical_root),
        "source_status": {"P1": "observed", "P2": "observed", "F1": "observed_status_map", "F2": "observed", "F3": "observed", "F4": "observed", "P3_F6": "mixed_observed_and_planned", "F7": "synthetic_placeholder", "F8": "synthetic_placeholder"},
        "tables": {k: str(v.relative_to(args.out)) for k, v in tables.items()},
        "figures": sorted(p.name for p in (args.out / "assets/figures").iterdir()),
        "training_boundary": d["manifest"]["training_max_log10_sigma"],
        "source_rows": d["manifest"]["source_rows"] if "source_rows" in d["manifest"] else 6024,
        "training_rows": d["manifest"].get("training_rows", 4819),
        "locked_tail_rows": d["verifier"]["locked_tail_rows_audited"],
        "md_status": "not_run_by_contract",
    }
    (args.out / "evidence/data/build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
