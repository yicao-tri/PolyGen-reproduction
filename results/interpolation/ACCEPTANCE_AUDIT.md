# Interpolation acceptance audit

**Overall status: PASS**

This audit covers the prediction-only interpolation benchmark at Q50, Q65, and Q80. MD was not started.

## Required checks

- `source_hash_matches_manifest`: **PASS**
- `split_train_rows_match`: **PASS**
- `split_test_rows_match`: **PASS**
- `split_row_overlap_absent`: **PASS**
- `targets_are_q50_q65_q80`: **PASS**
- `matched_seed_manifest`: **PASS**
- `matched_budget_manifest`: **PASS**
- `candidate_schema_complete`: **PASS**
- `active_candidate_rows`: **PASS**
- `all_active_cells_present`: **PASS**
- `unconditional_blocked_explicit`: **PASS**
- `unconditional_not_fabricated`: **PASS**

## Arm and cell accounting

- Active generated arms: continuous and binary.
- Matched seeds: 17, 42, 202, 303, 907.
- Active cells: 2 arms × 5 seeds × 3 targets = 30 cells, 100 candidates per cell.
- Unconditional + reranking: explicitly blocked; zero rows are reported and no proxy candidates are presented as generation evidence.
- Unsupported active cells: none.

## Added audit artifacts

- `candidate_predictions_complete.csv`: original candidate rows plus explicit candidate and acquisition provenance.
- `metrics_complete.csv`: target error, strict-hit, validity, novelty, valid uniqueness, support, uncertainty, diversity, failure, unsupported-cell flag, and acquisition status.
- `paired_seed_contrasts.csv`: seed-level continuous-minus-binary contrasts.
- `negative_control.json`: machine-readable unconditional blocked status.
- `verification.json`: hashes, split checks, schema checks, cell checks, and claim boundary.

## Claim boundary

The result is surrogate-only evidence for in-support target control. It does not establish MD-confirmed conductivity, physical monotonicity, or extrapolation beyond the training distribution.
