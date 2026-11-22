---
title: Pitch × PolyGen gap analysis — TODO and acceptance ledger
date: 2026-10-16
status: active
tags: [project/polygen-reproduction, project/ARC-Suite, type/gap-analysis]
---

# 结论

Stage 0 的真实数据图表已经重算并交付：P1/P2、F1–F5、T1–T6 均有机器可读源表、PNG/PDF/SVG 和 caption。剩余的核心阻塞仍是 physical validation：外推候选没有 PCFF+ 参数化、没有外推队列 MD、没有残差校准或 active-learning update。因此本包不把 `0 RF crossing` 写成“生成器不能外推”，而写成 **surrogate-only / verifier-limited，物理 crossing 尚未判定**。

# 全量 TODO

| ID | 任务 | 当前状态 | 本包产出 / 验收证据 | 下一步门槛 |
|---|---|---|---|---|
| A1 | Quantify verifier ceiling：locked-tail 分 bin 范围、残差、ρ、coverage，并比较 blind/full-source RF | **完成** | `assets/tables/T3_locked_tail_verifier_bins.csv`; `assets/figures/P2_verifier_blind_locked_tail.*`; `F5_verifier_audit.*` | 真实 MD 后重算同一指标；full-source 层不得替代 blind endpoint |
| A2 | 对 Q90/Q100/+0.25/+0.50 外推候选做分层 MD | **阻塞** | `assets/tables/T4_md_funnel.csv`; `candidate_selection_for_md.csv` 仍为 `not_run_proposed_only` | 先完成 A3/A4/A5；每结构 5 replicas、PCFF+ primary、PFP secondary |
| A3 | 验证 PCFF+ Top-1/候选可分型漏斗 | **NO_GO；preflight 完成** | `evidence/data/pcff_plus_bundle_audit/pcff_plus_bundle_audit.json`: 9 个 required classes 均无 candidate-specific bundle；canonical `top1_readiness_audit.json` 仍 FAIL | 获得候选专属 typing/charges/topology/coefficients；再跑 PEO+LiTFSI 阳性对照、磷体系阴性对照和 run-0 acceptance |
| A4 | 修复 Hisa review 的 9 个代码正确性问题并回归 | **隔离回归完成，canonical merge 待处理** | `HISA_REVIEW_ACTIONS.md`; `evidence/data/hisa_patch_regression_results.json`; `evidence/data/c1_recomputed_audit_fixed/` | 将隔离 patch 合并 canonical；#8 policy 和 #9 物理证据仍需 owner/实验闭环 |
| A5 | MD 命中判据预登记 | **已起草，未获外部批准** | `assets/tables/T6_freeze_card.csv`；其中命中/收敛行标记 `proposed_not_yet_TRI_approved` | 在任何新 MD 数据产生前由项目 owner 签字、记录日期/SHA |
| A6 | 定量“下一步行动”的 decision value | **定义完成，结果缺失** | T6 定义成本/确认命中；F8 是 synthetic placeholder | MD 后比较 RF ranking vs calibrated ranking 的 top-k confirmed hits / cost |
| A7 | residual-driven active-learning update | **阻塞** | F1/P3/F6 显示 update 为 planned；F8 synthetic | 依赖 A2 的 MD 真值和 A6 的 decision metric |
| A8 | MolMiner / Wee 严格同支持集重训 | **部分完成；strict MolMiner five-seed/five-epoch smoke PASS；20-epoch 与 50-epoch extended engineering comparison PASS；发表级结果未完成** | `STRICT_MOLMINER_SMOKE.md`; `assets/tables/T12_molminer_strict_c1_smoke.csv`; `assets/tables/T13_molminer_extended20_vs_smoke.csv`; `assets/tables/T14_molminer_extended50_vs_smoke.csv`; `assets/figures/S1_molminer_extended20_vs_smoke.*`; `assets/figures/S2_molminer_extended50_vs_smoke.*`; five split-specific 50-epoch runs have finite checkpoints and common RF generation audit; WeeMiner code smoke PASS but ZINC/logP-only | Freeze the final publication budget/checkpoint-selection rule; task-aligned Wee; same verifier/final candidate budget; independent held-out matched-support evaluation |
| A9 | fragment 表示、PI1M 预训练、Ohsaki/数据扩充实验 | **近似 overlap exploratory audit 完成，full-source audit 当前被外部 PI1M 文件缺失阻塞，训练实验未完成** | `evidence/data/pi1m_overlap/summary.json`：精确重合 59/6,024；`evidence/data/pi1m_near_overlap/summary.json`：1-in-10 systematic PI1M sample 中 Morgan≥0.85 共 21 行，其中 14 行非 exact；`evidence/data/pi1m_near_overlap_full/README.md` 记录 full-source 未运行；PI1M 预训练、Ohsaki 扩充仍未完成 | 恢复 `/tmp/pi1m/PI1M_v2.csv` 或提供等价审计输入；做 full-source、预注册的 near-duplicate audit；剔除 exact/near duplicates；再跑同一 extrapolation benchmark |
| A10 | Structural-OOD | **split leakage audit 完成，真正 OOD 仍阻塞** | `evidence/data/structure_split_audit/canonical_overlap_audit.json`：released-random canonical overlap 312；structure-disjoint overlap 0 | 获得 scaffold/family 标注和结构不交叉的 matched checkpoints；不能把 row-level disjoint 当作 scaffold-OOD |
| A11 | 统一图风格、修 Ext Fig1/Fig4/C1 缺陷 | **完成（本包）** | P1/P2、F2–F5 重画；unsupported、RF range、n、状态和 caption 已加 | 外部期刊尺寸确认后做最终版式回归 |
| A12 | 文档债务、grid、Overleaf sync | **部分完成** | 新包含 T2、grid 资产审计、动态 row-derived grid plan、Hisa snapshot 和 handoff；canonical grid summary 已覆盖 9 configs，但旧 `analysis.log` 仍陈旧；canonical Overleaf 未写入 | 重生成/归档旧 grid log；Overleaf token 需用户一次性授权 |
| A13 | 17 页稿加入 PolyGen Improve 回路页 | **稿件素材完成，主稿未改** | P1–P3 图、captions、讲稿候选文本在 `OVERLEAF_HANDOFF.md` | 由 owner 决定是否把三页插入 pitch；不得把 planned MD 写成结果 |

