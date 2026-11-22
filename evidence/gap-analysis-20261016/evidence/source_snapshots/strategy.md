---
title: Pitch × PolyGen 差距分析：目标图表、验收标准与端到端执行策略
tags: [project/polygen-reproduction, project/ARC-Suite, type/gap-analysis]
created: 2026-10-16
related:
  - "[[2026-10-15 - Midterm 17页完整英文稿（close-loop driven）]]"
  - "[[2026-10-14 - Midterm 证据、Related Work 与 Gap 对照]]"
  - "[[PolyGen-reproduction Hub]]"
  - "[[2026-09-30 - PolyGen续作论文蓝图：train-from-scratch 外推上限、与 MolMiner 对照及下一步]]"
  - "[[TODO]]"
status: draft
---

# 0. 结论先行

1. **17 页稿里没有 PolyGen 页。** 17 页稿（close-loop 版）只用了 MIT 和 HTXRD；PolyGen 只出现在上一版 16 页主线的 Slide 13（"Improve"）。要用 PolyGen，必须明确它在闭环里的角色：**Improve 回路 = 生成 → 验证 → 校准 → 选下一批 MD**。
2. **PolyGen 只走完了闭环的前半段。** 已有：目标、冻结协议、生成、RF 验证、locked-tail 审计。缺失：物理观测（MD）、残差校准、下一步行动、更新。pitch 的核心句（Slide 8、11、12）在 PolyGen 上没有一条有真实数据支撑。
3. **最关键的科学缺口：现有的"frontier-crossing = 0"不能归因于生成器。** 见 §2.1。RF 在 locked tail 上的预测被压在约 [−4.45, −4.18]，而真实值最高到约 −3.3。这个 verifier 在数学上就不会输出越过 −4.0845 的值。在做 MD 残差校准之前，这个负结果在 pitch 里只能说成"verifier-limited"，不能说成"generator-limited"。
4. **图的发表质量也有缺口。** 我只看了 3 张图（Ext Fig1、Ext Fig4、C1 five-seed），已经发现具体缺陷，见 §2.3。

> **范围与未验证项。** 数字来自我读到的 CSV、README 和 vault 笔记（`results/extrapolation/publication/extrapolation_aggregate_metrics.csv`、`results/experiment-c/publication/c1_five_seed_effect_summary.csv` 等）。我没有重跑任何代码，没有逐张检查全部 ~40 张 publication 图，也没有核对 git 远端状态。§4 的验收阈值是我提出的建议，不是 TRI 或期刊的规定。

---

# 1. Pitch 闭环 vs PolyGen 实际：逐环节对照

闭环（17 页稿 Slide 2）：**Goal → Act → Observe → Evaluate → Update**，加上 Slide 11–12 的 **Next action + 冻结预测**。

| 闭环环节 | Pitch 的要求 | PolyGen 现状 | 状态 |
|---|---|---|---|
| Goal / Contract（Slide 3） | 科学目标、成功判据、资产、动作空间显式化 | 目标 log10σ；冻结边界 −4.0845；4,819 行 ≤Q80、1,205 行 locked tail；`design_contract.json` 已有 | ✅ 有，但没画成图 |
| Act（生成） | 生成候选 | 5 seeds × {continuous, binary, unconditional-rerank}，4 阶段评测（interp / upper-tail / extrap / structural-OOD） | ✅ 前三阶段完成，structural-OOD blocked |
| Observe（物理观测） | 可比较的观测 | **只有 RF 代理。** MD：Top-1 PFP pilot 被判 NO-GO / `NON_CONVERGED_SMOKE_ONLY`；外推候选 MD 为 0；PCFF+ 运行时已验证，但 Top-1 的 PCFF+ 分型未实跑；Hisa review 的 9 处代码问题未清完 | ❌ 核心缺口 |
| Evaluate（校准） | 排序可靠性要在决策集中的区域检验（Slide 10 的 NOVA 论点） | locked-tail RF 审计已有：MAE 0.310，mean residual +0.310（系统性低估）；但 RF 预测范围塌缩 | ⚠️ 有诊断，没有修复 |
| Next action（Slide 11） | 选"改变决策"的下一步 | `candidate_selection_for_md.csv` 是"proposed"；`md_batch_manifest.csv` 全是 `PLANNED_NOT_RUN`；没有 EIG 或决策价值度量 | ❌ 无 |
| Freeze before experiment（Slide 12） | 先冻结预测、判据、模型版本 | 预测阶段已冻结（SHA、`frozen_manifest.json`、`design_contract.json`）；**MD 命中判据尚未预登记**（TODO 里写着"先预登记"） | ⚠️ 半有 |
| Update（回到假设） | 观测后更新信念，选下一轮 | 无。主动学习排在 MD 之后 | ❌ 无 |
| Reuse（Slide 17 第 3 问） | 能力可被他队复用 | MolMiner 对照只是行为基线（其语料含 HTP-MD）；Wee 未加入；严格同支持集重训未做 | ❌ 无 |

