# Continuous-vs-Binary Extrapolation Benchmark

## Purpose

Test whether continuous conductivity conditioning provides a real advantage over binary high/low conditioning for interpolation, upper-tail targeting, and extrapolation beyond the observed HTP-MD conductivity frontier.

The benchmark must distinguish model control from surrogate self-confidence. RF/GNN predictions alone are screening signals; claims about extrapolation require locked holdouts and later MD validation.

## Common rules for all four region tasks

- Repository: `/Users/yicao/Documents/ARC/PolyGen-reproduction`.
- Preserve the existing PR4 evidence and PR6 artifacts. Do not rewrite historical results.
- Reuse the already trained binary and continuous pipelines where possible.
- Use identical seeds, generation budgets, decoding settings, candidate filters, and reporting schemas across arms.
- Freeze the data split before fitting, fine-tuning, RF/GNN models, thresholds, or selecting candidates.
- Keep a machine-readable manifest for every split, model checkpoint, random seed, target, generated candidate, filter decision, prediction, and uncertainty.
- Do not pool candidates across model family, split, checkpoint, temperature, training budget, salt/formulation, or target regime.
- Report validity, novelty, uniqueness, support, uncertainty, target error, hit rate, and diversity for every arm/regime.

## Four regions

### 1. Interpolation

Use targets inside the training conductivity support, for example Q50, Q65, and Q80. Measure target error, monotonicity of achieved prediction versus requested target, and whether continuous conditioning provides finer control than binary high/low conditioning.

### 2. Upper-tail

Train below the highest tail while retaining an internal boundary evaluation. Use a predeclared split such as training through Q80 and evaluate targets near Q80–Q95. This tests control close to the frontier without claiming true extrapolation.

### 3. Extrapolation

Hold out the upper tail completely. A default protocol is training on `log10(conductivity) <= Q80`, locking Q80–Q100 away from generator training, surrogate fitting, hyperparameter tuning, and threshold selection. Query Q90, Q100, `train_max + 0.25`, and `train_max + 0.50` log units. Compare continuous conditioning against binary high/low and unconditional generation plus reranking. The decisive endpoint is MD-confirmed improvement beyond the locked training maximum.

### 4. Structural OOD

Create scaffold/family-grouped splits so close polymer analogues cannot cross train/test. Reuse the same target curve as the other regions. Report target control, chemical distance, support, uncertainty, and MD success/failure separately from ordinary property-tail extrapolation.

## Model arms

1. Continuous conditioning using the existing trained pipeline.
2. Binary high/low conditioning using the existing trained pipeline.
3. Unconditional generation plus the same frozen surrogate/reranking baseline, if the existing pipeline supports it without introducing a new model family.

Use matched generation counts and seeds. The binary arm may receive only its binary label; it must not be given the continuous target curve.

## Candidate selection for MD

Do not select only the single highest RF score. For each region and arm, stratify candidates across high predicted value, low/high uncertainty, novelty/support, and structural distance. Record the exact acquisition rule and candidate IDs.

Default staged budget:

- Tier 1: 48–96 candidates across regions and arms for short MD screening.
- Tier 2: 12–24 candidates for longer production runs with at least five replicas where feasible.

Continuous and binary must receive symmetric MD budgets within each region.

## Required metrics

- Target error and strict-hit rate for interpolation/upper-tail.
- Fraction of candidates whose MD value exceeds the locked training maximum for extrapolation.
- Best confirmed MD conductivity and improvement over the locked maximum.
- Calibration of RF prediction and uncertainty against MD.
- Residual `MD_log_sigma - RF_log_sigma` by target distance, support, uncertainty, and structural distance.
- Validity, novelty, uniqueness, diversity, support, MD failure rate, and force-field coverage.
- For structural OOD, nearest-neighbour distance and scaffold-held-out performance.

## Manager acceptance gates

The manager must not approve an experiment as complete unless:

