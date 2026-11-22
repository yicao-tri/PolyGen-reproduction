# Prospective MD validation protocol

## Primary question

Do the 20 continuous-conditioning candidates selected before MD achieve higher independently simulated ionic conductivity than candidates from binary PolyGen and the published PolyGen candidate pool under one common protocol?

## Frozen cohorts

- 20 continuous candidates requested at log conductivity -3, ranked by `predicted_log_sigma - 1.96 × uncertainty` after validity, novelty, support and uncertainty gates.
- 20 binary candidates selected by the identical rule.
- 20 published PolyGen candidates selected by a SHA-256 ordering of p-SMILES, independent of their already published conductivity outcomes. Their historical outcomes are retained only for audit and must not be used for prospective triage.
- Add PEO as a protocol control when its exact build specification is recovered from the original workflow.

## Simulation and analysis contract

Use the same LiTFSI formulation, 353 K condition, chain construction, PCFF+ parameters, relaxation, equilibration, production length and cluster Nernst–Einstein estimator as the published PolyGen workflow. Run five independently initialized replicas per structure. Randomize and blind cohort labels during build/simulation. Record build and force-field failures as outcomes rather than silently replacing structures.

Primary estimand: difference in structure-level mean log10 conductivity between continuous and binary cohorts. Secondary estimands: continuous versus legacy controls; probability of exceeding the best training-set benchmark; lower-confidence-bound yield; build success; transference number where available. Use structure—not trajectory frames—as the independent unit. Report bootstrap confidence intervals over structures and a permutation test of cohort labels. Do not select the best replica.

## Escalation gate

The current manifest is `PLANNED_NOT_RUN`. First execute standardized short MD for all cohorts. Long MD is permitted only under a frozen rule based on short-MD uncertainty and build success, applied identically across cohorts.
