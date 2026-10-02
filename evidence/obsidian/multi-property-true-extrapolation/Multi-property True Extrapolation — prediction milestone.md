---
title: Multi-property True Extrapolation — prediction milestone
date: 2026-10-01
status: prediction-complete-md-unavailable
tags: [polygen, polymer-electrolyte, multi-property, extrapolation, evidence]
---

# Research question

When all six high-value properties are hidden from training, does a jointly normalized condition increase credible frontier exploration relative to scalar conductivity conditioning, binary conductivity, or unconditional generation with reranking?

The primary estimand is the paired seed-by-target difference in joint frontier-crossing rate, `multi_continuous − scalar_continuous`. The decisive endpoint specified by the benchmark is MD-confirmed crossing; this milestone contains the complete prediction-only phase and records MD evidence as unavailable.

Cross-region status is tracked in `evidence/data/ACCEPTANCE_DASHBOARD.md` and `ACCEPTANCE_DASHBOARD.json`; interpolation and upper-tail prediction gates pass, while the common MD gate remains open.

# Frozen design and audit

The source is `inputs/release-data/htpmd-trainset.csv` with SHA-256 `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69`. The six transforms are conductivity, Li diffusivity, TFSI diffusivity and polymer diffusivity as `log10`; transference number and molality as raw values. The joint training intersection contains 2494 of 6024 rows; 3530 rows are locked audit-only.

Four arms (`multi_continuous`, `scalar_continuous`, `binary_conductivity`, `unconditional_reranking`) use five matched seeds, 1000 optimizer steps, 100 candidates per cell, matched decoding, and the same six-property RF verifier. The target cells are Q90, Q100, `train_max + 0.25`, and `train_max + 0.50`. All 20 runs produced artifacts; 8000 candidates populate 80 cells with n=100 each. Pairing audit status is `pass`.

## Figure 1 — response, error, and validity

![[assets/figures/fig01_response.png]]

> [!note] Figure 1 evidence
> **Shows:** Mean conductivity response, normalized joint target RMSE, and validity across four locked extrapolation queries.
> **Data:** `assets/tables/metrics_by_cell.csv`.
> **Script:** `evidence/scripts/multi_property_upper-tail.py` and `evidence/scripts/finalize_multi_property_extrapolation.py`.
> **Unit/statistics:** Descriptive means over five matched seeds; each cell contains 100 candidates. No inferential p-value is claimed.
> **Supports:** The prediction-phase response and quality profile under the frozen RF verifier.
> **Does not support:** MD-confirmed or experimental frontier crossing.

## Figure 2 — strict hits and frontier crossing

![[assets/figures/fig02_quality.png]]

> [!note] Figure 2 evidence
> **Shows:** Joint strict-hit and all-six-property predicted frontier-crossing fractions.
> **Data:** `assets/tables/metrics_by_cell.csv`, `assets/tables/unsupported_cells.csv`.
> **Supports:** The result that no arm produced a strict joint hit or predicted all-property crossing in this run.
> **Does not support:** A claim that no candidate could cross under MD; MD was not run.

## Figure 3 — locked holdout verifier audit

![[assets/figures/fig03_locked_audit.png]]

> [!note] Figure 3 evidence
> **Shows:** Observed versus RF-predicted transformed properties for locked source rows, used only after fitting.
> **Data:** `evidence/data/locked_tail_verifier_audit.csv` in the canonical result root; the compact package snapshot is represented by `assets/tables/metrics_by_cell.csv` and the source manifest.
> **Supports:** A surrogate-only locked-row calibration diagnostic.
> **Does not support:** RF–MD residual calibration, because no MD values exist.

The machine-readable locked-row calibration is `evidence/data/locked_surrogate_calibration.csv`. Across the 3135 locked audit rows, the RF surrogate is systematically conservative (prediction minus observed transformed value): conductivity bias −0.171, Li diffusivity −0.182, TFSI diffusivity −0.140, polymer diffusivity −0.166, transference number −0.075, and molality −0.033. These are surrogate calibration diagnostics only, not MD residuals.

# Results

No strict joint hits and no all-six-property predicted frontier crossings were observed in any arm or target cell. Mean candidate validity across cells was 0.5145 for multi-property, 0.4540 for scalar conductivity, 0.0010 for binary, and 0.5235 for unconditional reranking. The binary arm is therefore an explicit negative control, not a precision claim.

The defensible interpretation is that this configuration did not demonstrate surrogate-supported six-property extrapolation. It also does not establish that multi-property conditioning is physically conservative or physically superior: the required MD endpoint is missing. The result is consistent with either a genuinely difficult extrapolation problem, an overly narrow joint target/support geometry, or surrogate/generator mismatch; the current design cannot distinguish these mechanisms.

## Prospective MD gate

`assets/tables/md_validation_plan.csv` contains a symmetric 48-slot Tier-1 proposal with three strata per arm-target cell: high prediction/low uncertainty, high prediction/high uncertainty, and high novelty/low support. It is explicitly `planned_not_run`; no RF top-1-only selection was used. The proposal retains unsupported slots, including cells with no valid novel candidate. Launch remains blocked by the frozen PCFF+ parameter-coverage and LAMMPS-provider requirements in `TOP1_MD_VALIDATION_DESIGN_ZH.md`. No MD result is inferred from the proposal.

The machine-readable gate decision is `evidence/data/md_gate_audit.json` (`NO_GO`). It must be rechecked before any MD launch; PFP/ASE output is not an acceptable substitute for the specified PCFF+ LAMMPS protocol.

| Acceptance item | Evidence status | Source |
|---|---|---|
| source hash, split, targets, scaler frozen | observed | `evidence/data/frozen_manifest.json`, `source_audit.json`, `scaler_manifest.json` |
| matched seeds/budgets/schema | observed | `evidence/data/pairing_acceptance_audit.json`, `assets/tables/metrics_by_cell.csv` |
| locked-row leakage exclusion | observed | `evidence/data/verifier_manifest.json`, pairing audit |
| unsupported cells and failures | observed | `assets/tables/unsupported_cells.csv`, `failure_reasons.csv` |
| property-wise/joint surrogate crossing | observed: all zero | `assets/tables/metrics_by_cell.csv` |
| surrogate calibration on locked source rows | observed, surrogate-only | `assets/figures/fig03_locked_audit.png` |
| MD-confirmed crossing and best MD conductivity | unavailable: MD not run | benchmark contract |
| RF–MD residual calibration | unavailable: no MD measurements | benchmark contract |

# Manuscript boundary

Manuscript-ready: “Under a six-property Q80-intersection split, the prediction-only benchmark produced no strict joint hits or all-property frontier crossings across four extrapolation query levels and four matched arms.”

Not manuscript-ready without additional evidence: “multi-property conditioning enables credible physical extrapolation,” “candidate conductivity exceeds the training frontier,” or any claim about best confirmed MD conductivity. The next required milestone is a symmetric, preregistered MD screen of stratified candidates from `candidate_selection_for_md.csv`; that file is empty under the current strict surrogate gates, which itself must be addressed before MD.
