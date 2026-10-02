---
title: Multi-property Upper-tail Q80–Q95 — evidence milestone
date: 2026-10-01
status: evidence-complete-md-pending
tags:
  - PolyGen
  - multi-property-conditioning
  - upper-tail
  - surrogate-calibration
  - evidence
---

# Multi-property Upper-tail Q80–Q95

## Research question

当训练集限制在六个属性各自 Q80 以下时，多属性 conditioning 能否在 Q80–Q95 的近边界区域保持联合控制，并降低 RF surrogate 的高预测/低支持假阳性？本 milestone 只承载已冻结的 prediction-phase 证据；MD 未运行，因此不把 RF 结果写成物理验证。

## Frozen design and audit boundary

| Item | Frozen evidence |
|---|---|
| Source | released HTP-MD table, source hash `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69` |
| Split | six-property joint Q80 intersection: 2,494 / 6,024 rows (41.4%); locked Q80–Q95 rows excluded from fitting, filtering and selection |
| Transforms | conductivity, Li/TFSI/poly diffusivity: `log10`; transference number, molality: raw |
| Audit flags | transference number retains negative values for audit; molality has near-degenerate support; no silent clipping |
| Arms | multi-continuous, scalar-continuous, binary conductivity, unconditional + reranking |
| Matching | five seeds (17, 42, 202, 303, 907), 1,000 steps, 100 candidates per arm × seed × target cell, common decoder/filter/schema |
| Candidate provenance | 8,000 candidate rows with arm, seed, target, rank, structure, RF prediction, uncertainty, support and failure fields |
| Pairing | seed/target/row identity/leakage audit: `pass` |

## Acceptance status

| Layer | Required metric | Status and location |
|---|---|---|
| Joint control | joint RMSE, property MAE, strict-hit, feasibility/support, monotonicity | reported in Tables 1–3 and Figures 4–5 |
| Quality/credibility | validity, novelty, uniqueness, diversity, RF mean/uncertainty, support, failure | Tables 1 and 5; Figure 4C and Figure 5A |
| Extrapolation | frontier crossing, locked-tail calibration, residual stratification | Tables 2 and 4; Figure 4D; MD endpoints unavailable by contract |
| Coverage | unsupported cells, invalid structures, low support, high uncertainty, arm failure | `unsupported_cells.csv`, Table 5, acceptance checklist |
| Evidence separation | surrogate versus MD | locked-tail rows are post-run source audit only; `md_status=not_run` for candidates |
| Paired claims | identity and leakage checks | `pairing_acceptance_audit.json` = pass |

## Main findings

The multi-property arm had mean normalized joint RMSE **1.97** versus **2.15** for scalar conductivity conditioning, a descriptive reduction of **0.18 normalized units** under the matched benchmark. Mean validity was **0.560** versus **0.519**. These gains did not produce a joint strict hit or six-property frontier crossing: both rates were zero in every arm × target cell.

The multi-property arm had mean nearest-train support **0.572** and normalized joint RF uncertainty **0.659**. The predeclared credibility gate (support ≥ 0.35, uncertainty < 0.35, joint normalized error < 0.5) selected **zero candidates for MD**. Thus the result is surrogate adherence under a support bottleneck, not validated upper-tail extrapolation.

The locked-tail RF audit contains 3,135 source rows and remains separate from generated candidates. Conductivity residual `logσ_MD − logσ_RF` is **+0.263**, **+0.307** and **+0.372** log units in Q80–Q85, Q85–Q90 and Q90–Q95, respectively. This increasing positive bias is a calibration warning, not MD evidence for any generated structure.

## Figures and tables

![[assets/figures/Figure_4_nature_upper_tail_summary.png]]

*Figure 4. Joint control, property-wise target adherence, candidate credibility space and locked-tail calibration. Editable vector versions and caption are in `assets/figures/`.*

![[assets/figures/Figure_5_nature_failure_monotonicity.png]]

*Figure 5. Explicit failure/filter coverage and descriptive candidate-wise monotonicity.*

Machine-readable tables: [[assets/tables/Table_1_joint_acceptance_summary.csv|Table 1]], [[assets/tables/Table_2_property_target_adherence.csv|Table 2]], [[assets/tables/Table_3_candidate_wise_monotonicity.csv|Table 3]], [[assets/tables/Table_4_locked_tail_calibration.csv|Table 4]], [[assets/tables/Table_5_failure_support_audit.csv|Table 5]], [[assets/tables/Table_6_multi_vs_scalar_effects.csv|Table 6]].

## Claim map and limitations

- **Observed:** matched-arm RF metrics, candidate validity/failure/support/uncertainty, locked-tail calibration, and pairing audit.
- **Inferred cautiously:** multi-property conditioning reduced descriptive joint surrogate error relative to scalar conditioning in this frozen support-limited benchmark.
- **Unavailable:** MD-confirmed frontier crossing, `residual = logσ_MD − logσ_RF` for generated candidates, and residual models versus target distance/support/uncertainty/structural distance.
- **Critical limitation:** all Q80–Q95 joint cells are unsupported by the six-property training intersection. Zero strict hits therefore cannot be interpreted as proof of generator impossibility.

## Next decisive experiment

Run a blinded, predeclared stratified MD panel spanning target distance, support, uncertainty and structural distance; retain build failures in the denominator; freeze candidate selection before MD; then report property-wise and joint frontier crossing plus the MD–RF residual analysis. Until that is complete, the supported conclusion is calibration-aware constraint adherence, not physical upper-tail discovery.

## Evidence index

- Frozen manifests and audit JSON: `evidence/data/`
- Publication tables: `assets/tables/`
- Reproduction and rendering scripts: `evidence/scripts/`
- Manuscript handoff: [[OVERLEAF_HANDOFF.md]]
- Provenance ledger: [[PROVENANCE.csv]]
