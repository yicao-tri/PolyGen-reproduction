# Integration and preservation record

This branch starts at local `a8214ae`, which already integrates the grid, multi-property, manuscript, PI1M and scalar acceptance work. Fresh fetch found an additional real commit `f1f4f54` on PR #5; it was cherry-picked as a publication-figure/provenance asset without promoting the PFP smoke evidence.

All original local refs and tracked/untracked scientific outputs were preserved before mutation in the external handoff evidence folder. The environment `.venv` remains at its original path and was inventoried as ignored; caches and the environment are excluded from content archives. All gap-package checkpoints are preserved in the full external tar; only compact files are copied here. `HANDOFF_COPY_MANIFEST.json` lists exact inclusion decisions and hashes. Stable historical docs and raw outputs remain in place; no cleanup deletes were proposed.

Legacy branches/PRs are retained for review. Patch-equivalence alone is insufficient for removing PR #8/#10/#13 because their commits combine overlapping content differently. `branch_inventory.json` reports unmatched patch commits; compare final file trees before retiring them. PR #2 also retains distinct older content. These are preserved, not claimed merged. Consolidation means a single proposed review line; GitHub main and old PR states remain separately reported.

A4 Hisa-review patches remain isolated in the gap package. They have not been applied to production scripts in this handoff. Items #8 policy and #9 physical/process evidence need owner decisions; unit-test PASS is not Hisa approval. This keeps scientific/code decisions explicit rather than silently bundling behavior changes into an archive PR.

Historical documents in the root and Overleaf staging remain dated references. Start with the root HANDOFF and roadmap. The old grid analysis.log and Hub notes are not current status authorities. Existing prunable worktree registrations are retained; they consume metadata only and deleting them provides little benefit while open PR branches still need review.
