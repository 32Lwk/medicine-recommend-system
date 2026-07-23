#!/usr/bin/env bash
# Phase 1 インフラ一括セットアップ（CloudWatch / WAF / CloudFront）
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-infra.sh
#
# 個別実行:
#   ./scripts/setup-aws-cloudwatch.sh
#   ./scripts/setup-aws-waf.sh
#   ./scripts/setup-aws-cloudfront.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== medicine-recommend AWS Phase 1 infra ==="
echo ""

export SKIP_ECS_TD_UPDATE="${SKIP_ECS_TD_UPDATE:-true}"
bash "$ROOT/scripts/setup-aws-cloudwatch.sh"
echo ""
bash "$ROOT/scripts/setup-aws-waf.sh"
echo ""
bash "$ROOT/scripts/setup-aws-cloudfront.sh"
echo ""

if [[ -f "$ROOT/scripts/.aws-static-cdn-url" ]]; then
  CDN_URL="$(cat "$ROOT/scripts/.aws-static-cdn-url")"
  echo "=== Next steps ==="
  echo "1. Add to .env: STATIC_CDN_BASE_URL=${CDN_URL}"
  echo "2. Express env: STATIC_CDN_BASE_URL=${CDN_URL} ./scripts/update-aws-express-env.sh"
  echo "   (または .env に追記して ./scripts/update-aws-express-env.sh .env)"
  echo "3. Optional pipeline sync: add sync-static-to-s3.sh to buildspec post_build"
  echo "4. Verify: curl -I https://aws.medicine.yutok.dev/health"
fi
