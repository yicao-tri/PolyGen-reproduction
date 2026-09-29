# Pre-MD Upper-tail benchmark and candidate comparison

## Question

Can continuous generation produce novel polymer units that a full-source RF
surrogate places above the Q80 training boundary, and do those candidates look
like known high-conductivity structures or like genuinely new chemistry?

## Selection rule

The primary MD queue uses only information available before MD:

1. continuous arm only;
2. valid structure and novel versus the Q80 training rows;
3. Full-source RF prediction above the actual Q80 training maximum
   (−4.084499 log10(S cm−1));
4. RF uncertainty < 0.35 and support ≥ 0.35.

The locked Q80–Q95 structures are **not** used for selection.

## Results before MD

- 6,000 candidates were rescored with the full-source RF.
- 31 continuous candidates passed the pre-MD upper-tail screen (1.55% of the
  2,000 continuous candidates).
- The maximum full-RF prediction among continuous candidates was −3.9424
  log10(S cm−1), which is 0.1421 log units above the actual Q80 boundary.
- The 20 highest-scoring continuous candidates are in
  `continuous_top20_for_md.csv`.

This is a **screening upper bound**, not a predicted MD maximum. The full RF
has seen the locked-tail labels, so these hits cannot establish extrapolation.

## Analogue comparison

For every selected candidate, the benchmark records:

- the five nearest Q80-training structures by Morgan/Tanimoto similarity;
- their mean and maximum conductivity;
- the candidate-to-analogue RF difference;
- a separate post-hoc comparison to the five nearest locked-tail structures.

The Q80-training top-5 analogue set is the primary comparison because it is
available without looking at the locked tail. The locked-tail analogue fields
are descriptive only and must not be used to select MD candidates or claim
generalization.

## Recommended MD design

Use the selected continuous candidates as one arm, paired with:

1. their Q80-training top-5 analogues;
2. matched binary candidates at the same target where valid;
3. a small uncertainty-high/support-low continuous stratum;
4. a boundary control stratum below or near Q80.

For every MD-tested structure, preserve the same endpoint and compute:

```text
MD conductivity
MD − FullRF prediction
MD − BlindRF prediction
MD − actual Q80 boundary
MD − mean(top-5 Q80 analogue conductivity)
```

The decisive upper-tail endpoint is `MD − actual Q80 boundary > 0`, not a
positive RF score. The most informative mechanism test is whether selected
continuous candidates have a positive MD contrast against their matched
Q80-training analogues and whether that contrast survives after accounting for
RF uncertainty and support.

## Files

- `continuous_predicted_upper_tail_candidates.csv`: all 31 selected candidates
  with train and post-hoc locked-tail top-5 comparisons.
- `continuous_top20_for_md.csv`: recommended first MD queue.
- `benchmark_summary.json`: counts and predicted screening maximum.
- `../publication/Figure_full_source_RF_response.svg`: updated full-RF
  response/MAE/validity figure.

## Interpretation warning

The full-source RF is a better-calibrated post-hoc surrogate than the blind
Q80-only RF, but it is not an independent oracle. MD remains necessary to
decide whether any selected candidate truly crosses Q80.