1. the split and target manifest are frozen and reproducible;
2. no locked holdout information leaked into training, tuning, filtering, or selection;
3. binary and continuous used matched budgets;
4. every generated candidate has traceable predictions and filter decisions;
5. empty or unsupported target cells are reported rather than silently dropped;
6. claims separate surrogate evidence from MD evidence;
7. the result includes uncertainty, failure, and negative-control reporting.

## Next-step MD and residual active learning plan

After the prediction phase, the manager must produce a concrete candidate table for review before MD begins. It must include region, arm, target, candidate ID, structure, RF prediction, uncertainty, support, novelty, acquisition score, and reason for selection.

The default acquisition for the next round is a calibrated combination of expected high conductivity, uncertainty, novelty, and expected information gain, with penalties for low support and simulation infeasibility. After MD, compute residuals and fit a discrepancy/calibration model. The next generator round must use the residual model to reduce systematic overprediction in OOD regions while preserving exploration of candidates with informative uncertainty.

## Deliverables

- `splits/` or equivalent frozen split manifest;
- per-region generation and prediction tables;
- model/checkpoint/seed manifest;
- candidate-selection table for MD;
- region summary JSON and human-readable report;
- manager acceptance report;
- proposed MD execution plan;
- residual active-learning plan after MD results exist.

## Scientific claim boundary

The primary claim is conditional: continuous conditioning improves validated exploration across a defined interpolation-to-extrapolation benchmark under the frozen data representation, surrogate, and MD protocol. It is not a claim of experimentally measured conductivity until an experimental database match or laboratory measurement supports it.

最关键的实验设计
不要直接拿全部训练数据训练，然后要求一个更高 target，再用同一个 RF 打分。这只能证明 RF 自己相信自己。
应建立一个预注册的 interpolation-to-extrapolation benchmark：
区域	训练数据定义	查询 target	目的
Interpolation	保留中间 conductivity 区间	多个内部连续 target	测试控制精度与单调性
Upper-tail	训练到 Q80/Q90	接近 Q90–Q95	测试靠近边界时的控制
Extrapolation	训练集中移除最高 10–20%	高于训练上界的 target	测试真正外推
Structural OOD	按 polymer scaffold/family 分组切分	同样的 target grid	防止结构近邻泄漏


具体做法：
1. 用 HTP-MD 数据建立严格的高值尾部 holdout，例如训练集只保留 logσ ≤ Q80。
2. 把 Q80–Q100 完全锁起来，不能参与 generator、RF 或调参。
3. continuous、binary、unconditional+reranking 三个模型使用相同训练样本、参数预算、随机种子和生成数。
4. continuous 查询一条 target curve，例如：
Q50, Q65, Q80, Q90, Q100, train_max + 0.25, train_max + 0.50
5. binary 只能使用其 high label；它不能声称精确实现这些不同外推强度。
6. 对锁起来的高值样本与新做的 MD 结果统一做判断。
这样可以分开回答三个问题：
- continuous 是否更精确地命中内部 target？
- continuous 是否在高值边界更平滑、更单调？
- continuous 是否真的更容易找到超过训练上界、且被 MD 证实的候选？
MD 不应只验证 top-1
最容易出现 winner’s curse 的地方就是“每组只取 primary rank #1 去做 MD”。建议两阶段：
阶段	规模	目的
Tier 1 screening	48–96 candidates，短 MD	覆盖不同 target、arm、OOD 程度和不确定性
Tier 2 confirmation	12–24 candidates，≥5 replicas、更长 production	验证真正的高电导候选与误差


