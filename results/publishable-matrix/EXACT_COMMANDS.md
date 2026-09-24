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

PYTHONPATH=/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library/src \
  .venv/bin/python scripts/plot_publishable_matrix.py \
  --run results/publishable-matrix

.venv/bin/python scripts/build_md_handoff.py --run results/publishable-matrix
```

Deferred robustness run (TODO, not part of current claims): repeat the six-arm
loop with `--seed 202` and `--seed 303`, then compute paired seed-level effect
intervals. Do not treat the candidate bootstrap intervals in Figure 2 as
between-seed uncertainty.
