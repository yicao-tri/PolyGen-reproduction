---
title: Strategy-to-package crosswalk — Pitch × PolyGen gap analysis
date: 2026-10-16
status: current package audit
---

# Purpose

This crosswalk maps every named deliverable in the blueprint strategy to a
file, evidence state, and remaining gate. The authoritative source snapshot is
`evidence/source_snapshots/strategy.md`; the full A1–A13 ledger is in
`TODO_AND_ACCEPTANCE.md`.

The final machine-readable package audit is `evidence/data/final_readiness_audit.json`;
its human-readable interpretation is `FINAL_READINESS_AUDIT.md`.
The manuscript-ready evidence-bounded Results/Methods prose and replacement
map are in `PUBLICATION_PROSE.md`.
The machine-readable requirement ledger is
`evidence/data/strategy_requirements_traceability.csv`; the reconciled grid
snapshot is `evidence/source_snapshots/grid/analysis_reconciled.log`.

## Pitch deliverables

| Strategy item | Package artifact | Evidence state |
|---|---|---|
| P1 decision-value tradeoff | `assets/figures/P1_decision_value_tradeoff.{png,pdf,svg}`; `OVERLEAF_HANDOFF.md` | observed C1 surrogate data; no physical claim |
| P2 verifier blindness | `assets/figures/P2_verifier_blind_locked_tail.{png,pdf,svg}`; T3 | observed locked-tail RF audit; full-source RF kept post-hoc |
| P3 verifier-repair next action | `assets/figures/P3_verifier_repair_experiment.{png,pdf,svg}` | RF/smoke anchors observed; PCFF+/MD ladder remains planned |
| P-backup freeze card | `assets/tables/T6_freeze_card.csv` | drafted; owner approval still required |

The slide-ready copy and speaker notes are in `PITCH_INSERT_PAGES.md`; the
canonical 17-page pitch was not edited because its submission root and final
slide placement remain owner-controlled.

## Manuscript figures

| Figure | Package artifact | Status / replacement rule |
|---|---|---|
| F1 framework + loop | `assets/figures/F1_framework_and_closed_loop.*` | strategy diagram; dashed physical/update stages are planned |
| F2 interpolation | `assets/figures/F2_interpolation_controllability.*` | real five-seed surrogate data |
| F3 upper-tail | `assets/figures/F3_upper_tail_response.*` | real data; unsupported binary cells explicit |
| F4 extrapolation | `assets/figures/F4_extrapolation_response.*` | real prediction-stage data; zero is not physical failure |
| F5 verifier audit | `assets/figures/F5_verifier_audit.*` | real locked-tail and full-source diagnostic |
| F6 MD residual ladder | `assets/figures/F6_md_residual_ladder.*` | mixed observed/planned; replace planned MD values after PCFF+ run |
| F7 representation/data ablation | `assets/figures/F7_representation_data_ablation_SYNTHETIC.*` | synthetic planning values; replace with strict same-support fragment/PI1M/MD results |
| F8 decision change | `assets/figures/F8_decision_change_SYNTHETIC.*` | synthetic planning values; replace with RF-vs-calibrated MD-confirmed ranking |

The existing nine-configuration grid is retained as the conditional source
asset `F9_generation_grid_existing.*`; a repaired, ASCII-safe real-data version
is now `F9_generation_grid_repaired.*`. The auxiliary real MolMiner
comparison remains descriptive and is represented in T1/T5 rather than being
promoted to a strict same-support result. The generator asset boundary is
documented in `GENERATOR_ASSET_AUDIT.md`; WeeMiner code smoke passed, but its
available task is ZINC/logP and no C1 conductivity checkpoint is available.

## Tables and data contracts