**一句话差距：** pitch 说"从观测到可执行决策"，PolyGen 现在只证明了"在代理验证器下，生成器在边界内可控、在边界外零命中"，没有任何一个"决策"被产生或检验。

---

# 2. 现有结果的具体问题

## 2.1 科学上：verifier ceiling 混淆（最重要）

- Ext Fig 4（locked-tail audit）：真实 Q95–Q100 行的观测值高达约 −3.3，而 RF 预测全部落在约 −4.45 到 −4.18。
- 同时 Ext Fig 1 panel A：continuous 的 RF 预测对所有请求目标都平在 ≈ −4.30（Q90 到 train_max+0.50 都是）。
- 推论：RF 对这个区域**没有分辨力**，也越不过 −4.0845。因此"0 frontier crossing"同时可由两种原因解释：(a) 生成器没有产生高电导率结构；(b) verifier 看不出来。**现有数据区分不开。**
- 对 pitch 的影响：Slide 10 的论点（"全局看着没事，在决策集中处失效"）在 PolyGen 上恰好成立，可以直接用来讲，但措辞必须是 *"the verifier cannot resolve the region where the decision concentrates"*，而不是 *"extrapolation fails"*。这也符合 10-14 笔记的纪律：说 "no candidate predicted to cross the locked frontier"。
- 修复路径：MD 残差阶梯（RF → PCFF+ → PFP），或至少用 full-source RF（MAE 0.131）做同样的 ceiling 检验。

## 2.2 效应量的措辞边界

- C1 continuous vs binary：strict hit 0.1587 → 0.1780（+0.0193，paired t p = 0.014），MAE 0.694 → 0.633，但 validity 0.522 → 0.455、novelty 0.503 → 0.431 下降。
- 5/5 seed 同向，但 sign test p = 0.0625，只有 5 个种子。
- C1 panel A 显示：请求目标从 −5 到 −3，两个 arm 的 verifier 预测都几乎不动（continuous 约 −4.35 → −4.05）。"controllability" 的视觉证据弱，应改用相关系数、斜率和 CI 来表达，不要靠这条曲线。
- MolMiner 对照（validity ~0.95–0.99 vs ~0.4–0.56）：其语料含 HTP-MD，只能称 descriptive behavioral baseline。

## 2.3 图的质量缺陷（已核实的三张）

| 图 | 缺陷 |
|---|---|
| `Figure_1_extrapolation_response` | binary 在图例里有（橙色），图中**一条线都没有**，没有标注"unsupported"；三个子图占一半面积是空白；unconditional-rerank 只到 +0.25，缺 +0.50，无说明 |
| `Figure_4_locked_tail_rf_calibration` | 标题只有 "I"（面板字母被截成标题）；y 轴标签被裁切（"log₁₀ S cn…"）；没有 RF 不确定度；没有标出 verifier 预测上限；无 n |
| `c1_five_seed_publication` | 无明显错误；panel A 信息量低（见 2.2）；panel C 的 CI 用 t 区间（n=5），需在图注里写清 |

其余图（interpolation、upper-tail、multi-property、grid、MolMiner 对比）**我没有逐张看**，需要按 §4 的清单做一遍统一检查。

---

# 3. 目标图表设计

约定：**实线 = 已有真实数据**；**虚线/斜线填充 = 预期形状（synthetic）**。示意图在 `mockups/`（脚本 `make_mockups.py`），每张图右下角带红字 "SYNTHETIC MOCKUP"。**示意图只用于规划，绝不进入最终稿。** 目前只做了三张示意图，其余用文字规格描述。

