# Agent validation — 21 November 2026

Passed in the isolated integration worktree:

- `python3 scripts/validate_research_blueprint.py`
- Original project's `.venv/bin/python scripts/verify_extrapolation.py`
- Original project's `.venv/bin/python scripts/verify_upper_tail.py`
- Original project's `.venv/bin/python -m unittest discover -s tests -v`
- SQL opens read-only; integrity check is `ok`; all three named query column contracts execute; two independent builds produce identical SQLite SHA-256 and receipt.

Exact logs and exit codes are adjacent in `validation_summary.json` and `validation_*.log`. These are artifact/software checks by the agent, not human scientific approval. No new model training or MD was run. Historical gap readiness is intentionally incomplete; the curated compact copy omits large checkpoints listed in its manifest, so it is not represented as a freshly validated full training package. Use the complete preserved archive for full-package replay.

Full pytest validation: **17 passed in 3.94s**. The original virtualenv lacked pytest; pytest was installed into the external handoff `test-deps` folder and loaded through process-local PYTHONPATH. The shared original runtime was not changed.
