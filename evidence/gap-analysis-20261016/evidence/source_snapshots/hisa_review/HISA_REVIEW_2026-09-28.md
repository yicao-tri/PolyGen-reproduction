---
title: Hisa PR review：top1 PFP-MD pilot NO-GO 追溯与代码正确性问题清单
tags: [project/polygen-reproduction, review/hisa]
created: 2026-09-28
related:
  - "[[2026-09-25 - Top1 PFP-MD paired pilot（continuous vs binary）]]"
  - "[[2026-09-27 - Experiment C grid 扩展：新增 gpt-nano-3000steps-temp1.0，7-config 合并分析]]"
status: active
---

# Hisa 对 top1 PFP-MD pilot PR 的 review（2026-09-28）

来源：Hisatsugu Yamasaki 在 `yicao-tri/PolyGen-reproduction` PR 上的 review comment。

整体评价：generation-grid 的数值结果没问题；提出的问题都在 top1 pilot 的流程记录 + 几个脚本的正确性，建议在 top-10 PFP extension 建立在这个 pilot 之上之前先修。

## 1. 流程问题（非阻塞，但要补记录）

- `TOP1_MD_VALIDATION_DESIGN_ZH.md` 里 2026-09-24 记录了明确的 **NO-GO**：反对用当前 ARC/PFP 路径跑 top-1 200 ps job，原因是这会用 Matlantis PFP 替代 PCFF+、用普通 Nernst-Einstein 估计器替代原文的 cluster Nernst-Einstein，破坏该文档自己设定的"与原文 1:1 对齐"要求。
- 但已提交的 `top1_pilot_contract.json`（冻结于 2026-09-25T02:15 UTC）和对应 report 显示，这个 job 第二天还是用 PFP 跑了。
- report 本身有谨慎标注 `NON_CONVERGED_SMOKE_ONLY`，没有声称模型优越性，Hisa 认为科学结论上没有误导，**但没有任何地方记录 NO-GO 为什么被推翻**（例如"仅做 pipeline 冒烟测试可以不用 PCFF+，只要明确不是 paper-equivalent run"这类说明）。
- 需要：
  - 补一行说明，reconcile NO-GO 被 supersede 的原因。
  - 同步更新 `README.md` / `AUDIT_CHECKLIST.md` / `FROZEN_GENERATION_CONTRACT.json`——这几个文件目前仍写着 PFP/MD execution "requires sign-off" 和 "has not started"，与实际已跑的事实不一致。
- 关联问题：design doc 的 protocol table 要求 2 fs timestep（对齐原文），但实际跑的是 1 fs；总时长同样是 200 ps，掩盖了这个差异，需要补一行说明原因。

## 2. 代码正确性问题（top-10 PFP extension 前必须修）

| # | 文件 | 问题 | 影响 |
|---|---|---|---|
| 1 | `scripts/analyze_pfp_htpmd.py` | `conductivity()` 硬编码 `range(10) x range(10)` 求和，但 `population_matrix()` 分配的是 `(50,50)`，`--ion-pairs` 又没有上限 | 50 个 ion pairs（下一步的目标规模）时会静默丢失 cluster mass，导致报告的 conductivity 偏低；若单个 cluster 覆盖某物种全部离子还会直接 `IndexError` |
| 2 | `scripts/summarize_pfp_top1_pair.py` / `render_pfp_top1_report.py` | `cluster_ne_log10_S_cm` 在 cluster conductivity ≤ 0 时可能是 `None`，但 paired-contrast 相减和 `{:.4f}` 格式化都没有判空 | 未来只要有一对遇到"所有检测到的 cluster 都是简单 1:1 pair"这种情况就会直接崩溃 |
| 3 | `render_pfp_top1_report.py` | convergence-sensitivity 表对 `values[160.0]` 做无保护查找，但决定 160.0 是否被纳入的两个上游阈值判断（`<= elapsed_ps + 1e-9` vs `>= 159.9`）互相矛盾 | 例如跑到 159.95 ps 时会通过前面的 gate，但 render 阶段 `KeyError` |
| 4 | `scripts/audit_generation_benchmark.py` | `target_prediction_correlation` 是在 `groupby(['arm','seed','target'])` 内部计算的，而 `target` 在每个 group 内是常量 | 导致每一行的相关系数都是 NaN——这个指标目前实质上是坏的 |
| 5 | `tests/test_pfp_htpmd_analysis.py` | `test_ne_conductivity_matches_closed_form` 的输入会让 cluster-weighted 公式退化成普通 Nernst-Einstein 值 | 测不出 cluster-weighting 逻辑（本 PR 的核心计算）的回归 |
| 6 | `scripts/build_pfp_pilot_system.py` | "orthorhombic" 检查只验证了 lattice matrix 9 个元素里的 3 个（漏了 yy/zz vs xx） | 四方晶胞（tetragonal cell）会被误判通过，被静默打包进错误形状的 box |
| 7 | `scripts/build_grid_plan.py` | `GRID_PLAN.json` 里 `planned_raw_samples_gpt_nano`（90,000）和 `estimated_gpu_hours_gpt_nano`（67.5）与脚本自己循环算出来的值（18,000 / ~45）对不上 | 像是手改后遗留的过期数字 |
| 8 | `.gitattributes` | diff 把 `results/experiment-a/**/*.csv|tsv` 的 `-diff -merge -text` 属性去掉了、且没有替代方案 | 取消了对 sha256-tracked evidence 文件的保护——而这正是本 PR 新增注释想守护的东西，只是范围写错了文件夹 |
| 9（minor） | 归档快照 `results/experiment-c/pfp-pilot/production/scripts/render_pfp_top1_report.py` / `binary/runner.py` | 缺少诊断图部分和 COM-momentum-zeroing 调用（canonical/更新版本里有） | 需要检查这两份"冻结快照"对应的实际跑法是不是 COM drift 未校正——`analyze_pfp_htpmd.py` 自己的 diagnostic 也把这个标记为 unresolved |

