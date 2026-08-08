#!/usr/bin/env bash
# Lambda + Function URL for on-access AWS staging wake (used by Cloudflare Worker).
#
# Usage:
#   AWS_PROFILE=default ./scripts/setup-aws-wake-staging.sh
#   AWS_PROFILE=default ./scripts/setup-aws-wake-staging.sh --dry-run
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"
# shellcheck source=lib/bundle_lambda.sh
source "$ROOT/scripts/lib/bundle_lambda.sh"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

LAMBDA_NAME="${WAKE_LAMBDA_NAME:-medicine-recommend-wake-staging}"
LAMBDA_ROLE="${WAKE_LAMBDA_ROLE:-medicine-recommend-wake-staging-role}"
HANDLER_DIR="$ROOT/scripts/lambda/wake_staging"
OUT_FILE="$ROOT/scripts/.aws-wake-staging.json"
PIPELINE_NAME="${PIPELINE_NAME:-medicine-recommend-main}"
SCALING_RESOURCE_ID="service/${ECS_CLUSTER}/${ECS_SERVICE}"

echo "==> Wake-on-access Lambda: ${LAMBDA_NAME}"

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would create IAM + Lambda + Function URL"
  exit 0
fi

TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

if aws iam get-role --role-name "$LAMBDA_ROLE" >/dev/null 2>&1; then
  echo "IAM role exists: $LAMBDA_ROLE"
else
  aws iam create-role \
    --role-name "$LAMBDA_ROLE" \
    --assume-role-policy-document "$TRUST_POLICY" \
    --description "medicine-recommend wake staging on access" >/dev/null
  echo "Created IAM role: $LAMBDA_ROLE"
fi

aws iam attach-role-policy \
  --role-name "$LAMBDA_ROLE" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  2>/dev/null || true

INLINE_POLICY="$(mktemp)"
cat > "$INLINE_POLICY" <<EOFPOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:UpdateService"
      ],
      "Resource": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"
    },
    {
      "Effect": "Allow",
      "Action": ["application-autoscaling:RegisterScalableTarget"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["codepipeline:EnableStageTransition"],
      "Resource": "arn:aws:codepipeline:${AWS_REGION}:${AWS_ACCOUNT_ID}:${PIPELINE_NAME}"
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:PutParameter", "ssm:GetParameter"],
      "Resource": "arn:aws:ssm:${AWS_REGION}:${AWS_ACCOUNT_ID}:parameter/medicine-recommend/staging/*"
    }
  ]
}
EOFPOL
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE" \
  --policy-name medicine-recommend-wake-staging \
  --policy-document "$(aws_file_arg "$INLINE_POLICY")"
rm -f "$INLINE_POLICY"

ROLE_ARN="$(aws iam get-role --role-name "$LAMBDA_ROLE" --query Role.Arn --output text)"
sleep 8

WAKE_TOKEN=""
if [[ -f "$OUT_FILE" ]]; then
  WAKE_TOKEN="$(python3 - "$OUT_FILE" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("wake_token", ""))
except Exception:
    pass
PY
)"
fi
if [[ -z "$WAKE_TOKEN" ]]; then
  WAKE_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
fi

ZIP_FILE="${HANDLER_DIR}/.lambda-wake-bundle.zip"
bundle_lambda_zip "$HANDLER_DIR" "$ZIP_FILE"
ZIP_ARG="fileb://${ZIP_FILE}"
if command -v cygpath >/dev/null 2>&1; then
  ZIP_ARG="fileb://$(cygpath -w "$ZIP_FILE")"
fi

ENV_VARS="Variables={ECS_CLUSTER=${ECS_CLUSTER},ECS_SERVICE=${ECS_SERVICE},PIPELINE_NAME=${PIPELINE_NAME},WAKE_TOKEN=${WAKE_TOKEN},ENABLE_PIPELINE_ON_WAKE=false,WAKE_MIN_CAPACITY=1,WAKE_MAX_CAPACITY=1,WAKE_DESIRED_COUNT=1}"

if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file "$ZIP_ARG" \
    --region "$AWS_REGION" >/dev/null
  for attempt in 1 2 3 4 5 6; do
    if aws lambda update-function-configuration \
      --function-name "$LAMBDA_NAME" \
      --environment "$ENV_VARS" \
      --timeout 30 \
      --region "$AWS_REGION" >/dev/null 2>&1; then
      break
    fi
    [[ "$attempt" -eq 6 ]] && echo "WARN: update-function-configuration skipped" >&2
    sleep 5
  done
  echo "Updated Lambda: $LAMBDA_NAME"
else
  aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.12 \
    --role "$ROLE_ARN" \
    --handler handler.lambda_handler \
    --zip-file "$ZIP_ARG" \
    --timeout 30 \
    --environment "$ENV_VARS" \
    --region "$AWS_REGION" >/dev/null
  echo "Created Lambda: $LAMBDA_NAME"
fi
rm -f "$ZIP_FILE"

# Function URL (public + token auth in handler)
FUNC_URL=""
EXISTING_URL="$(aws lambda list-function-url-configs \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION" \
  --query 'FunctionUrlConfigs[0].FunctionUrl' \
  --output text 2>/dev/null || echo None)"
if [[ "$EXISTING_URL" != "None" && -n "$EXISTING_URL" ]]; then
  FUNC_URL="$EXISTING_URL"
else
  FUNC_URL="$(aws lambda create-function-url-config \
    --function-name "$LAMBDA_NAME" \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["GET","POST"],"AllowHeaders":["content-type","x-wake-token"]}' \
    --region "$AWS_REGION" \
    --query FunctionUrl --output text)"
  aws lambda add-permission \
    --function-name "$LAMBDA_NAME" \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE \
    --region "$AWS_REGION" 2>/dev/null || true
  aws lambda add-permission \
    --function-name "$LAMBDA_NAME" \
    --statement-id FunctionURLAllowPublicAccessInvoke \
    --action lambda:InvokeFunction \
    --principal "*" \
    --region "$AWS_REGION" 2>/dev/null || true
fi

LAMBDA_ARN="$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" --query Configuration.FunctionArn --output text)"

python3 - "$OUT_FILE" "$LAMBDA_ARN" "$FUNC_URL" "$WAKE_TOKEN" "$AWS_ACCOUNT_ID" "$AWS_REGION" <<'PY'
import json, sys
path, arn, url, token, account, region = sys.argv[1:7]
data = {
    "lambda_name": "medicine-recommend-wake-staging",
    "lambda_arn": arn,
    "function_url": url.rstrip("/"),
    "wake_token": token,
    "account_id": account,
    "region": region,
    "cloudflare_worker": "workers/cloudflare-aws-staging-wake.js",
    "cloudflare_route": "aws-medicine.yutok.dev/*",
    "wake_url": "https://aws-medicine.yutok.dev",
    "origin_url": "https://origin-aws-medicine.yutok.dev",
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(path)
PY

echo ""
echo "=== Wake staging ready ==="
echo "Function URL: ${FUNC_URL}"
echo "Config: scripts/.aws-wake-staging.json"
echo ""
echo "Next: deploy Cloudflare Worker — docs/ops/AWS_WAKE_ON_ACCESS.md"
echo "  WAKE_API_URL=${FUNC_URL}"
echo "  WAKE_TOKEN=(see .aws-wake-staging.json — do not commit token to public repos)"
