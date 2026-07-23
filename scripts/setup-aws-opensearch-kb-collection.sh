#!/usr/bin/env bash
# OpenSearch Serverless — Bedrock KB 用 VECTORSEARCH コレクション
#
# Usage:
#   AWS_PROFILE=admin ./scripts/setup-aws-opensearch-kb-collection.sh
#   # 出力 ARN を OPENSEARCH_COLLECTION_ARN に設定して setup-aws-bedrock-kb.sh を再実行
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

COLLECTION_NAME="${OPENSEARCH_COLLECTION_NAME:-${PROJECT_PREFIX}-kb}"
ROLE_NAME="${PROJECT_PREFIX}-bedrock-kb-role"
OUT_FILE="$ROOT/scripts/.aws-opensearch-collection-arn"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
PRINCIPAL="$(aws sts get-caller-identity --query Arn --output text)"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "==> OpenSearch Serverless collection: ${COLLECTION_NAME}"

ENC_POLICY="${PROJECT_PREFIX}-kb-encryption"
NET_POLICY="${PROJECT_PREFIX}-kb-network"
DATA_POLICY="mr-kb-data-access"

aws opensearchserverless create-security-policy \
  --name "$ENC_POLICY" \
  --type encryption \
  --policy "{\"Rules\":[{\"ResourceType\":\"collection\",\"Resource\":[\"collection/${COLLECTION_NAME}\"]}],\"AWSOwnedKey\":true}" \
  --region "$AWS_REGION" 2>/dev/null || echo "Encryption policy exists or updated"

aws opensearchserverless create-security-policy \
  --name "$NET_POLICY" \
  --type network \
  --policy "[{\"Description\":\"Public access\",\"Rules\":[{\"ResourceType\":\"collection\",\"Resource\":[\"collection/${COLLECTION_NAME}\"]}],\"AllowFromPublic\":true},{\"Description\":\"Bedrock service access\",\"Rules\":[{\"ResourceType\":\"collection\",\"Resource\":[\"collection/${COLLECTION_NAME}\"]}],\"SourceServices\":[\"bedrock.amazonaws.com\"],\"AllowFromPublic\":false}]" \
  --region "$AWS_REGION" 2>/dev/null || echo "Network policy exists or updated"

EXISTING="$(aws opensearchserverless list-collections --region "$AWS_REGION" \
  --query "collectionSummaries[?name=='${COLLECTION_NAME}'].id | [0]" --output text 2>/dev/null || true)"

if [[ -z "$EXISTING" || "$EXISTING" == "None" ]]; then
  aws opensearchserverless create-collection \
    --name "$COLLECTION_NAME" \
    --type VECTORSEARCH \
    --region "$AWS_REGION" >/dev/null
  echo "Collection creation started"
  for _ in $(seq 1 60); do
    EXISTING="$(aws opensearchserverless list-collections --region "$AWS_REGION" \
      --query "collectionSummaries[?name=='${COLLECTION_NAME}'].id | [0]" --output text 2>/dev/null || true)"
    STATUS="$(aws opensearchserverless list-collections --region "$AWS_REGION" \
      --query "collectionSummaries[?name=='${COLLECTION_NAME}'].status | [0]" --output text 2>/dev/null || true)"
    if [[ "$STATUS" == "ACTIVE" && -n "$EXISTING" && "$EXISTING" != "None" ]]; then
      break
    fi
    sleep 10
  done
fi

COLLECTION_ARN="arn:aws:aoss:${AWS_REGION}:${ACCOUNT_ID}:collection/${EXISTING}"
echo "$COLLECTION_ARN" > "$OUT_FILE"

DATA_DOC=$(cat <<EOF
[
  {
    "Rules": [
      {
        "ResourceType": "collection",
        "Resource": ["collection/${COLLECTION_NAME}"],
        "Permission": [
          "aoss:CreateCollectionItems",
          "aoss:DeleteCollectionItems",
          "aoss:UpdateCollectionItems",
          "aoss:DescribeCollectionItems"
        ]
      },
      {
        "ResourceType": "index",
        "Resource": ["index/${COLLECTION_NAME}/*"],
        "Permission": [
          "aoss:CreateIndex",
          "aoss:DeleteIndex",
          "aoss:UpdateIndex",
          "aoss:DescribeIndex",
          "aoss:ReadDocument",
          "aoss:WriteDocument"
        ]
      }
    ],
    "Principal": ["${ROLE_ARN}", "${PRINCIPAL}"]
  }
]
EOF
)

aws opensearchserverless create-access-policy \
  --name "$DATA_POLICY" \
  --type data \
  --policy "$DATA_DOC" \
  --region "$AWS_REGION" 2>/dev/null || echo "Data access policy exists (update manually if needed)"

echo ""
echo "OPENSEARCH_COLLECTION_ARN=${COLLECTION_ARN}"
echo "Next:"
echo "  OPENSEARCH_COLLECTION_ARN=${COLLECTION_ARN} AWS_PROFILE=admin ./scripts/setup-aws-bedrock-kb.sh"
