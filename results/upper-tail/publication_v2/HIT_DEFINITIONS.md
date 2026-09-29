# Upper-tail hit definitions v2

Boundary: `-4.084499` log10(S cm−1).

All target-hit metrics require valid, training-novel, support-eligible and
uncertainty-eligible candidates. They differ only in the allowed absolute RF
target error:

- `target_hit_0.50`: error < 0.50;
- `target_hit_0.25`: error < 0.25;
- `target_hit_0.10`: error < 0.10;
- `frontier_crossing_hit`: RF prediction > the actual Q80 training maximum;
- `validated_frontier_crossing_hit`: MD measurement > the boundary.

The last metric is `NA_MD_not_run` in this prediction-only phase. Full-source
RF values are post-hoc surrogate values and cannot support leakage-free
extrapolation claims.
