# PolyGen experiment-alignment TODO

This checklist aligns the current work with the published PolyGen study, [Yang et al., npj Computational Materials 10, 296 (2024)](https://www.nature.com/articles/s41524-024-01470-9), and the related closed-loop framework, [Lei et al., Digital Discovery (2025)](https://doi.org/10.1039/D4DD00293H). Status reflects the repository on 2026-09-24.

## Highest priority: independent physical validation

- [x] Freeze a five-seed continuous-versus-binary generator comparison with one independent verifier.
- [x] Freeze 20 continuous and 20 binary candidates before MD using the same support, uncertainty, validity and novelty gates.
- [x] Define a legacy PolyGen control panel using selection independent of published conductivity outcomes.
- [ ] Recover and freeze the exact PEO/build/formulation specification used by the published workflow.
- [ ] Run buildability and force-field-coverage checks on every frozen candidate; retain failures in the denominator.
- [ ] Run one randomized, blinded short-MD batch: continuous 20, binary 20, legacy PolyGen 20, plus PEO; five replicas per structure under the same LiTFSI/353 K/PCFF+ protocol.
- [ ] Analyze structure-level mean log conductivity with bootstrap confidence intervals and permutation tests; do not treat trajectory frames as replicates.
- [ ] Compare calibration of verifier predictions against MD and report rank correlation, MAE, interval coverage and OOD failures.
- [ ] Escalate to long MD only using a preregistered rule applied identically to all cohorts.

## Direct alignment with the original PolyGen paper

- [x] minGPT binary high/low baseline under a fixed budget.
- [x] Novelty and validity metrics.
- [x] Independent forward scoring and uncertainty/support gates, which are stricter than the original single GNN ranking.
- [ ] Reproduce uniqueness, synthesizability, similarity and diversity using the exact published metric definitions and denominators.
- [ ] Reproduce unconditional generation as a language-learning/control arm.
- [ ] Reproduce the full architecture comparison: minGPT versus 1D diffusion versus diffusion-LM.
- [ ] Reproduce hyperparameter sweeps and report quality-versus-training/inference-cost Pareto curves.
- [ ] Match the original large-candidate regime (100,000 conditional generations) or justify a power-equivalent fixed budget.
- [ ] Reproduce functional-group conditioning (ether present, carbonate absent), then compare it with continuous conductivity conditioning and joint conditioning.
- [ ] Reproduce PI1M pretraining followed by HTP-MD fine-tuning, including convergence, limited-data and diversity comparisons.
- [ ] Evaluate cation transference number alongside conductivity; do not infer it from conductivity alone.
- [ ] Reproduce the original candidate-selection funnel from generated pool through surrogate ranking, chemical filters, MD completion and final discoveries.

## Experiments required for the new contribution

- [ ] Repeat continuous-versus-binary training on support-aware targets, rather than reusing checkpoints trained for -5/-4/-3.
- [ ] Add continuous + condition dropout and continuous + auxiliary prediction head arms with equal parameter and compute budgets.
- [ ] Add a constructability objective or constrained decoder to recover the validity/novelty loss observed for continuous conditioning.
- [ ] Add PEDatamine only after unit harmonization, polymer identity resolution and DOI/polymer-family-disjoint splitting.
- [ ] Train a calibrated multi-domain forward model that outputs conductivity, uncertainty and support across chemistry, salt, loading and temperature.
- [ ] Test held-out temperature interpolation using repeated temperature curves for the same polymer/formulation.
- [ ] Test held-out salt/temperature/formulation combinations separately from unseen polymer structures.
- [ ] Upgrade C2 with a verifier that passes a prespecified held-out-formulation RMSE/calibration gate.
- [ ] Connect chemistry and formulation generators only where the joint verifier marks the complete system in-domain.
- [ ] Add DP/MW consistency, architecture, force-field coverage, polymerizability and simulation-build success to the final hit definition.

## Closed-loop experiments

- [ ] After unbiased MD validation, append completed outcomes—including failures—to a versioned training table.
- [ ] Compare no-feedback, random-feedback and uncertainty/expected-improvement acquisition under paired budgets.
- [ ] Run at least two feedback iterations and report mean, lower confidence bound, diversity and failure rate per iteration.
- [ ] Keep a sealed external test panel for the final iteration; never use it for acquisition or early stopping.

## Manuscript gates

- [ ] Promote the continuous-conditioning claim from exploratory to confirmatory with a preregistered seed count/power analysis and support-aware targets.
- [ ] Require MD evidence before using “higher conductivity” or “discovery”; before then use “verifier-defined target adherence.”
- [ ] Report all generation denominators: requested, parsed, valid, novel, in-support, unique, buildable, MD-complete and target-hitting.
- [ ] Release exact configs, environment, checkpoints, split rows, candidate manifests, failed-build logs and analysis scripts.
