#!/usr/bin/env bash
# Bedrock KB 作成（OpenSearch Serverless 連携）— admin 推奨
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

COLLECTION_ARN="${OPENSEARCH_COLLECTION_ARN:-}"
if [[ -z "$COLLECTION_ARN" && -f "$ROOT/scripts/.aws-opensearch-collection-arn" ]]; then
  COLLECTION_ARN="$(tr -d '\r\n' < "$ROOT/scripts/.aws-opensearch-collection-arn")"
fi
if [[ -z "$COLLECTION_ARN" ]]; then
  echo "ERROR: set OPENSEARCH_COLLECTION_ARN or run setup-aws-opensearch-kb-collection.sh" >&2
  exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
KB_NAME="${PROJECT_PREFIX}-concierge-kb"
ROLE_NAME="${PROJECT_PREFIX}-bedrock-kb-role"
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)"
VECTOR_INDEX="${KB_VECTOR_INDEX:-bedrock-knowledge-base-default-index}"
VECTOR_FIELD="${KB_VECTOR_FIELD:-bedrock-knowledge-base-default-vector}"
TEXT_FIELD="${KB_TEXT_FIELD:-AMAZON_BEDROCK_TEXT_CHUNK}"
METADATA_FIELD="${KB_METADATA_FIELD:-AMAZON_BEDROCK_METADATA}"

EXISTING_KB="$(aws bedrock-agent list-knowledge-bases --region "$AWS_REGION" \
  --query "knowledgeBaseSummaries[?name=='${KB_NAME}'].knowledgeBaseId | [0]" --output text 2>/dev/null || true)"

if [[ -n "$EXISTING_KB" && "$EXISTING_KB" != "None" ]]; then
  echo "Knowledge base exists: ${EXISTING_KB}"
  echo "$EXISTING_KB" > "$ROOT/scripts/.aws-bedrock-kb-id"
  exit 0
fi

KB_CFG='{"type":"VECTOR","vectorKnowledgeBaseConfiguration":{"embeddingModelArn":"arn:aws:bedrock:'"$AWS_REGION"'::foundation-model/amazon.titan-embed-text-v2:0"}}'
STORAGE_CFG='{"type":"OPENSEARCH_SERVERLESS","opensearchServerlessConfiguration":{"collectionArn":"'"$COLLECTION_ARN"'","vectorIndexName":"'"$VECTOR_INDEX"'","fieldMapping":{"vectorField":"'"$VECTOR_FIELD"'","textField":"'"$TEXT_FIELD"'","metadataField":"'"$METADATA_FIELD"'"}}}'

echo "==> create-knowledge-base: ${KB_NAME}"
set +e
CREATE_OUT="$(aws bedrock-agent create-knowledge-base \
  --region "$AWS_REGION" \
  --name "$KB_NAME" \
  --role-arn "$ROLE_ARN" \
  --knowledge-base-configuration "$KB_CFG" \
  --storage-configuration "$STORAGE_CFG" \
  --output json 2>&1)"
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  echo "$CREATE_OUT" >&2
  exit 1
fi

KB_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['knowledgeBase']['knowledgeBaseId'])" "$CREATE_OUT")"
echo "$KB_ID" > "$ROOT/scripts/.aws-bedrock-kb-id"
echo "Created KB: ${KB_ID}"
