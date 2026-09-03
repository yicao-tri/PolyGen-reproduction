# Reproducibility audit

## Evidence admitted to this package

There are only two admitted evidence classes:

1. machine-readable files distributed with the public code/data release or as an
   official tabular supplement;
2. JSON and CSV artifacts emitted by real executions on the provisioned DEV
   instance.

The input hash manifest and output provenance manifests identify the exact files
used for each derived artifact. The scripts recompute statistics from those files
on every run.

The model runners no longer depend on a second checkout: the necessary v1.0.0
source and public minGPT checkpoints are bundled under `vendor/`. Pre-rendered
upstream images, notebooks, and output-only loss artifacts are excluded so they
cannot be mistaken for results produced by this reproduction.

## Actual computations completed

- The release training tables are aggregated independently, including their
  conductivity and transference distributions.
- The released binary training file is joined to the continuous training file to
  calculate class balance and before/after-duplication distributions.
- The generated-polymer iterations are aggregated directly from their released
  simulation rows, retaining failed rows.
- Every validation-MD attempt is grouped by the literal prefix of its simulation
  name. Every group and every completed replica is included; no publication-style
  subset or manual index correction is applied.
- The released minGPT checkpoint was executed on DEV and its samples and metrics
  are archived.
- A lightweight minGPT training smoke was executed from the bundled public
  checkpoint: 10 optimizer steps followed by fresh generation and full scoring.
  Its DEV-generated runner, input-checkpoint, dataset, loss, and sample hashes are
  revalidated against the self-contained package.
- The released diffusionLM sample files were rescored on DEV and both the scored
  rows and calculated metrics are archived.
- diffusion1D training, validation, sampling, and checkpoint code paths were
  exercised on DEV. The actual run and decoded-sample summaries are archived.

All quantitative details for these bullets live in generated files rather than in
this manually maintained document.

## Differences and limits

The archived DEV experiments do not necessarily use the same sample population,
training duration, or unavailable weights as the publication experiments. Their
values are therefore reported as actual execution results, not substituted for
paper panels.

An exact numeric paper delta is intentionally absent whenever the comparison side
exists only as a value printed in a PDF. Adding such a value would violate the
actual-data-only policy. Exact comparison becomes valid only when the corresponding
machine-readable publication output, checkpoint, prediction array, or training log
is available and hashed as an input.

The currently unavailable evidence includes publication-generating arrays for
several panels, property-predictor artifacts, diffusion checkpoint files that are
not present in the release checkout, and pretraining/grid-search execution
artifacts. These are source-availability limits, not values to be approximated or
hardcoded.

## Execution patch

`patches/polygen-v1.0.0-reproducibility.patch` contains small code corrections
needed to run the released pipelines reliably. It fixes validation-batch use,
checkpoint configuration naming, ordered defensive token extraction, missing imports,
module qualification, and device selection. The patch contains no publication
result table.

## Verification

`scripts/verify_package.py` performs data-derived checks only. It recalculates the
summaries from raw inputs, recalculates the DEV index from actual artifacts,
checks row-level consistency, confirms that no PDF or rendered paper page is in
the package, and validates the full artifact manifest. It has no expected paper
counts or metric constants.
