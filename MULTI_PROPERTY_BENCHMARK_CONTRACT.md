# Multi-property implicit-conditioning benchmark contract

Status: design freeze candidate; no definitive multi-property results exist yet.

## Question and estimand

Does replacing the existing scalar conductivity condition with a jointly normalized
implicit condition improve controllable, support-aware generation of polymer
electrolytes across interpolation, upper-tail, and locked property extrapolation?

The primary contrast is paired continuous multi-property conditioning versus the
single-property continuous conductivity benchmark, using the same source rows,
seeds, generation counts, token model, decoder, filters, RF evaluation protocol,
and report schema. Binary high/low and unconditional+rerranking are controls, not
claims of multi-property precision.

## Source and properties

Canonical source: `inputs/release-data/htpmd-trainset.csv`.

Joint condition vector (all six fields, transformed before fitting):

1. `log10(conductivity)`
2. `log10(li_diffusivity)`
3. `log10(tfsi_diffusivity)`
4. `log10(poly_diffusivity)`
5. `transference_number` (raw, with invalid/nonphysical values audited rather than silently clipped)
6. `molality` (raw; near-degenerate support must be reported)

`trajectory_id`, structure identity, force-field, temperature, simulation time,
component labels, and atom counts are provenance/covariates only. They are not
conditioning targets in the first benchmark because several are constant or
metadata-like in the released table and would confound the property estimand.

The transform, per-dimension train-only center/scale, missing/nonfinite policy,
and covariance/support audit must be frozen before model fitting. No auxiliary
property loss is allowed in the primary arm.

## Arms and pairing

- `multi_continuous`: six-dimensional normalized condition vector concatenated via
  one learned prefix embedding, trained with the existing autoregressive MLE.
- `scalar_continuous`: existing conductivity-only condition, retained as the
  direct historical comparator.
- `binary_conductivity`: existing high/low conductivity interface; it receives no
  continuous target vector and is a negative control for fine joint control.
- `unconditional_reranking`: constant-condition generator plus frozen, separate
  property surrogate ranking; no target information enters generation.

All arms use matched seeds, optimizer steps, batch size, temperature, top-k,
generation counts, validity filters, and candidate schema. A target cell is a
joint vector; cells that are unsupported or degenerate are retained in an
`unsupported_cells.csv` table.

## Three regions

- Interpolation: target vectors at Q50, Q65, and Q80 per property, plus a
  predeclared coherent joint target set sampled from the train-only empirical
  copula/Gaussian model. No independent Cartesian quantile combinations are
  allowed without a support audit.
- Upper-tail: train only through each property's Q80 rule, with Q80--Q95 target
  vectors defined from the full source only for post-run evaluation/queries.
  Property-wise and joint target support are reported separately.
- Extrapolation: lock every row outside the training region from generator,
  surrogate, tuning, filtering, and selection. Query the coherent joint targets
  at Q90, Q100, train_max+0.25, and train_max+0.50 in transformed dimensions;
  if a joint target is not feasible, report it as unsupported rather than
  substituting an arbitrary vector.

For all regions, locked rows may be used only in the post-run audit of observed
values, never in fitting, threshold selection, or candidate selection.

## Candidate and surrogate outputs

Every candidate row must include region, arm, seed, target cell/vector, candidate
ID, structure, validity, novelty, uniqueness, support, RF prediction and
uncertainty for every property, joint target error, per-property target error,
filter decisions, failure reason, acquisition provenance, MD status, and force-
field coverage status. RF/GNN/surrogate evidence and MD evidence remain separate.

## Acceptance gates

1. Frozen source hash, split/target manifest, transform/scaler manifest, and seed
   schedule are present.
2. Locked holdout rows are absent from generator/surrogate fitting, tuning,
   filtering, and selection; this is verified programmatically.
3. All arm budgets and stochastic settings are matched.
4. All candidates are traceable and all empty/unsupported cells are explicit.
5. Summary tables and figures use the existing single-property schema adapter;
   absolute target-response, paired arm contrasts, support/uncertainty/failure,
   and candidate audit figures are emitted as SVG and PNG.
6. Negative controls include binary degeneracy, unconditional reranking,
   invalid structures, low support/high uncertainty, and target-vector
   incompatibility.
7. No MD or experimental claim is made until a separately approved, symmetric
   MD protocol is executed.