## 3.1 Pitch 页（建议 3 页 + 1 页 backup，插在 Case 2 之后、Act V 之前）

17 页稿目前 Slide 9–12 全是 HTXRD。PolyGen 作为"Improve"回路的短案例，放 3 页，不挤占 HTXRD 的时间。

### P1 — "A generator can look better on every dashboard and still not help the decision"

- **目的：** 说明 validity / novelty / hit rate 不等于决策价值。
- **图（重做，不沿用 C1 三面板）：** 一张 2×2 小图。
  - A：请求目标 vs verifier 预测（−5/−4/−3），两个 arm，虚线为 y = x；点上加 95% CI，标出斜率。
  - B：配对 seed 斜线图（strict hit，5 条线）。
  - C：continuous − binary 的差值 forest plot，四个指标（hit、MAE、validity、novelty），**validity / novelty 用红色标出方向为"代价"**。
  - D：binary 在 Q90/Q95 的 "unsupported (5/5 seed-cells)" 灰色斜线块，体现"不是被省略，而是结构性失效"。
- **表 T1（放 backup 或旁白）：**

| 行（arm） | 列 |
|---|---|
| Binary / Continuous / MolMiner（descriptive）/ Wee（待加） | strict-hit（mean ± SEM）· target MAE · validity · novelty · Δ vs binary [95% CI] · 备注（"语料含 HTP-MD"等） |

- **预期样子：** forest plot 里 hit 向右、MAE 向左（都是"好"），validity / novelty 向左（"代价"），一眼看出这是权衡。
- **状态：** 数据已有（`c1_five_seed_effect_summary.csv`）。图需重画。

### P2 — "The verifier is blind exactly where the decision concentrates"

- **目的：** 这是 PolyGen 和 NOVA（Slide 10）共享的论点，也是 pitch 里最诚实、最有力的一页。
- **图：** 两面板。
  - A（左）：locked-tail 散点，x = RF 预测，y = 观测值，按 Q80–90 / 90–95 / 95–100 着色，**加灰色竖带标出"RF 可输出范围"**，虚线 y = x，红线标 −4.0845 边界；右下注明 Spearman、MAE、mean residual。
  - B（右）：按分位 bin 的覆盖率条形图：RF 的 90% 区间在各 bin 的实际覆盖率（风格对齐 NOVA 的 0.887 → 0.403）。
- **表 T3（支撑数据，放 backup）：**

| 行（locked-tail 分位 bin） | 列 |
|---|---|
| Q80–90 / Q90–95 / Q95–100 | n 行 · 观测均值 · RF 预测均值 · mean residual · RF 预测最大值 · Spearman ρ · 区间覆盖率 |

- **预期样子：** 散点云是一个竖条，挤在 x ≈ −4.3，y 从 −4.08 一路延伸到 −3.3，对角线与竖条几乎不相交。
- **状态：** 原始数据已有（`locked_tail_verifier_audit.csv`）；图必须重画（现有图有裁切缺陷）；bin 级覆盖率还没算。

### P3 — "The next action is the experiment that repairs the verifier"

- **目的：** 展示 Slide 11 的"改变决策"在 PolyGen 上长什么样。
- **图：** 对应 `mockups/M1_verifier_ladder.png` 的 A 和 C。
  - A：verifier 阶梯。x = 请求目标，y = verifier 估计值：RF 实线（已有，平在 −4.30）；PCFF+ MD 虚线 + 阴影带（预期，**目前为空**）。
  - C：残差分解柱：Δ₁（RF → MD，代理误差）vs Δ₂（PCFF+ → PFP，力场差）。
- **预期样子：** MD 虚线斜向上，部分点越过 −4.0845，阴影带宽度显示不确定度；Δ₁ ≫ Δ₂ 说明瓶颈在代理，而不在力场。**这是预期假设，不是预测结果。如果 Δ₁ 很小，故事要改写。**
- **状态：** RF 部分已有；MD 部分**完全是空的**。pitch 当天前跑不出来，所以 P3 讲成"下一步设计"，虚线保留并标 "planned"。

### P-backup — 冻结协议卡

