# R1 — Does the evaluator support the next decision?

**State:** reviewable design, not preregistered or executed. The first spend would be bounded retrospective evaluation on existing labels. It buys information about nomination/ranking, not new candidate conductivities. Main scientific uncertainty: is zero RF crossing merely a range restriction, poor ordering, or both—and does any modest alternative improve the allocation of a fixed validation budget?

## 1. Competing explanations and discriminating observations

| Explanation | Observation that distinguishes it | Consequence |
|---|---|---|
| Range restriction alone | Predictions cannot exceed training maximum, but high-label recovery is useful | Retain RF as a ranker if justified; retire its absolute crossing gate. |
| Poor discrimination as well | RF fails high-label nomination and within-tail rank tests | Nomination strategy needs repair or independent labels, not a larger generated pool. |
| A flexible evaluator helps | A predeclared alternative improves held-out known-label nomination over the same simple baseline | It becomes a candidate nomination tool; generated-candidate physical truth remains untested. |
| Apparent improvement is easy negatives/support | Gain disappears against near-boundary controls or at lower structural support | Limit domain/claim; do not call it extrapolation capacity. |
| No available evaluator is adequate | No model passes the proposed decision gate | Park generator extrapolation rankings. Consider a separately budgeted outcome-blind physical panel, or stop. |

The RF convex-range bound is a code/method derivation already established. Do not spend model-training budget trying to rediscover it or require a forest to pass an impossible event.

## 2. Immutable inputs and retrospective boundary

Use canonical PolyGen `main` as located by CURRENT_STATE, observed locally at `de9f877e4214e4abb51640793327b2f6d2396bd4`. Source `inputs/release-data/htpmd-trainset.csv` has registered SHA-256 `89fec2f276df6bbc393a13c4bcf9359ce2a512c0b8c59a9c9cb45499be0c5b69`: 6,024 source structures. The historical Q80 manifest supplies 4,819 lower-support rows and 1,205 high-tail rows. Training maximum is −4.084499110675755 log10(S/cm); nominal Q80 is −4.084468800285627. Use the registered row sets rather than recomputing a convenient boundary.

All 1,205 tail labels have been inspected previously. They are **retrospective challenge labels**, not a fresh sealed test. Holding them out of a new fit does not erase prior knowledge. They must not be used to select hyperparameters, adjust thresholds or select a winning model after seeing results. Any later physical/externally sourced confirmation must be separately frozen. The experiment evaluates labels from one HTP-MD source; it does not certify experimental conductivity.

Before fits: verify input hashes, units, positivity before log transform, canonical repeat-unit identities, row IDs and duplicate/conflicting-label groups. If canonical groups cross the historical boundary, report and halt for an explicit grouping/deviation decision. Do not silently discard rows or overwrite original manifests. Exact-string uniqueness is not assumed to prove canonical/family separation.

## 3. Paired data construction

Assign only the lower-support canonical groups to three deterministic hash folds (`sha256('polygen-r1-20261124|' + canonical_id) mod 3`). Every arm uses identical folds, descriptors and row order. For each outer fold:

- Fit on two lower-support folds, approximately 3,212 rows; exact sizes must be reported after the audit.
- Test on the remaining lower-support fold, approximately 1,607 rows, **plus the same 1,205 known tail structures**.
- Fit all preprocessing using the outer training rows only. Hyperparameter choices use three inner group folds entirely within those training rows.
- Evaluate the full outer panel and a prespecified harder panel that keeps only Q60–Q80 lower-support negatives plus the same tail. Define those negatives from the historical source quantiles and save exact IDs before fits; label-defined challenge construction is disclosed, not treated as deployment sampling.

This creates known high and low outcomes; an all-tail panel alone cannot assess high-versus-low discrimination. It also sacrifices some training support relative to the original 4,819-row RF. Therefore compare newly fitted arms to each other, not causally against the old full-training RF summary. The historic RF remains a separate range/diagnostic reference. Three folds are robustness blocks, not three independent experiments: tail identities repeat.

## 4. Evaluator arms and controls

Use the exact historical fingerprint constructor (`compat.fp` / `fp_array` used by `scripts/run_extrapolation_benchmark.py`); record its parameters, library version and code hash. This fixes representation while varying the predictor.

| Arm | Frozen construction / fitting | Scientific role |
|---|---|---|
| RF | 300 trees, minimum leaf 2, max_features=sqrt, seed 20260923; squared-error criterion | Bounded baseline; ranking may still be useful. |
| Ridge | Same fingerprints; alpha in {1, 10, 100}, selected by inner group-CV MAE | Simple predictor with no averaging-tree output bound; not presumed to extrapolate correctly. |
| Small MLP | Same fingerprints; one 64-unit hidden layer, ReLU, alpha in {0.001, 0.01}, max_iter=500, fixed seed 20261124; inner group-CV MAE | Flexible sensitivity arm; retain nonconvergence/failures. No architecture search on the challenge tail. |
| Nearest neighbor | Training-only maximum-Tanimoto neighbor; average targets across exact similarity ties | Simple nomination baseline. It too is bounded in value, yet can rank. |
| Random nomination | Expected positive fraction for each exact panel; analytic finite-population reference | Chance allocation of the same slots; no artificial independent replicates from random draws. |

