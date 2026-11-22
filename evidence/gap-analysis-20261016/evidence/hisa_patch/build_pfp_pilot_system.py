#!/usr/bin/env python3
"""Pack a polymer/LiTFSI cell for the paired PFP pilot.

The Li and TFSI molecular geometries are extracted from the already-audited
continuous top-1 reference cell.  Packmol only changes rigid-body placement;
it does not assign a force field or charges.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_extxyz(path: Path) -> tuple[list[tuple[str, float, float, float]], float]:
    lines = path.read_text().splitlines()
    count = int(lines[0])
    match = re.search(r'Lattice="([^"]+)"', lines[1])
    if match is None:
        raise ValueError("Reference extxyz has no Lattice field")
    lattice = [float(value) for value in match.group(1).split()]
    if len(lattice) != 9:
        raise ValueError("Reference Lattice must contain 9 entries")
    off_diagonal = (lattice[1], lattice[2], lattice[3], lattice[5], lattice[6], lattice[7])
    if any(abs(value) > 1.0e-12 for value in off_diagonal) or any(value <= 0.0 for value in (lattice[0], lattice[4], lattice[8])):
        raise ValueError("Only an orthorhombic reference cell is supported")
    atoms = []
    for line in lines[2 : count + 2]:
        fields = line.split()
        atoms.append((fields[0], *(float(value) for value in fields[1:4])))
    if len(atoms) != count:
        raise ValueError("Reference extxyz atom count mismatch")
    return atoms, lattice[0]


def write_pdb(path: Path, atoms: list[tuple[str, float, float, float]]) -> None:
    lines = []
    for index, (symbol, x, y, z) in enumerate(atoms, 1):
        atom_name = f"{symbol}{index}"[:4]
        lines.append(
            f"HETATM{index:5d} {atom_name:<4s} MOL A   1    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00          {symbol:>2s}"
        )
    lines.extend(["TER", "END"])
    path.write_text("\n".join(lines) + "\n")


def read_pdb_atoms(path: Path) -> list[tuple[str, float, float, float]]:
    atoms = []
    for line in path.read_text().splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        symbol = line[76:78].strip()
        if not symbol:
            symbol = re.match(r"[A-Za-z]+", line[12:16].strip()).group(0)
        atoms.append(
            (symbol, float(line[30:38]), float(line[38:46]), float(line[46:54]))
        )
    return atoms


def write_extxyz(
    path: Path, atoms: list[tuple[str, float, float, float]], box_length: float
) -> None:
    header = (
        f'Lattice="{box_length} 0 0 0 {box_length} 0 0 0 {box_length}" '
        'Properties=species:S:1:pos:R:3 pbc="T T T"'
    )
    body = [f"{symbol:2s} {x:.8f} {y:.8f} {z:.8f}" for symbol, x, y, z in atoms]
    path.write_text(f"{len(atoms)}\n{header}\n" + "\n".join(body) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--polymer-pdb", type=Path, required=True)
    parser.add_argument("--reference-extxyz", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--polymer-chains", type=int, default=3)
    parser.add_argument("--ion-pairs", type=int, default=10)
    parser.add_argument("--polymer-mw", type=float, required=True)
    parser.add_argument("--box-length", type=float)
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--packmol", default="packmol")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference_atoms, reference_box = read_extxyz(args.reference_extxyz)
    # The audited reference cell is ordered as 3 x 308-atom polymer chains,
    # 10 Li atoms, then 10 x 15-atom TFSI molecules.
    ion_atoms = reference_atoms[-160:]
    li_atoms = ion_atoms[:10]
    tfsi_atoms = ion_atoms[10:25]
    if Counter(symbol for symbol, *_ in li_atoms) != Counter({"Li": 10}):
        raise ValueError("Reference Li block does not match the frozen contract")
    if Counter(symbol for symbol, *_ in tfsi_atoms) != Counter(
        {"C": 2, "F": 6, "N": 1, "O": 4, "S": 2}
    ):
        raise ValueError("Reference TFSI block does not match the frozen contract")

    li_pdb = args.output_dir / "Li.pdb"
    tfsi_pdb = args.output_dir / "TFSI.pdb"
    packed_pdb = args.output_dir / f"{args.label}.pdb"
    packed_extxyz = args.output_dir / f"{args.label}.extxyz"
    packmol_input = args.output_dir / "packmol.inp"
    write_pdb(li_pdb, [li_atoms[0]])
    # Translate the template near the origin so rigid-body placement is stable.
    ox, oy, oz = tfsi_atoms[0][1:]
    write_pdb(
        tfsi_pdb,
        [(s, x - ox, y - oy, z - oz) for s, x, y, z in tfsi_atoms],
    )
    box_length = args.box_length or reference_box
    packmol_input.write_text(
        f"""tolerance 2.0
filetype pdb
output {packed_pdb}
seed {args.seed}

structure {args.polymer_pdb.resolve()}
  number {args.polymer_chains}
  inside cube 0. 0. 0. {box_length}
end structure

structure {li_pdb.resolve()}
  number {args.ion_pairs}
  inside cube 0. 0. 0. {box_length}
end structure

structure {tfsi_pdb.resolve()}
  number {args.ion_pairs}
  inside cube 0. 0. 0. {box_length}
end structure
"""
    )
    completed = subprocess.run(
        [args.packmol],
        stdin=packmol_input.open("rb"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (args.output_dir / "packmol.log").write_bytes(completed.stdout)
    if completed.returncode != 0 or not packed_pdb.exists():
        raise RuntimeError(f"Packmol failed with exit code {completed.returncode}")
    packed_atoms = read_pdb_atoms(packed_pdb)
    write_extxyz(packed_extxyz, packed_atoms, box_length)

    molality = args.ion_pairs / (args.polymer_chains * args.polymer_mw / 1000.0)
    manifest = {
        "schema_version": "polygen.pfp-pilot-system.v1",
        "label": args.label,
        "status": "PFP_GEOMETRY_READY",
        "polymer_chains": args.polymer_chains,
        "ion_pairs": args.ion_pairs,
        "polymer_molecular_weight_g_mol": args.polymer_mw,
        "calculated_molality_mol_kg": molality,
        "box_length_A": box_length,
        "atom_count": len(packed_atoms),
        "formula": dict(sorted(Counter(symbol for symbol, *_ in packed_atoms).items())),
        "packing_seed": args.seed,
        "files": {
            packed_pdb.name: sha256(packed_pdb),
            packed_extxyz.name: sha256(packed_extxyz),
            "packmol.log": sha256(args.output_dir / "packmol.log"),
        },
    }
    (args.output_dir / "system_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
