#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
local_root="$repo_root/results/experiment-c/pfp-pilot/production"
kozo_stage="/tmp/polygen-pfp-top1-production-v1"
matlantis_root="mms-jobs/polygen-pfp-top1-production-v1"

# Refuse to collect an incomplete run.  This prevents a partial trajectory from
# replacing a complete evidence package if the command is invoked too early.
ssh kozo-dev-yi \
  "ssh matlantis 'test -s ~/$matlantis_root/continuous/results/batch_summary.json && test -s ~/$matlantis_root/binary/results/batch_summary.json && test -s ~/$matlantis_root/analysis/validation.json'"

# Generate the authoritative remote hash manifest only after analysis passes.
ssh kozo-dev-yi \
  "ssh matlantis 'cd ~/$matlantis_root && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS && sha256sum -c SHA256SUMS'"

# Use kozo-dev-yi as the explicit transfer hop because Matlantis is only
# addressable from that host.  Both staging targets are narrow and fixed.
ssh kozo-dev-yi "rm -rf '$kozo_stage' && scp -r 'matlantis:$matlantis_root' '$kozo_stage'"
mkdir -p "$local_root"
rsync -a --delete "kozo-dev-yi:$kozo_stage/" "$local_root/"

(cd "$local_root" && sha256sum -c SHA256SUMS)
echo "Collected and verified PFP top-1 evidence: $local_root"
