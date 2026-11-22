# PolyGen gap-analysis design contract

## Question and estimand

Primary question: under the frozen Q80 property-tail split, does continuous conductivity conditioning produce more surrogate-supported frontier crossings than the fixed-threshold binary negative control or unconditional generation plus frozen-RF reranking?

Primary estimand: paired seed-level difference in RF-gated frontier-crossing rate, continuous minus binary, with unconditional+rerranking as a prespecified control. The unit is the arm × seed × target cell; seed identities are shared across arms.

The physical follow-up estimand is separate: structure-level mean `log10(sigma)` under one common PCFF+ protocol, five independent replicas per structure, with structure—not trajectory frame—as the independent unit. It is not estimable in the current package because the extrapolation queue has not been parameterized or simulated.

## Frozen inputs

- Source: `/Users/yicao/Documents/ARC/PolyGen-reproduction/inputs/release-data/htpmd-trainset.csv`
- Source SHA-256: `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69`
- Source rows: 6,024; exact unique SMILES: 6,024.
- Train rule: `log10(conductivity) <= full-source Q80`, inclusive.
- Train rows: 4,819; locked Q80–Q100 rows: 1,205.
- Actual inclusive training maximum: `-4.084499110675755` log10(S/cm).
- Queries: Q90 `-3.987531610782325`; Q100 `-3.295367776501`; train-max+0.25 `-3.834499110675755`; train-max+0.50 `-3.584499110675755`.
- Arms: continuous target conditioning; fixed-threshold binary; unconditional+rerranking.
- Seeds: 17, 42, 202, 303, 907.
- Matched generation: gpt-nano, 1,000 optimizer steps, temperature 1.0, top-k 40, 100 candidates/cell; unconditional raw pool 400/cell assignment.
- RF gates: support ≥0.35; tree-SD uncertainty <0.35; strict target error <0.5.

## Interpretation boundary

The released extrapolation run is prediction-only. RF crossing is a screening endpoint, not physical conductivity. The locked-tail audit supports the statement that the blind RF systematically under-predicts the locked region; it does not identify whether the generator or verifier is responsible for the zero RF crossing. The PFP top-1 result is a one-structure, one-replica `NON_CONVERGED_SMOKE_ONLY` workflow anchor and is not evidence for the extrapolation queue.

## Expected inventory

- Pitch: P1–P3 plus backup freeze card.
- Manuscript: F1–F8 and T1–T6.
- Evidence: frozen source/contract/manifest, C1/extrapolation tables, locked-tail audit, candidate selection, MD manifest, provenance ledger, package manifest, and Overleaf handoff.

## Data-status convention

- `observed`: directly read from canonical CSV/JSON or recomputed from those files.
- `observed_status_only`: an operational state is observed, but no measurement exists yet (for example `PLANNED_NOT_RUN`).
- `mixed_observed_and_planned`: observed RF/PFP pilot anchors are shown together with visibly dashed synthetic/planned components.
- `synthetic_placeholder`: deterministic visual-only values that must be replaced by real data before publication.
- `unavailable`: required asset or experiment was not present and was not inferred.
