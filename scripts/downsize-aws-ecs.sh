#!/usr/bin/env bash
# Staging Fargate を 512 CPU / 1024 MiB に縮小（利用率が低い場合のコスト削減）。
# 元に戻す: CPU=1024 MEMORY=2048 ./scripts/downsize-aws-ecs.sh --restore
#
# Usage:
#   ./scripts/downsize-aws-ecs.sh
#   ./scripts/downsize-aws-ecs.sh --dry-run
#   CPU=1024 MEMORY=2048 ./scripts/downsize-aws-ecs.sh --restore
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

DRY_RUN=false
RESTORE=false
TARGET_CPU="${CPU:-512}"
TARGET_MEMORY="${MEMORY:-1024}"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --restore) RESTORE=true; TARGET_CPU="${CPU:-1024}"; TARGET_MEMORY="${MEMORY:-2048}" ;;
  esac
done

SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"

echo "==> ECS downsize: ${TARGET_CPU} CPU / ${TARGET_MEMORY} MiB"
CURRENT_JSON="$(aws ecs describe-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION" \
  --output json)"

CURRENT_CPU="$(python3 - "$CURRENT_JSON" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["service"]["activeConfigurations"][0]["cpu"])
PY
)"
CURRENT_MEMORY="$(python3 - "$CURRENT_JSON" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["service"]["activeConfigurations"][0]["memory"])
PY
)"

echo "    current: ${CURRENT_CPU} CPU / ${CURRENT_MEMORY} MiB"

if [[ "$CURRENT_CPU" == "$TARGET_CPU" && "$CURRENT_MEMORY" == "$TARGET_MEMORY" ]]; then
  echo "Already at target size. Nothing to do."
  exit 0
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would update express gateway to ${TARGET_CPU}/${TARGET_MEMORY}"
  exit 0
fi

UPDATE_JSON="$(python3 - "$CURRENT_JSON" "$TARGET_CPU" "$TARGET_MEMORY" <<'PY'
import json, sys

data = json.loads(sys.argv[1])
target_cpu, target_memory = sys.argv[2], sys.argv[3]
cfg = data["service"]["activeConfigurations"][0]
primary = dict(cfg["primaryContainer"])

out = {
    "serviceArn": data["service"]["serviceArn"],
    "primaryContainer": primary,
    "cpu": target_cpu,
    "memory": target_memory,
    "healthCheckPath": cfg.get("healthCheckPath", "/health"),
    "networkConfiguration": cfg.get("networkConfiguration"),
    "scalingTarget": cfg.get("scalingTarget"),
}
print(json.dumps(out))
PY
)"

aws ecs update-express-gateway-service \
  --region "$AWS_REGION" \
  --cli-input-json "$UPDATE_JSON" \
  --query 'service.{status:status.statusCode,revision:serviceRevisionArn,cpu:pendingConfigurations[0].cpu,memory:pendingConfigurations[0].memory}' \
  --output table

echo ""
echo "Done. Verify after deploy: curl -s https://aws.medicine.yutok.dev/health"
if [[ "$RESTORE" != true ]]; then
  echo "Restore: ./scripts/downsize-aws-ecs.sh --restore"
fi
