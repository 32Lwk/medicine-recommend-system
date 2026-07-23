#!/usr/bin/env bash
# ECS Express: Secrets Manager + primaryContainer.secrets へ移行
#
# .env は bash source 不可の行があるため Python で読み込み。
# シークレットは ECS 既存 env を優先（.env の localhost DATABASE_URL 等を上書きしない）。
#
# Usage:
#   ./scripts/setup-aws-express-secrets.sh .env
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ENV_FILE="${1:-.env}"
SECRET_PREFIX="${SECRET_PREFIX:-medicine-recommend/aws-staging}"
SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"
export AWS_CLI="$(command -v aws)"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

echo "==> Fetch current ECS Express configuration"
CURRENT_JSON="$(aws ecs describe-express-gateway-service \
  --service-arn "$SERVICE_ARN" \
  --region "$AWS_REGION" \
  --output json)"

# Merge .env (whitelisted) + ECS env; ECS wins for secret keys when .env looks local/dev
MERGE_JSON="$(python3 - "$ENV_FILE" "$CURRENT_JSON" <<'PY'
import json, os, sys, secrets
from pathlib import Path

env_file = Path(sys.argv[1])
ecs = json.loads(sys.argv[2])
cfg = ecs["service"]["activeConfigurations"][0]
ecs_map = {
    e["name"]: e["value"]
    for e in (cfg["primaryContainer"].get("environment") or [])
    if e.get("name")
}

allowed_env = {
    "MEDICINE_IMAGE_CDN_BASE", "STATIC_CDN_BASE_URL",
    "TRANSLATION_PROVIDER", "TTS_PROVIDER", "CONCIERGE_RAG_PROVIDER",
    "COMPREHEND_MEDICAL_ENABLED", "AWS_REGION", "AWS_DEFAULT_REGION",
    "REDIS_URL", "PERSONALIZE_CAMPAIGN_ARN", "PERSONALIZE_TRACKING_ID", "BEDROCK_KB_ID",
    "R2_S3_ENDPOINT",
}
file_map = {}
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in allowed_env:
            file_map[k] = v

secret_keys = [
    "OPENAI_API_KEY", "DATABASE_URL", "SECRET_KEY", "ADMIN_PASSWORD",
    "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "DEEPL_API_KEY",
    "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET",
]
secrets_out = {}
for sk in secret_keys:
    val = file_map.pop(sk, None) or ecs_map.get(sk) or os.environ.get(sk)
    if sk == "DATABASE_URL" and val and ("localhost" in val or "127.0.0.1" in val):
        val = ecs_map.get(sk) or val
    if sk in ("ADMIN_PASSWORD", "LINE_CHANNEL_SECRET") and not val:
        continue
    if sk == "SECRET_KEY" and not val:
        val = ecs_map.get(sk) or secrets.token_hex(32)
    secrets_out[sk] = val or ""

missing = [k for k in ("OPENAI_API_KEY", "DATABASE_URL", "SECRET_KEY") if not secrets_out.get(k)]
if missing:
    print(f"ERROR: missing required secrets: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

# Non-secret env: ECS base, overlay whitelisted .env
env_map = dict(ecs_map)
garbage = {"medicine-recommend-db", "postgres"}
for g in garbage:
    env_map.pop(g, None)
for sk in secret_keys:
    env_map.pop(sk, None)
env_map.update({k: v for k, v in file_map.items() if v})

env_map.setdefault("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc/")
env_map.setdefault("APP_ENV", "production")
env_map.setdefault("PUBLIC_SITE_URL", "https://aws.medicine.yutok.dev")

print(json.dumps({"secrets": secrets_out, "environment": env_map}))
PY
)"

echo "==> Upsert Secrets Manager"
SECRET_ARNS="$(python3 - "$MERGE_JSON" "$SECRET_PREFIX" "$AWS_REGION" <<'PY'
import json, os, subprocess, sys

data = json.loads(sys.argv[1])
prefix, region = sys.argv[2], sys.argv[3]
aws = os.environ.get("AWS_CLI", "aws")

slug = {
    "OPENAI_API_KEY": "openai-api-key",
    "DATABASE_URL": "database-url",
    "SECRET_KEY": "secret-key",
    "ADMIN_PASSWORD": "admin-password",
    "R2_ACCESS_KEY_ID": "r2-access-key-id",
    "R2_SECRET_ACCESS_KEY": "r2-secret-access-key",
    "DEEPL_API_KEY": "deepl-api-key",
    "LINE_CHANNEL_ACCESS_TOKEN": "line-channel-access-token",
    "LINE_CHANNEL_SECRET": "line-channel-secret",
}

def run(args):
    p = subprocess.run(args, capture_output=True, text=True, env=os.environ)
    if p.returncode != 0:
        raise RuntimeError(f"aws failed ({p.returncode}): {' '.join(args)}\n{p.stderr}")
    return p.stdout.strip()

def put(name, value):
    full = f"{prefix}/{name}"
    try:
        run([aws, "secretsmanager", "describe-secret", "--secret-id", full, "--region", region])
        run([aws, "secretsmanager", "put-secret-value", "--secret-id", full,
             "--secret-string", value, "--region", region])
    except RuntimeError:
        run([aws, "secretsmanager", "create-secret", "--name", full,
             "--secret-string", value, "--region", region])
    return run([aws, "secretsmanager", "describe-secret", "--secret-id", full,
                "--region", region, "--query", "ARN", "--output", "text"])

arns = {}
for k, v in data["secrets"].items():
    if not v or k not in slug:
        continue
    arns[k] = put(slug[k], v)
print(json.dumps({"secretArns": arns, "environment": data["environment"]}))
PY
)"

echo "==> update-express-gateway-service (secrets + env merge)"
UPDATE_JSON="$(python3 - "$CURRENT_JSON" "$SECRET_ARNS" <<'PY'
import json, sys

data = json.loads(sys.argv[1])
merge = json.loads(sys.argv[2])
cfg = data["service"]["activeConfigurations"][0]
primary = dict(cfg["primaryContainer"])

secret_arns = merge["secretArns"]
primary["environment"] = [
    {"name": k, "value": v} for k, v in sorted(merge["environment"].items())
]
primary["secrets"] = [
    {"name": k, "valueFrom": v} for k, v in sorted(secret_arns.items())
]

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
  --query 'service.status.statusCode' \
  --output text

echo ""
echo "Done. Migrated to Secrets Manager (see primaryContainer.secrets in ECS console)."
echo "Removed garbage env keys: medicine-recommend-db, postgres"
echo "Wait 2-4 min: curl -s https://aws.medicine.yutok.dev/health"
