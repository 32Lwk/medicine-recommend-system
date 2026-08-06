#!/usr/bin/env bash
# 新アカウント向け「コールドスタート」運用の初期設定。
#
# - Fargate 最小スペック（512/1024, maxTasks=1）
# - CloudWatch Logs 保持 7 日
# - ECS desiredCount=0 + CodePipeline 自動デプロイ停止（停止がデフォルト）
#
# 利用時: ./scripts/resume-aws-staging.sh  → 3–6 分で /health 200
# 停止時: ./scripts/stop-aws-staging.sh
#
# Usage:
#   AWS_PROFILE=default ./scripts/setup-aws-staging-cold-start.sh
#   AWS_PROFILE=default ./scripts/setup-aws-staging-cold-start.sh --keep-running
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

KEEP_RUNNING=false
[[ "${1:-}" == "--keep-running" ]] && KEEP_RUNNING=true

LOG_GROUP="/ecs/${PROJECT_PREFIX}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-7}"

echo "==> AWS staging cold-start setup (account=${AWS_ACCOUNT_ID})"
echo "    spec: 512 CPU / 1024 MiB, minTasks=1 maxTasks=1, workers=1"
echo "    logs: ${LOG_GROUP} retention=${LOG_RETENTION_DAYS}d"

echo "==> Tune ECS Express to minimal capacity"
ECS_CPU=512 \
ECS_MEMORY=1024 \
ECS_MIN_TASKS=1 \
ECS_MAX_TASKS=1 \
ECS_CPU_TARGET=70 \
GUNICORN_WORKERS=1 \
  bash "$ROOT/scripts/tune-aws-ecs-capacity.sh"

echo "==> CloudWatch Logs retention"
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName" --output text | grep -q "$LOG_GROUP"; then
  aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP" \
    --retention-in-days "$LOG_RETENTION_DAYS" \
    --region "$AWS_REGION"
  echo "    ${LOG_GROUP} -> ${LOG_RETENTION_DAYS} days"
else
  echo "    skip (log group not found: ${LOG_GROUP})"
fi

for extra in "/aws/codebuild/${PROJECT_PREFIX}-build" "/aws/lambda/medicine-recommend-budget-action"; do
  if aws logs describe-log-groups --log-group-name-prefix "$extra" --region "$AWS_REGION" \
    --query "logGroups[?logGroupName=='${extra}'].logGroupName" --output text 2>/dev/null | grep -q "$extra"; then
    aws logs put-retention-policy \
      --log-group-name "$extra" \
      --retention-in-days "$LOG_RETENTION_DAYS" \
      --region "$AWS_REGION" 2>/dev/null || true
    echo "    ${extra} -> ${LOG_RETENTION_DAYS} days"
  fi
done

if [[ "$KEEP_RUNNING" == true ]]; then
  echo "==> --keep-running: skip stop-aws-staging.sh"
  echo "    Resume manually if needed: ./scripts/resume-aws-staging.sh"
else
  echo "==> Default to stopped (cold)"
  bash "$ROOT/scripts/stop-aws-staging.sh"
fi

cat > "$ROOT/scripts/.aws-staging-cold-start.json" <<EOF
{
  "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "account_id": "${AWS_ACCOUNT_ID}",
  "ecs": {
    "cpu": 512,
    "memory": 1024,
    "min_tasks": 1,
    "max_tasks": 1,
    "gunicorn_workers": 1,
    "default_desired_count": 0
  },
  "logs_retention_days": ${LOG_RETENTION_DAYS},
  "resume": "./scripts/resume-aws-staging.sh",
  "stop": "./scripts/stop-aws-staging.sh"
}
EOF

echo ""
echo "=== Cold-start ready ==="
echo "  State: scripts/.aws-staging-cold-start.json"
echo "  Start: ./scripts/resume-aws-staging.sh   (wait 3–6 min for /health)"
echo "  Stop:  ./scripts/stop-aws-staging.sh"
