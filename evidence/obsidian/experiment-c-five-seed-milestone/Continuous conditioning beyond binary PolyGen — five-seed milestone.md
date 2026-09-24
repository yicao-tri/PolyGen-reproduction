---
title: Continuous conditioning beyond binary PolyGen — five-seed milestone
date: 2026-09-24
status: evidence-complete-md-pending
tags:
  - PolyGen
  - polymer-electrolyte
  - conditional-generation
  - molecular-dynamics
  - experiment-c
---

# Decision summary

The current offline experiment answers a narrow but important question: under one fixed HTP-MD split, equal generator budgets, and a common frozen verifier, does continuous conductivity conditioning improve target adherence over the original binary high/low PolyGen interface?

Across five paired training/generation seeds, the answer is **yes for verifier-defined target adherence, with a substantial validity/novelty tradeoff**. Strict target-hit rate increased from 0.1587 to 0.1780 (paired absolute difference +0.0193; 95% t interval 0.0064–0.0322). All five seed-level effects were positive. The paired t-test gave p=0.0141, while the distribution-free exact sign test gave p=0.0625; with only five independent seeds, this is exploratory rather than definitive confirmatory evidence.

This result does not yet establish higher physical conductivity. The next decisive experiment is a prospective, common-protocol MD comparison of the frozen continuous top-20 against binary and legacy PolyGen controls.

# What was held fixed

| Component | Frozen design |
|---|---|
| Generator comparison | Binary high/low prefix versus continuous conductivity prefix |
| Seeds | 17, 42, 202, 303, 907; paired across arms |
| Training data | 4,819 identical generator/verifier-training rows |
| Verifier test | 1,205 untouched, byte-identical rows |
| Training budget | 1,000 optimizer steps per arm/seed |
| Sampling | 100 candidates per arm × seed × target |
| Targets | log conductivity −5, −4, −3 |
| Total samples | 3,000 |
| Inferential unit | training/generation seed, not candidate or token |
| Primary outcome | valid, novel, in-support, low-uncertainty strict target-hit rate |

The data source SHA-256 is `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69`. The train/test row fingerprints and verifier metrics are in [[evidence/data/c1_five_seed_summary.json]]. The frozen verifier achieved RMSE 0.1569, MAE 0.1243 and R² 0.4979 on 1,205 held-out rows.

> [!note] Reproducibility state
> Source repository: `/Users/yicao/Documents/ARC/PolyGen-reproduction`; branch `experiment/complete-system-e2e`; base commit `7f2d831592a69d1ddc3bdd7396361c703d3beeb5`. The repository was dirty when this package was created, so the package snapshots—not the base commit alone—are the authoritative producing scripts. Artifact verification passed and six repository unit tests passed.

# Primary result and tradeoff

![[assets/figures/c1_five_seed_publication.png]]

> [!note] Figure 1 — Continuous conditioning improves target adherence with a validity tradeoff
> **Shows:** Requested target versus frozen-verifier response, paired seed hit rates, and paired effects for adherence and chemical yield.
> **Data:** `evidence/data/c1_five_seed_arm_target_metrics.csv`; summary tables in `assets/tables/`.
> **Script:** `evidence/scripts/plot_experiment_c.py` after `evidence/scripts/postprocess_experiment_c_publication.py`.
> **Command:** `.venv/bin/python scripts/postprocess_experiment_c_publication.py`, then Plot Atlas Python `scripts/plot_experiment_c.py`.
> **Unit/statistics:** Five paired training/generation seeds; panel A uses SEM across seeds; panel C uses 95% t intervals.
> **Supports:** Better verifier-defined target adherence and lower target MAE under the fixed benchmark.
> **Does not support:** Experimental conductivity, reliable extreme-target control, or complete-system discovery.

| Outcome | Binary | Continuous | Paired difference | 95% t interval |
|---|---:|---:|---:|---:|
| Strict target-hit rate | 0.1587 | 0.1780 | +0.0193 | [0.0064, 0.0322] |
| Target MAE | 0.6940 | 0.6331 | −0.0609 | [−0.0728, −0.0490] |
| Validity | 0.5220 | 0.4547 | −0.0673 | [−0.1303, −0.0044] |
| Novelty | 0.5033 | 0.4313 | −0.0720 | [−0.1431, −0.0009] |
| OOD rate | 0.0040 | 0.0093 | +0.0053 | [−0.0016, 0.0123] |

> **Source:** [[assets/tables/c1_five_seed_effect_summary.csv]]. Seed is the independent unit. The exact two-sided sign-test p value for the primary outcome is 0.0625. These inferential summaries are exploratory because n=5.

![[assets/figures/c1_five_seed_primary_effect.png]]

> [!note] Figure 2 — Seed-level primary effect
> **Shows:** Continuous-minus-binary strict target-hit difference for every paired seed and the mean 95% t interval.
> **Data:** `assets/tables/c1_five_seed_paired_effects.csv`.
> **Script/command:** Same as Figure 1.
> **Unit/statistics:** n=5 paired seeds; all five differences are positive.
> **Supports:** Directional reproducibility across the five runs.
> **Does not support:** A distribution-free p<0.05 claim or physical validation.

The continuous model was monotonic across the three requested targets in 5/5 seeds, with mean target–prediction correlation 0.991. Binary conditioning was monotonic in 4/5 seeds, with mean correlation 0.873. However, almost all strict hits occurred near the central −4 target. The −5 and −3 requests sit at or outside reliable support, so target ordering is stronger evidence than extreme-target attainment.

# Five-seed candidate chemistry

The candidate visualization is now generated from every complete paired seed batch discovered by the pipeline. Selection is fixed at two eligible, unique candidates per arm × seed × target, ranked by `target_error + 0.25 × uncertainty`. An incomplete single-arm seed is a hard error.

