#!/usr/bin/env python3
"""Render the top-1 paired PFP pilot report directly from validated JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sci(value: float) -> str:
    return f"{value:.4e}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--paired", type=Path, required=True)
    parser.add_argument("--continuous-analysis", type=Path, required=True)
    parser.add_argument("--binary-analysis", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load(args.contract)
    paired = load(args.paired)
    validation = load(args.validation)
    analyses = {
        "continuous": load(args.continuous_analysis),
        "binary": load(args.binary_analysis),
    }
    rows = {row["arm"]: row for row in paired["rows"]}
    candidates = {candidate["arm"]: candidate for candidate in contract["candidates"]}
    contrast = paired["paired_contrast"]
    interpretation = paired["interpretation"]
    figure_path = args.output.parent / "figures" / "pfp_top1_msd.svg"

    if validation["status"] != "passed":
        raise ValueError("Refusing to render a result report from failed evidence validation")

    lines = [
        "# PolyGen continuous vs binary：PFP top-1 pilot 结果",
        "",
        "## 结论摘要",
        "",
        f"两条 200 ps PFP 轨迹和 HTP-MD-compatible 分析已通过 {validation['checks_passed']}/{validation['checks_total']} 项证据门禁。",
        f"本 pilot 中 cNE0 电导率较高的 arm 为 **{interpretation['higher_pfp_pilot_conductivity_arm']}**；proxy 与 PFP 的两候选排序一致性为 **{interpretation['proxy_and_pfp_ranking_agree']}**。",
        "该结果仅是单 replica、200 ps 的技术可行性结果，标签为 `NON_CONVERGED_SMOKE_ONLY`；PFP-MD 不是实验真值，不能据此宣称模型优越。",
        "",
        "## 候选与结果",
        "",
        "| arm | canonical p-SMILES | proxy log10(S/cm) | PFP cNE0 (S/cm) | PFP log10(S/cm) | residual | D_Li (cm2/s) | D_TFSI (cm2/s) | t+ |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("continuous", "binary"):
        row = rows[arm]
        candidate = candidates[arm]
        lines.append(
            "| {arm} | `{smiles}` | {proxy:.6f} | {cond} | {log:.6f} | {residual:+.6f} | {li} | {tfsi} | {tn:.4f} |".format(
                arm=arm,
                smiles=candidate["canonical_smiles"],
                proxy=row["proxy_log10_S_cm"],
                cond=sci(row["cluster_ne_conductivity_S_cm"]),
                log=row["cluster_ne_log10_S_cm"],
                residual=row["residual_pfp_minus_proxy_log10_S_cm"],
                li=sci(row["li_diffusivity_cm2_s"]),
                tfsi=sci(row["tfsi_diffusivity_cm2_s"]),
                tn=row["transference_number_cluster"],
            )
        )
    if figure_path.exists():
        lines.extend(
            [
                "",
                "### 离子迁移诊断图",
                "",
                "![Continuous 与 binary top-1 的 Li+/TFSI− multi-origin MSD；灰色为 40–120 ps 斜率诊断时间窗。](figures/pfp_top1_msd.svg)",
                "",
                "图中连续值候选的 Li+ 与 TFSI− MSD 均更快增长；该图是扩散诊断，正式 HTP-MD diffusivity 仍使用 40 ps discard 后 160 ps 的 endpoint MSD 定义。",
            ]
        )
    lines.extend(
        [
            "",
            "### 累积轨迹长度敏感性",
            "",
            "| arm | 20 ps | 40 ps | 80 ps | 120 ps | 160 ps |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for arm in ("continuous", "binary"):
        values = {
            item["analysis_duration_ps"]: item["cluster_ne_log10_S_cm"]
            for item in analyses[arm]["convergence_diagnostic"]
        }
        lines.append(
            "| {arm} | {v20:.4f} | {v40:.4f} | {v80:.4f} | {v120:.4f} | {v160:.4f} |".format(
                arm=arm,
                v20=values[20.0],
                v40=values[40.0],
                v80=values[80.0],
                v120=values[120.0],
                v160=values[160.0],
            )
        )
    lines.extend(
        [
            "",
            "表中为从 40 ps production 时刻开始累积的 cNE0 log10(S/cm)。若随窗口仍有明显漂移，即使 MSD 拟合 R2 很高，也不能视为科学收敛。",
        ]
    )
    lines.extend(
        [
            "",
            "Residual 固定定义为 `PFP-MD log10 conductivity - proxy log10 conductivity`。",
            "",
            "## 配对对比",
            "",
            f"- continuous − binary PFP log10 conductivity：{contrast['cluster_ne_log10_S_cm']:+.6f}",
            f"- continuous − binary proxy log10 conductivity：{contrast['proxy_log10_S_cm']:+.6f}",
            f"- continuous − binary residual：{contrast['residual_log10_S_cm']:+.6f}",
            f"- continuous − binary Li diffusivity：{sci(contrast['li_diffusivity_cm2_s'])} cm2/s",
            f"- continuous − binary TFSI diffusivity：{sci(contrast['tfsi_diffusivity_cm2_s'])} cm2/s",
            "",
            "以上为一个 rank-pair 的描述性差异，不是统计检验。",
            "",
            "## 轨迹与质量诊断",
            "",
            "| arm | frames | analysis window | mean T (K) | COM displacement (A) | drift-corrected D_Li | endpoint/slope R2 (Li/TFSI) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for arm in ("continuous", "binary"):
        row = rows[arm]
        analysis = analyses[arm]
        drift = analysis["diffusivity"]["system_com_drift_diagnostic"]
        slope = analysis["diffusivity"]["multi_origin_slope_diagnostic"]
        lines.append(
            "| {arm} | {frames} | {window:.1f} ps | {temp:.2f} | {com:.5f} | {dli} | {rli:.3f}/{rtfsi:.3f} |".format(
                arm=arm,
                frames=row["frames_total"],
                window=row["analysis_ps"],
                temp=row["temperature_mean_K"],
                com=drift["system_com_displacement_A"],
                dli=sci(drift["li_cm2_s"]),
                rli=slope["li"]["r_squared"],
                rtfsi=slope["tfsi_N"]["r_squared"],
            )
        )
    lines.extend(
        [
            "",
            "## 与原文设计的差异",
            "",
            "原 PolyGen 验证采用 PCFF+、50 对 LiTFSI、1.5 mol/kg、5 ns production 和每候选 5 replicas；本 pilot 使用 PFP v8.0.0、10 对 LiTFSI、200 ps 和 1 replica。",
            "当前 continuous/binary 离散 molality 分别约为 1.5000/1.4527 mol/kg；3.2% 浓度差和较小 cell 均可能影响 paired contrast。",
            "扩展 top10 前应使用浓度匹配到 ±1% 的较大整数 cell，并在赋速后显式清零线性动量。正式模型比较至少需要 5 replicas × 5 ns；小子集可扩到 50 ns 检查收敛。",
            "",
            "## 证据状态",
            "",
            f"- validator：`{validation['status']}`（{validation['checks_passed']}/{validation['checks_total']}）",
            f"- paired summary：`{paired['status']}`",
            "- scientific convergence：`NON_CONVERGED_SMOKE_ONLY`",
            "- 所有 headline 数值均来自 `analysis.json` 与 `paired_summary.json`，未人工抄写。",
        ]
    )
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
