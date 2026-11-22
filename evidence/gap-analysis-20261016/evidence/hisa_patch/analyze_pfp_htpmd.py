#!/usr/bin/env python3
"""HTP-MD-compatible analysis of an ASE/PFP polymer-electrolyte trajectory.

The public HTP-MD implementation identifies TFSI transport with its nitrogen
atom and evaluates conductivity with its endpoint diffusivity and averaged
3.4-A ion-cluster population matrix.  This adapter preserves those definitions
while reading the ASE trajectories emitted by ``run_pfp_paired_pilot.py``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ELEMENTARY_CHARGE_C = 1.6021766209e-19
BOLTZMANN_J_K = 1.38064852e-23
ANGSTROM_TO_CM = 1.0e-8
PICOSECOND_TO_S = 1.0e-12
HTPMD_COMMIT = "4076e9baa8d2da0c9ee250bd2b75daa58d03986a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unwrap(wrapped: np.ndarray, cells: np.ndarray) -> np.ndarray:
    result = np.empty_like(wrapped)
    result[0] = wrapped[0]
    for frame in range(1, len(wrapped)):
        cell = cells[frame]
        fractional_delta = (wrapped[frame] - wrapped[frame - 1]) @ np.linalg.inv(cell)
        fractional_delta -= np.rint(fractional_delta)
        result[frame] = result[frame - 1] + fractional_delta @ cell
    return result


def endpoint_diffusivity(coords: np.ndarray, frame_dt_ps: float) -> tuple[float, float]:
    elapsed_ps = (len(coords) - 1) * frame_dt_ps
    msd_a2 = float(np.mean(np.sum((coords[-1] - coords[0]) ** 2, axis=-1)))
    diffusivity = msd_a2 * ANGSTROM_TO_CM**2 / (6.0 * elapsed_ps * PICOSECOND_TO_S)
    return msd_a2, diffusivity


def msd_curve(coords: np.ndarray, frame_dt_ps: float) -> tuple[np.ndarray, np.ndarray]:
    max_lag = len(coords) - 1
    dense = np.arange(1, min(max_lag, 200) + 1)
    sparse = np.unique(np.geomspace(1, max_lag, 180).astype(int))
    lags = np.unique(np.concatenate((dense, sparse, [max_lag])))
    values = np.array(
        [np.mean(np.sum((coords[lag:] - coords[:-lag]) ** 2, axis=-1)) for lag in lags]
    )
    return lags * frame_dt_ps, values


def slope_diffusivity(times_ps: np.ndarray, msd_a2: np.ndarray, start_ps: float, end_ps: float) -> dict:
    mask = (times_ps >= start_ps) & (times_ps <= end_ps)
    if np.count_nonzero(mask) < 3:
        raise ValueError("Diffusive fit window contains fewer than three MSD points")
    x = times_ps[mask]
    y = msd_a2[mask]
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    diffusivity = slope * ANGSTROM_TO_CM**2 / (6.0 * PICOSECOND_TO_S)
    return {
        "fit_start_ps": start_ps,
        "fit_end_ps": end_ps,
        "slope_A2_per_ps": float(slope),
        "intercept_A2": float(intercept),
        "r_squared": r2,
        "diffusivity_cm2_s": float(diffusivity),
    }


def connected_components(adjacency: np.ndarray) -> list[list[int]]:
    unseen = set(range(len(adjacency)))
    components = []
    while unseen:
        root = unseen.pop()
        component = [root]
        stack = [root]
        while stack:
            node = stack.pop()
            neighbors = set(np.flatnonzero(adjacency[node])) & unseen
            unseen -= neighbors
            component.extend(neighbors)
            stack.extend(neighbors)
        components.append(component)
    return components


def population_matrix(
    frames: list,
    selected_indices: np.ndarray,
    is_li: np.ndarray,
    is_n: np.ndarray,
    cutoff_a: float,
    checkpoint_frame_counts: set[int] | None = None,
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    # Keep enough room for the largest connected component seen in the
    # trajectory; conductivity() validates and traverses the full matrix.
    population = np.zeros((50, 50), dtype=float)
    checkpoint_frame_counts = checkpoint_frame_counts or set()
    checkpoints = {}
    for frame_number, atoms in enumerate(frames, 1):
        cell = np.asarray(atoms.cell)
        positions = atoms.positions[selected_indices]
        differences = positions[:, None, :] - positions[None, :, :]
        fractional = differences @ np.linalg.inv(cell)
        fractional -= np.rint(fractional)
        minimum_image = fractional @ cell
        distances = np.linalg.norm(minimum_image, axis=-1)
        adjacency = (distances <= cutoff_a) & (distances > 0.0)
        for component in connected_components(adjacency):
            li_count = int(np.count_nonzero(is_li[component]))
            anion_count = int(np.count_nonzero(is_n[component]))
            population[li_count, anion_count] += 1.0
        if frame_number in checkpoint_frame_counts:
            checkpoints[frame_number] = population.copy() / frame_number
    return population / len(frames), checkpoints


def conductivity(
    li_diff: float,
    tfsi_diff: float,
    population: np.ndarray,
    volume_a3: float,
    temperature_k: float,
    ion_pairs: int,
) -> dict:
    volume_cm3 = volume_a3 * ANGSTROM_TO_CM**3
    prefactor = ELEMENTARY_CHARGE_C**2 / (volume_cm3 * BOLTZMANN_J_K * temperature_k)
    cluster_sum = 0.0
    tn_num = 0.0
    tn_den = 0.0
    if population.ndim != 2 or population.shape[0] != population.shape[1]:
        raise ValueError("population matrix must be square")
    # Do not silently discard high-order ion clusters.  The population
    # matrix is intentionally larger than the number of ion pairs so that
    # connected components with many ions remain representable.
    for i in range(population.shape[0]):
        for j in range(population.shape[1]):
            charge2 = float((i - j) ** 2)
            if i > j:
                cluster_sum += charge2 * population[i, j] * li_diff
                tn_num += i * (i - j) * population[i, j] * li_diff
                tn_den += charge2 * population[i, j] * li_diff
            elif i < j:
                cluster_sum += charge2 * population[i, j] * tfsi_diff
                tn_num += i * (i - j) * population[i, j] * tfsi_diff
                tn_den += charge2 * population[i, j] * tfsi_diff
    ne = prefactor * ion_pairs * (li_diff + tfsi_diff)
    return {
        "cluster_nernst_einstein_S_cm": prefactor * cluster_sum,
        "cluster_transference_number": tn_num / tn_den if tn_den else None,
        "nernst_einstein_S_cm": ne,
        "nernst_einstein_transference_number": li_diff / (li_diff + tfsi_diff),
    }


def main() -> None:
    from ase.io import Trajectory

    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ion-pairs", type=int, default=10)
    parser.add_argument("--frame-dt-ps", type=float, default=0.1)
    parser.add_argument("--discard-ps", type=float, default=40.0)
    parser.add_argument("--temperature", type=float, default=353.0)
    parser.add_argument("--cluster-cutoff-a", type=float, default=3.4)
    parser.add_argument("--proxy-log10", type=float, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trajectory = Trajectory(str(args.trajectory), "r")
    all_frames = list(trajectory)
    trajectory.close()
    discard_frames = int(round(args.discard_ps / args.frame_dt_ps))
    frames = all_frames[discard_frames:]
    if len(frames) < 3:
        raise ValueError("Not enough frames remain after equilibration discard")
    symbols = np.array(frames[0].get_chemical_symbols())
    ion_atom_count = args.ion_pairs * 16
    polymer_atoms = len(symbols) - ion_atom_count
    li_indices = np.arange(polymer_atoms, polymer_atoms + args.ion_pairs)
    if not np.all(symbols[li_indices] == "Li"):
        raise ValueError("Frozen layout check failed: Li block not found")

    tfsi_start = polymer_atoms + args.ion_pairs
    tfsi_groups = [np.arange(tfsi_start + 15 * i, tfsi_start + 15 * (i + 1)) for i in range(args.ion_pairs)]
    expected_formula = {"C": 2, "F": 6, "N": 1, "O": 4, "S": 2}
    n_indices = []
    core_indices = []
    for group in tfsi_groups:
        formula = {symbol: int(np.count_nonzero(symbols[group] == symbol)) for symbol in np.unique(symbols[group])}
        if formula != expected_formula:
            raise ValueError(f"Frozen layout check failed for TFSI: {formula}")
        n_indices.extend(group[symbols[group] == "N"])
        core_indices.extend(group[np.isin(symbols[group], ["N", "O", "S"])])
    n_indices = np.asarray(n_indices, dtype=int)
    selected = np.concatenate((li_indices, np.asarray(core_indices, dtype=int)))
    selected_symbols = symbols[selected]
    is_li = selected_symbols == "Li"
    is_n = selected_symbols == "N"

    tracked_indices = np.concatenate((li_indices, n_indices))
    wrapped = np.array([atoms.positions[tracked_indices] for atoms in frames])
    cells = np.array([atoms.cell.array for atoms in frames])
    unwrapped = unwrap(wrapped, cells)
    li_coords = unwrapped[:, : args.ion_pairs]
    tfsi_coords = unwrapped[:, args.ion_pairs :]
    # HTP-MD initializes LAMMPS velocities with ``mom yes``.  The PFP runner's
    # Langevin integrator uses fixcm=True, but ASE's Maxwell-Boltzmann helper
    # does not itself zero the initial momentum.  Preserve the HTP raw MSD as
    # the primary value and expose a mass-weighted COM-corrected diagnostic.
    wrapped_all = np.array([atoms.positions for atoms in frames])
    unwrapped_all = unwrap(wrapped_all, cells)
    masses = frames[0].get_masses()
    system_com = np.sum(unwrapped_all * masses[None, :, None], axis=1) / np.sum(masses)
    com_relative = system_com - system_com[0]
    li_drift_corrected = li_coords - com_relative[:, None, :]
    tfsi_drift_corrected = tfsi_coords - com_relative[:, None, :]
    elapsed_ps = (len(frames) - 1) * args.frame_dt_ps
    li_endpoint_msd, li_diff = endpoint_diffusivity(li_coords, args.frame_dt_ps)
    tfsi_endpoint_msd, tfsi_diff = endpoint_diffusivity(tfsi_coords, args.frame_dt_ps)
    li_corrected_msd, li_corrected_diff = endpoint_diffusivity(
        li_drift_corrected, args.frame_dt_ps
    )
    tfsi_corrected_msd, tfsi_corrected_diff = endpoint_diffusivity(
        tfsi_drift_corrected, args.frame_dt_ps
    )
    li_time, li_msd = msd_curve(li_coords, args.frame_dt_ps)
    tfsi_time, tfsi_msd = msd_curve(tfsi_coords, args.frame_dt_ps)
    fit_start = elapsed_ps * 0.25
    fit_end = elapsed_ps * 0.75
    li_fit = slope_diffusivity(li_time, li_msd, fit_start, fit_end)
    tfsi_fit = slope_diffusivity(tfsi_time, tfsi_msd, fit_start, fit_end)
    convergence_durations = [
        duration
        for duration in (20.0, 40.0, 80.0, 120.0, 160.0)
        if duration <= elapsed_ps + 1.0e-9
    ]
    checkpoint_counts = {
        int(round(duration / args.frame_dt_ps)) + 1 for duration in convergence_durations
    }
    population, population_checkpoints = population_matrix(
        frames,
        selected,
        is_li,
        is_n,
        args.cluster_cutoff_a,
        checkpoint_counts,
    )
    volume_a3 = float(abs(np.linalg.det(cells[0])))
    conduct = conductivity(li_diff, tfsi_diff, population, volume_a3, args.temperature, args.ion_pairs)
    cluster_value = conduct["cluster_nernst_einstein_S_cm"]
    log_value = math.log10(cluster_value) if cluster_value > 0 else None

    with (args.output_dir / "msd_curve.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["lag_ps", "li_msd_A2", "tfsi_N_msd_A2"])
        tfsi_by_time = dict(zip(tfsi_time, tfsi_msd))
        for time_ps, value in zip(li_time, li_msd):
            writer.writerow([time_ps, value, tfsi_by_time[time_ps]])
    np.savetxt(args.output_dir / "population_matrix.txt", population)

    convergence = []
    for duration in convergence_durations:
        count = int(round(duration / args.frame_dt_ps)) + 1
        _, checkpoint_li_diff = endpoint_diffusivity(li_coords[:count], args.frame_dt_ps)
        _, checkpoint_tfsi_diff = endpoint_diffusivity(tfsi_coords[:count], args.frame_dt_ps)
        checkpoint_conductivity = conductivity(
            checkpoint_li_diff,
            checkpoint_tfsi_diff,
            population_checkpoints[count],
            volume_a3,
            args.temperature,
            args.ion_pairs,
        )
        cne = checkpoint_conductivity["cluster_nernst_einstein_S_cm"]
        convergence.append(
            {
                "analysis_duration_ps": duration,
                "frame_count": count,
                "li_diffusivity_cm2_s": checkpoint_li_diff,
                "tfsi_diffusivity_cm2_s": checkpoint_tfsi_diff,
                "cluster_ne_conductivity_S_cm": cne,
                "cluster_ne_log10_S_cm": math.log10(cne) if cne > 0 else None,
                "cluster_transference_number": checkpoint_conductivity[
                    "cluster_transference_number"
                ],
            }
        )
    with (args.output_dir / "convergence.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(convergence[0]))
        writer.writeheader()
        writer.writerows(convergence)

    result = {
        "schema_version": "polygen.pfp-htpmd-analysis.v1",
        "label": args.label,
        "status": "succeeded",
        "source": {
            "trajectory": args.trajectory.name,
            "trajectory_sha256": sha256(args.trajectory),
            "htpmd_reference_commit": HTPMD_COMMIT,
        "adapter_definition": "HTP-MD endpoint diffusivity, TFSI-N identity, 3.4-A O/S/N ion clusters, and full square cNE population sum"
        },
        "frames_total": len(all_frames),
        "frames_analyzed": len(frames),
        "discard_ps": args.discard_ps,
        "analysis_ps": elapsed_ps,
        "frame_dt_ps": args.frame_dt_ps,
        "temperature_K": args.temperature,
        "volume_A3": volume_a3,
        "polymer_atom_count": polymer_atoms,
        "ion_pairs": args.ion_pairs,
        "diffusivity": {
            "htpmd_endpoint": {
                "li_msd_A2": li_endpoint_msd,
                "li_cm2_s": li_diff,
                "tfsi_N_msd_A2": tfsi_endpoint_msd,
                "tfsi_cm2_s": tfsi_diff
            },
            "system_com_drift_diagnostic": {
                "system_com_displacement_A": float(np.linalg.norm(com_relative[-1])),
                "li_msd_A2": li_corrected_msd,
                "li_cm2_s": li_corrected_diff,
                "tfsi_N_msd_A2": tfsi_corrected_msd,
                "tfsi_cm2_s": tfsi_corrected_diff,
                "primary_definition_remains_uncorrected_htpmd_endpoint": True
            },
            "multi_origin_slope_diagnostic": {"li": li_fit, "tfsi_N": tfsi_fit}
        },
        "conductivity": conduct,
        "convergence_diagnostic": convergence,
        "proxy_comparison": {
            "proxy_log10_S_cm": args.proxy_log10,
            "pfp_cluster_ne_log10_S_cm": log_value,
            "residual_pfp_minus_proxy_log10_S_cm": log_value - args.proxy_log10 if log_value is not None else None
        },
        "quality": {
            "finite_values": bool(np.isfinite(unwrapped).all() and np.isfinite(population).all()),
            "population_ion_count_mean": float(sum((i + j) * population[i, j] for i in range(population.shape[0]) for j in range(population.shape[1]))),
            "expected_ion_count": 2 * args.ion_pairs,
            "constant_cell": bool(np.allclose(cells, cells[0])),
            "single_replica_short_pilot": True
        }
    }
    (args.output_dir / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