每个 target regime 都应让 continuous 与 binary 有对称预算。例如：
4 个 target regime
× 2 个 arms
× 每格 6 个候选
= 48 个 Tier 1 candidates
候选不能只按 RF prediction 排序。更好的选择是分层抽样：
- 高 RF、低 uncertainty；
- 高 RF、高 uncertainty；
- 高 novelty / 远离训练集；
- 靠近训练集的正对照；
- 每个区域都包含 continuous 和 binary。
这会让你看到：continuous 的优势是“真实更高 conductivity”，还是仅仅“更会骗 RF”。
residual-driven active learning 是最有价值的部分
定义：
residual = logσ_MD − logσ_RF
随后建立一个 residual / discrepancy model，输入包括：
- generated repeat-unit descriptors；
- target conductivity；
- RF mean 与 uncertainty；
- training-support score；
- nearest-neighbor similarity；
- functional groups；
- arm：continuous / binary；
- MD 状态和失败原因。
然后不再只优化：
maximize RF prediction
而是优化一个经过 MD 校准的 acquisition：
high calibrated conductivity
+ high expected improvement
+ informative uncertainty
+ structural novelty
− infeasible / unstable simulation risk
这会产生两个非常强的结果：
1. 你可以画出 RF 在不同 extrapolation distance 下的 calibration curve；
2. 你可以证明 MD feedback 让下一轮生成更少走向“高预测、低真实”的假阳性区域。
这里的本质不是让 residual 越大越好，而是学习 residual 的结构性来源，并让下一轮更好地校准高风险外推。
与公开实验数据库的关系
PEDatamine 可以作为“外部实验锚点”，但不能直接和 HTP-MD/RF 数值混在同一张性能榜上。
正确用法是：
- 严格匹配或分层 polymer chemistry、salt、salt concentration、temperature；
- 对 generated polymer 做 exact match、fingerprint similarity、scaffold/family similarity；
- 标记哪些 generated candidates 已有实验近邻；
- 比较实验数据和 MD/RF 的相对排序、区间覆盖与系统误差；
- 把没有实验近邻的高性能候选定义为真正的 chemical extrapolation candidates。
PEDatamine 包含 655 个 polymer–anion–salt formulation 和约 5,225 条实验 conductivity measurements，是最合适的外部实验参考。相关数据库论文
当前 SOTA 与你的差异化
最接近的工作已经表明：binary high/low conditional generation 加 MD 可以找到超过训练集最高 conductivity 的候选；一项 npj Computational Materials 工作对 100,000 个高标签生成物筛选，并对 top candidates 做多 replica MD，报告部分候选超过训练数据最高值。npj Computational Materials, 2025
另一个相关 polymer-electrolyte framework 已提出 conditional generation + MD feedback 的闭环。Digital Discovery, 2025
但你有机会做出明确差异：
现有工作常见做法	你的可发表贡献
high/low binary prompt	连续 target-response 曲线
生成后由同一 surrogate 排名	严格 tail holdout + MD 盲测
证明“找到高分子”	定量比较 interpolation、boundary、extrapolation
top-hit MD validation	按 OOD、uncertainty、arm 分层的 MD 验证
MD 加回训练集	residual-aware discrepancy learning
只报告最高性能	解释何时、为何 continuous 能或不能外推


Nature 子刊级 pitch
标题方向：
Continuous property conditioning enables calibrated extrapolation in polymer-electrolyte generation

摘要核心句可以是：
We show that continuous conductivity conditioning is not merely a finer alternative to binary high/low prompting: when coupled to uncertainty-aware molecular dynamics feedback, it provides a controllable route from interpolation to validated extrapolation beyond the observed polymer-electrolyte conductivity frontier.

文章的主图逻辑：
1. 连续条件 vs binary 的 target-response 曲线；
2. 严格 holdout 下的 interpolation、upper-tail、extrapolation benchmark；
3. 两种模型生成候选的结构/OOD 空间与 MD hit rate；
4. RF–MD residual 随 OOD distance 和 target 增长的图；
5. 一轮或多轮 active learning 后，calibration、validated hit rate、best confirmed conductivity 的改善；
6. 与 PEDatamine 实验空间的 mapping：已知化学、近邻化学、无实验先例化学。
最重要的 claim 应限制为：
Continuous conditioning improves validated exploration beyond a defined conductivity boundary under this data representation, MD protocol, and polymer-electrolyte formulation.

不要写成“发现了 experimentally superior polymer”，除非最终有合成/EIS 数据。
我认为这是可行且值得做的路线。它把你现有工作从一个条件生成对比，提升成“如何让生成模型可信地探索未知性能区域”的方法论文。
