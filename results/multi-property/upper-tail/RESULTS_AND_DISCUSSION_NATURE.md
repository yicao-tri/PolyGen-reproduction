# Results and discussion — multi-property Upper-tail benchmark

## Design and acceptance boundary

We evaluated four matched generation arms under a six-dimensional Q80 truncation of the released HTP-MD table. The training intersection contained **2494 of 6024 rows (41.4%)**. Conductivity, Li/TFSI/polymer diffusivities were transformed with `log10`; transference number and molality were retained on their raw scales. All six dimensions were finite, while transference number contained nonphysical negative values and molality showed near-degenerate support; both facts are retained in the source audit rather than clipped.

Every arm used the same five seeds, 1,000 optimizer steps, 100 candidates per target cell, decoder settings, RF verifier, filters and output schema. The unit for paired contrasts is the seed × target cell. The locked Q80–Q95 source rows were excluded from generator/RF fitting, thresholding, filtering and selection; they appear only in the post-run calibration audit.

## Boundary control is support-limited rather than extrapolation-successful

Across the four query vectors, mean normalized joint RMSE was **1.97** for the multi-property arm and **2.15** for the scalar comparator. The multi-property arm therefore reduced descriptive joint error by **-0.18** normalized units, but this difference did not translate into a joint strict hit: joint strict-hit and all-six-property frontier-crossing rates were zero in every arm × target cell. The result supports improved surrogate adherence only within a support-limited prediction benchmark; it does not support validated property extrapolation.

The multi-property arm retained mean validity of **0.560**, compared with **0.519** for scalar conditioning. Its mean support and normalized RF uncertainty were **0.572** and **0.659**, respectively. The strict credibility gate (support ≥ 0.35, uncertainty < 0.35, joint normalized error < 0.5) yielded no eligible MD-review candidates, so no candidate was promoted to physical validation.

## Property-wise adherence and monotonicity

Property-wise target MAE is reported for every arm and target in Table 2. Candidate-wise monotonicity is a descriptive rank-paired diagnostic: conditional arms pair the same generated rank across target cells, whereas unconditional reranking pairs selected ranks and is explicitly non-inferential. The corresponding fractions are in Table 3 and Figure 5. No arm shows uniformly monotonic responses across all six properties, so the benchmark does not establish reliable joint monotonic control.

## Locked-tail calibration and false-positive risk

The locked-tail audit compares frozen RF predictions with observed source values in Q80–Q95 bands, separately for each property. Residuals are defined as observed minus RF prediction; positive values are underprediction. Figure 4D and Table 4 show the calibration bias by property and tail distance. These rows were never used to fit or select candidates, so the audit diagnoses surrogate behavior rather than validating generated structures.

For conductivity, the locked-tail residual means across Q80–Q85, Q85–Q90 and Q90–Q95 were +0.263, +0.307, +0.372 log units. This is evidence that RF confidence and RF accuracy must remain separate from MD confirmation.

## Interpretation

The evidence is consistent with a conservative conclusion: multi-property conditioning can reduce the average frozen-surrogate joint target error relative to scalar conductivity conditioning under a common Q80-intersection training set, but the same experiment exposes a severe support bottleneck. Because the joint target vectors are unsupported by the coordinate-wise maxima of the intersection, zero joint hits and zero frontier crossings are not evidence that the generator cannot discover high-property structures in a larger or better-supported dataset. They do show that this frozen benchmark cannot justify a claim of controlled upper-tail extrapolation.

The unavailable endpoints are MD-confirmed frontier crossing and residual learning, because MD was not run by contract. The next decisive experiment is a symmetric, blinded MD study over a predeclared stratified candidate set, with build failures retained in the denominator and residuals analyzed against target distance, support, uncertainty and structural distance.

