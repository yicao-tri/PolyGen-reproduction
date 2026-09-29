# Interpolation tables and captions

## Table 1. Frozen interpolation benchmark

| Item | Frozen value |
|---|---|
| Source | `inputs/release-data/htpmd-trainset.csv` |
| Targets | Q50 −4.2653; Q65 −4.1874; Q80 −4.0845 log10(S cm−1) |
| Arms | continuous; binary; unconditional+rerranking recorded as blocked |
| Seeds | 17, 42, 202, 303, 907 |
| Candidates per arm/seed/target | 100 |
| Decoding | temperature 1.0; top-k 40 |
| MD | not run |

## Table 2. Aggregate prediction-phase metrics

| Arm | Mean validity | Mean strict-hit rate | Mean target MAE |
|---|---:|---:|---:|
| Continuous | 0.545 | 0.529 | 0.115 |
| Binary | 0.511 | 0.489 | 0.130 |

Cell-level values are in `interpolation_aggregate_metrics.csv`; the underlying candidate-level table retains all failures and filter decisions.

## Figure captions

**Figure 1 | Interpolation response under matched internal targets.** (A) Mean frozen-RF prediction versus requested Q50–Q80 target for continuous and binary conditioning. Crosses show the requested target curve; the separation between predictions and crosses indicates compressed verifier response rather than perfect target realization. (B) Target MAE and (C) validity fraction, shown as mean ± SEM across five matched seeds. This is the direct interpolation counterpart to the upper-tail response figure.

**Figure 2 | Interpolation output quality.** Heatmaps show strict-hit rate and validity by arm and requested quantile. All six arm-by-target cells contain generated candidates; unlike the upper-tail figure, no unsupported-cell dash is required.

**Figure 3 | Interpolation-specific controllability diagnostics.** (F) Achieved mean RF response across the target grid. (G) Candidate-wise monotonicity fraction, defined as the fraction of valid seed-by-candidate trajectories that are non-decreasing from Q50 to Q65 to Q80. The metric tests ordering of requested targets and should not be interpreted as physical monotonicity without MD.
