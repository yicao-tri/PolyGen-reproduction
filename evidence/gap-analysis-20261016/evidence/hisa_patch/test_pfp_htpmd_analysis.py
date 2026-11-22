import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parent / "analyze_pfp_htpmd.py"
SPEC = importlib.util.spec_from_file_location("analyze_pfp_htpmd", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_unwrap_crossing_orthorhombic_boundary():
    wrapped = np.array([[[9.8, 1.0, 1.0]], [[0.2, 1.0, 1.0]], [[0.7, 1.0, 1.0]]])
    cells = np.repeat(np.eye(3)[None, :, :] * 10.0, 3, axis=0)
    actual = MODULE.unwrap(wrapped, cells)
    np.testing.assert_allclose(actual[:, 0, 0], [9.8, 10.2, 10.7])


def test_htpmd_endpoint_diffusivity_units():
    coords = np.array([[[0.0, 0.0, 0.0]], [[np.sqrt(6.0), 0.0, 0.0]]])
    msd, diffusivity = MODULE.endpoint_diffusivity(coords, frame_dt_ps=1.0)
    assert np.isclose(msd, 6.0)
    assert np.isclose(diffusivity, 1.0e-4)


def test_connected_components():
    adjacency = np.array(
        [
            [False, True, False, False],
            [True, False, False, False],
            [False, False, False, True],
            [False, False, True, False],
        ]
    )
    components = MODULE.connected_components(adjacency)
    assert sorted(sorted(component) for component in components) == [[0, 1], [2, 3]]


def test_ne_conductivity_matches_closed_form():
    population = np.zeros((50, 50))
    population[1, 0] = 2.0
    population[0, 1] = 2.0
    result = MODULE.conductivity(
        li_diff=1.0e-6,
        tfsi_diff=2.0e-6,
        population=population,
        volume_a3=1000.0,
        temperature_k=300.0,
        ion_pairs=2,
    )
    prefactor = MODULE.ELEMENTARY_CHARGE_C**2 / (
        1000.0 * MODULE.ANGSTROM_TO_CM**3 * MODULE.BOLTZMANN_J_K * 300.0
    )
    expected = prefactor * 2.0 * (1.0e-6 + 2.0e-6)
    assert np.isclose(result["nernst_einstein_S_cm"], expected)
    assert np.isclose(result["cluster_nernst_einstein_S_cm"], expected)
