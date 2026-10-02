---
title: Multi-property benchmark — acceptance index
date: 2026-10-01
status: prediction-phase-complete-md-gate-open
tags:
  - PolyGen
  - multi-property
  - acceptance-dashboard
  - Obsidian-index
---

# Cross-region status

The prediction-phase evidence is complete across interpolation, upper-tail and true-extrapolation regions. The common MD gate remains open: no accepted symmetric PCFF+ MD run exists, so MD-confirmed frontier crossing and `logσ_MD − logσ_RF` residual calibration remain unavailable.

| Region | Status | Evidence entrypoint | Main boundary |
|---|---|---|---|
| Interpolation | Prediction complete; verifier PASS | [[PolyGen-reproduction/evidence/obsidian/multi-property-interpolation-milestone/Multi-property interpolation — Nature evidence package]] | Six-dimensional conditioning does not show lower joint RF error than scalar conditioning; no MD |
| Upper-tail | Prediction complete; locked surrogate calibration available | `PolyGen-reproduction/results/multi-property/upper-tail/RESULTS_AND_DISCUSSION_NATURE.md` | Surrogate improvement is support-limited; no MD |
| True extrapolation | Prediction complete; MD unavailable | [[PolyGen-reproduction/evidence/obsidian/multi-property-true-extrapolation/Multi-property True Extrapolation — prediction milestone]] | No strict joint hits or all-property predicted crossings; no MD |
| Common MD gate | Open / unavailable | `PolyGen-reproduction/results/multi-property/ACCEPTANCE_DASHBOARD.json` | PCFF+ coverage/provider acceptance and MD outcomes missing |

## Shared acceptance invariants

- Source hash, split, target and scaler manifests are frozen.
- Six-property transforms are explicit: four `log10` fields and two raw fields.
- Continuous, binary and unconditional+rerranking arms share matched seeds, budgets, decoding, filtering and schemas within each regional contract.
- Candidate-level provenance, unsupported cells, invalid structures, support, uncertainty and failures are retained.
- RF surrogate evidence is separated from MD evidence.
- Paired claims use seed/target/row identity and leakage audits.
- No region is summarized by RF top-1 only.

## Machine-readable dashboard

Canonical status: `results/multi-property/ACCEPTANCE_DASHBOARD.json`.

The interpolation-specific package contains its own frozen snapshots, four publication figures, derived tables, claim map, provenance ledger, package manifest and reproduction commands under `multi-property-interpolation-milestone/`.
