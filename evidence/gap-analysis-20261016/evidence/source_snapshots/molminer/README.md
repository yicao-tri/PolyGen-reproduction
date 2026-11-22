# MolMiner × PolyGen C1 comparison

这是 Raul 的 `molminer-polymer` 与 PolyGen reproduction 的首轮 matched-budget 对照证据包。

## Status

- 目标：`log10 conductivity ∈ {-5, -4, -3}`
- 预算：5 seeds × 100 samples/target = 1500 MolMiner samples
- MolMiner：公开 `best_polyru_s42.pth`，`log_conductivity` only，stochastic sampling，`max_fragments=80`
- PolyGen：已有 C1 publication five-seed binary / continuous metrics
- 共享 verifier：PolyGen C1 frozen random forest
- 重要边界：MolMiner checkpoint 来自 merged corpus，包含 HTP-MD；这轮是 descriptive matched-budget baseline，不是严格 held-out leaderboard。

## Reproduce

从 `PolyGen-reproduction` 根目录运行：

```bash
PYTHONPATH=/Users/yicao/Documents/ARC/resourses/molminer-polymer \
results/molminer-comparison/.venv/bin/python \
scripts/run_molminer_c1_comparison.py \
  --output results/molminer-comparison/runs/molminer-c1-seed5 \
  --max-fragments 80
```

生成比较表和图：

```bash
PYTHONPATH=/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library/src:$(pwd) \
results/molminer-comparison/.venv/bin/python \
scripts/analyze_molminer_polygen_comparison.py
```

方法拆解、representation 对齐、failure 解释和严格公平实验计划见 `METHOD_DECOMPOSITION.md`；冻结协议见 `DESIGN_CONTRACT.md`。
