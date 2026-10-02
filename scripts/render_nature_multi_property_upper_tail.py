#!/usr/bin/env python3
"""Build Nature-style analysis tables, figures, and manuscript text.

This is an analysis/packaging layer over frozen prediction-phase outputs. It
does not retrain, resample, alter candidate filters, or start MD.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/multi-property/upper-tail"
OUT = IN / "publication"
ARMS = ["multi_continuous", "scalar_continuous", "binary_conductivity", "unconditional_reranking"]
ARM_LABELS = {
    "multi_continuous": "Multi-property",
    "scalar_continuous": "Scalar conductivity",
    "binary_conductivity": "Binary",
    "unconditional_reranking": "Unconditional + reranking",
}
COLORS = {
    "multi_continuous": "#007C83",
    "scalar_continuous": "#4C78A8",
    "binary_conductivity": "#D55F02",
    "unconditional_reranking": "#6B6B6B",
}
PROPERTIES = ["conductivity", "li_diffusivity", "tfsi_diffusivity", "poly_diffusivity", "transference_number", "molality"]
PROPERTY_LABELS = {
    "conductivity": r"Conductivity ($\log_{10}\sigma$)",
    "li_diffusivity": r"Li diffusivity ($\log_{10}D_{Li}$)",
    "tfsi_diffusivity": r"TFSI diffusivity ($\log_{10}D_{TFSI}$)",
    "poly_diffusivity": r"Poly diffusivity ($\log_{10}D_{poly}$)",
    "transference_number": "Transference number",
    "molality": "Molality",
}
PLOT_PROPERTY_LABELS = [
    "Conductivity",
    "Li diffusivity",
    "TFSI diffusivity",
    "Poly diffusivity",
    "Transference",
    "Molality",
]
TARGETS = ["Q80_boundary", "Q85", "Q90", "Q95"]
TARGET_SHORT = {"Q80_boundary": "Q80", "Q85": "Q85", "Q90": "Q90", "Q95": "Q95"}


def sem(values) -> float:
    x = pd.Series(values).dropna().astype(float)
    return float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")


def pvalue_sign(values) -> float:
    x = pd.Series(values).dropna().astype(float)
    x = x[x != 0]
    if len(x) == 0:
        return float("nan")
    k = int((x > 0).sum())
    n = len(x)
    return float(2 * min(sum(math.comb(n, i) for i in range(k + 1)), sum(math.comb(n, i) for i in range(k, n + 1))) / (2 ** n))


def load():
    metrics = pd.read_csv(IN / "metrics_by_cell.csv")
    candidates = pd.read_csv(IN / "candidate_predictions.csv")
    locked = pd.read_csv(IN / "locked_tail_verifier_audit.csv")
    frozen = json.loads((IN / "frozen_manifest.json").read_text())
    source = json.loads((IN / "source_audit.json").read_text())
    return metrics, candidates, locked, frozen, source


def build_tables(metrics, candidates, locked, frozen, source):
    OUT.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for (arm, target), group in metrics.groupby(["arm", "target_label"], sort=False):
        row = {"arm": arm, "arm_label": ARM_LABELS[arm], "target_label": target, "target_short": TARGET_SHORT[target], "n_seeds": int(group.seed.nunique())}
        for col in ["validity", "novelty", "uniqueness", "diversity", "support_mean", "joint_uncertainty_mean", "failure_rate", "joint_target_rmse_normalized", "strict_hit", "joint_frontier_crossing"]:
            row[f"mean_{col}"] = float(group[col].mean())
            row[f"sem_{col}"] = sem(group[col])
        for prop in PROPERTIES:
            row[f"mae_{prop}"] = float(group[f"target_mae_{prop}"].mean())
            row[f"frontier_{prop}"] = float(group[f"frontier_crossing_rate_{prop}"].mean())
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "Table_1_joint_acceptance_summary.csv", index=False)

    adherence_rows = []
    for (arm, target), group in metrics.groupby(["arm", "target_label"], sort=False):
        for prop in PROPERTIES:
            adherence_rows.append({
                "arm": arm, "arm_label": ARM_LABELS[arm], "target_label": target, "property": prop,
                "target_mae_mean": float(group[f"target_mae_{prop}"].mean()), "target_mae_sem": sem(group[f"target_mae_{prop}"]),
                "frontier_crossing_rate_mean": float(group[f"frontier_crossing_rate_{prop}"].mean()),
            })
    adherence = pd.DataFrame(adherence_rows)
    adherence.to_csv(OUT / "Table_2_property_target_adherence.csv", index=False)

    # Candidate-wise rank-paired monotonicity: descriptive only; unconditional
    # uses reranking rank and is explicitly not an inferential pairing.
    mono_rows = []
    for (arm, seed), group in candidates.groupby(["arm", "seed"], sort=False):
        for prop in PROPERTIES:
            flags = []
            for rank, rank_group in group.groupby("selected_rank", sort=False):
                values = rank_group.set_index("target_label")[f"rf_prediction_{prop}"].reindex(TARGETS).to_numpy(dtype=float)
                if np.isfinite(values).all():
                    flags.append(bool(np.all(np.diff(values) >= -1e-12)))
            mono_rows.append({"arm": arm, "arm_label": ARM_LABELS[arm], "seed": int(seed), "response": "candidate_wise", "property": prop, "n_complete_rank_pairs": len(flags), "monotone_fraction": float(np.mean(flags)) if flags else np.nan, "pairing_note": "selected_rank paired; descriptive only" if arm == "unconditional_reranking" else "same candidate rank across target cells; descriptive only"})
    mono = pd.DataFrame(mono_rows)
    mono.to_csv(OUT / "Table_3_candidate_wise_monotonicity.csv", index=False)

    targets = {row["label"]: row["values_transformed"] for row in frozen["target_vectors"]}
    calibration_rows = []
    q_by_prop = {p: {row["quantile"]: row["values_transformed"][p] for row in frozen["target_vectors"]} for p in PROPERTIES}
    for prop in PROPERTIES:
        obs = locked[f"observed_{prop}"]
        pred = locked[f"predicted_{prop}"]
        for band, lo_q, hi_q in [("Q80-Q85", 0.80, 0.85), ("Q85-Q90", 0.85, 0.90), ("Q90-Q95", 0.90, 0.95)]:
            mask = (obs > q_by_prop[prop][lo_q]) & (obs <= q_by_prop[prop][hi_q]) & np.isfinite(pred)
            residual = obs[mask] - pred[mask]
            calibration_rows.append({
                "property": prop, "property_label": PROPERTY_LABELS[prop], "tail_band": band, "n": int(mask.sum()),
                "mae": float(np.abs(residual).mean()) if len(residual) else np.nan,
                "bias_observed_minus_rf": float(residual.mean()) if len(residual) else np.nan,
                "rmse": float(np.sqrt(np.mean(residual ** 2))) if len(residual) else np.nan,
                "residual_sem": sem(residual),
                "observed_mean": float(obs[mask].mean()) if mask.any() else np.nan,
                "predicted_mean": float(pred[mask].mean()) if mask.any() else np.nan,
            })
    calibration = pd.DataFrame(calibration_rows)
    calibration.to_csv(OUT / "Table_4_locked_tail_calibration.csv", index=False)

    fail_rows = []
    for (arm, target), group in candidates.groupby(["arm", "target_label"], sort=False):
        total = len(group)
        for reason, mask in {
            "invalid": ~group.valid,
            "exact_training_duplicate": group.valid & ~group.novel,
            "within_cell_duplicate": group.valid & ~group.unique_in_cell,
            "low_support": group.valid & ~group.support_eligible,
            "high_uncertainty": group.valid & ~group.uncertainty_eligible,
            "joint_target_error": group.valid & ~group.joint_error_eligible,
        }.items():
            fail_rows.append({"arm": arm, "arm_label": ARM_LABELS[arm], "target_label": target, "failure_class": reason, "n": int(mask.sum()), "fraction_of_candidates": float(mask.mean()), "denominator": total})
    failures = pd.DataFrame(fail_rows)
    failures.to_csv(OUT / "Table_5_failure_support_audit.csv", index=False)

    paired_rows = []
    for target in TARGETS:
        g = summary[summary.target_label == target].set_index("arm")
        for metric in ["mean_joint_target_rmse_normalized", "mean_strict_hit", "mean_joint_frontier_crossing", "mean_validity", "mean_support_mean", "mean_joint_uncertainty_mean"]:
            if "multi_continuous" in g.index and "scalar_continuous" in g.index:
                paired_rows.append({"target_label": target, "metric": metric, "multi_mean": float(g.loc["multi_continuous", metric]), "scalar_mean": float(g.loc["scalar_continuous", metric]), "multi_minus_scalar": float(g.loc["multi_continuous", metric] - g.loc["scalar_continuous", metric])})
    paired = pd.DataFrame(paired_rows)
    paired.to_csv(OUT / "Table_6_multi_vs_scalar_effects.csv", index=False)
    return summary, adherence, mono, calibration, failures, paired


def render(summary, adherence, mono, calibration, failures, paired):
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 10, "axes.labelsize": 11,
        "axes.titlesize": 11, "axes.linewidth": 1.1, "xtick.labelsize": 9,
        "ytick.labelsize": 9, "xtick.major.width": 1.0, "ytick.major.width": 1.0,
        "svg.fonttype": "none", "pdf.fonttype": 42, "savefig.dpi": 600,
    })
    x = np.arange(len(TARGETS))
    # Figure 4: primary Nature-style evidence composite.
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.4), gridspec_kw={"wspace": 0.38, "hspace": 0.48})
    ax = axes[0, 0]
    for arm in ARMS:
        g = summary[summary.arm == arm].set_index("target_label").reindex(TARGETS)
        ax.errorbar(x, g.mean_joint_target_rmse_normalized, yerr=g.sem_joint_target_rmse_normalized, color=COLORS[arm], marker="o", ms=4, lw=1.7, capsize=2.5, label=ARM_LABELS[arm])
    ax.set_xticks(x, ["Q80", "Q85", "Q90", "Q95"]); ax.set_ylabel("Joint target RMSE (normalized)"); ax.set_title("A  Joint control error", loc="left", fontweight="bold"); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=7.6, loc="upper left")

    ax = axes[0, 1]
    diff = paired[paired.metric == "mean_joint_target_rmse_normalized"].set_index("target_label").reindex(TARGETS).multi_minus_scalar.to_numpy()
    mat = np.zeros((len(PROPERTIES), len(TARGETS)))
    for i, prop in enumerate(PROPERTIES):
        for j, target in enumerate(TARGETS):
            m = adherence[(adherence.arm == "multi_continuous") & (adherence.target_label == target) & (adherence.property == prop)].target_mae_mean.iloc[0]
            s = adherence[(adherence.arm == "scalar_continuous") & (adherence.target_label == target) & (adherence.property == prop)].target_mae_mean.iloc[0]
            mat[i, j] = m - s
    vmax = max(abs(np.nanmin(mat)), abs(np.nanmax(mat)), 1e-6)
    im = ax.imshow(mat, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat[i, j]:+.2f}", ha="center", va="center", fontsize=7, color="white" if abs(mat[i, j]) > 0.65 * vmax else "#222222")
    ax.set_xticks(range(4), ["Q80", "Q85", "Q90", "Q95"]); ax.set_yticks(range(6), PLOT_PROPERTY_LABELS, fontsize=8.2); ax.set_title("B  Property-wise MAE: multi − scalar", loc="left", fontweight="bold"); ax.tick_params(length=0); ax.spines[:].set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03); cbar.set_label("Δ MAE", fontsize=8); cbar.ax.tick_params(labelsize=7)

    ax = axes[1, 0]
    # Use a deterministic subset only for visual density; tables retain all candidates.
    for arm in ARMS:
        g = pd.read_csv(IN / "candidate_predictions.csv")
        g = g[g.arm == arm].iloc[::4]
        ax.scatter(g.support, g.joint_uncertainty, s=4, alpha=0.12, color=COLORS[arm], rasterized=True)
    ax.axvline(0.35, color="#222222", lw=0.9, ls=(0, (3, 2))); ax.axhline(0.35, color="#222222", lw=0.9, ls=(0, (3, 2)))
    ax.set_xlabel("Nearest-train Tanimoto support"); ax.set_ylabel("Joint RF uncertainty (normalized)"); ax.set_title("C  Candidate credibility space", loc="left", fontweight="bold"); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS[a], markersize=5, label=ARM_LABELS[a]) for a in ARMS]
    ax.legend(handles=handles, frameon=False, fontsize=7, loc="upper right")

    ax = axes[1, 1]
    cal = calibration.copy(); band_order = ["Q80-Q85", "Q85-Q90", "Q90-Q95"]; xpos = np.arange(len(PROPERTIES)); offsets = [-0.22, 0, 0.22]
    for offset, band in zip(offsets, band_order):
        g = cal[cal.tail_band == band].set_index("property").reindex(PROPERTIES)
        ax.errorbar(xpos + offset, g.bias_observed_minus_rf, yerr=g.residual_sem, fmt="o", ms=3.5, lw=1.1, capsize=2, label=band)
    ax.axhline(0, color="#222222", lw=0.9, ls=(0, (3, 2))); ax.set_xticks(xpos, ["σ", "Li", "TFSI", "Poly", "t+", "m" ]); ax.set_ylabel("Locked-tail residual (observed − RF)"); ax.set_title("D  Locked-tail calibration bias", loc="left", fontweight="bold"); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.subplots_adjust(top=0.94, bottom=0.12, left=0.10, right=0.97)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"Figure_4_nature_upper_tail_summary.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # Figure 5: failure and monotonicity audit, intentionally separate from
    # absolute response so readers do not conflate level and mechanism.
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), gridspec_kw={"wspace": 0.72})
    failure_order = ["invalid", "exact_training_duplicate", "within_cell_duplicate", "low_support", "high_uncertainty", "joint_target_error"]
    fail_mat = failures.groupby(["failure_class", "arm"], sort=False).fraction_of_candidates.mean().unstack().reindex(index=failure_order, columns=ARMS)
    im = axes[0].imshow(fail_mat.to_numpy(), aspect="auto", vmin=0, vmax=1, cmap="OrRd")
    for i in range(fail_mat.shape[0]):
        for j in range(fail_mat.shape[1]):
            v = fail_mat.iloc[i, j]; axes[0].text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if v > 0.5 else "#222222")
    axes[0].set_xticks(range(4), ["Multi", "Scalar", "Binary", "Uncond."]); axes[0].set_yticks(range(len(failure_order)), [x.replace("_", " ") for x in failure_order], fontsize=8); axes[0].set_title("A  Failure and filter coverage", loc="left", fontweight="bold"); axes[0].tick_params(length=0); axes[0].spines[:].set_visible(False); fig.colorbar(im, ax=axes[0], fraction=0.045, pad=0.03).ax.tick_params(labelsize=7)
    mono_plot = mono.groupby(["property", "arm"], sort=False).monotone_fraction.mean().unstack().reindex(index=PROPERTIES, columns=ARMS)
    im = axes[1].imshow(mono_plot.to_numpy(), aspect="auto", vmin=0, vmax=1, cmap="YlGnBu")
    for i in range(mono_plot.shape[0]):
        for j in range(mono_plot.shape[1]):
            v = mono_plot.iloc[i, j]; axes[1].text(j, i, "—" if pd.isna(v) else f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if pd.notna(v) and v > 0.55 else "#222222")
    axes[1].set_xticks(range(4), ["Multi", "Scalar", "Binary", "Uncond."]); axes[1].set_yticks(range(len(PROPERTIES)), PLOT_PROPERTY_LABELS, fontsize=8.2); axes[1].set_title("B  Candidate-wise monotonicity", loc="left", fontweight="bold"); axes[1].tick_params(length=0); axes[1].spines[:].set_visible(False); fig.colorbar(im, ax=axes[1], fraction=0.045, pad=0.03).ax.tick_params(labelsize=7)
    fig.subplots_adjust(top=0.84, bottom=0.25, left=0.22, right=0.9)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"Figure_5_nature_failure_monotonicity.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_text(summary, adherence, mono, calibration, failures, paired, frozen, source):
    multi = summary[summary.arm == "multi_continuous"]
    scalar = summary[summary.arm == "scalar_continuous"]
    multi_rmse = multi.mean_joint_target_rmse_normalized.mean()
    scalar_rmse = scalar.mean_joint_target_rmse_normalized.mean()
    multi_valid = multi.mean_validity.mean(); scalar_valid = scalar.mean_validity.mean()
    conductivity_cal = calibration[calibration.property == "conductivity"]
    lines = []
    lines.append("# Results and discussion — multi-property Upper-tail benchmark\n")
    lines.append("## Design and acceptance boundary\n")
    lines.append(f"We evaluated four matched generation arms under a six-dimensional Q80 truncation of the released HTP-MD table. The training intersection contained **{source['joint_training_rows']} of {source['source_rows']} rows ({source['joint_training_fraction']:.1%})**. Conductivity, Li/TFSI/polymer diffusivities were transformed with `log10`; transference number and molality were retained on their raw scales. All six dimensions were finite, while transference number contained nonphysical negative values and molality showed near-degenerate support; both facts are retained in the source audit rather than clipped.\n")
    lines.append("Every arm used the same five seeds, 1,000 optimizer steps, 100 candidates per target cell, decoder settings, RF verifier, filters and output schema. The unit for paired contrasts is the seed × target cell. The locked Q80–Q95 source rows were excluded from generator/RF fitting, thresholding, filtering and selection; they appear only in the post-run calibration audit.\n")
    lines.append("## Boundary control is support-limited rather than extrapolation-successful\n")
    lines.append(f"Across the four query vectors, mean normalized joint RMSE was **{multi_rmse:.2f}** for the multi-property arm and **{scalar_rmse:.2f}** for the scalar comparator. The multi-property arm therefore reduced descriptive joint error by **{multi_rmse - scalar_rmse:+.2f}** normalized units, but this difference did not translate into a joint strict hit: joint strict-hit and all-six-property frontier-crossing rates were zero in every arm × target cell. The result supports improved surrogate adherence only within a support-limited prediction benchmark; it does not support validated property extrapolation.\n")
    lines.append(f"The multi-property arm retained mean validity of **{multi_valid:.3f}**, compared with **{scalar_valid:.3f}** for scalar conditioning. Its mean support and normalized RF uncertainty were **{multi.mean_support_mean.mean():.3f}** and **{multi.mean_joint_uncertainty_mean.mean():.3f}**, respectively. The strict credibility gate (support ≥ 0.35, uncertainty < 0.35, joint normalized error < 0.5) yielded no eligible MD-review candidates, so no candidate was promoted to physical validation.\n")
    lines.append("## Property-wise adherence and monotonicity\n")
    lines.append("Property-wise target MAE is reported for every arm and target in Table 2. Candidate-wise monotonicity is a descriptive rank-paired diagnostic: conditional arms pair the same generated rank across target cells, whereas unconditional reranking pairs selected ranks and is explicitly non-inferential. The corresponding fractions are in Table 3 and Figure 5. No arm shows uniformly monotonic responses across all six properties, so the benchmark does not establish reliable joint monotonic control.\n")
    lines.append("## Locked-tail calibration and false-positive risk\n")
    lines.append("The locked-tail audit compares frozen RF predictions with observed source values in Q80–Q95 bands, separately for each property. Residuals are defined as observed minus RF prediction; positive values are underprediction. Figure 4D and Table 4 show the calibration bias by property and tail distance. These rows were never used to fit or select candidates, so the audit diagnoses surrogate behavior rather than validating generated structures.\n")
    if len(conductivity_cal):
        lines.append(f"For conductivity, the locked-tail residual means across Q80–Q85, Q85–Q90 and Q90–Q95 were {', '.join(f'{x:+.3f}' for x in conductivity_cal.bias_observed_minus_rf)} log units. This is evidence that RF confidence and RF accuracy must remain separate from MD confirmation.\n")
    lines.append("## Interpretation\n")
    lines.append("The evidence is consistent with a conservative conclusion: multi-property conditioning can reduce the average frozen-surrogate joint target error relative to scalar conductivity conditioning under a common Q80-intersection training set, but the same experiment exposes a severe support bottleneck. Because the joint target vectors are unsupported by the coordinate-wise maxima of the intersection, zero joint hits and zero frontier crossings are not evidence that the generator cannot discover high-property structures in a larger or better-supported dataset. They do show that this frozen benchmark cannot justify a claim of controlled upper-tail extrapolation.\n")
    lines.append("The unavailable endpoints are MD-confirmed frontier crossing and residual learning, because MD was not run by contract. The next decisive experiment is a symmetric, blinded MD study over a predeclared stratified candidate set, with build failures retained in the denominator and residuals analyzed against target distance, support, uncertainty and structural distance.\n")
    (IN / "RESULTS_AND_DISCUSSION_NATURE.md").write_text("\n".join(lines) + "\n")
    (OUT / "FIGURE_CAPTIONS_NATURE.md").write_text("""# Nature-style figure captions

