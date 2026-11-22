---
title: Pitch × PolyGen gap analysis — evidence package
date: 2026-10-16
status: active
tags: [project/polygen-reproduction, project/ARC-Suite, type/evidence-report]
---

# Research question

Pitch 的 Improve 回路要求 `Act → Observe → Evaluate → Update`。PolyGen 当前证据已经完成 Act 和 surrogate Evaluate，但还没有把外推候选送入可比较的物理 Observe，也没有 residual calibration 或 Update。因此当前最稳妥的贡献不是“生成器已经实现物理外推”，而是：**在冻结的 HTP-MD/Q80 设定下，continuous conditioning 改善了支持集内的目标控制；当目标越过训练边界时，blind RF 无法分辨 locked-tail 决策区域，所有 RF-gated frontier crossing 均为 0，物理原因仍待 MD 判别。**

# Inputs and verified baseline

真实 source 为 6,024 行 HTP-MD。Q80 训练边界为 `-4.084499111` log10(S/cm)，训练集 4,819 行，locked Q80–Q100 为 1,205 行。五 seed C1 的 observed continuous-minus-binary effect 为：strict hit `+0.0193`（95% t CI `[+0.0064,+0.0322]`）、target MAE `−0.0609`（`[−0.0728,−0.0490]`），同时 validity `−0.0673`、novelty `−0.0720`。这些数字来自 paired seed summary，不能解释为独立 candidate 复制。

外推阶段使用 3 arms × 5 seeds × 4 查询点。continuous、binary、unconditional+rerranking 的 blind-RF frontier-crossing predicted hit rate 在四个查询点均为 0；binary 的 Q90/Q100/+0.25/+0.50 cells 因固定 −4.0 label 在 Q80 截断后 single-class，属于 structural unsupported，而不是可与 continuous 的 0 进行同义比较的失败质量分数。

# Verifier ceiling

Locked-tail audit 的 1,205 个真实 source rows 显示 blind RF 的 MAE `0.310`、mean observed-minus-predicted residual `+0.310`。分 bin 的预测均值分别约为 −4.278、−4.268、−4.246，而 observed means 从 −4.055 延伸到 −3.820；blind RF 的预测范围挤在约 −4.45 到 −4.19。full-source RF 的 post-hoc MAE 为 `0.131`，但它看过 locked-tail labels，不能替代 leakage-free endpoint。nominal tree-SD coverage 只是诊断，不是 calibrated uncertainty。

因此，P2/F5 支持 “verifier-limited in the decision region” 的表述；它不支持 “generator-limited” 或 “generator can never extrapolate”。

# Figures and tables

## Pitch pages

![[assets/figures/P1_decision_value_tradeoff.png]]

> **P1.** C1 的局部 target response、配对 seed 对比、连续−二值 effect forest，以及 binary extrapolation structural unsupported 状态。全部为 observed CSV 数据。

![[assets/figures/P2_verifier_blind_locked_tail.png]]

> **P2.** Locked-tail verifier audit。每点是一个真实 source row；右图是 nominal tree-SD interval diagnostic。full-source RF 以斜线表示，且仅为 post-hoc audit。

![[assets/figures/P3_verifier_repair_experiment.png]]

> **P3.** Real RF stage + observed but non-converged PFP top-1 smoke anchor + planned/synthetic PCFF+/PFP extrapolation ladder. Dashed components are not results.

## Manuscript inventory

| Artifact | Status | Main use |
|---|---|---|
| F1 | observed status map | four-stage benchmark + closed loop |
| F2 | observed | in-support interpolation |
| F3 | observed | upper-tail with unsupported cells |
| F4 | observed | extrapolation RF-only response |
| F5 | observed | verifier audit; alias of P2 |
| F6 | mixed observed/planned | residual ladder; MD queue remains missing |
| F7 | synthetic placeholder | representation/data ablation plan |
| F8 | synthetic placeholder | decision-change / active-learning plan |
| F9 | observed | existing nine-configuration generation-grid audit asset |
| T1–T6 | observed + status/proposal fields | baseline, stages, verifier, MD funnel, generators, freeze card |

Every figure has PNG/PDF/SVG and a nearby caption in `assets/figures/FIGURE_CAPTIONS.md`. Tables are in `assets/tables/`.

The existing generation grid is also preserved as F9: all 9 planned configurations are present (1,000/2,000/3,000 steps × temperatures 0.8/1.0/1.2), with 90 arm–seed sample files and 27,000 raw rows. Its plotted conductivity is frozen-RF prediction; it does not close the physical-validation gap.

Independent read-only reruns passed the prediction-stage extrapolation verification (`6,000` candidates, `60` cells, `200` proposed MD rows). The PFP top-1 evidence-chain validator passed `39/41` checks; the two failed checks are missing trajectory files referenced by the production summaries. The surviving PFP analysis is therefore retained only as a smoke anchor, not as converged physical evidence.

The data-provenance audit adds two real safeguards. The HTP release has `59/6,024` exact canonical overlaps with the external PI1M source (46 in train, 11 in locked Q80–Q95, 2 above Q95 or unassigned). A systematic 1-in-10 PI1M Morgan screen found 21 sampled candidates at Tanimoto ≥0.85, including 14 non-exact fingerprint-near rows; this is exploratory and not a full-source absence proof. Separately, the released-random split has 312 train–validation canonical overlaps, while the exact structure-disjoint split has zero. The latter is a row-level leakage audit, not scaffold/family structural-OOD evidence.

The Hisa code review is now package-local regression complete for the seven code-correctness items, including dynamic cNE population traversal, nullable rendering, boundary-safe convergence tables, non-degenerate cNE testing, full orthorhombic checks, dynamic grid totals, and the corrected cross-target C1 correlation. Canonical merge and the two process/policy items remain open.

# Missing evidence and next experiment

The hard blocker is not a plotting issue. `top1_readiness_audit.json` records failed PCFF+ parameter coverage and an ARC route that defaults to PFP rather than paper-equivalent PCFF+. The extrapolation `candidate_selection_for_md.csv` explicitly says `not_run_proposed_only`; the 60-structure C1 manifest is `PLANNED_NOT_RUN`. The next safe execution sequence is:

1. Resolve Hisa review items and add regression tests.
2. Run PCFF+ positive/negative parameterization controls and produce a missing-parameter report.
3. Freeze T6 with owner approval before any new physical data.
4. Execute short, blinded, common-protocol MD on a stratified queue; only escalate under the predeclared gate.
5. Add five-replica convergence-qualified structure-level results to T4/F6.
6. Fit RF→MD residual calibration and recompute the top-k decision queue for F8.

No remote MD submission was launched from this package because the canonical contract still marks MD as not run by contract, PCFF+ coverage failed, and the external force-field/provider boundary is unresolved. A quiet heartbeat monitor is registered separately for the exact canonical candidate/manifest state; it must stay quiet while unchanged and must not submit/restart/delete anything.

# Reproducibility

The producing script is `evidence/scripts/build_gap_package.py`. It reads only the canonical root and writes the package directory. The source snapshots, data snapshots, exact commands, provenance ledger, and package manifest are in this folder. Canonical `sources/` and the canonical project root are not modified by this package.
