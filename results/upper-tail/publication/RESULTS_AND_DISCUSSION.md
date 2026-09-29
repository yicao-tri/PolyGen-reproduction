# Results and Discussion: Upper-tail prediction benchmark

## Results

We next asked whether the apparent controllability advantage of continuous
conditioning persists when generation is trained only below the observed upper
tail. We froze a source-level Q80 boundary before model fitting. The nominal
full-source Q80 was −4.08447 log10(S cm−1), and the inclusive training set
contained 4,819 rows with an actual maximum of −4.08450. The Q80–Q95 tail was
locked for evaluation and contained 903 rows with no exact-SMILES overlap with
training. Continuous, binary, and unconditional generation followed the same
five-seed schedule, 1,000-step budget, temperature, and per-cell generation
budget. The unconditional arm generated a matched 400-candidate pool per seed
and assigned 100 candidates to each target by frozen-verifier reranking.

The first result was a clear separation between boundary control and
extrapolation. Continuous conditioning produced valid output in every target
cell and maintained a mean strict-hit rate of 0.55 across the boundary-to-Q95
grid. Its validity remained between 0.56 and 0.58, but the target MAE rose
from 0.231 log units at the boundary to 0.406 at Q95. The corresponding RF
predictions remained nearly flat around −4.31 log10(S cm−1), well below the
actual training maximum. Consequently, none of the 2,000 continuous reported
candidates passed the support- and uncertainty-gated criterion for an
upper-tail RF prediction above the training maximum.

The binary control was not an interpretable high/low comparison under this
split. We preserved the original −4.0 threshold from the prior benchmark, but
all 4,819 training rows fell below it; the arm was therefore single-class.
Binary generation retained valid output at the boundary and Q85, with mean
strict-hit rates of 0.43 in both cells, but produced no valid candidates in
any Q90 or Q95 cell. The unconditional+rerranking arm was weaker still: only
three boundary cells contained any valid candidate, and all Q85–Q95 cells were
unsupported. These unsupported cells are reported explicitly rather than
converted to missing or silently excluded from the comparison.

The frozen surrogate audit explains why a higher requested target did not yield
validated surrogate extrapolation. On the 903 locked Q80–Q95 source rows, the
RF had an MAE of 0.262 log units and a mean observed-minus-predicted residual
of +0.262 log units. The residual was positive throughout the locked tail,
showing systematic RF underprediction beyond the training boundary. In other
words, a generated structure receiving a prediction below the boundary cannot
be interpreted as evidence that the generator failed to explore the tail; the
verifier itself has a measurable tail bias. Conversely, a high RF score would
require an independent validation step because RF confidence and RF accuracy
are not interchangeable in this regime.

## Discussion

These results support a narrower but more defensible conclusion than a claim of
continuous-conditioning-driven extrapolation. Under the frozen HTP-MD
representation and verifier, continuous conditioning preserved usable
boundary-adjacent control and substantially higher valid-output coverage than
the two controls. It did not, however, produce surrogate-confirmed candidates
above the observed training frontier. The response curves therefore demonstrate
control near a boundary, not validated extrapolation beyond it.

The most important negative result is methodological. The RF calibration plot
shows that the locked tail is systematically underpredicted, so the same RF
cannot serve as both the discovery objective and the evidence for crossing the
frontier. This is precisely the failure mode that a tail-holdout benchmark is
intended to expose. Any claim of true upper-tail discovery now requires an
independent MD readout, with candidate selection stratified by RF prediction,
uncertainty, support, and novelty. The 183-row candidate table is therefore a
review queue, not a discovery list.

The binary result also identifies a design constraint for the next experiment.
The original −4.0 cutoff becomes degenerate after truncation at Q80. A
training-median cutoff (−4.31463) would restore two classes, but it would answer
a different question: whether binary conditioning separates the lower and
upper halves of the truncated training distribution. That sensitivity should
be run separately and labelled as a new estimand; it should not be merged with
the primary frozen-threshold result.

The appropriate claim boundary is therefore: **continuous conditioning retains
verifier-defined control and valid chemical yield near a Q80 training boundary,
but this prediction-only benchmark provides no evidence of RF-confirmed
extrapolation beyond that boundary.** It does not establish MD-confirmed or
experimentally measured conductivity. The next authorized stage is an
outcome-blinded MD validation of the stratified candidate queue, followed by
RF–MD residual calibration before any active-learning update.
