# Interpolation publication figures

**Figure 1 | Interpolation response under matched target requests.** Direct counterpart to the upper-tail response figure. (A) Frozen RF predictions follow the requested Q50–Q80 curve for both arms. (B) Target MAE remains lower than the upper-tail benchmark because all requests lie within the generator/verifier training support. (C) Validity is retained across the internal target grid. Points and error bars are means ± SEM across five matched seeds.

**Figure 2 | Interpolation output quality.** Heatmaps show strict-hit rate and validity by arm and requested quantile. Unlike the upper-tail figure, no unsupported-cell masking is required: all six arm-by-target cells have generated candidates.

**Figure 3 | Interpolation-specific controllability.** (F) Mean achieved RF response versus requested target, with the identity target curve shown for reference. (G) Candidate-wise monotonicity is the fraction of valid seed-by-candidate trajectories that are non-decreasing from Q50 to Q65 to Q80. This diagnostic is specific to interpolation and should not be interpreted as physical monotonicity without MD.
