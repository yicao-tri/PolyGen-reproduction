# 连续值 top-1 候选的 PolyGen 对齐 MD 验证设计

更新日期：2026-09-24

## 结论先行

- PR #4 已合并，并建立了 8 阶段研究蓝图。当前处于 S2（physical-validation readiness），尚未达到 S3（blinded common-protocol MD）的启动门槛。
- 冻结的连续值 top-1 候选为 `O=C(OCCCOCCO[*:1])[*:2]`；原始生成字符串为 `O=C([Au])OCCCOCCO[Cu]`，来自 continuous arm、seed 202、target −3.0。
- ARC Suite 到 Matlantis 的执行通路可访问且已有成功作业；但 ARC 当前默认使用 Matlantis PFP，现有 conductivity 分析是基于 Li 自扩散的普通 Nernst–Einstein 近似，不是原文的 LAMMPS + PCFF+ + cluster Nernst–Einstein 方法。
- 仓库中的 PolyGen 示例 LAMMPS 文件提供 PCFF+、Li/TFSI 模板、353 K、2 fs 和平衡/生产流程，但示例 metadata 是 3.0 mol/kg、10 ns；原文是 1.5 mol/kg、5 ns。示例还只包含已经参数化的 PEO 体系，不能自动为 top-1 生成 PCFF+ 参数。
- 已生成确定性的 top-1 methyl-terminated DP15 链（152 个重原子），并完成 3 条链 + 10 对 LiTFSI 的 1.500015 mol/kg 初始体系打包；公开 HTP-MD 的 cluster Nernst–Einstein 核心分析测试也已 26/26 通过。
- 因此现有资产足以设计、构建和分析实验；kozo-dev 上也已经验证可原生运行带 `MOLECULE + CLASS2 + KSPACE` 的 LAMMPS。**尚不足以启动与原文一一对应的 top-1 电导率 MD**。唯一剩余的物理输入缺口是 top-1 的完整 PCFF+ typing/charges/topology；此外还需把已验证的 LAMMPS runtime 接入 ARC 作业记录。不应把 ARC/PFP 数值与原文 binary 候选作物理比较。

## 1. 原文完整实验设计

### 1.1 数据与生成模型

1. 使用包含 6,024 个无定形 polymer-electrolyte 体系及 MD 离子输运标签的 HTP-MD 数据集。
2. 用带两个连接端点的 p-SMILES 表示重复单元，并进行字符级 tokenization 和定长 padding。
3. 比较 minGPT、1D diffusion 和 diffusion-LM。
4. 无条件生成以 novelty、uniqueness、validity、synthesizability、similarity、diversity 六指标评价；网格搜索时每组生成 200 个，最终最优模型生成 1,000 个。
5. 条件生成把 conductivity 最高 5% 标记为 high，其余为 low；high 类随机过采样到与 low 类平衡，并把类别 token 加到输入序列。
6. 用 HTP-MD 上训练的 GNN 预测生成候选的 conductivity 和 transference number。

### 1.2 原文候选漏斗

1. 用 high-conductivity 条件生成 100,000 个 polymers。
2. 用 GNN 对 100,000 个候选排序。
3. 选择预测排名前 50 个进入全原子 MD。
4. 每个结构运行 5 个独立 replicas；四个含 phosphinate 的候选因 PCFF+ 参数缺失而保留为失败，不做静默替换。
5. 50 × 5 = 250 个计划作业中完成 206 个；最终 46 个 polymer 有可用 MD 数据。

### 1.3 原文 MD 条件与输出

- 体系：polymer + LiTFSI。
- 温度：353 K。
- 盐浓度：1.5 mol/kg。
- 引擎/力场：LAMMPS + PCFF+（非极化经典力场）。
- 初始结构：将重复单元聚合到 backbone 至少包含 150 个非氢重原子，并用 methyl groups 封端；再构建无定形 polymer-salt cell。
- 流程：初始 relaxation → 顺序 NVT/NPT equilibration，使密度接近理论值 → 353 K NVT production。
- timestep：2.0 fs。
- production：5 ns；论文同时明确指出 50 ns 对低扩散体系更可靠，因此 5 ns 只用于快速定性筛选。
- 分析：cluster Nernst–Einstein，从 production trajectory 计算 ionic conductivity 和 cation transference number。
- 统计单位：polymer structure；每个结构 5 replicas，轨迹帧不是独立重复。

