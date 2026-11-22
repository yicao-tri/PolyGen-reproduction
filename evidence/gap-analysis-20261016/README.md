# Pitch × PolyGen gap analysis package

This package is the reproducible handoff for the 2026-10-16 gap analysis. It contains the requested TODO ledger, acceptance criteria, real-data figures, clearly marked synthetic/planned placeholders, source snapshots, table outputs, and manuscript-ready prose.

## Executive status

- Prediction-stage evidence: complete for the frozen Q80 split, including P1/P2 and F1–F5.
- Existing generation grid: nine configurations, 27,000 raw rows, five paired seeds per arm/configuration; included as F9 and audited in `evidence/data/grid_asset_audit.csv`.
- Physical validation: blocked. The canonical top-1 audit is `NO_GO` because PCFF+ parameter coverage and ARC PCFF+ integration both fail; the extrapolation MD manifest remains `PLANNED_NOT_RUN`.
- PFP pilot: the independent evidence-chain validator passes 39/41 checks; both failures are missing trajectory files, so the remaining analysis is explicitly smoke-only and non-converged.
- Synthetic placeholders: F7 and F8 only. They are deterministic planning visuals and must be replaced before publication. S1/T13 and S2/T14 are real observed MolMiner engineering-comparison outputs, but not a final matched-budget leaderboard.
- Canonical source and project files were treated as read-only; all new outputs are inside this package.

## Start here

1. [TODO_AND_ACCEPTANCE.md](TODO_AND_ACCEPTANCE.md) — full A1–A13 ledger and stage gates.
2. [Research question — Pitch × PolyGen gap analysis.md](Research%20question%20%E2%80%94%20Pitch%20%C3%97%20PolyGen%20gap%20analysis.md) — evidence report with embedded pitch figures.
3. [DESIGN_CONTRACT.md](DESIGN_CONTRACT.md) — estimand, frozen inputs, and interpretation boundary.
4. [OVERLEAF_HANDOFF.md](OVERLEAF_HANDOFF.md) — manuscript-ready prose, captions, and caveats.
5. [PROVENANCE.csv](PROVENANCE.csv) — artifact-to-source ledger.
6. [CLAIM_MAP.csv](CLAIM_MAP.csv) — observed/inferred/unavailable claim boundaries.
7. [HISA_REVIEW_ACTIONS.md](HISA_REVIEW_ACTIONS.md) — nine-item code/process review ledger and canonical closure boundary.
8. [STRATEGY_CROSSWALK.md](STRATEGY_CROSSWALK.md) — maps every P/F/T/G deliverable to an artifact and remaining gate.
9. [PITCH_INSERT_PAGES.md](PITCH_INSERT_PAGES.md) — ready-to-insert P1–P3 slide copy and speaker notes.
10. [GENERATOR_ASSET_AUDIT.md](GENERATOR_ASSET_AUDIT.md) — MolMiner/WeeMiner asset inventory, smoke result, and strict-comparison blockers.
11. [STRICT_MOLMINER_SMOKE.md](STRICT_MOLMINER_SMOKE.md) — isolated strict C1 preprocessing, NaN root-cause record, packed-loader repair, and five-seed generation smoke.
12. [FINAL_READINESS_AUDIT.md](FINAL_READINESS_AUDIT.md) — one-command package/claim/physical-gate readiness audit.
13. [PUBLICATION_PROSE.md](PUBLICATION_PROSE.md) — evidence-bounded Results, Methods, insertion map, and explicit synthetic-replacement instructions.
14. [GENERATOR_ASSET_AUDIT.md](GENERATOR_ASSET_AUDIT.md) — updated asset audit including the real 20-epoch and 50-epoch five-seed MolMiner extensions.
15. [strategy_requirements_traceability.csv](evidence/data/strategy_requirements_traceability.csv) — machine-readable A1–A13, P/F/T deliverable ledger with real, planned, synthetic, and blocked boundaries.

## Figures and tables

All publication figures have PNG, PDF, and SVG versions in [assets/figures](assets/figures). F1–F8 implement the strategy inventory; F7/F8 are explicitly synthetic placeholders; F9 is the existing real generation-grid audit asset.

The six requested tables plus auxiliary Hisa, PI1M-overlap, split-leakage, exploratory near-overlap, and generator-audit tables are in [assets/tables](assets/tables). Machine-readable source snapshots are in [evidence/data](evidence/data). The corrected real-data C1 audit is in [evidence/data/c1_recomputed_audit_fixed](evidence/data/c1_recomputed_audit_fixed). The canonical asset audit is in [evidence/data/asset_audit.json](evidence/data/asset_audit.json).

The strict MolMiner preflight is isolated under [evidence/experiments/molminer_strict_c1](evidence/experiments/molminer_strict_c1). The five-seed/five-epoch smoke and common 150-sample generation audit are summarized in [T12_molminer_strict_c1_smoke.csv](assets/tables/T12_molminer_strict_c1_smoke.csv). The real five-seed/20-epoch extension is in [T13_molminer_extended20_vs_smoke.csv](assets/tables/T13_molminer_extended20_vs_smoke.csv) and [S1_molminer_extended20_vs_smoke.png](assets/figures/S1_molminer_extended20_vs_smoke.png); the 50-epoch extension is in [T14_molminer_extended50_vs_smoke.csv](assets/tables/T14_molminer_extended50_vs_smoke.csv) and [S2_molminer_extended50_vs_smoke.png](assets/figures/S2_molminer_extended50_vs_smoke.png). These are engineering evidence only; A8 remains open for the final frozen budget, independent checkpoint selection, and task-aligned WeeMiner/equivalent training.

## Rebuild and validation

The package is rebuilt from the canonical repository with:

```text
PYTHONPATH=/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library/src \
/Users/yicao/Documents/ARC/PolyGen-reproduction/.venv/bin/python \
evidence/scripts/build_gap_package.py \
  --canonical-root /Users/yicao/Documents/ARC/PolyGen-reproduction --out .
```

The read-only asset audit is:

```text
/Users/yicao/Documents/ARC/PolyGen-reproduction/.venv/bin/python \
evidence/scripts/audit_canonical_assets.py \
  --canonical-root /Users/yicao/Documents/ARC/PolyGen-reproduction --out .
```

The candidate-specific PCFF+ preflight is reproducible with:

```text
/Users/yicao/Documents/ARC/PolyGen-reproduction/.venv/bin/python \
evidence/scripts/audit_pcff_plus_bundle.py \
  --canonical-root /Users/yicao/Documents/ARC/PolyGen-reproduction \
  --output-dir evidence/data/pcff_plus_bundle_audit
```

Its current result is `NO_GO`: geometry and formula assets are present, but
the candidate-specific LAMMPS data/input, atom typing, charges, bonded and
nonbonded coefficients, coverage report, and run-0 acceptance are absent.

Do not launch remote MD from this package. The next authorized experiment is parameter-coverage repair and owner-approved short MD under [T6_freeze_card.csv](assets/tables/T6_freeze_card.csv). The heartbeat monitor scope is recorded in [monitor/heartbeat_scope.md](monitor/heartbeat_scope.md).
