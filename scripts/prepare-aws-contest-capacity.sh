#!/usr/bin/env bash
# 大会本番向け: ECS 事前スケール + CPU/Memory 引き上げ + WAF 緩和
#
# 推奨タイミング: T-1（前日）〜 当日開始90分前。適用中はローリングデプロイが走る。
#
# Usage:
#   ./scripts/prepare-aws-contest-capacity.sh --dry-run
#   ./scripts/prepare-aws-contest-capacity.sh --apply
#   ./scripts/prepare-aws-contest-capacity.sh --restore
#
# 上書き例（1 vCPU / 2GB / タスク10 / WAF 10000）:
#   CONTEST_ECS_CPU=1024 CONTEST_ECS_MEMORY=2048 CONTEST_DESIRED_COUNT=10 \
#   CONTEST_WAF_RATE_LIMIT=10000 GUNICORN_WORKERS=3 \
#     ./scripts/prepare-aws-contest-capacity.sh --apply
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

STATE_FILE="$ROOT/scripts/.aws-contest-capacity-state.json"
MODE="dry-run"

# 1 vCPU + 2GB（Fargate 1024 CPU の最小 memory は 2048）
CONTEST_ECS_CPU="${CONTEST_ECS_CPU:-1024}"
CONTEST_ECS_MEMORY="${CONTEST_ECS_MEMORY:-2048}"
CONTEST_MIN_TASKS="${CONTEST_MIN_TASKS:-10}"
CONTEST_MAX_TASKS="${CONTEST_MAX_TASKS:-10}"
CONTEST_DESIRED_COUNT="${CONTEST_DESIRED_COUNT:-10}"
CONTEST_CPU_TARGET="${CONTEST_CPU_TARGET:-70}"
CONTEST_WAF_RATE_LIMIT="${CONTEST_WAF_RATE_LIMIT:-10000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

for arg in "$@"; do
  case "$arg" in
    --apply) MODE="apply" ;;
    --restore) MODE="restore" ;;
    --dry-run) MODE="dry-run" ;;
  esac
done

save_state() {
  python3 - "$STATE_FILE" "$@" <<'PY'
import json, sys, datetime
path = sys.argv[1]
payload = json.loads(sys.argv[2])
payload["saved_at"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"State saved: {path}")
PY
}

capture_current() {
  SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"
  EXPRESS_JSON="$(aws ecs describe-express-gateway-service \
    --service-arn "$SERVICE_ARN" \
    --region "$AWS_REGION" \
    --output json)"
  SVC_JSON="$(aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --output json)"

  python3 - "$EXPRESS_JSON" "$SVC_JSON" "$WEB_ACL_NAME" "$AWS_REGION" <<'PY'
import json, subprocess, sys

express = json.loads(sys.argv[1])
svc = json.loads(sys.argv[2])[0]
acl_name, region = sys.argv[3], sys.argv[4]
cfg = express["service"]["activeConfigurations"][0]
scaling = cfg.get("scalingTarget") or {}

waf_limit = 2000
try:
    acl_id = subprocess.check_output(
        ["aws", "wafv2", "list-web-acls", "--scope", "REGIONAL", "--region", region,
         "--query", f"WebACLs[?Name=='{acl_name}'].Id | [0]", "--output", "text"],
        text=True,
    ).strip()
    if acl_id and acl_id != "None":
        raw = subprocess.check_output(
            ["aws", "wafv2", "get-web-acl", "--name", acl_name, "--scope", "REGIONAL",
             "--id", acl_id, "--region", region, "--output", "json"],
            text=True,
        )
        for rule in json.loads(raw)["WebACL"].get("Rules", []):
            if rule.get("Name") == "RateLimitPerIp":
                waf_limit = rule["Statement"]["RateBasedStatement"]["Limit"]
                break
except Exception:
    pass

env = {e["name"]: e["value"] for e in (cfg["primaryContainer"].get("environment") or []) if e.get("name")}
print(json.dumps({
    "cpu": str(cfg["cpu"]),
    "memory": str(cfg["memory"]),
    "desired_count": svc.get("desiredCount"),
    "min_tasks": scaling.get("minTaskCount"),
    "max_tasks": scaling.get("maxTaskCount"),
    "cpu_target": scaling.get("autoScalingTargetValue"),
    "gunicorn_workers": env.get("GUNICORN_WORKERS", "2"),
    "waf_rate_limit_before": waf_limit,
}, ensure_ascii=False))
PY
}

