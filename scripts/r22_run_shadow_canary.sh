#!/usr/bin/env bash
# R22: shadow ON → warm → 50 persona canary → OFF → verify.
# PRIMARY=0 D2=0 locked. Synthetic only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"
export AWS_PROFILE="${AWS_PROFILE:-default}"

OUT="${1:-log/analysis/jev_r22_persona_canary.json}"
LIMIT="${LIMIT:-50}"
PY="${ROOT}/.venv/Scripts/python.exe"
if [[ ! -x "$PY" && ! -f "$PY" ]]; then
  PY="python"
fi

echo "==> R22 canary pipeline start (py=$PY)"
bash "$ROOT/scripts/r21_staging_shadow_flags.sh" on

# Wait ECS primary completed
for i in $(seq 1 36); do
  STATE="$(aws ecs describe-services --cluster "${ECS_CLUSTER:-default}" --services "${ECS_SERVICE:-medicine-recommend}" --region "${AWS_REGION:-ap-northeast-1}" --query 'services[0].deployments[0].rolloutState' --output text 2>/dev/null || echo UNKNOWN)"
  echo "deploy rollout=$STATE ($i)"
  if [[ "$STATE" == "COMPLETED" ]]; then
    break
  fi
  sleep 10
done

# Extra settle for tunnel interstitial
sleep 20

set +e
"$PY" "$ROOT/scripts/r22_staging_persona_canary.py" --wait-stable --limit "$LIMIT" --out "$ROOT/$OUT"
RC=$?
set -e

echo "==> Always OFF after canary (rc=$RC)"
bash "$ROOT/scripts/r21_staging_shadow_flags.sh" off

for i in $(seq 1 24); do
  if "$PY" "$ROOT/scripts/r21_verify_staging_flags.py"; then
    break
  fi
  sleep 10
done

exit "$RC"
