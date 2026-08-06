#!/usr/bin/env bash
# Write scripts/.aws-wake-staging.json from live AWS Lambda (local only, gitignored).
#
# Usage:
#   AWS_PROFILE=default ./scripts/print-aws-wake-staging-config.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

LAMBDA_NAME="${WAKE_LAMBDA_NAME:-medicine-recommend-wake-staging}"
OUT_FILE="$ROOT/scripts/.aws-wake-staging.json"
ORIGIN_URL="${ORIGIN_URL:-https://me-9585b72a360742069939f7e74bb4bb46.ecs.ap-northeast-1.on.aws}"

FUNC_URL="$(aws lambda list-function-url-configs \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --query 'FunctionUrlConfigs[0].FunctionUrl' \
  --output text)"
WAKE_TOKEN="$(aws lambda get-function-configuration \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --query 'Environment.Variables.WAKE_TOKEN' \
  --output text)"
LAMBDA_ARN="$(aws lambda get-function \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --query Configuration.FunctionArn \
  --output text)"

python3 - "$OUT_FILE" "$LAMBDA_ARN" "$FUNC_URL" "$WAKE_TOKEN" "$AWS_ACCOUNT_ID" "$AWS_REGION" "$ORIGIN_URL" <<'PY'
import json, sys
path, arn, url, token, account, region, origin = sys.argv[1:8]
data = {
    "lambda_name": "medicine-recommend-wake-staging",
    "lambda_arn": arn,
    "function_url": url.rstrip("/"),
    "wake_token": token,
    "origin_url": origin.rstrip("/"),
    "account_id": account,
    "region": region,
    "cloudflare_worker": "workers/cloudflare-aws-staging-wake.js",
    "cloudflare_route": "aws.medicine.yutok.dev/*",
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"Wrote {path}")
print(f"  WAKE_API_URL={data['function_url']}")
print(f"  ORIGIN_URL={data['origin_url']}")
print("  WAKE_TOKEN=(see file; do not commit)")
PY
