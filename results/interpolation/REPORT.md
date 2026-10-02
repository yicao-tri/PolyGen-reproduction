# Interpolation prediction-phase report

Status: prediction phase complete for continuous and binary arms; MD not run.

Acceptance audit: [`ACCEPTANCE_AUDIT.md`](ACCEPTANCE_AUDIT.md), with machine-readable checks in [`verification.json`](verification.json). The audit passes all required interpolation gates. The unconditional+rerranking arm remains explicitly blocked and is not represented by proxy candidates.

The frozen targets are Q50 = -4.26534, Q65 = -4.18738, and Q80 = -4.08452 in log10 conductivity. Five matched seeds (17, 42, 202, 303, 907), 100 candidates per arm/seed/target, identical decoding settings, and the existing frozen RF verifier were used.

Machine-readable artifacts:

- `frozen_manifest.json`: split, target, seed, checkpoint, and setting manifest.
- `candidate_predictions.csv`: one row per candidate with prediction, uncertainty, support, novelty, filter decision, and strict-hit flag.
- `metrics_by_cell.csv`: validity, novelty, uniqueness, support, uncertainty, target error, strict-hit, and failure metrics.
- `summary.json`: verifier metrics and monotonicity summaries.
- `metrics_complete.csv`: audit-complete metrics including valid uniqueness, diversity, failure, unsupported-cell flag, and acquisition status.
- `paired_seed_contrasts.csv`: paired continuous-minus-binary seed-level contrasts.

Across the five seeds, continuous strict-hit rates by target were approximately 0.50, 0.53, and 0.55 for Q50/Q65/Q80; binary rates were approximately 0.48, 0.51, and 0.52. Continuous target MAE was approximately 0.070, 0.109, and 0.166; binary was approximately 0.109, 0.114, and 0.201. These are surrogate-screening results only and are not MD or experimental conductivity evidence.

Monotonicity is reported per seed in `summary.json`; it is a candidate-wise fraction of valid candidates whose predicted conductivity is non-decreasing across Q50→Q65→Q80. It is not a claim of physical monotonicity.

## Blockers and acceptance status

1. Unconditional+rerranking is recorded as blocked because no released unconditional generator checkpoint is available in the repository. No proxy samples were relabeled as unconditional generation.
2. MD has not been started, per instruction. Therefore no validated hit, calibration-to-MD, force-field coverage, or residual active-learning update can be claimed.
3. Candidate selection for MD is not finalized here; the full candidate table is available for review before any simulation.

The split and target manifest are frozen and reproducible; source files and historical PR4/PR6 evidence were not modified. The next required gate is manager review of the candidate table and an explicit decision on how to supply the unconditional baseline before MD.
