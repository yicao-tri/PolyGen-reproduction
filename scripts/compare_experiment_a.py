#!/usr/bin/env python3
"""Create the machine-readable Experiment A comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CORE_METRICS = ("validity", "uniqueness", "novelty")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_metrics(record: dict) -> dict:
    return {name: record["metrics"][name] for name in CORE_METRICS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-baseline", type=Path, required=True)
    parser.add_argument("--paired-released", type=Path, required=True)
    parser.add_argument("--paired-disjoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    external = load(args.external_baseline)
    released = load(args.paired_released)
    disjoint = load(args.paired_disjoint)
    external_metrics = selected_metrics(external)
    released_metrics = selected_metrics(released)
    disjoint_metrics = selected_metrics(disjoint)
    result = {
        "metric_denominator": 100,
        "external_released_checkpoint": external_metrics,
        "paired_retrained_released_random": released_metrics,
        "paired_retrained_structure_disjoint": disjoint_metrics,
        "paired_delta_disjoint_minus_released_random": {
            name: disjoint_metrics[name] - released_metrics[name] for name in CORE_METRICS
        },
        "external_delta_disjoint_minus_released_checkpoint": {
            name: disjoint_metrics[name] - external_metrics[name] for name in CORE_METRICS
        },
        "interpretation_scope": {
            "paired_comparison": "Same seed, architecture, optimizer settings, 10,000 steps, and generation settings; split policy is the intended experimental variable.",
            "external_comparison": "Useful continuity check against the repository's prior result, but the released checkpoint's original training seed and full provenance are not available.",
            "replication_limit": "One training seed and one 100-sample generation draw; deltas are not uncertainty estimates.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
