#!/usr/bin/env python3
"""Summarize files produced by real DEV executions without benchmark constants."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "results" / "dev"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
COLORS = ("#3465a4", "#e67e22", "#2d936c", "#8754a1", "#c43b3b", "#767676")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def csv_metadata(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        rows = list(reader)
    return {
        "path": str(path.relative_to(ROOT)),
        "data_rows": max(0, len(rows) - 1),
        "columns": rows[0] if rows else [],
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def write_csv(path: Path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute_summary() -> dict:
    json_records = []
    for path in sorted(DEV.rglob("*.json")):
        json_records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
                "content": json.loads(path.read_text(encoding="utf-8")),
            }
        )
    csv_records = [csv_metadata(path) for path in sorted(DEV.rglob("*.csv"))]
    csv_by_path = {record["path"]: record for record in csv_records}

    consistency = []
    for record in json_records:
        path = ROOT / record["path"]
        content = record["content"]
        if path.name == "metrics.json" and "num_samples" in content:
            sample_path = path.with_name("samples.csv")
            if sample_path.is_file():
                observed = csv_by_path[str(sample_path.relative_to(ROOT))]["data_rows"]
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "num_samples",
                        "observed_source": str(sample_path.relative_to(ROOT)),
                        "claimed": content["num_samples"],
                        "observed": observed,
                        "matches": content["num_samples"] == observed,
                    }
                )
        if path.name == "metrics.json" and "selected_rows" in content:
            sample_path = path.with_name("scored_samples.csv")
            if sample_path.is_file():
                observed = csv_by_path[str(sample_path.relative_to(ROOT))]["data_rows"]
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "selected_rows",
                        "observed_source": str(sample_path.relative_to(ROOT)),
                        "claimed": content["selected_rows"],
                        "observed": observed,
                        "matches": content["selected_rows"] == observed,
                    }
                )
        if path.name == "sample_summary.json" and "samples" in content:
            sample_path = path.with_name("decoded_samples.csv")
            if sample_path.is_file():
                observed = csv_by_path[str(sample_path.relative_to(ROOT))]["data_rows"]
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "samples",
                        "observed_source": str(sample_path.relative_to(ROOT)),
                        "claimed": content["samples"],
                        "observed": observed,
                        "matches": content["samples"] == observed,
                    }
                )
        if path.name == "run_provenance.json":
            for filename, claim_field in (
                ("metrics.json", "metrics_sha256"),
                ("samples.csv", "samples_sha256"),
            ):
                observed_path = path.with_name(filename)
                if observed_path.is_file() and claim_field in content:
                    observed = digest(observed_path)
                    consistency.append(
                        {
                            "claim_source": record["path"],
                            "claim_field": claim_field,
                            "observed_source": str(observed_path.relative_to(ROOT)),
                            "claimed": content[claim_field],
                            "observed": observed,
                            "matches": content[claim_field] == observed,
                        }
                    )
            local_runner = ROOT / "scripts" / "run_mingpt_checkpoint.py"
            if "runner_sha256" in content:
                observed = digest(local_runner)
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "runner_sha256",
                        "observed_source": str(local_runner.relative_to(ROOT)),
                        "claimed": content["runner_sha256"],
                        "observed": observed,
                        "matches": content["runner_sha256"] == observed,
                    }
                )
            local_checkpoint = ROOT / "vendor" / "PolyGen-1.0.0" / "minGPT" / "ckpts" / "10000.pt"
            if "checkpoint_sha256" in content and local_checkpoint.is_file():
                observed = digest(local_checkpoint)
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "checkpoint_sha256",
                        "observed_source": str(local_checkpoint.relative_to(ROOT)),
                        "claimed": content["checkpoint_sha256"],
                        "observed": observed,
                        "matches": content["checkpoint_sha256"] == observed,
                    }
                )
            consistency.append(
                {
                    "claim_source": record["path"],
                    "claim_field": "bundled_repo_used",
                    "observed_source": record["path"],
                    "claimed": content.get("bundled_repo_used"),
                    "observed": True,
                    "matches": content.get("bundled_repo_used") is True,
                }
            )
        if path.name == "run_summary.json" and isinstance(content.get("artifacts"), dict):
            artifacts = content["artifacts"]
            for filename, claim_field in (
                ("loss_history.csv", "loss_history_sha256"),
                ("samples.csv", "samples_sha256"),
            ):
                observed_path = path.with_name(filename)
                if observed_path.is_file() and claim_field in artifacts:
                    observed = digest(observed_path)
                    consistency.append(
                        {
                            "claim_source": record["path"],
                            "claim_field": f"artifacts.{claim_field}",
                            "observed_source": str(observed_path.relative_to(ROOT)),
                            "claimed": artifacts[claim_field],
                            "observed": observed,
                            "matches": artifacts[claim_field] == observed,
                        }
                    )
            local_runner = ROOT / "scripts" / "run_mingpt_training.py"
            if "runner_sha256" in artifacts:
                observed = digest(local_runner)
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "artifacts.runner_sha256",
                        "observed_source": str(local_runner.relative_to(ROOT)),
                        "claimed": artifacts["runner_sha256"],
                        "observed": observed,
                        "matches": artifacts["runner_sha256"] == observed,
                    }
                )
            local_dataset = ROOT / "vendor" / "PolyGen-1.0.0" / "minGPT" / "htp_md.csv"
            if "dataset_sha256" in artifacts:
                observed = digest(local_dataset)
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "artifacts.dataset_sha256",
                        "observed_source": str(local_dataset.relative_to(ROOT)),
                        "claimed": artifacts["dataset_sha256"],
                        "observed": observed,
                        "matches": artifacts["dataset_sha256"] == observed,
                    }
                )
            training = content.get("training", {})
            local_start = ROOT / "vendor" / "PolyGen-1.0.0" / "minGPT" / "ckpts" / "10000.pt"
            if training.get("starting_checkpoint_sha256"):
                observed = digest(local_start)
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "training.starting_checkpoint_sha256",
                        "observed_source": str(local_start.relative_to(ROOT)),
                        "claimed": training["starting_checkpoint_sha256"],
                        "observed": observed,
                        "matches": training["starting_checkpoint_sha256"] == observed,
                    }
                )
            sample_path = path.with_name("samples.csv")
            if sample_path.is_file() and "generation" in content:
                observed = csv_by_path[str(sample_path.relative_to(ROOT))]["data_rows"]
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "generation.num_samples",
                        "observed_source": str(sample_path.relative_to(ROOT)),
                        "claimed": content["generation"].get("num_samples"),
                        "observed": observed,
                        "matches": content["generation"].get("num_samples") == observed,
                    }
                )
            loss_path = path.with_name("loss_history.csv")
            if loss_path.is_file() and "training" in content:
                observed = csv_by_path[str(loss_path.relative_to(ROOT))]["data_rows"]
                consistency.append(
                    {
                        "claim_source": record["path"],
                        "claim_field": "training.loss_rows",
                        "observed_source": str(loss_path.relative_to(ROOT)),
                        "claimed": content["training"].get("loss_rows"),
                        "observed": observed,
                        "matches": content["training"].get("loss_rows") == observed,
                    }
                )

    metrics = []
    for record in json_records:
        content = record["content"]
        if not isinstance(content, dict) or not isinstance(content.get("metrics"), dict):
            continue
        run = str(Path(record["path"]).parent.relative_to("results/dev"))
        for metric, value in sorted(content["metrics"].items()):
            metrics.append(
                {
                    "run": run,
                    "metric": metric,
                    "value": "" if value is None else value,
                    "source": record["path"],
                }
            )

    return {
        "summary": {
            "data_policy": "Every value in this file is read from a real execution artifact under results/dev and cross-checked where a matching sample CSV exists; no paper value is used.",
            "json_artifacts": json_records,
            "csv_artifacts": csv_records,
            "internal_consistency_checks": consistency,
        },
        "metrics": metrics,
        "json_records": json_records,
    }


def svg_document(width: int, height: int, title: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<style>text{{font-family:Arial,Helvetica,sans-serif;fill:#222}} .axis{{stroke:#333;stroke-width:1}} .grid{{stroke:#dedede;stroke-width:1}} .label{{font-size:13px}} .small{{font-size:11px}} .title{{font-size:20px;font-weight:700}} .panel{{font-size:15px;font-weight:700}}</style>
<text x="{width / 2:.1f}" y="29" text-anchor="middle" class="title">{html.escape(title)}</text>
{body}
</svg>'''


def render_metrics(metrics: Sequence[dict]) -> None:
    usable = [row for row in metrics if row["value"] != ""]
    runs = list(dict.fromkeys(row["run"] for row in usable))
    names = sorted({row["metric"] for row in usable})
    lookup = {(row["run"], row["metric"]): float(row["value"]) for row in usable}
    x, y, width, height = 90, 70, 1020, 390
    body = [
        f'<line x1="{x}" y1="{y + height}" x2="{x + width}" y2="{y + height}" class="axis"/>',
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + height}" class="axis"/>',
    ]
    for tick in range(6):
        value = tick / 5
        ty = y + height - value * height
        body.append(
            f'<line x1="{x}" y1="{ty}" x2="{x + width}" y2="{ty}" class="grid"/>'
            f'<text x="{x - 10}" y="{ty + 4}" text-anchor="end" class="small">{value:.1f}</text>'
        )
    group_width = width / max(1, len(names))
    bar_width = group_width / max(1, len(runs) + 1)
    for metric_index, metric in enumerate(names):
        for run_index, run in enumerate(runs):
            value = lookup.get((run, metric))
            if value is None:
                continue
            bx = x + metric_index * group_width + (run_index + 0.5) * bar_width
            bar_height = value * height
            body.append(
                f'<rect x="{bx}" y="{y + height - bar_height}" width="{bar_width * 0.78}" height="{bar_height}" fill="{COLORS[run_index % len(COLORS)]}"/>'
            )
        tx = x + (metric_index + 0.5) * group_width
        body.append(
            f'<text x="{tx}" y="{y + height + 12}" transform="rotate(28 {tx} {y + height + 12})" class="small">{html.escape(metric)}</text>'
        )
    for index, run in enumerate(runs):
        legend_y = 485 + index * 19
        body.append(
            f'<rect x="120" y="{legend_y - 11}" width="15" height="15" fill="{COLORS[index % len(COLORS)]}"/>'
            f'<text x="142" y="{legend_y + 1}" class="small">{html.escape(run)}</text>'
        )
    body.append(
        '<text x="600" y="570" text-anchor="middle" class="small">Bars are generated only from metrics.json files produced or rescored on DEV; absent metrics remain absent.</text>'
    )
    (FIGURES / "actual_dev_model_metrics.svg").write_text(
        svg_document(1200, 595, "Actual DEV model-evaluation metrics", "".join(body)),
        encoding="utf-8",
    )


def render_diffusion_diagnostics(json_records: Sequence[dict]) -> None:
    runs = []
    for record in json_records:
        content = record["content"]
        if not isinstance(content, dict) or "steps" not in content or "elapsed_seconds" not in content:
            continue
        runs.append(
            {
                "run": str(Path(record["path"]).parent.relative_to("results/dev")),
                "steps": float(content["steps"]),
                "elapsed": float(content["elapsed_seconds"]),
                "train_loss": content.get("train_loss_last_recorded"),
                "validation_loss": content.get("validation_loss_last_recorded"),
            }
        )
    if not runs:
        return
    x_positions = [185 + index * 250 for index in range(len(runs))]
    body: list[str] = []
    panels = (
        ("steps", "training steps", 70, 310),
        ("elapsed", "elapsed seconds", 430, 310),
    )
    for field, label, panel_x, panel_width in panels:
        panel_y, panel_height = 80, 310
        peak = max(run[field] for run in runs)
        body.append(
            f'<line x1="{panel_x}" y1="{panel_y + panel_height}" x2="{panel_x + panel_width}" y2="{panel_y + panel_height}" class="axis"/>'
            f'<line x1="{panel_x}" y1="{panel_y}" x2="{panel_x}" y2="{panel_y + panel_height}" class="axis"/>'
            f'<text x="{panel_x + panel_width / 2}" y="55" text-anchor="middle" class="panel">{html.escape(label)}</text>'
        )
        for index, run in enumerate(runs):
            cx = panel_x + (index + 0.5) / len(runs) * panel_width
            bar_height = run[field] / peak * panel_height if peak else 0
            body.append(
                f'<rect x="{cx - 35}" y="{panel_y + panel_height - bar_height}" width="70" height="{bar_height}" fill="{COLORS[index % len(COLORS)]}"/>'
                f'<text x="{cx}" y="{panel_y + panel_height - bar_height - 8}" text-anchor="middle" class="small">{run[field]:.8g}</text>'
                f'<text x="{cx}" y="{panel_y + panel_height + 15}" text-anchor="middle" class="small">run {index + 1}</text>'
            )
    for index, run in enumerate(runs):
        body.append(
            f'<rect x="90" y="{430 + index * 20}" width="14" height="14" fill="{COLORS[index % len(COLORS)]}"/>'
            f'<text x="112" y="{442 + index * 20}" class="small">run {index + 1}: {html.escape(run["run"])}</text>'
        )
    body.append(
        '<text x="400" y="510" text-anchor="middle" class="small">All bar heights and labels are read from DEV run_summary.json artifacts.</text>'
    )
    (FIGURES / "actual_diffusion1d_run_diagnostics.svg").write_text(
        svg_document(800, 535, "Actual diffusion1D DEV run diagnostics", "".join(body)),
        encoding="utf-8",
    )


def render_mingpt_training_losses() -> None:
    runs = []
    for path in sorted(DEV.rglob("loss_history.csv")):
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if not rows or not {"iteration", "train_loss", "validation_loss"}.issubset(rows[0]):
            continue
        runs.append(
            {
                "run": str(path.parent.relative_to(DEV)),
                "rows": [
                    (int(row["iteration"]), float(row["train_loss"]), float(row["validation_loss"]))
                    for row in rows
                ],
            }
        )
    if not runs:
        return

    values = [value for run in runs for row in run["rows"] for value in row[1:]]
    low, high = min(values), max(values)
    padding = (high - low) * 0.08 if high > low else max(abs(high) * 0.08, 0.01)
    low -= padding
    high += padding
    x, y, width, height = 95, 70, 1000, 390
    max_iteration = max(row[0] for run in runs for row in run["rows"])
    body = [
        f'<line x1="{x}" y1="{y + height}" x2="{x + width}" y2="{y + height}" class="axis"/>',
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + height}" class="axis"/>',
    ]
    for tick in range(6):
        value = low + (high - low) * tick / 5
        ty = y + height - tick * height / 5
        body.append(
            f'<line x1="{x}" y1="{ty}" x2="{x + width}" y2="{ty}" class="grid"/>'
            f'<text x="{x - 10}" y="{ty + 4}" text-anchor="end" class="small">{value:.4g}</text>'
        )
    for tick in range(6):
        iteration = max_iteration * tick / 5
        tx = x + width * tick / 5
        body.append(
            f'<text x="{tx}" y="{y + height + 20}" text-anchor="middle" class="small">{iteration:.0f}</text>'
        )

    for index, run in enumerate(runs):
        for series_index, (column_index, label) in enumerate(((1, "train"), (2, "validation"))):
            color = COLORS[(index * 2 + series_index) % len(COLORS)]
            points = []
            for row in run["rows"]:
                px = x + (row[0] - 1) / max(1, max_iteration - 1) * width
                py = y + height - (row[column_index] - low) / (high - low) * height
                points.append(f"{px:.2f},{py:.2f}")
            body.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>'
            )
            legend_y = 500 + (index * 2 + series_index) * 19
            body.append(
                f'<line x1="120" y1="{legend_y - 4}" x2="145" y2="{legend_y - 4}" stroke="{color}" stroke-width="3"/>'
                f'<text x="153" y="{legend_y}" class="small">{html.escape(run["run"])} — {label}</text>'
            )
    body.extend(
        [
            '<text x="595" y="495" text-anchor="middle" class="small">Every point is read from a DEV-generated loss_history.csv file.</text>',
            '<text x="595" y="555" text-anchor="middle" class="label">training iteration</text>',
            '<text x="20" y="265" transform="rotate(-90 20 265)" text-anchor="middle" class="label">cross-entropy loss</text>',
        ]
    )
    (FIGURES / "actual_mingpt_smoke_losses.svg").write_text(
        svg_document(1200, 580, "Actual minGPT lightweight smoke losses", "".join(body)),
        encoding="utf-8",
    )


def kozo_probe_report(json_records: Sequence[dict]) -> str:
    probes = [
        record["content"]
        for record in json_records
        if isinstance(record["content"], dict) and "probe_policy" in record["content"]
    ]
    if len(probes) != 1:
        raise ValueError(f"expected exactly one KO-POCHI probe artifact, found {len(probes)}")
    probe = probes[0]
    lines = [
        "# Actual KO-POCHI / ARC DEV end-to-end probe",
        "",
        probe["probe_policy"],
        "",
        f"- Core database chain passed: `{str(probe['core_checks_passed']).lower()}`",
        f"- Every launcher health URL was reachable: `{str(probe['registry_checks']['every_registry_health_reachable']).lower()}`",
        f"- Every launcher entry was semantically healthy: `{str(probe['registry_checks']['every_registry_entry_healthy']).lower()}`",
        f"- Full launcher aggregate passed: `{str(probe['all_checks_passed']).lower()}`",
        "",
        "## Launcher health matrix",
        "",
        "| App | Health path | HTTP reachable | Semantic health | Status fields | Error fields |",
        "|---|---|---:|---:|---|---|",
    ]
    for entry in probe["launcher_registry"]["entry_health"]:
        status_fields = json.dumps(entry.get("status_fields", {}), sort_keys=True).replace("|", "\\|")
        error_fields = json.dumps(entry.get("error_fields", {}), sort_keys=True).replace("|", "\\|")
        lines.append(
            f"| {entry.get('name')} | `{entry.get('health_path')}` | "
            f"{str(entry.get('reachable')).lower()} | {str(entry.get('healthy')).lower()} | "
            f"`{status_fields}` | `{error_fields}` |"
        )
    search = probe["database_search"]
    structure = probe["structure_fetch"]
    users = probe["activity_users"]
    lines.extend(
        [
            "",
            "## Database and structure path",
            "",
            f"- Query: `{probe['request']['composition']}`",
            f"- Backend/gateway user responses equal: `{str(users['responses_equal']).lower()}`",
            f"- Expected user match: `{json.dumps(users['expected_gateway_matches'], sort_keys=True)}`",
            f"- Search HTTP status: `{search['http_status']}`",
            f"- Search reported total: `{search['reported_total_count']}`",
            f"- Search returned rows: `{search['returned_count']}`",
            f"- First result: `{json.dumps(search['first_result'], sort_keys=True)}`",
            f"- CIF HTTP status: `{structure['http_status']}`",
            f"- CIF bytes/lines: `{structure['bytes']}` / `{structure['line_count']}`",
            f"- CIF contains atom-site fields: `{str(structure['contains_atom_site_fields']).lower()}`",
            "",
            "This report is regenerated from `results/dev/kozo-dev-e2e-probe.json`; it is not manually maintained.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    computed = compute_summary()
    (TABLES / "dev_execution_summary.json").write_text(
        json.dumps(computed["summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics = computed["metrics"]
    write_csv(TABLES / "dev_metrics_long.csv", metrics, ("run", "metric", "value", "source"))
    render_metrics(metrics)
    render_diffusion_diagnostics(computed["json_records"])
    render_mingpt_training_losses()
    (TABLES / "kozo_dev_e2e_report.md").write_text(
        kozo_probe_report(computed["json_records"]), encoding="utf-8"
    )
    dev_inputs = ";".join(record["path"] for record in computed["summary"]["json_artifacts"] + computed["summary"]["csv_artifacts"])
    provenance_rows = [
        {
            "artifact": "results/tables/dev_execution_summary.json",
            "generator": "scripts/summarize_actual_runs.py",
            "actual_execution_inputs": dev_inputs,
        },
        {
            "artifact": "results/tables/dev_metrics_long.csv",
            "generator": "scripts/summarize_actual_runs.py",
            "actual_execution_inputs": dev_inputs,
        },
        {
            "artifact": "results/figures/actual_dev_model_metrics.svg",
            "generator": "scripts/summarize_actual_runs.py",
            "actual_execution_inputs": dev_inputs,
        },
        {
            "artifact": "results/figures/actual_diffusion1d_run_diagnostics.svg",
            "generator": "scripts/summarize_actual_runs.py",
            "actual_execution_inputs": dev_inputs,
        },
        {
            "artifact": "results/figures/actual_mingpt_smoke_losses.svg",
            "generator": "scripts/summarize_actual_runs.py",
            "actual_execution_inputs": dev_inputs,
        },
        {
            "artifact": "results/tables/kozo_dev_e2e_report.md",
            "generator": "scripts/summarize_actual_runs.py",
            "actual_execution_inputs": "results/dev/kozo-dev-e2e-probe.json",
        },
    ]
    write_csv(
        TABLES / "dev_output_provenance.csv",
        provenance_rows,
        ("artifact", "generator", "actual_execution_inputs"),
    )
    print(json.dumps(computed["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
