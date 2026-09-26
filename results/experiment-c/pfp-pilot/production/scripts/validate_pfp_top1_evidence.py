#!/usr/bin/env python3
"""Validate the frozen PFP top-1 evidence chain without interpreting results."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def record(checks: list[dict], name: str, passed: bool, observed=None, expected=None) -> None:
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "observed": observed,
            "expected": expected,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--production-root", type=Path)
    parser.add_argument("--analysis-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = read(args.contract)
    preflight = read(args.preflight_root / "batch_summary.json")
    checks: list[dict] = []
    protocol = contract["protocol"]
    record(checks, "candidate_count", preflight["candidate_count"] == 2, preflight["candidate_count"], 2)
    record(checks, "preflight_status", preflight["status"] == "succeeded", preflight["status"], "succeeded")
    record(checks, "preflight_protocol_equal", preflight["paired_protocol_equal"] is True, preflight["paired_protocol_equal"], True)

    candidate_by_arm = {candidate["arm"]: candidate for candidate in contract["candidates"]}
    preflight_by_arm = {
        "continuous" if run["label"].startswith("polygen_continuous") else "binary": run
        for run in preflight["runs"]
    }
    for arm in ("continuous", "binary"):
        candidate = candidate_by_arm[arm]
        run = preflight_by_arm[arm]
        record(
            checks,
            f"{arm}.source_sha256",
            run["source_sha256"] == candidate["source_structure_sha256"],
            run["source_sha256"],
            candidate["source_structure_sha256"],
        )
        record(
            checks,
            f"{arm}.relaxation_force_gate",
            run["relaxed_max_force_eV_A"] <= contract["gates"]["relaxed_max_force_eV_A_max"],
            run["relaxed_max_force_eV_A"],
            contract["gates"]["relaxed_max_force_eV_A_max"],
        )
        relaxed = args.preflight_root / run["label"] / run["artifacts"]["relaxed_structure"]["path"]
        record(
            checks,
            f"{arm}.relaxed_file_hash",
            relaxed.exists() and sha256(relaxed) == run["artifacts"]["relaxed_structure"]["sha256"],
            sha256(relaxed) if relaxed.exists() else None,
            run["artifacts"]["relaxed_structure"]["sha256"],
        )

    if args.production_root:
        for arm in ("continuous", "binary"):
            batch_path = args.production_root / arm / "results" / "batch_summary.json"
            record(checks, f"{arm}.production_summary_exists", batch_path.exists(), batch_path.exists(), True)
            if not batch_path.exists():
                continue
            batch = read(batch_path)
            run = batch["runs"][0]
            preflight_run = preflight_by_arm[arm]
            expected_relaxed_hash = preflight_run["artifacts"]["relaxed_structure"]["sha256"]
            record(checks, f"{arm}.production_status", run["status"] == "succeeded", run["status"], "succeeded")
            record(checks, f"{arm}.production_source_chain", run["source_sha256"] == expected_relaxed_hash, run["source_sha256"], expected_relaxed_hash)
            for key, expected in (
                ("temperature_K", protocol["temperature_K"]),
                ("timestep_fs", protocol["timestep_fs"]),
                ("steps", protocol["total_steps"]),
                ("trajectory_interval_steps", protocol["trajectory_interval_steps"]),
                ("friction_per_fs", protocol["friction_per_fs"]),
                ("velocity_seed", protocol["velocity_seed"]),
            ):
                record(checks, f"{arm}.protocol.{key}", run[key] == expected, run[key], expected)
            record(
                checks,
                f"{arm}.frame_count",
                run["frame_count"] >= contract["gates"]["minimum_production_frames"],
                run["frame_count"],
                contract["gates"]["minimum_production_frames"],
            )
            trajectory = batch_path.parent / run["label"] / run["artifacts"]["trajectory"]["path"]
            record(
                checks,
                f"{arm}.trajectory_hash",
                trajectory.exists() and sha256(trajectory) == run["artifacts"]["trajectory"]["sha256"],
                sha256(trajectory) if trajectory.exists() else None,
                run["artifacts"]["trajectory"]["sha256"],
            )

    if args.analysis_root:
        for arm in ("continuous", "binary"):
            path = args.analysis_root / arm / "analysis.json"
            record(checks, f"{arm}.analysis_exists", path.exists(), path.exists(), True)
            if not path.exists():
                continue
            analysis = read(path)
            quality = analysis["quality"]
            record(checks, f"{arm}.analysis_status", analysis["status"] == "succeeded", analysis["status"], "succeeded")
            record(checks, f"{arm}.analysis_finite", quality["finite_values"], quality["finite_values"], True)
            record(checks, f"{arm}.analysis_constant_cell", quality["constant_cell"], quality["constant_cell"], True)
            record(
                checks,
                f"{arm}.analysis_ion_conservation",
                math.isclose(
                    quality["population_ion_count_mean"],
                    quality["expected_ion_count"],
                    rel_tol=0.0,
                    abs_tol=1.0e-8,
                ),
                quality["population_ion_count_mean"],
                quality["expected_ion_count"],
            )

    result = {
        "schema_version": "polygen.pfp-top1-validator.v1",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
