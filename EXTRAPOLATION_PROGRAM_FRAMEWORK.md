# PolyGen interpolation-to-extrapolation program

## Scope

This program tests whether continuous conductivity conditioning improves
controllable exploration from in-support interpolation to property-tail and
chemical-structure out-of-distribution settings. The four regions share a
frozen data representation, matched seeds, generation budgets, decoding
settings, candidate filters, and machine-readable reporting schema.

The central claim boundary is deliberately staged:

1. **Interpolation** asks whether requested targets can be controlled inside
   the observed support.
2. **Upper-tail** asks whether control remains usable near a declared Q80
   training boundary.
3. **Extrapolation** asks whether generation can produce candidates beyond a
   locked training maximum; surrogate scores are screening evidence only.
4. **Structural-OOD** asks whether the same control persists when scaffold or
   polymer-family analogues are excluded from training.

An MD-confirmed improvement beyond the locked training maximum is the decisive
endpoint for a true extrapolation claim. RF/GNN predictions, uncertainty, and
support are not independent physical validation.

## Workstreams and acceptance gates

| Workstream | Execution plan | Acceptance gate | Status |
|---|---|---|---|
| **Interpolation** | On the frozen split, evaluate Q50, Q65, and Q80. Compare continuous, binary high/low, and unconditional+rerranking with matched seeds, budgets, decoding, and filters. Record target error, strict-hit, monotonicity, validity, novelty, uniqueness, support, uncertainty, diversity, failure, and acquisition provenance. | Reproducible split/target manifest; matched three-arm budget; candidate-level prediction and filtering provenance; unsupported cells and negative controls explicit; surrogate evidence separated from MD evidence. | **Complete** — `results/interpolation/` |
| **Upper-tail** | Train through Q80 and evaluate boundary-to-Q95 targets. Freeze the actual training boundary and compare all three arms. Record RF prediction, uncertainty, support, novelty, residual, target adherence, strict-hit, monotonicity, validity, uniqueness, diversity, and failure. | No Q80–Q95 leakage; matched seeds/budgets; every target cell reported, including empty cells; RF high scores are not treated as MD evidence. | **Complete** — `results/upper-tail/` |
| **Extrapolation** | Lock all rows with `log10(conductivity) > Q80` away from generator training, RF/GNN fitting, tuning, thresholds, and candidate selection. Query Q90, Q100, `train_max + 0.25`, and `train_max + 0.50`; compare the three arms and retain actual training maximum, prediction, uncertainty, support, novelty, residual, validity, failure, and force-field coverage. | Prove locked-holdout isolation; report surrogate crossings without claiming MD success; use MD-confirmed improvement as the decisive endpoint. | **Next step / not run** — benchmark script and prediction evidence are still missing. |
| **Structural-OOD** | Use scaffold/family-grouped splits with no close analogues crossing train/test. Reuse the common target grid and compare all three arms. Record target control, validity, novelty, uniqueness, diversity, uncertainty, failure, chemical distance, nearest-neighbour distance, support, and scaffold-held-out performance. | Demonstrate scaffold/family isolation; distinguish structural OOD from property-tail extrapolation; report unsupported cells and candidate pools explicitly. | **Blocked** — `results/structural-ood/summary.json` records `blocked_for_matched_prediction`. |

## Current evidence boundary

Interpolation is complete and supports a narrower verifier-defined claim:
continuous conditioning improves average internal target adherence and valid
yield relative to the binary control under the frozen representation. The
response is not perfectly calibrated to the requested target, and candidate-
wise monotonicity is not guaranteed.

Upper-tail is complete as a prediction-only benchmark. At Q95, continuous RF
predictions remain below the actual Q80 training boundary, while the frozen
binary threshold degenerates after Q80 truncation. The locked-tail RF audit
also shows systematic underprediction, so the same RF cannot certify
extrapolation.

Structural-OOD cannot currently support a matched continuous-versus-binary
comparison because the released data lack scaffold/family annotations and no
structure-disjoint continuous/binary checkpoints are available. MD has not
been run for any of these workstreams.

## PR topology

The repository currently uses PR #7 as the umbrella evidence PR for the
completed interpolation, upper-tail, and structural-OOD audit package. The
recommended next stack is:

```text
codex-migration-review
        └── PR #7: completed interpolation + upper-tail + structural-OOD evidence
                └── next child PR: true extrapolation benchmark and prediction evidence
```

The true extrapolation child should be based on the head of PR #7 and should
add only its own frozen manifest, benchmark implementation, candidate table,
figures, report, and verification tests. A duplicate interpolation PR is not
created because the interpolation package is already part of PR #7; duplicating
those files would make review and merge order ambiguous.

