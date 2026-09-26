# PolyGen generation grid design

## Canonical location and migration boundary

The canonical working tree is `/Users/yicao/Documents/ARC/PolyGen-reproduction`.
The PFP top-1 pilot was migrated as a separate evidence commit and remains a
Stage-3/physical-validation artifact. It is not part of the generation grid.

The generation audit was migrated separately under
`results/experiment-c/generation-benchmark-audit/`. Historical outputs retain
their original provenance and are not relabeled as new grid runs.

## Comparability rule

The inferential identity is `arm × seed × target × config_id`. Results may be
compared only when model family, initialization/checkpoint, data split,
training budget, temperature, target allocation, and sample budget match.
Different model families, split policies, checkpoint initialization, or sample
budgets must remain separate configurations.

The current five-seed C1 result is the strongest existing paired generation
evidence: gpt-nano, 1,000 optimizer steps, temperature 1.0, fixed C1 split,
binary versus continuous arms, and 300 raw samples per arm/seed (100 per
target). It is not silently pooled with development diffusion or minGPT smoke
runs.

## Proposed grid

Use a staged grid rather than an unconstrained Cartesian explosion:

1. **Baseline replay:** gpt-nano, 1,000 steps, temperature 1.0, the fixed C1
   split, binary and continuous arms, five paired seeds.
2. **Temperature sensitivity:** temperature 0.8 and 1.2, holding all other
   fields fixed.
3. **Training-budget sensitivity:** 2,000 steps at temperature 1.0, holding
   all other fields fixed.
4. **Model-size sensitivity:** only if a real larger architecture/checkpoint
   and its training entry point are available. Never substitute repeated
   gpt-nano runs for this arm.
5. **Diffusion comparisons:** execute in a separate model-family block with
   its own split, steps, sampler temperature/noise schedule, checkpoint,
   target allocation, and verifier contract. Do not merge it into the C1
   binary/continuous estimand.

For every new arm/config, use the same five paired seeds and at least 1,000 raw
samples per arm/config. A simple allocation is 200 samples per seed, with an
explicit deterministic target allocation such as 67/67/66. Binary and
continuous arms must use exactly the same allocation.

## Required artifact contract

Each config receives an immutable directory under `results/experiment-c/grid/`
containing config JSON, command, environment, source hashes, checkpoint hashes,
seed schedule, target allocation, raw samples, verifier outputs, metrics,
ranking table, and audit status. No output is written into historical C1
directories.

Primary metrics are target MAE, target correlation, monotonicity, strict-hit,
uncertainty calibration, validity, uniqueness, novelty, similarity, diversity,
synthesizability, valid-and-novel yield, and buildable yield where the required
inputs exist. Missing metrics remain explicitly unavailable.

The primary candidate ranking remains the frozen rule:

`valid AND novel AND in-support AND uncertainty gate`, then descending
`predicted_log_sigma - 1.96 × uncertainty`.

Conductivity×novelty, conductivity×diversity, and
conductivity×synthesizability are secondary Pareto views; no new weighted
primary score is introduced.

## Current status

The grid manifest is an inventory and design contract. The `new grid run`
placeholder has not been executed. Stage 3 PFP/MD remains outside this grid and
requires explicit user sign-off.
