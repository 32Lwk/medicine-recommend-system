#!/usr/bin/env bash
# Bedrock Knowledge Base（Concierge RAG）— S3 同期 + KB 作成/更新
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-bedrock-kb.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

bash "$ROOT/scripts/sync-concierge-kb-to-s3.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"
KB_NAME="${PROJECT_PREFIX}-concierge-kb"
ROLE_NAME="${PROJECT_PREFIX}-bedrock-kb-role"
OUT_FILE="$ROOT/scripts/.aws-bedrock-kb-id"

echo "==> IAM role for Bedrock KB: ${ROLE_NAME}"
TRUST='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"bedrock.amazonaws.com"},"Action":"sts:AssumeRole","Condition":{"StringEquals":{"aws:SourceAccount":"'"$ACCOUNT_ID"'"},"ArnLike":{"aws:SourceArn":"arn:aws:bedrock:'"$AWS_REGION"':'"$ACCOUNT_ID"':knowledge-base/*"}}}]}'
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "Role exists"
else
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST" >/dev/null
  echo "Created role"
fi

POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::'"$BUCKET"'","arn:aws:s3:::'"$BUCKET"'/*"]},{"Effect":"Allow","Action":["bedrock:InvokeModel"],"Resource":"*"}]}'
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "${PROJECT_PREFIX}-bedrock-kb-s3" --policy-document "$POLICY" >/dev/null
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)"

EXISTING_KB="$(aws bedrock-agent list-knowledge-bases --region "$AWS_REGION" \
  --query "knowledgeBaseSummaries[?name=='${KB_NAME}'].knowledgeBaseId | [0]" --output text 2>/dev/null || true)"

if [[ -n "$EXISTING_KB" && "$EXISTING_KB" != "None" ]]; then
  KB_ID="$EXISTING_KB"
  echo "Knowledge base exists: ${KB_ID}"
else
  echo "==> Create Knowledge Base: ${KB_NAME}"
  KB_ID="$(aws bedrock-agent create-knowledge-base \
    --region "$AWS_REGION" \
    --name "$KB_NAME" \
    --role-arn "$ROLE_ARN" \
    --knowledge-base-configuration '{"type":"VECTOR","vectorKnowledgeBaseConfiguration":{"embeddingModelArn":"arn:aws:bedrock:'"$AWS_REGION"'::foundation-model/amazon.titan-embed-text-v2:0"}}' \
    --storage-configuration '{"type":"OPENSEARCH_SERVERLESS","opensearchServerlessConfiguration":{"collectionArn":"'"${OPENSEARCH_COLLECTION_ARN:-}"'","vectorIndexName":"'"${KB_VECTOR_INDEX:-concierge-index}"'","fieldMapping":{"vectorField":"embedding","textField":"text","metadataField":"metadata"}}}' \
    --query knowledgeBase.knowledgeBaseId --output text 2>/dev/null || true)"
  if [[ -z "$KB_ID" || "$KB_ID" == "None" ]]; then
    echo "WARN: auto-create failed (OpenSearch Serverless collection required)." >&2
    echo "Set OPENSEARCH_COLLECTION_ARN and re-run, or create KB in console then:" >&2
    echo "  echo '<kb-id>' > scripts/.aws-bedrock-kb-id" >&2
    exit 0
  fi
  echo "Created KB: ${KB_ID}"
fi

echo "$KB_ID" > "$OUT_FILE"
echo "BEDROCK_KB_ID=${KB_ID}" > "$ROOT/scripts/.aws-bedrock-kb-env"
echo ""
echo "Next: add BEDROCK_KB_ID=${KB_ID} and CONCIERGE_RAG_PROVIDER=bedrock_kb to .env"
echo "Then: ./scripts/setup-aws-ecs-secrets.sh .env"
