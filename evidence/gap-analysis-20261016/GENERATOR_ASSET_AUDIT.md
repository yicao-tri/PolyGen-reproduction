# Generator asset audit: MolMiner and WeeMiner

Date: 2026-10-16

## Outcome

The local generator assets are sufficient for a descriptive MolMiner C1
behavioral baseline and for an independent WeeMiner software smoke test. They
are not sufficient for the strict same-support C1 comparison requested by the
blueprint.

## MolMiner

The released `best_polyru_s42.pth` checkpoint and the five-seed matched-budget
runner are present. The real comparison contains 1,500 MolMiner samples over
targets `-5, -4, -3`, with the frozen PolyGen C1 random-forest verifier. The
headline values are:

- 1,465/1,500 valid repeat units;
- 1,345 unique valid units, of which 1,231 are novel relative to the merged
  MolMiner corpus;
- common-verifier RMSE `0.1569`, MAE `0.1243`, R² `0.4980`;
- strict hit rate `0.042`, `0.754`, and `0.000` at targets `-5`, `-4`, and
  `-3`, respectively.

This remains descriptive because the checkpoint was trained on the merged
corpus, which includes HTP-MD rows. It is not a held-out MolMiner model on the
PolyGen C1 split.

The strict retraining route is now executable through an isolated preflight.
The package rebuilt the split-specific 4,819-row training support, vocabulary,
rollouts, and packed tensors. The first legacy un-packed smoke failed with NaN
losses because the collate path divided the all-zero BOS saturation row by zero;
the packed loader correctly handles this row and produced finite training and
validation metrics. A second one-seed/one-epoch smoke with
`condition_dropout=0.1` also produced a loadable checkpoint and a generation
smoke of 4/8 valid two-star units at `log_conductivity=-3.6`. A follow-up
five-seed/five-epoch smoke (seeds 17, 23, 31, 47, 59) used a common 150-sample
generation budget and produced 47 valid units and 8 frozen-RF strict hits. A
real five-seed/20-epoch engineering extension then completed all 20 epochs
with finite checkpoints; under the same 150-request audit it produced 88 valid
units and 15 frozen-RF strict hits. The default-horizon 50-epoch extension
then completed 50/50 finite checkpoints for all five seeds and produced 125
valid units and 25 frozen-RF strict hits. The comparisons are rendered in S1
and S2 and tabulated in T13 and T14.

These are chain-of-custody and software-path results only. They do not replace
the required final frozen-budget comparison, independent checkpoint-selection
rule, matched candidate budget, or held-out evaluation.

## WeeMiner

The WeeMiner/WEECFP-SuRGE code and documentation are present under the local
resource checkout. The code targets ZINC/logP, not PolyGen C1 conductivity. Its
full ZINC train/valid/test CSVs and trained checkpoints are not bundled, and
the full documented training script explicitly describes the run as a fresh
retrain. Thus this is not an available C1 comparison arm.

The available local regression smoke test was run with the existing MolMiner
comparison virtual environment and passed all four tests. The test includes a
tiny train/reload/generate path; its measured smoke calibration was logP MAE
`1.355`, raw R² `-1.297`, and grouped R² `-0.920`. Those numbers are software
smoke evidence only and must not enter the PolyGen conductivity comparison.

## Required replacement experiment

For publication-grade cross-generator claims, create a task-aligned WeeMiner
or equivalent checkpoint using the same C1 train rows, five paired seeds, the
same candidate budget, and the same frozen verifier. Report validity, novelty,
support, uncertainty, strict hit, and target MAE with the generator-native
legality metrics kept separate. Do not merge the ZINC/logP smoke outputs into
T5.

## Evidence files

- MolMiner source snapshots: `evidence/source_snapshots/molminer/`.
- MolMiner real comparison data: `evidence/data/molminer_comparison/`.
- MolMiner existing real figure: `assets/figures/molminer_existing/`.
- WeeMiner source snapshots: `evidence/source_snapshots/weeminer/`.
- WeeMiner smoke result: `evidence/data/weeminer_smoke_test.txt`.
- Strict C1 preflight and smoke record: `STRICT_MOLMINER_SMOKE.md` and
  `evidence/data/molminer_strict_c1_smoke_audit.json`.
- Strict C1 isolated data, vocabularies, rollouts, packed tensors, checkpoints,
  and generation smoke: `evidence/experiments/molminer_strict_c1/`.
- Five-seed strict smoke table: `assets/tables/T12_molminer_strict_c1_smoke.csv`.
- Five-seed 20-epoch engineering comparison: `assets/tables/T13_molminer_extended20_vs_smoke.csv` and `assets/figures/S1_molminer_extended20_vs_smoke.*`.
- Five-seed 50-epoch engineering comparison: `assets/tables/T14_molminer_extended50_vs_smoke.csv` and `assets/figures/S2_molminer_extended50_vs_smoke.*`.
- The current publication table remains `assets/tables/T5_cross_generator.csv`;
  `assets/tables/T11_molminer_descriptive_c1.csv` preserves the full real
  target-level comparison for audit.
