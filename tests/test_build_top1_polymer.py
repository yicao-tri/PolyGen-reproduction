import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_top1_polymer.py"
SPEC = importlib.util.spec_from_file_location("build_top1_polymer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_minimum_degree_and_methyl_caps():
    degree = MODULE.minimum_degree(MODULE.DEFAULT_MONOMER, 150)
    chain = MODULE.build_methyl_terminated_chain(MODULE.DEFAULT_MONOMER, degree)
    assert degree == 15
    assert chain.GetNumHeavyAtoms() == 152
    assert MODULE.rdMolDescriptors.CalcMolFormula(chain) == "C92H156O60"
    assert all(atom.GetAtomicNum() != 0 for atom in chain.GetAtoms())


def test_build_is_topologically_deterministic():
    first = MODULE.build_methyl_terminated_chain(MODULE.DEFAULT_MONOMER, 15)
    second = MODULE.build_methyl_terminated_chain(MODULE.DEFAULT_MONOMER, 15)
    assert MODULE.Chem.MolToSmiles(first) == MODULE.Chem.MolToSmiles(second)
