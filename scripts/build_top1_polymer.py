#!/usr/bin/env python3
"""Build the frozen continuous top-1 polymer geometry for the MD readiness gate.

This script only constructs a deterministic methyl-terminated 3D polymer chain.
It does not assign PCFF+ atom types, charges, or force-field parameters.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors


DEFAULT_MONOMER = "[*]C(=O)OCCCOCCO[*]"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_monomer(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid monomer SMILES: {smiles}")
    dummies = [atom for atom in mol.GetAtoms() if atom.GetAtomicNum() == 0]
    if len(dummies) != 2:
        raise ValueError("Linear monomer must contain exactly two wildcard atoms")
    if any(len(atom.GetNeighbors()) != 1 for atom in dummies):
        raise ValueError("Each wildcard atom must have exactly one neighbor")
    return mol


def build_methyl_terminated_chain(monomer_smiles: str, degree: int) -> Chem.Mol:
    """Connect ``degree`` repeats and replace the two terminal wildcards by CH3."""
    if degree < 1:
        raise ValueError("degree must be positive")
    _validate_monomer(monomer_smiles)

    labeled = monomer_smiles.replace("[*]", "[1*]", 1).replace("[*]", "[2*]", 1)
    mol = Chem.MolFromSmiles(".".join([labeled] * degree))
    if mol is None:
        raise ValueError("Failed to parse repeated monomer fragments")
    editable = Chem.RWMol(mol)

    while True:
        fragments = Chem.GetMolFrags(editable.GetMol())
        fragment_of = {
            atom_index: fragment_index
            for fragment_index, atom_indices in enumerate(fragments)
            for atom_index in atom_indices
        }
        left, right = [], []
        for atom in editable.GetAtoms():
            if atom.GetAtomicNum() != 0:
                continue
            neighbor = atom.GetNeighbors()[0].GetIdx()
            item = (atom.GetIdx(), neighbor, fragment_of[atom.GetIdx()])
            if atom.GetIsotope() == 1:
                left.append(item)
            elif atom.GetIsotope() == 2:
                right.append(item)

        pair = next(
            (
                (right_item, left_item)
                for right_item in right
                for left_item in left
                if right_item[2] != left_item[2]
            ),
            None,
        )
        if pair is None:
            break
        (right_dummy, right_neighbor, _), (left_dummy, left_neighbor, _) = pair
        editable.AddBond(right_neighbor, left_neighbor, Chem.BondType.SINGLE)
        for atom_index in sorted((right_dummy, left_dummy), reverse=True):
            editable.RemoveAtom(atom_index)

    terminal_dummies = [
        atom for atom in editable.GetAtoms() if atom.GetAtomicNum() == 0
    ]
    if len(terminal_dummies) != 2:
        raise ValueError(f"Expected two terminal wildcards, found {len(terminal_dummies)}")
    for atom in terminal_dummies:
        atom.SetAtomicNum(6)
        atom.SetIsotope(0)
        atom.SetNoImplicit(False)

    chain = editable.GetMol()
    Chem.SanitizeMol(chain)
    return Chem.AddHs(chain)


def minimum_degree(monomer_smiles: str, minimum_heavy_atoms: int) -> int:
    for degree in range(1, 501):
        chain = build_methyl_terminated_chain(monomer_smiles, degree)
        if chain.GetNumHeavyAtoms() >= minimum_heavy_atoms:
            return degree
    raise ValueError("No degree up to 500 satisfies the heavy-atom target")


def embed(chain: Chem.Mol, seed: int) -> Chem.Mol:
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.useRandomCoords = True
    params.maxIterations = 5000
    if AllChem.EmbedMolecule(chain, params) != 0:
        raise RuntimeError("RDKit failed to generate a 3D conformer")
    if AllChem.UFFHasAllMoleculeParams(chain):
        AllChem.UFFOptimizeMolecule(chain, maxIters=500)
    return chain


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--monomer", default=DEFAULT_MONOMER)
    parser.add_argument("--minimum-heavy-atoms", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    degree = minimum_degree(args.monomer, args.minimum_heavy_atoms)
    chain = embed(build_methyl_terminated_chain(args.monomer, degree), args.seed)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    sdf_path = output_dir / "top1_methyl_terminated.sdf"
    pdb_path = output_dir / "top1_methyl_terminated.pdb"
    manifest_path = output_dir / "build_manifest.json"
    Chem.MolToMolFile(chain, str(sdf_path))
    Chem.MolToPDBFile(chain, str(pdb_path))

    manifest = {
        "status": "GEOMETRY_READY_FORCE_FIELD_NOT_ASSIGNED",
        "candidate": "continuous_top20_rank1",
        "canonical_repeat_smiles": "O=C(OCCCOCCO[*:1])[*:2]",
        "builder_repeat_smiles": args.monomer,
        "degree_of_polymerization": degree,
        "minimum_heavy_atoms": args.minimum_heavy_atoms,
        "actual_heavy_atoms": chain.GetNumHeavyAtoms(),
        "total_atoms_with_hydrogen": chain.GetNumAtoms(),
        "molecular_formula": rdMolDescriptors.CalcMolFormula(chain),
        "molecular_weight_g_mol": Descriptors.MolWt(chain),
        "terminal_cap": "methyl",
        "embedding": "RDKit ETKDGv3",
        "optimization": "UFF geometry only; not the MD force field",
        "random_seed": args.seed,
        "pcff_plus_parameterized": False,
        "files": {
            sdf_path.name: _sha256(sdf_path),
            pdb_path.name: _sha256(pdb_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