| Required table | Package file | State |
|---|---|---|
| T1 baseline | `assets/tables/T1_baseline.csv` | real PolyGen + descriptive MolMiner; Wee code exists but no task-aligned C1 result |
| T2 four-stage acceptance | `assets/tables/T2_four_stage_acceptance.csv` | real prediction stages; structural-OOD blocked |
| T3 verifier audit | `assets/tables/T3_locked_tail_verifier_bins.csv` | real blind locked-tail audit |
| T4 MD funnel | `assets/tables/T4_md_funnel.csv` | planned/not-run; PCFF+ gate fails |
| T5 cross-generator | `assets/tables/T5_cross_generator.csv` | real descriptive comparison; strict MolMiner five-seed/five-epoch smoke is archived but final frozen-budget retraining and task-aligned Wee remain missing; full MolMiner target rows in T11 |
| T11 MolMiner descriptive target rows | `assets/tables/T11_molminer_descriptive_c1.csv` | real auxiliary table; released-checkpoint support mismatch remains; strict smoke is tracked separately in `STRICT_MOLMINER_SMOKE.md` |
| T12 strict MolMiner smoke | `assets/tables/T12_molminer_strict_c1_smoke.csv` | five-seed/five-epoch same-support engineering smoke; not final matched-budget performance |
| T13 MolMiner extension | `assets/tables/T13_molminer_extended20_vs_smoke.csv` | real five-seed 20-epoch versus five-epoch comparison under the same 150-request frozen-RF audit; engineering evidence, not final leaderboard |
| T14 MolMiner extension | `assets/tables/T14_molminer_extended50_vs_smoke.csv` | real five-seed 50-epoch versus five-epoch comparison under the same 150-request frozen-RF audit; engineering evidence, not final leaderboard |
| T6 freeze card | `assets/tables/T6_freeze_card.csv` | pre-MD proposal; owner sign-off missing |
| T7 Hisa review | `assets/tables/T7_hisa_review_action_ledger.csv` | isolated regression ledger |
| T8 PI1M overlap | `assets/tables/T8_pi1m_overlap_audit.csv` | observed exact overlap provenance |
| T9 split leakage | `assets/tables/T9_structure_split_leakage_audit.csv` | observed canonical split audit |
| T10 PI1M near overlap | `assets/tables/T10_pi1m_near_overlap_exploratory.csv` | exploratory systematic sample; not absence proof |

## Acceptance gates G1–G8

| Gate | Current evidence | State |
|---|---|---|
| G1 format | F1–F8 and P1–P3 have PNG/PDF/SVG; F9 preserves conditional source formats | PASS for package assets; journal dimensions still owner-dependent |
| G2 layout | `evidence/data/figure_visual_qa.csv` and visual inspection | PASS for primary package art; F9 conditional glyph repair remains |
| G3 palette | shared arm colors and status colors in figures/captions | PASS package style; final journal template not selected |
| G4 statistics | captions include seed/candidate counts and interval language | PASS for current observed figures |
| G5 completeness | unsupported/planned/blocked states are drawn and captioned | PASS |
| G6 traceability | `PROVENANCE.csv`; package validator | PASS after rebuild; generator asset snapshots included |
| G7 claim honesty | `CLAIM_MAP.csv`; surrogate-only and synthetic labels | PASS for package claims |
| G8 independent readability | `FIGURE_CAPTIONS.md` and standalone evidence report | PASS package-level; journal copyedit remains |

The strict-generator extensions are visualized in
`assets/figures/S1_molminer_extended20_vs_smoke.*` and
`assets/figures/S2_molminer_extended50_vs_smoke.*`. Their bars are five-seed
means with SEM and their open points preserve seed-level variation. They do not
change the physical-validation downgrade or the final cross-generator closure
boundary.

## Stop/degrade rule

Because PCFF+ coverage and ARC PCFF+ integration remain FAIL, the package follows
the strategy's downgrade rule: the current publishable claim is a
surrogate-only extrapolation benchmark plus verifier audit. P3/F6 retain
planned MD elements, and F7/F8 remain synthetic placeholders. No PFP smoke
number is promoted to converged physical evidence.