## 3. 我们计划怎么改

- [ ] **流程记录补齐**：在 `TOP1_MD_VALIDATION_DESIGN_ZH.md` 补一段 reconciliation，说明 NO-GO 之后为什么仍执行了 PFP 版 top1 job（定性为 pipeline smoke test，非 paper-equivalent run），并同步刷新 `README.md`、`AUDIT_CHECKLIST.md`、`FROZEN_GENERATION_CONTRACT.json` 中过期的 "requires sign-off / has not started" 措辞。
- [ ] **补 timestep 说明**：在同一份文档里加一行，说明 1 fs vs 原文 2 fs 的差异及原因（若是为了稳定性/保守选择，需写明）。
- [ ] **`analyze_pfp_htpmd.py`**：把 `conductivity()` 里硬编码的 `range(10) x range(10)` 改为与 `population_matrix()` 的实际维度（含 `--ion-pairs` 的动态上限）保持一致，并加边界检查防止单 cluster 覆盖全部离子时的 `IndexError`。
- [ ] **`summarize_pfp_top1_pair.py` / `render_pfp_top1_report.py`**：对 `cluster_ne_log10_S_cm` 为 `None` 的情况加判空分支（配对相减 & 格式化都要处理），避免 cluster conductivity ≤ 0 时崩溃。
- [ ] **`render_pfp_top1_report.py`**：统一 160.0 是否入表的判断阈值（让上游 gate 和下游 lookup 用同一个条件），或改成 `.get()` + 缺省处理，消除 `KeyError` 风险。
- [ ] **`audit_generation_benchmark.py`**：修正 `target_prediction_correlation` 的计算——不能在按 `target` 分组之后再算与 `target` 的相关性，需要重新设计这个指标（很可能要去掉 `target` 或换一个不常量的分组维度）。
- [ ] **`test_pfp_htpmd_analysis.py`**：重写 `test_ne_conductivity_matches_closed_form` 的输入，使其在 cluster-weighted 公式和普通 Nernst-Einstein 不退化重合的情况下也能检测出回归。
- [ ] **`build_pfp_pilot_system.py`**：把 orthorhombic 检查补全为验证全部 9 个 lattice matrix 元素（含 yy/zz vs xx），拒绝四方晶胞被误判通过。
- [ ] **`build_grid_plan.py` / `GRID_PLAN.json`**：用脚本循环里实际算出的数字（18,000 raw / ~45 GPU-hours）覆盖掉过期的手改值（90,000 / 67.5），或者让 JSON 直接从脚本计算结果生成，避免以后再次漂移。
- [ ] **`.gitattributes`**：恢复 `results/experiment-a/**/*.csv|tsv` 的 `-diff -merge -text` 属性，确认 sha256-tracked evidence 文件范围没有被误删。
- [ ] **归档快照核查（minor）**：检查 `results/experiment-c/pfp-pilot/production/scripts/` 下冻结快照对应的实际运行是否确实缺失 COM-momentum-zeroing；如果是，需要在报告里补充 COM drift 未校正的说明，或重新跑一次校正版本作为新的冻结快照。

## 4. 状态

- 未合并，等待上述修改完成后再推进 top-10 PFP extension。
- 需要回复 Hisa：确认收到 review，逐条修复中，修完后请他再看一遍再合并。
