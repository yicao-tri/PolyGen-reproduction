# Experiment A: minGPT leakage audit and structure-disjoint rerun

## Result

The leakage concern is confirmed. The released conditional table contains
11,408 rows but only 6,024 unique p-SMILES. Its low-conductivity class has 5,704
rows and 5,704 unique structures; its high-conductivity class has 5,704 rows but
only 320 unique structures. The released pipeline applies `train_test_split`
to these already-balanced rows.

With the released `random_state=42` split, all 1,122 high-conductivity
validation rows occur in training. At the unique-structure level, all 312
positive validation structures overlap training. The negative-class overlap is
zero. The released validation loss therefore cannot support a claim of
generalization to unseen high-conductivity structures.

The corrected policy first deduplicates and stratifies the 6,024 structures,
then oversamples the positive class in training only. It preserves 9,126
balanced training rows (4,563 per label) while holding out 1,205 unique
validation structures (1,141 negative and 64 positive). Train/validation
structure overlap is zero for both labels.

An RDKit canonical-SMILES post-check parses every prepared row successfully.
It finds 312 canonical structures shared by train and validation under the
released split and zero under the corrected split. Thus the zero-overlap result
is not an artifact of comparing noncanonical strings.

## Apples-to-apples generation comparison

Both paired runs use seed 42, `gpt-nano`, 10,000 optimizer steps, batch size 64,
learning rate 5e-4, temperature 1.0, and 100 high-conductivity-conditioned
samples. Both start from random initialization. The intended experimental
variable is the split policy.

| Metric | Paired released-random | Paired structure-disjoint | Delta |
|---|---:|---:|---:|
| Validity | 0.96 | 0.93 | -0.03 |
| Uniqueness | 0.99 | 0.93 | -0.06 |
| Novelty | 0.61 | 0.42 | -0.19 |

For continuity, the pre-existing released-checkpoint seed-42 result was
validity 0.97, uniqueness 0.94, and novelty 0.57. Relative to that external
baseline, the corrected run changes by -0.04, -0.01, and -0.15 respectively.
That comparison is not as controlled because the released checkpoint's original
training seed and full provenance are unavailable.

## Interpretation

The executable conclusion survives in a narrower form: minGPT can generate a
high fraction of syntactically/chemically valid two-ended repeat-unit p-SMILES
under the positive label. The stronger conclusion does not survive this audit:
the released validation procedure does not establish conditional
generalization to unseen high-conductivity polymer structures.

In the paired rerun, correcting the split reduces all three headline generation
metrics, with the largest change in novelty (0.61 to 0.42). This is evidence that
the headline result is sensitive to leakage-safe data handling, not a precise
estimate of the expected degradation: there is one training seed and one
100-sample generation draw. Multiple training and generation seeds are needed
for uncertainty intervals.

Accordingly, prior numbers should not be used to make a self-generation or
prospective discovery claim to Ohsaki-san. They can be described as a released
workflow execution baseline. The structure-disjoint rerun supports feasibility
of repeat-unit generation, while prospective value still needs held-out
property/formulation evidence and downstream build/simulation checks.

## Evidence

- `results/experiment-a/split_audit.json`: released and corrected split counts
  and overlaps.
- `results/experiment-a/comparison.json`: machine-readable metrics and deltas.
- `results/experiment-a/canonical_overlap_audit.json`: RDKit canonical-structure
  overlap check.
- `results/experiment-a/released-random-seed42-10000/`: paired leaked-split run.
- `results/experiment-a/structure-disjoint-seed42-10000/`: paired corrected run.
- `scripts/mingpt_split.py`: deterministic split implementation.
- `tests/test_mingpt_split.py`: leakage, disjointness, balance, and determinism
  regression tests.
