#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
.venv/bin/python scripts/run_experiment_c1.py | tee results/experiment-c/c1_run.log
.venv/bin/python scripts/evaluate_experiment_c1b.py | tee results/experiment-c/c1b_run.log
.venv/bin/python scripts/run_experiment_c2.py | tee results/experiment-c/c2_run.log
.venv/bin/python scripts/audit_pedatamine.py
.venv/bin/python scripts/build_hierarchical_demo.py
ATLAS_PY="${PLOT_ATLAS_PYTHON:-/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library/.venv/bin/python}"
"$ATLAS_PY" scripts/plot_experiment_c.py
.venv/bin/python scripts/verify_experiment_c.py
