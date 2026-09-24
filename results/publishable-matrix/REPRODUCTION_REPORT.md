# PolyGen binary-to-continuous conditioning reproduction

## Outcome

The full executable, non-MD pipeline was completed for seed 101. Six matched
arms were trained for 10,000 steps and sampled at five in-distribution targets:
the original q95 binary conditioner, continuous MLP, continuous linear
projection, five-bin conditioner, shuffled-condition negative control, and
unconditional control. Each arm produced 2,500 raw samples (500 per target).

The seed-101 result supports a narrow conclusion: increasing conditioning
resolution beyond the original high/low label materially improves surrogate
target response. It does **not** yet show that the continuous MLP is superior
to every discretization: the five-bin arm had the best calibration in this run.
No claim of physical conductivity is made because full-atom MD is pending.

## What the original workflow does

The released PolyGen data contain 6,024 repeat units represented as p-SMILES
with `[Cu]` and `[Au]` connection markers. The paper uses an 80/20 split,
64-token minGPT sequences, five repeated conditioning tokens, a q95 high class,
and oversampling of the high class. The discovery stage samples 100,000
high-label candidates, ranks them with an HTP-MD-trained graph model, selects 50,
and runs five full-atom MD replicas per candidate. The reported MD setup builds
linear homopolymers with at least 150 backbone heavy atoms, LiTFSI at 1.5 mol
kg⁻¹, PCFF+, sequential NVT/NPT equilibration, and 5 ns 353 K NVT production
with a 2 fs step; conductivity is obtained by cluster Nernst–Einstein analysis.

The public repository contains generation code, checkpoints, data, and example
LAMMPS inputs, but not the publication graph-verifier checkpoint or a turnkey
p-SMILES-to-PCFF+ system builder. Therefore this package stops honestly at a
per-candidate MD handoff rather than substituting the RF surrogate for MD.

## Matched experiment design

- Canonical repeat-unit identities were grouped before an 80/10/10 split:
  4,819 train, 602 validation, 603 held-out test.
- All conditional arms use the same 9,209-row oversampled training multiset.
  The unconditional arm uses the 4,819 unique training structures.
- Architecture, vocabulary, 64-token context, five-token prefix, optimizer,
  batch size, 10,000 updates, sampling temperature, targets and sample count are
  held fixed. Only the conditioning representation changes.
- Targets are train q10/q30/q50/q70/q90: −4.5464, −4.3763, −4.2648, −4.1556,
  −3.9836 log10 conductivity. The binary q95 threshold is −3.8998, so all five
  targets map to the same LOW label. This is the central resolution limitation.

## Validation

String validity, RDKit parsing, exactly one `[Cu]` and `[Au]`, terminal/single
connection bonds, canonical uniqueness, training-set novelty, Morgan diversity,
SA score, nearest-training Tanimoto support, and two frozen forward models were
recorded for every sample. The held-out RF/Morgan verifier achieved RMSE 0.1528,
MAE 0.1217 and R² 0.4529; the independent descriptor HGB achieved RMSE 0.1648,
MAE 0.1290 and R² 0.3637. Their mean is used only for screening.

Exact canonical overlap across splits is zero. Near-neighbour separation is not
perfect: held-out test median nearest-train Tanimoto is 0.721; 19.4% are ≥0.8
and 3.65% are ≥0.9. This is disclosed as structural proximity, not hidden.

## Seed-101 results

| Arm | Pearson r | Slope | Calibration MAE | Strict hit | Relaxed hit | Monotonic steps |
|---|---:|---:|---:|---:|---:|---:|
| Binary | −0.154 | −0.002 | 0.159 | 0.306 | 0.573 | 2/4 |
| Continuous MLP | 0.953 | 0.348 | 0.105 | 0.432 | 0.740 | 4/4 |
| Continuous linear | 0.940 | 0.330 | 0.111 | 0.420 | 0.732 | 4/4 |
| Five-bin | 0.882 | 0.682 | 0.080 | 0.449 | 0.758 | 4/4 |
| Shuffled condition | 0.766 | 0.064 | 0.208 | 0.231 | 0.432 | 2/4 |
| Unconditional | 0.670 | 0.017 | 0.157 | 0.311 | 0.580 | 2/4 |

Generation quality remained comparable: binary versus continuous MLP polymer
validity was 0.825 vs 0.848, uniqueness 0.834 vs 0.851, novelty 0.735 vs 0.744,
SA<5 rate 0.648 vs 0.679, and diversity 0.745 vs 0.737.

The local released-checkpoint sanity baseline (100 samples, seed 42) produced
0.97 validity, 0.94 uniqueness, 0.57 novelty, 0.941 synthesizability and 0.692
diversity. It is a small local execution check, not a replacement for the
publication's large discovery run and not directly comparable to the matched
2,500-sample per-arm experiment.

## Candidate and MD handoff

Twenty binary and twenty continuous candidates passed validity, novelty,
uniqueness, structural support and uncertainty/disagreement filters. Their
complete records are in `tables/md_candidates.csv`; each also has a folder under
`md_handoff/` with metadata and the public LAMMPS input templates. Every folder
is marked `WAITING_FOR_SYSTEM_BUILD`. A runnable topology is intentionally not
fabricated.

The two 20-candidate sets contain seven identical canonical p-SMILES (35% of
each list; Jaccard overlap 7/33 = 21.2%). The 33 distinct repeat units are
rendered in `candidate_structures/`; publication overview copies are also in
`figures/binary_20_candidates.*`, `figures/continuous_20_candidates.*`, and
`figures/shared_7_candidates.*`. `[Cu]` and `[Au]` are connection markers in
the released p-SMILES convention, not a claim that the polymers contain copper
or gold.

## Claim boundary and TODO

Can claim now: for seed 101 and frozen surrogate screening, continuous and
five-bin conditioning produce a monotonic requested-to-predicted response that
the q95 binary baseline cannot express over q10–q90.

Cannot claim now: experimental conductivity; MD-confirmed conductivity;
continuous superiority to five-bin conditioning; multi-seed robustness;
statistical significance across training runs; synthesizability in the lab.

TODO: run seeds 202 and 303, report paired seed-level intervals/tests, obtain the
original system builder/PCFF+ parameterization workflow, run 40×5 MD replicas,
parse failures without exclusion, and generate requested-versus-MD figures.
