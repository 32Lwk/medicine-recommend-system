#!/usr/bin/env bash
# Bedrock KB: S3 data source 作成 + ingestion job 開始（Titan 429 対策付き）
#
# Usage:
#   AWS_PROFILE=admin ./scripts/sync-aws-bedrock-kb-ingestion.sh [KB_ID]
#
# 環境変数:
#   INGESTION_PREFLIGHT_WAIT_SEC=600  Titan 事前チェック最大待機（0=スキップ）
#   INGESTION_MAX_ATTEMPTS=5          StartIngestionJob リトライ回数
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/lib/aws_common.sh"

KB_ID="${1:-}"
if [[ -z "$KB_ID" && -f "$ROOT/scripts/.aws-bedrock-kb-id" ]]; then
  KB_ID="$(tr -d '\r\n' < "$ROOT/scripts/.aws-bedrock-kb-id")"
fi
if [[ -z "$KB_ID" ]]; then
  echo "Usage: $0 <knowledge-base-id>" >&2
  exit 1
fi

PREFLIGHT_WAIT="${INGESTION_PREFLIGHT_WAIT_SEC:-600}"
MAX_ATTEMPTS="${INGESTION_MAX_ATTEMPTS:-5}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"
DS_NAME="${PROJECT_PREFIX}-concierge-s3"

EXISTING_DS="$(aws bedrock-agent list-data-sources \
  --knowledge-base-id "$KB_ID" --region "$AWS_REGION" \
  --query "dataSourceSummaries[?name=='${DS_NAME}'].dataSourceId | [0]" --output text 2>/dev/null || true)"

if [[ -n "$EXISTING_DS" && "$EXISTING_DS" != "None" ]]; then
  DS_ID="$EXISTING_DS"
  echo "Data source exists: ${DS_ID}"
else
  echo "==> Create data source: ${DS_NAME}"
  DS_ID="$(aws bedrock-agent create-data-source \
    --region "$AWS_REGION" \
    --knowledge-base-id "$KB_ID" \
    --name "$DS_NAME" \
    --data-source-configuration "{\"type\":\"S3\",\"s3Configuration\":{\"bucketArn\":\"arn:aws:s3:::${BUCKET}\",\"inclusionPrefixes\":[\"content/\"]}}" \
    --query dataSource.dataSourceId --output text)"
  echo "Created data source: ${DS_ID}"
fi

echo "==> Start ingestion job (preflight + exponential backoff)"
cd "$ROOT"
py -3.11 scripts/start_bedrock_kb_ingestion.py "$KB_ID" "$DS_ID" \
  --profile "${AWS_PROFILE:-}" \
  --region "$AWS_REGION" \
  --preflight-max-wait "$PREFLIGHT_WAIT" \
  --max-attempts "$MAX_ATTEMPTS"
