#!/usr/bin/env bash
# 医薬品 KB ソース（Markdown + metadata + raw CSV）を S3 medicine/ へ同期
#
# Usage:
#   python scripts/build_medicine_kb_documents.py
#   AWS_PROFILE=admin ./scripts/sync-medicine-kb-to-s3.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"
BUILD_DIR="$ROOT/build/medicine"
DEST="s3://${BUCKET}/medicine/"

if [[ ! -d "$BUILD_DIR/products" ]]; then
  echo "ERROR: $BUILD_DIR/products not found. Run: python scripts/build_medicine_kb_documents.py" >&2
  exit 1
fi

echo "==> Sync build/medicine/ -> ${DEST}"
aws s3 sync "$(to_win_path "$BUILD_DIR")" "$DEST" --delete --region "$AWS_REGION"

echo "==> Sync raw CSV backup -> ${DEST}raw/data/"
aws s3 sync "$(to_win_path "$ROOT/data")" "${DEST}raw/data/" --region "$AWS_REGION" \
  --exclude "*" --include "*.csv" --exclude "pmda/backups/*"

echo "Medicine KB source synced to ${DEST}"
