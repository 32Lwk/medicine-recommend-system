#!/usr/bin/env bash
# Bedrock Managed KB 2 件を一時削除し、local RAG に切り替える（OpenSearch OCU 削減）。
#
# Usage:
#   AWS_PROFILE=admin ./scripts/suspend-aws-bedrock-kb.sh
#
# 8 月復旧:
#   AWS_PROFILE=admin ./scripts/resume-aws-bedrock-kb.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

STATE_FILE="$ROOT/scripts/.aws-bedrock-kb-suspended.json"
CONCIERGE_KB_ID="${CONCIERGE_KB_ID:-2CNAGQ2V4P}"
MEDICINE_KB_ID="${MEDICINE_KB_ID:-30BCEJCJHA}"
CONCIERGE_DS_ID="${CONCIERGE_DS_ID:-5NO6DO8WRT}"
MEDICINE_DS_ID="${MEDICINE_DS_ID:-0ZCBZWSQ7N}"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "WARN: $STATE_FILE missing — using defaults from docs/ops/AWS_BEDROCK_KB.md" >&2
fi

delete_ds() {
  local kb="$1" ds="$2"
  if aws bedrock-agent get-data-source --knowledge-base-id "$kb" --data-source-id "$ds" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "==> Delete data source ${ds} (kb ${kb})"
    aws bedrock-agent delete-data-source --knowledge-base-id "$kb" --data-source-id "$ds" --region "$AWS_REGION" >/dev/null
  fi
}

delete_kb() {
  local kb="$1"
  if aws bedrock-agent get-knowledge-base --knowledge-base-id "$kb" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "==> Delete knowledge base ${kb}"
    aws bedrock-agent delete-knowledge-base --knowledge-base-id "$kb" --region "$AWS_REGION" >/dev/null
  fi
}

echo "==> Switch ECS to local RAG (immediate)"
bash "$ROOT/scripts/apply-aws-minimal-env.sh"

delete_ds "$CONCIERGE_KB_ID" "$CONCIERGE_DS_ID"
delete_ds "$MEDICINE_KB_ID" "$MEDICINE_DS_ID"

echo "==> Wait for data sources (up to 10 min)"
for _ in $(seq 1 40); do
  c="$(aws bedrock-agent list-data-sources --knowledge-base-id "$CONCIERGE_KB_ID" --region "$AWS_REGION" --query 'length(dataSourceSummaries)' --output text 2>/dev/null || echo 0)"
  m="$(aws bedrock-agent list-data-sources --knowledge-base-id "$MEDICINE_KB_ID" --region "$AWS_REGION" --query 'length(dataSourceSummaries)' --output text 2>/dev/null || echo 0)"
  if [[ "$c" == "0" && "$m" == "0" ]]; then break; fi
  sleep 15
done

delete_kb "$CONCIERGE_KB_ID"
delete_kb "$MEDICINE_KB_ID"

echo "==> Wait for KB deletion (up to 10 min)"
for _ in $(seq 1 40); do
  n="$(aws bedrock-agent list-knowledge-bases --region "$AWS_REGION" --query 'length(knowledgeBaseSummaries)' --output text 2>/dev/null || echo 0)"
  if [[ "$n" == "0" ]]; then break; fi
  sleep 15
done

echo "Suspended. Restore in August: AWS_PROFILE=admin ./scripts/resume-aws-bedrock-kb.sh"
