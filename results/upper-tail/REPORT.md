# Upper-tail prediction phase

Status: complete for the frozen prediction phase; MD was not started.

## Frozen boundary and split

The immutable HTP-MD source is `inputs/release-data/htpmd-trainset.csv` with
SHA-256 `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69`.
The nominal full-source Q80 is `-4.0844688003`, while the inclusive training
rule `log10(conductivity) <= Q80` gives 4,819 training rows and an actual
training maximum of `-4.0844991107`. The locked Q80–Q95 evaluation tail has
903 rows and zero exact-SMILES overlap with training.

The evaluated target grid is the actual training boundary, Q85, Q90, and Q95:
`-4.0844991`, `-4.0404290`, `-3.9875316`, and `-3.9020916` log10(S/cm).
All model fitting, filtering, and selection used only the 4,819 training rows.

## Main result

The RF verifier does not produce a single support- and uncertainty-gated
candidate above the actual training maximum in any arm or target cell. The
upper-tail predicted-hit rate is therefore 0/6,000 reported candidates. This
is a negative surrogate-extrapolation result, not evidence of validated
physical extrapolation.

Across all 20 cells per arm, descriptive means are:

| arm | validity | verifier target MAE | strict-hit rate | RF prediction mean | upper-tail predicted-hit |
|---|---:|---:|---:|---:|---:|
| continuous | 0.5745 | 0.3095 | 0.5510 | -4.3131 | 0.0000 |
| binary | 0.2300 | 0.2845* | 0.2150* | -4.3470 | 0.0000 |
| unconditional + reranking | 0.0015* | 0.2576* | 0.0015* | -4.3421 | 0.0000 |

An asterisk marks averages affected by unsupported cells with no valid output;
they should not be interpreted as complete-arm performance. The strict-hit
definition is verifier-defined: valid, novel, support ≥0.35, RF uncertainty
<0.35, and absolute RF target error <0.5 log units.

Continuous conditioning is the only arm with valid output in every target cell,
but its predictions remain below the training boundary and become less aligned
with the requested target by Q95. Monotonicity is not consistently preserved:
the continuous mean response is monotone in 1/5 seeds; binary is monotone in
3/5 seeds but is not a meaningful high/low comparison here; unconditional has
no interpretable target-response curve because target labels are applied only
after generation.

## Protocol blockers and alternatives

The existing binary threshold was frozen at `-4.0` to preserve the PR6/C1
estimand. Under the Q80 training split, all 4,819 training rows are below that
threshold, so the binary arm is single-class and becomes a degenerate control.
It is retained and explicitly labelled as such; it must not support an
apples-to-apples high/low claim.

The prespecified fallback is a training-median cutoff (`-4.3146323544`) that
would balance labels inside the truncated training distribution. It was not
executed because it changes the binary estimand and would be a separate
sensitivity experiment.

There are 28 unsupported cells: binary Q90/Q95 for all five seeds, plus
unconditional+rerranking at the boundary for three seeds and at Q85/Q90/Q95
for all five seeds. These are recorded in `unsupported_cells.csv`, not dropped.

The locked-tail verifier audit reports RF MAE `0.2618` and mean observed-minus-
predicted residual `+0.2618` log units across the 903 locked rows. This positive
tail residual is direct evidence that the frozen RF underpredicts observed tail
rows; it does not validate generated candidates or replace MD.

## Candidate handoff

`candidate_selection_for_md.csv` contains 183 candidates selected by the
stratified high-prediction/uncertainty/support rules. It is a review queue only:
all rows have `md_status=not_run`, and no MD process was launched.

## Reproducibility and provenance

- Frozen split, boundary, target grid, seeds, binary status: `frozen_manifest.json`
- Exact run contract and environment: `run_contract.json`
- Training and locked-tail rows: `train_rows.csv`, `locked_tail_rows.csv`
- Candidate-level RF predictions and filter decisions: `candidate_predictions.csv`
- Cell metrics: `metrics_by_cell.csv`, `cell_support.csv`, `unsupported_cells.csv`
- Monotonicity: `monotonicity.csv`
- Locked-tail RF calibration/support/residual audit: `locked_tail_verifier_audit.csv`, `verifier_metrics.json`
- Failure accounting: `failure_reasons.csv`
- MD review queue: `candidate_selection_for_md.csv`
- Producing code: `scripts/run_upper_tail_benchmark.py`

The result supports only a conditional statement about this frozen HTP-MD
representation and RF screening protocol. It does not support a claim of
measured conductivity, MD success, or true extrapolation beyond the observed
frontier.
