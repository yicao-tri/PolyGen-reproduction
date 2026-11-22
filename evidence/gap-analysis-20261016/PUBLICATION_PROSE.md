# Publication prose — Pitch × PolyGen gap analysis

**Evidence status.** This text is ready for manuscript or pitch insertion at
the current evidence boundary. It deliberately separates observed surrogate
results from planned physical validation. Any sentence marked **[PLANNED]**
must be replaced after the corresponding experiment produces locked, auditable
measurements.

## Abstract-style summary

Conditional generation improves local target control only when the verifier can
resolve the target region. On the frozen C1 benchmark, continuous conditioning
increased the strict target-hit rate from 0.1587 to 0.1780 and reduced target
MAE from 0.6940 to 0.6331 across five matched training seeds, but it also
reduced validity from 0.5220 to 0.4547 and novelty from 0.5033 to 0.4313.
In the locked tail, the blind random-forest verifier had MAE 0.310 log10(S/cm)
and a mean observed-minus-predicted residual of +0.310 log10(S/cm), while its
full-source post-hoc counterpart had MAE 0.131. The resulting four RF-only
extrapolation cells had zero accepted frontier crossings for every arm and
query. These results establish a verifier-limited decision boundary, not a
physical failure of the generator: no extrapolation candidate currently has a
candidate-specific PCFF+ parameterization or a converged MD measurement.

## Results

### In-support controllability has a measurable trade-off

We evaluated three matched arms on the frozen C1 support using five paired
training seeds. Continuous conditioning produced a higher verifier-defined
strict target-hit rate than the binary arm (0.1780 versus 0.1587; paired
effect +0.0193, 95% paired-seed t interval [+0.0064, +0.0322]) and a lower
target MAE (0.6331 versus 0.6940). The same intervention lowered validity
(0.4547 versus 0.5220) and novelty (0.4313 versus 0.5033). The appropriate
interpretation is therefore a support-aware trade-off rather than unconditional
generator superiority. Replication units are training seeds; generated
molecules are not treated as independent biological or physical replicates.

### The verifier is least informative where extrapolation is being decided

The locked Q80–Q100 tail contains 1,205 source rows beyond the frozen training
boundary of −4.0845 log10(S/cm). The leakage-free blind RF predicts this region
with MAE 0.310 log10(S/cm) and a mean observed-minus-predicted residual of
+0.310 log10(S/cm). Its predictions occupy a substantially narrower band below
the observed tail than the labels themselves. A full-source RF reduces MAE to
0.131 only after seeing the locked-tail labels; it is consequently a diagnostic
audit and not a valid extrapolation endpoint. The corrected audit computes
correlation across all three target levels within each arm and seed, rather
than within a single constant-target bin; the corrected ranges are 0.274–0.507
for the binary arm and 0.717–0.845 for the continuous arm.

### RF-only frontier crossing is unresolved, not a physical negative result

At Q90, Q100, train-maximum +0.25, and train-maximum +0.50, no candidate in
any arm passed the frozen RF frontier-crossing gate after validity, novelty,
support, and uncertainty filters. The fixed binary arm is structurally
unsupported beyond Q80 because its truncated labels become single-class. The
zero crossing rate must therefore be reported as a surrogate/verifier result;
it must not be described as evidence that the generator cannot produce a
physically high-conductivity structure. The planned next experiment is a
stratified physical queue with candidate-specific PCFF+, five replicas per
structure, convergence checks, and RF-to-MD residual calibration.

### Strict-generator evidence is currently an engineering smoke boundary

The strict MolMiner preflight reconstructs the exact 4,819-row C1 training
support, vocabulary, rollouts, and packed tensors. A legacy un-packed path
produced NaNs because the all-zero BOS saturation row was divided by zero; the
packed loader repaired this data-path issue. Five small-model training seeds
(17, 23, 31, 47, 59) completed a five-epoch smoke. Under a common frozen-RF
audit of 150 requests, 47 valid two-star units and 8 strict hits were observed
(valid rate 0.3133; strict-hit rate 0.0533; valid-unit target MAE 0.7060).
These measurements establish reproducible software and data-path behavior only.
They are not the final matched-budget MolMiner result, not a WeeMiner
comparison, and not a physical conductivity result.

### Longer MolMiner runs improve the engineering boundary but do not close it

To test whether the five-epoch smoke was dominated by under-training, we ran
the same split-specific small model for 20 epochs at five training seeds
(17, 23, 31, 47, and 59). All five runs completed 20/20 checkpoints with
finite validation metrics and finite selected checkpoints. Under the same
frozen-RF generation audit—three targets (`-5/-4/-3`), 10 samples per target
and training seed, and 150 requests total—the extended arm produced 88 valid
two-star units and 15 strict hits, compared with 47 valid units and 8 strict
hits in the five-epoch smoke. Thus the observed valid rate increased from
0.3133 to 0.5867, the strict-hit rate from 0.0533 to 0.1000, and the
valid-unit target MAE changed from 0.7060 to 0.6514. S1 and T13 report the
20-epoch seed-level values. Extending the same setup to the strategy's default
50-epoch horizon completed 50/50 finite checkpoints for each seed and yielded
125 valid units and 25 strict hits in the same 150-request audit (valid rate
0.8333; strict-hit rate 0.1667; valid-unit target MAE 0.6580). S2 and T14
report that real comparison. These are observed engineering outcomes, but the
model remains small, the checkpoint selection is not yet the final independent
publication protocol, WeeMiner is not task-aligned, and no physical
conductivity claim follows from the frozen-RF strict-hit label.

