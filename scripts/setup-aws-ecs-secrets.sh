#!/usr/bin/env bash
# ECS Express: Secrets Manager 作成 + タスク定義更新 + サービス再デプロイ
#
# Usage:
#   export AWS_PROFILE=admin
#   cp .env.example .env   # OPENAI_API_KEY, DATABASE_URL, SECRET_KEY を記入
#   ./scripts/setup-aws-ecs-secrets.sh .env
#
set -euo pipefail

ENV_FILE="${1:-.env}"
REGION="${AWS_REGION:-ap-northeast-1}"
CLUSTER="${ECS_CLUSTER:-default}"
SERVICE="${ECS_SERVICE:-medicine-recommend}"
TASK_FAMILY="${ECS_TASK_FAMILY:-default-medicine-recommend}"
SECRET_PREFIX="${SECRET_PREFIX:-medicine-recommend/aws-staging}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "ERROR: ${name} is empty in ${ENV_FILE}" >&2
    exit 1
  fi
}

require_var OPENAI_API_KEY
require_var DATABASE_URL
require_var SECRET_KEY

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

put_secret() {
  local name="$1"
  local value="$2"
  local full="${SECRET_PREFIX}/${name}"
  if aws secretsmanager describe-secret --secret-id "$full" --region "$REGION" >/dev/null 2>&1; then
    aws secretsmanager put-secret-value --secret-id "$full" --secret-string "$value" --region "$REGION" >/dev/null
    echo "Updated secret ${full}" >&2
  else
    aws secretsmanager create-secret --name "$full" --secret-string "$value" --region "$REGION" >/dev/null
    echo "Created secret ${full}" >&2
  fi
  aws secretsmanager describe-secret --secret-id "$full" --region "$REGION" --query ARN --output text
}

echo "==> Upsert Secrets Manager entries" >&2
OPENAI_ARN="$(put_secret openai-api-key "$OPENAI_API_KEY")"
DB_ARN="$(put_secret database-url "$DATABASE_URL")"
SECRET_KEY_ARN="$(put_secret secret-key "$SECRET_KEY")"

ADMIN_ARN=""
if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  ADMIN_ARN="$(put_secret admin-password "$ADMIN_PASSWORD")"
fi

echo "==> Register new task definition revision" >&2
CURRENT="$(aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$REGION" --output json)"
NEW_ENV=$(python3 - "$CURRENT" "$OPENAI_ARN" "$DB_ARN" "$SECRET_KEY_ARN" "$ADMIN_ARN" <<'PY'
import json, sys
td = json.loads(sys.argv[1])["taskDefinition"]
for k in ("taskDefinitionArn", "revision", "status", "requiresAttributes", "compatibilities", "registeredAt", "registeredBy"):
    td.pop(k, None)
c = td["containerDefinitions"][0]
base = {e["name"]: e["value"] for e in c.get("environment") or []}
base.setdefault("APP_ENV", "production")
base.setdefault("PUBLIC_SITE_URL", "https://aws.medicine.yutok.dev")
base.setdefault("GUNICORN_WORKERS", "2")
base.setdefault("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")
base.setdefault("GUNICORN_TIMEOUT", "300")
c["environment"] = [{"name": k, "value": v} for k, v in sorted(base.items())]
c["secrets"] = [
    {"name": "OPENAI_API_KEY", "valueFrom": sys.argv[2]},
    {"name": "DATABASE_URL", "valueFrom": sys.argv[3]},
    {"name": "SECRET_KEY", "valueFrom": sys.argv[4]},
]
if sys.argv[5]:
    c["secrets"].append({"name": "ADMIN_PASSWORD", "valueFrom": sys.argv[5]})
print(json.dumps(td))
PY
)

NEW_ARN="$(aws ecs register-task-definition --region "$REGION" --cli-input-json "$NEW_ENV" --query 'taskDefinition.taskDefinitionArn' --output text)"
echo "Registered: ${NEW_ARN}" >&2

echo "==> Update ECS service" >&2
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --region "$REGION" \
  --query 'service.{taskDef:taskDefinition,status:status}' \
  --output table

echo ""
echo "Done. Wait 3-5 min, then:"
echo "  curl https://aws.medicine.yutok.dev/health"
echo "  Open https://aws.medicine.yutok.dev/ and send 頭痛"
