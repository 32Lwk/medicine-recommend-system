#!/usr/bin/env bash
# Reversible budget stop for AWS staging (no resource deletion).
#
# Stops:
#   - ECS Fargate tasks (desiredCount -> 0)
#   - CodePipeline auto-deploy (Source -> Build transition disabled)
#
# Does NOT delete: ALB, WAF, Bedrock KB, Secrets, S3, ECR, etc.
#
# Usage:
#   ./scripts/stop-aws-staging.sh
#   ./scripts/stop-aws-staging.sh --dry-run
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

STATE_FILE="$ROOT/scripts/.aws-staging-stop-state.json"
PIPELINE_NAME="${PIPELINE_NAME:-medicine-recommend-main}"
SCALING_RESOURCE_ID="service/${ECS_CLUSTER}/${ECS_SERVICE}"
PREVIOUS_DESIRED="$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query 'services[0].desiredCount' \
  --output text)"
read -r PREVIOUS_MIN PREVIOUS_MAX <<<"$(aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids "$SCALING_RESOURCE_ID" \
  --region "$AWS_REGION" \
  --query 'ScalableTargets[0].[MinCapacity,MaxCapacity]' \
  --output text 2>/dev/null || echo "1 1")"
PREVIOUS_MIN="${PREVIOUS_MIN:-1}"
PREVIOUS_MAX="${PREVIOUS_MAX:-1}"

echo "==> AWS staging stop (reversible)"
echo "    cluster=$ECS_CLUSTER service=$ECS_SERVICE region=$AWS_REGION"
echo "    current desiredCount=$PREVIOUS_DESIRED"

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would: register-scalable-target min=0 max=0"
  echo "[dry-run] would: update-service --desired-count 0"
  echo "[dry-run] would: disable-stage-transition Source Outbound on $PIPELINE_NAME"
  exit 0
fi

echo "==> Application Auto Scaling: MinCapacity=0 (prevent scale-up while stopped)"
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id "$SCALING_RESOURCE_ID" \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 0 \
  --max-capacity 0 \
  --region "$AWS_REGION" \
  --query '{MinCapacity:MinCapacity,MaxCapacity:MaxCapacity}' \
  --output table

aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --desired-count 0 \
  --region "$AWS_REGION" \
  --query 'service.{desired:desiredCount,running:runningCount}' \
  --output json

REASON="Budget stop (reversible) - $(date -u +%Y-%m-%dT%H:%MZ)"
aws codepipeline disable-stage-transition \
  --pipeline-name "$PIPELINE_NAME" \
  --stage-name Source \
  --transition-type Outbound \
  --reason "$REASON" \
  --region "$AWS_REGION"

cat > "$STATE_FILE" <<EOF
{
  "stopped_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": "Budget stop (reversible)",
  "ecs": {
    "cluster": "${ECS_CLUSTER}",
    "service": "${ECS_SERVICE}",
    "previous_desired_count": ${PREVIOUS_DESIRED},
    "previous_min_capacity": ${PREVIOUS_MIN},
    "previous_max_capacity": ${PREVIOUS_MAX}
  },
  "codepipeline": {
    "name": "${PIPELINE_NAME}",
    "disabled_transition": {
      "stage": "Source",
      "transition_type": "Outbound",
      "reason": "${REASON}"
    }
  }
}
EOF

echo ""
echo "Stopped. State saved: scripts/.aws-staging-stop-state.json"
echo "Resume: ./scripts/resume-aws-staging.sh"
echo ""
echo "Note: URL returns 503 until resume (ALB has no healthy targets)."
echo "Note: ALB / Secrets / CodePipeline base fee still incur charges."
