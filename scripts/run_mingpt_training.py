#!/usr/bin/env python3
"""Train, generate, and score minGPT with all experiment choices supplied by CLI."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
import traceback
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
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", choices=("conditional", "unconditional"), required=True)
    parser.add_argument("--max-iters", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--num-workers", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--model-type", required=True)
    parser.add_argument("--block-size", type=int, required=True)
    parser.add_argument("--label-length", type=int, required=True)
    parser.add_argument("--learning-rate", type=float, required=True)
    parser.add_argument("--beta1", type=float, required=True)
    parser.add_argument("--beta2", type=float, required=True)
    parser.add_argument("--weight-decay", type=float, required=True)
    parser.add_argument("--grad-norm-clip", type=float, required=True)
    parser.add_argument("--num-samples", type=int, required=True)
    parser.add_argument("--temperature", type=float, required=True)
    parser.add_argument(
        "--pretrain",
        type=Path,
        help="Optional starting checkpoint; a relative path is resolved inside --repo",
    )
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict], fieldnames: tuple[str, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    args = parse_args()
    for name in ("max_iters", "batch_size", "num_samples", "block_size", "label_length"):
        if getattr(args, name) <= 0:
            raise ValueError(f"--{name.replace('_', '-')} must be positive")
    import numpy as np  # pylint: disable=import-outside-toplevel
    import torch  # pylint: disable=import-outside-toplevel

    repo = args.repo.resolve()
    output = args.output.resolve()
    checkpoint_dir = output / "checkpoints"
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
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
    data_config.task = args.task
    data_config.block_size = args.block_size
    data_config.length = args.label_length
    train_dataset, test_dataset = pipeline.data_preprocessing(data_config)

    model_config = pipeline.get_default_model_config()
    model_config.model_type = args.model_type
    model_config.vocab_size = train_dataset.get_vocab_size()
    model_config.block_size = train_dataset.get_block_size()
    pipeline.load_model(model_config)

    train_config = pipeline.get_default_train_config()
    train_config.max_iters = args.max_iters
    train_config.batch_size = args.batch_size
    train_config.num_workers = args.num_workers
    train_config.learning_rate = args.learning_rate
    train_config.betas = (args.beta1, args.beta2)
    train_config.weight_decay = args.weight_decay
    train_config.grad_norm_clip = args.grad_norm_clip
    train_config.ckpt_path = str(checkpoint_dir) + os.sep
    train_config.call_back = lambda _trainer: None
    pretrain_path = None
    if args.pretrain is not None:
        pretrain_path = args.pretrain if args.pretrain.is_absolute() else repo / args.pretrain
        pretrain_path = pretrain_path.resolve()
        if not pretrain_path.is_file():
            raise FileNotFoundError(f"starting checkpoint not found: {pretrain_path}")
        train_config.pretrain = str(pretrain_path)

    training_started = time.time()
    train_loss, validation_loss = pipeline.train(train_config)
    training_seconds = time.time() - training_started
    final_checkpoint = checkpoint_dir / "final.pt"
    torch.save(pipeline.model.state_dict(), final_checkpoint)

    loss_rows = [
        {
            "iteration": index + 1,
            "train_loss": train_value,
            "validation_loss": validation_value,
        }
        for index, (train_value, validation_value) in enumerate(zip(train_loss, validation_loss))
    ]
    write_csv(
        output / "loss_history.csv",
        loss_rows,
        ("iteration", "train_loss", "validation_loss"),
    )

    generate_config = pipeline.get_default_generate_config()
    generate_config.ckpt_path = str(final_checkpoint)
    generate_config.task = args.task
    generate_config.num_samples = args.num_samples
    generate_config.temperature = args.temperature
    generation_started = time.time()
    samples = pipeline.generate(generate_config)
    generation_seconds = time.time() - generation_started
    write_csv(
        output / "samples.csv",
        [
            {
                "sample_index": index,
                "mol_smiles": sample,
            }
            for index, sample in enumerate(samples, 1)
        ],
        ("sample_index", "mol_smiles"),
    )

    metrics = {name: None for name in METRIC_NAMES}
    evaluation_error = None
    evaluation_notes = []
    try:
        metric_values = pipeline.evaluate()
        for name, value in zip(METRIC_NAMES, metric_values):
            numeric = float(value)
            if math.isfinite(numeric):
                metrics[name] = numeric
            else:
                evaluation_notes.append(f"{name} was non-finite and is stored as null")
    except Exception as exc:  # preserve a genuine smoke run even if no molecules survive filtering
        evaluation_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        (output / "evaluation_error.json").write_text(
            json.dumps(evaluation_error, indent=2) + "\n", encoding="utf-8"
        )
        evaluation_notes.append(
            "Release evaluation could not produce all metrics; the exact exception is preserved in evaluation_error.json."
        )

    sample_path = output / "samples.csv"
    loss_path = output / "loss_history.csv"
    nonempty_samples = sum(bool(str(sample).strip()) for sample in samples)
    record = {
        "data_policy": "All numeric values were emitted by this real training/generation invocation; no article value was loaded.",
        "repo": str(repo),
        "task": args.task,
        "seed": args.seed,
        "training": {
            "initialization": "checkpoint" if pretrain_path is not None else "random",
            "starting_checkpoint": str(pretrain_path) if pretrain_path is not None else None,
            "starting_checkpoint_sha256": digest(pretrain_path) if pretrain_path is not None else None,
            "max_iters": args.max_iters,
            "batch_size": args.batch_size,
            "num_workers": args.num_workers,
            "learning_rate": args.learning_rate,
            "betas": [args.beta1, args.beta2],
            "weight_decay": args.weight_decay,
            "grad_norm_clip": args.grad_norm_clip,
            "elapsed_seconds": training_seconds,
            "train_rows": len(train_dataset),
            "validation_rows": len(test_dataset),
            "loss_rows": len(loss_rows),
            "first_train_loss": train_loss[0],
            "last_train_loss": train_loss[-1],
            "minimum_train_loss": min(train_loss),
            "first_validation_loss": validation_loss[0],
            "last_validation_loss": validation_loss[-1],
            "minimum_validation_loss": min(validation_loss),
        },
        "model": {
            "model_type": args.model_type,
            "block_size": args.block_size,
            "label_length": args.label_length,
            "vocab_size": model_config.vocab_size,
        },
        "generation": {
            "num_samples": args.num_samples,
            "nonempty_samples": nonempty_samples,
            "unique_nonempty_samples": len({str(sample).strip() for sample in samples if str(sample).strip()}),
            "temperature": args.temperature,
            "elapsed_seconds": generation_seconds,
        },
        "metrics": metrics,
        "evaluation": {
            "completed_without_exception": evaluation_error is None,
            "notes": evaluation_notes,
            "error_file": "evaluation_error.json" if evaluation_error is not None else None,
        },
        "checkpoint": str(final_checkpoint),
        "artifacts": {
            "runner_sha256": digest(Path(__file__).resolve()),
            "dataset_sha256": digest(repo / "minGPT" / "htp_md.csv"),
            "checkpoint_sha256": digest(final_checkpoint),
            "loss_history_sha256": digest(loss_path),
            "samples_sha256": digest(sample_path),
        },
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    (output / "run_summary.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
