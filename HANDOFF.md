# PolyGen internship handoff — 21 November 2026

**Canonical main is consolidated; park new compute.** Prediction-stage evidence exists; physical validation and a publication-ready discovery claim do not.

- [Hisa roadmap and publication gates](docs/handoff/ROADMAP.md)
- [Scope, evidence boundaries and ownership](docs/handoff/SPEC.md)
- [Integration, archives and unresolved branches](docs/handoff/INTEGRATION.md)
- [Validation commands and results](docs/handoff/VALIDATION.md)
- [Rebuildable evidence SQL index](registry/README.md)
- [Preserved gap-analysis entry point](evidence/gap-analysis-20261016/README.md)

The authoritative branch is `main`. PR #14 was merged normally as `2731d7ddd232f36c84b09fe69f0a23b8d110d214` after checking actual repository rules: main protection disabled, no required checks/reviews, and ordinary merge allowed. Historical branches are preserved in verified `archive/20261121/` GitHub tags and complete bundles; superseded PRs were closed, not represented as independently merged. See `docs/handoff/branch_retirement_receipt.json`.

External restoration folder: `/Users/yicao/Documents/ARC/internship-handoff-20261121/projects/polygenius-optional/evidence/`. It contains all-ref Git bundles, full working-tree/gap archives, dirty and ignored inventories, source hashes and verification receipts. Do not copy the external tracking status into the scientific database.

Restore Git history in a new directory with `git clone local_all_refs.bundle restored-polygen`; restore non-Git results from `local_working_tree_preserved.tar.gz`, after checking archive hashes. Gap checkpoints live in `gap_analysis_preserved.tar.gz`. Never unpack over an active checkout. kozo legacy upstream and diffusion pilot were read and archived without overwriting their dirty files.
