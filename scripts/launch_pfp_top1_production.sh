#!/usr/bin/env bash
set -euo pipefail

root="$HOME/mms-jobs/polygen-pfp-top1-production-v1"
preflight="$HOME/mms-jobs/polygen-pfp-top1-relax-preflight-v1"
mkdir -p "$root/continuous" "$root/binary"
cp "$preflight/run_pfp_paired_pilot_v2.py" "$root/continuous/runner.py"
cp "$preflight/run_pfp_paired_pilot_v2.py" "$root/binary/runner.py"
cp "$preflight/results/polygen_continuous_top1/relaxed.extxyz" \
  "$root/continuous/continuous_top1_relaxed.extxyz"
cp "$preflight/results/binary_top1_3chains_10litfsi/relaxed.extxyz" \
  "$root/binary/binary_top1_relaxed.extxyz"

common_args="--temperature 353 --timestep-fs 1 --steps 200000 --trajectory-interval 100 --friction-per-fs 0.01 --seed 20260924 --relax-steps 0"

tmux kill-session -t polygen_cont_top1 2>/dev/null || true
tmux kill-session -t polygen_bin_top1 2>/dev/null || true
tmux new-session -d -s polygen_cont_top1 \
  "bash -ic 'cd $root/continuous && use_venv python311 && python runner.py --structures continuous_top1_relaxed.extxyz --output-dir results $common_args > execution.log 2>&1'"
tmux new-session -d -s polygen_bin_top1 \
  "bash -ic 'cd $root/binary && use_venv python311 && python runner.py --structures binary_top1_relaxed.extxyz --output-dir results $common_args > execution.log 2>&1'"
tmux list-sessions | grep 'polygen_.*_top1'
