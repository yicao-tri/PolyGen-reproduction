#!/usr/bin/env python3
"""Run a configurable diffusion1D training job from the PolyGen release."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path


BUNDLED_REPO = Path(__file__).resolve().parents[1] / "vendor" / "PolyGen-1.0.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=BUNDLED_REPO,
        help="PolyGen checkout; defaults to the patched v1.0.0 source bundled in this package",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--task", choices=("conditional", "unconditional"), required=True)
    parser.add_argument("--block-size", type=int)
    parser.add_argument("--model-dim", type=int)
    parser.add_argument("--model-dim-mults", type=int, nargs="+")
    parser.add_argument("--diffusion-steps", type=int)
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

    import denoising_diffusion_pytorch.denoising_diffusion_pytorch_1d_custom as d1_module
    from diffusion1D.pipeline import diffusion1D

    # The vendored trainer otherwise starts one worker per visible CPU.
    d1_module.cpu_count = lambda: args.workers

    pipeline = diffusion1D()
    data_config = pipeline.get_default_data_config()
    data_config.task = args.task
    data_config.file_path = str(repo / "diffusion1D" / "htp_md.csv")
    if args.block_size is not None:
        data_config.block_size = args.block_size
    _, _, vocab_size = pipeline.data_preprocessing(data_config)

    model_config = pipeline.get_default_model_config()
    if args.model_dim is not None:
        model_config.dim = args.model_dim
    if args.model_dim_mults is not None:
        model_config.dim_mults = tuple(args.model_dim_mults)
    if args.diffusion_steps is not None:
        model_config.diffusion_step = args.diffusion_steps
    model_config.vocab_size = vocab_size
    model_config.block_size = data_config.block_size
    pipeline.load_model(model_config)

    train_config = pipeline.get_default_train_config()
    train_config.num_steps = args.steps
    train_config.batch_size = args.batch_size
    train_config.ckpts_path = str(output)
    started = time.time()
    pipeline.train(train_config)
    elapsed = time.time() - started
    pipeline.trainer.save("final")

    loss = torch.load(output / "loss.pt", map_location="cpu")
    train_loss = loss[:, 0] if loss.ndim == 2 else loss
    val_loss = loss[:, 1] if loss.ndim == 2 and loss.shape[1] > 1 else None
    summary = {
        "steps": args.steps,
        "batch_size": args.batch_size,
        "workers": args.workers,
        "seed": args.seed,
        "task": args.task,
        "elapsed_seconds": elapsed,
        "recorded_loss_rows": int(len(loss)),
        "train_loss_first_recorded": float(train_loss[0]),
        "train_loss_last_recorded": float(train_loss[-1]),
        "train_loss_min_recorded": float(train_loss.min()),
        "validation_loss_first_recorded": float(val_loss[0]) if val_loss is not None else None,
        "validation_loss_last_recorded": float(val_loss[-1]) if val_loss is not None else None,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model": {
            "dim": model_config.dim,
            "dim_mults": list(model_config.dim_mults),
            "diffusion_steps": model_config.diffusion_step,
            "vocab_size": vocab_size,
            "block_size": model_config.block_size,
        },
    }
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
