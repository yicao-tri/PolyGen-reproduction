# PolyGen Work — Upper-tail: publishable results

## Main conclusion

Under a frozen Q80 training boundary, continuous conditioning has a clear
upper-tail *coverage and control* advantage over the frozen binary control:
it is valid in every target cell, retains 0.56–0.58 validity through Q95, and
retains 0.522 strict-hit at Q95. Binary conditioning is valid only at the
boundary and Q85, then becomes unsupported at Q90/Q95. However, this is not a
validated extrapolation advantage: the RF verifier predicts no generated
candidate above the actual training maximum in any arm or target cell.

The defensible claim is therefore: **continuous conditioning preserves usable
near-boundary target control and substantially higher valid-output yield, but
this prediction-only benchmark provides no evidence of surrogate-confirmed
upper-tail extrapolation beyond Q80.**

## Frozen protocol

- Source: `inputs/release-data/htpmd-trainset.csv`; SHA-256 is recorded in
  `frozen_manifest.json`.
- Training: 4,819 rows with log10 conductivity ≤ nominal Q80.
- Actual training maximum: −4.084499 log10(S cm−1).
- Locked Q80–Q95 audit tail: 903 rows, zero exact-SMILES overlap with training.
- Arms: continuous, binary, unconditional + reranking.
- Matched seeds: 17, 42, 202, 303, 907; 1,000 training steps; 100 reported
  candidates per target cell.
- MD: not run; all conclusions below are RF/verifier-level only.

## Endpoint summary

Values are means across the five matched seeds; SEMs and all target cells are in
`upper_tail_all_metrics.csv`. Unsupported cells are not converted into zeros
for interpretation.

| Arm / cell | RF prediction | RF uncertainty | Support | Novelty | Strict-hit | Validity | Uniqueness | Diversity | Failure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Continuous / boundary | −4.315 | 0.088 | 0.592 | 0.560 | 0.554 | 0.576 | 0.576 | 0.750 | 0.424 |
| Continuous / Q95 | −4.308 | 0.090 | 0.564 | 0.552 | 0.522 | 0.560 | 0.556 | 0.749 | 0.440 |
| Binary / boundary | −4.348 | 0.094 | 0.604 | 0.438 | 0.434 | 0.464 | 0.462 | 0.749 | 0.536 |
| Binary / Q85 | −4.346 | 0.095 | 0.603 | 0.426 | 0.456 | 0.426 | 0.416 | 0.752 | 0.574 |
| Binary / Q90, Q95 | unsupported | unsupported | unsupported | unsupported | 0 | 0 | 0 | — | 1 |
| Unconditional + reranking / Q85–Q95 | unsupported | unsupported | unsupported | unsupported | 0 | 0 | 0 | — | 1 |

Target MAE rises for continuous conditioning from 0.231 at the boundary to
0.406 log units at Q95. Its RF response remains nearly flat around −4.31,
well below the requested Q95 target (−3.902) and below the training maximum.
Thus target adherence degrades with distance even though valid output remains
available.

## Monotonicity and failure modes

The continuous RF-response curve is monotone in only 1/5 seeds; binary is
monotone in 3/5 seeds but is not an interpretable high/low comparison because
the frozen −4.0 threshold creates a single-class training set after Q80
truncation. Unconditional+rerranking has no intrinsic target-response curve;
targets are assigned after generation.

The frozen binary threshold is therefore a protocol limitation, not evidence
that binary conditioning is intrinsically incapable of upper-tail control. A
training-median threshold (−4.314632) is a valid sensitivity experiment, but
it changes the binary estimand and must remain separate from the primary result.

## RF residual and interpretation boundary

On the locked source tail, the RF has MAE 0.262, RMSE 0.269, and mean observed
minus predicted residual +0.262 log units (SD 0.060). The RF systematically
underpredicts the held-out tail. Therefore RF predictions cannot simultaneously
serve as the discovery objective and as proof that a generated candidate crosses
the frontier. The 183-row `candidate_selection_for_md.csv` is a stratified MD
review queue, not a validated discovery set.

## Figure and table package

- Figure 1: `Figure_1_upper_tail_response.{pdf,svg,png}` — RF response, target
  MAE, and validity.
- Figure 2: `Figure_2_upper_tail_quality_heatmap.{pdf,svg,png}` — strict-hit and
  validity with unsupported cells visible.
- Figure 3: `Figure_3_locked_tail_rf_calibration.{pdf,svg,png}` — RF tail bias and
  residual calibration.
- Complete metric table: `upper_tail_all_metrics.csv`.
- Cell-level evidence: `../metrics_by_cell.csv`, `../unsupported_cells.csv`,
  `../monotonicity.csv`, `../failure_reasons.csv`.

These figures support a negative-but-informative conclusion about
surrogate-confirmed extrapolation. They do not establish MD-confirmed or
experimentally measured conductivity.
