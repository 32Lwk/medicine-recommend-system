#!/usr/bin/env bash
# OpenSearch data access policy 更新 + vector index 作成
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

COLLECTION_NAME="${OPENSEARCH_COLLECTION_NAME:-medicine-recommend-kb}"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${PROJECT_PREFIX}-bedrock-kb-role"
PRINCIPAL="$(aws sts get-caller-identity --query Arn --output text)"
DATA_POLICY="mr-kb-data-access"

VER="$(aws opensearchserverless get-access-policy \
  --name "$DATA_POLICY" --type data --region "$AWS_REGION" \
  --query accessPolicyDetail.policyVersion --output text)"

POLICY="$(cat <<EOF
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
)"

aws opensearchserverless update-access-policy \
  --name "$DATA_POLICY" \
  --type data \
  --policy-version "$VER" \
  --policy "$POLICY" \
  --region "$AWS_REGION" >/dev/null

echo "Updated data access policy (principal: ${PRINCIPAL})"
sleep 5
cd "$ROOT"
python3 scripts/create_aoss_vector_index.py
echo "Next: ./scripts/create-aws-bedrock-kb.sh"
