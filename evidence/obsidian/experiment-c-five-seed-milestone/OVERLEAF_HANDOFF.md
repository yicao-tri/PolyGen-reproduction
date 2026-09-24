# Overleaf handoff — Experiment C five-seed milestone

## Manuscript-level takeaway

Continuous conductivity conditioning improves offline target adherence over the original binary high/low PolyGen interface under a fixed HTP-MD split and common frozen verifier. Across five paired seeds, strict target-hit rate increases from 0.1587 to 0.1780 and target MAE decreases from 0.6940 to 0.6331. The improvement is accompanied by lower validity and novelty, and it has not yet been confirmed by molecular dynamics.

## Proposed placement

- Main Results: Figure 1 (`assets/figures/c1_five_seed_publication.svg`) and Table 1 effect estimates.
- Main or Extended Data: Figure 2 (`assets/figures/c1_five_seed_primary_effect.svg`) to show all seed-level effects.
- Supplement: five-seed candidate sheets and target-specific table.
- Methods: paired-seed design, frozen verifier, support/uncertainty gate, and exact candidate-selection rule.
- Outlook/next validation: preregistered MD top-20 comparison.

## Candidate prose

**Observed / manuscript-ready.** Under identical data, model-size, optimization and sampling budgets, continuous conductivity conditioning increased mean strict target-hit rate from 0.1587 to 0.1780 across five paired training/generation seeds (mean paired difference 0.0193; 95% t interval 0.0064–0.0322). All five seed-level differences were positive. Because the exact two-sided sign-test p value was 0.0625, this five-seed analysis is best interpreted as consistent exploratory evidence rather than a definitive distribution-free test.

**Observed / manuscript-ready.** Continuous conditioning reduced target MAE by 0.0609 log10 S cm⁻¹ but decreased validity by 0.0673 and novelty by 0.0720. Thus the gain is a target-adherence versus chemical-yield tradeoff.

**Unavailable / do not write as achieved.** The current experiment does not show that continuous candidates have higher MD or experimental conductivity, nor that salt, temperature, loading, DP and architecture are jointly controllable.

## Final captions

**Figure 1 | Continuous conditioning improves target adherence with a validity tradeoff.** (A) Mean frozen-verifier prediction at each requested log-conductivity target; error bars show SEM across five training/generation seeds and the dashed line denotes ideal calibration. (B) Strict target-hit rates for paired binary and continuous runs; each connected pair is one seed. (C) Mean paired differences with 95% t intervals. Positive hit-rate and negative target-MAE differences favor continuous conditioning, whereas negative validity and novelty differences reveal reduced chemical yield.

**Figure 2 | Seed-level primary effect.** Continuous-minus-binary strict target-hit-rate differences for each paired seed and their mean with 95% t interval. All five effects are positive; the exact two-sided sign-test p value is 0.0625.

**Figure S1 | Five-seed continuous candidate gallery.** Two eligible unique candidates per seed and requested target were selected by the frozen score `target error + 0.25 × uncertainty`. Green borders identify structures also present in the eligible binary pool. Structures illustrate generator output and are not MD- or experimentally validated discoveries.

**Figure S2 | Five-seed binary candidate gallery.** The same deterministic stratified selection applied to the binary high/low baseline.

## Exact numeric sources

- Primary and secondary paired effects: `assets/tables/c1_five_seed_effect_summary.csv`.
- Individual paired seeds: `assets/tables/c1_five_seed_paired_effects.csv`.
- Target-specific means: `assets/tables/c1_five_seed_target_summary.csv`.
- Chemistry-pool comparison: `assets/tables/structure_comparison.csv`.
- Candidate identities and selection metadata: `assets/tables/candidate_structure_index.csv`.
- MD queue: `assets/tables/md_batch_manifest.csv`.

## Caveats that must survive editing

1. Seed—not generated candidate—is the independent unit.
2. n=5 is small; report both the paired t result and exact sign-test result.
3. The −5 and −3 targets are support-limited; most hits occur near −4.
4. Verifier-defined improvement is not physical validation.
5. Candidate structure overlap is exact canonical-p-SMILES overlap, not scaffold or functional-group equivalence.
6. C2 demonstrates pipeline execution but its held-out-formulation verifier error is too large for a conductivity claim.
7. The repository was dirty at package time; use the snapshotted scripts and manifest.

## Citations still needed

- Yang et al., “De novo design of polymer electrolytes using GPT-based and diffusion-based generative models,” npj Computational Materials 10, 296 (2024), DOI 10.1038/s41524-024-01470-9.
- Lei et al., “A materials discovery framework based on conditional generative models applied to the design of polymer electrolytes,” Digital Discovery (2025), DOI 10.1039/D4DD00293H.
- HTP-MD source paper and the original GNN verifier paper cited by Yang et al.
- Cluster Nernst–Einstein and PCFF+ protocol references used by the MD workflow.

## Producing evidence

- Data/postprocessing snapshot: `evidence/scripts/postprocess_experiment_c_publication.py`.
- Plot snapshot: `evidence/scripts/plot_experiment_c.py`.
- Candidate rendering snapshot: `evidence/scripts/render_experiment_c1_candidates.py`.
- MD manifest snapshot: `evidence/scripts/build_md_validation_plan.py`.
- Machine verification snapshot: `evidence/scripts/verify_experiment_c.py`.
