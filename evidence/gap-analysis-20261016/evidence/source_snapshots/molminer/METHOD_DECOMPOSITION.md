# MolMiner × PolyGen：方法拆解与生成差异

更新时间：2026-10-05  
状态：首轮 matched-budget C1 对照已完成；严格同训练支持的 retraining 尚未开始。

## 1. 这轮比较究竟固定了什么

两套系统都在 C1 任务上生成 polymer repeat units，目标为 `log10 conductivity = -5, -4, -3`，每个目标、每个 seed 生成 100 个样本，使用相同的五个 seed：`17, 42, 202, 303, 907`。PolyGen 延续 reproduction 的 binary / continuous 两个 arm；MolMiner 使用公开的 `best_polyru_s42.pth` checkpoint，只提供 `log_conductivity` 条件，其余九个属性 withheld。

这是一轮“同目标、同样本预算、同 verifier”的行为对照，不是严格的 held-out performance leaderboard：MolMiner 的公开 checkpoint 是在 merged corpus 上训练的，而 merged corpus 包含 HTP-MD；因此它和 PolyGen 的 C1 generator train/test 划分并不对齐。冻结的 comparison contract 见 `DESIGN_CONTRACT.md`。

## 2. MolMiner 的生成链路

MolMiner 不是字符级 SMILES language model，也不是一个只在离散图上逐边扩展的普通 graph decoder。它的主循环是：

```text
property prompt
  → PropertyScaler / masked multi-property prompt
  → MoleculeTransformer state
  → factored action head: fragment × attachment site
  → Architect legality + geometry-aware docking
  → open-site queue / saturation update
  → termination or next fragment
  → P-SMILES repeat-unit validation
```

关键实现位置：

- `molminer/generator.py`：采样循环、随机/greedy 解码、property prompt、`max_fragments` guard、intermediate trajectory。
- `molminer/models.py`：fragment embedding、saturation feature 的 FiLM、property FiLM、几何 pairwise bias、transformer readout。
- `molminer/factored_head.py`：`P(fragment) × P(site | fragment)`，而不是把整个候选动作压成一个扁平类别。
- `molminer/processor.py`：`GraphProcessor`、开放 attachment-site queue、`Architect.can_dock`、valence/element/arity/sanitize 检查，以及 conformer/UFF 相关的几何更新。
- `molminer/repeat_unit.py`：P-SMILES 的两个 `*` 端点、canonicalization、dimer sanitization 和 backbone fraction。

公开 corpus 有 13,605 个去重 repeat units，包含 HTP-MD、PolyMetriX Tg、RadonPy PI1070 和 Bicerano 来源；共有 10 个 property 头：`log_conductivity`、`log_li_diff`、`log_tfsi_diff`、`transference`、`tg`、`density`、`bulk_modulus`、`thermal_cond`、`dielectric`、`refractive_index`。检查点 metadata 显示 4-layer、16-head、`d_model=512`、`d_ff=2024`、factored head、`d_env=256`，训练 seed 为 42。

这意味着 MolMiner 的“合法性”部分进入了生成闭环：每一步都尝试一个具有 attachment site 的 fragment，并在 docking 前后做化学约束；但最终输出仍可能因为只剩一个 `*` 或超过 fragment cap 而失败。本轮将 `max_fragments=80` 的 cap-hit 计为 failure，而不是截断为成功样本。

## 3. PolyGen 的生成链路

本轮 PolyGen reproduction 使用 `scripts/run_experiment_c1.py`：

```text
P-SMILES-like endpoint sequence
  → DeepChem SmilesTokenizer
  → gpt-nano causal transformer
  → 5-token soft condition prefix
  → top-k(40) multinomial decoding
  → endpoint / RDKit post-hoc validity
  → frozen C1 random-forest verifier
```

continuous arm 将 z-scored scalar condition 经 MLP 映射后加到前五个 token embedding；binary arm 将 `cond >= -4` 映射成二分类 embedding。两者都训练 1000 steps、temperature 1.0。PolyGen 的化学合法性是在完整序列生成后判断：RDKit parseable 且恰好一个 `[Cu]` 和一个 `[Au]`，并不在每个 token/action 生成时做 MolMiner 式 docking。

因此，两者的长度、novelty 和 failure 不能直接按一个“token 数”解释：MolMiner 的 step 是 fragment action，PolyGen 的 step 是 tokenizer token；MolMiner 还有 geometry/queue/saturation state，PolyGen 的主要状态是 causal token prefix。

