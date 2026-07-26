#!/usr/bin/env bash
# PMDA 正本 CSV → Medicine Managed KB 反映（build → S3 sync → ingestion → eval）
#
# Usage:
#   AWS_PROFILE=admin ./scripts/reflect_medicine_kb.sh
#   AWS_PROFILE=admin ./scripts/reflect_medicine_kb.sh --skip-reparse
#   AWS_PROFILE=admin ./scripts/reflect_medicine_kb.sh --skip-eval
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

SKIP_REPARSE=0
SKIP_EVAL=0
for arg in "$@"; do
  case "$arg" in
    --skip-reparse) SKIP_REPARSE=1 ;;
    --skip-eval) SKIP_EVAL=1 ;;
  esac
done

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

MEDICINE_KB_ID="${MEDICINE_KB_ID:-30BCEJCJHA}"
MEDICINE_DS_ID="${MEDICINE_DS_ID:-0ZCBZWSQ7N}"

if [[ "$SKIP_REPARSE" -eq 0 ]]; then
  echo "==> Reparse raw HTML → CSV canonical"
  "$PY" "$ROOT/scripts/pmda/reparse_from_raw.py"
fi

echo "==> Build Medicine KB documents"
"$PY" "$ROOT/scripts/build_medicine_kb_documents.py" --clean

echo "==> Rebuild local RAG index (incremental embed, optional)"
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  "$PY" "$ROOT/scripts/build_local_rag_index.py" --namespace all \
    || echo "WARN: local RAG embed index build failed (BM25 + router remain active)"
else
  echo "    OPENAI_API_KEY unset — skip embed index (BM25 + router only)"
fi

echo "==> Sync build/medicine/ → S3"
bash "$ROOT/scripts/sync-medicine-kb-to-s3.sh"

echo "==> Start Medicine KB ingestion (kb=${MEDICINE_KB_ID})"
ingest_out="$("$PY" "$ROOT/scripts/start_bedrock_kb_ingestion.py" \
  "$MEDICINE_KB_ID" "$MEDICINE_DS_ID" \
  --skip-preflight \
  --preflight-max-wait 0 \
  --max-attempts "${KB_INGESTION_MAX_ATTEMPTS:-3}" \
  --region "$AWS_REGION" \
  ${AWS_PROFILE:+--profile "$AWS_PROFILE"} 2>&1)" || ingest_out=""
if [[ -z "$ingest_out" ]] || ! printf '%s\n' "$ingest_out" | grep -q '^Ingestion job:'; then
  echo "WARN: start ingestion returned conflict or error; checking for in-progress job" >&2
  [[ -n "$ingest_out" ]] && printf '%s\n' "$ingest_out" >&2
  job_id="$(AWS_PROFILE="${AWS_PROFILE:-}" aws bedrock-agent list-ingestion-jobs \
    --knowledge-base-id "$MEDICINE_KB_ID" \
    --data-source-id "$MEDICINE_DS_ID" \
    --region "$AWS_REGION" \
    --query 'ingestionJobSummaries[?status==`IN_PROGRESS`].ingestionJobId | [0]' \
    --output text 2>/dev/null || true)"
  if [[ -z "$job_id" || "$job_id" == "None" ]]; then
    echo "ERROR: could not start or find ingestion job" >&2
    exit 1
  fi
  echo "==> Resuming wait for in-progress job ${job_id}"
else
  printf '%s\n' "$ingest_out"
  job_id="$(printf '%s\n' "$ingest_out" | sed -n 's/^Ingestion job: //p' | tail -1)"
fi

wait_sec="${KB_INGESTION_WAIT_SEC:-3600}"
elapsed=0
poll=30
echo "==> Wait for ingestion job ${job_id} (max ${wait_sec}s)"
while [[ "$elapsed" -lt "$wait_sec" ]]; do
  job_status="$(AWS_PROFILE="${AWS_PROFILE:-}" aws bedrock-agent get-ingestion-job \
    --knowledge-base-id "$MEDICINE_KB_ID" \
    --data-source-id "$MEDICINE_DS_ID" \
    --ingestion-job-id "$job_id" \
    --region "$AWS_REGION" \
    --query 'ingestionJob.status' \
    --output text)"
  echo "    status=${job_status} elapsed=${elapsed}s"
  case "$job_status" in
    COMPLETE) break ;;
    FAILED|STOPPED)
      echo "ERROR: ingestion job ${job_id} ended with ${job_status}" >&2
      exit 1
      ;;
  esac
  sleep "$poll"
  elapsed=$((elapsed + poll))
done

if [[ "${job_status:-}" != "COMPLETE" ]]; then
  echo "ERROR: ingestion job timed out after ${wait_sec}s" >&2
  exit 1
fi
stamp="$(date +%Y%m%d)"
report_dir="$ROOT/log/analysis"
mkdir -p "$report_dir"
report_path="$report_dir/medicine_kb_pmda_reflect_${stamp}.json"

if [[ -n "$job_id" ]]; then
  AWS_PROFILE="${AWS_PROFILE:-}" aws bedrock-agent get-ingestion-job \
    --knowledge-base-id "$MEDICINE_KB_ID" \
    --data-source-id "$MEDICINE_DS_ID" \
    --ingestion-job-id "$job_id" \
    --region "$AWS_REGION" \
    --output json > "$report_path"
  echo "==> Ingestion report: $report_path"
fi

if [[ "$SKIP_EVAL" -eq 0 ]]; then
  echo "==> Run local RAG eval"
  "$PY" "$ROOT/scripts/eval_medicine_kb.py" \
    --provider local \
    --min-pass-pct 80 \
    --min-interaction-pass 5 \
    --output "$report_dir/medicine_kb_local_reflect_${stamp}.json" \
    || echo "WARN: local RAG eval below threshold"

  echo "==> Run Medicine KB eval (Bedrock)"
  "$PY" "$ROOT/scripts/eval_medicine_kb.py" \
    --phase phase2_kb \
    --output "$report_dir/medicine_kb_pmda_eval_${stamp}.json" \
    || echo "WARN: Bedrock medicine KB eval failed or below threshold"
fi

echo "==> Medicine KB reflect complete"
