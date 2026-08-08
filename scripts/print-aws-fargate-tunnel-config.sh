#!/usr/bin/env bash
# Print Fargate tunnel staging config (for Worker / DNS verification).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/scripts/.aws-fargate-tunnel.json"

if [[ ! -f "$STATE" ]]; then
  echo "ERROR: $STATE not found. Run migrate-aws-express-to-fargate-tunnel.sh first." >&2
  exit 1
fi

python3 - "$STATE" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
print("deploy_mode:", data.get("deploy_mode"))
print("origin_url:", data.get("origin_url"))
print("worker_url:", data.get("worker_url"))
print("task_family:", data.get("task_family"))
print("cluster/service:", data.get("cluster"), "/", data.get("service"))
print("")
print("Cloudflare Tunnel hostname -> http://localhost:8080")
print("Worker ORIGIN_URL should match origin_url")
PY
