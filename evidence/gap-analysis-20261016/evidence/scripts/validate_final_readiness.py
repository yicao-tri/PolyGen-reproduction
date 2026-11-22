#!/usr/bin/env python3
"""Validate the complete Pitch x PolyGen package without changing canonical data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


FIGURE_STEMS = [
    "P1_decision_value_tradeoff",
    "P2_verifier_blind_locked_tail",
    "P3_verifier_repair_experiment",
    "F1_framework_and_closed_loop",
    "F2_interpolation_controllability",
    "F3_upper_tail_response",
    "F4_extrapolation_response",
    "F5_verifier_audit",
    "F6_md_residual_ladder",
    "F7_representation_data_ablation_SYNTHETIC",
    "F8_decision_change_SYNTHETIC",
    "F9_generation_grid_repaired",
    "S1_molminer_extended20_vs_smoke",
    "S2_molminer_extended50_vs_smoke",
]
TABLES = [f"T{i}" for i in range(1, 15)]


def parse_csv(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def package_files(root: Path):
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
        and p.name != "PACKAGE_MANIFEST.json"
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
        and p.name != ".DS_Store"
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--canonical-root", type=Path, default=Path("/Users/yicao/Documents/ARC/PolyGen-reproduction"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    root = args.package_root.resolve()
    output = (args.output or root / "evidence/data/final_readiness_audit.json").resolve()
    checks = {}
    failures = []

    figure_missing = [
        f"assets/figures/{stem}.{ext}"
        for stem in FIGURE_STEMS
        for ext in ("png", "pdf", "svg")
        if not (root / f"assets/figures/{stem}.{ext}").is_file()
    ]
    checks["required_figures"] = {"status": "PASS" if not figure_missing else "FAIL", "missing": figure_missing}
    if figure_missing:
        failures.append("required_figures")

    table_missing = [f"assets/tables/{name}_" for name in TABLES if not list((root / "assets/tables").glob(f"{name}_*.csv"))]
    checks["required_tables"] = {"status": "PASS" if not table_missing else "FAIL", "missing_prefixes": table_missing}
    if table_missing:
        failures.append("required_tables")

    qa = parse_csv(root / "evidence/data/figure_visual_qa.csv")
    bad_qa = [row for row in qa if row.get("layout_status") not in {"pass", "conditional_source_asset"}]
    checks["figure_visual_qa"] = {"status": "PASS" if not bad_qa else "FAIL", "rows": len(qa), "bad_rows": bad_qa}
    if bad_qa:
        failures.append("figure_visual_qa")

    provenance = parse_csv(root / "PROVENANCE.csv")
    missing_provenance = []
    for row in provenance:
        for field in ("artifact_path", "source_data_snapshot", "source_script", "source_script_snapshot"):
            for raw in row[field].split(";"):
                path = raw.strip()
                if not path or path.startswith(("canonical ", "http", "not_included:")):
                    continue
                if not (root / path).exists():
                    missing_provenance.append({"artifact_id": row["artifact_id"], "field": field, "path": path})
    checks["provenance"] = {"status": "PASS" if not missing_provenance else "FAIL", "rows": len(provenance), "missing": missing_provenance}
    if missing_provenance:
        failures.append("provenance")

    manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text())
    manifest_paths = {row["path"] for row in manifest["files"]}
    disk_paths = package_files(root)
    manifest_diff = {"unlisted": sorted(disk_paths - manifest_paths), "missing": sorted(manifest_paths - disk_paths)}
    checks["package_manifest"] = {"status": "PASS" if not any(manifest_diff.values()) else "FAIL", "files": len(manifest_paths), "diff": manifest_diff}
    if any(manifest_diff.values()):
        failures.append("package_manifest")

    claims = parse_csv(root / "CLAIM_MAP.csv")
    claim_ids = {row["claim_id"] for row in claims}
    expected_claims = {f"C{i}" for i in range(1, 19)}
    checks["claim_map"] = {"status": "PASS" if expected_claims <= claim_ids else "FAIL", "rows": len(claims), "missing": sorted(expected_claims - claim_ids)}
    if expected_claims - claim_ids:
        failures.append("claim_map")

    smoke = json.loads((root / "evidence/experiments/molminer_strict_c1/five_seed_generation_smoke/aggregate_summary.json").read_text())
    smoke_pass = smoke.get("raw_rows") == 150 and smoke.get("valid_repeat_units") == 47 and smoke.get("strict_hits") == 8
    checks["strict_molminer_smoke"] = {"status": "PASS" if smoke_pass else "FAIL", "summary": smoke}
    if not smoke_pass:
        failures.append("strict_molminer_smoke")

    pcff = json.loads((root / "evidence/data/pcff_plus_bundle_audit/pcff_plus_bundle_audit.json").read_text())
    canonical_audit = json.loads((root / "evidence/data/asset_audit.json").read_text())
    physical_status = {
        "pcff_plus_preflight": pcff.get("status"),
        "top1_readiness": canonical_audit.get("physical_validation_gate", {}).get("top1_readiness_decision"),
        "md_status": canonical_audit.get("physical_validation_gate", {}).get("md_status"),
    }
    checks["physical_gate"] = {"status": "BLOCKED" if physical_status["pcff_plus_preflight"] != "PASS" else "PASS", **physical_status}

    unresolved = [
        "physical PCFF+ bundle and extrapolation MD are not available",
        "F7/F8 are synthetic/planned placeholders",
        "final publication-budget MolMiner comparison and task-aligned WeeMiner arm remain open",
        "A4 isolated Hisa fixes are not merged into canonical and A9 full-source PI1M/ablation experiments remain open",
        "Overleaf/submission-root synchronization remains owner-authorized only",
    ]
    result = {
        "schema_version": "polygen-final-readiness-v1",
        "status": "incomplete_by_design" if unresolved or failures else "ready",
        "package_root": str(root),
        "checks": checks,
        "hard_failures": failures,
        "unresolved_scope": unresolved,
        "interpretation": "The package is publication-ready only for its surrogate-only, verifier-limited claim boundary; physical crossing and final generator comparison are not claimed.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "hard_failures": failures, "physical_gate": physical_status}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
