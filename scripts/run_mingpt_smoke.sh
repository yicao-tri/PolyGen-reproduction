#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 OUTPUT_DIRECTORY SEED" >&2
  exit 2
fi

python "$(dirname "$0")/run_mingpt_training.py" \
  --output "$1" \
  --seed "$2" \
  --task conditional \
  --max-iters 10 \
  --batch-size 8 \
  --num-workers 0 \
  --model-type gpt-nano \
  --block-size 64 \
  --label-length 5 \
  --learning-rate 0.00005 \
  --beta1 0.9 \
  --beta2 0.95 \
  --weight-decay 0.1 \
  --grad-norm-clip 1.0 \
  --num-samples 100 \
  --temperature 1.0 \
  --pretrain minGPT/ckpts/10000.pt
