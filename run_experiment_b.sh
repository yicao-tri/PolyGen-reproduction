#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

.venv/bin/python -m unittest tests/test_complete_system_e2e.py -v
.venv/bin/python scripts/run_complete_system_e2e.py | tee results/experiment-b/run.log

ATLAS_PY="${PLOT_ATLAS_PYTHON:-/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library/.venv/bin/python}"
if [[ -x "$ATLAS_PY" ]]; then
  "$ATLAS_PY" scripts/plot_experiment_b.py
else
  echo "Plot Atlas Python not found; tables are complete but figure rendering was skipped." >&2
fi
