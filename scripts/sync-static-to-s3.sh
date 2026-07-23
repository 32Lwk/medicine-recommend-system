#!/usr/bin/env bash
# static/ を S3 に同期（CloudFront オリジン）
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/sync-static-to-s3.sh
#   ./scripts/sync-static-to-s3.sh --invalidate   # CloudFront キャッシュ削除も
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${STATIC_S3_BUCKET:-${PROJECT_PREFIX}-static-${ACCOUNT_ID}}"
COMMENT="${PROJECT_PREFIX} static assets"

aws s3 sync "$(to_win_path "$ROOT/static")/" "s3://${BUCKET}/static/" --delete --region "$AWS_REGION"
echo "Synced to s3://${BUCKET}/static/"

if [[ "${1:-}" == "--invalidate" ]]; then
  DIST_ID="$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='${COMMENT}'].Id | [0]" --output text 2>/dev/null || true)"
  if [[ -n "$DIST_ID" && "$DIST_ID" != "None" ]]; then
    aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/static/*"
    echo "Invalidation submitted for ${DIST_ID}"
  else
    echo "WARN: CloudFront distribution not found; skip invalidation" >&2
  fi
fi
