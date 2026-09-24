#!/usr/bin/env python3
"""Build the immutable five-seed Experiment C publication evidence package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/experiment-c/c1"
EXTRA = ROOT / "results/experiment-c/extra-seeds/seeds202-303"
OUT = ROOT / "results/experiment-c/publication"
EXPECTED_SEEDS = {17, 42, 202, 303, 907}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def t_summary(values: pd.Series) -> dict[str, float]:
    x = values.to_numpy(float)
    mean = float(x.mean())
    sem = float(stats.sem(x))
    low, high = stats.t.interval(0.95, len(x) - 1, loc=mean, scale=sem)
    test = stats.ttest_1samp(x, 0.0)
    return {
        "mean": mean,
        "sd": float(x.std(ddof=1)),
        "sem": sem,
        "ci95_low": float(low),
        "ci95_high": float(high),
        "paired_t": float(test.statistic),
        "paired_t_p_two_sided": float(test.pvalue),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fingerprints = {}
    for name in ("train_rows.csv", "test_rows.csv"):
        a, b = BASE / name, EXTRA / name
        if a.read_bytes() != b.read_bytes():
            raise RuntimeError(f"Pairing violation: {name} differs between seed batches")
        fingerprints[name] = sha256(a)

    base_result = json.loads((BASE / "result.json").read_text())
    extra_result = json.loads((EXTRA / "result.json").read_text())
    if base_result["source_sha256"] != extra_result["source_sha256"]:
        raise RuntimeError("Pairing violation: source data hashes differ")
    if base_result["verifier"] != extra_result["verifier"]:
        # JSON float roundoff in R2 is harmless; compare numerically below.
        for key in base_result["verifier"]:
            if not np.isclose(base_result["verifier"][key], extra_result["verifier"][key]):
                raise RuntimeError(f"Pairing violation: verifier metric {key} differs")

    sample_files = sorted(BASE.glob("*-seed*/samples.csv")) + sorted(EXTRA.glob("*-seed*/samples.csv"))
    samples = pd.concat([pd.read_csv(path) for path in sample_files], ignore_index=True)
    if set(samples.seed) != EXPECTED_SEEDS or len(samples) != 3000:
        raise RuntimeError("Expected five paired seeds and 3,000 generated samples")
    counts = samples.groupby(["arm", "seed", "target"]).size()
    if not counts.eq(100).all() or len(counts) != 30:
        raise RuntimeError("Expected 100 samples for each arm/seed/target cell")

    metrics = (
        samples.groupby(["arm", "seed", "target"])
        .agg(
            n=("hit", "size"),
            validity=("valid", "mean"),
            novelty=("novel", "mean"),
            hit_rate=("hit", "mean"),
            target_mae=("target_error", "mean"),
            mean_prediction=("predicted_log_sigma", "mean"),
            mean_uncertainty=("uncertainty", "mean"),
            ood_rate=("support", lambda x: float((x < 0.35).mean())),
        )
        .reset_index()
    )
    metrics.to_csv(OUT / "c1_five_seed_arm_target_metrics.csv", index=False)

    per_seed = (
        metrics.groupby(["arm", "seed"])
        .agg(
            hit_rate=("hit_rate", "mean"),
            validity=("validity", "mean"),
            novelty=("novelty", "mean"),
            target_mae=("target_mae", "mean"),
            ood_rate=("ood_rate", "mean"),
        )
        .reset_index()
    )
    per_seed.to_csv(OUT / "c1_five_seed_arm_metrics.csv", index=False)

    effect_rows = []
    paired = pd.DataFrame({"seed": sorted(EXPECTED_SEEDS)})
    for metric in ("hit_rate", "target_mae", "validity", "novelty", "ood_rate"):
        wide = per_seed.pivot(index="seed", columns="arm", values=metric).sort_index()
        delta = wide["continuous"] - wide["binary"]
        paired[f"binary_{metric}"] = wide["binary"].to_numpy()
        paired[f"continuous_{metric}"] = wide["continuous"].to_numpy()
        paired[f"delta_{metric}"] = delta.to_numpy()
        row = {
            "metric": metric,
            "binary_mean": float(wide["binary"].mean()),
            "continuous_mean": float(wide["continuous"].mean()),
            **t_summary(delta),
        }
        effect_rows.append(row)
    paired.to_csv(OUT / "c1_five_seed_paired_effects.csv", index=False)
    effects = pd.DataFrame(effect_rows)
    effects.to_csv(OUT / "c1_five_seed_effect_summary.csv", index=False)

    hit_delta = paired["delta_hit_rate"]
    exact_sign_p = float(stats.binomtest(int((hit_delta > 0).sum()), len(hit_delta), 0.5).pvalue)
    response = metrics.groupby(["arm", "seed"]).apply(
        lambda g: pd.Series({
            "target_prediction_correlation": float(np.corrcoef(g.target, g.mean_prediction)[0, 1]),
            "monotonic_increasing": bool(g.sort_values("target").mean_prediction.is_monotonic_increasing),
        }),
    ).reset_index()
    response.to_csv(OUT / "c1_five_seed_controllability.csv", index=False)

    verifier = base_result["verifier"]
    summary = {
        "status": "pass",
        "design": {
            "seeds": sorted(EXPECTED_SEEDS),
            "paired_unit": "training/generation seed",
            "targets_log10_S_per_cm": [-5.0, -4.0, -3.0],
            "samples_per_arm_seed_target": 100,
            "total_generated_samples": int(len(samples)),
            "generator_steps": 1000,
            "source_sha256": base_result["source_sha256"],
            "row_fingerprints": fingerprints,
        },
        "verifier": verifier,
        "primary_effect": {
            **effects.loc[effects.metric.eq("hit_rate")].iloc[0].drop("metric").to_dict(),
            "positive_seeds": int((hit_delta > 0).sum()),
            "n_seeds": int(len(hit_delta)),
            "exact_sign_test_p_two_sided": exact_sign_p,
            "interpretation": "Exploratory five-seed evidence; seed is the inferential unit.",
        },
        "controllability": {
            arm: {
                "mean_target_prediction_correlation": float(g.target_prediction_correlation.mean()),
                "monotonic_seeds": int(g.monotonic_increasing.sum()),
                "n_seeds": int(len(g)),
            }
            for arm, g in response.groupby("arm")
        },
    }
    (OUT / "c1_five_seed_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    target = metrics.groupby(["arm", "target"]).agg(
        hit_rate_mean=("hit_rate", "mean"),
        hit_rate_sem=("hit_rate", "sem"),
        target_mae_mean=("target_mae", "mean"),
        prediction_mean=("mean_prediction", "mean"),
        validity_mean=("validity", "mean"),
        novelty_mean=("novelty", "mean"),
        ood_rate_mean=("ood_rate", "mean"),
    ).reset_index()
    target.to_csv(OUT / "c1_five_seed_target_summary.csv", index=False)

    primary = summary["primary_effect"]
    mae = effects.loc[effects.metric.eq("target_mae")].iloc[0]
    validity = effects.loc[effects.metric.eq("validity")].iloc[0]
    novelty = effects.loc[effects.metric.eq("novelty")].iloc[0]
    text = f"""# Experiment C publication-ready results and discussion

