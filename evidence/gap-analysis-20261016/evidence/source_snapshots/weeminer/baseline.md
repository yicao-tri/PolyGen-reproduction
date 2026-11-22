# Measured CPU baseline — 2026-10-05

This is a reduced starting run, **not a reproduction of the historical full-data accuracy**. The original checkpoint files were absent from the release. All three demo models produced 10/10 valid molecules; all 640 recorded WeeMiner outputs passed RDKit sanitization.

## Protocol

- Python 3.12.3; dependency versions are pinned in `../requirements.txt`.
- Demo dataset: 139 molecules; 60 epochs each for baseline and WEECFP-SuRGE, 150 for SuRGE-parallel.
- WeeMiner: 2,000 ZINC training rows, 20 epochs, 399 fragment types, 2,385,313 parameters.
- Four progress heads: 800 native self-generation attempts plus three sets of 400 attempts; up to 15 epochs with validation selection.
- Per strategy: 64 unconditional attempts, plus 8 attempts per logP target (−2, 0, 1, 2, 3, 4, 5, 6). Python, NumPy, and PyTorch seed: 0.
- Novelty and property-distribution reference sets: first 20,000 CSV rows.

| Strategy | Valid | Diversity | Fragmented before repair | logP MAE | Grouped R² |
|---|---:|---:|---:|---:|---:|
| baseline (N=1) | 100.0% | 0.850 | 14.1% | 2.065 | 0.855 |
| Plan B best-of-8 | 100.0% | 0.845 | 6.2% | 2.204 | 0.840 |
| Plan B best-of-8 + Plan A | 100.0% | 0.854 | 6.2% | 2.180 | 0.702 |
| Plan C beam(3,5) | 100.0% | 0.798 | 0.0% | 2.701 | 0.572 |
| Plan E rollout(4,3,cap=10) | 100.0% | 0.850 | 14.1% | 2.594 | 0.118 |

The smaller run did not recover the historical improvements from best-of-8 or rollout guidance. Plain N=1 had lower logP MAE here. Training size, vocabulary, progress-head budgets, software environment, and evaluation counts differ from the historical experiment.

Validity is measured after largest-component repair. Novelty against part of the training data is not held-out generalization. The generated SAS proxy is not comparable to true Ertl SAS in the reference CSV. A small float32 covariance asymmetry produced GMM warnings; inspection found finite matrices and positive symmetrized eigenvalues, and the original sampling code was retained.

Local raw records and weights remain under `results/baseline/` and are excluded from Git. This document contains aggregate measurements only. The [technical writeup](../WEEMINER.md) contains the historical figures and their caveats. See [the README](../README.md) for rerun commands.
