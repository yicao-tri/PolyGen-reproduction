---
title: Multi-property interpolation — Nature evidence package
date: 2026-10-01
status: evidence-complete-surrogate-only
tags:
  - PolyGen
  - multi-property-conditioning
  - interpolation
  - surrogate-evidence
  - reproducibility
---

# Decision summary

This milestone answers a narrow benchmark question: under one frozen HTP-MD split, common target cells, matched seeds, generation budgets, decoding and filtering schema, does six-dimensional conditioning improve joint control over six electrolyte properties relative to scalar conductivity conditioning?

The answer is **not supported as an improvement by the current surrogate evidence**. Across the 21 target cells and five seed-level repetitions, the multi-property arm has mean joint RMSE 0.5793 (95% Student-t interval 0.5638–0.5949), compared with 0.5753 (0.5668–0.5837) for scalar conditioning. The paired multi-minus-scalar difference is +0.0041 (−0.0116–0.0197), so the point estimate slightly favors scalar conditioning and the interval includes no practically resolved difference. Joint strict-hit rates are essentially zero in both arms: 0.000095 for each, with no paired improvement.

The appropriate conclusion is therefore: **this run does not demonstrate improved internal joint controllability from six-dimensional conditioning**. It does show that the multi-property arm is executable, that all 21 target cells are supported by the train-only construction, and that the benchmark exposes a severe joint-hit bottleneck. The evidence is surrogate-defined and prediction-only; it does not establish MD, experimental conductivity, or extrapolation.

# Research question and estimand

The primary estimand is the seed-level paired difference in mean target-cell joint RMSE and joint strict-hit rate between `multi_continuous` and `scalar_continuous`, averaged over the same 21 target cells. The independent unit is the training/generation seed (`17, 42, 202, 303, 907`), not a generated candidate. Binary conductivity conditioning and unconditional generation followed by frozen RF reranking are controls.

The target design contains 18 one-property probes (Q50, Q65 and Q80 for each property, with the other five coordinates at train medians) and three coherent joint empirical-copula targets. The coherent targets are selected from train-only rows by mean marginal percentile. No independent Cartesian product of marginal quantiles was used.

# Frozen inputs and transformations

| Item | Frozen evidence |
|---|---|
| Source | `inputs/release-data/htpmd-trainset.csv`, 6,024 rows |
| Source SHA-256 | `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69` |
| Split | 4,819 train / 1,205 test; stratified conductivity-decile split; random state 20260923 |
| Log transforms | `conductivity`, `li_diffusivity`, `tfsi_diffusivity`, `poly_diffusivity` → `log10` |
| Raw transforms | `transference_number`, `molality` remain raw |
| Raw-value audit | all six fields finite; all log fields positive; transference range includes negative values and is explicitly retained; molality has nonzero but narrow train variance |
| Scaler | train-only fit; frozen in `transform_scaler_manifest.json` |
| Candidate budget | 4 arms × 5 seeds × 21 cells × 100 candidates = 42,000 rows |
| MD / force field | not run / not assessed by contract |

The complete source and transform records are in `evidence/data/source_audit.json`, `evidence/data/transform_scaler_manifest.json`, and `evidence/data/design_contract.json`.

# Primary result

![[assets/figures/Figure_1_property_probe_joint_error.png]]