apply_contest() {
  echo "==> Contest capacity prepare (mode=${MODE})"
  echo "    ECS: ${CONTEST_ECS_CPU} CPU / ${CONTEST_ECS_MEMORY} MiB"
  echo "    Tasks: desired=${CONTEST_DESIRED_COUNT} min=${CONTEST_MIN_TASKS} max=${CONTEST_MAX_TASKS}"
  echo "    GUNICORN_WORKERS=${GUNICORN_WORKERS}"
  echo "    WAF: ${CONTEST_WAF_RATE_LIMIT} req / 5min / IP"

  if [[ "$MODE" == "dry-run" ]]; then
    echo "[dry-run] would save state to ${STATE_FILE}"
    echo "[dry-run] would run tune-aws-ecs-capacity.sh"
    echo "[dry-run] would run update-aws-waf-rate.sh"
    echo "[dry-run] would update-service desiredCount=${CONTEST_DESIRED_COUNT}"
    exit 0
  fi

  BEFORE_JSON="$(capture_current)"
  save_state "$BEFORE_JSON"

  ECS_CPU="$CONTEST_ECS_CPU" \
  ECS_MEMORY="$CONTEST_ECS_MEMORY" \
  ECS_MIN_TASKS="$CONTEST_MIN_TASKS" \
  ECS_MAX_TASKS="$CONTEST_MAX_TASKS" \
  ECS_CPU_TARGET="$CONTEST_CPU_TARGET" \
  GUNICORN_WORKERS="$GUNICORN_WORKERS" \
    "$ROOT/scripts/tune-aws-ecs-capacity.sh"

  WAF_RATE_LIMIT="$CONTEST_WAF_RATE_LIMIT" "$ROOT/scripts/update-aws-waf-rate.sh"

  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --desired-count "$CONTEST_DESIRED_COUNT" \
    --region "$AWS_REGION" \
    --query 'service.{desired:desiredCount,running:runningCount,status:status}' \
    --output table

  echo ""
  echo "Applied. Wait 5-10 min for rollout, then verify:"
  echo "  curl -s https://aws.medicine.yutok.dev/health"
  echo "Restore after event: ./scripts/prepare-aws-contest-capacity.sh --restore"
}

restore_contest() {
  if [[ ! -f "$STATE_FILE" ]]; then
    echo "ERROR: ${STATE_FILE} not found" >&2
    exit 1
  fi
  if [[ "$MODE" == "dry-run" ]]; then
    echo "[dry-run] would restore from ${STATE_FILE}"
    python3 - "$STATE_FILE" <<'PY'
import json, sys
print(json.dumps(json.load(open(sys.argv[1], encoding="utf-8")), indent=2, ensure_ascii=False))
PY
    exit 0
  fi

  read -r RESTORE_CPU RESTORE_MEMORY RESTORE_DESIRED RESTORE_MIN RESTORE_MAX RESTORE_CPU_TARGET RESTORE_WORKERS <<EOF
$(python3 - "$STATE_FILE" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(
    d.get("cpu", "512"),
    d.get("memory", "1024"),
    d.get("desired_count", 2),
    d.get("min_tasks", 1),
    d.get("max_tasks", 10),
    d.get("cpu_target", 70),
    d.get("gunicorn_workers", "2"),
)
PY
)
EOF

  echo "==> Restore contest capacity from ${STATE_FILE}"
  ECS_CPU="$RESTORE_CPU" \
  ECS_MEMORY="$RESTORE_MEMORY" \
  ECS_MIN_TASKS="${RESTORE_MIN:-1}" \
  ECS_MAX_TASKS="${RESTORE_MAX:-10}" \
  ECS_CPU_TARGET="${RESTORE_CPU_TARGET:-70}" \
  GUNICORN_WORKERS="$RESTORE_WORKERS" \
    "$ROOT/scripts/tune-aws-ecs-capacity.sh"

  "$ROOT/scripts/update-aws-waf-rate.sh" --restore

  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --desired-count "$RESTORE_DESIRED" \
    --region "$AWS_REGION" \
    --query 'service.{desired:desiredCount,running:runningCount}' \
    --output table

  echo "Restored."
}

case "$MODE" in
  restore) restore_contest ;;
  *) apply_contest ;;
esac
