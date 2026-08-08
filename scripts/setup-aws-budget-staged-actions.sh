#!/usr/bin/env bash
# AWS Budgets 段階的コスト削減: SNS トピック + Lambda + IAM を一括作成。
#
# 予算アラート（コンソール）から各 SNS トピック ARN を指定すると、
# しきい値超過時に Lambda が段階的に ECS 縮小・env 最小化・停止を実行する。
#
# Usage:
#   ./scripts/setup-aws-budget-staged-actions.sh
#   ./scripts/setup-aws-budget-staged-actions.sh --dry-run
#
# 作成後: docs/ops/AWS_BUDGET_STAGED_ACTIONS.md の「予算コンソール設定」を参照。
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

LAMBDA_NAME="${LAMBDA_NAME:-medicine-recommend-budget-action}"
LAMBDA_ROLE="${LAMBDA_ROLE:-medicine-recommend-budget-action-role}"
HANDLER_DIR="$ROOT/scripts/lambda/budget_staged_action"
BUILD_PROJECT="${BUILD_PROJECT:-medicine-recommend-build}"
PIPELINE_NAME="${PIPELINE_NAME:-medicine-recommend-main}"
LOG_GROUP="/ecs/${PROJECT_PREFIX}"

STAGES=(stage1 stage2 stage3 stage4 stage5)
STAGE_LABELS=(
  "60% 予測 — Fargate 512/1024"
  "75% 実際 — minimal env"
  "80% 実際 — KB sync 停止 + log 7日"
  "90% 実際 — ECS 停止 + Pipeline 停止"
  "100% 実際 — 同上（再実行可）"
)

echo "==> AWS Budget staged actions"
echo "    account=$AWS_ACCOUNT_ID region=$AWS_REGION lambda=$LAMBDA_NAME"

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would create IAM role, 5 SNS topics, Lambda, subscriptions"
  exit 0
fi

# --- IAM role for Lambda ---
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
    --description "medicine-recommend budget staged cost actions"
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
        "ecs:DescribeExpressGatewayService",
        "ecs:UpdateExpressGatewayService",
        "ecs:DescribeServices",
        "ecs:UpdateService",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codepipeline:DisableStageTransition",
        "codepipeline:EnableStageTransition"
      ],
      "Resource": [
        "arn:aws:codepipeline:${AWS_REGION}:${AWS_ACCOUNT_ID}:${PIPELINE_NAME}",
        "arn:aws:codepipeline:${AWS_REGION}:${AWS_ACCOUNT_ID}:${PIPELINE_NAME}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "codebuild:BatchGetProjects",
        "codebuild:UpdateProject"
      ],
      "Resource": "arn:aws:codebuild:${AWS_REGION}:${AWS_ACCOUNT_ID}:project/${BUILD_PROJECT}"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:PutRetentionPolicy"],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"
    }
  ]
}
EOFPOL
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE" \
  --policy-name medicine-recommend-budget-action \
  --policy-document "$(aws_file_arg "$INLINE_POLICY")"
rm -f "$INLINE_POLICY"
echo "Attached inline policy medicine-recommend-budget-action"

ROLE_ARN="$(aws iam get-role --role-name "$LAMBDA_ROLE" --query Role.Arn --output text)"
echo "    role_arn=$ROLE_ARN"
sleep 10

# --- SNS topics (one per stage) ---
TOPIC_ARNS_FILE="$(mktemp)"
: > "$TOPIC_ARNS_FILE"
for i in "${!STAGES[@]}"; do
  stage="${STAGES[$i]}"
  topic_name="medicine-recommend-budget-${stage}"
  topic_arn="arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${topic_name}"

  if aws sns get-topic-attributes --topic-arn "$topic_arn" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "SNS topic exists: $topic_name"
  else
    topic_arn="$(aws sns create-topic \
      --name "$topic_name" \
      --region "$AWS_REGION" \
      --query TopicArn --output text)"
    echo "Created SNS topic: $topic_name"
  fi

  SNS_POLICY="$(mktemp)"
  cat > "$SNS_POLICY" <<EOFSNS
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "budgets.amazonaws.com"},
    "Action": "SNS:Publish",
    "Resource": "${topic_arn}",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "${AWS_ACCOUNT_ID}"}
    }
  }]
}
EOFSNS
  aws sns set-topic-attributes \
    --topic-arn "$topic_arn" \
    --attribute-name Policy \
    --attribute-value "$(cat "$SNS_POLICY")" \
    --region "$AWS_REGION"
  rm -f "$SNS_POLICY"

  echo "${stage}=${topic_arn}" >> "$TOPIC_ARNS_FILE"
done

topic_arn_for_stage() {
  local stage="$1"
  grep "^${stage}=" "$TOPIC_ARNS_FILE" | cut -d= -f2-
}

# --- Lambda package ---
ZIP_FILE="${HANDLER_DIR}/.lambda-budget-bundle.zip"
PY_HANDLER="$(to_win_path "$HANDLER_DIR")"
PY_ZIP="$(to_win_path "$ZIP_FILE")"
python3 - "$PY_HANDLER" "$PY_ZIP" <<'PY'
import sys, zipfile
from pathlib import Path
handler_dir = Path(sys.argv[1])
zip_path = Path(sys.argv[2])
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(handler_dir / "handler.py", "handler.py")
PY
ZIP_ARG="fileb://${ZIP_FILE}"
if command -v cygpath >/dev/null 2>&1; then
  ZIP_ARG="fileb://$(cygpath -w "$ZIP_FILE")"
