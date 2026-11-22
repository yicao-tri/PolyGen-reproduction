# WeeRollMiner

![WeeRollMiner — Generate with foresight](docs/images/weeminer-v2-hero.png)

Fragment-based molecular generation with a MolMiner-style baseline, WEECFP-SuRGE
variants, and WeeMiner's learned fragment-selection strategies.

Start with [the technical writeup](WEEMINER.md) and [the original variant guide](molminer_repro/README.md).
The code and sample data are included; full datasets and trained models are
shared separately.

## ZN dataset results

These results are for the **ZN dataset**, reported
in **WeeMiner presentation v2, slides 9–12**. The shared training pipeline uses
156,646 molecules and 20 joint-training epochs, followed by progress-head
fine-tuning. The [reduced local baseline](docs/baseline.md) documents the separate
2,000-molecule run in this checkout.

**Rollout reaches 0.886 logP MAE—a 50.7% reduction from the WeeMiner N=1 baseline.**
Fast reaches **0.935 MAE** with best-of-8 reranking. Both use the same trained
model and four-head progress ensemble.

| Metric | MolMiner (literature) | WeeMiner baseline (N=1) | WeeMiner Fast | WeeMiner Rollout |
|---|---:|---:|---:|---:|
| logP MAE ↓ | 1.000 | 1.797 | 0.935 | **0.886** |
| logP R², grouped ↑ | 0.890 | 0.848 | **0.987** | 0.981 |
| Validity ↑ | 1.000 | 1.000 | 1.000 | 1.000 |
| Uniqueness ↑ | 0.985 | 1.000 | 1.000 | 1.000 |
| Novelty ↑ | 0.999 | 1.000 | 1.000 | 1.000 |
| Diversity ↑ | **0.892** | 0.844 | 0.846 | 0.842 |

**Generation time:** Fast takes **0.316 s/molecule**; Rollout takes
**2.617 s/molecule** in the conditioned benchmark. Rollout spends about 8.3×
the generation time for a further 5.2% reduction in MAE.
The shared training pipeline takes **≈43 minutes (2,601 s)**, about **17× shorter**
than the **extrapolated** ≈12-hour local MolMiner-style pipeline, estimated from
a 200-molecule timing sample.

Quality metrics use **250 unconditional samples**; logP calibration uses
**160 samples across eight targets**. R² is computed on target-wise mean
outcomes; MAE uses individual samples. Validity is measured after assembly and
largest-component retention. These are single-run results, and the literature comparison
uses different evaluation and inference budgets. See [the technical writeup,
§§6 and 8](WEEMINER.md) for the protocol and comparison details.

## How it works

WeeMiner's rollout strategy proposes candidate fragments, samples possible
continuations, and scores them with a four-head progress ensemble to choose the
next fragment. After the fragment sequence is complete, it decodes bonds globally.
The diagram illustrates the top-four, three-rollout configuration from the v2 deck.

![Four candidate fragments branch into three simulated futures each; the progress ensemble helps select one fragment.](docs/images/weeminer-v2-rollout.png)

<details>
<summary>How connectivity differs from MolMiner</summary>

![MolMiner forms bonds incrementally; WeeMiner predicts fragment positions before a global bond decode.](docs/images/weeminer-v2-connectivity.png)

</details>

[Artwork and editable sources](docs/images/README.md) adapted from WeeMiner presentation v2.

## Setup

The verified environment is Python 3.12 on Linux, using CPU PyTorch. From a fresh
checkout with network access:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps --no-build-isolation -e .
```

With uv, the equivalent installation is:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt --index-strategy unsafe-best-match
uv pip install --python .venv/bin/python --no-deps --no-build-isolation -e .
source .venv/bin/activate
```

`requirements.txt` pins the tested CPU environment. A GPU installation needs
PyTorch built for the machine's CUDA setup; the full trainer selects CUDA when
available. Generation and self-generated progress-head training currently run
on CPU. Dependency versions from the historical experiment were not recorded.

## First run: no external data required

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -m unittest discover -s tests -v
python -m molminer_repro.train --variant baseline --epochs 60 \
  --out results/demo/baseline.pt
python -m molminer_repro.generate --checkpoint results/demo/baseline.pt \
  --n 10 --properties 'logP=2.5,QED=0.8'
```

The tests train tiny models, reload their checkpoints, and generate molecules.
They cover the sequential, parallel, and WeeMiner paths without requiring the
full dataset. GitHub Actions runs the same CPU checks. Passing a smoke test is
not a claim about molecular quality or property accuracy.

## Reduced and full experiments

Restore the ZINC files as described in [the data guide](molminer_repro/data/README.md),
then run `python scripts/check_data.py` to check their hashes.

```bash
# All three demo models, plus WeeMiner trained on 2,000 ZINC rows.
bash scripts/reproduce_baseline.sh results/new_baseline

# Full documented training budgets, starting from scratch.
bash scripts/reproduce_full.sh results/full
```

The full script trains on all 156,646 training molecules for 20 epochs, fits
one progress head with 12,000 generated attempts, fits three additional heads
with 6,000 attempts each, and benchmarks all five strategies. The main
architecture is 256 dimensions, three layers, 512 feed-forward dimensions,
and ref3 rotary positions. Phase C allows 15 epochs and selects its best
validation epoch. Some historical training details were not recorded; this is
a reproducible fresh retrain using the documented architecture and budgets,
not a guarantee of the same historical numbers. The full script is provided
for the team; it has not been run to completion during this preparation.

Run scripts create checkpoints, matching `.completer.pkl` files, and logs in
the chosen output directory. The reduced evaluation also saves JSON metrics
and every attempted SMILES. Use a fresh directory for each experiment. Old
RDKit binary caches are excluded and rebuilt from CSV to avoid version errors.

To evaluate restored historical models directly:

```bash
python -m molminer_repro.benchmark_full_comparison \
  --checkpoint artifacts/seqassemble_full_v9_selfgen.pt \
  --ensemble-checkpoints artifacts/seqassemble_full_ens_seed1.pt \
    artifacts/seqassemble_full_ens_seed2.pt artifacts/seqassemble_full_ens_seed3.pt \
  --n-unconditional 250 --n-per-target 20 --n-novelty-ref 20000 --seed 0
```

Each checkpoint needs its companion `.completer.pkl` beside it. The comparison
now seeds PyTorch along with the existing Python/NumPy RNGs. Exact values from
the old unseeded logs may differ. No trained models are included in Git.

## Project resources

- [Contribution and experiment conventions](CONTRIBUTING.md)
- [Metadata inventory and what stays out of Git](docs/metadata.md)
- [GitHub workflow and source export](docs/github_setup.md)
- [Presentation](weeminer_presentation/README.md)

No code license or author list is currently declared. The original research
references and methodological caveats are preserved.
