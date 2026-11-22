#!/usr/bin/env bash
set -euo pipefail

root="$HOME/mms-jobs/polygen-pfp-top1-production-v1"
tmux kill-session -t polygen_top1_analysis 2>/dev/null || true
tmux new-session -d -s polygen_top1_analysis \
  "bash -ic 'use_venv python311 && bash $root/scripts/watch_pfp_top1_and_analyze.sh $root > $root/analysis_watcher.log 2>&1'"
tmux list-sessions | grep '^polygen_top1_analysis:'
