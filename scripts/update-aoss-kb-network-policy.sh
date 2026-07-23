#!/usr/bin/env bash
# OpenSearch Serverless network policy — Bedrock サービスアクセス追加（401 対策）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/lib/aws_common.sh"

COLLECTION_NAME="${OPENSEARCH_COLLECTION_NAME:-medicine-recommend-kb}"
NET_POLICY="${PROJECT_PREFIX}-kb-network"

POLICY="$(cat <<EOF
[
  {
    "Description": "Public access for Bedrock KB collection",
    "Rules": [
      {
        "ResourceType": "collection",
        "Resource": ["collection/${COLLECTION_NAME}"]
      }
    ],
    "AllowFromPublic": true
  },
  {
    "Description": "Amazon Bedrock service access",
    "Rules": [
      {
        "ResourceType": "collection",
        "Resource": ["collection/${COLLECTION_NAME}"]
      }
    ],
    "SourceServices": ["bedrock.amazonaws.com"],
    "AllowFromPublic": false
  }
]
EOF
)"

VER="$(aws opensearchserverless get-security-policy \
  --name "$NET_POLICY" --type network --region "$AWS_REGION" \
  --query securityPolicyDetail.policyVersion --output text 2>/dev/null || true)"

if [[ -z "$VER" || "$VER" == "None" ]]; then
  aws opensearchserverless create-security-policy \
    --name "$NET_POLICY" \
    --type network \
    --policy "$POLICY" \
    --region "$AWS_REGION" >/dev/null
  echo "Created network policy ${NET_POLICY} (bedrock.amazonaws.com SourceServices)"
else
  aws opensearchserverless update-security-policy \
    --name "$NET_POLICY" \
    --type network \
    --policy-version "$VER" \
    --policy "$POLICY" \
    --region "$AWS_REGION" >/dev/null
  echo "Updated network policy ${NET_POLICY} (bedrock.amazonaws.com SourceServices)"
fi
echo "Wait ~60s for propagation, then: ./scripts/create-aws-bedrock-kb.sh"