> [!note] Figure 1 — Property-probe joint error
> **Shows:** Joint normalized RF target error for each of the six property-probe families across Q50, Q65 and Q80.
> **Data:** `evidence/data/metrics_by_cell.csv` and `evidence/data/target_cells.csv`.
> **Script:** `evidence/scripts/render_multi_property_interpolation.py`.
> **Command:** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/render_multi_property_interpolation.py`.
> **Unit/statistics:** Arm × seed × target cell; points and bars are means with SEM across five seeds.
> **Supports:** A descriptive comparison of surrogate-defined joint error across target probes.
> **Does not support:** Physical property control, MD agreement, or causal superiority.

![[assets/figures/Figure_2_coherent_joint_targets.png]]

> [!note] Figure 2 — Coherent joint targets
> **Shows:** Error and strict-hit rate for three train-only empirical-copula joint targets.
> **Data:** `evidence/data/metrics_by_cell.csv` and `evidence/data/target_cells.csv`.
> **Script:** `evidence/scripts/render_multi_property_interpolation.py`.
> **Unit/statistics:** Five matched seeds per arm; error bars are SEM. Strict-hit additionally requires validity, novelty, support, uncertainty and joint-error gates.
> **Supports:** The benchmark’s joint-control ceiling under the frozen surrogate gate.
> **Does not support:** Independent quantile-combination claims or experimental joint controllability.

| Metric | Multi-property | Scalar | Paired multi − scalar |
|---|---:|---:|---:|
| Joint RMSE | 0.5793 [0.5638, 0.5949] | 0.5753 [0.5668, 0.5837] | +0.0041 [−0.0116, +0.0197] |
| Joint strict-hit rate | 0.000095 | 0.000095 | 0.000000 |
| Validity | 0.5301 [0.4997, 0.5604] | 0.5072 [0.4371, 0.5773] | +0.0229 [−0.0532, +0.0990] |
| Novelty | 0.5107 [0.4809, 0.5405] | 0.4921 [0.4259, 0.5582] | +0.0186 [−0.0560, +0.0932] |
| Support | 0.5969 [0.5831, 0.6106] | 0.5877 [0.5722, 0.6032] | +0.0092 [−0.0028, +0.0211] |
| RF uncertainty | 0.5325 [0.5176, 0.5474] | 0.5313 [0.5250, 0.5376] | +0.0012 [−0.0110, +0.0134] |

Intervals are two-sided 95% Student-t intervals over five seed-level values; they are descriptive/exploratory and not multiplicity-adjusted confirmatory inference. Full values are in `assets/tables/arm_summary.csv` and `assets/tables/paired_summary.csv`.

# Quality, monotonicity and failure audit

![[assets/figures/Figure_3_cell_quality_audit.png]]

> [!note] Figure 3 — Cell-level quality audit
> **Shows:** Strict-hit and validity fractions across all 21 target cells and four arms.
> **Data:** `evidence/data/metrics_by_cell.csv`.
> **Script:** `evidence/scripts/render_multi_property_interpolation.py`.
> **Unit/statistics:** Arm × target cell, averaged over five seeds.
> **Supports:** Identification of target-cell heterogeneity and quality bottlenecks.
> **Does not support:** A top-1 RF claim or a physical discovery claim.

![[assets/figures/Figure_4_paired_quality_audit.png]]

> [!note] Figure 4 — Paired quality and failure audit
> **Shows:** Absolute quality, matched seed contrasts, Q50→Q65→Q80 cell-mean monotonicity, and overlapping failure modes.
> **Data:** `evidence/data/cell_quality_and_control.csv`, `assets/tables/paired_summary.csv`, and `assets/tables/property_monotonicity_summary.csv`.
> **Script:** `evidence/scripts/render_multi_property_interpolation_analysis.py` after `evidence/scripts/analyze_multi_property_interpolation.py`.
> **Unit/statistics:** Seed-level intervals for paired contrasts; five-seed monotonicity fractions; failure categories may overlap.
> **Supports:** The distinction between joint control, quality, and failure mechanisms.
> **Does not support:** Candidate-wise monotonicity, because independently generated target cells do not share structure identities.

The multi-property arm is monotonic for conductivity at the cell-mean level in 5/5 seeds, but monotonicity is weak or absent for most other properties. This supports a limited interpretation: the model can respond to the conductivity coordinate more consistently than it jointly controls all six coordinates. Candidate-wise monotonicity is not identifiable from this design and is labeled as such rather than inferred.

The full candidate pool contains explicit failure provenance. Across 42,000 rows, 26,061 are structurally valid and 15,939 are invalid; 13,594 contain a high-uncertainty failure flag; 169 contain a low-structural-support flag; and 16,747 are non-novel. These categories overlap. The two `eligible` rows are retained alongside the filtered rows so that failure rates are auditable rather than silently discarded.

# Controls and interpretation

Unconditional generation followed by RF reranking has lower mean joint RMSE (0.5405) and much higher validity (0.9241) than either conditional arm, but it is a different acquisition policy and should not be interpreted as evidence that unconditional generation solves joint conditioning. Binary conductivity is a negative control: it receives only a fixed high/low conductivity label and cannot express the six-dimensional target vector.

The observed pattern is most consistent with a surrogate-defined joint-control bottleneck: adding five extra target coordinates does not improve the frozen RF joint error or strict-hit rate under this generation budget. It is not evidence that the six-dimensional representation is intrinsically incapable of control; the result could reflect model capacity, optimization, target conditioning geometry, or the severity of the simultaneous gate. The correct manuscript claim is therefore a benchmark result, not a mechanistic claim about polymer physics.

# Evidence unavailable by design

| Requested metric | Status | Why |
|---|---|---|
| Property-wise and joint frontier crossing | Not applicable here | This is an interpolation package; frontier crossing belongs to the separate extrapolation benchmark. |
| Locked-holdout surrogate calibration | Unavailable in this package | Generation-time RF predictions are frozen, but a calibration artifact was not produced. |
| MD-confirmed frontier crossing | Unavailable | MD was explicitly not run. |
| `residual = logσ_MD − logσ_RF` | Unavailable | No MD outcomes exist. |
| Residual versus distance/support/uncertainty | Unavailable | Same missing MD outcome. |

These are not treated as zero or negative results. They are explicitly recorded in `assets/tables/unavailable_metrics.csv`.

# Reproducibility and pairing gate

The machine verifier reports PASS for source hash, split, six-property transforms, target grid, non-Cartesian coherent targets, 42,000 candidate rows, 420 metric rows, 100 candidates per cell, arm/seed completeness, binary policy, no-MD policy, historical-result preservation, and pairing/leakage checks. The authoritative verification record is `evidence/data/verification.json`; the pairing audit is `evidence/data/pairing_leakage_audit.json`.

Checkpoint provenance is per seed. Historical scalar/binary checkpoints are reused where present; remaining scalar seeds are matched 1,000-step retraining; multi-continuous and unconditional-reranking are newly trained. The exact checkpoint hashes and origins are in `evidence/data/frozen_manifest.json`.

Repository: `/Users/yicao/Documents/ARC/PolyGen-reproduction`; HEAD at packaging: `3e2e707d4db1da26e395c595e6860803f690561c`; repository dirty at packaging. The package snapshots under `evidence/scripts/` and `evidence/data/` are authoritative for this milestone. Historical result roots were preserved byte-for-byte by the pairing audit.

# Manuscript-ready claim boundaries

**Observed / suitable for Results with qualification.** Under a frozen train/test split and matched five-seed generation protocol, six-dimensional conditioning did not reduce surrogate-defined joint target RMSE relative to scalar conductivity conditioning; the paired mean difference was +0.0041 normalized units (95% Student-t interval −0.0116 to +0.0197), and joint strict-hit rates were effectively zero in both arms.

**Observed / suitable for Methods or Extended Data.** The benchmark uses 18 marginal probes and three train-only empirical-copula joint targets, with no independent Cartesian quantile product; all candidate rows retain validity, novelty, support, uncertainty, target error, and filter-failure provenance.

**Unavailable / do not write as achieved.** The package does not establish MD-confirmed conductivity, experimental conductivity, frontier crossing, calibrated locked-holdout uncertainty, or a physical mechanism for the joint-control bottleneck.

# Reproduction commands

```bash
cd /Users/yicao/Documents/ARC/PolyGen-reproduction
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/analyze_multi_property_interpolation.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/render_multi_property_interpolation.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/render_multi_property_interpolation_analysis.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/verify_multi_property_interpolation.py
```

The analysis and rendering commands consume the completed frozen outputs; they do not retrain models.
