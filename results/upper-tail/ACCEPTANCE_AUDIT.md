# Upper-tail acceptance audit

**Overall status: PASS_PREDICTION_PHASE_ONLY**

After training through Q80, does continuous target conditioning preserve near-boundary target control, monotonicity and support/calibration without presuming true extrapolation?

| Gate | Status |
|---|---|
| source_hash_and_locked_split | PASS |
| matched_three_arm_protocol | PASS |
| candidate_schema_provenance | PASS |
| required_metrics_and_unsupported_cells | PASS |
| binary_negative_control | PASS_WITH_DEGENERACY |
| paired_summary_compatibility | PASS |
| rf_calibration_vs_md_separation | PASS_WITH_MD_TODO |
| posthoc_fullrf_separation | PASS |
| prediction_phase_acceptance | PASS_PREDICTION_PHASE_ONLY |

## Explicit limitations

- Binary is a required degenerate single-class negative control under the frozen -4.0 threshold.
- 28 unsupported cells remain explicit in `unsupported_cells.csv`.
- RF residuals for generated candidates are not estimable until MD; locked-tail RF calibration is a surrogate audit only.
- Full-source RF artifacts are post-hoc and excluded from leakage-free claims.
- No MD or experimental conductivity claim is made.

## Compatibility layer

The new paired summaries, complete candidate schema, monotonicity detail, and residual calibration adapter are additive. Raw Upper-tail outputs and historical Interpolation/PR4/PR6 evidence were not overwritten.