## 2. 我们的前瞻实验设计

### 2.1 冻结问题与比较

主要问题：在相同的构建、配方、力场、平衡、production 和分析协议下，continuous top cohort 的结构级 conductivity 是否优于 binary top cohort？

主要对比：continuous − binary。次要对比：continuous − legacy PolyGen、continuous − PEO。符号为正表示 continuous 更高。

完整 S3 设计沿用 PR #4 冻结的 continuous top-20、binary top-20、legacy top-20，并增加 PEO；每个结构 5 replicas。失败构建、缺参数、数值不稳定和未完成均保留在分母中。

### 2.2 top-1 工程 smoke（本轮目标）

smoke 只回答“链路能否端到端产生可解析轨迹和分析文件”，不回答候选是否高导电。

| 环节 | 200 ps smoke | 原文/后续全量 | PASS 依据 |
|---|---:|---:|---|
| 候选身份 | frozen continuous rank 1 | 同一 frozen ID | canonical p-SMILES、源行、源文件和 SHA-256 一致 |
| polymer 构建 | backbone 至少 150 个非氢重原子、methyl 封端；固定 chain/DP 算法 | 相同 | 两端正确连接、价态正确、无断链、atom mapping 可追踪 |
| 配方 | LiTFSI 1.5 mol/kg | 1.5 mol/kg | 由实际 polymer mass 和离子对数反算 molality，误差在冻结容差内 |
| replicas | 1 个固定 seed | 5 个固定 seeds | seed、初始 cell、随机化过程写入 manifest |
| relaxation/equilibration | 保留原文顺序；每段缩短但不得省略类型 | 原文完整 NVT/NPT schedule | 无 lost atoms/NaN；温压密度日志齐全；最终 cell 有效 |
| production | 200 ps，353 K NVT，2 fs（100,000 steps） | 5 ns（2,500,000 steps） | 正常退出；预期帧数、时间跨度、盒信息和 species mapping 完整 |
| diffusivity | Li、TFSI 和必要 cluster 的 MSD diagnostic | 多时间原点 + 5 ns | MSD 时间轴正确；unwrap/PBC 正确；拟合窗预先冻结并输出斜率诊断 |
| conductivity | 仅 pipeline smoke 数值 | cluster Nernst–Einstein | cluster 定义、charge、population、单位和公式测试通过 |
| transference | 若 200 ps 无稳定区间则只输出 NA + 原因 | 原文同算法 | 不用单一 Li 自扩散替代原文 cation transference number |

200 ps 的 conductivity 数值必须标注 `NON_CONVERGED_SMOKE_ONLY`。由于扩散距离和 cluster population 采样不足，不允许用它与 binary 或论文结果做高低结论。

### 2.3 全量 top-1 通过后的扩展

1. 对 top-1 跑 5 × 5 ns，保持与原文相同的 PCFF+、353 K、1.5 mol/kg 和 cluster Nernst–Einstein。
2. 在读取结果前冻结 QC、排除规则、拟合窗、bootstrap 和失败处理。
3. top-1 只用于验证协议，不用于宣称 cohort 优势；结构级比较需要运行冻结的三组 top-20 + PEO。
4. 对低扩散或未形成线性 MSD 区间的结构，按预先统一的升级规则延长到 50 ns，不能按 arm 或结果选择性延长。

## 3. 现有资产审计

