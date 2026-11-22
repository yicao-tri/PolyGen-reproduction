# Final readiness audit

The machine-readable audit is
`evidence/data/final_readiness_audit.json`; rerun it with:

```text
PYTHONDONTWRITEBYTECODE=1 \
/Users/yicao/Documents/ARC/PolyGen-reproduction/.venv/bin/python \
evidence/scripts/validate_final_readiness.py \
  --package-root . \
  --canonical-root /Users/yicao/Documents/ARC/PolyGen-reproduction
```

The package-level checks currently pass for the requested figures, tables,
visual QA, provenance, claim map, and strict MolMiner smoke. The audit remains
`incomplete_by_design` because the canonical physical gate is still
`PCFF+ = NO_GO`, `top1 readiness = NO_GO`, and `MD = not_run_by_contract`.
F7/F8 remain synthetic/planned placeholders, the isolated Hisa fixes are not
claimed as canonical merges, the full-source PI1M/ablation work is not
complete, and the final frozen-budget MolMiner/WeeMiner comparison is not
claimed.

`PUBLICATION_PROSE.md` packages the observed Results/Methods wording, figure
insertion map, and explicit replacement instructions for every synthetic or
planned component; it is included in the package manifest and provenance
ledger.

The package also includes the real five-seed 20-epoch and 50-epoch MolMiner
engineering comparisons (`T13`/`S1` and `T14`/`S2`). The 50-epoch arm has
finite checkpoints for all five seeds and improves the strict-generator
engineering evidence, but does not change the final-budget, task-aligned
WeeMiner, or physical-validation gates.

This boundary is intentional: a green package audit cannot promote RF-only
crossings to physical measurements or turn a task-mismatched WeeMiner smoke
into a C1 conductivity result.
