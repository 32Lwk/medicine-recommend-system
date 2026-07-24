#!/usr/bin/env bash
# 医薬品 KB ソース（CSV 等）を S3 medicine/ プレフィックスへ同期
#
# Usage:
#   AWS_PROFILE=admin ./scripts/sync-medicine-kb-to-s3.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"
DEST="s3://${BUCKET}/medicine/data/"

echo "==> Sync data/*.csv -> ${DEST}"
aws s3 sync "$(to_win_path "$ROOT/data")" "$DEST" --delete --region "$AWS_REGION" \
  --exclude "*" --include "*.csv"

echo "Medicine KB source synced to ${DEST}"
