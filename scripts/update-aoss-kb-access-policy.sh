#!/usr/bin/env bash
# AOSS data access policy を拡張（index/* + dev ユーザー）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/lib/aws_common.sh"

DATA_POLICY="mr-kb-data-access"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${PROJECT_PREFIX}-bedrock-kb-role"
ADMIN_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:user/Admin"
DEV_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:user/medicine-recommend-dev"

VER="$(aws opensearchserverless get-access-policy \
  --name "$DATA_POLICY" --type data --region "$AWS_REGION" \
  --query accessPolicyDetail.policyVersion --output text)"

POLICY="$(cat <<EOF
[
  {
    "Rules": [
      {
        "ResourceType": "collection",
        "Resource": ["collection/medicine-recommend-kb"],
        "Permission": [
          "aoss:CreateCollectionItems",
          "aoss:DeleteCollectionItems",
          "aoss:UpdateCollectionItems",
          "aoss:DescribeCollectionItems"
        ]
      },
      {
        "ResourceType": "index",
        "Resource": ["index/medicine-recommend-kb/*"],
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
    "Principal": ["${ROLE_ARN}", "${ADMIN_ARN}", "${DEV_ARN}"]
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

echo "Updated ${DATA_POLICY} (index/* + dev user)"
sleep 15
