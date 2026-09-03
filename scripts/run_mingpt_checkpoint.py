#!/usr/bin/env python3
"""Generate and score polymers from a released PolyGen minGPT checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path


BUNDLED_REPO = Path(__file__).resolve().parents[1] / "vendor" / "PolyGen-1.0.0"
METRIC_NAMES = (
    "uniqueness",
    "novelty",
    "validity",
    "synthesizability",
    "similarity",
    "diversity",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=BUNDLED_REPO,
        help="PolyGen checkout; defaults to the patched v1.0.0 source bundled in this package",
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--task", choices=("conditional", "unconditional"), required=True)
    parser.add_argument("--num-samples", type=int, required=True)
    parser.add_argument("--temperature", type=float, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--block-size", type=int)
    parser.add_argument("--model-type", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import numpy as np  # pylint: disable=import-outside-toplevel
    import torch  # pylint: disable=import-outside-toplevel

    repo = args.repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(repo)
    sys.path.insert(0, str(repo))

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    from minGPT.pipeline import minGPT  # pylint: disable=import-outside-toplevel

    pipeline = minGPT()
    data_config = pipeline.get_default_data_config()
    data_config.file_path = str(repo / "minGPT" / "htp_md.csv")
    if args.block_size is not None:
        data_config.block_size = args.block_size
    data_config.task = args.task
    train_dataset, _ = pipeline.data_preprocessing(data_config)

    model_config = pipeline.get_default_model_config()
    model_config.model_type = args.model_type
    model_config.vocab_size = train_dataset.get_vocab_size()
    model_config.block_size = train_dataset.get_block_size()
    pipeline.load_model(model_config)

    generate_config = pipeline.get_default_generate_config()
    generate_config.ckpt_path = str((repo / args.checkpoint).resolve())
    generate_config.task = args.task
    generate_config.num_samples = args.num_samples
    generate_config.temperature = args.temperature
    samples = pipeline.generate(generate_config)
    metric_values = pipeline.evaluate()
    metrics = dict(zip(METRIC_NAMES, (float(value) for value in metric_values)))

    with (output / "samples.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sample_index", "mol_smiles"])
        writer.writerows(enumerate(samples, 1))

    result = {
        "repo": str(repo),
        "checkpoint": generate_config.ckpt_path,
        "task": args.task,
        "num_samples": args.num_samples,
        "temperature": args.temperature,
        "seed": args.seed,
        "block_size": data_config.block_size,
        "model_type": args.model_type,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "metrics": metrics,
    }
    (output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
