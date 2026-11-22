# Overleaf handoff — Pitch × PolyGen gap analysis

## Manuscript-level takeaway

Continuous conditioning improves in-support target control, but the frozen RF verifier cannot resolve the locked-tail region where the extrapolation decision is concentrated. All blind-RF frontier-crossing rates are zero across the four prespecified extrapolation targets and three arms; this is prediction-only evidence. Physical extrapolation remains unavailable until PCFF+ coverage, five-replica MD, convergence gates, and RF–MD residual calibration are complete.

## Suggested placement

- Main text: F1 framework; F2 interpolation; F3 upper-tail; F4 true extrapolation; F5 verifier audit.
- Supplementary/backup: P1 decision-value tradeoff, P2 verifier audit, T1–T6, full candidate/seed tables.
- Future-work figure: F6/F7/F8 only after synthetic placeholders are replaced; until then label them planned and keep them out of the results claim.

## Candidate prose with evidence strength

**Observed.** Across five matched seeds, continuous conditioning increased C1 strict target-hit rate from 0.1587 to 0.1780 and reduced target MAE from 0.6940 to 0.6331, while validity and novelty decreased from 0.5220 to 0.4547 and from 0.5033 to 0.4313, respectively. These are paired seed-level summaries of in-support generation, not physical conductivity measurements.

**Observed, prediction-only.** At Q90, Q100, train-max+0.25 and train-max+0.50, no candidate in any arm crossed the frozen training boundary according to the blind RF after the validity, novelty, support and uncertainty gates. The fixed binary arm is structurally unsupported after Q80 truncation because its −4.0 label becomes single-class.

**Observed diagnostic.** On 1,205 locked-tail source rows, the blind RF has MAE 0.310 and mean observed-minus-predicted residual +0.310. Its predictions occupy a narrow vertical band below the observed tail; the full-source RF reduces post-hoc MAE to 0.131 only because it has seen locked-tail labels.

**Audit correction.** The original C1 audit reported target–prediction correlation inside each single-target bin, where the target is constant and correlation is undefined. The corrected real-data audit records those bins as undefined and computes the correlation across all three target levels within each arm and seed; the resulting ranges are 0.274–0.507 for binary and 0.717–0.845 for continuous. This repairs the audit metric without changing the physical-validation boundary.

**Data-provenance diagnostics.** The external PI1M overlap audit found 59 exact canonical overlaps among 6,024 HTP rows (46 in the Q80 training subset, 11 in the locked Q80–Q95 subset, and 2 above Q95 or unassigned). An exploratory Morgan screen over a systematic 1-in-10 PI1M sample found 21 candidates at Tanimoto ≥0.85, including 14 non-exact fingerprint-near rows; this is not a full-source absence proof. The PI1M source is external and not committed in this package, and PI1M pretraining remains unavailable. A separate split audit found 312 canonical overlaps for the released-random split and zero for the exact structure-disjoint split. The latter is a leakage audit, not a scaffold/family structural-OOD result.

**Cross-generator asset boundary.** The released MolMiner checkpoint supports a real five-seed matched-budget C1 behavioral baseline, but it was trained on a merged corpus containing HTP-MD and is therefore not a held-out same-support comparison. WeeMiner code and a local four-test smoke path are available, but the available WeeMiner task is ZINC/logP and its full data/checkpoints are not bundled. Neither result supports a strict C1 conductivity leaderboard; the required same-support retraining remains open.

**Strict-generator preflight.** An isolated strict C1 MolMiner preflight now
rebuilds the exact 4,819-row training support, vocabulary, rollouts, and packed
tensors. The legacy un-packed path produced NaN because it divided the all-zero
BOS saturation row by zero; the packed path repaired this engineering issue.
Five small-model training seeds completed a five-epoch smoke and a common
150-request frozen-RF generation audit, yielding 47 valid two-star units and 8
strict hits. These numbers document a reproducible software path only and must
not be used as the final matched-budget or cross-generator result. The full
record is `STRICT_MOLMINER_SMOKE.md` and T12.

**Unavailable.** No extrapolation candidate has a PCFF+ parameterization and no extrapolation candidate has a converged MD measurement. The PFP top-1 pilot is one structure per arm, one non-converged smoke trajectory, and cannot be used as a superiority or extrapolation claim.

## Captions

Use `assets/figures/FIGURE_CAPTIONS.md` verbatim or adapt only after preserving evidence-status language. The preferred vector files are the corresponding `.pdf` or `.svg` files in `assets/figures/`.

## Numeric sources

- C1 effect numbers: `evidence/data/c1_five_seed_effect_summary.csv`.
- Extrapolation cell results: `evidence/data/extrapolation_aggregate_metrics.csv` and `evidence/data/extrapolation_metrics_by_cell.csv`.
- Locked-tail diagnostics: `evidence/data/locked_tail_verifier_audit.csv`, `assets/tables/T3_locked_tail_verifier_bins.csv`.
- Frozen boundary and protocol: `evidence/data/extrapolation_frozen_manifest.json`, `evidence/data/extrapolation_design_contract.json`.
- MD status: `evidence/data/candidate_selection_for_md.csv`, `evidence/data/md_batch_manifest.csv`, `evidence/data/top1_readiness_audit.json`.
- Corrected C1 audit: `evidence/data/c1_recomputed_audit_fixed/summary.json`, `evidence/data/c1_recomputed_audit_fixed/arm_seed_metrics.csv`.
- Hisa review closure: `HISA_REVIEW_ACTIONS.md`, `assets/tables/T7_hisa_review_action_ledger.csv`.
- PI1M and split provenance: `evidence/data/pi1m_overlap/summary.json`, `evidence/data/structure_split_audit/canonical_overlap_audit.json`, `assets/tables/T8_pi1m_overlap_audit.csv`, `assets/tables/T9_structure_split_leakage_audit.csv`.
- Exploratory PI1M near overlap: `evidence/data/pi1m_near_overlap/summary.json`, `evidence/data/pi1m_near_overlap/README.md`, `assets/tables/T10_pi1m_near_overlap_exploratory.csv`.
- Strict MolMiner preflight and smoke: `evidence/data/molminer_strict_c1_smoke_audit.json`, `evidence/experiments/molminer_strict_c1/`, `STRICT_MOLMINER_SMOKE.md`.

## Caveats to preserve

1. Do not call RF-only crossing a physical or experimental hit.
2. Do not infer generator-limited failure from the blind RF ceiling.
3. Do not use the full-source RF to make a leakage-free claim.
4. Keep binary unsupported cells visible.
5. Keep PFP top-1 `NON_CONVERGED_SMOKE_ONLY` beside any use of its numbers.
6. Do not synchronize Overleaf or edit the submission-root manuscript without owner authorization.