fi

LAMBDA_ENV="Variables={AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID},ECS_CLUSTER=${ECS_CLUSTER},ECS_SERVICE=${ECS_SERVICE},PROJECT_PREFIX=${PROJECT_PREFIX},PIPELINE_NAME=${PIPELINE_NAME},BUILD_PROJECT=${BUILD_PROJECT},LOG_GROUP=${LOG_GROUP}"
if [[ -f "$ROOT/scripts/.aws-fargate-tunnel.json" ]] || [[ "$(cat "$ROOT/scripts/.aws-deploy-mode" 2>/dev/null)" == "fargate_tunnel" ]]; then
  LAMBDA_ENV="${LAMBDA_ENV},ECS_DEPLOY_MODE=fargate_tunnel,FARGATE_TASK_FAMILY=${FARGATE_TASK_FAMILY:-medicine-recommend-tunnel}"
fi
LAMBDA_ENV="${LAMBDA_ENV}}"

if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file "$ZIP_ARG" \
    --region "$AWS_REGION" \
    --query 'FunctionArn' --output text >/dev/null
  for attempt in 1 2 3 4 5 6; do
    if aws lambda update-function-configuration \
      --function-name "$LAMBDA_NAME" \
      --environment "$LAMBDA_ENV" \
      --timeout 120 \
      --region "$AWS_REGION" >/dev/null 2>&1; then
      break
    fi
    if (( attempt == 6 )); then
      echo "WARN: update-function-configuration skipped (update in progress)" >&2
    else
      sleep 5
    fi
  done
  echo "Updated Lambda: $LAMBDA_NAME"
else
  aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.12 \
    --role "$ROLE_ARN" \
    --handler handler.lambda_handler \
    --zip-file "$ZIP_ARG" \
    --timeout 120 \
    --environment "$LAMBDA_ENV" \
    --region "$AWS_REGION" \
    --query 'FunctionArn' --output text >/dev/null
  echo "Created Lambda: $LAMBDA_NAME"
fi
rm -f "$ZIP_FILE"

LAMBDA_ARN="$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" --query Configuration.FunctionArn --output text)"

# --- SNS → Lambda subscriptions ---
for stage in "${STAGES[@]}"; do
  topic_arn="$(topic_arn_for_stage "$stage")"
  existing="$(aws sns list-subscriptions-by-topic \
    --topic-arn "$topic_arn" \
    --region "$AWS_REGION" \
    --query "Subscriptions[?Endpoint=='${LAMBDA_ARN}'].SubscriptionArn | [0]" \
    --output text 2>/dev/null || echo None)"

  if [[ "$existing" != "None" && "$existing" != pending:* ]]; then
    echo "Subscription exists: $stage"
  else
    aws sns subscribe \
      --topic-arn "$topic_arn" \
      --protocol lambda \
      --notification-endpoint "$LAMBDA_ARN" \
      --region "$AWS_REGION" >/dev/null
    echo "Subscribed Lambda to $stage"
  fi

  aws lambda add-permission \
    --function-name "$LAMBDA_NAME" \
    --statement-id "sns-${stage}" \
    --action lambda:InvokeFunction \
    --principal sns.amazonaws.com \
    --source-arn "$topic_arn" \
    --region "$AWS_REGION" \
    2>/dev/null || true
done

# --- Output for console setup ---
OUT_FILE="$ROOT/scripts/.aws-budget-staged-actions.json"
PY_OUT="$(to_win_path "$OUT_FILE")"
python3 - "$PY_OUT" "$LAMBDA_ARN" "$AWS_ACCOUNT_ID" "$AWS_REGION" "${STAGES[@]}" <<'PY'
import json, sys

out_file = sys.argv[1]
lambda_arn = sys.argv[2]
account = sys.argv[3]
region = sys.argv[4]
stages = sys.argv[5:]

labels = {
    "stage1": {"threshold": "60%", "type": "予測", "actions": "Fargate 512/1024"},
    "stage2": {"threshold": "75%", "type": "実際", "actions": "minimal env"},
    "stage3": {"threshold": "80%", "type": "実際", "actions": "KB sync 停止 + log 7日"},
    "stage4": {"threshold": "90%", "type": "実際", "actions": "ECS 停止 + Pipeline 停止"},
    "stage5": {"threshold": "100%", "type": "実際", "actions": "同上"},
}

data = {
    "lambda_arn": lambda_arn,
    "lambda_name": "medicine-recommend-budget-action",
    "stages": {
        s: {
            "sns_topic_arn": f"arn:aws:sns:{region}:{account}:medicine-recommend-budget-{s}",
            **labels[s],
        }
        for s in stages
    },
    "email_only_alerts": [
        {"alert": 1, "threshold": "50%", "type": "実際", "note": "通知のみ — SNS 不要"},
        {"alert": 2, "threshold": "60%", "type": "予測", "note": "stage1 SNS を設定"},
    ],
}
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(out_file)
PY

echo ""
echo "==> Done. Topic ARNs for Budget console:"
for i in "${!STAGES[@]}"; do
  stage="${STAGES[$i]}"
  echo "  Alert #$((i + 2)) (${STAGE_LABELS[$i]})"
  echo "    $(topic_arn_for_stage "$stage")"
done
rm -f "$TOPIC_ARNS_FILE"
echo ""
echo "Config saved: scripts/.aws-budget-staged-actions.json"
echo "Next: docs/ops/AWS_BUDGET_STAGED_ACTIONS.md"
