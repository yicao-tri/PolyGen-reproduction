# PolyGen actual-data reproduction

This is a self-contained, actual-data-only reproduction workspace for the public
PolyGen release associated with *De novo design of polymer electrolytes using
GPT-based and diffusion-based generative models*.

The scientific numbers in this folder are not copied from the paper. They are
generated from the machine-readable inputs under `inputs/` or from real execution
artifacts under `results/dev/`. See `DATA_POLICY.md` for the enforceable rule.

## Run the complete local pipeline

```bash
./run_end_to_end.sh
```

The command regenerates:

- raw dataset and validation-MD summaries;
- every-candidate replica statistics without omitting or renaming input groups;
- generated-polymer iteration summaries;
- vector plots whose axes, thresholds, counts, and annotations are calculated at
  runtime;
- summaries and plots of actual DEV model runs;
- input and full-package SHA-256 manifests;
- provenance and internal-consistency checks.
- an evidence-derived panel/table coverage matrix that never imports article values.

Only Python's standard library is required for this local aggregation pipeline.

## Result layout

```text
inputs/                 raw machine-readable release and validation files
results/dev/            samples and metrics from real DEV executions
results/tables/         script-generated summaries and provenance manifests
results/figures/        script-generated SVG plots
scripts/                aggregation, verification, and DEV run entry points
patches/                source fixes used to execute the released code
vendor/                 patched upstream PolyGen v1.0.0 source and public minGPT checkpoints
```

The main generated scientific summary is
`results/tables/dataset_summary.json`. Actual model metrics are in
`results/tables/dev_execution_summary.json` and
`results/tables/dev_metrics_long.csv`. `results/tables/artifact_manifest.csv`
hashes every package file except the manifest itself.

The accepted lightweight training proof is under
`results/dev/minGPT-checkpoint-finetune-smoke-seed907/`. Its training loss,
generated samples, evaluation metrics, runtime, environment, and artifact hashes
all come from one real DEV invocation. The matching loss figure is
`results/figures/actual_mingpt_smoke_losses.svg`.

`results/dev/kozo-dev-e2e-probe.json` is a machine-generated live probe of the
DEV backend, nginx gateway, activity-user path, database search, and returned CIF
structure. Its request parameters and every observed response fact are recorded
in the file; no result is copied into this README.

`REPRODUCTION_COVERAGE.md` and
`results/tables/reproduction_coverage.csv` are regenerated from the artifacts
that are actually present. They distinguish completed raw-data reproduction,
real-run analogues, partial evidence, conceptual panels, and missing inputs.
Panel identifiers are scope metadata only; the coverage generator contains no
scientific target copied from the article.

## Re-running models on DEV

The model entry points require all experiment-defining arguments explicitly.
This prevents publication settings from being silently embedded as script
constants:

```bash
python scripts/run_mingpt_checkpoint.py --help
python scripts/run_mingpt_training.py --help
python scripts/run_diffusion1d_training.py --help
python scripts/run_diffusionlm_saved_samples.py --help
python scripts/probe_kozo_dev.py --help
```

For the small checkpoint-fine-tuning smoke used in this package, run:

```bash
./scripts/run_mingpt_smoke.sh results/dev/minGPT-checkpoint-finetune-smoke-rerun 907
```

This executes only 10 optimizer steps and 100 generations. It starts from the
public checkpoint bundled in the release; it does not perform the large training
run or load any numeric value from the article.

The runners default to `vendor/PolyGen-1.0.0`, so a second source checkout is not
required. Experiment-defining parameters remain mandatory and must be supplied by
the caller. Run them inside the prepared PolyGen environment on DEV, write to a
new directory, then copy the resulting JSON/CSV artifacts under `results/dev/`
and rerun `./run_end_to_end.sh`.

The bundled source is the upstream v1.0.0 release with only the changes recorded
in `patches/polygen-v1.0.0-reproducibility.patch`. See `VENDORED_SOURCE.md` for
the inclusion and exclusion policy.

## What is and is not compared

Actual released data and actual DEV output are reported exactly as computed. A
paper-only number is not imported merely to create a numeric delta. Consequently,
the package can demonstrate execution, data aggregation, and internal
reproducibility, but it does not claim that unavailable publication arrays or
checkpoints have been recreated. Details are in `AUDIT.md`.