## 4. 预期并已观察到的生成差异

| 维度 | MolMiner | PolyGen | 这会怎样影响样本 |
|---|---|---|---|
| 基本单位 | 带 attachment site 的 fragment | tokenized SMILES 序列 | MolMiner 更容易保留局部化学合法性；PolyGen 更自由地探索字符串空间 |
| 生成状态 | graph queue、open sites、saturation、3D/几何特征 | causal token context | MolMiner 的结构增长带有动作可行域；PolyGen 的错误常在末端才暴露 |
| 条件输入 | 多属性 masked prompt；本轮只给 conductivity | binary 或 continuous scalar soft prefix | MolMiner 的 prompt 语义来自 quantile/property scaler；PolyGen continuous 是 C1 z-score scalar |
| 采样 | fragment/site/termination 的 stochastic action | top-k=40 后 multinomial | 结果的随机性来源不同，不能把 seed 当作同一个随机轨迹 |
| 合法性 | in-generation docking + 最终 P-SMILES validation | post-hoc RDKit/endpoint validation | MolMiner 常见 cap/valence failure；PolyGen 常见无效序列 |
| 输出形态 | 通常较短的 fragment trajectory，median 约 23–25 steps | token length 受 block size 截断 | 不能用 fragment steps 与 token length 做直接大小排名 |

本轮统计与这个机制一致：MolMiner 的 `-4` 目标最容易控制，strict hit rate 为 `0.754`；`-5` 只有 `0.042`；`-3` 为 `0`，并且 `-3` 的 generation success 降到 `0.954`，同时出现更高的 fragment/sanitize rejection。MolMiner 在 `-4` 的 target MAE 为 `0.295`，高于 PolyGen binary `0.198` / continuous `0.212` 的 reproduction 结果，因此在 MAE 上并不占优；但它在 strict hit 上为 `0.754`，高于 PolyGen binary `0.476` / continuous `0.528`。这说明“平均误差”和“strict hit”在这轮不同 support/validity 规则下并不等价，不能只看一个数字下结论。

PolyGen 五种子结果则显示：continuous 相对 binary 的总体 strict hit 小幅提高（`0.1587 → 0.1780`），但 validity/novelty 下降；两套系统都明显在 `-5` 与 `-3` 边界条件上失配，`-4` 附近最好。

## 5. 本轮证据

- 原始 MolMiner 样本：`runs/molminer-c1-seed5/samples.csv`，1500 rows。
- MolMiner seed × target 指标：`runs/molminer-c1-seed5/arm_seed_target_metrics.csv`，15 rows。
- docking / rejection 统计：`runs/molminer-c1-seed5/dock_stats.csv`。
- checkpoint 与输入哈希、运行配置：`runs/molminer-c1-seed5/manifest.json`。
- 首轮汇总：`runs/molminer-c1-seed5/summary.json`。
- 合并 target-level comparison：`analysis/combined_target_metrics.csv`。
- 汇总 JSON：`analysis/molminer_polygen_comparison_summary.json`。
- Figure 与 caption：`figures/molminer_polygen_c1_behavior.png`、`figures/molminer_polygen_c1_behavior_caption.md`。

首轮 MolMiner 总体结果：1500 raw rows，1465 个 valid repeat units，1345 个 unique valid canonical units，其中 1231 个相对 merged corpus 为 novel；common verifier 为 RMSE `0.1569`、MAE `0.1243`、R² `0.4980`。这些 verifier 指标用于描述共享评估器状态，不应被解释为 MolMiner 的 held-out model score。

## 6. 下一步严格公平实验

要把这轮行为 baseline 升级为真正的 apple-to-apple performance comparison，需要：

1. 用与 PolyGen 完全相同的 C1 train/test rows 重建 MolMiner 可用的 repeat-unit corpus，并确定只保留训练 split 的 property scaler / corpus novelty reference。
2. 用相同五个 training seeds 训练 MolMiner，而不是使用公开的 seed-42 merged-corpus checkpoint。
3. 明确 fragment vocabulary、geometry cache、training step budget 和 checkpoint selection rule。
4. 预注册同一套 validity、novelty、support、uncertainty、strict-hit 和 target-MAE 统计，并把 MolMiner native legality 与 PolyGen post-hoc validity 分开报告。

在完成这一步之前，当前结果最适合作为：**两种生成机制在同一 C1 任务预算下的第一轮行为差异证据**。
