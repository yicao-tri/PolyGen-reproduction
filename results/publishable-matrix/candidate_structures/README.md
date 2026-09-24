# Candidate structure figures

This directory contains deterministic RDKit 2-D depictions of the 20 binary
and 20 continuous seed-101 MD candidates.

- `binary_20_candidates.*`: binary overview grid.
- `continuous_20_candidates.*`: continuous overview grid.
- `shared_7_candidates.*`: seven canonical p-SMILES selected by both arms.
- `binary/` and `continuous/`: one PNG and one editable SVG per candidate.
- `candidate_structure_index.csv`: candidate ID, arm, target, surrogate score,
  overlap flag, canonical p-SMILES, and relative figure paths.

Green borders identify structures selected by both arms. Purple/red borders
identify binary/continuous-only selections. `[Cu]` and `[Au]` are polymer
connection markers from the source representation, not chemical composition.

Regenerate from the repository root:

```bash
.venv/bin/python scripts/render_candidate_structures.py \
  --candidates results/publishable-matrix/tables/md_candidates.csv \
  --output results/publishable-matrix/candidate_structures
```
