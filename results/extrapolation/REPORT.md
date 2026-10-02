# True conductivity extrapolation benchmark

Status: complete prediction phase; MD not run by contract.

The frozen training boundary is `-4.084499111` log10(S/cm), with 4819 rows at or below full-source Q80. The locked Q80-Q100 tail contains 1205 rows and is used only for post-run verifier auditing.

## Arm and evidence boundary

Continuous, fixed-threshold binary, and a true constant-zero unconditional model used the matched five-seed, 1000-step, temperature-1.0, top-k-40 protocol. The binary arm is a required negative control: its fixed -4.0 label is single-class after Q80 truncation and cannot encode the extrapolation target. The RF is the only released verifier; GNN fields are explicitly unavailable. Force-field coverage and MD are not assessed.

## Key artifacts

- `candidate_predictions.csv`: one row per generated candidate with identity, structure, arm, seed, target, validity, novelty, support, RF prediction/uncertainty, target error, filter decisions, failure reason, provenance, force-field status and MD status.
- `metrics_by_cell.csv` and `paired_contrasts.csv`: matched cell summaries and descriptive continuous-minus-binary contrasts.
- `unsupported_cells.csv`: binary target-degeneracy blocks and any empty/invalid cells; none are silently dropped.
- `candidate_selection_for_md.csv`: proposed stratified candidates only; it is not MD evidence.
- `pairing_acceptance_audit.json`: programmatic split, schema, pairing, provenance and no-MD checks.

## Claim boundary

Surrogate-supported frontier crossings are screening signals only. No candidate is MD-confirmed, and the benchmark does not support an experimentally measured conductivity claim.
