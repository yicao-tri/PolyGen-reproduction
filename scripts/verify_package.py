#!/usr/bin/env python3
"""Verify provenance and internal consistency without paper-derived constants."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def stringify_rows(rows: list[dict]) -> list[dict[str, str]]:
    return [{key: str(value) for key, value in row.items()} for row in rows]


def verify_artifact_manifest() -> None:
    manifest_path = TABLES / "artifact_manifest.csv"
    manifest = csv_rows(manifest_path)
    expected_paths = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path != manifest_path and "__pycache__" not in path.parts
    )
    assert [row["path"] for row in manifest] == [str(path.relative_to(ROOT)) for path in expected_paths]
    for row, path in zip(manifest, expected_paths):
        assert int(row["bytes"]) == path.stat().st_size, row["path"]
        assert row["sha256"] == sha256(path), row["path"]


def main() -> None:
    forbidden_directories = [ROOT / "reference", ROOT / "sources"]
    assert not any(path.exists() for path in forbidden_directories), "paper-derived source directory present"
    assert not any(ROOT.rglob("*.pdf")), "PDF files must remain outside the computational package"
    assert not any(ROOT.rglob("*.jpg")), "rendered paper pages must remain outside the computational package"

    vendor = ROOT / "vendor" / "PolyGen-1.0.0"
    required_vendor_files = (
        vendor / "LICENSE",
        vendor / "requirements.txt",
        vendor / "minGPT" / "pipeline.py",
        vendor / "minGPT" / "ckpts" / "10000.pt",
        vendor / "diffusion1D" / "pipeline.py",
        vendor / "diffusion1D" / "model" / "denoising_diffusion_pytorch" / "denoising_diffusion_pytorch_1d_custom.py",
        vendor / "diffusionLM" / "metrics.py",
        vendor / "diffusionLM" / "improved-diffusion" / "improved_diffusion" / "gaussian_diffusion.py",
    )
    assert all(path.is_file() for path in required_vendor_files), "bundled PolyGen source is incomplete"
    assert not any(vendor.rglob("*.pdf")), "vendor must not contain article PDFs"
    assert not any(vendor.rglob("*.png")), "vendor must not contain pre-rendered plots"
    assert not any(vendor.rglob("*.jpg")), "vendor must not contain pre-rendered images"
    assert not any(vendor.rglob("*.ipynb")), "vendor must not contain notebook output"
    assert not (vendor / "diffusion1D" / "ckpts").exists(), "upstream loss artifacts must not be bundled"
    assert not (vendor / "diffusionLM" / "improved-diffusion" / "generation_outputs").exists(), (
        "upstream generated samples must stay in the explicit raw-input area"
    )
    assert "x_val, y_val = batch_val" in (vendor / "minGPT" / "trainer_custom.py").read_text(
        encoding="utf-8"
    )
    assert "from diffusion1D.metrics import *" in (vendor / "diffusion1D" / "pipeline.py").read_text(
        encoding="utf-8"
    )
    assert 'out.find("[SEP]", start + len("[CLS]"))' in (vendor / "minGPT" / "pipeline.py").read_text(
        encoding="utf-8"
    )

    raw_module = load_module("reproduce_actual_data", ROOT / "scripts" / "reproduce_actual_data.py")
    actual = raw_module.compute_all()
    stored_summary = json.loads((TABLES / "dataset_summary.json").read_text(encoding="utf-8"))
    assert stored_summary == actual["summary"], "dataset_summary.json is not a fresh derivation from inputs"
    assert csv_rows(TABLES / "md_candidate_summary.csv") == stringify_rows(actual["validation_table_rows"])
    assert csv_rows(TABLES / "generated_iteration_summary.csv") == stringify_rows(actual["generated_iteration_rows"])

    input_manifest = csv_rows(TABLES / "input_manifest.csv")
    input_paths = sorted(path for path in (ROOT / "inputs").rglob("*") if path.is_file())
    assert [row["path"] for row in input_manifest] == [str(path.relative_to(ROOT)) for path in input_paths]
    for row, path in zip(input_manifest, input_paths):
        assert int(row["bytes"]) == path.stat().st_size, row["path"]
        assert row["sha256"] == sha256(path), row["path"]

    dev_module = load_module("summarize_actual_runs", ROOT / "scripts" / "summarize_actual_runs.py")
    dev_actual = dev_module.compute_summary()
    dev_stored = json.loads((TABLES / "dev_execution_summary.json").read_text(encoding="utf-8"))
    assert dev_stored == dev_actual["summary"], "DEV summary does not match actual result files"
    assert csv_rows(TABLES / "dev_metrics_long.csv") == stringify_rows(dev_actual["metrics"])
    assert (TABLES / "kozo_dev_e2e_report.md").read_text(encoding="utf-8") == dev_module.kozo_probe_report(
        dev_actual["json_records"]
    )
    assert all(check["matches"] for check in dev_stored["internal_consistency_checks"]), "DEV output self-check failed"

    coverage_module = load_module(
        "generate_coverage_report", ROOT / "scripts" / "generate_coverage_report.py"
    )
    coverage_rows = coverage_module.compute_rows()
    assert csv_rows(TABLES / "reproduction_coverage.csv") == coverage_rows
    assert (ROOT / "REPRODUCTION_COVERAGE.md").read_text(encoding="utf-8") == coverage_module.markdown_report(
        coverage_rows
    )

    required_figures = (
        "actual_training_class_balance.svg",
        "actual_conductivity_distributions.svg",
        "actual_validation_md_boxplots.svg",
        "actual_dev_model_metrics.svg",
        "actual_diffusion1d_run_diagnostics.svg",
        "actual_mingpt_smoke_losses.svg",
    )
    for name in required_figures:
        path = FIGURES / name
        assert path.is_file() and path.stat().st_size > 0, f"missing generated figure: {name}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("<svg") and text.rstrip().endswith("</svg>"), name

    generator_paths = (
        ROOT / "scripts" / "reproduce_actual_data.py",
        ROOT / "scripts" / "summarize_actual_runs.py",
        ROOT / "scripts" / "run_diffusion1d_training.py",
        ROOT / "scripts" / "run_diffusionlm_saved_samples.py",
        ROOT / "scripts" / "run_mingpt_checkpoint.py",
        ROOT / "scripts" / "run_mingpt_training.py",
        ROOT / "scripts" / "probe_kozo_dev.py",
        ROOT / "scripts" / "generate_coverage_report.py",
    )
    script_text = "\n".join(path.read_text(encoding="utf-8") for path in generator_paths)
    forbidden_script_tokens = (
        "supplementary_table_",
        "published_plot_",
        "sources/s41524",
        "supplementary-pages",
        "paper-derived-quarantine",
    )
    assert not any(token in script_text for token in forbidden_script_tokens), "paper-transcription logic remains in scripts"
    for runner in (
        ROOT / "scripts" / "run_mingpt_checkpoint.py",
        ROOT / "scripts" / "run_mingpt_training.py",
        ROOT / "scripts" / "run_diffusion1d_training.py",
        ROOT / "scripts" / "run_diffusionlm_saved_samples.py",
    ):
        assert '"vendor" / "PolyGen-1.0.0"' in runner.read_text(encoding="utf-8"), (
            f"runner does not default to bundled source: {runner.name}"
        )

    probe = json.loads((ROOT / "results" / "dev" / "kozo-dev-e2e-probe.json").read_text(encoding="utf-8"))
    assert probe["core_checks_passed"] == all(probe["core_checks"].values()), "KO-POCHI core aggregate is inconsistent"
    assert probe["all_checks_passed"] == (
        probe["core_checks_passed"] and all(probe["registry_checks"].values())
    ), "KO-POCHI full-stack aggregate is inconsistent"
    assert probe["core_checks_passed"], "KO-POCHI core live end-to-end probe recorded a failure"
    assert probe["all_checks_passed"], "launcher-wide live end-to-end probe recorded a failure"

    verify_artifact_manifest()
    print("PASS: outputs were independently recomputed from machine-readable inputs and real DEV artifacts")


if __name__ == "__main__":
    main()
