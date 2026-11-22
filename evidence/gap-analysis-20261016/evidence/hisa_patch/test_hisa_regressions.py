"""Isolated regression checks for the Hisa review patch candidates."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dynamic_cluster_population_and_square_guard():
    analyzer = load("analyze_pfp_htpmd")
    population = np.zeros((50, 50), dtype=float)
    population[11, 0] = 1.0
    population[0, 11] = 1.0
    result = analyzer.conductivity(1.0e-6, 2.0e-6, population, 1000.0, 300.0, 2)
    assert result["cluster_nernst_einstein_S_cm"] > 0.0
    assert not np.isclose(
        result["cluster_nernst_einstein_S_cm"], result["nernst_einstein_S_cm"]
    )
    try:
        analyzer.conductivity(1.0e-6, 2.0e-6, np.zeros((2, 3)), 1000.0, 300.0, 2)
    except ValueError as exc:
        assert "square" in str(exc)
    else:
        raise AssertionError("non-square population matrix was accepted")


def test_nullable_summary_and_renderer_formatting():
    summary = load("summarize_pfp_top1_pair")
    renderer = load("render_pfp_top1_report")
    assert summary.optional_difference(None, -4.0) is None
    assert summary.optional_difference(-3.0, -4.0) == 1.0
    assert renderer.fixed(None) == "n/a"
    assert renderer.fixed(-0.25, signed=True) == "-0.250000"
    assert renderer.sci(None) == "n/a"


def test_full_orthorhombic_lattice_validation():
    builder = load("build_pfp_pilot_system")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "reference.extxyz"
        atoms = "C 0 0 0\n"
        path.write_text(
            '1\nLattice="10 0 0 0 11 0 0 0 12" Properties=species:S:1:pos:R:3\n'
            + atoms
        )
        _, box = builder.read_extxyz(path)
        assert box == 10.0
        for index in (1, 2, 3, 5, 6, 7):
            lattice = [10.0, 0.0, 0.0, 0.0, 11.0, 0.0, 0.0, 0.0, 12.0]
            lattice[index] = 0.1
            path.write_text(
                "1\nLattice=\"" + " ".join(map(str, lattice)) + "\"\n" + atoms
            )
            try:
                builder.read_extxyz(path)
            except ValueError:
                pass
            else:
                raise AssertionError(f"off-diagonal lattice entry {index} was not rejected")


def test_grid_plan_totals_are_derived():
    plan = ROOT.parent / "GRID_PLAN.json"
    if not plan.exists():
        raise AssertionError("run the isolated grid planner before this check")
    data = json.loads(plan.read_text())
    assert data["planned_raw_samples_gpt_nano"] == 27000
    assert data["estimated_gpu_hours_gpt_nano"] == 90.0


if __name__ == "__main__":
    tests = [
        test_dynamic_cluster_population_and_square_guard,
        test_nullable_summary_and_renderer_formatting,
        test_full_orthorhombic_lattice_validation,
        test_grid_plan_totals_are_derived,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
