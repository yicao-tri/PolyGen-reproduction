# WeeMiner — technical writeup

Audience: an LLM (or engineer) picking up this codebase cold. This document
covers the algorithm, the training pipeline, every fragment-selection
strategy tried, and the full set of measured results, including negative
results and known limitations. Dense and factual by design — see
`weeminer_presentation/` for the slide-deck version (includes a
results-vs-literature slide, §8) and `molminer_repro/best_method.py` for
the single best-performing entry point.

All file paths below are relative to `molminer_repro/` (the package
directory), except `weeminer_presentation/` and any path already given a
`molminer_repro/` prefix — both are relative to the repo root.

## 0. What this is

A reproduction of MolMiner-style fragment-based molecule generation
(WEECFP-SuRGE), extended with a fragment-selection mechanism ("WeeMiner" —
Plan E: rollout-scored selection judged by a 4-head progress ensemble) that
measurably improves property-conditioned generation calibration over both
this repo's own baseline and the original paper's reported numbers on the
one metric that's directly comparable (see §6 for the honest caveats on
that comparison).

Core files:
- `seqassemble_model.py` — the model (`SeqAssembleModel`): causal
  rotary-attention transformer trunk + 4 heads.
- `train_seqassemble.py` — trains the trunk + all 4 heads jointly on real
  ZINC data.
- `finetune_progress_head.py` — repairs/improves `progress_head` via
  self-generated data, after the joint training above.
- `generate_seqassemble.py` — baseline (N=1) generation, `load_checkpoint`.
- `generate_seqassemble_strategies.py` — Plans A-E (fragment-selection
  strategies layered on top of baseline generation).
- `best_method.py` — **the designated best-performing method**: Plan E +
  4-head ensemble, winning hyperparameters, ready to call.
- `benchmark_full_comparison.py` — the comparison harness used for §7/§8.

## 1. Architecture (the trunk)

`SeqAssembleModel` (in `seqassemble_model.py`) is an autoregressive
sequence model over fragments, not atoms. One molecule = a sequence of
fragment tokens (from a ~3,035-entry vocabulary built by decomposing the
training set) plus a SEAL/STOP token.

- **`BatchedCausalRotaryAttention`**: causal self-attention where positional
  information is injected via rotary embeddings derived from each
  fragment's **SuRGE position** — a relational-distance embedding (graph
  distance to reference fragments, `ref3_positions`/`mean_distance_positions`
  in `weecfp.py`), not a sequence index. 3 layers, `d_model=256`.
- **Input embedding** per step: fragment identity embedding + a cached
  **WEECFP identity embedding** (`fragment_weecfp_embedding`, computed once
  per fragment *type*, order-independent) + the fragment's SuRGE position
  (injected via rotary rotation, not concatenation) + the conditioning
  vector `cond_vec` (12 standardized molecular properties, added at every
  position via `cond_proj`).
