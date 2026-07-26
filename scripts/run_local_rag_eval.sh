#!/usr/bin/env bash
# Local RAG retrieve eval ゲート（CI / CodeBuild / 手動）
#
# Usage:
#   ./scripts/run_local_rag_eval.sh
#   LOCAL_RAG_MIN_MEDICINE_PCT=80 LOCAL_RAG_MIN_CONCIERGE_PCT=90 ./scripts/run_local_rag_eval.sh
#   RUN_LOCAL_RAG_BENCHMARK=1 ./scripts/run_local_rag_eval.sh
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

MED_MIN="${LOCAL_RAG_MIN_MEDICINE_PCT:-80}"
CON_MIN="${LOCAL_RAG_MIN_CONCIERGE_PCT:-90}"
MED_OUT="${REPORT_DIR}/medicine_kb_local_ci_${STAMP}.json"
CON_OUT="${REPORT_DIR}/concierge_kb_local_ci_${STAMP}.json"

if [[ ! -d "${ROOT}/build/medicine" ]]; then
  echo "==> build/medicine missing — generating corpus"
  "$PY" "${ROOT}/scripts/build_medicine_kb_documents.py"
fi

echo "==> pytest local RAG router"
"$PY" -m pytest "${ROOT}/tests/services/test_local_rag_router.py" -q

echo "==> Medicine local RAG eval (min ${MED_MIN}%, interaction 5/5, mode both)"
"$PY" "${ROOT}/scripts/eval_medicine_kb.py" \
  --provider local \
  --mode both \
  --min-pass-pct "$MED_MIN" \
  --min-interaction-pass 5 \
  --output "$MED_OUT"

echo "==> Concierge local RAG eval (min ${CON_MIN}%)"
"$PY" "${ROOT}/scripts/eval_concierge_kb.py" \
  --provider local \
  --min-pass-pct "$CON_MIN" \
  --output "$CON_OUT"

if [[ "${RUN_LOCAL_RAG_BENCHMARK:-0}" == "1" ]]; then
  echo "==> retrieve latency benchmark"
  "$PY" "${ROOT}/scripts/local_rag_retrieve_benchmark.py" \
    --output "${REPORT_DIR}/local_rag_benchmark_${STAMP}.json"
fi

echo "==> E2E retrieve tier (fixture local_rag_e2e.yaml)"
"$PY" "${ROOT}/scripts/eval_local_rag_e2e.py" \
  --output "${REPORT_DIR}/local_rag_e2e_${STAMP}.json" \
  --min-retrieve-pass-pct 100

PAR_MIN="${LOCAL_RAG_MIN_PARAPHRASE_PCT:-85}"
PAR_OUT="${REPORT_DIR}/local_rag_paraphrase_${STAMP}.json"
echo "==> Paraphrase / colloquial eval (advisory min ${PAR_MIN}%)"
if "$PY" "${ROOT}/scripts/eval_local_rag_paraphrase.py" \
  --output "$PAR_OUT"; then
  echo "    paraphrase: OK ($PAR_OUT)"
else
  echo "    paraphrase: below threshold (advisory) — see $PAR_OUT" >&2
fi

DIV_MIN="${LOCAL_RAG_MIN_DIVERSE_PCT:-85}"
DIV_OUT="${REPORT_DIR}/local_rag_diverse_${STAMP}.json"
echo "==> Diverse + context eval (min ${DIV_MIN}%)"
LLM_FLAG=()
if [[ "${RUN_LOCAL_RAG_LLM_STRESS:-0}" == "1" ]]; then
  LLM_FLAG=(--with-llm-stress)
fi
"$PY" "${ROOT}/scripts/eval_local_rag_diverse.py" \
  --output "$DIV_OUT" \
  --min-pass-pct "$DIV_MIN" \
  "${LLM_FLAG[@]}"
echo "    diverse: $DIV_OUT"

QA_OUT="${REPORT_DIR}/medicine_qa_e2e_${STAMP}.json"
echo "==> Medicine QA E2E (local KB augment, advisory min 90%)"
if "$PY" "${ROOT}/scripts/eval_medicine_qa_e2e.py" \
  --output "$QA_OUT"; then
  echo "    medicine_qa_e2e: OK ($QA_OUT)"
else
  echo "    medicine_qa_e2e: below threshold (advisory) — see $QA_OUT" >&2
fi

if [[ "${RUN_LOCAL_RAG_E2E_HTTP:-0}" == "1" ]]; then
  echo "==> E2E HTTP tier"
  "$PY" "${ROOT}/scripts/eval_local_rag_e2e.py" \
    --with-http \
    --base-url "${E2E_BASE_URL:-${V2_TEST_BASE_URL:-http://127.0.0.1:5000/}}" \
    --output "${REPORT_DIR}/local_rag_e2e_http_${STAMP}.json"
fi

if [[ -n "${LOCAL_RAG_COMPARE_BASELINE:-}" && -f "${LOCAL_RAG_COMPARE_BASELINE}" ]]; then
  echo "==> compare with baseline ${LOCAL_RAG_COMPARE_BASELINE}"
  "$PY" "${ROOT}/scripts/compare_rag_eval.py" \
    "${LOCAL_RAG_COMPARE_BASELINE}" "$MED_OUT" || true
fi

echo "==> Local RAG eval passed"
echo "    medicine: $MED_OUT"
echo "    concierge: $CON_OUT"
