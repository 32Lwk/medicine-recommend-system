#!/usr/bin/env bash
# ElastiCache Serverless (Redis) — ECS VPC 内
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-elasticache.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

CACHE_NAME="${REDIS_CACHE_NAME:-${PROJECT_PREFIX}-redis}"
OUT_FILE="$ROOT/scripts/.aws-redis-url"

echo "==> Resolve ECS service network"
SUBNETS=""
SGS=""
if aws ecs describe-express-gateway-service \
  --service-arn "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}" \
  --region "$AWS_REGION" >/dev/null 2>&1; then
  EXPR_JSON="$(aws ecs describe-express-gateway-service \
    --service-arn "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}" \
    --region "$AWS_REGION" --output json)"
  SUBNETS="$(python3 - "$EXPR_JSON" <<'PY'
import json, sys
cfg = json.loads(sys.argv[1])["service"]["activeConfigurations"][0]
nc = cfg.get("networkConfiguration") or {}
print("\t".join(nc.get("subnets") or []))
PY
)"
  SGS="$(python3 - "$EXPR_JSON" <<'PY'
import json, sys
cfg = json.loads(sys.argv[1])["service"]["activeConfigurations"][0]
nc = cfg.get("networkConfiguration") or {}
print("\t".join(nc.get("securityGroups") or []))
PY
)"
fi
if [[ -z "$SUBNETS" || "$SUBNETS" == "None" ]]; then
  SUBNETS="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION" \
    --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' --output text 2>/dev/null || true)"
  SGS="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION" \
    --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups' --output text 2>/dev/null || true)"
fi

if [[ -z "$SUBNETS" || "$SUBNETS" == "None" ]]; then
  echo "ERROR: ECS subnets not found. Set SUBNET_IDS manually." >&2
  exit 1
fi

SUBNET_LIST="$(echo "$SUBNETS" | tr '\t' ' ')"
SG_LIST="$(echo "$SGS" | tr '\t' ' ')"

EXISTING="$(aws elasticache describe-serverless-caches --region "$AWS_REGION" \
  --query "ServerlessCaches[?ServerlessCacheName=='${CACHE_NAME}'].ServerlessCacheName | [0]" --output text 2>/dev/null || true)"

if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  ENDPOINT="$(aws elasticache describe-serverless-caches --serverless-cache-name "$CACHE_NAME" --region "$AWS_REGION" \
    --query 'ServerlessCaches[0].Endpoint.Address' --output text)"
else
  echo "==> Create ElastiCache Serverless: ${CACHE_NAME}"
  aws elasticache create-serverless-cache \
    --serverless-cache-name "$CACHE_NAME" \
    --engine redis \
    --subnet-ids $SUBNET_LIST \
    --security-group-ids $SG_LIST \
    --region "$AWS_REGION" >/dev/null
  echo "Waiting for cache (up to 10 min)..."
  for _ in $(seq 1 60); do
    STATUS="$(aws elasticache describe-serverless-caches --serverless-cache-name "$CACHE_NAME" --region "$AWS_REGION" \
      --query 'ServerlessCaches[0].Status' --output text 2>/dev/null || true)"
    if [[ "$STATUS" == "available" ]]; then
      break
    fi
    sleep 10
  done
  ENDPOINT="$(aws elasticache describe-serverless-caches --serverless-cache-name "$CACHE_NAME" --region "$AWS_REGION" \
    --query 'ServerlessCaches[0].Endpoint.Address' --output text)"
fi

REDIS_URL="rediss://${ENDPOINT}:6379"
echo "$REDIS_URL" > "$OUT_FILE"
echo "REDIS_URL=${REDIS_URL}"
echo "Add REDIS_URL to .env and run ./scripts/setup-aws-ecs-secrets.sh .env"
