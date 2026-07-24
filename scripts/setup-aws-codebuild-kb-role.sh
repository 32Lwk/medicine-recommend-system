#!/usr/bin/env bash
# CodeBuild ロールに KB sync / ingestion 権限を追加
#
# Usage:
#   AWS_PROFILE=admin ./scripts/setup-aws-codebuild-kb-role.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

CB_ROLE="${CB_ROLE:-medicine-recommend-codebuild-role}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"
CONCIERGE_KB_ID="${CONCIERGE_KB_ID:-2CNAGQ2V4P}"
MEDICINE_KB_ID="${MEDICINE_KB_ID:-30BCEJCJHA}"

POLICY="$(mktemp)"
cat > "$POLICY" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockKBIngestion",
      "Effect": "Allow",
      "Action": [
        "bedrock:StartIngestionJob",
        "bedrock:GetIngestionJob",
        "bedrock:ListIngestionJobs",
        "bedrock-agent:StartIngestionJob",
        "bedrock-agent:GetIngestionJob",
        "bedrock-agent:ListIngestionJobs"
      ],
      "Resource": [
        "arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:knowledge-base/${CONCIERGE_KB_ID}",
        "arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:knowledge-base/${MEDICINE_KB_ID}",
        "arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:knowledge-base/${CONCIERGE_KB_ID}/*",
        "arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:knowledge-base/${MEDICINE_KB_ID}/*"
      ]
    },
    {
      "Sid": "KBSourceBucket",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name "$CB_ROLE" \
  --policy-name medicine-recommend-codebuild-kb \
  --policy-document "file://${POLICY}"

rm -f "$POLICY"
echo "Attached inline policy medicine-recommend-codebuild-kb to ${CB_ROLE}"
echo "  KB bucket: s3://${BUCKET}/"
echo "  Concierge KB: ${CONCIERGE_KB_ID}"
echo "  Medicine KB: ${MEDICINE_KB_ID}"
echo "Wait ~10s for IAM propagation before re-running CodePipeline."