- **4 heads**, all reading the same trunk hidden state:
  - `action_head`: distribution over "next fragment, or STOP."
  - `pos_head`: predicts the next fragment's approximate SuRGE position.
  - `bond_vec_head`: produces a per-fragment vector later used for
    pairwise bond scoring (rotary rotate-then-dot-product, same mechanism
    as `generate_parallel.py`'s SuRGE-parallel variant).
  - `progress_head`: predicts the *eventual finished molecule's* full
    12-property vector from *any* partial prefix. Not used at all in the
    original MolMiner design — added specifically to support Plans D/E
    (see §5). 2-layer MLP (`Linear -> GELU -> Linear`, `d_model -> d_model
    -> 12`).

Assembly (turning a finished fragment+position sequence into a molecule)
is **not** learned autoregressively — it's a separate deterministic
decode step: `bond_vec_head` output + SuRGE positions -> rotary
rotate-and-dot-product pairwise bond scores -> two-phase Kruskal's-algorithm
greedy acceptance (trusted high-score edges first, then a vacancy-filling
pass) -> `assemble_fragments(..., allow_atom_overlap=False)` (in
`fragments.py`) builds one valence-respecting molecular graph -> RDKit
sanitizes -> canonical SMILES. If the accepted edges leave more than one
connected component, only the largest is kept and the molecule is flagged
`was_fragmented=True`.

## 2. Placement strategy vs. MolMiner — the core architectural difference

This is the single most important structural fact about this repo,
documented in `seqassemble_model.py`'s own module docstring:

- **MolMiner (baseline / the paper)**: at each generation step, pick the
  next fragment *and commit to a specific attachment site* (a specific atom
  on the already-growing molecule) *immediately*. A bond is formed the
  moment a fragment is placed. The partial molecule is always a single
  connected, chemically valid structure at every intermediate step
  (tree-growth, with a privileged seed fragment).
- **WeeMiner / SuRGE-style (this repo)**: at each step, pick the next
  fragment *and a rough relational position* (SuRGE graph-distance
  coordinate) — **no site selection, no bond commitment, no valence
  bookkeeping happens during the loop at all**. Fragments accumulate as an
  *unconnected set* with relational coordinates. Only after the *entire*
  sequence is generated (STOP emitted or the 40-fragment cap hit) does a
  single global bond-decoding pass (§1's Kruskal decode) decide **every**
  bond at once, from the final positions.

Practical consequence: MolMiner's construction can never produce a
disconnected result (structurally impossible by design). WeeMiner's *can*
— the global decode sometimes leaves multiple components, hence
`was_fragmented` and non-zero fragmentation rates throughout §7/§8 (the
paper reports 0% fragmentation; this repo's best rate is 4.0%, Plan C —
see §5). This is a real, currently-unresolved structural gap, not a bug to
patch — it's the direct cost of deferring connectivity decisions to a
global pass instead of deciding them locally and incrementally.

(Visualized as an actual wired diagram in `weeminer_presentation/`,
slide `fig1-placement`.)

## 3. Generation algorithm (Plan E / WeeMiner, the best method)

Implemented in `generate_with_rollout()`, `generate_seqassemble_strategies.py`.

1. **Condition completion**: `ConditionCompleter.complete(partial_props,
   np_rng)` (a fitted Gaussian mixture over the training property
   distribution) fills in whichever of the 12 properties weren't
   explicitly requested.
2. **Standardize**: `cond_vec = (raw_props - prop_mean) / prop_std`.
3. **Autoregressive loop**, up to `MAX_FRAGMENTS=40` iterations. At each
   step:
   a. Encode the committed sequence so far -> `hidden`; `action_head` gives
      a distribution over next-fragment-or-STOP.
   b. If no target property is set (fully unconditional call): sample once,
      plainly, and move on — the machinery below only pays for itself when
      there's something to steer toward.
   c. Otherwise, take the **top `top_m` candidates** from that distribution.
   d. For each candidate, run **`n_rollouts` independent stochastic
      rollouts** (`_rollout_predict`): hypothetically commit the candidate,
      then continue sampling plainly (no further lookahead) to a full
      completion — no assembly, no RDKit, just autoregressive sampling to
      get a plausible finished *hidden state*.
   e. At each rollout's final hidden state, query **all 4 progress_heads**
      (the checkpoint's own + 3 independently self-generated-fine-tuned
      ensemble members, all sharing the identical frozen trunk — see §4) and
      average their predictions. Average again across the `n_rollouts`
      rollouts for that candidate. Score = `-|predicted_property -
      target_value|`.
   f. Commit whichever candidate scored best. Every simulated rollout is
      discarded — only this one committed fragment persists.
4. Repeat until STOP is the committed choice or the step cap is hit.
5. **Bond decode + assemble** (§1's global Kruskal pass) on the final
   committed sequence.
6. **RDKit sanitize -> SMILES** — the *only* point in the entire generation
   where RDKit computes anything real. Everything upstream (including
   ranking 4 candidates x 3 rollouts x 4 heads = 12 forward-pass
   evaluations *per decision point*) uses only the model's own predictions.

Winning hyperparameters (found by sweeping 5 configs on the same
checkpoint, §7): `top_m=4, n_rollouts=3, rollout_cap=10`. Cost:
~2.7s/molecule vs. baseline's ~0.05s/molecule (~9x Plan B's cost, ~50x
baseline).

## 4. Training algorithm

### Phase A — real data -> features (`train_seqassemble.py`, setup)
`train.csv` (paper's official ZINC250k split, 156,646 molecules, SMILES +
12 real precomputed property columns, byte-verified against the paper's
own GitHub repo) -> `decompose_molecule()` per molecule -> fragments +
adjacency graph (cached to disk, `.frags_slots{N}_lim{M}.pkl`, ~4-5 min at
full scale) -> `build_vocab()` (~3,035 fragment types) -> per-type WEECFP
embeddings (cached) -> per-molecule SuRGE positions (recomputed per epoch
from a fresh random fragment-order permutation) -> `PropertyStandardizer`
(mean/std) + `ConditionCompleter` (GMM) fit on the 12 property columns.

### Phase B — joint trunk + heads training (`train_seqassemble.py`, main loop)
20 epochs, full dataset, batched with padding. Per batch: scheduled
sampling (`teacher_force_prob` decays 1.0 -> 0.0 over `--tf-decay-frac` of
training) mixes ground-truth SuRGE positions with the model's own
self-predicted positions for later tokens' attention/bond-scoring input —
so the model practices on the same kind of noisy self-generated positions
it will see at real generation time, not just ground truth. Losses:
- `action_loss`: cross-entropy, next fragment / STOP.
- `pos_loss`: MSE on `pos_head`'s prediction vs. true SuRGE position.
- `edge_loss`: class-imbalance-weighted BCE, true adjacency vs.
  `bond_vec_head`-derived scores.
- `progress_loss`: MSE, `progress_head`'s prediction vs. **this same
  molecule's own true property vector**, applied at *every* sequence
  position regardless of how much context is available.

`loss = action_loss + pos_loss + edge_weight*edge_loss +
progress_weight*progress_loss`. Output: a base checkpoint with all 4 heads
trained end-to-end on real data (e.g. `seqassemble_full_v4_progress.pt`).

**This phase has a latent bug in `progress_head` that Phase C exists to
fix** — see §4.1.

### 4.1 The progress_head shortcut bug (methodologically important)

In Phase B's training data, `cond_vec` (fed into the trunk) is *always*
set to the true molecule's own properties, and `progress_target` (what
`progress_head` is supervised against) is *also* that same molecule's true
properties. **`cond_vec == progress_target` on literally every training
example.** Since `cond_vec` is injected into the residual stream at every
position (`cond_proj`), the network can achieve zero training loss by
simply learning to echo `cond_vec` straight through — no structural
reasoning required, and critically, *no training example ever penalizes
this shortcut*, because it's never wrong in the training distribution.

**Diagnosis** (`diagnose_progress_head.py`, not a committed script but the
method is worth preserving): generate real sequences, trace
`progress_head`'s prediction at every step, compare against (a) the
trivial baseline "just repeat the target" and (b) the actual achieved
outcome of the finished molecule. On the untouched Phase-B checkpoint,
`progress_head`'s MAE was statistically indistinguishable from the trivial
baseline at *every* fraction-of-sequence-complete bucket, including
75-100% complete — i.e., it added zero information.

**Fix, Phase C** (`finetune_progress_head.py`, `--mode selfgen`): freeze
the trunk and every other head; generate molecules using the model's own
*actual* generation process (plain stochastic sampling, exactly Plan E's
inner-loop mechanism minus the scoring); assemble and measure each one's
*real* achieved property vector with RDKit (once, to build this dataset);
fine-tune only `progress_head` against these real outcomes. Because a
self-generated molecule's actual outcome genuinely differs from the target
it was conditioned on (that gap *is* the model's calibration error), this
supplies the training signal Phase B's data structurally could not.

**A second fix was tried and found much weaker**: `--mode corrupt` —
keep real ground-truth sequences, but corrupt the *input* `cond_vec` fed
to the trunk for a random fraction of examples (swapped with a different
molecule's true properties from the same batch) while keeping
`progress_head`'s target as this molecule's own true properties. This also
breaks the shortcut (target != input on the corrupted fraction) but gave a
much smaller effect than self-generated data — see §7 for numbers.

### Phase C details — self-generated dataset construction
`build_selfgen_dataset()`: for each of N molecules, pick a random target
(optionally: sweep across all 12 properties, not just logP; optionally
bias toward extreme z-scores, "tail oversampling"; optionally set 2-3
simultaneous targets, "multi-target"; optionally generate a fraction via a
cheaper Plan-B-style best-of-4 selection instead of plain sampling,
"on-policy mixing" — see §7.2 for which of these actually helped),
generate via the trunk's own sampling, assemble, measure real properties
once with RDKit, and record *every intermediate hidden state* from that
generation paired with the *one* real final outcome. A held-out
15%-by-molecule validation split (not by individual state/outcome pair, to
avoid leaking correlated states across the split) selects the best epoch
by validation loss rather than blindly taking the last epoch — this
mattered: every Phase-C run overfit within the first 1-4 epochs of a
15-25 epoch budget.

### Phase C — ensembling
Repeat the Phase-C fine-tune 3 more times from the same frozen trunk, each
with a different seed (independent self-generated data draw). Average all
4 resulting `progress_head`s' predictions at inference
(`_predicted_property(..., ensemble_heads=[...])` in
`generate_seqassemble_strategies.py`). This measurably beat every single
head, including the best individual one (§7.3) — ordinary variance
reduction from averaging independently-noisy estimators, not a new
mechanism.

**Final model = WeeMiner** = 1 trunk (Phase A+B, real data) + 4
`progress_head`s (Phase C, self-generated data) averaged at inference. This
is exactly what `best_method.py` loads.

## 5. Fragment-selection strategies (Plans A-E)

All implemented in `generate_seqassemble_strategies.py`, all built *on top
of* the same trunk — they differ only in how the next fragment is chosen
at each step, never in the model architecture itself.

- **Plan A** (`atom_selection="min_remaining"` in `generate_one`/others):
  when accepting a bond during assembly, prefer the attachment atom with
  the *least* remaining valence capacity, instead of the first eligible one
  in iteration order. Counters over-reuse of high-capacity "hub" atoms.
  Modest, real structural-realism improvement; roughly neutral-to-negative
  on calibration when combined with other plans (§7).
- **Plan B** (`generate_best_of_n`): generate N candidates independently
  (full, complete generations), score each by `progress_head`'s prediction
  on its *own* final state vs. the target (never RDKit at decision time —
  see the leakage note below), keep the best. A diagnostic-only oracle
  variant (`generate_best_of_n_oracle`) that scores with RDKit's *actual*
  computed property is kept for reference but must never be reported
  against literature numbers (see §6).
- **Plan C** (`generate_beam_search`): maintain `beam_width` partial
  routes, expand each by its own top-`expand_k` candidates per step, score
  by cumulative route log-probability plus (optionally) a Crippen-additive
  running logP heuristic. Weak calibration gain, but by far the best
  fragmentation rate of anything tried (4.0%, vs. baseline's ~14-16%) —
  route-log-probability-based pruning apparently favors more structurally
  coherent routes as a side effect.
- **Plan D** (`generate_with_progress_guidance`): one-step lookahead —
  hypothetically append each of the top-k candidates, read
  `progress_head`'s prediction on that one extra step's hidden state, reweight
  selection accordingly. Requires a `progress_head`-trained checkpoint.
  Real but modest gain; superseded by Plan E.
- **Plan E** (`generate_with_rollout`) — §3. The best-performing method.

### 5.1 A data-leakage bug and its fix (important, do not reintroduce)

The *first* implementations of Plan B and Plan E scored candidates using
`compute_properties()` — RDKit's *actual* computed value of the candidate
itself — as the selection criterion. This is not classical train/test
leakage, but it *is* circular: the thing being optimized was identical to
the thing later reported as the evaluation metric, making Plan B's early
MAE numbers (~0.28) an artifact of oracle-guided rejection sampling, not a
measure of generation quality. **Caught and fixed**: both plans now select
using only `progress_head`'s *predicted* property (learned, offline,
never touching the candidate's true value at decision time); RDKit is
invoked exactly once, on the single final committed molecule, purely to
report a SMILES. The oracle variant is retained only as an explicit,
clearly-labeled upper-bound diagnostic (`generate_best_of_n_oracle`) —
never to be compared against literature numbers.

## 6. Honest caveats before quoting any number below against the paper

1. **Inference-time-compute comparison, not model-quality comparison.**
   The paper's reported logP MAE/R2 are presumably a single-sample (N=1)
   metric. Plan B/E spend real extra compute (multiple candidates/rollouts)
   at generation time. The fair single-sample comparison is this repo's own
   `baseline (N=1)` row — and *that* remains behind the paper's number
   (§8). Plan E "beating" the paper's MAE is a claim about a
   compute-for-quality tradeoff being available, not about the raw
   generator being better calibrated.
2. **R2 methodology**: the paper computes R2 on **grouped-mean** values
   (`groupby(target).agg(mean)`, then `r2_score`) — verified directly from
   the paper's own `postprocess_calibration_plot.py` source — while MAE is
   raw/ungrouped. All `R2_grouped` numbers below use this exact
   methodology for a fair comparison; `R2_raw` is included separately and
   is *not* comparable to the paper's reported R2.
3. **Uniqueness/novelty at 1.000 is likely a small-sample artifact.**
   Measured over ~200-300 generated molecules; duplicate collisions become
   more likely as sample size grows (birthday-paradox scaling). The
   paper's 0.985/0.999 are presumably measured over a much larger set. Not
   safely interpretable as "this generator produces more unique molecules."
4. **Diversity (~0.84-0.86 vs. paper's 0.892)** does *not* have the
   small-sample escape hatch above and is a real, persistent gap — flat
   across every fragment-selection strategy tried, suggesting the ceiling
   is set by the fixed ~3,035-entry fragment vocabulary / decomposition
   scheme, not by selection strategy.
5. **Fragmentation never reaches the paper's 0%** (§2) — structural, tied
   to the defer-to-global-decode placement strategy.
6. **Size-correlated Wasserstein distances (molWt, TPSA, MR, HBD) run
   2-4x training std** in most strategies. Partly explained by a proven
   identity: `disjoint_size = true_size + n_edges` (disjoint fragment
   assembly is *mathematically* larger than the same fragments merged at
   shared atoms — verified exactly, not a bug), but this does have real
   downstream cost on these distributions.
7. **Run-to-run variance**: several ad hoc diagnostic scripts used during
   development did not fix `torch`'s global RNG seed (only `random`/numpy),
   so repeated runs against the *same* checkpoint can show several
   hundredths of MAE/R2 variation from run to run. Treat single-run
   comparisons of nearby numbers (e.g. 0.704 vs. 0.717) as noise-level;
   treat large gaps (e.g. 1.8 vs. 0.9) as real.

## 7. Results — progress_head quality (the mechanism Plan B/E depend on)

Measured via a direct correlation diagnostic: generate real sequences,
compare `progress_head`'s final-step prediction against (a) the trivial
"repeat the target" baseline and (b) the molecule's actual achieved
outcome.

| checkpoint | fix | data | MAE | R2 | Pearson r |
|---|---|---|---|---|---|
| v4 (Phase B only) | none | — | ~1.9 (== trivial baseline) | ~0 | ~0 |
| v5_corrupt | corrupted cond_vec | 40k real mols | small, real improvement late in sequence | — | — |
| v5_selfgen | self-generated | 800 mols | 1.140 | 0.742 | 0.865 |
| v6_selfgen | + multi-property sweep, val split, late-seq weighting | 4,000 mols | 0.755 | 0.874 | 0.938 |
| v7 (architecture: deeper+dropout+residual) | — | 4,000 mols | 0.943 | 0.825 | 0.919 |
| v8_residual (residual only, same width) | — | 4,000 mols | 0.765 | 0.857 | 0.926 |
| **v9_selfgen** | scaled up | **12,000 mols** | **0.704** | **0.888** | 0.943 |
| v10_combined | + tail oversample, multi-target, on-policy mix | 10,000 mols | 0.717 | 0.891 | — |
| **ensemble (v9 + 3 seeds)** | — | 4x 6,000 mols | **0.650** | **0.898** | **0.948** |

### 7.1 What worked
- **Self-generated data (Phase C) fixes the shortcut**; corrupted-cond_vec
  is a much weaker version of the same fix.
- **Scaling the self-generated dataset (800 -> 4,000 -> 12,000) gave real,
  monotonic improvement.** This was the single largest lever.
- **A held-out validation split with best-epoch selection was necessary**
  — every run overfit within 1-4 epochs; without it, later epochs would
  have shipped a worse checkpoint.
- **Ensembling 3 independently-seeded fine-tunes beat every single head**,
  including the best individual one — ordinary variance reduction, cheap
  (shared frozen trunk).

### 7.2 What didn't work
- **Architecture changes to `progress_head`** (deepening, dropout,
  reparameterizing as a residual on `cond_vec`) all came back neutral or
  worse than the original 2-layer absolute-value head — reverted. The
  bottleneck was data volume, not head capacity (every variant overfit
  fast regardless of depth).
- **Tail oversampling + multi-target joint conditioning + on-policy
  mixing** (v10_combined), layered on top of the already-scaled dataset,
  gave no further improvement over plain scaling (v9) on the logP-specific
  eval — statistically tied. May still matter for properties/conditioning
  combinations not covered by this specific diagnostic; untested.

### 7.3 Plan E hyperparameter sweep (v6_selfgen checkpoint, pre-ensemble)

| config | MAE |
|---|---|
| baseline (N=1) | 1.857 |
| Plan B best-of-8 | 0.899 |
| Plan B best-of-8 ORACLE (diagnostic only) | 0.311 |
| rollout(top_m=2, n_rollouts=2, cap=None) | 1.340 |
| rollout(top_m=3, n_rollouts=3, cap=10) | 0.989 |
| rollout(top_m=3, n_rollouts=3, cap=None) | 0.919 |
| **rollout(top_m=4, n_rollouts=3, cap=10)** | **0.846** — winner |

## 8. Results — full strategy comparison vs. literature

`benchmark_full_comparison.py`, v9 trunk + 4-head ensemble wired into
Plan B/E, n=250 unconditional / n=160 calibration (8 logP targets):

| strategy | valid | uniq | novel | diversity | frag% | logP MAE | R2_raw | R2_grouped |
|---|---|---|---|---|---|---|---|---|
| baseline (N=1) | 1.000 | 1.000 | 1.000 | 0.844 | 13.6% | 1.797 | 0.056 | 0.848 |
| Plan B best-of-8 (ensemble) | 1.000 | 1.000 | 1.000 | 0.846 | 16.8% | 0.935 | 0.700 | 0.987 |
| Plan B best-of-8 + Plan A (ensemble) | 1.000 | 1.000 | 1.000 | 0.857 | 17.6% | 1.570 | 0.407 | 0.677 |
| Plan C beam(3,5) | 1.000 | 1.000 | 1.000 | 0.848 | **4.0%** | 1.766 | 0.136 | 0.865 |
| **Plan E rollout(4,3,cap10) (ensemble)** | 1.000 | 1.000 | 1.000 | 0.842 | 12.8% | **0.886** | 0.788 | **0.981** |
| paper (literature) | 1.000 | 0.985 | 0.999 | 0.892 | 0.000 | 1.000 | n/a | 0.890 |

### 8.1 Compute cost, including an estimate of the literal paper algorithm

No paper wall-clock numbers are published, but this repo actually contains
a faithful, literal reproduction of the *original* MolMiner algorithm
(`model.py`/`train.py`/`generate.py` — unbatched, real 3D conformer
embedding + relaxation *after every fragment placement*, per-step site
selection with immediate bonding — as opposed to `seqassemble_model.py`'s
batched, geometry-free, defer-to-global-decode WeeMiner variant). Rather
than run that full algorithm to completion, it was timed on a 200-molecule
sample and extrapolated linearly to WeeMiner's actual measured scale
(156,646 molecules, 20 epochs) — a real, measured per-example cost, scaled,
not a simulation:

- Precompute (decompose + `embed_and_optimize`, real 3D, once): 37.64ms/mol
  measured -> **~5,896s (98 min)** extrapolated to 156,646 mols.
- Training step (unbatched forward+backward): 11.87ms/mol/epoch measured ->
  **~37,195s (10.3 hours)** extrapolated to 156,646 mols x 20 epochs.
- Generation (`generate_one`, real, on an actual trained checkpoint
  `baseline_10k.pt`, N=20): **0.600s/molecule** measured directly (3D
  relaxation after every attachment — no extrapolation needed here, this
  is real end-to-end per-molecule wall-clock).

Plan B best-of-8 and Plan E rollout(4,3,cap10) — the slide deck labels
these "Fast" and "Rollout" — are the two strategies compared here, both
with the 4-head ensemble wired in (§7.3/§8's `benchmark_full_comparison.py`
run). Both need the identical trained artifact: Phase A+B (1,281.1s)
**plus** the Phase C repair (one targeted self-generated fine-tune,
529.6s) **plus** 3 more independent fine-tunes for the ensemble (6,000
mols each, ~264s each, ~792s) — ~1,320s of Phase C on top of Phase B, for
a shared total of **~2,601s**. They differ only in generation-time cost:

| | Fast (Plan B best-of-8) | Rollout (Plan E) | Literal MolMiner-style (estimated) |
|---|---|---|---|
| Training, full pipeline (shared) | ~2,601s | ~2,601s | ~43,091s (~12 hours) |
| Query, per molecule | **0.316s** | 2.617s | 0.600s |

Both strategies train **~17x faster** than the literal paper algorithm
(same shared cost, since both need the identical trained artifact). On
query: **Fast is faster AND better-calibrated than the paper at the same
time** — 0.316s/mol vs. the paper's 0.600s/mol (~1.9x faster), while also
beating it on MAE (0.935 vs. 1.000) and R2 (0.987 vs. 0.890, §8's main
table). Rollout pushes calibration further (MAE 0.886, R2 0.981) but costs
~4.4x the paper's own per-molecule cost to do it — slower than the paper's
real 3D-relaxation generation, not just slower than this repo's own faster
strategies. **This reframes the earlier "64x slower" number**: that figure
compared Rollout against this repo's plain N=1 baseline specifically;
relative to the actual paper algorithm it's ~4.4x, because the paper's own
per-step cost was never as cheap as this repo's geometry-free baseline (or
Fast) to begin with.

Building the full 4-member ensemble serially costs about the same as one
full WeeMiner retrain (~1,320s vs. 1,281.1s) — the win is that a *single*
repair is cheap to iterate on, not that the whole ensemble is cheaper than
retraining from scratch. Ensemble members are independent and could run in
parallel across GPUs, which these serial numbers don't capture.

Per-property Wasserstein distance (vs. `augmented_zinc250k.txt`), same run
— only the properties with the largest strategy-to-strategy spread shown
(full table in `benchmark_full_comparison.py` output):

| property | baseline | Plan B | Plan B+A | Plan C | Plan E |
|---|---|---|---|---|---|
| TPSA | 73.98 | 73.94 | **21.82** | 67.39 | 76.10 |
| HBD | 3.63 | 3.66 | **0.88** | 3.01 | 3.78 |
| ring_count | 0.237 | 0.187 | **0.198** | 0.047 | 0.317 |
| molWt | 174.9 | 170.2 | 171.6 | **160.8** | 184.4 |

**Reading this table**: Plan E wins on calibration by a wide margin (best
MAE and R2 of everything tried, ahead of the paper's own numbers with
caveat #1 from §6 firmly attached). Plan C wins on structural fidelity
(fragmentation, molWt, ring_count). Plan B+A wins on several other
structural distributions (TPSA, HBD) at a large calibration cost. No
single strategy dominates every axis — pick based on which axis matters
for the use case; **`best_method.py` picks Plan E because calibration was
the axis this whole investigation was optimizing for.**

## 9. Checkpoint lineage (for future reference)

```
v3  -> paper-scale-ish baseline (no progress_head)
v4  -> v3 + progress_head added, jointly trained on real data (Phase B). SHORTCUT BUG.
v5_corrupt  -> v4 + progress_head fixed via corrupted-cond_vec (weak fix)
v5_selfgen  -> v4 + progress_head fixed via self-generated data, 800 mols
v6_selfgen  -> v5_selfgen recipe scaled to 4,000 mols + multi-property + val split + late-seq weight
v7          -> v6_selfgen + deeper/dropout/residual head (REVERTED, worse)
v8_residual -> v6_selfgen + residual-only head (REVERTED, no better)
v9_selfgen  -> v6_selfgen recipe scaled to 12,000 mols (BEST SINGLE HEAD)
v10_combined-> v9_selfgen + tail-oversample + multi-target + on-policy (no further gain)
ens_seed{1,2,3} -> v9_selfgen trunk, 3 more independent self-generated fine-tunes, 6,000 mols each
```

**Production checkpoints** (what `best_method.py` loads):
`seqassemble_full_v9_selfgen.pt` (trunk + native head) +
`seqassemble_full_ens_seed{1,2,3}.pt` (3 extra heads, averaged).

## 10. Where to look for what

| Need | File |
|---|---|
| Generate a molecule with the best method | `best_method.py` |
| Understand/modify the model architecture | `seqassemble_model.py` |
| Retrain the trunk from scratch on real data | `train_seqassemble.py` |
| Repair/rebuild `progress_head` | `finetune_progress_head.py` |
| Any fragment-selection strategy (A-E) | `generate_seqassemble_strategies.py` |
| Baseline (N=1) generation, checkpoint loading | `generate_seqassemble.py` |
| Full literature-metrics benchmark | `benchmark_full_comparison.py` |
| Fragment decomposition / assembly | `fragments.py` |
| WEECFP embeddings, SuRGE positions | `weecfp.py` |
| Property computation, conditioning/completer | `conditioning.py` |
| Slide-deck version of this document | `weeminer_presentation/` |
