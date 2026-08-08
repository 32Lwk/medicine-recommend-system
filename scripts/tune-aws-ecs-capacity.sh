#!/usr/bin/env bash
# ECS Express: タスクサイズアップ + min 2 タスク + オートスケール
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/tune-aws-ecs-capacity.sh
#
# 上書き例:
#   ECS_CPU=1024 ECS_MEMORY=2048 ECS_MIN_TASKS=2 ECS_MAX_TASKS=10 ECS_CPU_TARGET=70 \
#     ./scripts/tune-aws-ecs-capacity.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

if is_fargate_tunnel_mode; then
  exec bash "$ROOT/scripts/tune-aws-fargate-capacity.sh" "$@"
fi

ECS_CPU="${ECS_CPU:-1024}"
ECS_MEMORY="${ECS_MEMORY:-2048}"
ECS_MIN_TASKS="${ECS_MIN_TASKS:-2}"
ECS_MAX_TASKS="${ECS_MAX_TASKS:-10}"
ECS_CPU_TARGET="${ECS_CPU_TARGET:-70}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"

SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"
SCALING_RESOURCE_ID="service/${ECS_CLUSTER}/${ECS_SERVICE}"

echo "==> Target: cpu=${ECS_CPU} memory=${ECS_MEMORY} minTasks=${ECS_MIN_TASKS} maxTasks=${ECS_MAX_TASKS} cpuTarget=${ECS_CPU_TARGET}%"
echo "==> Describe Express service: ${ECS_SERVICE}"
CURRENT_JSON="$(aws ecs describe-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION" \
  --output json)"

UPDATE_JSON="$(python3 - "$CURRENT_JSON" "$ECS_CPU" "$ECS_MEMORY" "$ECS_MIN_TASKS" "$ECS_MAX_TASKS" "$ECS_CPU_TARGET" "$GUNICORN_WORKERS" <<'PY'
import json, sys

data = json.loads(sys.argv[1])
cpu, memory = sys.argv[2], sys.argv[3]
min_tasks, max_tasks = int(sys.argv[4]), int(sys.argv[5])
cpu_target = int(float(sys.argv[6]))
gunicorn_workers = sys.argv[7]

cfg = data["service"]["activeConfigurations"][0]
primary = dict(cfg["primaryContainer"])
env_map = {e["name"]: e["value"] for e in (primary.get("environment") or []) if e.get("name")}
env_map["GUNICORN_WORKERS"] = gunicorn_workers
env_map.setdefault("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")
env_map.setdefault("GUNICORN_TIMEOUT", "300")
primary["environment"] = [{"name": k, "value": v} for k, v in sorted(env_map.items())]

out = {
    "serviceArn": data["service"]["serviceArn"],
    "primaryContainer": primary,
    "cpu": str(cpu),
    "memory": str(memory),
    "healthCheckPath": cfg.get("healthCheckPath", "/health"),
    "networkConfiguration": cfg.get("networkConfiguration"),
    "scalingTarget": {
        "minTaskCount": min_tasks,
        "maxTaskCount": max_tasks,
        "autoScalingMetric": "AVERAGE_CPU",
        "autoScalingTargetValue": cpu_target,
    },
}
print(json.dumps(out))
PY
)"

echo "==> update-express-gateway-service (cpu/memory/scaling)"
aws ecs update-express-gateway-service \
  --region "$AWS_REGION" \
  --cli-input-json "$UPDATE_JSON" \
  --query 'service.{status:status.statusCode,cpu:serviceRevisionArn}' \
  --output table

echo "==> Application Auto Scaling: MinCapacity=${ECS_MIN_TASKS}"
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id "$SCALING_RESOURCE_ID" \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity "$ECS_MIN_TASKS" \
  --max-capacity "$ECS_MAX_TASKS" \
  --region "$AWS_REGION" \
  --query '{MinCapacity:MinCapacity,MaxCapacity:MaxCapacity}' \
  --output table

echo ""
echo "Done. Wait 3-6 min for 2 tasks on ${ECS_CPU}/${ECS_MEMORY}."
echo "  aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --query 'services[0].{desired:desiredCount,running:runningCount}'"
echo "  curl -s https://aws.medicine.yutok.dev/health"
