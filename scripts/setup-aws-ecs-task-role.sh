#!/usr/bin/env bash
# ECS タスクロールに Translate / Polly / Bedrock KB 等の権限を付与し、タスク定義を更新する。
# ecsTaskExecutionRole のみだと AWS 機能 API が AccessDenied になり smoke / 本番機能が失敗する。
#
# Usage (admin IAM 推奨):
#   AWS_PROFILE=admin ./scripts/setup-aws-ecs-task-role.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="${AWS_ACCOUNT_ID:-290780119994}"
REGION="${AWS_REGION:-ap-northeast-1}"
ROLE_NAME="${ECS_TASK_ROLE_NAME:-medicine-recommend-ecs-task-role}"
TASK_FAMILY="${ECS_TASK_FAMILY:-default-medicine-recommend}"
CLUSTER="${ECS_CLUSTER:-default}"
SERVICE="${ECS_SERVICE:-medicine-recommend}"

TRUST='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ecs-tasks.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}'

POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "MedicineRecommendAwsFeatures",
    "Effect": "Allow",
    "Action": [
      "translate:TranslateText",
      "polly:SynthesizeSpeech",
      "comprehendmedical:DetectEntitiesV2",
      "bedrock:InvokeModel",
      "bedrock-agent-runtime:Retrieve"
    ],
    "Resource": "*"
  }]
}'

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "==> ECS task role: ${ROLE_NAME}"
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "    role exists"
else
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST" \
    --description "medicine-recommend ECS task role (Translate/Polly/Bedrock KB)" >/dev/null
  echo "    created role"
fi

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "${ROLE_NAME}-aws-features" \
  --policy-document "$POLICY" >/dev/null
echo "    attached inline policy ${ROLE_NAME}-aws-features"

echo "==> Register task definition with taskRoleArn=${ROLE_ARN}"
CURRENT="$(aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$REGION" --output json)"
NEW_TD="$(python3 - "$CURRENT" "$ROLE_ARN" <<'PY'
import json, sys
td = json.loads(sys.argv[1])["taskDefinition"]
role_arn = sys.argv[2]
for k in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy",
):
    td.pop(k, None)
td["taskRoleArn"] = role_arn
print(json.dumps(td))
PY
)"

NEW_ARN="$(aws ecs register-task-definition \
  --region "$REGION" \
  --cli-input-json "$NEW_TD" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"
echo "    registered ${NEW_ARN}"

echo "==> Update ECS service ${CLUSTER}/${SERVICE}"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --region "$REGION" \
  --query 'service.{taskDef:taskDefinition,status:status}' \
  --output table

echo ""
echo "Done. After tasks stabilize, verify:"
echo "  curl -X POST https://aws.medicine.yutok.dev/api/smoke/aws-translate -H 'Content-Type: application/json' -d '{}'"
