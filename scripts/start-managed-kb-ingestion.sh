#!/usr/bin/env bash
# Managed KB 2 系統の ingestion job を非同期起動（完了待ちなし）
#
# Usage:
#   AWS_PROFILE=admin ./scripts/start-managed-kb-ingestion.sh
#
# 失敗時は exit 0 + WARN（CodeBuild post_build 用）
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

CONCIERGE_KB_ID="${CONCIERGE_KB_ID:-2CNAGQ2V4P}"
CONCIERGE_DS_ID="${CONCIERGE_DS_ID:-5NO6DO8WRT}"
MEDICINE_KB_ID="${MEDICINE_KB_ID:-30BCEJCJHA}"
MEDICINE_DS_ID="${MEDICINE_DS_ID:-0ZCBZWSQ7N}"
MAX_ATTEMPTS="${KB_INGESTION_MAX_ATTEMPTS:-3}"

start_job() {
  local label="$1"
  local kb_id="$2"
  local ds_id="$3"
  echo "==> Start ingestion: ${label} (kb=${kb_id} ds=${ds_id})"
  if out="$(python3 "$ROOT/scripts/start_bedrock_kb_ingestion.py" \
    "$kb_id" "$ds_id" \
    --skip-preflight \
    --preflight-max-wait 0 \
    --max-attempts "$MAX_ATTEMPTS" \
    --region "$AWS_REGION" \
    ${AWS_PROFILE:+--profile "$AWS_PROFILE"} 2>&1)"; then
    job_id="$(printf '%s\n' "$out" | sed -n 's/^Ingestion job: //p' | tail -1)"
    if [[ -n "$job_id" ]]; then
      echo "${label}_INGESTION_JOB_ID=${job_id}"
    else
      echo "WARN: ${label} ingestion started but job ID not parsed" >&2
      printf '%s\n' "$out" >&2
    fi
  else
    echo "WARN: ${label} ingestion start failed" >&2
    printf '%s\n' "$out" >&2
  fi
}

failed=0
start_job "CONCIERGE" "$CONCIERGE_KB_ID" "$CONCIERGE_DS_ID" || failed=1
start_job "MEDICINE" "$MEDICINE_KB_ID" "$MEDICINE_DS_ID" || failed=1

if [[ "$failed" -ne 0 ]]; then
  echo "WARN: one or more KB ingestion jobs failed to start (see above)"
fi
exit 0
