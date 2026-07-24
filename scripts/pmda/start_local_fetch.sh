#!/usr/bin/env bash
# PMDA 成分 live 連続 fetch 起動（cwd / pyc クリア / SIGHUP 耐性）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
find scripts/pmda -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
LOG_DIR="$ROOT/log/analysis"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/pmda_local_stdout.log" 2>>"$LOG_DIR/pmda_local_stderr.log"
exec .venv/bin/python -u scripts/pmda/run_live_fetch_local.py "$@"
