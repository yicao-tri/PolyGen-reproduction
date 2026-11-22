# MolMiner reproduction + WEECFP-SuRGE variant

A from-scratch PyTorch + RDKit implementation of the core mechanisms in
**MolMiner** (arXiv:2411.06608, fragment-based, order-agnostic, 3D-aware
autoregressive molecular design), plus a second variant that fuses in ideas
from **WEECFP-SuRGE** (arXiv:2609.04672): a parameter-free WEECFP fragment
embedding, and SuRGE rotary graph-distance positional encoding applied
alongside MolMiner's own Euclidean geometry bias.

This is **not** a byte-for-byte reproduction of either paper — there's no
public code, exact hyperparameters, or the papers' training data (ZINC-scale)
to match against. It's a faithful, runnable implementation of every mechanism
each paper describes, validated end-to-end (fragment decomposition → training
→ generation → valid-molecule output), with a few explicitly documented
simplifications. Treat it as a correct architectural skeleton to scale up, not
a benchmark-reproducing artifact.

A third, non-autoregressive **SuRGE-parallel** variant is also included
(`train_parallel.py` / `generate_parallel.py`) — it isn't in either paper, but
extends SuRGE's rotary encoding into a mechanism for deciding molecular
structure globally rather than one fragment at a time. See "A third variant"
below.

## What's faithful vs. simplified

| Mechanism | Status |
|---|---|
| Ring-system + isolated-bond fragment decomposition | Faithful (`fragments.py`) |
| Symmetry-aware attachment (canonical-rank classes) | Faithful (`fragments.py`) |
| Order-agnostic rollout (uniform random focal site) | Faithful (`rollout.py`) |
| Chemical validity by construction | Faithful (bonds only form at real open valences) |
| 12-property conditioning | 11 real RDKit descriptors + 1 **proxy** SAS (see `conditioning.py` docstring — Ertl's real SAS needs RDKit's Contrib `fpscores.pkl`, not in a plain pip install) |
| GMM completion of partially specified targets | Faithful (`conditioning.py`) |
| Geometry-aware attention bias (Gaussian-decayed centroid distance) | Faithful at generation time (incremental UFF relax after every attachment). At **training** time, approximated by slicing one whole-molecule ETKDG/UFF conformer per molecule instead of re-relaxing after every step (`geometry.py` docstring) |
| Auxiliary seed-fragment classifier | Faithful, simple feed-forward head over the conditioning vector |
| Attachment-class prediction | Simplified: a single shared class head (not conditioned on the predicted fragment identity via a pointer/cross-attention mechanism); invalid class indices are masked out at both train and generation time |
| WEECFP fingerprint | Faithful to the paper's description (MD5-strided signed writes, atomic-property block, neighbor-bond block, log-magnitude compression) |
| SuRGE rotary encoding | Faithful (`md` and `ref3` variants, exact RoPE-style rotation formula), applied over **fragment-tree** shortest-path distance rather than atom-sequence position |

## Layout

```
fragments.py     fragment decomposition, symmetry classes, per-class valence capacity
vocab.py         fragment-type vocabulary (canonical SMILES -> id) + PAD/SEAL tokens
rollout.py       order-agnostic molecular-story sampling + running site fractions
geometry.py      3D embedding/relaxation, per-fragment centroids, Gaussian distance kernel
weecfp.py        WEECFP fingerprint + SuRGE rotary graph-distance encoding
conditioning.py  12-property vector + GMM-based completion of partial targets
model.py         the shared transformer (baseline vs. WEECFP-SuRGE selected by flags)
dataset.py       molecule -> training Example (tensors + teacher-forcing targets)
train.py         training CLI for the two sequential variants (baseline / weecfp_surge)
generate.py      generation CLI for the two sequential variants
parallel_model.py    the SuRGE-parallel non-autoregressive set-prediction model
parallel_dataset.py  molecule -> ParallelExample (fragment set + positions + adjacency) + Hungarian matching
train_parallel.py    training CLI for the SuRGE-parallel variant
generate_parallel.py generation CLI for the SuRGE-parallel variant (Kruskal-style bond decoding)
data/sample_smiles.txt   139 bundled demo molecules (swap in ZINC/ChEMBL for real training)
```

## A third variant: SuRGE-parallel (non-autoregressive)

`train_parallel.py` / `generate_parallel.py` implement a genuinely different
generative paradigm from the two sequential variants above: instead of
growing the molecule one fragment at a time (pick an open site, attach a
fragment, repeat), the whole fragment SET is predicted at once, and the bond
structure is *decoded* from geometry rather than predicted as a sequence of
decisions:

1. **Parallel prediction.** `K` learned "slot" queries (DETR-style), conditioned
   on the property vector, run through a bidirectional transformer and each
   independently predicts a fragment identity and a SuRGE rotary position
   (`md` scalar or `ref3` 3-vector) — all `K` slots in one forward pass, no
   causal masking, no sequential dependency between them.
2. **How many slots are real** is predicted directly from the conditioning
   vector by a simple count classifier (reusing the same recipe as the
   seed-fragment head in the other variants), and slots `[0, count)` are
   always the active ones. An earlier version tried a per-slot existence
   classifier matched via Hungarian assignment over all `K` slots every step;
   at this dataset's scale that assignment never stabilized enough for slots
   to specialize (existence probabilities came out uniform across every slot,
   confirmed empirically) — fixing "how many" first turns the remaining
   match into a clean, always-square permutation problem instead.
