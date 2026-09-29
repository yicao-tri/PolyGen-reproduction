# Upper-tail tables and captions

## Table 1. Frozen benchmark definition

| Item | Frozen value |
|---|---|
| Source | `inputs/release-data/htpmd-trainset.csv` |
| Source SHA-256 | `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69` |
| Training rule | `log10(conductivity) <= Q80`, inclusive |
| Training rows | 4,819 |
| Actual training maximum | −4.08450 log10(S cm−1) |
| Locked Q80–Q95 rows | 903 |
| Arms | continuous; binary; unconditional + reranking |
| Seeds | 17, 42, 202, 303, 907 |
| Training budget | 1,000 optimizer steps |
| Sampling | temperature 1.0; top-k 40; 100 reported candidates per target cell |
| MD | not run |

## Table 2. Aggregate prediction-phase metrics

The machine-readable version is `upper_tail_aggregate_metrics.csv`. Entries are
means across the five matched seeds and are descriptive; unsupported cells are
retained as missing values in the underlying cell-level table.

| Arm | Validity | Strict-hit rate | Target MAE | RF prediction mean | RF upper-tail hit rate |
|---|---:|---:|---:|---:|---:|
| Continuous | 0.5745 | 0.5510 | 0.3095 | −4.3131 | 0.0000 |
| Binary* | 0.2300 | 0.2150 | 0.2845 | −4.3470 | 0.0000 |
| Unconditional + reranking* | 0.0015 | 0.0015 | 0.2576 | −4.3421 | 0.0000 |

*Aggregate values are affected by unsupported cells and should not be read as
complete-arm performance. See `unsupported_cells.csv`.

## Table 3. Frozen surrogate audit on locked tail

| Metric | Value |
|---|---:|
| Locked rows | 903 |
| RF MAE | 0.2618 log10(S cm−1) |
| RF RMSE | 0.2686 log10(S cm−1) |
| Mean observed − RF residual | +0.2618 log10(S cm−1) |
| Residual SD | 0.0603 log10(S cm−1) |

## Figure captions

See `FIGURE_CAPTIONS.md` for the final captions for Figures 1–3.