- 表 T6（冻结卡）：行 = 候选集、模型版本、verifier 版本、命中判据、复制次数、收敛判据、停止规则；列 = 值 · 冻结日期 · SHA。
- 用来回应 Slide 12 的"先冻结预测"。目前缺"MD 命中判据"这一行，必须在 MD 启动前补上。

## 3.2 论文图表（Nature 子刊风格续作）

当前 Overleaf 草稿只有 6 张图，且未同步（浏览器上传被拒）。目标是 8 张主图 + 5 张表。

| # | 图 | 设计 | 状态 |
|---|---|---|---|
| F1 | 框架图 | 左：四阶段评测（interp → upper-tail → extrap → structural-OOD）；右：Act → Observe → Evaluate → Update 回路，已完成的实线、未完成的虚线 | 未画 |
| F2 | 可控性（interpolation） | Q50/Q65/Q80：目标 vs 预测、MAE 热图（已有 Fig1–3），统一风格 | 有，需统一 |
| F3 | Upper-tail | continuous 的响应曲线；binary 在 Q90/Q95 用斜线块标 unsupported | 有，需补 unsupported 标注 |
| F4 | 外推响应 | 现 Ext Fig1 重做：binary 画成 "unsupported" 标记；rerank 缺 +0.50 要标注；加入 verifier 可输出范围灰带 | 有，需重做 |
| F5 | Verifier 审计 | = P2 的 A+B，另加 full-source RF 对比（MAE 0.131） | 需重画 |
| F6 | **MD 残差阶梯** | = P3 的 A、B、C 三面板（真实数据版，见 `M1_verifier_ladder.png` 的预期形状） | **无数据** |
| F7 | 表示 / 数据消融 | 柱状 + CI：{字符 token, fragment, +PI1M 预训练（剔除 59 条重合后）} × {Q90, Q100, +0.25, +0.50} 的 frontier-crossing（以 MD 确认为准） | **无数据**，fragment 版仅是提案 |
| F8 | 决策是否改变 | = `M2_decision_change.png`：(A) top-10 MD 队列中被确认命中的数量，RF 排序 vs 校准排序；(B) 累计确认命中 vs 回路轮数 | **无数据** |

| 表 | 行 × 列 |
|---|---|
| T1 基线 | arm（binary / continuous / MolMiner / Wee）× {strict-hit, MAE, validity, novelty, Δ [CI], 语料备注} |
| T2 四阶段验收 | 阶段（interp / upper-tail / extrap / structural-OOD）× arm × {n seeds, validity, frontier-crossing 或 hit, 状态：complete / unsupported / blocked} |
| T3 Verifier 审计 | locked-tail 分位 bin × {n, 观测均值, RF 均值, residual, RF 最大值, ρ, 覆盖率}（见 P2） |
| T4 MD 漏斗 | arm × cell × {生成数, 通过 validity/novelty/support, **PCFF+ 可分型**, 已跑 MD, 已收敛, MD σ (均值, CI), 越界命中} |
| T5 跨生成器 | PolyGen / MolMiner / Wee × {连通产率（统一口径）, validity, 支持内命中率, 语料是否含 HTP-MD, held-out 与否} |
| T6 冻结卡 | 见 P-backup |

> **T4 是最关键的新表。** 它同时回答"值得算的结构有多少"（PCFF+ 可分型）和"算出来是否越界"。行设计里 "可分型" 一列不能省，因为 Top-1 的分型本身还没验证过。

---

# 4. 发表质量验收标准

下列阈值是我提议的，请按期刊和 TRI 发表流程核对。

## 4.1 每张图的通用关卡（全部必须通过）

| # | 项 | 标准 |
|---|---|---|
| G1 | 格式 | 矢量 PDF + 同名 PNG（≥300 dpi）；单栏约 89 mm / 双栏约 183 mm 宽，按目标期刊最终确认 |
| G2 | 排版 | 最小字号 ≥ 6 pt（缩放后）；无裁切、无重叠；面板字母 A–D 在面板内，不能变成标题 |
| G3 | 配色 | 色盲安全；同一 arm 在所有图里同色（现用：continuous 青 `#1b7f86`、binary 橙 `#d2691e`、其他灰） |
| G4 | 统计 | 图注写明 n（seed 数、候选数）、误差类型（SEM / 95% CI）、配对与否；n = 5 的区间标注"t 区间" |
| G5 | 完整性 | 任何失败 / unsupported / blocked 的 cell **画出来并标注**，不能静默省略（修 Ext Fig1 的 binary） |
| G6 | 可追溯 | 图中每个数字可追到 `PROVENANCE.csv` 的一行（源脚本 + 数据 SHA）；一条命令重生成 |
| G7 | 诚实 | 虚线 / 示意元素在最终稿中不得出现；"verifier-limited" 与 "generator-limited" 的措辞与证据匹配 |
| G8 | 独立可读 | 不看正文，仅凭图 + 图注能读出结论和边界 |

