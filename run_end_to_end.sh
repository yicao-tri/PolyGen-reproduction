#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

cd "$(dirname "$0")"

python3 scripts/summarize_actual_runs.py
python3 scripts/reproduce_actual_data.py
python3 scripts/generate_coverage_report.py
python3 scripts/build_artifact_manifest.py
python3 scripts/verify_package.py