3. **Bonds are decoded, not predicted.** Each slot also outputs a "bond
   vector"; that vector is rotated by the slot's *own* predicted SuRGE
   position (the exact same `apply_rotary`/`md_angles`/`ref3_angles` code used
   in the sequential WEECFP-SuRGE variant), and every pair of slots is scored
   by a plain dot product of their rotated vectors — symmetric by
   construction. Two fragments whose positions differ by "one bond" end up
   with a characteristic relative rotation the model learns to associate with
   a real edge.
4. **Kruskal-style greedy assembly.** At generation time, all candidate pairs
   are sorted by predicted bond score (descending) and accepted immediately
   the moment they're valid — no cycle (union-find, exactly Kruskal's MST
   check) and open valence on both sides — until no more valid, sufficiently
   confident pairs remain. This is "fill in the whole structure from a global
   ranking of candidate bonds" rather than "grow one fragment at a time."

Training is a DETR-style set-prediction loss (count classification + Hungarian-
matched fragment classification + position regression + pairwise edge BCE),
with `z` deliberately fixed to zero rather than sampled noise — random z
carrying no information about which specific molecule is the training target
was confirmed to collapse slot specialization at this dataset's scale (see
comments in `train_parallel.py`); diversity instead comes from the GMM's
property sampling and from multinomial (not argmax) fragment-identity
sampling per slot.

There is no Euclidean/3D geometry bias in this variant: no 3D structure
exists until bonds are decided, so SuRGE's graph-topological signal is the
only positional information available at prediction time — which is exactly
the point of this variant.

```bash
python -m molminer_repro.train_parallel --surge-mode ref3 --epochs 150
python -m molminer_repro.generate_parallel --checkpoint molminer_repro/checkpoints/surge_parallel.pt \
    --n 10 --properties "logP=2.5,QED=0.8"
```

## Benchmarking caveats (baseline vs. SuRGE-parallel)

Head-to-head numbers reported for these two variants (validity, uniqueness,
property-MAE, speed) came with real methodological asymmetries, found by
auditing both pipelines directly rather than just comparing outputs:

- **No train/test split exists anywhere.** Both variants train on, and have
  their vocabulary + GMM property-completer fit on, the exact same molecule
  set used at generation time. Every reported number is an in-distribution
  sampling-quality measurement, not a generalization test, for **both**
  models equally.
- **Validity is not a fair axis of comparison.** MolMiner's sequential
  tree-growth is architecturally incapable of producing a disconnected
  structure. SuRGE-parallel's threshold-and-Kruskal bond decoding is *not*
  inherently connected -- its "keep only the largest connected component"
  step is a repair heuristic that silently discards fragments that didn't
  bond confidently enough. Measured directly: **~35% of generations drop at
  least one predicted fragment, ~7.6% of all predicted fragments never reach
  the final molecule.** Both variants reporting "100% valid" is not a
  comparable achievement -- one gets it for free by construction, the other
  partly by discarding whatever would have broken it.
- **`train_parallel.py`'s `precompute()` drops any molecule with more than
  `max_slots` fragments; `train.py`'s does not.** On the bundled dataset this
  currently excludes zero molecules (max fragment count is well under the
  default cap), so it hasn't skewed any reported result yet, but at
  ZINC-scale (where >24-fragment molecules are common) the two variants would
  train on systematically different-sized subsets unless this is fixed.
- **Training budget/capacity were never matched.** Different epoch counts,
  different transformer depth, and different generation-time fragment caps
  between the two CLIs were each tuned to that variant's own convergence, not
  equalized against the other for a controlled comparison.
- Checked and **not** an issue: exact-duplicate-of-training-set rate is
  actually higher for the baseline (10% of generations) than for
  SuRGE-parallel (0%), so SuRGE-parallel's better property-MAE isn't
  explained by memorization. The wall-clock speed gap is also real and
  mechanistically explained (profiled: ~86% of the baseline's time is RDKit
  conformer embedding/relaxation, which SuRGE-parallel never does), not an
  artifact of the issues above.

## Usage

```bash
# Reproduce MolMiner (baseline: learned fragment embeddings, Euclidean geometry bias only)
python -m molminer_repro.train --variant baseline --epochs 60

# The WEECFP-SuRGE variant: + parameter-free WEECFP fragment embeddings,
# + SuRGE rotary graph-distance encoding (mean-distance or 3-reference-atom)
python -m molminer_repro.train --variant weecfp_surge --surge-mode ref3 --epochs 60

# Generate, optionally pinning a subset of the 12 properties (rest sampled from
# the fitted GMM so the full conditioning vector stays realistic)
python -m molminer_repro.generate --checkpoint molminer_repro/checkpoints/baseline.pt \
    --n 10 --properties "logP=2.5,QED=0.8"
```

Point `--data` at a larger SMILES file (one per line) to train on more than the
bundled demo set — the code has no dataset-size assumptions baked in, but
training and (especially) generation both call RDKit's ETKDG/UFF embedding
per step, so wall-clock time scales with molecule count × epochs.

## Architecture notes

- **Tokens are fragments** (rings-as-one-unit, or single bonds), placed in
  teacher-forced order via one causal-masked transformer pass per molecule —
  the standard trick for training an autoregressive model with random valid
  orderings in a single forward pass.
- **Every attachment decision is a query**: `(parent fragment's hidden state,
  which of its symmetry classes, running occupied/free/sealed fractions) ->
  (attach fragment X at class C | SEAL)`. This mirrors the paper's
  factorization exactly; only the class-index head is simplified (see table).
- **The WEECFP-SuRGE variant changes exactly two things**: fragment token
  embeddings get an added WEECFP projection (works for fragments never seen
  during training, since WEECFP is parameter-free), and attention gets a
  second, independently-scaled rotary term keyed on fragment-tree distance,
  applied *alongside* MolMiner's own Euclidean bias rather than replacing it.
