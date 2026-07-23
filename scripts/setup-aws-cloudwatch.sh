#!/usr/bin/env bash
# CloudWatch Logs（ECS awslogs）+ アラーム
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-cloudwatch.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

LOG_GROUP="/ecs/${PROJECT_PREFIX}"
RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"
PIPELINE_NAME="${PIPELINE_NAME:-medicine-recommend-main}"

echo "==> CloudWatch Log Group: ${LOG_GROUP}"
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName" --output text | grep -q "$LOG_GROUP"; then
  echo "Log group exists"
else
  aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$AWS_REGION"
  echo "Created log group"
fi
aws logs put-retention-policy \
  --log-group-name "$LOG_GROUP" \
  --retention-in-days "$RETENTION_DAYS" \
  --region "$AWS_REGION"

if [[ "${SKIP_ECS_TD_UPDATE:-false}" == "true" ]]; then
  echo "==> SKIP_ECS_TD_UPDATE=true — skipping ECS task definition / service update"
else
echo "==> ECS task definition: enable awslogs driver"
CURRENT="$(aws ecs describe-task-definition --task-definition "$ECS_TASK_FAMILY" --region "$AWS_REGION" --output json)"
NEW_TD=$(python3 - "$CURRENT" "$LOG_GROUP" "$AWS_REGION" <<'PY'
import json, sys
td = json.loads(sys.argv[1])["taskDefinition"]
for k in ("taskDefinitionArn", "revision", "status", "requiresAttributes", "compatibilities", "registeredAt", "registeredBy"):
    td.pop(k, None)
c = td["containerDefinitions"][0]
c["logConfiguration"] = {
    "logDriver": "awslogs",
    "options": {
        "awslogs-group": sys.argv[2],
        "awslogs-region": sys.argv[3],
        "awslogs-stream-prefix": "ecs",
    },
}
print(json.dumps(td))
PY
)
NEW_ARN="$(aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$NEW_TD" --query 'taskDefinition.taskDefinitionArn' --output text)"
echo "Registered: ${NEW_ARN}"
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --query 'service.serviceName' \
  --output text
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
SNS_TOPIC="${ALARM_SNS_TOPIC_ARN:-}"

alarm_actions=()
if [[ -n "$SNS_TOPIC" ]]; then
  alarm_actions=(--alarm-actions "$SNS_TOPIC")
fi

echo "==> Alarm: ECS CPU high"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_PREFIX}-ecs-cpu-high" \
  --alarm-description "ECS service CPU > 80% for 5 min" \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions "Name=ClusterName,Value=${ECS_CLUSTER}" "Name=ServiceName,Value=${ECS_SERVICE}" \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  "${alarm_actions[@]}" \
  --region "$AWS_REGION"

TG_ARN="$(resolve_target_group_arn)"
if [[ -n "$TG_ARN" && "$TG_ARN" != "None" ]]; then
  TG_DIM="${TG_ARN#*:targetgroup/}"
  TG_DIM="targetgroup/${TG_DIM}"
  echo "==> Alarm: Target 5xx (${TG_DIM})"
  aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_PREFIX}-tg-5xx" \
    --alarm-description "ALB target 5xx count" \
    --namespace AWS/ApplicationELB \
    --metric-name HTTPCode_Target_5XX_Count \
    --dimensions "Name=TargetGroup,Value=${TG_DIM}" \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --treat-missing-data notBreaching \
    "${alarm_actions[@]}" \
    --region "$AWS_REGION" 2>/dev/null || echo "WARN: TG 5xx alarm skipped"
fi

echo "==> Alarm: CodePipeline failure"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_PREFIX}-pipeline-failed" \
  --alarm-description "CodePipeline execution failed" \
  --namespace AWS/CodePipeline \
  --metric-name PipelineExecutionFailure \
  --dimensions "Name=PipelineName,Value=${PIPELINE_NAME}" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  "${alarm_actions[@]}" \
  --region "$AWS_REGION" 2>/dev/null || echo "WARN: Pipeline alarm skipped"

echo ""
echo "Done. Log group: ${LOG_GROUP} (retention ${RETENTION_DAYS}d)"
echo "Optional: export ALARM_SNS_TOPIC_ARN=arn:aws:sns:... and re-run for notifications"
