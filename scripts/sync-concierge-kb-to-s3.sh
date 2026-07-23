#!/usr/bin/env bash
# Concierge KB ソースを S3 に同期
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/sync-concierge-kb-to-s3.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"

echo "==> Ensure S3 bucket: ${BUCKET}"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Bucket exists"
else
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  echo "Created bucket"
fi

echo "==> Sync concierge docs -> s3://${BUCKET}/concierge/"
aws s3 sync "$(to_win_path "$ROOT/docs/concierge")" "s3://${BUCKET}/concierge/" --delete --region "$AWS_REGION"
aws s3 sync "$(to_win_path "$ROOT/docs/public")" "s3://${BUCKET}/public/" --delete --region "$AWS_REGION"
aws s3 cp "$(to_win_path "$ROOT/src/content/concierge_knowledge.ja.json")" "s3://${BUCKET}/content/concierge_knowledge.ja.json" --region "$AWS_REGION"

echo "KB source synced to s3://${BUCKET}/"
