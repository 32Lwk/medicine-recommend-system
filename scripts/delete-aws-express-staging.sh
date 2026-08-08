#!/usr/bin/env bash
# Delete ECS Express Gateway service (removes attached ALB).
#
# Usage:
#   AWS_PROFILE=default ./scripts/delete-aws-express-staging.sh --confirm
#   ./scripts/delete-aws-express-staging.sh --dry-run
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

CONFIRM=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm) CONFIRM=true ;;
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
  shift
done

SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"

if ! aws ecs describe-express-gateway-service --service-arn "$SERVICE_ARN" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "Express service not found (already deleted?): ${ECS_SERVICE}"
  exit 0
fi

echo "==> ECS Express service to delete: ${ECS_SERVICE}"
aws ecs describe-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION" \
  --query 'service.{name:serviceName,status:status,endpoint:activeConfigurations[0].ingressPaths[0].endpoint}' \
  --output table

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would delete express gateway service"
  exit 0
fi

if [[ "$CONFIRM" != true ]]; then
  echo "ERROR: pass --confirm to delete Express (ALB will be removed)." >&2
  exit 1
fi

echo "==> Scaling Express to 0 before delete"
aws ecs update-express-gateway-service \
  --region "$AWS_REGION" \
  --cli-input-json "$(python3 - "$SERVICE_ARN" <<'PY'
import json, subprocess, sys, os
arn = sys.argv[1]
region = os.environ.get("AWS_REGION", "ap-northeast-1")
raw = subprocess.check_output(
    ["aws", "ecs", "describe-express-gateway-service", "--service-arn", arn, "--region", region, "--output", "json"],
    text=True,
)
data = json.loads(raw)
cfg = data["service"]["activeConfigurations"][0]
primary = dict(cfg["primaryContainer"])
out = {
    "serviceArn": data["service"]["serviceArn"],
    "primaryContainer": primary,
    "cpu": str(cfg.get("cpu") or "512"),
    "memory": str(cfg.get("memory") or "1024"),
    "healthCheckPath": cfg.get("healthCheckPath", "/health"),
    "networkConfiguration": cfg.get("networkConfiguration"),
    "scalingTarget": {"minTaskCount": 0, "maxTaskCount": 0, "autoScalingMetric": "AVERAGE_CPU", "autoScalingTargetValue": 70},
}
print(json.dumps(out))
PY
)" >/dev/null 2>&1 || true

sleep 15

echo "==> delete-express-gateway-service"
aws ecs delete-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION"

echo "Deleted. ALB removed with Express service."
echo "Next: ./scripts/setup-aws-fargate-tunnel.sh"
