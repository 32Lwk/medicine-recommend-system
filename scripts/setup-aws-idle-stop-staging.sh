#!/usr/bin/env bash
# EventBridge schedule → Lambda: stop ECS after IDLE_MINUTES without traffic.
#
# Usage:
#   AWS_PROFILE=default ./scripts/setup-aws-idle-stop-staging.sh
#   IDLE_MINUTES=45 ./scripts/setup-aws-idle-stop-staging.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"
# shellcheck source=lib/bundle_lambda.sh
source "$ROOT/scripts/lib/bundle_lambda.sh"

LAMBDA_NAME="${IDLE_STOP_LAMBDA_NAME:-medicine-recommend-idle-stop-staging}"
LAMBDA_ROLE="${IDLE_STOP_LAMBDA_ROLE:-medicine-recommend-idle-stop-staging-role}"
HANDLER_DIR="$ROOT/scripts/lambda/idle_stop_staging"
RULE_NAME="${IDLE_STOP_RULE_NAME:-medicine-recommend-staging-idle-stop}"
IDLE_MINUTES="${IDLE_MINUTES:-30}"
SCHEDULE="${IDLE_STOP_SCHEDULE:-rate(10 minutes)}"
OUT_FILE="$ROOT/scripts/.aws-idle-stop-staging.json"
SCALING_RESOURCE_ID="service/${ECS_CLUSTER}/${ECS_SERVICE}"
ACTIVITY_PARAM="/medicine-recommend/staging/last-activity"

echo "==> Idle auto-stop Lambda: ${LAMBDA_NAME} (idle=${IDLE_MINUTES}m)"

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
    --description "medicine-recommend idle auto-stop staging" >/dev/null
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
      "Action": ["ecs:DescribeServices", "ecs:UpdateService"],
      "Resource": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"
    },
    {
      "Effect": "Allow",
      "Action": ["application-autoscaling:RegisterScalableTarget"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameter"],
      "Resource": "arn:aws:ssm:${AWS_REGION}:${AWS_ACCOUNT_ID}:parameter/medicine-recommend/staging/*"
    }
  ]
}
EOFPOL
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE" \
  --policy-name medicine-recommend-idle-stop-staging \
  --policy-document "$(aws_file_arg "$INLINE_POLICY")"
rm -f "$INLINE_POLICY"

ROLE_ARN="$(aws iam get-role --role-name "$LAMBDA_ROLE" --query Role.Arn --output text)"
sleep 8

ZIP_FILE="${HANDLER_DIR}/.lambda-idle-bundle.zip"
bundle_lambda_zip "$HANDLER_DIR" "$ZIP_FILE"
ZIP_ARG="fileb://${ZIP_FILE}"
if command -v cygpath >/dev/null 2>&1; then
  ZIP_ARG="fileb://$(cygpath -w "$ZIP_FILE")"
fi

ENV_VARS="Variables={ECS_CLUSTER=${ECS_CLUSTER},ECS_SERVICE=${ECS_SERVICE},IDLE_MINUTES=${IDLE_MINUTES},ACTIVITY_PARAM=${ACTIVITY_PARAM}}"

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

LAMBDA_ARN="$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" --query Configuration.FunctionArn --output text)"

RULE_ARN="$(aws events describe-rule --name "$RULE_NAME" --region "$AWS_REGION" --query Arn --output text 2>/dev/null || echo None)"
if [[ "$RULE_ARN" == "None" || -z "$RULE_ARN" ]]; then
  RULE_ARN="$(aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "$SCHEDULE" \
    --state ENABLED \
    --description "Idle auto-stop medicine-recommend AWS staging ECS" \
    --region "$AWS_REGION" \
    --query RuleArn --output text)"
  echo "Created EventBridge rule: $RULE_NAME"
else
  aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "$SCHEDULE" \
    --state ENABLED \
    --region "$AWS_REGION" >/dev/null
fi

aws lambda add-permission \
  --function-name "$LAMBDA_NAME" \
  --statement-id "${RULE_NAME}-invoke" \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "$RULE_ARN" \
  --region "$AWS_REGION" 2>/dev/null || true

TARGETS="$(aws events list-targets-by-rule --rule "$RULE_NAME" --region "$AWS_REGION" --query 'Targets[?Id==`idle-stop`].Arn' --output text 2>/dev/null || true)"
if [[ -z "$TARGETS" || "$TARGETS" == "None" ]]; then
  aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "Id=idle-stop,Arn=${LAMBDA_ARN}" \
    --region "$AWS_REGION" >/dev/null
  echo "Linked rule → Lambda"
fi

python3 - "$OUT_FILE" "$LAMBDA_ARN" "$RULE_ARN" "$IDLE_MINUTES" "$SCHEDULE" "$AWS_ACCOUNT_ID" "$AWS_REGION" <<'PY'
import json, sys
path, arn, rule, idle, schedule, account, region = sys.argv[1:8]
data = {
    "lambda_name": "medicine-recommend-idle-stop-staging",
    "lambda_arn": arn,
    "eventbridge_rule": rule,
    "idle_minutes": int(idle),
    "schedule": schedule,
    "staging_url": "https://aws-medicine.yutok.dev",
    "account_id": account,
    "region": region,
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(path)
PY

echo ""
echo "=== Idle auto-stop ready ==="
echo "  Lambda: ${LAMBDA_NAME}"
echo "  Schedule: ${SCHEDULE}"
echo "  Idle threshold: ${IDLE_MINUTES} minutes"
echo "  Config: scripts/.aws-idle-stop-staging.json"
