# Multi-property implicit-conditioning TODO

This checklist is evidence-driven. A checked item requires a file, command,
exit code, or audit that proves it; task commentary is not completion evidence.

## Done: asset feasibility

- [x] Confirm canonical HTP-MD source and SHA-256.
- [x] Confirm all six requested fields are finite and non-missing.
- [x] Record train-only transforms: log10 for four diffusivity/conductivity
  fields; raw audited values for transference number and molality.
- [x] Record constant metadata fields and exclude them from the first property
  target vector.
- [x] Record the six-dimensional Q80 intersection: 2,494/6,024 rows.
- [x] Freeze the common design contract in
  `MULTI_PROPERTY_BENCHMARK_CONTRACT.md`.

Evidence: `results/multi-property/manager-audit/`.

## Required implementation

- [ ] Implement a six-dimensional condition encoder in the existing GPT prefix
  pathway; keep the autoregressive MLE objective and add no auxiliary property
  loss.
- [ ] Implement train-only scaler/covariance/support audit and persist its hash.
- [ ] Implement a joint surrogate suite with per-property RF mean/tree SD and a
  declared joint support/error rule.
- [ ] Implement a schema adapter so scalar historical tables and multi-property
  tables use the same candidate, metric, failure, and provenance columns.
- [ ] Add unit tests for transforms, target-cell construction, locked-row
  exclusion, condition dimensionality, candidate IDs, and arm pairing.

## Interpolation

- [ ] Freeze split, transforms, coherent Q50/Q65/Q80 targets, seeds and budgets.
- [ ] Run multi-continuous, scalar-continuous, binary, and unconditional arms.
- [ ] Emit candidate table, per-cell metrics, paired contrasts, unsupported cells,
  failure table, leakage audit, run manifest and exit codes.
- [ ] Emit absolute response, paired contrast, support/uncertainty/failure,
  and candidate audit figures as SVG and PNG.

## Upper-tail

- [ ] Freeze the per-property Q80 training rule and the joint training subset.
- [ ] Lock Q80--Q95 rows from generator, surrogate, tuning, filtering and
  selection; use them only for post-run audit.
- [ ] Run all four arms under matched budgets and report property-wise and joint
  target adherence/monotonicity.
- [ ] Emit the complete artifact and figure set above.

## Extrapolation

- [ ] Freeze the locked-tail split and actual train maxima per transformed field.
- [ ] Query coherent Q90, Q100, train_max+0.25 and train_max+0.50 vectors.
- [ ] Report unsupported target vectors explicitly; never substitute arbitrary
  Cartesian quantiles.
- [ ] Run all four arms only after the locked-row leakage audit passes.
- [ ] Report surrogate frontier crossing separately from MD-confirmed crossing;
  no MD claim is allowed in this prediction stage.

## MD and publication gate

- [ ] Manager review of candidate table before any MD launch.
- [ ] Symmetric continuous/binary Tier 1 budget: 48--96 total candidates.
- [ ] Symmetric Tier 2 budget: 12--24 candidates, at least five replicas where
  feasible.
- [ ] Stratify MD candidates by predicted value, uncertainty, support/novelty,
  and structural distance; do not select RF top-1 only.
- [ ] Record MD failure and force-field coverage separately from surrogate data.
- [ ] Fit residual `log_sigma_MD - log_sigma_RF` discrepancy/calibration models
  and generate the next-round acquisition plan.
- [ ] Only then write the publication-level cross-region conclusion.

