---
title: Hisa review action ledger — PFP top-1 pilot and generation benchmark
date: 2026-10-16
status: isolated regression evidence complete; canonical fixes still pending
---

# Scope

本文件把 2026-09-28 的 Hisa review 转成逐项可验收的 action ledger。所有代码修复均只在 `evidence/hisa_patch/` 做隔离验证；本包遵守项目约束，不修改 `/Users/yicao/Documents/ARC/PolyGen-reproduction` 的 canonical 资产。因此这里的 PASS 表示“补丁候选通过本包回归”，不表示 canonical PR 已合并。

原始审查快照：`evidence/source_snapshots/hisa_review/HISA_REVIEW_2026-09-28.md`。

## 逐项状态

| # | Hisa 问题 | 隔离处理 | 状态 | canonical 下一步 |
|---|---|---|---|---|
| 1 | `analyze_pfp_htpmd.py` 将 cNE population 固定为 `range(10)`，会漏掉 50×50 population 的高聚集态并可能越界 | patched copy 改为检查 square matrix 后动态遍历全部维度；回归覆盖 index 11 | PASS（isolated） | 合并 canonical analyzer，并更新 adapter definition / checksum |
| 2 | `None` cNE log 值在 paired contrast 中直接相减 | patched copy 使用 optional subtraction；缺失值保留为 `null` | PASS（isolated） | 合并 canonical summary，并补缺失值 fixture |
| 3 | convergence renderer 直接索引 `values[160.0]`；159.95 ps 等边界会通过上游门禁却渲染失败 | patched copy 改为 `.get()` + `n/a`；160 ps 缺失不会 KeyError | PASS（isolated） | 统一 159.9/160.0 边界定义并合并 renderer/test |
| 4 | `target_prediction_correlation` 在单 target group 内计算，因 target 常量而全部 NaN | patched copy 将单 target 相关性明确设为 NaN，并在 arm×seed 跨 target row 上计算相关性；修正 target summary 的 `predicted_mean` 来源 | PASS（real C1 audit） | 合并 canonical audit；保留单 target 不定义的注释 |
| 5 | cNE 单元测试退化为 ordinary NE，未测试 cluster weighting | patched copy 增加非退化高聚集态 population fixture，检查 cNE 与 NE 不相等且动态维度被纳入 | PASS（isolated） | 合并 canonical test |
| 6 | orthorhombic cell 检查遗漏 yz/zx/zy 等 off-diagonal entries | patched copy 检查完整 3×3 lattice 的 6 个 off-diagonal entries 与正 diagonal | PASS（isolated） | 合并 canonical builder/test |
| 7 | grid plan raw/GPU 总量手写且陈旧（当前 3 steps 实际是 27,000 raw / 90 GPU-hours for gpt-nano） | patched copy 从 rows 动态汇总并生成 plan；输出与现有 9-config grid 审计对齐 | PASS（isolated） | 重生成 canonical `GRID_PLAN.json`，同时归档旧 log |
| 8 | `.gitattributes` 移除了 experiment-A CSV/TSV 保护且无替代 | package 保存当前 snapshot，并把缺口列为 release hygiene TODO | OPEN（policy） | owner 决定是否恢复大文件保护或改用 LFS/manifest policy |
| 9 | archived snapshot 的 COM drift / diagnostics / report 内容与当前实现不一致 | package 核对到当前 analyzer 有 COM diagnostic，但 archived renderer 缺 optional MSD block；pilot 仍是 non-converged smoke | PARTIAL | 合并前重新生成报告、核验 trajectory hash，并完成 5-replica/5-ns 物理证据 |

## Process reconciliation

- 原始设计文件在 2026-09-24 对 “PFP 替代 PCFF+、ordinary NE 替代 cluster NE” 记录为 NO-GO；随后实际运行了 PFP pilot。
- pilot 报告本身标为 `NON_CONVERGED_SMOKE_ONLY`，没有把它写成科学结论，但设计文件、README、audit checklist 和 frozen contract 仍有 stale wording。
- 本包将该 pilot 定位为“技术可行性 smoke anchor”，将 `PCFF+`、5 replicas、5 ns、收敛判据和 residual calibration 继续保留为正式 physical gate；不以 PFP smoke 替代。
- 另一个文档不一致是设计写 2 fs timestep、实际运行 1 fs；canonical 合并前必须记录原因、输入文件和 checksum。

## Release rule

只有以下条件同时满足，A4 才能从“isolated regression PASS”升级为“canonical complete”：

1. canonical source merge 后重新跑对应 tests；
2. `audit_generation_benchmark.py` 重新生成 C1 audit 并保存 SHA；
3. renderer 能处理缺失/非正 cNE 与所有实际 convergence durations；
4. `.gitattributes`/LFS 策略由 owner 明确；
5. PCFF+ readiness 全部 PASS 后才允许新的 MD launch；PFP smoke 不构成放行。

