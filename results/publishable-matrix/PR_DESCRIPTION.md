## Why this experiment

PolyGen conditions minGPT generation with a binary high/low conductivity label.
That representation cannot express a requested conductivity trajectory within
one class. This PR reproduces the released minGPT generation/validation path and
changes only the conditioning representation, testing whether additional
resolution improves controllability while preserving generation quality.

## Experimental contract

- Source: released 6,024-repeat-unit HTP-MD/PolyGen dataset.
- Split: canonical-identity-grouped 80/10/10, yielding 4,819 train, 602
  validation, and 603 held-out test structures; exact canonical overlap is zero.
- Conditional training multiset: the same 9,209 oversampled rows for every
  conditional arm.
- Architecture/budget: minGPT `gpt-nano`, 64-token context, five-token prefix,
  batch 64, AdamW learning rate 5e-4, 10,000 steps, seed 101.
- Sampling: temperature 1.0; 500 generations at each train q10/q30/q50/q70/q90
  target (2,500 raw samples per arm).
- Arms: original q95 binary label, continuous MLP, continuous linear projection,
  five-bin discretization, shuffled-condition negative control, unconditional.
- Deferred robustness: seeds 202 and 303 are explicit TODOs; no multi-seed
  significance claim is made in this PR.

The five requested targets range from -4.5464 to -3.9836 log10 conductivity.
The binary high threshold is -3.8998, so all five targets map to LOW. This is
the resolution limitation being measured.

## Validation and pairing

Every generated row records raw output, canonical p-SMILES, parsing validity,
exactly one terminal single-bond `[Cu]`/`[Au]` connection pair, uniqueness,
training-set novelty, sampling settings and rank. Additional analysis records
SA score, Morgan diversity, nearest-training Tanimoto support, RF tree spread,
and disagreement between two frozen forward models.

Held-out verifier performance:

| Verifier | RMSE | MAE | R2 |
|---|---:|---:|---:|
| Morgan RF | 0.1528 | 0.1217 | 0.4529 |
| Descriptor HGB | 0.1648 | 0.1290 | 0.3637 |

The verifier ensemble is a screening instrument only. It is not the paper's
graph checkpoint and is not a replacement for full-atom MD.

## Seed-101 findings

| Arm | Pearson r | Response slope | Calibration MAE | Strict hit | Relaxed hit | Monotonic steps |
|---|---:|---:|---:|---:|---:|---:|
| Binary | -0.154 | -0.002 | 0.159 | 0.306 | 0.573 | 2/4 |
| Continuous MLP | 0.953 | 0.348 | 0.105 | 0.432 | 0.740 | 4/4 |
| Continuous linear | 0.940 | 0.330 | 0.111 | 0.420 | 0.732 | 4/4 |
| Five-bin | 0.882 | 0.682 | 0.080 | 0.449 | 0.758 | 4/4 |
| Shuffled | 0.766 | 0.064 | 0.208 | 0.231 | 0.432 | 2/4 |
| Unconditional | 0.670 | 0.017 | 0.157 | 0.311 | 0.580 | 2/4 |

Binary versus continuous MLP quality remains similar: polymer validity 0.825
vs 0.848, uniqueness 0.834 vs 0.851, novelty 0.735 vs 0.744, SA<5 rate 0.648
vs 0.679, and diversity 0.745 vs 0.737.

Interpretation: increasing condition resolution improves seed-101 surrogate
controllability relative to q95 binary conditioning. This run does not establish
that the continuous MLP is better than a sensible multi-bin conditioner: the
five-bin arm has the best calibration here.

## Candidate selection and new structure figures

The frozen screen selected 20 binary and 20 continuous candidates. Seven
canonical p-SMILES overlap, leaving 33 distinct repeat units (35% list overlap;
Jaccard 21.2%). This PR adds:

- two matched 20-candidate overview grids;
- a seven-candidate overlap grid;
- 40 individual PNG/SVG depictions and a machine-readable index;
- green overlap borders and arm-specific binary/continuous borders;
- target and surrogate prediction labels for each candidate.

`[Cu]` and `[Au]` are retained as polymer connection markers and must not be
interpreted as physical Cu/Au content.

## Full-atom MD status

Forty per-candidate handoff folders include metadata and public LAMMPS input
templates. All remain `WAITING_FOR_SYSTEM_BUILD`. The public release does not
contain the publication p-SMILES-to-linear-chain PCFF+ builder or complete
parameterization workflow. Required completion is: >=150 backbone heavy atoms,
LiTFSI 1.5 mol kg-1, PCFF+, sequential NVT/NPT equilibration, five independent
353 K NVT replicas, 5 ns per replica, 2 fs timestep, and cluster
Nernst-Einstein conductivity. No surrogate result is presented as MD.

## Reproduction and artifact map

- Run contract: `results/publishable-matrix/experiment_config.yaml`
- Exact commands: `results/publishable-matrix/EXACT_COMMANDS.md`
- Full report: `results/publishable-matrix/REPRODUCTION_REPORT.md`
- Training/generation: `scripts/run_publishable_matrix.py`
- Frozen verifier analysis: `scripts/analyze_publishable_matrix.py`
- Plot Atlas figures: `scripts/plot_publishable_matrix.py`
- Candidate depictions: `scripts/render_candidate_structures.py`
- MD handoff generation: `scripts/build_md_handoff.py`
- All generated rows: `results/publishable-matrix/tables/generated_candidates.csv`
- Endpoint metrics: `results/publishable-matrix/tables/controllability_endpoints.csv`
- Candidate manifest: `results/publishable-matrix/tables/md_candidates.csv`
- Figures: `results/publishable-matrix/figures/`

## Checks run

- Six arm outputs present, each with 2,500 generated rows.
- 15,000 generated rows in the consolidated table.
- 20 binary + 20 continuous MD candidates; seven canonical overlaps.
- 40 individual PNG and 40 individual SVG candidate depictions.
- Every figure exported as PNG and SVG and visually inspected.
- Exact/canonical split overlap is zero; near-neighbour split statistics are
  disclosed in `tables/split_audit.csv`.

## Claim boundary

Supported: seed-101 surrogate controllability and generation-quality comparison.

Not supported: experimental conductivity, MD-confirmed conductivity,
continuous-over-five-bin superiority, multi-seed robustness, training-run
statistical significance, or laboratory synthesizability.
