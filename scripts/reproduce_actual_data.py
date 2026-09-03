#!/usr/bin/env python3
"""Generate tables and vector figures only from machine-readable raw inputs.

This module deliberately does not open, parse, or transcribe the article PDF or
its rendered pages.  Every scientific number written below is calculated from
the CSV files under ``inputs/`` during the current invocation.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "inputs" / "release-data"
VALIDATION = ROOT / "inputs" / "official-supplement" / "41524_2024_1470_MOESM2_ESM.csv"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

TRAIN = RELEASE / "PolyGen-train-set-from-HTP-MD.csv"
FULL_TRAIN = RELEASE / "htpmd-trainset.csv"
BINARY_TRAIN = RELEASE / "minGPT" / "htp_md.csv"
GENERATED = RELEASE / "generated_polymers_in_two_iterations.csv"

COLORS = ("#3465a4", "#e67e22", "#2d936c", "#8754a1", "#c43b3b", "#767676")


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def write_csv(path: Path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def numeric_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "minimum": None,
            "q1": None,
            "median": None,
            "mean": None,
            "q3": None,
            "maximum": None,
            "population_standard_deviation": None,
        }
    return {
        "count": len(values),
        "minimum": min(values),
        "q1": quantile(values, 0.25),
        "median": median(values),
        "mean": mean(values),
        "q3": quantile(values, 0.75),
        "maximum": max(values),
        "population_standard_deviation": pstdev(values),
    }


def floats(rows: Iterable[dict[str, str]], column: str) -> list[float]:
    return [float(row[column]) for row in rows if row.get(column, "").strip()]


def box_statistics(values: Sequence[float]) -> dict[str, object]:
    q1 = quantile(values, 0.25)
    center = quantile(values, 0.5)
    q3 = quantile(values, 0.75)
    iqr = q3 - q1
    lower_limit = q1 - 1.5 * iqr
    upper_limit = q3 + 1.5 * iqr
    lower = min(value for value in values if value >= lower_limit)
    upper = max(value for value in values if value <= upper_limit)
    return {
        "q1": q1,
        "median": center,
        "q3": q3,
        "whisker_low": lower,
        "whisker_high": upper,
        "outliers": [value for value in values if value < lower or value > upper],
    }


def validation_groups(rows: Sequence[dict[str, str]]) -> list[dict]:
    """Group validation attempts without renaming, reordering, or dropping a group."""
    grouped: dict[str, list[dict[str, str]]] = {}
    replica_pattern = re.compile(r"^(?P<group>.+)_rep(?P<replica>[0-9]+)$")
    for row_number, row in enumerate(rows, start=1):
        match = replica_pattern.match(row["simulation_name"])
        if match is None:
            raise ValueError(f"cannot derive group from input row {row_number}: {row['simulation_name']!r}")
        grouped.setdefault(match.group("group"), []).append(row)

    output: list[dict] = []
    for input_order, (group_name, attempts) in enumerate(grouped.items(), start=1):
        values = floats(attempts, "ionic_conductivity(S/cm)")
        reasons = Counter(
            row["incomplete"]
            for row in attempts
            if not row["ionic_conductivity(S/cm)"].strip()
        )
        output.append(
            {
                "input_order": input_order,
                "simulation_group": group_name,
                "monomer_smiles": attempts[0]["monomer_smiles"],
                "attempted_replicas": len(attempts),
                "completed_replicas": len(values),
                "incomplete_replicas": len(attempts) - len(values),
                "incomplete_reasons": dict(sorted(reasons.items())),
                "replica_values": values,
                "mean_conductivity_s_per_cm": mean(values) if values else None,
            }
        )
    return output


def validation_table_rows(groups: Sequence[dict]) -> list[dict]:
    records: list[dict] = []
    for group in groups:
        values = group["replica_values"]
        stats = box_statistics(values) if values else {}
        records.append(
            {
                "input_order": group["input_order"],
                "simulation_group": group["simulation_group"],
                "monomer_smiles": group["monomer_smiles"],
                "attempted_replicas": group["attempted_replicas"],
                "completed_replicas": group["completed_replicas"],
                "incomplete_replicas": group["incomplete_replicas"],
                "incomplete_reasons": json.dumps(group["incomplete_reasons"], sort_keys=True),
                "mean_conductivity_s_per_cm": group["mean_conductivity_s_per_cm"] if values else "",
                "q1": stats.get("q1", ""),
                "median": stats.get("median", ""),
                "q3": stats.get("q3", ""),
                "whisker_low": stats.get("whisker_low", ""),
                "whisker_high": stats.get("whisker_high", ""),
                "outliers_s_per_cm": ";".join(map(str, stats.get("outliers", []))),
                "replica_values_s_per_cm": ";".join(map(str, values)),
            }
        )
    return records


def generated_iteration_rows(rows: Sequence[dict[str, str]]) -> list[dict]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["iteration_num"], []).append(row)
    output: list[dict] = []
    for iteration, members in grouped.items():
        completed = [row for row in members if row["conductivity_s_per_cm"].strip()]
        conductivity = floats(completed, "conductivity_s_per_cm")
        transference = floats(completed, "transference_number")
        output.append(
            {
                "iteration": iteration,
                "rows": len(members),
                "unique_monomer_smiles": len({row["monomer_smiles"] for row in members}),
                "completed_rows": len(completed),
                "failed_rows": len(members) - len(completed),
                "conductivity_minimum_s_per_cm": min(conductivity) if conductivity else "",
                "conductivity_median_s_per_cm": median(conductivity) if conductivity else "",
                "conductivity_mean_s_per_cm": mean(conductivity) if conductivity else "",
                "conductivity_maximum_s_per_cm": max(conductivity) if conductivity else "",
                "transference_minimum": min(transference) if transference else "",
                "transference_median": median(transference) if transference else "",
                "transference_mean": mean(transference) if transference else "",
                "transference_maximum": max(transference) if transference else "",
            }
        )
    return output


def compute_all() -> dict:
    train_rows = read_csv(TRAIN)
    full_train_rows = read_csv(FULL_TRAIN)
    binary_rows = read_csv(BINARY_TRAIN, delimiter="\t")
    generated_rows = read_csv(GENERATED)
    validation_rows = read_csv(VALIDATION)
    groups = validation_groups(validation_rows)

    train_conductivity = floats(train_rows, "conductivity")
    full_conductivity = floats(full_train_rows, "conductivity")
    full_transference = floats(full_train_rows, "transference_number")
    generated_conductivity = floats(generated_rows, "conductivity_s_per_cm")
    generated_transference = floats(generated_rows, "transference_number")
    validation_values = [value for group in groups for value in group["replica_values"]]
    group_means = [
        group["mean_conductivity_s_per_cm"]
        for group in groups
        if group["mean_conductivity_s_per_cm"] is not None
    ]

    row_class_counts = Counter(row["conductivity"] for row in binary_rows)
    unique_labels: dict[str, str] = {}
    conflicting_labels: list[str] = []
    for row in binary_rows:
        previous = unique_labels.setdefault(row["mol_smiles"], row["conductivity"])
        if previous != row["conductivity"]:
            conflicting_labels.append(row["mol_smiles"])
    unique_class_counts = Counter(unique_labels.values())
    conductivity_by_smiles = {row["mol_smiles"]: float(row["conductivity"]) for row in train_rows}
    unmatched = sorted(smiles for smiles in unique_labels if smiles not in conductivity_by_smiles)
    class_conductivity = {
        label: [
            conductivity_by_smiles[smiles]
            for smiles, assigned in unique_labels.items()
            if assigned == label and smiles in conductivity_by_smiles
        ]
        for label in sorted(unique_class_counts)
    }

    failure_reasons = Counter(
        row["incomplete"]
        for row in validation_rows
        if not row["ionic_conductivity(S/cm)"].strip()
    )
    threshold = max(train_conductivity)
    generated_iterations = generated_iteration_rows(generated_rows)

    summary = {
        "data_policy": "Every scientific value in this file was computed from machine-readable input files by scripts/reproduce_actual_data.py; no PDF value was used.",
        "release_training_data": {
            "rows": len(train_rows),
            "unique_mol_smiles": len({row["mol_smiles"] for row in train_rows}),
            "conductivity_s_per_cm": numeric_summary(train_conductivity),
        },
        "full_training_data": {
            "rows": len(full_train_rows),
            "unique_mol_smiles": len({row["mol_smiles"] for row in full_train_rows}),
            "conductivity_s_per_cm": numeric_summary(full_conductivity),
            "transference_number": numeric_summary(full_transference),
        },
        "binary_training_data": {
            "rows": len(binary_rows),
            "unique_mol_smiles": len(unique_labels),
            "row_class_counts": dict(sorted(row_class_counts.items())),
            "unique_class_counts": dict(sorted(unique_class_counts.items())),
            "conflicting_label_count": len(set(conflicting_labels)),
            "unmatched_to_release_training_count": len(unmatched),
            "unique_class_conductivity_s_per_cm": {
                label: numeric_summary(values) for label, values in class_conductivity.items()
            },
        },
        "generated_polymers_two_iterations": {
            "rows": len(generated_rows),
            "unique_monomer_smiles": len({row["monomer_smiles"] for row in generated_rows}),
            "completed_rows": len(generated_conductivity),
            "failed_rows": len(generated_rows) - len(generated_conductivity),
            "conductivity_s_per_cm": numeric_summary(generated_conductivity),
            "transference_number": numeric_summary(generated_transference),
            "iterations": generated_iterations,
        },
        "validation_md": {
            "attempt_rows": len(validation_rows),
            "completed_rows": len(validation_values),
            "incomplete_rows": len(validation_rows) - len(validation_values),
            "failure_reason_counts": dict(sorted(failure_reasons.items())),
            "candidate_groups": len(groups),
            "candidate_groups_with_completed_replicas": len(group_means),
            "candidate_groups_without_completed_replicas": len(groups) - len(group_means),
            "replica_conductivity_s_per_cm": numeric_summary(validation_values),
            "candidate_mean_conductivity_s_per_cm": numeric_summary(group_means),
            "release_training_maximum_s_per_cm": threshold,
            "candidate_means_above_release_training_maximum": sum(value > threshold for value in group_means),
        },
        "cross_checks": {
            "training_row_counts_equal": len(train_rows) == len(full_train_rows),
            "training_smiles_sets_equal": {
                row["mol_smiles"] for row in train_rows
            } == {row["mol_smiles"] for row in full_train_rows},
        },
    }
    return {
        "summary": summary,
        "validation_groups": groups,
        "validation_table_rows": validation_table_rows(groups),
        "generated_iteration_rows": generated_iterations,
        "train_rows": train_rows,
        "binary_rows": binary_rows,
        "generated_rows": generated_rows,
        "validation_rows": validation_rows,
        "class_conductivity": class_conductivity,
        "train_conductivity": train_conductivity,
        "generated_conductivity": generated_conductivity,
        "validation_values": validation_values,
    }


def svg_document(width: int, height: int, title: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<style>text{{font-family:Arial,Helvetica,sans-serif;fill:#222}} .axis{{stroke:#333;stroke-width:1}} .grid{{stroke:#dedede;stroke-width:1}} .label{{font-size:13px}} .small{{font-size:11px}} .title{{font-size:20px;font-weight:700}} .panel{{font-size:15px;font-weight:700}}</style>
<text x="{width / 2:.1f}" y="29" text-anchor="middle" class="title">{html.escape(title)}</text>
{body}
</svg>'''


def axes(x: float, y: float, width: float, height: float, xlabel: str, ylabel: str) -> str:
    return (
        f'<line x1="{x}" y1="{y + height}" x2="{x + width}" y2="{y + height}" class="axis"/>'
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + height}" class="axis"/>'
        f'<text x="{x + width / 2}" y="{y + height + 42}" text-anchor="middle" class="label">{html.escape(xlabel)}</text>'
        f'<text x="{x - 48}" y="{y + height / 2}" text-anchor="middle" transform="rotate(-90 {x - 48} {y + height / 2})" class="label">{html.escape(ylabel)}</text>'
    )


def padded_range(values: Sequence[float], fraction: float = 0.05) -> tuple[float, float]:
    low = min(values)
    high = max(values)
    span = high - low
    if span == 0:
        span = abs(high) if high else 1.0
    return low - span * fraction, high + span * fraction


def histogram(values: Sequence[float], low: float, high: float, bins: int) -> list[int]:
    counts = [0] * bins
    span = high - low
    for value in values:
        index = min(bins - 1, max(0, int((value - low) / span * bins)))
        counts[index] += 1
    return counts


def histogram_panel(
    series: Sequence[tuple[str, Sequence[float]]],
    x: float,
    y: float,
    width: float,
    height: float,
    xlabel: str,
) -> str:
    combined = [value for _, values in series for value in values]
    low, high = padded_range(combined)
    scientific_ticks = max(abs(low), abs(high)) < 0.01 or max(abs(low), abs(high)) >= 10000
    bins = max(12, min(48, round(math.sqrt(len(combined)))))
    records = [(name, histogram(values, low, high, bins), len(values)) for name, values in series]
    peak = max(count / total for _, counts, total in records for count in counts if total)
    body = [axes(x, y, width, height, xlabel, "fraction per bin")]
    for tick in range(6):
        value = low + (high - low) * tick / 5
        tx = x + width * tick / 5
        tick_text = f"{value:.2e}" if scientific_ticks else f"{value:.2f}"
        body.append(
            f'<line x1="{tx}" y1="{y + height}" x2="{tx}" y2="{y + height + 5}" class="axis"/>'
            f'<text x="{tx}" y="{y + height + 19}" text-anchor="middle" class="small">{tick_text}</text>'
        )
    for series_index, (name, counts, total) in enumerate(records):
        points = []
        for index, count in enumerate(counts):
            px = x + (index + 0.5) / bins * width
            py = y + height - (count / total) / peak * height if total and peak else y + height
            points.append(f"{px:.2f},{py:.2f}")
        color = COLORS[series_index % len(COLORS)]
        body.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>'
        )
        legend_y = y + 18 + series_index * 19
        body.append(
            f'<line x1="{x + width - 185}" y1="{legend_y}" x2="{x + width - 160}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>'
            f'<text x="{x + width - 153}" y="{legend_y + 4}" class="small">{html.escape(name)} (n={total})</text>'
        )
    return "".join(body)


def render_class_balance(data: dict) -> None:
    binary_rows = data["binary_rows"]
    train_map = {row["mol_smiles"]: float(row["conductivity"]) for row in data["train_rows"]}
    unique_labels: dict[str, str] = {}
    for row in binary_rows:
        unique_labels.setdefault(row["mol_smiles"], row["conductivity"])
    labels = sorted({row["conductivity"] for row in binary_rows})
    before = [
        (
            f"class {label}",
            [math.log10(train_map[smiles]) for smiles, value in unique_labels.items() if value == label and smiles in train_map],
        )
        for label in labels
    ]
    after = [
        (
            f"class {label}",
            [math.log10(train_map[row["mol_smiles"]]) for row in binary_rows if row["conductivity"] == label and row["mol_smiles"] in train_map],
        )
        for label in labels
    ]
    body = [
        histogram_panel(before, 78, 78, 485, 350, "log10 conductivity (S/cm)"),
        histogram_panel(after, 665, 78, 485, 350, "log10 conductivity (S/cm)"),
        '<text x="320" y="60" text-anchor="middle" class="panel">Unique rows before duplication</text>',
        '<text x="905" y="60" text-anchor="middle" class="panel">Rows in released binary training file</text>',
        '<text x="615" y="505" text-anchor="middle" class="small">Generated directly from the two released training CSVs; class names are preserved exactly as stored.</text>',
    ]
    (FIGURES / "actual_training_class_balance.svg").write_text(
        svg_document(1230, 530, "Actual released class distributions", "".join(body)),
        encoding="utf-8",
    )


def render_conductivity_distributions(data: dict) -> None:
    series = [
        ("release training", data["train_conductivity"]),
        ("generated iterations", data["generated_conductivity"]),
        ("validation replicas", data["validation_values"]),
    ]
    body = histogram_panel(series, 90, 70, 850, 390, "conductivity (S/cm)")
    body += '<text x="515" y="520" text-anchor="middle" class="small">Linear scale retains zero-valued rows; every curve is recomputed from a machine-readable input.</text>'
    (FIGURES / "actual_conductivity_distributions.svg").write_text(
        svg_document(1030, 545, "Actual conductivity distributions from released data", body),
        encoding="utf-8",
    )


def render_validation_boxplots(data: dict) -> None:
    groups = [group for group in data["validation_groups"] if group["replica_values"]]
    threshold = max(data["train_conductivity"])
    all_values = [value for group in groups for value in group["replica_values"]] + [threshold]
    low, high = padded_range(all_values, fraction=0.06)
    x, y, width, height = 90, 70, 1640, 460

    def py(value: float) -> float:
        return y + height - (value - low) / (high - low) * height

    body = [axes(x, y, width, height, "validation group in first-input order", "conductivity (S/cm)")]
    for tick in range(7):
        value = low + (high - low) * tick / 6
        ty = py(value)
        body.append(
            f'<line x1="{x}" y1="{ty}" x2="{x + width}" y2="{ty}" class="grid"/>'
            f'<text x="{x - 10}" y="{ty + 4}" text-anchor="end" class="small">{value:.3e}</text>'
        )
    for index, group in enumerate(groups):
        stats = box_statistics(group["replica_values"])
        cx = x + (index + 0.5) / len(groups) * width
        box_width = width / len(groups) * 0.62
        color = COLORS[index % len(COLORS)]
        q1y, q3y = py(stats["q1"]), py(stats["q3"])
        lowy, highy = py(stats["whisker_low"]), py(stats["whisker_high"])
        medy = py(stats["median"])
        body.extend(
            [
                f'<line x1="{cx}" y1="{highy}" x2="{cx}" y2="{lowy}" stroke="#333"/>',
                f'<line x1="{cx - box_width * 0.3}" y1="{highy}" x2="{cx + box_width * 0.3}" y2="{highy}" stroke="#333"/>',
                f'<line x1="{cx - box_width * 0.3}" y1="{lowy}" x2="{cx + box_width * 0.3}" y2="{lowy}" stroke="#333"/>',
                f'<rect x="{cx - box_width / 2}" y="{q3y}" width="{box_width}" height="{max(1, q1y - q3y)}" fill="{color}" fill-opacity="0.75" stroke="#333"/>',
                f'<line x1="{cx - box_width / 2}" y1="{medy}" x2="{cx + box_width / 2}" y2="{medy}" stroke="#222" stroke-width="1.5"/>',
                f'<text x="{cx + 2}" y="{y + height + 8}" transform="rotate(90 {cx + 2} {y + height + 8})" class="small">{html.escape(group["simulation_group"])}</text>',
                f'<title>{html.escape(group["simulation_group"])}; completed={group["completed_replicas"]}; mean={group["mean_conductivity_s_per_cm"]:.12g}</title>',
            ]
        )
        for outlier in stats["outliers"]:
            oy = py(outlier)
            body.append(f'<circle cx="{cx}" cy="{oy}" r="2.5" fill="#222"/>')
    threshold_y = py(threshold)
    above = sum(group["mean_conductivity_s_per_cm"] > threshold for group in groups)
    body.append(
        f'<line x1="{x}" y1="{threshold_y}" x2="{x + width}" y2="{threshold_y}" stroke="#c43b3b" stroke-width="2" stroke-dasharray="8 5"/>'
        f'<rect x="{x + 8}" y="{y + 7}" width="560" height="24" fill="white" fill-opacity="0.92"/>'
        f'<text x="{x + 18}" y="{y + 24}" class="small">computed release-training maximum = {threshold:.8g} S/cm; computed group means above it = {above}/{len(groups)}</text>'
        f'<text x="{x + width / 2}" y="750" text-anchor="middle" class="small">All groups with completed replicas are included in first appearance order from the validation CSV.</text>'
    )
    (FIGURES / "actual_validation_md_boxplots.svg").write_text(
        svg_document(1820, 780, "Actual validation-MD replica distributions", "".join(body)),
        encoding="utf-8",
    )


def write_input_manifest() -> None:
    paths = sorted(path for path in (ROOT / "inputs").rglob("*") if path.is_file())
    rows = [
        {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in paths
    ]
    write_csv(TABLES / "input_manifest.csv", rows, ("path", "bytes", "sha256"))


def write_provenance_manifest() -> None:
    raw_inputs = ";".join(
        str(path.relative_to(ROOT))
        for path in sorted(path for path in (ROOT / "inputs").rglob("*") if path.is_file())
    )
    generated_paths = [
        TABLES / "dataset_summary.json",
        TABLES / "md_candidate_summary.csv",
        TABLES / "generated_iteration_summary.csv",
        TABLES / "input_manifest.csv",
        FIGURES / "actual_training_class_balance.svg",
        FIGURES / "actual_conductivity_distributions.svg",
        FIGURES / "actual_validation_md_boxplots.svg",
    ]
    rows = [
        {
            "artifact": str(path.relative_to(ROOT)),
            "generator": "scripts/reproduce_actual_data.py",
            "machine_readable_inputs": raw_inputs,
        }
        for path in generated_paths
    ]
    write_csv(
        TABLES / "raw_output_provenance.csv",
        rows,
        ("artifact", "generator", "machine_readable_inputs"),
    )


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = compute_all()
    (TABLES / "dataset_summary.json").write_text(
        json.dumps(data["summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    validation_rows = data["validation_table_rows"]
    write_csv(TABLES / "md_candidate_summary.csv", validation_rows, tuple(validation_rows[0]))
    iteration_rows = data["generated_iteration_rows"]
    write_csv(TABLES / "generated_iteration_summary.csv", iteration_rows, tuple(iteration_rows[0]))
    write_input_manifest()
    render_class_balance(data)
    render_conductivity_distributions(data)
    render_validation_boxplots(data)
    write_provenance_manifest()
    print(json.dumps(data["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
