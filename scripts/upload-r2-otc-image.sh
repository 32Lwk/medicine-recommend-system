#!/usr/bin/env bash
# R2 に OTC 画像を 1 件アップロード（S3 互換 API + aws cli）
#
# Usage:
#   export R2_ACCESS_KEY_ID=...
#   export R2_SECRET_ACCESS_KEY=...
#   export R2_S3_ENDPOINT=https://2a1ac0678cd0b207ca4fa5681a9a0690.r2.cloudflarestorage.com
#   export R2_BUCKET=medicine-recommend-otc-images
#   ./scripts/upload-r2-otc-image.sh test static/line/medicine-noimage-hero.png
#
set -euo pipefail

SLUG="${1:?slug required (e.g. test)}"
FILE="${2:?file path required}"
BUCKET="${R2_BUCKET:-medicine-recommend-otc-images}"
ENDPOINT="${R2_S3_ENDPOINT:?set R2_S3_ENDPOINT}"
KEY="otc/${SLUG}.webp"

if [[ ! -f "$FILE" ]]; then
  echo "ERROR: file not found: $FILE" >&2
  exit 1
fi

export AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:?set R2_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:?set R2_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION=auto

aws s3 cp "$FILE" "s3://${BUCKET}/${KEY}" \
  --endpoint-url "$ENDPOINT" \
  --content-type "image/webp"

echo "Uploaded: https://images.yutok.dev/${KEY}"
echo "Verify: curl -sI https://images.yutok.dev/${KEY}"
