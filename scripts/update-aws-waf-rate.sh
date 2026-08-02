#!/usr/bin/env bash
# WAF レート制限（RateLimitPerIp）を更新。大会向け緩和 / 事後復旧用。
#
# Usage:
#   WAF_RATE_LIMIT=10000 ./scripts/update-aws-waf-rate.sh
#   ./scripts/update-aws-waf-rate.sh --restore   # scripts/.aws-contest-capacity-state.json の waf_rate_limit へ
#   ./scripts/update-aws-waf-rate.sh --dry-run
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

STATE_FILE="$ROOT/scripts/.aws-contest-capacity-state.json"
WEB_ACL_NAME="${WAF_WEB_ACL_NAME:-${PROJECT_PREFIX}-web-acl}"
DRY_RUN=false
RESTORE=false
RATE_LIMIT="${WAF_RATE_LIMIT:-}"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --restore) RESTORE=true ;;
  esac
done

if [[ "$RESTORE" == true && -z "$RATE_LIMIT" ]]; then
  if [[ ! -f "$STATE_FILE" ]]; then
    echo "ERROR: $STATE_FILE not found (run prepare-aws-contest-capacity.sh --apply first)" >&2
    exit 1
  fi
  RATE_LIMIT="$(python3 - "$STATE_FILE" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    d = json.load(f)
print(d.get("waf_rate_limit_before", 2000))
PY
)"
fi

if [[ -z "$RATE_LIMIT" ]]; then
  RATE_LIMIT="${WAF_RATE_LIMIT:-2000}"
fi

WEB_ACL_ARN="$(aws wafv2 list-web-acls --scope REGIONAL --region "$AWS_REGION" \
  --query "WebACLs[?Name=='${WEB_ACL_NAME}'].ARN | [0]" --output text)"
if [[ -z "$WEB_ACL_ARN" || "$WEB_ACL_ARN" == "None" ]]; then
  echo "ERROR: Web ACL ${WEB_ACL_NAME} not found. Run ./scripts/setup-aws-waf.sh first." >&2
  exit 1
fi

CURRENT="$(aws wafv2 get-web-acl \
  --name "$WEB_ACL_NAME" \
  --scope REGIONAL \
  --id "$(aws wafv2 list-web-acls --scope REGIONAL --region "$AWS_REGION" \
    --query "WebACLs[?Name=='${WEB_ACL_NAME}'].Id | [0]" --output text)" \
  --region "$AWS_REGION" \
  --output json)"

BEFORE_LIMIT="$(python3 - "$CURRENT" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
for rule in data.get("WebACL", {}).get("Rules", []):
    if rule.get("Name") == "RateLimitPerIp":
        print(rule["Statement"]["RateBasedStatement"]["Limit"])
        break
else:
    print("?")
PY
)"

echo "==> WAF ${WEB_ACL_NAME}: ${BEFORE_LIMIT} -> ${RATE_LIMIT} req / 5min / IP"

if [[ "$BEFORE_LIMIT" == "$RATE_LIMIT" ]]; then
  echo "Already at target rate limit."
  exit 0
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would update-web-acl Limit=${RATE_LIMIT}"
  exit 0
fi

UPDATED_JSON="$(python3 - "$CURRENT" "$RATE_LIMIT" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
new_limit = int(sys.argv[2])
acl = data["WebACL"]
for rule in acl.get("Rules", []):
    if rule.get("Name") == "RateLimitPerIp":
        rule["Statement"]["RateBasedStatement"]["Limit"] = new_limit
        break
else:
    raise SystemExit("RateLimitPerIp rule not found")
out = {
    "Name": acl["Name"],
    "Scope": "REGIONAL",
    "Id": acl["Id"],
    "DefaultAction": acl["DefaultAction"],
    "Rules": acl["Rules"],
    "VisibilityConfig": acl["VisibilityConfig"],
    "LockToken": data["LockToken"],
}
print(json.dumps(out))
PY
)"

aws wafv2 update-web-acl \
  --region "$AWS_REGION" \
  --cli-input-json "$UPDATED_JSON" \
  --query '{Name:Summary.Name,ARN:Summary.ARN}' \
  --output table

echo "Done. WAF rate limit is now ${RATE_LIMIT}/5min/IP."
