#!/usr/bin/env bash
# Concierge 技術 FAQ contract テスト（Support 不要・ローカル/CI 用）
#
# Usage:
#   ./scripts/concierge-technical-faq-contract.sh
#   RUN_CONCIERGE_FAQ_CONTRACT=1 ./scripts/aws-staging-smoke.sh  # contract テストも実行
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

need_cmd python

export PYTHONUTF8=1
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python
fi

echo "==> Concierge technical FAQ contract tests"
"$PY" -m pytest \
  tests/concierge/test_technical_faq_contract.py \
  tests/concierge/test_concierge_rag_integration.py \
  tests/content/test_concierge_tech_reference.py \
  tests/content/test_concierge_runtime_reference.py \
  tests/services/test_concierge_output_sanitize.py \
  tests/services/test_concierge_channel.py \
  tests/scripts/test_verify_concierge_ssot.py \
  -q --tb=line

echo "==> Concierge Meta KB L1 eval scripts"
"$PY" scripts/eval_concierge_intent_routing.py --min-pass-pct 92
"$PY" scripts/eval_concierge_technical_quality.py --min-pass-pct 90
"$PY" scripts/eval_concierge_boundary.py --min-pass-pct 100
"$PY" scripts/eval_concierge_line_smoke.py --min-pass-pct 100

echo "==> Concierge technical FAQ contract passed"