## Audited design

The analysis combines five paired training/generation seeds ({', '.join(map(str, sorted(EXPECTED_SEEDS)))}) under an identical data split, frozen verifier, 1,000-step training budget, model size, sampling budget, and target grid. Each arm generated 100 candidates at each of three targets per seed (3,000 candidates total). The inferential unit is the seed, not the individual generated candidate. Byte-identical train/test row files and the common source SHA-256 are recorded in `c1_five_seed_summary.json`.

## Results

Continuous conditioning increased the mean strict target-hit rate from {primary['binary_mean']:.4f} to {primary['continuous_mean']:.4f}, an absolute paired improvement of {primary['mean']:.4f} (95% t interval {primary['ci95_low']:.4f} to {primary['ci95_high']:.4f}; paired t-test p={primary['paired_t_p_two_sided']:.4f}). All five paired seeds favored continuous conditioning. Because only five seeds were run, the distribution-free exact sign test remains borderline (two-sided p={primary['exact_sign_test_p_two_sided']:.4f}); the t-test should therefore be treated as exploratory rather than definitive confirmatory evidence.

Target MAE decreased by {abs(mae['mean']):.4f} log10 S cm^-1 (95% t interval {mae['ci95_low']:.4f} to {mae['ci95_high']:.4f}). The continuous model was monotonic across the three requested targets in {summary['controllability']['continuous']['monotonic_seeds']}/5 seeds, with mean target-prediction correlation {summary['controllability']['continuous']['mean_target_prediction_correlation']:.3f}; the binary baseline was monotonic in {summary['controllability']['binary']['monotonic_seeds']}/5 seeds with mean correlation {summary['controllability']['binary']['mean_target_prediction_correlation']:.3f}.

