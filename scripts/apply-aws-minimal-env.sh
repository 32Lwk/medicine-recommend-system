#!/usr/bin/env bash
# ECS Express を最小構成 env に戻す（AWS_FEATURES_ROLLOUT ロールバック相当）。
# Bedrock KB / ElastiCache / Personalize の env を外し、DeepL + ローカル RAG + Web Speech にする。
#
# Usage: ./scripts/apply-aws-minimal-env.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"

echo "==> Apply minimal env to ${ECS_SERVICE}"
CURRENT_JSON="$(aws ecs describe-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION" \
  --output json)"

UPDATE_JSON="$(python3 - "$CURRENT_JSON" <<'PY'
import json, sys

data = json.loads(sys.argv[1])
cfg = data["service"]["activeConfigurations"][0]
primary = dict(cfg["primaryContainer"])
env_map = {e["name"]: e["value"] for e in (primary.get("environment") or []) if e.get("name")}

env_map["TRANSLATION_PROVIDER"] = "deepl"
env_map["CONCIERGE_RAG_PROVIDER"] = "local"
env_map["MEDICINE_RAG_PROVIDER"] = "local"
env_map["TTS_PROVIDER"] = "webspeech"
env_map["COMPREHEND_MEDICAL_ENABLED"] = "false"

for key in (
    "BEDROCK_KB_ID", "BEDROCK_MEDICINE_KB_ID", "BEDROCK_KB_SEARCH_MODE",
    "REDIS_URL", "PERSONALIZE_CAMPAIGN_ARN", "PERSONALIZE_TRACKING_ID",
):
    env_map.pop(key, None)

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

aws ecs update-express-gateway-service \
  --region "$AWS_REGION" \
  --cli-input-json "$UPDATE_JSON" \
  --query 'service.{status:status.statusCode,revision:serviceRevisionArn}' \
  --output table

echo "Done. Minimal env: deepl / local RAG / webspeech (see docs/ops/AWS_FEATURES_ROLLOUT.md)"