![[assets/figures/continuous_30_candidates.png]]

> [!note] Figure 3 — Continuous candidates across five seeds
> **Shows:** Thirty structures: 5 seeds × 3 targets × 2 candidates. Green borders mark structures appearing in both eligible arm pools.
> **Data:** `assets/tables/candidate_structure_index.csv` and the complete raw sample tables in the canonical repository.
> **Script:** `evidence/scripts/render_experiment_c1_candidates.py`.
> **Command:** `.venv/bin/python scripts/render_experiment_c1_candidates.py`.
> **Unit/statistics:** Deterministic stratified gallery; not an inferential sample.
> **Supports:** Output validity, endpoint representation, and chemical examples across all seed/target strata.
> **Does not support:** Synthetic accessibility, force-field coverage, or conductivity.

![[assets/figures/binary_30_candidates.png]]

> [!note] Figure 4 — Binary baseline candidates across five seeds
> **Shows/Data/Script:** Identical selection and rendering contract to Figure 3, applied to the binary arm.
> **Supports:** A visually auditable baseline under equal stratification.

| Arm | Eligible unique | Arm-exclusive | Shared | Median heavy atoms | Median TPSA |
|---|---:|---:|---:|---:|---:|
| Binary | 746 | 690 | 56 | 13 | 53.38 Å² |
| Continuous | 622 | 566 | 56 | 13 | 52.60 Å² |

The eligible-pool Jaccard overlap is 0.043. Thus the arms mostly generate different exact structures, but their coarse size and polarity summaries remain similar. The evidence is consistent with different samples from a related chemical region; it does not establish discovery of a new superior chemistry class.

> **Source:** [[assets/tables/structure_comparison.csv]]. Eligibility requires validity, novelty, support ≥0.35 and uncertainty <0.35. The structure pool aggregates generated samples and is descriptive, not an independent-replicate analysis.

# Claim map

| Status | Claim | Boundary |
|---|---|---|
| observed | Continuous conditioning improves mean verifier-defined strict hit rate by +0.0193 across five paired seeds. | Fixed HTP-MD split, frozen verifier, −5/−4/−3 target grid. |
| observed | Target MAE decreases by 0.0609 log units. | Same offline verifier; not MD or experiment. |
| observed | Validity and novelty decrease by 0.0673 and 0.0720. | Current decoder/training budget only. |
| observed | Continuous target response is monotonic in 5/5 seeds. | Three requested targets, with support limitations at both extremes. |
| inferred | Continuous conditioning learns a smoother target representation than binary labels. | Consistent with ordering and MAE; mechanism is not directly identified. |
| inferred | A constrained decoder or constructability auxiliary loss may recover yield. | Proposed intervention; not tested. |
| unavailable | New candidates have higher MD conductivity than original PolyGen candidates. | Prospective MD has not run. |
| unavailable | The method controls salt, temperature, loading, DP or architecture jointly. | C1 lacks crossed system-level data; C2 verifier is too weak for a physical claim. |
| unavailable | Continuous candidates are experimentally synthesizable. | No synthesis or experimental validation. |

# Next decisive experiment: prospective MD

The pipeline has frozen three 20-structure cohorts in [[assets/tables/md_batch_manifest.csv]]:

1. continuous top-20, selected at target −3 by `predicted_log_sigma − 1.96 × uncertainty` after common gates;
2. binary top-20 selected by the identical rule;
3. 20 legacy PolyGen controls selected by SHA-256 ordering of p-SMILES, independent of their published conductivity outcomes.

The primary contrast must be continuous versus binary under one randomized, blinded build/simulation batch. Continuous versus legacy PolyGen is secondary because the historical data may carry protocol/batch differences. Add PEO only after recovering its exact published build specification. Run five independently initialized replicas per structure, retain build/force-field failures in the denominator, and analyze structure-level means—not trajectory frames.

Full protocol: [[evidence/data/MD_VALIDATION_PROTOCOL]]. Frozen candidate tables are [[assets/tables/continuous_top20.csv]], [[assets/tables/binary_top20.csv]] and [[assets/tables/legacy_polygen_hash20.csv]]. All entries remain `PLANNED_NOT_RUN`.

# Alignment with published PolyGen

The published study compared minGPT, 1D diffusion and diffusion-LM; evaluated novelty, uniqueness, validity, synthesizability, similarity and diversity; tested binary conductivity and functional-group conditioning; generated 100,000 high-label candidates; screened top candidates with a GNN; and performed full-atom MD on 46 candidates. It also evaluated PI1M pretraining/fine-tuning. The related discovery-framework paper adds iterative MD feedback.

Our work currently covers the minGPT binary baseline, continuous conditioning, validity/novelty, independent verifier filtering, five paired seeds, and a formulation prototype. It has not yet reproduced the diffusion architectures, the full six-metric suite, the 100k regime, functional-group joint conditioning, PI1M pretraining, transference-number validation, or an MD feedback iteration.

The ordered checklist is maintained in [[evidence/data/POLYGEN_ALIGNMENT_TODO]]. Primary references: [Yang et al., npj Computational Materials (2024)](https://www.nature.com/articles/s41524-024-01470-9) and [Lei et al., Digital Discovery (2025)](https://doi.org/10.1039/D4DD00293H).

# Manuscript boundary

Manuscript-ready wording:

> Under a fixed HTP-MD split and common frozen verifier, continuous conductivity conditioning reproducibly improved verifier-defined target adherence over binary high/low PolyGen across five paired training/generation seeds, while reducing valid and novel yield.

Wording that must wait for MD:

> Continuous conditioning discovers polymers with higher conductivity than original PolyGen.

See [[OVERLEAF_HANDOFF]] for proposed placement, captions, exact numeric sources and caveats.
