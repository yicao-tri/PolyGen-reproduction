#!/usr/bin/env bash
set -euo pipefail

root="${1:-$HOME/mms-jobs/polygen-pfp-top1-production-v1}"
continuous="$root/continuous/results/batch_summary.json"
binary="$root/binary/results/batch_summary.json"
status="$root/analysis_watcher_status.json"

write_status() {
  local state=$1
  local detail=$2
  printf '{"schema_version":"polygen.pfp-analysis-watcher.v1","status":"%s","detail":"%s","updated_utc":"%s"}\n' \
    "$state" "$detail" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$status.tmp"
  mv "$status.tmp" "$status"
}

write_status waiting "waiting for both production batch summaries"
while [[ ! -s "$continuous" || ! -s "$binary" ]]; do
  sleep 60
  write_status waiting "waiting for both production batch summaries"
done

# Atomic directory creation prevents the watcher and a manual invocation from
# running the expensive trajectory analysis twice.
if ! mkdir "$root/.analysis.lock" 2>/dev/null; then
  write_status skipped "analysis lock already exists"
  exit 0
fi
trap 'rmdir "$root/.analysis.lock" 2>/dev/null || true' EXIT

write_status running "both production summaries found; running frozen analysis"
if bash "$root/scripts/run_pfp_top1_analysis.sh" "$root"; then
  write_status succeeded "analysis and evidence validation completed"
else
  code=$?
  write_status failed "analysis pipeline exited with code $code"
  exit "$code"
fi