# Stage gate

## Design / feasibility

- [x] primary estimand、对照 arm、seed pairing、冻结 Q80 split 和 interpretation boundary 已记录。
- [x] canonical source SHA、6,024 行、4,819 train / 1,205 locked tail、训练边界 −4.084499111 已记录。
- [x] binary 在 Q80 截断后 single-class degeneracy 已记录为 negative control。
- [ ] PCFF+ coverage 完整；目前 top-1 readiness gate fail。
- [x] MolMiner/WeeMiner local asset inventory recorded; strict MolMiner split/vocabulary/rollout/packed preflight and five-seed/five-epoch generation smoke are archived; no task-aligned WeeMiner conductivity result is claimed。
- [ ] MolMiner final frozen-budget/independent-selection strict C1 retraining and task-aligned WeeMiner/equivalent arm；50-epoch five-seed comparison is real engineering evidence but not the final publication leaderboard。

## Prediction completion

- [x] 3 arms × 5 seeds × 4 extrapolation cells，候选总数和退出码通过 canonical verification。
- [x] unsupported/blocked cell 显式保留，不当作 0 quality。
- [x] blind RF 与 full-source RF 的解释边界分开。
- [x] 在隔离临时根目录重跑 prediction-stage verification；6,000 candidates / 60 cells / 200 proposed MD rows 全部通过结构与泄漏检查。

## Physical completion

- [x] A4 Hisa review 的隔离 patch 回归和真实 C1 corrected audit 已完成；canonical merge、#8 policy 和 #9 physical follow-up 未完成。
- [ ] PCFF+ assignment / missing-parameter report。
- [x] Candidate-specific PCFF+ bundle preflight and explicit missing-class report completed; numerical coverage is intentionally not invented while the bundle is absent.
- [ ] external MD execution，5 replicas/structure，收敛和构建门禁。
- [ ] PFP top-1 证据链仅通过 39/41 checks；两个 trajectory hash 文件缺失，不能升级为 converged physical evidence。
- [ ] T4 complete，F6 real-data version，MD-confirmed crossing。
- [ ] residual calibration、decision-change F8、active-learning update。

## Generator strict-support closure boundary

The strict MolMiner smoke is a software/data-path acceptance only. The legacy
NaN failure and the packed-loader repair are recorded so they cannot be hidden
by a later successful run. The 4/8 generation result is not a publication
metric. A8 remains open until both generators use the same C1 support, paired
seeds, candidate budget, verifier, checkpoint-selection rule, and final
held-out evaluation.

## Publication gate

- [x] P1/P2/F1–F5 有 PNG、PDF、SVG，且各有 caption。
- [x] T1–T6 为 CSV，数字可回溯到输入表和脚本。
- [x] synthetic/planned 图全部在文件名、图内或 caption 中显式标注。
- [ ] 期刊最终单/双栏尺寸由 owner 确认后再做最后版式回归。
- [ ] Overleaf/主稿同步尚未授权，submission root 保持不变。

## Hisa review closure boundary

`HISA_REVIEW_ACTIONS.md` 是 A4 的逐项验收表。其 isolated PASS 仅证明 package-local patch 可通过回归，不宣称 canonical PR 已合并；尤其不解除 PCFF+ readiness 的 NO-GO，也不把 PFP smoke 升级为 MD 真值。
