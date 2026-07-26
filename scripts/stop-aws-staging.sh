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
PREVIOUS_DESIRED="$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query 'services[0].desiredCount' \
  --output text)"

echo "==> AWS staging stop (reversible)"
echo "    cluster=$ECS_CLUSTER service=$ECS_SERVICE region=$AWS_REGION"
echo "    current desiredCount=$PREVIOUS_DESIRED"

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would: update-service --desired-count 0"
  echo "[dry-run] would: disable-stage-transition Source Outbound on $PIPELINE_NAME"
  exit 0
fi

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
    "previous_desired_count": ${PREVIOUS_DESIRED}
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
echo "Note: ALB / Managed Bedrock KB / Secrets / CodePipeline base fee still incur charges."
