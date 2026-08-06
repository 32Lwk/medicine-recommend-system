#!/usr/bin/env bash
# Resume AWS staging after stop-aws-staging.sh (reversible).
#
# Usage:
#   ./scripts/resume-aws-staging.sh
#   ./scripts/resume-aws-staging.sh --desired-count 1
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

STATE_FILE="$ROOT/scripts/.aws-staging-stop-state.json"
PIPELINE_NAME="${PIPELINE_NAME:-medicine-recommend-main}"
SCALING_RESOURCE_ID="service/${ECS_CLUSTER}/${ECS_SERVICE}"
DESIRED="${1:-}"
MIN_CAP=1
MAX_CAP=1

if [[ "$DESIRED" == "--desired-count" ]]; then
  DESIRED="${2:-1}"
elif [[ -z "$DESIRED" ]]; then
  if [[ -f "$STATE_FILE" ]]; then
    DESIRED="$(python3 - "$STATE_FILE" <<'PY'
import json, os, subprocess, sys

path = sys.argv[1]
if not os.path.isfile(path):
    cygpath = subprocess.run(
        ["cygpath", "-w", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if cygpath.returncode == 0:
        path = cygpath.stdout.strip()
with open(path, encoding="utf-8") as f:
    data = json.load(f)
ecs = data.get("ecs", {})
print(ecs.get("previous_desired_count", 1))
PY
)"
    MIN_CAP="$(python3 - "$STATE_FILE" <<'PY'
import json, os, subprocess, sys
path = sys.argv[1]
if not os.path.isfile(path):
    cygpath = subprocess.run(["cygpath", "-w", path], capture_output=True, text=True, check=False)
    if cygpath.returncode == 0:
        path = cygpath.stdout.strip()
with open(path, encoding="utf-8") as f:
    ecs = json.load(f).get("ecs", {})
print(ecs.get("previous_min_capacity", 1))
PY
)"
    MAX_CAP="$(python3 - "$STATE_FILE" <<'PY'
import json, os, subprocess, sys
path = sys.argv[1]
if not os.path.isfile(path):
    cygpath = subprocess.run(["cygpath", "-w", path], capture_output=True, text=True, check=False)
    if cygpath.returncode == 0:
        path = cygpath.stdout.strip()
with open(path, encoding="utf-8") as f:
    ecs = json.load(f).get("ecs", {})
print(ecs.get("previous_max_capacity", 1))
PY
)"
  else
    DESIRED=1
  fi
fi

echo "==> AWS staging resume"
echo "    desiredCount=$DESIRED minCapacity=$MIN_CAP maxCapacity=$MAX_CAP pipeline=$PIPELINE_NAME"

aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id "$SCALING_RESOURCE_ID" \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity "$MIN_CAP" \
  --max-capacity "$MAX_CAP" \
  --region "$AWS_REGION" \
  --query '{MinCapacity:MinCapacity,MaxCapacity:MaxCapacity}' \
  --output table

aws codepipeline enable-stage-transition \
  --pipeline-name "$PIPELINE_NAME" \
  --stage-name Source \
  --transition-type Outbound \
  --region "$AWS_REGION"

aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --desired-count "$DESIRED" \
  --region "$AWS_REGION" \
  --query 'service.{desired:desiredCount,running:runningCount,status:status}' \
  --output json

echo ""
echo "Resumed. Wait 3–6 min, then: curl -s https://aws.medicine.yutok.dev/health"
