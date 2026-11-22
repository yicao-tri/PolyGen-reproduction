#!/usr/bin/env bash
set -euo pipefail

# Extended convergence run for the exact 4,819-row C1 MolMiner support.
# This is an auditable extended run, not an automatic publication claim:
# checkpoint selection still needs an owner-approved final protocol and a
# task-aligned WeeMiner/equivalent arm.

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
CANONICAL_VENV="${CANONICAL_VENV:-/Users/yicao/Documents/ARC/PolyGen-reproduction/.venv/bin/python}"
MOLMINER_ROOT="${MOLMINER_ROOT:-/Users/yicao/Documents/ARC/resourses/molminer-polymer}"
EPOCHS="${EPOCHS:-20}"
SEEDS="${SEEDS:-17 23 31 47 59}"

BASE="$PACKAGE_ROOT/evidence/experiments/molminer_strict_c1"
OUT_ROOT="$BASE/extended_${EPOCHS}epoch"
COMPAT="$PACKAGE_ROOT/evidence/scripts/torch_compat"
mkdir -p "$OUT_ROOT"

for seed in $SEEDS; do
  out="$OUT_ROOT/seed${seed}"
  mkdir -p "$out"
  PYTHONUNBUFFERED=1 \
  PYTHONPATH="$COMPAT:$MOLMINER_ROOT" \
  "$CANONICAL_VENV" \
  "$MOLMINER_ROOT/scripts/train_molminer.py" \
    --data_dir "$BASE" \
    --packed_dir "$BASE/packed" \
    --ckpt_dir "$out/checkpoints" \
    --exp_name "c1_extended${EPOCHS}_seed${seed}" \
    --device cpu \
    --d_model 128 --d_anchor 8 --n_heads 8 --num_layers 2 --d_ff 256 \
    --d_fragment 128 --d_env 64 --factored_head \
    --dropout 0.3 --prompt_dropout 0.1 --condition_dropout 0.1 \
    --batch_size 512 --total_epochs "$EPOCHS" --lr_horizon_epochs "$EPOCHS" \
    --peak_lr 1e-4 --min_lr 1e-6 --weight_decay 1e-2 \
    --fixedrollout --bucket_by_length --seed "$seed" \
    2>&1 | tee "$out/train.stdout.log"
done
