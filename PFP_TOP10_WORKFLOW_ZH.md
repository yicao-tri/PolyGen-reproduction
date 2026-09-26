# PolyGen continuous vs binary：PFP top-10 验证 workflow

## 1. 研究问题与边界

主问题：在完全相同的 PFP 构型生成、松弛、温度、浓度、轨迹长度和
HTP-MD 分析定义下，continuous 模型推荐的高电导候选是否比 binary 模型推荐的
候选具有更高的 PFP-MD cluster Nernst–Einstein（cNE0）电导率？

主 estimand 为候选 rank 配对后的
`continuous - binary` 的 `log10(cNE0 conductivity / S cm-1)`。候选级 proxy residual
固定定义为 `PFP-MD log10 conductivity - proxy log10 conductivity`，正值表示 proxy
低估 PFP pilot，负值表示 proxy 高估。

PFP-MD 是计算验证，不是实验真值。单个 200 ps replica 只回答“端到端技术链路能否
工作”，不得用于宣称模型优越或电导率收敛。

## 2. 候选冻结

每个模型分别从已冻结的 `continuous_top20.csv` 和 `binary_top20.csv` 选择前 10：

1. 分子必须通过 canonicalization、重复单元连接、元素覆盖和 PFP 支持检查。
2. 排名沿用 PR #4 已冻结的 conservative score；它同时惩罚 proxy target error 和
   uncertainty，不根据 PFP 结果重新排序。
3. 同一 arm 内 canonical SMILES 去重；跨 arm 相同结构保留，但标为 shared candidate。
4. topology/packing 失败只允许按预先冻结的下一名递补，并保留失败证据，禁止看过
   PFP 数值后换候选。

当前 top-1 pilot：

| arm | canonical p-SMILES | proxy log10(S/cm) | uncertainty |
|---|---|---:|---:|
| continuous | `O=C(OCCCOCCO[*:1])[*:2]` | -3.7789737 | 0.1371929 |
| binary | `O=C(OCCCOCCCCO[*:1])[*:2]` | -3.8305838 | 0.1404205 |

## 3. 原文与 PFP 对照

原 PolyGen/HTP-MD 全量条件：PCFF+；50 对 LiTFSI；约 150 个 backbone atoms/chain；
1.5 mol/kg；NVT/NPT equilibration；353 K NVT production；2 fs；5 ns；每个候选 5 个
replicas；HTP-MD cNE0 分析。50 ns 才被前序工作作为较接近收敛的参考。

PFP pilot 替代项：PFP v8.0.0/PBE、FIRE、Langevin NVT、1 fs、200 ps、1 replica。
分析仍保持 HTP-MD 定义：TFSI N 原子 MSD、3.4 Å Li/O/S/N cluster population、
cNE0。PFP 与 PCFF+ 不是同一势能面，所以二者只能比较在各自统一协议内的候选排序；
PFP residual 不能解释为 PCFF+ prediction error 或实验误差。

## 4. Stage A：top-1 端到端 pilot（当前运行）

- 每个 arm：3 条 polymer chains、10 对 LiTFSI；353 K。
- FIRE：最大 200 steps，门禁 `max force <= 0.2 eV/A`。
- NVT：Langevin，1 fs，200,000 steps，200 ps；每 100 steps 保存一帧。
- seed：20260924；两 arm 同一 seed 与 runner。
- 前 40 ps discard，后 160 ps 分析。
- 当前 top-1 runner 的 ASE Langevin 使用默认 `fixcm=True`，但初始 Maxwell-Boltzmann
  velocity 未显式调用 `Stationary`；最终必须同时报告全体系 COM 位移和 drift-corrected
  diffusivity 诊断，HTP 未修正 endpoint 仍为主定义。
- 必需产物：source/relaxed structure、trajectory、energy-temperature log、run summary、
  progress heartbeat、MSD curve、population matrix、analysis JSON、paired CSV/JSON、hash。

技术 PASS 门禁：

1. 两个 driver 正常退出并各有 2001 帧；
2. 坐标、能量、温度和分析值均有限；
3. cell 恒定、每帧离子 population 守恒 20；
4. relaxed force 门禁通过；
5. 两 arm 协议字段逐项一致；
6. endpoint 与 multi-origin MSD 同时报告，不用后者替换论文定义；
7. 结果强制标为 `NON_CONVERGED_SMOKE_ONLY`。

## 5. Stage B：top-10 screening

只有 Stage A 技术门禁全过才构建其余 18 个候选。先为每个候选执行 FIRE + 1 ps
preflight；全部通过后再做 200 ps 单 replica screening。该阶段用于发现 PFP 不支持、
packing 不稳定和明显低迁移候选，不做显著性检验。

从 top10 起 runner 在赋速后显式执行 `Stationary(..., preserve_temperature=True)`，与原
LAMMPS `velocity ... mom yes` 对齐，并把 `zero_linear_momentum=true` 写入 run summary。

有限体系必须修正当前 top-1 的离散浓度偏差：按各 polymer molecular weight 选择足够大
的 chain/ion integer cell，使每个体系均在 1.5 mol/kg 的 ±1% 内，并尽量固定 50 对
LiTFSI。若算力不允许，浓度差必须进入模型协变量，不能把 rank 差异直接归因于生成模型。

粗略 PFP 预算按当前实测约 0.08–0.09 s/step：20 个候选 × 200,000 steps 约
90–100 GPU-hours；并行度必须根据 Matlantis 配额冻结。每个 job 使用独立 output root、
tmux/session、固定 seed、进度文件和 SHA256 manifest。

## 6. Stage C：可比较的确认实验

从 Stage B 预先按 arm 内 rank 选择 top candidates，不能按观察到的噪声挑赢家。
最低确认设计为每候选 5 个独立 amorphous packings/seeds × 5 ns；若要接近原 HTP-MD
的“converged”定义，应对小子集扩展到 50 ns。配对单元为 `(rank, packing_seed)`，模型 arm
为固定效应，candidate 与 packing 为重复结构。报告：

- 每候选与每 arm 的 log10 cNE0 conductivity、Li/TFSI diffusivity、transference；
- proxy residual 和 rank correlation；
- continuous-binary 配对差、bootstrap 95% CI；
- family-wise primary endpoint 仅一个，候选级探索结果做多重比较校正；
- 轨迹长度敏感性（200 ps、1 ns、5 ns）及 replica 方差。

## 7. 决策规则

- Stage A PASS：说明 ARC→Matlantis→PFP→HTP-MD adapter 技术可用，不说明科学结论成立。
- 扩展 top10：两 arm 均 PASS，分析守恒，且没有系统性 PFP 元素/拓扑失败。
- 宣称排序改善：必须来自 Stage C；continuous-binary CI 不跨 0，且结论对浓度匹配和
  trajectory-window sensitivity 稳健。
- 若 PFP 与 proxy 大幅偏离：先检查浓度、密度、扩散 regime、cluster population、
  potential domain 和 replica variance，再讨论 proxy calibration。

## 8. 已知混杂因素

- 当前 top-1 的离散盐浓度为 1.5000 vs 1.4527 mol/kg，约 3.2% 差异；只能用于 pilot。
- 当前体系 10 对离子，小于原文 50 对，finite-size/cluster sampling 更强。
- PFP 没有显式复现 PCFF+ 的 0.7 TFSI charge scaling；cNE 分析中的 ±1 是输运计数，
  不是 PFP 势能的显式部分。
- 单一 packing 与单一 velocity seed 无法分离 amorphous initialization noise。
- 200 ps 通常不足以进入稳定扩散区；高 R2 也不能单独证明扩散收敛。