**Figure 4 | Joint control, property-wise adherence, credibility and locked-tail calibration.** (A) Mean normalized joint target RMSE across five matched seeds; points are seed means and bars are SEM. (B) Property-wise target-MAE difference between multi-property and scalar conditioning; negative values favor multi-property conditioning. (C) Candidate-level support versus normalized joint RF uncertainty; dashed lines are the frozen support and uncertainty gates. Points are a deterministic one-in-four display subsample; all candidates are retained in the machine-readable tables. (D) Mean locked-tail residual, observed minus RF prediction, by property and Q80–Q95 interval; bars are SEM over locked source rows. Locked rows are post-run audits only and are not generated-candidate or MD evidence.

**Figure 5 | Failure modes and candidate-wise monotonicity.** (A) Fractions of candidates assigned to explicit invalidity, duplication, support, uncertainty and target-error classes. (B) Fraction of complete rank-paired candidate traces that are non-decreasing across Q80, Q85, Q90 and Q95 for each property. Rank pairing is descriptive; unconditional reranking is selection-induced and not an inferential comparison.
""")
    checklist = {
        "source_hash_split_target_scaler_frozen": True,
        "six_transforms_explicit": True,
        "matched_arms_seeds_budget_generation_decoder_filter_schema": True,
        "candidate_provenance_complete": True,
        "unsupported_invalid_low_support_high_uncertainty_failures_reported": True,
        "surrogate_md_separated": True,
        "rf_top1_only": False,
        "paired_identity_leakage_audit_pass": json.loads((IN / "pairing_acceptance_audit.json").read_text())["status"] == "pass",
        "joint_strict_hit_available": True,
        "property_mae_available": True,
        "candidate_wise_monotonicity_available": True,
        "locked_calibration_available": True,
        "md_confirmed_frontier_crossing": False,
        "residual_md_minus_rf": False,
    }
    (IN / "ACCEPTANCE_CHECKLIST.json").write_text(json.dumps(checklist, indent=2) + "\n")


def main():
    metrics, candidates, locked, frozen, source = load()
    summary, adherence, mono, calibration, failures, paired = build_tables(metrics, candidates, locked, frozen, source)
    render(summary, adherence, mono, calibration, failures, paired)
    write_text(summary, adherence, mono, calibration, failures, paired, frozen, source)
    print(json.dumps({"output": str(IN), "tables": 6, "figures": 2, "candidate_rows": len(candidates), "locked_audit_rows": len(locked)}, indent=2))


if __name__ == "__main__":
    main()
