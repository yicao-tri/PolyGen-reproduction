# Continuous versus binary PolyGen generation grid

## Figure 1. Generation-grid response and candidate audit

![Figure 1](figures/polygen_generation_grid_at_a_glance.png)

**Figure 1 | Continuous-versus-binary PolyGen generation benchmark.** (a) Mean strict-hit rate across five paired seeds for the executable `gpt-nano` grid. Each point is one `temperature × training-step × arm` configuration; the axes and colors preserve the paired binary/continuous comparison. (b) Descriptive generation-quality summaries averaged over the nine executable configurations; error bars are configuration-level standard errors, not candidate-level inferential errors. (c) Representative candidates from the frozen baseline ranking, shown only as a structural audit of generated repeat units. (d) Training-set conductivity distribution and verifier-predicted conductivity distributions for generated candidates. The distributions in (d) are verifier outputs and should not be interpreted as experimental or molecular-dynamics conductivity.

## Results

The executable grid comprised nine `gpt-nano` configurations spanning three training budgets (1,000, 2,000, and 3,000 steps) and three sampling temperatures (0.8, 1.0, and 1.2). Each configuration used five paired seeds and identical target allocation in the binary and continuous arms: 100 generated samples at each of the three log-conductivity targets per seed and arm. Thus, every arm/configuration contributed 1,500 raw samples, and the complete grid contained 27,000 generated records.

Across the nine-configuration grid, continuous conditioning increased the mean strict-hit rate from 0.2197 in the binary arm to 0.2311, a descriptive paired difference of +0.0114. Continuous conditioning also reduced mean target MAE from 0.6860 to 0.6148 log10(S cm−1), corresponding to −0.0712 log units. These improvements were accompanied by lower mean validity (0.6110 versus 0.6893), novelty (0.5667 versus 0.6404), and uniqueness (0.5934 versus 0.6870). The pattern is therefore consistent with improved verifier-defined target adherence accompanied by a generation-quality trade-off, rather than a uniformly superior generator.

Panel a shows that the effect is not represented by a single temperature or training-budget setting. The grid was designed to expose sensitivity to sampling temperature and optimization budget while preserving the seed pairing and target allocation. Interpretation should remain configuration-specific; the figure is descriptive and is not a license to pool individual generated candidates as independent replicates.

Panel c provides a qualitative structural audit of the primary ranking. The displayed structures are selected from the valid, novel, in-support, uncertainty-gated pool using the prespecified score `predicted_log_sigma − 1.96 × uncertainty`. They are candidate examples, not experimentally validated discoveries. Panel d shows that the generated property distributions occupy the verifier-defined training-property regime, but the plotted property is a model prediction. It does not establish measured conductivity, transport, salt-temperature control, or physical transfer number.

## Interpretation boundary and missing panels

The current generation output does not contain auditable candidate-level synthesizability, diversity, or buildability fields. Consequently, these quantities are not imputed in Figure 1, and the corresponding Pareto analyses remain explicitly unavailable. Transfer number is likewise not available from Layer 1/2 generation data and requires a separate formulation/MD protocol. No PFP or MD result is included here.

The appropriate claim is therefore: **under a fixed HTP-MD split and frozen verifier, continuous conditioning improves verifier-defined target adherence across the executable generation grid, with lower validity, novelty, and uniqueness than the binary arm.** Advancement to Stage 3 requires explicit user sign-off and a separate physical-validation contract.

## Reproducibility

- Raw identity table: `analysis/grid_raw_with_identity.csv`
- Arm/seed/target metrics: `analysis/grid_arm_seed_target_metrics.csv`
- Paired contrasts: `analysis/grid_paired_contrasts.csv`
- Frozen top-50 audit: `analysis/grid_top50_primary.csv`
- Pareto availability audit: `analysis/grid_pareto_availability.csv`
- Main figure: `figures/polygen_generation_grid_at_a_glance.svg`
- Plot source: `scripts/render_generation_grid_nature.py`
- Analysis source: `scripts/analyze_generation_grid.py`
