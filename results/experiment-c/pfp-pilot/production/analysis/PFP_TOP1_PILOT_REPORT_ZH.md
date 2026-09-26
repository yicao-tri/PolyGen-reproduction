# PolyGen continuous vs binary：PFP top-1 pilot 结果

## 结论摘要

两条 200 ps PFP 轨迹和 HTP-MD-compatible 分析已通过 41/41 项证据门禁。
本 pilot 中 cNE0 电导率较高的 arm 为 **continuous**；proxy 与 PFP 的两候选排序一致性为 **True**。
该结果仅是单 replica、200 ps 的技术可行性结果，标签为 `NON_CONVERGED_SMOKE_ONLY`；PFP-MD 不是实验真值，不能据此宣称模型优越。

## 候选与结果

| arm | canonical p-SMILES | proxy log10(S/cm) | PFP cNE0 (S/cm) | PFP log10(S/cm) | residual | D_Li (cm2/s) | D_TFSI (cm2/s) | t+ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| continuous | `O=C(OCCCOCCO[*:1])[*:2]` | -3.778974 | 3.0497e-03 | -2.515744 | +1.263230 | 3.4868e-06 | 5.7749e-06 | 0.3687 |
| binary | `O=C(OCCCOCCCCO[*:1])[*:2]` | -3.830584 | 1.1555e-03 | -2.937245 | +0.893339 | 2.5418e-06 | 3.5715e-06 | -0.2206 |

### 离子迁移诊断图

![Continuous 与 binary top-1 的 Li+/TFSI− multi-origin MSD；灰色为 40–120 ps 斜率诊断时间窗。](figures/pfp_top1_msd.svg)

图中连续值候选的 Li+ 与 TFSI− MSD 均更快增长；该图是扩散诊断，正式 HTP-MD diffusivity 仍使用 40 ps discard 后 160 ps 的 endpoint MSD 定义。

### 累积轨迹长度敏感性

| arm | 20 ps | 40 ps | 80 ps | 120 ps | 160 ps |
|---|---:|---:|---:|---:|---:|
| continuous | -2.0926 | -2.2643 | -2.2238 | -2.4054 | -2.5157 |
| binary | -2.6434 | -2.7549 | -2.7191 | -2.8549 | -2.9372 |

表中为从 40 ps production 时刻开始累积的 cNE0 log10(S/cm)。若随窗口仍有明显漂移，即使 MSD 拟合 R2 很高，也不能视为科学收敛。

Residual 固定定义为 `PFP-MD log10 conductivity - proxy log10 conductivity`。

## 配对对比

- continuous − binary PFP log10 conductivity：+0.421501
- continuous − binary proxy log10 conductivity：+0.051610
- continuous − binary residual：+0.369891
- continuous − binary Li diffusivity：9.4493e-07 cm2/s
- continuous − binary TFSI diffusivity：2.2034e-06 cm2/s

以上为一个 rank-pair 的描述性差异，不是统计检验。

## 轨迹与质量诊断

| arm | frames | analysis window | mean T (K) | COM displacement (A) | drift-corrected D_Li | endpoint/slope R2 (Li/TFSI) |
|---|---:|---:|---:|---:|---:|---:|
| continuous | 2001 | 160.0 ps | 349.71 | 0.00726 | 3.4879e-06 | 0.999/0.978 |
| binary | 2001 | 160.0 ps | 349.28 | 0.00859 | 2.5421e-06 | 0.996/0.991 |

## 与原文设计的差异

原 PolyGen 验证采用 PCFF+、50 对 LiTFSI、1.5 mol/kg、5 ns production 和每候选 5 replicas；本 pilot 使用 PFP v8.0.0、10 对 LiTFSI、200 ps 和 1 replica。
当前 continuous/binary 离散 molality 分别约为 1.5000/1.4527 mol/kg；3.2% 浓度差和较小 cell 均可能影响 paired contrast。
扩展 top10 前应使用浓度匹配到 ±1% 的较大整数 cell，并在赋速后显式清零线性动量。正式模型比较至少需要 5 replicas × 5 ns；小子集可扩到 50 ns 检查收敛。

## 证据状态

- validator：`passed`（41/41）
- paired summary：`succeeded`
- scientific convergence：`NON_CONVERGED_SMOKE_ONLY`
- 所有 headline 数值均来自 `analysis.json` 与 `paired_summary.json`，未人工抄写。