| 资产/能力 | 状态 | 证据与限制 |
|---|---|---|
| 研究 blueprint | PASS | PR #4 已合并；`RESEARCH_BLUEPRINT.md` 与 `research/blueprint/status.json` 标记当前为 S2 |
| continuous top-1 身份 | PASS | `results/experiment-c/md-validation/continuous_top20.csv` rank 1 已冻结 |
| binary/legacy controls | PASS | PR #4 各冻结 top-20 cohort |
| 原版示例 LAMMPS 输入 | PARTIAL | 有 PCFF+ 平衡/production、Li/TFSI templates；只对应已参数化 PEO |
| 原文准确配方 | PASS | 3 条 DP15 polymer 链 + 10 Li + 10 TFSI，反算 1.500015 mol/kg；配方和结构文件已写入 manifest |
| top-1 polymer builder | PASS | 固定 seed 的 p-SMILES → DP15 → 152 heavy atoms → methyl caps；拓扑单测 2/2 PASS |
| top-1 PCFF+ 参数 | FAIL | 尚无 atom typing、charges、bonded/nonbonded coverage 报告 |
| ARC/SSH 可访问性 | PASS | `kozo-dev-yi` 可登录；ARC MD health 正常；Matlantis SSH 成功；历史 job 成功 |
| ARC 原文等价性 | FAIL | 当前 ARC 是 Matlantis PFP/ASE 路线，不是 LAMMPS PCFF+ |
| kozo-dev LAMMPS runtime | PASS（standalone） | LAMMPS 2 Aug 2023，启用 CLASS2/KSPACE/MOLECULE；`real + full + lj/class2/coul/long + PPPM` smoke 正常结束 |
| diffusivity 工具 | PARTIAL | ARC 有 MSD/diffusivity recipe，但需验证 polymer-electrolyte 的 PBC unwrap、species 和统计窗 |
| 原文 conductivity 工具 | PASS（独立分析环境） | 公开 `TRI-AMDD/htp_md` 的 trajectory → diffusivity/conductivity/transference 核心测试 26/26 PASS；尚待接入本次作业产物。ARC 内置实现仍只是单 species 普通 Nernst–Einstein，默认 Haven ratio 1 |
| 200 ps 科学充分性 | FAIL | 仅能作为执行 smoke，不能验证电导率排序或与论文作物理比较 |

## 4. 启动作业前必须关闭的 S2 门槛

1. **已完成**：p-SMILES polymerization、最小 DP、methyl termination、chain count、initial cell 和 LiTFSI 配方的确定性构建。
2. 为 top-1 生成 PCFF+ `system.lmp`，并输出 100% atom/bond/angle/dihedral/improper/nonbonded 参数覆盖报告。
3. **已完成**：从实际 polymer mass 计算盐量；3 chains + 10 ion pairs 为 1.500015 mol/kg，没有复用示例的固定 `nions=100`。
4. 冻结完整 equilibration schedule；仓库 `equilibration.in` 的具体阶段可作起点，但必须确认它就是论文使用版本。
5. **分析算法已回归通过**：HTP-MD cluster Nernst–Einstein 核心测试 26/26 PASS；待接入 top-1 轨迹。
6. 冻结 blinded ID、replica seeds、文件清单、作业重跑规则和 200 ps smoke contract。
7. **standalone runtime 已完成**：kozo-dev 可运行 LAMMPS CLASS2/KSPACE/MOLECULE；仍需接入 ARC provider，并以参数覆盖报告作为提交前置条件。

## 4.1 已关闭的分析子门槛

2026-09-24 在 `kozo-dev-yi` 上对公开 `TRI-AMDD/htp_md` commit
`4076e9baa8d2da0c9ee250bd2b75daa58d03986a` 做了隔离回归：

- `tests/shared/test_polymer.py` 与 `tests/trajectory/test_load.py`：26/26 PASS。
- 覆盖 Li/TFSI diffusivity、diffusivity time series、polymer diffusivity、cluster
  Nernst–Einstein conductivity、conductivity time series、transference number、molality、
  density、simulation length、degree of polymerization 和 LAMMPS trajectory loading。
- 两个 PCFF+ polymer-electrolyte 测试轨迹及 population matrices 均有 SHA-256
  记录，详见 `results/experiment-c/md-validation/top1_readiness_audit.json`。
