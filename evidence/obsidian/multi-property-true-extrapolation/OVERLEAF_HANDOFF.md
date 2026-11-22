# Overleaf handoff — multi-property true extrapolation

## Takeaway

The complete prediction-only benchmark used a frozen six-property Q80 intersection, four matched arms, five seeds, four extrapolation targets, and 8000 candidates. No strict joint hit or all-six-property predicted frontier crossing occurred. This is a negative/limitation result, not evidence of MD-confirmed failure or success.

## Suggested placement

Use as an appendix/evidence section accompanying the interpolation and upper-tail benchmarks. Main text should contain only the narrow prediction-only statement; defer full split, failure, support, and unsupported-cell tables to the supplement.

## Preferred figures and captions

- `assets/figures/fig01_response.svg`: response, joint RMSE, and validity across Q90, Q100, train-max offsets.
- `assets/figures/fig02_quality.svg`: strict-hit and predicted joint frontier-crossing heatmaps.
- `assets/figures/fig03_locked_audit.svg`: locked source-row surrogate audit.

Exact numeric sources are `assets/tables/metrics_by_cell.csv`, `paired_contrasts.csv`, and `failure_reasons.csv`. All reported values are descriptive means over matched seed-level cells; no p-value or MD claim is supplied.

## Required caveat

MD-confirmed crossing, best confirmed MD conductivity, and `logσ_MD − logσ_RF` residual calibration are unavailable because MD was not run. Do not call surrogate frontier crossing “true extrapolation.”

