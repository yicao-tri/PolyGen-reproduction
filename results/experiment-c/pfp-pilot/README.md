# PFP top-1 paired pilot evidence package

This directory records the reproducible evidence for the first paired PFP-MD
comparison of the frozen continuous and binary PolyGen candidate arms.

## Scope

- Two top-1 candidates, selected before PFP results from the frozen PR #4
  conservative score.
- PFP v8.0.0/PBE, 353 K Langevin NVT, 1 fs timestep, 200 ps, one shared
  velocity seed per arm.
- The first 40 ps are discarded; the remaining 160 ps are analyzed with the
  HTP-MD-compatible endpoint diffusivity and cluster Nernst--Einstein (cNE0)
  adapter.
- The scientific label is `NON_CONVERGED_SMOKE_ONLY`: this is a technical
  pilot, not a converged estimate or a model-superiority claim.

## Review entry points

- `production/analysis/PFP_TOP1_PILOT_REPORT_ZH.md`: human-readable report,
  including the MSD figure and the continuous-versus-binary contrast.
- `production/analysis/paired/paired_summary.json`: machine-readable headline
  results and residuals.
- `production/analysis/validation.json`: 41/41 evidence gates.
- `config/top1_pilot_contract.json`: frozen candidates, protocol, and gates.
- `production/analysis/figures/pfp_top1_msd.svg`: editable trajectory
  diagnostic figure.

## Raw-trajectory provenance

The two ASE trajectory files and verbose production logs are deliberately not
committed: they are approximately 369 MB together and are available in the
recorded Matlantis run root
`/home/jovyan/mms-jobs/polygen-pfp-top1-production-v1`.

Their SHA-256 fingerprints are embedded in
`production/analysis/paired/paired_summary.json`, each arm's
`production/*/results/*/run_summary.json`, and `production/SHA256SUMS`.
The committed scripts reproduce the analysis from those trajectories; the
validator checks the frozen source/relaxation/trajectory chain before report
generation.

## Interpretation boundary

The PFP pilot ranks the continuous top-1 candidate above the binary top-1
candidate by +0.421501 log10(cNE0 S/cm), approximately 2.64-fold, in this
single paired configuration. It is encouraging directional evidence only.
The candidate systems differ by 3.2% in discretized molality and have only 10
LiTFSI pairs; both constraints are addressed by the planned concentration-
matched, multi-seed, longer-trajectory study documented in
`PFP_TOP10_WORKFLOW_ZH.md`.
