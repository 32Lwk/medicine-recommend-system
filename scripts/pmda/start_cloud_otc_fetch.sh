#!/usr/bin/env bash
set -euo pipefail
cd /workspace
mkdir -p log/analysis
exec .venv/bin/python scripts/pmda/run_live_fetch_otc_cloud.py \
  --min-interval 1 \
  --merge-every 100 \
  --resume \
  --max-hours 20 \
  2>&1 | tee -a log/analysis/pmda_cloud_otc_run_20260725.log
