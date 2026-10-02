# Multi-property interpolation benchmark

## Status

This is a frozen, prediction-only six-property interpolation benchmark. MD was not run. Historical `results/interpolation`, `results/upper-tail`, and `results/extrapolation` were not modified.

## Design

The six condition fields are `log10(conductivity)`, `log10(li_diffusivity)`, `log10(tfsi_diffusivity)`, `log10(poly_diffusivity)`, raw `transference_number`, and raw `molality`. All transforms and the scaler are fit on the 4,819-row train split only. The target grid contains 18 one-property probes (Q50/Q65/Q80 with the other coordinates at train medians) and three coherent joint empirical-copula targets selected from train rows by mean marginal percentile. Independent quantile Cartesian products are forbidden and were not used.

The four arms are six-dimensional continuous conditioning, scalar conductivity conditioning, binary conductivity conditioning, and constant-condition generation followed by frozen six-property RF reranking. Every arm uses five matched seeds and 100 reported candidates per target cell.

Checkpoint provenance is recorded per seed in `frozen_manifest.json`. Historical scalar/binary checkpoints are reused where present; the remaining scalar seeds are matched retraining under the frozen 1,000-step seed/token/decoder/RF settings. The multi-continuous and unconditional-reranking arms are newly trained. This provenance policy does not change candidate counts or the primary paired unit.

## Evidence boundary

RF predictions, structural support, novelty, target error, and uncertainty are screening evidence only. They do not establish MD or experimental conductivity. Any unsupported target or empty arm-cell is retained in `unsupported_cells.csv`. The binary arm is a negative control because it receives only a fixed high/low conductivity label.

## Files

- `frozen_manifest.json`, `design_contract.json`, `source_audit.json`, and `transform_scaler_manifest.json` freeze inputs and transforms.
- `target_cells.csv` and `target_support_audit.json` document the non-Cartesian target construction.
- `candidate_predictions.csv`, `metrics_by_cell.csv`, and `paired_contrasts.csv` contain machine-readable outputs.
- `pairing_leakage_audit.json` records source, split, pairing, budget, binary-policy, MD, and historical-preservation checks.
- `publication/` contains SVG/PNG/PDF-ready figures and captions.

## Reproduction

```bash
.venv/bin/python scripts/multi_property_interpolation.py
.venv/bin/python scripts/render_multi_property_interpolation.py
.venv/bin/python scripts/verify_multi_property_interpolation.py
```
