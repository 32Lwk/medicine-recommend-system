#!/usr/bin/env bash
# Fargate tunnel: tune CPU/memory/scaling via new task definition revision.
#
# Usage:
#   ECS_CPU=512 ECS_MEMORY=1024 ECS_MIN_TASKS=1 ECS_MAX_TASKS=1 GUNICORN_WORKERS=1 \
#     ./scripts/tune-aws-fargate-capacity.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ECS_CPU="${ECS_CPU:-512}"
ECS_MEMORY="${ECS_MEMORY:-1024}"
ECS_MIN_TASKS="${ECS_MIN_TASKS:-1}"
ECS_MAX_TASKS="${ECS_MAX_TASKS:-1}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
TASK_FAMILY="${FARGATE_TASK_FAMILY:-medicine-recommend-tunnel}"
SCALING_RESOURCE_ID="service/${ECS_CLUSTER}/${ECS_SERVICE}"

echo "==> Fargate tunnel tune: cpu=${ECS_CPU} memory=${ECS_MEMORY} min=${ECS_MIN_TASKS} max=${ECS_MAX_TASKS}"

CURRENT_JSON="$(aws ecs describe-task-definition \
  --task-definition "$TASK_FAMILY" \
  --region "$AWS_REGION" \
  --output json)"

NEW_TD="$(python3 - "$CURRENT_JSON" "$ECS_CPU" "$ECS_MEMORY" "$GUNICORN_WORKERS" <<'PY'
import json, sys

current = json.loads(sys.argv[1])
cpu, memory, workers = sys.argv[2], sys.argv[3], sys.argv[4]
td = current["taskDefinition"]
for k in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy",
):
    td.pop(k, None)
td["cpu"] = str(cpu)
td["memory"] = str(memory)
for c in td.get("containerDefinitions") or []:
    if c.get("name") != "app":
        continue
    env_map = {e["name"]: e["value"] for e in (c.get("environment") or []) if e.get("name")}
    env_map["GUNICORN_WORKERS"] = workers
    env_map.setdefault("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")
    env_map.setdefault("GUNICORN_TIMEOUT", "300")
    c["environment"] = [{"name": k, "value": v} for k, v in sorted(env_map.items())]
print(json.dumps(td))
PY
)"

TMP="$(mktemp)"
printf '%s' "$NEW_TD" > "$TMP"
NEW_ARN="$(aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --cli-input-json "$(aws_file_arg "$TMP")" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"
rm -f "$TMP"

aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --query 'service.{taskDef:taskDefinition,desired:desiredCount}' \
  --output table

aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id "$SCALING_RESOURCE_ID" \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity "$ECS_MIN_TASKS" \
  --max-capacity "$ECS_MAX_TASKS" \
  --region "$AWS_REGION" \
  --output table

echo "Done. taskDefinition=${NEW_ARN}"
