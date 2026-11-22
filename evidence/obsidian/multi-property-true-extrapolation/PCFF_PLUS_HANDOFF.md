# PCFF+ parameterization handoff for multi-property extrapolation

## Scope

This handoff is for the frozen 48-slot Tier-1 proposal in `md_validation_plan.csv`. It does not authorize an MD launch by itself. The accepted protocol is LAMMPS with PCFF+, LiTFSI, 353 K, 1.5 mol/kg, the frozen chain/box construction, five independent replicas per structure, and the cluster Nernst–Einstein analysis.

## Required bundle per candidate

For every `candidate_id` with status `planned_not_run`, provide:

- canonical repeat-unit and polymerized structure with atom-map preserving the candidate ID;
- LAMMPS `data` file and `system.lmp` input;
- atom types, charges, masses, and residue/species labels;
- complete PCFF+ bond, angle, dihedral, improper, and nonbonded parameter tables;
- explicit Li/TFSI parameter provenance and cross-term definitions;
- a coverage report with numerator/denominator for every parameter class;
- SHA-256 for every supplied file;
- expected atom/species counts and initial salt molality;
- deterministic build seed and replica seed schedule.

## Acceptance checks before any run

Reject the bundle if any candidate has missing or guessed parameters, incomplete cross terms, atom-map drift, wrong Li/TFSI counts, wrong molality, or a coverage report below 100% for required interactions. `run 0` must complete with no missing coefficients, NaN, lost atoms, or topology errors. PFP/ASE output is not an accepted substitute.

## Run and analysis contract

After bundle acceptance, run a blinded short smoke for every arm/target stratum with identical schedule and replica policy. Record build failures and force-field failures in the denominator. Only after the predeclared short-MD QC gate may a structure be escalated to five replicas and longer production. Compute structure-level conductivity, transference number, and uncertainty with the frozen cluster Nernst–Einstein implementation; do not use trajectory frames as independent replicates.

## Required outputs

`md_job_manifest.csv`, `md_run_exit_codes.csv`, `md_failure_reasons.csv`, `md_structure_metrics.csv`, replica-level raw summaries, cluster population diagnostics, and `rf_md_residuals.csv` with `log_sigma_MD - log_sigma_RF`, target distance, support, uncertainty, and structural distance. The final primary contrast is paired `multi_continuous - scalar_continuous` joint MD-confirmed frontier crossing; no surrogate-only crossing may be promoted to the primary endpoint.
