# Strict C1 MolMiner smoke record

Date: 2026-10-16

This record is an engineering preflight for the strict same-support C1
comparison. It includes real five-seed, 20-epoch and 50-epoch extensions, but
none of the small-model runs is a final publication leaderboard.

## Preflight status

- Source: the released PolyGen HTP-MD table, 6,024 rows, with the exact
  canonical Q80 split and `random_state=20260923`.
- Generator training support: 4,819 rows; locked support: 1,205 rows.
- Vocabulary/coarsification: complete for all 4,819 training rows.
- Rollout preprocessing: 110,681 training stories; 2,942 validation stories;
  27,553 locked-tail stories from 1,202/1,205 locked molecules. Three locked
  molecules were retained as OOD/drop records because their fragments were not
  in the training vocabulary.
- Packed loader: complete for train, validation, and test splits; all packed
  saturation features are finite.

## Reproducible smoke sequence

The first un-packed training attempt failed with NaN losses. The source rows,
properties, coordinates, and story arrays were finite. The failure was traced
to the legacy collate path dividing the all-zero BOS saturation row by zero.
The packed loader was then used; its BOS/padding handling returns a finite zero
feature vector.

The repaired run used one CPU seed, one epoch, 128-wide / two-layer model,
factored attachment head, and `condition_dropout=0.1`:

| checkpoint | train loss | validation loss | non-term top-1 | status |
|---|---:|---:|---:|---|
| packed, no condition dropout | 4.3306 | 1.7651 | 0.4620 | finite smoke pass |
| packed, `condition_dropout=0.1` | 4.3245 | 1.7643 | 0.4789 | generation-path smoke checkpoint |

The second run is the checkpoint used for generation because the generator
requires condition dropout for a partially specified property request.

## Generation smoke

Using the second checkpoint, prompt `log_conductivity=-3.6`, and eight fixed
seeds produced 4/8 valid two-star repeat units. Four seeds returned no unit.
The five-seed extension then trained seeds 17, 23, 31, 47, and 59 for five
epochs each and evaluated a common budget of 10 samples at each target
`-5/-4/-3` per seed. Across 150 requests it produced 47 valid two-star units,
8 frozen-RF strict hits, and a valid rate of 0.3133. The result is still
recorded as smoke-only: five epochs and a small model cannot support a final
validity, novelty, controllability, or cross-generator claim.

## Twenty-epoch engineering extension

To test whether the five-epoch result was dominated by under-training, the same
small model, exact C1 support, packed loader, and five seeds were trained for
20 epochs. A PyTorch 2.0.1 compatibility shim was required: the local runtime
does not accept the upstream `mmap` keyword, and its self-attention fast path
can turn the float padding mask into an all-masked query row during evaluation.
The first compatibility attempt retained finite weights but produced NaN
validation metrics; that failed run is preserved under
`evidence/experiments/molminer_strict_c1/extended_20epoch_seed17_compat/`.
The corrected package-local fallback completed 20/20 checkpoints for every
seed, with finite validation metrics and a finite best checkpoint.

Using the same 150-request generation budget and frozen verifier, the extended
arm produced 88 valid two-star units and 15 strict hits (valid rate 0.5867;
strict-hit rate 0.1000; valid-unit target MAE 0.6514), versus 47 valid units
and 8 strict hits in the five-epoch smoke (0.3133; 0.0533; MAE 0.7060).
These are real observed engineering-comparison measurements, summarized in
`assets/tables/T13_molminer_extended20_vs_smoke.csv` and
`assets/figures/S1_molminer_extended20_vs_smoke.*`. They do not close the
final-budget, independent checkpoint-selection, task-aligned WeeMiner, or
physical MD gates.

## Fifty-epoch engineering extension

To exercise the strategy's default MolMiner training horizon, the same small
model, exact 4,819-row C1 support, packed loader, PyTorch compatibility shim,
and five seeds (17, 23, 31, 47, 59) were trained for 50 epochs. All five runs
produced 50/50 finite checkpoints and finite selected checkpoints. The best
checkpoint epochs were 42, 40, 45, 49, and 48 for seeds 17, 23, 31, 47, and
59, respectively.

Under the same frozen-RF audit used for the smoke and 20-epoch extension—three
targets (`-5/-4/-3`), 10 samples per target and training seed, and 150 requests
total—the 50-epoch arm produced 125 valid two-star units and 25 strict hits
(valid rate 0.8333; strict-hit rate 0.1667; valid-unit target MAE 0.6580),
versus 47 and 8 in the five-epoch smoke (0.3133; 0.0533; MAE 0.7060). The
real comparison is in `assets/tables/T14_molminer_extended50_vs_smoke.csv` and
`assets/figures/S2_molminer_extended50_vs_smoke.*`.

This is stronger engineering evidence that the five-epoch smoke was
under-trained, but it remains bounded evidence: the model is small, the
generation budget is an engineering audit, checkpoint selection is not yet the
independent final publication protocol, WeeMiner is not task-aligned, and
strict hits are frozen-RF labels rather than physical conductivity.

## Remaining strict-comparison TODO

1. Freeze the full training configuration and checkpoint-selection rule.
2. Freeze and run the final publication-budget MolMiner training on five paired
   seeds with an independent checkpoint-selection protocol; the 50-epoch
   extension is evidence for engineering progress, not the final leaderboard.
3. Run a task-aligned WeeMiner/equivalent arm on the same rows, support,
   verifier, and budget; the available WeeMiner assets remain ZINC/logP-only.
4. Generate the final matched candidate budget and recompute validity,
   uniqueness, novelty, support, target MAE, strict hit, and uncertainty.
5. Keep the existing released-checkpoint MolMiner table as descriptive only.

The five-seed smoke table is `assets/tables/T12_molminer_strict_c1_smoke.csv`;
its raw per-sample and per-seed outputs are under
`evidence/experiments/molminer_strict_c1/five_seed_generation_smoke/`.

Evidence: `evidence/experiments/molminer_strict_c1/`,
`evidence/data/molminer_strict_c1_smoke_audit.json`, and the preparation/
preprocessing scripts under `evidence/scripts/`.