## 4.2 论断级关卡（比图更重要）

| 论断 | 允许说的前提 |
|---|---|
| "continuous 比 binary 更可控" | 仅限训练支持内（interp / 近边界），并同时报告 validity / novelty 代价；n=5 的 sign test 不显著要写出来 |
| "外推：零命中" | 必须同时给出 verifier 可输出范围（F5）；没有 MD 前只能说 "no candidate predicted to cross"，不得说 "cannot extrapolate" |
| "候选越过 frontier" | 需要 ≥ N 个独立 MD 复制（建议沿用 TOP1 设计的 5 replicas）、**事先登记的收敛判据**，以及 PCFF+ 与 PFP 一致或差异已量化 |
| "RF 校准有问题 / 已修复" | 需要 MD 真值与 RF 的残差表（T4）和修复后的同一指标重算 |
| "表示 / 数据是瓶颈" | 需要 F7 的对照：同协议、同评测，改变且仅改变表示或数据 |
| "决策改变了" | 需要 F8：校准前后的 top-k 队列在 MD 确认命中数上有差异，且协议预先冻结 |

## 4.3 Pitch 页的验收

- 每页只有一个主张，标题是问句或结论句，与 §4.2 的措辞一致。
- 每个数字旁标"surrogate-only / preliminary / planned"之一。
- 虚线内容必须在 slide 上写 "planned"，口头也要说明。
- 不使用 `pfp_top1_msd.svg` 作为优越性证据（single replica，NON_CONVERGED）。

---

# 5. 差距清单

| ID | 差距 | 影响的图表 | 阻塞? | 估计工作量（仅供排序） |
|---|---|---|---|---|
| A1 | **Verifier ceiling 未量化**：RF 输出范围 vs 观测范围，无 bin 级覆盖率 | P2, F5, T3 | 否，数据已有 | 小，约半天 |
| A2 | **没有任何外推候选的 MD 观测** | P3, F6, T4, F7, F8 | **是**，核心 | 大，数天到数周，取决于资源 |
| A3 | PCFF+ 对 Top-1 分型未验证；可分型漏斗未做 | T4 | 阻塞 A2 | 中 |
| A4 | Hisa review 的 9 处代码正确性问题未清（cNE `range(10)`、NaN 相关、160.0 阈值 KeyError、ion-pairs 越界等） | 所有 MD 数值 | **阻塞 A2** | 中 |
| A5 | MD 命中判据未预登记 | T6, F6, 论断关卡 | 阻塞 A2 的解释 | 小，但必须在跑之前 |
| A6 | 无"下一步行动"的定量度量 | P3, F8 | 否 | 中 |
| A7 | 无更新 / 主动学习闭环 | F8 | 依赖 A2 | 大 |
| A8 | 严格同支持集的 MolMiner / Wee 重训未做；Wee 未入 C1 | T1, T5 | 否 | 大（依赖外部） |
| A9 | fragment 表示 / PI1M 预训练 / Ohsaki 数据均未实验 | F7 | 否 | 大；PI1M 近似重复检查未做，许可由 TRI 法务判断 |
| A10 | Structural-OOD blocked（缺 scaffold / family 标注） | T2 | 否 | 未知 |
| A11 | 图缺陷（Ext Fig1、Fig4）与风格未统一；Overleaf 图未同步 | 全部 | 否 | 小到中 |
| A12 | 文档债务：`EXTRAPOLATION_PROGRAM_FRAMEWORK.md` 等部分已过期；`molminer-comparison/` 未提交；grid 3000/0.8 未并入、3000/1.2 未跑 | F2–F4 引用 | 否 | 小 |
| A13 | 17 页稿无 PolyGen 页，且 PolyGen 在闭环中的角色未写入讲稿 | pitch | 否 | 小 |