Use identical train-derived normalization where required; no tail-fitted calibration or full-source RF in the blind comparison. Predictions, missing scores and fitting failures remain in complete ID-aligned outputs. A failed arm is unavailable, not assigned zero conductivity or quietly replaced. One deterministic seed per fit limits scope; these fits do not estimate neural-training-seed variability.

## 5. Endpoints and analysis

**Primary operational endpoint:** precision among the top K=100 nominations, where a positive is a known test structure above the historical Q80 training boundary. For each evaluator compute ΔP@100 versus the nearest-neighbor baseline on identical IDs. No padding by invalid/duplicate rows. Nearest-neighbor and model score ties at the K boundary use fractional inclusion of the entire tied group, avoiding arbitrary ID ordering as hidden performance. Report how many distinct known-positive nominations the difference represents. All methods receive the same K and candidate panel.

**Provisional practical target:** at least +0.10 ΔP@100, i.e. ten additional known-positive choices per 100 slots, with a simultaneous interval excluding zero. This is a **review proposal**, not a threshold inferred from data or a project-approved scientific standard. Hisa/reviewer should accept or revise it before any fits. Report the entire precision/recall-versus-K curve (K=25, 50, 100, 200) as sensitivity; do not choose K after results.

Diagnostics: AUROC, within-tail Spearman rank, MAE/signed bias by tail bin, score range versus training maximum, and distance-stratified nomination performance. The hard near-boundary panel exposes easy-negative effects. Record distinct nominated structures, calibration/coverage and failure/abstention counts. Tree SD remains ensemble spread, not a calibrated prediction interval. No numeric-conductivity or uncertainty-calibration qualification follows from passing a ranking test. An unbounded output alone is not validation.

Report the mean paired nomination contrast across the three outer panels, every panel result, and conditional uncertainty from 2,000 paired structure/group bootstrap resamples. Reuse a tail structure's bootstrap weight in all folds; do not count its three predictions as independent labels. With no duplicated canonical groups, the resampling group is source structure. Apply a Bonferroni family across RF, ridge and MLP contrasts (nominal 98.33% individual percentile intervals for an approximate 95% simultaneous family). State explicitly that fixed-fit conditional bootstrap excludes retraining uncertainty and that family-level chemical generality is not established. These retrospective intervals and the provisional gate are decision aids, not confirmatory discovery p-values.

Separate two decisions. **Useful ranking** is provisionally P@100 ≥0.80, a reported conditional lower bound above the analytic chance fraction, and hard-panel AUROC nominal-95% lower bound >0.5; assess the nearest-neighbor baseline too. This 80-of-100 target also needs reviewer acceptance before fits, and is retrospective assay qualification only. **Justifying a change of evaluator** additionally requires full-panel ΔP@100 ≥0.10 and the three-contrast simultaneous lower bound >0; the hard-panel point ΔP@100 must be nonnegative. No improvement over an already useful baseline is not failure of every evaluator. If baseline precision exceeds 0.90, the proposed ten-extra-hit target has insufficient headroom: report a ceiling-limited comparison and retain a qualified baseline rather than inventing a generator failure. A candidate that only passes on easy negatives receives no broad nomination qualification. If intervals are too wide, call the outcome inconclusive; additional bootstrap draws, repeated use of the same tail or more generated candidates do not purchase independent evidence.

## 6. Budget, outputs and stop rules

Proposed maximum before any new design: 9 outer predictor fits (three arms × three folds), plus 45 inner tuning fits (three outer folds × three inner folds × five ridge/MLP configurations), totaling **54 predictor fits**; nearest-neighbor evaluation is additional scoring, not a fitted generator. No new generator, candidates, physical labels or MD. Feature extraction is shared. No hardware timing is available: do not invent GPU-hours. Proposed analyst effort is 3–5 focused days for identity/provenance, fit harness, interpretation and report if all dependencies are available; runtime and queue waits need a later measured pilot. These estimates are neither resource approval nor a completion date.

Outputs under a **new** result root if later approved: frozen contract/input and fold hashes; arm configs/environment; exact fit counts and failures; ID-aligned held-out predictions; full/hard-panel nomination tables with tie handling; paired conditional intervals and diagnostics; cost log; a short explanation-to-action report. Never overwrite the frozen results used here.

Stop after this report. No tail-driven hyperparameter expansion. A passing ranker permits proposing a separate fair generator comparison—not launching it automatically. No adequate ranker means either separately approve an outcome-blind physical panel with parameterization/control/QC feasibility, or park. No result here proves generator physical superiority/failure or agent planning skill.

## 7. Next stage contract, only if justified

The subsequent generator study would preserve the old single-class binary as a historical negative control and separately define high as the top 20% **within training support**. Continuous, that nondegenerate binary, and unconditional plus common reranking would share source rows, model/seed blocks, raw decoding budgets and nomination rules. Report raw-attempt distinct-valid-novel/buildable yield alongside error conditional on valid output. Fragment is optional and requires matched corpus/checkpoint selection plus accepted collaborator ownership. Independent unit is the paired training seed, not candidate row. Seed count and any physical cohort require their own power/precision and resource decision. R1 does not authorize the earlier v2 illustrative 130/610 trajectories.
