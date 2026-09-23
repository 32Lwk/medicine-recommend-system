#!/usr/bin/env bash
# R21 staging shadow-only flags (D2 stays OFF; PRIMARY stays OFF).
# Usage:
#   AWS_PROFILE=default ./scripts/r21_staging_shadow_flags.sh on
#   AWS_PROFILE=default ./scripts/r21_staging_shadow_flags.sh off
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

MODE="${1:-}"
if [[ "$MODE" != "on" && "$MODE" != "off" ]]; then
  echo "Usage: $0 on|off" >&2
  exit 2
fi

export AWS_PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-ap-northeast-1}"
CLUSTER="${ECS_CLUSTER:-default}"
SERVICE="${ECS_SERVICE:-medicine-recommend}"
FAMILY="${FARGATE_TASK_FAMILY:-medicine-recommend-tunnel}"

if [[ "$MODE" == "on" ]]; then
  JEV_ENABLED=1
  JEV_SHADOW=1
else
  JEV_ENABLED=0
  JEV_SHADOW=0
fi
# Hard-locked for R21 canary contract
JEV_PRIMARY=0
D2=0

echo "==> R21 shadow flags mode=${MODE} ENABLED=${JEV_ENABLED} SHADOW=${JEV_SHADOW} PRIMARY=0 D2=0"
CURRENT="$(aws ecs describe-task-definition --task-definition "$FAMILY" --region "$REGION" --output json)"
NEW_JSON="$(python - "$CURRENT" "$JEV_ENABLED" "$JEV_SHADOW" "$JEV_PRIMARY" "$D2" <<'PY'
import json, sys
td = json.loads(sys.argv[1])["taskDefinition"]
for k in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy",
):
    td.pop(k, None)
want = {
    "JEV_ENABLED": sys.argv[2],
    "JEV_INTENT_ROUTER_SHADOW": sys.argv[3],
    "JEV_INTENT_ROUTER_PRIMARY": sys.argv[4],
    "POLICY_ENFORCEMENT_D2": sys.argv[5],
}
for c in td.get("containerDefinitions") or []:
    if c.get("name") != "app":
        continue
    env = {e["name"]: e["value"] for e in (c.get("environment") or [])}
    env.update(want)
    c["environment"] = [{"name": k, "value": str(v)} for k, v in sorted(env.items())]
print(json.dumps(td))
PY
)"

NEW_ARN="$(aws ecs register-task-definition --region "$REGION" --cli-input-json "$NEW_JSON" --query 'taskDefinition.taskDefinitionArn' --output text)"
echo "Registered: ${NEW_ARN}"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --region "$REGION" \
  --query 'service.{taskDef:taskDefinition,desired:desiredCount,status:status}' \
  --output json
echo "Done."