---

# 6. 端到端执行策略

原则：**先修"不需要新实验"的缺陷，再做阻塞项，最后做增量。** 每一步都有产出和验收，不用等下一步。

## Stage 0 — 本周内（pitch 之前，无需 MD）

1. **A1：verifier ceiling 分析。** 用 `locked_tail_verifier_audit.csv` 算 §3.1 P2 的 T3（bin 级 RF 范围、覆盖率、ρ），并对 full-source RF 重做一遍。**验收：** T3 表完成；结论明确写成 verifier-limited / generator-limited / 无法区分三选一，并给证据。
2. **A11：重画 P1、P2 图**（Ext Fig1、Fig4、C1 的重做）。**验收：** §4.1 的 G1–G8 全过。
3. **A13：写 P1–P3 的讲稿**，P3 明确标 "planned"。**验收：** 每页措辞符合 §4.2。
4. **A5：预登记 MD 命中判据**（候选集、复制数、收敛判据、命中阈值、停止规则），写成冻结卡 T6，并记 SHA。**验收：** 冻结卡在任何 MD 数据出来之前存在。

## Stage 1 — 下 1–2 周（解除 MD 阻塞）

5. **A4：修 Hisa review 的 9 处问题**，附回归测试。**验收：** Hisa 复核通过；旧 pilot 的结论按新代码重算并说明变化。
6. **A3：PCFF+ 分型漏斗。** 先 PEO + LiTFSI 阳性对照、磷体系阴性对照，再对每个 arm × cell 抽样分型（无 MD）。**验收：** T4 的"可分型"列填满，附 missing-parameter 报告。
7. **A12：文档与仓库债务**（更新 framework 文档、提交 molminer-comparison、并入 grid 3000/0.8），顺手同步 Overleaf 图（需 Yi 一次性授权 token，我不能代做）。

## Stage 2 — 2–4 周（核心新证据）

8. **A2：分层 MD 验证。** 每个外推 cell 取 RF 最高、高不确定度、随机对照各若干候选；先 PCFF+ 为主，PFP 为二级对照；每结构 5 replicas。**验收：** T4 完整；F6 三面板真实数据版；每个结果按收敛判据标 converged / non-converged，不收敛的不进主结论。
9. **A6：行动度量。** 以"MD 确认命中数 / 成本"定义决策价值，对比 RF 排序与校准排序。**验收：** F8(A) 真实数据版。

## Stage 3 — 之后

10. **A7：** 残差校准后的主动学习一轮，F8(B)。
11. **A9、A8：** fragment 表示小规模验证（同一外推 benchmark），PI1M（先剔除 59 条重合，再做近似重复检查）；MolMiner / Wee 严格重训。**验收：** F7、T5。
12. 用 F1–F8 + T1–T6 组装 Overleaf，按 PROVENANCE 打包交付。

## 停止与降级规则

- 若 Stage 2 的 MD 显示 RF 并非系统性低估（Δ₁ 小）：F6 / P3 的"verifier 修复"叙事作废，改写为"生成器确实没有越界"，这也是有效的负结果。
- 若 MD 资源不到位：pitch 保持 P1–P3（P3 为 planned），论文降为"surrogate-only 外推基准 + verifier 审计"这个较窄的贡献，并在 Limitations 里写清。

---

# 7. 需要你确认的点

1. 这份分析把 PolyGen 当作 **Improve 回路案例**（pitch 3 页 + backup）。如果你想的是整个论文，而不是 pitch，§3.2 和 §4.2 已覆盖，但 pitch 部分可以删。
2. 目标期刊和图尺寸（Nature 子刊 vs 其他）确认后，G1/G2 的数值才能定死。
3. MD 资源（Matlantis / medea-2026）的可用窗口，决定 Stage 2 是否能在 midterm 前启动。

示意图：![[Projects/PolyGen-reproduction/mockups/M1_verifier_ladder.png]]

![[Projects/PolyGen-reproduction/mockups/M2_decision_change.png]]

![[Projects/PolyGen-reproduction/mockups/M3_hypothesis_state.png]]
