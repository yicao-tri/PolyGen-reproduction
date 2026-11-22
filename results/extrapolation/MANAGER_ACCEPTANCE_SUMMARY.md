# Manager acceptance summary — true conductivity extrapolation

## Decision

**PASS — prediction phase only.** The frozen extrapolation benchmark is complete and artifact-verified. **MD-confirmed extrapolation is NOT ASSESSED** because MD was explicitly out of scope and must not be inferred from RF predictions.

## Scientific question and current interpretation

Question: above the actual training maximum, with Q80–Q100 fully locked, does continuous conditioning promote, suppress, or only exploit the surrogate?

Observed evidence is neutral-to-limiting for a physical extrapolation claim: continuous conditioning retains valid and strict-hit candidates near Q90 and `train_max+0.25`, but no arm produces a support/uncertainty-gated RF prediction above `train_max`. The locked-tail RF audit has positive observed-minus-predicted residual, so surrogate scores cannot certify frontier crossing. Binary is a prespecified degenerate negative control, not a successful target-control comparator under this split.

## Frozen protocol

- Source SHA256: `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69`
- Training rows: `4819`; actual `train_max`: `-4.084499111`
- Locked rows: `1205`; train/locked exact SMILES overlap: `0`
- Arms: continuous, fixed-threshold binary, true constant-zero unconditional+rerranking
- Matched seeds: 17, 42, 202, 303, 907; 100 candidates/cell; 400 unconditional raw candidates/seed; 1000 training steps; temperature 1.0; top-k 40; block size 64

## Headline surrogate metrics

Means across five matched seeds; RF frontier-crossing is after validity, novelty, support and uncertainty gates. These are surrogate-only summaries.

| Arm | Target | Validity | Strict-hit | RF frontier crossing |
|---|---|---:|---:|---:|
| continuous | Q90 | 0.564 | 0.536 | 0.000 |
| binary | Q90 | 0.000 | 0.000 | 0.000 |
| unconditional_reranking | Q90 | 1.000 | 0.962 | 0.000 |
| continuous | Q100 | 0.280 | 0.000 | 0.000 |
| binary | Q100 | 0.000 | 0.000 | 0.000 |
| unconditional_reranking | Q100 | 0.956 | 0.000 | 0.000 |
| continuous | train_max_plus_0.25 | 0.544 | 0.398 | 0.000 |
| binary | train_max_plus_0.25 | 0.000 | 0.000 | 0.000 |
| unconditional_reranking | train_max_plus_0.25 | 0.156 | 0.000 | 0.000 |
| continuous | train_max_plus_0.50 | 0.390 | 0.000 | 0.000 |
| binary | train_max_plus_0.50 | 0.000 | 0.000 | 0.000 |
| unconditional_reranking | train_max_plus_0.50 | 0.000 | 0.000 | 0.000 |

## Acceptance gates

| Gate | Status | Evidence |
|---|---|---|
| source_hash | PASS | `verification.json:source_hash_matches_manifest` |
| Q80_locked_split_and_actual_train_max | PASS | `verification.json:train_rows_are_q80_only + locked_rows_excluded_from_train` |
| required_targets | PASS | `frozen_manifest.json:Q90,Q100,train_max_plus_0.25,train_max_plus_0.50` |
| matched_three_arm_seed_budget | PASS | `15 runs, 60 cells, 100 candidates/cell, 400 unconditional raw pool/seed` |
| candidate_schema_and_provenance | PASS | `verification.json:required columns, unique IDs and provenance` |
| binary_negative_control | PASS_WITH_BLOCKED_CELLS | `binary_status=degenerate_single_class; 20 cells explicitly blocked` |
| unsupported_cells | PASS | `unsupported_cells.csv: 26 explicit rows` |
| paired_seed_contrast | PASS | `paired_contrasts.csv + paired_seed_summary.csv; descriptive, no independent-candidate inference` |
| residual_and_calibration_reporting | PASS_WITH_MD_TODO | `residual_calibration_by_cell.csv + locked_tail_verifier_audit.csv; generated residual not estimable before MD` |
| surrogate_only_vs_md_separation | PASS | `region_summary.json: md_evidence.status=not_run` |
| figure_png_svg_provenance | PASS | `verification.json artifact_sha256 + publication/FIGURE_CAPTIONS.md` |
| prediction_phase_acceptance | PASS | `verification.json and pairing_acceptance_audit.json both pass` |
| MD_confirmed_extrapolation_claim | NOT_ASSESSED | `MD explicitly out of scope; no physical frontier-crossing claim permitted` |

## Explicit blocked/unsupported cells

- Binary blocked: `20` cells = seeds `[17, 42, 202, 303, 907]` × all four targets. Reason: fixed `-4.0` cutoff is single-class after Q80 truncation.
- Unconditional unsupported: `6` cells: seed 17 / train_max_plus_0.50, seed 42 / train_max_plus_0.50, seed 202 / train_max_plus_0.50, seed 303 / train_max_plus_0.50, seed 907 / train_max_plus_0.25, seed 907 / train_max_plus_0.50. Reason: no valid generated candidate.
- Continuous unsupported: none.

## Residual/calibration boundary

Generated-candidate residual is explicitly `not_estimable_md_not_run` for every cell. The locked-tail RF audit is the available calibration reference: MAE `0.310`, RMSE `0.330`, mean residual `+0.310`.

## MD TODO

`candidate_selection_for_md.csv` contains `200` stratified proposed candidates. It is not MD evidence. Future MD must record build success, force-field coverage, replica status, MD value and `MD−RF` residual with symmetric continuous/binary budgets.

## Evidence

- Machine-readable summary: `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/extrapolation/manager_acceptance_summary.json`
- Per-cell residual/calibration adapter: `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/extrapolation/residual_calibration_by_cell.csv`
- Paired seed summary: `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/extrapolation/paired_seed_summary.csv`
- Final verification: `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/extrapolation/verification.json`
