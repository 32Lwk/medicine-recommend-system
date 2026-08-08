#!/usr/bin/env bash
# Wait until staging /health reports the expected git commit (live traffic signal).
#
# Replaces aws ecs wait services-stable for CodeBuild post_deploy — faster and
# directly verifies that the new revision is serving requests.
#
# Usage:
#   GIT_COMMIT=abc123 ./scripts/wait-staging-health-commit.sh
#   AWS_STAGING_URL=https://aws.medicine.yutok.dev ./scripts/wait-staging-health-commit.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

PRIMARY_URL="${AWS_STAGING_URL:-https://aws.medicine.yutok.dev}"
PRIMARY_URL="${PRIMARY_URL%/}"
FALLBACK_URL="${AWS_STAGING_FALLBACK_URL:-}"
if [[ -z "$FALLBACK_URL" ]]; then
  FALLBACK_URL="$(resolve_staging_health_url 2>/dev/null || true)"
fi
FALLBACK_URL="${FALLBACK_URL%/}"

EXPECTED_COMMIT="${GIT_COMMIT:-${CODEBUILD_RESOLVED_SOURCE_VERSION:-}}"
WAIT_SEC="${DEPLOY_HEALTH_WAIT_SEC:-420}"
POLL_SEC="${DEPLOY_HEALTH_POLL_SEC:-5}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd jq

if [[ -z "$EXPECTED_COMMIT" ]]; then
  echo "ERROR: GIT_COMMIT or CODEBUILD_RESOLVED_SOURCE_VERSION is required" >&2
  exit 1
fi

echo "==> wait staging /health for commit ${EXPECTED_COMMIT:0:12}"
echo "    primary: ${PRIMARY_URL}"
if [[ -n "$FALLBACK_URL" ]]; then
  echo "    fallback: ${FALLBACK_URL}"
fi
deadline=$((SECONDS + WAIT_SEC))

fetch_health() {
  local base="$1"
  curl -sf "${base}/health" 2>/dev/null || return 1
}

while (( SECONDS < deadline )); do
  resp=""
  active_url="$PRIMARY_URL"
  if resp="$(fetch_health "$PRIMARY_URL")"; then
    :
  elif [[ -n "$FALLBACK_URL" ]] && resp="$(fetch_health "$FALLBACK_URL")"; then
    active_url="$FALLBACK_URL"
    echo "    using fallback URL (custom domain TLS may be pending)"
  fi

  if [[ -n "$resp" ]]; then
    status="$(printf '%s' "$resp" | jq -r '.status // empty')"
    commit="$(printf '%s' "$resp" | jq -r '.git_commit // empty')"
    if [[ "$status" == "ok" ]]; then
      if [[ "$commit" == "$EXPECTED_COMMIT"* || "$commit" == "${EXPECTED_COMMIT:0:7}"* ]]; then
        echo "OK /health git_commit=${commit} url=${active_url}"
        exit 0
      fi
      echo "    waiting (current=${commit:-none}, want=${EXPECTED_COMMIT:0:7})..."
    fi
  else
    echo "    waiting for /health..."
  fi
  sleep "$POLL_SEC"
done

echo "ERROR: /health did not report commit ${EXPECTED_COMMIT:0:12} within ${WAIT_SEC}s" >&2
exit 1