- 扩大到 `tests/test_analysis.py` 后为 26 PASS / 2 FAIL；两个失败均发生在加载由
  scikit-learn 0.23.2 保存的旧 RF surrogate pickle，而当前环境为 scikit-learn
  1.7.2。它不否定 trajectory → physical properties 的 26 个核心断言，但说明旧
  surrogate 不能在当前环境直接复用。

因此，原文物理分析算法已证明可在 kozo-dev 上执行。

## 4.2 已关闭的构建与配方子门槛

- top-1 重复单元构建为 methyl-terminated DP15 链：152 个重原子、308 个总原子，
  分子式 `C92H156O60`；SDF 与 PDB 均记录 SHA-256。
- 初始体系包含 3 条 polymer chains、10 个 Li+ 和 10 个 TFSI−：共 1084 原子，
  反算浓度 1.500015 mol/kg，相对目标误差约 `1.0e-5`。
- 直接按 1.2 g/cm³ 打包失败；按原仓库输入中的 1.4411 线性扩箱因子，将初始打包
  密度设为 0.400958 g/cm³ 后成功。初始立方盒边长为 34.04965 Å；后续仍须通过
  原文的 NVT/NPT schedule 收缩和密度平衡，不能把初始盒密度当作 production 密度。
- 打包后的 extxyz SHA-256 为
  `09f4e53c8ec6fefb0ff0c1e6b8b5fe80d36ef2c78fe64a0a4e0a27242ecfb13a`。

剩余 launch blockers 已收敛为 top-1 的 PCFF+ 参数化，以及 LAMMPS/PCFF+ 与 ARC
作业编排的集成。

## 4.3 LAMMPS runtime 证据

- ARC 平台自身的 authoritative blueprint 将 “Real classical-MD vertical slice” 列为
  尚未实现的 Phase 4，并明确标注需要外部确认 MedeA/PCFF+ license、automation
  interface、export rules 和 legacy MIT protocol。
- Docker 客户端存在，但当前用户无权访问 daemon；conda-forge 的现成 LAMMPS 包
  又要求比主机更新的 GLIBC，因此两条预编译路线均不可用。
- 已用主机编译器从 LAMMPS commit
  `27d065a682a1bd01d811db77b96abb108db1771e` 构建 serial runtime，版本为
  2 Aug 2023，启用 `CLASS2 KSPACE MOLECULE`。
- 含两颗相反电荷粒子的 `units real`、`atom_style full`、
  `pair_style lj/class2/coul/long`、`kspace_style pppm`、`run 0` smoke 正常结束。
- 二进制 SHA-256：
  `84286e2494f909389e92ea79f8bd161243e6751d8831c4e6e46e7e0737b984f3`。
- 可复现构建脚本为 `scripts/build_lammps_pcff_runtime.sh`。此证据证明执行器能力，
  不代表已经获得 PCFF+ parameters，也不把 standalone runtime 误报为 ARC provider。

## 5. 本轮作业决定

`NO-GO`：不提交 top-1 200 ps 生产作业。

原因不是 SSH、算力、体系构建、LAMMPS runtime 或分析算法不可用，而是原文等价性的 PCFF+ 力场输入仍缺失；ARC 当前也还没有正式的 LAMMPS/PCFF+ provider。此时提交 ARC/PFP 作业会改变力场和 estimator，不能满足“每个实验与原文一一 match”的要求。

可接受的下一次启动条件：获得完整 PCFF+ 参数与 coverage report，并在 ARC 上验证 LAMMPS runtime；随后由 frozen manifest 生成唯一的 200 ps 输入，执行 top-1 单 replica smoke，得到带 `NON_CONVERGED_SMOKE_ONLY` 标签的 diffusivity/conductivity 技术结果，再扩展为 5 × 5 ns。

外部参数化团队的精确交付内容、接受检查和拒绝条件已经冻结在
`PCFF_PLUS_HANDOFF.md`。收到满足该契约的 bundle 后，不需要重新选择候选、重建
配方或更换分析方法，可以直接进入 LAMMPS `read_data`/`run 0` acceptance 和
200 ps smoke。
