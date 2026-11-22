# Full-source RF audit: revised surrogate design

## Why this layer exists

The original Upper-tail RF was trained only on the Q80 generator-training rows.
That is the correct RF for a leakage-free extrapolation claim, but it is a
biased surrogate in the locked tail: its Q80–Q95 MAE is 0.262 log units and its
mean observed-minus-predicted residual is +0.262.

This directory adds a second, explicitly post-hoc RF trained on all 6,024
source rows, including the 903 Q80–Q95 rows. It is intended as an MD-surrogate
audit and for estimating candidate quality after the blind experiment. It is
not used to redefine the primary extrapolation endpoint.

## Interpretation rules

1. `results/upper-tail/` remains the primary blind benchmark.
2. `fullrf_*` values are post-hoc full-source surrogate values.
3. Full-RF upper-tail hits cannot support a leakage-free claim because the RF
   has seen the locked-tail labels.
4. Any final claim that a polymer unit truly exceeds Q80 still requires MD or
   experimental validation.

## Key audit result

| RF | Training data | Locked-tail MAE | Mean residual |
|---|---|---:|---:|
| Blind RF | Q80 training rows only | 0.262 | +0.262 |
| Full-source RF | all 6,024 source rows | 0.131 | +0.126 |

With the full-source RF, continuous candidates show 1.4%, 2.0%, 1.2%, and
1.6% upper-tail predicted-hit rates at Boundary, Q85, Q90, and Q95,
respectively. These are useful for prioritizing an MD queue, but are not
evidence of extrapolation. Binary remains unsupported at Q90/Q95 because the
generator itself was trained with the degenerate frozen binary label.

## Files

- `fullrf_candidate_predictions.csv`: all original generated candidates,
  rescored by the full-source RF.
- `fullrf_metrics_by_cell.csv`: cell-level full-RF metrics.
- `fullrf_locked_tail_audit.csv`: full-RF calibration on the locked tail.
- `fullrf_summary.json`: source counts, residuals, and explicit leakage warning.

The producing script is `scripts/recompute_full_rf_audit.py`. It does not
modify the original blind RF outputs.
