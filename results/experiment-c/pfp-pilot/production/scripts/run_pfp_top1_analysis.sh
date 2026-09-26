#!/usr/bin/env bash
set -euo pipefail

root="${1:-$HOME/mms-jobs/polygen-pfp-top1-production-v1}"
preflight="${2:-$HOME/mms-jobs/polygen-pfp-top1-relax-preflight-v1/results}"
analysis="$root/analysis"
scripts="$root/scripts"
contract="$root/config/top1_pilot_contract.json"

continuous_run="$root/continuous/results/continuous_top1_relaxed"
binary_run="$root/binary/results/binary_top1_relaxed"

for required in \
  "$continuous_run/run_summary.json" \
  "$continuous_run/production.traj" \
  "$binary_run/run_summary.json" \
  "$binary_run/production.traj" \
  "$preflight/batch_summary.json" \
  "$contract"; do
  if [[ ! -s "$required" ]]; then
    echo "Required completed artifact is missing or empty: $required" >&2
    exit 2
  fi
done

mkdir -p "$analysis/continuous" "$analysis/binary" "$analysis/paired"

python "$scripts/analyze_pfp_htpmd.py" \
  --trajectory "$continuous_run/production.traj" \
  --output-dir "$analysis/continuous" \
  --ion-pairs 10 \
  --frame-dt-ps 0.1 \
  --discard-ps 40 \
  --temperature 353 \
  --cluster-cutoff-a 3.4 \
  --proxy-log10 -3.7789737147968334 \
  --label continuous_top1

python "$scripts/analyze_pfp_htpmd.py" \
  --trajectory "$binary_run/production.traj" \
  --output-dir "$analysis/binary" \
  --ion-pairs 10 \
  --frame-dt-ps 0.1 \
  --discard-ps 40 \
  --temperature 353 \
  --cluster-cutoff-a 3.4 \
  --proxy-log10 -3.8305837721099456 \
  --label binary_top1

python "$scripts/summarize_pfp_top1_pair.py" \
  --continuous-analysis "$analysis/continuous/analysis.json" \
  --continuous-run "$continuous_run/run_summary.json" \
  --continuous-log "$continuous_run/production.log" \
  --binary-analysis "$analysis/binary/analysis.json" \
  --binary-run "$binary_run/run_summary.json" \
  --binary-log "$binary_run/production.log" \
  --output-dir "$analysis/paired" \
  --expected-frames 2001

python "$scripts/validate_pfp_top1_evidence.py" \
  --contract "$contract" \
  --preflight-root "$preflight" \
  --production-root "$root" \
  --analysis-root "$analysis" \
  --output "$analysis/validation.json"

python "$scripts/render_pfp_top1_report.py" \
  --contract "$contract" \
  --paired "$analysis/paired/paired_summary.json" \
  --continuous-analysis "$analysis/continuous/analysis.json" \
  --binary-analysis "$analysis/binary/analysis.json" \
  --validation "$analysis/validation.json" \
  --output "$analysis/PFP_TOP1_PILOT_REPORT_ZH.md"

echo "PFP top-1 analysis and evidence validation completed: $analysis"
