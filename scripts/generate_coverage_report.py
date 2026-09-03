#!/usr/bin/env python3
"""Generate a paper-scope coverage report from package evidence, never paper values."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"


# These labels are non-numeric scope metadata only. They identify the result type
# that an independent reproduction would have to cover; no caption text or result
# value from the article is stored here.
SCOPES = (
    ("Fig. 1", "workflow schematic", "conceptual", ()),
    ("Fig. 2a", "unconditional hyperparameter comparison", "model_grid", ()),
    ("Fig. 2b", "unconditional model metrics", "model_metrics", ()),
    ("Fig. 2c", "unconditional generated examples", "model_samples", ()),
    ("Fig. 2d", "generated versus training property distributions", "property_predictions", ()),
    ("Fig. 3a", "conditional-training class balance", "class_balance", ("results/figures/actual_training_class_balance.svg",)),
    ("Fig. 3b", "conditional generated examples", "model_samples", ()),
    ("Fig. 3c", "conditional conductivity distributions", "property_predictions", ()),
    ("Fig. 3d", "conditional model metrics", "model_metrics", ()),
    ("Fig. 3e", "functional-group conditioning examples", "conditioned_functional_groups", ()),
    ("Fig. 3f", "functional-group conditioning frequencies", "conditioned_functional_groups", ()),
    ("Fig. 4a", "molecular-dynamics workflow schematic", "conceptual", ()),
    ("Fig. 4b", "validation property distributions", "validation_distributions", ("results/figures/actual_conductivity_distributions.svg",)),
    ("Fig. 4c", "candidate validation replica distributions", "validation_replicas", ("results/figures/actual_validation_md_boxplots.svg",)),
    ("Fig. 5a", "pretraining model metrics", "pretraining", ()),
    ("Fig. 5b", "pretraining and fine-tuning losses", "pretraining", ()),
    ("Fig. 5c", "data-volume performance study", "pretraining", ()),
    ("Fig. 5d", "data-volume similarity and diversity study", "pretraining", ()),
    ("Fig. 5e", "pretraining validity and uniqueness frontier", "pretraining", ()),
    ("Fig. 5f", "pretraining similarity and diversity frontier", "pretraining", ()),
    ("Supplementary Fig. 1", "model architecture schematic", "conceptual", ()),
    ("Supplementary Fig. 2", "functional groups in generated candidates", "conditioned_functional_groups", ()),
    ("Supplementary Fig. 3", "prediction and simulation relationship", "property_predictions", ()),
    ("Supplementary Table 1", "model evaluation metrics", "model_metrics", ()),
    ("Supplementary Table 2", "candidate validation properties", "validation_distributions", ()),
    ("Supplementary Table 3", "experiment settings", "publication_settings", ()),
    ("Supplementary Table 4", "minGPT grid outputs", "model_grid", ()),
    ("Supplementary Table 5", "diffusion1D grid outputs", "model_grid", ()),
    ("Supplementary Table 6", "diffusionLM grid outputs", "model_grid", ()),
)


def exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def joined_existing(paths: Sequence[str]) -> str:
    return ";".join(path for path in paths if exists(path))


def evidence_state() -> dict[str, object]:
    min_gpt = sorted((ROOT / "results" / "dev").glob("minGPT-*/samples.csv"))
    diffusion_lm = sorted((ROOT / "results" / "dev").glob("diffusionLM-*/scored_samples.csv"))
    diffusion_1d = sorted((ROOT / "results" / "dev").glob("diffusion1D-*/decoded_samples.csv"))
    metric_files = sorted((ROOT / "results" / "dev").glob("*/metrics.json"))
    return {
        "actual_sample_paths": tuple(
            str(path.relative_to(ROOT)) for path in min_gpt + diffusion_lm + diffusion_1d
        ),
        "actual_metric_paths": tuple(str(path.relative_to(ROOT)) for path in metric_files),
        "has_training_raw": exists("inputs/release-data/PolyGen-train-set-from-HTP-MD.csv")
        and exists("inputs/release-data/htpmd-trainset.csv")
        and exists("inputs/release-data/minGPT/htp_md.csv"),
        "has_iteration_raw": exists("inputs/release-data/generated_polymers_in_two_iterations.csv"),
        "has_validation_raw": exists("inputs/official-supplement/41524_2024_1470_MOESM2_ESM.csv"),
        "has_property_predictor": any((ROOT / "inputs").rglob("*predictor*")),
        "has_pretraining_assets": any((ROOT / "inputs").rglob("*PI1M*")),
        "has_grid_logs": any((ROOT / "results" / "dev").rglob("*grid*")),
        "has_functional_group_samples": any((ROOT / "inputs").rglob("*functional*")),
    }


def row_for(scope: tuple[str, str, str, tuple[str, ...]], state: dict[str, object]) -> dict[str, str]:
    item, topic, requirement, declared_outputs = scope
    evidence: tuple[str, ...] = ()

    if requirement == "conceptual":
        status = "conceptual-no-numeric-reproduction"
        reason = "No scientific result values are required; the package does not trace article artwork."
    elif requirement == "class_balance" and state["has_training_raw"] and all(map(exists, declared_outputs)):
        status = "reproduced-from-machine-readable-data"
        evidence = declared_outputs + ("results/tables/dataset_summary.json",)
        reason = "The plot and summary are regenerated from released training tables."
    elif requirement == "validation_replicas" and state["has_validation_raw"] and all(map(exists, declared_outputs)):
        status = "reproduced-from-machine-readable-data"
        evidence = declared_outputs + ("results/tables/md_candidate_summary.csv",)
        reason = "Every available validation row and literal simulation group is processed by the local script."
    elif requirement == "validation_distributions" and state["has_validation_raw"]:
        status = "partial-machine-readable-data"
        evidence = declared_outputs + (
            "results/tables/dataset_summary.json",
            "results/tables/md_candidate_summary.csv",
        )
        reason = "Released conductivity data are processed; the paired candidate property array needed for the full comparison is absent."
    elif requirement in {"model_metrics", "model_samples"} and (
        state["actual_metric_paths"] or state["actual_sample_paths"]
    ):
        status = "actual-dev-analogue-not-publication-run"
        evidence = tuple(state["actual_metric_paths"]) + tuple(state["actual_sample_paths"])
        reason = "Real DEV outputs are archived, but their task, duration, samples, or weights do not identify them as the publication-generating run."
    elif requirement == "property_predictions" and state["has_iteration_raw"]:
        status = "partial-machine-readable-data"
        evidence = (
            "inputs/release-data/generated_polymers_in_two_iterations.csv",
            "results/tables/generated_iteration_summary.csv",
        )
        reason = "A released generated-polymer table is summarized, but the property-predictor artifact and panel-generating arrays are absent."
    elif requirement == "model_grid" and state["has_grid_logs"]:
        status = "reproduced-from-actual-runs"
        reason = "Grid logs were detected and can be aggregated without a paper comparator."
    elif requirement == "pretraining" and state["has_pretraining_assets"]:
        status = "partial-machine-readable-data"
        reason = "Some pretraining assets were detected, but a complete result requires checkpoints, logs, and generated arrays."
    elif requirement == "conditioned_functional_groups" and state["has_functional_group_samples"]:
        status = "partial-machine-readable-data"
        reason = "Functional-group sample data were detected, but the full generation evidence is incomplete."
    else:
        status = "not-reproduced-missing-machine-readable-evidence"
        missing = {
            "model_grid": "original grid execution logs and publication checkpoints",
            "property_predictions": "property-predictor code or weights and panel-generating prediction arrays",
            "conditioned_functional_groups": "functional-group-conditioned generated samples and analysis arrays",
            "pretraining": "pretraining corpus, checkpoints, loss logs, and grid outputs",
            "publication_settings": "a non-PDF machine-readable experiment manifest",
        }.get(requirement, "publication-generating machine-readable output")
        reason = f"Missing {missing}; no value is transcribed from the article to fill the gap."

    evidence = tuple(path for path in evidence if exists(path))
    return {
        "item": item,
        "topic": topic,
        "status": status,
        "evidence": ";".join(evidence),
        "reason": reason,
    }


def compute_rows() -> list[dict[str, str]]:
    state = evidence_state()
    return [row_for(scope, state) for scope in SCOPES]


def markdown_report(rows: Sequence[dict[str, str]]) -> str:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Reproduction coverage generated from actual evidence",
        "",
        "This report is regenerated by `scripts/generate_coverage_report.py`. Panel identifiers and",
        "short topics are non-numeric scope metadata only. No caption text, scientific result, or",
        "comparison target is copied from the article. Every status is calculated from files present",
        "in this self-contained package.",
        "",
        "## Status totals",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Item-level coverage",
            "",
            "| Item | Topic | Computed status | Package evidence | Reason |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        evidence = row["evidence"].replace(";", "<br>") or "-"
        reason = row["reason"].replace("|", "\\|")
        lines.append(
            f"| {row['item']} | {row['topic']} | `{row['status']}` | {evidence} | {reason} |"
        )
    lines.extend(
        [
            "",
            "A missing item remains missing until a machine-readable source or a new real execution",
            "is added under `inputs/` or `results/dev/` and the end-to-end script is rerun.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    rows = compute_rows()
    TABLES.mkdir(parents=True, exist_ok=True)
    with (TABLES / "reproduction_coverage.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("item", "topic", "status", "evidence", "reason"))
        writer.writeheader()
        writer.writerows(rows)
    (ROOT / "REPRODUCTION_COVERAGE.md").write_text(markdown_report(rows), encoding="utf-8")
    print(markdown_report(rows))


if __name__ == "__main__":
    main()
