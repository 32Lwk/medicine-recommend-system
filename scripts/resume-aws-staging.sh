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
DESIRED="${1:-}"

if [[ "$DESIRED" == "--desired-count" ]]; then
  DESIRED="${2:-1}"
elif [[ -z "$DESIRED" ]]; then
  if [[ -f "$STATE_FILE" ]]; then
    DESIRED="$(python3 - "$STATE_FILE" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    print(json.load(f)["ecs"]["previous_desired_count"])
PY
)"
  else
    DESIRED=1
  fi
fi

echo "==> AWS staging resume"
echo "    desiredCount=$DESIRED pipeline=$PIPELINE_NAME"

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
echo "Resumed. Verify: curl -sI https://aws.medicine.yutok.dev/health"
