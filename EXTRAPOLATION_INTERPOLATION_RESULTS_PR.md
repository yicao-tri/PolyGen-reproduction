# PolyGen Work — extrapolation and new interpolation results

## TL;DR

This PR creates a single, reviewable evidence package for the new interpolation,
upper-tail, and structural-OOD analyses built on the original PolyGen pipeline.

The central result is deliberately narrower than a claim of successful
extrapolation: **continuous conditioning preserves useful target control and
valid-output yield near a frozen Q80 boundary, but the prediction-only benchmark
does not produce RF-confirmed candidates above the training frontier.**

At Q95, continuous conditioning retains validity 0.560 and strict-hit 0.522,
whereas the frozen binary arm is unsupported at Q90/Q95 because the original
−4.0 threshold becomes single-class after Q80 truncation. The unconditional
plus reranking control is unsupported beyond the boundary. The locked-tail RF
has mean observed-minus-predicted residual +0.262 log units, so RF scores cannot
be treated as independent evidence of extrapolation. MD was not started.

## Why this PR exists

The original PolyGen result established conditional generation and comparison
against binary controls in the observed regime. This PR asks the next scientific
question:

> Does continuous conditioning provide a reproducible advantage when the model
> is trained below a declared property boundary and asked to control targets
> toward, across, or beyond that boundary?

The new analyses separate three claims that were previously easy to conflate:

1. interpolation/control: can requested targets be followed inside support?
2. near-boundary control: does the response remain usable as the request
   approaches the observed frontier?
3. extrapolation: does an independently checked candidate cross the locked
   training maximum?

The PR stores the evidence for all three questions without rewriting PR4/PR6
history or modifying `sources/`.

## Figure 1 — upper-tail response and valid yield

![Figure 1: upper-tail response](https://raw.githubusercontent.com/yicao-tri/PolyGen-reproduction/experiment/extrapolation-interpolation-results/results/upper-tail/publication/Figure_1_upper_tail_response.png)

Continuous conditioning is the only arm with valid output in every target cell.
Its target MAE increases from 0.231 at the actual training boundary to 0.406 at
Q95, while RF predictions remain near −4.31 log10(S cm−1), below both the
requested Q95 target (−3.902) and the actual training maximum (−4.0845).
This is evidence for near-boundary control with degradation, not evidence that
the generated candidates cross the frontier.

## Figure 2 — strict-hit, validity, and unsupported cells

![Figure 2: cell-level quality](https://raw.githubusercontent.com/yicao-tri/PolyGen-reproduction/experiment/extrapolation-interpolation-results/results/upper-tail/publication/Figure_2_upper_tail_quality_heatmap.png)

The heatmap keeps unsupported cells visible. Continuous maintains strict-hit
rates of 0.554, 0.570, 0.558, and 0.522 from Boundary through Q95. Binary is
usable only at Boundary/Q85 and falls to unsupported at Q90/Q95. The
unconditional+rerranking control is effectively unsupported beyond the
boundary. Zeros in unsupported cells are not interpreted as measured failure;
the cell-level CSV records the distinction explicitly.

## Figure 3 — verifier calibration in the locked tail

![Figure 3: locked-tail RF calibration](https://raw.githubusercontent.com/yicao-tri/PolyGen-reproduction/experiment/extrapolation-interpolation-results/results/upper-tail/publication/Figure_3_locked_tail_rf_calibration.png)

The frozen RF underpredicts the 903-row Q80–Q95 audit tail: MAE 0.262,
RMSE 0.269, and mean observed-minus-predicted residual +0.262 log units.
This is a mechanism-level limitation of the screening verifier. It explains why
flat or sub-boundary RF predictions cannot by themselves establish generator
failure, and why a future extrapolation claim requires independent MD or
experimental validation.

## New interpolation and structural-OOD results

The interpolation package extends the same matched-seed reporting schema to
in-support targets, preserving target adherence, strict-hit, monotonicity,
validity, novelty, uniqueness, diversity, RF uncertainty, support, and failure
accounting. Structural-OOD adds a family/scaffold-held-out audit so that
property-tail behavior is not mistaken for chemical-family generalization.

These analyses turn the original PolyGen question into a more discriminating
program: continuous conditioning may improve *control resolution* and
near-boundary coverage without implying that the model has learned a physically
valid route beyond the data frontier.

## Experimental contract

- Frozen source and split manifests are included with hashes and row IDs.
- Upper-tail training uses 4,819 rows at or below nominal Q80; 903 Q80–Q95
  rows are locked with zero exact-SMILES overlap.
- Arms are continuous, frozen-threshold binary, and unconditional+rerranking.
- Seeds are matched: 17, 42, 202, 303, 907.
- Training budget is 1,000 optimizer steps; target cells report 100 candidates.
- RF prediction, uncertainty, support, novelty, residual, target adherence,
  strict-hit, monotonicity, validity, uniqueness, diversity, and failure are
  retained in machine-readable outputs.
- MD is not run in this PR.

## Main contribution to the paper

This PR adds a defensible boundary between controllability and extrapolation.
It contributes:

1. a frozen Q80–Q95 protocol with explicit actual-boundary accounting;
2. matched continuous/binary/unconditional controls;
3. a complete surrogate-quality audit rather than RF-only ranking;
4. explicit unsupported-cell and degenerate-control reporting;
5. publication-ready figures, captions, tables, and provenance;
6. a candidate queue for a separately authorized MD validation stage.

The proposed manuscript-level claim is:

> Continuous conditioning retains verifier-defined target control and valid
> chemical yield near a Q80 training boundary, but this prediction-only study
> provides no evidence of surrogate-confirmed extrapolation beyond Q80.

## Limitations and required follow-up

- The frozen −4.0 binary threshold is degenerate after Q80 truncation. A
  training-median binary cutoff is a separate sensitivity estimand and is not
  merged into the primary comparison.
- RF residual bias prevents RF-only claims of frontier crossing.
- MD and experimental measurements remain intentionally outside this PR.
- The next authorized stage is stratified MD validation followed by RF–MD
  residual calibration and only then any active-learning update.

## Review order and artifact map

Review the evidence in this order:

1. `EXTRAPOLATION_EXPERIMENT_BLUEPRINT.md`
2. `results/interpolation/REPORT.md`
3. `results/upper-tail/REPORT.md`
4. `results/structural-ood/STRUCTURAL_OOD_REPORT.md`
5. `results/*/publication/RESULTS_AND_DISCUSSION.md`
6. machine-readable manifests, metrics, unsupported-cell tables, and producing
   scripts.

The publication figure captions are stored beside the figures in
`results/interpolation/publication/FIGURE_CAPTIONS.md` and
`results/upper-tail/publication/FIGURE_CAPTIONS.md`.

This is an experiment/evidence PR. It does not modify the submission-root
manuscript, does not push to Overleaf, and does not claim MD-confirmed
conductivity.
