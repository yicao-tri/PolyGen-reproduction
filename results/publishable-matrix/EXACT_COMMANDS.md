# Exact commands

Run from the repository root with the included `.venv`.

```bash
for arm in binary continuous linear multibin shuffled unconditional; do
  .venv/bin/python scripts/run_publishable_matrix.py \
    --output results/publishable-matrix --arm "$arm" --seed 101 \
    --steps 10000 --samples 500 --temperature 1.0
done

.venv/bin/python scripts/analyze_publishable_matrix.py \
  --run results/publishable-matrix --seed 101

# Optional house style: point this at a Plot Atlas checkout's src directory.
PYTHONPATH="${PLOT_ATLAS_SRC:-/path/to/plot_library/src}" \
  .venv/bin/python scripts/plot_publishable_matrix.py \
  --run results/publishable-matrix

.venv/bin/python scripts/build_md_handoff.py --run results/publishable-matrix

# Render all 40 selected repeat units, the two 20-candidate grids, and the
# seven-structure overlap grid. Set PLOT_ATLAS_SRC to use the house style;
# otherwise the script uses its deterministic local fallback.
PLOT_ATLAS_SRC="${PLOT_ATLAS_SRC:-}" \
  .venv/bin/python scripts/render_candidate_structures.py \
  --candidates results/publishable-matrix/tables/md_candidates.csv \
  --output results/publishable-matrix/candidate_structures
```

Deferred robustness run (TODO, not part of current claims): repeat the six-arm
loop with `--seed 202` and `--seed 303`, then compute paired seed-level effect
intervals. Do not treat the candidate bootstrap intervals in Figure 2 as
between-seed uncertainty.
