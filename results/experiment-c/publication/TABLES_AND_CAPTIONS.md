# Experiment C publication tables and figure captions

## Table 1. Five-seed paired C1 outcomes

| Outcome | Binary mean | Continuous mean | Paired difference | 95% t interval | Paired t-test p |
|---|---:|---:|---:|---:|---:|
| Strict target-hit rate | 0.1587 | 0.1780 | +0.0193 | [0.0064, 0.0322] | 0.0141 |
| Target MAE (log10 S cm^-1) | 0.6940 | 0.6331 | -0.0609 | [-0.0728, -0.0490] | 0.000143 |
| Validity | 0.5220 | 0.4547 | -0.0673 | [-0.1303, -0.0044] | 0.04112 |
| Novelty | 0.5033 | 0.4313 | -0.0720 | [-0.1431, -0.0009] | 0.04828 |
| OOD rate | 0.0040 | 0.0093 | +0.0053 | [-0.0016, 0.0123] | 0.0993 |

Note: the seed is the inferential unit (n=5 paired seeds). The two-sided exact sign-test p value for the primary hit-rate effect is 0.0625. The t intervals and p values are exploratory because n is small.

## Table 2. Target-specific outcomes

| Arm | Target | Hit rate | Target MAE | Mean verifier prediction | Validity | Novelty | OOD rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Binary | -5.0 | 0.000 | 0.698 | -4.302 | 0.504 | 0.486 | 0.008 |
| Binary | -4.0 | 0.476 | 0.198 | -4.195 | 0.500 | 0.480 | 0.004 |
| Binary | -3.0 | 0.000 | 1.186 | -4.186 | 0.562 | 0.544 | 0.000 |
| Continuous | -5.0 | 0.006 | 0.632 | -4.368 | 0.406 | 0.396 | 0.002 |
| Continuous | -4.0 | 0.528 | 0.212 | -4.210 | 0.554 | 0.538 | 0.008 |
| Continuous | -3.0 | 0.000 | 1.055 | -4.055 | 0.404 | 0.360 | 0.018 |

## Figure captions

**Figure 1. Continuous conditioning improves target adherence with a validity tradeoff.** (A) Mean frozen-verifier prediction at each requested log-conductivity target; error bars show SEM across five training/generation seeds. The dashed line is ideal calibration. (B) Strict target-hit rates for paired binary and continuous runs; each connected pair is one seed. (C) Mean paired differences with 95% t intervals. Positive hit-rate and negative target-MAE differences favor continuous conditioning, whereas negative validity and novelty differences expose the chemical-yield cost.

**Figure 2. Seed-level primary effect.** Continuous-minus-binary strict target-hit-rate differences for each paired seed and their mean with 95% t interval. All five effects are positive; the exact two-sided sign-test p value is 0.0625.

**Figure S1. Deterministic candidate-structure sheets.** Two eligible unique candidates are selected per arm, seed and target from the original three-seed panel using the frozen score target error + 0.25 x verifier uncertainty. Structures illustrate generator output and are not MD- or experimentally validated discoveries.
