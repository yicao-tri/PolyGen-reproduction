#!/usr/bin/env python3
"""Create the frozen continuous-vs-binary PFP top-1 comparison."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def temperature_stats(path: Path, discard_ps: float) -> dict:
    values = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) != 5 or fields[0] == "Time[ps]":
            continue
        try:
            time_ps = float(fields[0])
            temperature = float(fields[-1])
        except ValueError:
            continue
        if time_ps >= discard_ps:
            values.append(temperature)
    if not values:
        return {"count": 0, "mean_K": None, "min_K": None, "max_K": None}
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "count": len(values),
        "mean_K": mean,
        "std_K": math.sqrt(variance),
        "min_K": min(values),
        "max_K": max(values),
    }


def row(arm: str, analysis: dict, run: dict, log: Path, expected_frames: int) -> dict:
    diff = analysis["diffusivity"]["htpmd_endpoint"]
    cond = analysis["conductivity"]
    proxy = analysis["proxy_comparison"]
    quality = analysis["quality"]
    technical_gate = all(
        [
            analysis["status"] == "succeeded",
            run["status"] == "succeeded",
            analysis["frames_total"] >= expected_frames,
            analysis["analysis_ps"] >= 159.9,
            quality["finite_values"],
            quality["constant_cell"],
            math.isclose(
                quality["population_ion_count_mean"],
                quality["expected_ion_count"],
                abs_tol=1e-8,
            ),
        ]
    )
    return {
        "arm": arm,
        "trajectory_sha256": analysis["source"]["trajectory_sha256"],
        "frames_total": analysis["frames_total"],
        "analysis_ps": analysis["analysis_ps"],
        "temperature_mean_K": temperature_stats(log, analysis["discard_ps"])["mean_K"],
        "li_diffusivity_cm2_s": diff["li_cm2_s"],
        "tfsi_diffusivity_cm2_s": diff["tfsi_cm2_s"],
        "cluster_ne_conductivity_S_cm": cond["cluster_nernst_einstein_S_cm"],
        "cluster_ne_log10_S_cm": proxy["pfp_cluster_ne_log10_S_cm"],
        "ne_conductivity_S_cm": cond["nernst_einstein_S_cm"],
        "transference_number_cluster": cond["cluster_transference_number"],
        "proxy_log10_S_cm": proxy["proxy_log10_S_cm"],
        "residual_pfp_minus_proxy_log10_S_cm": proxy[
            "residual_pfp_minus_proxy_log10_S_cm"
        ],
        "technical_gate_pass": technical_gate,
        "scientific_convergence_status": "NON_CONVERGED_SMOKE_ONLY",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for arm in ("continuous", "binary"):
        parser.add_argument(f"--{arm}-analysis", type=Path, required=True)
        parser.add_argument(f"--{arm}-run", type=Path, required=True)
        parser.add_argument(f"--{arm}-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-frames", type=int, default=2001)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for arm in ("continuous", "binary"):
        rows.append(
            row(
                arm,
                load(getattr(args, f"{arm}_analysis")),
                load(getattr(args, f"{arm}_run")),
                getattr(args, f"{arm}_log"),
                args.expected_frames,
            )
        )
    by_arm = {item["arm"]: item for item in rows}
    continuous = by_arm["continuous"]
    binary = by_arm["binary"]
    contrast = {
        "direction": "continuous_minus_binary",
        "cluster_ne_log10_S_cm": continuous["cluster_ne_log10_S_cm"]
        - binary["cluster_ne_log10_S_cm"],
        "cluster_ne_conductivity_S_cm": continuous["cluster_ne_conductivity_S_cm"]
        - binary["cluster_ne_conductivity_S_cm"],
        "li_diffusivity_cm2_s": continuous["li_diffusivity_cm2_s"]
        - binary["li_diffusivity_cm2_s"],
        "tfsi_diffusivity_cm2_s": continuous["tfsi_diffusivity_cm2_s"]
        - binary["tfsi_diffusivity_cm2_s"],
        "proxy_log10_S_cm": continuous["proxy_log10_S_cm"]
        - binary["proxy_log10_S_cm"],
        "residual_log10_S_cm": continuous["residual_pfp_minus_proxy_log10_S_cm"]
        - binary["residual_pfp_minus_proxy_log10_S_cm"],
    }
    summary = {
        "schema_version": "polygen.pfp-top1-paired-summary.v1",
        "status": "succeeded" if all(item["technical_gate_pass"] for item in rows) else "failed_gate",
        "rows": rows,
        "paired_contrast": contrast,
        "interpretation": {
            "higher_pfp_pilot_conductivity_arm": max(
                rows, key=lambda item: item["cluster_ne_log10_S_cm"]
            )["arm"],
            "proxy_and_pfp_ranking_agree": (
                contrast["proxy_log10_S_cm"] * contrast["cluster_ne_log10_S_cm"] > 0
            ),
            "claim_limit": "One 200 ps replica per arm; technical feasibility only, not converged truth.",
        },
    }
    (args.output_dir / "paired_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (args.output_dir / "paired_results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
