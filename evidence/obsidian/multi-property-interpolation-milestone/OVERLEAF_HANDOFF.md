# Overleaf handoff — Multi-property interpolation

## Manuscript-level takeaway

Under a frozen HTP-MD split and matched five-seed protocol, six-dimensional conditioning did not improve surrogate-defined joint target control over scalar conductivity conditioning. Mean joint RMSE was 0.5793 for the multi-property arm and 0.5753 for the scalar arm; the paired multi-minus-scalar difference was +0.0041 with a 95% Student-t interval of −0.0116 to +0.0197. Joint strict-hit rates were effectively zero in both arms. This is a benchmark result about a frozen RF surrogate, not MD or experimental evidence.

## Suggested placement

- Main Results: Figure 1 or Figure 2, with the narrow null result and the exact paired contrast.
- Extended Data: Figure 3 for cell-level quality and Figure 4 for monotonicity/failure mechanisms.
- Methods: target construction, train-only transformations, support audit, paired seed unit, and candidate-level provenance.
- Limitations: no MD, no frontier crossing, no locked-holdout calibration artifact, and candidate-wise monotonicity not identifiable.

## Candidate prose

**Observed / manuscript-ready.** Under identical target cells, five seeds, generation budgets, decoding and filtering rules, six-dimensional conditioning did not reduce normalized joint RF error relative to scalar conductivity conditioning. The mean joint RMSE was 0.5793 versus 0.5753, respectively, with a paired multi-minus-scalar difference of +0.0041 (95% Student-t interval −0.0116 to +0.0197; seed-level n=5).

**Observed / manuscript-ready.** Joint strict-hit rates were effectively zero in both conditional arms (0.000095 in each arm after averaging over the 21 target cells and five seeds), indicating that the simultaneous validity, novelty, support, uncertainty and joint-error gate was substantially more stringent than any one-dimensional response trend.

**Observed / manuscript-ready with qualification.** Cell-mean RF predictions were monotonic across Q50→Q65→Q80 for conductivity in 5/5 multi-property seeds, but monotonicity was inconsistent for the other properties. Candidate-wise monotonicity cannot be claimed because target cells do not share structure identities.

**Unavailable / do not write as achieved.** No statement about MD-confirmed frontier crossing, experimental conductivity, residual calibration, or physical mechanism is supported by this package.

## Figure captions

Use the captions in `assets/figures/FIGURE_CAPTIONS.md` and `assets/figures/Figure_4_caption.md`. Preferred vector assets are:

- `assets/figures/Figure_1_property_probe_joint_error.svg`
- `assets/figures/Figure_2_coherent_joint_targets.svg`
- `assets/figures/Figure_3_cell_quality_audit.svg`
- `assets/figures/Figure_4_paired_quality_audit.svg`

## Exact numeric sources

- `assets/tables/arm_summary.csv`: arm means and 95% Student-t intervals.
- `assets/tables/paired_summary.csv`: seed-level paired contrasts.
- `assets/tables/property_monotonicity_summary.csv`: Q50→Q65→Q80 cell-mean monotonicity.
- `assets/tables/unavailable_metrics.csv`: metrics not identifiable or not run.
- `evidence/data/verification.json`: completion and pairing gate.

## Caveats that must survive editing

1. Seed, not candidate, is the independent unit.
2. Intervals are descriptive/exploratory over five seeds and are not multiplicity-adjusted confirmatory inference.
3. The target grid contains coherent train-only joint targets, not independent Cartesian quantile combinations.
4. Full candidate pools retain filtered rows and explicit failure reasons; do not report only eligible or RF top-1 rows.
5. RF predictions, support and uncertainty are surrogate-screening evidence.
6. MD and force-field coverage were not run by contract.
7. Checkpoint provenance is per seed and is recorded in `frozen_manifest.json`.

## Analysis path

The exact reproducibility chain is:

```text
candidate_predictions.csv + target_cells.csv
  → scripts/analyze_multi_property_interpolation.py
  → analysis/*.csv and analysis/*.json
  → scripts/render_multi_property_interpolation.py
  → scripts/render_multi_property_interpolation_analysis.py
  → publication/*.png, *.svg, *.pdf
```
