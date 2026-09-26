import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SYSTEM_DIR = (
    ROOT
    / "results"
    / "experiment-c"
    / "md-validation"
    / "top1-smoke-input"
    / "system-geometry"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_top1_packed_system_manifest_and_artifact_are_consistent():
    manifest = json.loads((SYSTEM_DIR / "system_geometry_manifest.json").read_text())
    structure = SYSTEM_DIR / "top1_3chains_10litfsi_expanded.extxyz"

    assert manifest["polymer_chains"] == 3
    assert manifest["li_ions"] == manifest["tfsi_ions"] == 10
    assert manifest["atom_count"] == 1084
    assert float(structure.read_text().splitlines()[0]) == manifest["atom_count"]
    assert abs(manifest["calculated_molality_mol_kg"] - 1.5) / 1.5 < 2e-5
    assert _sha256(structure) == manifest["packed_extxyz_sha256"]
    assert manifest["pcff_plus_parameterized"] is False