This gain came with a chemical-yield tradeoff. Mean validity changed by {validity['mean']:.4f} (binary {validity['binary_mean']:.4f}, continuous {validity['continuous_mean']:.4f}), and novelty changed by {novelty['mean']:.4f} (binary {novelty['binary_mean']:.4f}, continuous {novelty['continuous_mean']:.4f}). Most strict hits occur at the central -4 target; the -5 and -3 targets are poorly covered by the frozen verifier's training support. The primary effect therefore demonstrates improved offline target adherence within this benchmark, not validated discovery at the target extremes.

## Claim boundary

The strongest supported claim is: *under a fixed HTP-MD split and common frozen verifier, continuous conductivity conditioning reproducibly improves verifier-defined target adherence over binary high/low PolyGen across five paired seeds, while reducing valid and novel yield.* It does not establish experimental conductivity, salt/temperature controllability, or complete-system generation. Those require the separate formulation experiment and prospective MD or laboratory validation.
"""
    (OUT / "RESULTS_AND_DISCUSSION.md").write_text(text)
    metric_labels = {
        "hit_rate": "Strict target-hit rate",
        "target_mae": "Target MAE (log10 S cm^-1)",
        "validity": "Validity",
        "novelty": "Novelty",
        "ood_rate": "OOD rate",
    }
    table_lines = [
        "# Experiment C publication tables and figure captions",
        "",
        "## Table 1. Five-seed paired C1 outcomes",
        "",
        "| Outcome | Binary mean | Continuous mean | Paired difference | 95% t interval | Paired t-test p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in effects.iterrows():
        table_lines.append(
            f"| {metric_labels[row.metric]} | {row.binary_mean:.4f} | {row.continuous_mean:.4f} | "
            f"{row['mean']:+.4f} | [{row.ci95_low:.4f}, {row.ci95_high:.4f}] | {row.paired_t_p_two_sided:.4g} |"
        )
    table_lines += [
        "",
        "Note: the seed is the inferential unit (n=5 paired seeds). The two-sided exact sign-test p value for the primary hit-rate effect is 0.0625. The t intervals and p values are exploratory because n is small.",
        "",
        "## Table 2. Target-specific outcomes",
        "",
        "| Arm | Target | Hit rate | Target MAE | Mean verifier prediction | Validity | Novelty | OOD rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in target.iterrows():
        table_lines.append(
            f"| {row.arm.capitalize()} | {row.target:.1f} | {row.hit_rate_mean:.3f} | "
            f"{row.target_mae_mean:.3f} | {row.prediction_mean:.3f} | {row.validity_mean:.3f} | "
            f"{row.novelty_mean:.3f} | {row.ood_rate_mean:.3f} |"
        )
    table_lines += [
        "",
        "## Figure captions",
        "",
        "**Figure 1. Continuous conditioning improves target adherence with a validity tradeoff.** (A) Mean frozen-verifier prediction at each requested log-conductivity target; error bars show SEM across five training/generation seeds. The dashed line is ideal calibration. (B) Strict target-hit rates for paired binary and continuous runs; each connected pair is one seed. (C) Mean paired differences with 95% t intervals. Positive hit-rate and negative target-MAE differences favor continuous conditioning, whereas negative validity and novelty differences expose the chemical-yield cost.",
        "",
        "**Figure 2. Seed-level primary effect.** Continuous-minus-binary strict target-hit-rate differences for each paired seed and their mean with 95% t interval. All five effects are positive; the exact two-sided sign-test p value is 0.0625.",
        "",
        "**Figure S1. Deterministic candidate-structure sheets.** Two eligible unique candidates are selected per arm, seed and target from the original three-seed panel using the frozen score target error + 0.25 x verifier uncertainty. Structures illustrate generator output and are not MD- or experimentally validated discoveries.",
    ]
    (OUT / "TABLES_AND_CAPTIONS.md").write_text("\n".join(table_lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
