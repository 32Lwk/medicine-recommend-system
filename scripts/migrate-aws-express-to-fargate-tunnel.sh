#!/usr/bin/env bash
# Migrate ECS Express staging -> Fargate + Cloudflare Tunnel (no ALB).
#
# Usage:
#   CLOUDFLARE_TUNNEL_TOKEN=... AWS_PROFILE=default ./scripts/migrate-aws-express-to-fargate-tunnel.sh --confirm
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

CONFIRM=false
DRY_RUN=false
TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"
ORIGIN_HOST="${TUNNEL_ORIGIN_HOST:-origin-aws-medicine.yutok.dev}"
EXPORT_FILE="$ROOT/scripts/.aws-express-export.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm) CONFIRM=true ;;
    --dry-run) DRY_RUN=true ;;
    --tunnel-token) TUNNEL_TOKEN="$2"; shift ;;
    --origin-host) ORIGIN_HOST="$2"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
  shift
done

if [[ -z "$TUNNEL_TOKEN" ]]; then
  echo "ERROR: set CLOUDFLARE_TUNNEL_TOKEN or --tunnel-token" >&2
  exit 1
fi

if [[ "$CONFIRM" != true && "$DRY_RUN" != true ]]; then
  echo "ERROR: pass --confirm (or --dry-run)" >&2
  exit 1
fi

echo "==> Step 1/4: export Express configuration"
python3 "$ROOT/scripts/export_aws_express_config.py" --output "$EXPORT_FILE"

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would delete Express and create Fargate tunnel service"
  bash "$ROOT/scripts/setup-aws-fargate-tunnel.sh" --dry-run --from-export "$EXPORT_FILE" --tunnel-token "$TUNNEL_TOKEN" --origin-host "$ORIGIN_HOST"
  exit 0
fi

echo "==> Step 2/4: delete ECS Express (ALB removed)"
bash "$ROOT/scripts/delete-aws-express-staging.sh" --confirm

echo "==> Step 3/4: create Fargate + Cloudflare Tunnel ECS service"
bash "$ROOT/scripts/setup-aws-fargate-tunnel.sh" \
  --from-export "$EXPORT_FILE" \
  --tunnel-token "$TUNNEL_TOKEN" \
  --origin-host "$ORIGIN_HOST"

echo "==> Step 4/4: update cold-start metadata"
python3 - "$ROOT/scripts/.aws-staging-cold-start.json" <<'PY'
import json, sys
from datetime import datetime, timezone
path = sys.argv[1]
try:
    data = json.load(open(path, encoding="utf-8"))
except FileNotFoundError:
    data = {}
data["deploy_mode"] = "fargate_tunnel"
data["migrated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(path, "a", encoding="utf-8").write("\n")
print(f"updated {path}")
PY

cat > "$ROOT/scripts/.aws-deploy-mode" <<EOF
fargate_tunnel
EOF

echo ""
echo "=== Migration complete ==="
echo "  Export backup: ${EXPORT_FILE}"
echo "  State: scripts/.aws-fargate-tunnel.json"
echo ""
echo "Manual steps:"
echo "  1. Cloudflare Zero Trust -> Tunnel -> Public hostname:"
echo "     ${ORIGIN_HOST} -> http://localhost:8080"
echo "  2. workers/wrangler.toml ORIGIN_URL=https://${ORIGIN_HOST}"
echo "  3. cd workers && npx wrangler deploy"
echo "  4. ./scripts/resume-aws-staging.sh"
echo "  5. curl -s https://aws-medicine.yutok.dev/health"
