#!/usr/bin/env python3
"""Audit the local candidate-specific PCFF+ bundle without launching MD.

The audit deliberately distinguishes missing local inputs from parameters that
were never assessed. It does not infer atom types or fabricate coefficients.
The canonical PolyGen repository is read-only input; only --output-dir is
written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def asset(path: Path, root: Path, status: str, note: str) -> dict:
    row = {
        "path": str(path),
        "relative_to_canonical": str(path.relative_to(root)) if path.is_relative_to(root) else None,
        "present": path.exists(),
        "status": status,
        "note": note,
    }
    if path.is_file():
        row.update({"bytes": path.stat().st_size, "sha256": sha256(path)})
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.canonical_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    smoke = root / "results/experiment-c/md-validation/top1-smoke-input"
    audit_path = root / "results/experiment-c/md-validation/top1_readiness_audit.json"
    audit = json.loads(audit_path.read_text())

    expected = {
        "candidate_identity": smoke / "top1_methyl_terminated.sdf",
        "candidate_pdb": smoke / "top1_methyl_terminated.pdb",
        "packed_geometry": smoke / "system-geometry/top1_3chains_10litfsi_expanded.extxyz",
        "candidate_build_manifest": smoke / "build_manifest.json",
        "system_geometry_manifest": smoke / "system-geometry/system_geometry_manifest.json",
        "candidate_lammps_data": smoke / "system.lmp",
        "candidate_lammps_input": smoke / "in.lmp",
        "atom_typing_and_charges": smoke / "pcff_plus_atom_types_charges.json",
        "bond_coefficients": smoke / "pcff_plus_bond_coeffs.txt",
        "angle_coefficients": smoke / "pcff_plus_angle_coeffs.txt",
        "dihedral_coefficients": smoke / "pcff_plus_dihedral_coeffs.txt",
        "improper_coefficients": smoke / "pcff_plus_improper_coeffs.txt",
        "nonbonded_coefficients": smoke / "pcff_plus_pair_coeffs.txt",
        "parameter_coverage_report": smoke / "pcff_plus_coverage_report.json",
        "run0_acceptance_report": smoke / "run0_acceptance.json",
    }

    sections = {}
    for name, path in expected.items():
        if path.exists():
            status = "present"
            note = "present in the audited local top-1 bundle"
        else:
            status = "missing_from_local_bundle"
            note = "not present in the audited local candidate-specific bundle; no parameter value inferred"
        sections[name] = asset(path, root, status, note)

    reference_only = [
        asset(
            Path("/Users/yicao/Documents/ARC/liquid-electrolyte-entropy/work/htp_md_upstream_v2/example_for_relaxation_equilibration/newfile.data"),
            root,
            "reference_only",
            "already-parameterized PEO example; not the frozen PolyGen top-1 candidate",
        ),
        asset(
            Path("/Users/yicao/Documents/ARC/resourses/htp-md-toolbox/data/ion_parameters/Li.params"),
            root,
            "reference_only",
            "ion template; does not supply candidate polymer typing or cross terms",
        ),
        asset(
            Path("/Users/yicao/Documents/ARC/resourses/htp-md-toolbox/data/ion_parameters/TFSI.params"),
            root,
            "reference_only",
            "ion template; does not supply candidate polymer typing or cross terms",
        ),
    ]

    required_classes = [
        "atom_types_charges_masses",
        "bond_coefficients",
        "angle_coefficients",
        "dihedral_coefficients",
        "improper_coefficients",
        "nonbonded_pair_coefficients",
        "cross_terms_and_mixing_rules",
        "topology_atom_map",
        "lammps_run0_acceptance",
    ]
    coverage = {
        name: {
            "status": "not_assessed_candidate_specific_bundle_missing",
            "numerator": None,
            "denominator": None,
            "reason": "A complete candidate-specific PCFF+ bundle is absent; do not report a numerical coverage fraction.",
        }
        for name in required_classes
    }

    report = {
        "schema_version": "polygen-pcff-plus-bundle-audit-v1",
        "status": "NO_GO",
        "canonical_root": str(root),
        "candidate_readiness_decision": audit.get("decision"),
        "candidate": audit.get("candidate"),
        "gates_from_canonical_readiness_audit": audit.get("gates", {}),
        "local_bundle_scope": "top1-smoke-input only; remote or uncommitted parameter files were not assumed",
        "candidate_specific_assets": sections,
        "reference_only_assets": reference_only,
        "coverage_by_required_class": coverage,
        "launch_rule": "Do not launch PCFF+ MD until all required classes have candidate-specific coefficients, complete coverage counts, SHA-256 manifest, and a passing LAMMPS run-0 acceptance.",
    }
    path = out / "pcff_plus_bundle_audit.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(path), "status": report["status"], "required_classes": len(required_classes)}, indent=2))


if __name__ == "__main__":
    main()
