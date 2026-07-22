#!/usr/bin/env bash
# ECS Express / CodeBuild のデプロイ・ランタイム待ち時間を短縮するワンショット調整。
#
# 主なボトルネック（2026-07-22 調査）:
#   - ECS Express CANARY bakeTime 3+3 分 → push から反映まで 6〜8 分
#   - CodeBuild NO_CACHE → Docker ビルド ~2 分/回
#   - GUNICORN_WORKERS=1 → 同時リクエスト 1 本のみ
#
# Usage:
#   export AWS_PROFILE=admin
#   ./scripts/tune-aws-ecs-performance.sh
#
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-1}"
CLUSTER="${ECS_CLUSTER:-default}"
SERVICE="${ECS_SERVICE:-medicine-recommend}"
TASK_FAMILY="${ECS_TASK_FAMILY:-default-medicine-recommend}"
BUILD_PROJECT="${CODEBUILD_PROJECT:-medicine-recommend-build}"

echo "==> ECS: shorten CANARY bake (Express Gateway は ROLLING 不可)"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --region "$REGION" \
  --deployment-configuration '{"maximumPercent":200,"minimumHealthyPercent":100,"strategy":"CANARY","bakeTimeInMinutes":0,"canaryConfiguration":{"canaryPercent":5.0,"canaryBakeTimeInMinutes":0}}' \
  --query 'service.deploymentConfiguration.{strategy:strategy,bake:bakeTimeInMinutes,canary:canaryConfiguration}' \
  --output table

echo "==> ECS: GUNICORN_WORKERS=2 in task definition"
CURRENT="$(aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$REGION" --output json)"
NEW_TD=$(python3 - "$CURRENT" <<'PY'
import json, sys
td = json.loads(sys.argv[1])["taskDefinition"]
for k in ("taskDefinitionArn", "revision", "status", "requiresAttributes", "compatibilities", "registeredAt", "registeredBy"):
    td.pop(k, None)
c = td["containerDefinitions"][0]
env = {e["name"]: e["value"] for e in c.get("environment") or []}
env["GUNICORN_WORKERS"] = "2"
env.setdefault("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")
env.setdefault("GUNICORN_TIMEOUT", "300")
c["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
print(json.dumps(td))
PY
)
NEW_ARN="$(aws ecs register-task-definition --region "$REGION" --cli-input-json "$NEW_TD" --query 'taskDefinition.taskDefinitionArn' --output text)"
echo "Registered: ${NEW_ARN}"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --region "$REGION" \
  --query 'service.serviceName' \
  --output text

echo "==> CodeBuild: enable local Docker layer cache"
aws codebuild update-project \
  --name "$BUILD_PROJECT" \
  --region "$REGION" \
  --cache '{"type":"LOCAL","modes":["LOCAL_DOCKER_LAYER_CACHE","LOCAL_SOURCE_CACHE"]}' \
  --query 'project.cache' \
  --output json

echo ""
echo "Done. buildspec.yml の BuildKit + cache-from も main に merge 済みであること。"
echo "  curl https://aws.medicine.yutok.dev/health"
