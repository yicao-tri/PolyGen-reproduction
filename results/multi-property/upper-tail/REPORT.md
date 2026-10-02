# Multi-property Upper-tail prediction report

Status: definitive prediction phase complete; MD not run.

The frozen six-dimensional training rule retained **2494 / 6024** source rows (all six transformed properties at or below their respective full-source Q80 values). All four arms used the same rows, five seeds, 1,000 optimizer steps, 100 candidates per target cell, and the same frozen per-property RF verifier. The four target vectors Q80, Q85, Q90, and Q95 were defined from full-source marginal quantiles and used only as locked post-run queries/audits.

The primary evidence is in `metrics_by_cell.csv`, `paired_contrasts.csv`, `monotonicity.csv`, and `candidate_predictions.csv`. `unsupported_cells.csv` retains coordinate-wise and joint support status; binary target-vector incompatibility is an explicit negative control. `locked_tail_verifier_audit.csv` is a post-run audit only. No result supports MD or experimental claims.

Pairing status is recorded in `pairing_acceptance_audit.json`. Publication SVG/PNG and captions are under `publication/`.

The Nature-quality synthesis is `RESULTS_AND_DISCUSSION_NATURE.md`, with machine-readable Tables 1–6 and Figures 4–5 under `publication/`. The Obsidian-tracked evidence milestone is at `../../evidence/obsidian/multi-property-upper-tail-q80-q95/Multi-property Upper-tail Q80–Q95 — evidence milestone.md`; it includes the frozen manifests, candidate-level provenance, locked-tail audit, scripts, captions, and Overleaf handoff.
