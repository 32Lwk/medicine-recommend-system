#!/usr/bin/env bash
# Cloud Agent / Cursor Cloud 向け PMDA 成分 fetch 起動
#
# Usage:
#   ./scripts/pmda/start_cloud_ingredient_fetch.sh --prepare-queue
#   ./scripts/pmda/start_cloud_ingredient_fetch.sh --max-hours 48
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

exec "$PY" "$ROOT/scripts/pmda/run_live_fetch_ingredient_cloud.py" "$@"
