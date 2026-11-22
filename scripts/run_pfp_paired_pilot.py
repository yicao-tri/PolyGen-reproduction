#!/usr/bin/env python3
"""Deterministic paired PFP MD runner for the PolyGen top-1 pilot.

This script is executed inside the Matlantis python311 environment.  It keeps
the two candidate arms under one code path and writes one artifact directory
per structure plus a machine-readable batch summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
from ase import units
from ase.io import Trajectory, read, write
from ase.md import MDLogger
from ase.md.langevin import Langevin
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
from ase.optimize import FIRE
from pfp_api_client.pfp.calculators.ase_calculator import ASECalculator
from pfp_api_client.pfp.estimator import Estimator


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(temporary, path)


def run_one(
    structure_path: Path,
    output_root: Path,
    *,
    temperature: float,
    timestep_fs: float,
    steps: int,
    trajectory_interval: int,
    friction_per_fs: float,
    seed: int,
    relax_steps: int,
    relax_fmax: float,
) -> dict:
    label = structure_path.stem
    output_dir = output_root / label
    output_dir.mkdir(parents=True, exist_ok=True)
    atoms = read(structure_path)
    atoms.calc = ASECalculator(Estimator(calc_mode="PBE", model_version="v8.0.0"))
    started = time.time()

    initial_energy = float(atoms.get_potential_energy())
    initial_max_force = float(np.linalg.norm(atoms.get_forces(), axis=1).max())
    relaxation_path = output_dir / "relaxation.traj"
    if relax_steps:
        optimizer = FIRE(atoms, trajectory=str(relaxation_path), logfile=str(output_dir / "relaxation.log"))
        optimizer.run(fmax=relax_fmax, steps=relax_steps)
    relaxed_energy = float(atoms.get_potential_energy())
    relaxed_max_force = float(np.linalg.norm(atoms.get_forces(), axis=1).max())
    write(output_dir / "relaxed.extxyz", atoms)

    rng = np.random.default_rng(seed)
    MaxwellBoltzmannDistribution(atoms, temperature_K=temperature, rng=rng)
    Stationary(atoms, preserve_temperature=True)
    trajectory_path = output_dir / "production.traj"
    log_path = output_dir / "production.log"
    trajectory = Trajectory(str(trajectory_path), "w", atoms)
    dynamics = Langevin(
        atoms,
        timestep_fs * units.fs,
        temperature_K=temperature,
        friction=friction_per_fs / units.fs,
        trajectory=trajectory,
        loginterval=trajectory_interval,
    )
    dynamics.attach(
        MDLogger(
            dynamics,
            atoms,
            str(log_path),
            header=True,
            stress=False,
            peratom=False,
            mode="w",
        ),
        interval=trajectory_interval,
    )

    production_started = time.time()

    def write_progress() -> None:
        completed_steps = int(dynamics.nsteps)
        elapsed = time.time() - production_started
        rate = completed_steps / elapsed if elapsed > 0 else 0.0
        remaining = (steps - completed_steps) / rate if rate > 0 else None
        write_json_atomic(
            output_dir / "progress.json",
            {
                "schema_version": "polygen.pfp-pilot-progress.v1",
                "label": label,
                "status": "running" if completed_steps < steps else "completed",
                "completed_steps": completed_steps,
                "total_steps": steps,
                "completed_ps": completed_steps * timestep_fs / 1000.0,
                "elapsed_seconds": elapsed,
                "estimated_remaining_seconds": remaining,
                "updated_unix_seconds": time.time(),
            },
        )

    dynamics.attach(write_progress, interval=trajectory_interval)
    dynamics.run(steps)
    trajectory.close()
    final_energy = float(atoms.get_potential_energy())
    final_temperature = float(atoms.get_temperature())
    frame_count = len(Trajectory(str(trajectory_path), "r"))
    summary = {
        "schema_version": "polygen.pfp-pilot-run.v1",
        "label": label,
        "status": "succeeded",
        "source_structure": structure_path.name,
        "source_sha256": sha256(structure_path),
        "atom_count": len(atoms),
        "temperature_K": temperature,
        "timestep_fs": timestep_fs,
        "steps": steps,
        "production_ps": steps * timestep_fs / 1000.0,
        "trajectory_interval_steps": trajectory_interval,
        "friction_per_fs": friction_per_fs,
        "velocity_seed": seed,
        "zero_linear_momentum": True,
        "relaxation_steps": relax_steps,
        "relaxation_fmax_eV_A": relax_fmax,
        "initial_energy_eV": initial_energy,
        "initial_max_force_eV_A": initial_max_force,
        "relaxed_energy_eV": relaxed_energy,
        "relaxed_max_force_eV_A": relaxed_max_force,
        "final_energy_eV": final_energy,
        "final_temperature_K": final_temperature,
        "frame_count": frame_count,
        "elapsed_seconds": time.time() - started,
        "artifacts": {
            "trajectory": {"path": trajectory_path.name, "sha256": sha256(trajectory_path)},
            "log": {"path": log_path.name, "sha256": sha256(log_path)},
            "relaxed_structure": {
                "path": "relaxed.extxyz",
                "sha256": sha256(output_dir / "relaxed.extxyz"),
            },
        },
    }
    write_json_atomic(output_dir / "run_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structures", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--temperature", type=float, default=353.0)
    parser.add_argument("--timestep-fs", type=float, default=1.0)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--trajectory-interval", type=int, default=100)
    parser.add_argument("--friction-per-fs", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--relax-steps", type=int, default=0)
    parser.add_argument("--relax-fmax", type=float, default=0.1)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for structure in args.structures:
        summaries.append(
            run_one(
                structure,
                args.output_dir,
                temperature=args.temperature,
                timestep_fs=args.timestep_fs,
                steps=args.steps,
                trajectory_interval=args.trajectory_interval,
                friction_per_fs=args.friction_per_fs,
                seed=args.seed,
                relax_steps=args.relax_steps,
                relax_fmax=args.relax_fmax,
            )
        )
    batch = {
        "schema_version": "polygen.pfp-pilot-batch.v1",
        "status": "succeeded",
        "candidate_count": len(summaries),
        "paired_protocol_equal": all(
            all(item[key] == summaries[0][key] for item in summaries)
            for key in (
                "temperature_K",
                "timestep_fs",
                "steps",
                "trajectory_interval_steps",
                "friction_per_fs",
                "velocity_seed",
                "relaxation_steps",
                "relaxation_fmax_eV_A",
            )
        ),
        "runs": summaries,
    }
    write_json_atomic(args.output_dir / "batch_summary.json", batch)
    print(json.dumps(batch, indent=2))


if __name__ == "__main__":
    main()
