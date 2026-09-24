# Bundled PolyGen source

`vendor/PolyGen-1.0.0` contains the code needed by the model runners, the release
training inputs, molecular-dynamics example files, and the publicly distributed
minGPT checkpoints. The upstream release is TRI-AMDD/PolyGen v1.0.0, identified
by the official release listing as commit `c64caaf`.

The exact local source used for this copy was
`/Users/yicao/Documents/ARC/09-02/PolyGen-1.0.0`. That source archive did not
contain Git metadata, so every included file is instead covered by the package's
SHA-256 artifact manifest.

The copy intentionally excludes:

- article PDFs and supplementary-page captures;
- notebooks and all pre-rendered PNG/JPG images;
- Python caches;
- the released diffusion1D loss artifact and loss plot;
- diffusionLM's released generated-sample directory, whose two admitted sample
  files live explicitly under `inputs/release-data/` instead.

The patch at `patches/polygen-v1.0.0-reproducibility.patch` is applied inside the
bundled tree. It contains execution fixes only and no publication results. The
verification script checks required source/checkpoint paths, patch markers,
excluded artifact classes, and every bundled-file hash.

`results/dev/minGPT-checkpoint-finetune-smoke-seed907/` is a fresh DEV execution
made with this package's bundled source and runner. It loads the bundled public
checkpoint, applies 10 optimizer steps, generates new samples, and evaluates them.
The DEV summary hashes the runner, starting checkpoint, dataset, losses, generated
samples, and final checkpoint. The local verification pass recomputes every hash
whose artifact is archived in this package; scientific values are not maintained
in this document.
