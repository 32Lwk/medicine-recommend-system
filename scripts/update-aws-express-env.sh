#!/usr/bin/env bash
# ECS Express: primaryContainer.environment をマージ更新（PassRole 不要）
#
# Usage:
#   # STATIC_CDN_BASE_URL 等を .env から反映
#   ./scripts/update-aws-express-env.sh .env
#
#   # 単一変数
#   STATIC_CDN_BASE_URL=https://xxx.cloudfront.net/static ./scripts/update-aws-express-env.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ENV_FILE="${1:-}"
SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"

if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
  while IFS='=' read -r key val; do
    [[ -z "$key" ]] && continue
    export "$key=$val"
  done < <(python3 - "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
allowed = {
    "MEDICINE_IMAGE_CDN_BASE", "STATIC_CDN_BASE_URL", "TRANSLATION_PROVIDER",
    "TTS_PROVIDER", "CONCIERGE_RAG_PROVIDER", "COMPREHEND_MEDICAL_ENABLED",
    "AWS_REGION", "AWS_DEFAULT_REGION", "REDIS_URL", "PERSONALIZE_CAMPAIGN_ARN",
    "PERSONALIZE_TRACKING_ID", "BEDROCK_KB_ID", "BEDROCK_MEDICINE_KB_ID",
    "MEDICINE_RAG_PROVIDER", "BEDROCK_KB_SEARCH_MODE",
}
path = Path(sys.argv[1])
for line in path.read_text(encoding="utf-8").splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k in allowed:
        print(f"{k}={v}")
PY
  )
fi

if [[ -f "$ROOT/scripts/.aws-bedrock-kb-id" && -z "${BEDROCK_KB_ID:-}" ]]; then
  BEDROCK_KB_ID="$(tr -d '\r\n' < "$ROOT/scripts/.aws-bedrock-kb-id")"
  export BEDROCK_KB_ID
fi

if [[ -f "$ROOT/scripts/.aws-bedrock-medicine-kb-id" && -z "${BEDROCK_MEDICINE_KB_ID:-}" ]]; then
  BEDROCK_MEDICINE_KB_ID="$(tr -d '\r\n' < "$ROOT/scripts/.aws-bedrock-medicine-kb-id")"
  export BEDROCK_MEDICINE_KB_ID
fi

# Managed KB 既定（旧 Customer-managed のみ vector）
export CONCIERGE_RAG_PROVIDER="${CONCIERGE_RAG_PROVIDER:-bedrock_kb}"
export MEDICINE_RAG_PROVIDER="${MEDICINE_RAG_PROVIDER:-bedrock_kb}"
export BEDROCK_KB_SEARCH_MODE="${BEDROCK_KB_SEARCH_MODE:-managed}"

MERGE_KEYS=(
  MEDICINE_IMAGE_CDN_BASE
  STATIC_CDN_BASE_URL
  TRANSLATION_PROVIDER
  TTS_PROVIDER
  CONCIERGE_RAG_PROVIDER
  COMPREHEND_MEDICAL_ENABLED
  AWS_REGION
  AWS_DEFAULT_REGION
  REDIS_URL
  PERSONALIZE_CAMPAIGN_ARN
  PERSONALIZE_TRACKING_ID
  BEDROCK_KB_ID
  BEDROCK_MEDICINE_KB_ID
  MEDICINE_RAG_PROVIDER
  BEDROCK_KB_SEARCH_MODE
)

if [[ -f "$ROOT/scripts/.aws-static-cdn-url" && -z "${STATIC_CDN_BASE_URL:-}" ]]; then
  STATIC_CDN_BASE_URL="$(cat "$ROOT/scripts/.aws-static-cdn-url")"
fi

echo "==> Describe Express service: ${ECS_SERVICE}"
CURRENT_JSON="$(aws ecs describe-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION" \
  --output json)"

UPDATE_JSON="$(python3 - "$CURRENT_JSON" <<'PY'
import json, os, sys

data = json.loads(sys.argv[1])
cfg = data["service"]["activeConfigurations"][0]
primary = dict(cfg["primaryContainer"])
env_list = list(primary.get("environment") or [])
env_map = {e["name"]: e["value"] for e in env_list if e.get("name")}

keys = [
    "MEDICINE_IMAGE_CDN_BASE",
    "STATIC_CDN_BASE_URL",
    "TRANSLATION_PROVIDER",
    "TTS_PROVIDER",
    "CONCIERGE_RAG_PROVIDER",
    "COMPREHEND_MEDICAL_ENABLED",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "REDIS_URL",
    "PERSONALIZE_CAMPAIGN_ARN",
    "PERSONALIZE_TRACKING_ID",
    "BEDROCK_KB_ID",
    "BEDROCK_MEDICINE_KB_ID",
    "MEDICINE_RAG_PROVIDER",
    "BEDROCK_KB_SEARCH_MODE",
]
for key in keys:
    val = os.environ.get(key)
    if val:
        env_map[key] = val

if not env_map.get("MEDICINE_IMAGE_CDN_BASE"):
    env_map.setdefault("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc/")

primary["environment"] = [{"name": k, "value": v} for k, v in sorted(env_map.items())]

out = {
    "serviceArn": data["service"]["serviceArn"],
    "primaryContainer": primary,
    "cpu": cfg.get("cpu"),
    "memory": cfg.get("memory"),
    "healthCheckPath": cfg.get("healthCheckPath", "/health"),
    "networkConfiguration": cfg.get("networkConfiguration"),
    "scalingTarget": cfg.get("scalingTarget"),
}
print(json.dumps(out))
PY
)"

echo "==> update-express-gateway-service (env merge)"
aws ecs update-express-gateway-service \
  --region "$AWS_REGION" \
  --cli-input-json "$UPDATE_JSON" \
  --query 'service.{status:status.statusCode,revision:serviceRevisionArn}' \
  --output table

echo ""
echo "Done. Wait 2-4 min, then: curl -sI https://aws.medicine.yutok.dev/health"
if [[ -n "${STATIC_CDN_BASE_URL:-}" ]]; then
  echo "STATIC_CDN_BASE_URL=${STATIC_CDN_BASE_URL}"
fi
