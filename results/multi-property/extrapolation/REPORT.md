# Multi-property True Extrapolation

Status: definitive prediction phase complete; MD not run.

The frozen six-property Q80 intersection retained **2494 / 6024** rows. All four arms used five paired seeds, 1,000 optimizer steps, 100 candidates per target cell, and the same frozen six-property RF verifier. Targets were Q90, Q100, train_max+0.25 and train_max+0.50 in transformed property coordinates.

All 20 run artifacts were completed and post-processed from disk after a non-scientific finalization bug was repaired. See `metrics_by_cell.csv`, `paired_contrasts.csv`, `candidate_predictions.csv`, `pairing_acceptance_audit.json`, and `publication/`. Locked rows were not used for fitting, tuning, filtering or selection. MD and experimental claims remain unsupported.

The frozen verifier produced no strict joint hits or all-six-property frontier crossings in any arm/cell. Mean candidate validity across cells was 0.5145 for multi-property, 0.4540 for scalar conductivity, 0.0010 for binary, and 0.5235 for unconditional reranking. These are prediction-only negative/limitation results: the benchmark does not establish validated physical extrapolation.