The local PyTorch 2.0.1 runtime also exposed an environment-specific failure:
the initial compatibility attempt yielded NaN validation metrics because the
evaluation fast path mishandled the float padding mask. The failed run is
retained as audit evidence; a package-local fallback then produced finite
metrics for all five extended runs. This repair is a software reproducibility
note, not a scientific performance claim.

### Provenance and structural-OOD boundaries

The source contains 6,024 canonical rows, with 4,819 training rows and 1,205
locked-tail rows. An exact canonical overlap audit found 59 overlaps with the
available PI1M source; a systematic 1-in-10 exploratory Morgan screen found 21
rows with Tanimoto similarity at least 0.85, including 14 non-exact rows. The
latter is not a full-source absence proof. A released-random split audit found
312 canonical overlaps, whereas the exact structure-disjoint audit found zero;
the latter is a leakage audit and should not be called scaffold- or
family-level structural OOD without the missing family annotations and matched
checkpoints.

## Methods and reporting contract

All primary prediction comparisons use the frozen Q80 split, matched training
seeds, the same validity/novelty/support/uncertainty filters, and the blind RF
endpoint. The full-source RF is retained only as a post-hoc verifier audit.
Each figure caption states whether values are observed, planned, or synthetic;
unsupported cells remain visible rather than being converted to zero quality.
The physical-validation gate requires candidate-specific PCFF+ typing, charges,
topology, bonded and non-bonded coefficients, a complete SHA-256 bundle, a
passing run-0 acceptance, five-replica MD, and convergence before a physical
crossing can be claimed.

## Figure and table insertion map

| Manuscript location | Asset | Status and required wording |
|---|---|---|
| Main framework | F1 | Observed prediction-stage evidence; physical/update loop dashed and planned |
| Main controllability | F2–F4 | Observed RF/surrogate results; no physical conductivity claim |
| Main verifier audit | F5/P2 | Blind RF is the leakage-free endpoint; full-source RF is diagnostic only |
| Decision-value backup | P1 | Observed in-support trade-off; seed-level replication |
| Physical next-action schematic | P3/F6 | RF panel observed; PCFF+/PFP ladder is planned or smoke-only |
| Generator grid | F9 repaired | Real nine-configuration RF-surrogate audit; not measured conductivity |
| Strict generator audit | T12 and strict smoke evidence | Five-epoch engineering smoke only |
| Extended strict generator audit | S1/T13 and S2/T14 | Real five-seed 20-epoch and 50-epoch engineering comparisons; not final leaderboard or physical validation |
| Representation/data ablation | F7 | **[PLANNED] Synthetic placeholder; replace with real ablation measurements** |
| Decision-change update | F8 | **[PLANNED] Synthetic placeholder; replace after MD and residual calibration** |

## Limitations and replacement instructions

The present package is publication-ready for the surrogate-only,
verifier-limited claim boundary, but not for a final physical-validation claim.
Before submission, replace F7/F8 with real outputs, freeze the final MolMiner
budget and independent checkpoint-selection protocol, complete the
task-aligned WeeMiner arms, obtain the candidate-specific PCFF+ bundle, run the
pre-registered five-replica MD queue, and recompute T4/F6 and the decision-
change analysis from locked measurements. Do not synchronize the Overleaf or
submission-root manuscript until the project owner authorizes that write.

## Source map

- Numeric results: `evidence/data/c1_five_seed_effect_summary.csv`,
  `evidence/data/locked_tail_verifier_audit.csv`, and
  `evidence/data/extrapolation_aggregate_metrics.csv`.
- Figure captions: `assets/figures/FIGURE_CAPTIONS.md`.
- Physical gate: `evidence/data/final_readiness_audit.json` and
  `evidence/data/pcff_plus_bundle_audit/pcff_plus_bundle_audit.json`.
- Strict generator audit: `STRICT_MOLMINER_SMOKE.md`, T12, and
  `evidence/experiments/molminer_strict_c1/five_seed_generation_smoke/`.
- Extended strict generator audit: `T13_molminer_extended20_vs_smoke.csv`,
  `S1_molminer_extended20_vs_smoke.*`, `T14_molminer_extended50_vs_smoke.csv`,
  `S2_molminer_extended50_vs_smoke.*`,
  `evidence/experiments/molminer_strict_c1/extended_20epoch_training_summary.csv`,
  `evidence/experiments/molminer_strict_c1/extended_20epoch_generation/`,
  `evidence/experiments/molminer_strict_c1/extended_50epoch_training_summary.csv`,
  and `evidence/experiments/molminer_strict_c1/extended_50epoch_generation/`.
