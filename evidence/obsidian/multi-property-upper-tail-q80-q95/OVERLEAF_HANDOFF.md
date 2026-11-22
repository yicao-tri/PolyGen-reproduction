# Overleaf handoff — multi-property Upper-tail Q80–Q95

## Manuscript placement

- Main text: Figure 4, with the matched-arm joint-control result and locked-tail calibration caveat.
- Extended Data or Supplementary Figure: Figure 5, failure coverage and candidate-wise monotonicity.
- Supplementary Tables: Tables 1–6 as CSV-derived tables.
- Methods: frozen source/split/scaler manifests and paired identity/leakage audit.

## Main result paragraph

Under a six-property joint Q80 truncation, multi-property conditioning reduced mean normalized joint RF target error from 2.15 to 1.97 relative to scalar conductivity conditioning, while increasing mean validity from 0.519 to 0.560 under matched seeds, budgets, candidate counts, decoding and filters. However, joint strict-hit and six-property frontier-crossing rates were zero in every arm × target cell. The result therefore supports improved surrogate adherence within a support-limited benchmark, but not validated upper-tail extrapolation.

## Required caveat

The Q80–Q95 source rows were locked and used only for post-run RF calibration. Generated candidates were not MD-tested (`md_status=not_run`), and no candidate passed the predeclared support/uncertainty/error gate. Accordingly, MD-confirmed frontier crossing and generated-candidate `logσ_MD − logσ_RF` residuals are unavailable.

## Figure captions

Use `assets/figures/FIGURE_CAPTIONS_NATURE.md` verbatim as the caption source. Vector SVG/PDF and machine-readable CSV files are retained beside the PNG previews.
