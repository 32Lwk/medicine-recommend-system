#!/usr/bin/env bash
# ECS Fargate + Cloudflare Tunnel staging (no ALB).
#
# Usage:
#   CLOUDFLARE_TUNNEL_TOKEN=... AWS_PROFILE=default ./scripts/setup-aws-fargate-tunnel.sh
#   ./scripts/setup-aws-fargate-tunnel.sh --from-export scripts/.aws-express-export.json
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"
ORIGIN_HOST="${TUNNEL_ORIGIN_HOST:-origin-aws-medicine.yutok.dev}"
FROM_EXPORT=""
DRY_RUN=""
EXTRA=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN="--dry-run" ;;
    --from-export) FROM_EXPORT="$2"; shift ;;
    --tunnel-token) TUNNEL_TOKEN="$2"; shift ;;
    --origin-host) ORIGIN_HOST="$2"; shift ;;
    *) EXTRA+=("$1") ;;
  esac
  shift
done

if [[ -z "$TUNNEL_TOKEN" ]]; then
  echo "ERROR: set CLOUDFLARE_TUNNEL_TOKEN or --tunnel-token" >&2
  echo "  See docs/ops/AWS_FARGATE_TUNNEL.md" >&2
  exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

ARGS=(
  python3 "$ROOT/scripts/setup_fargate_tunnel.py"
  --region "$AWS_REGION"
  --account-id "$ACCOUNT_ID"
  --cluster "$ECS_CLUSTER"
  --service "$ECS_SERVICE"
  --task-family "${FARGATE_TASK_FAMILY:-medicine-recommend-tunnel}"
  --project-prefix "$PROJECT_PREFIX"
  --log-group "/ecs/${PROJECT_PREFIX}"
  --tunnel-token "$TUNNEL_TOKEN"
  --origin-host "$ORIGIN_HOST"
)
[[ -n "$FROM_EXPORT" ]] && ARGS+=(--from-export "$FROM_EXPORT")
[[ -n "$DRY_RUN" ]] && ARGS+=("$DRY_RUN")
ARGS+=("${EXTRA[@]}")

echo "==> setup-aws-fargate-tunnel (account=${ACCOUNT_ID})"
"${ARGS[@]}"

echo ""
echo "Next:"
echo "  1. Cloudflare Tunnel: ${ORIGIN_HOST} -> http://localhost:8080"
echo "  2. workers/wrangler.toml ORIGIN_URL=https://${ORIGIN_HOST}"
echo "  3. wrangler deploy && ./scripts/resume-aws-staging.sh"
