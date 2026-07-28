#!/usr/bin/env bash
# Concierge Meta KB 総合 eval（L1 retrieve + contract + 任意 live）
#
# Usage:
#   ./scripts/run_concierge_comprehensive_eval.sh
#   RUN_LIVE_QUALITY=1 ./scripts/run_concierge_comprehensive_eval.sh
#   RUN_LIVE_JUDGE=1 RUN_LIVE_QUALITY=1 ./scripts/run_concierge_comprehensive_eval.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_DIR="${ROOT}/log/analysis"
mkdir -p "$REPORT_DIR"

echo "==> [1/4] Concierge technical FAQ contract (pytest + L1 eval)"
bash "${ROOT}/scripts/concierge-technical-faq-contract.sh"

echo "==> [2/4] Concierge local RAG retrieve (all fixtures, min 90%)"
"$PY" "${ROOT}/scripts/eval_concierge_kb.py" \
  --provider local \
  --all-fixtures \
  --min-pass-pct 90 \
  --output "${REPORT_DIR}/concierge_kb_comprehensive_${STAMP}.json"

echo "==> [3/4] Retrieve latency benchmark (advisory P95 target 800ms)"
"$PY" "${ROOT}/scripts/local_rag_retrieve_benchmark.py" \
  --output "${REPORT_DIR}/concierge_benchmark_comprehensive_${STAMP}.json" \
  || echo "    benchmark: advisory warning (see report)"

echo "==> [4/4] Unit tests (concierge rag context + technical)"
"$PY" -m pytest \
  "${ROOT}/tests/services/test_concierge_rag_context.py" \
  "${ROOT}/tests/concierge/test_technical_faq_contract.py" \
  -q

if [[ "${RUN_LIVE_QUALITY:-0}" == "1" ]]; then
  echo "==> [L3a] Live LLM quality — rule tier (technical + casual)"
  LIVE_TIER="${LIVE_TIER:-rule}"
  "$PY" "${ROOT}/scripts/eval_concierge_technical_quality_live.py" \
    --tier "$LIVE_TIER" \
    --min-pass-pct "${LIVE_MIN_PASS_PCT:-85}" \
    --output "${REPORT_DIR}/concierge_technical_quality_live_${STAMP}.json" \
    || LIVE_TECH=$?
  "$PY" "${ROOT}/scripts/eval_concierge_technical_quality_live.py" \
    --fixture "${ROOT}/tests/fixtures/concierge_live_casual.yaml" \
    --tier "$LIVE_TIER" \
    --min-pass-pct "${LIVE_CASUAL_MIN_PASS_PCT:-80}" \
    --output "${REPORT_DIR}/concierge_live_casual_${STAMP}.json" \
    || LIVE_CASUAL=$?

  if [[ "${RUN_LIVE_JUDGE:-0}" == "1" ]]; then
    echo "==> [L3b] Live judge-failures rescue tier"
    "$PY" "${ROOT}/scripts/eval_concierge_technical_quality_live.py" \
      --tier judge-failures \
      --min-pass-pct "${LIVE_MIN_PASS_PCT:-85}" \
      --output "${REPORT_DIR}/concierge_technical_quality_live_judge_failures_${STAMP}.json" \
      || true
    "$PY" "${ROOT}/scripts/eval_concierge_technical_quality_live.py" \
      --fixture "${ROOT}/tests/fixtures/concierge_live_casual.yaml" \
      --tier judge-failures \
      --min-pass-pct "${LIVE_CASUAL_MIN_PASS_PCT:-80}" \
      --output "${REPORT_DIR}/concierge_live_casual_judge_failures_${STAMP}.json" \
      || true
    echo "==> [L3c] Live judge-pass strict tier"
    "$PY" "${ROOT}/scripts/eval_concierge_technical_quality_live.py" \
      --tier judge-pass \
      --min-pass-pct "${LIVE_MIN_PASS_PCT:-85}" \
      --output "${REPORT_DIR}/concierge_technical_quality_live_judge_pass_${STAMP}.json" \
      || true
  fi

  if [[ "${RUN_DIALOGUE_E2E:-1}" == "1" ]]; then
    echo "==> [L3d] Multi-turn dialogue E2E (scripted + GPT user)"
    DIALOGUE_JUDGE=()
    if [[ "${RUN_LIVE_JUDGE:-0}" == "1" ]]; then
      DIALOGUE_JUDGE=(--judge)
    fi
    "$PY" "${ROOT}/scripts/eval_concierge_dialogue_e2e.py" \
      ${DIALOGUE_JUDGE[@]+"${DIALOGUE_JUDGE[@]}"} \
      --min-pass-pct "${DIALOGUE_MIN_PASS_PCT:-80}" \
      --output "${REPORT_DIR}/concierge_dialogue_e2e_${STAMP}.json" \
      || DIALOGUE=$?
  fi
else
  echo "==> [L3] Live quality skipped (set RUN_LIVE_QUALITY=1 to enable)"
fi

echo "==> Concierge comprehensive eval passed"
